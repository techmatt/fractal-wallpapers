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
use crate::iterate::{self, Lattice, Orbit, Symbols, Wants};
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
    /// Closest the orbit came to the axis cross through the origin:
    /// `min min(|Re z|, |Im z|)` — the Pickover stalk.
    ///
    /// The circle trap's sparse twin. A circle is a closed curve and a cross is
    /// two lines through the origin, so this trap is *non-periodic and unbounded*:
    /// there is no repeating unit cell the way the lattice trap has one, and no
    /// centre the way the circle has one. The texture that comes out reads as
    /// organic flow rather than as a grid, and like the other traps it is defined
    /// in the interior too.
    TrapCross,
    /// Mean of `exp(−D²/σ²)` over the orbit, `D` the cross-trap distance.
    ///
    /// The accumulating cross. [`TrapCross`](FieldSpec::TrapCross) keeps the
    /// single closest pass and throws the rest of the orbit away; this weighs
    /// *every* pass by how close it came and averages them, so a pixel whose orbit
    /// grazed the cross a dozen times reads differently from one that grazed it
    /// once. `sigma` is the width of the kernel and is a live parameter rather
    /// than a curve in disguise: it sits **inside** the average, and no monotone
    /// curve applied to `mean(D)` reproduces `mean(exp(−D²/σ²))`.
    ///
    /// Exterior only, like the other averaging fields — which is also what keeps
    /// the interior black under the composite this field was found for.
    Threads {
        #[serde(default = "threads_sigma")]
        sigma: f64,
    },
    /// Mean step length `|zₙ − zₙ₋₁|` over the orbit.
    ///
    /// How fast the orbit was moving, on average, rather than where it went. It is
    /// defined for a bounded orbit too — a periodic cycle has a perfectly good mean
    /// step — so it fills the interior, and inside the set it separates the
    /// components by the size of the cycle they fall into.
    Velocity,
    /// The angle of the iterate the orbit escaped on, as a fraction of a turn.
    ///
    /// The classic decomposition: which way the orbit was pointing when it left.
    /// The exterior of the set is tiled by the escape count into rings, and this
    /// cuts each ring the other way, into the cells that lead to each other by one
    /// step of the recurrence. Exterior only — an orbit that never left has no
    /// escape angle.
    Decomposition,
    /// The exterior distance estimate, `2·|z|·ln|z|/|dz|`, scaled.
    ///
    /// The one field here that is a **length in the plane** rather than a
    /// statistic of the orbit: it estimates how far the sample is from the set
    /// itself. That makes it the field whose contours are the set's own offset
    /// curves, and the reason it looks so unlike an escape count at the same
    /// place — the escape count crowds every contour against the boundary, and
    /// this one spaces them evenly out from it.
    ///
    /// It is the only field that needs the derivative recurrence, which costs a
    /// complex multiply per iteration, so it is also the most expensive.
    ///
    /// `scale` multiplies the estimate. It cannot change the picture — the
    /// per-frame stretch divides it straight back out — and is here because the
    /// estimate is a physical length that a reader of a dumped field may want in
    /// the units of their own choosing.
    ///
    /// **No lighting.** A distance estimate is often the input to a normal-map
    /// shading pass; that pass is deliberately not in this engine. See
    /// [`crate::mode`].
    De {
        #[serde(default = "de_scale")]
        scale: f64,
    },
    /// The orbit's symbolic address: which angular sector each step landed in,
    /// read as the digits of one fractional number.
    ///
    /// See [`crate::iterate::Address`] for the accumulation and for why the
    /// address must not travel through an `f32`. Defined everywhere: `z₀` alone
    /// spells a first symbol, so even a point that never moves has an address.
    Itinerary {
        #[serde(default = "itinerary_sectors")]
        sectors: u32,
        /// The base the symbols are written in. Absent means `= sectors`, a clean
        /// base-`k` expansion — the sensible default, and the reason this is an
        /// option rather than a number: a default written as a constant could not
        /// follow `sectors` when a caller moved it.
        #[serde(default)]
        weight_base: Option<f64>,
        #[serde(default = "itinerary_depth")]
        depth: u32,
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
/// All nine read the same accumulation, so they are free alternatives rather than
/// separate renders: one pass over the orbit records the closest and farthest
/// approach, where and when each happened, and the running mean, and each of
/// these is a different question asked of that one record.
#[derive(Clone, Copy, Debug, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Reduction {
    /// The closest approach itself — the canonical, beaded look.
    #[default]
    MinimumDistance,
    /// The mean distance to the lattice over the whole orbit. Smoother than the
    /// minimum, because every step contributes instead of only the best one.
    AverageDistance,
    /// The farthest the orbit ever got from every lattice point. Bounded above by
    /// half the unit cell's diagonal, so this is the one reduction here whose
    /// range is the same at every location.
    MaximumDistance,
    /// The step the closest approach happened on — *when*, not *how close*.
    IterMin,
    /// The step the farthest approach happened on.
    IterMax,
    /// The angle of the iterate at the closest approach.
    AngleMin,
    /// The angle of the iterate at the farthest approach.
    AngleMax,
    /// The angle of `(mean − nearest) + i(farthest − mean)`: how lopsided the
    /// orbit's spread of lattice distances was, read as a direction.
    MeanAngle,
    /// `nearest / farthest` — how tightly the orbit's approaches bunched, as a
    /// number in `[0, 1]` that is scale-free by construction.
    Ratio,
}

