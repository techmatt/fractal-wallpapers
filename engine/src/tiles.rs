//! Training tiles: one iteration pass per location, every tile a crop of it.
//!
//! A judge of locations is trained on pictures, and one picture per location is
//! not enough — the head would learn the palette and the framing along with the
//! place. So each location becomes a small batch of **tiles**, each drawing its
//! own colormap, its own framing, its own antialiasing and its own JPEG quality,
//! and the head sees the location under all of them.
//!
//! The naive way to make those tiles is to render each one. That is what makes
//! this module worth having: a tile differs from its neighbours in *coloring* and
//! in *framing*, and neither of those requires iterating the recurrence again. So
//! one location is one iteration pass over a slightly **extended field** — wider
//! than the canonical frame by the most any tile can be shifted or zoomed out —
//! and every tile is a crop of that field, resampled and colored. At the shipped
//! recipe that is 1.5 million subpixels per location instead of thirty-two frames
//! of nine hundred thousand: a **thirty-fold** cut, and the reason a corpus-wide
//! rebuild is an afternoon rather than a week.
//!
//! ```text
//! location ─▶ extended field (one pass) ─▶ crop ─▶ stretch ─▶ colormap ─▶ resample ─▶ JPEG
//!                                          ×32, each its own draw
//! ```
//!
//! Four decisions hold the module up.
//!
//! **The margin is an equal plane distance on all four sides.** A tile's shift is
//! one magnitude in canonical-frame-*width* units pointed in a uniform direction,
//! so at 16:9 a vertical displacement of 5% of the width is 8.9% of the height.
//! Padding each axis by a fraction of its own extent under-pads the vertical and
//! lets the tallest shifted crop run off the bottom. The containment bound that
//! follows is checked, never clamped:
//!
//! ```text
//! extend  ≥  1 + 2·shift_max + max(1, H/W)·(scale_hi − 1)
//! ```
//!
//! At the shipped 640×360, `[0.90, 1.10]` and 5% that is `1 + 0.10 + 0.10 = 1.20`
//! **exactly** — the extension, the scale band and the shift cap are one decision
//! with nothing to spare, and moving any of the three moves the other two.
//!
//! **The field's supersampling is one number for the whole build, and the two
//! antialiasing levels are a *mode* rather than a factor.** With one field there
//! is no per-tile supersample left to name. The canonical build sets it to 2; a
//! build that sets it to anything else, or renders a tile at another size, is a
//! different **regime** and says so in every file name it writes — see
//! [`regime_tag`], without which two regimes would share one cache and the
//! second would skip-as-present over the first one's pictures.
//! The filtered arm is exact in kind — Lanczos-3 in
//! linear light, the same kernel a whole-frame render uses, at a ratio the random
//! scale makes non-integer. The point-sampled arm cannot be exact: an even
//! supersampled grid holds no sample at a pixel centre, so the honest stand-in
//! for an unfiltered render is the nearest subpixel, displaced by at most half of
//! one. Running a box filter instead would average about `ratio` subpixels and
//! produce a *second filtered tile*, destroying the axis the level exists to be.
//!
//! **Each crop is normalized against its own samples.** The stretch is the one
//! genuinely frame-global step in the coloring, so it is measured per tile over
//! the window that tile covers — the population a whole-frame render of that
//! crop would have seen.
//!
//! **The iteration cap is the canonical frame's, per location.** The extended
//! field never re-derives a cap from its own wider width: one field serves every
//! crop, so a per-crop cap is not expressible, and a cap that drifted with the
//! extension would make the tiles of one location incomparable with each other.
//!
//! Every draw comes from `(seed_tag, location, slot)` with a disjoint slot
//! namespace per axis, so adding an axis never reshuffles the others and a tile
//! is a pure function of its location row plus this module. Fields are rendered
//! into a local buffer, cropped, and dropped; nothing is cached.

use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::Instant;

use num_complex::Complex;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};

use crate::coloring::{INTERIOR, Stretch, Transform};
use crate::colormap::Colormap;
use crate::family::Family;
use crate::field::{self, FieldSpec};
use crate::resample;
use crate::rng::{self, Rng};
use crate::spec::{FamilySpec, Location, Pair, decimal, default_colormap_dir};
use crate::viewport::Viewport;

/// Draw-slot namespaces, disjoint by construction. A tile's index is added to
/// the base, so slot `GEOMETRY + 7` is tile 7's framing and nothing else's.
const SLOT_GEOMETRY: u64 = 1_000;
const SLOT_PALETTE: u64 = 2_000;
const SLOT_LEVEL: u64 = 3_000;
const SLOT_QUALITY: u64 = 4_000;

/// A batch of locations to turn into tiles.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TilesSpec {
    pub schema: u32,
    /// JSONL: one location per line, as [`PlanRow`].
    pub locations: PathBuf,
    /// Tiles land at
    /// `<out_root>/<location_id>/t<NN>_<palette>_s<scale>_sh<shift>_<level>_q<q><regime>.jpg`,
    /// where `<regime>` is `_<w>x<h>ss<n>` and empty at the canonical regime. See
    /// [`regime_tag`]: it is what lets two geometries share one `out_root`.
    pub out_root: PathBuf,
    /// Where the record of what was written goes, one line per tile.
    pub manifest: PathBuf,
    #[serde(default = "default_colormap_dir")]
    pub colormap_dir: PathBuf,
    /// Names the whole fan-out. Changing it reshuffles every draw in the corpus,
    /// which is why it is recorded on every row rather than inferred.
    pub seed_tag: String,
    #[serde(default)]
    pub recipe: Recipe,
    /// Stop after this many locations. The whole path runs — field, crops, JPEGs,
    /// manifest — so a bounded rehearsal is the real thing on a prefix, and every
    /// row it writes says `partial` so it can never be read as a finished build.
    #[serde(default)]
    pub limit: Option<usize>,
}

