//! What an orbit is reduced to: one number per sample.
//!
//! A *field* is a scalar over the viewport, and the choice of which scalar is
//! the choice of what the picture is a picture of. The smooth iteration count
//! says how long the orbit survived. The strange fields say something else about
//! the same orbit — which angles it passed through, how close it came to a
//! circle or to the integer lattice, how sharply it turned — and because they
//! come off the same iteration, they cost a reduction rather than a re-render.
//!
//! Two properties every field here shares, and both are load-bearing:
//!
//! * **`NaN` means the sample has no value.** For the exterior-only fields that
//!   is the interior of the set; for a field that fills the interior it never
//!   happens. The mask rides inside the data rather than beside it, so a field
//!   is one array and cannot be separated from the information about which of
//!   its entries mean anything.
//! * **The value is raw.** No normalization, no curve, no color. That is what
//!   makes a dumped field worth keeping: everything downstream of it is cheap
//!   and reversible, and everything upstream is neither.

use std::num::NonZeroU32;

use rayon::prelude::*;
use serde::{Deserialize, Serialize};

use crate::family::Family;
use crate::iterate::{self, Lattice, Orbit, Wants};
use crate::viewport::Viewport;

/// Which scalar to reduce an orbit to, and the constants that shape it.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum FieldSpec {
    /// Fractional escape time. The spine: it is defined for every family, it
    /// varies smoothly everywhere outside the set, and every composite mode
    /// here uses it as the base the texture is laid over.
    Smooth,
    /// The integer step the orbit escaped on — the classic escape count, before
    /// anyone thought to make it fractional.
    ///
    /// A **teaching field**, and the one field here that is deliberately worse
    /// than its neighbour: it is the floor of [`Smooth`](FieldSpec::Smooth), so
    /// a render of it terraces into flat bands exactly where the smooth one runs
    /// continuously. That contrast is the whole of why the smooth count exists,
    /// and it is easier to show than to describe.
    ///
    /// `cycle` is the classic band mapping `palette[n mod N]`: the count wraps
    /// every `N` iterations, so the gradient repeats across the frame instead of
    /// being spent once over whatever range the frame happened to hold. Absent
    /// means no wrap. Exterior only, like the smooth count it shadows.
    ///
    /// It is not in the mode catalog and never will be — see [`crate::mode`].
    Discrete {
        #[serde(default)]
        cycle: Option<NonZeroU32>,
    },
    /// Mean of `½ + ½·sin(density · arg z)` over the orbit.
    ///
    /// The sine turns the angle each iterate arrived at into a stripe, and
    /// averaging over the orbit combs those stripes into the flowing striations
    /// that follow the escape flow rather than the escape time. Exterior only.
    Stripe {
        #[serde(default = "stripe_density")]
        density: f64,
    },
    /// Triangle-inequality average.
    ///
    /// The inequality bounds `|z² + c|` between `‖z²|−|c‖` and `|z²|+|c|`; this
    /// records where in that window the step actually landed, averaged over the
    /// orbit. It bands far more finely than the escape time does, which is what
    /// makes it read as engraving rather than as contours. Exterior only.
    Tia,
    /// Mean turning angle `|arg((zₙ−zₙ₋₁)/(zₙ₋₁−zₙ₋₂))|` over the orbit.
    ///
    /// How sharply the orbit cornered, on average. Exterior only.
    Curvature,
    /// Closest the orbit came to a circle of this radius: `min ‖z|−r‖`.
    ///
    /// An orbit trap — the field is a property of the whole orbit's *shape*
    /// rather than of its escape — and unlike the averaging fields it is defined
    /// for interior points too, because a bounded orbit still has a closest
    /// approach. That is what lets it fill the black lake a smooth render leaves.
    TrapCircle {
        #[serde(default = "trap_radius")]
        radius: f64,
    },
    /// Closest approach to the Gaussian integers — the points of the complex
    /// plane with whole real and imaginary parts — or an angle read off that
    /// approach. An orbit trap whose unit cell repeats across the whole plane,
    /// so it tiles rather than centering on anything. Defined everywhere.
    GaussianInt {
        #[serde(default)]
        reduce: Reduction,
    },
    /// `Σ exp(−|z|)` over the orbit.
    ///
    /// Every iterate contributes, weighted by how close to the origin it stayed,
    /// so the sum is dominated by the slow early part of the orbit and runs
    /// smoothly with escape time. Exterior only.
    ExpSmoothing,
}

