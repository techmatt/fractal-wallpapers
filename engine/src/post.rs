//! The **post stage** of a style: passes over the whole composited frame.
//!
//! A style's layers are per-sample ([`crate::style`]): each is a function of one
//! sample's channels, so a window of the frame composites alone. A post pass is the
//! other kind of step, the one a layer may never be: it reads **neighbours**. It runs
//! once the stack is composited and before the tone is measured, over the frame's
//! linear samples and the channels the escape loop left beside them (the distance to
//! the set, whether the orbit escaped, a height), so a pass can follow the fractal
//! rather than the pixels, and the style's tone is held on the picture the pass made.
//!
//! **A pass is a pure function of the frame's buffers**, in sample order, so
//! `style-wasm/` draws it to the same picture as the native engine; and because it
//! needs the whole frame, a style with a post stage is drawn whole
//! ([`crate::style::paint`]), never in tiles. Every size a pass takes is a fraction of
//! the frame's width, so a draft and the full-size frame are the same picture.
//!
//! There are three passes. The **paper** ([`Paper`]) cuts a height into a few flat
//! sheets on its rank over the frame, each one colour with the fractal's own level
//! line for its edge, tears the edges as a dry brush does (`ragged`) and lays each
//! sheet's `shadow` on those under it. The **rays** ([`Rays`]) cast straight beams
//! from the frame's brightest samples, as spokes or as shafts from a point. The
//! **mosaic** is a recursive tiling whose cells split where the set is, each cell a
//! flat facet of the picture under it.
//!
//! ```text
//! lattice    equilateral triangles, each split in four by its edges' midpoints; the
//!            same lattice's rhombi (`rhombi`), split in four as slanted quads; or
//!            (`spiral`) quads of a log-polar lattice about a point, split in four
//! split      a cell splits while the set is within `reach` cell edges of it (or it
//!            straddles the set's edge, or the picture inside varies by `detail`),
//!            down to `smallest`: big, calm cells far from the set, ever finer at it
//! fill       `flat`: the mean of the picture under the facet; `turned`: the picture
//!            itself, turned about the facet's middle and slipped by `shift`
//! shade      `relief`: each facet tilted to the plane fitted through a height under
//!            it; `fold`: each facet a low pyramid, one face per edge; both lit from
//!            `azimuth`
//! inlay      each facet's own children, and theirs, drawn into it as faint lighter
//!            and darker cells: nested detail where the tiling itself is calm
//! seam       a thin line along every facet's rim
//! opacity    how much of the mosaic is laid over the picture it was made from
//! ```

use rayon::prelude::*;
use serde::{Deserialize, Serialize};

use crate::coloring::Transform;
use crate::colormap::Colormap;
use crate::field::FieldSpec;
use crate::style::{Paint, Source};

/// One pass of a style's post stage.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum Pass {
    Mosaic(Mosaic),
    Paper(Paper),
    Rays(Rays),
}

impl Pass {
    /// The channel the pass reads beside the picture, when it names one.
    pub fn height(&self) -> Option<Source> {
        match self {
            Pass::Mosaic(mosaic) => mosaic.height,
            Pass::Paper(paper) => Some(paper.height),
            Pass::Rays(_) => None,
        }
    }
}

/// Whether a pass's height is a channel the frame's own loop carries: a plain field.
fn plain(height: &Source) -> bool {
    height.field.is_some()
        && height.view.is_none()
        && height.inside.is_none()
        && height.radial.is_none()
        && height.bubble.is_none()
        && height.lines.is_none()
        && height.stroke.is_none()
}

/// What a facet of the mosaic is filled with.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Fill {
    /// The mean of the picture under the facet: one flat colour.
    #[default]
    Flat,
    /// The picture itself, turned about the facet's middle.
    Turned,
}

/// The log-polar lattice: `arms` square-ish quads round each ring about `center`.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct Spiral {
    /// The point the rings shrink to, in fractions of the frame from its top-left.
    pub center: [f64; 2],
    /// Quads round one ring.
    pub arms: u32,
    /// How many quads each ring is turned past the one outside it: the rings' seams
    /// line up at 0 and run as spiral arms otherwise.
    pub twist: f64,
}

impl Default for Spiral {
    fn default() -> Spiral {
        Spiral {
            center: [0.5, 0.5],
            arms: 12,
            twist: 0.0,
        }
    }
}

/// The cells a facet would split into, drawn into it without splitting it.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Inlay {
    /// How many times the facet is split for the pattern (at most [`INLAID`]), never to
    /// cells under the mosaic's `smallest`.
    #[serde(default = "two")]
    pub levels: u32,
    /// How far a cell is lightened or darkened at each level, a share of its colour.
    pub amount: f64,
}

fn two() -> u32 {
    2
}

/// The deepest an inlay goes.
pub const INLAID: u32 = 6;

/// A line along every facet's rim.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Seam {
    /// The rim's width in frame widths, never more than [`SEAM_SHARE`] of the facet's
    /// edge, so a small facet keeps its face.
    pub width: f64,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub color: Option<Paint>,
    #[serde(default = "one")]
    pub opacity: f64,
}

fn one() -> f64 {
    1.0
}

/// The steepest a facet tilts (rise over run), however fast the height under it
/// climbs: at the default elevation of 45 a face turned from the light is dimmed to
/// about a third (under about 31 degrees it can reach black).
pub const STEEPEST: f64 = 0.6;

/// The most of a facet's edge its seam takes.
pub const SEAM_SHARE: f64 = 0.08;

/// The most `levels` a mosaic may ask for (a spiral's quads over `largest` split
/// further, down to it, first), and the most cells it may hold: a bound on memory
/// (about 150 bytes a cell) however a style is written. [`SMALLEST_LARGEST`] and
/// [`SMALLEST`] bound the lattice itself, so the count is small before it is taken.
pub const DEEPEST: u32 = 10;
pub const MOST_CELLS: usize = 6_000_000;
pub const SMALLEST_LARGEST: f64 = 1.0 / 256.0;
pub const SMALLEST: f64 = 1e-5;

/// The mosaic pass. Every length is a fraction of the frame's width.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct Mosaic {
    /// The log-polar quad lattice; absent, the triangle lattice.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub spiral: Option<Spiral>,
    /// The cells are the triangle lattice's rhombi, two triangles each, split in four
    /// as slanted quads: two families of seams where the triangles have three.
    #[serde(skip_serializing_if = "std::ops::Not::not")]
    pub rhombi: bool,
    /// Triangles and rhombi: the lattice turned by this many degrees.
    pub tilt: f64,
    /// The edge of the largest cell: the triangle lattice's own, and the size above
    /// which a spiral's quad always splits.
    pub largest: f64,
    /// No cell's edge is below this: the floor the splitting stops at.
    pub smallest: f64,
    /// The most times a cell of the largest size splits.
    pub levels: u32,
    /// A cell splits while the set is within this many of its edges of it; 0 leaves
    /// only the cells the set's edge crosses.
    pub reach: f64,
    /// A cell also splits while the picture inside it varies by more than this (the
    /// standard deviation of its root luminance); 0 turns the rule off.
    pub detail: f64,
    pub fill: Fill,
    /// `turned`: degrees each facet's view is turned, times a number per facet: a
    /// triangle's or rhombus's one of −1, 0, 1; a spiral quad's column round its ring, at
    /// its middle (so 360 over the `arms` turns each view with the ring).
    pub turn: f64,
    /// `turned`: how far each facet's view is slipped, in facet edges, each its own way:
    /// neighbours then show the picture broken along their seam.
    pub shift: f64,
    /// The facet's tilt per unit of height across one of its edges, the plane fitted
    /// to `height` under it; 0 leaves the facets level.
    pub relief: f64,
    /// The height `relief` reads: a plain field channel, stretched over the frame.
    /// Absent: the picture's own root luminance.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub height: Option<Source>,
    /// The slope of each facet's faces as a low pyramid, one face per edge.
    pub fold: f64,
    /// Where the light on `relief` and `fold` comes from, degrees anticlockwise.
    pub azimuth: f64,
    pub elevation: f64,
    /// How much of the mosaic is laid over the picture beneath, in `[0, 1]`: under 1 the
    /// facets are translucent plates and the stack's own detail shows through them.
    pub opacity: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub inlay: Option<Inlay>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub seam: Option<Seam>,
}

impl Default for Mosaic {
    fn default() -> Mosaic {
        Mosaic {
            spiral: None,
            rhombi: false,
            tilt: 0.0,
            largest: 0.25,
            smallest: 0.004,
            levels: 6,
            reach: 1.0,
            detail: 0.0,
            fill: Fill::Flat,
            turn: 0.0,
            shift: 0.0,
            relief: 0.0,
            height: None,
            fold: 0.0,
            azimuth: 135.0,
            elevation: 45.0,
            opacity: 1.0,
            inlay: None,
            seam: None,
        }
    }
}

impl Pass {
    /// Refuse a pass that would draw something other than what it says.
    pub fn validate(&self) -> Result<(), String> {
        match self {
            Pass::Mosaic(mosaic) => mosaic.validate(),
            Pass::Paper(paper) => paper.validate(),
            Pass::Rays(rays) => rays.validate(),
        }
    }
}

impl Mosaic {
    fn validate(&self) -> Result<(), String> {
        let finite = [
            self.tilt,
            self.reach,
            self.detail,
            self.turn,
            self.shift,
            self.relief,
            self.fold,
            self.azimuth,
            self.elevation,
        ];
        if finite.iter().any(|value| !value.is_finite()) {
            return Err("mosaic: every member is a finite number".into());
        }
        if !(self.smallest >= SMALLEST && self.smallest <= self.largest && self.largest <= 4.0) {
            return Err(format!(
                "mosaic: {SMALLEST} <= smallest <= largest <= 4 frame widths, got {} and {}",
                self.smallest, self.largest
            ));
        }
        if self.largest < SMALLEST_LARGEST {
            return Err(format!(
                "mosaic: largest is at least 1/256 of the frame, got {}",
                self.largest
            ));
        }
        if self.levels > DEEPEST {
            return Err(format!("mosaic: levels is at most {DEEPEST}"));
        }
        if self.reach < 0.0 || self.detail < 0.0 || self.relief < 0.0 || self.fold < 0.0 {
            return Err("mosaic: reach, detail, relief and fold are not negative".into());
        }
        if !(0.0..=4.0).contains(&self.shift) {
            return Err("mosaic: shift is 0 to 4 facet edges".into());
        }
        if self.rhombi && self.spiral.is_some() {
            return Err("mosaic: rhombi are the triangle lattice's, not a spiral's".into());
        }
        if !(0.0..=1.0).contains(&self.opacity) {
            return Err("mosaic: opacity is in [0, 1]".into());
        }
        if !(self.elevation > 0.0 && self.elevation <= 90.0) {
            return Err("mosaic: elevation is in (0, 90] degrees".into());
        }
        if let Some(spiral) = self.spiral {
            if !(3..=360).contains(&spiral.arms) {
                return Err("mosaic: a spiral has 3 to 360 arms".into());
            }
            if !(spiral.twist.is_finite() && spiral.center.iter().all(|c| (-4.0..=5.0).contains(c)))
            {
                return Err(
                    "mosaic: a spiral's twist is finite and its center within 4 frames of the frame"
                        .into(),
                );
            }
        }
        if let Some(inlay) = self.inlay {
            if inlay.levels > INLAID || !(0.0..1.0).contains(&inlay.amount) {
                return Err(format!(
                    "mosaic: an inlay has at most {INLAID} levels and an amount in [0, 1)"
                ));
            }
        }
        if let Some(seam) = &self.seam {
            if !(seam.width > 0.0 && seam.width.is_finite()) {
                return Err("mosaic: a seam's width is a positive length".into());
            }
            if !(0.0..=1.0).contains(&seam.opacity) {
                return Err("mosaic: a seam's opacity is in [0, 1]".into());
            }
            if let Some(paint) = &seam.color {
                paint.validate("mosaic seam")?;
            }
        }
        if self.height.is_some_and(|height| !plain(&height)) {
            return Err("mosaic: height is a plain field channel, with no view".into());
        }
        Ok(())
    }
}