/// The tile recipe: what a location's fan-out is drawn from.
///
/// Defaults are the shipped recipe. They are defaults rather than constants
/// because a spec that states them is a spec that can be read back years later
/// without this file, and the plan record does state them.
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Recipe {
    /// `[width, height]` of one tile, in output pixels.
    #[serde(default = "default_tile")]
    pub tile: [u32; 2],
    #[serde(default = "default_tiles")]
    pub tiles: usize,
    /// Samples per canonical output pixel, per axis, in the extended field.
    #[serde(default = "default_field_supersample")]
    pub field_supersample: u32,
    /// How much wider than the canonical frame the field is rendered.
    #[serde(default = "default_extend")]
    pub extend: f64,
    /// `[lo, hi]` of the per-tile zoom draw, as a factor of the canonical frame.
    #[serde(default = "default_scale")]
    pub scale: [f64; 2],
    /// Largest per-tile displacement, as a fraction of the canonical frame width.
    #[serde(default = "default_shift")]
    pub shift_frac_max: f64,
    /// `[lo, hi]` of the per-tile JPEG quality draw, inclusive.
    #[serde(default = "default_quality")]
    pub quality: [u8; 2],
    /// Every colormap a free tile may draw, uniformly and with replacement.
    pub palette_pool: Vec<String>,
    /// `[name, count]` reservations over the **low** tile slots. Drawn from the
    /// tiles, never added to them: a floor is a minimum, not a bonus, and a
    /// floor palette that is also in the pool can be drawn again above it.
    #[serde(default)]
    pub floor_palette: Vec<(String, usize)>,
    /// How many low slots carry the **canonical view**: dead centre, scale
    /// exactly 1, antialiased, at [`CANONICAL_QUALITY`]. One is enough, and one
    /// is the point — it is the picture a deployed judge is handed, so every
    /// location must own it and it must not be a draw. Pinning the whole cell
    /// rather than the framing alone is what makes a second build stage
    /// unnecessary: with a coin on the reconstruction, half the corpus would
    /// have no canonical view and it would have to be rendered again afterwards.
    #[serde(default = "default_floor_identity")]
    pub floor_identity: usize,
}

fn default_tile() -> [u32; 2] {
    [640, 360]
}
fn default_tiles() -> usize {
    32
}
fn default_field_supersample() -> u32 {
    2
}
fn default_extend() -> f64 {
    1.2
}
fn default_scale() -> [f64; 2] {
    [0.90, 1.10]
}
fn default_shift() -> f64 {
    0.05
}
fn default_quality() -> [u8; 2] {
    [60, 95]
}
fn default_floor_identity() -> usize {
    1
}

/// The JPEG quality the canonical view is written at — the engine's own, the
/// one every other JPEG it writes uses, so a location rendered fresh through
/// `render` and a location read out of the tile cache are the same picture.
pub const CANONICAL_QUALITY: u8 = 90;

impl Default for Recipe {
    fn default() -> Recipe {
        Recipe {
            tile: default_tile(),
            tiles: default_tiles(),
            field_supersample: default_field_supersample(),
            extend: default_extend(),
            scale: default_scale(),
            shift_frac_max: default_shift(),
            quality: default_quality(),
            palette_pool: Vec::new(),
            floor_palette: Vec::new(),
            floor_identity: default_floor_identity(),
        }
    }
}

/// One location of the plan.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PlanRow {
    pub schema: u32,
    /// The location's index in this build. It seeds every draw, so it is part of
    /// the recipe's identity and not a display detail.
    pub location_id: u64,
    pub family: FamilySpec,
    pub viewport: crate::spec::ViewportSpec,
    /// The **canonical** frame's iteration cap. Omitted means the depth-aware
    /// policy decides from the canonical width — never from the extended
    /// field's own wider one, which would raise the cap on the padding and make
    /// a location's tiles incomparable with a plain render of it.
    #[serde(default)]
    pub maxiter: Option<u32>,
}

/// The extended field's geometry, and the crop → field coordinate map.
#[derive(Clone, Copy, Debug)]
struct FieldGeom {
    out_width: u32,
    out_height: u32,
    supersample: u32,
    /// Extended field size, in subpixels.
    samples_x: u32,
    samples_y: u32,
    /// Whole-subpixel pad per side — the same on all four, an equal plane
    /// distance. Whole, so the extended grid *contains* the canonical grid at an
    /// integer offset and the canonical framing lands on the same sample
    /// positions a plain render would have used.
    pad: u32,
    /// The plane width actually rendered.
    width: f64,
}

impl FieldGeom {
    fn build(recipe: &Recipe, width: f64) -> FieldGeom {
        let [out_width, out_height] = recipe.tile;
        let supersample = recipe.field_supersample;
        let base_x = out_width * supersample;
        let base_y = out_height * supersample;
        // Rounded up, so the realized margin is never below what was asked for.
        let pad = (((recipe.extend - 1.0) / 2.0) * base_x as f64)
            .ceil()
            .max(0.0) as u32;
        let samples_x = base_x + 2 * pad;
        let samples_y = base_y + 2 * pad;
        FieldGeom {
            out_width,
            out_height,
            supersample,
            samples_x,
            samples_y,
            pad,
            width: width * samples_x as f64 / base_x as f64,
        }
    }

    /// Realized extension on each axis. The vertical one is larger, because the
    /// margin is an equal plane distance and the frame is wider than it is tall.
    fn realized_extend(&self) -> [f64; 2] {
        [
            self.samples_x as f64 / (self.out_width * self.supersample) as f64,
            self.samples_y as f64 / (self.out_height * self.supersample) as f64,
        ]
    }

    /// The view handed to the iteration: the extended frame at one sample per
    /// subpixel, so the field array is exactly `samples_x × samples_y`.
    fn view(&self, center: Complex<f64>) -> Viewport {
        Viewport {
            center,
            width: self.width,
            out_width: self.samples_x,
            out_height: self.samples_y,
            supersample: 1,
        }
    }

