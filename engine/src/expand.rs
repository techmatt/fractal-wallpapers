//! One rung of a walk, for a batch of frontier nodes.
//!
//! `expand` is the engine's half of the search. It takes nodes — places a walk
//! has reached — and for each one draws a handful of candidate next frames from
//! the geometric policy, puts every candidate through the structural gates, and
//! reports the survivors with a small image of each. It chooses nothing: the
//! survivors come back in the order they were drawn, and which of them the walk
//! expands next is the walk's decision, made in Python where the scorer lives.
//!
//! ```text
//! node ──▶ field ──▶ policy ──▶ candidate ──▶ interior cap ──▶ band ──▶ occupancy ──▶ survivor
//!                       ×N                     (128 px)        (node field)         + a JPEG
//! ```
//!
//! Three properties are load-bearing, and each is a decision rather than an
//! implementation detail:
//!
//! * **Every candidate is reported, survivor or not.** A rejected candidate
//!   carries the gate that refused it, because a walk that only records what it
//!   kept cannot afterwards say what it was refusing — and "the gates were too
//!   tight" and "there was nothing there" look identical from the survivors
//!   alone.
//! * **A node expands identically wherever it is popped.** The stream comes from
//!   `(seed, node_id)`, so a rung is reproducible on its own, out of order, in a
//!   different batch, a week later.
//! * **A frame's readings are taken once, not once per draw.** The candidates
//!   of one rung all come off the same parent render, and two of the three
//!   proposal branches are pure functions of it. Measured on a real julia leg:
//!   the focus finder was 47% of expansion at 105 ms a call, 117 calls over 44
//!   distinct frames, because it ran per candidate. [`foci::Frame`] is where
//!   that became per node, and it took 34% off expansion for a bit-identical
//!   ledger. The rest of the clock is where it looks: the child renders 27%,
//!   occupancy 15%, the parent render 6%, the probes 3%, the JPEGs 2%.
//! * **The gate render is the reported image.** The source project rendered the
//!   gates at one iteration cap and the thumbnail at another, and paid for both;
//!   here the cap is a function of the frame's width, so the two are the same
//!   render and the picture is literally the thing the gates measured.
//!
//! The images are JPEG because there are a great many of them. A walk that
//! expands a few thousand nodes writes tens of thousands of these, and they are
//! steering material — looked at in bulk, fed to a scorer, then thrown away.
//! That is the one place in this engine where a lossy format is the right
//! answer (measured: the same frames are a median 2.4× larger as PNGs), and it
//! is why [`crate::resample::write_image`] picks its encoder from the file name
//! instead of the caller stating it.

use std::path::PathBuf;
use std::time::Instant;

use num_complex::Complex;
use serde::{Deserialize, Serialize};

use crate::colormap::Colormap;
use crate::foci::{self, Branch, Focus, Placement, Policy};
use crate::maxiter;
use crate::resample;
use crate::rng::{self, Rng};
use crate::screen::{self, Band, Battery, Escape, NODE_SUPERSAMPLE, NODE_WIDTH, node_height};
use crate::spec::{FamilySpec, decimal, default_colormap_dir, to_decimal_string};
use crate::viewport::Viewport;

/// A batch of rungs to expand.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ExpandSpec {
    pub schema: u32,
    /// The family every node in this batch belongs to. A batch is homogeneous:
    /// the family is part of a location's identity, so a batch that mixed two
    /// would be two walks sharing a report.
    pub family: FamilySpec,
    /// The run's seed. A node's own stream is derived from this and its id.
    pub seed: u64,
    pub nodes: Vec<Node>,
    /// Where the thumbnails go. Written as `<out_dir>/node<id>_c<index>.jpg`.
    pub out_dir: PathBuf,
    pub colormap: String,
    #[serde(default = "default_colormap_dir")]
    pub colormap_dir: PathBuf,
    #[serde(default)]
    pub gates: Gates,
    #[serde(default)]
    pub policy: PolicySpec,
    /// Whether the report carries each node's kept focus set.
    ///
    /// **Off, and a production report is byte-identical without it.** The focus
    /// set is a reading of the parent frame and is already taken — the flag
    /// decides whether it is *reported*, not whether it is computed, so a run
    /// with it on draws the same candidates from the same stream as a run with
    /// it off. It is off because a walk writes tens of thousands of these rungs
    /// and nothing in the walk reads a focus it did not aim at.
    #[serde(default)]
    pub report_foci: bool,
}

