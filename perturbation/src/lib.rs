//! The perturbation kernel: `z^d + c` below the `f64` floor, one smooth lane a sample.
//!
//! ```text
//! Spec::parse(json)                  a frame: exact decimal centre, width, grid, cap
//! spec.reference_orbit()             one fixed-point orbit, computed once per frame
//! compute_rows(spec, orbit, rows)    the smooth field as f64 lanes, NaN for interior
//! compute_listed(spec, orbit, list)  the same samples, named one at a time
//! ```
//!
//! **This crate is the picture and nothing else.** It draws what the explorer's Deep
//! tab draws on the CPU, and it is that tab's kernel: the website's
//! `explorer/perturb-wasm` wraps it in the `extern "C"` exports the page calls and builds
//! it to `perturb.wasm`, and `fractal-engine render-link` calls it natively for a `dv=`
//! link. Minibrot search, the Dive and the GPU path are the website's and are not here.
//!
//! **The output is lanes, not colour.** One `f64` a sample, in the layout the engine's
//! `smooth` band produces, so the engine's own colouring shades it without being told
//! which kernel drew it.
//!
//! No dependencies at all, and every number a frame is drawn from is in its [`Spec`],
//! which is read from the same flat JSON the page sends.
//!
//! ## What this does not do
//!
//! `z^d + c` at integer degrees two to six, on both of its planes — the Multibrot
//! set of that degree and its Julia sets — in `smooth`, and nothing else. No
//! other family has a delta recurrence written here; no other mode's channels are
//! reduced. It is not a wider engine, it is one kernel with the degree as a const
//! parameter.

use std::sync::atomic::{AtomicU64, Ordering};

use crate::fx::Fx;
use crate::json::Value;
use crate::kernel::Kernel;
use crate::reference::Reference;

pub mod fx;
pub mod json;
pub mod kernel;
#[cfg(all(target_arch = "wasm32", target_feature = "simd128"))]
mod lanes;
pub mod policy;
pub mod progress;
pub mod reference;

/// The record's own version, in the same spirit as every JSONL record in this
/// repository.
pub const SCHEMA: u32 = 1;

/// Whether [`kernel::Kernel::interior`] is on when a spec does not say.
///
/// **On**, and the README carries the evidence and the caveat. Across both
/// ladders, and at every threshold from `2^-300` to `2^-4`, it never painted
/// interior a sample the plain run escaped from — but beside a parabolic point it
/// did, at every degree, until interior_switch_fix_ckpt162 made the threshold a
/// gate in front of a proof (README §3). What it *saves* depends
/// entirely on the view: 75% to 98% on a frame inside a minibrot, and −9% on the
/// audit's anchor, where only about seventeen periods fit inside the cap and
/// `|dz|` has no room to fall.
pub const SHIPS_INTERIOR: bool = true;

/// The fewest representable numbers one sample step may span in the delta before
/// a frame is refused. See [`Spec::delta_ulps`].
///
/// **Four, and it is the engine's own `viewport::RESOLUTION_ULPS` restated** —
/// the same shape as [`cap::for_width`], and restated for the same reason, which
/// is that this crate does not link the engine. The number says the same thing on
/// both sides of the floor: below it a picture is of the arithmetic rather than
/// of the set, and the honest answer is a sentence.
pub const DELTA_ULPS: f64 = 4.0;

// ------------------------------------------------------------------- the cap policy

/// The engine's own depth policy, continued past the point where it gives up.
///
/// `maxiter::for_width` is `BASE · (1 + PER_OCTAVE · log₂(HOME_WIDTH / width))`
/// clamped to `[FLOOR, CEILING]`, and the engine's `CEILING` of 67,000 saturates at a
/// width of about 4.7e-16. That is fine for a renderer that refuses to go deeper
/// and wrong for one that does: every perturbation-depth view would be flattened
/// to the same cap, and a frame at 1e-28 would be a black disc.
///
/// So the shape is the engine's, restated rather than imported — this crate does
/// not link the engine — and only the ceiling moves. **Touching
/// `maxiter::for_width` itself was never an option**: it is read by
/// `spec.rs::resolve`, `MaxiterSpec::caps`, `screen.rs`, `expand.rs`, the wasm
/// `maxiter_for_width` and Python's `engine.maxiter_for`, so a wider ceiling
/// there moves the cap of every shallow picture the project has.
pub mod cap {
    /// The view width the policy is calibrated at, the engine's `HOME_WIDTH`.
    pub const HOME_WIDTH: f64 = 3.0;
    /// The engine's `BASE`.
    pub const BASE: f64 = 4000.0;
    /// The engine's `PER_OCTAVE`.
    pub const PER_OCTAVE: f64 = 0.30;
    /// The engine's `FLOOR`.
    pub const FLOOR: f64 = 200.0;
    /// **The ceiling on every cap the explorer chooses by itself, and it stays at a
    /// million by Matt's ruling.** The engine's is 67,000 and exists to stop a
    /// raised base being re-clipped; this one bounds how far the page may go
    /// unasked — the width policy below, the probe's doublings
    /// ([`crate::policy::next_cap`]) and a preview tile (`nuclei::tile_cap`, in
    /// the website wrapper's `explorer/perturb-wasm/src/nuclei.rs`). The width
    /// formula alone reaches it only at about 4e-250 — it gives 48,551 at 2e-11
    /// and 117,518 at 1e-28 — but the doublings do reach it, and it binds on the
    /// degree-6 near-parabolic body frames, which are still a fifth the cap's fault
    /// here. The limit is kept and the page says where it binds, rather than being
    /// raised (`README.md` §10).
    ///
    /// **One of two ceilings** *(Matt, cap_split_ckpt145)*: nothing automatic may
    /// run away, so this one stays where it was, and a cap somebody asks for
    /// deliberately is held to [`EXPLICIT_CEILING`] instead.
    pub const AUTOMATIC_CEILING: f64 = 1_000_000.0;

    /// **The ceiling on a cap somebody asks for**, twice the automatic one *(Matt,
    /// cap_split_ckpt145)*: a typed `n` or one in a link (`permalink.js`'s
    /// `CAP_LIMIT` is this number, and `deep.test.mjs` holds the two together),
    /// Halve and Double, an opened minibrot's thirty-two periods
    /// (`nuclei::open_cap`, in the website wrapper's
    /// `explorer/perturb-wasm/src/nuclei.rs`) and a descent's pinned caps
    /// (`builder/descent.py`).
    /// None of those is a loop the page runs on its own, so none of them can run
    /// away; what bounds them is the reference orbit, sixteen bytes a point and
    /// one copy per worker (`README.md` §8 has the measurement).
    pub const EXPLICIT_CEILING: f64 = 2_000_000.0;

    /// The iteration cap for a view of the given plane width.
    pub fn for_width(width: f64) -> u32 {
        if width.is_nan() || width <= 0.0 {
            return BASE as u32;
        }
        let octaves = (HOME_WIDTH / width).log2();
        let raw = BASE * (1.0 + PER_OCTAVE * octaves);
        raw.clamp(FLOOR, AUTOMATIC_CEILING) as u32
    }
}

// ------------------------------------------------------------------------ the spec

