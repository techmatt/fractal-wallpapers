//! A **style**: a declarative stack of layers over the channels one orbit gives.
//!
//! A named mode ([`crate::mode`]) is one field, or two blended, through the
//! colormap. A style is the next shape up, made for capturing the *feel* of a
//! reference picture rather than one more statistic of the orbit: several
//! channels read off **one** escape loop per sample, each layer turning one of
//! them into colour or into light, and the layers stacked by a blend and an
//! opacity. The stack is data — a style file under `data/styles/` carries it,
//! the render spec's `style` key hands it here — so a new style is mostly a new
//! file, and a new primitive (a channel, a layer kind, a blend) is added only
//! when a reference needs one.
//!
//! **The compositor is a pure per-sample function of the channels, the layer
//! parameters and the colormap**, once the frame-wide stretch of each channel is
//! measured — the same measure-then-samples split the explorer already makes for
//! the named colorings. Nothing here reads a neighbouring sample: the one thing
//! that looks like it must, a surface normal, is read analytically off the orbit
//! (`z` and `dz` at the escape), so a band of rows composites to the same bytes
//! as the whole frame and the explorer can port it by porting this file.
//!
//! What the channels are:
//!
//! ```text
//! any FieldSpec    smooth, decomposition, de, threads, trap_cross, stripe, … —
//!                  the field catalog read as channels, each its own reduce()
//! gradient         the unit direction ∇ν points, from w = dz/z: (−Re w, Im w);
//!                  the light layer's normal is built on it
//! ```
//!
//! The layer kinds, in the order a stack usually has them:
//!
//! ```text
//! palette   a channel through the existing leveled spend → the colormap
//! light     the stack so far, lit: a height read off a channel, banded into
//!           rings, a Blinn–Phong highlight and a rim, on the gradient's normal
//! glow      a channel as an alpha, a constant or palette colour blended through it
//! pattern   a checker of escape bands × escape-angle sectors, as an alpha
//! ```
//!
//! Every layer may carry a `mask`, a channel read as an extra alpha. Blends are
//! [`Blend`]'s, applied per channel in linear light on values clamped to `[0, 1]`.
//! The spec's own `palette` keeps the bake (`mirror`, `reverse`) and the rolloff;
//! where on the map each layer lands is that layer's (`palette`'s `cycles`,
//! `gamma`, `phase`, `transfer`).

use num_complex::Complex;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};

use crate::coloring::{
    self, Blend, Painted, Palette, Rolloff, Spend, Stretch, Transfer, Transform,
};
use crate::colormap::{Bake, Colormap, srgb_to_linear};
use crate::family::Family;
use crate::field::{Field, FieldSpec};
use crate::iterate::{self, Wants};
use crate::projection::Projection;
use crate::viewport::Viewport;

/// A style as the render spec carries it: the stack, and what the set's inside is.
///
/// Everything a style *file* says beyond this — its reference image, what it
/// reuses, its suggested map — is provenance for a reader and never reaches the
/// engine; the CLI strips it.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Style {
    pub name: String,
    /// The colour of a sample whose orbit never escaped. Black when absent.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub interior: Option<Paint>,
    pub layers: Vec<Layer>,
    /// The frame's tonal balance, held after the stack is composited. Absent: the
    /// stack's own balance, whatever the location makes of it.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tone: Option<Tone>,
    /// Where each sample looks: a per-sample pre-map of the frame before anything is
    /// iterated ([`crate::projection`]). Absent: the straight view.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub projection: Option<Projection>,
}

/// Per-frame tonal normalisation: the composite's median lightness moved to `median`,
/// and optionally its 10th percentile to `p10`.
///
/// A stack fitted on one location is fitted to that location's share of field
/// against structure; at a location with more far field the same stack draws a
/// paler (or darker) picture, and the style's balance does not hold. This is the
/// one frame-wide measurement taken of the **composite** rather than of a channel:
/// the median of CIE `L*` (over 100) across the finished picture — each pixel its
/// block of supersamples averaged, not the samples themselves ([`toned`]) — and then every
/// sample's lightness goes through the one curve `L ↦ b + (1 − b)·L^g` that carries
/// that median to the target, its hue and chroma ratios kept (each linear channel
/// scaled by the change in luminance, so a lifted saturated colour can clip at the
/// encode). The curve always fixes 1, so a highlight stays a highlight. Without a
/// `p10` the floor `b` is 0 and black stays black, so only the middle moves; with
/// one, `b` lifts the darks (a black becomes a grey of lightness `b`) or, below 0,
/// crushes the deepest of them to black.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Tone {
    /// The target median lightness, CIE `L*` over 100, in `(0, 1)`.
    pub median: f64,
    /// The target 10th-percentile lightness, below the median. With it the curve
    /// is `L ↦ b + (1 − b)·L^g`, the two constants solved so both the median and
    /// the shadows land: the floor `b` lifts (or sinks) the darks, so the frame's
    /// contrast is held as well as its key. Without it `b` is 0.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub p10: Option<f64>,
    /// A flame fractal's log-density curve, laid on the composite before its
    /// lightness is measured: each sample's luminance `Y` becomes
    /// `ln(1 + k·Y) / ln(1 + k)`, its hue kept (a colour too saturated to be lifted
    /// that far whitens instead, [`lifted`]; [`log_density`]). A faint thread
    /// is lifted by far more than a bright one, so faint structure beside a hot
    /// core stays visible, and the median and p10 targets are then met on the
    /// compressed frame. Absent: no curve.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub log_density: Option<f64>,
}

/// The log-density curve [`Tone::log_density`] lays on a luminance in `[0, 1]`:
/// `ln(1 + k·Y) / ln(1 + k)`, which fixes 0 and 1 and lifts everything between.
pub fn log_density(luminance: f64, k: f64) -> f64 {
    (k * luminance.clamp(0.0, 1.0)).ln_1p() / k.ln_1p()
}

/// A colour in `[0, 1]` of luminance `before` carried to luminance `after ≥ before`
/// without clipping a channel: scaled while its brightest channel allows, then mixed
/// towards white for the rest, so its hue holds and only a colour too saturated to
/// be lifted that far loses chroma, the way an overexposed highlight does.
fn lifted(rgb: [f64; 3], before: f64, after: f64) -> [f64; 3] {
    let after = after.clamp(before, 1.0);
    let peak = rgb.iter().cloned().fold(0.0, f64::max);
    let scale = (after / before).min(1.0 / peak);
    let scaled = rgb.map(|c| c * scale);
    let reached = before * scale;
    if after - reached <= 1e-12 || reached >= 1.0 {
        return scaled;
    }
    let t = (after - reached) / (1.0 - reached);
    scaled.map(|c| c + (1.0 - c) * t)
}

/// The farthest a tone curve's exponent goes either way: a frame a stack draws
/// almost all white or all black is a stack wrong for it, not one to rescue.
const TONE_LIMIT: f64 = 8.0;

/// A channel and the curve its stretched position goes through: a field of the
/// catalog, the inside channel, the radial channel or a bubble — exactly one.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Source {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub field: Option<FieldSpec>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub inside: Option<Inside>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub radial: Option<Radial>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub bubble: Option<Bubble>,
    #[serde(default)]
    pub transform: Transform,
    /// Read the channel from the other end: `1 − position`, before the curve.
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub invert: bool,
}

impl Source {
    /// A stretched position in `[0, 1]` through the invert and the curve.
    pub fn curve(&self, position: f64) -> f64 {
        let position = position.clamp(0.0, 1.0);
        self.transform.apply(if self.invert {
            1.0 - position
        } else {
            position
        })
    }
}

/// The one channel that is not read off the orbit: how **near** each sample is to
/// a point of the frame — its distance in frame heights, negated, so a circle is
/// round at any aspect and the frame's stretch puts the core at 1 and the farthest
/// corner at 0, the end most maps keep their light colours at.
///
/// A picture whose hue and brightness fall away from a core — a whirl around a
/// bright centre — is coloured by *where* a sample is as much as by what its orbit
/// did, and no field says that: the smooth count is as high on every arm's edge as
/// at the core. Defined on every sample, inside the set too.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct Radial {
    /// The core, as fractions of the frame from its top-left corner.
    pub center: [f64; 2],
}

impl Default for Radial {
    fn default() -> Radial {
        Radial { center: [0.5, 0.5] }
    }
}

/// The one channel a style reads **inside** the set: `−ln min|zₙ|` over the first
/// `iterations` steps of an orbit that never escaped, with its own gradient.
///
/// The smooth count says nothing inside, so a style that left the inside to a flat
/// colour drew every bulb as a hole. The closest approach to the critical point is
/// what an interior orbit does have: it climbs without bound towards each preimage
/// of a superattracting cycle's nucleus, so its level sets are the nested rings an
/// interior "atom" colouring shows, and it is differentiable — the gradient comes
/// from `z` and `dz` at the step the minimum was taken, exactly as the smooth
/// count's does at the escape. `NaN` on every sample that escaped.
///
/// It costs a second orbit, run only for interior samples and only this far.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct Inside {
    pub iterations: u32,
}

impl Default for Inside {
    fn default() -> Inside {
        Inside { iterations: 1000 }
    }
}

/// The **bubble** trap: the disc `|z − center| < radius`, read at the step the orbit
/// enters it for the `hit`-th time.
///
/// The circle trap ([`FieldSpec::TrapCircle`]) keeps the orbit's closest pass to a
/// circle, which draws rings that cross and merge. Reading the disc at an **entry**
/// draws discs instead: the samples whose orbit first lands in the disc at step `n`
/// are a conformal preimage of the disc under `n` steps, so each is a round bubble,
/// and the bubbles of every later step fill the gaps the earlier ones leave — a
/// circle packing, the smallest crowding into the cusps where two meet. Within one
/// bubble, `z` at the entry runs over the whole disc, so `1 − |z − center|/radius`
/// is a dome over it (`height`), its angle a set of rays from its middle (`angle`),
/// and the step a number per bubble (`step`). A later `hit` is the same disc
/// entered again after the orbit left it: a packing of smaller bubbles *inside*
/// each bubble of the hit before.
///
/// Its own loop, like [`Inside`]'s, because the gradient needs `dz` at the chosen
/// step; it stops at the entry, so a sample's cost is its step, not the cap. `NaN`
/// on a sample whose orbit escapes or runs out of steps before the entry.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct Bubble {
    /// The disc's centre, a point of the orbit's plane `[re, im]`.
    pub center: [f64; 2],
    pub radius: f64,
    /// Which entry: 1 is the first time the orbit lands in the disc.
    pub hit: u32,
    pub read: BubbleRead,
    /// Repeat the disc on a square lattice of this spacing through `center`, so the
    /// trap is every disc `|z − center − spacing·(j + ik)| < radius`. One disc is a
    /// target an orbit can miss for good; a lattice of them is one almost every orbit
    /// lands in sooner or later, so the bubbles fill the frame. Absent: the one disc.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub spacing: Option<f64>,
    /// Read only orbits that escape: inside the set the channel is `NaN`. A bounded
    /// orbit falls into its attracting cycle, and where that cycle sits in a disc,
    /// every sample of the basin enters it — one smeared bubble over the whole
    /// component rather than a packing, which the inside channel paints better.
    #[serde(skip_serializing_if = "std::ops::Not::not")]
    pub escaped: bool,
    /// The largest bubble drawn, as a fraction of the frame's width: an entry whose
    /// disc pulls back larger than that (`radius / |dz| > largest · width`, `dz` the
    /// orbit's derivative in the pixel) is passed over, not counted. Deep in a zoom
    /// every early step's disc pulls back far larger than the frame and draws one
    /// straight edge across it; with this the packing starts at a frame-relative size
    /// wherever the frame is, as a glow's `falloff` does. Absent: every entry counts.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub largest: Option<f64>,
    /// The **face**: a smaller disc inside each bubble, internally tangent to its rim,
    /// its centre moved from the bubble's by `shift` (a vector in radii, of length
    /// below 1) and its radius `(1 − |shift|)·radius`. What the `crescent` read paints
    /// is the lune between the two: widest opposite the shift, nothing where the face
    /// touches the rim. The shift is in the disc's own plane, so each bubble's pullback
    /// turns it by its own `arg dz`: the crescents face every way. Absent: no face.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub shift: Option<[f64; 2]>,
}

impl Default for Bubble {
    fn default() -> Bubble {
        Bubble {
            center: [0.0, 0.0],
            radius: 1.0,
            hit: 1,
            read: BubbleRead::Height,
            spacing: None,
            escaped: false,
            largest: None,
            shift: None,
        }
    }
}

