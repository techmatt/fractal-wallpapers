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
        let mut valid: Vec<f64> = samples.filter(|v| v.is_finite()).map(|v| v as f64).collect();
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
    colormap: &Colormap,
) -> Result<Painted, String> {
    match coloring {
        Coloring::Field { field, transform } => {
            let sampled = field::render_field(view, family, maxiter, *field);
            Ok(Painted {
                linear: colorize(&sampled.fields[0], *transform, colormap),
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
        .paint(view, family, maxiter, colormap),
    }
}

/// Color one field into linear-light RGB, one entry per sample.
pub fn colorize(field: &Field, transform: Transform, colormap: &Colormap) -> Vec<[f64; 3]> {
    let stretch = Stretch::measure(field);
    field
        .values
        .par_iter()
        .map(|&value| {
            if value.is_finite() {
                colormap.lookup(transform.apply(stretch.position(value as f64)))
            } else {
                INTERIOR
            }
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
    colormap: &Colormap,
) -> Vec<[f64; 3]> {
    let base_stretch = Stretch::measure(base);
    let texture_stretch = Stretch::measure(texture);
    base.values
        .par_iter()
        .zip(&texture.values)
        .map(|(&base_value, &texture_value)| {
            let under = base_value
                .is_finite()
                .then(|| base_transform.apply(base_stretch.position(base_value as f64)));
            let over = texture_value
                .is_finite()
                .then(|| texture_transform.apply(texture_stretch.position(texture_value as f64)));
            let gray = match (under, over) {
                (None, None) => return INTERIOR,
                (Some(under), None) => under,
                (None, Some(over)) => over,
                (Some(under), Some(over)) => under + (blend.apply(under, over) - under) * weight,
            };
            colormap.lookup(gray)
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
}