/// Which statistic of the lattice trap becomes the field.
///
/// All three read the same accumulation, so they are free alternatives rather
/// than separate renders.
#[derive(Clone, Copy, Debug, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Reduction {
    /// The closest approach itself — the canonical, beaded look.
    #[default]
    MinimumDistance,
    /// The angle of the iterate at the closest approach.
    AngleMin,
    /// The angle of `(mean − nearest) + i(farthest − mean)`: how lopsided the
    /// orbit's spread of lattice distances was, read as a direction.
    MeanAngle,
}

fn stripe_density() -> f64 {
    6.0
}
fn trap_radius() -> f64 {
    1.0
}

impl FieldSpec {
    /// The name this field is written as.
    pub fn name(&self) -> &'static str {
        match self {
            FieldSpec::Smooth => "smooth",
            FieldSpec::Discrete { .. } => "discrete",
            FieldSpec::Stripe { .. } => "stripe",
            FieldSpec::Tia => "tia",
            FieldSpec::Curvature => "curvature",
            FieldSpec::TrapCircle { .. } => "trap_circle",
            FieldSpec::GaussianInt { .. } => "gaussian_int",
            FieldSpec::ExpSmoothing => "exp_smoothing",
        }
    }

    /// Which per-iteration channels this field reads.
    pub fn wants(&self) -> Wants {
        match *self {
            // Both read the escape itself, which the loop always records.
            FieldSpec::Smooth | FieldSpec::Discrete { .. } => Wants::default(),
            FieldSpec::Stripe { density } => Wants {
                stripe: Some(density),
                ..Wants::default()
            },
            FieldSpec::Tia => Wants {
                tia: true,
                ..Wants::default()
            },
            FieldSpec::Curvature => Wants {
                curvature: true,
                ..Wants::default()
            },
            FieldSpec::TrapCircle { radius } => Wants {
                trap_circle: Some(radius),
                ..Wants::default()
            },
            FieldSpec::GaussianInt { .. } => Wants {
                gaussian_int: true,
                ..Wants::default()
            },
            FieldSpec::ExpSmoothing => Wants {
                exp_smoothing: true,
                ..Wants::default()
            },
        }
    }

    /// Reduce one orbit to this field's scalar, or `None` where the field has
    /// nothing to say about that sample.
    pub fn reduce(&self, orbit: &Orbit) -> Option<f64> {
        let fade = orbit.fade();
        match *self {
            FieldSpec::Smooth => orbit.escaped.then_some(orbit.smooth),
            FieldSpec::Discrete { cycle } => orbit.escaped.then(|| match cycle {
                Some(length) => (orbit.iteration % length.get()) as f64,
                None => orbit.iteration as f64,
            }),
            FieldSpec::Stripe { .. } => orbit.escaped.then(|| orbit.stripe.deband(fade)).flatten(),
            FieldSpec::Tia => orbit.escaped.then(|| orbit.tia.deband(fade)).flatten(),
            FieldSpec::Curvature => orbit
                .escaped
                .then(|| orbit.curvature.deband(fade))
                .flatten(),
            FieldSpec::TrapCircle { .. } => {
                orbit.trap_circle.is_finite().then_some(orbit.trap_circle)
            }
            FieldSpec::GaussianInt { reduce } => reduce.of(&orbit.lattice),
            FieldSpec::ExpSmoothing => {
                let (sum, count) = orbit.exp_smoothing;
                (orbit.escaped && count > 0).then_some(sum)
            }
        }
    }

    /// Whether two fields can be gathered in a single pass.
    ///
    /// One orbit carries one stripe density and one trap radius, so a composite
    /// of two fields of the same kind would have to pick one of their constants
    /// and quietly render something other than what it was asked for.
    pub fn conflicts_with(&self, other: &FieldSpec) -> bool {
        self.name() == other.name()
    }
}

impl Reduction {
    fn of(self, lattice: &Lattice) -> Option<f64> {
        let mean = lattice.mean()?;
        Some(match self {
            Reduction::MinimumDistance => lattice.nearest,
            Reduction::AngleMin => turn(lattice.at_nearest),
            Reduction::MeanAngle => turn(num_complex::Complex::new(
                mean - lattice.nearest,
                lattice.farthest - mean,
            )),
        })
    }
}

