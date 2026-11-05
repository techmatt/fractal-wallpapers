//! Where a sample looks when the frame is not a straight view of the plane.
//!
//! A [`Viewport`] maps the frame onto a rectangle of the plane: equal steps across
//! the picture are equal steps in `c`. A **projection** is a per-sample coordinate
//! pre-map put in front of that, before anything is iterated: the sample's place in
//! the frame becomes a `c` some other way, and the orbit, the fields and the
//! compositor never know. It is a pure function of the sample's position and the
//! view, so a band of rows draws the same bytes as the whole frame and the explorer
//! can port it as a function of the pixel.
//!
//! The one projection is the **log-polar** (exponential-map) view. Around a
//! vanishing point at frame position `p₀`, a sample at offset `p` (radius `r`,
//! angle `θ`, `y` up) reads
//!
//! ```text
//! u = power · ln(r / R)                  R: half the frame's width
//! v = turns · θ + twist · u + angle
//! c = center + (width / 2) · exp(u + i·v)
//! ```
//!
//! so `c` is the exponential of a strip coordinate `(u, v)`, wrapped back into a
//! disc round the vanishing point: every zoom octave of the plane round `center`
//! becomes a ring of the picture of the same proportions, and a location whose
//! structure repeats per octave (a Misiurewicz point, a repelling cycle of a Julia
//! set) tiles the disc in rings of self-similar cells, shrinking without end towards
//! the point. `turns` copies the plane's full turn round `center` that many times
//! round the disc (an integer, so the seam where `θ` wraps is no seam), and
//! `power`, which defaults to `turns`, keeps the map conformal: a cell keeps its
//! shape. `twist` shears the strip, turning `v` by `twist` radians per e-fold of the
//! plane's radius, which undoes a spiral: at a point whose structure turns by
//! `arg λ` every time it shrinks by `|λ|`, a `twist` of `arg λ / ln|λ|` stacks each
//! octave's copy straight above the last. With `turns = power = 1`, no twist and the
//! point in the middle, it is the straight view, sample for sample.
//!
//! The map is not an isometry, so the two things the compositor reads that carry a
//! plane length are carried through its Jacobian: a distance estimate is divided by
//! the local sample spacing (relative to the straight view's), so it stays a
//! distance in samples, and a gradient is pulled back to the frame, so a light's
//! azimuth is the frame's and not the plane's.

use num_complex::Complex;
use serde::{Deserialize, Serialize};

use crate::viewport::Viewport;

/// A per-sample coordinate pre-map, as a style carries it: `{"log_polar": {…}}`.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case", deny_unknown_fields)]
pub enum Projection {
    LogPolar(LogPolar),
}

/// The exponential-map view: see the module documentation for the formula.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct LogPolar {
    /// The vanishing point, as fractions of the frame from its top-left corner. The
    /// viewport's `center` is the plane point it shows.
    pub center: [f64; 2],
    /// Copies of the plane's full turn round the point, round the disc. At least 1.
    pub turns: u32,
    /// The exponent on the frame radius: e-folds of the plane per e-fold of the
    /// picture. Absent, `turns`: the conformal map, where a cell keeps its shape.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub power: Option<f64>,
    /// Radians the plane angle turns per e-fold of the plane radius.
    pub twist: f64,
    /// Degrees the whole view is turned by, anticlockwise.
    pub angle: f64,
    /// Escape steps per ring of the picture: what a style layer's `period` is
    /// counted in under this view. At a point whose structure repeats every `p`
    /// steps each time it shrinks by `|λ|`, the smooth count climbs by `p` per
    /// repeat, so the location (not the style) knows how many steps make one ring of
    /// the size the style wants; the style says "one band per ring" and stays the
    /// same everywhere.
    pub ring: f64,
}

impl Default for LogPolar {
    fn default() -> LogPolar {
        LogPolar {
            center: [0.5, 0.5],
            turns: 1,
            power: None,
            twist: 0.0,
            angle: 0.0,
            ring: 1.0,
        }
    }
}

/// One projected sample: its plane point and the Jacobian `∂c/∂p` in the frame's
/// sample units, `y` up. The Jacobian is `None` at the vanishing point itself.
#[derive(Clone, Copy, Debug)]
pub struct Sample {
    pub point: Complex<f64>,
    /// `∂c/∂x` and `∂c/∂y`, each a plane vector written as a complex number.
    pub jacobian: Option<[Complex<f64>; 2]>,
}

