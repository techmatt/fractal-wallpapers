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
pub struct Taps {
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
    build_taps_at(destination_len, source_len, 0.0, ss as f64)
}

/// The same kernel, for a reduction that starts at a fractional `origin` and
/// runs at a non-integer `ratio`.
///
/// A whole-frame render reduces the supersampled grid by an integer factor from
/// its very first sample, which is the case [`build_taps`] covers. A *crop* of a
/// larger field does neither: it begins part-way into the field, at a fraction
/// of a subpixel, and its ratio is the crop's scale times the field's
/// supersampling — which a random scale makes irrational. Both facts land here
/// and nowhere else, so the filter itself is the same kernel at the same reach.
pub fn build_taps_at(
    destination_len: usize,
    source_len: usize,
    origin: f64,
    ratio: f64,
) -> Vec<Taps> {
    let reach = RADIUS * ratio;
    (0..destination_len)
        .map(|d| {
            let center = origin + (d as f64 + 0.5) * ratio;
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

/// Reduce a linear-light buffer through kernels somebody else built.
///
/// [`downsample`] is this with the kernels of a whole-frame render; the tile
/// builder passes the kernels of a crop. Splitting the two apart keeps one
/// implementation of the separable passes and the sRGB encoding, which is the
/// half that is easy to get subtly wrong twice.
pub fn apply_taps(
    linear: &[[f64; 3]],
    source_width: usize,
    source_height: usize,
    horizontal: &[Taps],
    vertical: &[Taps],
) -> Vec<u8> {
    let out_width = horizontal.len();

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
                encode(pixel, &mut row);
            }
            row
        })
        .collect();

    rows.concat()
}

/// Reduce a supersampled linear-light image to `out_width × out_height` sRGB8.
///
/// Separable: a horizontal pass, then a vertical one over the intermediate.
/// Doing it separably rather than with a 2-D kernel turns `(6·ss)²` multiplies
/// per output pixel into `2·(6·ss)`, which at `ss = 4` is the difference between
/// a render that resamples in a second and one that resamples in a minute.
///
/// **At `ss = 1` there is no reduction and both passes are skipped.** The kernel
/// is centered on the one source sample the output pixel *is*, and every other
/// tap lands on an integer offset, where a windowed sinc is zero — so the
/// normalized weights are one on the center and nothing anywhere else, and the
/// two passes are a long way to copy a buffer.
///
/// Skipping them is **byte-identical**, checked by
/// [`the_ss1_skip_is_the_filter_it_skips`] over a ramp and a hard edge, and by
/// 171 real renders — every family through every catalogued mode at the node
/// regime — before it landed. The residual the skip removes is real but is not
/// visible at eight bits: the off-center taps normalize to about `6e-17`
/// together, which is `5e-15` of one 8-bit code value, so a byte could only move
/// for a pixel that lands that close to a rounding boundary.
///
/// It is worth skipping because the node regime — 384x216 at `ss = 1`, the
/// walk's own frame, drawn tens of thousands of times a run — is the `ss = 1`
/// case, and the two passes are about **0.9 ms** of it.
///
/// [`the_ss1_skip_is_the_filter_it_skips`]: tests::the_ss1_skip_is_the_filter_it_skips
pub fn downsample(
    linear: &[[f64; 3]],
    source_width: usize,
    source_height: usize,
    out_width: usize,
    out_height: usize,
    ss: u32,
) -> Vec<u8> {
    if ss == 1 && source_width == out_width && source_height == out_height {
        return encode_only(linear);
    }
    let horizontal = build_taps(out_width, source_width, ss);
    let vertical = build_taps(out_height, source_height, ss);
    apply_taps(linear, source_width, source_height, &horizontal, &vertical)
}

/// Clamp one linear-light pixel's overshoot and encode it, onto the end of a row.
///
/// The last two steps of a reduction, and the whole of what a frame that was
/// never supersampled needs doing to it.
///
/// Inlined by request: it is called once per output pixel from inside the
/// filter's own hot loop, which is where it used to be written out.
#[inline]
fn encode(pixel: [f64; 3], row: &mut Vec<u8>) {
    for channel in pixel {
        let encoded = linear_to_srgb(channel.clamp(0.0, 1.0));
        row.push((encoded * 255.0 + 0.5) as u8);
    }
}

/// A buffer that is already at output resolution, encoded and nothing else.
///
/// **In parallel, and that is not an optimization of the skip — it is what makes
/// the skip a saving at all.** The two passes it replaces cost about fifty
/// multiply-adds per output pixel, and this costs one `powf`; but that `powf` is
/// the expensive half and [`apply_taps`] was already spreading it over every
/// core. Measured serial against the filter at the node regime, skipping the
/// passes was 0.85x — *slower* — because it traded fifty cheap operations for
/// losing the parallelism on the one costly one. Chunked, the same skip is a
/// clear win. A future edit that quietly makes this serial reverses the sign of
/// the whole leg.
fn encode_only(linear: &[[f64; 3]]) -> Vec<u8> {
    linear
        .par_chunks(ENCODE_CHUNK)
        .map(|chunk| {
            let mut bytes = Vec::with_capacity(chunk.len() * 3);
            for &pixel in chunk {
                encode(pixel, &mut bytes);
            }
            bytes
        })
        .collect::<Vec<Vec<u8>>>()
        .concat()
}

/// Pixels one worker encodes at a time.
///
/// The filter's own unit of parallel work is a row, and this is a row of a wide
/// frame rounded to a power of two: small enough that a 384-pixel walk frame
/// still reaches every core, large enough that the per-chunk `Vec` is not most
/// of the cost.
const ENCODE_CHUNK: usize = 2048;

