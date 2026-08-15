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
//! Beside that line sits the **search**, which uses it rather than extending it:
//!
//! ```text
//! rng          SplitMix64, so a walk is reproducible from a number
//! screen       the structural gates — interior cap, escape band, occupancy
//! foci         where to look next: scale-space maxima, density, uniform
//! expand       one rung of a walk, for a batch of nodes
//! ```
//!
//! And beside *that*, the one bulk producer:
//!
//! ```text
//! tiles        one field per location, many colored crops of it — the pictures
//!              a judge is trained on
//! ```
//!
//! The search decides *where* to render and never *how*: it reads fields the
//! pipeline above produced and returns coordinates. What makes a picture good is
//! not its business — that judgement lives in Python, in a scorer this half is
//! written to be steered by and does not contain.
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
pub mod expand;
pub mod family;
pub mod field;
pub mod foci;
pub mod iterate;
pub mod maxiter;
pub mod mode;
pub mod resample;
pub mod rng;
pub mod screen;
pub mod spec;
pub mod tiles;
pub mod viewport;
