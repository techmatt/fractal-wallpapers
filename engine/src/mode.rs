//! The named modes: the colorings that were worth keeping.
//!
//! A [`Coloring`](crate::coloring::Coloring) is a wide space — any field through
//! any curve, any pair of fields through any blend, any trap shape at any
//! threshold — and almost all of it is bad. What is here is the part that
//! survived being looked at: twenty settled points in that space, each with a
//! name, so a render can ask for a look rather than for a parameter vector.
//!
//! They come in four shapes, and the shape decides what can be done with the
//! result:
//!
//! * **One field** — `smooth` and the strange fields beside it. These map a
//!   scalar through the colormap, so they can be dumped and recolored.
//! * **Composites** — a smooth base with a strange field blended over it. The
//!   base carries the shape of the escape and the texture writes structure into
//!   it, including into the interior, where the smooth field has nothing to say.
//! * **Modulates** — a smooth base whose *palette position* a second field
//!   perturbs, rather than whose value it blends with. Two members, `itinerary`
//!   and `tail_itinerary`, which read the same address at opposite ends of the
//!   orbit.
//! * **Direct traps** — the color-valued family, which paints during the
//!   iteration and never makes a field at all.
//!
//! Anything not in this list is still reachable by writing the coloring out in
//! full. A name is a claim that a setting is worth returning to, and that claim
//! is what this list is for.
//!
//! ## Tiers, and why the catalog needs them
//!
//! The catalog is also the **production roster**: everything downstream that has
//! to pick a coloring — the render cache, the finished-render corpora, curation's
//! mode draw — reads it rather than a list of its own. That made "is this mode
//! shippable?" and "does this mode exist?" the same question, and they are not.
//!
//! So every entry carries a [`Tier`]. A **production** mode may be drawn by
//! anything; a **niche** mode is renderable on demand by name and is excluded from
//! every production draw. The exclusion is enforced at the one place a mode is
//! drawn, reading [`production`] — not at each caller, which is how a rule four
//! call sites have to remember becomes a rule one of them forgets.
//!
//! [`crate::field::FieldSpec::Discrete`] is the harder case and stays out of the
//! catalog entirely: it is a *teaching* field whose whole purpose is to be worse
//! than its neighbour, so it has no business having a name at all.
//! `no_catalogued_mode_reads_a_teaching_field` is that guard.
//!
//! ## What is deliberately absent
//!
//! One capability the source project had is **not** debt and will not arrive:
//! **normal-map shading** — lighting a render by the surface normal of a distance
//! estimate, with an azimuth and a height to place the lamp. Matt's call, and the
//! reason is that it makes a fractal look like an embossed metal plaque rather
//! than like a field: it replaces the picture's own structure with a lighting
//! model's. The `de` field is here without it, as a scalar coloring like any
//! other, and that is the whole of what this engine takes from that corner.

use crate::coloring::{Blend, Coloring, Layer, Transform};
use crate::direct_trap::Shape;
use crate::family::Family;
use crate::field::{AddressStart, FieldSpec, Reduction};

/// Whether a mode may be drawn by production or only asked for by name.
#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Tier {
    /// Shippable: every draw may pick it, and the corpora were collected over it.
    Production,
    /// Renderable on demand, excluded from every production draw. A mode is niche
    /// because it is expensive, unproven at scale, or interesting rather than
    /// good — never because it is broken, which would make it absent instead.
    ///
    /// The tier is a **holding place**, not a verdict: `threads` and `itinerary`
    /// stayed here until a round of human labels said they were worth drawing and
    /// the judge that ranks them could express the tier those labels used. `de` is
    /// the one that stays, because what it is for is a picture somebody asks for by
    /// name.
    Niche,
}

/// One named mode: what it is called, what it is for, and whether it ships.
#[derive(Clone, Copy, Debug)]
pub struct Entry {
    pub name: &'static str,
    pub identity: &'static str,
    pub tier: Tier,
}

const fn production(name: &'static str, identity: &'static str) -> Entry {
    Entry {
        name,
        identity,
        tier: Tier::Production,
    }
}

const fn niche(name: &'static str, identity: &'static str) -> Entry {
    Entry {
        name,
        identity,
        tier: Tier::Niche,
    }
}

