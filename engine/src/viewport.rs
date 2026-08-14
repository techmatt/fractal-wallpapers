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

    /// Whether `f64` still resolves this view.
    ///
    /// Below roughly `1e-13` of the coordinates' own magnitude, neighbouring
    /// pixel centers round to the same `f64` and the render quietly becomes a
    /// picture of floating-point spacing instead of a picture of the set. The
    /// engine refuses rather than draws that.
    pub fn is_resolvable_in_f64(&self) -> bool {
        self.pixel_size() > 1e-13
    }
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
