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

use crate::coloring::{self, Blend, Painted, Palette, Rolloff, Spend, Stretch, Transform};
use crate::colormap::{Bake, Colormap, srgb_to_linear};
use crate::family::Family;
use crate::field::{Field, FieldSpec};
use crate::iterate::{self, Wants};
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
}

/// A channel and the curve its stretched position goes through: a field of the
/// catalog, or the inside channel — exactly one of the two.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Source {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub field: Option<FieldSpec>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub inside: Option<Inside>,
    #[serde(default)]
    pub transform: Transform,
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

/// Which lane a source reads.
#[derive(Clone, Copy, Debug, PartialEq)]
enum Key {
    Field(FieldSpec),
    Inside,
}

impl Source {
    fn key(&self) -> Key {
        match self.field {
            Some(field) => Key::Field(field),
            None => Key::Inside,
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
    /// `pattern` only.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub checker: Option<Checker>,
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
        let mut sigmas = Vec::new();
        for (index, layer) in self.layers.iter().enumerate() {
            let at = format!("style '{}' layer {index} ({:?})", self.name, layer.kind);
            if !(0.0..=1.0).contains(&layer.opacity) {
                return Err(format!("{at}: opacity is in [0, 1], got {}", layer.opacity));
            }
            let allowed: &[&str] = match layer.kind {
                Kind::Palette => &["channel", "palette"],
                Kind::Light => &["channel", "light"],
                Kind::Glow => &["channel", "color", "power"],
                Kind::Pattern => &["color", "checker"],
            };
            for (name, present) in [
                ("channel", layer.channel.is_some()),
                ("palette", layer.palette.is_some()),
                ("light", layer.light.is_some()),
                ("color", layer.color.is_some()),
                ("power", layer.power.is_some()),
                ("checker", layer.checker.is_some()),
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
            if let Some(mask) = layer.mask {
                if !(mask.power.is_finite() && mask.power > 0.0) {
                    return Err(format!("{at}: mask power must be positive"));
                }
            }
            for source in layer
                .channel
                .iter()
                .chain(layer.mask.iter().map(|m| &m.channel))
            {
                match (source.field, source.inside) {
                    (Some(_), None) => {}
                    (None, Some(inside)) if inside.iterations > 0 => {}
                    (None, Some(_)) => return Err(format!("{at}: inside needs iterations >= 1")),
                    _ => {
                        return Err(format!(
                            "{at}: a channel names exactly one of 'field' and 'inside'"
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
            .flat_map(|layer| {
                layer
                    .channel
                    .iter()
                    .chain(layer.mask.iter().map(|m| &m.channel))
            })
            .filter_map(|source| source.inside.map(|inside| inside.iterations))
            .max()
    }
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
    interior_fraction: f64,
}

impl Channels {
    fn lane(&self, key: Key) -> &[f32] {
        match key {
            Key::Inside => &self.inside,
            Key::Field(field) => {
                let index = self
                    .fields
                    .iter()
                    .position(|f| *f == field)
                    .expect("every field a layer reads was gathered");
                &self.lanes[index]
            }
        }
    }

    fn gradient(&self, key: Key) -> &[[f32; 2]] {
        match key {
            Key::Inside => &self.inside_gradient,
            Key::Field(_) => &self.gradient,
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
    type Row = (Vec<Vec<f32>>, Vec<[f32; 2]>, Vec<(f32, [f32; 2])>, u64);
    let rows: Vec<Row> = (0..height)
        .into_par_iter()
        .map(|row| {
            let mut lanes = vec![Vec::with_capacity(width as usize); fields.len()];
            let mut gradients = Vec::with_capacity(if lights { width as usize } else { 0 });
            let mut insides = Vec::with_capacity(if reach.is_some() { width as usize } else { 0 });
            let mut inside = 0u64;
            for col in 0..width {
                let pixel = view.sample_point(col, row);
                let orbit = iterate::run(family, pixel, maxiter, &wants);
                if !orbit.escaped {
                    inside += 1;
                }
                if let Some(iterations) = reach {
                    let read = (!orbit.escaped)
                        .then(|| self::inside(family, pixel, iterations))
                        .flatten();
                    insides.push(read.map_or((f32::NAN, [f32::NAN; 2]), |(value, [x, y])| {
                        (value as f32, [x as f32, y as f32])
                    }));
                }
                for (lane, field) in lanes.iter_mut().zip(&fields) {
                    lane.push(field.reduce(&orbit).map_or(f32::NAN, |value| value as f32));
                }
                if lights {
                    let unit = orbit
                        .escaped
                        .then(|| gradient(orbit.last, orbit.derivative))
                        .flatten();
                    gradients.push(unit.map_or([f32::NAN; 2], |[x, y]| [x as f32, y as f32]));
                }
            }
            (lanes, gradients, insides, inside)
        })
        .collect();

    let total = (width * height) as usize;
    let mut lanes = vec![Vec::with_capacity(total); fields.len()];
    let mut gradient = Vec::with_capacity(if lights { total } else { 0 });
    let mut inside_lane = Vec::with_capacity(if reach.is_some() { total } else { 0 });
    let mut inside_gradient = Vec::with_capacity(if reach.is_some() { total } else { 0 });
    let mut inside = 0u64;
    for (row_lanes, row_gradient, row_insides, row_inside) in rows {
        for (lane, part) in lanes.iter_mut().zip(row_lanes) {
            lane.extend(part);
        }
        gradient.extend(row_gradient);
        for (value, unit) in row_insides {
            inside_lane.push(value);
            inside_gradient.push(unit);
        }
        inside += row_inside;
    }
    Channels {
        fields,
        lanes,
        gradient,
        inside: inside_lane,
        inside_gradient,
        interior_fraction: inside as f64 / (width as f64 * height as f64).max(1.0),
    }
}

/// A layer's frame-wide measurements, taken once before any sample is composited.
enum Measured {
    Palette { spend: Spend, palette: Palette },
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
            (_, Some(source)) => Measured::Stretched(Stretch::over(
                channels.lane(source.key()).iter().map(|&v| v as f64),
            )),
            _ => Measured::Nothing,
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
    let lights: Vec<Light> = style
        .layers
        .iter()
        .map(|layer| layer.light.clone().unwrap_or_default())
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
                    let mut m = mask.channel.transform.apply(stretch.position(value as f64));
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
                        let transform = layer.channel.map_or(Transform::Linear, |s| s.transform);
                        let over = colormap
                            .lookup(palette.place(transform.apply(spend.position(value as f64))));
                        rgb = blend(rgb, over, layer.blend, alpha);
                    }
                    (Measured::Stretched(stretch), Kind::Light) => {
                        let value = lanes[index][i];
                        let [gx, gy] = layer
                            .channel
                            .map_or([f32::NAN; 2], |source| channels.gradient(source.key())[i]);
                        if !(value.is_finite() && gx.is_finite()) {
                            continue;
                        }
                        let transform = layer.channel.map_or(Transform::Linear, |s| s.transform);
                        let height = transform.apply(stretch.position(value as f64));
                        let lit = shade(
                            rgb,
                            height,
                            [gx as f64, gy as f64],
                            &lights[index],
                            highlights[index],
                        );
                        rgb = mix(rgb, lit, alpha);
                    }
                    (Measured::Stretched(stretch), _) => {
                        let value = lanes[index][i];
                        if !value.is_finite() {
                            continue;
                        }
                        let transform = layer.channel.map_or(Transform::Linear, |s| s.transform);
                        let position = transform.apply(stretch.position(value as f64));
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

    Ok(Painted {
        linear: coloring::toned(linear, palette),
        interior_fraction: channels.interior_fraction,
        texture_flat: None,
    })
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

    #[test]
    fn a_member_a_kind_ignores_is_refused() {
        let text = r##"{"name": "x", "layers": [{"kind": "glow", "channel": {"field": {"kind": "smooth"}},
            "color": {"rgb": "#ffffff"}, "palette": {}}]}"##;
        let style: Style = serde_json::from_str(text).unwrap();
        assert!(style.validate().unwrap_err().contains("takes no 'palette'"));
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