    /// A tile's window in field-subpixel units. Output pixel `d` sits at
    /// `origin + (d + 0.5)·ratio`; the canonical framing maps to
    /// `(pad, pad, supersample)` exactly.
    fn window(&self, geometry: Geometry) -> Window {
        let base_x = (self.out_width * self.supersample) as f64;
        let base_y = (self.out_height * self.supersample) as f64;
        let (dx, dy) = geometry.offset();
        Window {
            // Both displacements convert through the frame WIDTH: the shift is a
            // single magnitude in width units, which is what the containment
            // bound is derived from.
            x: self.pad as f64 + dx * base_x + 0.5 * base_x * (1.0 - geometry.scale),
            y: self.pad as f64 - dy * base_x + 0.5 * base_y * (1.0 - geometry.scale),
            ratio: geometry.scale * self.supersample as f64,
        }
    }
}

/// Where one tile reads the field, in subpixels.
#[derive(Clone, Copy, Debug, Serialize)]
struct Window {
    x: f64,
    y: f64,
    ratio: f64,
}

/// One tile's framing: a zoom and a displacement of the canonical frame.
#[derive(Clone, Copy, Debug, Serialize)]
struct Geometry {
    scale: f64,
    shift_frac: f64,
    angle: f64,
}

impl Geometry {
    fn canonical() -> Geometry {
        Geometry {
            scale: 1.0,
            shift_frac: 0.0,
            angle: 0.0,
        }
    }

    fn draw(seed: u64, recipe: &Recipe) -> Geometry {
        let [lo, hi] = recipe.scale;
        let mut rng = Rng(seed);
        Geometry {
            scale: lo + rng.unit() * (hi - lo),
            shift_frac: rng.unit() * recipe.shift_frac_max,
            angle: rng.unit() * std::f64::consts::TAU,
        }
    }

    /// The displacement as `(dx, dy)` in canonical-frame-width fractions.
    fn offset(self) -> (f64, f64) {
        (
            self.shift_frac * self.angle.cos(),
            self.shift_frac * self.angle.sin(),
        )
    }
}

/// How a tile is reconstructed from the field. See the module docs: this is a
/// mode, not a supersample factor, because one field leaves no factor to name.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
enum Level {
    /// Reconstructed by point sampling: the nearest subpixel, and the honest
    /// stand-in for a render that never supersampled.
    Aliased,
    /// Reconstructed by Lanczos-3 in linear light at the crop's own ratio.
    Antialiased,
}

impl Level {
    /// The two levels, in the order the coin reads them.
    const BOTH: [Level; 2] = [Level::Aliased, Level::Antialiased];

    fn name(self) -> &'static str {
        match self {
            Level::Aliased => "aliased",
            Level::Antialiased => "antialiased",
        }
    }
}

/// One tile's fully-drawn recipe. Nothing here is decided again at render time.
#[derive(Clone, Debug)]
struct Tile {
    index: usize,
    geometry: Geometry,
    window: Window,
    level: Level,
    palette: String,
    quality: u8,
    output: PathBuf,
}

/// One row of the manifest: everything needed to find, read, or rebuild a tile.
#[derive(Debug, Serialize)]
struct ManifestRow<'a> {
    schema: u32,
    location_id: u64,
    tile: usize,
    path: String,
    palette: &'a str,
    level: Level,
    quality: u8,
    scale: f64,
    shift_frac: f64,
    shift_angle: f64,
    /// The tile's window into the field, so a tile can be rebuilt from its own
    /// row without re-drawing anything.
    window: Window,
    maxiter: u32,
    seed_tag: &'a str,
    location: &'a Location,
    field: FieldRecord,
    tile_size: [u32; 2],
    /// True on every row a `limit`-bounded run wrote. A partial build that could
    /// pass for a whole one is how a head ends up trained on a prefix.
    partial: bool,
}

#[derive(Clone, Copy, Debug, Serialize)]
struct FieldRecord {
    supersample: u32,
    samples: [u32; 2],
    pad: u32,
    width: f64,
    extend: [f64; 2],
}

/// What the build did.
#[derive(Debug, Serialize)]
pub struct TilesReport {
    pub schema: u32,
    pub locations: usize,
    pub tiles_written: usize,
    pub tiles_skipped: usize,
    pub locations_skipped: usize,
    pub manifest: String,
    pub out_root: String,
    pub seed_tag: String,
    pub recipe: Recipe,
    pub containment: Containment,
    pub partial: bool,
    pub seconds: TilesSeconds,
}

/// The containment bound, stated as the numbers that produced it.
#[derive(Debug, Serialize)]
pub struct Containment {
    pub required: f64,
    pub declared: f64,
    pub realized_extend: [f64; 2],
    pub field_samples: [u32; 2],
}

#[derive(Debug, Serialize)]
pub struct TilesSeconds {
    pub field: f64,
    pub tiles: f64,
    pub total: f64,
}

/// A path as the manifest records it: forward slashes, whichever platform wrote
/// it. A record is read by the training loop on the other operating system as
/// often as on this one, and a backslash there is a file name.
fn posix(path: &Path) -> String {
    path.to_string_lossy().replace('\\', "/")
}

/// A location's stream, from the tag and the location's own id.
fn location_seed(tag: &str, location_id: u64) -> u64 {
    rng::sub_seed(tag_seed(tag), location_id)
}

/// The tag's own 64 bits. FNV-1a, so the same tag gives the same stream in any
/// language with wrapping arithmetic — the property that lets a fan-out be
/// audited from outside this crate.
fn tag_seed(tag: &str) -> u64 {
    let mut hash: u64 = 0xcbf2_9ce4_8422_2325;
    for byte in tag.as_bytes() {
        hash ^= *byte as u64;
        hash = hash.wrapping_mul(0x0000_0100_0000_01B3);
    }
    hash
}

