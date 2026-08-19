//! The structural gates: what a view has to be before anything looks at it.
//!
//! A walk proposes far more views than it can afford to keep, and the great
//! majority of them are junk for reasons that need no judgement at all — the
//! frame is mostly the set's interior, or it is a flat wash that escapes in
//! three iterations, or it is empty space with nothing in it to look at. These
//! are *structural* facts about the field, and they are decided here, before any
//! scorer is consulted and without any scorer existing.
//!
//! Three gates, in the order they cost money:
//!
//! ```text
//! interior cap   interior_fraction < cap        one cheap 128-wide field
//! accept band    spread and escape median       the node field
//! occupancy      detail spread over the frame   the node field, shaded
//! ```
//!
//! The interior cap runs first because it is the cheapest and kills the most:
//! interior fraction is scale-robust, so a 128-pixel probe answers it as well as
//! a full render would. The band and the occupancy floor read the node-sized
//! field the walk needs anyway.
//!
//! **The cap is a guarantee the rest of the pipeline is built on.** At the
//! sourcing default a view whose interior fraction reaches 0.30 is junk without
//! exception — not usually, not on average — so everything downstream may assume
//! no such view is in the corpus. That is why the number lives here as a
//! documented constant rather than as a tuning knob with a plausible range.

use serde::{Deserialize, Serialize};

use crate::colormap::srgb8_to_oklab;

/// Interior share at or above which a view is refused at sourcing.
///
/// Interior counts everything the orbit never escaped from — the set itself and
/// anything the iteration cap could not separate from it. Measured over the
/// source project's walks, a candidate above this is junk with no exceptions
/// worth the render, so the cap is exact rather than approximate: moving it is a
/// change to what the corpus is guaranteed to exclude.
///
/// **The value is calibrated on the source project's walks, and the label side
/// now disagrees with it.** Measured against 306 human verdicts, the cliff is at
/// **0.10**, not 0.30: every row at interior ≥ 0.10 was scored 1, without
/// exception, and the highest-interior keeper sits at 0.096. The sheet screen
/// that reads the same quantity was set to **0.12** on that evidence — zero
/// measured cost, with headroom above the highest observed keeper.
///
/// So 0.30 is not wrong, it is *loose*: it still excludes only junk, which is
/// all it ever promised, but it excludes almost none of the junk it could. At
/// this value the rule fires on 1 row in 306.
///
/// The value here is **deliberately unchanged**. Tightening it is a run-design
/// decision — it changes what a walk spends its time on and what reaches the
/// corpus at all — and it belongs to whoever makes that decision, not to the
/// measurement that motivates it.
pub const INTERIOR_CAP: f64 = 0.30;

/// Middle-90% spread of the escape times, below which a frame is flat.
pub const SPREAD_MIN: f64 = 20.0;

/// Median escape time, below which the whole frame is far exterior.
pub const ESCAPE_MEDIAN_MIN: f64 = 3.0;

/// Share of tiles carrying detail, below which a frame is empty.
///
/// Calibrated on the source project's labeling crops rather than on navigation
/// frames, which is a real caveat and the reason this one is a knob where
/// [`INTERIOR_CAP`] is not.
pub const OCCUPANCY_FLOOR: f64 = 0.321;

/// Tile grid the occupancy is measured on: 32 across, 18 down — the frame's own
/// 16:9, so a tile is square and a horizontal streak counts like a vertical one.
pub const OCCUPANCY_TILES: (usize, usize) = (32, 18);

/// Per-tile mean edge energy above which a tile counts as occupied. OKLab ΔE per
/// pixel, so the threshold is in perceptual units and does not move with the
/// palette.
pub const DETAIL_FLOOR: f64 = 0.010;

/// What one pass over a frame says about how its orbits escaped.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
pub struct Escape {
    /// Share of samples whose orbit never escaped.
    pub interior_fraction: f64,
    /// Number of samples that did escape.
    pub escaped: usize,
    /// Median escape time over the escaped samples.
    pub median: f64,
    /// The 5th and 95th percentiles, and the span between them.
    pub p5: f64,
    pub p95: f64,
    pub spread: f64,
}

