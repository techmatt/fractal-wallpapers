//! Where to look next: the walk's proposal policy.
//!
//! One rung of a walk asks a single question — given this frame, where inside it
//! should the next, smaller frame go? The answer is a *geometric* one. Nothing
//! here knows whether a picture is any good; it knows where a frame has
//! structure and where it does not, and it aims there. Judgement arrives later,
//! from a scorer, and reads what this proposed rather than replacing it.
//!
//! Three branches, drawn by weight:
//!
//! ```text
//! foci      a scale-space maximum of the smoothed escape field
//! density   the detail-weighted centroid of the frame
//! random    a uniform point well inside the frame
//! ```
//!
//! **Foci** is the interesting one. Smooth the escape field at several scales,
//! take the local maxima, and score each by peak response × isolation — *not* by
//! persistence across scales. Persistence rewards mass, so it walks into
//! thickets: the largest, busiest blob wins every time and the walk stops
//! finding anything else. Isolation rewards a peak that stands alone against its
//! own neighbourhood, which is what a spiral eye looks like from above.
//!
//! **Random** is the measure-uniformity injection. A walk that only ever
//! descends into what the field points at samples the plane by the field's
//! measure rather than by area, and quietly stops visiting whole kinds of place.
//! The source project drew this branch from a thin band near the set, using a
//! distance estimate this engine does not compute yet; until it does, the branch
//! draws uniformly inside the frame, which is what that project did for its
//! dynamical families for the same reason.

use num_complex::Complex;

use crate::rng::Rng;
use crate::screen::{DETAIL_FLOOR, OCCUPANCY_TILES, tile_energy};
use crate::viewport::Viewport;

/// Scales the focus finder smooths at, in field pixels.
///
/// Five of them, spanning a factor of two: a spiral eye is a blob at whatever
/// size it happens to be, and a single scale finds only the blobs near it.
pub const SIGMAS: [f64; 5] = [8.0, 10.0, 12.0, 14.0, 16.0];

/// A candidate maximum must sit above this quantile of its own scale's exterior
/// field. Without it every gentle undulation is a local maximum.
const MAXIMUM_FLOOR_QUANTILE: f64 = 0.85;

/// Most foci a frame reports, best first.
const TOP_FOCI: usize = 16;

/// The escape field is clipped at this quantile of its exterior values before
/// smoothing.
///
/// Escape time diverges at the boundary, so an unclipped smoothed field is
/// monotone toward the set: its only maxima are against the set's edge, and the
/// finder returns the boundary every time. Clipping saturates that band so an
/// isolated exterior ridge can win.
const CLIP_QUANTILE: f64 = 0.90;

/// Which branch proposed a target.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Branch {
    Foci,
    Density,
    Random,
}

impl Branch {
    pub fn name(self) -> &'static str {
        match self {
            Branch::Foci => "foci",
            Branch::Density => "density",
            Branch::Random => "random",
        }
    }
}

/// Where the chosen target lands inside the child frame.
///
/// A walk that always centers its target produces a column of concentric
/// frames, each a crop of the last, and the shallow rungs of every walk look
/// alike. Placing the target off-center is the dial that decorrelates them.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Placement {
    Center,
    Horizon,
    Offset,
}

impl Placement {
    pub fn name(self) -> &'static str {
        match self {
            Placement::Center => "center",
            Placement::Horizon => "horizon",
            Placement::Offset => "offset",
        }
    }
}

/// One maximum of the smoothed field, in field-pixel coordinates.
#[derive(Clone, Copy, Debug)]
pub struct Focus {
    pub x: f64,
    pub y: f64,
    /// Peak height in standard deviations above its scale's exterior mean.
    pub peak: f64,
    /// Peak divided by the local field mean — how alone this peak stands.
    pub isolation: f64,
    /// How many scales detected it. Reported, never used as the sampling weight.
    pub scales: u32,
    /// *Which* scales detected it, one bit per entry of the sigma list, low bit
    /// first. A bitmask rather than a list because a [`Focus`] is `Copy` and is
    /// copied per draw; [`Focus::detected_at`] spells it back out against the
    /// sigmas it was found with. `scales` is this many bits set.
    pub detected: u32,
    /// `peak × isolation`: the weight it is sampled by.
    pub score: f64,
}

