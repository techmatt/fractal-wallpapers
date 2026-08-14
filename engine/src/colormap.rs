//! Colormaps: control points on disk, a lookup table in memory.
//!
//! A colormap is a list of `(position, sRGB8)` stops. Two things happen on load,
//! and both are choices worth naming.
//!
//! **Interpolation is perceptual, not linear.** Stops are converted to OKLab and
//! interpolated there. Interpolating in linear RGB makes a gradient that is
//! mathematically even and visually lumpy: the eye sees bands of near-constant
//! lightness separated by fast transitions, exactly where the colormap was meant
//! to be smooth. Since the field feeding a colormap is itself smooth and evenly
//! spaced, any unevenness the interpolation introduces shows up directly in the
//! picture.
//!
//! **The result is baked to a table.** Every subsample looks up a color, and at
//! 2560×1440 with 4× supersampling that is 59 million lookups. Interpolating in
//! OKLab per lookup would put a pair of cube roots in the innermost loop for a
//! result that only ever takes [`TABLE_SIZE`] distinct values anyway.

use std::path::Path;

use serde::Deserialize;

/// Entries in the baked table. Fine enough that the interpolation between
/// neighbouring entries is well below one step of 8-bit output.
pub const TABLE_SIZE: usize = 4096;

/// Whether a map's two ends meet.
///
/// Nothing in this slice reads it — a single pass through the gradient never
/// reaches the seam. It is recorded because the moment coloring repeats the
/// gradient across a field, a sequential map's ends slam together and the seam
/// becomes the most visible edge in the image.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Kind {
    /// The last color returns to the first: the map can repeat seamlessly.
    Cyclic,
    /// The map runs from one end to the other and does not come back.
    Sequential,
}

/// A colormap file: the tracked text form.
#[derive(Debug, Deserialize)]
struct ColormapFile {
    schema: u32,
    name: String,
    kind: Kind,
    #[allow(dead_code)] // provenance for a reader, not for the renderer
    source: String,
    stops: Vec<(f64, [u8; 3])>,
}

/// A colormap baked to a lookup table of linear-light RGB.
pub struct Colormap {
    name: String,
    kind: Kind,
    table: Vec<[f64; 3]>,
}

impl Colormap {
    /// Load `<directory>/<name>.json`.
    pub fn load(directory: &Path, name: &str) -> Result<Colormap, String> {
        let path = directory.join(format!("{name}.json"));
        let text = std::fs::read_to_string(&path)
            .map_err(|e| format!("read colormap {}: {e}", path.display()))?;
        let file: ColormapFile = serde_json::from_str(&text)
            .map_err(|e| format!("parse colormap {}: {e}", path.display()))?;
        if file.schema != 1 {
            return Err(format!(
                "colormap {} has schema {}, expected 1",
                path.display(),
                file.schema
            ));
        }
        if file.name != name {
            return Err(format!(
                "colormap {} calls itself '{}'",
                path.display(),
                file.name
            ));
        }
        Colormap::from_stops(file.name, file.kind, &file.stops)
    }

    /// Bake a colormap from sRGB8 control points.
    pub fn from_stops(
        name: impl Into<String>,
        kind: Kind,
        stops: &[(f64, [u8; 3])],
    ) -> Result<Colormap, String> {
        let name = name.into();
        if stops.len() < 2 {
            return Err(format!("colormap '{name}' needs at least two stops"));
        }

        let mut stops: Vec<(f64, [f64; 3])> = stops
            .iter()
            .map(|&(position, rgb)| (position, srgb8_to_oklab(rgb)))
            .collect();
        stops.sort_by(|a, b| a.0.total_cmp(&b.0));

        let table = (0..TABLE_SIZE)
            .map(|i| {
                let t = i as f64 / (TABLE_SIZE - 1) as f64;
                oklab_to_linear_srgb(interpolate(&stops, t))
            })
            .collect();

        Ok(Colormap { name, kind, table })
    }

    pub fn name(&self) -> &str {
        &self.name
    }

    pub fn kind(&self) -> Kind {
        self.kind
    }