impl Escape {
    /// Read the statistics off a smooth-escape field, where `NaN` marks interior.
    ///
    /// The percentiles are taken over the escaped samples only. Including the
    /// interior would make the spread a function of how much of the frame is
    /// black, which the interior cap already measures and measures better.
    pub fn of(field: &[f32]) -> Escape {
        let mut escaped: Vec<f64> = field
            .iter()
            .filter(|value| value.is_finite())
            .map(|&value| value as f64)
            .collect();
        let total = field.len().max(1);
        let interior_fraction = (field.len() - escaped.len()) as f64 / total as f64;
        escaped.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

        let count = escaped.len();
        let quantile = |t: f64| -> f64 {
            if count == 0 {
                f64::NAN
            } else {
                escaped[((t * (count - 1) as f64).round() as usize).min(count - 1)]
            }
        };
        let (p5, p95) = (quantile(0.05), quantile(0.95));
        Escape {
            interior_fraction,
            escaped: count,
            median: quantile(0.5),
            p5,
            p95,
            spread: p95 - p5,
        }
    }
}

/// The two-sided band a frame's escape distribution has to sit inside.
///
/// Two clauses, failing in opposite directions: `spread_min` refuses a frame
/// with no variety in it, `escape_median_min` refuses one that is entirely far
/// exterior. There is deliberately no interior clause here — the interior cap
/// owns that question and answers it a render earlier.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Band {
    pub spread_min: f64,
    pub escape_median_min: f64,
}

impl Default for Band {
    fn default() -> Band {
        Band {
            spread_min: SPREAD_MIN,
            escape_median_min: ESCAPE_MEDIAN_MIN,
        }
    }
}

impl Band {
    /// The clause this frame fails, or `None` if it sits inside the band.
    ///
    /// Order matters only for what gets reported: a frame that fails both is
    /// named by the first, so the tally of causes stays readable.
    pub fn refusal(&self, escape: &Escape) -> Option<&'static str> {
        if escape.escaped == 0 || escape.median < self.escape_median_min {
            Some("instant_escape")
        } else if escape.spread < self.spread_min {
            Some("flat")
        } else {
            None
        }
    }
}

/// Per-pixel OKLab gradient magnitude, by forward difference.
///
/// The last row and column have no forward neighbour, so that axis contributes
/// nothing there rather than wrapping around to the far edge.
fn edge_energy(oklab: &[[f64; 3]], width: usize, height: usize) -> Vec<f64> {
    let difference = |a: &[f64; 3], b: &[f64; 3]| -> f64 {
        ((a[0] - b[0]).powi(2) + (a[1] - b[1]).powi(2) + (a[2] - b[2]).powi(2)).sqrt()
    };
    let mut energy = vec![0.0; width * height];
    for row in 0..height {
        for col in 0..width {
            let here = &oklab[row * width + col];
            let across = if col + 1 < width {
                difference(here, &oklab[row * width + col + 1])
            } else {
                0.0
            };
            let down = if row + 1 < height {
                difference(here, &oklab[(row + 1) * width + col])
            } else {
                0.0
            };
            energy[row * width + col] = (across * across + down * down).sqrt();
        }
    }
    energy
}

/// Mean edge energy per tile, row-major over the `tiles` grid.
///
/// A ragged remainder — the rows and columns left over when the image does not
/// divide evenly — is dropped rather than folded into the edge tiles, so every
/// tile covers the same number of pixels and the means are comparable.
pub fn tile_energy(pixels: &[u8], width: usize, height: usize, tiles: (usize, usize)) -> Vec<f64> {
    let (across, down) = tiles;
    if width == 0 || height == 0 || across == 0 || down == 0 {
        return vec![0.0; across * down];
    }
    let oklab: Vec<[f64; 3]> = pixels
        .chunks_exact(3)
        .map(|rgb| srgb8_to_oklab([rgb[0], rgb[1], rgb[2]]))
        .collect();
    if oklab.len() < width * height {
        return vec![0.0; across * down];
    }
    let energy = edge_energy(&oklab, width, height);

    let (tile_width, tile_height) = (width / across, height / down);
    if tile_width == 0 || tile_height == 0 {
        return vec![0.0; across * down];
    }
    let mut means = vec![0.0; across * down];
    for ty in 0..down {
        for tx in 0..across {
            let mut sum = 0.0;
            for row in 0..tile_height {
                let start = (ty * tile_height + row) * width + tx * tile_width;
                for col in 0..tile_width {
                    sum += energy[start + col];
                }
            }
            means[ty * across + tx] = sum / (tile_width * tile_height) as f64;
        }
    }
    means
}