impl Bubble {
    /// The loop this reads: every read of one disc and hit shares it.
    fn trap(&self) -> Bubble {
        Bubble {
            read: BubbleRead::Height,
            ..*self
        }
    }
}

/// What a bubble channel reads off the entry.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BubbleRead {
    /// `1 − |z − center|/radius`: 1 at the bubble's middle, 0 at its rim. Its
    /// gradient points inwards, so a light at `period` 2 lights each bubble as a
    /// hemisphere, and a glow on it inverted is a bright rim.
    #[default]
    Height,
    /// The step of the entry: one number per bubble, larger for the smaller
    /// bubbles in the cusps.
    Step,
    /// The angle of `z − center` at the entry, as a fraction of a turn: rays from
    /// each bubble's middle, which a sheet cuts into a star.
    Angle,
    /// Across the lune between the rim and the face ([`Bubble::shift`]): 0 at the
    /// face's edge, 1 at the rim, `NaN` on the face. Its gradient points across the
    /// band towards the rim, so a light lights each lune as a curved band — on the
    /// early, large bubbles a ribbon sweeping the frame.
    Crescent,
}

/// How many reads a bubble loop has, one lane each.
const BUBBLE_READS: usize = 4;

/// Which lane a source reads.
#[derive(Clone, Copy, Debug, PartialEq)]
enum Key {
    Field(FieldSpec),
    Inside,
    Radial([f64; 2]),
    Bubble(Bubble),
}

impl Source {
    fn key(&self) -> Key {
        match (self.field, self.radial, self.bubble) {
            (Some(field), _, _) => Key::Field(field),
            (None, Some(radial), _) => Key::Radial(radial.center),
            (None, None, Some(bubble)) => Key::Bubble(bubble),
            (None, None, None) => Key::Inside,
        }
    }
}

/// A colour a layer paints with: a literal sRGB hex, or a position on the map.
///
/// The map position is what lets a style follow whatever palette it is given — a
/// glow that is "the map's far end" stays in key with any map, where a literal
/// white is the same white under all of them.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case", deny_unknown_fields)]
pub enum Paint {
    Rgb(String),
    Palette(f64),
}

/// What a layer does.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Kind {
    Palette,
    Light,
    Glow,
    Pattern,
    Sheet,
}

/// One layer of the stack. Which members a kind takes is checked in
/// [`Style::validate`], so a member given to a kind that ignores it is refused
/// rather than silently dropped.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Layer {
    pub kind: Kind,
    #[serde(default = "normal")]
    pub blend: Blend,
    #[serde(default = "one")]
    pub opacity: f64,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub mask: Option<Mask>,
    /// The channel the layer reads: the palette position, the light's height,
    /// the glow's alpha. Not on a pattern.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub channel: Option<Source>,
    /// `palette` only: where on the map the channel lands.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub palette: Option<Palette>,
    /// `light` only.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub light: Option<Light>,
    /// `glow` and `pattern`: what they paint.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub color: Option<Paint>,
    /// `glow` only: the alpha is the channel's position to this power.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub power: Option<f64>,
    /// `glow` on the distance estimate only: read the channel as a length rather
    /// than a frame-wide stretch, its position `exp(−d / falloff)` with `d` the
    /// distance to the set in frame widths ([`falloff`]).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub falloff: Option<f64>,
    /// `pattern` only.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub checker: Option<Checker>,
    /// `sheet` only.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub sheet: Option<Sheet>,
    /// `palette` only: a second channel that bends where on the map the first lands.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub warp: Option<Warp>,
}

impl Layer {
    /// Every channel the layer reads: its own, its mask's and its warp's.
    fn sources(&self) -> impl Iterator<Item = &Source> {
        self.channel
            .iter()
            .chain(self.mask.iter().map(|m| &m.channel))
            .chain(self.warp.iter().map(|w| &w.channel))
    }
}

/// A palette layer's position bent by a second channel: the warp channel's rank in
/// the frame, centred on 0, times `amount`, is added to the position before the map
/// is read (and the sum clamped to `[0, 1]`).
///
/// A palette laid along the radial channel draws concentric rings of the map, which
/// with the map a style was fitted to is a glow, and with a map whose colours are not
/// in lightness order is a target. Bending the position by the structure — the
/// smooth count, the distance estimate — makes the rings follow the arms, so the hue
/// still falls away from the core but along the picture's own shapes.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Warp {
    pub channel: Source,
    pub amount: f64,
}

/// A stack of translucent sheets cut from one channel: the field read as nested
/// shells, each a faint film whose far edge is a bright rim.
///
/// The channel's position is cut into `bands` equal steps, offset by `phase` (in
/// bands). Across each step `p` runs `0 → 1`, and the sheet's alpha is
/// `fill·p + (1 − fill)·exp(−(1 − p)/edge)`: a face that rises gently across the
/// step, a rim at full at its far edge, and a drop to the next sheet's face — a
/// scooped cavity under a lit lip. One band of an inverted channel is a glow that
/// falls off exponentially from wherever the channel is lowest. Where the field turns sharply the steps crowd together
/// and so do the rims, so the brightness lands on creases and edges and the flat
/// stretches stay dim; that is the whole of how the picture gets its glass webbing,
/// and several sheets on different channels, or one channel at different `bands`,
/// overlap into it. Without a `color` a sheet paints the stack beneath it, so under
/// `screen` it lightens in whatever hue the stack already has.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct Sheet {
    pub bands: f64,
    pub phase: f64,
    /// The rim's width, as a fraction of a step.
    pub edge: f64,
    /// How far the face rises towards its rim, in `[0, 1]`: the face's alpha
    /// climbs linearly from 0 at its near edge to `fill`, the scoop.
    pub fill: f64,
    /// Cut the steps by the sample's rank in the frame (the default), so each
    /// sheet covers an equal share of the picture wherever the frame is; `false`
    /// cuts them by the channel's stretch, equal spans of value.
    pub rank: bool,
    /// Cut a step every `period` of the channel's **raw** value instead, neither
    /// rank nor stretch (and `bands` unread): see [`Light::period`].
    #[serde(skip_serializing_if = "Option::is_none")]
    pub period: Option<f64>,
}

impl Default for Sheet {
    fn default() -> Sheet {
        Sheet {
            bands: 8.0,
            phase: 0.0,
            edge: 0.08,
            fill: 0.05,
            rank: true,
            period: None,
        }
    }
}

/// Where in its step a raw value sits, for a layer cut every `period` of the
/// channel's own value: `value / period + phase`, wrapped into `[0, 1)`.
///
/// A frame-wide cut (the rank, the stretch) spends its steps over whatever range the
/// frame holds, so a view that runs ever deeper — the log-polar view, whose smooth
/// count climbs by the same amount every octave inwards, without end — gets its
/// steps smeared across the deep end. A cut in the value's own units is the same
/// at every octave: at `period` 1 on the smooth count, one step per escape step,
/// each step an equipotential ring, and the rings tile the self-similar view.
pub fn periodic(value: f64, period: f64, phase: f64) -> f64 {
    (value / period + phase).rem_euclid(1.0)
}

impl Sheet {
    /// The sheet's alpha at a channel position in `[0, 1]`.
    pub fn alpha(&self, position: f64) -> f64 {
        let x = position * self.bands + self.phase;
        // The top of the range is approached from below: a sample the stretch
        // clipped to exactly 1 sits on the last rim, not at the foot of a face the
        // wrap would otherwise start — which, on an inverted channel, is the line
        // the glow is brightest along.
        let p = if position >= 1.0 {
            1.0 - (-x).rem_euclid(1.0)
        } else {
            x.rem_euclid(1.0)
        };
        self.fill * p + (1.0 - self.fill) * (-(1.0 - p) / self.edge).exp()
    }
}

/// A glow's position at distance `d` from the set, both it and `width` in frame
/// widths: `exp(−d / width)`, 1 on the set and `1/e` one `width` away.
///
/// A frame-wide stretch of the distance estimate spends its range on whatever the
/// frame holds, so a frame with one far void and a frame of dense filigree draw
/// their threads at different widths, and the stretch's nearly-zero end crowds
/// every thread into the same few percent. Read as a length, the distance is the
/// same at every location and resolution: a thread is `width` of the frame wide,
/// its core at full and its halo falling off exponentially, the way a flame
/// fractal's luminous strands look. Two glows on the one channel at a hair's
/// `width` and a wide one draw the hot core and the bloom round it.
pub fn falloff(distance: f64, width: f64) -> f64 {
    (-distance.max(0.0) / width).exp()
}

/// A channel read as an extra alpha on a layer.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Mask {
    pub channel: Source,
    #[serde(default)]
    pub invert: bool,
    #[serde(default = "one")]
    pub power: f64,
}

/// A lit height field: the channel's position is the height, banded into rings.
///
/// The normal is never differenced off neighbours. Its direction in the plane is
/// the **gradient** channel — the way the smooth count climbs, read off `dz/z` —
/// and how far it tilts is a profile of the height: a `slope` that tilts every
/// sample the same way up the field, and a `rings` profile that is a cylinder's
/// cross-section across each of `bands` equal steps of the height, so each band
/// reads as a glass tube with its highlight on the side facing the light.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct Light {
    /// Rings across the frame's height range.
    pub bands: f64,
    /// How much of the normal is the ring's tube, in `[0, 1]`; the rest is flat.
    pub rings: f64,
    /// A constant tilt up the field, so the stack reads as one rising surface.
    pub slope: f64,
    /// Where the light comes from, degrees anticlockwise from the plane's +x.
    pub azimuth: f64,
    /// And how high, degrees above the plane.
    pub elevation: f64,
    pub ambient: f64,
    pub diffuse: f64,
    pub specular: f64,
    pub shininess: f64,
    /// A Fresnel-like brightening where the surface turns away from the viewer.
    pub rim: f64,
    pub rim_power: f64,
    /// The highlight's colour. White when absent.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub highlight: Option<Paint>,
    /// Cut a ring every `period` of the channel's **raw** value instead of `bands`
    /// across the frame's stretch ([`periodic`]); the channel's curve and invert
    /// then shape the height within each ring. On the smooth count at 1, every
    /// ring is one escape step: equipotential tubes, the same at every depth.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub period: Option<f64>,
}

impl Default for Light {
    fn default() -> Light {
        Light {
            bands: 8.0,
            rings: 0.7,
            slope: 0.2,
            azimuth: 135.0,
            elevation: 45.0,
            ambient: 0.5,
            diffuse: 0.6,
            specular: 0.6,
            shininess: 30.0,
            rim: 0.0,
            rim_power: 3.0,
            highlight: None,
            period: None,
        }
    }
}

/// A checker over the escape: bands of the smooth count across, sectors of the
/// escape angle along — binary decomposition at `sectors: 2`.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct Checker {
    /// Cells per unit of the smooth count, across the equipotentials.
    pub per_iteration: f64,
    /// Cells per turn of the escape angle, along the field lines.
    pub sectors: u32,
}

impl Default for Checker {
    fn default() -> Checker {
        Checker {
            per_iteration: 1.0,
            sectors: 2,
        }
    }
}

fn normal() -> Blend {
    Blend::Normal
}

fn one() -> f64 {
    1.0
}

impl Paint {
    fn linear(&self, colormap: &Colormap) -> [f64; 3] {
        match self {
            Paint::Rgb(hex) => parse_hex(hex)
                .map(|rgb| rgb.map(|c| srgb_to_linear(c as f64 / 255.0)))
                .unwrap_or([0.0; 3]),
            Paint::Palette(t) => colormap.lookup(*t),
        }
    }

    fn validate(&self, what: &str) -> Result<(), String> {
        match self {
            Paint::Rgb(hex) => parse_hex(hex)
                .map(|_| ())
                .ok_or_else(|| format!("{what}: '{hex}' is not a #rrggbb colour")),
            Paint::Palette(t) if !(0.0..=1.0).contains(t) => {
                Err(format!("{what}: a palette position is in [0, 1], got {t}"))
            }
            Paint::Palette(_) => Ok(()),
        }
    }
}

fn parse_hex(text: &str) -> Option<[u8; 3]> {
    let digits = text.strip_prefix('#')?;
    if digits.len() != 6 || !digits.is_ascii() {
        return None;
    }
    let byte = |at: usize| u8::from_str_radix(&digits[at..at + 2], 16).ok();
    Some([byte(0)?, byte(2)?, byte(4)?])
}