/// The frame a pass reads, in samples, row-major.
pub struct Frame<'a> {
    pub width: usize,
    pub height: usize,
    /// The composited stack, linear light.
    pub linear: &'a [[f64; 3]],
    /// Whether each sample's orbit escaped.
    pub escaped: &'a [bool],
    /// The distance to the set in frame widths; not finite where there is none.
    pub near: &'a [f32],
    /// The pass's height, not finite where there is none. A mosaic's is in `[0, 1]`,
    /// or empty for the picture's own; a paper's is the raw value, highest on top, and
    /// not finite wherever the orbit never escaped.
    pub heights: &'a [f32],
}

/// What the samples under one cell add up to.
#[derive(Clone, Copy)]
struct Cell {
    count: f64,
    rgb: [f64; 3],
    /// Root luminance and its square, for `detail`.
    light: f64,
    light_squared: f64,
    near: f32,
    inside: u32,
    outside: u32,
    /// The plane fit's moments over the samples that have a height.
    fitted: f64,
    moments: [f64; 8],
}

impl Cell {
    const EMPTY: Cell = Cell {
        count: 0.0,
        rgb: [0.0; 3],
        light: 0.0,
        light_squared: 0.0,
        near: f32::INFINITY,
        inside: 0,
        outside: 0,
        fitted: 0.0,
        moments: [0.0; 8],
    };

    fn add(&mut self, other: &Cell) {
        self.count += other.count;
        for k in 0..3 {
            self.rgb[k] += other.rgb[k];
        }
        self.light += other.light;
        self.light_squared += other.light_squared;
        self.near = self.near.min(other.near);
        self.inside += other.inside;
        self.outside += other.outside;
        self.fitted += other.fitted;
        for k in 0..8 {
            self.moments[k] += other.moments[k];
        }
    }

    /// The gradient of the plane fitted to the heights, per frame width.
    fn slope(&self) -> [f64; 2] {
        let n = self.fitted;
        if n < 3.0 {
            return [0.0; 2];
        }
        let [h, hx, hy, x, y, xx, xy, yy] = self.moments;
        let (mx, my, mh) = (x / n, y / n, h / n);
        let (sxx, sxy, syy) = (xx - n * mx * mx, xy - n * mx * my, yy - n * my * my);
        let (sxh, syh) = (hx - n * mx * mh, hy - n * my * mh);
        let det = sxx * syy - sxy * sxy;
        // Samples along one row or column leave a spread that is rounding noise.
        let least = 1e-12 * (xx + yy);
        if !(sxx > least && syy > least && det > 1e-9 * sxx * syy) {
            return [0.0; 2];
        }
        [(sxh * syy - syh * sxy) / det, (syh * sxx - sxh * sxy) / det]
    }
}

/// One cell of the lattice's coarsest level, and where its tree is kept.
#[derive(Clone, Copy)]
struct Root {
    /// Its edge in frame widths.
    edge: f64,
    /// How many times it may split.
    levels: u32,
    /// Where its level 0 sits among the cells; level `l` follows at `(4^l − 1) / 3`.
    offset: usize,
}

fn level_offset(level: u32) -> usize {
    ((1usize << (2 * level)) - 1) / 3
}

/// The lattice: which root a frame point is in, and where in it.
enum Lattice {
    Triangles {
        /// Unit vectors of the turned lattice.
        cos: f64,
        sin: f64,
        side: f64,
        low: [i64; 2],
        size: [i64; 2],
    },
    /// The triangle lattice's own cells before their diagonal: `(s, t)` along its axes.
    Rhombi {
        cos: f64,
        sin: f64,
        side: f64,
        low: [i64; 2],
        size: [i64; 2],
    },
    Spiral {
        center: [f64; 2],
        arms: f64,
        twist: f64,
        /// One ring's step in `ln r`: a quad as wide as it is deep.
        step: f64,
        low: i64,
        rings: i64,
    },
}

/// A point inside one root: barycentric `(a, b, c)` of a triangle, or `(s, t, _)` of a
/// quad, each in `[0, 1]`.
type Local = [f64; 3];

const SQRT3_2: f64 = 0.866_025_403_784_438_6;

impl Lattice {
    /// The lattice over a frame `aspect` (height over width) tall.
    fn over(mosaic: &Mosaic, aspect: f64) -> Lattice {
        let corners = [
            [-0.5, -0.5 * aspect],
            [0.5, -0.5 * aspect],
            [-0.5, 0.5 * aspect],
            [0.5, 0.5 * aspect],
        ];
        match mosaic.spiral {
            None => {
                let (sin, cos) = mosaic.tilt.to_radians().sin_cos();
                let side = mosaic.largest;
                let lattice = Lattice::Triangles {
                    cos,
                    sin,
                    side,
                    low: [0; 2],
                    size: [1; 2],
                };
                let mut bounds = [[i64::MAX, i64::MIN]; 2];
                for corner in corners {
                    let [p, q] = lattice.skewed(corner);
                    for (bound, value) in bounds.iter_mut().zip([p, q]) {
                        // The coordinates are affine, so the corners bound the frame.
                        bound[0] = bound[0].min(value.floor() as i64);
                        bound[1] = bound[1].max(value.floor() as i64);
                    }
                }
                let low = [bounds[0][0], bounds[1][0]];
                let size = [
                    bounds[0][1] - bounds[0][0] + 1,
                    bounds[1][1] - bounds[1][0] + 1,
                ];
                if mosaic.rhombi {
                    Lattice::Rhombi {
                        cos,
                        sin,
                        side,
                        low,
                        size,
                    }
                } else {
                    Lattice::Triangles {
                        cos,
                        sin,
                        side,
                        low,
                        size,
                    }
                }
            }
            Some(spiral) => {
                let arms = spiral.arms as f64;
                let step = std::f64::consts::TAU / arms;
                let center = [spiral.center[0] - 0.5, (spiral.center[1] - 0.5) * aspect];
                let farthest = corners
                    .iter()
                    .map(|c| (c[0] - center[0]).hypot(c[1] - center[1]))
                    .fold(0.0, f64::max);
                // The innermost ring is the first whose quads are under `smallest`.
                let innermost = mosaic.smallest / step;
                let low = (innermost.ln() / step).floor() as i64;
                let high = (farthest.max(innermost).ln() / step).floor() as i64 + 1;
                Lattice::Spiral {
                    center,
                    arms,
                    twist: spiral.twist,
                    step,
                    low,
                    rings: (high - low + 1).max(1),
                }
            }
        }
    }

    /// A frame point in the triangle lattice's own skewed coordinates.
    fn skewed(&self, [x, y]: [f64; 2]) -> [f64; 2] {
        let (Lattice::Triangles { cos, sin, side, .. } | Lattice::Rhombi { cos, sin, side, .. }) =
            self
        else {
            return [x, y];
        };
        let (u, v) = (x * cos + y * sin, y * cos - x * sin);
        let q = v / (side * SQRT3_2);
        [u / side - 0.5 * q, q]
    }

    /// The frame point at the triangle lattice's skewed coordinates `(p, q)`.
    fn placed(&self, p: f64, q: f64) -> [f64; 2] {
        let (Lattice::Triangles { cos, sin, side, .. } | Lattice::Rhombi { cos, sin, side, .. }) =
            self
        else {
            return [p, q];
        };
        let (u, v) = ((p + 0.5 * q) * side, q * side * SQRT3_2);
        [u * cos - v * sin, u * sin + v * cos]
    }

    /// A spiral's `(column, ring)` coordinates of a frame point.
    fn wound(&self, [x, y]: [f64; 2]) -> [f64; 2] {
        let Lattice::Spiral {
            center,
            arms,
            twist,
            step,
            ..
        } = self
        else {
            return [x, y];
        };
        let (dx, dy) = (x - center[0], y - center[1]);
        let ring = dx.hypot(dy).max(1e-300).ln() / step;
        let turn = dy.atan2(dx) / std::f64::consts::TAU;
        [turn * arms + twist * ring, ring]
    }

    /// A triangle root's corners in the frame, in the order its barycentrics count.
    fn triangle(&self, root_index: usize) -> [[f64; 2]; 3] {
        let Lattice::Triangles { low, size, .. } = *self else {
            return [[0.0; 2]; 3];
        };
        let cell = root_index / 2;
        let (i0, j0) = (
            (cell as i64 % size[0] + low[0]) as f64,
            (cell as i64 / size[0] + low[1]) as f64,
        );
        let place = |p: f64, q: f64| self.placed(p, q);
        if root_index % 2 == 0 {
            [place(i0, j0), place(i0 + 1.0, j0), place(i0, j0 + 1.0)]
        } else {
            [
                place(i0 + 1.0, j0 + 1.0),
                place(i0, j0 + 1.0),
                place(i0 + 1.0, j0),
            ]
        }
    }

    /// Each root's edge and how often it may split. A triangle wholly off the frame
    /// (the lattice is a parallelogram round it) holds no sample and never splits.
    fn roots(&self, mosaic: &Mosaic, aspect: f64) -> Vec<(f64, u32)> {
        // How often a cell of `edge` may halve: down to the largest size for nothing,
        // then `levels` times, never under `smallest`.
        let levels_of = |edge: f64| {
            let mut levels = 0;
            let mut counted = 0;
            let mut edge = edge;
            // Two past the deepest is already over the cell budget, and still a
            // count a 32-bit module holds.
            while levels < DEEPEST + 2 && edge * 0.5 >= mosaic.smallest {
                if edge <= mosaic.largest * (1.0 + 1e-9) {
                    if counted == mosaic.levels {
                        break;
                    }
                    counted += 1;
                }
                edge *= 0.5;
                levels += 1;
            }
            levels
        };
        match *self {
            Lattice::Triangles { side, size, .. } => {
                let levels = levels_of(side);
                (0..(size[0] * size[1] * 2) as usize)
                    .map(|root_index| {
                        let corners = self.triangle(root_index);
                        let off = |axis: usize, half: f64| {
                            corners.iter().all(|corner| corner[axis] < -half)
                                || corners.iter().all(|corner| corner[axis] > half)
                        };
                        let outside = off(0, 0.5) || off(1, 0.5 * aspect);
                        (side, if outside { 0 } else { levels })
                    })
                    .collect()
            }
            Lattice::Rhombi {
                side, low, size, ..
            } => {
                let levels = levels_of(side);
                (0..size[0] * size[1])
                    .map(|cell| {
                        let (i0, j0) = (
                            (cell % size[0] + low[0]) as f64,
                            (cell / size[0] + low[1]) as f64,
                        );
                        let corners = [
                            self.placed(i0, j0),
                            self.placed(i0 + 1.0, j0),
                            self.placed(i0, j0 + 1.0),
                            self.placed(i0 + 1.0, j0 + 1.0),
                        ];
                        let off = |axis: usize, half: f64| {
                            corners.iter().all(|corner| corner[axis] < -half)
                                || corners.iter().all(|corner| corner[axis] > half)
                        };
                        let outside = off(0, 0.5) || off(1, 0.5 * aspect);
                        (side, if outside { 0 } else { levels })
                    })
                    .collect()
            }
            Lattice::Spiral {
                arms,
                step,
                low,
                rings,
                ..
            } => (0..rings)
                .flat_map(|ring| {
                    let edge = (((low + ring) as f64 + 0.5) * step).exp() * step;
                    std::iter::repeat_n((edge, levels_of(edge)), arms as usize)
                })
                .collect(),
        }
    }