/// JPEG quality for the steering thumbnails, on the encoder's 0–100 scale.
///
/// High enough that the compression is invisible at the sizes these are looked
/// at, low enough that a walk's tens of thousands of them fit somewhere.
const JPEG_QUALITY: u8 = 90;

/// Write an image, picking the encoder from the file name.
///
/// Two formats, and the choice between them is not a preference: a finished
/// render is a **PNG**, because it is the picture and a picture that has been
/// through a lossy encoder is a different picture. A walk's steering thumbnail
/// is a **JPEG**, because there are tens of thousands of them and they exist to
/// be glanced at, scored, and thrown away. Measured over eight of a real walk's
/// own frames at 384 pixels wide, the same picture is a median **2.4×** larger
/// as a PNG (2.0× to 3.0×) — which over a long run is the difference between a
/// record that fits beside its ledger and one that does not.
///
/// The extension decides, rather than a parameter, so the choice is visible in
/// the path that gets recorded rather than in a flag that does not.
pub fn write_image(
    path: &std::path::Path,
    pixels: &[u8],
    width: u32,
    height: u32,
) -> Result<(), String> {
    let lossy = path
        .extension()
        .and_then(|e| e.to_str())
        .is_some_and(|e| e.eq_ignore_ascii_case("jpg") || e.eq_ignore_ascii_case("jpeg"));
    if lossy {
        write_jpeg(path, pixels, width, height)
    } else {
        write_png(path, pixels, width, height)
    }
}

fn make_parent(path: &std::path::Path) -> Result<(), String> {
    if let Some(parent) = path.parent()
        && !parent.as_os_str().is_empty()
    {
        std::fs::create_dir_all(parent).map_err(|e| format!("create {}: {e}", parent.display()))?;
    }
    Ok(())
}

/// Write an 8-bit sRGB image as a JPEG at the thumbnail quality.
pub fn write_jpeg(
    path: &std::path::Path,
    pixels: &[u8],
    width: u32,
    height: u32,
) -> Result<(), String> {
    write_jpeg_at(path, pixels, width, height, JPEG_QUALITY)
}

/// Write an 8-bit sRGB image as a JPEG at a stated quality.
///
/// A training tile draws its own quality, because the compression a judge will
/// meet at deploy time is not a constant and a head trained at one quality reads
/// the artifacts of another as structure.
pub fn write_jpeg_at(
    path: &std::path::Path,
    pixels: &[u8],
    width: u32,
    height: u32,
    quality: u8,
) -> Result<(), String> {
    make_parent(path)?;
    let file =
        std::fs::File::create(path).map_err(|e| format!("create {}: {e}", path.display()))?;
    let encoder = jpeg_encoder::Encoder::new(std::io::BufWriter::new(file), quality);
    let (width, height) = (u16::try_from(width), u16::try_from(height));
    let (Ok(width), Ok(height)) = (width, height) else {
        return Err(format!(
            "{}: JPEG holds at most 65535 pixels per side",
            path.display()
        ));
    };
    encoder
        .encode(pixels, width, height, jpeg_encoder::ColorType::Rgb)
        .map_err(|e| format!("write {}: {e}", path.display()))
}

/// Write an 8-bit sRGB image as a PNG.
pub fn write_png(
    path: &std::path::Path,
    pixels: &[u8],
    width: u32,
    height: u32,
) -> Result<(), String> {
    make_parent(path)?;
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

    /// **The `ss = 1` skip is the filter it skips, byte for byte.**
    ///
    /// The claim the skip rests on: at `ss = 1` the Lanczos kernel normalizes to
    /// one on the center tap and zero everywhere else, so running the two passes
    /// and not running them cannot differ. Checked on the two patterns that would
    /// break it if anything would — a ramp, where every pixel differs from its
    /// neighbours by a little and a residual weight would show, and a hard edge,
    /// where it would show by a lot.
    #[test]
    fn the_ss1_skip_is_the_filter_it_skips() {
        let (width, height) = (37usize, 23usize);
        let ramp: Vec<[f64; 3]> = (0..width * height)
            .map(|i| {
                let t = i as f64 / (width * height) as f64;
                [t, 1.0 - t, (t * 7.0).fract()]
            })
            .collect();
        let edge: Vec<[f64; 3]> = (0..width * height)
            .map(|i| {
                if (i % width) < width / 2 {
                    [0.0, 0.0, 0.0]
                } else {
                    [1.0, 1.0, 1.0]
                }
            })
            .collect();
        for (name, linear) in [("ramp", &ramp), ("edge", &edge)] {
            let horizontal = build_taps(width, width, 1);
            let vertical = build_taps(height, height, 1);
            let filtered = apply_taps(linear, width, height, &horizontal, &vertical);
            let skipped = downsample(linear, width, height, width, height, 1);
            assert_eq!(filtered, skipped, "{name}");
        }
    }

    /// The weights the skip is allowed to drop: one on the center tap, and
    /// nothing that survives being added to it anywhere else.
    #[test]
    fn the_ss1_kernel_normalizes_to_the_identity() {
        for taps in build_taps(16, 16, 1) {
            let (best, &weight) = taps
                .weights
                .iter()
                .enumerate()
                .max_by(|a, b| a.1.abs().total_cmp(&b.1.abs()))
                .unwrap();
            assert_eq!(weight, 1.0, "center tap is not exactly one");
            let residual: f64 = taps
                .weights
                .iter()
                .enumerate()
                .filter(|(index, _)| *index != best)
                .map(|(_, w)| w.abs())
                .sum();
            assert!(
                residual < f64::EPSILON / 2.0,
                "residual {residual} is visible"
            );
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