impl Style {
    /// Refuse a stack that would draw something other than what it says.
    pub fn validate(&self) -> Result<(), String> {
        if self.layers.is_empty() {
            return Err(format!("style '{}' has no layers", self.name));
        }
        if let Some(paint) = &self.interior {
            paint.validate("style interior")?;
        }
        if let Some(projection) = &self.projection {
            projection
                .validate()
                .map_err(|refusal| format!("style '{}': {refusal}", self.name))?;
        }
        if let Some(tone) = self.tone {
            if !(tone.median > 0.0 && tone.median < 1.0) {
                return Err(format!(
                    "style '{}': tone median is a lightness in (0, 1), got {}",
                    self.name, tone.median
                ));
            }
            if tone
                .p10
                .is_some_and(|p10| !(p10 >= 0.0 && p10 < tone.median))
            {
                return Err(format!(
                    "style '{}': tone p10 is a lightness in [0, median)",
                    self.name
                ));
            }
            if tone
                .log_density
                .is_some_and(|k| !(k.is_finite() && k > 0.0))
            {
                return Err(format!(
                    "style '{}': tone log_density is a positive gain",
                    self.name
                ));
            }
        }
        let mut sigmas = Vec::new();
        for (index, layer) in self.layers.iter().enumerate() {
            let at = format!("style '{}' layer {index} ({:?})", self.name, layer.kind);
            if !(0.0..=1.0).contains(&layer.opacity) {
                return Err(format!("{at}: opacity is in [0, 1], got {}", layer.opacity));
            }
            let period = (layer.light.as_ref().and_then(|light| light.period))
                .or(layer.sheet.and_then(|sheet| sheet.period));
            if period.is_some_and(|period| !(period.is_finite() && period > 0.0)) {
                return Err(format!(
                    "{at}: period is a positive number of the channel's units"
                ));
            }
            let allowed: &[&str] = match layer.kind {
                Kind::Palette => &["channel", "palette", "warp"],
                Kind::Light => &["channel", "light"],
                Kind::Glow => &["channel", "color", "power", "falloff"],
                Kind::Pattern => &["color", "checker"],
                Kind::Sheet => &["channel", "sheet", "color"],
            };
            for (name, present) in [
                ("channel", layer.channel.is_some()),
                ("palette", layer.palette.is_some()),
                ("light", layer.light.is_some()),
                ("color", layer.color.is_some()),
                ("power", layer.power.is_some()),
                ("falloff", layer.falloff.is_some()),
                ("checker", layer.checker.is_some()),
                ("sheet", layer.sheet.is_some()),
                ("warp", layer.warp.is_some()),
            ] {
                if present && !allowed.contains(&name) {
                    return Err(format!("{at}: a {:?} layer takes no '{name}'", layer.kind));
                }
            }
            if layer.kind != Kind::Pattern && layer.channel.is_none() {
                return Err(format!("{at}: needs a 'channel'"));
            }
            if matches!(layer.kind, Kind::Glow | Kind::Pattern) && layer.color.is_none() {
                return Err(format!("{at}: needs a 'color'"));
            }
            if let Some(color) = &layer.color {
                color.validate(&at)?;
            }
            if let Some(power) = layer.power {
                if !(power.is_finite() && power > 0.0) {
                    return Err(format!("{at}: power must be positive, got {power}"));
                }
            }
            if let Some(falloff) = layer.falloff {
                if !(falloff.is_finite() && falloff > 0.0) {
                    return Err(format!(
                        "{at}: falloff is a positive fraction of the frame width, got {falloff}"
                    ));
                }
                match layer.channel.and_then(|source| source.field) {
                    Some(FieldSpec::De { scale }) if scale.is_finite() && scale > 0.0 => {}
                    Some(FieldSpec::De { .. }) => {
                        return Err(format!(
                            "{at}: a falloff divides the estimate's scale out; it must be positive"
                        ));
                    }
                    _ => {
                        return Err(format!(
                            "{at}: a falloff reads a length, so its channel is the field 'de'"
                        ));
                    }
                }
            }
            if let Some(palette) = &layer.palette {
                palette.validate()?;
                if palette.bake != Bake::default() || palette.rolloff != Rolloff::None {
                    return Err(format!(
                        "{at}: mirror, reverse and rolloff are the spec's palette, not a \
                         layer's — the map is baked once for the whole stack"
                    ));
                }
            }
            if layer.kind == Kind::Light {
                if layer.blend != Blend::Normal {
                    return Err(format!(
                        "{at}: a light layer relights the stack; its blend is normal"
                    ));
                }
                let light = layer.light.clone().unwrap_or_default();
                if !(light.bands.is_finite() && light.bands > 0.0) {
                    return Err(format!("{at}: bands must be positive"));
                }
                if !(0.0..=1.0).contains(&light.rings) {
                    return Err(format!("{at}: rings is in [0, 1]"));
                }
                if !(light.shininess > 0.0 && light.rim_power > 0.0) {
                    return Err(format!("{at}: shininess and rim_power must be positive"));
                }
                if let Some(paint) = &light.highlight {
                    paint.validate(&at)?;
                }
            }
            if let Some(checker) = layer.checker {
                if checker.sectors == 0
                    || !checker.per_iteration.is_finite()
                    || checker.per_iteration <= 0.0
                {
                    return Err(format!(
                        "{at}: a checker needs sectors >= 1 and per_iteration > 0"
                    ));
                }
            }
            if let Some(sheet) = layer.sheet {
                if !(sheet.bands.is_finite() && sheet.bands > 0.0)
                    || !(sheet.edge.is_finite() && sheet.edge > 0.0)
                    || !sheet.phase.is_finite()
                    || !(0.0..=1.0).contains(&sheet.fill)
                {
                    return Err(format!(
                        "{at}: a sheet needs bands > 0, edge > 0, a finite phase and fill in [0, 1]"
                    ));
                }
            }
            if layer.warp.is_some_and(|warp| !warp.amount.is_finite()) {
                return Err(format!("{at}: a warp's amount must be finite"));
            }
            if let Some(mask) = layer.mask {
                if !(mask.power.is_finite() && mask.power > 0.0) {
                    return Err(format!("{at}: mask power must be positive"));
                }
            }
            if layer.kind == Kind::Light && layer.channel.is_some_and(|s| s.radial.is_some()) {
                return Err(format!(
                    "{at}: a light needs a channel read off the orbit, which has a gradient; \
                     radial has none"
                ));
            }
            for source in layer.sources() {
                match (source.field, source.inside, source.radial, source.bubble) {
                    (Some(_), None, None, None) => {}
                    (None, Some(inside), None, None) if inside.iterations > 0 => {}
                    (None, Some(_), None, None) => {
                        return Err(format!("{at}: inside needs iterations >= 1"));
                    }
                    (None, None, Some(radial), None)
                        if radial.center.iter().all(|c| c.is_finite()) => {}
                    (None, None, Some(_), None) => {
                        return Err(format!("{at}: a radial centre is two finite fractions"));
                    }
                    (None, None, None, Some(bubble))
                        if bubble.hit >= 1
                            && bubble.radius.is_finite()
                            && bubble.radius > 0.0
                            && bubble.center.iter().all(|c| c.is_finite())
                            && bubble.spacing.is_none_or(|s| s.is_finite() && s > 0.0)
                            && bubble.largest.is_none_or(|l| l.is_finite() && l > 0.0)
                            && bubble.shift.is_none_or(|[x, y]| {
                                let length = x.hypot(y);
                                length.is_finite() && length > 0.0 && length < 1.0
                            })
                            && (bubble.read != BubbleRead::Crescent || bubble.shift.is_some()) => {}
                    (None, None, None, Some(_)) => {
                        return Err(format!(
                            "{at}: a bubble needs hit >= 1, a positive radius, spacing and largest, \
                             a finite centre, a shift of length in (0, 1), and a shift to read a crescent"
                        ));
                    }
                    _ => {
                        return Err(format!(
                            "{at}: a channel names exactly one of 'field', 'inside', 'radial' \
                             and 'bubble'"
                        ));
                    }
                }
                match source.field.unwrap_or(FieldSpec::Smooth) {
                    FieldSpec::Itinerary { .. } => {
                        return Err(format!(
                            "{at}: itinerary is not a style channel — its value is an address \
                             whose deep digits a stretch through f32 would lose"
                        ));
                    }
                    FieldSpec::Threads { sigma } => sigmas.push(sigma),
                    _ => {}
                }
            }
        }
        // One escape loop feeds every channel, and it accumulates one threads kernel.
        sigmas.dedup();
        if sigmas.len() > 1 {
            return Err(format!(
                "style '{}' asks for threads at {} kernel widths; one loop carries one",
                self.name,
                sigmas.len()
            ));
        }
        Ok(())
    }

    /// Every field a layer reads, once each, in first-use order.
    fn fields(&self) -> Vec<FieldSpec> {
        let mut fields = vec![FieldSpec::Smooth];
        let mut take = |field: FieldSpec| {
            if !fields.contains(&field) {
                fields.push(field);
            }
        };
        for layer in &self.layers {
            if let Some(field) = layer.channel.and_then(|source| source.field) {
                take(field);
            }
            if let Some(field) = layer.mask.and_then(|mask| mask.channel.field) {
                take(field);
            }
            if let Some(field) = layer.warp.and_then(|warp| warp.channel.field) {
                take(field);
            }
            if layer.kind == Kind::Pattern {
                take(FieldSpec::Decomposition);
            }
        }
        fields
    }

    fn lights(&self) -> bool {
        self.layers.iter().any(|layer| layer.kind == Kind::Light)
    }

    /// How far the inside channel runs, when any layer reads it: the longest asked.
    fn inside(&self) -> Option<u32> {
        self.layers
            .iter()
            .flat_map(|layer| layer.sources())
            .filter_map(|source| source.inside.map(|inside| inside.iterations))
            .max()
    }

    /// Every bubble loop a layer reads (one per disc and hit), once each, and the
    /// reads asked of it: height, step, angle, crescent.
    fn bubbles(&self) -> Vec<(Bubble, [bool; BUBBLE_READS])> {
        let mut traps: Vec<(Bubble, [bool; BUBBLE_READS])> = Vec::new();
        for source in self.layers.iter().flat_map(|layer| layer.sources()) {
            let Some(bubble) = source.bubble else {
                continue;
            };
            let trap = bubble.trap();
            let at = match traps.iter().position(|(t, _)| *t == trap) {
                Some(at) => at,
                None => {
                    traps.push((trap, [false; BUBBLE_READS]));
                    traps.len() - 1
                }
            };
            traps[at].1[bubble.read as usize] = true;
        }
        traps
    }

    /// Every radial centre a layer reads, once each.
    fn radials(&self) -> Vec<[f64; 2]> {
        let mut centers: Vec<[f64; 2]> = Vec::new();
        for layer in &self.layers {
            for source in layer.sources() {
                if let Some(radial) = source.radial {
                    if !centers.contains(&radial.center) {
                        centers.push(radial.center);
                    }
                }
            }
        }
        centers
    }
}

/// The radial channel of one sample: its distance from `center`, in frame heights.
pub fn radial(center: [f64; 2], col: u32, row: u32, width: u32, height: u32) -> f64 {
    let (width, height) = (width as f64, height as f64);
    let x = (col as f64 + 0.5 - center[0] * width) / height;
    let y = (row as f64 + 0.5 - center[1] * height) / height;
    x.hypot(y)
}

/// What one escape loop left per sample: a lane per field, and the gradients.
struct Channels {
    fields: Vec<FieldSpec>,
    lanes: Vec<Vec<f32>>,
    /// Unit `∇ν` in the plane, `NaN` where the orbit did not escape.
    gradient: Vec<[f32; 2]>,
    /// The inside channel, and its unit gradient; `NaN` where the orbit escaped.
    inside: Vec<f32>,
    inside_gradient: Vec<[f32; 2]>,
    /// One lane per radial centre the stack reads.
    radials: Vec<([f64; 2], Vec<f32>)>,
    /// One entry per bubble loop: its reads (empty where unasked), the height's unit
    /// gradient (empty without a light) and the crescent's (empty unless both asked).
    bubbles: Vec<BubbleLanes>,
    interior_fraction: f64,
}

struct BubbleLanes {
    trap: Bubble,
    reads: [Vec<f32>; BUBBLE_READS],
    gradient: Vec<[f32; 2]>,
    crescent_gradient: Vec<[f32; 2]>,
}