    /// The root a frame point is in, and the point's place in it.
    fn locate(&self, point: [f64; 2]) -> (usize, Local) {
        match *self {
            Lattice::Triangles { low, size, .. } | Lattice::Rhombi { low, size, .. } => {
                let [p, q] = self.skewed(point);
                let i = (p.floor() as i64).clamp(low[0], low[0] + size[0] - 1);
                let j = (q.floor() as i64).clamp(low[1], low[1] + size[1] - 1);
                let (fp, fq) = (
                    (p - i as f64).clamp(0.0, 1.0),
                    (q - j as f64).clamp(0.0, 1.0),
                );
                let cell = ((j - low[1]) * size[0] + (i - low[0])) as usize;
                if matches!(self, Lattice::Rhombi { .. }) {
                    return (cell, [fp, fq, 0.0]);
                }
                let cell = cell * 2;
                if fp + fq < 1.0 {
                    (cell, [1.0 - fp - fq, fp, fq])
                } else {
                    (cell + 1, [fp + fq - 1.0, 1.0 - fp, 1.0 - fq])
                }
            }
            Lattice::Spiral {
                arms, low, rings, ..
            } => {
                let [a, b] = self.wound(point);
                let ring = (b.floor() as i64).clamp(low, low + rings - 1);
                let column = a.floor().rem_euclid(arms);
                let s = (a - a.floor()).clamp(0.0, 1.0);
                let t = (b - ring as f64).clamp(0.0, 1.0);
                (
                    (ring - low) as usize * arms as usize + column as usize,
                    [s, t, 0.0],
                )
            }
        }
    }

    /// Which of a cell's four children a point is in, and its place in that child.
    fn child(&self, [a, b, c]: Local) -> (usize, Local) {
        match self {
            Lattice::Triangles { .. } => {
                if a >= 0.5 {
                    (0, [2.0 * a - 1.0, 2.0 * b, 2.0 * c])
                } else if b >= 0.5 {
                    (1, [2.0 * a, 2.0 * b - 1.0, 2.0 * c])
                } else if c >= 0.5 {
                    (2, [2.0 * a, 2.0 * b, 2.0 * c - 1.0])
                } else {
                    (3, [1.0 - 2.0 * a, 1.0 - 2.0 * b, 1.0 - 2.0 * c])
                }
            }
            Lattice::Rhombi { .. } | Lattice::Spiral { .. } => {
                let (right, up) = (a >= 0.5, b >= 0.5);
                (
                    right as usize + 2 * up as usize,
                    [
                        2.0 * a - if right { 1.0 } else { 0.0 },
                        2.0 * b - if up { 1.0 } else { 0.0 },
                        0.0,
                    ],
                )
            }
        }
    }
}

/// A sample's frame point in frame widths from the frame's middle.
fn point_of(col: usize, row: usize, width: usize, height: usize) -> [f64; 2] {
    let w = width as f64;
    [
        (col as f64 + 0.5 - 0.5 * w) / w,
        (row as f64 + 0.5 - 0.5 * height as f64) / w,
    ]
}

fn root_luminance(rgb: [f64; 3]) -> f64 {
    (0.2126 * rgb[0].clamp(0.0, 1.0)
        + 0.7152 * rgb[1].clamp(0.0, 1.0)
        + 0.0722 * rgb[2].clamp(0.0, 1.0))
    .sqrt()
}

/// What a facet's slip is hashed under, past every level a turn or an inlay uses.
const SLIP: u32 = 64;

/// A whole number per facet, the same on every machine.
fn hashed(root: usize, level: u32, node: u64) -> u64 {
    let mut x = (root as u64)
        .wrapping_mul(0x9E37_79B9_7F4A_7C15)
        .wrapping_add((level as u64) << 56)
        .wrapping_add(node);
    x ^= x >> 30;
    x = x.wrapping_mul(0xBF58_476D_1CE4_E5B9);
    x ^= x >> 27;
    x = x.wrapping_mul(0x94D0_49BB_1331_11EB);
    x ^ (x >> 31)
}

/// The sample a frame point lands on, mirrored back in at the frame's edges.
fn sample_at(point: [f64; 2], width: usize, height: usize) -> usize {
    let w = width as f64;
    let mirrored = |value: f64, size: usize| {
        let period = 2.0 * size as f64;
        let folded = value.rem_euclid(period);
        let inside = if folded >= size as f64 {
            period - folded
        } else {
            folded
        };
        (inside.floor() as usize).min(size - 1)
    };
    let col = mirrored(point[0] * w + 0.5 * w, width);
    let row = mirrored(point[1] * w + 0.5 * height as f64, height);
    row * width + col
}