/// The regime segment of a tile's name: the geometry the picture was made at.
///
/// A tile differs from another tile of the same location, slot, palette and
/// framing when it is drawn at a different **regime** — a different tile size or
/// a different field supersample — and until this was in the name those two were
/// one file. The build skips a location whose tiles are all present, so aiming a
/// second regime at the first one's cache rendered nothing and exited 0 with a
/// record claiming a geometry that is not what is on disk.
///
/// The canonical regime elides, exactly as `job_name`'s spec omits a field at its
/// settled default: every name written before this segment existed is still the
/// name that regime writes, byte for byte, so the corpus does not move.
fn regime_tag(recipe: &Recipe) -> String {
    if recipe.tile == default_tile() && recipe.field_supersample == default_field_supersample() {
        String::new()
    } else {
        format!(
            "_{}x{}ss{}",
            recipe.tile[0], recipe.tile[1], recipe.field_supersample
        )
    }
}

/// The floor's slot → palette expansion: `twilight_shifted:2 blue_orange:2`
/// reserves slots 0 and 1 for the first and slots 2 and 3 for the second.
fn floor_slots(recipe: &Recipe) -> Vec<&str> {
    recipe
        .floor_palette
        .iter()
        .flat_map(|(name, count)| std::iter::repeat_n(name.as_str(), *count))
        .collect()
}

/// Every tile of one location, drawn.
fn plan_tiles(recipe: &Recipe, geom: &FieldGeom, row: &PlanRow, tag: &str) -> Vec<Tile> {
    let seed = location_seed(tag, row.location_id);
    let floor = floor_slots(recipe);
    let regime = regime_tag(recipe);
    let [quality_lo, quality_hi] = recipe.quality;
    (0..recipe.tiles)
        .map(|index| {
            let slot = index as u64;
            let palette = match floor.get(index) {
                Some(name) => (*name).to_string(),
                None => {
                    let mut rng = Rng(rng::sub_seed(seed, SLOT_PALETTE + slot));
                    recipe.palette_pool[rng.below(recipe.palette_pool.len())].clone()
                }
            };
            let canonical = index < recipe.floor_identity;
            let geometry = if canonical {
                Geometry::canonical()
            } else {
                Geometry::draw(rng::sub_seed(seed, SLOT_GEOMETRY + slot), recipe)
            };
            let level = if canonical {
                Level::Antialiased
            } else {
                let mut rng = Rng(rng::sub_seed(seed, SLOT_LEVEL + slot));
                Level::BOTH[rng.below(Level::BOTH.len())]
            };
            let quality = if canonical {
                CANONICAL_QUALITY
            } else if quality_hi > quality_lo {
                let mut rng = Rng(rng::sub_seed(seed, SLOT_QUALITY + slot));
                quality_lo + rng.below((quality_hi - quality_lo) as usize + 1) as u8
            } else {
                quality_lo
            };
            // The tile index leads the name. Under an independent draw two free
            // slots may land on the same palette at the same rounded framing, so
            // uniqueness is structural rather than left to the draw. The regime
            // trails it, and is empty at the canonical one.
            let name = format!(
                "t{index:02}_{palette}_s{:.4}_sh{:.4}_{}_q{quality}{regime}.jpg",
                geometry.scale,
                geometry.shift_frac,
                level.name()
            );
            Tile {
                index,
                geometry,
                window: geom.window(geometry),
                level,
                palette,
                quality,
                output: Path::new(&row.location_id.to_string()).join(name),
            }
        })
        .collect()
}

/// Color and resample one crop of the field, and write it.
fn write_tile(
    values: &[f32],
    geom: &FieldGeom,
    tile: &Tile,
    colormap: &Colormap,
    path: &Path,
) -> Result<(), String> {
    let (out_width, out_height) = (geom.out_width as usize, geom.out_height as usize);
    let (samples_x, samples_y) = (geom.samples_x as usize, geom.samples_y as usize);
    let window = tile.window;

    // The sub-rectangle the crop reads, as whole subpixels. The filtered arm
    // reaches three output pixels either way, so its rectangle is the window
    // grown by the kernel's reach; the point arm reads exactly its own window.
    let reach = match tile.level {
        Level::Aliased => 0.0,
        Level::Antialiased => 3.0 * window.ratio,
    };
    let x0 = (window.x - reach).floor().max(0.0) as usize;
    let y0 = (window.y - reach).floor().max(0.0) as usize;
    let x1 = ((window.x + window.ratio * out_width as f64 + reach).ceil() as usize).min(samples_x);
    let y1 = ((window.y + window.ratio * out_height as f64 + reach).ceil() as usize).min(samples_y);
    let (crop_width, crop_height) = (x1 - x0, y1 - y0);

    // The stretch is measured over the window the tile covers — not over the
    // kernel's overhang, and not over the extended field.
    let inside_x0 = window.x.floor().max(0.0) as usize;
    let inside_y0 = window.y.floor().max(0.0) as usize;
    let inside_x1 = ((window.x + window.ratio * out_width as f64).ceil() as usize).min(samples_x);
    let inside_y1 = ((window.y + window.ratio * out_height as f64).ceil() as usize).min(samples_y);
    let stretch = Stretch::over(
        (inside_y0..inside_y1)
            .flat_map(|row| values[row * samples_x + inside_x0..row * samples_x + inside_x1].iter())
            .map(|&value| value as f64),
    );

    let pixels = match tile.level {
        Level::Aliased => {
            let mut pixels = Vec::with_capacity(out_width * out_height * 3);
            for down in 0..out_height {
                let row =
                    ((window.y + (down as f64 + 0.5) * window.ratio) as usize).min(samples_y - 1);
                for across in 0..out_width {
                    let column = ((window.x + (across as f64 + 0.5) * window.ratio) as usize)
                        .min(samples_x - 1);
                    let value = values[row * samples_x + column];
                    let linear = if value.is_finite() {
                        colormap.lookup(Transform::Linear.apply(stretch.position(value as f64)))
                    } else {
                        INTERIOR
                    };
                    for channel in linear {
                        let encoded = crate::colormap::linear_to_srgb(channel.clamp(0.0, 1.0));
                        pixels.push((encoded * 255.0 + 0.5) as u8);
                    }
                }
            }
            pixels
        }
        Level::Antialiased => {
            let linear: Vec<[f64; 3]> = (y0..y1)
                .flat_map(|row| values[row * samples_x + x0..row * samples_x + x1].iter())
                .map(|&value| {
                    if value.is_finite() {
                        colormap.lookup(Transform::Linear.apply(stretch.position(value as f64)))
                    } else {
                        INTERIOR
                    }
                })
                .collect();
            let horizontal =
                resample::build_taps_at(out_width, crop_width, window.x - x0 as f64, window.ratio);
            let vertical = resample::build_taps_at(
                out_height,
                crop_height,
                window.y - y0 as f64,
                window.ratio,
            );
            resample::apply_taps(&linear, crop_width, crop_height, &horizontal, &vertical)
        }
    };

    // Written under a temporary name and renamed, so a killed run leaves either
    // a whole tile or none — a half-written JPEG is a training example that
    // decodes and is wrong.
    let temporary = path.with_extension("jpg.partial");
    resample::write_jpeg_at(
        &temporary,
        &pixels,
        geom.out_width,
        geom.out_height,
        tile.quality,
    )?;
    std::fs::rename(&temporary, path).map_err(|e| format!("rename {}: {e}", path.display()))
}

