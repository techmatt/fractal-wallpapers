//! Supersampled colors → an 8-bit sRGB image.
//!
//! Two things happen here, and the order of them is the whole point.
//!
//! **The filter is Lanczos-3, scaled to the reduction.** A box average — add up
//! each output pixel's own subsamples and divide — is what most renderers do and
//! it aliases: it ignores everything just outside the pixel, so a filament that
//! crosses a pixel boundary contributes to one side and not the other. A
//! windowed sinc of radius 3 reaches three *output* pixels either way, which at
//! `ss` subsamples per pixel is a radius of `3·ss` in the source. Getting that
//! scaling wrong — using a radius of 3 source samples — under-blurs and aliases
//! about as badly as the box does.
//!
//! **The filtering happens in linear light, the encoding after.** Averaging
//! gamma-encoded values darkens every edge in the image, because the encoding is
//! curved and the average of a curve is not the curve of the average. So the
//! whole resample runs on linear values and `linear_to_srgb` is applied once, at
//! the very end, to the result.
//!
//! Lanczos has negative lobes, which means a high-contrast edge overshoots past
//! the ends of the range. That is what makes it sharp; it also means the result
//! must be clamped before it becomes 8-bit.

use rayon::prelude::*;

use crate::colormap::linear_to_srgb;

/// Kernel radius in output pixels.
const RADIUS: f64 = 3.0;

/// The Lanczos-3 kernel: a sinc windowed by a wider sinc.
fn lanczos3(x: f64) -> f64 {
    let x = x.abs();
    if x < 1e-12 {
        return 1.0;
    }
    if x >= RADIUS {
        return 0.0;
    }
    let pi_x = std::f64::consts::PI * x;
    let windowed = pi_x / RADIUS;
    (pi_x.sin() / pi_x) * (windowed.sin() / windowed)
}

/// One output coordinate's kernel: where its run of source samples starts, and
/// the weights over that run, already normalized to sum to 1.
struct Taps {
    start: usize,
    weights: Vec<f64>,
}

/// Precompute the kernel for every output coordinate of a 1-D reduction.
///
/// Output coordinate `d` is centered at source position `(d + 0.5)·ss`, and
/// source sample `s` sits at `s + 0.5`. Weights are renormalized per output
/// coordinate because the kernel gets clipped at the edges of the image, and an
/// unnormalized clipped kernel darkens the border.
fn build_taps(destination_len: usize, source_len: usize, ss: u32) -> Vec<Taps> {
    let ratio = ss as f64;
    let reach = RADIUS * ratio;
    (0..destination_len)
        .map(|d| {
            let center = (d as f64 + 0.5) * ratio;
            let first = ((center - reach).floor().max(0.0)) as usize;
            let last = ((center + reach).ceil() as usize).min(source_len - 1);
            let mut weights: Vec<f64> = (first..=last)
                .map(|s| lanczos3((s as f64 + 0.5 - center) / ratio))
                .collect();
            let total: f64 = weights.iter().sum();
            if total != 0.0 {
                for weight in &mut weights {
                    *weight /= total;
                }
            }
            Taps {
                start: first,
                weights,
            }
        })
        .collect()
}

/// Reduce a supersampled linear-light image to `out_width × out_height` sRGB8.
///
/// Separable: a horizontal pass, then a vertical one over the intermediate.
/// Doing it separably rather than with a 2-D kernel turns `(6·ss)²` multiplies
/// per output pixel into `2·(6·ss)`, which at `ss = 4` is the difference between
/// a render that resamples in a second and one that resamples in a minute.
pub fn downsample(
    linear: &[[f64; 3]],
    source_width: usize,
    source_height: usize,
    out_width: usize,
    out_height: usize,
    ss: u32,
) -> Vec<u8> {
    let horizontal = build_taps(out_width, source_width, ss);
    let vertical = build_taps(out_height, source_height, ss);

    // Horizontal pass: every source row narrowed to the output width.
    let narrowed: Vec<Vec<[f64; 3]>> = (0..source_height)
        .into_par_iter()
        .map(|row| {
            let base = row * source_width;
            horizontal
                .iter()
                .map(|taps| {
                    let mut sum = [0.0f64; 3];
                    for (offset, &weight) in taps.weights.iter().enumerate() {
                        let source = linear[base + taps.start + offset];
                        for channel in 0..3 {
                            sum[channel] += weight * source[channel];
                        }
                    }
                    sum
                })
                .collect()
        })
        .collect();

    // Vertical pass: clamp the filter's overshoot, then encode.
    let rows: Vec<Vec<u8>> = vertical
        .par_iter()
        .map(|taps| {
            let mut accumulated = vec![[0.0f64; 3]; out_width];
            for (offset, &weight) in taps.weights.iter().enumerate() {
                let source_row = &narrowed[taps.start + offset];
                for (target, source) in accumulated.iter_mut().zip(source_row) {
                    for channel in 0..3 {
                        target[channel] += weight * source[channel];
                    }
                }
            }
            let mut row = Vec::with_capacity(out_width * 3);
            for pixel in accumulated {
                for channel in pixel {
                    let encoded = linear_to_srgb(channel.clamp(0.0, 1.0));
                    row.push((encoded * 255.0 + 0.5) as u8);
                }
            }
            row
        })
        .collect();

    rows.concat()
}