impl Channels {
    fn lane(&self, key: Key) -> &[f32] {
        match key {
            Key::Inside => &self.inside,
            Key::Radial(center) => {
                &self
                    .radials
                    .iter()
                    .find(|(c, _)| *c == center)
                    .expect("every radial centre a layer reads was gathered")
                    .1
            }
            Key::Field(field) => {
                let index = self
                    .fields
                    .iter()
                    .position(|f| *f == field)
                    .expect("every field a layer reads was gathered");
                &self.lanes[index]
            }
            Key::Bubble(bubble) => &self.bubble(bubble).reads[bubble.read as usize],
        }
    }

    fn bubble(&self, bubble: Bubble) -> &BubbleLanes {
        self.bubbles
            .iter()
            .find(|lanes| lanes.trap == bubble.trap())
            .expect("every bubble a layer reads was gathered")
    }

    fn gradient(&self, key: Key) -> &[[f32; 2]] {
        match key {
            Key::Inside => &self.inside_gradient,
            Key::Field(_) => &self.gradient,
            Key::Bubble(bubble) if bubble.read == BubbleRead::Crescent => {
                &self.bubble(bubble).crescent_gradient
            }
            Key::Bubble(bubble) => &self.bubble(bubble).gradient,
            // Refused by `Style::validate`: radial has no orbit gradient to light.
            Key::Radial(_) => &[],
        }
    }
}

/// The inside channel of one orbit that never escaped, and its unit gradient.
///
/// **Where the orbit falls into `|z| < ε`** — every interior sample of a Julia set
/// whose `c` is a nucleus, and the samples near a minibrot's own nucleus — the value
/// is the escape count turned inside out: a smooth *convergence* count. Near a
/// superattracting cycle through `0`, one period raises `|z|` to the local degree
/// `d`, exactly as one step does near infinity, so the first step `n` inside the
/// disc and the period `p` (the steps to the next arrival) give
/// `s = n − p·log_d(ln|zₙ| / ln ε)`, continuous across each arrival ring. The value
/// is `−s`: highest at the nucleus, falling by one a period outwards, so a layer
/// banding it draws concentric rings into every bulb.
///
/// **Elsewhere** — an attracting cycle that stays away from `0` — it is
/// `asinh(−ln min|zₙ|)` over the first `iterations` steps, the closest approach to
/// the critical point, read at the step it was taken. The two pieces meet in
/// different components, never inside one.
///
/// Both gradients are `−∇ln|z|` at the step read, so [`gradient`] is the formula. Its
/// own loop rather than a channel of [`iterate::run`]: it needs `dz` at one chosen
/// step, which no field keeps, and it runs only for the samples the escape loop
/// already found inside. The recurrence is [`Family::step`]'s, not a copy of it.
pub fn inside(family: &Family, pixel: Complex<f64>, iterations: u32) -> Option<(f64, [f64; 2])> {
    let (mut z, mut z_prev, c) = family.seed(pixel);
    let (mut dz, mut dz_prev) = family.derivative_seed();
    let mut best = (f64::INFINITY, z, dz);
    let mut arrival: Option<(u32, Complex<f64>, Complex<f64>)> = None;
    let mut left = false;
    for n in 1..=iterations {
        let next = family.derivative_step(z, dz, dz_prev);
        dz_prev = dz;
        dz = next;
        let next = family.step(z, z_prev, c);
        z_prev = z;
        z = next;
        let magnitude_sq = z.norm_sqr();
        if magnitude_sq < best.0 {
            best = (magnitude_sq, z, dz);
        }
        match arrival {
            None if magnitude_sq < EPSILON * EPSILON && magnitude_sq > 0.0 => {
                arrival = Some((n, z, dz));
            }
            Some(_) if magnitude_sq >= EPSILON * EPSILON => left = true,
            Some((first, z, dz)) if left => {
                let period = (n - first) as f64;
                let depth = (0.5 * z.norm_sqr().ln()) / EPSILON.ln();
                let count = first as f64 - period * depth.ln() / family.escape_exponent().ln();
                return Some((-count, gradient(z, dz)?));
            }
            _ => {}
        }
    }
    let (magnitude_sq, z, dz) = best;
    if !(magnitude_sq.is_finite() && magnitude_sq > 0.0) {
        return None;
    }
    Some(((-0.5 * magnitude_sq.ln()).asinh(), gradient(z, dz)?))
}

/// The disc an orbit has arrived at the critical point's cycle in.
const EPSILON: f64 = 1e-3;

/// One bubble entry: the step, `z − center` there, and `dz/d(pixel)` there.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Entry {
    pub step: u32,
    pub offset: Complex<f64>,
    pub derivative: Complex<f64>,
}

impl Entry {
    /// The four reads, in [`BubbleRead`]'s order; the crescent is `NaN` off the lune
    /// and on a trap without a face.
    pub fn reads(&self, trap: &Bubble) -> [f64; BUBBLE_READS] {
        let turn = (self.offset.arg() / std::f64::consts::TAU).rem_euclid(1.0);
        let crescent = self.lune(trap).map_or(f64::NAN, |(across, _)| across);
        [
            1.0 - self.offset.norm() / trap.radius,
            self.step as f64,
            turn,
            crescent,
        ]
    }

    /// Where the entry sits across the lune between the rim and the face, and that
    /// position's gradient in the disc's plane, when it is on the lune at all.
    ///
    /// With `a` the distance outside the face's edge and `b` the distance inside the
    /// rim, the position is `a / (a + b)`: 0 at the face, 1 at the rim, the same
    /// fraction of the band's width wherever the band is wide or thin. Its gradient
    /// is `(b·∇a − a·∇b) / (a + b)²`, with `∇a` the unit vector from the face's centre
    /// and `∇b` the unit vector towards the bubble's.
    fn lune(&self, trap: &Bubble) -> Option<(f64, Complex<f64>)> {
        let [x, y] = trap.shift?;
        let shift = Complex::new(x, y) * trap.radius;
        let face = trap.radius * (1.0 - shift.norm() / trap.radius);
        let from_face = self.offset - shift;
        let (a, b) = (from_face.norm() - face, trap.radius - self.offset.norm());
        if !(a > 0.0 && b >= 0.0) {
            return None;
        }
        let along = |v: Complex<f64>| v / v.norm();
        let grad = (along(from_face) * b + along(self.offset) * a) / (a + b).powi(2);
        Some((a / (a + b), grad))
    }

    /// The unit direction the crescent read climbs in the pixel, towards the rim:
    /// the plane gradient pulled back through `dz` (`∇ₚ = conj(dz)·∇`, as in
    /// [`gradient`]).
    pub fn across(&self, trap: &Bubble) -> Option<[f64; 2]> {
        let (_, grad) = self.lune(trap)?;
        let pulled = self.derivative.conj() * grad;
        let length = pulled.norm();
        (length.is_finite() && length > 0.0).then(|| [pulled.re / length, pulled.im / length])
    }

    /// The unit direction the height climbs: towards the bubble's middle. The height
    /// is `1 − |z − center|/radius`, a negative multiple of `ln|z − center|`, so this
    /// is [`gradient`] with the offset in place of `z`.
    pub fn uphill(&self) -> Option<[f64; 2]> {
        gradient(self.offset, self.derivative)
    }
}

/// Where the orbit of `pixel` enters `trap`'s disc for the `hit`-th time, within
/// `maxiter` steps and before it escapes. An entry is a step inside the disc after
/// one outside it; the seed counts as outside, so `z₁` in the disc is the first.
/// `width` is the frame's width in the plane, read only by [`Bubble::largest`].
pub fn bubble(
    family: &Family,
    pixel: Complex<f64>,
    maxiter: u32,
    trap: &Bubble,
    width: f64,
) -> Option<Entry> {
    // |dz| an entry needs for its disc to pull back no larger than `largest` frames.
    let least_sq = trap
        .largest
        .map_or(0.0, |largest| (trap.radius / (largest * width)).powi(2));
    let (mut z, mut z_prev, c) = family.seed(pixel);
    let (mut dz, mut dz_prev) = family.derivative_seed();
    let center = Complex::new(trap.center[0], trap.center[1]);
    let (radius_sq, bailout_sq) = (
        trap.radius * trap.radius,
        iterate::BAILOUT * iterate::BAILOUT,
    );
    let mut was_inside = false;
    let mut hits = 0;
    for step in 1..=maxiter {
        let next = family.derivative_step(z, dz, dz_prev);
        dz_prev = dz;
        dz = next;
        let next = family.step(z, z_prev, c);
        z_prev = z;
        z = next;
        let magnitude_sq = z.norm_sqr();
        if magnitude_sq > bailout_sq || magnitude_sq.is_nan() {
            return None;
        }
        let offset = match trap.spacing {
            None => z - center,
            Some(spacing) => {
                let cell = (z - center) / spacing;
                z - center - Complex::new(cell.re.round(), cell.im.round()) * spacing
            }
        };
        let inside = offset.norm_sqr() < radius_sq;
        if inside && !was_inside && dz.norm_sqr() >= least_sq {
            hits += 1;
            if hits == trap.hit {
                return Some(Entry {
                    step,
                    offset,
                    derivative: dz,
                });
            }
        }
        was_inside = inside;
    }
    None
}

/// The unit direction in which the smooth count climbs, from the escape's `z` and
/// `dz/d(pixel)`.
///
/// `ν = n + 1 − log_d(ln|z|/ln B)`, so `∇ν` is a negative multiple of `∇ln|z|`, and
/// for `z` holomorphic in the pixel `∇ln|z| = (Re w, −Im w)` with `w = z′/z`. The
/// multiple is positive wherever the orbit escaped (`ln|z| > ln B > 0`), so the
/// direction is `(−Re w, Im w)` normalized, and its length — which runs off to
/// infinity at the boundary — is deliberately thrown away: the light layer spends
/// its tilt on the *profile* of the height, not on how steep the count is here.
pub fn gradient(last: Complex<f64>, derivative: Complex<f64>) -> Option<[f64; 2]> {
    let w = derivative / last;
    let (x, y) = (-w.re, w.im);
    let length = x.hypot(y);
    (length.is_finite() && length > 0.0).then(|| [x / length, y / length])
}