/// Read the plan.
fn read_plan(path: &Path) -> Result<Vec<PlanRow>, String> {
    let text =
        std::fs::read_to_string(path).map_err(|e| format!("read plan {}: {e}", path.display()))?;
    let mut rows = Vec::new();
    for (number, line) in text.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let row: PlanRow = serde_json::from_str(line)
            .map_err(|e| format!("{}:{}: {e}", path.display(), number + 1))?;
        if row.schema != 1 {
            return Err(format!(
                "{}:{}: plan row has schema {}, expected 1",
                path.display(),
                number + 1,
                row.schema
            ));
        }
        if row.maxiter == Some(0) {
            return Err(format!(
                "{}:{}: location {} pins an iteration cap of zero",
                path.display(),
                number + 1,
                row.location_id
            ));
        }
        rows.push(row);
    }
    Ok(rows)
}

/// The containment bound, and the check that the declared extension meets it.
fn containment(recipe: &Recipe) -> Result<f64, String> {
    let [width, height] = recipe.tile;
    let [_, scale_hi] = recipe.scale;
    let aspect = (height as f64 / width as f64).max(1.0);
    let required = 1.0 + 2.0 * recipe.shift_frac_max + aspect * (scale_hi - 1.0);
    // A tolerance, because the shipped recipe sits exactly on the bound and
    // `1 + 0.1 + (1.1 − 1.0)` is 1.2000000000000002 in binary: a bare comparison
    // would refuse the configuration this module was written for. The slack is a
    // billionth of a frame; the per-tile window check is the real guarantee.
    if recipe.extend < required - 1e-9 {
        return Err(format!(
            "extend {} is below the containment bound {required:.9} = 1 + 2·{} + max(1, {}/{})·({} − 1). \
             The widest tile displaced by the largest shift would read off the end of the field, \
             and the resample would smear the edge rather than fail. Widen the field or narrow \
             the draw — they are one decision.",
            recipe.extend, recipe.shift_frac_max, height, width, scale_hi
        ));
    }
    Ok(required)
}

/// Check that every drawn window lands inside the field.
///
/// Defence in depth behind the containment bound: the tap builder clamps at the
/// source edge, so a window that ran off would produce an edge-smeared tile
/// rather than an error, and a silently wrong training example is exactly what
/// this module exists to stop producing.
fn check_window(geom: &FieldGeom, tile: &Tile) -> Result<(), String> {
    let window = tile.window;
    let far_x = window.x + window.ratio * geom.out_width as f64;
    let far_y = window.y + window.ratio * geom.out_height as f64;
    if window.x < 0.0
        || window.y < 0.0
        || far_x > geom.samples_x as f64
        || far_y > geom.samples_y as f64
    {
        return Err(format!(
            "tile {} reads [{:.2}, {:.2}] × [{:.2}, {:.2}] of a {}×{} field (scale {:.4}, shift \
             {:.4}) — the extension is too small for the draw",
            tile.index,
            window.x,
            far_x,
            window.y,
            far_y,
            geom.samples_x,
            geom.samples_y,
            tile.geometry.scale,
            tile.geometry.shift_frac
        ));
    }
    Ok(())
}

