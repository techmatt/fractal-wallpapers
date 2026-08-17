//! The coloring that never makes a field.
//!
//! Every other mode reduces an orbit to one number and looks that number up in
//! the colormap once. A direct trap does the opposite: it watches the orbit, and
//! **every time an iterate passes close to a chosen shape** it takes a sample
//! from the colormap and composites it into the pixel. A pixel's color is the
//! stack of every near miss the orbit made, in the order it made them.
//!
//! That is where the lacy, overlapping look comes from, and it has three
//! consequences worth naming:
//!
//! * **There is no scalar to keep.** The color is built during the iteration and
//!   never passes through an index, so a direct trap cannot be dumped and
//!   recolored — the samples come *from* the gradient rather than being looked
//!   up in it afterwards.
//! * **It is order-dependent**, and therefore deterministic only because the
//!   iteration is.
//! * **It has no whole-frame normalization**, so unlike every other mode here it
//!   does not adapt to the location it is pointed at. That is the reason this
//!   family reads as a specialist: it is spectacular where the orbit's near
//!   misses are sparse, and a white sheet where they are not.
//!
//! The distance to the shape does double duty on each hit: it picks the gradient
//! sample (`d/threshold`, so a close approach reads from the bottom of the
//! gradient) and it feathers the sample's opacity (`1 − d/threshold`, so a close
//! approach lands hardest). One number decides both, which is why the strokes
//! have soft edges without any second parameter to tune.

use rayon::prelude::*;

use num_complex::Complex;
use serde::{Deserialize, Serialize};

use crate::coloring::{Blend, MergeOrder, Painted};
use crate::colormap::{Colormap, srgb_to_linear};
use crate::family::Family;
use crate::iterate::BAILOUT;
use crate::viewport::Viewport;

/// The shape an iterate is measured against.
///
/// Each variant is a different way of measuring how far a point is from the
/// origin, and painting where that measure is small draws the shape's contour
/// through the orbit's near misses.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Shape {
    /// `|z|` — beads on the radius.
    Point,
    /// `‖z|−r‖` — concentric overlapping scales.
    Ring,
    /// `min(|Re z|,|Im z|)` — the two axes, as a "+".
    Cross,
    /// The axis cross together with its 45° twin: an eight-rayed asterisk.
    Hypercross,
    /// `|Re z|+|Im z|` — diamond contours.
    Diamond,
    /// `max(|Re z|,|Im z|)` — square contours.
    Box,
    /// `(|Re z|^{2/3}+|Im z|^{2/3})^{3/2}` — a concave four-pointed star.
    Astroid,
    /// `|Im z|` — the real axis alone: horizontal bands, the one anisotropic
    /// member of the family.
    Lines,
}

/// Distance from a point to the axis cross through the origin: `min(|Re z|, |Im z|)`.
///
/// Written out here, once, because two unrelated things read it: this module's
/// [`Shape::Cross`] and the scalar `trap_cross` / `threads` channels in
/// [`crate::iterate`]. A cross is the cheapest trap there is and the temptation
/// to re-spell `min(|Re|, |Im|)` at each site is exactly how the direct family
/// and the scalar family would drift into measuring two different crosses.
pub fn cross_distance(z: Complex<f64>) -> f64 {
    z.re.abs().min(z.im.abs())
}

impl Shape {
    /// Distance from an iterate to this shape, centered on the origin.
    pub fn distance(self, z: Complex<f64>, radius: f64) -> f64 {
        let (re, im) = (z.re.abs(), z.im.abs());
        match self {
            Shape::Point => z.norm(),
            Shape::Ring => (z.norm() - radius).abs(),
            Shape::Cross => cross_distance(z),
            Shape::Hypercross => {
                let diagonal =
                    (z.re - z.im).abs().min((z.re + z.im).abs()) * std::f64::consts::FRAC_1_SQRT_2;
                cross_distance(z).min(diagonal)
            }
            Shape::Diamond => re + im,
            Shape::Box => re.max(im),
            Shape::Astroid => (re.powf(2.0 / 3.0) + im.powf(2.0 / 3.0)).powf(1.5),
            Shape::Lines => im,
        }
    }

    /// How close counts as a hit, when the spec does not say.
    ///
    /// These are **not** a shared distance. The measures above live on wildly
    /// different scales — the diamond's is never smaller than the cross's, the
    /// astroid's dwarfs both — so one threshold across all eight would paint the
    /// frame solid under one shape and leave it empty under another. Each
    /// default is instead the measured distance at which *that* shape paints
    /// about the same share of a frame as the cross does at its settled 0.1, so
    /// the shapes are comparable in stroke weight rather than in units.
    pub fn default_threshold(self) -> f64 {
        match self {
            Shape::Point => 0.60,
            Shape::Ring => 0.078,
            Shape::Cross => 0.10,
            Shape::Hypercross => 0.074,
            Shape::Diamond => 0.80,
            Shape::Box => 0.55,
            Shape::Astroid => 1.06,
            Shape::Lines => 0.127,
        }
    }
}

