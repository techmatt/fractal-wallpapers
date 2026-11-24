//! A frame stirred by the fractal's own field, before anything is iterated.
//!
//! A [`crate::projection`] says where a sample looks from its place in the frame
//! alone. A **stir** moves that point by what an escape loop finds there: a pass
//! reads the smooth count of a *copy* of the fractal (the frame's own, or one seen
//! through a [`View`]) and pushes the point along the copy's level lines,
//!
//! ```text
//! p ← p + (strength / steps) · L · sin(2π·(ν / period + phase)) · e^(i·angle) · ĝ
//! ```
//!
//! with `ν` the copy's smooth count at `p`, `ĝ` the unit direction it climbs in and
//! `L` the copy's distance estimate there, capped at `largest` frame widths. At
//! `angle` 90 the push runs along the level line, so the point is carried round
//! whatever the line encloses; the sine turns it the other way every half `period`
//! of the count, so neighbouring bands shear against each other, and whatever the
//! stack then draws at the moved point is combed into S-curls where its own bands
//! cross the copy's. `steps` repeats the push from wherever the last one landed (a
//! flow followed, not one jump), which is what lets a curl wind up without the map
//! folding over itself.
//!
//! The length is the distance to the copy's set, so the push shrinks to nothing on
//! the set and a point inside it never moves: the curls are as large as the room the
//! set leaves them and tighten without end towards it. A pass is one more escape
//! loop per step and per sample, and still a pure function of the sample: a band of
//! rows draws the bytes the whole frame would.
//!
//! The stirred map is no isometry, so it hands the compositor a Jacobian as a
//! projection does ([`Sample`]): a forward difference over half a sample step, two
//! more runs of the passes, taken only when a light, a distance or an `inside`
//! channel asks for it.

use num_complex::Complex;
use serde::{Deserialize, Serialize};

use crate::family::Family;
use crate::iterate::{self, Interior, Wants};
use crate::projection::Sample;
use crate::style::View;
use crate::viewport::Viewport;

/// The most steps one pass takes, and the most passes a style stirs with: each step
/// is an escape loop per sample (three with a Jacobian).
pub const MAX_STEPS: u32 = 16;
pub const MAX_PASSES: usize = 4;

/// One pass of the stir: see the module documentation for the formula.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct Stir {
    /// The copy whose field pushes the point. The default is the frame's own.
    pub view: View,
    /// How far the point is carried in all, in lengths `L`: at `angle` 90 about the
    /// radians it turns round what the level line encloses.
    pub strength: f64,
    /// Degrees from the direction the copy's count climbs in to the push: 90 runs
    /// along the level line, 0 towards the copy's set.
    pub angle: f64,
    /// Escape steps of the copy per full swing of the push. 0: no swing, one way.
    pub period: f64,
    /// Where in its swing the push is at a count of 0, in turns.
    pub phase: f64,
    /// The cap on the length `L`, in frame widths.
    pub largest: f64,
    /// How many times the push is taken, each from where the last landed.
    pub steps: u32,
}

impl Default for Stir {
    fn default() -> Stir {
        Stir {
            view: View::default(),
            strength: 1.0,
            angle: 90.0,
            period: 4.0,
            phase: 0.0,
            largest: 0.05,
            steps: 1,
        }
    }
}

impl Stir {
    /// Refuse a pass that would draw something other than what it says.
    pub fn validate(&self) -> Result<(), String> {
        if !self.view.is_valid() {
            return Err("stir view is finite, its zoom positive".into());
        }
        if !(self.strength.is_finite() && self.angle.is_finite() && self.phase.is_finite()) {
            return Err("stir strength, angle and phase are finite".into());
        }
        if !(self.period.is_finite() && self.period >= 0.0) {
            return Err("stir period is a number of escape steps, or 0 for no swing".into());
        }
        if !(self.largest.is_finite() && self.largest > 0.0 && self.largest <= 1.0) {
            return Err("stir largest is a fraction of the frame's width in (0, 1]".into());
        }
        if !(1..=MAX_STEPS).contains(&self.steps) {
            return Err(format!("stir steps is 1 to {MAX_STEPS}"));
        }
        Ok(())
    }
}

/// The natural logarithm of a positive, finite, normal `x`, by arithmetic alone:
/// `x = m·2^e` with `m` in `(√½, √2]`, and `ln m = 2·atanh((m − 1)/(m + 1))` by its
/// series, to about an ulp. See [`Stirring`] for why the stir has its own.
fn ln(x: f64) -> f64 {
    let bits = x.to_bits();
    let mut exponent = ((bits >> 52) & 0x7ff) as i64 - 1023;
    let mut mantissa = f64::from_bits((bits & 0x000f_ffff_ffff_ffff) | 0x3ff0_0000_0000_0000);
    if mantissa > std::f64::consts::SQRT_2 {
        mantissa *= 0.5;
        exponent += 1;
    }
    let s = (mantissa - 1.0) / (mantissa + 1.0);
    let s2 = s * s;
    // Σ s^2k / (2k + 1), k = 11 down to 0: |s| is under 0.172, so the next term is
    // under 1e-18.
    let mut series = 0.0;
    for k in (0..12).rev() {
        series = series * s2 + 1.0 / (2 * k + 1) as f64;
    }
    2.0 * s * series + exponent as f64 * std::f64::consts::LN_2
}

