//! Field → color.
//!
//! A smooth iteration count is not a color and has no natural range: it depends
//! on the family, the zoom depth, and the iteration cap, and its distribution is
//! badly skewed — most of a frame's samples escape early, a thin band near the
//! boundary runs to the cap. Handing raw counts to a colormap gives an image
//! that is one flat color with a hairline of everything else.
//!
//! So the field is normalized against **its own frame** before it is looked up.
//! The stretch reads the 0.5th and 99.5th percentiles of the escaped samples and
//! maps that span to `[0, 1]`. Trimming half a percent from each end costs
//! nothing visible and stops a handful of extreme samples from compressing the
//! rest of the picture into a corner of the gradient.
//!
//! The consequence is that this stage is **not** per-pixel pure: it reads the
//! whole frame before it can color any of it. That is the price of a render that
//! frames itself, and it is why the field, not the color, is the thing worth
//! keeping.

use rayon::prelude::*;

use crate::colormap::Colormap;
use crate::field::Field;

/// Percentile of escaped samples mapped to the bottom of the gradient.
pub const CLIP_LOW: f64 = 0.5;
/// Percentile of escaped samples mapped to the top of the gradient.
pub const CLIP_HIGH: f64 = 99.5;

/// The color interior samples take.
///
/// Black, and deliberately so: the interior is the set itself, and letting it
/// read as negative space is what gives the exterior structure something to be
/// structure *against*. Filling it is a coloring choice this slice does not make.
const INTERIOR: [f64; 3] = [0.0, 0.0, 0.0];

/// A frame's normalization: the span of field values the gradient covers.
#[derive(Clone, Copy, Debug)]
pub struct Stretch {
    low: f64,
    span: f64,
}

impl Stretch {
    /// Measure the stretch over a field's escaped samples.
    ///
    /// A frame with no escaped samples at all — a view entirely inside the set —
    /// gets a degenerate but harmless stretch: everything is interior, so
    /// nothing will be looked up through it.
    pub fn measure(field: &Field) -> Stretch {
        let mut escaped: Vec<f64> = field
            .values
            .iter()
            .filter(|v| v.is_finite())
            .map(|&v| v as f64)
            .collect();
        if escaped.is_empty() {
            return Stretch {
                low: 0.0,
                span: 1.0,
            };
        }
        let low = percentile(&mut escaped, CLIP_LOW);
        let high = percentile(&mut escaped, CLIP_HIGH);
        Stretch {
            low,
            span: if high > low { high - low } else { 1.0 },
        }
    }

    /// Place one field value on the gradient.
    pub fn position(&self, value: f64) -> f64 {
        ((value - self.low) / self.span).clamp(0.0, 1.0)
    }
}

/// Color a field into linear-light RGB, one entry per sample.
///
/// The result stays in linear light and at supersampled resolution: the
/// resample downstream both averages and encodes, and doing either here would
/// mean doing it twice.
pub fn colorize(field: &Field, colormap: &Colormap) -> Vec<[f64; 3]> {
    let stretch = Stretch::measure(field);
    field
        .values
        .par_iter()
        .map(|&value| {
            if value.is_finite() {
                colormap.lookup(stretch.position(value as f64))
            } else {
                INTERIOR
            }
        })
        .collect()
}

/// The `p`-th percentile of `values`, which is partially reordered in place.
fn percentile(values: &mut [f64], p: f64) -> f64 {
    let last = values.len() - 1;
    let index = (((p / 100.0) * last as f64).round() as usize).min(last);
    let (_, nth, _) = values.select_nth_unstable_by(index, f64::total_cmp);
    *nth
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::colormap::Kind;

    fn field_of(values: &[f32]) -> Field {
        Field {
            values: values.to_vec(),
            width: values.len() as u32,
            height: 1,
        }
    }

    #[test]
    fn percentiles_bracket_the_data() {
        let mut values: Vec<f64> = (0..=100).map(|i| i as f64).collect();
        assert_eq!(percentile(&mut values.clone(), 0.0), 0.0);
        assert_eq!(percentile(&mut values.clone(), 50.0), 50.0);
        assert_eq!(percentile(&mut values, 100.0), 100.0);
    }

    #[test]
    fn the_stretch_spans_the_bulk_of_the_frame() {
        let values: Vec<f32> = (0..1000).map(|i| i as f32).collect();
        let stretch = Stretch::measure(&field_of(&values));
        assert!(stretch.position(0.0) <= 0.0);
        assert!(stretch.position(999.0) >= 1.0);
        assert!((stretch.position(500.0) - 0.5).abs() < 0.02);
    }

    /// A few runaway samples must not flatten everything else. Without the
    /// percentile trim, one value a thousand times the rest would push the whole
    /// distribution into the first thousandth of the gradient.
    #[test]
    fn outliers_do_not_compress_the_gradient() {
        let mut values: Vec<f32> = (0..1000).map(|i| i as f32).collect();
        values.push(1_000_000.0);
        let stretch = Stretch::measure(&field_of(&values));
        assert!((stretch.position(500.0) - 0.5).abs() < 0.02);
    }

    #[test]
    fn interior_samples_color_black_and_escaped_ones_do_not() {
        let map = Colormap::from_stops(
            "two",
            Kind::Sequential,
            &[(0.0, [255, 255, 255]), (1.0, [255, 255, 255])],
        )
        .unwrap();
        let field = field_of(&[f32::NAN, 1.0, 2.0, 3.0]);
        let colors = colorize(&field, &map);
        assert_eq!(colors[0], INTERIOR);
        for color in &colors[1..] {
            assert!(color[0] > 0.9, "escaped sample colored {color:?}");
        }
    }

    #[test]
    fn a_field_with_no_escaped_samples_is_all_interior() {
        let map = Colormap::from_stops(
            "two",
            Kind::Sequential,
            &[(0.0, [255, 0, 0]), (1.0, [0, 0, 255])],
        )
        .unwrap();
        let colors = colorize(&field_of(&[f32::NAN; 8]), &map);
        assert!(colors.iter().all(|&c| c == INTERIOR));
    }
}
