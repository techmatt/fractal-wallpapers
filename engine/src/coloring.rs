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
///
/// The third spends it by **rank**: every sample gets the same share, so the
/// gradient is spent evenly over the *samples* rather than over the values.
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
    /// Spend it by the sample's rank among the frame's own samples: histogram
    /// equalization, and the one transfer that replaces the percentile stretch
    /// rather than remapping it.
    ///
    /// It replaces it because it *is* a normalization, and a stronger one: the
    /// stretch trims half a percent from each end and maps what is left linearly,
    /// so a badly skewed field still lands skewed. A rank flattens the
    /// distribution outright — half the samples are below the middle of the
    /// gradient by construction, whatever the values were — which is why nothing
    /// clips and why the result is the same picture at every location.
    ///
    /// The price is that it is not a function of the value alone: two frames of
    /// the same field at different places spend their gradient differently, and
    /// equal spans of value no longer get equal spans of color. That is the right
    /// trade only when the *ordering* is the content, which is the case for the
    /// palette-position modulation in [`Coloring::Modulate`].
    Rank,
}

/// How many value bins the edge transfer measures over. Fine enough that the
/// remap is smooth, coarse enough that every bin holds samples to average.
pub const TRANSFER_BINS: usize = 200;

/// The weight a bin that measured no movement still gets, before the exponent.
///
/// Not a guard against zero — it is the **floor on how flat the transfer may
/// get**, and it is load-bearing. At a weight of `1/4` a bin measuring nothing
/// is worth `0.02^0.25 = 0.38` of the busiest bin's share rather than nearly
/// nothing, so a smooth region keeps a visible span of the gradient instead of
/// collapsing onto one color. Dropping it to a rounding guard changes the
/// picture by a third of the range on the frames that use this transfer, which
/// is how its value was found.
const TRANSFER_FLOOR: f64 = 0.02;

/// What happens to the brightest part of a picture before it is written.
///
/// The screening colorings drive their output toward white: every trap hit lifts
/// the accumulator and enough of them stack into a flat white plateau with the
/// color washed out of it. A rolloff bends the top of the tone range back down so
/// that color re-emerges, and leaves the midtones and shadows where they are.
///
/// It acts on **luminance**, not on each channel: the three channels are rescaled
/// by one ratio, so a highlight keeps its hue. Curving each channel separately
/// would pull the brightest one down fastest and drain the highlight toward gray,
/// which is the thing being fixed.
#[derive(Clone, Copy, Debug, Default, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Rolloff {
    /// Leave the highlights alone. The exact identity.
    #[default]
    None,
    /// Identity up to `knee`, then a `tanh` shoulder that approaches white
    /// without reaching it. Continuous in value and in slope at the knee, so
    /// nothing below it moves at all and there is no visible join.
    SoftKnee { knee: f64 },
    /// `l/(1+l)` everywhere. The classic photographic curve: it has no knee, so
    /// it starts compressing from zero and *every* tone moves, the shadows least.
    /// Half unit slope at the origin, which is what makes it read as a flatter,
    /// filmic picture rather than as a rescued highlight.
    Reinhard,
    /// The ACES filmic approximation, `(l(2.51l+0.03))/(l(2.43l+0.59)+0.14)`.
    ///
    /// The one curve here that is an **S** rather than a compression: it *darkens*
    /// the deep shadows, *lifts* the midtones above the identity, and compresses
    /// the highlights. So contrast survives the rolloff instead of being spent on
    /// it — which is the difference between a picture that has been tone-mapped and
    /// one that has been flattened — and it is also why this is the only rolloff
    /// here that can make a sample brighter than it arrived.
    ///
    /// It has a genuine white point: the fit crosses 1 at `l ≈ 7.24` and is clamped
    /// there. Nothing in this pipeline reaches it — a painted pixel is a colormap
    /// lookup in `[0, 1]`, where the curve tops out at `0.80` — but the clamp is
    /// what keeps that a fact about the input rather than a hazard.
    Aces,
}

impl Rolloff {
    /// Map one luminance value. `l` is non-negative.
    pub fn apply(self, l: f64) -> f64 {
        match self {
            Rolloff::None => l,
            Rolloff::SoftKnee { knee } => {
                if l <= knee {
                    l
                } else {
                    knee + (1.0 - knee) * ((l - knee) / (1.0 - knee)).tanh()
                }
            }
            Rolloff::Reinhard => l / (1.0 + l),
            Rolloff::Aces => {
                ((l * (2.51 * l + 0.03)) / (l * (2.43 * l + 0.59) + 0.14)).clamp(0.0, 1.0)
            }
        }
    }

