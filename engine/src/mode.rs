//! The named modes: the colorings that were worth keeping.
//!
//! A [`Coloring`](crate::coloring::Coloring) is a wide space — any field through
//! any curve, any pair of fields through any blend, any trap shape at any
//! threshold — and almost all of it is bad. What is here is the part that
//! survived being looked at: sixteen settled points in that space, each with a
//! name, so a render can ask for a look rather than for a parameter vector.
//!
//! They come in three shapes, and the shape decides what can be done with the
//! result:
//!
//! * **One field** — `smooth` and the six strange fields beside it. These map a
//!   scalar through the colormap, so they can be dumped and recolored.
//! * **Composites** — a smooth base with a strange field screened over it. The
//!   base carries the shape of the escape and the texture writes structure into
//!   it, including into the interior, where the smooth field has nothing to say.
//! * **Direct traps** — the color-valued family, which paints during the
//!   iteration and never makes a field at all.
//!
//! Anything not in this list is still reachable by writing the coloring out in
//! full. A name is a claim that a setting is worth returning to, and that claim
//! is what this list is for.

use crate::coloring::{Blend, Coloring, Layer, Transform};
use crate::direct_trap::Shape;
use crate::field::{FieldSpec, Reduction};

/// Every named mode, with the line that says what it is for.
pub const CATALOG: [(&str, &str); 16] = [
    (
        "smooth",
        "Fractional escape time: the spine every composite builds on.",
    ),
    ("tia", "Triangle-inequality average: fine engraved banding."),
    (
        "stripe",
        "Stripe average at density 6: combed flowing striations.",
    ),
    (
        "exp_smoothing",
        "Sum of exp(-|z|) over the orbit: an averaging alternative to smooth.",
    ),
    (
        "gaussian_int",
        "Closest approach to the integer lattice: a tiled, beaded field.",
    ),
    (
        "trap_circle",
        "Closest approach to the unit circle, read through a log curve.",
    ),
    ("curvature", "Mean turning angle of the orbit."),
    (
        "smooth_mean_angle",
        "Smooth base, screened with the lattice trap's spread angle.",
    ),
    (
        "smooth_angle_min",
        "Smooth base, screened with the angle at the lattice's closest approach.",
    ),
    (
        "smooth_trap_circle",
        "Smooth base, screened with the circle trap: structure in the interior.",
    ),
    (
        "smooth_stripe",
        "Smooth base, screened with the stripe average.",
    ),
    ("smooth_curvature", "Smooth base, screened with curvature."),
    (
        "direct_trap_ring",
        "Direct trap, ring shape, screened over black: the cleanest of the family.",
    ),
    (
        "direct_trap_screen",
        "Direct trap, cross shape, screened over black: bright thorns.",
    ),
    (
        "direct_trap_multiply",
        "Direct trap, cross shape, multiplied over white: dark lace on light.",
    ),
    (
        "direct_trap_lines",
        "Direct trap on the real axis: the narrowest, most directional member.",
    ),
];

/// The weight the composite modes give their texture.
///
/// Not 1: at full strength the texture's own normalization competes with the
/// base's and the escape structure stops being legible underneath it. This is
/// the settled value for all five.
const TEXTURE_WEIGHT: f64 = 0.85;