/// `(cos, sin)` of `turns` whole turns, by arithmetic alone: the turn folded into an
/// eighth, and the two Taylor series there, to about an ulp.
pub(crate) fn cos_sin(turns: f64) -> (f64, f64) {
    // A turn a hair under a whole one rounds up to it: that is no turn.
    let fraction = turns - turns.floor();
    let quarters = if fraction < 1.0 { 4.0 * fraction } else { 0.0 };
    let quadrant = quarters.floor();
    let part = quarters - quadrant;
    // Within a quarter turn, the half nearer the axis: `x` is at most π/4.
    let (near, swapped) = match part > 0.5 {
        true => (1.0 - part, true),
        false => (part, false),
    };
    let x = near * std::f64::consts::FRAC_PI_2;
    let x2 = x * x;
    // sin x / x and cos x, each as Σ (−x²)^k / n! down from x^18: the next term is
    // under 1e-19.
    let (mut sine, mut cosine) = (0.0, 0.0);
    for k in (0..10).rev() {
        let n = (2 * k) as f64;
        sine = 1.0 - sine * x2 / ((n + 2.0) * (n + 3.0));
        cosine = 1.0 - cosine * x2 / ((n + 1.0) * (n + 2.0));
    }
    let sine = sine * x;
    let (c, s) = match swapped {
        true => (sine, cosine),
        false => (cosine, sine),
    };
    match quadrant as i64 {
        0 => (c, s),
        1 => (-s, c),
        2 => (-c, -s),
        _ => (s, -c),
    }
}

/// One pass made ready for a frame.
struct Pass {
    stir: Stir,
    /// The family the copy's loop runs, and what it asks for.
    family: Family,
    wants: Wants,
    /// `zoom·e^(i·turn)`: the frame's offset from its centre, as the copy reads it.
    spin: Complex<f64>,
    /// `e^(i·(angle − turn))`: the copy's uphill direction, as the frame's push.
    turn: Complex<f64>,
    /// `ln` of the copy's escape exponent, which the smooth count divides by.
    log_degree: f64,
}

/// A style's passes made ready for one frame.
///
/// **Every number between the sample's point and the moved point is made by `+`,
/// `−`, `×`, `÷` and `√` alone**, the operations IEEE 754 rounds one way: the smooth
/// count, the distance, the swing and the turn are computed here ([`ln`],
/// [`cos_sin`]) rather than read off [`iterate::Orbit`] or the platform's `sin` and
/// `ln`. Near the copy's set the push changes direction within the distance it
/// moves a point, so several steps of it magnify a difference in the last bit into
/// a different sample; the native engine and `style-wasm` link different maths
/// libraries, whose logarithms and sines agree only to that last bit, and a stir
/// that read them drew a few hundred visibly different samples a frame. Two things
/// still carry a library's last bit into it: a point that reaches the stir through a
/// [`crate::projection`], and a copy of a fractional-degree family, whose every step
/// is the library's `powf` ([`Family::FractionalMultibrot`]).
pub struct Stirring {
    passes: Vec<Pass>,
}

/// `ln` of the escape radius, `2^16` ([`iterate::BAILOUT`]).
const LOG_BAILOUT: f64 = 16.0 * std::f64::consts::LN_2;

impl Stirring {
    /// `None` for a style that does not stir.
    pub fn of(stirs: &[Stir], family: &Family) -> Option<Stirring> {
        if stirs.is_empty() {
            return None;
        }
        let unit = |degrees: f64| {
            let (cosine, sine) = cos_sin(degrees / 360.0);
            Complex::new(cosine, sine)
        };
        let passes = stirs
            .iter()
            .map(|stir| {
                let moved = stir.view.family(family);
                let wants = Wants {
                    derivative: true,
                    interior: Some(Interior::of(&moved)),
                    ..Wants::default()
                };
                Pass {
                    stir: *stir,
                    family: moved,
                    wants,
                    spin: unit(stir.view.turn) * stir.view.zoom,
                    turn: unit(stir.angle - stir.view.turn),
                    log_degree: ln(moved.escape_exponent()),
                }
            })
            .collect();
        Some(Stirring { passes })
    }