/// Build every tile of every location in the plan.
pub fn run(spec: TilesSpec) -> Result<TilesReport, String> {
    if spec.schema != 1 {
        return Err(format!("spec has schema {}, expected 1", spec.schema));
    }
    let recipe = spec.recipe;
    if recipe.tiles == 0 {
        return Err("a location with no tiles is a location the head never sees".into());
    }
    if recipe.field_supersample == 0 {
        return Err("field_supersample must be at least 1".into());
    }
    if recipe.palette_pool.is_empty() {
        return Err("palette_pool is empty: a free tile has nothing to draw".into());
    }
    let [scale_lo, scale_hi] = recipe.scale;
    if !(scale_lo > 0.0 && scale_hi >= scale_lo) {
        return Err(format!(
            "scale must satisfy 0 < lo ≤ hi, got [{scale_lo}, {scale_hi}]"
        ));
    }
    let [quality_lo, quality_hi] = recipe.quality;
    if quality_lo == 0 || quality_hi > 100 || quality_hi < quality_lo {
        return Err(format!(
            "quality must satisfy 1 ≤ lo ≤ hi ≤ 100, got [{quality_lo}, {quality_hi}]"
        ));
    }
    let reserved: usize = recipe.floor_palette.iter().map(|(_, count)| count).sum();
    if reserved > recipe.tiles {
        return Err(format!(
            "the palette floor reserves {reserved} of {} tiles — a floor is drawn FROM the \
             tiles, never added to them",
            recipe.tiles
        ));
    }
    if recipe.floor_identity > recipe.tiles {
        return Err(format!(
            "floor_identity {} exceeds the {} tiles it is drawn from",
            recipe.floor_identity, recipe.tiles
        ));
    }
    let required = containment(&recipe)?;

    let mut plan = read_plan(&spec.locations)?;
    let partial = spec.limit.is_some_and(|limit| limit < plan.len());
    if let Some(limit) = spec.limit {
        plan.truncate(limit);
    }
    if plan.is_empty() {
        return Err(format!("{} holds no locations", spec.locations.display()));
    }

    // Every colormap the recipe can reach, baked once for the whole run.
    let mut names: Vec<String> = recipe.palette_pool.clone();
    names.extend(recipe.floor_palette.iter().map(|(name, _)| name.clone()));
    names.sort();
    names.dedup();
    let colormaps: Vec<(String, Colormap)> = names
        .iter()
        .map(|name| {
            Colormap::load(&spec.colormap_dir, name).map(|colormap| (name.clone(), colormap))
        })
        .collect::<Result<_, _>>()?;
    let colormap_of = |name: &str| -> &Colormap {
        &colormaps
            .iter()
            .find(|(known, _)| known == name)
            .expect("every drawn palette is in the baked set")
            .1
    };

    if let Some(parent) = spec.manifest.parent()
        && !parent.as_os_str().is_empty()
    {
        std::fs::create_dir_all(parent).map_err(|e| format!("create {}: {e}", parent.display()))?;
    }
    let mut manifest = std::io::BufWriter::new(
        std::fs::File::create(&spec.manifest)
            .map_err(|e| format!("create {}: {e}", spec.manifest.display()))?,
    );

    let started = Instant::now();
    let (mut field_seconds, mut tile_seconds) = (0.0, 0.0);
    let (mut written, mut skipped, mut locations_skipped) = (0usize, 0usize, 0usize);
    let mut last_geom: Option<FieldGeom> = None;

    for (index, row) in plan.iter().enumerate() {
        let resolved = resolve(row)?;
        let geom = FieldGeom::build(&recipe, resolved.width);
        // Checked against the FIELD's grid, not the tile's. The field is
        // supersampled and extended, so its samples sit closer together than a
        // plain render's, and it is the field that runs out of `f64` first.
        let view = geom.view(resolved.center);
        if !view.is_resolvable_in_f64() {
            return Err(format!(
                "location {}: the extended field samples {:.3e} apart, at the limit of f64 — \
                 neighbouring subpixels would round to the same coordinate and the tiles would \
                 be pictures of the arithmetic",
                row.location_id,
                view.pixel_size()
            ));
        }
        last_geom = Some(geom);
        let tiles = plan_tiles(&recipe, &geom, row, &spec.seed_tag);
        for tile in &tiles {
            check_window(&geom, tile)?;
        }

        let paths: Vec<PathBuf> = tiles
            .iter()
            .map(|tile| spec.out_root.join(&tile.output))
            .collect();
        let missing: Vec<usize> = (0..tiles.len())
            .filter(|&slot| !paths[slot].is_file())
            .collect();
        skipped += tiles.len() - missing.len();

        if missing.is_empty() {
            // Every tile is already on disk, so the field never has to be
            // iterated: that is what makes a killed run cheap to continue.
            locations_skipped += 1;
        } else {
            if let Some(parent) = paths[0].parent() {
                std::fs::create_dir_all(parent)
                    .map_err(|e| format!("create {}: {e}", parent.display()))?;
            }
            let clock = Instant::now();
            let sampled =
                field::render_field(&view, &resolved.family, resolved.maxiter, FieldSpec::Smooth);
            field_seconds += clock.elapsed().as_secs_f64();
            let values = &sampled.fields[0].values;

            let clock = Instant::now();
            missing
                .par_iter()
                .map(|&slot| {
                    write_tile(
                        values,
                        &geom,
                        &tiles[slot],
                        colormap_of(&tiles[slot].palette),
                        &paths[slot],
                    )
                })
                .collect::<Result<Vec<()>, String>>()?;
            tile_seconds += clock.elapsed().as_secs_f64();
            written += missing.len();
        }

        let extend = geom.realized_extend();
        for (slot, tile) in tiles.iter().enumerate() {
            let record = ManifestRow {
                schema: 1,
                location_id: row.location_id,
                tile: tile.index,
                path: posix(&paths[slot]),
                palette: &tile.palette,
                level: tile.level,
                quality: tile.quality,
                scale: tile.geometry.scale,
                shift_frac: tile.geometry.shift_frac,
                shift_angle: tile.geometry.angle,
                window: tile.window,
                maxiter: resolved.maxiter,
                seed_tag: &spec.seed_tag,
                location: &resolved.location,
                field: FieldRecord {
                    supersample: geom.supersample,
                    samples: [geom.samples_x, geom.samples_y],
                    pad: geom.pad,
                    width: geom.width,
                    extend,
                },
                tile_size: recipe.tile,
                partial,
            };
            writeln!(
                manifest,
                "{}",
                serde_json::to_string(&record).map_err(|e| format!("manifest row: {e}"))?
            )
            .map_err(|e| format!("write {}: {e}", spec.manifest.display()))?;
        }

        if (index + 1) % 100 == 0 || index + 1 == plan.len() {
            let elapsed = started.elapsed().as_secs_f64();
            let rate = elapsed / (index + 1) as f64;
            eprintln!(
                "tiles: {}/{} locations  {written} written  {skipped} present  \
                 {elapsed:.0}s elapsed  {:.0}s left",
                index + 1,
                plan.len(),
                rate * (plan.len() - index - 1) as f64
            );
        }
    }

    manifest
        .flush()
        .map_err(|e| format!("write {}: {e}", spec.manifest.display()))?;
    let geom = last_geom.expect("a non-empty plan renders at least one location");

    Ok(TilesReport {
        schema: 1,
        locations: plan.len(),
        tiles_written: written,
        tiles_skipped: skipped,
        locations_skipped,
        manifest: spec.manifest.display().to_string(),
        out_root: spec.out_root.display().to_string(),
        seed_tag: spec.seed_tag,
        containment: Containment {
            required,
            declared: recipe.extend,
            realized_extend: geom.realized_extend(),
            field_samples: [geom.samples_x, geom.samples_y],
        },
        recipe,
        partial,
        seconds: TilesSeconds {
            field: field_seconds,
            tiles: tile_seconds,
            total: started.elapsed().as_secs_f64(),
        },
    })
}

