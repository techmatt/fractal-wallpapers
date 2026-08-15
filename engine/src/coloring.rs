//! Field → color. One path, every mode.
//!
//! A field is not a color and has no natural range: it depends on the family,
//! the zoom depth, and the iteration cap, and its distribution is badly skewed —
//! most of a frame's samples escape early, a thin band near the boundary runs to
//! the cap. Handing raw values to a colormap gives an image that is one flat
//! color with a hairline of everything else.
//!
//! So a field is normalized against **its own frame** before it is looked up.
//! The stretch reads the 0.5th and 99.5th percentiles of the valid samples and
//! maps that span to `[0, 1]`. Trimming half a percent from each end costs
//! nothing visible and stops a handful of extreme samples from compressing the
//! rest of the picture into a corner of the gradient.
//!
//! The consequence is that this stage is **not** per-pixel pure: it reads the
//! whole frame before it can color any of it. That is the price of a render that
//! frames itself, and it is why the field, not the color, is the thing worth
//! keeping.
//!
//! Three shapes of coloring share that path:
//!
//! ```text
//! field      one scalar field   → stretch → curve → colormap
//! composite  two scalar fields  → a stretch each → blend → colormap
//! direct     no scalar at all   → gradient samples composited during iteration
//! ```
//!
//! The order in `composite` is the whole point of it: each field is normalized
//! against its own distribution *before* they meet, so a texture whose values
//! live in a hundredth of the base's range still arrives at full strength.
//! Normalizing after the blend would let whichever field had the wider spread
//! decide the picture.

use rayon::prelude::*;
use serde::{Deserialize, Serialize};

use crate::colormap::Colormap;
use crate::direct_trap::{self, Shape};
use crate::family::Family;
use crate::field::{self, Field, FieldSpec};
use crate::viewport::Viewport;

/// Percentile of valid samples mapped to the bottom of the gradient.
pub const CLIP_LOW: f64 = 0.5;
/// Percentile of valid samples mapped to the top of the gradient.
pub const CLIP_HIGH: f64 = 99.5;

/// The color samples with no field value take.
///
/// Black, and deliberately so: for the exterior-only fields that is the set
/// itself, and letting it read as negative space is what gives the exterior
/// structure something to be structure *against*. The fields that fill the
/// interior never reach it.
pub const INTERIOR: [f64; 3] = [0.0, 0.0, 0.0];

/// A curve applied to the normalized field before it is looked up.
///
/// Each maps `[0, 1]` onto `[0, 1]` and is monotone, so none of them can reorder
/// the field — they only decide how much of the gradient each part of the
/// distribution gets. That is a coloring choice, not a different field, which is
/// why it lives here and not in [`crate::field`].
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Transform {
    /// The field as it is.
    #[default]
    Linear,
    /// `√x` — gives the low end more of the gradient.
    Sqrt,
    /// `ln(1+x)/ln 2` — gives the low end much more of it. What a field with a
    /// long thin tail needs: the trap fields spend most of their range on a few
    /// samples that came very close.
    Log,
    /// A smoothstep S-curve — pushes contrast into the middle and flattens both
    /// ends.
    Scurve,
}

impl Transform {
    /// Apply the curve to a value already normalized to `[0, 1]`.
    pub fn apply(self, x: f64) -> f64 {
        let x = x.clamp(0.0, 1.0);
        match self {
            Transform::Linear => x,
            Transform::Sqrt => x.sqrt(),
            Transform::Log => x.ln_1p() / std::f64::consts::LN_2,
            Transform::Scurve => x * x * (3.0 - 2.0 * x),
        }
    }
}

/// Which quantity the gradient's length is spent on.
///
/// The stretch spends it by **value**: equal spans of field value get equal
/// spans of color, so a band edge lands wherever the values happen to cross a
/// boundary. That is the right default and it is what every mode does unless
/// told otherwise.
///
/// The alternative spends it by **edge**: the arc between two colors is widened
/// where the field is changing fast and narrowed where it is flat, so color
/// transitions land on the picture's geometric edges instead of on arbitrary
/// isovalues.
#[derive(Clone, Copy, Debug, Default, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Transfer {
    /// Spend the gradient by field value: the stretch on its own.
    #[default]
    Value,
    /// Spend it by how fast the field is moving, with `weight` deciding how
    /// hard. At `0` this *is* the value transfer — every bin weighs the same —
    /// which is why it is the family's own edge rather than a separate mode.
    Edge { weight: f64 },
}