    /// Look up `t ∈ [0, 1]`, returning linear-light RGB.
    ///
    /// Linear light, not sRGB, because averaging is what happens next: the
    /// supersampled colors get combined by the resample, and averaging sRGB
    /// values darkens edges. `t` is clamped rather than wrapped — the caller
    /// decides what falling off the end means, and in this slice nothing does.
    pub fn lookup(&self, t: f64) -> [f64; 3] {
        let position = t.clamp(0.0, 1.0) * (TABLE_SIZE - 1) as f64;
        let index = position.floor() as usize;
        if index >= TABLE_SIZE - 1 {
            return self.table[TABLE_SIZE - 1];
        }
        let fraction = position - index as f64;
        let (a, b) = (self.table[index], self.table[index + 1]);
        [
            a[0] + (b[0] - a[0]) * fraction,
            a[1] + (b[1] - a[1]) * fraction,
            a[2] + (b[2] - a[2]) * fraction,
        ]
    }
}

/// Interpolate the sorted OKLab stops at `t`, holding the end colors beyond the
/// outermost stops.
fn interpolate(stops: &[(f64, [f64; 3])], t: f64) -> [f64; 3] {
    let last = stops.len() - 1;
    if t <= stops[0].0 {
        return stops[0].1;
    }
    if t >= stops[last].0 {
        return stops[last].1;
    }
    let upper = stops.partition_point(|&(position, _)| position <= t);
    let (lo_pos, lo) = stops[upper - 1];
    let (hi_pos, hi) = stops[upper];
    let span = hi_pos - lo_pos;
    let fraction = if span > 0.0 { (t - lo_pos) / span } else { 0.0 };
    [
        lo[0] + (hi[0] - lo[0]) * fraction,
        lo[1] + (hi[1] - lo[1]) * fraction,
        lo[2] + (hi[2] - lo[2]) * fraction,
    ]
}

// ---------------------------------------------------------------------------
// Color spaces
// ---------------------------------------------------------------------------

/// sRGB transfer function, decoding an encoded component to linear light.
pub fn srgb_to_linear(c: f64) -> f64 {
    if c <= 0.04045 {
        c / 12.92
    } else {
        ((c + 0.055) / 1.055).powf(2.4)
    }
}

/// sRGB transfer function, encoding linear light for output.
pub fn linear_to_srgb(c: f64) -> f64 {
    let c = c.clamp(0.0, 1.0);
    if c <= 0.0031308 {
        c * 12.92
    } else {
        1.055 * c.powf(1.0 / 2.4) - 0.055
    }
}

/// Linear sRGB → OKLab (Ottosson's matrices).
pub fn linear_srgb_to_oklab(rgb: [f64; 3]) -> [f64; 3] {
    let [r, g, b] = rgb;
    let l = 0.412_221_470_8 * r + 0.536_332_536_3 * g + 0.051_445_992_9 * b;
    let m = 0.211_903_498_2 * r + 0.680_699_545_1 * g + 0.107_396_956_6 * b;
    let s = 0.088_302_461_9 * r + 0.281_718_837_6 * g + 0.629_978_700_5 * b;
    let (l, m, s) = (l.cbrt(), m.cbrt(), s.cbrt());
    [
        0.210_454_255_3 * l + 0.793_617_785_0 * m - 0.004_072_046_8 * s,
        1.977_998_495_1 * l - 2.428_592_205_0 * m + 0.450_593_709_9 * s,
        0.025_904_037_1 * l + 0.782_771_766_2 * m - 0.808_675_766_0 * s,
    ]
}

/// OKLab → linear sRGB.
pub fn oklab_to_linear_srgb(lab: [f64; 3]) -> [f64; 3] {
    let [lightness, a, b] = lab;
    let l = lightness + 0.396_337_777_4 * a + 0.215_803_757_3 * b;
    let m = lightness - 0.105_561_345_8 * a - 0.063_854_172_8 * b;
    let s = lightness - 0.089_484_177_5 * a - 1.291_485_548_0 * b;
    let (l, m, s) = (l * l * l, m * m * m, s * s * s);
    [
        4.076_741_662_1 * l - 3.307_711_591_3 * m + 0.230_969_929_2 * s,
        -1.268_438_004_6 * l + 2.609_757_401_1 * m - 0.341_319_396_5 * s,
        -0.004_196_086_3 * l - 0.703_418_614_7 * m + 1.707_614_701_0 * s,
    ]
}

