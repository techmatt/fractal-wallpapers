//! The escape-time loop, and what an orbit remembers on the way out.
//!
//! Iterate until the orbit leaves a disc of radius [`BAILOUT`] or until the
//! iteration cap runs out. A point that leaves gets a *smooth* iteration count —
//! a real number, not an integer — so the field it lands in has no visible
//! terraces. A point that stays gets `NaN`, which carries "interior" through the
//! rest of the pipeline as data rather than as a parallel mask.
//!
//! The smooth count is not the only thing an orbit can say about itself. The
//! strange coloring modes read *other* summaries of the same orbit — the angles
//! it passed through, how close it came to a circle or to the integer lattice,
//! how sharply it turned. Every one of those is an accumulation over the same
//! iteration, so they are gathered here, in the loop, and reduced afterwards.
//!
//! What is gathered is decided by [`Wants`] rather than gathered unconditionally.
//! A `sin`, two `atan2` and a lattice round per iteration is a large multiple of
//! the arithmetic an escape test costs, and a render reads one or two of these
//! channels, never all of them. The flag set is fixed for a whole render, so the
//! branches predict perfectly and a mode pays only for what it looks at.

use num_complex::Complex;

use crate::direct_trap::cross_distance;
use crate::family::Family;

/// Escape radius `B`.
///
/// Large on purpose. The smooth count's accuracy depends on `|z|` overshooting
/// the boundary by a negligible relative amount when the orbit finally crosses
/// it, and a bailout this size makes the first step past the boundary land far
/// enough out that the fractional part is clean. The angle-reading channels
/// (stripe, the triangle inequality) need it for a second reason: they assume
/// `|z| ≫ |c|` at escape, so that the last term they average is dominated by the
/// recurrence rather than by the constant.
pub const BAILOUT: f64 = 65536.0; // 2^16

/// How often [`run`] asks whether an orbit is proven interior, in steps. See the loop.
const INTERIOR_EVERY: u32 = 16;

/// Which per-iteration channels this render actually reads.
///
/// `Option` carries both halves of the question — whether a channel is wanted
/// and the shape constant it needs — so there is no way to switch one on and
/// forget to hand it its parameter.
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct Wants {
    /// Stripe average, at this sine density.
    pub stripe: Option<f64>,
    /// Triangle-inequality average.
    pub tia: bool,
    /// Curvature average.
    pub curvature: bool,
    /// Closest approach to a circle of this radius.
    pub trap_circle: Option<f64>,
    /// Closest approach to the axis cross through the origin.
    pub trap_cross: bool,
    /// Accumulated cross trap, at this kernel width.
    pub threads: Option<f64>,
    /// Gaussian-integer lattice statistics.
    pub gaussian_int: bool,
    /// Exponential smoothing.
    pub exp_smoothing: bool,
    /// Mean step length.
    pub velocity: bool,
    /// The symbolic address, to this many symbols in this base.
    pub itinerary: Option<Symbols>,
    /// The derivative of the orbit with respect to the pixel, which the distance
    /// estimate divides by. The most expensive flag here — a complex multiply per
    /// iteration on top of the recurrence's own — so nothing but `de` sets it.
    pub derivative: bool,
    /// Stop an orbit once it is **proven never to escape**, and report it as the
    /// loop would have at the cap. No field asks for this: [`crate::field::sweep_row`]
    /// sets it, and only where every field of the pass either reads an escape — a
    /// bounded orbit reduces to `None` whatever it did on the way — or reads a
    /// statistic an exact repeat makes final (see [`Interior`]). A pass with one of
    /// the second kind is handed [`Interior::REPEAT`], which has no disk: an orbit in
    /// a disk is still wandering towards its cycle, and a minimum over it is not yet
    /// final.
    pub interior: Option<Interior>,
}

/// The two ways an orbit is proven interior before the cap, in [`run`].
///
/// **A disk the cycle carries into itself.** Where the plane has an attracting
/// cycle `z₀ … z_{p−1}` and a disk about `z₀` that `p` steps of the map send strictly
/// inside itself, with room left over for `f64` rounding, an orbit that enters the
/// disk stays within a bounded chain of disks for ever and never reaches the bailout.
/// [`Interior::of`] finds one on the Julia planes and gives its proof.
///
/// **An exact repeat.** The loop is a deterministic function of its state — `z`,
/// and on Phoenix `z_{n−1}` as well — so a state whose bits come round again is on
/// a cycle it will never leave, and a cycle that has not escaped yet never will.
/// Brent's scheme finds it: keep the state at each power-of-two step and compare
/// every step with it. That is exact on every family and needs no proof per
/// family; it catches an attracting cycle once rounding has settled the orbit on a
/// float cycle, which is later than the disk and on any plane at all.
///
/// **A repeat also makes some of the orbit's statistics final**, which a disk does
/// not. Once the state at step `n` is the state at an earlier step `s`, every later
/// iterate is one of `z_{s+1} … z_n`, and the loop has already accumulated each of
/// those. So a stopped orbit reads exactly as the orbit run to the cap for:
///
/// - a **minimum or maximum** — the circle and cross traps, the lattice's nearest
///   and farthest, and the iterate and step each happened at, because the strict
///   comparisons keep the first occurrence and a revisit only ties it;
/// - a **head address**, once it holds `depth` symbols, after which nothing is
///   appended — the loop does not stop on a repeat before then;
/// - a **tail address** whose roll is exact ([`Symbols::rolls_exactly`]): it is then
///   the last `depth` symbols before the cap and nothing else, and those are the
///   cycle's, read from the phase the cap falls at. The loop steps round to that
///   phase and spells them; see [`run`].
///
/// A mean, a sum, a count and a colour composited per iterate are not final: each
/// keeps changing for every step the cap has left. Those passes are not handed this.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Interior {
    /// A point of the attracting cycle, the disk's centre.
    pub center: Complex<f64>,
    /// The disk's squared radius, already shrunk for the test's own rounding.
    /// Zero where no disk is known, which no orbit enters, and the repeat is
    /// then the only test.
    pub radius_sq: f64,
}

impl Interior {
    /// The exact repeat alone, with no disk: what a pass that reads a statistic of the
    /// interior orbit is handed.
    pub const REPEAT: Interior = Interior {
        center: Complex::new(0.0, 0.0),
        radius_sq: 0.0,
    };

    /// The interior tests that hold on `family`: the repeat everywhere, and a
    /// disk where the plane has one.
    ///
    /// **The disk is the Julia planes' alone.** `z ↦ z^d + c` has one critical
    /// point, `0`, so it has at most one attracting cycle and that cycle attracts
    /// `0`'s orbit: iterating `0` finds it, or finds that there is none. The
    /// parameter planes have a different cycle at every pixel — the cardioid and
    /// the main component are answered in `sweep_row` before the loop, and the
    /// rest is the repeat's. Phoenix steps a pair `(z, z_{n−1})` and would need a
    /// norm on it; the repeat covers it.
    ///
    /// **The proof, per step of the cycle.** For `|h| ≤ r`,
    /// `|f(zᵢ + h) − z_{i+1}| ≤ Σ_{k=1}^{d} C(d,k)·|zᵢ|^{d−k}·r^k + |f(zᵢ) − z_{i+1}|`:
    /// the binomial expansion of `(zᵢ + h)^d − zᵢ^d` under the triangle inequality,
    /// plus how far the `f64` cycle point is from mapping exactly onto the next one.
    /// `SLOP` is added to every link for the loop's own rounding of a step, which at
    /// `|z| ≤ 3` and degree six is under `10⁻¹²`. Chaining the bound round the cycle
    /// gives `r_p` from `r₀`; a disk of radius `r₀` about `z₀` is accepted when
    /// `r_p ≤ (1 − MARGIN)·r₀`, so every `p` steps carry the orbit back into the disk
    /// with room to spare, and every step in between is within `rᵢ ≤ 1` of `zᵢ`,
    /// nowhere near the bailout. The largest power of two that closes is taken and
    /// then bisected upward. The test in the loop compares against a radius shrunk by
    /// `10⁻⁶` relative, far more than the rounding of `|z − z₀|²` at `r₀ ≥ 10⁻⁶`.
    ///
    /// Computed once per thread and family and remembered, because `sweep_row` asks
    /// once per row.
    pub fn of(family: &Family) -> Interior {
        let none = Interior::REPEAT;
        let Family::Julia { degree, c } = *family else {
            return none;
        };
        /// A family's key — degree and the bits of `c` — beside the disk it proved.
        type Held = ((u32, u64, u64), Interior);
        thread_local! {
            static LAST: std::cell::Cell<Option<Held>> =
                const { std::cell::Cell::new(None) };
        }
        let key = (degree, c.re.to_bits(), c.im.to_bits());
        if let Some((held, interior)) = LAST.get() {
            if held == key {
                return interior;
            }
        }
        let interior = julia_disk(family, degree).unwrap_or(none);
        LAST.set(Some((key, interior)));
        interior
    }
}

