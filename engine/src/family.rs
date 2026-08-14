//! The five families: what each recurrence is, and how a pixel enters it.
//!
//! A family answers three questions and nothing else:
//!
//!  * [`seed`](Family::seed) — where does the orbit start, and what is the fixed
//!    constant? Parameter-plane families read the pixel as the constant `c` and
//!    start at `z = 0`; dynamical families fix `c` and start at `z = pixel`.
//!  * [`step`](Family::step) — one application of the recurrence.
//!  * [`degree`](Family::degree) — the exponent that dominates escape, which is
//!    the base of the outer logarithm in the smooth iteration count.
//!
//! The escape loop itself lives in [`crate::iterate`] and is written once.

use num_complex::Complex;

/// The Phoenix additive constant of the classic Ushiki instance.
pub const PHOENIX_C: Complex<f64> = Complex::new(0.5667, 0.0);
/// The Phoenix `z_{n-1}` coefficient of the classic Ushiki instance.
pub const PHOENIX_P: Complex<f64> = Complex::new(-0.5, 0.0);

/// One escape-time family.
///
/// [`Multibrot`](Family::Multibrot) at degree 2 *is* the Mandelbrot set, and
/// [`Julia`](Family::Julia) at degree 2 is its classic dynamical twin, so the
/// two-plus-three families the spec names collapse to three recurrences here.
/// The spec keeps `mandelbrot` as a name because that is what the thing is
/// called; the engine keeps one code path because that is what it is.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Family {
    /// `z ← z^d + c`, `z₀ = 0`, `c` = the pixel. The parameter plane: each pixel
    /// asks a different question of the same starting point.
    Multibrot { degree: u32 },
    /// `z ← z^d + c`, `z₀` = the pixel, `c` fixed. The dynamical plane: every
    /// pixel asks the same question from a different starting point.
    Julia { degree: u32, c: Complex<f64> },
    /// Ushiki's Phoenix: `z_{n+1} = z_n² + c + p·z_{n-1}`, `z₀` = the pixel and
    /// `z₋₁` fixed. A dynamical plane with one step of memory, which is what
    /// gives it the flame-like strands the quadratic families cannot make.
    ///
    /// `p = 0` erases the memory term and leaves `z² + c` — a quadratic Julia
    /// set — which is the property `iterate::tests` pins.
    Phoenix {
        c: Complex<f64>,
        p: Complex<f64>,
        /// The `z₋₁` the orbit starts with. Zero is the classic slice; anything
        /// else is a different set from the same `(c, p)`.
        z_prev: Complex<f64>,
    },
}

/// The orbit's initial state: `(z₀, z₋₁, c)`.
///
/// `z₋₁` is meaningful only to Phoenix; the memoryless families report zero and
/// never read it back.
pub type Seed = (Complex<f64>, Complex<f64>, Complex<f64>);

impl Family {
    /// Start the orbit for one point of the viewport.
    pub fn seed(&self, pixel: Complex<f64>) -> Seed {
        let zero = Complex::new(0.0, 0.0);
        match *self {
            Family::Multibrot { .. } => (zero, zero, pixel),
            Family::Julia { c, .. } => (pixel, zero, c),
            Family::Phoenix { c, z_prev, .. } => (pixel, z_prev, c),
        }
    }

    /// One step of the recurrence: `(z_n, z_{n-1}, c) → z_{n+1}`.
    pub fn step(&self, z: Complex<f64>, z_prev: Complex<f64>, c: Complex<f64>) -> Complex<f64> {
        match *self {
            Family::Multibrot { degree } | Family::Julia { degree, .. } => cpow(z, degree) + c,
            Family::Phoenix { p, .. } => z * z + c + p * z_prev,
        }
    }

