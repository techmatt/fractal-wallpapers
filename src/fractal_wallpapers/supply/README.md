Turning compute into new good material where it is scarcest: the census, the
price, the allocation, and the loop that spends the clock on them.

```
partitions   what the books are kept separately for
release_mix  one ratio table, shipped as data
currency     what a find is worth, and where the cuts are
location     what "the same location" means, once
ledgers      the union of everything every walk has found
census       stock, target, and the standing deficit
prices       cost to find: the measured estimate and the seed it starts from
apportion    a share vector into whole slots, without zeroing anybody
allocation   the floor, the water-filling, and the floor's carry
quota        the object a run holds; the only thing that decides the mix
refill       what to do about a partition whose queue has run dry
twins        Julia parameters derived from the parent plane's admissions
proven       roots at every location a human scored a keeper, at the frame they scored
saturation   cross-run memory, straight off the ledgers
novelty      the two levers against monotony: the discount and the share
autopsy      what each claim on the batch bought, in pictures, and why each refusal was one
places       `harvest export` / `harvest stats`: a run's kept places as one file and one page
tau_h        how good a cheap look must be before a real one is paid for
harvest      the production loop, and everything that keeps it honest
```

The loop: **census** (what each partition holds against what the release mix says it is
owed), **price** (what a unit of currency costs there, measured as the run goes),
**allocate** (intended share of the clock ∝ deficit ÷ price, with a floor everyone gets),
**serve** (divide the batch's slots by how far each partition is below its intent),
**credit** (what the batch found, deduplicated, back into price and stock). A batch's
slots are claimed in a **ruled, one-directional order**: 1 the **floor** (the carry's
claimants), 2 the protected exploration **share** of what is left, 3 the deficit-priced
**contest** over the remainder, lineage-discounted. Nothing below eats what is above.

```
fractal-wallpapers census
fractal-wallpapers harvest --minutes 30 --root-channel proven   # the standing leg: every partition
fractal-wallpapers harvest --finish-by 07:00 --release-slots 20 --release-workers 8
fractal-wallpapers harvest --no-exploration --lineage-discount 0   # neither lever
fractal-wallpapers harvest --partition phoenix:classic --root-channel proven --root-channel viewport_sampler
fractal-wallpapers harvest --out-dir <run> export                 # or: stats
fractal-wallpapers derive-proven-seeds --partition mandelbrot --write   # to read it
fractal-wallpapers derive-plane-seeds --columns N --per-partition M --write
fractal-wallpapers derive-prices --run artifacts/harvest --regularize --write
fractal-wallpapers derive-tau-h --write
```

## The books and the mix

**Currency is `n4 + 0.1·n3`** (`currency.CLASS_WEIGHT`), one table read by the deficit,
the in-run price and the readout, so moving a weight moves all three. **Stock is two legs
and a location is in exactly one**: the human's class where a human has looked, else
`census.MACHINE_STOCK_DISCOUNT` (0.2) × the machine's class. Precedence, never addition
(a sheet is cut from ledger rows, so a location can be in both). The discount sits under
the ~50% rate at which machine keepers survive a human look, so a machine-filled
partition keeps a mild appetite until labels re-anchor it.

**The standing deficit is a launch snapshot**; only prices and realized minutes move
inside a run. **The mix is decided where the batch is popped**, never by weighting the
root draw (whatever multiplies fastest in the frontier dilutes that). The quota tracks
realized *minutes* and serves whoever is furthest below; slot demand is minute demand ÷
what a slot costs there, so being cheap buys turns, not time. Unspent floor time carries
in minutes and comes due at batch twenty at a 5% floor.

**A named-partition list aims a leg; it does not overrule the census share.**
`--partition` is repeatable, default every registered one. One partition keeps the books
for it alone; several buy each a seat and the 0.05 floor, not minutes: a partition at
zero deficit runs on its floor. **To move the clock, move the census** (label it, or
change `release_mix`).

**Four levers stand between a long run and one composition.** The per-root expansion
cap bounds what a root *spends* (`--root-expansions` 12 on a parameter plane,
`--dynamical-root-expansions` 36 on julia and phoenix, per Matt's ruling that variety
within one `c` is wanted; `discovery/walk.py`'s `Limits`). `--lineage-cap` (off in a
harvest, on for a deep run) bounds what it *books*, exactly, recording further admits
`not_admitted` with `lineage_capped: true`. Under them, two soft levers in `novelty`:
the **lineage discount** `max(f, 1/(1+k·n))` on a lineage's expected credit, `n` its
admissions this run, in the contest only and applied at the pop so the Gumbel is never
re-rolled; and the **exploration share**, post-floor slots reserved for roots whose
neighbourhood no ledger has booked from, priced on its own admission rate, where only
the junk floor kills.

**The exploration share is spread evenly over the drawable partitions, carried across
batches** (`Exploration.taken`, checkpointed): a batch holds one or two share slots
against ten partitions. `exploration_slots` never sees an intent. `share.weight_source`
reads `even_carry`; a 0.0 in `quota.exploration.realized.per_partition` beside a
non-empty `novel_queues` is a defect.

⚠ **`--lineage-cap` and the reconcile**: a capped lineage's rows push no node, and the
batch identity subtracts rows whose lineage the walk reports full.

## Root channels

**The standing leg is every partition with `--root-channel proven` on.**

**`proven`** roots the walk at every place a human scored a keeper, at the scored frame:
it returns ~95% of a run's admissions. On a dynamical partition it buys a *frame* a
`c`-pool cannot express (a pool root comes up at the home view, nearly always already
saturated). Off unless named, and interleaved, never substituted: it opens no new
ground. Decided in `proven.py` alone: the **tier floor** `min(currency.CLASS_WEIGHT)`
(3, exactly a keeper); the **three quality label stores** (`proven.stores()`), unioned
and deduplicated on the place, credited on `provenance.store`; **every partition**
(`SERVED` is `ALL_PARTITIONS`); **`RATIO` 2** proven entries per pool entry; order
**best tier, then `blake2b(key)`**, so a resume is exact and stable as the store grows,
and the root id names a place, not a position.

**`twins`**: an admitted degree-`d` plane location's centre *is* a `c` for the degree-`d`
Julia family. At degree 2 the derived list and the tracked pool share the queue one for
one, the pool reserved into the c-spacing floor; little derives there because the pool
claims nearly the whole plane. A `c` inside the floor of one walked is counted
(`near_walked`), not refused. `proven.interleave` is unstable under a growing second
argument, so `_twin_queue` builds once and extends. New proven julia roots are not new
`c`: count both.

**`viewport_sampler`** (`discovery.viewport_sampler`) serves the pinned plane and every
parameter plane, not a twin. On the **pinned plane**, a jittered grid over the home box
per octave rung (`(4^(R+1) - 4) / 3` frames, 340 at the default four, `--sampler-rungs`);
rung 4 is the productive one per root, so widen it before adding a rung, and a new
`--seed` redraws the same ground. On a **parameter plane**, a straddle refinement
(`discovery/README.md`'s *A parameter plane: straddle refinement*) merged at the queue's
tail (`Refill._continuous_queue`) behind the pool-plus-proven side; such a partition is
open until the channel says exhausted (`Refill._open`), and refinement is paid inside
the refill, under `--refill-share`.

**The plane seed pool** (`data/discovery/plane_seed_pool.jsonl`) is deterministic
(`verify` asserts byte equality), so a walked-out plane has no fresh pool supply until a
`derive-plane-seeds --write`. Its `home_view` rows never produce; they keep
`has_channel` true for a family the solver refused. A root names its channel under
`provenance.channel` (`source` is the pool file).

**A pinned plane's fresh-root pool is one row** (`pools.classic_phoenix_pool()`), so
`phoenix:classic` lives off `proven` and the sampler. **Naming no root channel leaves a
one-root partition unservable, and nothing reports it starved**: `has_channel` is true,
and `starved()` declines because `remaining()` is zero. Read `pool_state`'s launch lines
(pool size, label share, drawn, or why nothing serves) and make a single-digit pool name
a channel or drop the partition.

### With no root channel named, the whole standing root supply is small enough to walk out in a night

On pools and twins alone every queue empties together and the run stops `nothing
servable` inside a long budget. Budget such a leg at about five hours: the partition list
aims a leg, it does not extend one.

### The refill cadence

Under `--low-water` (`LOW_WATER` 8, which is `Limits.batch`) a partition is handed
`low_water` roots (one knob, two jobs; `per_draw` has no flag), then left for
`--cooldown` batches (`COOLDOWN` 10). `starved` already skips `remaining <= 0`, so on a
live shelf the cooldown only idles screened viewports. **The cadence was the whole of
it** on a one-partition pinned-plane leg: `--low-water 16 --cooldown 1` runs its clock
out. The defaults suit a ten-partition run and stay.

## Degree 6: twelve partitions, two with no labels behind them

`multibrot6` and `julia:multibrot6` are in `partitions.PARAMETER_PLANES`, so
`ALL_PARTITIONS` is twelve; `release_mix.json` 1.0, `tau_h.json` fail-open 0.0, prices
measured at **2.736 active minutes a unit (`multibrot6`) and 0.027 (`julia:multibrot6`)**.
**Nothing label-fed will ever serve them** (`partitions.NEVER_LABELLED`): the sampler is
the plane's one root source, so a harvest turns it on for `multibrot6` unnamed
(`cli.supply_commands.build_sampler_channel`); the twin feeds off its plane.

```
fractal-wallpapers harvest --partition multibrot6 --root-channel viewport_sampler
```

## The clock

**`--minutes` counts active minutes** (`expand` plus `trigger_reframings`); outside it
are start-up (about six minutes, even with `--no-saturation`), refills, the closing
re-score and `curate score`. Wall per active minute is
`schedule.ACTIVE_TO_WALL_DRAWING_VIEWS` (1.13) when the judge draws views, else
`ACTIVE_TO_WALL_SCORING_GATE_RENDERS` (1.013); the config picks, `schedule.plan` says
which. **It is the only backstop** (`--wall-budget` is `curate run`'s): no batch starts
whose running mean would overrun. Pair it with `--batches`.

**`--finish-by HH:MM` derives `--minutes`**: the span to the next `HH:MM`, less the
release leg, the rest of `curate run`, the closing `curate score`, a 2-minute ledger load
and a 20-minute margin, divided by the ratio. `schedule.py` owns every term and writes
it to `summary.json` as `finish_by`. Read rather than written: the **release rate** off
the latest tracked release leg (`data/curation/runs/<run>.json`, scaled to
`--release-workers`, 41.9 s the fallback; the caller passes `records.latest_release_leg()`
to `schedule.release_rate`, so `schedule` imports no record store); the **closing
re-score**, solved rather than iterated; the **colorize term**, `curation.budget`'s
answer for `--strange-share` and `--strange-modes`. `--release-slots` defaults to
`curation.run.DEFAULT_N`. It derives; it does not pace.

### `--score-workers` is a flag with almost nothing left to do

A harvest scores the gate render `expand` already wrote, so it draws no picture to
score; where views are drawn the engine's own threads saturate the box (two workers
0.88x, four 1.01x). It stays for re-scoring an old ledger. `curation.release` does earn
its fan-out (3.19x at four).

**Run a harvest through `python -u`**, or a backgrounded leg's log stays empty through
start-up.

## Ledgers, reconcile and resume

**`--ledgers` names one root, one tier** (default `artifacts`, the hot tier via
`cli.resolve_output`), and `saturation` and `novelty` are only as wide as it; no value
reaches the whole history. `ledgers.ledger_paths` answers how many (looked up at
`<run directory>/walk.jsonl`, never `rglob`). The `run` header records `invocation`
beside `ledgers_read`. A saturation verdict is re-derivable:
`saturation.build(paths=ledgers.ledger_paths(root, exclude))` and
`VisitedIndex.density`. `_apply_memory` asks only about survivors.

**Every batch reconciles, and one that does not balance ends the run**
(`ReconcileError`, a `SystemExit`): every candidate has a known fate, every frontier
arrival is admitted or expandable, every admission is new or known. The checkpoint
(`harvest.STATE_SCHEMA` 5) is written after the reconcile; **an older schema is refused
at resume**, never adopted. A crashed run's failed-batch rows stay in `walk.jsonl`: cut
the ledger back to the checkpointed batch first, keeping the full copy.

## What a run writes for a readout to price it with

`walk.jsonl`'s row kinds and `harvest export`'s `locations.jsonl` are in the root
[`FORMATS.md`](../../../FORMATS.md). `summary.json` adds: `tally.by_partition` (share
against contest per partition, median head score off `harvest.SCORE_BINS` bins);
`tally.saturation_by_partition`; `tally.minutes` (`expand`, `reframe`, `refine`, the last
the once-per-run close-time framing scan, charged after `--minutes`, not budgeted);
`walk.operators` and `walk.counts` (`reframing:<operator>:<available|reason>`,
`refine:*`); `refine` (see `discovery/README.md`); `quota.floor_versus_deficit` and
`quota.unspent_floor` (`spent`, `unspent`, `starved`).

## Reading a run afterwards: `quota.jsonl` beside the ledger

Every batch appends to `<run>/quota.jsonl`: intent, folded vector, floor debts, prices,
queues, and slots per partition per channel. The **channel autopsy reads it**: a refused
card names its floor and, for a frontier node never expanded, why (capped, outbid on
partition or rank, discounted lineage, run stopped). The sample is **stratified by
fate** (two cards a class minimum) and covers unpictured structural refusals.