/// The disk [`Interior::of`] proves, about a point of the Julia plane's attracting
/// cycle, or `None`.
fn julia_disk(family: &Family, degree: u32) -> Option<Interior> {
    /// Steps of the critical orbit before the cycle is read off it.
    const SETTLE: u32 = 10_000;
    /// The longest cycle looked for.
    const LONGEST: usize = 64;
    /// How near the orbit must come back to call it a cycle; the proof charges
    /// whatever is left as each link's residual.
    const CLOSE: f64 = 1e-9;
    /// Per-link allowance for the loop's own rounding of one step.
    const SLOP: f64 = 1e-10;
    /// How far inside itself the return must land.
    const MARGIN: f64 = 1e-3;
    /// The smallest disk worth a test.
    const SMALLEST: f64 = 1e-6;

    let zero = Complex::new(0.0, 0.0);
    let (_, _, c) = family.seed(zero);
    let step = |z: Complex<f64>| family.step(z, zero, c);
    let mut z = zero;
    for _ in 0..SETTLE {
        z = step(z);
        // NaN counts as escaped: an orbit that overflowed has no cycle to read.
        let m = z.norm_sqr();
        if m.is_nan() || m > 16.0 {
            return None;
        }
    }
    let mut cycle = vec![z];
    let mut w = step(z);
    while (w - z).norm() > CLOSE {
        if cycle.len() == LONGEST {
            return None;
        }
        cycle.push(w);
        w = step(w);
    }
    let p = cycle.len();
    let links: Vec<(f64, f64)> = (0..p)
        .map(|i| {
            (
                cycle[i].norm(),
                (step(cycle[i]) - cycle[(i + 1) % p]).norm(),
            )
        })
        .collect();
    // How far `p` steps can carry a point from within `r0` of `z₀`, or `∞` if some
    // link leaves the unit neighbourhood the rounding allowance was sized for.
    let returns = |r0: f64| -> f64 {
        let mut r = r0;
        for &(modulus, residual) in &links {
            let mut spread = 0.0;
            let mut binomial = 1.0;
            for k in 1..=degree {
                binomial = binomial * (degree - k + 1) as f64 / k as f64;
                spread += binomial * modulus.powi((degree - k) as i32) * r.powi(k as i32);
            }
            r = spread + residual + SLOP;
            if r.is_nan() || r > 1.0 {
                return f64::INFINITY;
            }
        }
        r
    };
    let closes = |r0: f64| returns(r0) <= (1.0 - MARGIN) * r0;
    let mut low = 0.5;
    while !closes(low) {
        low *= 0.5;
        if low < SMALLEST {
            return None;
        }
    }
    let mut high = 2.0 * low;
    for _ in 0..30 {
        let middle = 0.5 * (low + high);
        if closes(middle) {
            low = middle;
        } else {
            high = middle;
        }
    }
    let radius = low * (1.0 - 1e-6);
    Some(Interior {
        center: cycle[0],
        radius_sq: radius * radius,
    })
}

impl Wants {
    /// Everything two fields between them ask for, in one pass.
    ///
    /// Where both want the same channel with a different constant the first
    /// wins; [`crate::coloring::Coloring`] refuses to build such a pair, because
    /// one orbit cannot carry two stripe densities and silently picking one is
    /// how a render stops meaning what its record says it means.
    pub fn union(self, other: Wants) -> Wants {
        Wants {
            stripe: self.stripe.or(other.stripe),
            tia: self.tia || other.tia,
            curvature: self.curvature || other.curvature,
            trap_circle: self.trap_circle.or(other.trap_circle),
            trap_cross: self.trap_cross || other.trap_cross,
            threads: self.threads.or(other.threads),
            gaussian_int: self.gaussian_int || other.gaussian_int,
            exp_smoothing: self.exp_smoothing || other.exp_smoothing,
            velocity: self.velocity || other.velocity,
            itinerary: self.itinerary.or(other.itinerary),
            derivative: self.derivative || other.derivative,
            interior: self.interior.or(other.interior),
        }
    }
}

/// How an orbit's angular itinerary is read off as one number.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Symbols {
    /// How many equal angular sectors the plane is cut into.
    pub sectors: u32,
    /// The base the symbols are written in. `= sectors` makes the address a clean
    /// base-`k` expansion; a smaller base decays more slowly and so keeps more of
    /// the deep symbols visible.
    pub base: f64,
    /// How many symbols the address holds.
    pub depth: u32,
    /// Which `depth` symbols of the orbit the address is made of. The spec-level
    /// spelling is [`AddressStart`](crate::field::AddressStart); the loop needs
    /// only the answer, which is what keeps the wire format out of it.
    pub window: AddressWindow,
}

/// Which `depth` symbols of an orbit an address is made of.
///
/// **Three-valued, and each value is a different question.** The first two read
/// the *head* of the orbit and differ only in whether the pixel's own sector is
/// the leading digit; the third reads the *tail* and so has no leading digit to
/// argue about. It was a `bool` while there were two, and widening it is what
/// keeps the third from arriving as "not `z₀`" — which is what `z₁` already
/// means.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum AddressWindow {
    /// The first `depth` symbols, opening on `z₀`: the pixel's own sector is the
    /// most significant digit. The settled default.
    #[default]
    HeadFromZ0,
    /// The first `depth` symbols, opening on `z₁`. Every digit is then one the
    /// recurrence produced.
    HeadFromZ1,
    /// The **last** `depth` symbols the orbit spelled before it stopped —
    /// escaping, or running out of iterations. `z₀` is never one of them: the
    /// tail is a fact about where the orbit ended up, and the pixel's own sector
    /// only reaches it on an orbit too short to fill the window.
    Tail,
}

impl AddressWindow {
    /// Whether `z₀` spells a symbol. The one thing the escape loop asks before
    /// it starts stepping.
    pub fn opens_on_z0(self) -> bool {
        self == AddressWindow::HeadFromZ0
    }

    /// Whether the address rolls rather than filling once.
    pub fn is_tail(self) -> bool {
        self == AddressWindow::Tail
    }
}

impl Symbols {
    /// Whether a tail address rolled with these symbols is **exactly** its last
    /// `depth` symbols, whatever came before them.
    ///
    /// Three conditions, each a step of [`Address::roll`]'s `frac(value·base) +
    /// sector·base^{−depth}` being exact: the base is a power of two, so the
    /// multiply and the bottom weight are exact; it is at least `sectors`, so the
    /// integer part `fract` drops is the oldest symbol and nothing else; and
    /// `depth·log₂base ≤ 53`, so every window is a multiple of the bottom weight that
    /// an `f64` holds. The named modes' four sectors in base four to 26 symbols are 52
    /// bits. Anything else rounds, the rounding carries history the window no longer
    /// shows, and only the whole run reproduces it.
    pub fn rolls_exactly(&self) -> bool {
        let bits = self.base.to_bits();
        let power_of_two = self.base.is_finite() && bits & ((1 << 52) - 1) == 0;
        let exponent = ((bits >> 52) & 0x7ff) as i64 - 1023;
        power_of_two
            && exponent >= 1
            && self.base >= self.sectors as f64
            && self.depth as i64 * exponent <= 53
    }
}

/// A running mean that remembers its last term.
///
/// The averaging modes have a problem the smooth count solved long ago: the
/// number of terms in the average is the integer escape count, so the average
/// jumps every time a neighbouring pixel escapes one step later. [`deband`]
/// fixes it the same way the smooth count does — by fading the final term in
/// rather than admitting it all at once — which is why the last term is kept
/// separately instead of only the sum.
///
/// [`deband`]: Average::deband
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct Average {
    sum: f64,
    count: u32,
    last: f64,
}

impl Average {
    fn push(&mut self, term: f64) {
        self.sum += term;
        self.count += 1;
        self.last = term;
    }

    /// The mean, with the last term faded in by `fade ∈ [0, 1]`.
    ///
    /// `fade` is the fractional part of the smooth iteration count, which runs
    /// to zero exactly at the escape boundary. At `fade = 0` the answer is the
    /// mean of every term *but* the last — which is what the pixel next door,
    /// escaping one step earlier, computed. So the two agree across the step
    /// boundary instead of terracing.
    pub fn deband(&self, fade: f64) -> Option<f64> {
        match self.count {
            0 => None,
            1 => Some(self.sum),
            count => {
                let mean = self.sum / count as f64;
                let without_last = (self.sum - self.last) / (count - 1) as f64;
                Some(fade * mean + (1.0 - fade) * without_last)
            }
        }
    }
}

/// The orbit's angular itinerary, accumulated as one fractional number.
///
/// Each step contributes the index of the angular sector its iterate landed in,
/// written as the next digit of a base-`base` fraction: the first symbol is the
/// most significant, and the sum is the orbit's *address* in the fractal's own
/// self-similar lamination. Two nearby pixels whose orbits take the same route
/// through the sectors get nearly the same address however long they run, which
/// is what makes this independent of the escape time rather than a restretch of
/// it.
///
/// **The address is `f64` and stays `f64`.** A base-`k` expansion to `d` symbols
/// needs `d·log₂k` bits of mantissa, so at `k = 4` the 53 bits of an `f64` are
/// spent after 26 symbols and an `f32` after 11. Rounding a deep address into
/// `f32` does not blur it — it bands it, because whole subtrees of the lamination
/// collapse onto one value. That is why the coloring this feeds never travels
/// through the `f32` field dump.
///
/// ## The two windows
///
/// A **head** address ([`AddressWindow::HeadFromZ0`], [`AddressWindow::HeadFromZ1`])
/// fills once and then ignores everything after it: the first `depth` symbols are
/// the address and the orbit's later life is not in the number. A **tail** address
/// ([`AddressWindow::Tail`]) keeps rolling — every step pushes a symbol in at the
/// bottom and shifts one out of the top — so what it holds is the last `depth`
/// symbols the orbit spelled before it stopped.
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct Address {
    value: f64,
    /// The weight the next symbol will carry: `base^{−(n+1)}`. A tail address
    /// does not use it: every symbol it takes carries the same weight, at the
    /// bottom of the window.
    weight: f64,
    count: u32,
}

