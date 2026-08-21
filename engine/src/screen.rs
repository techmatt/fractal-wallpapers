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

use std::path::PathBuf;
use std::time::Instant;

use num_complex::Complex;
use serde::{Deserialize, Serialize};

use crate::coloring::{self, Transform};
use crate::colormap::{Colormap, srgb8_to_oklab};
use crate::family::Family;
use crate::field::{self, FieldSpec};
use crate::maxiter;
use crate::resample;
use crate::spec::{Degree, FamilySpec, decimal, default_colormap_dir, to_decimal_string};
use crate::viewport::Viewport;

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

// --------------------------------------------------------------------------- #
// The frame the gates read, and the battery run on it.
// --------------------------------------------------------------------------- #

/// Width of the cheap first-stage probe, in pixels.
///
/// Interior fraction is scale-robust — a frame that is 40% set at 128 pixels is
/// 40% set at 4000 — so the gate that rejects the most candidates can be
/// answered on a thumbnail. Everything past this stage costs about ten times as
/// much per candidate, which is the entire argument for the stage existing.
pub const PROBE_WIDTH: u32 = 128;

/// The field sampling every frame the gates read is drawn at.
///
/// One sample per output pixel, everywhere: the parent field, the probe and the
/// gate render alike. A walk draws tens of thousands of these and none of them is
/// a picture anybody keeps, so supersampling them would be paying deploy quality
/// for steering material. It is a constant rather than a setting because the gate
/// render is scored through a head trained at exactly this sampling.
pub const NODE_SUPERSAMPLE: u32 = 1;

/// Default width of the node field the policy and the later gates read.
///
/// Wide enough that the focus finder's scales are a sensible fraction of the
/// frame, narrow enough to render a few thousand times an hour.
pub const NODE_WIDTH: u32 = 384;

/// The height that goes with a node field of `width`, at the frame's own 16:9.
pub fn node_height(width: u32) -> u32 {
    ((width as f64 * 9.0 / 16.0).round() as u32).max(1)
}

/// A frame rendered once, kept in all three of the forms the gates want.
pub struct Framed {
    pub field: Vec<f32>,
    pub pixels: Vec<u8>,
    pub escape: Escape,
}

/// Render one frame and reduce it, once, for everything downstream.
pub fn render_frame(view: &Viewport, family: &Family, cap: u32, colormap: &Colormap) -> Framed {
    let sampled = field::render_field(view, family, cap, FieldSpec::Smooth);
    let field = sampled.fields[0].values.clone();
    let linear = coloring::colorize(&sampled.fields[0], Transform::Linear, colormap);
    let pixels = resample::downsample(
        &linear,
        view.sample_width() as usize,
        view.sample_height() as usize,
        view.out_width as usize,
        view.out_height as usize,
        view.supersample,
    );
    let escape = Escape::of(&field);
    Framed {
        field,
        pixels,
        escape,
    }
}

/// The three thresholds a frame is screened against.
///
/// The gate *values*, and only those. A walk's [`crate::expand::Gates`] carries
/// two more — whether the occupancy floor acts at the first rung, and the width
/// below which a rung is not taken — because both are facts about *descending*,
/// and a frame somebody named has no rung and takes no step. Both default to the
/// constants at the top of this module, and
/// `the_two_gate_settings_agree_on_every_shared_value` is what keeps the two
/// from drifting apart.
#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Battery {
    /// Interior share at or above which a frame is refused.
    pub interior_cap: f64,
    /// Share of tiles that must carry detail.
    pub occupancy_floor: f64,
    pub band: Band,
}

impl Default for Battery {
    fn default() -> Battery {
        Battery {
            interior_cap: INTERIOR_CAP,
            occupancy_floor: OCCUPANCY_FLOOR,
            band: Band::default(),
        }
    }
}

/// One gate's reading, the threshold it was read against, and which way it went.
///
/// Every gate the battery *reached* reports one of these, passed or failed, and
/// the ones it never reached report none: a frame the interior cap refused was
/// never measured for occupancy, and a verdict for a gate that did not run would
/// be an invention. Which is also why a screening names a fate rather than
/// leaving a reader to and-together the list.
#[derive(Clone, Copy, Debug, Serialize)]
pub struct Verdict {
    /// The gate, under the name a refusal is recorded by.
    pub gate: &'static str,
    /// What was measured on this frame.
    pub reading: f64,
    /// What it had to clear.
    pub threshold: f64,
    pub passed: bool,
}