/// How many value bins the edge transfer measures over. Fine enough that the
/// remap is smooth, coarse enough that every bin holds samples to average.
pub const TRANSFER_BINS: usize = 256;

/// Keeps a bin that measured no movement from being weighed at exactly zero,
/// which would spend no gradient at all on it and collapse its values onto one
/// color.
const TRANSFER_FLOOR: f64 = 1e-6;

/// The palette pass: everything between a normalized field and a color.
///
/// A **mode** says which field to read and through which curve. This says how
/// the gradient is spent on it, and it is deliberately a separate object: two
/// pictures of the same place in the same mode through the same map can look
/// entirely unalike because of what is here, so it is recorded per render rather
/// than folded into the mode's name. Every default is the identity — a spec that
/// says nothing about the palette renders exactly as it did before any of this
/// existed.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct Palette {
    /// A power applied after the mode's curve. Below 1 lifts the low end toward
    /// the top of the gradient, above 1 pushes it down.
    pub gamma: f64,
    /// How many times the gradient is traversed across the field's range. Only
    /// a cyclic map can do this without a seam, which is why nothing here sets
    /// it on a caller's behalf.
    pub cycles: f64,
    /// Where in the gradient the traversal starts, in turns.
    pub phase: f64,
    /// How the map is baked: flipped, folded, or neither.
    #[serde(flatten)]
    pub bake: crate::colormap::Bake,
    /// Which quantity the gradient's length is spent on.
    pub transfer: Transfer,
}

impl Default for Palette {
    fn default() -> Palette {
        Palette {
            gamma: 1.0,
            cycles: 1.0,
            phase: 0.0,
            bake: crate::colormap::Bake::default(),
            transfer: Transfer::Value,
        }
    }
}

impl Palette {
    /// Check what the type cannot, before a render starts.
    pub fn validate(&self) -> Result<(), String> {
        if !(self.gamma.is_finite() && self.gamma > 0.0) {
            return Err(format!("gamma must be positive, got {}", self.gamma));
        }
        if !(self.cycles.is_finite() && self.cycles > 0.0) {
            return Err(format!("cycles must be positive, got {}", self.cycles));
        }
        if !self.phase.is_finite() {
            return Err(format!("phase must be a number, got {}", self.phase));
        }
        if let Transfer::Edge { weight } = self.transfer
            && !(weight.is_finite() && weight >= 0.0)
        {
            return Err(format!(
                "the edge transfer's weight must be at least 0, got {weight}"
            ));
        }
        Ok(())
    }

    /// Whether the gradient is traversed once, from its start.
    pub fn traverses_once(&self) -> bool {
        self.cycles == 1.0 && self.phase == 0.0
    }

    /// Place a `[0, 1]` value on the gradient: gamma, then the traversal.
    ///
    /// The two wraps are kept separate and in this order because they are not
    /// the same as one: `frac(frac(x·c) + p)` and `frac(x·c + p)` differ exactly
    /// at the top of the range, which is the value every fully-saturated sample
    /// in the picture takes.
    pub fn place(&self, value: f64) -> f64 {
        let gray = value.clamp(0.0, 1.0).powf(self.gamma);
        if self.traverses_once() {
            return gray;
        }
        ((gray * self.cycles).rem_euclid(1.0) + self.phase).rem_euclid(1.0)
    }
}

/// How two `[0, 1]` values are merged into one.
///
/// The same small table serves the composite modes (blending two fields) and the
/// direct modes (blending each gradient sample against what is already there),
/// because it is the same question in both places.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Blend {
    /// The new value, ignoring the old one.
    Normal,
    /// `a·b` — darkens; the texture's dark regions cut into the base.
    Multiply,
    /// `1−(1−a)(1−b)` — brightens; the texture's bright regions lift the base.
    /// The blend every composite mode here uses: the texture *adds* light where
    /// it has something to say and leaves the base alone where it does not.
    Screen,
    /// Multiply in the shadows, screen in the highlights.
    Overlay,
    /// `min(a,b)` — the texture clamps the base from above.
    Min,
}

impl Blend {
    /// Merge `under` and `over`, both in `[0, 1]`, into `[0, 1]`.
    pub fn apply(self, under: f64, over: f64) -> f64 {
        match self {
            Blend::Normal => over,
            Blend::Multiply => under * over,
            Blend::Screen => 1.0 - (1.0 - under) * (1.0 - over),
            Blend::Overlay => {
                if under < 0.5 {
                    2.0 * under * over
                } else {
                    1.0 - 2.0 * (1.0 - under) * (1.0 - over)
                }
            }
            Blend::Min => under.min(over),
        }
    }
}