    /// Rescale one linear-light pixel so its luminance is rolled off.
    pub fn shade(self, pixel: [f64; 3]) -> [f64; 3] {
        if self == Rolloff::None {
            return pixel;
        }
        let luminance = 0.2126 * pixel[0] + 0.7152 * pixel[1] + 0.0722 * pixel[2];
        if luminance <= 1e-9 {
            return pixel;
        }
        let scale = self.apply(luminance) / luminance;
        [
            (pixel[0] * scale).clamp(0.0, 1.0),
            (pixel[1] * scale).clamp(0.0, 1.0),
            (pixel[2] * scale).clamp(0.0, 1.0),
        ]
    }
}

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
    /// What happens to the highlights once a color has been chosen. The one
    /// stage here that acts on the color rather than on the index into the map,
    /// and it is here because it belongs to the same recipe a record carries.
    pub rolloff: Rolloff,
}

impl Default for Palette {
    fn default() -> Palette {
        Palette {
            gamma: 1.0,
            cycles: 1.0,
            phase: 0.0,
            bake: crate::colormap::Bake::default(),
            transfer: Transfer::Value,
            rolloff: Rolloff::None,
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
        if let Rolloff::SoftKnee { knee } = self.rolloff
            && !(knee.is_finite() && (0.0..1.0).contains(&knee))
        {
            return Err(format!(
                "the rolloff's knee must be at least 0 and below 1, got {knee}"
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
    /// `min(a+b, 1)` — genuinely additive, clamped at the top of the range.
    ///
    /// Not screen, and the difference is the point. Screen is `a+b−ab`, so the
    /// texture's contribution shrinks as the base brightens and vanishes where the
    /// base is already white: it is a *soft* lift that can never overshoot. Add
    /// lifts by the same amount everywhere and saturates when the sum runs out of
    /// range, which is a harder, brighter texture — and the operator the `threads`
    /// mode was tuned against. Substituting screen for it is a different picture,
    /// not a rounding of the same one.
    Add,
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
            Blend::Add => (under + over).min(1.0),
        }
    }
}

/// Which side of a direct trap's merge the new gradient sample is on.
///
/// A direct trap composites one sample per near miss into what the earlier misses
/// already left behind, so there are two operands and an order to put them in.
/// **Three of the five blends are commutative and cannot tell the difference**;
/// `normal` and `overlay` can, and for those the order decides whether the orbit's
/// last near miss covers its first or is covered by it.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MergeOrder {
    /// The new sample goes over what is already there. The order every mode in the
    /// catalog uses, and what every record written before this key existed meant.
    #[default]
    BottomUp,
    /// What is already there goes over the new sample, so the orbit's *earliest*
    /// near miss is the one on top.
    TopDown,
}

impl MergeOrder {
    /// Merge an existing pixel with a new gradient sample, this way round.
    pub fn merge(self, blend: Blend, standing: f64, sample: f64) -> f64 {
        match self {
            MergeOrder::BottomUp => blend.apply(standing, sample),
            MergeOrder::TopDown => blend.apply(sample, standing),
        }
    }

    fn is_default(&self) -> bool {
        *self == MergeOrder::BottomUp
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
        /// A power applied to the texture's normalized value before the blend, so
        /// the texture can be bent without bending the base.
        ///
        /// The palette recipe's own `gamma` describes the *picture*, which is what
        /// the base makes; this is the texture's alone. Absent means the texture
        /// carries no gamma of its own, which is what every composite here does
        /// and what every record written before this key existed means — so the
        /// key appears in a record only when it says something. That is a
        /// deliberate exception to "echo every default": the composite coloring is
        /// hashed into the render cache's file names, and a key that appeared
        /// unconditionally would rename every picture the corpora were built from.
        #[serde(default, skip_serializing_if = "Option::is_none")]
        texture_gamma: Option<f64>,
    },
    /// A base whose *palette position* the texture perturbs, rather than whose
    /// value it blends with.
    ///
    /// Every other composite here is a blend in field space: two fields are
    /// normalized, merged into one number, and that number is looked up once. This
    /// one looks up a **different place in the gradient per sample**: the base is
    /// spent by rank, and the texture shifts where in the gradient that rank lands.
    ///
    /// The consequence is what the shape is for. Where the base is detailed its
    /// rank sweeps the gradient quickly and a modest shift is a minor recolor;
    /// where the base is flat the rank barely moves and the shift is the only
    /// variation there is. So the texture fills in the *boring* regions and leaves
    /// the busy ones nearly alone — which no field-space blend does, because a
    /// blend's strength does not know how fast the base is moving.
    ///
    /// **The base is spent by rank as part of what this is**, not as a palette
    /// knob: `shift` is a distance along the gradient, and it only means the same
    /// thing everywhere in the frame if the base's own spending is uniform. A
    /// palette recipe that asks for another transfer alongside this coloring is
    /// refused rather than quietly overridden — see [`Coloring::agrees_with`].
    Modulate {
        base: Layer,
        texture: Layer,
        /// How far the texture may push the base's palette position, in turns of
        /// the gradient. Modest is the point: at 0.5 the address perturbs the
        /// base's own structure, and by 1.5 it overrides it.
        #[serde(default = "half")]
        shift: f64,
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
        /// Which side of the merge a new sample is on. Absent is `bottom_up`, and
        /// absent for the same recorded-name reason `texture_gamma` is.
        #[serde(default, skip_serializing_if = "MergeOrder::is_default")]
        merge_order: MergeOrder,
        #[serde(default = "black")]
        start_color: String,
        /// The curve the nearness of a hit is read through, before the palette
        /// recipe places it. A direct trap has no field to normalize, so this is
        /// the one curve in its path and it acts on the same `[0, 1]` a field
        /// mode's stretch produces.
        #[serde(default)]
        transform: Transform,
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
                texture_gamma,
                ..
            } => {
                if base.field.conflicts_with(&texture.field) {
                    return Err(format!(
                        "a composite of '{}' with itself has nothing to blend, and one orbit \
                         carries only one set of that field's constants",
                        base.field.name()
                    ));
                }
                in_unit_interval(*texture_weight, "texture_weight")?;
                if texture_gamma.is_some_and(|gamma| !(gamma.is_finite() && gamma > 0.0)) {
                    return Err(format!(
                        "texture_gamma must be positive, got {}",
                        texture_gamma.expect("checked as present above")
                    ));
                }
                Ok(())
            }
            Coloring::Modulate {
                base,
                texture,
                shift,
            } => {
                if base.field.conflicts_with(&texture.field) {
                    return Err(format!(
                        "a modulate of '{}' with itself would shift the gradient by the same \
                         quantity it is spending it on",
                        base.field.name()
                    ));
                }
                if !shift.is_finite() {
                    return Err(format!("shift must be a number, got {shift}"));
                }
                Ok(())
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
            Coloring::Modulate { .. } => Some(
                "a modulate looks up a different place in the gradient per sample, so there is \
                 no single scalar index behind it — and its texture is carried at f64 precisely \
                 to keep it out of the f32 dump. Dump one of its two fields on its own instead.",
            ),
            Coloring::Direct { .. } => Some(
                "a direct trap is color-valued: it composites gradient samples during the \
                 iteration and never produces a scalar index, so there is nothing to serialize",
            ),
        }
    }

    /// Check this coloring against the palette recipe it will be rendered through.
    ///
    /// Almost every pairing is free — a coloring produces a `[0, 1]` and a recipe
    /// spends the gradient on it, and neither needs to know about the other. The
    /// one exception is [`Coloring::Modulate`], which spends its base by rank as
    /// part of its own definition: a recipe asking for a different transfer
    /// alongside it is asking for something this cannot do, and the honest answer
    /// is a message rather than a render that quietly ignored the request.
    pub fn agrees_with(&self, palette: &Palette) -> Result<(), String> {
        if matches!(self, Coloring::Modulate { .. }) && palette.transfer != Transfer::Value {
            return Err(format!(
                "a modulate spends its base by rank as part of what it is, so a recipe cannot \
                 also spend it by {:?} — one of the two requests would have to be dropped. Leave \
                 the palette's transfer unset with this coloring.",
                palette.transfer
            ));
        }
        Ok(())
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
        Stretch::over(field.values.iter().map(|&value| value as f64))
    }

    /// Measure the stretch over any run of samples, invalid ones included.
    ///
    /// A crop of a larger field normalizes against **its own** samples, not
    /// against the field it was cut from: the whole point of the stretch is that
    /// a frame frames itself, and a tile borrowing a wider frame's percentiles
    /// would be colored for a picture nobody is looking at.
    pub fn over(samples: impl Iterator<Item = f64>) -> Stretch {
        let mut valid: Vec<f64> = samples.filter(|v| v.is_finite()).collect();
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

/// A frame's samples in sorted order: what turns a value into its rank.
///
/// The one normalization here that is not a formula but a *sort*. It is built from
/// the frame's own valid samples and answers, for any value, what share of them
/// were below it — histogram equalization, and the same thing the percentile
/// stretch already computes at two points rather than at all of them.
///
/// The rank is a **midrank**: the mean of the shares strictly below and at-or-below
/// the value, so a plateau of equal samples lands at the middle of the span it
/// occupies rather than at one end of it. That is what keeps a field with a large
/// flat region from putting the whole region at the very top or bottom of the
/// gradient.
pub struct Ranks {
    sorted: Vec<f64>,
}

impl Ranks {
    /// Sort a frame's valid samples, ready to rank against.
    pub fn measure(samples: impl Iterator<Item = f64>) -> Ranks {
        let mut sorted: Vec<f64> = samples.filter(|value| value.is_finite()).collect();
        sorted.sort_unstable_by(f64::total_cmp);
        Ranks { sorted }
    }

    /// Where this value falls among the frame's samples, in `[0, 1]`.
    pub fn position(&self, value: f64) -> f64 {
        if self.sorted.is_empty() {
            return 0.0;
        }
        let below = self.sorted.partition_point(|&other| other < value);
        let at_or_below = self.sorted.partition_point(|&other| other <= value);
        0.5 * (below + at_or_below) as f64 / self.sorted.len() as f64
    }
}

/// A [`Transfer`] measured against one frame: what a raw field value becomes.
///
/// The three variants are not three stages — they are three answers to the same
/// question, and picking one is what a transfer *is*. Value and edge share the
/// percentile stretch, because the edge transfer remaps a stretched position;
/// rank replaces the stretch outright, because it is a normalization of its own.
enum Spend {
    Value(Stretch),
    Edge(Stretch, Edges),
    Rank(Ranks),
}

impl Spend {
    /// Measure the transfer this recipe asks for over one field.
    fn measure(field: &Field, transfer: Transfer) -> Spend {
        match transfer {
            Transfer::Value => Spend::Value(Stretch::measure(field)),
            Transfer::Edge { weight } => {
                let stretch = Stretch::measure(field);
                let edges = Edges::measure(field, &stretch, weight);
                Spend::Edge(stretch, edges)
            }
            Transfer::Rank => Spend::Rank(Ranks::measure(
                field.values.iter().map(|&value| value as f64),
            )),
        }
    }

    /// Where one raw field value lands on the gradient, in `[0, 1]`.
    fn position(&self, value: f64) -> f64 {
        match self {
            Spend::Value(stretch) => stretch.position(value),
            Spend::Edge(stretch, edges) => edges.remap(stretch.position(value)),
            Spend::Rank(ranks) => ranks.position(value),
        }
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
    let mut painted = paint_untoned(view, family, maxiter, coloring, palette, colormap)?;
    if palette.rolloff != Rolloff::None {
        // Last, on the finished color and before anything averages it: rolling
        // off after the resample would bend a highlight the resample had already
        // blended into its neighbours.
        painted.linear = painted
            .linear
            .par_iter()
            .map(|&pixel| palette.rolloff.shade(pixel))
            .collect();
    }
    Ok(painted)
}

fn paint_untoned(
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
            texture_gamma,
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
                    *texture_gamma,
                    palette,
                    colormap,
                ),
                interior_fraction: sampled.interior_fraction,
            })
        }
        Coloring::Modulate {
            base,
            texture,
            shift,
        } => {
            // The exact pass, and the reason it exists: the texture here is an
            // address whose deep digits are the picture, so it never narrows.
            let (fields, interior_fraction) =
                field::sample_exact(view, family, maxiter, &[base.field, texture.field]);
            Ok(Painted {
                linear: modulate(
                    &fields[0].narrow(),
                    &fields[1],
                    base.transform,
                    texture.transform,
                    *shift,
                    palette,
                    colormap,
                ),
                interior_fraction,
            })
        }
        Coloring::Direct {
            shape,
            trap_radius,
            threshold,
            opacity,
            merge,
            merge_order,
            start_color,
            transform,
        } => direct_trap::Painter::new(
            *shape,
            *trap_radius,
            *threshold,
            *opacity,
            *merge,
            *merge_order,
            start_color,
            *transform,
        )?
        .paint(view, family, maxiter, colormap),
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
    let spend = Spend::measure(field, palette.transfer);
    field
        .values
        .par_iter()
        .map(|&value| {
            if !value.is_finite() {
                return INTERIOR;
            }
            let position = spend.position(value as f64);
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
    texture_gamma: Option<f64>,
    palette: &Palette,
    colormap: &Colormap,
) -> Vec<[f64; 3]> {
    let base_spend = Spend::measure(base, palette.transfer);
    let texture_stretch = Stretch::measure(texture);
    // The recipe describes the picture, and the picture is what the base makes:
    // the texture is a screen over it and carries no gamma from the recipe. Its own
    // `texture_gamma` is the one power that reaches it. The traversal comes after
    // the blend, because it is about the color the pair arrived at rather than
    // about either field.
    let gamma = Palette {
        cycles: 1.0,
        phase: 0.0,
        ..*palette
    };
    base.values
        .par_iter()
        .zip(&texture.values)
        .map(|(&base_value, &texture_value)| {
            let under = base_value
                .is_finite()
                .then(|| gamma.place(base_transform.apply(base_spend.position(base_value as f64))));
            let over = texture_value.is_finite().then(|| {
                let value = texture_transform.apply(texture_stretch.position(texture_value as f64));
                match texture_gamma {
                    Some(power) => value.powf(power),
                    None => value,
                }
            });
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

/// Modulate the base's palette position by the texture.
///
/// `position = frac( rank(base) + shift · normalize(texture) )`, and the texture
/// arrives as [`field::Exact`] rather than as a `Field` because the one coloring
/// this shape exists for carries a value whose deep digits do not survive `f32`.
///
/// Two departures from [`composite`], both deliberate:
///
/// * **The base is spent by rank**, always. See [`Coloring::Modulate`].
/// * **A sample the base has nothing to say about is interior**, even where the
///   texture does have a value. A composite falls back to the texture alone
///   because the two are peers; here the texture is a perturbation *of* the base
///   and there is nothing to perturb, so the honest answer is the set's own black.
fn modulate(
    base: &Field,
    texture: &field::Exact,
    base_transform: Transform,
    texture_transform: Transform,
    shift: f64,
    palette: &Palette,
    colormap: &Colormap,
) -> Vec<[f64; 3]> {
    let ranks = Ranks::measure(base.values.iter().map(|&value| value as f64));
    let spread = Stretch::over(texture.values.iter().copied());
    base.values
        .par_iter()
        .zip(&texture.values)
        .map(|(&base_value, &texture_value)| {
            if !base_value.is_finite() {
                return INTERIOR;
            }
            let gray = base_transform.apply(ranks.position(base_value as f64));
            let over = if texture_value.is_finite() {
                texture_transform.apply(spread.position(texture_value))
            } else {
                0.0
            };
            // The perturbation rides on the recipe's own phase rather than
            // replacing it: `place` already computes `frac(gray·cycles + phase)`,
            // so a per-sample phase is the whole of what this coloring needs and
            // there is no second traversal stage to keep in agreement with it.
            let placed = Palette {
                phase: palette.phase + shift * over,
                ..*palette
            }
            .place(gray);
            colormap.lookup(placed)
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
        for blend in EVERY_BLEND {
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

    const EVERY_BLEND: [Blend; 6] = [
        Blend::Normal,
        Blend::Multiply,
        Blend::Screen,
        Blend::Overlay,
        Blend::Min,
        Blend::Add,
    ];

    /// Add is a sum, and that is what makes it a different operator from screen
    /// rather than a rounding of it: below saturation the two disagree by exactly
    /// the product they differ by on paper, and add is the brighter of them.
    #[test]
    fn add_is_a_sum_and_screen_is_not() {
        assert_eq!(Blend::Add.apply(0.25, 0.5), 0.75);
        assert_eq!(
            Blend::Add.apply(0.5, 0.75),
            1.0,
            "add saturates, it does not wrap"
        );
        assert_eq!(Blend::Add.apply(0.0, 0.4), 0.4);
        for a in 0..=20 {
            for b in 0..=20 {
                let (under, over) = (a as f64 / 20.0, b as f64 / 20.0);
                let (sum, screen) = (
                    Blend::Add.apply(under, over),
                    Blend::Screen.apply(under, over),
                );
                assert!(sum >= screen - 1e-12, "screen out-brightened add");
                if under + over <= 1.0 {
                    assert!(
                        ((sum - screen) - under * over).abs() < 1e-12,
                        "the two differ by something other than their product"
                    );
                }
            }
        }
    }

    /// The commutative blends cannot tell the two merge orders apart, and the two
    /// that are not commutative must. That split is the whole content of the knob:
    /// setting it on a screened trap would be a no-op that looked like a choice.
    #[test]
    fn the_merge_order_matters_exactly_where_the_blend_is_not_commutative() {
        let (standing, sample) = (0.3, 0.8);
        for blend in EVERY_BLEND {
            let up = MergeOrder::BottomUp.merge(blend, standing, sample);
            let down = MergeOrder::TopDown.merge(blend, standing, sample);
            let commutative = matches!(
                blend,
                Blend::Multiply | Blend::Screen | Blend::Min | Blend::Add
            );
            if commutative {
                assert_eq!(up, down, "{blend:?} should not notice the order");
            } else {
                assert_ne!(up, down, "{blend:?} should notice the order");
            }
        }
        assert_eq!(MergeOrder::BottomUp.merge(Blend::Normal, 0.3, 0.8), 0.8);
        assert_eq!(MergeOrder::TopDown.merge(Blend::Normal, 0.3, 0.8), 0.3);
        assert_eq!(MergeOrder::default(), MergeOrder::BottomUp);
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
                None,
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
            None,
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
                texture_gamma: None,
            },
            Coloring::Composite {
                base: Layer {
                    field: FieldSpec::Smooth,
                    transform: Transform::Linear,
                },
                texture: Layer {
                    field: FieldSpec::Threads { sigma: 0.15 },
                    transform: Transform::Linear,
                },
                blend: Blend::Add,
                texture_weight: 0.5,
                texture_gamma: Some(0.7),
            },
            Coloring::Modulate {
                base: Layer {
                    field: FieldSpec::Smooth,
                    transform: Transform::Linear,
                },
                texture: Layer {
                    field: FieldSpec::Itinerary {
                        sectors: 4,
                        weight_base: Some(4.0),
                        depth: 26,
                    },
                    transform: Transform::Linear,
                },
                shift: 0.5,
            },
            Coloring::Direct {
                shape: Shape::Ring,
                trap_radius: 1.0,
                threshold: Some(0.0597),
                opacity: 0.45,
                merge: Blend::Screen,
                merge_order: MergeOrder::TopDown,
                start_color: "black".into(),
                transform: Transform::Linear,
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
            texture_gamma: None,
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
            merge_order: MergeOrder::BottomUp,
            start_color: "black".into(),
            transform: Transform::Linear,
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

    /// The rank transfer spends the gradient evenly over the *samples*, so a field
    /// whose values pile up in one corner comes out flat: every decile of the
    /// samples gets a decile of the gradient, whatever the values were. That is the
    /// property the percentile stretch does not have, and the reason this transfer
    /// replaces it rather than remapping it.
    #[test]
    fn the_rank_transfer_flattens_the_distribution_the_stretch_leaves_skewed() {
        // Ninety samples crushed into the bottom hundredth of the range and ten
        // spread across the rest: the shape a trap field actually has.
        let mut values: Vec<f32> = (0..90).map(|i| i as f32 / 9000.0).collect();
        values.extend((0..10).map(|i| 0.1 + i as f32));
        let field = Field {
            values,
            width: 100,
            height: 1,
        };
        let stretch = Stretch::measure(&field);
        let ranks = Ranks::measure(field.values.iter().map(|&v| v as f64));

        let crushed = field.values[..90]
            .iter()
            .filter(|&&v| stretch.position(v as f64) < 0.1)
            .count();
        assert!(crushed > 80, "the stretch was not skewed to begin with");
        let low = field.values[..90]
            .iter()
            .filter(|&&v| ranks.position(v as f64) < 0.1)
            .count();
        assert!(low < 20, "the rank left the pile piled up: {low} of 90");

        // Half the samples below the middle of the gradient, by construction.
        let below = field
            .values
            .iter()
            .filter(|&&v| ranks.position(v as f64) < 0.5)
            .count();
        assert!(
            (45..=55).contains(&below),
            "{below} of 100 below the middle"
        );
    }

    /// A rank is still a monotone remap onto `[0, 1]` — it may reweight the
    /// gradient, never reorder the field — and it answers for a frame with nothing
    /// in it rather than dividing by zero.
    #[test]
    fn a_rank_is_monotone_and_survives_an_empty_frame() {
        let ranks = Ranks::measure([3.0, 1.0, 2.0, 2.0, 5.0].into_iter());
        let mut previous = -1.0;
        for step in 0..=60 {
            let here = ranks.position(step as f64 / 10.0);
            assert!(
                (0.0..=1.0).contains(&here),
                "rank left the interval: {here}"
            );
            assert!(here >= previous, "the rank went backwards");
            previous = here;
        }
        // The repeated value lands at the middle of the span it occupies rather
        // than at either end of it: one sample below it, two at it, so the midrank
        // is halfway across the second and third of five.
        assert!((ranks.position(2.0) - 0.4).abs() < 1e-12);
        assert_eq!(Ranks::measure(std::iter::empty()).position(1.0), 0.0);
    }

    /// The whole path must honour the transfer the recipe names, not only the
    /// object that measures it: a rank-spent render of a skewed field has to differ
    /// from a value-spent one, and neither may leave the interior painted.
    #[test]
    fn shading_through_a_rank_differs_from_shading_through_the_stretch() {
        let mut values: Vec<f32> = (0..90).map(|i| i as f32 / 9000.0).collect();
        values.extend((0..9).map(|i| 0.1 + i as f32));
        values.push(f32::NAN);
        let field = Field {
            values,
            width: 100,
            height: 1,
        };
        let recipe = |transfer| Palette {
            transfer,
            ..Palette::default()
        };
        let by_value = shade(&field, Transform::Linear, &recipe(Transfer::Value), &ramp());
        let by_rank = shade(&field, Transform::Linear, &recipe(Transfer::Rank), &ramp());
        assert_eq!(by_value.last(), Some(&INTERIOR));
        assert_eq!(by_rank.last(), Some(&INTERIOR));
        let moved = by_value
            .iter()
            .zip(&by_rank)
            .filter(|(a, b)| (a[0] - b[0]).abs() > 1e-6)
            .count();
        assert!(moved > 50, "the rank transfer changed {moved} samples");
    }

    /// The texture's own gamma bends the texture and leaves the base where it is —
    /// which is the whole reason it is a separate knob from the recipe's gamma.
    #[test]
    fn the_texture_gamma_bends_the_texture_and_not_the_base() {
        let base = field_of(&[0.0, 1.0, 2.0, 3.0]);
        let texture = field_of(&[0.0, 1.0, 2.0, 3.0]);
        let paint = |gamma| {
            composite(
                &base,
                &texture,
                Transform::Linear,
                Transform::Linear,
                Blend::Screen,
                1.0,
                gamma,
                &Palette::default(),
                &ramp(),
            )
        };
        let plain = paint(None);
        assert_eq!(plain, paint(Some(1.0)), "a gamma of one is the identity");
        // A gamma below one lifts the texture, so a screen over it brightens.
        let lifted = paint(Some(0.4));
        let interior_lifted = lifted[1][0] > plain[1][0] + 1e-9;
        assert!(interior_lifted, "the texture gamma did nothing");
        // Where the texture is at the bottom of its range there is nothing for a
        // power to lift, so the base still decides that sample alone.
        assert!((lifted[0][0] - plain[0][0]).abs() < 1e-12);
    }

    /// The modulate's defining property: where the base is flat the texture is the
    /// only variation there is, and where the base is busy it is a perturbation.
    /// Read as two frames of the same texture over two different bases.
    #[test]
    fn a_modulate_fills_the_flat_base_and_perturbs_the_busy_one() {
        let texture = field::Exact {
            values: (0..64).map(|i| (i % 8) as f64).collect(),
            width: 8,
            height: 8,
        };
        let paint = |base: &Field| {
            modulate(
                base,
                &texture,
                Transform::Linear,
                Transform::Linear,
                0.5,
                &Palette::default(),
                &ramp(),
            )
        };
        let flat = Field {
            values: vec![1.0; 64],
            width: 8,
            height: 8,
        };
        let busy = Field {
            values: (0..64).map(|i| i as f32).collect(),
            width: 8,
            height: 8,
        };
        let over_flat = paint(&flat);
        let distinct: std::collections::BTreeSet<u64> =
            over_flat.iter().map(|c| c[0].to_bits()).collect();
        assert!(
            distinct.len() >= 8,
            "a flat base left the texture invisible: {} colors",
            distinct.len()
        );

        // Against the busy base the same texture must not be the whole picture:
        // the rank of the base has to be moving the color too.
        let over_busy = paint(&busy);
        let rows_agree = (0..8).all(|row| {
            let start = row * 8;
            over_busy[start..start + 8]
                .iter()
                .zip(&over_flat[start..start + 8])
                .all(|(a, b)| (a[0] - b[0]).abs() < 1e-9)
        });
        assert!(!rows_agree, "the base's own structure was overridden");
    }

    /// A modulate paints the set black wherever its base has nothing to say, even
    /// where the texture does. That is the one place it departs from a composite,
    /// and it is what keeps the interior black under `itinerary`.
    #[test]
    fn a_modulate_leaves_the_interior_black_even_where_the_texture_speaks() {
        let base = Field {
            values: vec![f32::NAN, f32::NAN, 1.0, 2.0],
            width: 4,
            height: 1,
        };
        let texture = field::Exact {
            values: vec![0.25, 0.75, 0.5, 0.9],
            width: 4,
            height: 1,
        };
        let colors = modulate(
            &base,
            &texture,
            Transform::Linear,
            Transform::Linear,
            0.5,
            &Palette::default(),
            &ramp(),
        );
        assert_eq!(colors[0], INTERIOR);
        assert_eq!(colors[1], INTERIOR, "the texture painted the interior");
        assert_ne!(colors[2], INTERIOR);
    }

    /// A shift of zero leaves the base alone, so the modulate degenerates to a
    /// rank-spent render of its base — the check that the perturbation is a
    /// perturbation rather than a replacement.
    #[test]
    fn a_modulate_with_no_shift_is_its_base_spent_by_rank() {
        let base = Field {
            values: (0..32).map(|i| (i * i) as f32).collect(),
            width: 32,
            height: 1,
        };
        let texture = field::Exact {
            values: (0..32).map(|i| i as f64).collect(),
            width: 32,
            height: 1,
        };
        let modulated = modulate(
            &base,
            &texture,
            Transform::Linear,
            Transform::Linear,
            0.0,
            &Palette::default(),
            &ramp(),
        );
        let ranked = shade(
            &base,
            Transform::Linear,
            &Palette {
                transfer: Transfer::Rank,
                ..Palette::default()
            },
            &ramp(),
        );
        for (a, b) in modulated.iter().zip(&ranked) {
            assert!((a[0] - b[0]).abs() < 1e-12, "{a:?} against {b:?}");
        }
    }

    /// A modulate spends its base by rank as part of what it is, so a recipe that
    /// asks for another transfer is refused rather than half-honoured.
    #[test]
    fn a_modulate_refuses_a_recipe_that_spends_its_base_another_way() {
        let coloring = Coloring::Modulate {
            base: Layer {
                field: FieldSpec::Smooth,
                transform: Transform::Linear,
            },
            texture: Layer {
                field: FieldSpec::Itinerary {
                    sectors: 4,
                    weight_base: Some(4.0),
                    depth: 26,
                },
                transform: Transform::Linear,
            },
            shift: 0.5,
        };
        coloring.agrees_with(&Palette::default()).unwrap();
        let message = coloring
            .agrees_with(&Palette {
                transfer: Transfer::Edge { weight: 0.25 },
                ..Palette::default()
            })
            .unwrap_err();
        assert!(message.contains("rank"), "{message}");
        // Every other coloring is free to be spent any way at all.
        Coloring::default()
            .agrees_with(&Palette {
                transfer: Transfer::Rank,
                ..Palette::default()
            })
            .unwrap();
    }

    /// Below the knee nothing moves at all, above it the shoulder approaches
    /// white without reaching it, and the two meet without a step.
    #[test]
    fn the_rolloff_bends_only_the_highlights() {
        let knee = 0.35;
        let soft = Rolloff::SoftKnee { knee };
        for step in 0..=35 {
            let value = step as f64 / 100.0;
            assert_eq!(soft.apply(value), value, "the shadows moved");
        }
        assert!(
            (soft.apply(knee) - knee).abs() < 1e-12,
            "there is a step at the knee"
        );
        for step in 36..=200 {
            let value = step as f64 / 100.0;
            let out = soft.apply(value);
            assert!(out < value, "a highlight was not compressed");
            assert!(out < 1.0, "the shoulder reached white");
        }
        assert!(
            soft.apply(4.0) > soft.apply(2.0),
            "the shoulder went backwards"
        );
    }

    /// Every rolloff is a monotone map of the non-negative reals into `[0, 1]` that
    /// fixes black, and none of them reaches white over the range a painted pixel
    /// actually takes. Monotone because a tone curve may not reorder two tones;
    /// fixing black because a curve that lifted the shadows off zero would put a fog
    /// over the set itself.
    #[test]
    fn every_rolloff_is_a_monotone_curve_that_fixes_black() {
        for rolloff in [
            Rolloff::None,
            Rolloff::SoftKnee { knee: 0.35 },
            Rolloff::Reinhard,
            Rolloff::Aces,
        ] {
            assert_eq!(rolloff.apply(0.0), 0.0, "{rolloff:?} lifted black");
            let mut previous = -1.0;
            for step in 0..=4000 {
                let value = step as f64 / 100.0;
                let out = rolloff.apply(value);
                assert!(out >= previous, "{rolloff:?} went backwards at {value}");
                previous = out;
            }
            // The identity is the one curve that is allowed to hand back whatever it
            // was given; every actual rolloff bounds its output, and none of them
            // reaches white over `[0, 1]` — the range a painted pixel, being a
            // colormap lookup, actually arrives in.
            if rolloff == Rolloff::None {
                continue;
            }
            for step in 0..=4000 {
                let out = rolloff.apply(step as f64 / 100.0);
                assert!((0.0..=1.0).contains(&out), "{rolloff:?} left the range");
            }
            assert!(rolloff.apply(1.0) < 1.0, "{rolloff:?} reached white at 1");
        }
    }

    /// The three curves are three different shapes, and each one's own doc claim is
    /// what separates it: the knee leaves the shadows exactly alone, Reinhard
    /// compresses from zero and only ever darkens, and ACES is the S — deep shadows
    /// down, midtones *up*, highlights compressed.
    #[test]
    fn the_three_rolloffs_are_three_shapes() {
        let knee = Rolloff::SoftKnee { knee: 0.35 };
        assert_eq!(knee.apply(0.1), 0.1, "the knee moved a shadow");

        assert_eq!(Rolloff::Reinhard.apply(1.0), 0.5);
        for step in 1..=200 {
            let value = step as f64 / 100.0;
            assert!(
                Rolloff::Reinhard.apply(value) < value,
                "reinhard failed to darken {value}"
            );
        }

        assert!(
            Rolloff::Aces.apply(0.01) < 0.01,
            "aces lifted a deep shadow"
        );
        assert!(
            Rolloff::Aces.apply(0.4) > 0.4,
            "aces failed to lift a midtone"
        );
        assert!((Rolloff::Aces.apply(1.0) - 0.804).abs() < 0.01);
        // Which is what makes it the one curve here that is not a compression: it
        // crosses the identity, and the other two never do.
        assert!(Rolloff::Aces.apply(0.4) > Rolloff::Reinhard.apply(0.4));
    }

    /// A rolled-off highlight keeps its hue: all three channels are rescaled by
    /// one ratio, which is the whole reason it works on luminance.
    #[test]
    fn a_rolled_off_highlight_keeps_its_hue() {
        let soft = Rolloff::SoftKnee { knee: 0.35 };
        let pixel = [0.9, 0.6, 0.3];
        let out = soft.shade(pixel);
        let ratio = out[0] / pixel[0];
        for channel in 0..3 {
            assert!(
                (out[channel] / pixel[channel] - ratio).abs() < 1e-12,
                "channel {channel} was scaled differently"
            );
        }
        assert!(ratio < 1.0, "the highlight was not pulled down");
        assert_eq!(Rolloff::None.shade(pixel), pixel);
        assert_eq!(soft.shade([0.0, 0.0, 0.0]), [0.0, 0.0, 0.0]);
    }
}