/// The fate of a frame no gate refused.
pub const SURVIVED: &str = "survived";

/// What the battery made of one frame.
pub struct Screening {
    /// The interior fraction of the 128-pixel probe — the first thing measured.
    pub probe_interior_fraction: f64,
    /// The node render, absent for a frame the probe's cap refused: that frame
    /// never had one, so the numbers that come off one do not exist for it.
    pub framed: Option<Framed>,
    pub occupancy: Option<f64>,
    pub verdicts: Vec<Verdict>,
    /// `"survived"`, or the gate that refused this frame.
    pub fate: &'static str,
}

impl Screening {
    pub fn passed(&self) -> bool {
        self.fate == SURVIVED
    }

    /// The interior fraction a record carries: the node render's where there is
    /// one, and the probe's where the cap refused before there was.
    pub fn interior_fraction(&self) -> f64 {
        match &self.framed {
            Some(framed) => framed.escape.interior_fraction,
            None => self.probe_interior_fraction,
        }
    }
}

impl Battery {
    /// Put one frame through every gate, in the order they cost money.
    ///
    /// ```text
    /// interior cap   on a 128-pixel probe          the cheapest, and the deadliest
    /// interior cap   again, on the node render     the cap is a guarantee, not a filter
    /// accept band    spread and escape median      the node field
    /// occupancy      detail spread over the frame  the node field, shaded
    /// ```
    ///
    /// The cap runs **twice** on purpose. Interior fraction is scale-robust but
    /// not scale-*identical*, so a frame that read 0.299 on the probe can read
    /// 0.301 on the frame the record keeps — and the cap is a guarantee the rest
    /// of the pipeline is built on rather than a filter that is usually right.
    /// The second reading costs nothing, because the number is already in hand.
    ///
    /// `measure_occupancy` is how a caller waives the last gate. A walk waives it
    /// at the first rung, where it over-fires; an `occupancy_floor` of zero
    /// waives it everywhere. Either way that gate reports no verdict, because it
    /// did not run.
    pub fn screen(
        &self,
        view: &Viewport,
        family: &Family,
        cap: u32,
        colormap: &Colormap,
        measure_occupancy: bool,
    ) -> Screening {
        let mut verdicts = Vec::with_capacity(4);
        let capped = self.interior_cap > 0.0;

        // Stage 1 — the cheap interior cap.
        let probe = Viewport {
            center: view.center,
            width: view.width,
            out_width: PROBE_WIDTH,
            out_height: ((PROBE_WIDTH as f64 * view.out_height as f64 / view.out_width as f64)
                .round() as u32)
                .max(1),
            supersample: NODE_SUPERSAMPLE,
        };
        let probed = field::render_field(&probe, family, cap, FieldSpec::Smooth);
        let probe_interior = Escape::of(&probed.fields[0].values).interior_fraction;
        if capped {
            verdicts.push(Verdict {
                gate: "interior_cap",
                reading: probe_interior,
                threshold: self.interior_cap,
                passed: probe_interior < self.interior_cap,
            });
            if probe_interior >= self.interior_cap {
                return Screening {
                    probe_interior_fraction: probe_interior,
                    framed: None,
                    occupancy: None,
                    verdicts,
                    fate: "interior_cap",
                };
            }
        }

        // Stage 2 — the node render, and the three gates that read it.
        let framed = render_frame(view, family, cap, colormap);
        let escape = framed.escape;
        let refused = |fate: &'static str,
                       verdicts: Vec<Verdict>,
                       occupancy: Option<f64>,
                       framed: Framed| Screening {
            probe_interior_fraction: probe_interior,
            framed: Some(framed),
            occupancy,
            verdicts,
            fate,
        };
        if capped {
            verdicts.push(Verdict {
                gate: "interior_cap",
                reading: escape.interior_fraction,
                threshold: self.interior_cap,
                passed: escape.interior_fraction < self.interior_cap,
            });
            if escape.interior_fraction >= self.interior_cap {
                return refused("interior_cap", verdicts, None, framed);
            }
        }

        let clause = self.band.refusal(&escape);
        verdicts.push(Verdict {
            gate: "instant_escape",
            reading: escape.median,
            threshold: self.band.escape_median_min,
            passed: clause != Some("instant_escape"),
        });
        if clause != Some("instant_escape") {
            verdicts.push(Verdict {
                gate: "flat",
                reading: escape.spread,
                threshold: self.band.spread_min,
                passed: clause != Some("flat"),
            });
        }
        if let Some(clause) = clause {
            return refused(clause, verdicts, None, framed);
        }

        let measured = measure_occupancy && self.occupancy_floor > 0.0;
        let share = measured.then(|| {
            occupancy(
                &framed.pixels,
                view.out_width as usize,
                view.out_height as usize,
            )
        });
        if let Some(value) = share {
            verdicts.push(Verdict {
                gate: "occupancy_floor",
                reading: value,
                threshold: self.occupancy_floor,
                passed: value >= self.occupancy_floor,
            });
            if value < self.occupancy_floor {
                return refused("occupancy_floor", verdicts, share, framed);
            }
        }

        Screening {
            probe_interior_fraction: probe_interior,
            framed: Some(framed),
            occupancy: share,
            verdicts,
            fate: SURVIVED,
        }
    }
}

