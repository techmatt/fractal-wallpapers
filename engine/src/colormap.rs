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

use serde::{Deserialize, Serialize};

/// Entries in the baked table. Fine enough that the interpolation between
/// neighbouring entries is well below one step of 8-bit output.
pub const TABLE_SIZE: usize = 4096;

/// Whether a map's two ends meet.
///
/// A single pass through the gradient never reaches the seam, so for most
/// renders this is only provenance. It becomes load-bearing the moment coloring
/// repeats the gradient across a field: a sequential map's ends slam together
/// and the seam becomes the most visible edge in the image. [`Bake::mirror`] is
/// the fix, and it is refused on a cyclic map — which has no seam to fix.
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

/// Which way a colormap is baked, and whether it is folded first.
///
/// Both belong to the *bake* rather than to a lookup: they change the table, not
/// the index into it, so a render that uses either pays for them once.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, default)]
pub struct Bake {
    /// Read the gradient from its far end back to its near one.
    pub reverse: bool,
    /// Fold the map into an out-and-back before baking it.
    ///
    /// A sequential map repeated across a field slams its last color against its
    /// first at every wrap, and that seam is the most visible edge in the
    /// picture. Folding removes it — at the cost of halving how much of the
    /// gradient one pass shows, which is a real change to the image and so is
    /// never applied on a map's behalf. A cyclic map already meets itself and
    /// must not be folded: it would halve the cycle the map was drawn to have.
    pub mirror: bool,
}

impl Colormap {
    /// Load `<directory>/<name>.json`, baked as written.
    pub fn load(directory: &Path, name: &str) -> Result<Colormap, String> {
        Colormap::load_baked(directory, name, Bake::default())
    }

    /// Load `<directory>/<name>.json` and bake it the way `bake` asks.
    pub fn load_baked(directory: &Path, name: &str, bake: Bake) -> Result<Colormap, String> {
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
        Colormap::from_stops_baked(file.name, file.kind, &file.stops, bake)
    }

    /// Bake a colormap from sRGB8 control points, as written.
    pub fn from_stops(
        name: impl Into<String>,
        kind: Kind,
        stops: &[(f64, [u8; 3])],
    ) -> Result<Colormap, String> {
        Colormap::from_stops_baked(name, kind, stops, Bake::default())
    }

    /// Bake a colormap from sRGB8 control points, folding and flipping first.
    pub fn from_stops_baked(
        name: impl Into<String>,
        kind: Kind,
        stops: &[(f64, [u8; 3])],
        bake: Bake,
    ) -> Result<Colormap, String> {
        let name = name.into();
        if stops.len() < 2 {
            return Err(format!("colormap '{name}' needs at least two stops"));
        }
        if bake.mirror && kind == Kind::Cyclic {
            return Err(format!(
                "colormap '{name}' is cyclic, so folding it would halve the cycle it was drawn \
                 to have. Folding is the seam fix for a sequential map, which has a seam."
            ));
        }

        let folded;
        let stops: &[(f64, [u8; 3])] = if bake.mirror {
            folded = mirror(stops);
            &folded
        } else {
            stops
        };

        let mut stops: Vec<(f64, [f64; 3])> = stops
            .iter()
            .map(|&(position, rgb)| (position, srgb8_to_oklab(rgb)))
            .collect();
        stops.sort_by(|a, b| a.0.total_cmp(&b.0));

        let table = (0..TABLE_SIZE)
            .map(|i| {
                let i = if bake.reverse { TABLE_SIZE - 1 - i } else { i };
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

/// Fold a stop list into a symmetric out-and-back.
///
/// The map runs forward across the first half and back across the second, so
/// whatever color it opened with is also what it closes with and a repeat has no
/// seam. `n` stops become `2n − 1`: the two ends are each shared between the
/// halves rather than duplicated, and the opening color is written again at
/// `1.0` — that closing segment is the fold, and leaving it to be inferred would
/// hold the second-to-last color flat across the end instead.
fn mirror(stops: &[(f64, [u8; 3])]) -> Vec<(f64, [u8; 3])> {
    let mut sorted = stops.to_vec();
    sorted.sort_by(|a, b| a.0.total_cmp(&b.0));
    let span = sorted[sorted.len() - 1].0 - sorted[0].0;
    if span <= 0.0 || !span.is_finite() {
        return sorted;
    }
    let low = sorted[0].0;
    let at = |index: usize| 0.5 * (sorted[index].0 - low) / span;
    let mut out: Vec<(f64, [u8; 3])> = (0..sorted.len())
        .map(|index| (at(index), sorted[index].1))
        .collect();
    out.extend(
        (1..sorted.len() - 1)
            .rev()
            .map(|index| (1.0 - at(index), sorted[index].1)),
    );
    out.push((1.0, sorted[0].1));
    out
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

    #[test]
    fn reversing_reads_the_same_gradient_from_the_other_end() {
        let forward = ramp();
        let backward = Colormap::from_stops_baked(
            "ramp",
            Kind::Sequential,
            &[
                (0.0, [10, 20, 200]),
                (0.5, [240, 250, 250]),
                (1.0, [255, 160, 0]),
            ],
            Bake {
                reverse: true,
                mirror: false,
            },
        )
        .unwrap();
        for step in 0..=10 {
            let t = step as f64 / 10.0;
            let there = forward.lookup(t);
            let back = backward.lookup(1.0 - t);
            for channel in 0..3 {
                assert!(
                    (there[channel] - back[channel]).abs() < 1e-12,
                    "reversed lookup at {t} differs on channel {channel}"
                );
            }
        }
    }

    /// The point of folding: whatever the map opened with is also what it closes
    /// with, so repeating it has no seam. The far end of the original lands in
    /// the middle instead.
    #[test]
    fn folding_turns_a_run_into_an_out_and_back() {
        let folded = Colormap::from_stops_baked(
            "ramp",
            Kind::Sequential,
            &[
                (0.0, [10, 20, 200]),
                (0.5, [240, 250, 250]),
                (1.0, [255, 160, 0]),
            ],
            Bake {
                reverse: false,
                mirror: true,
            },
        )
        .unwrap();
        let opening = folded.lookup(0.0);
        let closing = folded.lookup(1.0);
        for channel in 0..3 {
            assert!(
                (opening[channel] - closing[channel]).abs() < 0.02,
                "a folded map does not close on the color it opened with"
            );
        }
        // The original far end lands at the fold. Compared loosely on purpose:
        // the fold is a kink in the gradient and the baked table straddles it,
        // so the entry at exactly 0.5 is an average across the turn.
        let middle = folded.lookup(0.5);
        let far_end = ramp().lookup(1.0);
        for channel in 0..3 {
            assert!(
                (middle[channel] - far_end[channel]).abs() < 0.01,
                "the original far end should sit at the fold"
            );
        }
    }

    /// Folding a cyclic map would halve the cycle it was drawn to have, so it is
    /// refused rather than silently done.
    #[test]
    fn a_cyclic_map_is_not_folded() {
        let refusal = Colormap::from_stops_baked(
            "loop",
            Kind::Cyclic,
            &[(0.0, [0, 0, 0]), (0.5, [255, 255, 255]), (1.0, [0, 0, 0])],
            Bake {
                reverse: false,
                mirror: true,
            },
        )
        .err()
        .expect("folding a cyclic map is refused");
        assert!(refusal.contains("cyclic"), "got: {refusal}");
    }
}
