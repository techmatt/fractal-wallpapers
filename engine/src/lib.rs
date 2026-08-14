//! The rendering engine: escape-time fields, colormaps, and the resample that
//! turns one into a picture.
//!
//! The pipeline is a straight line, and each stage is a module:
//!
//! ```text
//! spec         a render described as JSON — family, viewport, coloring, colormap
//! mode         the named colorings: what a render asks for instead of parameters
//! family       the recurrence itself: what z starts at, and what one step does
//! iterate      one escape-time loop, and the channels an orbit is worth reading
//! field        those channels reduced over a supersampled grid → a scalar field
//! coloring     field → linear-light RGB, through a stretch and a colormap
//! direct_trap  the one coloring that paints during iteration and makes no field
//! dump         a field written to disk, and the record that says what it is
//! resample     Lanczos-3 down to the target resolution, then sRGB
//! ```
//!
//! The seam that matters is between [`field`] and [`coloring`]. A field is a
//! plain `Vec<f32>` with `NaN` marking the samples that have no value, so it can
//! be written to disk, colored more than once, or colored by something other
//! than this crate without any of the earlier stages running again. Everything
//! downstream of the field is cheap; everything upstream is not — which is what
//! `dump-field` and `recolor` are built on, and why [`direct_trap`], the one
//! coloring that has no field, is also the one that cannot be recolored.
//!
//! Deliberately absent: deep-zoom precision tiers, the derivative recurrence and
//! the lighting it feeds, and any fast path that trades a branch for clarity.
//! Those arrive later, behind the same seam.

pub mod coloring;
pub mod colormap;
pub mod direct_trap;
pub mod dump;
pub mod family;
pub mod field;
pub mod iterate;
pub mod maxiter;
pub mod mode;
pub mod resample;
pub mod spec;
pub mod viewport;
