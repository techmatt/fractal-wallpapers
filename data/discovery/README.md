The seed pools a walk starts from. Data, not samplers — a walk draws its roots
from these files, and no family in this project invents one.

```
julia_c_pool.jsonl         209 julia parameters, thinned at the c-spacing floor
phoenix_seed_pool.jsonl     96 phoenix parameter points, (c, p, z₋₁) in full
plane_seed_pool.jsonl    1,922 parameter-plane roots, solved for rather than drawn
```

**The julia pool** is what a three-stage screen left after drawing the
near-boundary shell, screening each `c` for viability at one render, and ranking
the survivors on boundary proximity with the interior-lake channel required to
fire. Its `channel` column is provenance and nothing selects on it: `ranked_harvest`
and `cheap_harvest` are parameters that were ranked from a canonical and a cheap
render respectively, `near_minibrot` is one parameter per known degree-2 nucleus
at a fixed multiple of its atom radius, and `near_boundary` is the unbiased
near-boundary draw the earlier pool was made of.

Its one invariant is the **`c`-spacing floor of 3.2e-2**, verified at every load.
That number is a tolerance chosen against pool cost, not a distance at which the
looks stop being similar: measured at a fixed viewport across five decades of
separation the near-duplicate rate falls smoothly the whole way, with no knee to
read a floor off. What it buys is a stated rate at the bottom of the admitted
band — the closest pairs it admits are near-duplicates about 7% of the time,
against about 20% at a floor three times finer.

**The phoenix pool** is drawn near the exact stability skeleton, which is what
replaces "near the boundary of the set" for a family that has no such boundary:
the phoenix recurrence lifts to an invertible map with no critical point, so
there is no connectedness locus to sit on the edge of, but the curves where the
fixed point and the two-cycle go neutral are closed forms and are where the
near-parabolic filigree lives. Two branches survive in the shipped pool —
cardioid and period-2 — because the third was drawn, labeled, and measured dead
to a human eye. `real_p_mode` marks the sampler's real-`p` sub-mode and is **not**
the classic pinned instance; it says `p` was drawn on the real axis with no
displacement off the curve and `z₋₁` zero, while `c` still comes from the closed
form at a complex phase.

**The plane pool is solved for, not drawn.** An unscreened shell draw over the
higher multibrot degrees measured zero good locations out of a hundred and
forty-four, so there is no sampler for `mandelbrot` or `multibrot3/4/5` and there
will not be one. Instead a coarse grid — 340×191 — is laid over each family's home
frame, every point is handed to this repository's own `identify_nucleus`, and each
distinct atom becomes one root framed at `FRAME_MULTIPLE ×` its own window scale.
Roots are kept round-robin across periods (21–37 per family) and ranked on `f64`
headroom only *within* a period, so the pool is places rather than five hundred
views of one place. Each family also contributes its home view, and the six
hand-picked Mandelbrot frames the earliest walks ran on are carried along as the
only roots here a person chose.

Regenerate it — never hand-edit it — with:

```
fractal-wallpapers derive-plane-seeds          # re-derive and check the shipped file
fractal-wallpapers derive-plane-seeds --write  # re-derive and replace it
```

The verify is the default because the file's only real claim is that the
procedure still produces it. Roughly fifteen minutes of Newton either way.

This pool is load-bearing rather than convenient: without it `has_channel` is
false for all four parameter-plane partitions, they can never be refilled once
their queues drain, and a harvest that intended two thirds of its clock for them
spends none of it. That is exactly how the first production run stalled.