/// The opacity a screened cross is held below.
///
/// Screen only ever brightens, and the cross is the easiest shape to hit, so
/// that one combination accumulates toward white and stays there. A fully white
/// frame carries no information and no later tone adjustment can recover any:
/// the samples that would have distinguished its pixels were already added
/// together. Measured on the worst locations, hard-white pixels stay at zero up
/// to an opacity of 0.08 and about 6% at 0.15, then climb steeply — 14% at 0.20,
/// 39% at 0.30. So the pair below is clamped to the corner that cannot blow out.
/// Every other shape and blend is left alone: they either hit far less often or
/// do not brighten at all.
pub const SCREEN_CROSS_OPACITY_CAP: f64 = 0.15;
/// The threshold a screened cross is held below. See [`SCREEN_CROSS_OPACITY_CAP`].
pub const SCREEN_CROSS_THRESHOLD_CAP: f64 = 0.08;

/// A direct trap with every constant resolved and every clamp applied.
pub struct Painter {
    shape: Shape,
    radius: f64,
    threshold: f64,
    opacity: f64,
    merge: Blend,
    merge_order: MergeOrder,
    start_color: [f64; 3],
    transform: crate::coloring::Transform,
}

impl Painter {
    /// Resolve a direct-trap coloring, filling in the shape's default threshold
    /// and applying the screened-cross clamp.
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        shape: Shape,
        radius: f64,
        threshold: Option<f64>,
        opacity: f64,
        merge: Blend,
        merge_order: MergeOrder,
        start_color: &str,
        transform: crate::coloring::Transform,
    ) -> Result<Painter, String> {
        let saturating = merge == Blend::Screen && shape == Shape::Cross;
        let (opacity_cap, threshold_cap) = if saturating {
            (SCREEN_CROSS_OPACITY_CAP, SCREEN_CROSS_THRESHOLD_CAP)
        } else {
            (1.0, f64::INFINITY)
        };
        Ok(Painter {
            shape,
            radius,
            threshold: threshold
                .unwrap_or_else(|| shape.default_threshold())
                .max(1e-12)
                .min(threshold_cap),
            opacity: opacity.clamp(0.0, 1.0).min(opacity_cap),
            merge,
            merge_order,
            start_color: parse_start_color(start_color)?,
            transform,
        })
    }

    /// The trap distance below which an iterate paints, after any clamp.
    pub fn threshold(&self) -> f64 {
        self.threshold
    }

    /// The layer opacity, after any clamp.
    pub fn opacity(&self) -> f64 {
        self.opacity
    }

    /// Iterate `view` and composite the gradient samples into linear-light RGB.
    pub fn paint(
        &self,
        view: &Viewport,
        family: &Family,
        maxiter: u32,
        colormap: &Colormap,
    ) -> Result<Painted, String> {
        let width = view.sample_width();
        let height = view.sample_height();

        let rows: Vec<(Vec<[f64; 3]>, u32)> = (0..height)
            .into_par_iter()
            .map(|row| {
                let mut colors = Vec::with_capacity(width as usize);
                let mut interior = 0;
                for col in 0..width {
                    let (color, escaped) =
                        self.trace(family, view.sample_point(col, row), maxiter, colormap);
                    if !escaped {
                        interior += 1;
                    }
                    colors.push(color);
                }
                (colors, interior)
            })
            .collect();

        let samples = (width as u64 * height as u64).max(1);
        let interior: u64 = rows.iter().map(|(_, count)| *count as u64).sum();
        Ok(Painted {
            linear: rows.into_iter().flat_map(|(colors, _)| colors).collect(),
            interior_fraction: interior as f64 / samples as f64,
        })
    }

    /// One orbit's worth of compositing. Returns the pixel and whether the orbit
    /// escaped.
    fn trace(
        &self,
        family: &Family,
        pixel: Complex<f64>,
        maxiter: u32,
        colormap: &Colormap,
    ) -> ([f64; 3], bool) {
        let bailout_sq = BAILOUT * BAILOUT;
        let (mut z, mut z_prev, c) = family.seed(pixel);
        // The background the samples land on. Black absorbs the multiplicative
        // blends, which is why the mode that multiplies starts from white: dark
        // lace on a light ground is the same construction upside down.
        let mut color = self.start_color;

        for _ in 1..=maxiter {
            let next = family.step(z, z_prev, c);
            z_prev = z;
            z = next;

            let distance = self.shape.distance(z, self.radius);
            if distance < self.threshold {
                // **The key is the nearness itself.** A direct trap has no
                // field, so there is nothing to normalize and nothing for the
                // palette recipe's gamma or traversal to act on — those describe
                // how a field's distribution is spent across the gradient, and a
                // trap distance is already a fraction of a threshold. Applying
                // them here would be a category error, and a visible one: it
                // moved these four modes by ten times what every other mode
                // moved. What does reach a trap is the bake — a reversed or
                // folded map is a different gradient — and the rolloff, which
                // acts after the color is chosen.
                let key = self
                    .transform
                    .apply((distance / self.threshold).clamp(0.0, 1.0));
                let sample = colormap.lookup(key);
                let alpha = self.opacity * (1.0 - key);
                for channel in 0..3 {
                    let blended =
                        self.merge_order
                            .merge(self.merge, color[channel], sample[channel]);
                    color[channel] = blended * alpha + color[channel] * (1.0 - alpha);
                }
            }

            if z.norm_sqr() > bailout_sq {
                return (color, true);
            }
        }
        (color, false)
    }
}