impl Focus {
    /// The blurring scales that detected this peak, in field pixels.
    ///
    /// The per-sigma survival as a reader wants it: the sigma values themselves,
    /// in the order the finder swept them, rather than a mask nobody outside this
    /// module can decode.
    pub fn detected_at(&self, sigmas: &[f64]) -> Vec<f64> {
        sigmas
            .iter()
            .enumerate()
            .filter(|(index, _)| *index < 32 && self.detected & (1 << index) != 0)
            .map(|(_, sigma)| *sigma)
            .collect()
    }
}

/// The proposal policy's weights.
#[derive(Clone, Debug)]
pub struct Policy {
    /// Branch weights, `(foci, density, random)`. Normalized on use.
    pub branch: (f64, f64, f64),
    /// Placement weights, `(center, horizon, offset)`. Normalized on use.
    pub placement: (f64, f64, f64),
    /// Foci closer than this fraction of the frame width to an already-kept,
    /// higher-scoring focus are dropped before the weighted draw.
    pub focus_spread: f64,
    pub sigmas: Vec<f64>,
}

impl Default for Policy {
    fn default() -> Policy {
        Policy {
            branch: (0.70, 0.10, 0.20),
            placement: (0.25, 0.40, 0.35),
            focus_spread: 0.12,
            sigmas: SIGMAS.to_vec(),
        }
    }
}

/// A proposed target: where to aim, and which branch said so.
pub struct Target {
    pub point: Complex<f64>,
    pub branch: Branch,
    /// The focus's sampling score, or `NaN` for the branches that have none.
    pub score: f64,
}

/// The plane coordinate at fractional field pixel `(x, y)`.
///
/// Row 0 is the top of the frame and so the largest imaginary part, which is why
/// the vertical term is subtracted.
pub fn pixel_to_point(view: &Viewport, x: f64, y: f64) -> Complex<f64> {
    let across = (x + 0.5) / view.out_width as f64 - 0.5;
    let down = 0.5 - (y + 0.5) / view.out_height as f64;
    Complex::new(
        view.center.re + across * view.width,
        view.center.im + down * view.plane_height(),
    )
}

/// The frame a rung proposes from, and the readings of it the draws share.
///
/// A node draws several candidates off **one** parent frame, and two of the
/// three branches are pure functions of that frame: the scale-space focus set
/// and the detail-weighted centroid are the same points however many times they
/// are asked for. Reading them per *draw* rather than per *frame* is the whole
/// of what this type exists to stop — the focus finder is twenty smoothing
/// passes over the field and was measured at 47% of a walk's expansion clock,
/// two thirds of it spent re-deriving a set that had not moved.
///
/// So a frame is built once per node and each reading is taken on the first
/// draw that wants it. The randomness stays where it was: the branch draw, the
/// weighted focus draw and the uniform point still consume the node's stream in
/// the same order, because none of the cached work ever touched it.
///
/// **The policy is the node's, not the draw's.** A frame caches under the
/// assumption that the policy it is asked with does not change beneath it,
/// which is true by construction — a batch carries one policy — and is why the
/// readings are not keyed by anything.
pub struct Frame<'a> {
    view: &'a Viewport,
    field: &'a [f32],
    pixels: &'a [u8],
    /// The spread focus set, taken on the first foci draw.
    foci: Option<Vec<Focus>>,
    /// How many maxima the finder returned before the spread rule thinned them.
    /// Kept beside the set because the difference between the two is the whole
    /// cost of that rule, and it is not recoverable from the survivors.
    found: usize,
    /// The detail-weighted centroid, taken on the first density draw.
    density: Option<Complex<f64>>,
}