/// Write an RGB8 buffer as a PNG.
pub fn write_png(
    path: &std::path::Path,
    pixels: &[u8],
    width: u32,
    height: u32,
) -> Result<(), String> {
    if let Some(parent) = path.parent()
        && !parent.as_os_str().is_empty()
    {
        std::fs::create_dir_all(parent).map_err(|e| format!("create {}: {e}", parent.display()))?;
    }
    let file =
        std::fs::File::create(path).map_err(|e| format!("create {}: {e}", path.display()))?;
    let mut encoder = png::Encoder::new(std::io::BufWriter::new(file), width, height);
    encoder.set_color(png::ColorType::Rgb);
    encoder.set_depth(png::BitDepth::Eight);
    let mut writer = encoder
        .write_header()
        .map_err(|e| format!("write header {}: {e}", path.display()))?;
    writer
        .write_image_data(pixels)
        .map_err(|e| format!("write {}: {e}", path.display()))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_kernel_is_one_at_the_center_and_zero_at_the_integers() {
        assert!((lanczos3(0.0) - 1.0).abs() < 1e-12);
        for n in 1..=3 {
            assert!(lanczos3(n as f64).abs() < 1e-9, "nonzero at {n}");
        }
        assert_eq!(lanczos3(3.5), 0.0);
    }

    #[test]
    fn every_output_coordinates_weights_sum_to_one() {
        for ss in [1u32, 2, 4] {
            for taps in build_taps(16, 16 * ss as usize, ss) {
                let total: f64 = taps.weights.iter().sum();
                assert!((total - 1.0).abs() < 1e-12, "ss {ss}: sum {total}");
            }
        }
    }

    /// A flat field must stay flat — including at the border, where the kernel
    /// is clipped. This is the property the per-coordinate renormalization buys.
    #[test]
    fn a_constant_image_survives_the_resample() {
        let (out_w, out_h, ss) = (8usize, 5usize, 4u32);
        let (src_w, src_h) = (out_w * ss as usize, out_h * ss as usize);
        let gray = crate::colormap::srgb_to_linear(128.0 / 255.0);
        let linear = vec![[gray; 3]; src_w * src_h];
        let pixels = downsample(&linear, src_w, src_h, out_w, out_h, ss);
        assert_eq!(pixels.len(), out_w * out_h * 3);
        for &value in &pixels {
            assert_eq!(value, 128, "constant image resampled unevenly");
        }
    }

    /// A hard edge overshoots under a windowed sinc. The clamp is what keeps
    /// that overshoot from wrapping around into the opposite color.
    #[test]
    fn a_hard_edge_stays_inside_the_range() {
        let (out_w, out_h, ss) = (8usize, 1usize, 4u32);
        let (src_w, src_h) = (out_w * ss as usize, out_h * ss as usize);
        let linear: Vec<[f64; 3]> = (0..src_w * src_h)
            .map(|i| {
                if i % src_w < src_w / 2 {
                    [0.0; 3]
                } else {
                    [1.0; 3]
                }
            })
            .collect();
        let pixels = downsample(&linear, src_w, src_h, out_w, out_h, ss);
        assert_eq!(pixels[0], 0);
        assert_eq!(*pixels.last().unwrap(), 255);
    }
}