/// Read a start color: the names `black` and `white`, or an sRGB `#rrggbb`.
///
/// The result is linear light, because that is what the gradient samples it
/// composites against are in. Decoding it here rather than at the end is the
/// difference between a background that sits behind the lace and one that is
/// half a stop off from every color painted onto it.
pub fn parse_start_color(text: &str) -> Result<[f64; 3], String> {
    let text = text.trim();
    match text {
        "black" => return Ok([0.0, 0.0, 0.0]),
        "white" => return Ok([1.0, 1.0, 1.0]),
        _ => {}
    }
    let hex = text.strip_prefix('#').unwrap_or(text);
    if hex.len() != 6 || !hex.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err(format!(
            "start_color '{text}' is not 'black', 'white', or an sRGB hex like '#1b2a4f'"
        ));
    }
    let channel = |at: usize| {
        let value = u8::from_str_radix(&hex[at..at + 2], 16).expect("checked as hex above");
        srgb_to_linear(value as f64 / 255.0)
    };
    Ok([channel(0), channel(2), channel(4)])
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::colormap::Kind;

    const SHAPES: [Shape; 8] = [
        Shape::Point,
        Shape::Ring,
        Shape::Cross,
        Shape::Hypercross,
        Shape::Diamond,
        Shape::Box,
        Shape::Astroid,
        Shape::Lines,
    ];

    fn gradient() -> Colormap {
        Colormap::from_stops(
            "ramp",
            Kind::Sequential,
            &[(0.0, [255, 0, 0]), (1.0, [0, 0, 255])],
        )
        .unwrap()
    }

    fn view() -> Viewport {
        Viewport {
            center: Complex::new(0.0, 0.0),
            width: 3.0,
            out_width: 24,
            out_height: 16,
            supersample: 1,
        }
    }

    fn julia() -> Family {
        Family::Julia {
            degree: 2,
            c: Complex::new(-0.4, 0.6),
        }
    }

    #[test]
    fn every_distance_is_non_negative_and_zero_on_its_own_shape() {
        for shape in SHAPES {
            for step in 0..64 {
                let angle = std::f64::consts::TAU * step as f64 / 64.0;
                let z = Complex::from_polar(1.7, angle);
                let distance = shape.distance(z, 1.0);
                assert!(distance >= 0.0 && distance.is_finite(), "{shape:?}");
            }
        }
        let origin = Complex::new(0.0, 0.0);
        assert_eq!(Shape::Point.distance(origin, 1.0), 0.0);
        assert_eq!(Shape::Ring.distance(Complex::new(0.0, 1.0), 1.0), 0.0);
        assert_eq!(Shape::Cross.distance(Complex::new(3.0, 0.0), 1.0), 0.0);
        assert_eq!(Shape::Lines.distance(Complex::new(3.0, 0.0), 1.0), 0.0);
        // The hypercross adds the diagonals the plain cross does not have.
        let diagonal = Complex::new(2.0, 2.0);
        assert!(Shape::Hypercross.distance(diagonal, 1.0) < 1e-12);
        assert!(Shape::Cross.distance(diagonal, 1.0) > 1.0);
    }

    /// The measures are on different scales, and the defaults are what makes
    /// them comparable. A shared threshold would not: check that the ordering of
    /// the defaults follows the ordering of the measures.
    #[test]
    fn each_shape_has_its_own_calibrated_threshold() {
        let z = Complex::new(0.6, 0.35);
        assert!(Shape::Diamond.distance(z, 1.0) > Shape::Cross.distance(z, 1.0));
        assert!(Shape::Diamond.default_threshold() > Shape::Cross.default_threshold());
        for shape in SHAPES {
            assert!(shape.default_threshold() > 0.0, "{shape:?}");
        }
    }

    #[test]
    fn a_start_color_is_a_name_or_a_hex_triple() {
        assert_eq!(parse_start_color("black").unwrap(), [0.0, 0.0, 0.0]);
        assert_eq!(parse_start_color(" white ").unwrap(), [1.0, 1.0, 1.0]);
        assert_eq!(parse_start_color("#ffffff").unwrap(), [1.0, 1.0, 1.0]);
        let mid = parse_start_color("808080").unwrap();
        // sRGB middle grey is far below half in linear light; a start color that
        // skipped the decode would sit at 0.5 and read as a much lighter ground.
        assert!(mid[0] > 0.2 && mid[0] < 0.25, "{mid:?}");
        assert!(parse_start_color("puce").is_err());
        assert!(parse_start_color("#12345").is_err());
    }

    /// A sample that never enters the trap must come out exactly the background,
    /// with no rounding drift from a blend that ran anyway.
    #[test]
    fn a_pixel_the_orbit_never_visits_keeps_the_background() {
        let painter = Painter::new(
            Shape::Ring,
            1.0,
            Some(1e-9), // hit essentially nothing
            0.45,
            Blend::Screen,
            MergeOrder::BottomUp,
            "white",
            Default::default(),
        )
        .unwrap();
        let painted = painter.paint(&view(), &julia(), 60, &gradient()).unwrap();
        assert!(painted.linear.iter().all(|&color| color == [1.0, 1.0, 1.0]));
    }

    /// Multiplying onto white is the only way to build dark lace on a light
    /// ground; multiplying onto black would be dead, since black absorbs.
    #[test]
    fn multiplying_onto_white_darkens_and_onto_black_does_nothing() {
        let paint = |start| {
            Painter::new(
                Shape::Cross,
                1.0,
                Some(0.1),
                0.2,
                Blend::Multiply,
                MergeOrder::BottomUp,
                start,
                Default::default(),
            )
            .unwrap()
            .paint(&view(), &julia(), 200, &gradient())
            .unwrap()
            .linear
        };
        let on_white = paint("white");
        assert!(
            on_white.iter().any(|c| c[0] < 0.99),
            "nothing was painted onto the white ground"
        );
        assert!(paint("black").iter().all(|c| c == &[0.0, 0.0, 0.0]));
    }

    /// The one combination that can saturate is clamped at the source, so no
    /// spec can ask for a frame that is beyond recovery.
    #[test]
    fn a_screened_cross_is_held_below_the_saturating_corner() {
        let painter = Painter::new(
            Shape::Cross,
            1.0,
            Some(0.5),
            0.9,
            Blend::Screen,
            MergeOrder::BottomUp,
            "black",
            Default::default(),
        )
        .unwrap();
        assert_eq!(painter.opacity(), SCREEN_CROSS_OPACITY_CAP);
        assert_eq!(painter.threshold(), SCREEN_CROSS_THRESHOLD_CAP);

        // Below the cap the clamp is not there at all, and no other shape or
        // blend is touched by it.
        let under = Painter::new(
            Shape::Cross,
            1.0,
            Some(0.05),
            0.15,
            Blend::Screen,
            MergeOrder::BottomUp,
            "black",
            Default::default(),
        )
        .unwrap();
        assert_eq!(under.threshold(), 0.05);
        assert_eq!(under.opacity(), 0.15);
        let ring = Painter::new(
            Shape::Ring,
            1.0,
            Some(0.5),
            0.9,
            Blend::Screen,
            MergeOrder::BottomUp,
            "black",
            Default::default(),
        )
        .unwrap();
        assert_eq!(ring.threshold(), 0.5);
        assert_eq!(ring.opacity(), 0.9);
    }

    #[test]
    fn an_absent_threshold_takes_the_shape_s_default() {
        for shape in SHAPES {
            let painter = Painter::new(
                shape,
                1.0,
                None,
                0.45,
                Blend::Multiply,
                MergeOrder::BottomUp,
                "black",
                Default::default(),
            )
            .unwrap();
            assert_eq!(painter.threshold(), shape.default_threshold(), "{shape:?}");
        }
    }

    /// The direct path still knows which orbits escaped, so a direct render's
    /// record carries the same sanity number every other mode's does.
    #[test]
    fn the_interior_fraction_survives_the_color_valued_path() {
        let whole_set = Viewport {
            center: Complex::new(-0.5, 0.0),
            ..view()
        };
        let painted = Painter::new(
            Shape::Cross,
            1.0,
            None,
            0.2,
            Blend::Multiply,
            MergeOrder::BottomUp,
            "white",
            Default::default(),
        )
        .unwrap()
        .paint(
            &whole_set,
            &Family::Multibrot { degree: 2 },
            400,
            &gradient(),
        )
        .unwrap();
        assert!(
            painted.interior_fraction > 0.02 && painted.interior_fraction < 0.9,
            "{}",
            painted.interior_fraction
        );
    }
}