impl Address {
    /// Add the sector this iterate landed in.
    ///
    /// A head address stops once it is full; a tail address rolls, dropping its
    /// oldest symbol to make room.
    fn push(&mut self, z: Complex<f64>, symbols: Symbols) {
        if symbols.depth == 0 {
            return;
        }
        let sector = Address::sector(z, symbols);
        if symbols.window.is_tail() {
            self.roll(sector, symbols);
        } else {
            self.append(sector, symbols);
        }
    }

    /// Which of the `k` angular sectors an iterate landed in.
    ///
    /// `atan2` runs `(−π, π]`; shifting by π puts the cut on the negative real
    /// axis and the sectors in `[0, k)` counting counter-clockwise from there.
    fn sector(z: Complex<f64>, symbols: Symbols) -> f64 {
        let turns = (z.im.atan2(z.re) + std::f64::consts::PI) / std::f64::consts::TAU;
        let sector = (turns * symbols.sectors as f64).floor();
        sector.clamp(0.0, (symbols.sectors - 1) as f64)
    }

    /// One more digit of a head address, unless it is already full.
    fn append(&mut self, sector: f64, symbols: Symbols) {
        if self.count >= symbols.depth {
            return;
        }
        if self.count == 0 {
            self.weight = 1.0 / symbols.base;
        }
        self.value += sector * self.weight;
        self.weight /= symbols.base;
        self.count += 1;
    }

    /// One more digit of a tail address: shift the window up a place, drop what
    /// falls off the top, and write the new symbol into the bottom.
    ///
    /// `frac(value·base) + sector·base^{−depth}` is the whole rule. Multiplying
    /// by the base moves the oldest symbol into the integer part, `fract` is what
    /// drops it, and the new symbol goes in at the window's least significant
    /// place.
    ///
    /// **Exact when `base ≥ sectors`, which is the only way the named mode asks
    /// for it** — four sectors in base four. There the symbols that stay are
    /// worth `Σ_{i≥1} sᵢ·base^{−i} ≤ (sectors−1)/(base−1) ≤ 1`, so the integer
    /// part is the dropped symbol and nothing else. Under a *smaller* weight base
    /// — the option that exists so the deep symbols decay more slowly — the
    /// retained window can reach past 1 and `fract` takes a bite out of a symbol
    /// that was meant to stay. That is a real limit of this arithmetic rather
    /// than a bug to work around, and it is stated here because a caller lowering
    /// `weight_base` under a tail start is the one who has to know it.
    ///
    /// **An orbit shorter than `depth` reads with leading zeros**, because the
    /// window fills from the bottom: the first symbol lands at `base^{−depth}`
    /// and climbs a place per step. So the tail address is near zero wherever the
    /// orbit escaped fast, and only reaches the size a head address has where the
    /// orbit ran the full `depth`. That is the point of the field rather than a
    /// defect — it puts the address's structure where the orbits are long — and
    /// at exactly `depth` symbols the two windows agree, which is what makes the
    /// tail a continuation of the head rather than a different number.
    fn roll(&mut self, sector: f64, symbols: Symbols) {
        let bottom = symbols.base.powi(-(symbols.depth as i32));
        self.value = (self.value * symbols.base).fract() + sector * bottom;
        self.count += 1;
    }

    /// The address, if any symbol was spelled at all.
    pub fn value(&self) -> Option<f64> {
        (self.count > 0).then_some(self.value)
    }

    /// How many symbols were pushed. A tail address counts every step the orbit
    /// took, not the `depth` it kept.
    pub fn symbols(&self) -> u32 {
        self.count
    }
}

/// How close an orbit came to the integer lattice, and where.
///
/// Every point of the complex plane has a nearest Gaussian integer — a point
/// with whole real and imaginary parts. Watching an orbit's distance to that
/// lattice turns the whole plane into an orbit trap with a repeating unit cell,
/// which is what gives this channel its beaded, tiled look.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Lattice {
    /// Closest the orbit ever came to a lattice point.
    pub nearest: f64,
    /// The iterate at that closest approach.
    pub at_nearest: Complex<f64>,
    /// The step the closest approach happened on.
    pub step_nearest: u32,
    /// Farthest the orbit ever got from every lattice point.
    pub farthest: f64,
    /// The iterate at that farthest approach.
    pub at_farthest: Complex<f64>,
    /// The step the farthest approach happened on.
    pub step_farthest: u32,
    sum: f64,
    count: u32,
}

impl Lattice {
    fn empty() -> Lattice {
        Lattice {
            nearest: f64::INFINITY,
            at_nearest: Complex::new(0.0, 0.0),
            step_nearest: 0,
            farthest: 0.0,
            at_farthest: Complex::new(0.0, 0.0),
            step_farthest: 0,
            sum: 0.0,
            count: 0,
        }
    }

    /// Mean distance to the lattice over the orbit, if it had any iterates.
    pub fn mean(&self) -> Option<f64> {
        (self.count > 0).then(|| self.sum / self.count as f64)
    }

    fn push(&mut self, z: Complex<f64>, step: u32) {
        let distance = (z - Complex::new(z.re.round(), z.im.round())).norm();
        self.sum += distance;
        self.count += 1;
        if distance < self.nearest {
            self.nearest = distance;
            self.at_nearest = z;
            self.step_nearest = step;
        }
        if distance > self.farthest {
            self.farthest = distance;
            self.at_farthest = z;
            self.step_farthest = step;
        }
    }
}

/// What one point did, and what it saw on the way.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Orbit {
    /// The orbit left the bailout disc within the iteration cap.
    pub escaped: bool,
    /// The step the orbit left on when `escaped`, `0` otherwise.
    ///
    /// The classic escape count, kept beside the smooth one because it is a
    /// different number and not a rounding of it: the smooth count is what a
    /// picture wants and this is what the algorithm actually measured. Only
    /// [`FieldSpec::Discrete`](crate::field::FieldSpec::Discrete) reads it, and
    /// only for orbits that escaped — an orbit that did not has no escape step,
    /// and `0` is that absence rather than a step it reached.
    pub iteration: u32,
    /// Smooth iteration count when `escaped`, `NaN` otherwise.
    pub smooth: f64,
    /// Mean of `½ + ½·sin(density · arg z)`.
    pub stripe: Average,
    /// Mean of the triangle-inequality ratio.
    pub tia: Average,
    /// Mean turning angle between consecutive steps.
    pub curvature: Average,
    /// Closest approach to the trap circle; `∞` if that channel was not wanted.
    pub trap_circle: f64,
    /// Closest approach to the axis cross; `∞` if that channel was not wanted.
    pub trap_cross: f64,
    /// Mean of `exp(−D²/σ²)` over the orbit, `D` the cross-trap distance.
    pub threads: Average,
    /// Lattice-trap statistics.
    pub lattice: Lattice,
    /// `Σ exp(−|z|)` and the number of terms in it.
    pub exp_smoothing: (f64, u32),
    /// Mean length of a step, `|zₙ − zₙ₋₁|`.
    pub velocity: Average,
    /// The orbit's angular address.
    pub itinerary: Address,
    /// The last iterate the loop produced — the one it escaped on when it did.
    ///
    /// Not gated: `z` is already in hand at the moment the loop returns, so
    /// keeping it costs a move. The escape angle reads it, and so does the
    /// distance estimate, which needs `|z|` and `|dz|` from the same step.
    pub last: Complex<f64>,
    /// `dz/d(pixel)` at that last iterate; `0` if the derivative was not wanted.
    pub derivative: Complex<f64>,
}

impl Orbit {
    fn new() -> Orbit {
        Orbit {
            escaped: false,
            iteration: 0,
            smooth: f64::NAN,
            stripe: Average::default(),
            tia: Average::default(),
            curvature: Average::default(),
            trap_circle: f64::INFINITY,
            trap_cross: f64::INFINITY,
            threads: Average::default(),
            lattice: Lattice::empty(),
            exp_smoothing: (0.0, 0),
            velocity: Average::default(),
            itinerary: Address::default(),
            last: Complex::new(0.0, 0.0),
            derivative: Complex::new(0.0, 0.0),
        }
    }