/// A direction as a fraction of a full turn, in `[0, 1)`.
fn turn(w: num_complex::Complex<f64>) -> f64 {
    let half_turns = w.im.atan2(w.re) / std::f64::consts::PI; // [-1, 1]
    let positive = if half_turns < 0.0 {
        half_turns + 2.0
    } else {
        half_turns
    };
    (positive * 0.5).rem_euclid(1.0)
}

/// A scalar field at supersampled resolution, row-major.
pub struct Field {
    pub values: Vec<f32>,
    pub width: u32,
    pub height: u32,
}

/// Everything one pass over the viewport produced.
pub struct Sampled {
    /// One field per requested [`FieldSpec`], in the order they were asked for.
    pub fields: Vec<Field>,
    /// Share of samples whose orbit never escaped.
    ///
    /// A property of the iteration rather than of any field, so it means the
    /// same thing for a mode that fills the interior as for one that leaves it
    /// black — which is what makes it the one number worth putting in a render's
    /// record, and the first thing to look at when a frame comes out flat.
    pub interior_fraction: f64,
}

/// Iterate `family` over every sample of `view`, reducing each orbit to every
/// field in `fields`.
///
/// Rows run in parallel and are collected in order, so the result is identical
/// however the work was scheduled. Determinism here is not a nicety: a render
/// that depends on thread timing cannot be compared against anything, including
/// its own earlier self.
pub fn sample(view: &Viewport, family: &Family, maxiter: u32, fields: &[FieldSpec]) -> Sampled {
    let width = view.sample_width();
    let height = view.sample_height();
    let wants = fields
        .iter()
        .map(FieldSpec::wants)
        .fold(Wants::default(), Wants::union);

    // One row of every field at once, plus that row's interior count: the orbit
    // is expensive and is visited once.
    let rows: Vec<(Vec<Vec<f32>>, u32)> = (0..height)
        .into_par_iter()
        .map(|row| {
            let mut lanes = vec![Vec::with_capacity(width as usize); fields.len()];
            let mut interior = 0;
            for col in 0..width {
                let orbit = iterate::run(family, view.sample_point(col, row), maxiter, &wants);
                if !orbit.escaped {
                    interior += 1;
                }
                for (lane, field) in lanes.iter_mut().zip(fields) {
                    lane.push(field.reduce(&orbit).map_or(f32::NAN, |value| value as f32));
                }
            }
            (lanes, interior)
        })
        .collect();

    let samples = (width as u64 * height as u64).max(1);
    let interior: u64 = rows.iter().map(|(_, count)| *count as u64).sum();
    let mut values: Vec<Vec<f32>> = vec![Vec::with_capacity(samples as usize); fields.len()];
    for (lanes, _) in rows {
        for (all, row) in values.iter_mut().zip(lanes) {
            all.extend(row);
        }
    }

    Sampled {
        fields: values
            .into_iter()
            .map(|values| Field {
                values,
                width,
                height,
            })
            .collect(),
        interior_fraction: interior as f64 / samples as f64,
    }
}

/// Iterate `family` over `view`, reducing to a single field.
pub fn render_field(view: &Viewport, family: &Family, maxiter: u32, field: FieldSpec) -> Sampled {
    sample(view, family, maxiter, &[field])
}

#[cfg(test)]
mod tests {
    use super::*;
    use num_complex::Complex;

    fn whole_set_view(supersample: u32) -> Viewport {
        Viewport {
            center: Complex::new(-0.5, 0.0),
            width: 3.0,
            out_width: 32,
            out_height: 18,
            supersample,
        }
    }

    fn every_field() -> Vec<FieldSpec> {
        vec![
            FieldSpec::Smooth,
            FieldSpec::Discrete { cycle: None },
            FieldSpec::Stripe { density: 6.0 },
            FieldSpec::Tia,
            FieldSpec::Curvature,
            FieldSpec::TrapCircle { radius: 1.0 },
            FieldSpec::GaussianInt {
                reduce: Reduction::MinimumDistance,
            },
            FieldSpec::ExpSmoothing,
        ]
    }

    #[test]
    fn the_field_has_one_value_per_sample() {
        let view = whole_set_view(2);
        let sampled = render_field(
            &view,
            &Family::Multibrot { degree: 2 },
            200,
            FieldSpec::Smooth,
        );
        let field = &sampled.fields[0];
        assert_eq!(field.width, 64);
        assert_eq!(field.height, 36);
        assert_eq!(field.values.len(), 64 * 36);
    }