/// A plan row with its strings parsed, and the strings kept for the record.
struct Resolved {
    family: Family,
    center: Complex<f64>,
    width: f64,
    maxiter: u32,
    location: Location,
}

fn resolve(row: &PlanRow) -> Result<Resolved, String> {
    let spec = crate::spec::RenderSpec {
        schema: 1,
        family: clone_family(&row.family)?,
        viewport: crate::spec::ViewportSpec {
            center_re: row.viewport.center_re.clone(),
            center_im: row.viewport.center_im.clone(),
            width: row.viewport.width.clone(),
        },
        resolution: [1, 1],
        supersample: 1,
        mode: None,
        coloring: None,
        palette: Default::default(),
        colormap: String::new(),
        colormap_dir: PathBuf::new(),
        maxiter: row.maxiter,
        output: PathBuf::new(),
    };
    let resolved = spec.resolve()?;
    Ok(Resolved {
        family: resolved.family,
        center: resolved.view.center,
        width: decimal(&resolved.location.width, "viewport.width")?,
        maxiter: resolved.maxiter,
        location: resolved.location,
    })
}

/// `FamilySpec` is deserialize-only and holds owned strings; a plan row is read
/// once and rendered once, so the copy is a formality rather than a cost.
fn clone_family(family: &FamilySpec) -> Result<FamilySpec, String> {
    let pair = |p: &Pair| -> Pair { [p[0].clone(), p[1].clone()] };
    Ok(match family {
        FamilySpec::Mandelbrot => FamilySpec::Mandelbrot,
        FamilySpec::Multibrot { degree } => FamilySpec::Multibrot { degree: *degree },
        FamilySpec::Julia { degree, c } => FamilySpec::Julia {
            degree: *degree,
            c: pair(c),
        },
        FamilySpec::Phoenix { c, p, z_prev } => FamilySpec::Phoenix {
            c: pair(c),
            p: pair(p),
            z_prev: pair(z_prev),
        },
        // A render-only family has no business in a training tile: the tiles are
        // what the judges learn a location from, and this family is never a
        // location a judge will be asked about. Refused here rather than in the
        // loop, because a plan is read whole before a single field is iterated.
        FamilySpec::FractionalMultibrot { .. } => {
            return Err(crate::spec::render_only_refusal(
                "fractional_multibrot",
                "cut into training tiles",
            ));
        }
    })
}