    /// The exterior distance estimate: how far this point is from the set.
    ///
    /// `2·|z|·ln|z| / |dz|`, read at the iterate the orbit escaped on. The
    /// classic Koenigs/Douady–Hubbard estimate: the orbit's escape speed measures
    /// how fast the potential is climbing, and the derivative measures how much
    /// of that climb is the *pixel* moving rather than the iteration running, so
    /// their ratio is a length in the plane. It is a real distance, which is what
    /// makes it useful as a field — it does not restretch with the iteration cap
    /// the way an escape count does.
    ///
    /// `None` for an orbit that did not escape (there is no boundary crossing to
    /// read the estimate at) and for a vanishing derivative, which is a critical
    /// point of the iteration rather than a distance of zero.
    ///
    /// **An overflowed derivative reports zero rather than nothing.** The
    /// derivative grows by a factor of `d·|z|^{d−1}` per step, so a sample within a
    /// hair of the boundary at a deep zoom can run `|dz|` past `f64`'s ceiling —
    /// and once it is infinite the recurrence can turn it into a `NaN` on the next
    /// step. Both mean the same thing: the quotient has underflowed, and the sample
    /// is closer to the set than this arithmetic can measure. That is a distance of
    /// zero, not an absent value; reporting it as absent would paint an exterior
    /// sample with the interior's own black and dust a deep frame's brightest region
    /// with speckles. It has not been seen on the frames measured — on a released
    /// 2·10⁻⁵-wide multibrot frame at a cap of 24 462 this field's empty samples are
    /// exactly the interior, to the sample — so the arm is a guard rather than a
    /// fix, and it is here because the failure it guards against is invisible until
    /// somebody zooms further.
    pub fn distance_estimate(&self) -> Option<f64> {
        if !self.escaped {
            return None;
        }
        let slope = self.derivative.norm();
        if !slope.is_finite() {
            return Some(0.0);
        }
        let magnitude = self.last.norm();
        let estimate = 2.0 * magnitude * magnitude.ln() / slope;
        (slope > 0.0 && estimate.is_finite() && estimate >= 0.0).then_some(estimate)
    }

    /// How far past the last whole iteration the orbit escaped, in `[0, 1)`.
    ///
    /// Zero for an orbit that did not escape, so an interior point contributes
    /// no fade — and the averaging channels are exterior-only anyway.
    pub fn fade(&self) -> f64 {
        if self.escaped {
            self.smooth.fract().clamp(0.0, 1.0)
        } else {
            0.0
        }
    }
}

/// Iterate one point of the plane, keeping the channels `wants` asks for.
///
/// `pixel` is the point's coordinate in whichever plane the family lives in:
/// the constant `c` for a parameter-plane family, the starting value `z₀` for a
/// dynamical one. [`Family::seed`] makes that choice; this loop does not know
/// which it got.
// TODO(perf): the source project reached deep zoom by iterating a low-precision
// delta against one high-precision reference orbit, rebasing when the delta grew
// past the reference. That belongs here when deep zoom does.
/// **Always inlined, and it is worth about four times the field time.**
///
/// This loop collapses to the bare recurrence only when the compiler can see the
/// family and the [`Wants`] at the *call site*: the eleven channel checks below
/// fold away, the match over the families becomes one multiply, and the `Orbit`
/// stops being built. The inliner's own cost model refuses a function this long
/// across a crate boundary, and refusing it measured 6.3 s against 1.5 s on a
/// 1280×720 frame of the site explorer's wasm build, where the family and the
/// mode arrive from a JSON spec and the call site is the only place they are
/// constant. Inside this crate the call site is [`crate::field::sweep_row`],
/// which writes one out per family and per channel set for the same reason, so
/// the attribute costs a copy of this loop per entry of that table — which is
/// what the table is buying.
#[inline(always)]
pub fn run(family: &Family, pixel: Complex<f64>, maxiter: u32, wants: &Wants) -> Orbit {
    let bailout_sq = BAILOUT * BAILOUT;
    let (mut z, mut z_prev, c) = family.seed(pixel);
    let c_abs = c.norm();

    // The two previous iterates, which curvature needs to measure a turn. This
    // is a separate history from `z_prev`: that one is Phoenix's memory term and
    // starts at `z₋₁`, which is a constant of the family rather than a point of
    // the orbit.
    let mut one_back = z;
    // Written at the top of every pass, before the one channel that reads it —
    // which needs three points and so waits for the second pass anyway.
    let mut two_back;

    // The derivative of the orbit with respect to the pixel, advanced in lockstep
    // with `z` when a field asks for it. Two steps of history, because Phoenix's
    // derivative has a memory term exactly as Phoenix does.
    let (mut dz, mut dz_prev) = family.derivative_seed();

    let mut orbit = Orbit::new();
    orbit.last = z;

    // **A head address opening on `z₀` spells its first symbol here.** Every other
    // channel accumulates from `n = 1`, which for an average is a rounding
    // difference. For an address it is not: `s₀` is the most significant digit, so
    // dropping it shifts every address by a whole base-`k` place and the field
    // means something else. This push is the only reason `z₀` is offered to any
    // channel at all — and the other two windows ask not to be offered it, for
    // two different reasons. `z₁` because on a dynamical plane `z₀` is the pixel
    // and its sector is a wedge rather than a fact about the orbit; the tail
    // because it reads the end of the orbit, where `z₀` has no business unless
    // the orbit was too short to fill the window.
    if let Some(symbols) = wants
        .itinerary
        .filter(|symbols| symbols.window.opens_on_z0())
    {
        orbit.itinerary.push(z, symbols);
    }

    // Brent's saved state for the exact repeat, taken again at every power of two.
    // `z_{n−1}` is part of the state only where the step reads it.
    let memory = matches!(family, Family::Phoenix { .. } | Family::PhoenixM { .. });
    let mut saved = (z, z_prev);
    // The step `saved` was taken at, so that a repeat knows a period: `n − saved_at`.
    let mut saved_at = 0;

    for n in 1..=maxiter {
        // |z²| before the step: the triangle inequality compares the actual next
        // iterate against the bounds `|z²| ± |c|` that the inequality allows it.
        // A `hypot` is the most expensive thing in this loop, so it is computed
        // only for the one channel that reads it.
        let squared_abs = if wants.tia { (z * z).norm() } else { 0.0 };

        // Before the step, because `dz_{n+1} = f'(z_n)·dz_n` reads the iterate the
        // step is about to leave behind.
        if wants.derivative {
            let next = family.derivative_step(z, dz, dz_prev);
            dz_prev = dz;
            dz = next;
        }

        let next = family.step(z, z_prev, c);
        two_back = one_back;
        one_back = z;
        z_prev = z;
        z = next;
        orbit.last = z;

        let magnitude_sq = z.norm_sqr();
        let magnitude = magnitude_sq.sqrt();

        if let Some(radius) = wants.trap_circle {
            orbit.trap_circle = orbit.trap_circle.min((magnitude - radius).abs());
        }
        if wants.trap_cross {
            orbit.trap_cross = orbit.trap_cross.min(cross_distance(z));
        }
        if let Some(sigma) = wants.threads {
            // The kernel is inside the average, not outside it: `mean(exp(−D²/σ²))`
            // is not any curve applied to `mean(D)`, which is what makes σ a live
            // parameter rather than something the post-stretch curve could absorb.
            let distance = cross_distance(z);
            orbit
                .threads
                .push((-(distance * distance) / (sigma * sigma)).exp());
        }
        if wants.gaussian_int {
            orbit.lattice.push(z, n);
        }
        if wants.velocity {
            orbit.velocity.push((z - one_back).norm());
        }
        if let Some(symbols) = wants.itinerary {
            orbit.itinerary.push(z, symbols);
        }
        if wants.exp_smoothing {
            orbit.exp_smoothing.0 += (-magnitude).exp();
            orbit.exp_smoothing.1 += 1;
        }
        if let Some(density) = wants.stripe {
            orbit
                .stripe
                .push(0.5 + 0.5 * (density * z.im.atan2(z.re)).sin());
        }
        if wants.tia {
            // Where the actual step landed, between the closest and farthest the
            // triangle inequality permits it to. Degenerate when the two bounds
            // coincide — at the origin, or with `c = 0` — which is what the guard
            // on the denominator is for.
            let low = (squared_abs - c_abs).abs();
            let high = squared_abs + c_abs;
            let span = high - low;
            orbit.tia.push(if span > 1e-300 {
                ((magnitude - low) / span).clamp(0.0, 1.0)
            } else {
                0.0
            });
        }
        // A turn needs three points, so this channel starts one step later than
        // the others.
        if wants.curvature && n >= 2 {
            let step = z - one_back;
            let previous_step = one_back - two_back;
            if previous_step.norm_sqr() > 1e-300 {
                orbit.curvature.push((step / previous_step).arg().abs());
            }
        }

        if magnitude_sq > bailout_sq {
            orbit.escaped = true;
            orbit.iteration = n;
            orbit.smooth = smooth_count(n, magnitude_sq, family.escape_exponent());
            if wants.derivative {
                orbit.derivative = dz;
            }
            return orbit;
        }

        // After the escape test, so a stopped orbit is one that has not escaped
        // yet and, by [`Interior`]'s two proofs, never will: it leaves the loop as
        // one that ran out of iterations does.
        //
        // **Every `INTERIOR_EVERY`th step, not every step.** Tested every step, the two
        // tests cost an orbit that escapes — which is most of them on most frames — up to
        // 15% (the Phoenix anchor 1.74 s to 1.92 s at 1600×900 ss4). An orbit in the disk
        // stays there for ever, so testing it late loses nothing; and the repeat, compared
        // only at multiples of the stride and saved at powers of two, still meets a cycle
        // of length `L` once the saved step passes `INTERIOR_EVERY·L`.
        if let Some(interior) = wants.interior {
            if n % INTERIOR_EVERY == 0 {
                if (z - interior.center).norm_sqr() < interior.radius_sq {
                    break;
                }
                let bits = |w: Complex<f64>| (w.re.to_bits(), w.im.to_bits());
                if bits(z) == bits(saved.0) && (!memory || bits(z_prev) == bits(saved.1)) {
                    // Every channel but the address is final here, or absent from a
                    // pass that is handed the repeat (see [`Interior`]).
                    let Some(symbols) = wants.itinerary else {
                        break;
                    };
                    if !symbols.window.is_tail() {
                        // A head address is final once it is full, and the orbit keeps
                        // going until it is: the repeat comes round again.
                        if orbit.itinerary.symbols() >= symbols.depth {
                            break;
                        }
                    } else if symbols.rolls_exactly() {
                        // A tail address is the last `depth` symbols before the cap.
                        // From step `saved_at` on, the state repeats every `period`
                        // steps, so the state `k` steps on is the state `k mod period`
                        // steps on: step that far without spelling, then spell the
                        // symbols the cap's window holds. Nothing else is read
                        // afterwards from an orbit that did not escape.
                        let period = n - saved_at;
                        let left = maxiter - n;
                        let spelled = left.min(symbols.depth);
                        for _ in 0..(left - spelled) % period {
                            (z, z_prev) = (family.step(z, z_prev, c), z);
                        }
                        for _ in 0..spelled {
                            (z, z_prev) = (family.step(z, z_prev, c), z);
                            orbit.itinerary.push(z, symbols);
                        }
                        break;
                    }
                }
                if n.is_power_of_two() {
                    saved = (z, z_prev);
                    saved_at = n;
                }
            }
        }
    }

    if wants.derivative {
        orbit.derivative = dz;
    }
    orbit
}