// --------------------------------------------------------------------------- #
// Screening a frame somebody named.
// --------------------------------------------------------------------------- #

/// A batch of named frames to screen.
///
/// Heterogeneous on purpose, unlike an expansion: every frame carries its own
/// family, because there is no shared random stream here for a family to be part
/// of. A manifest of locations is exactly this list, in the order it was written.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ScreenSpec {
    pub schema: u32,
    pub frames: Vec<Frame>,
    #[serde(default)]
    pub battery: Battery,
    pub colormap: String,
    #[serde(default = "default_colormap_dir")]
    pub colormap_dir: PathBuf,
    /// Width of the frame the gates read. The height follows from 16:9.
    #[serde(default = "default_node_width")]
    pub node_width: u32,
    /// Where the screened frames go, as `<out_dir>/frame<index>.jpg`. Omit for
    /// verdicts alone.
    #[serde(default)]
    pub out_dir: Option<PathBuf>,
    /// Whether the occupancy floor acts. On by default.
    ///
    /// Here for one reason: a walk waives this gate at its first rung, where it
    /// over-fires on a root frame still resolving structure the tighter child has
    /// not entered yet. So a first-rung candidate in a ledger passed a battery of
    /// two gates, and screening it against three would report a refusal the run
    /// that recorded it never made. Off, the gate reports no verdict, because it
    /// did not run.
    #[serde(default = "yes")]
    pub occupancy: bool,
}

fn yes() -> bool {
    true
}

fn default_node_width() -> u32 {
    NODE_WIDTH
}

/// One frame to screen: a location, as a record already writes one.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Frame {
    pub family: FamilySpec,
    pub center_re: String,
    pub center_im: String,
    pub width: String,
    /// Iterations per sample. Absent means the depth-aware policy decides, which
    /// is what a walk's own candidate was drawn under.
    #[serde(default)]
    pub maxiter: Option<u32>,
}

/// What the battery made of one named frame.
#[derive(Debug, Serialize)]
pub struct Screened {
    /// Which row of the batch this was. Part of the frame's file name.
    pub index: usize,
    pub family: &'static str,
    pub degree: Degree,
    pub center_re: String,
    pub center_im: String,
    pub width: String,
    pub maxiter: u32,
    pub probe_interior_fraction: f64,
    pub interior_fraction: f64,
    /// Absent for a frame the probe's cap refused: it never had a node render.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub escape: Option<Escape>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub occupancy: Option<f64>,
    /// One entry per gate that ran, in the order they ran.
    pub verdicts: Vec<Verdict>,
    pub fate: &'static str,
    pub passed: bool,
    /// The frame the later gates read, where one was rendered and asked for.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub image: Option<String>,
}

/// What one batch of screenings did.
#[derive(Debug, Serialize)]
pub struct ScreenReport {
    pub schema: u32,
    /// The geometry every frame was screened at, and the field sampling behind
    /// it — the same two names an expansion's report states, for the same
    /// reason: two pictures are comparable only at one geometry.
    pub tile: [u32; 2],
    pub field_supersample: u32,
    pub probe_width: u32,
    pub battery: Battery,
    /// Whether the occupancy floor acted. Stated, because a report that did not
    /// say so would be indistinguishable from one where every frame happened to
    /// clear it.
    pub occupancy: bool,
    pub frames: Vec<Screened>,
    pub seconds: f64,
}

