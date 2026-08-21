//! Where a pixel is, in the plane.
//!
//! A viewport is a center and a width. The height follows from the output
//! aspect ratio, which keeps pixels square — the one geometric property a
//! wallpaper cannot afford to get wrong, because a stretched fractal reads as a
//! badly-drawn one rather than as a differently-framed one.
//!
//! Center and width arrive as **decimal strings** and stay that way in
//! [`crate::spec`]. The string is the identity of a location: two renders are of
//! the same place when their strings match, and `f64` is a lossy view of that
//! identity which will stop being enough the moment deep zoom arrives. Here, at
//! the point where geometry becomes arithmetic, the strings have already been
//! parsed and only the `f64` view remains.

use num_complex::Complex;

/// The rectangle of the plane an image covers, and the grid it is sampled on.
#[derive(Clone, Copy, Debug)]
pub struct Viewport {
    pub center: Complex<f64>,
    /// Width of the view in plane units. Height is derived, never given.
    pub width: f64,
    pub out_width: u32,
    pub out_height: u32,
    /// Linear supersampling factor: each output pixel is sampled `ss × ss` times.
    pub supersample: u32,
}

impl Viewport {
    /// Height of the view in plane units, derived so pixels stay square.
    pub fn plane_height(&self) -> f64 {
        self.width * (self.out_height as f64 / self.out_width as f64)
    }

    /// Plane-space size of one output pixel.
    pub fn pixel_size(&self) -> f64 {
        self.width / self.out_width as f64
    }

    /// Plane-space distance between neighbouring *samples*.
    ///
    /// This, and not [`pixel_size`](Self::pixel_size), is the grid arithmetic
    /// happens on: a supersampled render forms `supersample` times as many
    /// coordinates across the same width, and it is the finest grid that runs
    /// out of `f64` first.
    pub fn sample_spacing(&self) -> f64 {
        self.width / self.sample_width() as f64
    }

    /// Width of the supersampled grid.
    pub fn sample_width(&self) -> u32 {
        self.out_width * self.supersample
    }

    /// Height of the supersampled grid.
    pub fn sample_height(&self) -> u32 {
        self.out_height * self.supersample
    }

    /// The plane coordinate at the center of sample cell `(col, row)` of the
    /// supersampled grid.
    ///
    /// Row 0 is the top of the image and therefore the *largest* imaginary part,
    /// which is why the vertical term is subtracted rather than added.
    pub fn sample_point(&self, col: u32, row: u32) -> Complex<f64> {
        let across = (col as f64 + 0.5) / self.sample_width() as f64 - 0.5;
        let down = 0.5 - (row as f64 + 0.5) / self.sample_height() as f64;
        Complex::new(
            self.center.re + across * self.width,
            self.center.im + down * self.plane_height(),
        )
    }

    /// The unit of last place of the coordinates this view forms.
    ///
    /// [`sample_point`](Self::sample_point) forms an *absolute* coordinate —
    /// `center + across * width` — so what a sample position is rounded to is
    /// the spacing of `f64` at the magnitude of that sum, not at the magnitude
    /// of the offset. The reach of the frame is used rather than the center, so
    /// a frame straddling a binade is measured at its coarser end.
    pub fn coordinate_ulp(&self) -> f64 {
        let reach = (self.center.re.abs() + self.width.abs() / 2.0)
            .max(self.center.im.abs() + self.plane_height().abs() / 2.0);
        ulp(reach)
    }

    /// How many representable numbers one sample step spans.
    ///
    /// The whole of the `f64` question in one figure: below `1` two
    /// neighbouring sample centers are the same number.
    pub fn resolution_ulps(&self) -> f64 {
        let step = self.sample_spacing();
        if !step.is_finite() || step <= 0.0 {
            return 0.0;
        }
        step / self.coordinate_ulp()
    }