/// Every named mode, with the line that says what it is for.
pub const CATALOG: [Entry; 20] = [
    production(
        "smooth",
        "Fractional escape time: the spine every composite builds on.",
    ),
    production("tia", "Triangle-inequality average: fine engraved banding."),
    production(
        "stripe",
        "Stripe average at density 6: combed flowing striations.",
    ),
    production(
        "exp_smoothing",
        "Sum of exp(-|z|) over the orbit: an averaging alternative to smooth.",
    ),
    production(
        "gaussian_int",
        "Closest approach to the integer lattice: a tiled, beaded field.",
    ),
    production(
        "trap_circle",
        "Closest approach to the unit circle, read through a log curve.",
    ),
    production("curvature", "Mean turning angle of the orbit."),
    production(
        "smooth_mean_angle",
        "Smooth base, screened with the lattice trap's spread angle.",
    ),
    production(
        "smooth_angle_min",
        "Smooth base, screened with the angle at the lattice's closest approach.",
    ),
    production(
        "smooth_trap_circle",
        "Smooth base, screened with the circle trap: structure in the interior.",
    ),
    production(
        "smooth_stripe",
        "Smooth base, screened with the stripe average.",
    ),
    production("smooth_curvature", "Smooth base, screened with curvature."),
    production(
        "direct_trap_ring",
        "Direct trap, ring shape, screened over black: the cleanest of the family.",
    ),
    production(
        "direct_trap_screen",
        "Direct trap, cross shape, screened over black: bright thorns.",
    ),
    production(
        "direct_trap_multiply",
        "Direct trap, cross shape, multiplied over white: dark lace on light.",
    ),
    production(
        "direct_trap_lines",
        "Direct trap on the real axis: the narrowest, most directional member.",
    ),
    production(
        "threads",
        "Smooth base plus the accumulated cross trap: sparse organic flow.",
    ),
    production(
        "itinerary",
        "Smooth base whose palette position the orbit's angular address shifts. \
         The address opens at z1 on a dynamical plane and at z0 on a parameter one.",
    ),
    production(
        "tail_itinerary",
        "Smooth base shifted by the LAST symbols of the orbit's angular address, \
         rather than the first. Reads the same on both planes.",
    ),
    niche(
        "de",
        "Distance to the set itself, read through a log curve. No lighting.",
    ),
];

/// The weight the composite modes give their texture.
///
/// Not 1: at full strength the texture's own normalization competes with the
/// base's and the escape structure stops being legible underneath it. This is
/// the settled value for all five screened composites. `threads` is additive and
/// carries its own, lower weight.
const TEXTURE_WEIGHT: f64 = 0.85;

/// The kernel width and additive weight `threads` was kept at.
///
/// Both were found on deliberately generic locations, which is why they are
/// written here as one mode's settled pair rather than as defaults anything else
/// reads: 0.15 is sharp enough to read as threads rather than haze, and 0.5 lets
/// the texture be seen without erasing the escape structure it lies over.
const THREADS_SIGMA: f64 = 0.15;
const THREADS_WEIGHT: f64 = 0.5;

/// The address `itinerary` reads, and how far it pushes the palette.
///
/// Four sectors in base four, which makes the address a clean base-4 expansion;
/// 26 symbols, which is the `f64` ceiling at that base; and a shift of half a turn
/// of the gradient, which perturbs the smooth base's own structure rather than
/// overriding it. See [`crate::field::FieldSpec::Itinerary`].
///
/// **The first three are `tail_itinerary`'s too**, which is why they are named
/// here rather than written into the one arm. The base four is also what makes a
/// tail window exact — see [`TAIL_ITINERARY_START`]. Moving any of them renames
/// every cached picture of *both* modes, which is the reason the tail arrived as
/// a mode of its own rather than as a fourth knob on this one.
const ITINERARY_SECTORS: u32 = 4;
const ITINERARY_BASE: f64 = 4.0;
const ITINERARY_DEPTH: u32 = 26;
const ITINERARY_SHIFT: f64 = 0.5;