impl<'a> Frame<'a> {
    /// A frame over one node render: its escape field and the pixels of it.
    pub fn new(view: &'a Viewport, field: &'a [f32], pixels: &'a [u8]) -> Frame<'a> {
        Frame {
            view,
            field,
            pixels,
            foci: None,
            found: 0,
            density: None,
        }
    }

    /// This frame's kept foci, taking them if no draw has yet.
    ///
    /// The door a reporter comes in by. Asking costs a reading of the parent
    /// field and consumes **nothing** from the node's random stream — which is
    /// what lets a run that reports its foci draw the same candidates as one
    /// that does not.
    pub fn kept_foci(&mut self, policy: &Policy) -> &[Focus] {
        self.foci(policy)
    }

    /// How many maxima the finder returned before the spread rule thinned them.
    pub fn focus_count(&mut self, policy: &Policy) -> usize {
        self.foci(policy);
        self.found
    }

    /// Draw the next target on this frame.
    pub fn propose(&mut self, policy: &Policy, rng: &mut Rng) -> Target {
        let (weight_foci, weight_density, weight_random) = policy.branch;
        let total = weight_foci.max(0.0) + weight_density.max(0.0) + weight_random.max(0.0);
        let draw = rng.unit() * if total > 0.0 { total } else { 1.0 };

        if draw < weight_foci {
            let view = self.view;
            if let Some(focus) = sample_focus(self.foci(policy), rng) {
                return Target {
                    point: pixel_to_point(view, focus.x, focus.y),
                    branch: Branch::Foci,
                    score: focus.score,
                };
            }
            // An empty focus set is a fact about the frame, not a failure: fall
            // through to density rather than redrawing the branch, so the rung
            // still costs one draw and the stream stays reproducible.
        }

        if draw < weight_foci + weight_density {
            return Target {
                point: self.density(),
                branch: Branch::Density,
                score: f64::NAN,
            };
        }

        Target {
            point: interior_point(self.view, rng),
            branch: Branch::Random,
            score: f64::NAN,
        }
    }

    /// This frame's foci, spread out — found on the first ask, kept after it.
    fn foci(&mut self, policy: &Policy) -> &[Focus] {
        if self.foci.is_none() {
            let found = find_foci(self.view, self.field, &policy.sigmas);
            self.found = found.len();
            self.foci = Some(spread_out(
                &found,
                policy.focus_spread * self.view.out_width as f64,
            ));
        }
        self.foci.as_deref().unwrap_or_default()
    }

    /// This frame's detail-weighted centroid — measured on the first ask.
    fn density(&mut self) -> Complex<f64> {
        *self
            .density
            .get_or_insert_with(|| density_point(self.view, self.pixels))
    }
}

/// A uniform point of the frame, at least 20% in from every edge — so the child
/// frame it anchors still has the parent's structure around it.
fn interior_point(view: &Viewport, rng: &mut Rng) -> Complex<f64> {
    let across = 0.2 + 0.6 * rng.unit();
    let down = 0.2 + 0.6 * rng.unit();
    Complex::new(
        view.center.re + (across - 0.5) * view.width,
        view.center.im + (0.5 - down) * view.plane_height(),
    )
}

/// The detail-weighted centroid of the frame, with a void guard.
///
/// If the centroid itself lands on an empty tile — which happens whenever the
/// detail sits in two clumps with nothing between them — it is replaced by the
/// peak tile. A centroid between two things is not a thing.
fn density_point(view: &Viewport, pixels: &[u8]) -> Complex<f64> {
    let (across, down) = OCCUPANCY_TILES;
    let tiles = tile_energy(
        pixels,
        view.out_width as usize,
        view.out_height as usize,
        OCCUPANCY_TILES,
    );

    let (mut sum, mut weighted_x, mut weighted_y) = (0.0, 0.0, 0.0);
    let (mut peak, mut peak_at) = (f64::NEG_INFINITY, 0usize);
    for ty in 0..down {
        for tx in 0..across {
            let energy = tiles[ty * across + tx];
            weighted_x += energy * (tx as f64 + 0.5) / across as f64;
            weighted_y += energy * (ty as f64 + 0.5) / down as f64;
            sum += energy;
            if energy > peak {
                peak = energy;
                peak_at = ty * across + tx;
            }
        }
    }
    let (mut fx, mut fy) = if sum > 0.0 {
        (weighted_x / sum, weighted_y / sum)
    } else {
        (0.5, 0.5)
    };
    let tx = ((fx * across as f64) as usize).min(across - 1);
    let ty = ((fy * down as f64) as usize).min(down - 1);
    if tiles[ty * across + tx] < DETAIL_FLOOR {
        fx = ((peak_at % across) as f64 + 0.5) / across as f64;
        fy = ((peak_at / across) as f64 + 0.5) / down as f64;
    }
    Complex::new(
        view.center.re + (fx - 0.5) * view.width,
        view.center.im + (0.5 - fy) * view.plane_height(),
    )
}

/// Drop foci that sit within `radius` pixels of an already-kept, better one.
///
/// Without this the densest ridge contributes a dozen near-identical maxima and
/// wins the weighted draw by sheer count rather than by being the best place.
fn spread_out(foci: &[Focus], radius: f64) -> Vec<Focus> {
    if radius <= 0.0 || foci.len() < 2 {
        return foci.to_vec();
    }
    let squared = radius * radius;
    let mut kept: Vec<Focus> = Vec::new();
    for &focus in foci {
        if kept
            .iter()
            .all(|k| (k.x - focus.x).powi(2) + (k.y - focus.y).powi(2) > squared)
        {
            kept.push(focus);
        }
    }
    kept
}

/// Draw one focus with probability proportional to its score.
fn sample_focus(foci: &[Focus], rng: &mut Rng) -> Option<Focus> {
    let total: f64 = foci.iter().map(|f| f.score.max(0.0)).sum();
    if foci.is_empty() || total <= 0.0 {
        return None;
    }
    let mut ticket = rng.unit() * total;
    for focus in foci {
        ticket -= focus.score.max(0.0);
        if ticket <= 0.0 {
            return Some(*focus);
        }
    }
    foci.last().copied()
}

/// Scale-space maxima of the smoothed escape field.
pub fn find_foci(view: &Viewport, field: &[f32], sigmas: &[f64]) -> Vec<Focus> {
    let (width, height) = (view.out_width as usize, view.out_height as usize);
    let count = width * height;
    if count == 0 || field.len() < count {
        return Vec::new();
    }

    // The field, its validity mask, and the interior mask. Interior samples
    // carry no escape time, so they are excluded from the smoothing rather than
    // smoothed as zeros — a zero would pull the field down beside the set and
    // manufacture a ridge one pixel further out.
    let mut escape = vec![0.0; count];
    let mut valid = vec![0.0; count];
    let mut interior = vec![0.0; count];
    let mut exterior: Vec<f64> = Vec::new();
    for i in 0..count {
        let value = field[i] as f64;
        if value.is_finite() {
            escape[i] = value;
            valid[i] = 1.0;
            exterior.push(value);
        } else {
            interior[i] = 1.0;
        }
    }
    if exterior.len() < 16 {
        return Vec::new();
    }
    exterior.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let cap =
        exterior[((CLIP_QUANTILE * (exterior.len() - 1) as f64) as usize).min(exterior.len() - 1)];
    for value in escape.iter_mut() {
        if *value > cap {
            *value = cap;
        }
    }

    struct Detection {
        x: usize,
        y: usize,
        scale: usize,
        peak: f64,
        isolation: f64,
    }
    let mut detections: Vec<Detection> = Vec::new();

    for (index, &sigma) in sigmas.iter().enumerate() {
        let radius = sigma.round().max(1.0) as usize;
        // Normalized convolution: smoothing the field and the mask together, and
        // dividing, is what keeps the exterior average from being dragged toward
        // zero by the interior it borders.
        let numerator = smooth(&escape, width, height, radius);
        let denominator = smooth(&valid, width, height, radius);
        let mut smoothed = vec![f64::NAN; count];
        for i in 0..count {
            if denominator[i] > 1e-6 {
                smoothed[i] = numerator[i] / denominator[i];
            }
        }

        // Exclude everything within about σ of the set. A minibrot's halo is a
        // ring of very high escape times and would otherwise be every scale's
        // strongest maximum, on every frame that contains one.
        let excluded = dilate(&interior, width, height, radius);

        // The local mean at twice the scale, which the isolation ratio is
        // against: a peak is isolated when it stands above its own surroundings,
        // not above the frame.
        let filled: Vec<f64> = smoothed
            .iter()
            .map(|v| if v.is_nan() { 0.0 } else { *v })
            .collect();
        let mask: Vec<f64> = smoothed
            .iter()
            .map(|v| if v.is_nan() { 0.0 } else { 1.0 })
            .collect();
        let local_numerator = smooth(&filled, width, height, 2 * radius);
        let local_denominator = smooth(&mask, width, height, 2 * radius);

        let mut values: Vec<f64> = (0..count)
            .filter(|&i| !smoothed[i].is_nan() && excluded[i] == 0.0)
            .map(|i| smoothed[i])
            .collect();
        if values.len() < 8 {
            continue;
        }
        let mean = values.iter().sum::<f64>() / values.len() as f64;
        let variance = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / values.len() as f64;
        let deviation = variance.sqrt().max(1e-9);
        values.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let floor = values
            [((MAXIMUM_FLOOR_QUANTILE * (values.len() - 1) as f64) as usize).min(values.len() - 1)];

        let reach = (sigma * 0.4).round().max(2.0) as i64;
        for y in 0..height as i64 {
            for x in 0..width as i64 {
                let here = (y as usize) * width + x as usize;
                if smoothed[here].is_nan() || excluded[here] != 0.0 || smoothed[here] < floor {
                    continue;
                }
                let value = smoothed[here];
                // Maximal *within the region*: excluded neighbours are skipped
                // rather than compared against, or a pixel just outside the
                // exclusion ring always loses to the halo it was excluded from
                // and no exterior pixel ever wins.
                let mut is_maximum = true;
                'neighbours: for dy in -reach..=reach {
                    let ny = y + dy;
                    if ny < 0 || ny >= height as i64 {
                        continue;
                    }
                    for dx in -reach..=reach {
                        let nx = x + dx;
                        if nx < 0 || nx >= width as i64 || (dx == 0 && dy == 0) {
                            continue;
                        }
                        let there = (ny as usize) * width + nx as usize;
                        if smoothed[there].is_nan() || excluded[there] != 0.0 {
                            continue;
                        }
                        if smoothed[there] > value {
                            is_maximum = false;
                            break 'neighbours;
                        }
                    }
                }
                if !is_maximum {
                    continue;
                }
                let local = if local_denominator[here] > 1e-6 {
                    local_numerator[here] / local_denominator[here]
                } else {
                    value
                };
                detections.push(Detection {
                    x: x as usize,
                    y: y as usize,
                    scale: index,
                    peak: (value - mean) / deviation,
                    isolation: if local.abs() > 1e-9 {
                        value / local
                    } else {
                        1.0
                    },
                });
            }
        }
    }