    #[test]
    fn a_view_of_the_whole_set_holds_both_interior_and_exterior() {
        let sampled = render_field(
            &whole_set_view(1),
            &Family::Multibrot { degree: 2 },
            400,
            FieldSpec::Smooth,
        );
        let interior = sampled.interior_fraction;
        assert!(
            interior > 0.05 && interior < 0.95,
            "interior fraction {interior}"
        );
    }

    /// Supersampling must subdivide the same rectangle, not shift it: the
    /// interior fraction is a coarse but honest witness that it does.
    #[test]
    fn supersampling_does_not_move_the_view() {
        let family = Family::Multibrot { degree: 2 };
        let coarse =
            render_field(&whole_set_view(1), &family, 400, FieldSpec::Smooth).interior_fraction;
        let fine =
            render_field(&whole_set_view(4), &family, 400, FieldSpec::Smooth).interior_fraction;
        assert!((coarse - fine).abs() < 0.02, "{coarse} vs {fine}");
    }

    /// The interior fraction is a property of the iteration, so it must not
    /// depend on which field was asked for — including the fields that have a
    /// value everywhere and leave no `NaN` behind to count.
    #[test]
    fn the_interior_fraction_is_the_same_whichever_field_is_read() {
        let family = Family::Multibrot { degree: 2 };
        let view = whole_set_view(1);
        let together = sample(&view, &family, 400, &every_field());
        for field in every_field() {
            let alone = render_field(&view, &family, 400, field);
            assert!(
                (alone.interior_fraction - together.interior_fraction).abs() < 1e-12,
                "{field:?}"
            );
        }
    }

    /// Reducing many fields in one pass must give exactly what reducing them one
    /// at a time gives — otherwise the composite path is rendering a different
    /// picture from the one its two halves describe.
    #[test]
    fn one_pass_over_many_fields_matches_a_pass_each() {
        let family = Family::Julia {
            degree: 2,
            c: Complex::new(-0.4, 0.6),
        };
        let view = whole_set_view(1);
        let fields = every_field();
        let together = sample(&view, &family, 300, &fields);
        for (index, field) in fields.iter().enumerate() {
            let alone = render_field(&view, &family, 300, *field);
            let a = &alone.fields[0].values;
            let b = &together.fields[index].values;
            assert_eq!(a.len(), b.len());
            for (i, (x, y)) in a.iter().zip(b).enumerate() {
                assert_eq!(x.to_bits(), y.to_bits(), "{field:?} at sample {i}");
            }
        }
    }

    /// Which fields fill the interior and which leave it empty is a fact about
    /// each field's definition, and the whole reason the composite modes exist:
    /// a trap field has something to say exactly where the smooth field does not.
    #[test]
    fn the_exterior_only_fields_are_the_ones_that_read_an_escape() {
        let family = Family::Multibrot { degree: 2 };
        let view = whole_set_view(1);
        let sampled = sample(&view, &family, 400, &every_field());
        let interior = (sampled.interior_fraction * sampled.fields[0].values.len() as f64) as usize;
        assert!(interior > 0);

        // The two orbit traps, which have a closest approach to report whether
        // or not the orbit ever left. Everything else reads an escape.
        let fills_the_interior = [
            FieldSpec::TrapCircle { radius: 1.0 },
            FieldSpec::GaussianInt {
                reduce: Reduction::MinimumDistance,
            },
        ];
        for (spec, field) in every_field().iter().zip(&sampled.fields) {
            let empty = field.values.iter().filter(|v| !v.is_finite()).count();
            let expected = if fills_the_interior.contains(spec) {
                0
            } else {
                interior
            };
            assert_eq!(empty, expected, "{spec:?}");
        }
    }