/// Share of tiles carrying detail — the frame's occupancy.
///
/// Deliberately a *count* of occupied tiles rather than a mean energy: a single
/// bright filament across an otherwise empty frame has a respectable mean and an
/// occupancy near zero, and it is the second number that says the frame has
/// nothing to look at.
pub fn occupancy(pixels: &[u8], width: usize, height: usize) -> f64 {
    let (across, down) = OCCUPANCY_TILES;
    let tiles = tile_energy(pixels, width, height, OCCUPANCY_TILES);
    if tiles.is_empty() {
        return 0.0;
    }
    let occupied = tiles.iter().filter(|&&mean| mean > DETAIL_FLOOR).count();
    occupied as f64 / (across * down) as f64
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ramp(count: usize) -> Vec<f32> {
        (0..count).map(|i| i as f32).collect()
    }

    #[test]
    fn interior_samples_are_the_ones_with_no_value() {
        let field = [1.0, f32::NAN, 3.0, f32::NAN];
        let escape = Escape::of(&field);
        assert_eq!(escape.interior_fraction, 0.5);
        assert_eq!(escape.escaped, 2);
    }

    #[test]
    fn the_spread_is_the_middle_ninety_percent() {
        let escape = Escape::of(&ramp(101));
        assert_eq!(escape.p5, 5.0);
        assert_eq!(escape.p95, 95.0);
        assert_eq!(escape.spread, 90.0);
        assert_eq!(escape.median, 50.0);
    }

    /// An all-interior frame has no escape distribution at all, and the band has
    /// to say so rather than compare against `NaN` — where every comparison is
    /// false and the frame would sail through.
    #[test]
    fn a_frame_with_nothing_escaping_is_refused_rather_than_compared_against_nan() {
        let escape = Escape::of(&[f32::NAN, f32::NAN]);
        assert_eq!(escape.escaped, 0);
        assert!(escape.median.is_nan());
        assert_eq!(Band::default().refusal(&escape), Some("instant_escape"));
    }

    #[test]
    fn the_band_names_the_clause_that_failed() {
        let band = Band::default();
        let flat = Escape {
            interior_fraction: 0.0,
            escaped: 100,
            median: 50.0,
            p5: 49.0,
            p95: 51.0,
            spread: 2.0,
        };
        assert_eq!(band.refusal(&flat), Some("flat"));
        let far = Escape {
            median: 1.0,
            ..flat
        };
        assert_eq!(band.refusal(&far), Some("instant_escape"));
        let good = Escape {
            spread: 60.0,
            ..flat
        };
        assert_eq!(band.refusal(&good), None);
    }

    #[test]
    fn a_flat_image_has_no_occupancy_and_a_noisy_one_has_all_of_it() {
        let (width, height) = (64, 36);
        let flat = vec![40u8; width * height * 3];
        assert_eq!(occupancy(&flat, width, height), 0.0);

        let mut checker = vec![0u8; width * height * 3];
        for row in 0..height {
            for col in 0..width {
                let value = if (row + col) % 2 == 0 { 0 } else { 255 };
                let at = (row * width + col) * 3;
                checker[at] = value;
                checker[at + 1] = value;
                checker[at + 2] = value;
            }
        }
        assert_eq!(occupancy(&checker, width, height), 1.0);
    }

    /// Occupancy counts tiles, so detail concentrated in one corner must read
    /// low however strong it is. That is the whole reason the gate is a tile
    /// count rather than a mean.
    #[test]
    fn detail_in_one_corner_reads_as_low_occupancy() {
        let (width, height) = (64, 36);
        let mut pixels = vec![0u8; width * height * 3];
        for row in 0..height / 6 {
            for col in 0..width / 8 {
                if (row + col) % 2 == 0 {
                    let at = (row * width + col) * 3;
                    pixels[at] = 255;
                    pixels[at + 1] = 255;
                    pixels[at + 2] = 255;
                }
            }
        }
        let share = occupancy(&pixels, width, height);
        assert!(share > 0.0 && share < 0.1, "{share}");
    }
}