    if detections.is_empty() {
        return Vec::new();
    }

    // Merge across scales, strongest first: a blob detected at four scales is
    // one focus, and the strongest detection is the one that names its position.
    detections.sort_by(|a, b| {
        b.peak
            .partial_cmp(&a.peak)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    let mean_sigma = sigmas.iter().sum::<f64>() / sigmas.len().max(1) as f64;
    let merge_radius_squared = (mean_sigma * 0.75).powi(2);
    let mut merged: Vec<(Focus, Vec<usize>)> = Vec::new();
    for detection in &detections {
        let (x, y) = (detection.x as f64, detection.y as f64);
        let hit = merged
            .iter()
            .position(|(f, _)| (f.x - x).powi(2) + (f.y - y).powi(2) <= merge_radius_squared);
        match hit {
            Some(at) => {
                if !merged[at].1.contains(&detection.scale) {
                    merged[at].1.push(detection.scale);
                }
                merged[at].0.scales = merged[at].1.len() as u32;
                merged[at].0.detected |= scale_bit(detection.scale);
                if detection.isolation > merged[at].0.isolation {
                    merged[at].0.isolation = detection.isolation;
                }
            }
            None => merged.push((
                Focus {
                    x,
                    y,
                    peak: detection.peak.max(0.0),
                    isolation: detection.isolation,
                    scales: 1,
                    detected: scale_bit(detection.scale),
                    score: 0.0,
                },
                vec![detection.scale],
            )),
        }
    }

    let mut foci: Vec<Focus> = merged
        .into_iter()
        .map(|(mut focus, _)| {
            focus.score = focus.peak.max(0.0) * focus.isolation.max(0.0);
            focus
        })
        .filter(|focus| focus.score > 0.0)
        .collect();
    foci.sort_by(|a, b| {
        b.score
            .partial_cmp(&a.score)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    foci.truncate(TOP_FOCI);
    foci
}

/// The bit one sigma of the sweep occupies in [`Focus::detected`].
///
/// Sigma lists past 32 entries are not a thing this policy takes — five is the
/// default and the widest ever run is a handful — so a scale beyond the mask
/// simply does not set a bit rather than the mask growing a heap allocation for
/// a case nobody has.
fn scale_bit(scale: usize) -> u32 {
    if scale < 32 { 1 << scale } else { 0 }
}

/// A Gaussian, approximated by three box passes — which is what the central
/// limit theorem says a box convolved with itself enough times becomes. Three is
/// the usual place to stop: the shape is already close and each further pass
/// costs another sweep of the frame.
fn smooth(source: &[f64], width: usize, height: usize, radius: usize) -> Vec<f64> {
    let once = box_pass(source, width, height, radius);
    let twice = box_pass(&once, width, height, radius);
    box_pass(&twice, width, height, radius)
}

/// One separable box mean of window `2r+1`, edges clamped, by running sum.
fn box_pass(source: &[f64], width: usize, height: usize, radius: usize) -> Vec<f64> {
    let window = (2 * radius + 1) as f64;
    let mut across = vec![0.0; width * height];
    for y in 0..height {
        let row = y * width;
        let mut sum = 0.0;
        for k in 0..=radius.min(width - 1) {
            sum += source[row + k];
        }
        sum += source[row] * radius as f64; // the clamped left tail
        for x in 0..width {
            across[row + x] = sum / window;
            let add = (x + radius + 1).min(width - 1);
            let drop = x.saturating_sub(radius);
            sum += source[row + add] - source[row + drop];
        }
    }
    let mut out = vec![0.0; width * height];
    for x in 0..width {
        let mut sum = 0.0;
        for k in 0..=radius.min(height - 1) {
            sum += across[k * width + x];
        }
        sum += across[x] * radius as f64;
        for y in 0..height {
            out[y * width + x] = sum / window;
            let add = (y + radius + 1).min(height - 1);
            let drop = y.saturating_sub(radius);
            sum += across[add * width + x] - across[drop * width + x];
        }
    }
    out
}

/// Grow a mask by `radius`, separably: a pixel is set if any pixel within the
/// square of that radius was.
fn dilate(mask: &[f64], width: usize, height: usize, radius: usize) -> Vec<f64> {
    let mut across = vec![0.0f64; width * height];
    for y in 0..height {
        let row = y * width;
        for x in 0..width {
            let low = x.saturating_sub(radius);
            let high = (x + radius).min(width - 1);
            across[row + x] = (low..=high).fold(0.0f64, |m, k| m.max(mask[row + k]));
        }
    }
    let mut out = vec![0.0f64; width * height];
    for x in 0..width {
        for y in 0..height {
            let low = y.saturating_sub(radius);
            let high = (y + radius).min(height - 1);
            out[y * width + x] = (low..=high).fold(0.0f64, |m, k| m.max(across[k * width + x]));
        }
    }
    out
}

/// Draw where the target lands inside the child frame.
pub fn pick_placement(weights: (f64, f64, f64), rng: &mut Rng) -> Placement {
    let total = weights.0.max(0.0) + weights.1.max(0.0) + weights.2.max(0.0);
    let ticket = rng.unit() * if total > 0.0 { total } else { 1.0 };
    if ticket < weights.0 {
        Placement::Center
    } else if ticket < weights.0 + weights.1 {
        Placement::Horizon
    } else {
        Placement::Offset
    }
}

/// The child frame's center, given where the target should sit inside it.
///
/// `center` puts the target in the middle; `horizon` moves it along the frame's
/// long axis only, which is the composition a wide image usually wants; `offset`
/// moves it in both. Both offsets stay within the middle 60% so the target
/// cannot end up against an edge.
pub fn child_center(
    target: Complex<f64>,
    placement: Placement,
    width: f64,
    height: f64,
    rng: &mut Rng,
) -> Complex<f64> {
    match placement {
        Placement::Center => target,
        Placement::Horizon => {
            let across = 0.2 + 0.6 * rng.unit();
            Complex::new(target.re - (across - 0.5) * width, target.im)
        }
        Placement::Offset => {
            let across = 0.2 + 0.6 * rng.unit();
            let down = 0.2 + 0.6 * rng.unit();
            Complex::new(
                target.re - (across - 0.5) * width,
                target.im - (0.5 - down) * height,
            )
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::family::Family;
    use crate::field::{self, FieldSpec};

    fn view(width: f64, center: Complex<f64>) -> Viewport {
        Viewport {
            center,
            width,
            out_width: 128,
            out_height: 72,
            supersample: 1,
        }
    }

    #[test]
    fn the_corners_of_a_frame_map_to_the_corners_of_the_plane_rectangle() {
        let view = view(4.0, Complex::new(0.0, 0.0));
        let top_left = pixel_to_point(&view, 0.0, 0.0);
        let bottom_right = pixel_to_point(&view, 127.0, 71.0);
        assert!(top_left.re < 0.0 && top_left.im > 0.0);
        assert!(bottom_right.re > 0.0 && bottom_right.im < 0.0);
        // Row 0 is the top, so it carries the largest imaginary part.
        assert!(top_left.im > bottom_right.im);
    }

    #[test]
    fn a_whole_set_view_offers_somewhere_to_go() {
        let family = Family::Multibrot { degree: 2 };
        let busy = view(3.0, Complex::new(-0.5, 0.0));
        let sampled = field::render_field(&busy, &family, 2000, FieldSpec::Smooth);
        let foci = find_foci(&busy, &sampled.fields[0].values, &SIGMAS);
        assert!(
            !foci.is_empty(),
            "the whole set should offer somewhere to go"
        );
        for focus in &foci {
            assert!(focus.score > 0.0);
            assert!(focus.x >= 0.0 && focus.x < 128.0);
        }
    }

    /// A frame with almost no exterior has no field to find maxima in, and the
    /// finder says so rather than reporting the handful of escaped samples as
    /// structure.
    ///
    /// The *other* degenerate frame — far exterior, where everything escapes at
    /// once — is deliberately **not** this function's problem. Its peaks are
    /// normalized by the field's own deviation, so numerical noise still
    /// produces maxima, and no amount of care here would change that. Such a
    /// frame is refused by the accept band as flat, one gate later, which is
    /// where "there is nothing here" belongs: it is a statement about the frame,
    /// not about where to aim inside it.
    #[test]
    fn a_frame_with_no_exterior_has_no_foci() {
        let family = Family::Multibrot { degree: 2 };
        let inside = view(0.02, Complex::new(-0.5, 0.0));
        let sampled = field::render_field(&inside, &family, 4000, FieldSpec::Smooth);
        assert!(
            sampled.interior_fraction > 0.99,
            "{}",
            sampled.interior_fraction
        );
        assert!(find_foci(&inside, &sampled.fields[0].values, &SIGMAS).is_empty());
    }

    /// A frame keeps its readings, and keeping them changes nothing.
    ///
    /// The saving is real work removed — the focus finder ran once per draw and
    /// now runs once per frame — so the claim that has to be pinned is that the
    /// draws are the *same* draws. A fresh frame per proposal is exactly what
    /// the per-draw path was, so proposing four times off one frame and
    /// proposing once off each of four frames, on one stream, must agree point
    /// for point.
    #[test]
    fn a_frame_proposes_what_a_fresh_frame_per_draw_would_have() {
        let family = Family::Multibrot { degree: 2 };
        let busy = view(3.0, Complex::new(-0.5, 0.0));
        let sampled = field::render_field(&busy, &family, 2000, FieldSpec::Smooth);
        let field = &sampled.fields[0].values;
        let pixels = vec![128u8; (busy.out_width * busy.out_height * 3) as usize];
        let policy = Policy::default();

        let mut kept = Frame::new(&busy, field, &pixels);
        let mut shared = Rng(0xD15C0);
        let mut fresh = Rng(0xD15C0);
        let mut branches = Vec::new();
        for _ in 0..16 {
            let one = kept.propose(&policy, &mut shared);
            let two = Frame::new(&busy, field, &pixels).propose(&policy, &mut fresh);
            assert_eq!(one.point, two.point);
            assert_eq!(one.branch, two.branch);
            assert_eq!(one.score.is_nan(), two.score.is_nan());
            if !one.score.is_nan() {
                assert_eq!(one.score, two.score);
            }
            branches.push(one.branch);
        }
        // The run has to have exercised the branch the cache is for, or it
        // pinned nothing.
        assert!(branches.contains(&Branch::Foci), "{branches:?}");
    }

    /// Foci are the sampling weight, so they must be sorted by it — a caller
    /// truncating the list has to be truncating the worst ones.
    #[test]
    fn foci_come_back_best_first() {
        let family = Family::Multibrot { degree: 2 };
        let busy = view(3.0, Complex::new(-0.5, 0.0));
        let sampled = field::render_field(&busy, &family, 2000, FieldSpec::Smooth);
        let foci = find_foci(&busy, &sampled.fields[0].values, &SIGMAS);
        for pair in foci.windows(2) {
            assert!(pair[0].score >= pair[1].score);
        }
    }

    #[test]
    fn spreading_drops_the_crowded_ones_and_keeps_the_best() {
        let focus = |x: f64, score: f64| Focus {
            x,
            y: 0.0,
            peak: score,
            isolation: 1.0,
            scales: 1,
            detected: 1,
            score,
        };
        let crowded = [focus(0.0, 9.0), focus(1.0, 8.0), focus(50.0, 7.0)];
        let kept = spread_out(&crowded, 10.0);
        assert_eq!(kept.len(), 2);
        assert_eq!(kept[0].score, 9.0);
        assert_eq!(kept[1].x, 50.0);
        assert_eq!(spread_out(&crowded, 0.0).len(), 3);
    }

    #[test]
    fn a_placement_keeps_the_target_inside_the_middle_of_the_child_frame() {
        let mut rng = Rng(4);
        let target = Complex::new(0.25, -0.1);
        for _ in 0..200 {
            for placement in [Placement::Center, Placement::Horizon, Placement::Offset] {
                let center = child_center(target, placement, 0.4, 0.225, &mut rng);
                let across = (target.re - center.re) / 0.4 + 0.5;
                let down = 0.5 - (target.im - center.im) / 0.225;
                assert!((0.2..=0.8).contains(&across), "{across}");
                assert!((0.2..=0.8).contains(&down), "{down}");
            }
        }
    }

    #[test]
    fn a_uniform_smooth_of_a_constant_field_is_that_constant() {
        let source = vec![2.5; 32 * 18];
        for value in smooth(&source, 32, 18, 3) {
            assert!((value - 2.5).abs() < 1e-12, "{value}");
        }
    }

    #[test]
    fn dilation_grows_a_single_pixel_into_its_square() {
        let mut mask = vec![0.0; 9 * 9];
        mask[4 * 9 + 4] = 1.0;
        let grown = dilate(&mask, 9, 9, 2);
        assert_eq!(grown[2 * 9 + 2], 1.0);
        assert_eq!(grown[6 * 9 + 6], 1.0);
        assert_eq!(grown[9 + 4], 0.0);
    }
}