/// Lay the mosaic over `frame`: its linear samples, facet by facet.
pub fn mosaic(
    mosaic: &Mosaic,
    frame: &Frame,
    colormap: &Colormap,
) -> Result<Vec<[f64; 3]>, String> {
    let (width, height) = (frame.width, frame.height);
    if width == 0 || height == 0 {
        return Ok(frame.linear.to_vec());
    }
    let aspect = height as f64 / width as f64;
    let lattice = Lattice::over(mosaic, aspect);
    let mut total = 0usize;
    let roots: Vec<Root> = lattice
        .roots(mosaic, aspect)
        .into_iter()
        .map(|(edge, levels)| {
            let offset = total;
            total = total.saturating_add(level_offset(levels + 1));
            Root {
                edge,
                levels,
                offset,
            }
        })
        .collect();
    if total > MOST_CELLS {
        return Err(format!(
            "mosaic: {total} cells is over the {MOST_CELLS} it may hold; raise smallest or largest, or lower levels"
        ));
    }

    // Each root's tree is built, split and painted in turn, so one root's cells are
    // held at a time (the whole frame's trees at once ran to about 190 MB at 1280x800
    // ss2), and each root's samples are listed in sample order, so its sums are the
    // ones a single tree over the frame held, bit for bit.
    let mut members: Vec<Vec<u32>> = vec![Vec::new(); roots.len()];
    for i in 0..width * height {
        let (root_index, _) = lattice.locate(point_of(i % width, i / width, width, height));
        let i = u32::try_from(i).map_err(|_| format!("mosaic: {width}x{height} samples"))?;
        members[root_index].push(i);
    }

    let (azimuth, elevation) = (mosaic.azimuth.to_radians(), mosaic.elevation.to_radians());
    // Rows run down the frame, so an anticlockwise azimuth has its `y` turned over.
    let to_light = [
        elevation.cos() * azimuth.cos(),
        -elevation.cos() * azimuth.sin(),
        elevation.sin(),
    ];
    let lit = mosaic.relief > 0.0 || mosaic.fold > 0.0;
    let seam = mosaic.seam.as_ref().map(|seam| {
        let color = seam
            .color
            .as_ref()
            .map_or([0.0; 3], |paint| paint.linear(colormap));
        (seam.width, color, seam.opacity)
    });
    let turn = mosaic.turn.to_radians();

    let mut painted = vec![[0.0; 3]; width * height];
    for (root_index, samples) in members.iter().enumerate() {
        // The root's tree alone: its level 0 at the start.
        let root = Root {
            offset: 0,
            ..roots[root_index]
        };
        // Every sample into its finest cell, in sample order (so the sums are the same
        // on every machine), then each level summed into the one above.
        let mut cells = vec![Cell::EMPTY; level_offset(root.levels + 1)];
        for &i in samples {
            let i = i as usize;
            let (col, row) = (i % width, i / width);
            let point = point_of(col, row, width, height);
            let (_, mut local) = lattice.locate(point);
            let mut node = 0usize;
            for _ in 0..root.levels {
                let (digit, inner) = lattice.child(local);
                node = node * 4 + digit;
                local = inner;
            }
            let cell = &mut cells[root.offset + level_offset(root.levels) + node];
            let rgb = frame.linear[i];
            let light = root_luminance(rgb);
            cell.count += 1.0;
            for k in 0..3 {
                cell.rgb[k] += rgb[k];
            }
            cell.light += light;
            cell.light_squared += light * light;
            if frame.escaped[i] {
                cell.outside += 1;
                let near = frame.near[i];
                if near.is_finite() {
                    cell.near = cell.near.min(near);
                }
            } else {
                cell.inside += 1;
            }
            let h = if frame.heights.is_empty() {
                light
            } else {
                frame.heights[i] as f64
            };
            if h.is_finite() {
                let [x, y] = point;
                cell.fitted += 1.0;
                for (moment, value) in
                    cell.moments
                        .iter_mut()
                        .zip([h, h * x, h * y, x, y, x * x, x * y, y * y])
                {
                    *moment += value;
                }
            }
        }
        for level in (0..root.levels).rev() {
            let (parents, children) = (
                root.offset + level_offset(level),
                root.offset + level_offset(level + 1),
            );
            for node in 0..1usize << (2 * level) {
                let mut sum = Cell::EMPTY;
                for digit in 0..4 {
                    sum.add(&cells[children + node * 4 + digit]);
                }
                cells[parents + node] = sum;
            }
        }

        // Which cells split: every one over the largest size, then where the set is.
        let mut split = vec![false; cells.len()];
        for level in 0..root.levels {
            let edge = root.edge / (1u64 << level) as f64;
            let at = root.offset + level_offset(level);
            for node in 0..1usize << (2 * level) {
                let cell = &cells[at + node];
                if cell.count == 0.0 {
                    continue;
                }
                let spread = (cell.light_squared / cell.count - (cell.light / cell.count).powi(2))
                    .max(0.0)
                    .sqrt();
                split[at + node] = edge > mosaic.largest * (1.0 + 1e-9)
                    || (cell.inside > 0 && cell.outside > 0)
                    || (cell.near as f64) < mosaic.reach * edge
                    || (mosaic.detail > 0.0 && spread > mosaic.detail);
            }
        }

        let drawn: Vec<[f64; 3]> = samples
            .par_iter()
            .map(|&i| {
                let i = i as usize;
                let (col, row) = (i % width, i / width);
                let point = point_of(col, row, width, height);
                let (_, mut local) = lattice.locate(point);
                let (mut node, mut level) = (0usize, 0u32);
                // The facet's corners (a triangle's) or its low corner and size (a quad's),
                // carried down the tree with the point.
                let mut corners = match lattice {
                    Lattice::Triangles { .. } => lattice.triangle(root_index),
                    Lattice::Rhombi { low, size, .. } => {
                        let cell = root_index as i64;
                        [
                            [
                                (cell % size[0] + low[0]) as f64,
                                (cell / size[0] + low[1]) as f64,
                            ],
                            [1.0, 0.0],
                            [0.0; 2],
                        ]
                    }
                    Lattice::Spiral { arms, low, .. } => {
                        let arms = arms as usize;
                        [
                            [
                                (root_index % arms) as f64,
                                (root_index / arms) as f64 + low as f64,
                            ],
                            [1.0, 0.0],
                            [0.0; 2],
                        ]
                    }
                };
                while level < root.levels && split[root.offset + level_offset(level) + node] {
                    let (digit, inner) = lattice.child(local);
                    node = node * 4 + digit;
                    local = inner;
                    level += 1;
                    corners = match lattice {
                        Lattice::Triangles { .. } => {
                            let [a, b, c] = corners;
                            let mid = |p: [f64; 2], q: [f64; 2]| {
                                [0.5 * (p[0] + q[0]), 0.5 * (p[1] + q[1])]
                            };
                            match digit {
                                0 => [a, mid(a, b), mid(a, c)],
                                1 => [mid(a, b), b, mid(b, c)],
                                2 => [mid(a, c), mid(b, c), c],
                                _ => [mid(b, c), mid(a, c), mid(a, b)],
                            }
                        }
                        Lattice::Rhombi { .. } | Lattice::Spiral { .. } => {
                            let half = 0.5 * corners[1][0];
                            [
                                [
                                    corners[0][0] + half * (digit % 2) as f64,
                                    corners[0][1] + half * (digit / 2) as f64,
                                ],
                                [half, 0.0],
                                [0.0; 2],
                            ]
                        }
                    };
                }
                let cell = &cells[root.offset + level_offset(level) + node];
                let edge = root.edge / (1u64 << level) as f64;

                // The facet's middle, how far the sample is from its rim, the way out
                // through the nearest edge, and the number its turn is counted in.
                let (middle, rim, outward, count) = match lattice {
                    Lattice::Triangles { .. } => {
                        let [a, b, c] = corners;
                        let middle = [(a[0] + b[0] + c[0]) / 3.0, (a[1] + b[1] + c[1]) / 3.0];
                        let nearest = if local[0] <= local[1] && local[0] <= local[2] {
                            0
                        } else if local[1] <= local[2] {
                            1
                        } else {
                            2
                        };
                        let away = [
                            middle[0] - corners[nearest][0],
                            middle[1] - corners[nearest][1],
                        ];
                        let length = away[0].hypot(away[1]).max(1e-300);
                        (
                            middle,
                            local[nearest] * edge * SQRT3_2,
                            [away[0] / length, away[1] / length],
                            (hashed(root_index, level, node as u64) % 3) as f64 - 1.0,
                        )
                    }
                    Lattice::Rhombi { cos, sin, .. } => {
                        let size = corners[1][0];
                        let middle =
                            lattice.placed(corners[0][0] + 0.5 * size, corners[0][1] + 0.5 * size);
                        // Out through a side: square to the axis that side runs along.
                        let (along, across) = (
                            [cos, sin],
                            [0.5 * cos - SQRT3_2 * sin, 0.5 * sin + SQRT3_2 * cos],
                        );
                        let (from_s, from_t) = ([across[1], -across[0]], [-along[1], along[0]]);
                        let [s, t, _] = local;
                        let sides = [
                            (s, [-from_s[0], -from_s[1]]),
                            (1.0 - s, from_s),
                            (t, [-from_t[0], -from_t[1]]),
                            (1.0 - t, from_t),
                        ];
                        let (share, outward) =
                            sides
                                .into_iter()
                                .fold((f64::INFINITY, [0.0; 2]), |best, side| {
                                    if side.0 < best.0 { side } else { best }
                                });
                        (
                            middle,
                            share * edge * SQRT3_2,
                            outward,
                            (hashed(root_index, level, node as u64) % 3) as f64 - 1.0,
                        )
                    }
                    Lattice::Spiral {
                        center,
                        arms,
                        twist,
                        step,
                        low,
                        ..
                    } => {
                        let size = corners[1][0];
                        let (a, b) = (corners[0][0] + 0.5 * size, corners[0][1] + 0.5 * size);
                        let radius = (b * step).exp();
                        let angle = (a - twist * b) / arms * std::f64::consts::TAU;
                        let middle = [
                            center[0] + radius * angle.cos(),
                            center[1] + radius * angle.sin(),
                        ];
                        let (dx, dy) = (point[0] - center[0], point[1] - center[1]);
                        let r = dx.hypot(dy).max(1e-300);
                        let (out, round) = ([dx / r, dy / r], [-dy / r, dx / r]);
                        let [s, t, _] = local;
                        let sides = [
                            (s, [-round[0], -round[1]]),
                            (1.0 - s, round),
                            // Inside the innermost ring a quad is a wedge to the middle:
                            // it has no inner side for a seam or a face.
                            (
                                if r.ln() < low as f64 * step {
                                    f64::INFINITY
                                } else {
                                    t
                                },
                                [-out[0], -out[1]],
                            ),
                            (1.0 - t, out),
                        ];
                        let (share, outward) =
                            sides
                                .into_iter()
                                .fold((f64::INFINITY, [0.0; 2]), |best, side| {
                                    if side.0 < best.0 { side } else { best }
                                });
                        (middle, share * r * step * size, outward, a)
                    }
                };

                let mut rgb = match mosaic.fill {
                    Fill::Flat => cell.rgb.map(|sum| sum / cell.count.max(1.0)),
                    Fill::Turned => {
                        let (sin, cos) = (turn * count).sin_cos();
                        let (dx, dy) = (point[0] - middle[0], point[1] - middle[1]);
                        // Each facet slips its own way: a direction off its own number.
                        let way = (hashed(root_index, level + SLIP, node as u64) >> 11) as f64
                            / (1u64 << 53) as f64
                            * std::f64::consts::TAU;
                        let slip = mosaic.shift * edge;
                        let read = [
                            middle[0] + dx * cos - dy * sin + slip * way.cos(),
                            middle[1] + dx * sin + dy * cos + slip * way.sin(),
                        ];
                        frame.linear[sample_at(read, width, height)]
                    }
                };
                if lit {
                    let [gx, gy] = cell.slope();
                    let tilt = [
                        mosaic.fold * outward[0] - mosaic.relief * edge * gx,
                        mosaic.fold * outward[1] - mosaic.relief * edge * gy,
                    ];
                    let steep = tilt[0].hypot(tilt[1]);
                    let tilt = tilt.map(|t| t * (STEEPEST / steep.max(STEEPEST)));
                    let length = (tilt[0] * tilt[0] + tilt[1] * tilt[1] + 1.0).sqrt();
                    let facing =
                        (tilt[0] * to_light[0] + tilt[1] * to_light[1] + to_light[2]) / length;
                    let gain = (facing / to_light[2]).max(0.0);
                    rgb = rgb.map(|c| c * gain);
                }
                if let Some(inlay) = mosaic.inlay {
                    let (mut inner, mut within, mut size) = (node as u64, local, edge);
                    let mut gain = 1.0;
                    for depth in 1..=inlay.levels {
                        size *= 0.5;
                        if size < mosaic.smallest {
                            break;
                        }
                        let (digit, next) = lattice.child(within);
                        (inner, within) = (inner * 4 + digit as u64, next);
                        let unit = (hashed(root_index, level + depth, inner) >> 11) as f64
                            / (1u64 << 53) as f64;
                        gain *= 1.0 + inlay.amount * (2.0 * unit - 1.0);
                    }
                    rgb = rgb.map(|c| c * gain);
                }
                if let Some((seam_width, color, opacity)) = seam {
                    if rim < seam_width.min(SEAM_SHARE * edge) {
                        for k in 0..3 {
                            rgb[k] += (color[k] - rgb[k]) * opacity;
                        }
                    }
                }
                if mosaic.opacity < 1.0 {
                    let under = frame.linear[i];
                    for k in 0..3 {
                        rgb[k] = under[k] + (rgb[k] - under[k]) * mosaic.opacity;
                    }
                }
                rgb
            })
            .collect();
        for (&i, rgb) in samples.iter().zip(drawn) {
            painted[i as usize] = rgb;
        }
    }
    Ok(painted)
}

/// What a sheet of the paper pass is filled with.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Stock {
    /// The map, read once per sheet.
    #[default]
    Map,
    /// The mean of the picture under the sheet.
    Picture,
}

/// The shadow each sheet casts on the sheets under it.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Shadow {
    /// How far the shadow fades over, in frame widths.
    pub width: f64,
    /// How far it is thrown from the edge that casts it, in frame widths.
    #[serde(default)]
    pub offset: f64,
    /// Where the light comes from, degrees anticlockwise: the shadow falls the other way.
    #[serde(default = "upper_left")]
    pub azimuth: f64,
    #[serde(default = "one")]
    pub opacity: f64,
    /// Black when absent.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub color: Option<Paint>,
}

fn upper_left() -> f64 {
    135.0
}

/// A dry brush's edge: each sheet's rim dragged along the stroke, bristle by bristle.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Ragged {
    /// The farthest a rim is dragged either way, in frame widths.
    pub reach: f64,
    /// How long one stroke runs, in frame widths.
    pub length: f64,
    /// How wide one bristle is, in frame widths.
    pub width: f64,
    /// The way the brush was drawn, degrees anticlockwise.
    #[serde(default)]
    pub azimuth: f64,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub accent: Option<Accent>,
}

/// A few strokes of another colour, laid where the brush moved a rim.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Accent {
    pub color: Paint,
    /// The share of strokes that carry it.
    pub share: f64,
}

/// The most sheets a paper pass cuts, and the widest its shadow fades.
pub const MOST_SHEETS: u32 = 64;
pub const WIDEST_SHADOW: f64 = 0.25;

/// The farthest a paper's `hop` and `phase` go either way, in turns of the map.
pub const MOST_TURNS: f64 = 1000.0;

/// A bristle is this share of a stroke's broad wobble across the brush.
const BRISTLES: f64 = 8.0;

/// The **paper** pass: the frame as stacked sheets of cut paper. A height is cut into
/// `levels` flat sheets on its rank over the frame, each one colour with a hard edge
/// that is the fractal's own level line; `ragged` tears the edges as a dry brush does,
/// and `shadow` lays each sheet's shadow on those under it.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct Paper {
    /// The height the sheets are cut from: a plain field channel. It is cut on its
    /// rank, so only `invert` (which end is the top sheet) changes the picture, never
    /// its `transform`.
    pub height: Source,
    /// How many sheets.
    pub levels: u32,
    /// Each sheet's share of the frame, as a multiple of the one under it: at 1 the
    /// sheets are equal areas, under 1 they thin towards the top.
    pub taper: f64,
    pub fill: Stock,
    /// `map`: sheet `i` reads the map at `phase + i·hop`, wrapped, so neighbours can
    /// be far apart on it. Absent: the sheets walk the map once, end to end.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub hop: Option<f64>,
    pub phase: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ragged: Option<Ragged>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub shadow: Option<Shadow>,
    /// How much of the paper is laid over the picture beneath, in `[0, 1]`.
    pub opacity: f64,
}

impl Default for Paper {
    fn default() -> Paper {
        Paper {
            height: Source {
                field: Some(FieldSpec::Smooth),
                inside: None,
                radial: None,
                bubble: None,
                lines: None,
                stroke: None,
                view: None,
                transform: Transform::default(),
                invert: false,
            },
            levels: 9,
            taper: 1.0,
            fill: Stock::Map,
            hop: None,
            phase: 0.0,
            ragged: None,
            shadow: None,
            opacity: 1.0,
        }
    }
}