/// Where the named mode opens its address, which is the one setting in this
/// catalog that the family decides.
///
/// On a **dynamical plane** `z₀` is the pixel, so an address opened there spells
/// its most significant symbol from the pixel's own angular sector — a hard wedge
/// seam along the axes, drawn over the set rather than by it. Matt looked at the
/// pair on 2026-08-17 and kept `z1`, so that is what the mode is here. On a
/// **parameter plane** `z₀ = 0` for every pixel: there is no wedge to remove and
/// opening at `z₁` would only renumber every address by a base-`k` place, so the
/// mode stays at `z0` and [`Coloring::agrees_with_family`] refuses the other.
///
/// The choice serializes because it is no longer the field's default everywhere:
/// a dynamical-plane `itinerary` record carries `"start": "z1"`, which is what
/// keeps the record and the picture the same statement.
///
/// [`Coloring::agrees_with_family`]: crate::coloring::Coloring::agrees_with_family
fn itinerary_start(family: Option<&Family>) -> AddressStart {
    match family {
        Some(family) if family.pixel_is_z0() => AddressStart::Z1,
        _ => AddressStart::Z0,
    }
}

/// Where `tail_itinerary` reads its address, and how far it pushes the palette.
///
/// **The two settings that make it a mode of its own, and the only two that
/// differ from `itinerary`.** The sectors, the weight base and the depth are read
/// from `itinerary`'s own constants above rather than restated, because the two
/// modes are the same address and it is only the window over it that moves — a
/// second copy of `26` here would be a number nobody would keep in step.
///
/// The shift matches `itinerary`'s half turn deliberately. It is what makes the
/// pair comparable: rendered side by side at one location, everything but which
/// end of the orbit the address is read from is held fixed, which is the whole
/// question the mode was added to ask.
///
/// The start is a **catalog constant and not a function of the family**, which is
/// the one structural difference from [`itinerary_start`]. A tail address never
/// reads `z₀`, so the wedge that split `itinerary` across the two planes cannot
/// arise, and `tail_itinerary` is one coloring everywhere. See
/// [`AddressStart::Tail`](crate::field::AddressStart::Tail).
const TAIL_ITINERARY_START: AddressStart = AddressStart::Tail;
const TAIL_ITINERARY_SHIFT: f64 = 0.5;

/// Look a mode up by name, over the family it will be rendered on.
///
/// `None` is the **catalog's own form** — what `fractal-engine modes` prints.
/// Nineteen of the twenty entries are the same coloring whatever they are drawn
/// over; `itinerary` is not, and its catalog form is its parameter-plane one. See
/// [`itinerary_start`]. `tail_itinerary` is in the nineteen — its start is a
/// constant, not the family's answer.
pub fn resolve(name: &str, family: Option<&Family>) -> Result<Coloring, String> {
    let field = |field, transform| Coloring::Field { field, transform };
    let over_smooth = |field| Coloring::Composite {
        base: smooth_base(),
        texture: Layer {
            field,
            transform: Transform::Linear,
        },
        blend: Blend::Screen,
        texture_weight: TEXTURE_WEIGHT,
        texture_gamma: None,
    };
    let direct = |shape, threshold, opacity, merge, start_color: &str| Coloring::Direct {
        shape,
        trap_radius: 1.0,
        threshold: Some(threshold),
        opacity,
        merge,
        merge_order: crate::coloring::MergeOrder::BottomUp,
        start_color: start_color.to_string(),
        transform: Transform::Linear,
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
        // The two modes that are not linear, and for the same reason: both fields
        // pile their values up near zero — a circle trap's closest approaches and
        // a distance estimate's samples against the boundary — and a log curve is
        // what spreads that pile back across the gradient instead of leaving the
        // frame one flat color.
        "trap_circle" => field(FieldSpec::TrapCircle { radius: 1.0 }, Transform::Log),
        "curvature" => field(FieldSpec::Curvature, Transform::Linear),
        "de" => field(FieldSpec::De { scale: 1.0 }, Transform::Log),

        // --- composites: a strange field blended over the smooth base ---
        "smooth_mean_angle" => over_smooth(FieldSpec::GaussianInt {
            reduce: Reduction::MeanAngle,
        }),
        "smooth_angle_min" => over_smooth(FieldSpec::GaussianInt {
            reduce: Reduction::AngleMin,
        }),
        "smooth_trap_circle" => over_smooth(FieldSpec::TrapCircle { radius: 1.0 }),
        "smooth_stripe" => over_smooth(FieldSpec::Stripe { density: 6.0 }),
        "smooth_curvature" => over_smooth(FieldSpec::Curvature),
        // Additive, not screened. The one composite here that is: see
        // [`Blend::Add`](crate::coloring::Blend::Add).
        "threads" => Coloring::Composite {
            base: smooth_base(),
            texture: Layer {
                field: FieldSpec::Threads {
                    sigma: THREADS_SIGMA,
                },
                transform: Transform::Linear,
            },
            blend: Blend::Add,
            texture_weight: THREADS_WEIGHT,
            texture_gamma: None,
        },

        // --- the modulates ---
        "itinerary" => Coloring::Modulate {
            base: smooth_base(),
            texture: Layer {
                field: FieldSpec::Itinerary {
                    sectors: ITINERARY_SECTORS,
                    weight_base: Some(ITINERARY_BASE),
                    depth: ITINERARY_DEPTH,
                    start: itinerary_start(family),
                },
                transform: Transform::Linear,
            },
            shift: ITINERARY_SHIFT,
        },

        "tail_itinerary" => Coloring::Modulate {
            base: smooth_base(),
            texture: Layer {
                field: FieldSpec::Itinerary {
                    sectors: ITINERARY_SECTORS,
                    weight_base: Some(ITINERARY_BASE),
                    depth: ITINERARY_DEPTH,
                    start: TAIL_ITINERARY_START,
                },
                transform: Transform::Linear,
            },
            shift: TAIL_ITINERARY_SHIFT,
        },

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

/// The base every composite and the one modulate build on.
fn smooth_base() -> Layer {
    Layer {
        field: FieldSpec::Smooth,
        transform: Transform::Linear,
    }
}

/// Every mode name, in catalog order.
pub fn names() -> impl Iterator<Item = &'static str> {
    CATALOG.iter().map(|entry| entry.name)
}

/// Every mode a production draw may pick, in catalog order.
///
/// **The one place the tier is enforced.** A caller that draws a mode reads this
/// rather than filtering [`names`] itself, so "production cannot draw a niche
/// mode" is a property of one function instead of a rule at every draw site.
pub fn production_names() -> impl Iterator<Item = &'static str> {
    CATALOG
        .iter()
        .filter(|entry| entry.tier == Tier::Production)
        .map(|entry| entry.name)
}