    /// Whether `f64` still resolves this view.
    ///
    /// **The limit is relative, and it used to be enforced as an absolute
    /// constant.** The refusal read `pixel_size() > 1e-13`, which is a spacing
    /// compared against a number that is only the right one when the
    /// coordinates are of order one — and it read the *output* pixel, so a
    /// supersampled render was judged on a grid four times coarser than the one
    /// it samples. Both are fixed here: the question is asked of the sample
    /// grid, against the coordinates' own unit of last place.
    ///
    /// The old constant was measured and is conservative by 2.05–3.26 decades
    /// depending on the center's magnitude — at release geometry it refused
    /// width `2.56e-10` while adjacent sample centers first collide between
    /// `1.42e-13` and `2.27e-12`. Nothing below it was ever drawn wrong; a great
    /// deal above the real wall was simply refused.
    ///
    /// **What this guards is COORDINATE REPRESENTABILITY, and nothing else.** A
    /// true answer here says two neighbouring sample centers are still two
    /// numbers. It says nothing about the escape count computed from either,
    /// and there is a second wall — the *fidelity* wall — two to eight decades
    /// above this one that it does not guard and cannot cheaply detect: `f64`
    /// carries about `1e-16`, a few thousand iterations of a stretching map
    /// spend it, and the count that comes back is not the value at that point.
    /// Measured against 50-digit orbits from the same starting `f64`
    /// coordinate, escape counts pass 1% disagreement anywhere from `1e-4` to
    /// `1e-10` depending on the case — worst where the orbits linger near the
    /// boundary, which is a property of the center and not of the degree: a
    /// degree-2 mandelbrot node on a period-198 nucleus is 2.3% wrong at
    /// `1e-5`. Callers wanting depth policy read
    /// `fractal_wallpapers.deep.depth`, whose floor is an aesthetic one; this
    /// refusal is not it.
    pub fn is_resolvable_in_f64(&self) -> bool {
        self.resolution_ulps() >= RESOLUTION_ULPS
    }
}

/// Representable numbers one sample step must span for a view to be drawn.
///
/// **One is where the wall physically is** — a step of a single unit of last
/// place means two neighbouring sample centers round to the same coordinate and
/// the picture is of the arithmetic rather than of the set. Four is that with
/// two bits of headroom, so every sample center is placed to within an eighth
/// of a step and the sampling stays even rather than merely distinct.
///
/// It is deliberately small. The rail this replaced was so far above the wall
/// that it decided which views existed; this one only refuses what `f64` cannot
/// draw, and how deep a search may go is a policy its own caller sets — the
/// walk's `gates.min_width`, and the deep mode's own floor.
pub const RESOLUTION_ULPS: f64 = 4.0;

/// The distance from `value` to the next representable `f64` above it.
///
/// Zero and the subnormals answer with the smallest positive `f64`, which is
/// their true spacing; a non-finite magnitude has no spacing and answers with
/// one, so a caller dividing by it gets a refusal rather than an infinity.
fn ulp(value: f64) -> f64 {
    let value = value.abs();
    if !value.is_finite() {
        return 1.0;
    }
    let next = f64::from_bits(value.to_bits() + 1);
    next - value
}

#[cfg(test)]
mod tests {
    use super::*;

    fn viewport() -> Viewport {
        Viewport {
            center: Complex::new(0.0, 0.0),
            width: 4.0,
            out_width: 4,
            out_height: 2,
            supersample: 1,
        }
    }

    #[test]
    fn pixels_are_square() {
        let view = viewport();
        assert_eq!(view.plane_height(), 2.0);
        assert_eq!(
            view.pixel_size(),
            view.plane_height() / view.out_height as f64
        );
    }

    #[test]
    fn the_grid_is_centered_and_the_top_row_is_the_largest_imaginary_part() {
        let view = viewport();
        let top_left = view.sample_point(0, 0);
        let bottom_right = view.sample_point(3, 1);
        assert_eq!(top_left, Complex::new(-1.5, 0.5));
        assert_eq!(bottom_right, Complex::new(1.5, -0.5));
    }

    /// A view at the geometry a release picture is drawn at.
    fn release(center: Complex<f64>, width: f64) -> Viewport {
        Viewport {
            center,
            width,
            out_width: 2560,
            out_height: 1440,
            supersample: 4,
        }
    }