fn stripe_density() -> f64 {
    6.0
}
fn trap_radius() -> f64 {
    1.0
}
/// The kernel width Matt kept: sharp enough to read as threads rather than haze.
fn threads_sigma() -> f64 {
    0.15
}
fn de_scale() -> f64 {
    1.0
}
fn itinerary_sectors() -> u32 {
    4
}
/// Symbols the address holds by default.
///
/// **26, which is the `f64` ceiling at the default four sectors** — 53 mantissa
/// bits over 2 bits per base-4 symbol — and not a taste call. Past it the deep
/// digits are rounding noise, and rounding noise in an address does not look like
/// noise: it collapses whole subtrees of the lamination onto one value and reads
/// as banding. A caller raising `sectors` has to lower this in step (17 at 8, 13
/// at 16); nothing here does it on their behalf, because the number of symbols is
/// what the field *is*.
fn itinerary_depth() -> u32 {
    26
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
            FieldSpec::TrapCross => "trap_cross",
            FieldSpec::Threads { .. } => "threads",
            FieldSpec::GaussianInt { .. } => "gaussian_int",
            FieldSpec::ExpSmoothing => "exp_smoothing",
            FieldSpec::Velocity => "velocity",
            FieldSpec::Decomposition => "decomposition",
            FieldSpec::De { .. } => "de",
            FieldSpec::Itinerary { .. } => "itinerary",
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
            FieldSpec::TrapCross => Wants {
                trap_cross: true,
                ..Wants::default()
            },
            FieldSpec::Threads { sigma } => Wants {
                threads: Some(sigma),
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
            FieldSpec::Velocity => Wants {
                velocity: true,
                ..Wants::default()
            },
            // The escape angle reads the last iterate, which the loop keeps
            // whether or not anyone asked.
            FieldSpec::Decomposition => Wants::default(),
            FieldSpec::De { .. } => Wants {
                derivative: true,
                ..Wants::default()
            },
            FieldSpec::Itinerary {
                sectors,
                weight_base,
                depth,
            } => Wants {
                itinerary: Some(Symbols {
                    sectors,
                    base: weight_base.unwrap_or(sectors as f64),
                    depth,
                }),
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
            FieldSpec::TrapCross => orbit.trap_cross.is_finite().then_some(orbit.trap_cross),
            FieldSpec::Threads { .. } => {
                orbit.escaped.then(|| orbit.threads.deband(fade)).flatten()
            }
            FieldSpec::GaussianInt { reduce } => reduce.of(&orbit.lattice),
            FieldSpec::ExpSmoothing => {
                let (sum, count) = orbit.exp_smoothing;
                (orbit.escaped && count > 0).then_some(sum)
            }
            FieldSpec::Velocity => orbit.velocity.deband(fade),
            FieldSpec::Decomposition => orbit.escaped.then(|| turn(orbit.last)),
            FieldSpec::De { scale } => orbit.distance_estimate().map(|estimate| scale * estimate),
            FieldSpec::Itinerary { .. } => orbit.itinerary.value(),
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
            Reduction::AverageDistance => mean,
            Reduction::MaximumDistance => lattice.farthest,
            Reduction::IterMin => lattice.step_nearest as f64,
            Reduction::IterMax => lattice.step_farthest as f64,
            Reduction::AngleMin => turn(lattice.at_nearest),
            Reduction::AngleMax => turn(lattice.at_farthest),
            Reduction::MeanAngle => turn(num_complex::Complex::new(
                mean - lattice.nearest,
                lattice.farthest - mean,
            )),
            // An orbit that never left a lattice point has no bunching to
            // measure; zero is the tightest ratio there is, which is what that
            // degenerate case means.
            Reduction::Ratio => {
                if lattice.farthest > 0.0 {
                    lattice.nearest / lattice.farthest
                } else {
                    0.0
                }
            }
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

/// The same field before it was narrowed to `f32`.
///
/// Every field here is *reduced* at `f64` and then stored at `f32`, because that
/// is what a dump is worth keeping as: half the bytes, and 24 bits of mantissa is
/// more than any escape count or trap distance carries. One field breaks that
/// bargain — [`FieldSpec::Itinerary`], whose value is a base-`k` expansion whose
/// deep digits *are* the picture — so the coloring that reads it takes this
/// instead and never touches the narrow form.
pub struct Exact {
    pub values: Vec<f64>,
    pub width: u32,
    pub height: u32,
}

impl Exact {
    /// The `f32` field this would have been stored as.
    pub fn narrow(&self) -> Field {
        Field {
            values: self.values.iter().map(|&value| value as f32).collect(),
            width: self.width,
            height: self.height,
        }
    }
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
    let (lanes, interior_fraction) = gather(view, family, maxiter, fields, |value| {
        value.map_or(f32::NAN, |value| value as f32)
    });
    Sampled {
        fields: lanes
            .into_iter()
            .map(|values| Field {
                values,
                width: view.sample_width(),
                height: view.sample_height(),
            })
            .collect(),
        interior_fraction,
    }
}

/// The same pass, keeping every field at the precision it was reduced at.
///
/// Costs twice the memory of [`sample`] and is worth it for exactly one field —
/// see [`Exact`]. Everything else about the pass is identical, which is the point:
/// the narrow and the exact form of a field differ only in the last conversion, so
/// there is no second sampler to keep in agreement with the first.
pub fn sample_exact(
    view: &Viewport,
    family: &Family,
    maxiter: u32,
    fields: &[FieldSpec],
) -> (Vec<Exact>, f64) {
    let (lanes, interior_fraction) = gather(view, family, maxiter, fields, |value| {
        value.unwrap_or(f64::NAN)
    });
    (
        lanes
            .into_iter()
            .map(|values| Exact {
                values,
                width: view.sample_width(),
                height: view.sample_height(),
            })
            .collect(),
        interior_fraction,
    )
}

/// One pass over the viewport, one lane per field, each value kept as `keep` says.
fn gather<T: Copy + Send>(
    view: &Viewport,
    family: &Family,
    maxiter: u32,
    fields: &[FieldSpec],
    keep: fn(Option<f64>) -> T,
) -> (Vec<Vec<T>>, f64) {
    let width = view.sample_width();
    let height = view.sample_height();
    let wants = fields
        .iter()
        .map(FieldSpec::wants)
        .fold(Wants::default(), Wants::union);

    // One row of every field at once, plus that row's interior count: the orbit
    // is expensive and is visited once.
    let rows: Vec<(Vec<Vec<T>>, u32)> = (0..height)
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
                    lane.push(keep(field.reduce(&orbit)));
                }
            }
            (lanes, interior)
        })
        .collect();

    let samples = (width as u64 * height as u64).max(1);
    let interior: u64 = rows.iter().map(|(_, count)| *count as u64).sum();
    let mut values: Vec<Vec<T>> = vec![Vec::with_capacity(samples as usize); fields.len()];
    for (lanes, _) in rows {
        for (all, row) in values.iter_mut().zip(lanes) {
            all.extend(row);
        }
    }
    (values, interior as f64 / samples as f64)
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

    /// Every reduction of the lattice trap, so a test that walks the fields walks
    /// all nine rather than the one that happens to be the default.
    const EVERY_REDUCTION: [Reduction; 9] = [
        Reduction::MinimumDistance,
        Reduction::AverageDistance,
        Reduction::MaximumDistance,
        Reduction::IterMin,
        Reduction::IterMax,
        Reduction::AngleMin,
        Reduction::AngleMax,
        Reduction::MeanAngle,
        Reduction::Ratio,
    ];

    fn every_field() -> Vec<FieldSpec> {
        vec![
            FieldSpec::Smooth,
            FieldSpec::Discrete { cycle: None },
            FieldSpec::Stripe { density: 6.0 },
            FieldSpec::Tia,
            FieldSpec::Curvature,
            FieldSpec::TrapCircle { radius: 1.0 },
            FieldSpec::TrapCross,
            FieldSpec::Threads { sigma: 0.15 },
            FieldSpec::GaussianInt {
                reduce: Reduction::MinimumDistance,
            },
            FieldSpec::ExpSmoothing,
            FieldSpec::Velocity,
            FieldSpec::Decomposition,
            FieldSpec::De { scale: 1.0 },
            FieldSpec::Itinerary {
                sectors: 4,
                weight_base: None,
                depth: 26,
            },
        ]
    }

    /// The fields that have a value for a bounded orbit too. Two orbit traps —
    /// which have a closest approach whether or not the orbit left — plus the mean
    /// step length and the address, both of which a periodic cycle has as much as
    /// an escaping orbit does. Everything else reads an escape.
    fn fills_the_interior() -> Vec<FieldSpec> {
        vec![
            FieldSpec::TrapCircle { radius: 1.0 },
            FieldSpec::TrapCross,
            FieldSpec::GaussianInt {
                reduce: Reduction::MinimumDistance,
            },
            FieldSpec::Velocity,
            FieldSpec::Itinerary {
                sectors: 4,
                weight_base: None,
                depth: 26,
            },
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

        let filling = fills_the_interior();
        for (spec, field) in every_field().iter().zip(&sampled.fields) {
            let empty = field.values.iter().filter(|v| !v.is_finite()).count();
            if filling.contains(spec) {
                assert_eq!(empty, 0, "{spec:?} left the interior empty");
            } else {
                // An exterior-only field is empty exactly on the interior — except
                // the distance estimate, which also declines a vanishing
                // derivative, so it is held to "at least the interior" instead.
                let floor = matches!(spec, FieldSpec::De { .. });
                assert!(
                    if floor {
                        empty >= interior
                    } else {
                        empty == interior
                    },
                    "{spec:?}: {empty} empty samples against {interior} interior"
                );
            }
        }
    }

    /// Every reduction of the lattice trap must produce a live field, and the two
    /// that are angles must be fractions of a turn. Nine free alternatives are only
    /// worth having if each one says something.
    #[test]
    fn every_lattice_reduction_reads_the_same_pass_and_says_something() {
        let view = whole_set_view(1);
        let family = Family::Multibrot { degree: 2 };
        let fields: Vec<FieldSpec> = EVERY_REDUCTION
            .iter()
            .map(|&reduce| FieldSpec::GaussianInt { reduce })
            .collect();
        let sampled = sample(&view, &family, 400, &fields);
        for (reduce, field) in EVERY_REDUCTION.iter().zip(&sampled.fields) {
            let mut distinct = std::collections::BTreeSet::new();
            for value in &field.values {
                assert!(value.is_finite(), "{reduce:?} left a sample empty");
                distinct.insert(value.to_bits());
            }
            assert!(distinct.len() > 4, "{reduce:?} is nearly one flat value");
            if matches!(reduce, Reduction::AngleMin | Reduction::AngleMax) {
                for value in &field.values {
                    assert!((0.0..1.0).contains(value), "{reduce:?} gave {value}");
                }
            }
            if matches!(reduce, Reduction::Ratio) {
                for value in &field.values {
                    assert!((0.0..=1.0).contains(value), "ratio gave {value}");
                }
            }
        }
    }

    /// The distance estimate is a length in the plane, so scaling it must not move
    /// the picture: the per-frame stretch divides the scale straight back out. That
    /// is the whole reason `scale` is allowed to exist as a knob on a field.
    #[test]
    fn scaling_the_distance_estimate_does_not_change_where_it_lands() {
        use crate::coloring::Stretch;
        let view = whole_set_view(1);
        let family = Family::Multibrot { degree: 2 };
        let plain = render_field(&view, &family, 400, FieldSpec::De { scale: 1.0 });
        let scaled = render_field(&view, &family, 400, FieldSpec::De { scale: 1000.0 });
        let (a, b) = (
            Stretch::measure(&plain.fields[0]),
            Stretch::measure(&scaled.fields[0]),
        );
        let mut compared = 0;
        for (one, many) in plain.fields[0].values.iter().zip(&scaled.fields[0].values) {
            if !one.is_finite() {
                continue;
            }
            compared += 1;
            assert!(
                (a.position(*one as f64) - b.position(*many as f64)).abs() < 1e-4,
                "the scale moved a sample from {one} to {many}"
            );
        }
        assert!(compared > 100, "nothing was compared");
    }

    /// The address must spell its most significant digit from `z₀`. On the
    /// dynamical plane `z₀` is the pixel, so the first symbol is a fact about the
    /// pixel alone: sample four points, one per quadrant sector, and the addresses
    /// must land in four different quarters of `[0, 1)`.
    #[test]
    fn the_address_opens_on_the_starting_point_s_own_sector() {
        let family = Family::Julia {
            degree: 2,
            c: Complex::new(-0.4, 0.6),
        };
        let spec = FieldSpec::Itinerary {
            sectors: 4,
            weight_base: Some(4.0),
            depth: 26,
        };
        let mut quarters = std::collections::BTreeSet::new();
        for &(re, im) in &[(0.9, 0.1), (-0.1, 0.9), (-0.9, -0.1), (0.1, -0.9)] {
            let orbit = iterate::run(&family, Complex::new(re, im), 200, &spec.wants());
            let address = spec.reduce(&orbit).expect("the address is always defined");
            assert!((0.0..1.0).contains(&address), "address {address}");
            quarters.insert((address * 4.0).floor() as u32);
        }
        assert_eq!(quarters.len(), 4, "z₀ did not decide the leading symbol");
    }

    /// An address is `depth` symbols and no more: past the ceiling the digits are
    /// rounding noise, so the accumulation has to actually stop.
    #[test]
    fn the_address_stops_at_its_depth() {
        let family = Family::Julia {
            degree: 2,
            c: Complex::new(-0.4, 0.6),
        };
        let deep = FieldSpec::Itinerary {
            sectors: 4,
            weight_base: Some(4.0),
            depth: 26,
        };
        let shallow = FieldSpec::Itinerary {
            sectors: 4,
            weight_base: Some(4.0),
            depth: 2,
        };
        let point = Complex::new(0.31, 0.22);
        let deep_orbit = iterate::run(&family, point, 500, &deep.wants());
        let shallow_orbit = iterate::run(&family, point, 500, &shallow.wants());
        assert_eq!(shallow_orbit.itinerary.symbols(), 2);
        assert!(deep_orbit.itinerary.symbols() <= 26);
        // The shallow address is the deep one's leading two digits, so the two
        // agree to within the weight of the third.
        let (a, b) = (
            deep.reduce(&deep_orbit).unwrap(),
            shallow.reduce(&shallow_orbit).unwrap(),
        );
        assert!((a - b).abs() < 1.0 / 16.0, "{a} against {b}");
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

        // The kept parameters are the defaults, so the two experimental fields can
        // be asked for by name alone.
        let threads: FieldSpec = serde_json::from_str(r#"{"kind":"threads"}"#).unwrap();
        assert_eq!(threads, FieldSpec::Threads { sigma: 0.15 });
        let address: FieldSpec = serde_json::from_str(r#"{"kind":"itinerary"}"#).unwrap();
        assert_eq!(
            address,
            FieldSpec::Itinerary {
                sectors: 4,
                weight_base: None,
                depth: 26,
            }
        );
    }

    /// An absent `weight_base` means "= sectors", and it has to follow `sectors`
    /// rather than being pinned to the default four — that is the whole reason it
    /// is an option instead of a number with a default.
    #[test]
    fn an_absent_weight_base_follows_the_sector_count() {
        let follows = FieldSpec::Itinerary {
            sectors: 8,
            weight_base: None,
            depth: 17,
        };
        let stated = FieldSpec::Itinerary {
            sectors: 8,
            weight_base: Some(8.0),
            depth: 17,
        };
        assert_eq!(follows.wants(), stated.wants());
        let differing = FieldSpec::Itinerary {
            sectors: 8,
            weight_base: Some(2.0),
            depth: 17,
        };
        assert_ne!(follows.wants(), differing.wants());
    }
}