impl Paper {
    fn validate(&self) -> Result<(), String> {
        if !plain(&self.height) {
            return Err("paper: height is a plain field channel, with no view".into());
        }
        if !(2..=MOST_SHEETS).contains(&self.levels) {
            return Err(format!("paper: levels is 2 to {MOST_SHEETS}"));
        }
        if !(self.taper > 0.0 && self.taper <= 1.0) {
            return Err("paper: taper is in (0, 1]".into());
        }
        // Past a few turns of the map a position is only its fraction; far past them
        // the fraction is rounding, and an overflow has none.
        let turns = |position: f64| position.abs() <= MOST_TURNS;
        if !(turns(self.phase) && self.hop.is_none_or(turns)) {
            return Err(format!(
                "paper: hop and phase are within {MOST_TURNS} turns of the map"
            ));
        }
        if !(0.0..=1.0).contains(&self.opacity) {
            return Err("paper: opacity is in [0, 1]".into());
        }
        if let Some(ragged) = &self.ragged {
            if !((0.0..=0.5).contains(&ragged.reach) && ragged.azimuth.is_finite()) {
                return Err(
                    "paper: a ragged edge reaches 0 to 0.5 frame widths, at a finite azimuth"
                        .into(),
                );
            }
            if !(ragged.width >= 1e-5 && ragged.length >= ragged.width && ragged.length <= 4.0) {
                return Err(
                    "paper: a ragged edge has 1e-5 <= width <= length <= 4 frame widths".into(),
                );
            }
            if let Some(accent) = &ragged.accent {
                accent.color.validate("paper accent")?;
                if !(0.0..=1.0).contains(&accent.share) {
                    return Err("paper: an accent's share is in [0, 1]".into());
                }
            }
        }
        if let Some(shadow) = &self.shadow {
            if !(shadow.width > 0.0 && shadow.width <= WIDEST_SHADOW) {
                return Err(format!(
                    "paper: a shadow's width is a length up to {WIDEST_SHADOW} of the frame"
                ));
            }
            if !((0.0..=WIDEST_SHADOW).contains(&shadow.offset) && shadow.azimuth.is_finite()) {
                return Err(format!(
                    "paper: a shadow's offset is 0 to {WIDEST_SHADOW} of the frame, its azimuth finite"
                ));
            }
            if !(0.0..=1.0).contains(&shadow.opacity) {
                return Err("paper: a shadow's opacity is in [0, 1]".into());
            }
            if let Some(paint) = &shadow.color {
                paint.validate("paper shadow")?;
            }
        }
        Ok(())
    }

    /// The rank each sheet starts at, and 1: `levels + 1` shares of the frame.
    fn cuts(&self) -> Vec<f64> {
        let mut cuts = vec![0.0];
        let (mut share, mut total) = (1.0, 0.0);
        for _ in 0..self.levels {
            total += share;
            cuts.push(total);
            share *= self.taper;
        }
        cuts.iter().map(|cut| cut / total).collect()
    }
}

/// A number in `[0, 1)` off a lattice point: the same on every machine.
fn unit(ix: i64, iy: i64, seed: u64) -> f64 {
    let mut x = (ix as u64)
        .wrapping_mul(0x9E37_79B9_7F4A_7C15)
        .wrapping_add((iy as u64).wrapping_mul(0xC2B2_AE3D_27D4_EB4F))
        .wrapping_add(seed.wrapping_mul(0x1656_67B1_9E37_79F9));
    x ^= x >> 30;
    x = x.wrapping_mul(0xBF58_476D_1CE4_E5B9);
    x ^= x >> 27;
    x = x.wrapping_mul(0x94D0_49BB_1331_11EB);
    ((x ^ (x >> 31)) >> 11) as f64 / (1u64 << 53) as f64
}

fn eased(t: f64) -> f64 {
    t * t * (3.0 - 2.0 * t)
}

/// Value noise in `[-1, 1]`, smooth both ways.
fn wobble(x: f64, y: f64, seed: u64) -> f64 {
    let (ix, iy) = (x.floor(), y.floor());
    let (fx, fy) = (eased(x - ix), eased(y - iy));
    let (ix, iy) = (ix as i64, iy as i64);
    let low = unit(ix, iy, seed) + (unit(ix + 1, iy, seed) - unit(ix, iy, seed)) * fx;
    let high = unit(ix, iy + 1, seed) + (unit(ix + 1, iy + 1, seed) - unit(ix, iy + 1, seed)) * fx;
    2.0 * (low + (high - low) * fy) - 1.0
}

/// Value noise in `[-1, 1]`, smooth along `x` and one value per whole `y`: bristles.
fn bristled(x: f64, y: f64, seed: u64) -> f64 {
    let ix = x.floor();
    let fx = eased(x - ix);
    let (ix, iy) = (ix as i64, y.floor() as i64);
    2.0 * (unit(ix, iy, seed) + (unit(ix + 1, iy, seed) - unit(ix, iy, seed)) * fx) - 1.0
}

/// A lane blurred by a box of `radius` samples each way, twice over (a tent), the
/// frame's edge samples repeated past it. Sums run in sample order.
fn blurred(lane: &[f32], width: usize, height: usize, radius: usize) -> Vec<f32> {
    if radius == 0 {
        return lane.to_vec();
    }
    let span = (2 * radius + 1) as f64;
    let mut lane = lane.to_vec();
    let mut next = vec![0f32; lane.len()];
    for _ in 0..2 {
        for row in 0..height {
            let line = &lane[row * width..(row + 1) * width];
            let at = |col: isize| line[col.clamp(0, width as isize - 1) as usize] as f64;
            let mut sum: f64 = (-(radius as isize)..=radius as isize).map(at).sum();
            for col in 0..width {
                next[row * width + col] = (sum / span) as f32;
                let col = col as isize;
                sum += at(col + radius as isize + 1) - at(col - radius as isize);
            }
        }
        let at = |row: isize, col: usize| {
            next[row.clamp(0, height as isize - 1) as usize * width + col] as f64
        };
        let mut sums: Vec<f64> = (0..width)
            .map(|col| {
                (-(radius as isize)..=radius as isize)
                    .map(|row| at(row, col))
                    .sum()
            })
            .collect();
        for row in 0..height {
            for (col, sum) in sums.iter_mut().enumerate() {
                lane[row * width + col] = (*sum / span) as f32;
                let row = row as isize;
                *sum += at(row + radius as isize + 1, col) - at(row - radius as isize, col);
            }
        }
    }
    lane
}

/// Lay the paper over `frame`: `frame.heights` is the raw height, highest on top and
/// not finite where the orbit never escaped. Those samples keep the picture beneath
/// and lie over every sheet (under every sheet when the height is inverted).
pub fn paper(paper: &Paper, frame: &Frame, colormap: &Colormap) -> Result<Vec<[f64; 3]>, String> {
    let (width, height) = (frame.width, frame.height);
    if width == 0 || height == 0 {
        return Ok(frame.linear.to_vec());
    }
    let levels = paper.levels as usize;
    let mut sorted: Vec<f32> = frame
        .heights
        .iter()
        .copied()
        .filter(|h| h.is_finite())
        .collect();
    sorted.sort_unstable_by(f32::total_cmp);
    let cuts = paper.cuts();
    let set = if paper.height.invert {
        -1.0
    } else {
        levels as f32
    };
    let brush = paper.ragged.as_ref().map(|ragged| {
        let (sin, cos) = ragged.azimuth.to_radians().sin_cos();
        let accent = ragged
            .accent
            .as_ref()
            .map(|accent| (accent.color.linear(colormap), accent.share));
        // Rows run down the frame, so an anticlockwise azimuth has its `y` turned over.
        (ragged, [cos, -sin], accent)
    });

    // Each sample's sheet as the height cuts it: a pure function of the sample.
    let cut: Vec<f32> = (0..width * height)
        .into_par_iter()
        .map(|i| {
            let h = frame.heights[i];
            if !h.is_finite() {
                return set;
            }
            let rank = sorted.partition_point(|&v| v < h) as f64 / sorted.len() as f64;
            (cuts.partition_point(|&cut| cut <= rank) - 1).min(levels - 1) as f32
        })
        .collect();
    // The brush drags each sample's sheet along the stroke, every bristle its own
    // length, from a sample up to `reach` away; the set's own edge is never dragged.
    let sheets: Vec<(f32, bool)> = match &brush {
        None => cut.iter().map(|&sheet| (sheet, false)).collect(),
        Some((ragged, along, accent)) => (0..width * height)
            .into_par_iter()
            .map(|i| {
                if !frame.heights[i].is_finite() {
                    return (cut[i], false);
                }
                let (col, row) = (i % width, i / width);
                let [x, y] = point_of(col, row, width, height);
                let (a, b) = (
                    (x * along[0] + y * along[1]) / ragged.length,
                    (y * along[0] - x * along[1]) / ragged.width,
                );
                let push = 0.5 * wobble(a, b / BRISTLES, 1) + 0.5 * bristled(a, b, 2);
                let drag = ragged.reach * push * width as f64;
                let from = (row as f64 + drag * along[1])
                    .round()
                    .clamp(0.0, (height - 1) as f64) as usize
                    * width
                    + (col as f64 + drag * along[0])
                        .round()
                        .clamp(0.0, (width - 1) as f64) as usize;
                if !frame.heights[from].is_finite() || cut[from] == cut[i] {
                    return (cut[i], false);
                }
                let accented = accent.is_some_and(|(_, share)| {
                    unit(a.floor() as i64, (b / BRISTLES).floor() as i64, 3) < share
                });
                (cut[from], accented)
            })
            .collect(),
    };

    let fills: Vec<[f64; 3]> = match paper.fill {
        Stock::Map => (0..levels)
            .map(|sheet| {
                let at = match paper.hop {
                    Some(hop) => paper.phase + sheet as f64 * hop,
                    None => paper.phase + (sheet as f64 + 0.5) / levels as f64,
                };
                colormap.lookup(at - at.floor())
            })
            .collect(),
        Stock::Picture => {
            let mut sums = vec![([0.0; 3], 0.0f64); levels];
            for (i, &(sheet, _)) in sheets.iter().enumerate() {
                if frame.heights[i].is_finite() {
                    let (sum, count) = &mut sums[sheet as usize];
                    for k in 0..3 {
                        sum[k] += frame.linear[i][k];
                    }
                    *count += 1.0;
                }
            }
            sums.into_iter()
                .map(|(sum, count)| sum.map(|c| c / count.max(1.0)))
                .collect()
        }
    };

    let shade = paper.shadow.as_ref().map(|shadow| {
        let w = width as f64;
        let lane: Vec<f32> = sheets.iter().map(|&(sheet, _)| sheet).collect();
        // Two boxes of half the width each fade over about the whole of it.
        let radius = (0.25 * shadow.width * w).round() as usize;
        let (sin, cos) = shadow.azimuth.to_radians().sin_cos();
        let towards = [
            (shadow.offset * w * cos).round() as isize,
            (-shadow.offset * w * sin).round() as isize,
        ];
        let color = shadow
            .color
            .as_ref()
            .map_or([0.0; 3], |paint| paint.linear(colormap));
        (
            blurred(&lane, width, height, radius),
            towards,
            color,
            shadow.opacity,
        )
    });

    let painted = (0..width * height)
        .into_par_iter()
        .map(|i| {
            let (sheet, accented) = sheets[i];
            let under = frame.linear[i];
            let mut rgb = if !frame.heights[i].is_finite() {
                under
            } else if accented {
                brush
                    .as_ref()
                    .and_then(|brush| brush.2)
                    .map_or(under, |a| a.0)
            } else {
                fills[sheet as usize]
            };
            if let Some((above, towards, color, opacity)) = &shade {
                let col = (i % width) as isize + towards[0];
                let row = (i / width) as isize + towards[1];
                let from = row.clamp(0, height as isize - 1) as usize * width
                    + col.clamp(0, width as isize - 1) as usize;
                let dark = ((above[from] - sheet) as f64).clamp(0.0, 1.0) * opacity;
                for k in 0..3 {
                    rgb[k] += (color[k] - rgb[k]) * dark;
                }
            }
            if paper.opacity < 1.0 {
                for k in 0..3 {
                    rgb[k] = under[k] + (rgb[k] - under[k]) * paper.opacity;
                }
            }
            rgb
        })
        .collect();
    Ok(painted)
}