impl TilesSpec {
    /// Read a tiles spec from JSON text.
    pub fn parse(text: &str) -> Result<TilesSpec, String> {
        serde_json::from_str(text).map_err(|e| format!("spec: {e}"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn recipe() -> Recipe {
        Recipe {
            palette_pool: vec!["twilight_shifted".into(), "blue_orange".into()],
            floor_palette: vec![("twilight_shifted".into(), 2), ("blue_orange".into(), 2)],
            ..Recipe::default()
        }
    }

    #[test]
    fn the_shipped_recipe_sits_exactly_on_the_containment_bound() {
        let required = containment(&recipe()).unwrap();
        assert!((required - 1.2).abs() < 1e-9, "required {required}");
        let mut wider = recipe();
        wider.scale = [0.90, 1.15];
        assert!(containment(&wider).is_err(), "a wider zoom must not fit");
        let mut further = recipe();
        further.shift_frac_max = 0.08;
        assert!(
            containment(&further).is_err(),
            "a further shift must not fit"
        );
    }

    /// The margin is an equal plane distance, so the *relative* extension is
    /// larger on the short axis. Hiding that is how the vertical gets under-padded.
    #[test]
    fn the_vertical_extension_is_the_larger_one() {
        let geom = FieldGeom::build(&recipe(), 3.0);
        let [across, down] = geom.realized_extend();
        assert!(across >= 1.2 && down > across, "{across} vs {down}");
        assert_eq!(geom.samples_x, 640 * 2 + 2 * 128);
        assert_eq!(geom.samples_y, 360 * 2 + 2 * 128);
    }

    /// Tiles are what the judges learn a location from, so a render-only family
    /// is refused where the plan is read — before a field is iterated, and long
    /// before a tile could be written under a head's name.
    #[test]
    fn a_render_only_family_cannot_be_cut_into_tiles() {
        let message = clone_family(&FamilySpec::FractionalMultibrot {
            degree: "2.5".into(),
        })
        .unwrap_err();
        assert!(message.contains("render-only"), "{message}");
        for family in [
            FamilySpec::Mandelbrot,
            FamilySpec::Multibrot { degree: 4 },
            FamilySpec::Phoenix {
                c: ["0.5667".into(), "0.0".into()],
                p: ["-0.5".into(), "0.0".into()],
                z_prev: ["0.0".into(), "0.0".into()],
            },
        ] {
            clone_family(&family).expect("every other family still copies");
        }
    }

    /// The canonical framing must land on the field's own grid at an integer
    /// offset, or the tile every deploy-time score is compared against is a
    /// resampling of the picture rather than the picture.
    #[test]
    fn the_canonical_framing_lands_on_the_pad_exactly() {
        let geom = FieldGeom::build(&recipe(), 3.0);
        let window = geom.window(Geometry::canonical());
        assert_eq!(window.x, geom.pad as f64);
        assert_eq!(window.y, geom.pad as f64);
        assert_eq!(window.ratio, geom.supersample as f64);
    }

    /// Every draw of the corpus has to stay inside the field. Checking the
    /// extremes is not enough — the shift direction is uniform, so the binding
    /// case is a diagonal one.
    #[test]
    fn every_drawn_window_stays_inside_the_field() {
        let recipe = recipe();
        let geom = FieldGeom::build(&recipe, 0.5);
        for location_id in 0..400u64 {
            let row = PlanRow {
                schema: 1,
                location_id,
                family: FamilySpec::Mandelbrot,
                viewport: Default::default(),
                maxiter: Some(1000),
            };
            for tile in plan_tiles(&recipe, &geom, &row, "a-tag") {
                check_window(&geom, &tile).expect("a drawn window left the field");
            }
        }
    }

    /// The floor is a minimum drawn from the tiles: the reserved low slots carry
    /// the named palettes and the canonical framing, and everything above them
    /// is free.
    #[test]
    fn the_floor_reserves_the_low_slots_and_nothing_more() {
        let recipe = recipe();
        let geom = FieldGeom::build(&recipe, 3.0);
        let row = PlanRow {
            schema: 1,
            location_id: 7,
            family: FamilySpec::Mandelbrot,
            viewport: Default::default(),
            maxiter: Some(1000),
        };
        let tiles = plan_tiles(&recipe, &geom, &row, "a-tag");
        assert_eq!(tiles.len(), 32);
        assert_eq!(tiles[0].palette, "twilight_shifted");
        assert_eq!(tiles[1].palette, "twilight_shifted");
        assert_eq!(tiles[2].palette, "blue_orange");
        assert_eq!(tiles[3].palette, "blue_orange");
        assert_eq!(tiles[0].geometry.scale, 1.0);
        assert_eq!(tiles[0].geometry.shift_frac, 0.0);
        assert!(
            tiles[1].geometry.scale != 1.0,
            "only slot 0 is the canonical framing"
        );
    }

    /// A tile is a pure function of its location row and the tag: same inputs,
    /// same fan-out; a different tag, a different one.
    #[test]
    fn the_fan_out_replays_from_the_tag_and_the_location() {
        let recipe = recipe();
        let geom = FieldGeom::build(&recipe, 3.0);
        let row = PlanRow {
            schema: 1,
            location_id: 11,
            family: FamilySpec::Mandelbrot,
            viewport: Default::default(),
            maxiter: Some(1000),
        };
        let once = plan_tiles(&recipe, &geom, &row, "a-tag");
        let again = plan_tiles(&recipe, &geom, &row, "a-tag");
        let other = plan_tiles(&recipe, &geom, &row, "another-tag");
        for slot in 0..once.len() {
            assert_eq!(once[slot].output, again[slot].output);
        }
        assert!(
            (0..once.len()).any(|slot| once[slot].output != other[slot].output),
            "a fresh tag must reshuffle the fan-out"
        );
    }

    /// The canonical regime's names are the names that existed before the regime
    /// segment did. Written out against the literal legacy form rather than
    /// against `regime_tag` itself, because a test that asks the same function
    /// the code asks would pass on any convention it happened to adopt.
    #[test]
    fn the_canonical_regime_writes_the_name_it_always_wrote() {
        let recipe = recipe();
        assert_eq!(recipe.tile, [640, 360]);
        assert_eq!(recipe.field_supersample, 2);
        let geom = FieldGeom::build(&recipe, 3.0);
        let row = PlanRow {
            schema: 1,
            location_id: 4242,
            family: FamilySpec::Mandelbrot,
            viewport: Default::default(),
            maxiter: Some(1000),
        };
        for tile in plan_tiles(&recipe, &geom, &row, "location-tiles-v1") {
            let legacy = format!(
                "t{:02}_{}_s{:.4}_sh{:.4}_{}_q{}.jpg",
                tile.index,
                tile.palette,
                tile.geometry.scale,
                tile.geometry.shift_frac,
                tile.level.name(),
                tile.quality
            );
            assert_eq!(tile.output, Path::new("4242").join(&legacy));
        }
    }

    /// Three regimes, three sets of names. Before the regime segment existed
    /// these were the same thirty-two files, so an ss1 build aimed at the ss2
    /// cache skipped every one of them and exited 0 over pictures that were ss2.
    #[test]
    fn a_second_regime_cannot_land_on_the_first_ones_files() {
        let row = PlanRow {
            schema: 1,
            location_id: 4242,
            family: FamilySpec::Mandelbrot,
            viewport: Default::default(),
            maxiter: Some(1000),
        };
        let regimes = [([640u32, 360u32], 2u32), ([640, 360], 1), ([384, 216], 1)];
        let mut all: Vec<PathBuf> = Vec::new();
        for (tile, supersample) in regimes {
            let recipe = Recipe {
                tile,
                field_supersample: supersample,
                ..recipe()
            };
            let geom = FieldGeom::build(&recipe, 3.0);
            all.extend(
                plan_tiles(&recipe, &geom, &row, "location-tiles-v1")
                    .into_iter()
                    .map(|tile| tile.output),
            );
        }
        let total = all.len();
        assert_eq!(total, 3 * 32);
        all.sort();
        all.dedup();
        assert_eq!(all.len(), total, "two regimes share a file name");
    }

    /// Adding an axis must not reshuffle the others, which is what the disjoint
    /// slot namespaces buy. The quality draw and the palette draw of one tile
    /// come from different streams, so they cannot be correlated.
    #[test]
    fn the_draws_of_one_tile_come_from_separate_streams() {
        let seed = location_seed("a-tag", 3);
        let slots = [SLOT_GEOMETRY, SLOT_PALETTE, SLOT_LEVEL, SLOT_QUALITY];
        let mut seen: Vec<u64> = (0..32u64)
            .flat_map(|tile| {
                slots
                    .iter()
                    .map(move |base| rng::sub_seed(seed, base + tile))
            })
            .collect();
        let total = seen.len();
        seen.sort_unstable();
        seen.dedup();
        assert_eq!(seen.len(), total, "two draw slots share a stream");
    }
}