/// Which tier a named mode is on, or `None` for a name that is not in the catalog.
pub fn tier(name: &str) -> Option<Tier> {
    CATALOG
        .iter()
        .find(|entry| entry.name == name)
        .map(|entry| entry.tier)
}

#[cfg(test)]
mod tests {
    use super::*;

    use num_complex::Complex;

    /// The catalog's own form of a mode — no family, so `itinerary` comes back at
    /// `z0`. Every claim below that is not about the plane is a claim about this.
    fn catalogued(name: &str) -> Result<Coloring, String> {
        resolve(name, None)
    }

    /// One dynamical plane and one parameter plane, which is the whole of the
    /// split [`itinerary_start`] turns on.
    const JULIA: Family = Family::Julia {
        degree: 2,
        c: Complex::new(-0.8, 0.156),
    };
    const MANDELBROT: Family = Family::Multibrot { degree: 2 };

    #[test]
    fn every_catalogued_mode_resolves_and_is_valid() {
        for entry in CATALOG {
            let coloring = catalogued(entry.name).unwrap_or_else(|e| panic!("{}: {e}", entry.name));
            coloring
                .validate()
                .unwrap_or_else(|e| panic!("{} is not a valid coloring: {e}", entry.name));
            assert!(
                !entry.identity.is_empty(),
                "{} has no identity line",
                entry.name
            );
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

    /// Smooth is the spine: it is the default coloring, and every composite and
    /// the modulate are built on it. If those ever disagree the textures are being
    /// laid over something other than what `smooth` renders.
    #[test]
    fn smooth_is_the_default_and_the_base_of_every_composite() {
        assert_eq!(catalogued("smooth").unwrap(), Coloring::default());
        for name in names() {
            let base = match catalogued(name).unwrap() {
                Coloring::Composite { base, .. } | Coloring::Modulate { base, .. } => base,
                _ => continue,
            };
            assert_eq!(base, smooth_base(), "{name}");
        }
    }

    /// The four shapes of coloring, and which modes are which — the split that
    /// decides what `dump-field` will accept.
    ///
    /// The modulate count moved from one to two when `tail_itinerary` arrived.
    /// These are the intended counts and not a tally that follows the catalog: a
    /// mode added without a decision about which shape it is would fail here,
    /// which is the point of writing them down.
    #[test]
    fn the_catalog_splits_into_eight_fields_six_composites_two_modulates_and_four_traps() {
        let mut fields = Vec::new();
        let mut composites = Vec::new();
        let mut modulates = Vec::new();
        let mut direct = Vec::new();
        for name in names() {
            match catalogued(name).unwrap() {
                Coloring::Field { .. } => fields.push(name),
                Coloring::Composite { .. } => composites.push(name),
                Coloring::Modulate { .. } => modulates.push(name),
                Coloring::Direct { .. } => direct.push(name),
            }
        }
        assert_eq!(fields.len(), 8, "{fields:?}");
        assert_eq!(composites.len(), 6, "{composites:?}");
        assert_eq!(modulates.len(), 2, "{modulates:?}");
        assert_eq!(direct.len(), 4, "{direct:?}");
        for name in &fields {
            assert!(
                catalogued(name).unwrap().dumpable_field().is_some(),
                "{name}"
            );
        }
        for name in composites.iter().chain(&modulates).chain(&direct) {
            assert!(
                catalogued(name).unwrap().why_not_a_field().is_some(),
                "{name}"
            );
        }
    }

    /// The catalog is the production roster, so a teaching field may not appear
    /// anywhere in it — not as a mode of its own, and not hidden as one half of
    /// a composite. Every field a catalogued mode reads is checked, because the
    /// second way in is the one nobody would look for.
    #[test]
    fn no_catalogued_mode_reads_a_teaching_field() {
        for name in names() {
            for field in fields_of(name) {
                assert!(
                    !matches!(field, FieldSpec::Discrete { .. }),
                    "{name} reads the discrete field, which is not a production coloring"
                );
            }
        }
    }

    fn fields_of(name: &str) -> Vec<FieldSpec> {
        match catalogued(name).unwrap() {
            Coloring::Field { field, .. } => vec![field],
            Coloring::Composite { base, texture, .. }
            | Coloring::Modulate { base, texture, .. } => vec![base.field, texture.field],
            Coloring::Direct { .. } => Vec::new(),
        }
    }

    /// The tier split, stated once: one niche mode, everything else ships, and the
    /// production roster is a strict subset of the catalog.
    ///
    /// `threads` and `itinerary` were held here while the judge that would have to
    /// rank them could not express the top of its own scale. That gate is closed —
    /// the strange head trains four classes and its release bar has been restated
    /// against it — so they are drawable. `de` stays, and permanently: Matt's call.
    #[test]
    fn the_distance_estimate_is_the_one_niche_mode_and_nothing_else_is() {
        let niche: Vec<&str> = CATALOG
            .iter()
            .filter(|entry| entry.tier == Tier::Niche)
            .map(|entry| entry.name)
            .collect();
        assert_eq!(niche, vec!["de"]);

        let drawn: Vec<&str> = production_names().collect();
        assert_eq!(drawn.len(), CATALOG.len() - niche.len());
        for name in &niche {
            assert!(!drawn.contains(name), "{name} is drawable");
            assert_eq!(tier(name), Some(Tier::Niche));
        }
        for name in &drawn {
            assert_eq!(tier(name), Some(Tier::Production), "{name}");
        }
        assert_eq!(tier("nautilus"), None);
    }

    /// A niche mode is still a real mode: it resolves by name and renders, which
    /// is the whole difference between "not drawn" and "not there". The two that
    /// have since been promoted resolve the same way they always did — a tier
    /// moves what may *draw* a mode and nothing else about it.
    #[test]
    fn a_niche_mode_still_resolves_by_name() {
        for name in ["threads", "itinerary", "de"] {
            catalogued(name).unwrap_or_else(|e| panic!("{name}: {e}"));
        }
    }

    /// The two experimental modes are pinned to the parameters Matt kept. They were
    /// tuned on deliberately generic locations, so these numbers are the *record*
    /// of a judgement rather than a derivation — which is exactly why a test has to
    /// hold them: nothing else would notice them drifting.
    #[test]
    fn the_kept_parameters_are_what_the_two_experimental_modes_resolve_to() {
        let Coloring::Composite {
            texture,
            blend,
            texture_weight,
            ..
        } = catalogued("threads").unwrap()
        else {
            panic!("threads is a composite");
        };
        assert_eq!(texture.field, FieldSpec::Threads { sigma: 0.15 });
        assert_eq!(blend, Blend::Add, "threads is additive, not screened");
        assert_eq!(texture_weight, 0.5);

        let Coloring::Modulate { texture, shift, .. } = catalogued("itinerary").unwrap() else {
            panic!("itinerary is a modulate");
        };
        assert_eq!(
            texture.field,
            FieldSpec::Itinerary {
                sectors: 4,
                weight_base: Some(4.0),
                depth: 26,
                start: AddressStart::Z0,
            }
        );
        assert_eq!(shift, 0.5);
    }

    /// The one setting in the catalog the family decides, and the only difference
    /// between the two answers: everything else about the mode is the same coloring
    /// on both planes, so a reader can hold "itinerary means one thing" and this.
    #[test]
    fn the_address_opens_at_z1_where_the_mode_is_drawn_over_a_dynamical_plane() {
        fn address(family: Option<&Family>) -> FieldSpec {
            let Coloring::Modulate { texture, .. } = resolve("itinerary", family).unwrap() else {
                panic!("itinerary is a modulate");
            };
            texture.field
        }
        let with = |start| FieldSpec::Itinerary {
            sectors: ITINERARY_SECTORS,
            weight_base: Some(ITINERARY_BASE),
            depth: ITINERARY_DEPTH,
            start,
        };

        for family in [
            JULIA,
            Family::Julia {
                degree: 5,
                c: Complex::new(0.4, 0.0),
            },
            crate::family::CLASSIC_PHOENIX,
        ] {
            assert_eq!(address(Some(&family)), with(AddressStart::Z1), "{family:?}");
        }
        for degree in 2..=5 {
            let family = Family::Multibrot { degree };
            assert_eq!(address(Some(&family)), with(AddressStart::Z0), "{family:?}");
        }
        assert_eq!(address(None), with(AddressStart::Z0), "the catalog's form");
    }

    /// The plane moves one key and nothing else — not the shift, not the base, not
    /// any other entry in the catalog. Otherwise "which plane is this?" would be a
    /// question every mode's record had to be read against.
    #[test]
    fn no_other_mode_changes_with_the_plane() {
        for name in names() {
            let over_julia = resolve(name, Some(&JULIA)).unwrap();
            let over_mandelbrot = resolve(name, Some(&MANDELBROT)).unwrap();
            assert_eq!(over_mandelbrot, catalogued(name).unwrap(), "{name}");
            assert_eq!(over_julia == over_mandelbrot, name != "itinerary", "{name}");
        }
    }

    /// The refusal and the mode agree: the catalog never hands back a coloring the
    /// family it was resolved over would reject.
    #[test]
    fn every_mode_resolves_to_a_coloring_its_own_family_accepts() {
        for family in [JULIA, MANDELBROT, crate::family::CLASSIC_PHOENIX] {
            for name in names() {
                resolve(name, Some(&family))
                    .unwrap()
                    .agrees_with_family(&family)
                    .unwrap_or_else(|e| panic!("{name} over {family:?}: {e}"));
            }
        }
    }

    /// The distance estimate ships as a scalar field and nothing else: no lighting,
    /// no normal map, no lamp. That absence is a decision, so it is asserted rather
    /// than left to be noticed.
    #[test]
    fn the_distance_estimate_is_a_plain_field_coloring() {
        assert_eq!(
            catalogued("de").unwrap(),
            Coloring::Field {
                field: FieldSpec::De { scale: 1.0 },
                transform: Transform::Log,
            }
        );
    }

    /// The tail mode is the head mode with one key moved, and that is the claim
    /// worth pinning: if the sectors, the base, the depth or the shift ever part,
    /// the contact sheet the pair was chosen on stops being a comparison of the
    /// window and becomes a comparison of four things at once.
    #[test]
    fn the_tail_mode_is_the_itinerary_with_the_window_moved_and_nothing_else() {
        let Coloring::Modulate {
            base: tail_base,
            texture: tail,
            shift: tail_shift,
        } = catalogued("tail_itinerary").unwrap()
        else {
            panic!("tail_itinerary is a modulate");
        };
        let Coloring::Modulate {
            base: head_base,
            texture: head,
            shift: head_shift,
        } = catalogued("itinerary").unwrap()
        else {
            panic!("itinerary is a modulate");
        };

        assert_eq!(tail_base, head_base, "both are built on the smooth spine");
        assert_eq!(tail_shift, head_shift, "the shift is matched on purpose");
        assert_eq!(tail_shift, 0.5);
        assert_eq!(tail.transform, head.transform);
        assert_eq!(
            tail.field,
            FieldSpec::Itinerary {
                sectors: ITINERARY_SECTORS,
                weight_base: Some(ITINERARY_BASE),
                depth: ITINERARY_DEPTH,
                start: AddressStart::Tail,
            }
        );

        let (
            FieldSpec::Itinerary {
                sectors: tail_sectors,
                weight_base: tail_weight_base,
                depth: tail_depth,
                start: tail_start,
            },
            FieldSpec::Itinerary {
                sectors: head_sectors,
                weight_base: head_weight_base,
                depth: head_depth,
                start: head_start,
            },
        ) = (tail.field, head.field)
        else {
            panic!("both textures are addresses");
        };
        assert_eq!(tail_sectors, head_sectors);
        assert_eq!(tail_weight_base, head_weight_base);
        assert_eq!(tail_depth, head_depth);
        assert_ne!(tail_start, head_start, "the window is the whole difference");
    }

    /// The tail window is exact at the base the catalog asks for, which is the
    /// one thing that makes the mode's arithmetic more than approximately right.
    /// See `Address::roll`: the retained symbols are worth less than one, so the
    /// integer part `fract` drops is the departing symbol and nothing else.
    #[test]
    fn the_tail_modes_weight_base_is_the_one_the_rolling_window_is_exact_at() {
        let Coloring::Modulate { texture, .. } = catalogued("tail_itinerary").unwrap() else {
            panic!("tail_itinerary is a modulate");
        };
        let FieldSpec::Itinerary {
            sectors,
            weight_base,
            ..
        } = texture.field
        else {
            panic!("the texture is an address");
        };
        assert!(
            weight_base.unwrap_or(sectors as f64) >= sectors as f64,
            "a tail window under a weight base below the sector count clips a symbol \
             it was meant to keep"
        );
    }

    /// The tail mode is one coloring on both planes, and that is a fact about the
    /// window rather than an omission: `z0` is not in a tail address, so there is
    /// no wedge to remove and nothing for the family to decide. Asserted at both
    /// ends — the coloring does not move, and both planes accept it.
    #[test]
    fn the_tail_address_is_the_same_on_both_planes_and_accepted_on_both() {
        for family in [JULIA, MANDELBROT, crate::family::CLASSIC_PHOENIX] {
            let over = resolve("tail_itinerary", Some(&family)).unwrap();
            assert_eq!(over, catalogued("tail_itinerary").unwrap(), "{family:?}");
            over.agrees_with_family(&family)
                .unwrap_or_else(|e| panic!("{family:?}: {e}"));
        }
    }

    /// The refusal is a three-way match and not a name match, so the plane rule
    /// is stated once per window rather than falling out of which variants happen
    /// to be spelled. `z1` on a parameter plane is still refused; the tail is not.
    #[test]
    fn the_plane_refuses_the_z1_window_and_only_that_one() {
        let address = |start| Coloring::Modulate {
            base: smooth_base(),
            texture: Layer {
                field: FieldSpec::Itinerary {
                    sectors: ITINERARY_SECTORS,
                    weight_base: Some(ITINERARY_BASE),
                    depth: ITINERARY_DEPTH,
                    start,
                },
                transform: Transform::Linear,
            },
            shift: ITINERARY_SHIFT,
        };
        address(AddressStart::Z0)
            .agrees_with_family(&MANDELBROT)
            .unwrap();
        address(AddressStart::Tail)
            .agrees_with_family(&MANDELBROT)
            .unwrap();
        let refused = address(AddressStart::Z1)
            .agrees_with_family(&MANDELBROT)
            .unwrap_err();
        assert!(refused.contains("z1 start"), "{refused}");
        for start in [AddressStart::Z0, AddressStart::Z1, AddressStart::Tail] {
            address(start).agrees_with_family(&JULIA).unwrap();
        }
    }

    #[test]
    fn an_unknown_mode_names_the_ones_that_exist() {
        let message = catalogued("nautilus").unwrap_err();
        assert!(message.contains("nautilus"));
        assert!(message.contains("smooth_stripe"), "{message}");
    }
}