    /// The discrete field is the step the smooth one sits in, sample for sample.
    /// That is what the article's smooth-versus-discrete figure is a picture of,
    /// and it is the reason the pair is worth rendering at one location.
    ///
    /// Compared with a tolerance because a field is `f32`: the exact claim —
    /// `floor(smooth) == iteration` — is `f64` arithmetic and is pinned where
    /// that arithmetic happens, in [`crate::iterate`]. Here a smooth count a
    /// thousandth below a whole number can have rounded up on the way into the
    /// array, and that is a fact about storage rather than about the fields.
    #[test]
    fn the_discrete_field_is_the_step_the_smooth_one_sits_in() {
        let view = whole_set_view(1);
        let family = Family::Multibrot { degree: 2 };
        let sampled = sample(
            &view,
            &family,
            400,
            &[FieldSpec::Smooth, FieldSpec::Discrete { cycle: None }],
        );
        let mut bands = std::collections::BTreeSet::new();
        for (smooth, discrete) in sampled.fields[0]
            .values
            .iter()
            .zip(&sampled.fields[1].values)
        {
            if smooth.is_nan() {
                assert!(discrete.is_nan(), "the two disagree about the interior");
                continue;
            }
            let into_the_step = smooth - discrete;
            assert!(
                (-1e-3..1.0).contains(&into_the_step),
                "smooth {smooth} is not inside step {discrete}"
            );
            assert_eq!(*discrete, discrete.trunc(), "a step that is not whole");
            bands.insert(*discrete as u32);
        }
        assert!(bands.len() > 4, "a frame with no bands proves nothing");
    }

    /// A cycle is the classic `palette[n mod N]`: the count wraps, so the field
    /// cannot leave `[0, N)` however deep the frame's escape counts run.
    #[test]
    fn a_cycle_wraps_the_count_it_reads() {
        let length = 8;
        let cycled = FieldSpec::Discrete {
            cycle: Some(NonZeroU32::new(length).unwrap()),
        };
        let sampled = sample(
            &whole_set_view(1),
            &Family::Multibrot { degree: 2 },
            400,
            &[FieldSpec::Discrete { cycle: None }, cycled],
        );
        let mut wrapped = false;
        for (plain, banded) in sampled.fields[0]
            .values
            .iter()
            .zip(&sampled.fields[1].values)
        {
            if plain.is_nan() {
                continue;
            }
            assert_eq!(*banded, (*plain as u32 % length) as f32);
            wrapped |= *plain >= length as f32;
        }
        assert!(
            wrapped,
            "no sample ran past the cycle, so nothing was wrapped"
        );
    }

    #[test]
    fn a_field_names_itself_and_two_of_a_kind_conflict() {
        assert_eq!(FieldSpec::Stripe { density: 6.0 }.name(), "stripe");
        assert!(
            FieldSpec::Stripe { density: 6.0 }.conflicts_with(&FieldSpec::Stripe { density: 3.0 })
        );
        assert!(!FieldSpec::Smooth.conflicts_with(&FieldSpec::Tia));
    }

    /// The angle reductions are fractions of a turn, so they must land in
    /// `[0, 1)` from every quadrant — including the negative-imaginary half,
    /// where an unshifted `atan2` would come back negative and read as black.
    #[test]
    fn an_angle_is_a_fraction_of_a_turn() {
        for step in 0..64 {
            let angle = -std::f64::consts::PI + std::f64::consts::TAU * step as f64 / 64.0;
            let value = turn(Complex::from_polar(1.0, angle));
            assert!((0.0..1.0).contains(&value), "{angle} gave {value}");
        }
        assert!(turn(Complex::new(1.0, 0.0)).abs() < 1e-12);
        assert!((turn(Complex::new(-1.0, 0.0)) - 0.5).abs() < 1e-12);
        // Below the real axis the raw angle is negative; the fold is what stops
        // a whole half-plane from reading as the bottom of the gradient.
        assert!((turn(Complex::new(0.0, -1.0)) - 0.75).abs() < 1e-12);
    }

    /// A spec round-trips through JSON: the record of a render has to be able to
    /// re-render it.
    #[test]
    fn a_field_spec_round_trips_through_json() {
        for field in every_field() {
            let text = serde_json::to_string(&field).unwrap();
            let back: FieldSpec = serde_json::from_str(&text).unwrap();
            assert_eq!(field, back, "{text}");
        }
        let defaulted: FieldSpec = serde_json::from_str(r#"{"kind":"stripe"}"#).unwrap();
        assert_eq!(defaulted, FieldSpec::Stripe { density: 6.0 });

        let banded: FieldSpec = serde_json::from_str(r#"{"kind":"discrete","cycle":24}"#).unwrap();
        assert_eq!(
            banded,
            FieldSpec::Discrete {
                cycle: NonZeroU32::new(24)
            }
        );
        // A cycle of zero is not a band mapping, and the type refuses it at the
        // door rather than leaving a modulo-by-zero for the reduction to meet.
        assert!(serde_json::from_str::<FieldSpec>(r#"{"kind":"discrete","cycle":0}"#).is_err());
    }
}