/// sRGB8 → OKLab.
pub fn srgb8_to_oklab(rgb: [u8; 3]) -> [f64; 3] {
    linear_srgb_to_oklab([
        srgb_to_linear(rgb[0] as f64 / 255.0),
        srgb_to_linear(rgb[1] as f64 / 255.0),
        srgb_to_linear(rgb[2] as f64 / 255.0),
    ])
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ramp() -> Colormap {
        Colormap::from_stops(
            "ramp",
            Kind::Sequential,
            &[
                (0.0, [10, 20, 200]),
                (0.5, [240, 250, 250]),
                (1.0, [255, 160, 0]),
            ],
        )
        .unwrap()
    }

    #[test]
    fn oklab_round_trips_through_the_srgb_cube() {
        let mut worst = 0.0f64;
        for &r in &[0u8, 17, 64, 128, 200, 255] {
            for &g in &[0u8, 17, 64, 128, 200, 255] {
                for &b in &[0u8, 17, 64, 128, 200, 255] {
                    let linear = [
                        srgb_to_linear(r as f64 / 255.0),
                        srgb_to_linear(g as f64 / 255.0),
                        srgb_to_linear(b as f64 / 255.0),
                    ];
                    let back = oklab_to_linear_srgb(linear_srgb_to_oklab(linear));
                    for channel in 0..3 {
                        worst = worst.max(
                            (linear_to_srgb(linear[channel]) - linear_to_srgb(back[channel])).abs(),
                        );
                    }
                }
            }
        }
        // Half a step of 8-bit output is ~0.002; stay far under it.
        assert!(worst < 1e-4, "round-trip error {worst:e}");
    }

    #[test]
    fn the_table_passes_through_its_stops() {
        let map = ramp();
        for &(position, rgb) in &[
            (0.0, [10u8, 20, 200]),
            (0.5, [240, 250, 250]),
            (1.0, [255, 160, 0]),
        ] {
            let got = map.lookup(position);
            for channel in 0..3 {
                let want = srgb_to_linear(rgb[channel] as f64 / 255.0);
                assert!(
                    (got[channel] - want).abs() < 5e-3,
                    "stop {position}: got {got:?}"
                );
            }
        }
    }

    #[test]
    fn lookups_are_clamped_not_wrapped() {
        let map = ramp();
        assert_eq!(map.lookup(-1.0), map.lookup(0.0));
        assert_eq!(map.lookup(2.0), map.lookup(1.0));
    }

    /// A perceptual interpolation should march through lightness at a roughly
    /// even pace. Measure the OKLab lightness step between table entries and
    /// require the largest to stay within a small multiple of the mean — the
    /// property linear-RGB interpolation fails.
    #[test]
    fn the_gradient_is_perceptually_even() {
        let map = ramp();
        let steps: Vec<f64> = map
            .table
            .windows(2)
            .map(|pair| {
                let a = linear_srgb_to_oklab(pair[0]);
                let b = linear_srgb_to_oklab(pair[1]);
                (b[0] - a[0]).abs()
            })
            .collect();
        let mean = steps.iter().sum::<f64>() / steps.len() as f64;
        let largest = steps.iter().fold(0.0f64, |acc, &s| acc.max(s));
        assert!(
            largest < mean * 4.0,
            "largest step {largest} vs mean {mean}"
        );
    }

    #[test]
    fn the_tracked_colormaps_load() {
        let directory = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("data")
            .join("palettes");
        for name in ["twilight_shifted", "blue_orange"] {
            let map =
                Colormap::load(&directory, name).unwrap_or_else(|e| panic!("loading {name}: {e}"));
            assert_eq!(map.name(), name);
            for &t in &[0.0, 0.25, 0.5, 0.75, 1.0] {
                for channel in map.lookup(t) {
                    assert!(channel.is_finite(), "{name} at {t} is not finite");
                }
            }
        }
        assert_eq!(
            Colormap::load(&directory, "twilight_shifted")
                .unwrap()
                .kind(),
            Kind::Cyclic
        );
    }
}
