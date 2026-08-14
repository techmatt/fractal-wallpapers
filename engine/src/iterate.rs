//! The escape-time loop. One loop, every family.
//!
//! Iterate until the orbit leaves a disc of radius [`BAILOUT`] or until the
//! iteration cap runs out. A point that leaves gets a *smooth* iteration count —
//! a real number, not an integer — so the field it lands in has no visible
//! terraces. A point that stays gets `NaN`, which carries "interior" through the
//! rest of the pipeline as data rather than as a parallel mask.

use num_complex::Complex;

use crate::family::Family;

/// Escape radius `B`.
///
/// Large on purpose. The smooth count's accuracy depends on `|z|` overshooting
/// the boundary by a negligible relative amount when the orbit finally crosses
/// it, and a bailout this size makes the first step past the boundary land far
/// enough out that the fractional part is clean.
pub const BAILOUT: f64 = 65536.0; // 2^16

/// What one point did.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Escape {
    /// The orbit left the bailout disc within the iteration cap.
    pub escaped: bool,
    /// Smooth iteration count when `escaped`, `NaN` otherwise.
    pub smooth: f64,
}

impl Escape {
    /// The orbit never left: an interior point.
    pub fn interior() -> Self {
        Escape {
            escaped: false,
            smooth: f64::NAN,
        }
    }
}

/// Iterate one point of the plane.
///
/// `pixel` is the point's coordinate in whichever plane the family lives in:
/// the constant `c` for a parameter-plane family, the starting value `z₀` for a
/// dynamical one. [`Family::seed`] makes that choice; this loop does not know
/// which it got.
// TODO(perf): the source project reached deep zoom by iterating a low-precision
// delta against one high-precision reference orbit, rebasing when the delta grew
// past the reference. That belongs here when deep zoom does.
pub fn escape(family: &Family, pixel: Complex<f64>, maxiter: u32) -> Escape {
    let bailout_sq = BAILOUT * BAILOUT;
    let (mut z, mut z_prev, c) = family.seed(pixel);

    for n in 1..=maxiter {
        let next = family.step(z, z_prev, c);
        z_prev = z;
        z = next;

        let magnitude_sq = z.norm_sqr();
        if magnitude_sq > bailout_sq {
            return Escape {
                escaped: true,
                smooth: smooth_count(n, magnitude_sq, family.degree()),
            };
        }
    }

    Escape::interior()
}