    /// The exponent that governs escape, and so the base of the smooth count's
    /// outer logarithm.
    ///
    /// Phoenix reports 2: once `|z|` is large the quadratic term swamps the
    /// linear memory term `p·z_{n-1}`, so the escape is quadratic even though
    /// the set is not. The memory reshapes which points escape, not how fast the
    /// ones that do run away.
    pub fn degree(&self) -> u32 {
        match *self {
            Family::Multibrot { degree } | Family::Julia { degree, .. } => degree,
            Family::Phoenix { .. } => 2,
        }
    }

    /// Where this family is worth looking first, in the plane it lives in.
    ///
    /// Everything is centered on the origin except the Mandelbrot set, which is
    /// the one family here that is not symmetric about it: its cardioid and the
    /// bulbs behind it sit roughly between `-2` and `0.5`, so a view of the
    /// whole set centers on `-0.5`. The higher multibrots regain that symmetry —
    /// `z^d + c` has `d − 1` fold rotational symmetry about the origin — and the
    /// dynamical planes have it too, since every filled Julia and Phoenix set
    /// surrounds the origin.
    pub fn home_center(&self) -> Complex<f64> {
        match *self {
            Family::Multibrot { degree: 2 } => Complex::new(-0.5, 0.0),
            _ => Complex::new(0.0, 0.0),
        }
    }
}

/// `z^k` for `k ≥ 1` by repeated multiplication.
///
/// Repeated multiplication rather than `powc`: the exponents in play are 2
/// through 5, so this is both faster and exact where a polar round trip is
/// neither. `k = 2` is a single multiply, the case that dominates every render.
fn cpow(z: Complex<f64>, k: u32) -> Complex<f64> {
    let mut acc = z;
    for _ in 1..k {
        acc *= z;
    }
    acc
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cpow_matches_repeated_multiplication() {
        let z = Complex::new(0.3, -0.7);
        assert_eq!(cpow(z, 1), z);
        assert_eq!(cpow(z, 2), z * z);
        assert_eq!(cpow(z, 5), z * z * z * z * z);
    }

    #[test]
    fn parameter_plane_seeds_at_zero_and_dynamical_at_the_pixel() {
        let pixel = Complex::new(0.1, 0.2);
        let c = Complex::new(-0.8, 0.156);

        let (z0, _, cm) = Family::Multibrot { degree: 2 }.seed(pixel);
        assert_eq!(z0, Complex::new(0.0, 0.0));
        assert_eq!(cm, pixel);

        let (z0, _, cj) = Family::Julia { degree: 2, c }.seed(pixel);
        assert_eq!(z0, pixel);
        assert_eq!(cj, c);
    }

    /// Only the Mandelbrot set is off-center; the rest are symmetric about the
    /// origin and are framed there.
    #[test]
    fn only_the_mandelbrot_set_comes_home_off_the_origin() {
        let origin = Complex::new(0.0, 0.0);
        assert_eq!(
            Family::Multibrot { degree: 2 }.home_center(),
            Complex::new(-0.5, 0.0)
        );
        for degree in 3..=5 {
            assert_eq!(Family::Multibrot { degree }.home_center(), origin);
        }
        assert_eq!(
            Family::Julia {
                degree: 2,
                c: origin
            }
            .home_center(),
            origin
        );
        assert_eq!(
            Family::Phoenix {
                c: PHOENIX_C,
                p: PHOENIX_P,
                z_prev: origin
            }
            .home_center(),
            origin
        );
    }

    /// The memory term is the whole of the difference between Phoenix and a
    /// quadratic Julia, so with `p = 0` the two steps must agree exactly.
    #[test]
    fn phoenix_with_zero_p_steps_like_a_quadratic_julia() {
        let c = Complex::new(0.3, -0.1);
        let phoenix = Family::Phoenix {
            c,
            p: Complex::new(0.0, 0.0),
            z_prev: Complex::new(0.9, 0.4),
        };
        let julia = Family::Julia { degree: 2, c };
        let z = Complex::new(0.25, 0.6);
        let z_prev = Complex::new(0.9, 0.4);
        assert_eq!(phoenix.step(z, z_prev, c), julia.step(z, z_prev, c));
    }
}