impl Sample {
    /// The plane length one sample step spans here: `√|det J|`.
    pub fn spacing(&self) -> Option<f64> {
        let [dx, dy] = self.jacobian?;
        let det = dx.re * dy.im - dx.im * dy.re;
        let spacing = det.abs().sqrt();
        (spacing.is_finite() && spacing > 0.0).then_some(spacing)
    }

    /// A unit plane direction pulled back to the frame (`Jᵀ g`) and renormalised:
    /// the direction the same quantity climbs in across the picture.
    pub fn pull_back(&self, unit: [f64; 2]) -> Option<[f64; 2]> {
        let [dx, dy] = self.jacobian?;
        let x = unit[0] * dx.re + unit[1] * dx.im;
        let y = unit[0] * dy.re + unit[1] * dy.im;
        let length = x.hypot(y);
        (length.is_finite() && length > 0.0).then(|| [x / length, y / length])
    }
}

impl Projection {
    /// Refuse a projection that would draw something other than what it says.
    pub fn validate(&self) -> Result<(), String> {
        let Projection::LogPolar(view) = self;
        if view.turns == 0 {
            return Err("log_polar turns is at least 1".into());
        }
        if view
            .power
            .is_some_and(|power| !(power.is_finite() && power > 0.0))
        {
            return Err("log_polar power is a positive number".into());
        }
        if !(view.twist.is_finite() && view.angle.is_finite()) {
            return Err("log_polar twist and angle are finite".into());
        }
        if !(view.ring.is_finite() && view.ring > 0.0) {
            return Err("log_polar ring is a positive number of escape steps".into());
        }
        if !view.center.iter().all(|f| f.is_finite()) {
            return Err("log_polar center is two finite fractions of the frame".into());
        }
        Ok(())
    }

    /// The unit a layer's `period` is counted in under this view.
    pub fn ring(&self) -> f64 {
        let Projection::LogPolar(view) = self;
        view.ring
    }