    /// Where the frame's plane point `point` is carried to.
    pub fn moved(&self, frame: &Viewport, maxiter: u32, mut point: Complex<f64>) -> Complex<f64> {
        for pass in &self.passes {
            let stir = &pass.stir;
            let cap = stir.largest * frame.width;
            // [`View::point`], with this pass's own turn.
            let shift = Complex::new(stir.view.shift[0], stir.view.shift[1]) * frame.width;
            let offset = match pass.family.pixel_is_z0() {
                true => shift,
                false => shift + Complex::new(stir.view.c[0], stir.view.c[1]),
            };
            for _ in 0..stir.steps {
                let read = frame.center + pass.spin * (point - frame.center) + offset;
                let orbit = iterate::run(&pass.family, read, maxiter, &pass.wants);
                // On the copy's set, or inside it, nothing pushes: the point stays.
                if !orbit.escaped {
                    break;
                }
                let (z, dz) = (orbit.last, orbit.derivative);
                let (z2, dz2) = (z.norm_sqr(), dz.norm_sqr());
                // The count climbs along `−conj(dz/z)` ([`crate::style::gradient`]),
                // which is `−conj(dz)·z` over a positive number.
                let uphill = -(dz.conj() * z);
                let steepness = uphill.norm_sqr().sqrt();
                if !(z2.is_finite() && z2 > 1.0 && dz2 > 0.0 && steepness > 0.0)
                    || !steepness.is_finite()
                {
                    break;
                }
                let log_z = 0.5 * ln(z2);
                // The distance estimate, `2·|z|·ln|z| / |dz|`; one in the copy's plane
                // is `zoom` times one in the frame's.
                let distance = 2.0 * z2.sqrt() * log_z / dz2.sqrt();
                let length = (distance / stir.view.zoom).min(cap);
                let swing = match stir.period > 0.0 {
                    true => {
                        // The smooth count, as [`iterate::run`] has it.
                        let count = (orbit.iteration + 1) as f64
                            - ln(log_z / LOG_BAILOUT) / pass.log_degree;
                        cos_sin(count / stir.period + stir.phase).1
                    }
                    false => 1.0,
                };
                let push = pass.turn
                    * (uphill / steepness)
                    * (stir.strength / stir.steps as f64 * length * swing);
                if !push.re.is_finite() || !push.im.is_finite() {
                    break;
                }
                point += push;
            }
        }
        point
    }

