//! The one random number generator, and why the walk owns its seed.
//!
//! A walk is a search that draws: which focus it descends into, where in the
//! child frame that focus lands, how far it zooms. Every one of those draws has
//! to be reproducible from a number written down in the record, or a walk cannot
//! be re-run and a surprising result cannot be looked at twice.
//!
//! SplitMix64 is the whole generator: sixty-four bits of state, three multiplies
//! per draw, no seeding ritual. It is not cryptographic and does not need to be.
//! What it is, is *cheap to reproduce* — the constants below are the entire
//! specification, so the same stream comes out of any language that has 64-bit
//! wrapping arithmetic, which is what lets a walk be audited from outside this
//! crate.
//!
//! The stream a node expands on comes from [`sub_seed`], not from a generator
//! threaded through the run. That is deliberate: a node then expands identically
//! whichever batch it is popped in and whatever else the run did first, so a
//! single rung can be replayed on its own.

/// SplitMix64: state is the seed, and the seed is the state.
#[derive(Clone, Copy, Debug)]
pub struct Rng(pub u64);

impl Rng {
    /// The next 64 bits.
    pub fn next_u64(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }

    /// A uniform index in `0..n`. `n = 0` gives 0 rather than dividing by zero.
    pub fn below(&mut self, n: usize) -> usize {
        if n == 0 {
            return 0;
        }
        (self.next_u64() % n as u64) as usize
    }

    /// A uniform `f64` in `[0, 1)`, from the top 53 bits — the ones the mixer
    /// has stirred most.
    pub fn unit(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 / (1u64 << 53) as f64
    }

    /// A log-uniform draw in `[low, high]`, which is what a zoom factor wants:
    /// the band is a ratio, so halving and doubling should be equally likely.
    pub fn log_uniform(&mut self, low: f64, high: f64) -> f64 {
        if high <= low {
            low
        } else {
            (low.ln() + self.unit() * (high.ln() - low.ln())).exp()
        }
    }
}

/// The stream one node expands on, from the run's seed and the node's id.
///
/// Both go through the mixer rather than being added, so neighbouring node ids
/// do not give neighbouring streams — and a node's expansion is a pure function
/// of `(seed, node_id)`, independent of batch order.
pub fn sub_seed(seed: u64, node_id: u64) -> u64 {
    Rng(seed ^ node_id.wrapping_mul(0x9E37_79B9_7F4A_7C15)).next_u64()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_unit_draw_stays_inside_the_half_open_unit_interval() {
        let mut rng = Rng(12345);
        for _ in 0..10_000 {
            let value = rng.unit();
            assert!((0.0..1.0).contains(&value), "{value}");
        }
    }

    #[test]
    fn a_seed_reproduces_its_whole_stream() {
        let first: Vec<u64> = (0..8).scan(Rng(7), |r, _| Some(r.next_u64())).collect();
        let again: Vec<u64> = (0..8).scan(Rng(7), |r, _| Some(r.next_u64())).collect();
        assert_eq!(first, again);
    }

    #[test]
    fn distinct_nodes_of_one_run_get_distinct_streams() {
        let seeds: Vec<u64> = (0..64).map(|id| sub_seed(20260814, id)).collect();
        let mut sorted = seeds.clone();
        sorted.sort_unstable();
        sorted.dedup();
        assert_eq!(sorted.len(), seeds.len());
        assert_eq!(sub_seed(20260814, 5), sub_seed(20260814, 5));
        assert_ne!(sub_seed(20260814, 5), sub_seed(20260815, 5));
    }

    /// A zoom band is a ratio band: the geometric mean of many draws must land
    /// near the geometric center, not the arithmetic one.
    #[test]
    fn the_log_uniform_draw_is_uniform_in_the_logarithm() {
        let mut rng = Rng(99);
        let n = 20_000;
        let mean_log: f64 = (0..n)
            .map(|_| rng.log_uniform(0.35, 0.50).ln())
            .sum::<f64>()
            / n as f64;
        let want = (0.35f64.ln() + 0.50f64.ln()) / 2.0;
        assert!((mean_log - want).abs() < 0.01, "{mean_log} vs {want}");
        assert_eq!(rng.log_uniform(0.4, 0.4), 0.4);
    }
}
