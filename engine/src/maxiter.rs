//! How many iterations a view deserves.
//!
//! The iteration cap decides what counts as interior, so it is a rendering
//! parameter disguised as a performance one. Set it too low and structure that
//! would have resolved turns into a flat black lake; the picture is not slow,
//! it is wrong.
//!
//! What the cap should track is **zoom depth**, not magnification. Escape times
//! at a given visual scale grow roughly like the logarithm of the magnification,
//! so the cap grows linearly in octaves:
//!
//! ```text
//! maxiter(width) = clamp( BASE · (1 + K · log₂(HOME_WIDTH / width)), FLOOR, CEILING )
//! ```
//!
//! The constants come from the source project, where they were measured rather
//! than guessed: a set of locations spanning ten octaves of depth was each
//! walked up a ladder of caps until the rendered structure stopped changing, and
//! the converged cap came out at a near-constant multiple of the shape above.
//! The shape was right; the base was eight times too low. `BASE` is that
//! corrected value, and `CEILING` exists only to stop the raised base from being
//! re-clipped at depth.

/// The view width the policy is calibrated at — a view of the whole set.
pub const HOME_WIDTH: f64 = 3.0;
/// Iterations at `HOME_WIDTH`.
pub const BASE: f64 = 4000.0;
/// Iterations added per octave of zoom, as a fraction of `BASE`.
pub const PER_OCTAVE: f64 = 0.30;
/// Never iterate fewer than this, however far out the view is pulled.
pub const FLOOR: f64 = 200.0;
/// Never iterate more than this, however deep the view goes.
pub const CEILING: f64 = 67_000.0;

/// The iteration cap for a view of the given plane width.
pub fn for_width(width: f64) -> u32 {
    if width.is_nan() || width <= 0.0 {
        return BASE as u32;
    }
    let octaves = (HOME_WIDTH / width).log2();
    let raw = BASE * (1.0 + PER_OCTAVE * octaves);
    raw.clamp(FLOOR, CEILING) as u32
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_home_width_gets_the_base() {
        assert_eq!(for_width(HOME_WIDTH), BASE as u32);
    }

    #[test]
    fn each_octave_of_zoom_adds_a_fixed_share_of_the_base() {
        let one = for_width(HOME_WIDTH / 2.0);
        let two = for_width(HOME_WIDTH / 4.0);
        assert_eq!(one, (BASE * 1.30) as u32);
        assert_eq!(two, (BASE * 1.60) as u32);
    }

    #[test]
    fn the_clamps_hold_at_both_ends() {
        assert_eq!(for_width(1e12), FLOOR as u32); // pulled far out
        assert_eq!(for_width(1e-40), CEILING as u32); // driven far in
    }

    #[test]
    fn a_degenerate_width_falls_back_rather_than_producing_nonsense() {
        assert_eq!(for_width(0.0), BASE as u32);
        assert_eq!(for_width(-1.0), BASE as u32);
    }
}