/// One frontier node: a place the walk has reached, and how it got there.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Node {
    pub node_id: u64,
    /// The root this node descends from. Carried through untouched so the walk
    /// can hold a per-root budget without the engine knowing what one is.
    pub root_id: u64,
    pub center_re: String,
    pub center_im: String,
    pub width: String,
    /// Rungs from the root. The first rung is depth 1.
    pub depth: u32,
}

/// The structural gates, and the floor on how deep a rung may go.
#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Gates {
    /// Interior share at or above which a candidate is refused.
    pub interior_cap: f64,
    /// Share of tiles that must carry detail.
    pub occupancy_floor: f64,
    /// Whether the occupancy floor applies at the first rung.
    ///
    /// It over-fires there: a root frame is wide and still resolving structure
    /// that the first, much tighter child has not entered yet, so the floor
    /// kills children that would have been fine one rung later. Off by default,
    /// and on from the second rung regardless.
    pub occupancy_at_first_rung: bool,
    pub band: Band,
    /// Frame width below which a rung is not taken.
    ///
    /// **A policy, not the `f64` wall.** The wall is
    /// [`crate::viewport::Viewport::is_resolvable_in_f64`] and it is relative to
    /// the coordinates' own magnitude: at a finished wallpaper's geometry it
    /// falls between `2e-12` and `9e-12` over the c-plane. So [`MIN_WIDTH`] is
    /// two to three decades of headroom above it, and not the "four decades"
    /// this comment used to claim — an arithmetic that compared a *width*
    /// against a *spacing*. A deep descent passes its own value here.
    pub min_width: f64,
}

impl Gates {
    /// The three thresholds, as the battery that reads them takes them.
    pub fn battery(&self) -> Battery {
        Battery {
            interior_cap: self.interior_cap,
            occupancy_floor: self.occupancy_floor,
            band: self.band,
        }
    }
}

impl Default for Gates {
    fn default() -> Gates {
        Gates {
            interior_cap: screen::INTERIOR_CAP,
            occupancy_floor: screen::OCCUPANCY_FLOOR,
            occupancy_at_first_rung: false,
            band: Band::default(),
            min_width: MIN_WIDTH,
        }
    }
}

/// The floor on a shallow walk's frame width.
///
/// Bring-up insurance that stayed: it keeps a walk inside the regime this
/// engine's `f64` arithmetic was measured in, well above where the arithmetic
/// actually fails. The deep run mode sets its own.
pub const MIN_WIDTH: f64 = 1e-9;

/// How the policy is configured for this batch.
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PolicySpec {
    /// Candidate next-frames drawn per node.
    pub candidates: usize,
    pub node_width: u32,
    /// Branch weights `[foci, density, random]`.
    pub branch_weights: [f64; 3],
    /// Placement weights `[center, horizon, offset]`.
    pub placement: [f64; 3],
    /// Minimum separation between kept foci, as a fraction of the frame width.
    pub focus_spread: f64,
    /// Log-uniform band the per-rung zoom factor is drawn from.
    pub zoom: [f64; 2],
    pub sigmas: Vec<f64>,
}

impl Default for PolicySpec {
    fn default() -> PolicySpec {
        let policy = Policy::default();
        PolicySpec {
            candidates: 4,
            node_width: NODE_WIDTH,
            branch_weights: [policy.branch.0, policy.branch.1, policy.branch.2],
            placement: [policy.placement.0, policy.placement.1, policy.placement.2],
            focus_spread: policy.focus_spread,
            zoom: [0.35, 0.50],
            sigmas: policy.sigmas,
        }
    }
}