/// One field with the curve it is read through.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Layer {
    pub field: FieldSpec,
    #[serde(default)]
    pub transform: Transform,
}

/// How a render turns orbits into color.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Coloring {
    /// One field through the colormap.
    Field {
        field: FieldSpec,
        #[serde(default)]
        transform: Transform,
    },
    /// Two fields, each normalized against its own distribution, then blended.
    ///
    /// `texture_weight` fades between the base alone and the full blend, so it
    /// is the dial that says how much of the texture to let through without
    /// changing what the texture *is*.
    Composite {
        base: Layer,
        texture: Layer,
        blend: Blend,
        #[serde(default = "full")]
        texture_weight: f64,
    },
    /// Gradient samples composited during the iteration itself. See
    /// [`crate::direct_trap`] — this one never makes a scalar field at all.
    Direct {
        shape: Shape,
        #[serde(default = "unit")]
        trap_radius: f64,
        /// How close to the shape an iterate must come to paint. Absent means
        /// the shape's own default, which is calibrated so every shape paints a
        /// comparable share of the frame.
        #[serde(default)]
        threshold: Option<f64>,
        #[serde(default = "half")]
        opacity: f64,
        merge: Blend,
        #[serde(default = "black")]
        start_color: String,
    },
}

fn full() -> f64 {
    1.0
}
fn unit() -> f64 {
    1.0
}
fn half() -> f64 {
    0.5
}
fn black() -> String {
    "black".to_string()
}

impl Default for Coloring {
    fn default() -> Coloring {
        Coloring::Field {
            field: FieldSpec::Smooth,
            transform: Transform::Linear,
        }
    }
}

impl Coloring {
    /// Check what cannot be checked by the type — and do it before a render
    /// starts, so a bad spec costs a message rather than a minute.
    pub fn validate(&self) -> Result<(), String> {
        match self {
            Coloring::Field { .. } => Ok(()),
            Coloring::Composite {
                base,
                texture,
                texture_weight,
                ..
            } => {
                if base.field.conflicts_with(&texture.field) {
                    return Err(format!(
                        "a composite of '{}' with itself has nothing to blend, and one orbit \
                         carries only one set of that field's constants",
                        base.field.name()
                    ));
                }
                in_unit_interval(*texture_weight, "texture_weight")
            }
            Coloring::Direct {
                trap_radius,
                threshold,
                opacity,
                start_color,
                ..
            } => {
                if !(trap_radius.is_finite() && *trap_radius >= 0.0) {
                    return Err(format!(
                        "trap_radius must be non-negative, got {trap_radius}"
                    ));
                }
                if threshold.is_some_and(|t| !(t.is_finite() && t > 0.0)) {
                    return Err(format!(
                        "threshold must be positive, got {}",
                        threshold.expect("checked as present above")
                    ));
                }
                in_unit_interval(*opacity, "opacity")?;
                direct_trap::parse_start_color(start_color).map(|_| ())
            }
        }
    }

    /// The scalar field this coloring maps through the colormap, if it has one.
    ///
    /// `None` is what makes a coloring undumpable, and each shape's reason is
    /// different — see [`Coloring::why_not_a_field`].
    pub fn dumpable_field(&self) -> Option<Layer> {
        match self {
            Coloring::Field { field, transform } => Some(Layer {
                field: *field,
                transform: *transform,
            }),
            _ => None,
        }
    }

    /// Why this coloring has no single scalar field behind it.
    pub fn why_not_a_field(&self) -> Option<&'static str> {
        match self {
            Coloring::Field { .. } => None,
            Coloring::Composite { .. } => Some(
                "a composite normalizes each of its two fields against the whole frame before \
                 blending them, so no single raw field reproduces it. Dump one of its two \
                 fields on its own instead.",
            ),
            Coloring::Direct { .. } => Some(
                "a direct trap is color-valued: it composites gradient samples during the \
                 iteration and never produces a scalar index, so there is nothing to serialize",
            ),
        }
    }
}

fn in_unit_interval(value: f64, name: &str) -> Result<(), String> {
    if (0.0..=1.0).contains(&value) {
        Ok(())
    } else {
        Err(format!("{name} must be between 0 and 1, got {value}"))
    }
}

/// A frame's normalization: the span of field values the gradient covers.
#[derive(Clone, Copy, Debug)]
pub struct Stretch {
    low: f64,
    span: f64,
}

