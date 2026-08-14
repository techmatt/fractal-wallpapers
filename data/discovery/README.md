The seed pools a walk starts from. Data, not samplers — a walk over the
dynamical families draws its roots from these files, and the parameter-plane
families have no draw at all.

```
julia_c_pool.jsonl       209 julia parameters, thinned at the c-spacing floor
phoenix_seed_pool.jsonl   96 phoenix parameter points, (c, p, z₋₁) in full
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

There is deliberately **no pool for the parameter-plane families**. An unscreened
shell draw over the higher multibrot degrees measured zero good locations out of
a hundred and forty-four, so those walks are supplied by an explicit seed file
(`--seeds`) and by what the reframing operators find from places a walk already
reached.