impl PolicySpec {
    fn policy(&self) -> Policy {
        Policy {
            branch: (
                self.branch_weights[0],
                self.branch_weights[1],
                self.branch_weights[2],
            ),
            placement: (self.placement[0], self.placement[1], self.placement[2]),
            focus_spread: self.focus_spread,
            sigmas: self.sigmas.clone(),
        }
    }
}

/// One candidate frame, and what the gates made of it.
#[derive(Debug, Serialize)]
pub struct Candidate {
    pub node_id: u64,
    pub root_id: u64,
    pub parent_depth: u32,
    pub depth: u32,
    /// Which of this node's draws this was. Part of the thumbnail's name.
    pub child_index: usize,
    /// The candidate's location, as the decimal strings it will be recorded as.
    pub center_re: String,
    pub center_im: String,
    pub width: String,
    pub branch: &'static str,
    pub placement: &'static str,
    /// The focus's sampling score, when the foci branch proposed it.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub focus_score: Option<f64>,
    pub maxiter: u32,
    pub interior_fraction: f64,
    /// Absent for a candidate the interior cap refused: it never had a node
    /// render, so the numbers that come off one do not exist for it.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub escape: Option<Escape>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub occupancy: Option<f64>,
    /// `"survived"`, or the gate that refused this candidate.
    pub fate: &'static str,
    /// The thumbnail, for a survivor.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub image: Option<String>,
}

/// One kept focus of a node's parent frame, as the report carries it.
///
/// The whole subject of a proposal is the set this describes: peaks of the
/// smoothed escape field that survived at one or more blurring scales, ranked by
/// how alone each stands, and thinned so two of them are never the same place.
/// Everything here is *reported* — the sampling weight is `score` and it is
/// exactly what it was before this row existed.
#[derive(Debug, Serialize)]
pub struct ReportedFocus {
    /// Where the peak is in the parent frame, in field pixels: column and row,
    /// row 0 at the top. The frame's own geometry is [`ExpandReport::tile`].
    pub x: f64,
    pub y: f64,
    /// The same point in the plane, as the decimal strings a location is written
    /// in — so a focus can be framed and rendered without re-deriving the pixel
    /// mapping on the reader's side.
    pub center_re: String,
    pub center_im: String,
    /// Peak height in standard deviations above its scale's exterior mean.
    pub peak: f64,
    /// Peak over the local field mean at twice the scale: how alone it stands.
    pub isolation: f64,
    /// `peak × isolation` — the weight the foci branch samples by.
    pub score: f64,
    /// The blurring scales that detected this peak, in field pixels. The
    /// per-sigma survival, spelled out rather than counted.
    pub sigmas: Vec<f64>,
    /// Distance in field pixels to the nearest other kept focus, or `null` when
    /// this is the only one. Every value here is above the spread radius by
    /// construction — that is what the thinning did — and this is what says by
    /// how much.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub spacing: Option<f64>,
}

/// One node's focus set: what the finder found, and what survived the thinning.
#[derive(Debug, Serialize)]
pub struct NodeFoci {
    pub node_id: u64,
    pub root_id: u64,
    /// The depth of the *parent* frame these were read off, not of its children.
    pub depth: u32,
    /// Maxima the finder returned, before any were dropped for landing on top of
    /// a better one. The difference between this and `kept.len()` is the whole
    /// cost of the spread rule.
    pub found: usize,
    /// Minimum separation between kept foci, in field pixels: the policy's
    /// `focus_spread` against this frame's width.
    pub spread_radius: f64,
    pub kept: Vec<ReportedFocus>,
}

/// A node that produced no survivor, and the constraint that bound.
#[derive(Debug, Serialize)]
pub struct Dead {
    pub node_id: u64,
    pub root_id: u64,
    pub parent_depth: u32,
    pub depth: u32,
    pub cause: &'static str,
}