/// The **rays** pass: beams of light cast from the frame's brightest samples. Each
/// sample brighter than all but `share` of the frame casts the part of its light above
/// that cut along `spokes` straight lines (a streak at 2, a cross at 4, a star at 6 or
/// 8), fading over `length`; or, with `center`, outwards along the line from that point,
/// as shafts through haze. A beam is straight and reads its neighbours, so no layer can
/// draw it: the light along it is whatever the fractal set alight at its root.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct Rays {
    /// The share of the frame's samples that cast (by luminance), in (0, 0.5].
    pub share: f64,
    /// How many beams each source casts, evenly round the circle from `angle`.
    pub spokes: u32,
    /// The first spoke's direction, degrees anticlockwise from the right.
    pub angle: f64,
    /// How far a beam runs before it fades to 1/e, in frame widths.
    pub length: f64,
    /// Shafts from this point instead of spokes (fractions of the frame's width and
    /// height): each sample gathers the light between it and the point. With a center,
    /// `spokes` and `angle` are not read.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub center: Option<[f64; 2]>,
    /// The beams' gain over the light that casts them.
    pub strength: f64,
    /// Every beam this paint times its source's luminance (so a dark paint dims the
    /// beams); absent, each beam its source's own colour.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub color: Option<Paint>,
}

impl Default for Rays {
    fn default() -> Rays {
        Rays {
            share: 0.02,
            spokes: 4,
            angle: 45.0,
            length: 0.05,
            center: None,
            strength: 1.0,
            color: None,
        }
    }
}

/// The most spokes a rays pass casts, and the longest a beam runs (frame widths).
pub const MOST_SPOKES: u32 = 16;
pub const LONGEST_BEAM: f64 = 2.0;

/// The most doubling passes a shaft sums over: 2^14 samples. A long `length` on a wide
/// frame can ask for more, but only samples on the frame cast, so no shaft ever needs
/// more than the frame's diagonal (5,120 x 3,200 samples at full size: about 6,000).
const SHAFT_PASSES: u32 = 14;

/// The frame width in samples a spoke's `strength` means what it says at: the draft's
/// (1280 wide at supersample 2), where styles are tuned and kept. A spoke sums the light
/// behind each sample, and a source covers more samples on a finer grid, so its beams are
/// scaled by this over the frame's width: a draft, the full frame and the explorer draw
/// one picture, and at the draft's own width the scale is exactly 1.
pub const SPOKE_WIDTH: f64 = 2560.0;

/// A shaft gathers out to this many `length`s, past which its light is under 1/20.
const SHAFT_REACH: f64 = 3.0;

impl Rays {
    fn validate(&self) -> Result<(), String> {
        let finite = [self.share, self.angle, self.length, self.strength];
        if finite.iter().any(|value| !value.is_finite()) {
            return Err("rays: every member is a finite number".into());
        }
        if !(self.share > 0.0 && self.share <= 0.5) {
            return Err("rays: share is in (0, 0.5]".into());
        }
        if !(1..=MOST_SPOKES).contains(&self.spokes) {
            return Err(format!("rays: 1 to {MOST_SPOKES} spokes"));
        }
        if !(self.length >= 1e-4 && self.length <= LONGEST_BEAM) {
            return Err(format!(
                "rays: length is 1e-4 to {LONGEST_BEAM} frame widths"
            ));
        }
        if !(0.0..=100.0).contains(&self.strength) {
            return Err("rays: strength is 0 to 100".into());
        }
        if let Some(center) = self.center {
            if !center
                .iter()
                .all(|c| c.is_finite() && (-4.0..=5.0).contains(c))
            {
                return Err("rays: a center is within 4 frames of the frame".into());
            }
        }
        if let Some(paint) = &self.color {
            paint.validate("rays")?;
        }
        Ok(())
    }
}

/// The light one sample casts: the part of it above the frame's cut, by luminance.
fn casting(linear: &[[f64; 3]], share: f64) -> Vec<[f32; 3]> {
    let luminance = |rgb: &[f64; 3]| 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2];
    let mut sorted: Vec<f64> = linear.iter().map(luminance).collect();
    let rank = ((sorted.len() as f64 * (1.0 - share)) as usize).min(sorted.len() - 1);
    let (_, &mut cut, _) = sorted.select_nth_unstable_by(rank, f64::total_cmp);
    linear
        .iter()
        .map(|rgb| {
            let light = luminance(rgb);
            if !(light > cut && light.is_finite()) {
                return [0.0; 3];
            }
            let above = 1.0 - cut.max(0.0) / light;
            rgb.map(|c| (c.max(0.0) * above) as f32)
        })
        .collect()
}

/// One spoke's beams, swept in a single pass: each sample is its own light plus the
/// beam arriving from one step back along the spoke, faded by `fade`. `lanes` is laid
/// out `major` slices of `minor` samples, the sweep running across slices; a step back
/// is one slice back and `slope` samples along it (between two samples, it reads both).
fn swept(
    lanes: &[[f32; 3]],
    major: usize,
    minor: usize,
    ahead: bool,
    slope: f64,
    fade: f32,
) -> Vec<[f32; 3]> {
    let mut beam = vec![[0.0f32; 3]; lanes.len()];
    let order: Vec<usize> = match ahead {
        true => (0..major).collect(),
        false => (0..major).rev().collect(),
    };
    let (whole, part) = (slope.floor(), (slope - slope.floor()) as f32);
    let whole = whole as isize;
    let mut previous: Option<usize> = None;
    for slice in order {
        let at = slice * minor;
        for m in 0..minor {
            let mut rgb = lanes[at + m];
            if let Some(back) = previous {
                // The beam arriving here left one slice back, `slope` samples behind.
                let from = m as isize - whole;
                let read = |i: isize| -> [f32; 3] {
                    match i >= 0 && (i as usize) < minor {
                        true => beam[back * minor + i as usize],
                        false => [0.0; 3],
                    }
                };
                let (near, far) = (read(from), read(from - 1));
                for k in 0..3 {
                    rgb[k] += fade * (near[k] * (1.0 - part) + far[k] * part);
                }
            }
            beam[at + m] = rgb;
        }
        previous = Some(slice);
    }
    beam
}

/// The pass: the picture with the beams its brightest samples cast added over it.
pub fn rays(rays: &Rays, frame: &Frame, colormap: &Colormap) -> Result<Vec<[f64; 3]>, String> {
    let (width, height) = (frame.width, frame.height);
    if width == 0 || height == 0 {
        return Ok(frame.linear.to_vec());
    }
    let mut light = casting(frame.linear, rays.share);
    if let Some(paint) = &rays.color {
        let tint = paint.linear(colormap);
        for rgb in light.iter_mut() {
            let bright = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2];
            *rgb = tint.map(|c| (c * bright as f64) as f32);
        }
    }
    let reach = rays.length * width as f64;
    let mut beams = vec![[0.0f32; 3]; width * height];
    // A shaft is a mean, the same at any size; a spoke is a sum over the samples behind,
    // so it is scaled to the width its `strength` is read at.
    let gain = match rays.center {
        None => rays.strength * (SPOKE_WIDTH / width as f64),
        Some(_) => rays.strength,
    };
    match rays.center {
        None => {
            for spoke in 0..rays.spokes {
                let degrees = rays.angle + 360.0 * spoke as f64 / rays.spokes as f64;
                let (sin, cos) = degrees.to_radians().sin_cos();
                // Rows run down the frame, so anticlockwise is up: the beam's row step is -sin.
                let (dx, dy) = (cos, -sin);
                let across = dx.abs() >= dy.abs();
                let (step, slope) = match across {
                    true => (dx, dy / dx.abs()),
                    false => (dy, dx / dy.abs()),
                };
                let fade = (-(1.0 + slope * slope).sqrt() / reach).exp() as f32;
                let beam = if across {
                    // Sweep the columns: lay the frame out column by column first.
                    let mut columns = vec![[0.0f32; 3]; width * height];
                    for row in 0..height {
                        for col in 0..width {
                            columns[col * height + row] = light[row * width + col];
                        }
                    }
                    let swept = swept(&columns, width, height, step > 0.0, slope, fade);
                    let mut rows = vec![[0.0f32; 3]; width * height];
                    for col in 0..width {
                        for row in 0..height {
                            rows[row * width + col] = swept[col * height + row];
                        }
                    }
                    rows
                } else {
                    swept(&light, height, width, step > 0.0, slope, fade)
                };
                for ((sum, beam), own) in beams.iter_mut().zip(&beam).zip(&light) {
                    for k in 0..3 {
                        sum[k] += beam[k] - own[k];
                    }
                }
            }
        }
        Some(center) => {
            let (cx, cy) = (center[0] * width as f64, center[1] * height as f64);
            // A shaft sums the light behind a sample, towards the center, each sample
            // `fade` of the one before. Summed by doubling: after pass `k` each sample
            // holds the sum over the 2^k samples behind it, so `SHAFT_PASSES` passes of
            // one tap each reach 2^SHAFT_PASSES samples and skip none on the way.
            let longest = SHAFT_REACH * reach;
            let passes = (longest.max(2.0).log2().ceil() as u32).min(SHAFT_PASSES);
            let mut fade = (-1.0 / reach).exp();
            let mut sum: Vec<[f32; 3]> = light.clone();
            let mut stride = 1.0;
            for _ in 0..passes {
                let behind = &sum;
                let next: Vec<[f32; 3]> = (0..width * height)
                    .into_par_iter()
                    .map(|i| {
                        let (px, py) = ((i % width) as f64 + 0.5, (i / width) as f64 + 0.5);
                        let (tx, ty) = (cx - px, cy - py);
                        let distance = (tx * tx + ty * ty).sqrt();
                        let mut rgb = behind[i];
                        if distance > stride {
                            let at = bilinear(
                                behind,
                                width,
                                height,
                                px + tx / distance * stride,
                                py + ty / distance * stride,
                            );
                            for k in 0..3 {
                                rgb[k] += (fade * at[k]) as f32;
                            }
                        }
                        rgb
                    })
                    .collect();
                sum = next;
                stride *= 2.0;
                fade *= fade;
            }
            // A shaft is the mean of the light behind it, the nearest counting most.
            let mean = (1.0 - (-1.0 / reach).exp()) as f32;
            beams = sum
                .iter()
                .zip(&light)
                .map(|(total, own)| [0, 1, 2].map(|k| (total[k] - own[k]) * mean))
                .collect();
        }
    }
    Ok(frame
        .linear
        .iter()
        .zip(&beams)
        .map(|(rgb, beam)| {
            let mut out = *rgb;
            for k in 0..3 {
                out[k] += gain * beam[k] as f64;
            }
            out
        })
        .collect())
}

