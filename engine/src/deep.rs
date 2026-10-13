//! **The deep backend: a `dv=` link drawn by perturbation**, from the same kernel the
//! explorer's Deep tab runs.
//!
//! [`Perturbation`] is the [`DeepBackend`] `render-link` hands a deep view to. It builds
//! the frame's [`Spec`] the way the tab's `deep-render.js` `deepSpecOf` does, takes the
//! reference orbit at the view's own centre — a cold open, the only orbit a link names —
//! and draws the rows on every core through `perturbation::compute_rows_counted`. The
//! lanes go back through [`crate::link::shade_lanes`], the engine's own colouring, so
//! everything past the kernel is the shallow path's code.
//!
//! What it settles, of the four things [`DeepBackend`]'s doc lists:
//!
//! - **The orbit** is the cold open's: no reference named, so the kernel takes the
//!   centre (or a Julia view's parameter). The tab reuses a held orbit only where the
//!   key and the centre are exactly the view's, which draws the same picture.
//! - **The cap** is the link's `n` where it carries one, and otherwise the width's
//!   default (`perturbation::cap::for_width`) — what a link open draws, because an
//!   arrival is an automatic pass and never probes. No `policy::settle`.
//! - **The arrival fit** is not ported, and `render-link` refuses a deep link without
//!   `scale` before it reaches a backend (`main.rs`): the tab's `fit.js` is its own
//!   least-squares fit, not the engine's `autolevel`, and what it fits depends on the
//!   window's grid as well as the link.
//! - **`libm`** is the platform's. Native and wasm `ln` are not promised to agree to the
//!   bit, so the picture is the tab's within a stated tolerance:
//!   `fixtures/deep-cases.json` and [`tests`] measure it.
//!
//! The anchor of a Julia view is [`anchor_of`], `deep-render.js`'s `anchorOf` in Rust.

use perturbation::{Anchor, Spec, compute_rows_counted};
use rayon::prelude::*;

use crate::link::{DeepBackend, DeepFrame, DeepView, Lanes};

/// The perturbation kernel as `render-link`'s deep backend.
pub struct Perturbation;

impl DeepBackend for Perturbation {
    fn name(&self) -> &'static str {
        "perturbation"
    }

    fn lanes(&self, frame: &DeepFrame) -> Result<Lanes, String> {
        let spec = spec_of(frame.view, frame.samples);
        let drawn = draw(&spec)?;
        Ok(Lanes {
            width: spec.sample_width(),
            height: spec.sample_height(),
            smooth: drawn.smooth,
        })
    }
}

/// A frame's field and what it cost.
pub struct Drawn {
    /// One smooth lane a sample, row-major, `NaN` for interior.
    pub smooth: Vec<f64>,
    /// Iterations run, summed over the frame.
    pub ran: u64,
    /// Iterations the interior switch spared, summed over the frame.
    pub saved: u64,
}

/// The [`Spec`] the Deep tab builds for this view at `samples` across and down:
/// `deepSpecOf(view, width, height)` at a cold open, one sample a pixel.
///
/// The centre and the Julia parameter are the view's exact decimal text, the width its
/// double, the cap its `n` or `None` for the width's default, the interior switch on.
pub fn spec_of(view: &DeepView, samples: [u32; 2]) -> Spec {
    Spec {
        center_re: view.x.text(),
        center_im: view.y.text(),
        width: view.w.value,
        resolution: samples,
        supersample: 1,
        maxiter: view.maxiter,
        reference: None,
        period: None,
        julia: view.julia.as_ref().map(|(re, im)| (re.text(), im.text())),
        anchor: anchor_of(view).unwrap_or(Anchor::Parameter),
        interior: perturbation::SHIPS_INTERIOR,
        degree: view.degree,
    }
}

/// `deep-render.js`'s `anchorOf`: which point of the Julia orbit a view is drawn from,
/// the nearer of `z = c` and `z = 0` to its centre, ties to `c`. `None` off the Julia
/// plane.
///
/// The distances are the page's: an exact decimal difference rounded once to a double
/// (`fx.difference`), and each coordinate's own nearest double (`fx.toNumber`).
pub fn anchor_of(view: &DeepView) -> Option<Anchor> {
    let (julia_re, julia_im) = view.julia.as_ref()?;
    let to_parameter = view
        .x
        .difference(julia_re)
        .abs()
        .max(view.y.difference(julia_im).abs());
    let to_origin = view.x.to_f64().abs().max(view.y.to_f64().abs());
    Some(if to_origin < to_parameter {
        Anchor::Origin
    } else {
        Anchor::Parameter
    })
}

/// The frame's lanes, every row on the pool, or the sentence the tab's `plan` refuses it
/// with — the same sentence, since both ask the kernel's own `Spec::drawable`.
pub fn draw(spec: &Spec) -> Result<Drawn, String> {
    spec.drawable()?;
    let orbit = spec.reference_orbit()?;
    // One row a task: a row is one band to the kernel, so the bytes are the ones a
    // whole-frame band writes (the kernel's `tests/parity.rs` holds a band cut in two to
    // that, and the bytes of a sample do not depend on its band), and each band's counters
    // come back with it rather than through a static.
    let bands: Vec<_> = (0..spec.sample_height())
        .into_par_iter()
        .map(|row| compute_rows_counted(spec, &orbit, row, row + 1))
        .collect();
    let mut drawn = Drawn {
        smooth: Vec::with_capacity((spec.sample_width() * spec.sample_height()) as usize),
        ran: 0,
        saved: 0,
    };
    for band in bands {
        drawn.ran += band.ran;
        drawn.saved += band.saved;
        drawn.smooth.extend(
            band.lanes
                .chunks_exact(8)
                .map(|bytes| f64::from_le_bytes(bytes.try_into().expect("eight bytes"))),
        );
    }
    Ok(drawn)
}

#[cfg(test)]
mod tests;