/// What one batch of rungs did.
#[derive(Debug, Serialize)]
pub struct ExpandReport {
    pub schema: u32,
    pub nodes: usize,
    /// The geometry every picture in this report was drawn at, and the field
    /// sampling behind it — the same two names a tile build's recipe uses.
    ///
    /// Stated rather than assumed. The walk scores the gate render through a head
    /// trained on tiles, which is only the same question if the two are the same
    /// picture, and the frame size is one of the things that would make them two.
    /// The reader gets it from the engine that drew them instead of re-deriving
    /// the aspect rule on its own side.
    pub tile: [u32; 2],
    pub field_supersample: u32,
    pub candidates: Vec<Candidate>,
    pub dead: Vec<Dead>,
    /// Each node's kept focus set, present only when the spec asked for it. A
    /// node that never reached a parent render — one the width floor stopped —
    /// contributes no entry, because it has no frame to have read foci off.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub foci: Option<Vec<NodeFoci>>,
    pub seconds: f64,
}

impl ExpandSpec {
    /// Read an expand spec from JSON text.
    pub fn parse(text: &str) -> Result<ExpandSpec, String> {
        let spec: ExpandSpec = serde_json::from_str(text).map_err(|e| format!("spec: {e}"))?;
        if spec.schema != 1 {
            return Err(format!("spec has schema {}, expected 1", spec.schema));
        }
        if spec.policy.candidates == 0 {
            return Err("policy.candidates must be at least 1".into());
        }
        if spec.policy.node_width < 32 {
            return Err(format!(
                "policy.node_width {} is too small for the focus finder's scales",
                spec.policy.node_width
            ));
        }
        if !spec.gates.min_width.is_finite() || spec.gates.min_width <= 0.0 {
            return Err("gates.min_width must be positive".into());
        }
        Ok(spec)
    }
}

