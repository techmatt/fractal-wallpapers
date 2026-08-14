//! The rendering engine: escape-time fields, colormaps, and the resample that
//! turns one into a picture.
//!
//! The pipeline is a straight line, and each stage is a module:
//!
//! ```text
//! spec      a render described as JSON — family, viewport, resolution, colormap
//! family    the recurrence itself: what z starts at, and what one step does
//! iterate   one escape-time loop, shared by every family
//! field     that loop run over a supersampled grid → a scalar field
//! coloring  field → linear-light RGB through a colormap
//! resample  Lanczos-3 down to the target resolution, then sRGB
//! ```
//!
//! The seam that matters is between [`field`] and [`coloring`]. A field is a
//! plain `Vec<f32>` with `NaN` marking the pixels that never escaped, so it can
//! be written to disk, colored more than once, or colored by something other
//! than this crate without any of the earlier stages running again. Everything
//! downstream of the field is cheap; everything upstream is not.
//!
//! Deliberately absent: deep-zoom precision tiers, alternate coloring channels
//! (orbit traps, distance estimates), and any fast path that trades a branch for
//! clarity. Those arrive later, behind the same seam.

pub mod coloring;
pub mod colormap;
pub mod family;
pub mod field;
pub mod iterate;
pub mod maxiter;
pub mod resample;
pub mod spec;
pub mod viewport;