/// Look a mode up by name.
pub fn resolve(name: &str) -> Result<Coloring, String> {
    let field = |field, transform| Coloring::Field { field, transform };
    let over_smooth = |field| Coloring::Composite {
        base: Layer {
            field: FieldSpec::Smooth,
            transform: Transform::Linear,
        },
        texture: Layer {
            field,
            transform: Transform::Linear,
        },
        blend: Blend::Screen,
        texture_weight: TEXTURE_WEIGHT,
    };
    let direct = |shape, threshold, opacity, merge, start_color: &str| Coloring::Direct {
        shape,
        trap_radius: 1.0,
        threshold: Some(threshold),
        opacity,
        merge,
        start_color: start_color.to_string(),
    };

    Ok(match name {
        // --- one field ---
        "smooth" => field(FieldSpec::Smooth, Transform::Linear),
        "tia" => field(FieldSpec::Tia, Transform::Linear),
        "stripe" => field(FieldSpec::Stripe { density: 6.0 }, Transform::Linear),
        "exp_smoothing" => field(FieldSpec::ExpSmoothing, Transform::Linear),
        "gaussian_int" => field(
            FieldSpec::GaussianInt {
                reduce: Reduction::MinimumDistance,
            },
            Transform::Linear,
        ),
        // The one mode that is not linear: a circle trap's values pile up near
        // zero, and a log curve is what spreads that pile back across the
        // gradient instead of leaving the frame one flat color.
        "trap_circle" => field(FieldSpec::TrapCircle { radius: 1.0 }, Transform::Log),
        "curvature" => field(FieldSpec::Curvature, Transform::Linear),

        // --- composites: a strange field screened over the smooth base ---
        "smooth_mean_angle" => over_smooth(FieldSpec::GaussianInt {
            reduce: Reduction::MeanAngle,
        }),
        "smooth_angle_min" => over_smooth(FieldSpec::GaussianInt {
            reduce: Reduction::AngleMin,
        }),
        "smooth_trap_circle" => over_smooth(FieldSpec::TrapCircle { radius: 1.0 }),
        "smooth_stripe" => over_smooth(FieldSpec::Stripe { density: 6.0 }),
        "smooth_curvature" => over_smooth(FieldSpec::Curvature),

        // --- direct traps ---
        // The thresholds are each shape's own: they are calibrated to paint a
        // comparable share of the frame, not to a shared distance.
        "direct_trap_ring" => direct(Shape::Ring, 0.0597, 0.45, Blend::Screen, "black"),
        "direct_trap_screen" => direct(Shape::Cross, 0.05, 0.15, Blend::Screen, "black"),
        "direct_trap_multiply" => direct(Shape::Cross, 0.1, 0.2, Blend::Multiply, "white"),
        "direct_trap_lines" => direct(Shape::Lines, 0.0807, 0.45, Blend::Screen, "black"),

        _ => {
            return Err(format!(
                "unknown mode '{name}'. Known modes: {}",
                names().collect::<Vec<_>>().join(", ")
            ));
        }
    })
}

/// Every mode name, in catalog order.
pub fn names() -> impl Iterator<Item = &'static str> {
    CATALOG.iter().map(|(name, _)| *name)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_catalogued_mode_resolves_and_is_valid() {
        for (name, identity) in CATALOG {
            let coloring = resolve(name).unwrap_or_else(|e| panic!("{name}: {e}"));
            coloring
                .validate()
                .unwrap_or_else(|e| panic!("{name} is not a valid coloring: {e}"));
            assert!(!identity.is_empty(), "{name} has no identity line");
        }
    }

    #[test]
    fn the_catalog_has_no_duplicates() {
        let mut seen: Vec<&str> = names().collect();
        let total = seen.len();
        seen.sort_unstable();
        seen.dedup();
        assert_eq!(seen.len(), total);
    }

    /// Smooth is the spine: it is the default coloring, and every composite is
    /// built on it. If those two ever disagree the composites are laying their
    /// texture over something other than what `smooth` renders.
    #[test]
    fn smooth_is_the_default_and_the_base_of_every_composite() {
        assert_eq!(resolve("smooth").unwrap(), Coloring::default());
        for name in names() {
            if let Coloring::Composite { base, .. } = resolve(name).unwrap() {
                assert_eq!(
                    base,
                    Layer {
                        field: FieldSpec::Smooth,
                        transform: Transform::Linear
                    },
                    "{name}"
                );
            }
        }
    }

    /// The three shapes of coloring, and which modes are which — the split that
    /// decides what `dump-field` will accept.
    #[test]
    fn the_catalog_splits_into_seven_fields_five_composites_and_four_traps() {
        let mut fields = Vec::new();
        let mut composites = Vec::new();
        let mut direct = Vec::new();
        for name in names() {
            match resolve(name).unwrap() {
                Coloring::Field { .. } => fields.push(name),
                Coloring::Composite { .. } => composites.push(name),
                Coloring::Direct { .. } => direct.push(name),
            }
        }
        assert_eq!(fields.len(), 7, "{fields:?}");
        assert_eq!(composites.len(), 5, "{composites:?}");
        assert_eq!(direct.len(), 4, "{direct:?}");
        for name in &fields {
            assert!(resolve(name).unwrap().dumpable_field().is_some(), "{name}");
        }
        for name in composites.iter().chain(&direct) {
            assert!(resolve(name).unwrap().why_not_a_field().is_some(), "{name}");
        }
    }

    #[test]
    fn an_unknown_mode_names_the_ones_that_exist() {
        let message = resolve("nautilus").unwrap_err();
        assert!(message.contains("nautilus"));
        assert!(message.contains("smooth_stripe"), "{message}");
    }
}