/// One frame, as JSON.
///
/// The centre is **text** and stays text until it reaches [`Fx::parse`]. That is
/// the one thing this boundary exists to get right: the engine's own
/// `spec::decimal` is `str::parse::<f64>`, and at 1e-28 the digits it discards
/// are the ones that say where the view is. The width is a plain `f64` and
/// wants no more — 1e-28 is nowhere near what an exponent cannot hold, and it is
/// the *spacing between* coordinates rather than a coordinate.
#[derive(Debug, Clone)]
pub struct Spec {
    pub center_re: String,
    pub center_im: String,
    pub width: f64,
    pub resolution: [u32; 2],
    pub supersample: u32,
    /// An explicit cap, overriding [`cap::for_width`]. Unlike the engine's wasm,
    /// where this is a probe's knob and never a picture's, here it is also the
    /// escape hatch for a view whose policy cap is more than a reader will wait
    /// for.
    pub maxiter: Option<u32>,
    /// The reference point, defaulting to the view centre. A nucleus is worth
    /// naming: it makes the orbit periodic, which is both smaller and better
    /// behaved than a walk out to the cap.
    pub reference: Option<(String, String)>,
    /// The reference's period, where it is a nucleus. The orbit is then stored
    /// for one period and the index wraps instead of rebasing.
    pub period: Option<u32>,
    /// The Julia parameter: the `c` of `z ↦ z² + c`, held fixed while `z₀` is the
    /// pixel. **Absent is the Mandelbrot set**, which is what every spec written
    /// before this member existed is.
    pub julia: Option<(String, String)>,
    /// Which point of the reference orbit a Julia view's offset is taken from.
    /// No meaning without [`Spec::julia`], and refused without it.
    pub anchor: Anchor,
    pub interior: bool,
    /// The degree of `z ↦ z^d + c`, from two to six *(deep_degrees_ckpt140)*.
    /// **Absent is two**, which is what every spec written before this member
    /// existed is, and it is the one member that means the same thing on both
    /// sides of the Mandelbrot/Julia fork: the Multibrot set of degree `d` and the
    /// Julia sets of that same recurrence.
    pub degree: u32,
}

/// The point a Julia view measures its offset from, which is always a point of
/// the stored reference orbit and never an arbitrary place.
///
/// The orbit is `Z₀ = 0, Z₁ = c, Z₂ = c² + c, …` — the critical orbit of `c` —
/// and it is simultaneously the Julia orbit of `z = 0` and, shifted by one, the
/// Julia orbit of `z = c`. So both anchors are *on* it, their offsets are exact
/// fixed-point subtractions, and which one a frame uses changes nothing about
/// the mathematics: it changes only how much of the pixel step survives into
/// `f64`. See [`Spec::delta_ulps`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Anchor {
    /// `z = c`, entered at index 1. Where the filigree is.
    Parameter,
    /// `z = 0`, entered at index 0 — the critical point itself, and the one
    /// place the picture has exact two-fold symmetry.
    Origin,
}

const KNOWN: &[&str] = &[
    "schema",
    "center_re",
    "center_im",
    "width",
    "resolution",
    "supersample",
    "maxiter",
    "reference_re",
    "reference_im",
    "period",
    "julia_re",
    "julia_im",
    "anchor",
    "interior",
    "degree",
];

impl Spec {
    pub fn parse(text: &str) -> Result<Spec, String> {
        let object = json::object(text).ok_or("the spec is not a flat JSON object")?;
        if let Some(name) = object.unknown(KNOWN) {
            return Err(format!("the spec carries no member named `{name}`"));
        }
        match object.get("schema") {
            Some(Value::Num(version)) if *version == SCHEMA as f64 => {}
            Some(Value::Num(version)) => {
                return Err(format!("this module reads schema {SCHEMA}, not {version}"));
            }
            _ => return Err("the spec needs a `schema`".to_string()),
        }

        let text_of = |key: &str| -> Result<String, String> {
            match object.get(key) {
                Some(Value::Str(value)) => Ok(value.clone()),
                Some(Value::Num(_)) => Err(format!(
                    "`{key}` has to be a string: a coordinate written as a JSON number \
                     has already lost the digits this module exists for"
                )),
                _ => Err(format!("the spec needs a `{key}`")),
            }
        };
        let count_of = |key: &str| -> Option<u32> {
            match object.get(key) {
                Some(Value::Num(value)) if *value >= 1.0 && value.fract() == 0.0 => {
                    Some(*value as u32)
                }
                _ => None,
            }
        };

        let center_re = text_of("center_re")?;
        let center_im = text_of("center_im")?;
        let width = match object.get("width") {
            Some(Value::Num(value)) if *value > 0.0 && value.is_finite() => *value,
            _ => return Err("the spec needs a positive `width`".to_string()),
        };
        let resolution = match object.get("resolution") {
            Some(Value::Nums(pair)) if pair.len() == 2 && pair[0] >= 1.0 && pair[1] >= 1.0 => {
                [pair[0] as u32, pair[1] as u32]
            }
            None => [1, 1],
            _ => return Err("`resolution` is two positive integers".to_string()),
        };
        let reference = match (object.get("reference_re"), object.get("reference_im")) {
            (None, None) => None,
            _ => Some((text_of("reference_re")?, text_of("reference_im")?)),
        };
        let interior = match object.get("interior") {
            Some(Value::Bool(value)) => *value,
            None | Some(Value::Null) => SHIPS_INTERIOR,
            _ => return Err("`interior` is a boolean".to_string()),
        };
        let julia = match (object.get("julia_re"), object.get("julia_im")) {
            (None, None) => None,
            _ => Some((text_of("julia_re")?, text_of("julia_im")?)),
        };
        let anchor = match object.get("anchor") {
            None | Some(Value::Null) => Anchor::Parameter,
            Some(Value::Str(name)) if name == "parameter" => Anchor::Parameter,
            Some(Value::Str(name)) if name == "origin" => Anchor::Origin,
            Some(_) => return Err("`anchor` is \"parameter\" or \"origin\"".to_string()),
        };
        let period = count_of("period");
        let degree = match object.get("degree") {
            None | Some(Value::Null) => 2,
            Some(Value::Num(value))
                if value.fract() == 0.0 && kernel::DEGREES.contains(&(*value as u32)) =>
            {
                *value as u32
            }
            Some(_) => {
                return Err(format!(
                    "`degree` is a whole number from {} to {}: this kernel draws z^d + c at                      integer degrees and no others",
                    kernel::DEGREES.start(),
                    kernel::DEGREES.end()
                ));
            }
        };

        // Each of these three is a member that means something only on the other
        // side of the fork, and a spec that carries both is a spec whose author
        // believed something untrue about what is being drawn. Said rather than
        // ignored, for the reason every refusal in this module is a sentence.
        if julia.is_some() {
            if reference.is_some() {
                return Err(
                    "a Julia frame's reference is the critical orbit of its own \
                            `julia_re`/`julia_im`, so it cannot also be given a \
                            `reference_re`/`reference_im`"
                        .to_string(),
                );
            }
            if period.is_some() {
                return Err(
                    "`period` wraps a Mandelbrot nucleus's reference, and a Julia \
                            frame's reference is a critical orbit rather than a nucleus"
                        .to_string(),
                );
            }
        } else if object.get("anchor").is_some() {
            return Err(
                "`anchor` says which point of the Julia reference a view is offset \
                        from, and this spec has no `julia_re`"
                    .to_string(),
            );
        }

        Ok(Spec {
            center_re,
            center_im,
            width,
            resolution,
            supersample: count_of("supersample").unwrap_or(1),
            maxiter: count_of("maxiter"),
            reference,
            period,
            julia,
            anchor,
            interior,
            degree,
        })
    }