/// Iterate one point, keeping nothing but the escape.
pub fn escape(family: &Family, pixel: Complex<f64>, maxiter: u32) -> Orbit {
    run(family, pixel, maxiter, &Wants::default())
}

/// The smooth (fractional) iteration count of an orbit that escaped at step `n`
/// with `|z|² = magnitude_sq`.
///
/// `nu = (n + 1) − log_d( ln|z| / ln B )`
///
/// The integer count alone is a staircase: every point between two escape steps
/// gets the same value, and the field bands. The correction measures *how far
/// past* the bailout the orbit landed. Near escape `|z_{n+1}| ≈ |z_n|^d`, so one
/// step multiplies `ln|z|` by `d` — which makes `log_d` the right way to read
/// the overshoot as a fraction of a step, and makes the **degree** the base. Get
/// that base wrong and every family but the quadratic one bands anyway.
///
/// Dividing by `ln B` inside the logarithm pins `nu` to zero at the bailout
/// boundary. To a colormap normalized over the frame that is an invisible
/// constant shift — but it is load-bearing to [`Average::deband`], which reads
/// the *fraction* of this number as "how far into the last step the orbit got".
/// Drop the `ln B` and that fraction is offset by a constant, the fade happens
/// at the wrong moment, and the averaging modes terrace in a way that looks like
/// brickwork.
fn smooth_count(n: u32, magnitude_sq: f64, degree: f64) -> f64 {
    let log_z = 0.5 * magnitude_sq.ln(); // ln|z|
    let log_bailout = BAILOUT.ln();
    let overshoot = log_z / log_bailout;

    // The double logarithm is finite only for an orbit genuinely outside the
    // bailout disc. Anything else — an overflow to infinity, a degenerate
    // bailout — falls back to the integer count rather than poisoning the field
    // with a NaN that would read as "interior".
    if overshoot.is_finite() && overshoot > 0.0 {
        (n + 1) as f64 - overshoot.ln() / degree.ln()
    } else {
        (n + 1) as f64
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn julia(c: Complex<f64>) -> Family {
        Family::Julia { degree: 2, c }
    }

    fn everything() -> Wants {
        Wants {
            stripe: Some(6.0),
            tia: true,
            curvature: true,
            trap_circle: Some(1.0),
            trap_cross: true,
            threads: Some(0.15),
            gaussian_int: true,
            exp_smoothing: true,
            velocity: true,
            itinerary: Some(Symbols {
                sectors: 4,
                base: 4.0,
                depth: 26,
                window: AddressWindow::HeadFromZ0,
            }),
            derivative: true,
            interior: None,
        }
    }

    #[test]
    fn the_origin_is_interior_to_every_multibrot() {
        for degree in 2..=6 {
            let family = Family::Multibrot { degree };
            let sample = escape(&family, Complex::new(0.0, 0.0), 500);
            assert!(!sample.escaped, "degree {degree}: the origin escaped");
            assert!(sample.smooth.is_nan());
        }
    }

    #[test]
    fn a_far_away_point_escapes_immediately() {
        let family = Family::Multibrot { degree: 2 };
        let sample = escape(&family, Complex::new(1e6, 1e6), 500);
        assert!(sample.escaped);
        assert!(sample.smooth.is_finite());
    }

    /// Both classes must be present in a view that spans the set, for every
    /// family — the cheapest evidence that a recurrence is actually live.
    #[test]
    fn every_family_produces_both_interior_and_exterior() {
        let c = Complex::new(-0.8, 0.156);
        let families = [
            Family::Multibrot { degree: 2 },
            Family::Multibrot { degree: 3 },
            Family::Multibrot { degree: 4 },
            Family::Multibrot { degree: 5 },
            Family::Multibrot { degree: 6 },
            julia(c),
            Family::Julia {
                degree: 3,
                c: Complex::new(0.0, 0.0),
            },
            Family::Julia {
                degree: 5,
                c: Complex::new(0.0, 0.0),
            },
            Family::Phoenix {
                c: crate::family::PHOENIX_C,
                p: crate::family::PHOENIX_P,
                z_prev: Complex::new(0.0, 0.0),
            },
        ];
        for family in families {
            let (mut escaped, mut interior) = (0, 0);
            for row in 0..32 {
                for col in 0..32 {
                    let re = -1.8 + 3.6 * (col as f64 + 0.5) / 32.0;
                    let im = -1.8 + 3.6 * (row as f64 + 0.5) / 32.0;
                    let sample = escape(&family, Complex::new(re, im), 400);
                    if sample.escaped {
                        escaped += 1;
                        assert!(sample.smooth.is_finite(), "{family:?}: non-finite smooth");
                    } else {
                        interior += 1;
                    }
                }
            }
            assert!(
                escaped > 0 && interior > 0,
                "{family:?}: escaped={escaped} interior={interior}"
            );
        }
    }

    /// Phoenix with `p = 0` and `z₋₁ = 0` is a quadratic Julia set — not
    /// approximately, exactly. The memory term is the only difference between
    /// the two recurrences, and multiplying it by zero removes it.
    #[test]
    fn phoenix_with_zero_p_is_a_quadratic_julia() {
        let c = Complex::new(-0.4, 0.6);
        let phoenix = Family::Phoenix {
            c,
            p: Complex::new(0.0, 0.0),
            z_prev: Complex::new(0.0, 0.0),
        };
        let twin = julia(c);
        for row in 0..40 {
            for col in 0..40 {
                let re = -1.6 + 3.2 * (col as f64 + 0.5) / 40.0;
                let im = -1.6 + 3.2 * (row as f64 + 0.5) / 40.0;
                let pixel = Complex::new(re, im);
                let a = escape(&phoenix, pixel, 600);
                let b = escape(&twin, pixel, 600);
                assert_eq!(a.escaped, b.escaped, "at {pixel}");
                assert_eq!(
                    a.smooth.to_bits(),
                    b.smooth.to_bits(),
                    "smooth count differs at {pixel}"
                );
            }
        }
    }

    /// The Phoenix parameter plane with `p = 0` is the Mandelbrot set, exactly: `z₀ =
    /// z₋₁ = 0` and a zero memory term leave `z² + c` from the origin. Held over a grid
    /// that crosses the whole set, interior and exterior both, to the smooth count's bits.
    #[test]
    fn the_phoenix_plane_with_zero_p_is_the_mandelbrot_set() {
        let plane = Family::PhoenixM {
            p: Complex::new(0.0, 0.0),
        };
        let mandelbrot = Family::Multibrot { degree: 2 };
        let (mut escaped, mut interior) = (0, 0);
        for row in 0..48 {
            for col in 0..64 {
                let re = -2.2 + 3.0 * (col as f64 + 0.5) / 64.0;
                let im = -1.2 + 2.4 * (row as f64 + 0.5) / 48.0;
                let pixel = Complex::new(re, im);
                let a = escape(&plane, pixel, 600);
                let b = escape(&mandelbrot, pixel, 600);
                assert_eq!(a.escaped, b.escaped, "at {pixel}");
                assert_eq!(
                    a.smooth.to_bits(),
                    b.smooth.to_bits(),
                    "smooth count differs at {pixel}"
                );
                if a.escaped {
                    escaped += 1;
                } else {
                    interior += 1;
                }
            }
        }
        assert!(
            escaped > 0 && interior > 0,
            "escaped={escaped} interior={interior}"
        );
    }

    /// The plane's point is its Julia set's `c`: at the same `p`, the plane's orbit of
    /// `c` is the Phoenix set's orbit of `z₀ = 0`, step for step. That identity is what
    /// makes a click on the plane open the picture it was a point of.
    #[test]
    fn a_point_of_the_phoenix_plane_is_its_phoenix_set_at_the_origin() {
        let p = crate::family::PHOENIX_P;
        let plane = Family::PhoenixM { p };
        for c in [
            crate::family::PHOENIX_C,
            Complex::new(0.3, 0.2),
            Complex::new(-0.9, 0.45),
        ] {
            let set = Family::Phoenix {
                c,
                p,
                z_prev: Complex::new(0.0, 0.0),
            };
            let a = escape(&plane, c, 800);
            let b = escape(&set, Complex::new(0.0, 0.0), 800);
            assert_eq!(a.escaped, b.escaped, "at {c}");
            assert_eq!(a.smooth.to_bits(), b.smooth.to_bits(), "at {c}");
        }
    }

    /// A non-zero `z₋₁` is a real axis, not a decoration: it must move the set.
    #[test]
    fn a_nonzero_z_prev_gives_a_different_set() {
        let classic = Family::Phoenix {
            c: crate::family::PHOENIX_C,
            p: crate::family::PHOENIX_P,
            z_prev: Complex::new(0.0, 0.0),
        };
        let shifted = Family::Phoenix {
            c: crate::family::PHOENIX_C,
            p: crate::family::PHOENIX_P,
            z_prev: Complex::new(0.35, -0.2),
        };
        let differing = (0..48)
            .flat_map(|row| (0..48).map(move |col| (row, col)))
            .filter(|&(row, col)| {
                let re = -1.6 + 3.2 * (col as f64 + 0.5) / 48.0;
                let im = -1.6 + 3.2 * (row as f64 + 0.5) / 48.0;
                let pixel = Complex::new(re, im);
                escape(&classic, pixel, 400).escaped != escape(&shifted, pixel, 400).escaped
            })
            .count();
        assert!(differing > 0, "z₋₁ changed nothing");
    }

    /// The smooth count must cross an escape-step boundary continuously: that is
    /// the entire reason it exists. Walk the real axis inward from `c = 4` to
    /// `c = 2.05`, where every point escapes and the integer count ticks from 3
    /// to 4 partway along. The integer count jumps by 1 there; the smooth count
    /// must not jump at all.
    #[test]
    fn the_smooth_count_does_not_terrace() {
        let family = Family::Multibrot { degree: 2 };
        let samples: Vec<f64> = (0..2000)
            .map(|step| {
                let re = 4.0 - 1.95 * step as f64 / 2000.0;
                let sample = escape(&family, Complex::new(re, 0.0), 100);
                assert!(sample.escaped, "c = {re} should escape");
                sample.smooth
            })
            .collect();

        let total: f64 = samples.last().unwrap() - samples.first().unwrap();
        assert!(
            total > 0.5,
            "the walk never crossed a step boundary ({total})"
        );

        let largest_step = samples
            .windows(2)
            .map(|pair| (pair[1] - pair[0]).abs())
            .fold(0.0f64, f64::max);
        assert!(
            largest_step < 0.05,
            "terrace of {largest_step} in the field"
        );
    }

    /// The escape radius has to be at least `2^(1/(d−1))` for the escape test to
    /// mean anything: below that a point can leave the disc and come back. The
    /// requirement grows without bound as `d` falls toward 1 — it is 2 at the
    /// quadratic degree and ~2.38 at 1.8 — so the lowest degree the spec admits
    /// is where the check belongs, and [`BAILOUT`] has to clear it.
    ///
    /// It clears it by four orders of magnitude, which is the point: `2^16`
    /// stays a valid bailout down to `d = 1 + 1/16`, so
    /// [`LOWEST_FRACTIONAL_DEGREE`](crate::spec::LOWEST_FRACTIONAL_DEGREE) is a
    /// claim about what has been looked at rather than about the arithmetic.
    #[test]
    fn the_bailout_covers_the_lowest_degree() {
        let required = |d: f64| 2f64.powf(1.0 / (d - 1.0));
        assert!((required(1.8) - 2.378).abs() < 0.001, "{}", required(1.8));
        assert!(required(crate::spec::LOWEST_FRACTIONAL_DEGREE) < BAILOUT);

        // Where the margin actually runs out, so that lowering the bound past
        // this point cannot pass silently.
        let breaking = 1.0 + 1.0 / BAILOUT.log2();
        assert!((breaking - 1.0625).abs() < 1e-12, "{breaking}");
        assert!(crate::spec::LOWEST_FRACTIONAL_DEGREE > breaking);
    }

    /// Below the quadratic degree the smooth count's base is `ln d < ln 2`, which
    /// *amplifies* the overshoot correction rather than shrinking it — so a
    /// wrong normalization would show up here more loudly than at `d = 2`. Walk
    /// the real axis of the `d = 1.8` parameter plane across an escape-step
    /// boundary and require the same continuity [`the_smooth_count_does_not_terrace`]
    /// requires of the quadratic.
    #[test]
    fn the_smooth_count_does_not_terrace_below_degree_two() {
        for degree in [1.8, 1.9] {
            let family = Family::FractionalMultibrot { degree };
            let samples: Vec<f64> = (0..2000)
                .map(|step| {
                    let re = 4.0 - 1.9 * step as f64 / 2000.0;
                    let sample = escape(&family, Complex::new(re, 0.0), 200);
                    assert!(sample.escaped, "d = {degree}, c = {re} should escape");
                    sample.smooth
                })
                .collect();

            let total: f64 = samples.last().unwrap() - samples.first().unwrap();
            assert!(
                total > 0.5,
                "d = {degree}: no step boundary crossed ({total})"
            );

            let largest_step = samples
                .windows(2)
                .map(|pair| (pair[1] - pair[0]).abs())
                .fold(0.0f64, f64::max);
            assert!(
                largest_step < 0.05,
                "d = {degree}: terrace of {largest_step}"
            );
        }
    }

    /// The integer count and the smooth one are two readings of one escape, and
    /// the smooth one *refines* the other: it lands inside the step the orbit
    /// actually left on. That is what makes a discrete render the floor of a
    /// smooth one, which is the whole content of the figure the two make
    /// together — so it is pinned here rather than assumed there.
    #[test]
    fn the_smooth_count_lands_inside_the_step_the_orbit_left_on() {
        let families = [
            Family::Multibrot { degree: 2 },
            Family::Multibrot { degree: 5 },
            Family::FractionalMultibrot { degree: 1.8 },
            julia(Complex::new(-0.8, 0.156)),
            Family::Phoenix {
                c: crate::family::PHOENIX_C,
                p: crate::family::PHOENIX_P,
                z_prev: Complex::new(0.0, 0.0),
            },
        ];
        for family in families {
            for row in 0..60 {
                for col in 0..60 {
                    let pixel = Complex::new(
                        -2.0 + 4.0 * (col as f64 + 0.5) / 60.0,
                        -2.0 + 4.0 * (row as f64 + 0.5) / 60.0,
                    );
                    let orbit = escape(&family, pixel, 500);
                    if !orbit.escaped {
                        assert_eq!(
                            orbit.iteration, 0,
                            "{family:?}: an interior point has no step"
                        );
                        continue;
                    }
                    assert_eq!(
                        orbit.smooth.floor() as u32,
                        orbit.iteration,
                        "{family:?} at {pixel}: smooth {} is not inside step {}",
                        orbit.smooth,
                        orbit.iteration
                    );
                }
            }
        }
    }

    /// Asking for nothing must not change what the escape says. This is the
    /// property that lets [`Wants`] be an optimization rather than a mode: the
    /// gated channels are written, never read, by the escape test.
    #[test]
    fn gathering_channels_does_not_move_the_escape() {
        let family = julia(Complex::new(-0.4, 0.6));
        for row in 0..24 {
            for col in 0..24 {
                let pixel = Complex::new(
                    -1.5 + 3.0 * (col as f64 + 0.5) / 24.0,
                    -1.5 + 3.0 * (row as f64 + 0.5) / 24.0,
                );
                let bare = escape(&family, pixel, 300);
                let full = run(&family, pixel, 300, &everything());
                assert_eq!(bare.escaped, full.escaped);
                assert_eq!(bare.smooth.to_bits(), full.smooth.to_bits());
            }
        }
    }

    /// Each channel has a range its definition guarantees, and a channel that
    /// leaves its range has an arithmetic bug that a picture would only show as
    /// "looks a bit odd".
    #[test]
    fn every_channel_stays_inside_its_own_definition() {
        let family = julia(Complex::new(-0.8, 0.156));
        let wants = everything();
        for row in 0..24 {
            for col in 0..24 {
                let pixel = Complex::new(
                    -1.5 + 3.0 * (col as f64 + 0.5) / 24.0,
                    -1.5 + 3.0 * (row as f64 + 0.5) / 24.0,
                );
                let orbit = run(&family, pixel, 300, &wants);
                let fade = orbit.fade();

                let stripe = orbit.stripe.deband(fade).unwrap();
                assert!((0.0..=1.0).contains(&stripe), "stripe {stripe}");
                let tia = orbit.tia.deband(fade).unwrap();
                assert!((0.0..=1.0).contains(&tia), "tia {tia}");
                if let Some(curvature) = orbit.curvature.deband(fade) {
                    assert!((0.0..=std::f64::consts::PI).contains(&curvature));
                }
                assert!(orbit.trap_circle >= 0.0 && orbit.trap_circle.is_finite());
                // Half the diagonal of the unit cell is the farthest any point
                // can be from every lattice point.
                let corner = std::f64::consts::SQRT_2 / 2.0 + 1e-12;
                assert!(orbit.lattice.nearest <= corner, "{}", orbit.lattice.nearest);
                assert!(orbit.lattice.farthest <= corner);
                assert!(orbit.lattice.mean().unwrap() <= corner);
                let (sum, count) = orbit.exp_smoothing;
                assert!(sum >= 0.0 && sum <= count as f64);

                assert!(orbit.trap_cross >= 0.0 && orbit.trap_cross.is_finite());
                // A Gaussian kernel of a real distance: strictly in (0, 1].
                let threads = orbit.threads.deband(fade).unwrap();
                assert!(threads > 0.0 && threads <= 1.0, "threads {threads}");
                let velocity = orbit.velocity.deband(fade).unwrap();
                assert!(
                    velocity >= 0.0 && velocity.is_finite(),
                    "velocity {velocity}"
                );
                // The address is a base-4 fraction of at most 26 digits, so it is
                // strictly inside [0, 1) whatever the orbit did.
                let address = orbit.itinerary.value().unwrap();
                assert!((0.0..1.0).contains(&address), "address {address}");
                assert!(orbit.itinerary.symbols() <= 26);
                if let Some(estimate) = orbit.distance_estimate() {
                    assert!(estimate >= 0.0 && estimate.is_finite(), "de {estimate}");
                }
            }
        }
    }

    /// The distance estimate has to be a **distance**, not merely a field that
    /// looks like one. On the real axis right of the Mandelbrot set the true
    /// distance is known — the cardioid cusp sits at `0.25` — so the estimate can
    /// be held to two things a mere field would fail: it stays within a small
    /// factor of the truth, and that factor *tightens toward one* as the point
    /// closes in on the set. The second is the load-bearing half: the estimate is
    /// asymptotic in the number of steps the orbit survives, so a far point escapes
    /// in two iterations and is over-estimated, and a near one is not.
    #[test]
    fn the_distance_estimate_is_within_a_small_factor_of_the_real_distance() {
        let family = Family::Multibrot { degree: 2 };
        let wants = Wants {
            derivative: true,
            ..Wants::default()
        };
        let mut ratios = Vec::new();
        let mut previous = f64::INFINITY;
        for &c in &[4.0, 2.0, 1.0, 0.5] {
            let estimate = run(&family, Complex::new(c, 0.0), 4000, &wants)
                .distance_estimate()
                .unwrap_or_else(|| panic!("no estimate at c = {c}"));
            let truth = c - 0.25;
            let ratio = estimate / truth;
            assert!(
                (0.5..4.0).contains(&ratio),
                "at c = {c} the estimate {estimate} is {ratio}x the true distance {truth}"
            );
            assert!(
                estimate < previous,
                "the estimate did not shrink at c = {c}"
            );
            previous = estimate;
            ratios.push(ratio);
        }
        for pair in ratios.windows(2) {
            assert!(
                pair[1] < pair[0],
                "the estimate did not tighten on the way in: {ratios:?}"
            );
        }
        assert!(*ratios.last().unwrap() < 1.5, "{ratios:?}");
    }

    /// An overflowed derivative means the quotient underflowed, which is a distance
    /// of zero and not an absent value — otherwise a deep frame's brightest region
    /// comes back speckled with the interior's black.
    #[test]
    fn an_overflowed_derivative_reads_as_a_distance_of_zero() {
        let mut orbit = Orbit::new();
        orbit.escaped = true;
        orbit.last = Complex::new(BAILOUT * 2.0, 0.0);
        for slope in [f64::INFINITY, f64::NAN] {
            orbit.derivative = Complex::new(slope, 0.0);
            assert_eq!(orbit.distance_estimate(), Some(0.0), "slope {slope}");
        }
        // A vanishing derivative is a different thing — a critical point of the
        // iteration — and has no distance to report at all.
        orbit.derivative = Complex::new(0.0, 0.0);
        assert_eq!(orbit.distance_estimate(), None);
        // And an orbit that never escaped has no boundary crossing to read.
        orbit.derivative = Complex::new(1.0, 0.0);
        orbit.escaped = false;
        assert_eq!(orbit.distance_estimate(), None);
    }

    /// The averaging channels get the same treatment the smooth count gets, and
    /// for the same reason: walk across an escape-step boundary and the value
    /// must not jump. Without the fade the mean gains a whole term at once.
    #[test]
    fn the_averaging_channels_do_not_terrace() {
        let family = Family::Multibrot { degree: 2 };
        let wants = Wants {
            stripe: Some(6.0),
            tia: true,
            ..Wants::default()
        };
        let mut stripes = Vec::new();
        let mut tias = Vec::new();
        for step in 0..4000 {
            let re = 4.0 - 1.95 * step as f64 / 4000.0;
            let orbit = run(&family, Complex::new(re, 0.0), 100, &wants);
            let fade = orbit.fade();
            stripes.push(orbit.stripe.deband(fade).unwrap());
            tias.push(orbit.tia.deband(fade).unwrap());
        }
        for (name, samples) in [("stripe", &stripes), ("tia", &tias)] {
            let largest = samples
                .windows(2)
                .map(|pair| (pair[1] - pair[0]).abs())
                .fold(0.0f64, f64::max);
            assert!(largest < 0.02, "{name} terraces by {largest}");
        }
    }

    /// A channel nobody asked for must stay at its empty value rather than
    /// quietly accumulating — otherwise the gate is decoration and the cost it
    /// was written to avoid is still being paid.
    #[test]
    fn unwanted_channels_stay_empty() {
        let family = julia(Complex::new(-0.4, 0.6));
        let orbit = run(
            &family,
            Complex::new(0.3, 0.2),
            200,
            &Wants {
                stripe: Some(6.0),
                ..Wants::default()
            },
        );
        assert!(orbit.stripe.deband(orbit.fade()).is_some());
        assert_eq!(orbit.tia, Average::default());
        assert_eq!(orbit.curvature, Average::default());
        assert_eq!(orbit.trap_circle, f64::INFINITY);
        assert_eq!(orbit.trap_cross, f64::INFINITY);
        assert_eq!(orbit.threads, Average::default());
        assert_eq!(orbit.lattice.mean(), None);
        assert_eq!(orbit.exp_smoothing, (0.0, 0));
        assert_eq!(orbit.velocity, Average::default());
        assert_eq!(orbit.itinerary.value(), None);
        // The derivative is the most expensive gate here, so the one thing that
        // must be true of it when nobody asked is that it never ran.
        assert_eq!(orbit.derivative, Complex::new(0.0, 0.0));
        assert_eq!(orbit.distance_estimate(), None);
    }

    #[test]
    fn a_union_of_wants_asks_for_both_sides() {
        let stripe = Wants {
            stripe: Some(6.0),
            ..Wants::default()
        };
        let trap = Wants {
            trap_circle: Some(1.0),
            ..Wants::default()
        };
        let both = stripe.union(trap);
        assert_eq!(both.stripe, Some(6.0));
        assert_eq!(both.trap_circle, Some(1.0));
        assert!(!both.tia);
        assert!(!both.derivative);
    }

    /// The derivative recurrence is differentiated from the recurrence itself, so
    /// the cheapest honest check on it is a numerical one: the analytic derivative
    /// must agree with a finite difference of the orbit in the pixel.
    #[test]
    fn the_derivative_recurrence_matches_a_finite_difference() {
        let wants = Wants {
            derivative: true,
            ..Wants::default()
        };
        let families = [
            Family::Multibrot { degree: 2 },
            Family::Multibrot { degree: 4 },
            julia(Complex::new(-0.4, 0.6)),
            Family::Phoenix {
                c: crate::family::PHOENIX_C,
                p: crate::family::PHOENIX_P,
                z_prev: Complex::new(0.0, 0.0),
            },
        ];
        // Short, so the derivative and the difference are both far from overflow;
        // a long orbit is exponentially sensitive and a difference cannot follow it.
        let steps = 6;
        let step = 1e-7;
        for family in families {
            let pixel = Complex::new(0.31, 0.22);
            let analytic = run(&family, pixel, steps, &wants).derivative;
            let ahead = run(&family, pixel + Complex::new(step, 0.0), steps, &wants).last;
            let behind = run(&family, pixel - Complex::new(step, 0.0), steps, &wants).last;
            let difference = (ahead - behind) / (2.0 * step);
            let error = (analytic - difference).norm() / analytic.norm().max(1.0);
            assert!(error < 1e-4, "{family:?}: {analytic} against {difference}");
        }
    }

    /// A point in each of the four sectors, chosen so the sector is readable off
    /// the signs: `atan2` is shifted by π before the cut, so the quadrants number
    /// `(−,−) = 0`, `(+,−) = 1`, `(+,+) = 2`, `(−,+) = 3`.
    fn in_sector(sector: u32) -> Complex<f64> {
        match sector {
            0 => Complex::new(-1.0, -1.0),
            1 => Complex::new(1.0, -1.0),
            2 => Complex::new(1.0, 1.0),
            3 => Complex::new(-1.0, 1.0),
            other => panic!("there are four sectors, not {other}"),
        }
    }

    fn address_of(sectors: &[u32], depth: u32, window: AddressWindow) -> f64 {
        let symbols = Symbols {
            sectors: 4,
            base: 4.0,
            depth,
            window,
        };
        let mut address = Address::default();
        for &sector in sectors {
            address.push(in_sector(sector), symbols);
        }
        address.value().expect("something was spelled")
    }

    /// The four sector points spell the digits they are named for. Everything
    /// below is hand-computed against this mapping, so it is asserted first
    /// rather than assumed.
    #[test]
    fn the_four_sector_points_spell_their_own_digits() {
        for sector in 0..4 {
            let expected = f64::from(sector) / 4.0;
            let spelled = address_of(&[sector], 1, AddressWindow::HeadFromZ0);
            assert_eq!(spelled, expected, "sector {sector}");
        }
    }

    /// **The rolling window, against an orbit computed by hand.**
    ///
    /// Five symbols `1 2 3 0 2` into a three-symbol address. A head keeps the
    /// first three — `1/4 + 2/16 + 3/64 = 0.421875` — and never moves again. A
    /// tail keeps the last three, `3 0 2`, which is `3/4 + 0/16 + 2/64 =
    /// 0.78125`. Both are exact in binary, so these are equalities and not
    /// tolerances.
    #[test]
    fn a_tail_address_holds_the_last_symbols_and_a_head_holds_the_first() {
        let orbit = [1, 2, 3, 0, 2];
        assert_eq!(
            address_of(&orbit, 3, AddressWindow::HeadFromZ0),
            0.421875,
            "the head fills once and ignores the rest of the orbit"
        );
        assert_eq!(
            address_of(&orbit, 3, AddressWindow::Tail),
            0.78125,
            "the tail is `3 0 2`, the last three symbols"
        );
    }

    /// A tail window fills from the bottom, so a short orbit reads with leading
    /// zeros — and at exactly `depth` symbols the two windows agree, which is
    /// what makes the tail a continuation of the head rather than a different
    /// number. Both are hand-computed: `1·4⁻³`, then `1·4⁻² + 2·4⁻³`, then the
    /// full `1/4 + 2/16 + 3/64`.
    #[test]
    fn a_tail_window_fills_from_the_bottom_and_meets_the_head_when_it_is_full() {
        assert_eq!(address_of(&[1], 3, AddressWindow::Tail), 1.0 / 64.0);
        assert_eq!(
            address_of(&[1, 2], 3, AddressWindow::Tail),
            1.0 / 16.0 + 2.0 / 64.0
        );
        assert_eq!(
            address_of(&[1, 2, 3], 3, AddressWindow::Tail),
            address_of(&[1, 2, 3], 3, AddressWindow::HeadFromZ0),
        );
    }

    /// The window that is not a start: a tail address is the same number whether
    /// the orbit that fed it was long or short, as long as its last `depth`
    /// symbols were the same. That is the property a rolling window is for, and
    /// the one a head cannot have.
    #[test]
    fn a_tail_address_forgets_everything_before_the_window() {
        let short = address_of(&[3, 0, 2], 3, AddressWindow::Tail);
        let long = address_of(&[1, 2, 3, 0, 2], 3, AddressWindow::Tail);
        let longer = address_of(&[0, 0, 1, 1, 2, 3, 3, 0, 2], 3, AddressWindow::Tail);
        assert_eq!(short, long);
        assert_eq!(long, longer);
        assert_ne!(
            address_of(&[1, 2, 3, 0, 2], 3, AddressWindow::HeadFromZ0),
            long,
            "a head does not forget: it never saw the tail at all"
        );
    }

    /// A depth of nothing spells nothing, whichever window asked. The tail path
    /// is the one that would otherwise divide the window into a `base⁰` place and
    /// let the address run past 1.
    #[test]
    fn an_address_of_no_symbols_holds_no_value() {
        for window in [
            AddressWindow::HeadFromZ0,
            AddressWindow::HeadFromZ1,
            AddressWindow::Tail,
        ] {
            let symbols = Symbols {
                sectors: 4,
                base: 4.0,
                depth: 0,
                window,
            };
            let mut address = Address::default();
            for sector in [1, 2, 3] {
                address.push(in_sector(sector), symbols);
            }
            assert_eq!(address.value(), None, "{window:?}");
        }
    }

    /// **`z₀` is offered to the head-from-`z₀` window and to no other.** Read off
    /// the symbol count through the real escape loop rather than off the address,
    /// because that is where the offer is made: a head opening on `z₀` has seen
    /// one more iterate than the orbit took steps, and the other two have seen
    /// exactly as many.
    #[test]
    fn only_the_head_from_z0_window_is_offered_the_pixel_itself() {
        let family = julia(Complex::new(-0.8, 0.156));
        let pixel = Complex::new(0.31, 0.22);
        let counted = |window| {
            let wants = Wants {
                itinerary: Some(Symbols {
                    sectors: 4,
                    base: 4.0,
                    // Deep enough that no window here fills, so the count is the
                    // number of iterates offered rather than the cap.
                    depth: 10_000,
                    window,
                }),
                ..Wants::default()
            };
            let orbit = run(&family, pixel, 400, &wants);
            (orbit.itinerary.symbols(), orbit.iteration)
        };
        let (from_z0, steps) = counted(AddressWindow::HeadFromZ0);
        let (from_z1, _) = counted(AddressWindow::HeadFromZ1);
        let (tail, _) = counted(AddressWindow::Tail);
        assert!(steps > 1, "the probe orbit has to actually run");
        assert_eq!(from_z0, steps + 1, "z0 spells a symbol of its own");
        assert_eq!(from_z1, steps);
        assert_eq!(tail, steps, "the tail never reads the pixel");
    }

    /// An average of one term has nothing to fade against, and an average of
    /// none has no value at all — the two cases where the deband lerp would
    /// divide by zero if it were written as one expression.
    #[test]
    fn a_short_average_still_answers() {
        assert_eq!(Average::default().deband(0.5), None);
        let mut one = Average::default();
        one.push(0.25);
        assert_eq!(one.deband(0.0), Some(0.25));
        assert_eq!(one.deband(1.0), Some(0.25));
    }

    /// The tail's roll is exact at the named modes' four sectors in base four to 26
    /// symbols, and at no setting where one of the three conditions fails.
    #[test]
    fn the_tail_rolls_exactly_only_where_its_arithmetic_is_exact() {
        let symbols = |sectors, base, depth| Symbols {
            sectors,
            base,
            depth,
            window: AddressWindow::Tail,
        };
        for (sectors, base, depth, exact) in [
            (4, 4.0, 26, true),
            (4, 4.0, 27, false),
            (2, 2.0, 53, true),
            (4, 8.0, 17, true),
            (4, 8.0, 18, false),
            (4, 3.0, 26, false),
            (4, 2.0, 26, false),
            (4, 4.5, 10, false),
            (1, 1.0, 10, false),
        ] {
            assert_eq!(
                symbols(sectors, base, depth).rolls_exactly(),
                exact,
                "{sectors} sectors, base {base}, depth {depth}"
            );
        }
    }

    /// **A tail address stopped at a repeat is the one run to the cap, and it did stop.**
    /// At the centre of the Mandelbrot set's period-3 bulb, outside the cardioid and the
    /// bulb the sampler answers before the loop, over caps that put the cap at every
    /// phase of the cycle, on the bits. A tail address counts every symbol it spelled, so
    /// fewer than the cap is the proof that the loop stepped round to the phase rather
    /// than running there.
    #[test]
    fn a_tail_address_stopped_at_a_repeat_is_the_one_run_to_the_cap() {
        let family = Family::Multibrot { degree: 2 };
        let pixel = Complex::new(-0.1225611668766536, 0.7448617666197442);
        let symbols = Symbols {
            sectors: 4,
            base: 4.0,
            depth: 26,
            window: AddressWindow::Tail,
        };
        let full = Wants {
            itinerary: Some(symbols),
            trap_circle: Some(1.0),
            ..Wants::default()
        };
        let stopped = Wants {
            interior: Some(Interior::REPEAT),
            ..full
        };
        for cap in 3000..3006 {
            let a = run(&family, pixel, cap, &full);
            let b = run(&family, pixel, cap, &stopped);
            assert!(!a.escaped && !b.escaped);
            assert_eq!(a.itinerary.symbols(), cap);
            assert!(b.itinerary.symbols() < cap / 2, "cap {cap}: never stopped");
            assert_eq!(
                a.itinerary.value().unwrap().to_bits(),
                b.itinerary.value().unwrap().to_bits(),
                "cap {cap}"
            );
            assert_eq!(
                a.trap_circle.to_bits(),
                b.trap_circle.to_bits(),
                "cap {cap}"
            );
        }
    }
}