    /// The width at which neighbouring sample centers first round together,
    /// found the way the deep probe found it: by bisection on the samples
    /// themselves, with no reference to the rule under test.
    fn measured_collision_width(center: Complex<f64>) -> f64 {
        let collides = |width: f64| {
            let view = release(center, width);
            let middle = view.sample_width() / 2;
            view.sample_point(middle, 0).re == view.sample_point(middle + 1, 0).re
        };
        // Bisect in the log, so the bracket closes on a ratio rather than on a
        // difference — the answer spans four decades across these centers.
        let (mut low, mut high) = (1e-16f64, 1e-6f64);
        for _ in 0..120 {
            let probe = (low * high).sqrt();
            if collides(probe) {
                low = probe;
            } else {
                high = probe;
            }
        }
        high
    }

    /// The narrowest width the rule under test still draws, bisected the same
    /// way, so the two boundaries are found by the same method.
    fn refusal_boundary(center: Complex<f64>) -> f64 {
        let (mut low, mut high) = (1e-16f64, 1e-6f64);
        for _ in 0..120 {
            let probe = (low * high).sqrt();
            if release(center, probe).is_resolvable_in_f64() {
                high = probe;
            } else {
                low = probe;
            }
        }
        high
    }

    #[test]
    fn the_wall_is_where_neighbouring_samples_stop_being_distinct() {
        // Four magnitudes, spanning the binades a c-plane location lives in.
        // The claim is not a width — it is that the refusal sits a small,
        // *constant* multiple above where the samples actually collide, at
        // every one of them. A rule that were secretly absolute would show a
        // headroom moving with the magnitude instead.
        for center in [
            Complex::new(0.081, 0.0),
            Complex::new(0.233, 0.0),
            Complex::new(0.749, 0.0),
            Complex::new(1.0, 0.0),
        ] {
            let collision = measured_collision_width(center);
            assert!(
                !release(center, collision).is_resolvable_in_f64(),
                "{center} collides at {collision:e} and must be refused there",
            );
            let headroom = refusal_boundary(center) / collision;
            // Adjacent centers round together at somewhere between a third and
            // a half of a unit of last place, depending where in the binade the
            // coordinates sit, so `RESOLUTION_ULPS` of headroom reads as 8-12x
            // of width. The band is the measurement's own spread, not a slack.
            assert!(
                (6.0..=16.0).contains(&headroom),
                "{center}: refusal sits {headroom:.1}x above the collision",
            );
        }
    }

    #[test]
    fn the_limit_is_relative_and_not_a_constant_width() {
        // Same geometry, same width, four times the coordinate magnitude: the
        // old absolute rule could not tell these apart and this one must.
        let width = 6e-12;
        assert!(release(Complex::new(0.2, 0.0), width).is_resolvable_in_f64());
        assert!(!release(Complex::new(1.6, 0.0), width).is_resolvable_in_f64());
    }

    #[test]
    fn supersampling_is_what_runs_out_of_f64_first() {
        // The refusal used to read the output pixel and so ignored this
        // entirely: sixteen times the samples over one width is a grid four
        // times finer, and it is the grid the arithmetic happens on.
        let plain = Viewport {
            supersample: 1,
            ..release(Complex::new(1.0, 0.0), 6e-12)
        };
        assert!(plain.is_resolvable_in_f64());
        assert!(!release(Complex::new(1.0, 0.0), 6e-12).is_resolvable_in_f64());
        assert_eq!(plain.sample_spacing(), plain.pixel_size());
    }

    #[test]
    fn a_view_at_the_origin_is_limited_by_its_own_reach() {
        // Nothing absolute about the wall: at the origin the coordinates are
        // themselves tiny, and `f64` resolves a frame far below any fixed floor.
        let view = release(Complex::new(0.0, 0.0), 1e-30);
        assert!(view.is_resolvable_in_f64());
        assert!(view.resolution_ulps() > 1e9);
    }

    #[test]
    fn supersampling_subdivides_the_same_rectangle() {
        let mut view = viewport();
        view.supersample = 2;
        assert_eq!(view.sample_width(), 8);
        // The outermost sample sits half a *sub*-cell inside the same edge.
        assert!((view.sample_point(0, 0).re - -1.75).abs() < 1e-12);
        assert!((view.sample_point(7, 3).re - 1.75).abs() < 1e-12);
    }
}