    pub fn sample_width(&self) -> u32 {
        self.resolution[0] * self.supersample
    }

    pub fn sample_height(&self) -> u32 {
        self.resolution[1] * self.supersample
    }

    pub fn plane_height(&self) -> f64 {
        self.width * (self.resolution[1] as f64 / self.resolution[0] as f64)
    }

    pub fn maxiter(&self) -> u32 {
        self.maxiter.unwrap_or_else(|| cap::for_width(self.width))
    }

    /// The limb count this frame's reference orbit is computed at.
    ///
    /// The view's own rule everywhere but one place: **a Julia frame anchored at
    /// `z = 0` is sized for `step^d`**, because its first step raises the pixel
    /// offset to the degree and the orbit has to tell two of those apart. See
    /// [`reference::limbs_pow`], which is where the measurement is.
    pub fn limbs(&self) -> usize {
        reference::limbs_pow(self.width, self.sample_width(), self.limb_power())
    }

    /// The power of the sample step the reference has to resolve: the degree at
    /// the Julia origin anchor, where `z₁ = z₀^d + c`, and one everywhere else.
    pub fn limb_power(&self) -> u32 {
        match (&self.julia, self.anchor) {
            (Some(_), Anchor::Origin) => self.degree,
            _ => 1,
        }
    }

    /// Whether [`Spec::limbs`] holds every bit the frame needs, rather than stopping
    /// at [`fx::MAX_LIMBS`]. The origin anchor reaches the clamp far sooner than any
    /// other view: at `480·2^(−896/d)` across, 6.6e-133 at `d = 2`, against about
    /// 9e-268 for every other view at 480 samples.
    pub fn limbs_fit(&self) -> bool {
        reference::limbs_pow_fits(self.width, self.sample_width(), self.limb_power())
    }

    /// The reference orbit this spec asks for.
    ///
    /// **A Julia frame's is the critical orbit of its own parameter** — `Z₀ = 0,
    /// Z₁ = c, Z₂ = c² + c, …`, which is byte for byte the orbit a Mandelbrot
    /// frame centred at that `c` computes. That is the whole reason the jump
    /// costs nothing: the workers are already holding it.
    pub fn reference_orbit(&self) -> Result<Reference, String> {
        let limbs = self.limbs();
        let (re, im) = match (&self.julia, &self.reference) {
            (Some((re, im)), _) => (re.as_str(), im.as_str()),
            (None, Some((re, im))) => (re.as_str(), im.as_str()),
            (None, None) => (self.center_re.as_str(), self.center_im.as_str()),
        };
        let c_re = Fx::parse(re, limbs).ok_or_else(|| format!("`{re}` is not a decimal"))?;
        let c_im = Fx::parse(im, limbs).ok_or_else(|| format!("`{im}` is not a decimal"))?;
        // A view entered at `Z₁` has one step less of reference in front of it
        // than one entered at `Z₀`, so it asks for one more point rather than
        // rebasing a step early.
        let steps = self.maxiter() + self.entry() as u32;
        Ok(reference::orbit_of(
            self.degree,
            &c_re,
            &c_im,
            steps,
            self.period,
        ))
    }

    /// The index of the stored orbit a sample's delta starts against.
    ///
    /// One for a Julia view anchored at `z = c`, because `Z₁ = c`; zero for
    /// everything else, `Z₀ = 0` being both the Mandelbrot start and the Julia
    /// orbit of the critical point.
    pub fn entry(&self) -> usize {
        matches!((&self.julia, self.anchor), (Some(_), Anchor::Parameter)) as usize
    }

    /// The point a sample's delta is measured from: the Julia view's anchor, the
    /// named Mandelbrot reference, or the view centre itself.
    fn offset_from(&self) -> Option<(&str, &str)> {
        match (&self.julia, self.anchor) {
            (Some(_), Anchor::Origin) => Some(("0", "0")),
            (Some((re, im)), Anchor::Parameter) => Some((re.as_str(), im.as_str())),
            (None, _) => self
                .reference
                .as_ref()
                .map(|(re, im)| (re.as_str(), im.as_str())),
        }
    }

    /// How far the view centre is from the point the delta is measured from, in
    /// `f64`, taken in fixed point.
    ///
    /// **Never `f64(center) − f64(reference)`.** At the depths this crate is for,
    /// those two are the same `f64` and the difference is exactly zero — which
    /// would draw the reference's own neighbourhood wherever the view actually
    /// is, and look entirely plausible.
    pub fn centre_offset(&self) -> Result<(f64, f64), String> {
        let Some((re, im)) = self.offset_from() else {
            return Ok((0.0, 0.0));
        };
        let limbs = self.limbs();
        let parse =
            |text: &str| Fx::parse(text, limbs).ok_or_else(|| format!("`{text}` is not a decimal"));
        Ok((
            parse(&self.center_re)?.sub(&parse(re)?).to_f64(),
            parse(&self.center_im)?.sub(&parse(im)?).to_f64(),
        ))
    }

    /// Whether this frame can be drawn at all, or the sentence that says why not: the
    /// two refusals made before any orbit is computed, in one place for every caller —
    /// the page's `plan` export and `fractal-engine render-link` alike.
    ///
    /// A frame whose reference needs more limbs than [`fx::MAX_LIMBS`], and one whose
    /// samples, at its distance from the anchor, are fewer than [`DELTA_ULPS`] doubles
    /// apart ([`Spec::delta_ulps`]).
    pub fn drawable(&self) -> Result<(), String> {
        if !self.limbs_fit() {
            return Err(if self.limb_power() > 1 {
                format!(
                    "this frame is drawn from z = 0, where one pixel of it is told apart from the \
                     next only at its width to the power {}, and that needs more than the {} limbs \
                     the kernel computes a reference at. Zoom out, or move toward z = c.",
                    self.limb_power(),
                    fx::MAX_LIMBS,
                )
            } else {
                format!(
                    "telling one pixel of this frame from the next needs more than the {} limbs \
                     the kernel computes a reference at. Zoom out.",
                    fx::MAX_LIMBS,
                )
            });
        }
        match self.delta_ulps() {
            ulps if ulps >= DELTA_ULPS => Ok(()),
            ulps => Err(format!(
                "this frame is {} from the point its arithmetic is anchored at, and one pixel of \
                 it spans {:.2} of the numbers a double has left there — fewer than the {} it \
                 takes to tell two pixels apart. Every sample would start from the same delta and \
                 the picture would be flat. Zoom out, or move back toward the anchor.",
                if self.julia.is_some() {
                    "too far"
                } else {
                    "too far from its reference"
                },
                ulps,
                DELTA_ULPS,
            )),
        }
    }

    /// How many representable numbers one sample step spans, in the `f64` the
    /// delta starts from.
    ///
    /// **This is the engine's own `resolution_ulps` asked of a different
    /// number.** There the question is whether two neighbouring sample centres
    /// are the same `f64` coordinate; here the coordinates are exact decimals
    /// and it is the *delta* that is a double — the offset from the anchor plus
    /// the pixel's own geometry. A view a long way from its anchor at a width far
    /// below it has an offset whose last bit is coarser than the whole frame, and
    /// every pixel of it would start from the same delta: one flat picture, drawn
    /// with total confidence. [`DELTA_ULPS`] is what that is refused against.
    ///
    /// Infinite where the offset is exactly zero, which is every view centred on
    /// its anchor — including, always, a Mandelbrot frame referenced at its own
    /// centre.
    pub fn delta_ulps(&self) -> f64 {
        let (re, im) = match self.centre_offset() {
            Ok(offset) => offset,
            Err(_) => return f64::INFINITY,
        };
        let far = re.abs().max(im.abs());
        #[allow(clippy::neg_cmp_op_on_partial_ord, reason = "NaN is caught here too")]
        if !(far > 0.0) {
            return f64::INFINITY;
        }
        (self.width / self.sample_width() as f64) / (far.next_up() - far)
    }

