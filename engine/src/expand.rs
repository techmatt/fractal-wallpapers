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

use crate::coloring::{self, Transform};
use crate::colormap::Colormap;
use crate::family::Family;
use crate::field::{self, FieldSpec};
use crate::foci::{self, Branch, Placement, Policy};
use crate::maxiter;
use crate::resample;
use crate::rng::{self, Rng};
use crate::screen::{self, Band, Escape};
use crate::spec::{FamilySpec, decimal, default_colormap_dir, to_decimal_string};
use crate::viewport::Viewport;

/// Width of the cheap first-stage probe, in pixels.
///
/// Interior fraction is scale-robust — a frame that is 40% set at 128 pixels is
/// 40% set at 4000 — so the gate that rejects the most candidates can be
/// answered on a thumbnail. Everything past this stage costs about ten times as
/// much per candidate, which is the entire argument for the stage existing.
const PROBE_WIDTH: u32 = 128;

/// Default width of the node field the policy and the later gates read.
///
/// Wide enough that the focus finder's scales are a sensible fraction of the
/// frame, narrow enough to render a few thousand times an hour.
const NODE_WIDTH: u32 = 384;

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
    /// Not a performance limit — a correctness one. Below about `1e-13` of the
    /// coordinates' magnitude two neighbouring pixels round to the same `f64`
    /// and the render is a picture of floating-point spacing. This floor sits
    /// four decades above that, which leaves a wallpaper-fidelity render of the
    /// same location hundreds of units of last place per sample.
    pub min_width: f64,
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

/// The `f64`-reliable floor on a walk's frame width.
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
    pub candidates: Vec<Candidate>,
    pub dead: Vec<Dead>,
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

/// A frame rendered once, kept in all three of the forms the gates want.
struct Rendered {
    field: Vec<f32>,
    pixels: Vec<u8>,
    escape: Escape,
}

/// Render one frame and reduce it, once, for everything downstream.
fn render(view: &Viewport, family: &Family, cap: u32, colormap: &Colormap) -> Rendered {
    let sampled = field::render_field(view, family, cap, FieldSpec::Smooth);
    let field = sampled.fields[0].values.clone();
    let linear = coloring::colorize(&sampled.fields[0], Transform::Linear, colormap);
    let pixels = resample::downsample(
        &linear,
        view.sample_width() as usize,
        view.sample_height() as usize,
        view.out_width as usize,
        view.out_height as usize,
        view.supersample,
    );
    let escape = Escape::of(&field);
    Rendered {
        field,
        pixels,
        escape,
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

    let node_width = spec.policy.node_width;
    let node_height = ((node_width as f64 * 9.0 / 16.0).round() as u32).max(1);
    let probe_height =
        ((PROBE_WIDTH as f64 * node_height as f64 / node_width as f64).round() as u32).max(1);
    let [zoom_low, zoom_high] = spec.policy.zoom;

    let mut candidates = Vec::new();
    let mut dead = Vec::new();

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
            supersample: 1,
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

        let parent_field = render(
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

            // Stage 1 — the cheap interior cap.
            let probe = Viewport {
                center,
                width: child_width,
                out_width: PROBE_WIDTH,
                out_height: probe_height,
                supersample: 1,
            };
            let probed = field::render_field(&probe, &family, cap, FieldSpec::Smooth);
            let probe_interior = Escape::of(&probed.fields[0].values).interior_fraction;
            if gates.interior_cap > 0.0 && probe_interior >= gates.interior_cap {
                refused_by = Some(bind(refused_by, "interior_cap"));
                candidates.push(row("interior_cap", probe_interior, None, None, None));
                continue;
            }

            // Stage 2 — the node render, and the two gates that read it.
            let view = Viewport {
                center,
                width: child_width,
                out_width: node_width,
                out_height: node_height,
                supersample: 1,
            };
            let rendered = render(&view, &family, cap, &colormap);
            // The cap again, on the frame the row will actually record.
            //
            // Interior fraction is scale-robust but not scale-*identical*, so a
            // candidate that read 0.299 on the 128-pixel probe can read 0.301
            // here — and the cap is a guarantee the rest of the pipeline is
            // built on, not a filter that is usually right. Re-checking costs
            // nothing, because the number is already in hand.
            if gates.interior_cap > 0.0 && rendered.escape.interior_fraction >= gates.interior_cap {
                refused_by = Some(bind(refused_by, "interior_cap"));
                candidates.push(row(
                    "interior_cap",
                    rendered.escape.interior_fraction,
                    Some(rendered.escape),
                    None,
                    None,
                ));
                continue;
            }
            if let Some(clause) = gates.band.refusal(&rendered.escape) {
                refused_by = Some(bind(refused_by, clause));
                candidates.push(row(
                    clause,
                    rendered.escape.interior_fraction,
                    Some(rendered.escape),
                    None,
                    None,
                ));
                continue;
            }
            let occupancy =
                screen::occupancy(&rendered.pixels, node_width as usize, node_height as usize);
            if occupancy_here && occupancy < gates.occupancy_floor {
                refused_by = Some(bind(refused_by, "occupancy_floor"));
                candidates.push(row(
                    "occupancy_floor",
                    rendered.escape.interior_fraction,
                    Some(rendered.escape),
                    Some(occupancy),
                    None,
                ));
                continue;
            }

            let name = format!("node{}_c{}.jpg", node.node_id, index);
            resample::write_image(
                &spec.out_dir.join(&name),
                &rendered.pixels,
                node_width,
                node_height,
            )?;
            survivors += 1;
            candidates.push(row(
                "survived",
                rendered.escape.interior_fraction,
                Some(rendered.escape),
                Some(occupancy),
                Some(name),
            ));
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
        candidates,
        dead,
        seconds: started.elapsed().as_secs_f64(),
    })
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
}