fn gather(view: &Viewport, family: &Family, maxiter: u32, style: &Style) -> Channels {
    let fields = style.fields();
    let lights = style.lights();
    let wants = fields
        .iter()
        .map(FieldSpec::wants)
        .fold(Wants::default(), Wants::union);
    // The same proof of interior `field::sweep_row` hands a pass whose every field
    // reads an escape or a statistic a repeat makes final; never the cardioid skips.
    let escape_only = fields.iter().all(|field| {
        matches!(
            field,
            FieldSpec::Smooth
                | FieldSpec::Stripe { .. }
                | FieldSpec::Tia
                | FieldSpec::Curvature
                | FieldSpec::Threads { .. }
                | FieldSpec::ExpSmoothing
                | FieldSpec::Decomposition
                | FieldSpec::De { .. }
        )
    });
    let settle = if escape_only {
        Some(iterate::Interior::of(family))
    } else {
        fields
            .iter()
            .all(FieldSpec::is_final_at_a_repeat)
            .then_some(iterate::Interior::REPEAT)
    };
    let wants = Wants {
        derivative: wants.derivative || lights,
        interior: settle,
        ..wants
    };

    let width = view.sample_width();
    let height = view.sample_height();
    let reach = style.inside();
    let traps = style.bubbles();
    type BubbleRow = ([Vec<f32>; BUBBLE_READS], Vec<[f32; 2]>, Vec<[f32; 2]>);
    type Row = (
        Vec<Vec<f32>>,
        Vec<[f32; 2]>,
        Vec<(f32, [f32; 2])>,
        u64,
        Vec<BubbleRow>,
    );
    let rows: Vec<Row> = (0..height)
        .into_par_iter()
        .map(|row| {
            let mut bubble_rows: Vec<BubbleRow> =
                traps.iter().map(|_| Default::default()).collect();
            let mut lanes = vec![Vec::with_capacity(width as usize); fields.len()];
            let mut gradients = Vec::with_capacity(if lights { width as usize } else { 0 });
            let mut insides = Vec::with_capacity(if reach.is_some() { width as usize } else { 0 });
            let mut inside = 0u64;
            for col in 0..width {
                // Straight, or through the projection with its Jacobian: a distance
                // estimate is rescaled to the local sample spacing (so the straight
                // view's own is untouched) and a gradient pulled back to the frame.
                let (pixel, projected) = match &style.projection {
                    None => (view.sample_point(col, row), None),
                    Some(projection) => {
                        let sample = projection.sample(view, col, row);
                        (sample.point, Some(sample))
                    }
                };
                let to_frame = |unit: Option<[f64; 2]>| match projected {
                    None => unit,
                    Some(sample) => unit.and_then(|unit| sample.pull_back(unit)),
                };
                let de_scale = projected.map(|sample| {
                    sample
                        .spacing()
                        .map_or(f64::NAN, |spacing| view.sample_spacing() / spacing)
                });
                let orbit = iterate::run(family, pixel, maxiter, &wants);
                if !orbit.escaped {
                    inside += 1;
                }
                if let Some(iterations) = reach {
                    let read = (!orbit.escaped)
                        .then(|| self::inside(family, pixel, iterations))
                        .flatten()
                        .and_then(|(value, unit)| Some((value, to_frame(Some(unit))?)));
                    insides.push(read.map_or((f32::NAN, [f32::NAN; 2]), |(value, [x, y])| {
                        (value as f32, [x as f32, y as f32])
                    }));
                }
                for (lane, field) in lanes.iter_mut().zip(&fields) {
                    let value = field.reduce(&orbit).map(|value| match (field, de_scale) {
                        (FieldSpec::De { .. }, Some(scale)) => value * scale,
                        _ => value,
                    });
                    lane.push(value.map_or(f32::NAN, |value| value as f32));
                }
                if lights {
                    let unit = to_frame(
                        orbit
                            .escaped
                            .then(|| gradient(orbit.last, orbit.derivative))
                            .flatten(),
                    );
                    gradients.push(unit.map_or([f32::NAN; 2], |[x, y]| [x as f32, y as f32]));
                }
                for ((trap, wanted), (reads, unit_lane, across_lane)) in
                    traps.iter().zip(&mut bubble_rows)
                {
                    let entry = (orbit.escaped || !trap.escaped)
                        .then(|| bubble(family, pixel, maxiter, trap, view.width))
                        .flatten();
                    let values = entry.map_or([f64::NAN; BUBBLE_READS], |entry| entry.reads(trap));
                    for ((lane, value), want) in reads.iter_mut().zip(values).zip(wanted) {
                        if *want {
                            lane.push(value as f32);
                        }
                    }
                    let unit = |unit: Option<[f64; 2]>| {
                        to_frame(unit).map_or([f32::NAN; 2], |[x, y]| [x as f32, y as f32])
                    };
                    if lights {
                        unit_lane.push(unit(entry.and_then(|entry| entry.uphill())));
                    }
                    if lights && wanted[BubbleRead::Crescent as usize] {
                        across_lane.push(unit(entry.and_then(|entry| entry.across(trap))));
                    }
                }
            }
            (lanes, gradients, insides, inside, bubble_rows)
        })
        .collect();

    let total = (width * height) as usize;
    let mut lanes = vec![Vec::with_capacity(total); fields.len()];
    let mut gradient = Vec::with_capacity(if lights { total } else { 0 });
    let mut inside_lane = Vec::with_capacity(if reach.is_some() { total } else { 0 });
    let mut inside_gradient = Vec::with_capacity(if reach.is_some() { total } else { 0 });
    let mut inside = 0u64;
    let mut bubbles: Vec<BubbleLanes> = traps
        .iter()
        .map(|(trap, _)| BubbleLanes {
            trap: *trap,
            reads: Default::default(),
            gradient: Vec::new(),
            crescent_gradient: Vec::new(),
        })
        .collect();
    for (row_lanes, row_gradient, row_insides, row_inside, row_bubbles) in rows {
        for (lane, part) in lanes.iter_mut().zip(row_lanes) {
            lane.extend(part);
        }
        for (whole, (reads, unit_lane, across_lane)) in bubbles.iter_mut().zip(row_bubbles) {
            for (lane, part) in whole.reads.iter_mut().zip(reads) {
                lane.extend(part);
            }
            whole.gradient.extend(unit_lane);
            whole.crescent_gradient.extend(across_lane);
        }
        gradient.extend(row_gradient);
        for (value, unit) in row_insides {
            inside_lane.push(value);
            inside_gradient.push(unit);
        }
        inside += row_inside;
    }
    let radials = style
        .radials()
        .into_iter()
        .map(|center| {
            let lane = (0..total)
                .map(|i| {
                    let (col, row) = (i as u32 % width, i as u32 / width);
                    -radial(center, col, row, width, height) as f32
                })
                .collect();
            (center, lane)
        })
        .collect();
    Channels {
        fields,
        lanes,
        gradient,
        inside: inside_lane,
        inside_gradient,
        radials,
        bubbles,
        interior_fraction: inside as f64 / (width as f64 * height as f64).max(1.0),
    }
}

/// A layer's frame-wide measurements, taken once before any sample is composited.
enum Measured {
    Palette { spend: Spend, palette: Palette },
    Ranked(Spend),
    Stretched(Stretch),
    Nothing,
}

/// Iterate `view` once and composite the style's stack, sample by sample.
pub fn paint(
    view: &Viewport,
    family: &Family,
    maxiter: u32,
    style: &Style,
    palette: &Palette,
    colormap: &Colormap,
) -> Result<Painted, String> {
    style.validate()?;
    let channels = gather(view, family, maxiter, style);
    let samples = (view.sample_width() * view.sample_height()) as usize;
    let field_of = |key: Key| Field {
        values: channels.lane(key).to_vec(),
        width: view.sample_width(),
        height: view.sample_height(),
    };

    // The measure half: every frame-wide statistic, once.
    let measured: Vec<Measured> = style
        .layers
        .iter()
        .map(|layer| match (layer.kind, layer.channel) {
            (Kind::Palette, Some(source)) => {
                let palette = layer.palette.unwrap_or_default();
                let field = field_of(source.key());
                Measured::Palette {
                    spend: Spend::of(&field, &palette),
                    palette,
                }
            }
            (Kind::Sheet, Some(source)) if layer.sheet.unwrap_or_default().rank => {
                Measured::Ranked(Spend::measure(&field_of(source.key()), Transfer::Rank))
            }
            (_, Some(source)) => Measured::Stretched(Stretch::over(
                channels.lane(source.key()).iter().map(|&v| v as f64),
            )),
            _ => Measured::Nothing,
        })
        .collect();
    let warps: Vec<Option<(Warp, Spend, &[f32])>> = style
        .layers
        .iter()
        .map(|layer| {
            layer.warp.map(|warp| {
                let key = warp.channel.key();
                let spend = Spend::measure(&field_of(key), Transfer::Rank);
                (warp, spend, channels.lane(key))
            })
        })
        .collect();
    let masks: Vec<Option<Stretch>> = style
        .layers
        .iter()
        .map(|layer| {
            layer.mask.map(|mask| {
                Stretch::over(channels.lane(mask.channel.key()).iter().map(|&v| v as f64))
            })
        })
        .collect();
    let interior = style
        .interior
        .as_ref()
        .map_or(coloring::INTERIOR, |paint| paint.linear(colormap));
    let colors: Vec<Option<[f64; 3]>> = style
        .layers
        .iter()
        .map(|layer| layer.color.as_ref().map(|paint| paint.linear(colormap)))
        .collect();
    let highlights: Vec<[f64; 3]> = style
        .layers
        .iter()
        .map(|layer| {
            layer
                .light
                .as_ref()
                .and_then(|light| light.highlight.clone())
                .map_or([1.0; 3], |paint| paint.linear(colormap))
        })
        .collect();
    // A layer's period is counted in the view's rings: escape steps, unprojected.
    let ring = style.projection.map_or(1.0, |projection| projection.ring());
    let lights: Vec<Light> = style
        .layers
        .iter()
        .map(|layer| {
            let light = layer.light.clone().unwrap_or_default();
            // A periodic light's height is already its place in one ring.
            match light.period {
                Some(_) => Light {
                    bands: 1.0,
                    ..light
                },
                None => light,
            }
        })
        .collect();
    let smooth = channels.lane(Key::Field(FieldSpec::Smooth));
    let lanes: Vec<&[f32]> = style
        .layers
        .iter()
        .map(|layer| {
            layer
                .channel
                .map_or(&[][..], |source| channels.lane(source.key()))
        })
        .collect();
    let mask_lanes: Vec<&[f32]> = style
        .layers
        .iter()
        .map(|layer| {
            layer
                .mask
                .map_or(&[][..], |mask| channels.lane(mask.channel.key()))
        })
        .collect();
    let angle = style
        .layers
        .iter()
        .any(|layer| layer.kind == Kind::Pattern)
        .then(|| channels.lane(Key::Field(FieldSpec::Decomposition)));

    // The samples half: a pure function of one sample's channels and the above.
    let linear: Vec<[f64; 3]> = (0..samples)
        .into_par_iter()
        .map(|i| {
            let escaped = smooth[i].is_finite();
            let mut rgb = if escaped { [0.0; 3] } else { interior };
            for (index, layer) in style.layers.iter().enumerate() {
                let mut alpha = layer.opacity;
                if let (Some(mask), Some(stretch)) = (layer.mask, &masks[index]) {
                    let value = mask_lanes[index][i];
                    if !value.is_finite() {
                        continue;
                    }
                    let mut m = mask.channel.curve(stretch.position(value as f64));
                    if mask.invert {
                        m = 1.0 - m;
                    }
                    alpha *= m.powf(mask.power);
                }
                if alpha <= 0.0 {
                    continue;
                }
                match (&measured[index], layer.kind) {
                    (Measured::Palette { spend, palette }, _) => {
                        let value = lanes[index][i];
                        if !value.is_finite() {
                            continue;
                        }
                        let curve = |x: f64| layer.channel.map_or(x, |s| s.curve(x));
                        let mut position = curve(spend.position(value as f64));
                        if let Some((warp, bend, lane)) = &warps[index] {
                            let by = lane[i];
                            if by.is_finite() {
                                let toward = warp.channel.curve(bend.position(by as f64)) - 0.5;
                                position = (position + warp.amount * toward).clamp(0.0, 1.0);
                            }
                        }
                        let over = colormap.lookup(palette.place(position));
                        rgb = blend(rgb, over, layer.blend, alpha);
                    }
                    (Measured::Stretched(stretch), Kind::Light) => {
                        let value = lanes[index][i];
                        let [gx, gy] = layer.channel.map_or([f32::NAN; 2], |source| {
                            channels
                                .gradient(source.key())
                                .get(i)
                                .copied()
                                .unwrap_or([f32::NAN; 2])
                        });
                        if !(value.is_finite() && gx.is_finite()) {
                            continue;
                        }
                        let curve = |x: f64| layer.channel.map_or(x, |s| s.curve(x));
                        let height = curve(match lights[index].period {
                            Some(period) => periodic(value as f64, period * ring, 0.0),
                            None => stretch.position(value as f64),
                        });
                        let lit = shade(
                            rgb,
                            height,
                            [gx as f64, gy as f64],
                            &lights[index],
                            highlights[index],
                        );
                        rgb = mix(rgb, lit, alpha);
                    }
                    (Measured::Ranked(_) | Measured::Stretched(_), Kind::Sheet) => {
                        let value = lanes[index][i];
                        if !value.is_finite() {
                            continue;
                        }
                        let curve = |x: f64| layer.channel.map_or(x, |s| s.curve(x));
                        let mut sheet = layer.sheet.unwrap_or_default();
                        let position = curve(match (&measured[index], sheet.period) {
                            (_, Some(period)) => {
                                let position = periodic(value as f64, period * ring, sheet.phase);
                                (sheet.bands, sheet.phase) = (1.0, 0.0);
                                position
                            }
                            (Measured::Ranked(spend), None) => spend.position(value as f64),
                            (Measured::Stretched(stretch), None) => stretch.position(value as f64),
                            _ => unreachable!("the arm matched one of the two"),
                        });
                        let over = colors[index].unwrap_or(rgb);
                        rgb = blend(rgb, over, layer.blend, alpha * sheet.alpha(position));
                    }
                    (Measured::Ranked(_), _) => unreachable!("only a sheet is ranked"),
                    (Measured::Stretched(stretch), _) => {
                        let value = lanes[index][i];
                        if !value.is_finite() {
                            continue;
                        }
                        let curve = |x: f64| layer.channel.map_or(x, |s| s.curve(x));
                        let position = curve(match (layer.falloff, layer.channel) {
                            (Some(width), Some(source)) => {
                                let scale = match source.field {
                                    Some(FieldSpec::De { scale }) => scale,
                                    _ => 1.0,
                                };
                                falloff(value as f64 / (scale * view.width), width)
                            }
                            _ => stretch.position(value as f64),
                        });
                        let strength = position.powf(layer.power.unwrap_or(1.0));
                        let over = colors[index].unwrap_or([1.0; 3]);
                        rgb = blend(rgb, over, layer.blend, alpha * strength);
                    }
                    (Measured::Nothing, _) => {
                        let checker = layer.checker.unwrap_or_default();
                        let (Some(nu), Some(turn)) = (
                            smooth[i].is_finite().then_some(smooth[i] as f64),
                            angle.map(|lane| lane[i]).filter(|t| t.is_finite()),
                        ) else {
                            continue;
                        };
                        let across = (nu * checker.per_iteration).floor() as i64;
                        let along = (turn as f64 * checker.sectors as f64).floor() as i64;
                        if (across + along).rem_euclid(2) == 1 {
                            let over = colors[index].unwrap_or([1.0; 3]);
                            rgb = blend(rgb, over, layer.blend, alpha);
                        }
                    }
                }
            }
            rgb
        })
        .collect();

    let linear = match style.tone {
        Some(tone) => toned(
            linear,
            tone,
            view.sample_width() as usize,
            view.supersample as usize,
        ),
        None => linear,
    };
    Ok(Painted {
        linear: coloring::toned(linear, palette),
        interior_fraction: channels.interior_fraction,
        texture_flat: None,
    })
}