    /// `dc` for sample cell `(col, row)` of the supersampled grid — and, for a
    /// Julia frame, the same number under its other name, `δ₀`.
    ///
    /// The geometry is the engine's `Viewport::sample_point`, offset by the
    /// reference rather than added to the centre: row 0 is the top of the image
    /// and so the largest imaginary part, which is why the vertical term is
    /// subtracted.
    ///
    /// **One expression, two jobs, and that is the shape of the whole Julia
    /// case.** For Mandelbrot this is the sample's distance from the reference
    /// *parameter*, and it enters every step of the recurrence; for Julia it is
    /// the sample's distance from the anchor *point*, and it enters once, as the
    /// delta the loop starts from.
    pub fn dc(&self, offset: (f64, f64), col: u32, row: u32) -> (f64, f64) {
        let across = (col as f64 + 0.5) / self.sample_width() as f64 - 0.5;
        let down = 0.5 - (row as f64 + 0.5) / self.sample_height() as f64;
        (
            offset.0 + across * self.width,
            offset.1 + down * self.plane_height(),
        )
    }
}

// --------------------------------------------------------------------- the band

/// The smooth field for sample rows `[first, last)`, as little-endian `f64`.
///
/// One lane, `NaN` for interior — what `engine.wasm`'s `compute_band` produces
/// for `smooth`, in the layout it produces it, so the page's existing
/// `shade_level` colours this without being told which kernel drew it.
///
/// **It is not narrowed through `f32`.** The engine rounds every inexact lane to
/// `f32` on the way out, because that is what a dumped field stores and the
/// picture wanted is the one the pipeline draws. At this depth that rounding is
/// visible: the `f32` step at a smooth count of 65,000 is about 0.008 and at
/// 1,000,000 about 0.06, and the percentile stretch downstream would band on it.
/// The offset is per-frame and the stretch ignores a constant, so the fix is
/// available — but it belongs to whoever puts a picture on a page, and until
/// then this hands over everything it computed.
///
/// The band's two counters are left where [`band_ran`] and [`band_saved`] read them, as
/// the page's wrapper wants; [`compute_rows_counted`] hands them back instead.
pub fn compute_rows(spec: &Spec, orbit: &Reference, first: u32, last: u32) -> Vec<u8> {
    let band = compute_rows_counted(spec, orbit, first, last);
    BAND_RAN.store(band.ran, Ordering::Relaxed);
    BAND_SAVED.store(band.saved, Ordering::Relaxed);
    band.lanes
}

/// One band's lanes and what it cost, together.
pub struct Band {
    /// Little-endian `f64`, one a sample, row-major, `NaN` for interior.
    pub lanes: Vec<u8>,
    /// The iterations the band ran.
    pub ran: u64,
    /// The iterations the interior switch spared it.
    pub saved: u64,
}

/// [`compute_rows`], with the counters returned rather than left in a static — for a
/// caller that draws bands on several threads at once, where one static would hold
/// whichever band finished last.
pub fn compute_rows_counted(spec: &Spec, orbit: &Reference, first: u32, last: u32) -> Band {
    let kernel = Kernel::new(orbit, spec.maxiter(), spec.interior).at_entry(spec.entry());
    let offset = spec.centre_offset().unwrap_or((0.0, 0.0));
    let width = spec.sample_width();
    let mut bytes = Vec::with_capacity(((last - first) * width) as usize * 8);
    // The fork is taken once for the band rather than once for each of its
    // samples: the loops are the same text and different monomorphizations, one
    // per set and degree, which is what keeps the degree-2 Mandelbrot loop
    // exactly the loop it was.
    macro_rules! fill_at {
        ($d:literal, $julia:literal) => {
            fill::<$d, $julia>(spec, &kernel, offset, first, last, &mut bytes)
        };
    }
    let (ran, saved) = match (spec.degree, spec.julia.is_some()) {
        (2, false) => fill_at!(2, false),
        (2, true) => fill_at!(2, true),
        (3, false) => fill_at!(3, false),
        (3, true) => fill_at!(3, true),
        (4, false) => fill_at!(4, false),
        (4, true) => fill_at!(4, true),
        (5, false) => fill_at!(5, false),
        (5, true) => fill_at!(5, true),
        (6, false) => fill_at!(6, false),
        (6, true) => fill_at!(6, true),
        // `Spec::parse` refuses any other degree in a sentence, and a `Spec` built
        // by hand with one draws nothing rather than drawing the wrong set.
        _ => (0, 0),
    };
    Band {
        lanes: bytes,
        ran,
        saved,
    }
}

/// The band's samples appended to `bytes`, and what they ran and saved.
fn fill<const D: usize, const JULIA: bool>(
    spec: &Spec,
    kernel: &Kernel,
    offset: (f64, f64),
    first: u32,
    last: u32,
    bytes: &mut Vec<u8>,
) -> (u64, u64) {
    let width = spec.sample_width();
    #[cfg(all(target_arch = "wasm32", target_feature = "simd128"))]
    {
        let inputs: Vec<(f64, f64)> = (first..last)
            .flat_map(|row| (0..width).map(move |col| (col, row)))
            .map(|(col, row)| spec.dc(offset, col, row))
            .collect();
        paired::<D, JULIA>(spec, kernel, &inputs, bytes)
    }
    #[cfg(not(all(target_arch = "wasm32", target_feature = "simd128")))]
    {
        let (mut ran, mut saved) = (0u64, 0u64);
        for row in first..last {
            for col in 0..width {
                let (re, im) = spec.dc(offset, col, row);
                let outcome = kernel.sample_with::<D, JULIA>(re, im);
                ran += outcome.iterations as u64;
                if outcome.detected_interior {
                    saved += spec.maxiter().saturating_sub(outcome.iterations) as u64;
                }
                bytes.extend_from_slice(&outcome.smooth.to_le_bytes());
            }
        }
        (ran, saved)
    }
}

/// The samples at `inputs` (each its `dc`, or a Julia frame's starting delta), drawn two
/// to a vector by [`lanes::fill`], appended to `bytes` in list order, with the band's
/// two counters returned — what [`fill`] and [`fill_listed`] do one sample at a time in
/// the scalar module and on native. The same outcome per sample bit for bit; see
/// `src/lanes.rs`.
#[cfg(all(target_arch = "wasm32", target_feature = "simd128"))]
fn paired<const D: usize, const JULIA: bool>(
    spec: &Spec,
    kernel: &Kernel,
    inputs: &[(f64, f64)],
    bytes: &mut Vec<u8>,
) -> (u64, u64) {
    let blank = kernel::interior_outcome(0, 0, false, false, 1.0, 0);
    let mut outcomes = vec![blank; inputs.len()];
    if kernel.interior {
        lanes::fill::<D, JULIA, true>(kernel, inputs, &mut outcomes);
    } else {
        lanes::fill::<D, JULIA, false>(kernel, inputs, &mut outcomes);
    }
    let (mut ran, mut saved) = (0u64, 0u64);
    for outcome in &outcomes {
        ran += outcome.iterations as u64;
        if outcome.detected_interior {
            saved += spec.maxiter().saturating_sub(outcome.iterations) as u64;
        }
        bytes.extend_from_slice(&outcome.smooth.to_le_bytes());
    }
    (ran, saved)
}

