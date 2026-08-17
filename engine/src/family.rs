//! The five families: what each recurrence is, and how a pixel enters it.
//!
//! A family answers four questions and nothing else:
//!
//!  * [`seed`](Family::seed) — where does the orbit start, and what is the fixed
//!    constant? Parameter-plane families read the pixel as the constant `c` and
//!    start at `z = 0`; dynamical families fix `c` and start at `z = pixel`.
//!  * [`step`](Family::step) — one application of the recurrence.
//!  * [`degree`](Family::degree) — the exponent that dominates escape, which is
//!    the base of the outer logarithm in the smooth iteration count.
//!  * [`derivative_seed`](Family::derivative_seed) and
//!    [`derivative_step`](Family::derivative_step) — the same recurrence
//!    differentiated with respect to the pixel, which is what the distance
//!    estimate reads. One question, asked in two halves for the same reason the
//!    orbit is: where it starts, and how it advances.
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

/// A view of the whole plane a dynamical set lives in.
///
/// Three units across on the origin. This is the **exception**, not the rule:
/// the one family that gets it is [`Family::Julia`], whose set is a different
/// shape for every `c`, so no one frame contains every member and there is
/// nothing to derive a row from. See [`Family::measured_extent`].
const WHOLE_PLANE: HomeView = HomeView {
    center: Complex::new(0.0, 0.0),
    width: 3.0,
};

/// Samples per axis of the grid every filled set below was measured on.
pub const MEASURE_GRID: u32 = 4001;

/// Half-span of that grid: it covers `[−2.5, 2.5]` on both axes, and includes
/// them, so a set's needle on an axis is not missed between two samples.
pub const MEASURE_HALF_SPAN: f64 = 2.5;

/// Iteration cap the measurement ran at. A "filled set" here is what a render at
/// this cap paints as interior, which is the thing a frame has to hold — not the
/// mathematical set, which no finite loop can produce.
pub const MEASURE_CAP: u32 = 4000;

/// Slack a home frame carries beyond the set, as a share of the set's own extent
/// on whichever axis decided the frame. One constant, shared by every row.
pub const HOME_MARGIN: f64 = 0.10;

/// The output aspect every home view is composed for. A frame is specified by
/// its width, so a set that is tall for its width has to buy the height.
pub const HOME_ASPECT: f64 = 16.0 / 9.0;

/// The measured bounding box of one family's filled set, as `(low, high)` per
/// axis — the raw input the family's home-view row is derived from.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Extent {
    pub re: (f64, f64),
    pub im: (f64, f64),
}

impl Extent {
    /// The set's own centre: the midpoint of the box, so whatever margin the
    /// frame has is spread evenly rather than piled on one side.
    pub fn center(&self) -> Complex<f64> {
        Complex::new(0.5 * (self.re.0 + self.re.1), 0.5 * (self.im.0 + self.im.1))
    }

    pub fn width(&self) -> f64 {
        self.re.1 - self.re.0
    }

    pub fn height(&self) -> f64 {
        self.im.1 - self.im.0
    }

    /// **The rule**, and there is only one of it.
    ///
    /// A frame is specified by its width, so both axes are expressed as the
    /// width they demand: the set's own width, and the width a 16:9 frame needs
    /// in order to be tall enough. The larger of the two decides the frame, and
    /// [`HOME_MARGIN`] of that is added so the set does not touch the edge.
    ///
    /// The two roundings at the end are for the reader, and both are safe:
    /// the width is rounded **up** to a tenth of a unit, which only ever adds
    /// margin, and the centre to a hundredth, which moves it by at most 0.005
    /// against a margin measured in tenths.
    pub fn frame(&self) -> HomeView {
        let demanded = self.width().max(self.height() * HOME_ASPECT);
        let center = self.center();
        HomeView {
            center: Complex::new(round_to_hundredth(center.re), round_to_hundredth(center.im)),
            width: ((demanded * (1.0 + HOME_MARGIN)) * 10.0).ceil() / 10.0,
        }
    }
}

fn round_to_hundredth(value: f64) -> f64 {
    (value * 100.0).round() / 100.0
}

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

