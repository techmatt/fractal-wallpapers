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

/// The frame a render gets when it is told nothing about where to look.
///
/// The same two numbers a viewport is, with the resolution left out: a home view
/// is not a picture, it is where a picture of this family starts.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct HomeView {
    pub center: Complex<f64>,
    /// Width of the view in plane units. The height follows from the output
    /// aspect ratio, which is why a home view for a *tall* set has to be
    /// specified as a width wide enough to buy the height.
    pub width: f64,
}

/// A view of the whole plane the parameter-plane and Julia sets live in.
///
/// Three units across, centered on the set: the framing every family here came
/// home to before there was a table, kept for the four that were framed at it.
const WHOLE_PLANE: f64 = 3.0;

/// Where the classic Phoenix set is framed, and why it is not [`WHOLE_PLANE`].
///
/// Phoenix is the one family here whose set is **taller than it is wide**, and
/// by a long way: measured over a 4001² grid at a cap of 4000, the filled set
/// spans `re ∈ [−0.679, 0.755]` and `im ∈ ±1.271` — 1.43 across and 2.54 tall,
/// an aspect of 0.56 against a 16:9 frame's 1.78. A frame is specified by its
/// width, so at three units across it is 1.69 tall and cuts the top and bottom
/// off both lobes, which is what the first engine slice recorded as a watch item
/// and what this is.
///
/// So the width is derived from the **height** the set needs: `2.54 × 16/9 =
/// 4.52` to contain it exactly, and 5 units to contain it with a tenth of its
/// own height in margin. The center is the set's own, so what is left over is
/// spread evenly rather than piled on one side. `phoenix_comes_home_to_a_frame_
/// that_holds_its_set` re-measures it.
///
/// The consequence is a lot of exterior either side of a narrow flame, and that
/// is what framing a portrait subject in a landscape frame costs. The
/// alternative is not a tighter frame, it is a cropped set.
pub const PHOENIX_HOME: HomeView = HomeView {
    center: Complex::new(0.04, 0.0),
    width: 5.0,
};

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

    /// Where this family is worth looking first, and how wide.
    ///
    /// A table, one row per family, and it is the whole of what "no viewport
    /// given" means. Nothing in production reads it: every render a walk, a tile
    /// build or a curation run makes names its own viewport, so this is the
    /// default framing of a hand-run `render` and of a family's own picture in
    /// the article, and moving a row moves those and nothing else.
    ///
    /// Centers first. Everything is centered on the origin except the Mandelbrot
    /// set, which is the one parameter plane here that is not symmetric about
    /// it: its cardioid and the bulbs behind it sit roughly between `-2` and
    /// `0.5`, so a view of the whole set centers on `-0.5`. The higher
    /// multibrots regain that symmetry — `z^d + c` has `d − 1` fold rotational
    /// symmetry about the origin — and a filled Julia set surrounds the origin
    /// too. Phoenix is centered on its own measured set; see [`PHOENIX_HOME`].
    ///
    /// Widths second, and only Phoenix's is derived. A Julia set's extent
    /// depends on its `c` and no one frame contains every member, so the
    /// dynamical twin comes home to the whole plane and the walk composes from
    /// there. The parameter planes are framed at the same three units they were
    /// framed at before this table existed.
    pub fn home_view(&self) -> HomeView {
        let at = |re, width| HomeView {
            center: Complex::new(re, 0.0),
            width,
        };
        match *self {
            Family::Multibrot { degree: 2 } => at(-0.5, WHOLE_PLANE),
            Family::Multibrot { .. } => at(0.0, WHOLE_PLANE),
            Family::Julia { .. } => at(0.0, WHOLE_PLANE),
            Family::Phoenix { .. } => PHOENIX_HOME,
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

    fn classic_phoenix() -> Family {
        Family::Phoenix {
            c: PHOENIX_C,
            p: PHOENIX_P,
            z_prev: Complex::new(0.0, 0.0),
        }
    }

    /// The home table, row by row. Only the Mandelbrot set is off-center among
    /// the sets that are symmetric about the origin, and only Phoenix is framed
    /// at anything other than the whole plane.
    #[test]
    fn each_family_comes_home_to_its_own_row() {
        let origin = Complex::new(0.0, 0.0);
        let home = Family::Multibrot { degree: 2 }.home_view();
        assert_eq!(home.center, Complex::new(-0.5, 0.0));
        assert_eq!(home.width, WHOLE_PLANE);
        for degree in 3..=5 {
            let home = Family::Multibrot { degree }.home_view();
            assert_eq!(home.center, origin);
            assert_eq!(home.width, WHOLE_PLANE);
        }
        let home = Family::Julia {
            degree: 2,
            c: origin,
        }
        .home_view();
        assert_eq!(home.center, origin);
        assert_eq!(home.width, WHOLE_PLANE);
        assert_eq!(classic_phoenix().home_view(), PHOENIX_HOME);
    }

    /// Phoenix's row is the one that was derived rather than inherited, so it is
    /// the one re-measured here: at 16:9 its home frame must hold every point of
    /// the filled set, with real margin left over on the axis that decided the
    /// frame. The grid is coarse enough to run in a debug build and fine enough
    /// that a frame off by a percent would show.
    #[test]
    fn phoenix_comes_home_to_a_frame_that_holds_its_set() {
        let family = classic_phoenix();
        let home = PHOENIX_HOME;
        let half_width = home.width / 2.0;
        let half_height = home.width * 9.0 / 16.0 / 2.0;

        let (mut widest, mut tallest) = (0.0f64, 0.0f64);
        let steps = 300;
        for row in 0..=steps {
            for col in 0..=steps {
                let re = -2.5 + 5.0 * col as f64 / steps as f64;
                let im = -2.5 + 5.0 * row as f64 / steps as f64;
                if crate::iterate::escape(&family, Complex::new(re, im), 500).escaped {
                    continue;
                }
                widest = widest.max((re - home.center.re).abs());
                tallest = tallest.max((im - home.center.im).abs());
            }
        }
        assert!(tallest > 1.2, "the search found no set to frame");
        assert!(
            widest < half_width && tallest < half_height,
            "the set reaches ({widest:.4}, {tallest:.4}) and the frame is \
             ({half_width:.4}, {half_height:.4})"
        );
        // Height is what decides this frame, so that is where the margin has to
        // be real rather than a rounding.
        assert!(
            tallest < half_height * 0.95,
            "no margin: the set reaches {tallest:.4} of {half_height:.4}"
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