/// What the last band cost, in iterations, and what the interior switch saved it: the
/// two numbers [`band_ran`] and [`band_saved`] read.
static BAND_RAN: AtomicU64 = AtomicU64::new(0);
static BAND_SAVED: AtomicU64 = AtomicU64::new(0);

/// The iterations the last [`compute_rows`] or [`compute_listed`] ran, as an `f64`.
///
/// **The page reads these two to choose the interior switch for the next pass of the
/// same frame**, through the wrapper's export of the same name. The switch never moves a
/// pixel — a sample it stops is one the plain loop runs to the cap, and both write `NaN` —
/// but in wasm it is about half the loop's speed where it does not fire, which is most of
/// the frames a reader opens. `ran + saved` is what the plain loop would have run, so a
/// quarter pass drawn with the switch on says, exactly, what the full pass would run
/// either way.
///
/// One static for the process: under threads it is whichever band finished last, which
/// is why a native caller that wants it runs one band at a time.
pub fn band_ran() -> f64 {
    BAND_RAN.load(Ordering::Relaxed) as f64
}

/// The iterations the interior switch spared the last band: the cap less the step it
/// stopped at, summed over the samples it stopped. Zero with it off.
pub fn band_saved() -> f64 {
    BAND_SAVED.load(Ordering::Relaxed) as f64
}

// ------------------------------------------------------------- the reference buffer

/// Bytes of header on the reference buffer, before the orbit's `f64` pairs.
///
/// Sixteen rather than the twelve the fields need, so the pairs start `f64`
/// aligned: a `DataView` on the JavaScript side does not care, and a
/// `Float64Array` view over the same bytes does.
pub const REFERENCE_HEADER: usize = 16;

/// Pack a reference orbit for the boundary: `count`, flags, the period residual,
/// then `count` interleaved `(re, im)` pairs.
pub fn pack_reference(orbit: &Reference) -> Vec<u8> {
    let mut bytes = Vec::with_capacity(REFERENCE_HEADER + orbit.len() * 16);
    bytes.extend_from_slice(&(orbit.len() as u32).to_le_bytes());
    let flags = (orbit.escaped as u32) | ((orbit.periodic as u32) << 1);
    bytes.extend_from_slice(&flags.to_le_bytes());
    bytes.extend_from_slice(&orbit.period_residual.to_le_bytes());
    for [re, im] in &orbit.points {
        bytes.extend_from_slice(&re.to_le_bytes());
        bytes.extend_from_slice(&im.to_le_bytes());
    }
    bytes
}

/// Read back what [`pack_reference`] wrote.
pub fn unpack_reference(bytes: &[u8]) -> Option<Reference> {
    if bytes.len() < REFERENCE_HEADER || (bytes.len() - REFERENCE_HEADER) % 16 != 0 {
        return None;
    }
    let count = u32::from_le_bytes(bytes[0..4].try_into().ok()?) as usize;
    if count == 0 || (bytes.len() - REFERENCE_HEADER) / 16 != count {
        return None;
    }
    let flags = u32::from_le_bytes(bytes[4..8].try_into().ok()?);
    let period_residual = f64::from_le_bytes(bytes[8..16].try_into().ok()?);
    let mut points = Vec::with_capacity(count);
    for index in 0..count {
        let at = REFERENCE_HEADER + index * 16;
        points.push([
            f64::from_le_bytes(bytes[at..at + 8].try_into().ok()?),
            f64::from_le_bytes(bytes[at + 8..at + 16].try_into().ok()?),
        ]);
    }
    Some(Reference {
        points,
        escaped: flags & 1 != 0,
        periodic: flags & 2 != 0,
        period_residual,
        // The limb count is the reference's own history and no part of how it is
        // read; the kernel never asks.
        limbs: 0,
    })
}

/// The smooth field for the listed samples, as little-endian `f64` in list order.
///
/// A sample is named by its global index into the supersampled grid, `row · W + col`
/// with `W` the sample width: the index the `values` array of a whole field stores it
/// at. **Each sample is the same arithmetic [`compute_rows`] does for it** — the same
/// kernel at the same entry, the same `dc` from the same offset, the same
/// monomorphization — so its eight bytes are bit for bit the eight a band covering its
/// row writes. What this exists for is a scattered list: the samples a GPU pass left
/// running, which rows would redo most of the frame to finish.
///
/// `BAND_RAN` and `BAND_SAVED` are the list's, as they are a band's. Null on a spec
/// that will not parse, an orbit that will not unpack, an empty list, or any index
/// outside the grid. The index list and the orbit are **borrowed**.
pub fn compute_listed(spec: &Spec, orbit: &Reference, indices: &[u32]) -> Option<Vec<u8>> {
    let samples = spec.sample_width() as u64 * spec.sample_height() as u64;
    if indices.is_empty() || indices.iter().any(|&index| index as u64 >= samples) {
        return None;
    }
    // Every line from here to the fork is `compute_rows`'s, so a sample cannot be told
    // which of the two asked for it.
    let kernel = Kernel::new(orbit, spec.maxiter(), spec.interior).at_entry(spec.entry());
    let offset = spec.centre_offset().unwrap_or((0.0, 0.0));
    let mut bytes = Vec::with_capacity(indices.len() * 8);
    macro_rules! fill_at {
        ($d:literal, $julia:literal) => {
            fill_listed::<$d, $julia>(spec, &kernel, offset, indices, &mut bytes)
        };
    }
    match (spec.degree, spec.julia.is_some()) {
        (2, false) => fill_at!(2, false),
        (2, true) => fill_at!(2, true),
        (3, false) => fill_at!(3, false),
        (3, true) => fill_at!(3, true),
        (4, false) => fill_at!(4, false),
        (4, true) => fill_at!(4, true),
        (5, false) => fill_at!(5, false),
        (5, true) => fill_at!(5, true),
        (6, false) => fill_at!(6, false),
        (6, true) => fill_at!(6, true),
        _ => return None,
    }
    Some(bytes)
}