    /// The stirred sample for one that reads `point` with Jacobian `[dx, dy]` (plane
    /// per sample step, `y` up). With `jacobian`, the stirred map's own, by a forward
    /// difference over half a sample step; without, `None`, at a third of the loops.
    pub fn sample(
        &self,
        frame: &Viewport,
        maxiter: u32,
        point: Complex<f64>,
        steps: [Complex<f64>; 2],
        jacobian: bool,
    ) -> Sample {
        let moved = self.moved(frame, maxiter, point);
        let jacobian = jacobian.then(|| {
            steps.map(|step| (self.moved(frame, maxiter, point + step * 0.5) - moved) * 2.0)
        });
        Sample {
            point: moved,
            jacobian,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn frame() -> Viewport {
        Viewport {
            center: Complex::new(-0.75, 0.25),
            width: 0.6,
            out_width: 48,
            out_height: 30,
            supersample: 1,
        }
    }

    const FAMILY: Family = Family::Multibrot { degree: 2 };

    fn stirring(stir: Stir) -> Stirring {
        stir.validate().unwrap();
        Stirring::of(&[stir], &FAMILY).unwrap()
    }

    fn points(frame: &Viewport) -> impl Iterator<Item = Complex<f64>> + '_ {
        (0..frame.sample_height()).flat_map(move |row| {
            (0..frame.sample_width()).map(move |col| frame.sample_point(col, row))
        })
    }

    #[test]
    fn the_stirs_own_logarithm_and_turn_are_the_librarys_to_a_few_bits() {
        for index in 0..4000 {
            let x = 1.0000001f64.powi(index * index) * (1.0 + index as f64 / 7.0);
            let (own, library) = (ln(x), x.ln());
            assert!(
                (own - library).abs() <= 4.0 * f64::EPSILON * library.abs().max(1.0),
                "ln {x}"
            );
            let turns = index as f64 / 129.7 - 15.0;
            let (cosine, sine) = cos_sin(turns);
            let angle = std::f64::consts::TAU * (turns - turns.floor());
            assert!((cosine - angle.cos()).abs() < 1e-14, "cos of {turns} turns");
            assert!((sine - angle.sin()).abs() < 1e-14, "sin of {turns} turns");
        }
        assert_eq!(cos_sin(0.25), (0.0, 1.0));
        assert_eq!(cos_sin(-0.5), (-1.0, -0.0));
        assert_eq!(cos_sin(-1e-20), (1.0, 0.0));
        assert!((LOG_BAILOUT - iterate::BAILOUT.ln()).abs() < 1e-14);
    }

    #[test]
    fn the_stirs_count_is_the_orbits_smooth_count() {
        // The swing reads a count made here; it is the one the layers band.
        let wants = Wants {
            derivative: true,
            ..Wants::default()
        };
        for point in points(&frame()) {
            let orbit = iterate::run(&FAMILY, point, 200, &wants);
            if !orbit.escaped {
                continue;
            }
            let log_z = 0.5 * ln(orbit.last.norm_sqr());
            let count = (orbit.iteration + 1) as f64 - ln(log_z / LOG_BAILOUT) / ln(2.0);
            assert!((count - orbit.smooth).abs() < 1e-12, "{point}");
        }
    }

    #[test]
    fn a_stir_of_no_strength_is_the_straight_view() {
        let frame = frame();
        let still = stirring(Stir {
            strength: 0.0,
            steps: 3,
            ..Stir::default()
        });
        let step = frame.sample_spacing();
        let steps = [Complex::new(step, 0.0), Complex::new(0.0, step)];
        for point in points(&frame) {
            let sample = still.sample(&frame, 200, point, steps, true);
            assert_eq!(sample.point, point);
            assert!((sample.spacing().unwrap() / step - 1.0).abs() < 1e-9);
        }
    }

    #[test]
    fn a_point_inside_the_set_stays_and_no_push_passes_its_cap() {
        let frame = frame();
        let stir = Stir {
            strength: 2.0,
            largest: 0.02,
            steps: 4,
            ..Stir::default()
        };
        let stirred = stirring(stir);
        let inside = Complex::new(-1.0, 0.0);
        assert_eq!(stirred.moved(&frame, 200, inside), inside);
        let cap = stir.strength * stir.largest * frame.width;
        let mut carried = 0;
        for point in points(&frame) {
            let moved = stirred.moved(&frame, 200, point);
            assert!((moved - point).norm() <= cap * (1.0 + 1e-12), "{point}");
            carried += usize::from(moved != point);
        }
        assert!(carried > 100, "only {carried} samples moved");
    }

    #[test]
    fn a_push_along_the_level_line_keeps_the_copys_own_count() {
        // At angle 90 a small push runs along the copy's level line, so the count it
        // was read off barely moves; the same push at angle 0 climbs it.
        let frame = frame();
        let point = Complex::new(-0.75, 0.42);
        let wants = Wants::default();
        let count = |at: Complex<f64>| iterate::run(&FAMILY, at, 200, &wants).smooth;
        let pushed = |angle: f64| {
            let stir = Stir {
                strength: 0.05,
                angle,
                period: 0.0,
                steps: 4,
                ..Stir::default()
            };
            stirring(stir).moved(&frame, 200, point)
        };
        let (along, up) = (pushed(90.0), pushed(0.0));
        assert!(along != point && up != point);
        let (drift, climb) = (count(along) - count(point), count(up) - count(point));
        assert!(climb > 0.0, "the push at angle 0 climbed {climb}");
        assert!(
            drift.abs() < 0.05 * climb,
            "{drift} along against {climb} up"
        );
    }

    #[test]
    fn a_turned_view_pushes_in_the_frames_own_directions() {
        // A copy turned half round the frame's centre reads the plane mirrored through
        // it, and its push is turned back into the frame: the plain push at the
        // mirrored point, mirrored.
        let frame = Viewport {
            center: Complex::new(-0.5, 0.0),
            ..frame()
        };
        let point = Complex::new(0.1, 0.5);
        let plain = stirring(Stir {
            period: 0.0,
            ..Stir::default()
        });
        let turned = stirring(Stir {
            period: 0.0,
            view: View {
                turn: 180.0,
                ..View::default()
            },
            ..Stir::default()
        });
        // The copy at 180° reads the plane point mirrored through the centre.
        let mirror = |p: Complex<f64>| frame.center * 2.0 - p;
        let want = mirror(plain.moved(&frame, 200, mirror(point)));
        let got = turned.moved(&frame, 200, point);
        assert!((got - want).norm() < 1e-12, "{got} against {want}");
    }

    #[test]
    fn a_stir_that_cannot_draw_is_refused() {
        for bad in [
            r#"{"steps": 0}"#,
            r#"{"steps": 17}"#,
            r#"{"largest": 0}"#,
            r#"{"period": -1}"#,
            r#"{"view": {"zoom": 0}}"#,
        ] {
            let stir: Stir = serde_json::from_str(bad).unwrap();
            assert!(stir.validate().is_err(), "{bad}");
        }
        assert!(serde_json::from_str::<Stir>(r#"{"step": 2}"#).is_err());
        let stir: Stir =
            serde_json::from_str(r#"{"strength": 1.5, "view": {"turn": 40}}"#).unwrap();
        assert!(stir.validate().is_ok());
    }
}