/// The smooth (fractional) iteration count of an orbit that escaped at step `n`
/// with `|z|² = magnitude_sq`.
///
/// `nu = (n + 1) − log_d( ln|z| / ln B )`
///
/// The integer count alone is a staircase: every point between two escape steps
/// gets the same value, and the field bands. The correction measures *how far
/// past* the bailout the orbit landed. Near escape `|z_{n+1}| ≈ |z_n|^d`, so one
/// step multiplies `ln|z|` by `d` — which makes `log_d` the right way to read
/// the overshoot as a fraction of a step, and makes the **degree** the base. Get
/// that base wrong and every family but the quadratic one bands anyway.
///
/// Dividing by `ln B` inside the logarithm pins `nu` to zero at the bailout
/// boundary. That is a constant shift, invisible to a colormap normalized over
/// the frame, and load-bearing to anything that compares fields across bailouts.
fn smooth_count(n: u32, magnitude_sq: f64, degree: u32) -> f64 {
    let log_z = 0.5 * magnitude_sq.ln(); // ln|z|
    let log_bailout = BAILOUT.ln();
    let overshoot = log_z / log_bailout;

    // The double logarithm is finite only for an orbit genuinely outside the
    // bailout disc. Anything else — an overflow to infinity, a degenerate
    // bailout — falls back to the integer count rather than poisoning the field
    // with a NaN that would read as "interior".
    if overshoot.is_finite() && overshoot > 0.0 {
        (n + 1) as f64 - overshoot.ln() / (degree as f64).ln()
    } else {
        (n + 1) as f64
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn julia(c: Complex<f64>) -> Family {
        Family::Julia { degree: 2, c }
    }

    #[test]
    fn the_origin_is_interior_to_every_multibrot() {
        for degree in 2..=5 {
            let family = Family::Multibrot { degree };
            let sample = escape(&family, Complex::new(0.0, 0.0), 500);
            assert!(!sample.escaped, "degree {degree}: the origin escaped");
            assert!(sample.smooth.is_nan());
        }
    }

    #[test]
    fn a_far_away_point_escapes_immediately() {
        let family = Family::Multibrot { degree: 2 };
        let sample = escape(&family, Complex::new(1e6, 1e6), 500);
        assert!(sample.escaped);
        assert!(sample.smooth.is_finite());
    }

    /// Both classes must be present in a view that spans the set, for every
    /// family — the cheapest evidence that a recurrence is actually live.
    #[test]
    fn every_family_produces_both_interior_and_exterior() {
        let c = Complex::new(-0.8, 0.156);
        let families = [
            Family::Multibrot { degree: 2 },
            Family::Multibrot { degree: 3 },
            Family::Multibrot { degree: 4 },
            Family::Multibrot { degree: 5 },
            julia(c),
            Family::Julia {
                degree: 3,
                c: Complex::new(0.0, 0.0),
            },
            Family::Julia {
                degree: 5,
                c: Complex::new(0.0, 0.0),
            },
            Family::Phoenix {
                c: crate::family::PHOENIX_C,
                p: crate::family::PHOENIX_P,
                z_prev: Complex::new(0.0, 0.0),
            },
        ];
        for family in families {
            let (mut escaped, mut interior) = (0, 0);
            for row in 0..32 {
                for col in 0..32 {
                    let re = -1.8 + 3.6 * (col as f64 + 0.5) / 32.0;
                    let im = -1.8 + 3.6 * (row as f64 + 0.5) / 32.0;
                    let sample = escape(&family, Complex::new(re, im), 400);
                    if sample.escaped {
                        escaped += 1;
                        assert!(sample.smooth.is_finite(), "{family:?}: non-finite smooth");
                    } else {
                        interior += 1;
                    }
                }
            }
            assert!(
                escaped > 0 && interior > 0,
                "{family:?}: escaped={escaped} interior={interior}"
            );
        }
    }

    /// Phoenix with `p = 0` and `z₋₁ = 0` is a quadratic Julia set — not
    /// approximately, exactly. The memory term is the only difference between
    /// the two recurrences, and multiplying it by zero removes it.
    #[test]
    fn phoenix_with_zero_p_is_a_quadratic_julia() {
        let c = Complex::new(-0.4, 0.6);
        let phoenix = Family::Phoenix {
            c,
            p: Complex::new(0.0, 0.0),
            z_prev: Complex::new(0.0, 0.0),
        };
        let twin = julia(c);
        for row in 0..40 {
            for col in 0..40 {
                let re = -1.6 + 3.2 * (col as f64 + 0.5) / 40.0;
                let im = -1.6 + 3.2 * (row as f64 + 0.5) / 40.0;
                let pixel = Complex::new(re, im);
                let a = escape(&phoenix, pixel, 600);
                let b = escape(&twin, pixel, 600);
                assert_eq!(a.escaped, b.escaped, "at {pixel}");
                assert_eq!(
                    a.smooth.to_bits(),
                    b.smooth.to_bits(),
                    "smooth count differs at {pixel}"
                );
            }
        }
    }

    /// A non-zero `z₋₁` is a real axis, not a decoration: it must move the set.
    #[test]
    fn a_nonzero_z_prev_gives_a_different_set() {
        let classic = Family::Phoenix {
            c: crate::family::PHOENIX_C,
            p: crate::family::PHOENIX_P,
            z_prev: Complex::new(0.0, 0.0),
        };
        let shifted = Family::Phoenix {
            c: crate::family::PHOENIX_C,
            p: crate::family::PHOENIX_P,
            z_prev: Complex::new(0.35, -0.2),
        };
        let differing = (0..48)
            .flat_map(|row| (0..48).map(move |col| (row, col)))
            .filter(|&(row, col)| {
                let re = -1.6 + 3.2 * (col as f64 + 0.5) / 48.0;
                let im = -1.6 + 3.2 * (row as f64 + 0.5) / 48.0;
                let pixel = Complex::new(re, im);
                escape(&classic, pixel, 400).escaped != escape(&shifted, pixel, 400).escaped
            })
            .count();
        assert!(differing > 0, "z₋₁ changed nothing");
    }

    /// The smooth count must cross an escape-step boundary continuously: that is
    /// the entire reason it exists. Walk the real axis inward from `c = 4` to
    /// `c = 2.05`, where every point escapes and the integer count ticks from 3
    /// to 4 partway along. The integer count jumps by 1 there; the smooth count
    /// must not jump at all.
    #[test]
    fn the_smooth_count_does_not_terrace() {
        let family = Family::Multibrot { degree: 2 };
        let samples: Vec<f64> = (0..2000)
            .map(|step| {
                let re = 4.0 - 1.95 * step as f64 / 2000.0;
                let sample = escape(&family, Complex::new(re, 0.0), 100);
                assert!(sample.escaped, "c = {re} should escape");
                sample.smooth
            })
            .collect();

        let total: f64 = samples.last().unwrap() - samples.first().unwrap();
        assert!(
            total > 0.5,
            "the walk never crossed a step boundary ({total})"
        );

        let largest_step = samples
            .windows(2)
            .map(|pair| (pair[1] - pair[0]).abs())
            .fold(0.0f64, f64::max);
        assert!(
            largest_step < 0.05,
            "terrace of {largest_step} in the field"
        );
    }
}