impl Stretch {
    /// Measure the stretch over a field's valid samples.
    ///
    /// A frame with no valid samples at all — a view entirely inside the set,
    /// colored by an exterior-only field — gets a degenerate but harmless
    /// stretch: nothing will be looked up through it.
    pub fn measure(field: &Field) -> Stretch {
        Stretch::over(field.values.iter().copied())
    }

    /// Measure the stretch over any run of samples, invalid ones included.
    ///
    /// A crop of a larger field normalizes against **its own** samples, not
    /// against the field it was cut from: the whole point of the stretch is that
    /// a frame frames itself, and a tile borrowing a wider frame's percentiles
    /// would be colored for a picture nobody is looking at.
    pub fn over(samples: impl Iterator<Item = f32>) -> Stretch {
        let mut valid: Vec<f64> = samples
            .filter(|v| v.is_finite())
            .map(|v| v as f64)
            .collect();
        if valid.is_empty() {
            return Stretch {
                low: 0.0,
                span: 1.0,
            };
        }
        let low = percentile(&mut valid, CLIP_LOW);
        let high = percentile(&mut valid, CLIP_HIGH);
        Stretch {
            low,
            span: if high > low { high - low } else { 1.0 },
        }
    }

    /// Place one field value on the gradient.
    pub fn position(&self, value: f64) -> f64 {
        ((value - self.low) / self.span).clamp(0.0, 1.0)
    }
}

/// A remap of the stretched position that spends gradient where the field moves.
///
/// Built in two halves. The **profile** is a fact about the field alone: how fast
/// the field is moving, on average, among the samples that stretched into each
/// value bin. It is measured once. The **curve** is that profile raised to a
/// weight and accumulated, which is the running share of the gradient each value
/// has earned by the time it is reached; raising the weight concentrates color on
/// the fast bins, and a weight of zero weighs every bin the same and gives back
/// the straight line.
pub struct Edges {
    curve: Vec<f64>,
}

impl Edges {
    /// Measure a field's movement, bin by stretched value.
    ///
    /// The movement is `|∇field|` by forward differences over samples that have
    /// one — a partial reaching into the interior has no value to difference
    /// against and contributes nothing rather than a fabricated zero.
    pub fn measure(field: &Field, stretch: &Stretch, weight: f64) -> Edges {
        let (width, height) = (field.width as usize, field.height as usize);
        let mut sums = vec![0.0f64; TRANSFER_BINS];
        let mut counts = vec![0u64; TRANSFER_BINS];

        for row in 0..height {
            for col in 0..width {
                let here = field.values[row * width + col] as f64;
                if !here.is_finite() {
                    continue;
                }
                let mut moved = 0.0;
                let mut has_partial = false;
                if col + 1 < width {
                    let east = field.values[row * width + col + 1] as f64;
                    if east.is_finite() {
                        moved += (east - here) * (east - here);
                        has_partial = true;
                    }
                }
                if row + 1 < height {
                    let south = field.values[(row + 1) * width + col] as f64;
                    if south.is_finite() {
                        moved += (south - here) * (south - here);
                        has_partial = true;
                    }
                }
                if !has_partial {
                    continue;
                }
                let bin = ((stretch.position(here) * TRANSFER_BINS as f64) as usize)
                    .min(TRANSFER_BINS - 1);
                sums[bin] += moved.sqrt();
                counts[bin] += 1;
            }
        }

        let mut profile: Vec<f64> = sums
            .iter()
            .zip(&counts)
            .map(|(&sum, &count)| if count > 0 { sum / count as f64 } else { 0.0 })
            .collect();
        let peak = profile.iter().copied().fold(0.0, f64::max);
        if peak > 0.0 {
            for value in &mut profile {
                *value /= peak;
            }
        }

        // The curve holds the share earned at every bin *edge*, so it has one
        // more entry than there are bins and opens at zero.
        let mut curve = Vec::with_capacity(TRANSFER_BINS + 1);
        curve.push(0.0);
        let mut running = 0.0;
        for value in &profile {
            running += (value + TRANSFER_FLOOR).powf(weight);
            curve.push(running);
        }
        if running > 0.0 {
            for value in &mut curve {
                *value /= running;
            }
        } else {
            for (index, value) in curve.iter_mut().enumerate() {
                *value = index as f64 / TRANSFER_BINS as f64;
            }
        }
        Edges { curve }
    }

    /// Remap one stretched position through the curve.
    pub fn remap(&self, position: f64) -> f64 {
        let scaled = position.clamp(0.0, 1.0) * TRANSFER_BINS as f64;
        let bin = (scaled.floor() as usize).min(TRANSFER_BINS - 1);
        let fraction = scaled - bin as f64;
        self.curve[bin] + (self.curve[bin + 1] - self.curve[bin]) * fraction
    }
}