/// Expand every node in `spec` by one rung.
pub fn run(spec: ExpandSpec) -> Result<ExpandReport, String> {
    let started = Instant::now();
    let resolved = spec.family.resolve()?;
    let family = resolved.family;
    if family.is_render_only() {
        return Err(crate::spec::render_only_refusal(resolved.kind, "walked"));
    }
    let colormap = Colormap::load(&spec.colormap_dir, &spec.colormap)?;
    let policy = spec.policy.policy();
    let gates = spec.gates;
    let battery = gates.battery();

    let node_width = spec.policy.node_width;
    let node_height = node_height(node_width);
    let [zoom_low, zoom_high] = spec.policy.zoom;

    let mut candidates = Vec::new();
    let mut dead = Vec::new();
    let mut reported_foci: Vec<NodeFoci> = Vec::new();

    for node in &spec.nodes {
        let mut rng = Rng(rng::sub_seed(spec.seed, node.node_id));
        let depth = node.depth + 1;
        let parent = Viewport {
            center: Complex::new(
                decimal(&node.center_re, "node.center_re")?,
                decimal(&node.center_im, "node.center_im")?,
            ),
            width: decimal(&node.width, "node.width")?,
            out_width: node_width,
            out_height: node_height,
            supersample: NODE_SUPERSAMPLE,
        };
        if !parent.width.is_finite() || parent.width <= 0.0 {
            return Err(format!("node {}: width must be positive", node.node_id));
        }

        // One zoom draw per rung, shared by every candidate. The rung is a step
        // to a *scale*; the candidates are proposals about where to put a frame
        // at that scale, and drawing a zoom per candidate would confound the two.
        let child_width = parent.width * rng.log_uniform(zoom_low, zoom_high);
        if child_width < gates.min_width {
            dead.push(Dead {
                node_id: node.node_id,
                root_id: node.root_id,
                parent_depth: node.depth,
                depth,
                cause: "width_floor",
            });
            continue;
        }
        let child_height = child_width * node_height as f64 / node_width as f64;

        let parent_field = screen::render_frame(
            &parent,
            &family,
            maxiter::for_width(parent.width),
            &colormap,
        );
        let occupancy_here =
            gates.occupancy_floor > 0.0 && (node.depth > 1 || gates.occupancy_at_first_rung);

        // One frame for the node, not one per draw: the focus set and the
        // centroid are readings of the parent render, and every candidate of
        // this rung would otherwise take them again off the same pixels.
        let mut frame = foci::Frame::new(&parent, &parent_field.field, &parent_field.pixels);

        let mut survivors = 0usize;
        let mut refused_by: Option<&'static str> = None;
        for index in 0..spec.policy.candidates {
            let target = frame.propose(&policy, &mut rng);
            // The random branch is always centered: it is there to sample the
            // plane evenly, and offsetting it would re-introduce the very bias
            // the branch exists to counter.
            let placement = if target.branch == Branch::Random {
                Placement::Center
            } else {
                foci::pick_placement(policy.placement, &mut rng)
            };
            let center =
                foci::child_center(target.point, placement, child_width, child_height, &mut rng);
            let cap = maxiter::for_width(child_width);

            let row = |fate: &'static str,
                       interior: f64,
                       escape: Option<Escape>,
                       occupancy: Option<f64>,
                       image: Option<String>| Candidate {
                node_id: node.node_id,
                root_id: node.root_id,
                parent_depth: node.depth,
                depth,
                child_index: index,
                center_re: to_decimal_string(center.re),
                center_im: to_decimal_string(center.im),
                width: to_decimal_string(child_width),
                branch: target.branch.name(),
                placement: placement.name(),
                focus_score: target.score.is_finite().then_some(target.score),
                maxiter: cap,
                interior_fraction: interior,
                escape,
                occupancy,
                fate,
                image,
            };

            // The gates themselves, in the order they cost money. The
            // battery is `screen`'s and not this module's, so the `screen`
            // subcommand and a walk cannot come to different verdicts about one
            // frame — which is a real risk once two callers exist, and the
            // reason the battery moved rather than being copied.
            let view = Viewport {
                center,
                width: child_width,
                out_width: node_width,
                out_height: node_height,
                supersample: NODE_SUPERSAMPLE,
            };
            let screening = battery.screen(&view, &family, cap, &colormap, occupancy_here);
            let escape = screening.framed.as_ref().map(|framed| framed.escape);
            if !screening.passed() {
                refused_by = Some(bind(refused_by, screening.fate));
                candidates.push(row(
                    screening.fate,
                    screening.interior_fraction(),
                    escape,
                    screening.occupancy,
                    None,
                ));
                continue;
            }

            let framed = screening.framed.expect("a survivor has a node render");
            let name = format!("node{}_c{}.jpg", node.node_id, index);
            resample::write_image(
                &spec.out_dir.join(&name),
                &framed.pixels,
                node_width,
                node_height,
            )?;
            survivors += 1;
            candidates.push(row(
                "survived",
                framed.escape.interior_fraction,
                Some(framed.escape),
                screening.occupancy,
                Some(name),
            ));
        }

        // After the draws, so the focus set is whatever the draws already
        // caused to be taken — and taken here where it was not, which costs a
        // reading and consumes nothing from the node's stream. That is what
        // makes a report with this on carry the same candidates as one without.
        if spec.report_foci {
            let spread_radius = policy.focus_spread * parent.out_width as f64;
            let found = frame.focus_count(&policy);
            let kept = frame.kept_foci(&policy);
            reported_foci.push(NodeFoci {
                node_id: node.node_id,
                root_id: node.root_id,
                depth: node.depth,
                found,
                spread_radius,
                kept: kept
                    .iter()
                    .map(|focus| reported(focus, kept, &parent, &policy.sigmas))
                    .collect(),
            });
        }

        if survivors == 0 {
            dead.push(Dead {
                node_id: node.node_id,
                root_id: node.root_id,
                parent_depth: node.depth,
                depth,
                cause: refused_by.unwrap_or("no_candidate"),
            });
        }
    }

    Ok(ExpandReport {
        schema: 1,
        nodes: spec.nodes.len(),
        tile: [node_width, node_height],
        field_supersample: NODE_SUPERSAMPLE,
        candidates,
        dead,
        foci: spec.report_foci.then_some(reported_foci),
        seconds: started.elapsed().as_secs_f64(),
    })
}

