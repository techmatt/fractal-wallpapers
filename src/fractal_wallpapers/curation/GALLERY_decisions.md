The append-only log this stage's reasoning lives in: the retirements, the audits, the
flips and the before/afters that reached what [`GALLERY.md`](GALLERY.md) now states in
the present tense. Every section below was moved here **verbatim on 2026-09-12** from
that file, under its original heading and in its original order — nothing was
rewritten, re-dated, merged or reordered on the way across, so a citation that named
one of these headings still resolves. **One class of edit was made and it is the
only one**: a pointer that said *above* or *below* about a section that stayed in
[`GALLERY.md`](GALLERY.md) now names that heading and that file, because a
direction is a citation that goes wrong silently once the two files are apart.

Read this for *why the answer is this one*, and read [`GALLERY.md`](GALLERY.md) for
*what the answer is*. A section here is a reading of the tree in front of it on the day
it was taken: the constants, the record fields and the stores it names may have moved
since, and where a live spelling is what a reader needs, the reference file is the
authority.

**New entries are APPENDED and never inserted**, and an entry already here is never
edited in place. A decision that supersedes one below is a new section at the bottom
saying so, because a log rewritten to agree with today cannot say what anybody believed
yesterday.

## The pre-solver gallery pass, and what took its place

**Deleted on 2026-08-28**, ruled at ckpt 87. The command was spelled `curate
gallery` — a spelling this project no longer has, and **not** today's `curate
solve record`, which is a solve and not a draw. It was the second
phase: a quality-weighted farthest-point draw over the neutral embeddings picked
N locations, each chosen point bought a small judged attempt on its own
neighbourhood, and a sequential walk seated the winners under two floors, the
one-wallpaper-per-location rule and the colour ceiling. Four passes ran under it —
`gallery1` through `gallery4` — and **what they wrote is now their winners and
nothing else**: the rows in `data/curation/release/<pass>/`, and 14,316 rows in
the candidate ledger. Their pass records, slot rows, manifests and attempt store
were retired on 2026-09-06, Matt's ruling. Two things were established before
deleting: the numbers a doc priced a full-size leg off already sit in
[`MEASUREMENTS.md`](MEASUREMENTS.md), and no label row in any store resolved
through that store — all 26,066 of them resolve on their own join, `n_unkeyed`
zero in every store before and after.

**What replaced it is propose-then-choose.** `curate solve` is the whole
choosing now — off the candidate ledger rather than off a draw's own attempts, so
it chooses among pictures that already exist. It draws no points: the ledger is
the proposal side and `curate hunt`, `curate mine` and `curate depth` are what add
to it. It renders its seats unless told `--no-render`, at
[`release.RELEASE_REGIME`], which is the geometry the pass shipped at and is now
named where every leg that ships a wallpaper reads it.

It was briefly two legs — a sequential `curate seat` and an exact `curate solve` —
and that pair is gone too. `curate seat` is retired; the exact solve is retired;
the one leg behind `curate solve` is *`curate solve` — one leg, one pool, one
command* in [`GALLERY.md`](GALLERY.md).

Three commands went with the phase: `curate gallery` itself, `curate draw` (its step-4
point draw alone) and `curate on-demand` (the reconciliation of a pass's
extra-pick log with its attempt store, which had already run on every pass it was
written for). `curate gallery-store` outlasted them by nine days, because the four
passes' attempt rows were about a third of what the ledger's backfill could reach
— and it went on 2026-09-06 as well. What that costs is stated at
[`candidate_ledger.rebuild`](candidate_ledger/rebuild.py): a rebuild from scratch
would now produce a ledger short those rows. The rows already in the ledger are
untouched, and the ledger is durable, mirrored and checked, so a rebuild is not a
path anybody should be on.

What the pass established and the gallery stage still rests on is in
[`GALLERY.md`](GALLERY.md): the
**colour ceiling** and its targets, which `curate solve` reads; the **binding reason** an empty seat records, which is how the four passes'
slot rows are still re-read; and the **framing refinement**, whose live home is
the walk's own close-of-run leg (`supply/harvest.py`) rather than a seating.

**A `centered` row is refined on its scale alone.** A location row carrying
`centered: true` — every nucleus location `discovery.reframing` writes, and
anything else whose centre *is* the location — has stage B switched off:
`framing.recentres` returns nothing for it, `framing.refine` plans no stage-B
frames for it, and the record says `centered` beside the decision. Three frames a
location instead of seven, and the reason is not the saving: a quarter-frame off a
solved nucleus is a crop of somewhere else wearing the atom's name, and the
minibrot the reframing channel exists to frame would be off centre in the picture
a gallery seats. The flag is read off the row through `framing.is_centered`, never
off a channel name, so a row that has never heard of the field and a row that says
`false` are one case.

#### A budget to the pair, and the two records made before it was one

⚠ **It was a budget between SEATS until 2026-09-09, and a gallery with few seats
could overrun it by a lot.** The clock was read once per seat in the sweep, and
`chain_at` is a nested walk over that ejection's whole `ready` list — so one
seat's neighbourhood was unbounded in time and a sweep's granularity was the seat
count. Observed 2026-09-07: a pass holding **7** seats ran the stage **522.8 s
against the 300 s budget**, 74% over, on 150 million pairs. At the shipping rungs
it was invisible — a thousand seats is a thousand clock reads a sweep — and it bit
exactly where the gallery is small and the population large, which is the case a
budget exists for.

**The check is now inside the walk**, in `chain_at` and in `_terminal` both, read
before every pair and unwinding whatever trial is in flight, so a bound stage
stops at a trial boundary on a gallery as valid as an exhausted one's. The read
costs a `monotonic` against a `counted_refusal` on the same iteration.

**It was a proposal until then, and what settled it was those two records.** The
argument for taking it was that a bound stage's seating is already decided by
wherever the clock happened to fall mid-walk, so no correct answer is being
preserved — true only if no record was made that way. Two were. Every `augment`
block in every record on the box was swept for a phase whose `stopped_because`
says the budget ran out: **57 records carry an augment block and exactly two
bound**, both `depth_2`, both n=2000, both under `artifacts/curation/solve/` —
`tentative_n2000_20260904T234133Z` (300 s budget, 301.24 s, 867,427 pairs, filled
1,795) and `tentative_n2000_20260905T001615Z` (1,800 s budget, 1,822.61 s,
13,186,436 pairs, filled 1,984). They are the two this section quotes as *seats
1,795 at 300 s and 1,984 at 1,800 s*. Neither is a published stamp, and both are
records the store keeps and a stamp can name. **They were made under the unbounded
stage and they are left exactly as they are**: re-solving them would be a
different pass's answer written under a stamp that already means something, and
the readings above are read as *what the stage did on 2026-09-04*, not as
something today's code reproduces. A record made after 2026-09-09 at n=2000 will
not agree with them, and that is the change working rather than a discrepancy.

**At n=2000 it is a budget question and the exhaustive cost is unknown** — over
30 minutes, and nothing has run it to the end. What dominates there is the **chain
search and not the diversity rule**: the search is **40% of augment time at n=2000
against 91% at n=1000** [measured], so the next speedup at the larger rung is in the
search rather than in `Twins.within`. The shipped stage seats 1,795 at 300 s and
1,984 at 1,800 s, neither exhausted and no mode short.

### A `p_fine` bar on the view raises the objective and deletes the worst fifth

**First, the filter is a filter on the seatable pool and not a coverage hole
wearing one.** Of the 277,542-candidate pool, 40,127 rows clear their mode's bar,
and the fine head has read **exactly those 40,127** — `clearing == above_bar` holds
*set for set* and not merely in count, with every accepted mode landing on the
`p_ge4` rule and none falling back to `p_ge3`. The other 237,415 are refused
`below_its_mode_bar` before any rule runs, so **excluding unscored rows costs a
solve nothing**. Of the 40,127, **10,974 read ≥0.50**, 9,646 ≥0.60 and 8,271 ≥0.70
— Matt's ratified bar keeps a **quarter** of the seatable pool.

**It fills at 0.50 and at 0.60, and 0.70 is open rather than short.** The 943 seats
the 0.70 arm reported are a budget artifact: the chain stage stopped on
`augment.DEFAULT_SECONDS` at 300.8 s with sweep 2 still finding 26 chains, where
0.50 and 0.60 both exhausted. 0.80 and 0.90 were never run. That is *A narrowed
view is a different cost regime, and the budget DOES bind there* in
[`GALLERY.md`](GALLERY.md), and it is why a short seating over one is read off the
augment log before it is believed.

**The filter RAISES the objective while filling the same thousand seats** — sum
**1786.5 → 1876.6** at 0.50, and 1887.0 at 0.60. So the unfiltered solve is leaving
objective on the table rather than spending it on breadth it could not otherwise
buy. What it costs is the demand shortfall, **0 → 18**, and two starved mode floors.

**And the median barely moves: 0.9343 → 0.9314.** The bar is not buying a better
gallery so much as **deleting its worst fifth** — the control seats 69 pictures
below `p_fine` 0.10 and 173 below 0.50, and at 0.50 those are zero by construction
while everything above the bar is left roughly where it was. **581 of 1000 seats and
649 of 1000 places are shared with the control**, so it is a real re-composition and
still far less violent than the `rank-key → cascade` flip, which shared 179.

The four runs whole are [`MEASUREMENTS.md`](MEASUREMENTS.md)'s *What a `p_fine` bar
on the view buys at n=1000, measured 2026-09-07*; what one costs on the clock is
*What the solve costs by stage, control and narrowed, measured 2026-09-07* beside it.

#### The first seating on the adopted column, and what the concentration cost

**`20260910T025205Z`, n=1000 at the defaults with `--explain-keys` over the 442
gallery-grade rows** — `tentative_solve_20260909`. Full at 1,000/1,000, shortfall
0, 13 of 13 modes, 48 of 48 cells at or over the colour floor, zero deadlock, 78.4 s.

**Seat churn against `20260909T215815Z` is 784 of 1,000**, which is the adoption's
whole effect on the seating with every rule held still. For scale, the colour floor
itself moved 162 seats. **The seating churns LESS than the pool did**: the admitted
row set turned over 93.3% and the seating 78.4%, because 399 of the 784 arrivals are
rows the old bar admitted too and simply did not seat.

⚠ **448 fewer places cost 189 clusters, and the cluster is what the seat rule
reads.** Admitted places fell 6,683 → 6,235, but the neutral pre-selection folded
915 of them where it had folded 1,174, so reachable clusters fell only 5,509 →
5,320 — 3.4%, against 5.3 clusters per seat of headroom. The concentration landed
disproportionately on places that were going to be absorbed anyway. **Distinct
places bound nothing**: `location` refusals moved 2,499 → 2,639 while
`the_leg_had_no_seat_left` went 540 → 1,433 and `cell_allowance` 6,751 → 5,911.
The pool got easier to seat and the binding moved to the seat budget.

**Only 152 of the 1,000 seats come from places the old bar did not admit at all**,
and 166 of the outgoing record's seats stand at places the new bar does not admit.
The place sets overlap far more than the row sets do — 4,727 places in both against
6,302 rows — so a 93.3% row turnover is mostly a re-choice *within* a place, and one
seat per cluster collapses most of it before it can reach the gallery.

**Which cells sit exactly at the floor is a property of the head and not a standing
list.** Six did on the outgoing column, five do here, and only two are the same:
`dark_muted_lime` and `dark_vivid_lime` stay, `dark_vivid_yellow`,
`light_muted_lime` and `light_vivid_magenta` arrive, and `dark_vivid_cyan`,
`light_vivid_cyan`, `light_vivid_azure` and `light_muted_blue` leave — the four that
leave are the four whose clearing places roughly doubled under the refit. The
sharpest single move is `light_vivid_magenta` **42 → 20**: its clearing places went
364 → 175 and the floor is the only thing holding it at 20. None of the five is
supply-bound — the thinnest, `dark_vivid_lime`, clears 52 places against a floor of
20 — and in all five `the_leg_had_no_seat_left` is now the largest refusal column
where `cell_allowance` led two of them before.

### At the planning size the binding constraint is distinctness, not places

**n=2000 is the size the collection is being built toward** (Matt), and `SOLVE_census_n2000`
is the first census taken there. It reverses what the n=1000 record suggested.

**890 of 2,000 seats.** The refusal order inverts between the two sizes, because the cell
allowance is `floor(k * t * n) + 1` and doubles with n while the pool does not:

| rule | n=1000 rows | n=2000 rows | n=2000 distinct locations |
|---|---|---|---|
| `twin` | 3,275 | **4,090** | **2,785** |
| `cell_allowance` | **4,120** | 2,845 | 2,082 |
| `location` | 1,228 | 1,817 | **663** |
| `group_cap`, `family_allowance` | 0 | 0 | 0 |

**The twin test refuses 2,785 distinct locations against one-per-location's 663.** Places
are not what runs out — 4,791 survive pre-selection for 890 seats — and neither is colour
supply. Among refusals *while choosing* at n=2000 it is twin 6,431 rows against
cell_allowance 1,588. **The palette group cap and the family allowance have never fired at
any size**; the realized group maximum is 6 against a cap of 50.

**The colour ceiling binds at small n and stops binding by n=2000.** At n=150 the allowance
is 7 and **30 of 48 cells sit at it** with pool unseated behind them, which makes the
allowance the limit. At n=2000 the allowance is 84 and only **3 of 48** reach it; the other
45 are held down by the twin test — `dark_muted_azure` has 34 seats of an allowed 84 with
428 unseated places, 4 refused by the allowance and **336 by twin**.

**Read a shortfall against `curate headroom`, not on its own.** At n=2000 the leg's realized
shortfall is 178 seats, but the census proves only **61** of it: `mode_floors` needs 600 and
supplies 539, while `one_per_location` has +2,791 slack and the cell cover +1,880. The other
117 is candidates the pool held and the leg could not seat. **Only two modes are genuinely
empty** — `smooth_mean_angle` and `smooth_angle_min` hold 30 distinct clearing locations each
against a floor of 60 — and closing that provable gap is about **1.3 engine-hours** at the
census's own `seconds_per_win`. The other eight short demands had unseated pool behind them,
so they are a distinctness problem and mining more of the same places makes more twins.

**The census cannot yet price the constraint that binds.** `twin_diversity` reads supply 0 /
slack 0 unless a `--twin` sweep is handed in, so the one block that would bound distinctness
is the opt-in one. At 4,791 places that sweep is the minutes-to-hours leg — an attempt was
stopped unfinished at ~40 min — and everything above says the next census should pay for it.

### And the threshold it binds at is too high — `AUDIT_twin_refusals_short_modes`

Audited on 2026-09-02 over `overnight_after`, the n=2000 gallery that closed every census
floor and still fell 68 seats short. **The pairs the twin test refuses stop being duplicates
at about 0.65 τ**, read off contact sheets of refused ↔ seated pairs, per mode: ~0.60 τ for
`direct_trap_multiply`, ~0.62 for `smooth_stripe` and `smooth_angle_min`, ~0.58 for
`smooth_mean_angle`, and ~0.72 for `direct_trap_screen`, whose pool is one look and so reads
as similar further out. An independent statistic agrees and was not used to reach it: the
share of refused pairs made with the **same palette map** runs 93-98% below 0.4 τ and
collapses through 55% at 0.5-0.6 τ to 32% at 0.6-0.7 and 11% at 0.9-1.0, against a 0.2% base
rate. **66% of all twin refusals sit above 0.65 τ**, and all twenty of the farthest-refused
pairs sit at the threshold itself and are plainly different pictures.

Solved at **0.65 τ globally the gallery goes 1,033 → 1,569 seats and the shortfall 68 → 7**,
four of the five short modes closing outright. Two costs: **500 of the 1,033 seated pictures
are not in it** — the lexicographic objective reshuffles once there are more seats to fill —
and it holds **3,795 pairs the shipped threshold would refuse** against zero today.

**The ruling came the same day**: Matt took `TAU` to 0.65 τ globally on 2026-09-02, which is
the 0.03809 that stood until 2026-09-05, when he took it to 0.90 of *that* — 0.034281 — by
eye rather than off a sitting. `curation.ceiling.TAU` carries both moves and what the second
cost; the sentence above is what the audit said before either was taken and is left as it was
written.

**What the 2026-09-05 move was read off.** A 200-pair boundary sheet, Matt's eye:
**88 pairs were ruled too close and all 88 were admitted-side** — pairs the standing
threshold was letting through — which is 9% of the view. The fit never crossed 0.5 and
the objective is flat below 0.85x, so 0.90x is a choice inside a flat region and not a
crossing. At n=1000 τ moves **no seat count** — every candidate fills — and what it
moves is worst/sum and *which* thousand: **158 seats turned over at 0.90x** [measured].
⚠ **The twin rule holds back about 34% of the view at τ**; the rejection ledger's twin
count (41 on that record) undercounts it badly because twin runs last, so read the
crossing sweep and never the ledger column.

**The colour-and-geometry gate is dead, and was measured rather than dropped**:
**AUC 0.448** — below chance — so a signature that mixes colour with geometry cannot
separate the pairs a person calls twins. Two near-white pictures with different
geometry collapse in a colour signature, which is the mechanism. The shipped test is
the pixel-cloud metric alone; a themed pass swaps it for the geometry-only `Places`
rule at radius 0.07, and τ is not in the themed path at all.

**The record is already the refusal log, so an audit like this needs no re-solve.**
`solve.json`'s `diversity_refusals` carries, per refused candidate, the seat it collided with,
the measured distance and how many seats were inside the threshold. Two things to know when
reading it. The named seat is the seat **at the moment of refusal** and the swap loop may have
taken it back out afterwards — 930 of 6,976 here, carried by only 77 distinct keys — so a
reader joining against the finished `seated` block silently loses them. And `same_location` is
**structurally zero**: `location` precedes `twin` in [`rules.RULES`], so a candidate standing
where a seat already stands never reaches the twin test at all.

**A wider radius needs no solve either.** It can never add a seat, so its whole effect is the
seated pairs falling inside the new radius, each of which must lose one member: the seats
given up are a minimum vertex cover of that graph. Over `overnight_after` that is 389-765 of
1,033 seats at 1.25 τ and 458-911 at 1.5 τ, before any refill — which is why the widening
what-if was priced this way rather than solved.

### The twin metric's two costs, both now taken

Measured in `SOLVE_census_n2000` and taken in `EDIT_twin_metric_directions`. They are
different stages of the same signature and they compose.

**1. The sort runs on the contiguous axis, for a byte-identical answer.** `signature`
used to build `[SAMPLES, DIRECTIONS]` C-contiguous and sort `axis=0`, which is
`DIRECTIONS` independent sorts each striding `SAMPLES` floats apart. It now transposes
into a contiguous copy and sorts the last axis. The sort itself is much cheaper that way
— 8.1 ms against 13.2 ms at 256 directions, 32.2 against 84.9 at 1024 — but the copy
takes most of it back, so **end to end the rearrangement is 1.28x** and not the 1.75x
`SOLVE_census_n2000` projected off the sort alone. The transpose on the way out keeps the
flat form quantile-major, which is what `reduce_signature` reshapes against.

It is byte-identical, checked rather than assumed, because BLAS picks a kernel per shape
and could accumulate three terms in another order: today's code forced back to 1024
directions reproduces signatures captured before the edit over 40 real pictures —
**20,971,520 bytes, 0 differing elements of 5,242,880, `tobytes()` equal**.
`test_the_contiguous_sort_is_the_same_answer_as_the_strided_one` keeps the retired
formulation beside the shipped one and pins it, because a speedup whose output moved
would be a bug wearing a speedup's clothes.

**Why a copy rather than projecting straight into the transposed shape, which is the
trap.** `lattice @ points.T` gives `[DIRECTIONS, SAMPLES]` contiguous and bit-identical
for free, and it went in first. The projection's inner dimension is **3**, so there is
nothing in it to parallelise — and BLAS threads that shape anyway. The whole signature
went to **24.93 ms wall for 185 ms of CPU** against 9.57 ms and 9.38 ms with threads
capped: a spin-wait, 20x the CPU for 2.6x worse wall time, and three times worse again
inside `curation.signatures`' three-worker pool. At 256 directions `points @ lattice.T`
`[4096,256]` is 0.70 ms and threading helps it; `lattice @ points.T` `[256,4096]` is
5.79 ms wall for 56.6 ms of CPU.

**Nothing failed and no test caught it** — the answers were identical either way. It
surfaced as a number that made no sense: the sidecar sweep ran past 600 s where the
1024-direction sweep had been 448 s, on a signature four times cheaper.

**Two measured dead ends.** `numpy.einsum` with `optimize=True` is bit-identical and
looks nearly free, because it returns a **non-contiguous transposed view of the same
BLAS result** — timing it times the view, and sorting it strides again; with
`optimize=False` it is contiguous but its own accumulation is not bit-identical. And
`numpy.partition` to the 256 kth positions the 128 quantiles need is 181-246 ms against
the sort's 116 ms.

**2. The metric has its own direction count, at 256.** [`pixel_clouds.DIRECTIONS`], and
deliberately not `groups.DIRECTIONS`, which stays at 1024 for the palette-group M1
matrix — a different metric over colormap *ramps* rather than pictures, and the one
every stored group name was cut under. The audit behind that split: every non-test
reader of the shared constant was either the twin metric's (`pixel_clouds.lattice`,
`distance`, `distances`, `Clouds.price`, `METRIC`, `rules.reduce_signature`,
`rules.bound_width`, `signatures.shape`) or `groups.m1`'s own default. Nothing else
took it. `QUANTILES`, `SAMPLES` and `HUE_WEIGHT` are still shared.

Project-and-sort scales better than linearly in the count — 117 ms at 1024, 47 at 512,
22 at 256, 9.3 at 128 — because the metric is a Monte Carlo estimate over the lattice
and fewer slices is the same expectation with more variance. Measured over 731 pairs in
the 0.5-1.5x `TAU` band, each setting given its own `groups.directions(count)` call
because a 256-point Fibonacci lattice is not a prefix of a 1024-point one:

| DIRECTIONS | ms | descriptor | p95 error as % of TAU | twin decisions flipped |
|---|---|---|---|---|
| 512 | 32.9 | 256 KiB | 0.3% | **0 of 731** |
| 256 | 14.4 | 128 KiB | 0.8% | **1 of 731** |
| 128 | 7.3 | 64 KiB | 1.5% | 3 of 731 |
| 64 | 3.6 | 32 KiB | 3.0% | 4 of 731 |

Every flipped pair sat within **0.05% of TAU at 256** and 0.41% at 64, flip direction
is balanced, and the `got/reference` ratio is centred on 1.0000 within 0.02% — so it is
noise rather than bias and **a re-fitted `TAU` would buy nothing**. The exposure is
small because the bound removes it: **99.03%** of pairs over a 3,000-row sidecar sample
are settled without measuring, matching the leg's own 99.62% at n=2000, and only 6.1% of
the comparisons a leg must measure sit inside the 256-setting's own noise band. Scaled
onto the n=1000 record's 51,019 measured comparisons that is ~125 to ~1,570 flipped
comparisons depending on the estimator, 0.001-0.013% of the 11.94 M the leg makes.

**The prune stays sound at any count**: the bound is the identity
`|mean a - mean b| <= mean|a - b|` on the same projection vector, so it becomes an exact
bound for the narrower metric rather than an inexact one for the wider.

**`TAU` is not refitted and must not be.** The error is added variance centred on
1.0000, not a shift, so there is nothing for a refit to absorb — and a threshold moved
to chase it would silently change which pairs are twins for reasons that have nothing
to do with the pictures.

### What was retired, and why

`PROBE_ilp_n1000` measured the exact solve against the thirty-minute bar
production wants: `curate solve run --n 1000 --no-render` was killed at a hard
1800 s having reached **stage 3 of round 1**, so there was no incumbent, no gap, no
seated set and no record. One cutting-plane round did not finish, `ROUNDS` is a
backstop of 60, and the round count grows with `n` (2 at n=20, 18 at n=120).

**The headline was the seed, not branch-and-bound.** 46% of the budget went to
`seed_greedily` before HiGHS ran, and it *failed* — 534 of 1000 seats, 6,282 cuts
— because it called `Pairs.measure([at, *seated])` once per considered candidate
and `measure` walks **every pair** of the list it is handed. O(seats²) per
candidate, cubic overall: invisible at n=150, 828 s at n=1000. Nothing in the
shipped leg may reuse that call shape, and `test_rules.py` guards it.

**Shrinking the model would have bought nothing.** The matrix was 98,457 binaries,
18,249 rows and 533,513 nonzeros *at both n=150 and n=1000* — identical, because
only the bounds moved — and it built in 0.4-0.6 s.

Gone with it: `Program`, `matrices`, `lexicographic`, `relaxation`,
`cutting_plane`, `seed_greedily`, `Pairs`, the elastic solve, the deletion filter,
the shortage list, `curate solve sweep`, `curate solve truncate`, and the SciPy
dependency. What stayed is everything that was never the ILP: the pool, the
per-mode bars, the ceiling, the release leg, the contact sheet, and the
`reduce_signature` bound — *The pairwise rule is now one rule and it is a count*
in [`GALLERY.md`](GALLERY.md).

### Where the coarse key still decides — `AUDIT_ckpt117_fine_key_sites_and_place_radius_sheet_0909`

`preselect` orders its walk by `p_ge4` and the seating orders on the cascade key,
so inside a near-duplicate cluster the survivor is not the row a seating would
have reached for. This is every other place that shape appears, swept over the
curation package. **Nothing here was changed on this reading.** `preselect`
itself was changed on the next one — see *The fold picks its survivor on the
seating key*, below — and on the one after that it stopped destroying rows
altogether, which is what made its own row's *reversible* column stale. Every
other row of both tables still stands.

One constraint shapes the whole answer and is stated rather than assumed:
`gallery-grade score-pool` runs on **coarse-clears only**, so `p_fine` exists
above `solve.Q4_BAR` and nowhere else. A site working below that bar cannot
switch keys whatever anybody would prefer. Hence two lists.

**Sites that could read `p_fine` and do not.** *Reversible* is the column that
matters: an ordering a later pass can revisit is a different thing from a
deletion.

| site | the decision | `p_fine` there | reversible |
| --- | --- | --- | --- |
| ~~`distinct.preselect`~~ **moved 2026-09-09**, and it no longer deletes | the walk order, and so **which place represents a near-cluster** — each place offered by its strongest candidate's raw `P(>=4)` | **all of it.** It runs on the clearing pool, and after `at_fine_bar` on a barred pass | ~~**no** — the place and every row it carries leave the pass under `SAME_PLACE`, and nothing revisits~~ **the irreversibility went too**: the rows stay in the pool under the survivor's cluster and the seating chooses between them |
| ~~`solve.strongest_locations`~~ **moved 2026-09-09**, and it cuts clusters now | `--locations N` keeps the N strongest **places** by their best candidate's raw `P(>=4)` | **all of it** — it is called on the line after `at_fine_bar` | ~~**no** within the pass; the cut places are gone before the view is sized~~ still no, and still the reason it moved |
| `candidate_ledger.prune` → `retention.decide` | top-`RETAIN_PER_PAIR` per (location, mode) on the fitted `rank_key`; a loser loses its row **and its JPEG** | **11.9%** of the rows it ranks. Only 7.1% of pairs hold two rows with a reading | **no**, and it is the only site here that destroys anything |
| `depth.best_field_by_location`, `mine.best_by_location` | which row is a place's *best*, which sets the band the near and deepen draws read | yes for the `[SEATING_BAR, PRIMED_BAR)` band — 0.50 to 0.90, entirely above `Q4_BAR` | yes — a draw spends renders and deletes nothing |
| `depth.near_places` / `proven_places` / `deficient_modes`, `mine.deepen_places` | threshold that best at 0.50 / 0.90 on raw `P(>=4)` | yes, above 0.50 | yes |
| `solve.pool`'s closing sort | hands the pool back `(-score, key)` | yes for the above-bar eighth | yes — the walk re-sorts by `ranking(order)`; this is presentation |
| `headroom.census`'s `best` / `strongest` | which row represents a place in the census, and the order the twin bound is walked in | yes above the bar | yes — a report |
| `shrinkage`'s best-per-group, `hunt` and `mine`'s contact sheets | ordering for a page or a measurement | yes above the bar | yes |

**Sites that structurally cannot.**

| site | the decision | why not |
| --- | --- | --- |
| `headroom.bars` / `clearing` | the per-mode bar itself, at `DEFAULT_BAR` or `FALLBACK_BAR` | it **is** the coarse gate. A fine reading below it does not exist by construction |
| the prune's below-bar majority | 88.1% of what it ranks | those rows never cleared the coarse bar, so there is nothing to order them by |
| `depth.ranked_bands`, `mine.ranked_places` | the ranked breadth order over **never-opened** places, on the location head's `P(>=3)` | no candidate exists at those places, so no candidate head has a picture to read |
| `embeddings.admitted_only`, `floors.passes_junk_floor` | drops a place under the junk floor | location head, same reason |
| `manufacture`'s extension tier | which admitted places get built, on the location head's `P(>=4)` | same |
| `framing.rank` / `adoptable` / `gain_of` | which reframing a location adopts | scored on fresh probe renders the ledger never held; `score-pool` reads pool rows |
| `solve.pool`'s five exclusions | niche mode, rejection, off-regime, no picture, no score | facts about a row, not scores |
| `selection.select`, `rejection.below_acting_bar` | which candidates take release slots, and which served rows are taken back | the **finished-render** heads' `p_ge3` at release geometry — a different head on different pixels, outside these three columns entirely |

**And the three that already read it**, because they take the leg's own key and
that key is `cascade`: `view.stratify`, both swap loops, and `curation.augment`
(`gallery.value` is `solve.value_of`). Above `Q4_BAR` those *are* `p_fine`.

**What the prune ranks, measured 2026-09-09.** 356,622 ledger rows, every one of
them carrying a live-judge reading; **42,300 carry a `p_fine`, 11.86%**. Of the
46,295 rows above `Q4_BAR`, 91.4% have one — the missing 3,995 are the store
growing since `pool_scores.jsonl` was last written, which is one-shot. Of the
160,403 (location, mode) pairs, **139,146 hold no row with a reading at all** and
7.1% hold two, so within-pair a fine key mostly has nothing to order. At rest the
prune's live decision surface is tiny — 165 pairs over the keep, holding 1,126
rows — because it runs at every merge; 145 of those 165 hold two readable rows.

**What the pre-selection's order costs, measured on
`tentative_n1000_20260909T061451Z`.** That pass ran `--fine-bar 0.50` under
`cascade`, so every one of its 11,362 candidates had a `p_fine` before the
pre-selection ran. It folded **1,144 of 6,471 places, 17.7%**. Of the 1,042
refusals where both sides' pictures resolve to a pool key, **435 — 41.8% —
discarded the place whose best candidate reads *higher* on `p_fine` than the place
that absorbed it**, median delta -0.0215 and mean absolute delta 0.150. That is
the shape the audit went looking for, at the one site where it is not reversible.

`PRESELECT_RADIUS` is **held** at 0.02 — Matt read `the-72.html` on 2026-09-09 and
every pair under the radius is the same geometric location, so the radius is not
too large and shrinking it would only refuse to fold real duplicates. **The
representative rule moved on that reading**, which is the next section; the radius
did not, and nothing about it is a function of the key.

### The fold picks its survivor on the seating key — `PRESELECT_ckpt117_fold_on_the_seating_key_0909`

Since 2026-09-09 `distinct.preselect` offers each place by its strongest row on
**`p_fine(>=4)` where the fine-tier head has read that row**, and on raw `P(>=4)`
where it has not. The walk order *is* the rule about which place represents a
near-cluster, the fold was then the one pool-construction decision that **deleted**
— it stopped later the same day, *The fold merges instead of deleting* in
[`GALLERY.md`](GALLERY.md) — and
the audit above measured it discarding the higher-`p_fine` place in 41.8% of the
resolvable folds. The docstring's claim — that the survivor is the place a seating
would have reached for — is only true on the key the seating orders by, and now it
is true.

**The two scales are stacked and never mixed.** A place with a fine reading is
offered ahead of every place without one, which is `solve.cascade_order`'s `1 + p`
in the other direction and its ruling: unknown never outranks measured. Mixing a
`p_fine` and a `P(>=4)` in one comparison would be sorting on two different
calibrations.

**The fallback is not optional and it is not silent.** `gallery-grade score-pool`
runs on coarse-clears only, so `p_fine` exists above `Q4_BAR` and nowhere else, and
this walk runs on passes where `at_fine_bar` did not — a themed pass on the relaxed
crossing, a solve given no `--fine-bar`, and the 3,995 above-bar rows a one-shot
read has not caught up with. So every record carries `key` (`p_fine`, `p_ge4` or
`both`), `ordered_on` (the place counts under each), `places_on_the_fallback` and a
per-place `ordered_on` on every refusal row, and a walk where every place fell back
says so in a line of its own rather than reading as a walk that used the new key.
Treated the way `--augment` is: **a record that carries no `key` folded on
`p_ge4`**, and a record taken after this change is not comparable to
`20260909T061451Z` on the objective, because it is a different pool.

**How much the two keys disagree, measured 2026-09-09** on one clearing pool —
11,637 rows at 6,683 places, `--fine-bar 0.50`, both walks over the same rows so
the reading is the change itself and not two solves' worth of noise. The new key
folds 1,174 places and the old 1,175, so the *size* of the fold does not move.
**Which places survive does**: the two kept sets differ over **543 places**, 272
kept only by the new key and 271 only by the old, and of the folds both keys make,
**589 name a different survivor**. That is 8.1% of the pool changing hands and half
the clusters getting a different representative, out of a change that moves the
refusal count by one.

**The first record folded on the new key is `20260909T161932Z`**, n=1000,
`--fine-bar 0.50`, shipped defaults, and it is **not comparable to
`20260909T061451Z` on the objective**: the ledger grew 293,235 → 308,885 rows in
between, so the barred pool went 11,362 rows at 6,471 places to 11,637 at 6,683.
Term by term it reads seats 1,000 → 1,000, worst **1.50391 → 1.50391**, demand
shortfall **7 → 1**, sum 1,885.59 → 1,889.59; the shortfall that moved is
`itinerary`, seated 25 → 31 against its floor of 32, whose own clearing pool went
90 → 100 over the same interval. **Neither number is attributable to the key.**
The fold refused **1,174 of 6,683 places, 17.6%**, against 1,144 of 6,471, 17.7%.

What *is* attributable, because it is read off the record's own refusal rows:
**0 of the 1,174 folds discarded the higher-`p_fine` place**, against 435 of 1,042
— 41.8% — in the record before it. The trade is exact and it is stated rather than
hidden: **496 of the 1,174, 42.3%, now discard the higher-`p_ge4` place**, mean
absolute delta 0.1315. The fold sacrifices the coarse column at the rate it used to
sacrifice the fine one, and the fine one is the column the seating reads.

**What the fold still destroys, and picking a better survivor does not fix it.**
This is the measurement *The fold merges instead of deleting* in
[`GALLERY.md`](GALLERY.md) was built on, and it is stated in the
tense it was taken in: at this reading the fold kept all of the survivor's ledger
and destroyed all of the absorbed place's. Read over the 1,144 folds of `20260909T061451Z` — 438 clusters, the
largest absorbing 44 places — against the rows those places hold in the clearing
pool today, 2,151 rows destroyed:

| what the absorbed place held that the survivor does not | folds | share |
| --- | --- | --- |
| a **mode** the survivor has no row in | 477 | 41.7% |
| a **colour cell** the survivor cannot reach | 1,088 | 95.1% |
| neither — the survivor covers it | 39 | 3.4% |

Mean mode overlap is **0.674** and mean cell overlap **0.220**. So the overlap is
**not** near-total: the key change fixes which place represents a cluster and does
nothing about what leaves with the other one. The modes lost outright are the
common ones in proportion — `smooth` 149, `tia` 144, `stripe` 131 — and 48 distinct
cells are lost at least once, led by `dark_vivid_red` 264 and `light_vivid_red`
203.

**`itinerary` is the sharp one.** Nine of the 1,144 absorbed places hold an
`itinerary` row and in **eight** of them the survivor holds none — against a mode
that is **short 7** in that same record. That is not proof the eight would have
seated, and it is the reason to state the measurement rather than assume the
overlap: this is what a per-cluster constraint would be bidding for. **None was
built**, on this reading or on the key change.

#### Both folds over one pool, n=1000

`20260909T165641Z` (pool) and `20260909T165848Z` (delete), taken back to back on the
same ledger, `--n 1000`, tentative, no release render, shipped defaults otherwise.
The pre-selection is identical in both: **6,683 places fold into 5,509 clusters,
1,174 absorbed, 2,165 rows** — which is what stayed in one arm and left in the other.

| | pool | delete |
| --- | --- | --- |
| rows after the pre-selection | **11,637** | 9,472 |
| places / clusters after it | 6,683 / 5,509 | 5,509 / 5,509 |
| rows in the view | 11,160 | 9,263 |
| seats | 1,000 | 1,000 |
| demand shortfall | **0** | 1 |
| worst seated | 1.50391 | 1.50391 |
| sum | **1,891.212064** | 1,889.586793 |
| solve wall time | 100.16 s | 89.52 s |

Term by term the two agree on the first and third tiers and differ on the second and
fourth. Reading the stages: the seed fills **806** seats against 816 — more rows
competing for the same 5,509 clusters, so the greedy leaves more on the table — and
the chain stage then reaches 1,000 in both, from a shortfall of 34 against 39, which
the second swap loop takes to **0 against 1**.

**The two questions this was built to answer.**

**71 of the 1,000 seats are held by a row at a place the destructive fold would have
absorbed** — 7.1% of the gallery, at 71 of the 1,174 absorbed places. Those rows do
not exist in the other arm.

**`itinerary` met its floor.** 31 against a floor of 32 under `delete`, and **32
against 32** under `pool`: the only shortfall either arm carried, closed. Per-mode
seats meet every floor in the pooled arm and all but that one in the destructive
one. The rest of the roster moves by single seats in both directions —
`direct_trap_screen` 27 → 28, `smooth_angle_min` 32 → 33, `smooth_mean_angle` 47 →
48, `tia` 288 → 297, `threads` 65 → 67, against `smooth` 166 → 160 and `stripe` 249
→ 240. The gallery trades the two uncapped modes for the floored ones, which is the
objective's second tier doing what it is above the fourth to do.

**Cluster sizes.** 5,063 clusters of one place, 262 of two, 71 of three, and a long
thin tail: 32 of four, 25 of five, then singles out to one cluster of **56 places**.
So the coarsening is concentrated — 446 clusters hold more than one place, 8.1% of
them — and the largest is a `julia:mandelbrot` neighbourhood the pool has mined
hard.

**What it costs.** The solve is **100.16 s against 89.52 s, +11.9%**, and the
diversity rule is essentially all of it: **89.913 s against 80.291 s, +12.0%**, over
**17,975 measured pairs against 11,769, +52.7%**, with the reduced bound settling
16,328,214 seat comparisons against 13,344,266 and the norm screen 12,613,957 of
those against 9,991,480. The rule is the stage that opens pictures, the **view** it
walks grew 9,263 → 11,160 rows (+20.5%), and it grew 12%. `rules.Twins.record` carries `seconds` from this
reading on, so the next pool that grows can be read against it rather than inferred
from the pass total.

### The `--locations` cut takes the seating key, and cuts clusters — `PRECLOSEOUT_ckpt117_strongest_locations_fate_split_and_docs_0909`

`--locations N` is the one lever on the false positives that live in a learned
score's upper tail: let the leg reach only the N strongest places and see what it
seats. It carried `preselect`'s defect in a second place, and it carried it after
`preselect`'s was fixed.

**Nothing in production has ever passed it.** Every solve record on this machine
was swept — **130 in the hot store, none in the archive** — and exactly one names
`pool.truncated_to`: `top22`, taken **2026-08-26**, before the fine head, before
the cascade key and before the fold. So this is a **consistency fix**, not a
correctness win, and no record moves because of it.

**Two things were wrong.** It ranked places on raw `P(>=4)` while the fold beside
it and the seating above it both rank on the fitted key, so an unread place could
outrank a measured one — the defect *The fold picks its survivor on the seating
key* closed one line away. And it cut **places** while the fold pools them, so a
place whose cluster sibling survived was dropped anyway: the discard *The fold
merges instead of deleting* in [`GALLERY.md`](GALLERY.md) had just removed, taken
one stage later.

**Both close in the same move, and the move is where it runs.** A cut on clusters
has to know the clusters, so `solve.strongest_clusters` runs **after**
`distinct.preselect` rather than one line after `at_fine_bar`, and it ranks each
cluster by its strongest row under `distinct.offered_at` — `p_fine` where the head
has read it, raw `P(>=4)` where it has not, the two scales stacked. `solve.within`
filters on `cluster` rather than on `location` to match, which is the same string
on every row of a pass that folded nothing.

**The record says which key it cut under and how many clusters took the fallback**,
the way `preselection` does, and it says it whether or not a cut was asked for:
`pool.truncation` carries `key`, `ordered_on`, `clusters_on_the_fallback`,
`clusters_offered` and `clusters_reached`. `pool.reachable_locations` was renamed
`reachable_clusters`, so a record carrying the old name was taken under the old
placement.

**Moving it also takes the per-mode bars off the truncated tail.**
`headroom.bars` puts a mode below `FALLBACK_LOCATIONS` distinct clearing places on
`P(>=3)` instead, so a pool truncated to twenty-two places first sent almost every
mode to the fallback and the bars were a function of the cut. They are now taken
over the whole clearing pool, and the cut acts on what survives it.

### The group cap was a second spelling, and the census was the one that was wrong

Until 2026-08-31 the `palette_group_cap` block priced against `ceiling.GROUP_CAP` —
a flat **one seat a group**, the retired `curate seat` leg's cap — while the leg
that actually runs takes `ceiling.group_cap(n, solve.DEFAULT_GROUP_CAP)`, the
proportional `max(1, floor(0.025 n))`. At `n = 1000` that is 1 against **25**. The
census read 754 groups at one seat each, called the pool short by 246, and it was
the loudest short block in the record; the shipped leg at the same rung found **no
ceiling binding at all** and a realized maximum of **7** seats in any one group.
The block was not a tight bound on the rule — it was a different rule.

It is fixed by asking `ceiling` rather than spelling the cap again, the block now
carries `cap` and `cap_rule`, and the census is **schema 4**: a schema 3 reading of
this block is not comparable. The note it used to carry — that the count was the
`TIGHT form` and the pixels could exempt a second seat within `TAU_GROUP` — went
with it, because `curation.rules` **dropped** that same-group distance row rather
than merging it. The count is the whole cap and there is no second threshold.

**The same second spelling survived in the other census until 2026-09-08.**
`candidate_ledger.inventory.feasibility` priced its `group_cap` row against
`ceiling.GROUP_CAP` too, so it wanted one distinct group per seat and reported
`binds` on any pool holding fewer groups than seats — 942 against 1,000 at n=1000,
where the cap is 25 and refuses nothing. It put a false *`group_cap` binds* into a
leg's readout twice, the second time costing a separate census to unpick. Fixed the
same way, off `ceiling.group_cap(n, solve.DEFAULT_GROUP_CAP)`, with `cap_rule`
beside `cap` and `needs` as `ceil(n / cap)` groups; `tests/test_candidate_ledger.py`
holds it to the solve's cap over a ladder. Two consumers of one retired constant,
found eight days apart, is the argument for the rule that a **cap is asked of
`ceiling` and never spelled a second time**.

**Why the census survived the question at all.** The gallery leg's own expand hook
reports a per-constraint shortfall, so the obvious move was to retire the census as
a second spelling of the rules. It does not cover it: `solve.expand` walks
`gallery.demands`, which is the mode floors and any colour target, and it runs
*after* a leg. It has no `one_per_location`, no cell or family ceiling, no group
cap, no twin bound, and no renders-per-win — and it cannot answer anything at a
rung nobody has solved, which is the census's whole job. The two are the upper and
lower bound of the same pair, and the fix was to make them agree rather than to
delete one.

### Both gallery decisions flipped on 2026-08-28, and the incumbent is still reachable

Built at ckpt 88 behind flags; **both are the default since 2026-08-28**. The cap is
the ckpt-88 ruling, the key is Matt's acceptance by eye on the four-arm contact sheets
at `n = 150`. `curate solve run` with no flag now seats the proportional cap on a fitted
key; the walk every earlier gallery took is two named flags away and the record says
which rule and which key it ran under, by name, either way.

**The key moved a second time on 2026-09-07**, to `cascade` — see *`cascade` is the
default since 2026-09-07* in [`GALLERY.md`](GALLERY.md). So `--key` now carries
three names and two of them
are historical: `rank-key` is what every gallery between the two flips was seated in
and `p_ge4` is what everything before 2026-08-28 ran.

**A third default joined them on 2026-09-04 and the incumbent line grew a third
flag with it** — see *The spiral share cap is a tenth by default* in
[`GALLERY.md`](GALLERY.md). An
invocation that means the pre-flip gallery has to say `--spiral-cap none`, because
saying nothing no longer means no cap.

```
curate solve run --n 150                                  # proportional + cascade + 0.10
curate solve run --n 150 --group-cap identity --key p_ge4 --spiral-cap none  # the incumbent, whole
curate solve run --n 150 --group-cap {identity,proportional}  # the palette-group cap
curate solve run --n 150 --key {cascade,rank-key,p_ge4}   # the sort key
curate solve run --n 150 --spiral-cap {SHARE,none}        # the spiral share cap
curate solve run --n 150 --fine-bar SCORE                 # the fine head's quality bar, OFF by default
curate solve run --n 150 --sheet-out <path>               # the contact sheet, elsewhere
curate solve run --n 150 [--release-regime WxHssN] [--workers 3]
```

`solve.DEFAULT_KEY` and `solve.DEFAULT_GROUP_CAP` are the two constants, and
`solve.ranking_for` is the one place a pass pays for its key — it reads the
flatness sidecar and the location scores, once per pool. `seat(order=...)` overrides
it, which is what a sweep seating one pool four ways passes.

### A record is discarded by default — 2026-09-13

**Reverses what the tree said.** Until this ruling, `CLAUDE.md`, `.gitignore`,
`tentative.PUBLISHED`, [`GALLERY.md`](GALLERY.md) and `curate solve list` all said an
unpublished record *stays in the store, kept*. The rule Matt actually operates by is the
opposite: a record is discarded once whatever it was made to measure has been measured,
and it is kept only when he says so — which he says for a record a published or upcoming
figure cites, and for the current official n=1000 record, and otherwise does not.

**What the stale sentence cost.** It was applied as an *action* twice this checkpoint —
the 2026-09-12 sweep of the early-September diagnostic series, 59 records and 64.55 MiB,
and the deletion of `20260913T001955Z` the same day — without ever being written where a
leg could read it. So the next leg read the doc, concluded the opposite, and left
`20260913T011105Z` in the store as a kept record. **A ruling that governs what a leg does
belongs in `CLAUDE.md`**: the handoff documents are not visible from inside a Claude Code
session, and a decision that lives only in them is a decision the next leg will contradict
in good faith.

**Keeping needs a reason and discarding does not**, and the wording everywhere is
deliberate about that — it is not a balance of considerations a leg is invited to weigh at
the end of its run. The cost of a leftover is misreading hazard and prune protection, not
bytes: `tentative.protected_keys` sweeps published and unpublished stamps alike, so an
unmeant record pins candidate rows against retention until somebody remembers it exists,
and no prune's output says which record is holding a key. Publication, durability and
retention are three questions and this ruling is the third one.
