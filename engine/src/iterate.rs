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
    /// How many symbols to take before stopping.
    pub depth: u32,
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
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct Address {
    value: f64,
    /// The weight the next symbol will carry: `base^{−(n+1)}`.
    weight: f64,
    count: u32,
}

impl Address {
    /// Add the sector this iterate landed in, unless the address is already full.
    fn push(&mut self, z: Complex<f64>, symbols: Symbols) {
        if self.count >= symbols.depth {
            return;
        }
        if self.count == 0 {
            self.weight = 1.0 / symbols.base;
        }
        // `atan2` runs `(−π, π]`; shifting by π puts the cut on the negative real
        // axis and the sectors in `[0, k)` counting counter-clockwise from there.
        let turns = (z.im.atan2(z.re) + std::f64::consts::PI) / std::f64::consts::TAU;
        let sector = (turns * symbols.sectors as f64).floor();
        let sector = sector.clamp(0.0, (symbols.sectors - 1) as f64);
        self.value += sector * self.weight;
        self.weight /= symbols.base;
        self.count += 1;
    }

    /// The address, if any symbol was spelled at all.
    pub fn value(&self) -> Option<f64> {
        (self.count > 0).then_some(self.value)
    }

    /// How many symbols the address holds.
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

    // **The address's first symbol is `z₀`'s.** Every other channel here
    // accumulates from `n = 1`, which for an average is a rounding difference. For
    // an address it is not: `s₀` is the most significant digit, so dropping it
    // shifts every address by a whole base-`k` place and the field means something
    // else. This push is the only reason `z₀` is offered to any channel at all.
    if let Some(symbols) = wants.itinerary {
        orbit.itinerary.push(z, symbols);
    }

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
            orbit.smooth = smooth_count(n, magnitude_sq, family.degree());
            if wants.derivative {
                orbit.derivative = dz;
            }
            return orbit;
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
fn smooth_count(n: u32, magnitude_sq: f64, degree: u32) -> f64 {
    let log_z = 0.5 * magnitude_sq.ln(); // ln|z|
    let log_bailout = BAILOUT.ln();
    let overshoot = log_z / log_bailout;

    // The double logarithm is finite only for an orbit genuinely outside the
    // bailout disc. Anything else — an overflow to infinity, a degenerate
    // bailout — falls back to the integer count rather than poisoning the field
    // with a NaN that would read as "interior".
    if overshoot.is_finite() && overshoot > 0.0 {
        (n + 1) as f64 - overshoot.ln() / (degree as f64).ln()
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
            }),
            derivative: true,
        }
    }

    #[test]
    fn the_origin_is_interior_to_every_multibrot() {
        for degree in 2..=5 {
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
}