/// The edge transfer for a field, or `None` when the gradient is spent by value.
fn edges_for(field: &Field, stretch: &Stretch, palette: &Palette) -> Option<Edges> {
    match palette.transfer {
        Transfer::Value => None,
        Transfer::Edge { weight } => Some(Edges::measure(field, stretch, weight)),
    }
}

/// Everything a coloring pass produced.
pub struct Painted {
    /// Linear-light RGB, one entry per supersample.
    ///
    /// It stays in linear light and at supersampled resolution because the
    /// resample downstream both averages and encodes, and doing either here
    /// would mean doing it twice.
    pub linear: Vec<[f64; 3]>,
    /// Share of samples whose orbit never escaped.
    pub interior_fraction: f64,
}

/// Iterate `view` and color it, whichever shape of coloring this is.
pub fn paint(
    view: &Viewport,
    family: &Family,
    maxiter: u32,
    coloring: &Coloring,
    palette: &Palette,
    colormap: &Colormap,
) -> Result<Painted, String> {
    match coloring {
        Coloring::Field { field, transform } => {
            let sampled = field::render_field(view, family, maxiter, *field);
            Ok(Painted {
                linear: shade(&sampled.fields[0], *transform, palette, colormap),
                interior_fraction: sampled.interior_fraction,
            })
        }
        Coloring::Composite {
            base,
            texture,
            blend,
            texture_weight,
        } => {
            let sampled = field::sample(view, family, maxiter, &[base.field, texture.field]);
            Ok(Painted {
                linear: composite(
                    &sampled.fields[0],
                    &sampled.fields[1],
                    base.transform,
                    texture.transform,
                    *blend,
                    *texture_weight,
                    palette,
                    colormap,
                ),
                interior_fraction: sampled.interior_fraction,
            })
        }
        Coloring::Direct {
            shape,
            trap_radius,
            threshold,
            opacity,
            merge,
            start_color,
        } => direct_trap::Painter::new(
            *shape,
            *trap_radius,
            *threshold,
            *opacity,
            *merge,
            start_color,
        )?
        .paint(view, family, maxiter, palette, colormap),
    }
}

/// Color one field into linear-light RGB, one entry per sample.
///
/// Kept as the plain-recipe spelling of [`shade`], because a recolor of a dumped
/// field asks exactly this and reads nothing about a palette recipe.
pub fn colorize(field: &Field, transform: Transform, colormap: &Colormap) -> Vec<[f64; 3]> {
    shade(field, transform, &Palette::default(), colormap)
}

/// Color one field into linear-light RGB, through a palette recipe.
///
/// The order is the whole of it: stretch, then transfer, then the mode's curve,
/// then gamma and the traversal, then the map. Each stage takes `[0, 1]` to
/// `[0, 1]`, so any of them can be the identity without the rest noticing.
pub fn shade(
    field: &Field,
    transform: Transform,
    palette: &Palette,
    colormap: &Colormap,
) -> Vec<[f64; 3]> {
    let stretch = Stretch::measure(field);
    let edges = edges_for(field, &stretch, palette);
    field
        .values
        .par_iter()
        .map(|&value| {
            if !value.is_finite() {
                return INTERIOR;
            }
            let mut position = stretch.position(value as f64);
            if let Some(edges) = &edges {
                position = edges.remap(position);
            }
            colormap.lookup(palette.place(transform.apply(position)))
        })
        .collect()
}

/// Blend two fields into linear-light RGB.
///
/// Where only one of the two has a value, that one is used alone rather than the
/// pair being discarded. That is what keeps a smooth base + trap texture from
/// blacking out the interior: the smooth field says nothing there, the trap
/// field does, and the picture should show what is known rather than nothing.
#[allow(clippy::too_many_arguments)]
fn composite(
    base: &Field,
    texture: &Field,
    base_transform: Transform,
    texture_transform: Transform,
    blend: Blend,
    weight: f64,
    palette: &Palette,
    colormap: &Colormap,
) -> Vec<[f64; 3]> {
    let base_stretch = Stretch::measure(base);
    let texture_stretch = Stretch::measure(texture);
    // The recipe describes the picture, and the picture is what the base makes:
    // the texture is a screen over it and carries no gamma of its own. The
    // traversal comes after the blend, because it is about the color the pair
    // arrived at rather than about either field.
    let edges = edges_for(base, &base_stretch, palette);
    let gamma = Palette {
        cycles: 1.0,
        phase: 0.0,
        ..*palette
    };
    base.values
        .par_iter()
        .zip(&texture.values)
        .map(|(&base_value, &texture_value)| {
            let under = base_value.is_finite().then(|| {
                let mut position = base_stretch.position(base_value as f64);
                if let Some(edges) = &edges {
                    position = edges.remap(position);
                }
                gamma.place(base_transform.apply(position))
            });
            let over = texture_value
                .is_finite()
                .then(|| texture_transform.apply(texture_stretch.position(texture_value as f64)));
            let gray = match (under, over) {
                (None, None) => return INTERIOR,
                (Some(under), None) => under,
                (None, Some(over)) => over,
                (Some(under), Some(over)) => under + (blend.apply(under, over) - under) * weight,
            };
            colormap.lookup(
                Palette {
                    gamma: 1.0,
                    ..*palette
                }
                .place(gray),
            )
        })
        .collect()
}

