The three tables the supply engine runs on. Policy and measurement, as data.

```
release_mix.json            how much of a release each partition should be
cost_to_find_measured.json  what a finished run measured a unit of currency to cost
cost_to_find.json           the seed a run is handed: the measured table, shrunk
tau_h.json                  the cheap cut, per partition — underived, and says so
```

**`release_mix.json` is policy**, and it is the only copy. Relative ratios rather
than shares, so registering or retiring a partition renormalizes the rest instead
of leaving every other row wrong until somebody re-sums them. The table and the
partition registry are checked against each other in both directions at every
load: a registered partition with no ratio would be given a target of nothing and
read downstream as an absence of demand, and a ratio for an unregistered
partition quietly deflates every other ratio.

A ratio of zero is refused. A partition that should get none of a release is
retired from the registry; zeroing leaves it registered, floored, censused and
permanently starved. **A row is a ratio and there is no second kind of entry.**
There was one until 2026-09-02: `externally_supplied`, on `phoenix:classic`, which
kept its ratio and took away its share of the clock, its floor, and its place in
the starvation census. No job outside the walk ever filled it, so what the flag
bought was silence — the partition was zero at every stage from the walk onward
and the one report that would have said so had been switched off. A partition the
walk cannot currently feed is *starved*, and starvation is something this engine
already knows how to say.

**A release ratio is not a draw weight.** This table says how much of a
*release* a partition is owed; `curation/draw_weights.py` says what a partition
is worth in a *breadth draw*, given what it costs to render — `phoenix` and
`phoenix:classic` at 0.25 there since 2026-09-02, on `dtm_variants` spending
63.5% of a leg's clock on 10.6% of its candidates. The two are read at different
stages, neither derives the other, and a leg may lean on both at once: they
multiply. `phoenix:classic` sitting at 0.2 here and 0.25 there is not a
disagreement, it is two questions.

**The two price tables are evidence and policy, kept apart.**
`cost_to_find_measured.json` is what a run actually spent per unit of currency,
summed and divided once; nothing reads it at run time. `cost_to_find.json` is that
table shrunk geometrically toward its own median, and it is what a run is handed.
Shrinkage rather than a bound, because a bound cannot tell *implausible* from *the
thing the run was run to find out* — at the edge it reports the bound and discards
the measurement. A partition that produced less than one whole class-4's worth of
currency is not priced at all: it carries the flat seed and is stamped
`defaulted`, because minutes over zero units is no measurement, and dropping the
row would make "never served" indistinguishable from "never tracked".

Both tables came from the source project's last steady-state production run and
are the only numbers in this repository that were transferred rather than
measured here. Regenerate them from a finished run — never hand-edit a row, and
never edit the measured table the seed is derived from. Every constant, including
the smoothing rate, reaches a shipped table through a regeneration.

**`tau_h.json` is underived, and says so.** The cheap cut is a point on one
scorer's probability scale, so a value carried in from another project's scorer
would be a number about nothing. Every partition sits at the fail-open value and
the walk confirms everything it reaches; an absent table and a table of zeros read
identically to a run, and only the second one says which partitions were
considered.

```
fractal-wallpapers derive-prices --run artifacts/harvest --regularize --write
fractal-wallpapers derive-tau-h --write
```