/// CIE `L*` over 100 of a linear-light colour, clamped to `[0, 1]` first.
pub fn lightness(rgb: [f64; 3]) -> f64 {
    let y = (0.2126 * rgb[0].clamp(0.0, 1.0)
        + 0.7152 * rgb[1].clamp(0.0, 1.0)
        + 0.0722 * rgb[2].clamp(0.0, 1.0))
    .clamp(0.0, 1.0);
    let f = if y > LSTAR_KNEE.powi(3) {
        y.cbrt()
    } else {
        y / (3.0 * LSTAR_KNEE * LSTAR_KNEE) + 4.0 / 29.0
    };
    (116.0 * f - 16.0) / 100.0
}

/// The luminance a lightness ([`lightness`]) is of.
fn luminance_of(lightness: f64) -> f64 {
    let f = (lightness * 100.0 + 16.0) / 116.0;
    if f > LSTAR_KNEE {
        f * f * f
    } else {
        3.0 * LSTAR_KNEE * LSTAR_KNEE * (f - 4.0 / 29.0)
    }
}

const LSTAR_KNEE: f64 = 6.0 / 29.0;

/// The exponent [`Tone`] spends: `g` with `median^g = target`, within the limit.
pub fn tone_exponent(median: f64, target: f64) -> f64 {
    if !(median > 0.0 && median < 1.0) {
        return 1.0;
    }
    (target.ln() / median.ln()).clamp(1.0 / TONE_LIMIT, TONE_LIMIT)
}

/// The tone curve's constants `(b, g)`: `L ↦ b + (1 − b)·L^g` carrying the measured
/// `median` to `tone.median` and, when the tone asks, the measured `p10` to its own.
///
/// With no `p10` the floor is 0 and `g` is solved outright. With one, `b` follows
/// from `g` through the median and `g` is searched on a log grid within the limit
/// for the 10th percentile's best fit — a grid rather than a root-finder because
/// the fit need not cross zero, and the nearest miss is still the right curve.
pub fn tone_curve(median: f64, p10: f64, tone: Tone) -> (f64, f64) {
    let Some(target_low) = tone.p10 else {
        return (0.0, tone_exponent(median, tone.median));
    };
    if !(median > 0.0 && median < 1.0 && p10 >= 0.0 && p10 < median) {
        return (0.0, tone_exponent(median, tone.median));
    }
    let floor = |g: f64| {
        let m = median.powf(g);
        (tone.median - m) / (1.0 - m)
    };
    let mut best = (f64::INFINITY, 0.0, 1.0);
    for step in 0..=400 {
        let g = TONE_LIMIT.powf(step as f64 / 200.0 - 1.0);
        let b = floor(g);
        if !b.is_finite() || b >= tone.median {
            continue;
        }
        let miss = (b + (1.0 - b) * p10.powf(g) - target_low).abs();
        if miss < best.0 {
            best = (miss, b, g);
        }
    }
    (best.1, best.2)
}

/// How close the picture's median and p10 must come to the targets before the tone
/// pass stops re-solving its curve: well inside the band `style tones` checks.
const TONE_SETTLED: f64 = 0.001;

/// How many times the curve is re-solved against the picture it makes.
const TONE_REFINEMENTS: usize = 3;

/// One sample through the tone curve `L ↦ b + (1 − b)·L^g`, its hue and chroma kept.
fn tone_sample(rgb: [f64; 3], b: f64, g: f64) -> [f64; 3] {
    let curve = |l: f64| (b + (1.0 - b) * l.powf(g)).clamp(0.0, 1.0);
    let l = lightness(rgb);
    let before = luminance_of(l);
    if before <= 0.0 {
        return [luminance_of(curve(0.0)); 3];
    }
    let scale = luminance_of(curve(l)) / before;
    rgb.map(|c| c.clamp(0.0, 1.0) * scale)
}

/// The **picture's** median and 10th-percentile lightness: each output pixel the mean
/// of its `ss × ss` block of samples in linear light (each sample through the curve
/// `(b, g)` first, when one is given), read on every `stride`-th pixel.
///
/// The block mean stands in for the resample's Lanczos filter: the percentiles of the
/// two agree to the third decimal, and the mean is a few additions a pixel.
fn picture_percentiles(
    linear: &[[f64; 3]],
    width: usize,
    ss: usize,
    curve: Option<(f64, f64)>,
) -> Option<(f64, f64)> {
    let ss = ss.max(1);
    let out_width = width / ss;
    let pixels = if out_width == 0 {
        0
    } else {
        linear.len() / (ss * ss * out_width) * out_width
    };
    let stride = (pixels / 1_000_000).max(1);
    let mut sampled: Vec<f64> = (0..pixels)
        .into_par_iter()
        .step_by(stride)
        .map(|pixel| {
            let (row, col) = (pixel / out_width, pixel % out_width);
            let mut sum = [0.0; 3];
            for dy in 0..ss {
                let start = (row * ss + dy) * width + col * ss;
                for &rgb in &linear[start..start + ss] {
                    let rgb = match curve {
                        Some((b, g)) => tone_sample(rgb, b, g),
                        None => rgb.map(|c| c.clamp(0.0, 1.0)),
                    };
                    for k in 0..3 {
                        sum[k] += rgb[k];
                    }
                }
            }
            let n = (ss * ss) as f64;
            lightness(sum.map(|c| c / n))
        })
        .collect();
    if sampled.is_empty() {
        return None;
    }
    let middle = sampled.len() / 2;
    let median = *sampled.select_nth_unstable_by(middle, f64::total_cmp).1;
    let tenth = sampled.len() / 10;
    let p10 = *sampled.select_nth_unstable_by(tenth, f64::total_cmp).1;
    Some((median, p10))
}

/// Measure the **picture's** lightness and carry it to the tone's targets.
///
/// The percentiles are the finished picture's, not the samples': each output pixel
/// is its block of supersamples averaged ([`picture_percentiles`]), because that is
/// what a person, and `style tones`, reads. A thin dark filament or a sub-pixel bead
/// is a dark sample but only a darker pixel, so the samples' median sits below the
/// picture's, and by how much depends on the supersample: measured on the samples, a
/// 2560x1600 ss2 frame drew up to 0.03 lighter than the target its samples met.
///
/// The curve is applied to the samples and the average is taken after it, and the
/// average of a curve is not the curve of the average, so one solve lands near the
/// target rather than on it. The picture the curve would make is measured without
/// being made, and the solve is repeated with the targets moved by the miss, up to
/// [`TONE_REFINEMENTS`] times; one curve is applied, once. At supersample 1 the
/// picture is the samples and the first solve is exact.
fn toned(linear: Vec<[f64; 3]>, tone: Tone, width: usize, ss: usize) -> Vec<[f64; 3]> {
    let linear = match tone.log_density {
        None => linear,
        Some(k) => linear
            .into_par_iter()
            .map(|rgb| {
                let rgb = rgb.map(|c| c.clamp(0.0, 1.0));
                let before = luminance_of(lightness(rgb));
                if before <= 0.0 {
                    return rgb;
                }
                lifted(rgb, before, log_density(before, k))
            })
            .collect(),
    };
    let Some((median, p10)) = picture_percentiles(&linear, width, ss, None) else {
        return linear;
    };
    let (mut b, mut g) = tone_curve(median, p10, tone);
    if ss > 1 {
        let mut aim = tone;
        for _ in 0..TONE_REFINEMENTS {
            let Some((got, got_low)) = picture_percentiles(&linear, width, ss, Some((b, g))) else {
                break;
            };
            let low_miss = tone.p10.map_or(0.0, |target| target - got_low);
            let miss = tone.median - got;
            if miss.abs() < TONE_SETTLED && low_miss.abs() < TONE_SETTLED {
                break;
            }
            aim.median = (aim.median + miss).clamp(0.01, 0.99);
            aim.p10 = aim
                .p10
                .map(|low| (low + low_miss).clamp(0.0, aim.median - 0.01));
            (b, g) = tone_curve(median, p10, aim);
        }
    }
    if b == 0.0 && (g - 1.0).abs() < 1e-9 {
        return linear;
    }
    linear
        .into_par_iter()
        .map(|rgb| tone_sample(rgb, b, g))
        .collect()
}

/// Blend `over` onto `under` channel by channel, then take `alpha` of the result.
fn blend(under: [f64; 3], over: [f64; 3], mode: Blend, alpha: f64) -> [f64; 3] {
    let mut out = [0.0; 3];
    for k in 0..3 {
        let a = under[k].clamp(0.0, 1.0);
        let b = over[k].clamp(0.0, 1.0);
        out[k] = under[k] + (mode.apply(a, b) - under[k]) * alpha.clamp(0.0, 1.0);
    }
    out
}

fn mix(a: [f64; 3], b: [f64; 3], t: f64) -> [f64; 3] {
    let t = t.clamp(0.0, 1.0);
    [
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    ]
}

/// Light one sample of the stack.
///
/// The ring profile is a cylinder's: across each band `x` runs `−1 → 1`, the
/// normal's in-plane part is `x` along the gradient and its height `√(1 − x²)`.
/// The slope tilts the whole surface down the gradient — a surface rising towards
/// the set faces away from it — and `rings` mixes the two.
pub fn shade(
    rgb: [f64; 3],
    height: f64,
    along: [f64; 2],
    light: &Light,
    highlight: [f64; 3],
) -> [f64; 3] {
    let phase = (height * light.bands).rem_euclid(1.0);
    let x = 2.0 * phase - 1.0;
    let tube = (1.0 - x * x).max(0.0).sqrt();
    let tilt = light.rings * x - (1.0 - light.rings) * light.slope;
    let up = light.rings * tube + (1.0 - light.rings);
    let normal = normalize([tilt * along[0], tilt * along[1], up]);

    let (azimuth, elevation) = (light.azimuth.to_radians(), light.elevation.to_radians());
    let to_light = [
        elevation.cos() * azimuth.cos(),
        elevation.cos() * azimuth.sin(),
        elevation.sin(),
    ];
    let halfway = normalize([to_light[0], to_light[1], to_light[2] + 1.0]);
    let diffuse = dot(normal, to_light).max(0.0);
    let specular = dot(normal, halfway).max(0.0).powf(light.shininess);
    let rim = (1.0 - normal[2].clamp(0.0, 1.0)).powf(light.rim_power);
    let gain = light.ambient + light.diffuse * diffuse;
    let shine = light.specular * specular + light.rim * rim;
    [
        rgb[0] * gain + shine * highlight[0],
        rgb[1] * gain + shine * highlight[1],
        rgb[2] * gain + shine * highlight[2],
    ]
}

fn dot(a: [f64; 3], b: [f64; 3]) -> f64 {
    a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
}