impl ScreenSpec {
    /// Read a screen spec from JSON text.
    pub fn parse(text: &str) -> Result<ScreenSpec, String> {
        let spec: ScreenSpec = serde_json::from_str(text).map_err(|e| format!("spec: {e}"))?;
        if spec.schema != 1 {
            return Err(format!("spec has schema {}, expected 1", spec.schema));
        }
        if spec.frames.is_empty() {
            return Err("frames must name at least one location".into());
        }
        if spec.node_width < 32 {
            return Err(format!(
                "node_width {} is narrower than the grid the occupancy floor is measured on",
                spec.node_width
            ));
        }
        Ok(spec)
    }
}

/// Screen every frame in `spec` and report what each gate said.
///
/// The battery is the one an expansion runs, at the geometry an expansion runs it
/// at. This exists because those gates were reachable only through a walk that
/// *proposes* frames, and a reader who wants to know what the filter makes of a
/// frame they can name had nowhere to ask.
pub fn run(spec: ScreenSpec) -> Result<ScreenReport, String> {
    let started = Instant::now();
    let colormap = Colormap::load(&spec.colormap_dir, &spec.colormap)?;
    let out_width = spec.node_width;
    let out_height = node_height(out_width);

    let mut frames = Vec::with_capacity(spec.frames.len());
    for (index, frame) in spec.frames.into_iter().enumerate() {
        let resolved = frame.family.resolve()?;
        if resolved.family.is_render_only() {
            return Err(crate::spec::render_only_refusal(resolved.kind, "screened"));
        }
        let width = decimal(&frame.width, "width")?;
        if !width.is_finite() || width <= 0.0 {
            return Err(format!("frame {index}: width must be positive"));
        }
        let view = Viewport {
            center: Complex::new(
                decimal(&frame.center_re, "center_re")?,
                decimal(&frame.center_im, "center_im")?,
            ),
            width,
            out_width,
            out_height,
            supersample: NODE_SUPERSAMPLE,
        };
        let cap = frame.maxiter.unwrap_or_else(|| maxiter::for_width(width));

        let screening =
            spec.battery
                .screen(&view, &resolved.family, cap, &colormap, spec.occupancy);

        let image = match (&spec.out_dir, &screening.framed) {
            (Some(directory), Some(framed)) => {
                let name = format!("frame{index}.jpg");
                resample::write_image(
                    &directory.join(&name),
                    &framed.pixels,
                    out_width,
                    out_height,
                )?;
                Some(name)
            }
            _ => None,
        };

        frames.push(Screened {
            index,
            family: resolved.kind,
            degree: resolved.degree,
            center_re: to_decimal_string(view.center.re),
            center_im: to_decimal_string(view.center.im),
            width: to_decimal_string(width),
            maxiter: cap,
            probe_interior_fraction: screening.probe_interior_fraction,
            interior_fraction: screening.interior_fraction(),
            escape: screening.framed.as_ref().map(|framed| framed.escape),
            occupancy: screening.occupancy,
            passed: screening.passed(),
            fate: screening.fate,
            verdicts: screening.verdicts,
            image,
        });
    }

    Ok(ScreenReport {
        schema: 1,
        tile: [out_width, out_height],
        field_supersample: NODE_SUPERSAMPLE,
        probe_width: PROBE_WIDTH,
        battery: spec.battery,
        occupancy: spec.occupancy,
        frames,
        seconds: started.elapsed().as_secs_f64(),
    })
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

    /// The two gate settings both default to the constants at the top of this
    /// module, and this is what says so. `expand::Gates` carries two fields more
    /// — both about *descending* — and if either struct's defaults ever stopped
    /// agreeing on the three shared ones, a walk and the `screen` subcommand
    /// would come to different verdicts about one frame.
    #[test]
    fn the_two_gate_settings_agree_on_every_shared_value() {
        let gates = crate::expand::Gates::default();
        let battery = Battery::default();
        assert_eq!(gates.interior_cap, battery.interior_cap);
        assert_eq!(gates.occupancy_floor, battery.occupancy_floor);
        assert_eq!(gates.band, battery.band);
        assert_eq!(gates.battery().interior_cap, gates.interior_cap);
        assert_eq!(gates.battery().occupancy_floor, gates.occupancy_floor);
        assert_eq!(gates.battery().band, gates.band);
    }

    fn screen_spec(frames: &str, extra: &str) -> String {
        format!(
            r#"{{"schema":1,"frames":[{frames}],
                "colormap":"twilight_shifted","colormap_dir":"../data/palettes"
                {extra}}}"#
        )
    }

    fn frame(family: &str, center: (&str, &str), width: &str) -> String {
        format!(
            r#"{{"family":{family},"center_re":"{}","center_im":"{}","width":"{width}"}}"#,
            center.0, center.1
        )
    }

    const MANDELBROT: &str = r#"{"kind":"mandelbrot"}"#;

    #[test]
    fn a_spec_that_names_no_frame_is_refused() {
        let message = ScreenSpec::parse(&screen_spec("", "")).unwrap_err();
        assert!(message.contains("at least one"), "{message}");
    }

    /// The subcommand exists so a frame somebody *named* can be put through the
    /// filter. Every gate that ran says what it read and what it read it
    /// against, and the fate names the one that decided.
    #[test]
    fn every_gate_that_ran_reports_what_it_read() {
        let text = screen_spec(&frame(MANDELBROT, ("-0.75", "0.1"), "0.4"), "");
        let report = run(ScreenSpec::parse(&text).unwrap()).unwrap();
        assert_eq!(report.frames.len(), 1);
        assert_eq!(report.tile, [NODE_WIDTH, 216]);
        assert_eq!(report.field_supersample, NODE_SUPERSAMPLE);
        assert_eq!(report.probe_width, PROBE_WIDTH);

        let screened = &report.frames[0];
        assert_eq!(screened.family, "mandelbrot");
        assert!(!screened.verdicts.is_empty());
        for verdict in &screened.verdicts {
            assert!(verdict.reading.is_finite() || verdict.gate == "instant_escape");
        }
        // The fate is the first gate that failed, and nothing after it ran.
        match screened.verdicts.iter().find(|verdict| !verdict.passed) {
            Some(failed) => {
                assert_eq!(screened.fate, failed.gate);
                assert!(!screened.passed);
            }
            None => {
                assert_eq!(screened.fate, SURVIVED);
                assert!(screened.passed);
            }
        }
    }

    /// A frame deep inside the set dies at the cap, on the 128-pixel probe — so
    /// it never gets a node render and reports no escape statistics, because it
    /// has none.
    #[test]
    fn a_frame_inside_the_set_dies_at_the_probe_and_reports_nothing_it_never_measured() {
        let text = screen_spec(&frame(MANDELBROT, ("-0.5", "0"), "0.05"), "");
        let report = run(ScreenSpec::parse(&text).unwrap()).unwrap();
        let screened = &report.frames[0];
        assert_eq!(screened.fate, "interior_cap");
        assert!(screened.escape.is_none());
        assert!(screened.occupancy.is_none());
        assert_eq!(screened.verdicts.len(), 1, "no later gate ran");
        assert_eq!(screened.interior_fraction, screened.probe_interior_fraction);
    }

    /// The whole claim of this subcommand is that it is *expand's* filter. A
    /// candidate the walk gated at depth 2 — where the occupancy floor acts —
    /// must get the same fate when it is handed back by name.
    #[test]
    fn a_named_frame_gets_the_same_fate_the_walk_gave_it() {
        let nodes = r#"{"node_id":3,"root_id":1,"center_re":"-0.75","center_im":"0.1",
                        "width":"0.4","depth":2}"#;
        let expansion = crate::expand::run(
            crate::expand::ExpandSpec::parse(&format!(
                r#"{{"schema":1,"family":{MANDELBROT},"seed":11,"nodes":[{nodes}],
                     "out_dir":"{}","colormap":"twilight_shifted",
                     "colormap_dir":"../data/palettes"}}"#,
                std::env::temp_dir()
                    .join("fractal_engine_screen")
                    .display()
                    .to_string()
                    .replace('\\', "/")
            ))
            .unwrap(),
        )
        .unwrap();
        assert!(!expansion.candidates.is_empty());

        let frames: Vec<String> = expansion
            .candidates
            .iter()
            .map(|candidate| {
                format!(
                    r#"{{"family":{MANDELBROT},"center_re":"{}","center_im":"{}",
                         "width":"{}","maxiter":{}}}"#,
                    candidate.center_re, candidate.center_im, candidate.width, candidate.maxiter
                )
            })
            .collect();
        let report = run(ScreenSpec::parse(&screen_spec(&frames.join(","), "")).unwrap()).unwrap();

        for (candidate, screened) in expansion.candidates.iter().zip(report.frames.iter()) {
            assert_eq!(
                candidate.fate, screened.fate,
                "{} {} at width {}",
                candidate.center_re, candidate.center_im, candidate.width
            );
        }
    }
}