/// The `p`-th percentile of `values`, which is partially reordered in place.
fn percentile(values: &mut [f64], p: f64) -> f64 {
    let last = values.len() - 1;
    let index = (((p / 100.0) * last as f64).round() as usize).min(last);
    let (_, nth, _) = values.select_nth_unstable_by(index, f64::total_cmp);
    *nth
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::colormap::Kind;

    fn field_of(values: &[f32]) -> Field {
        Field {
            values: values.to_vec(),
            width: values.len() as u32,
            height: 1,
        }
    }

    fn white() -> Colormap {
        Colormap::from_stops(
            "two",
            Kind::Sequential,
            &[(0.0, [255, 255, 255]), (1.0, [255, 255, 255])],
        )
        .unwrap()
    }

    fn ramp() -> Colormap {
        Colormap::from_stops(
            "ramp",
            Kind::Sequential,
            &[(0.0, [0, 0, 0]), (1.0, [255, 255, 255])],
        )
        .unwrap()
    }

    #[test]
    fn percentiles_bracket_the_data() {
        let mut values: Vec<f64> = (0..=100).map(|i| i as f64).collect();
        assert_eq!(percentile(&mut values.clone(), 0.0), 0.0);
        assert_eq!(percentile(&mut values.clone(), 50.0), 50.0);
        assert_eq!(percentile(&mut values, 100.0), 100.0);
    }

    #[test]
    fn the_stretch_spans_the_bulk_of_the_frame() {
        let values: Vec<f32> = (0..1000).map(|i| i as f32).collect();
        let stretch = Stretch::measure(&field_of(&values));
        assert!(stretch.position(0.0) <= 0.0);
        assert!(stretch.position(999.0) >= 1.0);
        assert!((stretch.position(500.0) - 0.5).abs() < 0.02);
    }

    /// A few runaway samples must not flatten everything else. Without the
    /// percentile trim, one value a thousand times the rest would push the whole
    /// distribution into the first thousandth of the gradient.
    #[test]
    fn outliers_do_not_compress_the_gradient() {
        let mut values: Vec<f32> = (0..1000).map(|i| i as f32).collect();
        values.push(1_000_000.0);
        let stretch = Stretch::measure(&field_of(&values));
        assert!((stretch.position(500.0) - 0.5).abs() < 0.02);
    }

    #[test]
    fn samples_without_a_value_color_black_and_the_rest_do_not() {
        let field = field_of(&[f32::NAN, 1.0, 2.0, 3.0]);
        let colors = colorize(&field, Transform::Linear, &white());
        assert_eq!(colors[0], INTERIOR);
        for color in &colors[1..] {
            assert!(color[0] > 0.9, "valid sample colored {color:?}");
        }
    }

    #[test]
    fn a_field_with_no_valid_samples_is_all_interior() {
        let colors = colorize(&field_of(&[f32::NAN; 8]), Transform::Linear, &white());
        assert!(colors.iter().all(|&c| c == INTERIOR));
    }

    /// Every curve must be a reparameterization of the gradient and nothing
    /// more: it may not leave `[0, 1]`, and it may not reorder the field.
    #[test]
    fn every_curve_is_monotone_on_the_unit_interval() {
        for transform in [
            Transform::Linear,
            Transform::Sqrt,
            Transform::Log,
            Transform::Scurve,
        ] {
            assert!(transform.apply(0.0).abs() < 1e-12, "{transform:?} at 0");
            assert!(
                (transform.apply(1.0) - 1.0).abs() < 1e-12,
                "{transform:?} at 1"
            );
            let mut previous = -1.0;
            for step in 0..=1000 {
                let y = transform.apply(step as f64 / 1000.0);
                assert!((0.0..=1.0).contains(&y), "{transform:?} left the interval");
                assert!(y >= previous, "{transform:?} is not monotone");
                previous = y;
            }
        }
        // Sqrt and log lift the low end; the S-curve pushes it down.
        assert!(Transform::Sqrt.apply(0.25) > 0.25);
        assert!(Transform::Log.apply(0.25) > 0.25);
        assert!(Transform::Scurve.apply(0.25) < 0.25);
    }

    #[test]
    fn every_blend_stays_inside_the_unit_square() {
        for blend in [
            Blend::Normal,
            Blend::Multiply,
            Blend::Screen,
            Blend::Overlay,
            Blend::Min,
        ] {
            for a in 0..=20 {
                for b in 0..=20 {
                    let value = blend.apply(a as f64 / 20.0, b as f64 / 20.0);
                    assert!((0.0..=1.0).contains(&value), "{blend:?} gave {value}");
                }
            }
        }
        assert_eq!(Blend::Screen.apply(0.0, 0.5), 0.5);
        assert_eq!(Blend::Screen.apply(1.0, 0.0), 1.0);
        assert_eq!(Blend::Multiply.apply(0.5, 0.5), 0.25);
    }

    /// Screen only ever brightens, which is why it is the composite blend: a
    /// texture can add structure to the base but never subtract the base's own.
    #[test]
    fn screen_never_darkens_the_base() {
        for a in 0..=20 {
            for b in 0..=20 {
                let (under, over) = (a as f64 / 20.0, b as f64 / 20.0);
                assert!(Blend::Screen.apply(under, over) >= under - 1e-12);
            }
        }
    }

    /// The texture weight must be a real fade between the base alone and the
    /// full blend, with both ends exact.
    #[test]
    fn the_texture_weight_fades_between_the_base_and_the_blend() {
        let base = field_of(&[0.0, 1.0, 2.0, 3.0]);
        let texture = field_of(&[3.0, 2.0, 1.0, 0.0]);
        let map = ramp();
        let paint = |weight| {
            composite(
                &base,
                &texture,
                Transform::Linear,
                Transform::Linear,
                Blend::Screen,
                weight,
                &Palette::default(),
                &map,
            )
        };
        let none = paint(0.0);
        let alone = colorize(&base, Transform::Linear, &map);
        for (a, b) in none.iter().zip(&alone) {
            assert_eq!(a, b, "weight 0 must be the base alone");
        }
        let full = paint(1.0);
        for (faded, screened) in none.iter().zip(&full) {
            assert!(screened[0] >= faded[0] - 1e-12);
        }
        assert!(full[0][0] > none[0][0], "the texture never showed up");
    }

    /// Where one field has nothing to say the other carries the sample alone —
    /// the property that lets a smooth base keep a trap texture's interior.
    #[test]
    fn a_composite_falls_back_to_whichever_field_has_a_value() {
        let base = field_of(&[f32::NAN, f32::NAN, 0.0, 1.0]);
        let texture = field_of(&[f32::NAN, 0.5, 1.0, 0.0]);
        let colors = composite(
            &base,
            &texture,
            Transform::Linear,
            Transform::Linear,
            Blend::Screen,
            1.0,
            &Palette::default(),
            &ramp(),
        );
        assert_eq!(colors[0], INTERIOR, "neither field had a value");
        assert!(
            colors[1] != INTERIOR,
            "the texture alone should still paint"
        );
    }

    #[test]
    fn a_coloring_round_trips_through_json() {
        let colorings = [
            Coloring::default(),
            Coloring::Composite {
                base: Layer {
                    field: FieldSpec::Smooth,
                    transform: Transform::Linear,
                },
                texture: Layer {
                    field: FieldSpec::TrapCircle { radius: 1.0 },
                    transform: Transform::Linear,
                },
                blend: Blend::Screen,
                texture_weight: 0.85,
            },
            Coloring::Direct {
                shape: Shape::Ring,
                trap_radius: 1.0,
                threshold: Some(0.0597),
                opacity: 0.45,
                merge: Blend::Screen,
                start_color: "black".into(),
            },
        ];
        for coloring in colorings {
            let text = serde_json::to_string(&coloring).unwrap();
            let back: Coloring = serde_json::from_str(&text).unwrap();
            assert_eq!(coloring, back, "{text}");
            coloring.validate().unwrap();
        }
    }

    #[test]
    fn a_composite_of_a_field_with_itself_is_refused() {
        let layer = |density| Layer {
            field: FieldSpec::Stripe { density },
            transform: Transform::Linear,
        };
        let message = Coloring::Composite {
            base: layer(6.0),
            texture: layer(3.0),
            blend: Blend::Screen,
            texture_weight: 0.85,
        }
        .validate()
        .unwrap_err();
        assert!(message.contains("stripe"), "{message}");
    }

    #[test]
    fn only_a_single_field_coloring_can_be_dumped() {
        assert!(Coloring::default().dumpable_field().is_some());
        assert!(Coloring::default().why_not_a_field().is_none());
        let direct = Coloring::Direct {
            shape: Shape::Cross,
            trap_radius: 1.0,
            threshold: None,
            opacity: 0.15,
            merge: Blend::Screen,
            start_color: "black".into(),
        };
        assert!(direct.dumpable_field().is_none());
        assert!(direct.why_not_a_field().unwrap().contains("color-valued"));
    }

    /// The default recipe is the identity: this is what lets every existing mode
    /// and every existing record keep meaning what it meant.
    #[test]
    fn a_recipe_that_says_nothing_moves_nothing() {
        let plain = Palette::default();
        for step in 0..=20 {
            let value = step as f64 / 20.0;
            assert_eq!(plain.place(value), value);
        }
    }

    /// Traversing the gradient twice puts the whole of it in each half of the
    /// range; a phase shift rotates where it starts.
    #[test]
    fn cycles_repeat_the_gradient_and_phase_rotates_it() {
        let twice = Palette {
            cycles: 2.0,
            ..Palette::default()
        };
        assert!((twice.place(0.25) - 0.5).abs() < 1e-12);
        assert!((twice.place(0.75) - 0.5).abs() < 1e-12);

        let shifted = Palette {
            phase: 0.25,
            ..Palette::default()
        };
        assert!((shifted.place(0.5) - 0.75).abs() < 1e-12);
        assert!((shifted.place(0.9) - 0.15).abs() < 1e-12);
    }

    /// Gamma below one lifts the low end and above one pushes it down, and
    /// neither can reorder two values.
    #[test]
    fn gamma_bends_the_range_without_reordering_it() {
        let lifted = Palette {
            gamma: 0.5,
            ..Palette::default()
        };
        let pushed = Palette {
            gamma: 2.0,
            ..Palette::default()
        };
        assert!(lifted.place(0.25) > 0.25);
        assert!(pushed.place(0.25) < 0.25);
        for step in 0..20 {
            let (low, high) = (step as f64 / 20.0, (step + 1) as f64 / 20.0);
            assert!(lifted.place(low) <= lifted.place(high));
            assert!(pushed.place(low) <= pushed.place(high));
        }
    }

    /// A weight of zero weighs every bin the same, so the edge transfer gives
    /// back the straight line it started from. That is the family's own edge and
    /// the reason it is one transfer with a dial rather than two transfers.
    #[test]
    fn the_edge_transfer_at_zero_weight_is_the_value_transfer() {
        let field = field_of(&[0.0, 1.0, 2.0, 40.0, 41.0, 42.0, 80.0, 81.0, 82.0]);
        let stretch = Stretch::measure(&field);
        let edges = Edges::measure(&field, &stretch, 0.0);
        for step in 0..=20 {
            let value = step as f64 / 20.0;
            assert!(
                (edges.remap(value) - value).abs() < 1e-9,
                "weight 0 moved {value} to {}",
                edges.remap(value)
            );
        }
    }

    /// With weight above zero the transfer is still a remap of [0, 1] onto
    /// itself and still monotone — it may not reorder the field, only decide how
    /// much color each part of it gets.
    #[test]
    fn the_edge_transfer_is_a_monotone_remap_of_the_whole_range() {
        let mut values = Vec::new();
        for _row in 0..16 {
            for col in 0..16 {
                // A field that is flat on one side and steep on the other, so
                // the two halves have something to disagree about.
                values.push(if col < 8 {
                    col as f32
                } else {
                    (col as f32) * 20.0
                });
            }
        }
        let field = Field {
            width: 16,
            height: 16,
            values,
        };
        let stretch = Stretch::measure(&field);
        let edges = Edges::measure(&field, &stretch, 1.0);
        assert!(edges.remap(0.0).abs() < 1e-12);
        assert!((edges.remap(1.0) - 1.0).abs() < 1e-12);
        let mut previous = -1.0;
        for step in 0..=100 {
            let here = edges.remap(step as f64 / 100.0);
            assert!(here >= previous - 1e-12, "the remap went backwards");
            previous = here;
        }
    }
}