fn normalize(v: [f64; 3]) -> [f64; 3] {
    let length = dot(v, v).sqrt();
    if length > 0.0 {
        [v[0] / length, v[1] / length, v[2] / length]
    } else {
        [0.0, 0.0, 1.0]
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_gradient_points_up_the_smooth_count() {
        // Mandelbrot at c = 2 + 0.1i escapes on the first steps; step the pixel a
        // hair along the returned direction and the smooth count must rise.
        let family = Family::Multibrot { degree: 2 };
        let wants = Wants {
            derivative: true,
            ..Wants::default()
        };
        for pixel in [
            Complex::new(0.3, 0.6),
            Complex::new(-0.8, 0.2),
            Complex::new(-1.9, 0.01),
        ] {
            let orbit = iterate::run(&family, pixel, 1000, &wants);
            assert!(orbit.escaped);
            let [x, y] = gradient(orbit.last, orbit.derivative).unwrap();
            let h = 1e-7;
            let ahead = iterate::run(&family, pixel + Complex::new(x * h, y * h), 1000, &wants);
            let behind = iterate::run(&family, pixel - Complex::new(x * h, y * h), 1000, &wants);
            assert!(
                ahead.smooth > behind.smooth,
                "{pixel}: {} vs {}",
                ahead.smooth,
                behind.smooth
            );
        }
    }

    fn grid() -> impl Iterator<Item = Complex<f64>> {
        (0..40).flat_map(|i| {
            (0..25).map(move |j| Complex::new(-2.0 + i as f64 * 0.06, -1.2 + j as f64 * 0.1))
        })
    }

    fn trap(hit: u32, spacing: Option<f64>) -> Bubble {
        Bubble {
            center: [0.5, 0.5],
            radius: 0.3,
            hit,
            spacing,
            ..Bubble::default()
        }
    }

    #[test]
    fn a_bubble_entry_is_inside_its_disc_and_a_later_hit_comes_later() {
        let family = Family::Multibrot { degree: 2 };
        let mut entered = 0;
        for pixel in grid() {
            for spacing in [None, Some(1.0)] {
                let Some(first) = bubble(&family, pixel, 500, &trap(1, spacing), 1.0) else {
                    assert!(bubble(&family, pixel, 500, &trap(2, spacing), 1.0).is_none());
                    continue;
                };
                entered += 1;
                assert!(first.offset.norm() < 0.3, "{pixel}: {}", first.offset);
                let [height, _, turn, crescent] = first.reads(&trap(1, spacing));
                assert!(crescent.is_nan(), "no face, no crescent");
                assert!((0.0..=1.0).contains(&height) && (0.0..1.0).contains(&turn));
                if let Some(second) = bubble(&family, pixel, 500, &trap(2, spacing), 1.0) {
                    assert!(second.step > first.step, "{pixel}");
                }
            }
        }
        assert!(
            entered > 100,
            "only {entered} entries: the grid does not exercise the trap"
        );
    }

    #[test]
    fn a_crescent_is_the_lune_between_the_rim_and_the_face() {
        // Face shifted right by half a radius: radius 0.15, centred at +0.15. The lune
        // is widest on the left, 0 at the face's edge, 1 at the rim, NaN on the face.
        let face = Bubble {
            shift: Some([0.5, 0.0]),
            ..trap(1, None)
        };
        let at = |x: f64, y: f64| Entry {
            step: 3,
            offset: Complex::new(x, y),
            derivative: Complex::new(2.0, 0.0),
        };
        let across = |x: f64, y: f64| at(x, y).reads(&face)[3];
        assert!(
            across(0.2, 0.0).is_nan() && across(0.15, 0.1).is_nan(),
            "on the face"
        );
        assert!(across(0.31, 0.0).is_nan() || across(0.31, 0.0) > 1.0 - 1e-9);
        assert!(across(-0.2999, 0.0) > 0.99 && across(-0.0001, 0.0) < 0.01);
        let middle = across(-0.15, 0.0);
        assert!((middle - 0.5).abs() < 1e-9, "{middle}");
        // Climbs towards the rim: leftwards on the left, through a real dz.
        let [x, y] = at(-0.15, 0.0).across(&face).unwrap();
        assert!(x < -0.99 && y.abs() < 1e-9, "{x} {y}");
        // A conformal turn of dz turns the direction with it (∇ₚ = conj(dz)·∇).
        let turned = Entry {
            derivative: Complex::new(0.0, 2.0),
            ..at(-0.15, 0.0)
        };
        let [x, y] = turned.across(&face).unwrap();
        assert!(x.abs() < 1e-9 && (y.abs() - 1.0).abs() < 1e-9, "{x} {y}");
        // A face needs a shift of length in (0, 1), and a crescent needs a face.
        let style = |bubble: serde_json::Value| {
            serde_json::from_value::<Style>(serde_json::json!({
                "name": "lune",
                "layers": [{"kind": "glow", "channel": {"bubble": bubble}, "color": {"palette": 0.5}}]
            }))
            .unwrap()
            .validate()
        };
        assert!(style(serde_json::json!({"radius": 0.3, "read": "crescent"})).is_err());
        assert!(style(serde_json::json!({"radius": 0.3, "shift": [1.0, 0.0]})).is_err());
        assert_eq!(
            style(serde_json::json!({"radius": 0.3, "shift": [0.3, 0.2], "read": "crescent"})),
            Ok(())
        );
    }

    #[test]
    fn a_lattice_of_discs_catches_more_orbits_than_one_disc() {
        let family = Family::Multibrot { degree: 2 };
        let caught = |spacing| {
            grid()
                .filter(|&pixel| bubble(&family, pixel, 500, &trap(1, spacing), 1.0).is_some())
                .count()
        };
        let (one, lattice) = (caught(None), caught(Some(1.0)));
        assert!(lattice > one + 100, "one disc {one}, the lattice {lattice}");
    }

    #[test]
    fn a_largest_bubble_passes_over_the_entries_that_pull_back_too_big() {
        // At a frame a thousandth wide, a disc counts only once |dz| has grown past
        // radius / (largest · width): never earlier than the unbounded entry, and
        // always at a derivative that large.
        let family = Family::Multibrot { degree: 2 };
        let (width, largest) = (1e-3, 0.05);
        let bounded = Bubble {
            largest: Some(largest),
            ..trap(1, Some(1.0))
        };
        let mut later = 0;
        for pixel in grid() {
            let (Some(free), Some(held)) = (
                bubble(&family, pixel, 500, &trap(1, Some(1.0)), width),
                bubble(&family, pixel, 500, &bounded, width),
            ) else {
                continue;
            };
            assert!(held.step >= free.step, "{pixel}");
            assert!(held.derivative.norm() >= 0.3 / (largest * width) * (1.0 - 1e-12));
            later += usize::from(held.step > free.step);
        }
        assert!(
            later > 50,
            "only {later} entries moved: the bound is not exercised"
        );
    }

    #[test]
    fn the_bubble_gradients_point_up_the_height_and_across_the_crescent() {
        // Step the pixel a hair along the returned direction: the entry step is the
        // same and the height rises, so a light at period 2 domes every disc.
        // The same claim for the crescent's direction, across the lune towards the rim.
        let family = Family::Multibrot { degree: 2 };
        let shape = Bubble {
            shift: Some([0.4, 0.3]),
            ..trap(1, Some(1.0))
        };
        let (mut checked, mut lunes) = (0, 0);
        for pixel in grid() {
            let Some(entry) = bubble(&family, pixel, 500, &shape, 1.0) else {
                continue;
            };
            let [height, _, _, crescent] = entry.reads(&shape);
            let (read, [x, y]) = if (0.1..0.9).contains(&crescent) {
                (3, entry.across(&shape).unwrap())
            } else if (0.1..0.9).contains(&height) {
                (0, entry.uphill().unwrap())
            } else {
                continue;
            };
            let h = 1e-8;
            let nudge = Complex::new(x * h, y * h);
            // A hair away the orbit can cross into another disc, or out of the cap:
            // the claim is about one disc, so only a pair on the same entry counts.
            let (Some(ahead), Some(behind)) = (
                bubble(&family, pixel + nudge, 500, &shape, 1.0),
                bubble(&family, pixel - nudge, 500, &shape, 1.0),
            ) else {
                continue;
            };
            if ahead.step != entry.step || behind.step != entry.step {
                continue;
            }
            let (ahead, behind) = (ahead.reads(&shape)[read], behind.reads(&shape)[read]);
            assert!(ahead > behind, "{pixel}: read {read}, {ahead} vs {behind}");
            checked += 1;
            lunes += usize::from(read == 3);
        }
        assert!(checked > 50, "only {checked} samples checked");
        assert!(lunes > 10, "only {lunes} crescent samples checked");
    }

    #[test]
    fn a_bubble_without_a_disc_is_refused() {
        for bubble in [
            r#"{"radius": 0.0}"#,
            r#"{"hit": 0}"#,
            r#"{"spacing": 0.0}"#,
            r#"{"largest": 0.0}"#,
            r#"{"center": [0.5, 0.5], "radius": -1.0}"#,
        ] {
            let text = format!(
                r#"{{"name": "x", "layers": [{{"kind": "palette", "channel": {{"bubble": {bubble}}}}}]}}"#
            );
            let style: Style = serde_json::from_str(&text).unwrap();
            assert!(style.validate().is_err(), "{bubble} was accepted");
        }
        let both = r#"{"name": "x", "layers": [{"kind": "palette",
            "channel": {"bubble": {}, "field": {"kind": "smooth"}}}]}"#;
        let style: Style = serde_json::from_str(both).unwrap();
        assert!(style.validate().is_err());
    }

    #[test]
    fn a_member_a_kind_ignores_is_refused() {
        let text = r##"{"name": "x", "layers": [{"kind": "glow", "channel": {"field": {"kind": "smooth"}},
            "color": {"rgb": "#ffffff"}, "palette": {}}]}"##;
        let style: Style = serde_json::from_str(text).unwrap();
        assert!(style.validate().unwrap_err().contains("takes no 'palette'"));
    }

    #[test]
    fn a_sheet_is_dim_over_its_face_and_full_at_its_rim() {
        let sheet = Sheet {
            bands: 4.0,
            phase: 0.0,
            edge: 0.05,
            fill: 0.1,
            rank: true,
            period: None,
        };
        // Mid-face of the second step is half way up the scoop; just short of its
        // far edge is the rim.
        assert!((sheet.alpha(0.375) - 0.05).abs() < 1e-3);
        assert!(sheet.alpha(0.4999) > 0.99);
        // Past the edge the next sheet starts at the foot of its face again.
        assert!(sheet.alpha(0.5001) < 0.01);
        // The very top of the range is the last rim, never a wrap to a new face,
        // and the very bottom is the first face's foot.
        assert!(sheet.alpha(1.0) > 0.99);
        assert!(sheet.alpha(0.0) < 0.01);
    }

    #[test]
    fn a_period_cuts_the_raw_value_the_same_at_every_depth() {
        assert!((periodic(7.25, 1.0, 0.0) - 0.25).abs() < 1e-12);
        assert!((periodic(107.25, 1.0, 0.0) - 0.25).abs() < 1e-12);
        assert!((periodic(9.0, 4.0, 0.5) - 0.75).abs() < 1e-12);
        assert!((periodic(-0.25, 1.0, 0.0) - 0.75).abs() < 1e-12);
        let text = r#"{"name": "x", "layers": [{"kind": "light", "channel": {"field": {"kind": "smooth"}},
            "light": {"period": 0.0}}]}"#;
        let style: Style = serde_json::from_str(text).unwrap();
        assert!(style.validate().unwrap_err().contains("period"));
    }

    #[test]
    fn a_falloff_glow_is_full_on_the_set_and_one_over_e_one_width_out() {
        assert!((falloff(0.0, 0.01) - 1.0).abs() < 1e-12);
        assert!((falloff(0.01, 0.01) - (-1.0f64).exp()).abs() < 1e-12);
        assert!(falloff(0.1, 0.01) < 1e-4);
        // A non-positive estimate (rounding at the boundary) is on the set.
        assert!((falloff(-1e-9, 0.01) - 1.0).abs() < 1e-12);
        let text = r##"{"name": "x", "layers": [{"kind": "glow", "channel": {"field": {"kind": "smooth"}},
            "color": {"rgb": "#ffffff"}, "falloff": 0.01}]}"##;
        let style: Style = serde_json::from_str(text).unwrap();
        assert!(style.validate().unwrap_err().contains("field 'de'"));
        let text = r##"{"name": "x", "layers": [{"kind": "glow", "channel": {"field": {"kind": "de", "scale": 0.0}},
            "color": {"rgb": "#ffffff"}, "falloff": 0.01}]}"##;
        let style: Style = serde_json::from_str(text).unwrap();
        assert!(style.validate().unwrap_err().contains("scale"));
        let text = r##"{"name": "x", "layers": [{"kind": "glow", "channel": {"field": {"kind": "de"}},
            "color": {"rgb": "#ffffff"}, "falloff": -1.0}]}"##;
        let style: Style = serde_json::from_str(text).unwrap();
        assert!(style.validate().unwrap_err().contains("falloff"));
    }

    #[test]
    fn a_falloff_glow_reads_a_length_whatever_the_estimate_is_scaled_by() {
        let glow = |scale: f64, width: f64| {
            let text = format!(
                r##"{{"name": "x", "layers": [{{"kind": "glow", "channel":
                {{"field": {{"kind": "de", "scale": {scale}}}}}, "color": {{"rgb": "#ffffff"}},
                "blend": "add", "falloff": {width}}}]}}"##
            );
            let style: Style = serde_json::from_str(&text).unwrap();
            let view = Viewport {
                center: Complex::new(-0.1011, 0.9563),
                width: 0.05,
                out_width: 40,
                out_height: 25,
                supersample: 1,
            };
            let map = Colormap::from_stops(
                "ramp",
                crate::colormap::Kind::Sequential,
                &[(0.0, [0, 0, 0]), (1.0, [255, 255, 255])],
            )
            .unwrap();
            let family = Family::Multibrot { degree: 2 };
            paint(&view, &family, 500, &style, &Palette::default(), &map)
                .unwrap()
                .linear
        };
        let plain = glow(1.0, 0.01);
        let scaled = glow(1000.0, 0.01);
        let close = plain
            .iter()
            .zip(&scaled)
            .all(|(a, b)| (0..3).all(|k| (a[k] - b[k]).abs() < 1e-4));
        assert!(close, "the estimate's scale moved the glow");
        // A wider falloff lights more of the frame.
        let wide = glow(1.0, 0.05);
        let mean = |frame: &[[f64; 3]]| frame.iter().map(|rgb| rgb[1]).sum::<f64>();
        assert!(mean(&wide) > mean(&plain));
    }

    /// One escape-time view, small, and a stack that reads every channel the
    /// projection carries a Jacobian into: the distance estimate and the gradient.
    fn painted(projection: Option<&str>) -> Painted {
        let text = format!(
            r#"{{"name": "x", {} "layers": [
                {{"kind": "palette", "channel": {{"field": {{"kind": "de"}}}}}},
                {{"kind": "light", "channel": {{"field": {{"kind": "smooth"}}}}, "light": {{"period": 1.0}}}}]}}"#,
            projection.map_or(String::new(), |p| format!(r#""projection": {p},"#))
        );
        let style: Style = serde_json::from_str(&text).unwrap();
        let view = Viewport {
            center: Complex::new(-0.1011, 0.9563),
            width: 0.05,
            out_width: 40,
            out_height: 25,
            supersample: 1,
        };
        let map = Colormap::from_stops(
            "ramp",
            crate::colormap::Kind::Sequential,
            &[(0.0, [10, 20, 60]), (1.0, [200, 250, 250])],
        )
        .unwrap();
        let family = Family::Multibrot { degree: 2 };
        paint(&view, &family, 500, &style, &Palette::default(), &map).unwrap()
    }

    #[test]
    fn the_log_polar_view_at_one_turn_about_the_middle_draws_the_straight_view() {
        let straight = painted(None);
        let projected = painted(Some(r#"{"log_polar": {}}"#));
        // The two form each point by different arithmetic, a few ulps apart, and an
        // orbit at the boundary can carry that into a different escape: allow a
        // handful of samples, never a drift.
        let differ = straight
            .linear
            .iter()
            .zip(&projected.linear)
            .filter(|(a, b)| (0..3).any(|k| (a[k] - b[k]).abs() > 1e-6))
            .count();
        assert!(
            differ * 50 < straight.linear.len(),
            "{differ} samples differ"
        );
        let turned = painted(Some(r#"{"log_polar": {"turns": 4, "twist": 0.3}}"#));
        assert_ne!(straight.linear, turned.linear);
    }

    #[test]
    fn an_inverted_channel_reads_from_the_other_end() {
        let text = r#"{"field": {"kind": "de"}, "transform": "sqrt", "invert": true}"#;
        let source: Source = serde_json::from_str(text).unwrap();
        assert!((source.curve(0.75) - 0.5).abs() < 1e-12);
        assert_eq!(source.curve(1.0), 0.0);
    }

    #[test]
    fn radial_is_round_in_frame_heights() {
        // A 16:10 frame of 160x100 samples: the centre is 0, a point half a height
        // right of it and one half a height above it are the same distance.
        let at = |col, row| radial([0.5, 0.5], col, row, 160, 100);
        assert!(at(80, 50) < 0.01);
        assert!((at(130, 50) - at(80, 0)).abs() < 0.011);
        assert!((at(130, 50) - 0.505).abs() < 1e-3);
    }

    #[test]
    fn a_light_on_radial_is_refused() {
        let text = r##"{"name": "x", "layers": [{"kind": "light", "channel": {"radial": {}}}]}"##;
        let style: Style = serde_json::from_str(text).unwrap();
        assert!(style.validate().unwrap_err().contains("radial has none"));
    }

    #[test]
    fn tone_carries_the_median_to_its_target_and_keeps_the_ends() {
        // A frame of greys whose median lightness is 0.8, toned to 0.6.
        let greys: Vec<[f64; 3]> = (0..=100)
            .map(|k| luminance_of(0.6 + 0.4 * k as f64 / 100.0))
            .chain([0.0, 1.0])
            .map(|y| [y; 3])
            .collect();
        let width = greys.len();
        let out = toned(
            greys,
            Tone {
                median: 0.6,
                p10: None,
                log_density: None,
            },
            width,
            1,
        );
        let mut light: Vec<f64> = out.iter().map(|&c| lightness(c)).collect();
        light.sort_by(f64::total_cmp);
        assert!(
            (light[light.len() / 2] - 0.6).abs() < 0.01,
            "{}",
            light[light.len() / 2]
        );
        assert_eq!(light[0], 0.0);
        assert!((light[light.len() - 1] - 1.0).abs() < 1e-9);
        // Hue is kept: a colour's channels scale together.
        let warm = toned(
            vec![[0.8, 0.4, 0.2]; 3],
            Tone {
                median: 0.3,
                p10: None,
                log_density: None,
            },
            3,
            1,
        );
        assert!((warm[0][0] / warm[0][1] - 2.0).abs() < 1e-9);
    }

    /// **The tone pass reads the picture, not the samples.** Every 2x2 block here
    /// holds one black sample (a sub-pixel bead) beside three greys, so the samples'
    /// median is a grey's and the picture's, each block averaged, is darker. Toned at
    /// ss 2, the averaged picture lands both targets; the samples do not.
    #[test]
    fn a_supersampled_tone_lands_on_the_averaged_picture() {
        let (out_width, out_height, ss) = (60, 40, 2);
        let width = out_width * ss;
        let mut frame = vec![[0.0; 3]; width * out_height * ss];
        for row in 0..out_height * ss {
            for col in 0..width {
                let pixel = (row / ss) * out_width + col / ss;
                let grey = luminance_of(0.2 + 0.7 * pixel as f64 / (out_width * out_height) as f64);
                let bead = row % ss == 0 && col % ss == 0;
                frame[row * width + col] = if bead { [0.0; 3] } else { [grey; 3] };
            }
        }
        let tone = Tone {
            median: 0.4,
            p10: Some(0.2),
            log_density: None,
        };
        let out = toned(frame, tone, width, ss);
        let mut picture: Vec<f64> = (0..out_width * out_height)
            .map(|pixel| {
                let (row, col) = (pixel / out_width, pixel % out_width);
                let mut sum = 0.0;
                for dy in 0..ss {
                    for dx in 0..ss {
                        sum += out[(row * ss + dy) * width + col * ss + dx][1];
                    }
                }
                lightness([sum / (ss * ss) as f64; 3])
            })
            .collect();
        picture.sort_by(f64::total_cmp);
        let median = picture[picture.len() / 2];
        let p10 = picture[picture.len() / 10];
        assert!((median - 0.4).abs() < 0.005, "picture median {median}");
        assert!((p10 - 0.2).abs() < 0.005, "picture p10 {p10}");
        let mut samples: Vec<f64> = out.iter().map(|&c| lightness(c)).collect();
        samples.sort_by(f64::total_cmp);
        assert!(
            (samples[samples.len() / 2] - 0.4).abs() > 0.02,
            "the samples' median {} is not the picture's",
            samples[samples.len() / 2]
        );
    }

    #[test]
    fn a_tone_with_shadows_lands_both_percentiles() {
        let tone = Tone {
            median: 0.36,
            p10: Some(0.2),
            log_density: None,
        };
        let (b, g) = tone_curve(0.5, 0.1, tone);
        let curve = |l: f64| b + (1.0 - b) * l.powf(g);
        assert!((curve(0.5) - 0.36).abs() < 1e-9);
        assert!((curve(0.1) - 0.2).abs() < 0.01, "{}", curve(0.1));
        assert!((curve(1.0) - 1.0).abs() < 1e-9);
    }

    #[test]
    fn log_density_lifts_a_faint_thread_more_than_a_bright_one_and_keeps_the_ends() {
        assert_eq!(log_density(0.0, 50.0), 0.0);
        assert!((log_density(1.0, 50.0) - 1.0).abs() < 1e-12);
        let (faint, bright) = (0.01, 0.5);
        let lift = |y: f64| log_density(y, 50.0) / y;
        assert!(lift(faint) > 3.0 * lift(bright));
        // Through the tone pass: hue is kept, black stays black, white stays white,
        // and the median still lands.
        let frame = vec![
            [0.02, 0.06, 0.01],
            [0.02, 0.06, 0.01],
            [0.2, 0.5, 0.1],
            [0.0; 3],
            [1.0; 3],
        ];
        let out = toned(
            frame,
            Tone {
                median: 0.3,
                p10: None,
                log_density: Some(50.0),
            },
            5,
            1,
        );
        assert!((out[0][1] / out[0][0] - 3.0).abs() < 1e-9);
        assert!(
            (lightness(out[0]) - 0.3).abs() < 0.01,
            "{}",
            lightness(out[0])
        );
        assert_eq!(out[3], [0.0; 3]);
        assert!((lightness(out[4]) - 1.0).abs() < 1e-9);
        // A saturated colour is never clipped channel by channel: it reaches its
        // lifted luminance by scaling while it can and then whitening, so its
        // brightest channel stays the brightest and nothing leaves [0, 1].
        let orange = [1.0, 0.5, 0.0];
        let before = luminance_of(lightness(orange));
        let after = log_density(before, 50.0);
        let out = lifted(orange, before, after);
        assert!(out.iter().all(|c| (0.0..=1.0).contains(c)), "{out:?}");
        assert!((luminance_of(lightness(out)) - after).abs() < 1e-9);
        assert!(out[0] >= out[1] && out[1] >= out[2]);
        // A dim one only scales, its hue exactly kept.
        let dim = [0.1, 0.05, 0.0];
        let before = luminance_of(lightness(dim));
        let out = lifted(dim, before, log_density(before, 50.0));
        assert!((out[0] / out[1] - 2.0).abs() < 1e-9 && out[2] == 0.0);
    }

    #[test]
    fn a_warp_is_a_palette_layers_and_reads_its_channel() {
        let text = r##"{"name": "x", "layers": [{"kind": "palette", "channel": {"radial": {}},
            "warp": {"channel": {"field": {"kind": "de"}}, "amount": 0.3}}]}"##;
        let style: Style = serde_json::from_str(text).unwrap();
        style.validate().unwrap();
        // The warp's field is gathered beside the smooth count every style reads.
        assert_eq!(style.fields().len(), 2);
        let text = r##"{"name": "x", "layers": [{"kind": "glow", "channel": {"radial": {}},
            "color": {"rgb": "#ffffff"}, "warp": {"channel": {"radial": {}}, "amount": 0.3}}]}"##;
        let style: Style = serde_json::from_str(text).unwrap();
        assert!(style.validate().unwrap_err().contains("takes no 'warp'"));
    }

    #[test]
    fn a_hex_colour_reads() {
        assert_eq!(parse_hex("#ff8000"), Some([255, 128, 0]));
        assert_eq!(parse_hex("ff8000"), None);
        assert_eq!(parse_hex("#ff80"), None);
    }

    #[test]
    fn flat_light_with_no_highlight_is_a_gain() {
        let light = Light {
            rings: 0.0,
            slope: 0.0,
            elevation: 90.0,
            ambient: 0.25,
            diffuse: 0.5,
            specular: 0.0,
            ..Light::default()
        };
        let out = shade([0.4, 0.2, 0.1], 0.3, [1.0, 0.0], &light, [1.0; 3]);
        for (got, want) in out.iter().zip([0.3, 0.15, 0.075]) {
            assert!((got - want).abs() < 1e-12);
        }
    }
}