/// The classic Ushiki instance in full: what `{"kind": "phoenix"}` alone means,
/// and the instance the Phoenix row of the home table was measured on.
pub const CLASSIC_PHOENIX: Family = Family::Phoenix {
    c: PHOENIX_C,
    p: PHOENIX_P,
    z_prev: Complex::new(0.0, 0.0),
};

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

    /// Whether the pixel is `z₀` — the dynamical planes — rather than `c`.
    ///
    /// The same split [`seed`](Family::seed) and
    /// [`derivative_seed`](Family::derivative_seed) already turn on, asked as a
    /// question so a caller that needs to know which plane it is on reads it here
    /// instead of matching the families over again and forgetting Phoenix.
    pub fn pixel_is_z0(&self) -> bool {
        match *self {
            Family::Multibrot { .. } => false,
            Family::Julia { .. } | Family::Phoenix { .. } => true,
        }
    }

    /// One step of the recurrence: `(z_n, z_{n-1}, c) → z_{n+1}`.
    pub fn step(&self, z: Complex<f64>, z_prev: Complex<f64>, c: Complex<f64>) -> Complex<f64> {
        match *self {
            Family::Multibrot { degree } | Family::Julia { degree, .. } => cpow(z, degree) + c,
            Family::Phoenix { p, .. } => z * z + c + p * z_prev,
        }
    }

    /// The derivative's initial state: `(dz₀, dz₋₁)`, differentiated with
    /// respect to whichever quantity the pixel *is*.
    ///
    /// That is the whole subtlety of the derivative recurrence, and it is why it
    /// lives beside [`seed`](Family::seed) rather than in the loop: a
    /// parameter-plane family differentiates by `c`, and `z₀ = 0` does not depend
    /// on `c`, so it opens at zero. A dynamical family differentiates by `z₀`,
    /// which *is* the pixel, so it opens at one. Get the two the wrong way round
    /// and the distance estimate is off by a whole term everywhere.
    pub fn derivative_seed(&self) -> (Complex<f64>, Complex<f64>) {
        let (zero, one) = (Complex::new(0.0, 0.0), Complex::new(1.0, 0.0));
        match *self {
            Family::Multibrot { .. } => (zero, zero),
            Family::Julia { .. } => (one, zero),
            Family::Phoenix { .. } => (one, zero),
        }
    }

    /// One step of the derivative recurrence, differentiated term by term from
    /// [`step`](Family::step): `(z_n, dz_n, dz_{n-1}) → dz_{n+1}`.
    ///
    /// * `z^d + c` by `c`  → `d·z^{d−1}·dz + 1`
    /// * `z^d + c` by `z₀` → `d·z^{d−1}·dz`
    /// * `z² + c + p·z_{n−1}` by `z₀` → `2·z·dz + p·dz_{n−1}`
    ///
    /// The `+1` is the parameter plane's alone, and Phoenix is the one family
    /// whose derivative needs its own memory term — which is why this takes two
    /// steps of history exactly as `step` does.
    pub fn derivative_step(
        &self,
        z: Complex<f64>,
        dz: Complex<f64>,
        dz_prev: Complex<f64>,
    ) -> Complex<f64> {
        match *self {
            Family::Multibrot { degree } => {
                Complex::new(degree as f64, 0.0) * cpow(z, degree - 1) * dz + 1.0
            }
            Family::Julia { degree, .. } => {
                Complex::new(degree as f64, 0.0) * cpow(z, degree - 1) * dz
            }
            Family::Phoenix { p, .. } => 2.0 * z * dz + p * dz_prev,
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

    /// What this family's filled set was measured to span, or `None` for the
    /// one family that cannot be measured.
    ///
    /// These five boxes are the **only** framing numbers in the engine. They are
    /// measurements, not choices: a `MEASURE_GRID`² grid over `±MEASURE_HALF_SPAN`
    /// at a cap of [`MEASURE_CAP`], and a sample counts as filled when its orbit
    /// has not left the bailout disc by the cap.
    ///
    /// | family | re | im | exact 16:9 width | the row it derives to |
    /// |---|---|---|---|---|
    /// | mandelbrot | [−2.000, 0.453] | ±1.100 | 3.91 | (−0.77, 0) w 4.4 |
    /// | multibrot d=3 | ±0.701 | ±1.323 | 4.70 | (0, 0) w 5.2 |
    /// | multibrot d=4 | [−1.259, 0.801] | ±1.116 | 3.97 | (−0.23, 0) w 4.4 |
    /// | multibrot d=5 | ±0.914 | ±0.914 | 3.25 | (0, 0) w 3.6 |
    /// | phoenix classic | [−0.679, 0.755] | ±1.271 | 4.52 | (0.04, 0) w 5.0 |
    ///
    /// Two of those numbers surprise. The Mandelbrot set reaches `re = 0.453`,
    /// well right of the main cardioid's rightmost point at `0.375`: a symmetric
    /// pair of components sits out at `0.44 ± 0.375i`, ~2 900 grid samples of it,
    /// and they are still filled at a cap of 2 × 10⁷. And **every one of the five
    /// is taller than a 16:9 frame three units wide** — every width in the fourth
    /// column is height-driven — so the whole-plane framing clipped all of them,
    /// not only Phoenix.
    ///
    /// Julia is the exception and stays one: its set is a different shape for
    /// every `c`, so there is no set to measure and no containing frame to
    /// derive. It comes home to [`WHOLE_PLANE`] by that stated exception rather
    /// than by the rule. A degree outside the supported range is refused at the
    /// spec, and reported here as unmeasured rather than guessed at.
    ///
    /// Phoenix's box is the **classic Ushiki instance**, which is what
    /// `{"kind": "phoenix"}` alone means, and every Phoenix shares its row. That
    /// is not the Julia case: Phoenix has a canonical instance to measure and
    /// Julia has none, and a home view is where a picture of the family starts,
    /// not a claim about every point of its parameter space.
    pub fn measured_extent(&self) -> Option<Extent> {
        let at = |re: (f64, f64), im: (f64, f64)| Some(Extent { re, im });
        match *self {
            Family::Multibrot { degree: 2 } => at((-2.0, 0.4525), (-1.1, 1.1)),
            Family::Multibrot { degree: 3 } => at((-0.70125, 0.70125), (-1.3225, 1.3225)),
            Family::Multibrot { degree: 4 } => at((-1.25875, 0.80125), (-1.11625, 1.11625)),
            Family::Multibrot { degree: 5 } => at((-0.91375, 0.91375), (-0.91375, 0.91375)),
            Family::Multibrot { .. } => None,
            Family::Julia { .. } => None,
            Family::Phoenix { .. } => at((-0.67875, 0.755), (-1.27125, 1.27125)),
        }
    }

    /// Where this family is worth looking first, and how wide.
    ///
    /// The whole of what "no viewport given" means — for a hand-run `render`,
    /// for a family's own picture in the article, and for a walk root that was
    /// given a family and no place to start. **This function is the single owner
    /// of that framing**: the discovery half reads it through
    /// `fractal-engine home-view` rather than keeping a literal of its own, so
    /// there is one table and it cannot drift.
    ///
    /// Nothing here is a taste call. Every row is [`Extent::frame`] evaluated on
    /// [`Family::measured_extent`] — one rule, one margin, re-derived per family
    /// — and the one family with nothing to measure is framed by a stated
    /// exception instead. The textbook Mandelbrot view `(−0.5, 3.0)` does not
    /// survive that: it is a choice, it clips the set at 16:9, and the rule
    /// replaces it with `(−0.77, 4.4)`.
    pub fn home_view(&self) -> HomeView {
        match self.measured_extent() {
            Some(extent) => extent.frame(),
            None => WHOLE_PLANE,
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

    /// The plane question and the seed have to agree, because a caller reads the
    /// question and then assumes the seed: `pixel_is_z0` is true exactly where
    /// `seed` hands the pixel back as `z₀`.
    #[test]
    fn the_plane_question_answers_what_the_seed_does() {
        let pixel = Complex::new(0.1, 0.2);
        for family in [
            Family::Multibrot { degree: 2 },
            Family::Multibrot { degree: 5 },
            Family::Julia {
                degree: 2,
                c: Complex::new(-0.8, 0.156),
            },
            CLASSIC_PHOENIX,
        ] {
            let (z0, ..) = family.seed(pixel);
            assert_eq!(family.pixel_is_z0(), z0 == pixel, "{family:?}");
        }
    }

    /// Every family whose set can be measured, so a test can say "each of these"
    /// once and mean the whole table.
    fn derivable() -> Vec<(&'static str, Family)> {
        vec![
            ("mandelbrot", Family::Multibrot { degree: 2 }),
            ("multibrot3", Family::Multibrot { degree: 3 }),
            ("multibrot4", Family::Multibrot { degree: 4 }),
            ("multibrot5", Family::Multibrot { degree: 5 }),
            ("phoenix", CLASSIC_PHOENIX),
        ]
    }

    /// The home table, row by row — and the whole point of the table is that
    /// nothing in it was chosen. Each row is the rule evaluated on that family's
    /// measured box, so this test recomputes it rather than restating it.
    #[test]
    fn each_family_comes_home_to_the_rule_evaluated_on_its_own_set() {
        for (name, family) in derivable() {
            let extent = family.measured_extent().expect("a derivable family");
            assert_eq!(family.home_view(), extent.frame(), "{name}");
        }
        // The values the rule lands on, written down once so a change to the
        // rule cannot pass unnoticed as a change to nothing.
        let rows = [
            ("mandelbrot", -0.77, 4.4),
            ("multibrot3", 0.0, 5.2),
            ("multibrot4", -0.23, 4.4),
            ("multibrot5", 0.0, 3.6),
            ("phoenix", 0.04, 5.0),
        ];
        for ((name, family), (_, center_re, width)) in derivable().into_iter().zip(rows) {
            let home = family.home_view();
            assert_eq!(home.center, Complex::new(center_re, 0.0), "{name}");
            assert_eq!(home.width, width, "{name}");
        }
    }

    /// The textbook Mandelbrot view is an inherited choice, and the derivation
    /// does not reproduce it: three units across at 16:9 is 1.69 tall, and the
    /// set is 2.2. Pinned so the row cannot quietly revert to the familiar one.
    #[test]
    fn the_mandelbrot_row_is_derived_rather_than_textbook() {
        let home = Family::Multibrot { degree: 2 }.home_view();
        assert_ne!(home.center, Complex::new(-0.5, 0.0));
        assert_ne!(home.width, WHOLE_PLANE.width);
        assert!(home.width * 9.0 / 16.0 > 2.2, "it has to hold the set");
    }

    /// Julia's row is the one exception, and it is an exception about the
    /// *family*, not about a particular `c`: no single frame contains every
    /// member, so there is nothing to measure and nothing to derive.
    #[test]
    fn julia_comes_home_to_the_whole_plane_by_exception() {
        for c in [Complex::new(0.0, 0.0), Complex::new(-0.4, 0.6)] {
            let family = Family::Julia { degree: 2, c };
            assert_eq!(family.measured_extent(), None);
            assert_eq!(family.home_view(), WHOLE_PLANE);
        }
    }

    /// The generalized containment test: **re-measure, never trust the
    /// constant.** For every derivable family the filled set is found again from
    /// the recurrence, and the home frame must hold all of it at 16:9 with real
    /// margin on the axis that decided the frame.
    ///
    /// The grid is coarse enough to run in a debug build, so it finds slightly
    /// less of each set than the derivation's did — which is checked too, in
    /// both directions: a recorded box the recurrence disagrees with is the one
    /// way this table could be wrong without any frame looking wrong.
    #[test]
    fn every_derivable_family_still_frames_the_set_its_recurrence_makes() {
        let steps = 300;
        let span = 2.0 * MEASURE_HALF_SPAN;
        let grid_step = span / steps as f64;
        for (name, family) in derivable() {
            let home = family.home_view();
            let recorded = family.measured_extent().expect("a derivable family");
            let half_width = home.width / 2.0;
            let half_height = home.width * 9.0 / 16.0 / 2.0;

            let (mut widest, mut tallest) = (0.0f64, 0.0f64);
            let (mut re_span, mut im_span) = (0.0f64, 0.0f64);
            for row in 0..=steps {
                let im = -MEASURE_HALF_SPAN + span * row as f64 / steps as f64;
                for col in 0..=steps {
                    let re = -MEASURE_HALF_SPAN + span * col as f64 / steps as f64;
                    if crate::iterate::escape(&family, Complex::new(re, im), 500).escaped {
                        continue;
                    }
                    widest = widest.max((re - home.center.re).abs());
                    tallest = tallest.max((im - home.center.im).abs());
                    re_span = re_span.max(re.abs());
                    im_span = im_span.max(im.abs());
                }
            }

            assert!(tallest > 0.5, "{name}: the search found no set to frame");
            assert!(
                widest < half_width && tallest < half_height,
                "{name}: the set reaches ({widest:.4}, {tallest:.4}) and the frame is \
                 ({half_width:.4}, {half_height:.4})"
            );
            // The width was bought to hold the height, so that is where the
            // margin has to be real rather than a rounding.
            assert!(
                tallest < half_height * 0.95,
                "{name}: no margin — the set reaches {tallest:.4} of {half_height:.4}"
            );
            // And the recorded box is the same set: a coarse grid can only miss
            // the tips, never invent them, so it must land just inside.
            let recorded_re = recorded.re.0.abs().max(recorded.re.1.abs());
            let recorded_im = recorded.im.0.abs().max(recorded.im.1.abs());
            assert!(
                re_span <= recorded_re + grid_step && im_span <= recorded_im + grid_step,
                "{name}: the recurrence reaches ({re_span:.4}, {im_span:.4}), past the \
                 recorded ({recorded_re:.4}, {recorded_im:.4})"
            );
            assert!(
                im_span > 0.85 * recorded_im,
                "{name}: the recorded box claims {recorded_im:.4} of height and the \
                 recurrence finds only {im_span:.4}"
            );
        }
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