/// [`fill`] over a list of global sample indices rather than a range of rows.
fn fill_listed<const D: usize, const JULIA: bool>(
    spec: &Spec,
    kernel: &Kernel,
    offset: (f64, f64),
    indices: &[u32],
    bytes: &mut Vec<u8>,
) {
    let width = spec.sample_width();
    #[cfg(all(target_arch = "wasm32", target_feature = "simd128"))]
    {
        let inputs: Vec<(f64, f64)> = indices
            .iter()
            .map(|&index| spec.dc(offset, index % width, index / width))
            .collect();
        let (ran, saved) = paired::<D, JULIA>(spec, kernel, &inputs, bytes);
        BAND_RAN.store(ran, Ordering::Relaxed);
        BAND_SAVED.store(saved, Ordering::Relaxed);
    }
    #[cfg(not(all(target_arch = "wasm32", target_feature = "simd128")))]
    {
        let (mut ran, mut saved) = (0u64, 0u64);
        for &index in indices {
            let (col, row) = (index % width, index / width);
            let (re, im) = spec.dc(offset, col, row);
            let outcome = kernel.sample_with::<D, JULIA>(re, im);
            ran += outcome.iterations as u64;
            if outcome.detected_interior {
                saved += spec.maxiter().saturating_sub(outcome.iterations) as u64;
            }
            bytes.extend_from_slice(&outcome.smooth.to_le_bytes());
        }
        BAND_RAN.store(ran, Ordering::Relaxed);
        BAND_SAVED.store(saved, Ordering::Relaxed);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const ANCHOR: &str = r#"{
        "schema": 1,
        "center_re": "-0.74501772828532335842941892835857434",
        "center_im": "0.14993443275456819177805709088257971",
        "width": 2e-11,
        "resolution": [480, 270]
    }"#;

    #[test]
    fn the_anchor_spec_reads_and_implies_the_audits_numbers() {
        let spec = Spec::parse(ANCHOR).unwrap();
        assert_eq!(spec.sample_width(), 480);
        assert_eq!(spec.limbs(), 3);
        assert_eq!(spec.interior, SHIPS_INTERIOR);
        // The audit's depth-aware policy gave 48,551 for this view, and the
        // engine's own formula is what that policy is.
        assert_eq!(spec.maxiter(), 48_551);
    }

    #[test]
    fn the_ceiling_is_this_crates_and_the_shape_is_the_engines() {
        // Where the engine still answers, the two agree.
        assert_eq!(cap::for_width(3.0), 4000);
        assert_eq!(cap::for_width(1.5), 5200);
        // Past the engine's ceiling this one keeps going.
        assert!(cap::for_width(1e-16) > 67_000);
        assert_eq!(cap::for_width(1e-28), 117_518);
        assert_eq!(cap::for_width(1e-300), cap::AUTOMATIC_CEILING as u32);
        assert_eq!(cap::for_width(1e30), cap::FLOOR as u32);
    }

    #[test]
    fn an_unknown_member_is_refused_rather_than_ignored() {
        let text = ANCHOR.replace("supersample", "ss").replace(
            r#""resolution": [480, 270]"#,
            r#""resolution": [480, 270], "deep": true"#,
        );
        let why = Spec::parse(&text).unwrap_err();
        assert!(why.contains("`deep`"), "{why}");
    }

    #[test]
    fn a_centre_written_as_a_number_is_refused_by_name() {
        let text = ANCHOR.replace(
            r#""-0.74501772828532335842941892835857434""#,
            "-0.74501772828532335842941892835857434",
        );
        let why = Spec::parse(&text).unwrap_err();
        assert!(why.contains("has to be a string"), "{why}");
    }

    #[test]
    #[allow(
        clippy::excessive_precision,
        reason = "the digits past f64 are the test"
    )]
    fn the_centre_offset_is_taken_in_fixed_point_and_not_in_f64() {
        let text = ANCHOR.replace(
            r#""resolution": [480, 270]"#,
            r#""resolution": [480, 270],
               "reference_re": "-0.74501772828532335842941892835857000",
               "reference_im": "0.14993443275456819177805709088257971""#,
        );
        let spec = Spec::parse(&text).unwrap();
        let (dx, dy) = spec.centre_offset().unwrap();
        assert_eq!(dy, 0.0);
        // Three limbs truncate at 2^-128, which is 2.9e-39 — six orders below
        // the offset and twenty-five below the sample spacing this view has.
        assert!((dx + 4.34e-33).abs() < 1e-38, "offset was {dx:e}");
        // The same subtraction the engine would have done.
        let narrowed =
            -0.74501772828532335842941892835857434f64 - -0.74501772828532335842941892835857000f64;
        assert_eq!(narrowed, 0.0);
    }

    /// The geometry has to be the engine's, or a deep frame would be off by half
    /// a pixel from every shallow one.
    #[test]
    fn the_sample_grid_is_the_engines() {
        let spec = Spec::parse(ANCHOR).unwrap();
        let (left, _) = spec.dc((0.0, 0.0), 0, 0);
        let (right, _) = spec.dc((0.0, 0.0), 479, 0);
        let spacing = spec.width / 480.0;
        assert!(
            (left + right).abs() < spacing * 1e-12,
            "the grid is not centred: {left:e} and {right:e}"
        );
        let (_, top) = spec.dc((0.0, 0.0), 0, 0);
        let (_, bottom) = spec.dc((0.0, 0.0), 0, 269);
        assert!(top > 0.0 && bottom < 0.0, "row 0 is not the top");
        assert!(((right - left) - spacing * 479.0).abs() < spacing * 1e-12);
    }

    #[test]
    fn a_reference_buffer_round_trips() {
        let spec = Spec::parse(ANCHOR).unwrap();
        let orbit = spec.reference_orbit().unwrap();
        let packed = pack_reference(&orbit);
        let back = unpack_reference(&packed).unwrap();
        assert_eq!(back.len(), orbit.len());
        assert_eq!(back.points[17], orbit.points[17]);
        assert_eq!(back.escaped, orbit.escaped);
        assert_eq!(back.periodic, orbit.periodic);
        assert_eq!(packed.len(), REFERENCE_HEADER + 16 * orbit.len());
        assert!(unpack_reference(&packed[..packed.len() - 1]).is_none());
        assert!(unpack_reference(&[]).is_none());
    }

    /// The cases the two pins below read: the engine's own output, written by
    /// `scratch/perturb_validate cases` and committed beside this file, standing
    /// in for a dependency on the engine crate.
    fn engine_cases() -> json::Object {
        json::object(include_str!("../smooth-cases.json"))
            .expect("smooth-cases.json is a flat object")
    }

    fn numbers<'a>(cases: &'a json::Object, key: &str) -> &'a [f64] {
        match cases.get(key) {
            Some(Value::Nums(values)) => values,
            _ => panic!("smooth-cases.json has no `{key}`"),
        }
    }

    /// **The formula, pinned bit for bit.**
    ///
    /// `smooth_count` is restated in this crate rather than imported, so the
    /// thing that has to be held to the engine is the closed form and not a
    /// whole render. These cases are the engine's own `(escape step, |z|² at it,
    /// smooth)` triples, read off `Orbit`, so the comparison iterates nothing
    /// and there is nowhere for a difference in arithmetic to hide: an exact
    /// equality is the right assertion and it holds.
    ///
    /// **Exact on Windows, where the cases were recorded**, and within
    /// [`LN_ULPS`] elsewhere: the formula's three `ln` come from the platform's C
    /// runtime, which another operating system need not round the same way. The
    /// engine holds the same formula against its own on every platform, in one run,
    /// exactly (`iterate.rs`, `the_deep_kernels_smooth_count_is_this_one`).
    #[test]
    fn the_smooth_formula_is_the_engines_to_the_last_bit() {
        let cases = engine_cases();
        let step = numbers(&cases, "step");
        let magnitude_sq = numbers(&cases, "magnitude_sq");
        let expected = numbers(&cases, "formula");
        assert!(step.len() >= 100, "only {} cases", step.len());
        for index in 0..step.len() {
            let ours = kernel::smooth_count(step[index] as u32, magnitude_sq[index]);
            let apart = ours.to_bits().abs_diff(expected[index].to_bits());
            let allowed = if cfg!(windows) { 0 } else { LN_ULPS };
            assert!(
                apart <= allowed,
                "case {index}: step {}, |z|² {:e}: {ours} against {}, {apart} ulps apart",
                step[index],
                magnitude_sq[index],
                expected[index]
            );
        }
    }

    /// How far a recorded `ln`-bearing value may sit from this platform's own, in units
    /// of the last place, where the platform is not the one that recorded it. The
    /// explorer's wasm and this box's native `ln` were measured one apart at most.
    const LN_ULPS: u64 = 4;

    /// **The field, pinned by its distribution — and the distribution is the
    /// engine's error, not this kernel's.**
    ///
    /// The same cases as a whole frame: every sample the engine drew, drawn again
    /// by this kernel. The interior mask is identical and has to be. The smooth
    /// counts are held to a *share* rather than to a worst case, and
    /// `fractal-website/explorer/perturb-wasm/tests/probe.rs` says why: run the
    /// same 311 escaping samples against a 384-bit oracle and **this kernel is
    /// nearer the truth on 307 of them and
    /// the plain `f64` loop on 4**. The ~7% that differ by more than 1e-6 are
    /// samples where `f64` has accumulated a visible error over a few thousand
    /// iterations — the audit's own finding that fidelity fails far above the
    /// coordinate wall — so tightening this assertion would be pinning the kernel
    /// to a field that is wrong.
    ///
    /// **Not one of the 311 is bit-equal**, and that is the expected answer
    /// rather than a surprise: the two loops do different arithmetic in a
    /// different order, escape counts here run to thousands, and the last place
    /// of a `f64` parts company long before that. Bit-equality has one right home
    /// and it is the closed form above.
    #[test]
    fn the_smooth_field_matches_the_engines_committed_cases() {
        let cases = engine_cases();
        let Some(Value::Str(centre_re)) = cases.get("center_re") else {
            panic!("no center_re")
        };
        let Some(Value::Str(centre_im)) = cases.get("center_im") else {
            panic!("no center_im")
        };
        let Some(Value::Num(width)) = cases.get("width") else {
            panic!("no width")
        };
        let Some(Value::Num(maxiter)) = cases.get("maxiter") else {
            panic!("no maxiter")
        };
        let dc_re = numbers(&cases, "dc_re");
        let dc_im = numbers(&cases, "dc_im");
        let smooth = numbers(&cases, "smooth");

        let maxiter = *maxiter as u32;
        let limbs = reference::limbs_for(*width, 20);
        let c_re = Fx::parse(centre_re, limbs).unwrap();
        let c_im = Fx::parse(centre_im, limbs).unwrap();
        let orbit = reference::orbit(&c_re, &c_im, maxiter, None);
        let kernel = Kernel::new(&orbit, maxiter, false);

        assert!(dc_re.len() >= 100, "only {} cases", dc_re.len());
        let (mut escaping, mut close, mut inside) = (0, 0, 0);
        for index in 0..dc_re.len() {
            let ours = kernel.sample(dc_re[index], dc_im[index]).smooth;
            // The engine writes `null` for interior, which reads back as NaN.
            let theirs = smooth[index];
            assert_eq!(
                ours.is_nan(),
                theirs.is_nan(),
                "case {index} at ({}, {}): ours {ours}, theirs {theirs}",
                dc_re[index],
                dc_im[index]
            );
            if theirs.is_nan() {
                inside += 1;
                continue;
            }
            escaping += 1;
            if (ours - theirs).abs() < 1e-6 {
                close += 1;
            }
        }
        assert!(escaping > 50 && inside > 20, "{escaping} out / {inside} in");
        assert!(
            close as f64 / escaping as f64 > 0.90,
            "only {close} of {escaping} escaping samples were within 1e-6"
        );
    }

    // ------------------------------------------------------------------ julia

    /// The anchor spec with a Julia parameter bolted on: the same deep `c`, now
    /// drawn as the Julia set of itself at `z = c`.
    fn julia_spec() -> String {
        ANCHOR.replace(
            r#""resolution": [480, 270]"#,
            r#""resolution": [480, 270],
              "julia_re": "-0.74501772828532335842941892835857434",
              "julia_im": "0.14993443275456819177805709088257971""#,
        )
    }

    #[test]
    fn a_julia_frames_reference_is_the_mandelbrot_orbit_at_the_same_c() {
        let mandelbrot = Spec::parse(ANCHOR).unwrap();
        let julia = Spec::parse(&julia_spec()).unwrap();
        assert!(julia.julia.is_some());
        // The one point of difference is the extra step a view entered at `Z₁`
        // needs; every point they share is the same point.
        let theirs = mandelbrot.reference_orbit().unwrap();
        let ours = julia.reference_orbit().unwrap();
        assert_eq!(ours.len(), theirs.len() + 1);
        assert_eq!(&ours.points[..theirs.len()], &theirs.points[..]);
    }

    /// **The origin anchor's orbit is sized for the square of the step**, and the
    /// parameter anchor's is not — the one place a frame's limb count is not the
    /// view's own.
    #[test]
    fn the_origin_anchor_is_computed_at_twice_the_bits() {
        let deep = far_spec(1e-30).replace(r#""schema": 1"#, r#""schema": 1, "anchor": "origin""#);
        let origin = Spec::parse(&deep).unwrap();
        let parameter = Spec::parse(&far_spec(1e-30)).unwrap();
        assert_eq!(parameter.limbs(), reference::limbs_for(1e-30, 480));
        assert_eq!(origin.limbs(), reference::limbs_pow(1e-30, 480, 2));
        assert!(origin.limbs() > parameter.limbs());
        // The orbit is the one that carries them.
        assert_eq!(origin.reference_orbit().unwrap().limbs, origin.limbs());
        // And a frame so narrow that even sixteen limbs cannot hold its square does not
        // fit, which the wrapper's `plan` refuses in a sentence rather than drawing at a
        // clamped count.
        let past = far_spec(1e-150).replace(r#""schema": 1"#, r#""schema": 1, "anchor": "origin""#);
        assert!(!Spec::parse(&past).unwrap().limbs_fit());
    }

    /// **The degree is a member with a default**, so every spec written before it
    /// existed is still degree two, and nothing outside two to six is drawn.
    #[test]
    fn the_degree_is_two_unless_the_spec_says_otherwise() {
        assert_eq!(Spec::parse(ANCHOR).unwrap().degree, 2);
        let with = |degree: &str| {
            ANCHOR.replace(
                r#""schema": 1"#,
                &format!(r#""schema": 1, "degree": {degree}"#),
            )
        };
        for degree in 2..=6 {
            let spec = Spec::parse(&with(&degree.to_string())).unwrap();
            assert_eq!(spec.degree, degree);
        }
        for bad in ["1", "7", "2.5", "\"3\"", "-3"] {
            let why = Spec::parse(&with(bad)).unwrap_err();
            assert!(why.contains("`degree`"), "{bad}: {why}");
        }
        // The origin anchor's orbit is sized for the step to the degree.
        let origin = far_spec(1e-12).replace(
            r#""schema": 1"#,
            r#""schema": 1, "anchor": "origin", "degree": 5"#,
        );
        let spec = Spec::parse(&origin).unwrap();
        assert_eq!(spec.limbs(), reference::limbs_pow(1e-12, 480, 5));
        // And a degree-d reference is the orbit of `z^d + c`: the Julia orbit of a
        // degree-3 frame at `c` is one point longer than the degree-3 Mandelbrot
        // orbit there, and shares every point with it, as at degree two.
        let three = ANCHOR.replace(r#""schema": 1"#, r#""schema": 1, "degree": 3"#);
        let julia = julia_spec().replace(r#""schema": 1"#, r#""schema": 1, "degree": 3"#);
        let m = Spec::parse(&three).unwrap().reference_orbit().unwrap();
        let j = Spec::parse(&julia).unwrap().reference_orbit().unwrap();
        assert_eq!(&j.points[..m.len()], &m.points[..]);
        let quadratic = Spec::parse(ANCHOR).unwrap().reference_orbit().unwrap();
        assert_ne!(
            m.points[2], quadratic.points[2],
            "degree 3 drew the quadratic orbit"
        );
    }

    #[test]
    fn the_entry_index_is_the_anchor_and_nothing_else() {
        assert_eq!(Spec::parse(ANCHOR).unwrap().entry(), 0);
        assert_eq!(Spec::parse(&julia_spec()).unwrap().entry(), 1);
        let origin = julia_spec().replace(r#""schema": 1"#, r#""schema": 1, "anchor": "origin""#);
        let spec = Spec::parse(&origin).unwrap();
        assert_eq!(spec.anchor, Anchor::Origin);
        assert_eq!(spec.entry(), 0);
    }

    /// A view centred on its anchor has an offset of exactly zero, so the pixel
    /// step is all the `f64` is carrying and the question does not arise.
    #[test]
    fn a_view_on_its_anchor_resolves_and_a_far_one_does_not() {
        let spec = Spec::parse(&julia_spec()).unwrap();
        assert!(spec.delta_ulps().is_infinite());
        assert!(Spec::parse(ANCHOR).unwrap().delta_ulps().is_infinite());

        // **The wall is a long way out, and where it is is worth pinning.** The
        // same frame moved to `z = 0` while still anchored at `z = c` has an
        // offset of about 0.76, whose ulp is 1.1e-16 — so at 2e-11 across 480
        // samples a pixel still spans 375 of them and the frame is perfectly
        // drawable. It is the deep widths that cannot afford it.
        let away = far_spec(2e-11);
        assert!(Spec::parse(&away).unwrap().delta_ulps() > 300.0);

        // Nine decades down, the same offset leaves less than one number to a
        // pixel: every sample would start from the same delta.
        let spec = Spec::parse(&far_spec(1e-20)).unwrap();
        assert!(spec.delta_ulps() < DELTA_ULPS, "{}", spec.delta_ulps());

        // And from the origin anchor the very same frame is exact. That is what
        // the second anchor is for, and the only thing it is for.
        let anchored =
            far_spec(1e-20).replace(r#""schema": 1"#, r#""schema": 1, "anchor": "origin""#);
        assert!(Spec::parse(&anchored).unwrap().delta_ulps().is_infinite());
    }

    /// The anchor's `c`, drawn as a Julia set, framed at `z = 0` — a full 0.76
    /// away from the anchor the arithmetic is measured against.
    fn far_spec(width: f64) -> String {
        julia_spec()
            .replace(
                r#""center_re": "-0.74501772828532335842941892835857434""#,
                r#""center_re": "0""#,
            )
            .replace(
                r#""center_im": "0.14993443275456819177805709088257971""#,
                r#""center_im": "0""#,
            )
            .replace(r#""width": 2e-11"#, &format!(r#""width": {width:e}"#))
    }

    #[test]
    fn the_members_that_mean_nothing_together_are_refused() {
        let with_reference = julia_spec().replace(
            r#""schema": 1"#,
            r#""schema": 1, "reference_re": "0", "reference_im": "0""#,
        );
        assert!(
            Spec::parse(&with_reference)
                .unwrap_err()
                .contains("critical orbit")
        );

        let with_period = julia_spec().replace(r#""schema": 1"#, r#""schema": 1, "period": 2838"#);
        assert!(Spec::parse(&with_period).unwrap_err().contains("nucleus"));

        // And an anchor with nothing to anchor to.
        let stray = ANCHOR.replace(r#""schema": 1"#, r#""schema": 1, "anchor": "origin""#);
        assert!(Spec::parse(&stray).unwrap_err().contains("`julia_re`"));

        // Half a parameter is not a parameter.
        let half = ANCHOR.replace(r#""schema": 1"#, r#""schema": 1, "julia_re": "0.25""#);
        assert!(Spec::parse(&half).unwrap_err().contains("julia_im"));
    }

    // ------------------------------------------------------------- the sample list

    /// **A listed sample is the band's sample, bit for bit**, at every degree, on both
    /// planes, with the interior switch either way, and supersampled: every index of the
    /// grid, listed in a scrambled order, lands on the eight bytes `compute_rows` wrote.
    #[test]
    fn a_listed_sample_is_the_bands_sample_to_the_bit() {
        let shallow = r#"{"schema": 1,
            "center_re": "-0.743643887037158704752191506114774",
            "center_im": "0.131825904205311970493132056385139",
            "width": 1e-6, "resolution": [24, 14], "maxiter": 3000"#;
        let mut specs = Vec::new();
        for degree in 2..=6 {
            for interior in [false, true] {
                specs.push(format!(
                    r#"{shallow}, "degree": {degree}, "interior": {interior}}}"#
                ));
            }
        }
        specs.push(format!(
            r#"{shallow}, "supersample": 2, "interior": true}}"#
        ));
        let small = |text: &str| {
            text.replace(r#""resolution": [480, 270]"#, r#""resolution": [20, 12]"#)
                .replace(r#""schema": 1"#, r#""schema": 1, "maxiter": 4000"#)
        };
        specs.push(small(ANCHOR));
        specs.push(small(
            &ANCHOR.replace(r#""schema": 1"#, r#""schema": 1, "interior": true"#),
        ));
        specs.push(small(&julia_spec()));
        specs.push(small(
            &julia_spec().replace(r#""schema": 1"#, r#""schema": 1, "degree": 3"#),
        ));
        for text in &specs {
            let spec = Spec::parse(text).unwrap();
            let orbit = spec.reference_orbit().unwrap();
            let rows = compute_rows(&spec, &orbit, 0, spec.sample_height());
            let total = spec.sample_width() * spec.sample_height();
            // A fixed scramble: 7 is prime to every total here.
            let indices: Vec<u32> = (0..total).map(|k| (k * 7 + 3) % total).collect();
            let listed = compute_listed(&spec, &orbit, &indices).unwrap();
            for (k, &index) in indices.iter().enumerate() {
                let at = index as usize * 8;
                assert_eq!(
                    &listed[k * 8..k * 8 + 8],
                    &rows[at..at + 8],
                    "{text} at {index}"
                );
            }
            // `BAND_RAN` is not compared here: it is one static, and the test harness
            // runs other bands beside this one. The wasm check compares it.
        }
    }

    #[test]
    fn a_list_outside_the_grid_or_empty_is_refused() {
        let spec = Spec::parse(&ANCHOR.replace("[480, 270]", "[8, 4]")).unwrap();
        let orbit = Reference {
            points: vec![[0.0, 0.0]; 4],
            escaped: false,
            periodic: false,
            period_residual: 0.0,
            limbs: 0,
        };
        assert!(compute_listed(&spec, &orbit, &[]).is_none());
        assert!(compute_listed(&spec, &orbit, &[0, 32]).is_none());
        assert!(compute_listed(&spec, &orbit, &[31]).is_some());
    }
}