/// The lanes between four samples at a point in samples (`0.5` is the first sample's
/// middle), each read in proportion; off the frame, nothing.
fn bilinear(lanes: &[[f32; 3]], width: usize, height: usize, x: f64, y: f64) -> [f64; 3] {
    let (x, y) = (x - 0.5, y - 0.5);
    let (x0, y0) = (x.floor(), y.floor());
    let (fx, fy) = (x - x0, y - y0);
    let mut rgb = [0.0; 3];
    for (ox, oy, w) in [
        (0, 0, (1.0 - fx) * (1.0 - fy)),
        (1, 0, fx * (1.0 - fy)),
        (0, 1, (1.0 - fx) * fy),
        (1, 1, fx * fy),
    ] {
        let (col, row) = (x0 as isize + ox, y0 as isize + oy);
        if col < 0 || row < 0 || col >= width as isize || row >= height as isize {
            continue;
        }
        let at = lanes[row as usize * width + col as usize];
        for k in 0..3 {
            rgb[k] += w * at[k] as f64;
        }
    }
    rgb
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::colormap::Kind;

    fn map() -> Colormap {
        Colormap::from_stops(
            "ramp",
            Kind::Sequential,
            &[(0.0, [0, 0, 0]), (1.0, [255, 255, 255])],
        )
        .unwrap()
    }

    /// A frame whose set is the vertical line a third of the way across: escaped
    /// everywhere, `near` the distance to the line, the picture a ramp across.
    fn painted(mosaic: &Mosaic, width: usize, height: usize) -> Vec<[f64; 3]> {
        let mut linear = Vec::new();
        let mut near = Vec::new();
        for row in 0..height {
            for col in 0..width {
                let [x, _] = point_of(col, row, width, height);
                linear.push([x + 0.5, 0.5, 0.25]);
                near.push((x + 1.0 / 6.0).abs() as f32);
            }
        }
        let escaped = vec![true; width * height];
        let frame = Frame {
            width,
            height,
            linear: &linear,
            escaped: &escaped,
            near: &near,
            heights: &[],
        };
        super::mosaic(mosaic, &frame, &map()).unwrap()
    }

    /// The runs of one colour along a row: each is a facet's width in samples.
    fn runs(row: &[[f64; 3]]) -> Vec<usize> {
        let mut runs = vec![1];
        for pair in row.windows(2) {
            if pair[0] == pair[1] {
                *runs.last_mut().unwrap() += 1;
            } else {
                runs.push(1);
            }
        }
        runs
    }

    #[test]
    fn facets_are_fine_at_the_set_and_large_far_from_it() {
        let lattices = [
            Mosaic::default(),
            Mosaic {
                rhombi: true,
                tilt: 20.0,
                ..Mosaic::default()
            },
            Mosaic {
                spiral: Some(Spiral::default()),
                ..Mosaic::default()
            },
        ];
        for mosaic in lattices {
            let (width, height) = (600, 400);
            let picture = painted(&mosaic, width, height);
            let row = &picture[150 * width..151 * width];
            let runs = runs(row);
            let mut at = 0;
            let (mut beside, mut far) = (usize::MAX, 0);
            for run in runs {
                let middle = at + run / 2;
                if middle.abs_diff(200) < 12 {
                    beside = beside.min(run);
                }
                if middle > 480 {
                    far = far.max(run);
                }
                at += run;
            }
            assert!(
                beside <= 8,
                "the facets at the set are a few samples: {beside}"
            );
            assert!(far >= 20, "the facets far from it are large: {far}");
        }
    }

    #[test]
    fn a_draft_is_the_full_frame_s_picture() {
        // Sizes are fractions of the frame, so half the samples draw the same facets:
        // every draft sample is the mean of the full frame's four there, to the
        // samples a facet's edge crosses.
        let mosaic = Mosaic {
            smallest: 0.02,
            ..Mosaic::default()
        };
        let (full, draft) = (painted(&mosaic, 640, 400), painted(&mosaic, 320, 200));
        let mut far = 0;
        for row in 0..200 {
            for col in 0..320 {
                let small = draft[row * 320 + col];
                let big = full[(2 * row) * 640 + 2 * col];
                if (0..3).any(|k| (small[k] - big[k]).abs() > 0.02) {
                    far += 1;
                }
            }
        }
        assert!(
            far < 320 * 200 / 8,
            "{far} draft samples off the full frame"
        );
    }

    #[test]
    fn a_flat_fill_keeps_the_frame_s_mean_and_a_fold_lights_one_face_of_three() {
        let flat = painted(&Mosaic::default(), 300, 200);
        let mean = |picture: &[[f64; 3]]| picture.iter().map(|p| p[0]).sum::<f64>() / 60_000.0;
        assert!((mean(&flat) - 0.5).abs() < 1e-9);
        let folded = painted(
            &Mosaic {
                fold: 0.5,
                reach: 0.0,
                ..Mosaic::default()
            },
            300,
            200,
        );
        // Far from the set one large facet shows more than one shade.
        let row = &folded[100 * 300..101 * 300];
        let shades = runs(&row[220..300]).len();
        assert!(shades >= 2, "a folded facet has faces: {shades}");
    }

    #[test]
    fn a_seam_never_takes_a_small_facet_s_face() {
        let seamed = Mosaic {
            seam: Some(Seam {
                width: 0.5,
                color: Some(Paint::Rgb("#ff0000".into())),
                opacity: 1.0,
            }),
            ..Mosaic::default()
        };
        let picture = painted(&seamed, 300, 200);
        let red = picture.iter().filter(|p| **p == [1.0, 0.0, 0.0]).count();
        assert!(red > 0 && red < picture.len() * 3 / 4, "{red} seam samples");
    }

    #[test]
    fn an_inlay_draws_a_calm_facet_s_children_into_it() {
        let calm = Mosaic {
            reach: 0.0,
            ..Mosaic::default()
        };
        let inlaid = Mosaic {
            inlay: Some(Inlay {
                levels: 3,
                amount: 0.1,
            }),
            ..calm.clone()
        };
        let (plain, inlaid) = (painted(&calm, 400, 250), painted(&inlaid, 400, 250));
        // One row through the far field: a few facets plain, several cells in each inlaid.
        let row = |picture: &[[f64; 3]]| runs(&picture[125 * 400 + 250..125 * 400 + 400]).len();
        assert!(
            row(&inlaid) >= 3 * row(&plain),
            "{} against {}",
            row(&inlaid),
            row(&plain)
        );
        // Never more than the amount at each level, either way.
        for (a, b) in plain.iter().zip(&inlaid) {
            let gain = b[1] / a[1];
            assert!(
                (0.9f64.powi(3) - 1e-9..=1.1f64.powi(3) + 1e-9).contains(&gain),
                "{gain}"
            );
        }
    }

    #[test]
    fn an_opacity_lays_the_mosaic_over_the_picture_it_was_made_from() {
        let whole = painted(&Mosaic::default(), 200, 125);
        let half = painted(
            &Mosaic {
                opacity: 0.5,
                ..Mosaic::default()
            },
            200,
            125,
        );
        let none = painted(
            &Mosaic {
                opacity: 0.0,
                ..Mosaic::default()
            },
            200,
            125,
        );
        for ((whole, half), under) in whole.iter().zip(&half).zip(&none) {
            assert!((half[0] - 0.5 * (whole[0] + under[0])).abs() < 1e-12);
        }
        // At none of it the frame is the picture: the ramp across.
        assert!((none[10][0] - (point_of(10, 0, 200, 125)[0] + 0.5)).abs() < 1e-12);
    }

    #[test]
    fn a_shift_slips_each_turned_facet_s_view_its_own_way() {
        // Unsplit rhombi over the ramp: unshifted, a turned view at no turn is the
        // picture; shifted, each facet reads the ramp a fixed step off, its own.
        let turned = Mosaic {
            rhombi: true,
            fill: Fill::Turned,
            reach: 0.0,
            ..Mosaic::default()
        };
        let slipped = Mosaic {
            shift: 0.2,
            ..turned.clone()
        };
        let (plain, slipped) = (painted(&turned, 400, 250), painted(&slipped, 400, 250));
        let mut steps: Vec<i64> = Vec::new();
        for (index, (a, b)) in plain.iter().zip(&slipped).enumerate() {
            let [x, _] = point_of(index % 400, index / 400, 400, 250);
            assert!((a[0] - (x + 0.5)).abs() < 1e-12);
            let step = ((b[0] - a[0]) * 400.0).round() as i64;
            assert!(
                step.abs() <= 20,
                "a slip of 0.2 of a 0.25 edge is 20 samples: {step}"
            );
            if (-0.4..0.4).contains(&x) && !steps.contains(&step) {
                steps.push(step);
            }
        }
        assert!(steps.len() >= 3, "facets slip their own ways: {steps:?}");
    }

    #[test]
    fn a_tall_frame_pays_only_for_the_roots_it_touches() {
        // The lattice is a parallelogram round the frame; on a 9:16 frame most of its
        // triangles are off it, and a deep mosaic must still fit the cell budget.
        let deep = Mosaic {
            largest: 0.5,
            smallest: 0.0018,
            levels: 8,
            ..Mosaic::default()
        };
        let (width, height) = (90, 160);
        let linear = vec![[0.5; 3]; width * height];
        let frame = Frame {
            width,
            height,
            linear: &linear,
            escaped: &vec![true; width * height],
            near: &vec![1.0; width * height],
            heights: &[],
        };
        assert!(mosaic(&deep, &frame, &map()).is_ok());
    }

    #[test]
    fn a_seam_is_a_line_at_a_spiral_s_middle_too() {
        let seamed = Mosaic {
            spiral: Some(Spiral::default()),
            seam: Some(Seam {
                width: 0.0002,
                color: Some(Paint::Rgb("#ff0000".into())),
                opacity: 1.0,
            }),
            ..Mosaic::default()
        };
        let picture = painted(&seamed, 2000, 1250);
        // The disc inside the innermost ring is about 20 samples across here; the
        // seams meet at its very middle, so read the ring 6 to 10 samples out.
        let (mut red, mut read) = (0, 0);
        for row in 613..637 {
            for col in 988..1012 {
                let from = (col as f64 - 999.5).hypot(row as f64 - 624.5);
                if (6.0..10.0).contains(&from) {
                    read += 1;
                    red += (picture[row * 2000 + col] == [1.0, 0.0, 0.0]) as usize;
                }
            }
        }
        assert!(
            red > 0 && red * 2 < read,
            "{red} of {read} samples are seam"
        );
    }

    /// The paper over a frame whose height climbs left to right (the rightmost
    /// `inside` columns never escaped), the picture under it a ramp across.
    fn papered(paper: &Paper, width: usize, height: usize, inside: usize) -> Vec<[f64; 3]> {
        let (mut linear, mut heights) = (Vec::new(), Vec::new());
        for _ in 0..height {
            for col in 0..width {
                linear.push([col as f64 / width as f64, 0.5, 0.25]);
                heights.push(if col < width - inside {
                    col as f32
                } else {
                    f32::NAN
                });
            }
        }
        let frame = Frame {
            width,
            height,
            linear: &linear,
            escaped: &vec![true; width * height],
            near: &[],
            heights: &heights,
        };
        super::paper(paper, &frame, &map()).unwrap()
    }

    #[test]
    fn paper_cuts_the_height_into_flat_sheets_that_taper() {
        let even = Paper {
            levels: 4,
            ..Paper::default()
        };
        let picture = papered(&even, 400, 10, 0);
        assert_eq!(runs(&picture[..400]), vec![100; 4]);
        // The grey ramp read once per sheet, at its middle: dark to light.
        assert!(picture[0][0] < picture[150][0] && picture[150][0] < picture[399][0]);
        let tapered = Paper {
            taper: 0.5,
            ..even.clone()
        };
        let widths = runs(&papered(&tapered, 400, 10, 0)[..400]);
        assert_eq!(widths.len(), 4);
        assert!(
            widths.windows(2).all(|pair| pair[1] < pair[0]),
            "{widths:?}"
        );
        // A hop walks the map out of order, wrapped; the picture's mean fills a sheet.
        let hopped = Paper {
            hop: Some(0.6),
            ..even.clone()
        };
        let row = papered(&hopped, 400, 10, 0);
        assert!(
            row[150][0] > row[250][0],
            "sheet 1 reads 0.6, sheet 2 reads 0.2"
        );
        let mean = Paper {
            fill: Stock::Picture,
            ..even
        };
        let row = papered(&mean, 400, 10, 0);
        assert!((row[0][0] - 49.5 / 400.0).abs() < 1e-12);
    }

    #[test]
    fn a_shadow_falls_on_the_sheet_under_an_edge_and_never_on_the_one_above() {
        let plain = Paper {
            levels: 2,
            ..Paper::default()
        };
        let shadowed = Paper {
            shadow: Some(Shadow {
                width: 0.1,
                offset: 0.0,
                azimuth: 0.0,
                opacity: 0.5,
                color: None,
            }),
            ..plain.clone()
        };
        let (flat, dark) = (papered(&plain, 400, 40, 0), papered(&shadowed, 400, 40, 0));
        let row = 20 * 400;
        // The edge is at column 200: the lower sheet darkens towards it, the upper is untouched.
        assert_eq!(dark[row + 50], flat[row + 50]);
        assert!(dark[row + 199][0] < dark[row + 185][0] && dark[row + 185][0] <= flat[row][0]);
        assert!(dark[row + 199][0] >= 0.5 * flat[row][0] - 1e-12);
        assert_eq!(dark[row + 200..row + 400], flat[row + 200..row + 400]);
        // The set lies over every sheet and keeps the picture under it; inverted, it
        // lies under them all and takes their shadow.
        let over = papered(&shadowed, 400, 40, 40);
        assert_eq!(over[row + 380], [380.0 / 400.0, 0.5, 0.25]);
        assert!(over[row + 359][0] < over[row + 300][0]);
        let mut under = shadowed.clone();
        under.height.invert = true;
        let under = papered(&under, 400, 40, 40);
        assert!(under[row + 360][0] < 360.0 / 400.0);
    }

    #[test]
    fn a_ragged_edge_is_dragged_no_farther_than_its_reach() {
        let clean = Paper {
            levels: 2,
            ..Paper::default()
        };
        let ragged = Paper {
            ragged: Some(Ragged {
                reach: 0.05,
                length: 0.2,
                width: 0.01,
                azimuth: 0.0,
                accent: Some(Accent {
                    color: Paint::Rgb("#ff0000".into()),
                    share: 0.5,
                }),
            }),
            ..clean.clone()
        };
        let (flat, torn) = (
            papered(&clean, 400, 200, 40),
            papered(&ragged, 400, 200, 40),
        );
        let (mut moved, mut red) = (0, 0);
        for (index, (a, b)) in flat.iter().zip(&torn).enumerate() {
            if a != b {
                moved += 1;
                red += (*b == [1.0, 0.0, 0.0]) as usize;
                let col = index % 400;
                assert!((160..240).contains(&col), "column {col} moved");
            }
        }
        assert!(moved > 200, "{moved} samples moved");
        assert!(red > 0 && red < moved, "{red} of {moved} carry the accent");
        assert_eq!(torn, papered(&ragged, 400, 200, 40));
    }

    #[test]
    fn a_paper_pass_reads_and_refuses() {
        let pass: Pass = serde_json::from_str(
            r#"{"kind": "paper", "levels": 5, "shadow": {"width": 0.02},
                "ragged": {"reach": 0.01, "length": 0.1, "width": 0.002}}"#,
        )
        .unwrap();
        assert!(pass.validate().is_ok());
        assert_eq!(pass.height().unwrap().field, Some(FieldSpec::Smooth));
        assert!(serde_json::from_str::<Pass>(r#"{"kind": "paper", "sheets": 4}"#).is_err());
        for refused in [
            r#"{"kind": "paper", "levels": 1}"#,
            r#"{"kind": "paper", "levels": 65}"#,
            r#"{"kind": "paper", "taper": 0.0}"#,
            r#"{"kind": "paper", "hop": 1e307}"#,
            r#"{"kind": "paper", "opacity": 1.5}"#,
            r#"{"kind": "paper", "height": {"radial": {}}}"#,
            r#"{"kind": "paper", "shadow": {"width": 0.5}}"#,
            r#"{"kind": "paper", "shadow": {"width": 0.01, "color": {"rgb": "red"}}}"#,
            r#"{"kind": "paper", "ragged": {"reach": 0.01, "length": 0.001, "width": 0.002}}"#,
            r#"{"kind": "paper", "ragged": {"reach": 1.0, "length": 0.1, "width": 0.002}}"#,
        ] {
            let pass: Pass = serde_json::from_str(refused).unwrap();
            assert!(pass.validate().is_err(), "{refused}");
        }
    }

    #[test]
    fn a_pass_reads_and_refuses() {
        let pass: Pass =
            serde_json::from_str(r#"{"kind": "mosaic", "levels": 4, "spiral": {"arms": 9}}"#)
                .unwrap();
        assert!(pass.validate().is_ok());
        let Pass::Mosaic(read) = &pass else {
            panic!("a mosaic was read");
        };
        assert_eq!((read.levels, read.spiral.unwrap().arms), (4, 9));
        assert!(serde_json::from_str::<Pass>(r#"{"kind": "mosaic", "depth": 4}"#).is_err());
        for refused in [
            r#"{"kind": "mosaic", "smallest": 0.5}"#,
            r#"{"kind": "mosaic", "largest": 0.001, "smallest": 0.001}"#,
            r#"{"kind": "mosaic", "smallest": 1e-9}"#,
            r#"{"kind": "mosaic", "opacity": 1.5}"#,
            r#"{"kind": "mosaic", "rhombi": true, "spiral": {}}"#,
            r#"{"kind": "mosaic", "shift": 5.0}"#,
            r#"{"kind": "mosaic", "inlay": {"levels": 7, "amount": 0.1}}"#,
            r#"{"kind": "mosaic", "spiral": {"center": [1e300, 0.5]}}"#,
        ] {
            let pass: Pass = serde_json::from_str(refused).unwrap();
            assert!(pass.validate().is_err(), "{refused}");
        }
        let fine = Mosaic {
            smallest: 0.0001,
            levels: 10,
            ..Mosaic::default()
        };
        let frame = Frame {
            width: 2,
            height: 2,
            linear: &[[0.0; 3]; 4],
            escaped: &[true; 4],
            near: &[1.0; 4],
            heights: &[],
        };
        assert!(mosaic(&fine, &frame, &map()).is_err());
    }

    /// A dark frame with one bright sample at `(col, row)`, through a rays pass.
    fn rayed(rays: &Rays, width: usize, height: usize, col: usize, row: usize) -> Vec<[f64; 3]> {
        let mut linear = vec![[0.01, 0.01, 0.01]; width * height];
        linear[row * width + col] = [1.0, 0.5, 0.25];
        let escaped = vec![true; width * height];
        let frame = Frame {
            width,
            height,
            linear: &linear,
            escaped: &escaped,
            near: &[],
            heights: &[],
        };
        super::rays(rays, &frame, &map()).unwrap()
    }

    #[test]
    fn a_streak_runs_both_ways_along_its_row_and_fades() {
        let streak = Rays {
            share: 0.01,
            spokes: 2,
            angle: 0.0,
            length: 0.1,
            ..Rays::default()
        };
        let (width, height) = (64, 16);
        let out = rayed(&streak, width, height, 32, 8);
        let at = |col: usize, row: usize| out[row * width + col];
        // Along the row, both ways, fading with distance and keeping its source's colour.
        assert!(at(33, 8)[0] > at(40, 8)[0] && at(40, 8)[0] > at(60, 8)[0]);
        assert!(at(31, 8)[0] > at(24, 8)[0] && at(24, 8)[0] > 0.02);
        assert!((at(40, 8)[0] - 0.01) > 1.9 * (at(40, 8)[1] - 0.01));
        // Off the row, nothing: a beam at angle 0 is one sample thin.
        for col in 0..width {
            assert_eq!(at(col, 7), [0.01, 0.01, 0.01]);
            assert_eq!(at(col, 9), [0.01, 0.01, 0.01]);
        }
        // The source itself is not lit twice.
        assert_eq!(at(32, 8), [1.0, 0.5, 0.25]);
    }

    #[test]
    fn a_star_casts_a_beam_along_each_spoke_and_none_between() {
        let star = Rays {
            share: 0.01,
            spokes: 4,
            angle: 45.0,
            length: 0.2,
            ..Rays::default()
        };
        let (width, height) = (48, 48);
        let out = rayed(&star, width, height, 24, 24);
        let lit = |col: usize, row: usize| out[row * width + col][0] - 0.01;
        for (col, row) in [(30, 18), (18, 18), (18, 30), (30, 30)] {
            assert!(lit(col, row) > 0.1, "a diagonal at ({col}, {row})");
        }
        for (col, row) in [(30, 24), (24, 18), (18, 24), (24, 30)] {
            assert!(
                lit(col, row).abs() < 1e-9,
                "between spokes at ({col}, {row})"
            );
        }
    }

    #[test]
    fn a_spoke_is_one_beam_at_every_size() {
        // A source a fixed share of the frame wide covers twice the samples on a grid
        // twice as fine; the beam a fixed fraction of the frame past it holds its light.
        let streak = Rays {
            share: 0.05,
            spokes: 2,
            angle: 0.0,
            length: 0.1,
            ..Rays::default()
        };
        let beam_at = |width: usize| {
            let height = width / 4;
            let mut linear = vec![[0.01, 0.01, 0.01]; width * height];
            for row in height / 2 - width / 64..height / 2 + width / 64 {
                for col in width / 4 - width / 64..width / 4 + width / 64 {
                    linear[row * width + col] = [1.0, 1.0, 1.0];
                }
            }
            let escaped = vec![true; width * height];
            let frame = Frame {
                width,
                height,
                linear: &linear,
                escaped: &escaped,
                near: &[],
                heights: &[],
            };
            let out = super::rays(&streak, &frame, &map()).unwrap();
            out[(height / 2) * width + width / 2][0] - 0.01
        };
        let (coarse, fine) = (beam_at(256), beam_at(512));
        assert!(coarse > 0.01, "the beam reaches mid-frame: {coarse}");
        assert!(
            (fine / coarse - 1.0).abs() < 0.1,
            "twice the samples, the same beam: {coarse} then {fine}"
        );
    }

    #[test]
    fn a_shaft_runs_away_from_its_center() {
        let shafts = Rays {
            share: 0.01,
            length: 0.2,
            center: Some([0.0, 0.5]),
            ..Rays::default()
        };
        let (width, height) = (64, 16);
        let out = rayed(&shafts, width, height, 16, 8);
        let lit = |col: usize, row: usize| out[row * width + col][0] - 0.01;
        // A shaft is the mean light behind it: one bright sample in 12.8 dims it to ~1/13.
        assert!(lit(24, 8) > 0.01 && lit(24, 8) > lit(40, 8) && lit(40, 8) > 0.0);
        // Nothing between the source and the center.
        assert!(lit(8, 8).abs() < 1e-9);
    }

    #[test]
    fn rays_refuse_what_they_cannot_draw() {
        for bad in [
            Rays {
                share: 0.0,
                ..Rays::default()
            },
            Rays {
                spokes: 0,
                ..Rays::default()
            },
            Rays {
                length: 3.0,
                ..Rays::default()
            },
            Rays {
                strength: f64::NAN,
                ..Rays::default()
            },
        ] {
            assert!(Pass::Rays(bad).validate().is_err());
        }
        assert!(Pass::Rays(Rays::default()).validate().is_ok());
    }
}