    /// The plane point sample `(col, row)` of `view`'s supersampled grid reads.
    pub fn sample(&self, view: &Viewport, col: u32, row: u32) -> Sample {
        let Projection::LogPolar(map) = self;
        let (width, height) = (view.sample_width() as f64, view.sample_height() as f64);
        let x = col as f64 + 0.5 - map.center[0] * width;
        let y = map.center[1] * height - (row as f64 + 0.5);
        let r2 = x * x + y * y;
        if !(r2 > 0.0) {
            return Sample {
                point: view.center,
                jacobian: None,
            };
        }
        let turns = map.turns as f64;
        let power = map.power.unwrap_or(turns);
        let u = power * (0.5 * r2.ln() - (0.5 * width).ln());
        let v = turns * y.atan2(x) + map.twist * u + map.angle.to_radians();
        let offset = Complex::from_polar(0.5 * view.width * u.exp(), v);
        // ∂u/∂p = power·p/r², ∂θ/∂p = (−y, x)/r², ∂v/∂p = turns·∂θ/∂p + twist·∂u/∂p;
        // ∂c/∂u = offset and ∂c/∂v = i·offset.
        let du = [power * x / r2, power * y / r2];
        let dv = [
            turns * -y / r2 + map.twist * du[0],
            turns * x / r2 + map.twist * du[1],
        ];
        let turn = Complex::new(0.0, 1.0) * offset;
        Sample {
            point: view.center + offset,
            jacobian: Some([offset * du[0] + turn * dv[0], offset * du[1] + turn * dv[1]]),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn view() -> Viewport {
        Viewport {
            center: Complex::new(-0.1011, 0.9563),
            width: 0.02,
            out_width: 64,
            out_height: 40,
            supersample: 2,
        }
    }

    fn log_polar(map: LogPolar) -> Projection {
        Projection::LogPolar(map)
    }

    #[test]
    fn one_turn_at_power_one_about_the_middle_is_the_straight_view() {
        let view = view();
        let straight = log_polar(LogPolar::default());
        for row in 0..view.sample_height() {
            for col in 0..view.sample_width() {
                let want = view.sample_point(col, row);
                let got = straight.sample(&view, col, row);
                assert!((got.point - want).norm() < 1e-15, "({col}, {row})");
                let spacing = got.spacing().unwrap();
                assert!((spacing / view.sample_spacing() - 1.0).abs() < 1e-9);
                let [a, b] = got.pull_back([0.6, 0.8]).unwrap();
                assert!((a - 0.6).abs() < 1e-9 && (b - 0.8).abs() < 1e-9);
            }
        }
    }

    #[test]
    fn each_ring_of_the_picture_is_one_octave_of_the_plane() {
        // Conformal at four turns: doubling the frame radius is four octaves of the
        // plane, whatever the direction.
        let view = view();
        let map = log_polar(LogPolar {
            turns: 4,
            ..LogPolar::default()
        });
        let middle = (view.sample_width() / 2, view.sample_height() / 2);
        let near = map.sample(&view, middle.0 + 4, middle.1);
        let far = map.sample(&view, middle.0 + 9, middle.1);
        let ratio = (far.point - view.center).norm() / (near.point - view.center).norm();
        // Sample centres sit half a sample below the point's row.
        let want = (9.5f64.hypot(0.5) / 4.5f64.hypot(0.5)).powi(4);
        assert!(
            (ratio - want).abs() < 1e-9 * ratio,
            "{ratio} against {want}"
        );
    }

    #[test]
    fn whole_turns_leave_no_seam_where_the_angle_wraps() {
        // Just above and just below the negative x axis from the point.
        let view = view();
        for turns in 1..=6 {
            let map = log_polar(LogPolar {
                turns,
                twist: 0.37,
                center: [0.75, 0.5],
                ..LogPolar::default()
            });
            let above = map.sample(&view, 10, view.sample_height() / 2 - 1);
            let below = map.sample(&view, 10, view.sample_height() / 2);
            let gap = (above.point - below.point).norm();
            let step = above.spacing().unwrap();
            assert!(gap < 2.0 * step, "turns {turns}: {gap} against {step}");
        }
    }

    #[test]
    fn the_jacobian_is_the_finite_difference() {
        let view = view();
        let map = log_polar(LogPolar {
            turns: 3,
            power: Some(2.0),
            twist: 0.8,
            angle: 30.0,
            center: [0.3, 0.6],
            ring: 1.0,
        });
        let Projection::LogPolar(lp) = map;
        // The formula, at a non-grid point, differenced.
        let at = |x: f64, y: f64| {
            let width = view.sample_width() as f64;
            let u = 2.0 * ((x * x + y * y).sqrt() / (0.5 * width)).ln();
            let v = 3.0 * y.atan2(x) + lp.twist * u + lp.angle.to_radians();
            view.center + Complex::from_polar(0.5 * view.width * u.exp(), v)
        };
        let (col, row) = (50u32, 7u32);
        let x = col as f64 + 0.5 - 0.3 * view.sample_width() as f64;
        let y = 0.6 * view.sample_height() as f64 - (row as f64 + 0.5);
        let h = 1e-4;
        let dx = (at(x + h, y) - at(x - h, y)) / (2.0 * h);
        let dy = (at(x, y + h) - at(x, y - h)) / (2.0 * h);
        let sample = map.sample(&view, col, row);
        assert!((sample.point - at(x, y)).norm() < 1e-15);
        let [jx, jy] = sample.jacobian.unwrap();
        assert!((jx - dx).norm() < 1e-6 * dx.norm(), "{jx} vs {dx}");
        assert!((jy - dy).norm() < 1e-6 * dy.norm(), "{jy} vs {dy}");
    }

    #[test]
    fn a_projection_that_cannot_draw_is_refused() {
        let zero = log_polar(LogPolar {
            turns: 0,
            ..LogPolar::default()
        });
        assert!(zero.validate().is_err());
        let flat = log_polar(LogPolar {
            power: Some(0.0),
            ..LogPolar::default()
        });
        assert!(flat.validate().is_err());
        let parsed: Projection =
            serde_json::from_str(r#"{"log_polar": {"turns": 3, "twist": 0.5}}"#).unwrap();
        assert!(parsed.validate().is_ok());
        assert!(serde_json::from_str::<Projection>(r#"{"log_polar": {"turn": 3}}"#).is_err());
    }
}
