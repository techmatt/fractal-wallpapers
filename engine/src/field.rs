//! Field production: run the escape loop over the supersampled grid.
//!
//! This is the expensive stage and the only one that iterates. What it produces
//! — a scalar per sample, `NaN` where the orbit never escaped — is everything a
//! colormap needs. Keeping it as a plain array of `f32` is what makes recoloring
//! cheap later: the answer to "what does this look like in a different palette"
//! costs a pass over memory, not a re-render.

use rayon::prelude::*;

use crate::family::Family;
use crate::iterate;
use crate::viewport::Viewport;

/// A scalar field at supersampled resolution, row-major.
///
/// `NaN` marks a sample whose orbit did not escape. The mask rides inside the
/// data rather than beside it, so a field is one array and cannot be separated
/// from the information about which of its entries mean anything.
pub struct Field {
    pub values: Vec<f32>,
    pub width: u32,
    pub height: u32,
}

impl Field {
    /// Fraction of samples that never escaped.
    pub fn interior_fraction(&self) -> f64 {
        if self.values.is_empty() {
            return 1.0;
        }
        let interior = self.values.iter().filter(|v| !v.is_finite()).count();
        interior as f64 / self.values.len() as f64
    }
}

/// Iterate `family` over every sample of `view` at `maxiter`.
///
/// Rows run in parallel and are collected in order, so the field is identical
/// however the work was scheduled. Determinism here is not a nicety: a render
/// that depends on thread timing cannot be compared against anything, including
/// its own earlier self.
// TODO(perf): the source project's kernel computed only the per-orbit channels
// the active coloring actually reads, selected at compile time. With one channel
// there is nothing to select; revisit when orbit traps and distance estimates
// arrive.
pub fn render_field(view: &Viewport, family: &Family, maxiter: u32) -> Field {
    let width = view.sample_width();
    let height = view.sample_height();

    let rows: Vec<Vec<f32>> = (0..height)
        .into_par_iter()
        .map(|row| {
            (0..width)
                .map(|col| {
                    let point = view.sample_point(col, row);
                    iterate::escape(family, point, maxiter).smooth as f32
                })
                .collect()
        })
        .collect();

    Field {
        values: rows.concat(),
        width,
        height,
    }
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

    #[test]
    fn the_field_has_one_value_per_sample() {
        let view = whole_set_view(2);
        let field = render_field(&view, &Family::Multibrot { degree: 2 }, 200);
        assert_eq!(field.width, 64);
        assert_eq!(field.height, 36);
        assert_eq!(field.values.len(), 64 * 36);
    }

    #[test]
    fn a_view_of_the_whole_set_holds_both_interior_and_exterior() {
        let field = render_field(&whole_set_view(1), &Family::Multibrot { degree: 2 }, 400);
        let interior = field.interior_fraction();
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
        let coarse = render_field(&whole_set_view(1), &family, 400).interior_fraction();
        let fine = render_field(&whole_set_view(4), &family, 400).interior_fraction();
        assert!((coarse - fine).abs() < 0.02, "{coarse} vs {fine}");
    }
}