/// One kept focus as the report carries it, spacing and sigmas resolved.
fn reported(focus: &Focus, kept: &[Focus], view: &Viewport, sigmas: &[f64]) -> ReportedFocus {
    let point = foci::pixel_to_point(view, focus.x, focus.y);
    let spacing = kept
        .iter()
        .filter(|other| !std::ptr::eq(*other, focus))
        .map(|other| ((other.x - focus.x).powi(2) + (other.y - focus.y).powi(2)).sqrt())
        .fold(f64::INFINITY, f64::min);
    ReportedFocus {
        x: focus.x,
        y: focus.y,
        center_re: to_decimal_string(point.re),
        center_im: to_decimal_string(point.im),
        peak: focus.peak,
        isolation: focus.isolation,
        score: focus.score,
        sigmas: focus.detected_at(sigmas),
        spacing: spacing.is_finite().then_some(spacing),
    }
}

/// The binding constraint on a node, when every candidate was refused.
///
/// The furthest-reached gate wins: a node whose candidates all died at the
/// interior cap was never measured for occupancy, so reporting "occupancy" for
/// it would name a gate that never ran. Ordering them by how far the candidate
/// got is what makes the tally of causes mean something.
fn bind(seen: Option<&'static str>, cause: &'static str) -> &'static str {
    let rank = |name: &str| match name {
        "interior_cap" => 0,
        "instant_escape" | "flat" => 1,
        "occupancy_floor" => 2,
        _ => 0,
    };
    match seen {
        Some(previous) if rank(previous) >= rank(cause) => previous,
        _ => cause,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn spec_text(nodes: &str, extra: &str) -> String {
        format!(
            r#"{{"schema":1,"family":{{"kind":"mandelbrot"}},"seed":7,
                "nodes":[{nodes}],"out_dir":"{}",
                "colormap":"twilight_shifted","colormap_dir":"../data/palettes"
                {extra}}}"#,
            temp_dir().display().to_string().replace('\\', "/")
        )
    }

    fn temp_dir() -> PathBuf {
        std::env::temp_dir().join("fractal_engine_expand")
    }

    fn node(id: u64, center: (&str, &str), width: &str, depth: u32) -> String {
        format!(
            r#"{{"node_id":{id},"root_id":1,"center_re":"{}","center_im":"{}",
                "width":"{width}","depth":{depth}}}"#,
            center.0, center.1
        )
    }

    /// A walk is discovery, and a render-only family is not discoverable: it is
    /// refused before a single node is drawn, so there is no way for one to
    /// reach a ledger, a supply book, or a seed pool by way of a walk.
    #[test]
    fn a_render_only_family_cannot_be_walked() {
        let text = spec_text(&node(1, ("-0.5", "0"), "3.0", 1), "").replace(
            r#""family":{"kind":"mandelbrot"}"#,
            r#""family":{"kind":"fractional_multibrot","degree":"2.5"}"#,
        );
        let message = run(ExpandSpec::parse(&text).unwrap()).unwrap_err();
        assert!(message.contains("render-only"), "{message}");
    }

    #[test]
    fn a_spec_of_the_wrong_schema_is_refused() {
        let text = spec_text(&node(1, ("-0.5", "0"), "3.0", 1), "")
            .replace("\"schema\":1", "\"schema\":2");
        assert!(ExpandSpec::parse(&text).unwrap_err().contains("schema"));
    }

    #[test]
    fn a_policy_that_draws_nothing_is_refused() {
        let text = spec_text(
            &node(1, ("-0.5", "0"), "3.0", 1),
            r#","policy":{"candidates":0,"node_width":384,"branch_weights":[0.7,0.1,0.2],
                "placement":[0.25,0.4,0.35],"focus_spread":0.12,"zoom":[0.35,0.5],
                "sigmas":[8,10,12,14,16]}"#,
        );
        assert!(ExpandSpec::parse(&text).unwrap_err().contains("candidates"));
    }

    /// The floor is checked against the width the rung would land at, not the
    /// one it starts from — a node just above it must still refuse to step.
    #[test]
    fn a_rung_that_would_cross_the_width_floor_is_not_taken() {
        let text = spec_text(&node(1, ("-0.5", "0"), "1.5e-9", 1), "");
        let report = run(ExpandSpec::parse(&text).unwrap()).unwrap();
        assert!(report.candidates.is_empty());
        assert_eq!(report.dead.len(), 1);
        assert_eq!(report.dead[0].cause, "width_floor");
        assert_eq!(report.dead[0].depth, 2);
    }

    #[test]
    fn every_candidate_is_reported_with_a_fate() {
        let text = spec_text(&node(1, ("-0.5", "0"), "3.0", 1), "");
        let report = run(ExpandSpec::parse(&text).unwrap()).unwrap();
        assert_eq!(report.candidates.len(), 4, "one row per draw");
        for candidate in &report.candidates {
            assert!(!candidate.fate.is_empty());
            assert_eq!(candidate.depth, 2);
            assert!(candidate.width.parse::<f64>().unwrap() < 3.0);
            assert_eq!(candidate.image.is_some(), candidate.fate == "survived");
        }
    }

    /// The report says what geometry it drew at, because the reader scores those
    /// pictures through a head trained at one geometry and cannot check that from
    /// the pictures themselves.
    #[test]
    fn the_report_states_the_regime_every_picture_was_drawn_at() {
        let text = spec_text(&node(1, ("-0.5", "0"), "3.0", 1), "");
        let report = run(ExpandSpec::parse(&text).unwrap()).unwrap();
        assert_eq!(report.tile, [NODE_WIDTH, 216]);
        assert_eq!(report.field_supersample, 1);

        let wider = spec_text(
            &node(1, ("-0.5", "0"), "3.0", 1),
            r#","policy":{"candidates":2,"node_width":640,"branch_weights":[0.7,0.1,0.2],
                "placement":[0.25,0.4,0.35],"focus_spread":0.12,"zoom":[0.35,0.5],
                "sigmas":[8,10,12,14,16]}"#,
        );
        let report = run(ExpandSpec::parse(&wider).unwrap()).unwrap();
        assert_eq!(
            report.tile,
            [640, 360],
            "the height follows the frame's own aspect"
        );
    }

    /// Reproducibility is the property the whole record rests on: the same node
    /// under the same seed must produce the same rung, whatever else ran first.
    #[test]
    fn a_node_expands_identically_however_the_batch_is_ordered() {
        let one =
            run(ExpandSpec::parse(&spec_text(&node(9, ("-0.5", "0"), "3.0", 1), "")).unwrap())
                .unwrap();
        let batch = format!(
            "{},{}",
            node(4, ("-0.75", "0.1"), "1.0", 2),
            node(9, ("-0.5", "0"), "3.0", 1)
        );
        let many = run(ExpandSpec::parse(&spec_text(&batch, "")).unwrap()).unwrap();
        let mine: Vec<_> = many
            .candidates
            .iter()
            .filter(|c| c.node_id == 9)
            .map(|c| (&c.center_re, &c.center_im, &c.width, c.fate))
            .collect();
        let alone: Vec<_> = one
            .candidates
            .iter()
            .map(|c| (&c.center_re, &c.center_im, &c.width, c.fate))
            .collect();
        assert_eq!(mine, alone);
    }

    /// The interior cap is the guarantee everything downstream is built on, so
    /// nothing may leave this stage above it — measured on the frame the row
    /// records, not on the cheaper probe the gate first ran on.
    #[test]
    fn no_survivor_is_ever_above_the_interior_cap() {
        let batch = format!(
            "{},{},{}",
            node(1, ("-0.5", "0"), "3.0", 1),
            node(2, ("-0.75", "0.1"), "0.4", 2),
            node(3, ("-0.1", "0.9"), "0.2", 3)
        );
        let report = run(ExpandSpec::parse(&spec_text(&batch, "")).unwrap()).unwrap();
        let mut survivors = 0;
        for candidate in &report.candidates {
            if candidate.fate == "survived" {
                survivors += 1;
                assert!(
                    candidate.interior_fraction < screen::INTERIOR_CAP,
                    "{} escaped the cap",
                    candidate.interior_fraction
                );
            }
        }
        assert!(survivors > 0, "the whole set should yield somewhere to go");
    }

    /// A node deep inside the set is exactly what the cap exists to stop, and
    /// the cause it dies of has to name that gate rather than a later one.
    #[test]
    fn a_node_inside_the_set_dies_at_the_interior_cap() {
        let text = spec_text(&node(5, ("-0.5", "0"), "0.05", 3), "");
        let report = run(ExpandSpec::parse(&text).unwrap()).unwrap();
        assert_eq!(report.dead.len(), 1, "{:?}", report.candidates);
        assert_eq!(report.dead[0].cause, "interior_cap");
        assert!(
            report
                .candidates
                .iter()
                .all(|c| c.fate == "interior_cap" && c.escape.is_none())
        );
    }

    /// The whole promise of the flag: a run that reports its foci draws the same
    /// candidates as one that does not. The focus set is a reading of the parent
    /// frame and consumes nothing from the node's stream, so turning the report
    /// on may add a key and may not move a single coordinate.
    #[test]
    fn reporting_the_foci_leaves_every_candidate_exactly_where_it_was() {
        let node = node(4, ("-0.75", "0.1"), "0.4", 2);
        let quiet = run(ExpandSpec::parse(&spec_text(&node, "")).unwrap()).unwrap();
        let loud =
            run(ExpandSpec::parse(&spec_text(&node, r#","report_foci":true"#)).unwrap()).unwrap();

        assert!(quiet.foci.is_none(), "off by default");
        assert!(loud.foci.is_some());
        let strip = |report: &ExpandReport| {
            let mut value = serde_json::to_value(report).unwrap();
            let object = value.as_object_mut().unwrap();
            object.remove("foci");
            object.remove("seconds");
            value
        };
        assert_eq!(strip(&quiet), strip(&loud));
    }

    /// What the report says about a focus is what the finder actually decided:
    /// which blurring scales saw it, how alone it stands, and how far the
    /// nearest kept neighbour is — which the spread rule guarantees is at least
    /// the radius it thinned at.
    #[test]
    fn a_reported_focus_carries_the_scales_that_found_it_and_its_spacing() {
        let report = run(ExpandSpec::parse(&spec_text(
            &node(4, ("-0.75", "0.1"), "0.4", 2),
            r#","report_foci":true"#,
        ))
        .unwrap())
        .unwrap();
        let nodes = report.foci.unwrap();
        assert_eq!(nodes.len(), 1);
        let found = &nodes[0];
        assert_eq!(found.node_id, 4);
        assert_eq!(found.depth, 2, "the parent's depth, not its children's");
        assert!(found.found >= found.kept.len(), "thinning never adds one");
        assert!(!found.kept.is_empty(), "this frame has structure in it");

        let sigmas = PolicySpec::default().sigmas;
        for focus in &found.kept {
            assert!(!focus.sigmas.is_empty(), "a focus was detected somewhere");
            for sigma in &focus.sigmas {
                assert!(sigmas.contains(sigma), "{sigma} is not a scale we swept");
            }
            assert!(focus.score > 0.0);
            assert_eq!(focus.score, focus.peak.max(0.0) * focus.isolation.max(0.0));
            if let Some(spacing) = focus.spacing {
                assert!(
                    spacing > found.spread_radius,
                    "{spacing} is inside the radius the spread rule thinned at"
                );
            }
        }
    }
}
