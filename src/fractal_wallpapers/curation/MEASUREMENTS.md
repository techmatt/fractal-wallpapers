Every standing quantity this stage relies on, in the order this document makes them.
Split out of [`README.md`](README.md) so a rate is quoted from one place rather than
restated beside each mechanism — those live there, in [`GALLERY.md`](GALLERY.md) and
in [`LEGS.md`](LEGS.md). The caveat under *Every per-candidate rate this project has
measured* is stated once and governs every row in this file. **The reasoning is no
longer here**: every leg that settled a knob, and every reading a later one bounded
or reversed, is the log in
[`MEASUREMENTS_decisions.md`](MEASUREMENTS_decisions.md), so a figure is read off
this file without reading the superseded ones it arrived through. A section that
moved leaves the rule it settled stated here in one sentence and a citation to its
heading there, and where the reading *is* the standing quantity that sentence
carries the number too.

## What it costs, measured on this machine

The first two on the 98,457-candidate pool (11,210 clearing, 9,380 after the neutral
pre-selection over 4,496 places), idle, 2026-08-31; the n=2000 column on the
100,743-candidate pool the reframe-q4 merge left (11,574 clearing, 9,744 after
pre-selection over 4,791 places), 2026-09-01. All `--no-render`:

| | n=150 | n=1000 | n=2000 |
|---|---|---|---|
| view | 6,515 rows over 597 strata | 8,704 over 597 | 9,461 over 604 |
| seats | 150 of 150 | **653 of 1000** | **890 of 2000** |
| **signatures decoded** | **289** (was 4,624) | **19,113** (was 24,969) | **28,826** |
| swaps | 18 over 3 passes | 49 over 3 passes | 75 over 3 passes |
| seed | 22.3 s | 402.0 s | 947.3 s |
| swap loop | 7.1 s | 1,617.9 s | 2,632.1 s, ran out of improvements |
| whole leg, on a *shared* machine | 38.4 s (was 461.1 s) | 2,030.8 s (was 2,743.4 s) | 3,592.1 s |

**And this is the leg before the metric came down to 256 directions**, which is most of
what it cost. Measured the same day on the same pool, `--no-render`, same gallery at
n=150 seat for seat:

| | n=150 | n=2000 |
|---|---|---|
| whole leg | 46.1 s → **16.2 s (2.85x)** | 3,592.1 s → **607.2 s (5.9x)** |
| seed | 25.1 s → **4.5 s** | 947.3 s → **145.8 s** |
| swap loop | 9.4 s → **1.7 s** | 2,632.1 s → **451.3 s** |
| signatures decoded | 317 → 314 | 28,826 → 28,112 |

**And the gallery it chooses barely moves, which was checked against a control rather
than argued.** At n=150 it is **seat for seat identical** — same 150 places, same 26
swaps, same objective, every refusal count the same. At n=2000, against the same pool at
1024 directions (`control1024_n2000`, which is the retired metric exactly because the
sort rearrangement is byte-identical there):

| | 1024 | 256 |
|---|---|---|
| seats / shortfall / worst | 878 / 200 / 0.097761 | **all three identical** |
| sum | 422.86 | 421.56 (−0.3%) |
| places held | — | **863 of 878 (98.3%)** |
| whole leg | 2,517.6 s | **607.2 s** |

The first three objective tiers do not move. Over 5,700 twin verdicts, **5,674 agree**;
26 pairs the old metric called twins the new one does not (0.46%) and 13 the other way,
with the median distance on shared refusals moving **+0.000008** — three parts in ten
million of `ceiling.TAU`. **Read a diverging census against the pool first**: the
`census_n2000` comparison looked like a 22-seat shortfall regression and every seat of it
was `direct_trap_multiply` losing 183 of its 220 clearing rows to a merge, not the metric.

A gallery at the planning size is **ten minutes** now rather than an hour. **n=1000 was
not re-run**, so the only figure for it is the 2,030.8 s above; scaling by the n=2000
ratio puts it near six minutes and nothing has measured that.

The seconds are upper bounds — this machine is usually running something else — so
the **decode counts** are the figure to compare; they are off each record's own
counters and they predict the walls at all three sizes.

Against the retired program's **1800 s and no answer** at n=1000. The pool cannot
fill a thousand seats under these rules — 653 is what it holds — and the four mode
floors that go short are on the expand hook.

**A gallery at n=2000 is an hour and the swap loop still terminates**, which is worth
knowing before capping one: `--swap-seconds 3600` was set as insurance on that run and
never bound. The planning size is affordable.

**The seed is no longer the whole cost** — at n=2000 it is 947 s of 3,592 — but the
signature still is, at both of its stages. Both were taken on 2026-09-01; see *The twin
metric's two costs* in [`GALLERY.md`](GALLERY.md), and read this table as the leg
**before** them.

**At `n = 1000` the mode floors are provably short and every rung below them has
exactly zero slack** — [`MEASUREMENTS_decisions.md`](MEASUREMENTS_decisions.md)'s
*What the flip found, measured 2026-08-31*.

**`curate solve run --n 150 --no-render` is 44.6 s** — 11.2 s of it pool and view,
24.5 s the seed, 8.9 s the swap loop, measured 2026-09-01 over the 100,743-candidate
pool. The five-minute figure this document used to carry is the leg before
`curation.signatures` and the two swap prunes —
[`MEASUREMENTS_decisions.md`](MEASUREMENTS_decisions.md)'s *What the gallery leg
costs at n=150 on this machine*.

## What the rule does, measured at n = 150 under routing

`flip_flat` (`--flat-floor`, one seat a mode) beside `flip_floored` (the default),
on **one pool** — 97,423 candidates, 11,137 clearing, 4,480 places after the
neutral pre-selection — same rank key, same proportional group cap, 2026-08-31,
after the modulate re-routing and with `tail_itinerary` at weight 0. **The flip is
not conditional on any of it**: the ruling is *The seat floors that make a 2 mean
something* in [`GALLERY.md`](GALLERY.md), and this is the pathology check.

**Both filled 150 of 150 and all 14 modes, and every floor was filled — `starved`
is empty on both.** The floors ask for 45 of the 150 seats, and because each was
filled the census's covering bound over those modes, `sum of min(floor, that mode's
clearing places)`, is exactly the 45 they need.

**Three of the thirteen floors bind**: `itinerary` (1 seat under the flat floor,
floor 5, took **6**), `direct_trap_lines` (1 → 2) and `direct_trap_multiply`
(1 → 2). The other ten were already above their floor and the rule asked them for
nothing.

**And it moved 46 of the 150 seats, not 7.** That is the finding, and it is the
same shape the pre-routing reading found (52 there). Filling three floors demands
seven seats; what changes is a third of the gallery, because the scarcity leg
seats 45 before the general leg starts and every one of those takes a location, a
colour cell and a palette group out of what the general leg then sees. By mode:
`itinerary` +5, `stripe` +3, `curvature` `direct_trap_screen` `smooth_angle_min`
+2 each, against `smooth_stripe` −7, `threads` −6, `smooth_curvature` −3,
`tia` −1. `smooth` is unmoved at 33 both ways.

**Of the 45 seats the floor leg placed, 22 would have been seated anyway** — the
flat gallery holds them too — so **23 seats exist only because a floor bound**.
That is the price, and it is what the autopsy sheet lays out beside the 46 seats
the flat gallery held and the floored one does not.

The refusal ledger says the same from the other side: `cell_allowance` 2,773 →
**3,095**, `the_greedy_had_no_seat_left` 6,002 → 5,655, `twin` 99 → **68**,
`group_cap` 4 → **19**, `location` 291 → 332.

**The two orderings still disagree about whether it is better.** The floored
gallery has the better worst seat on the judge's own column (`P(>=4)` 0.5184
against 0.5070), holds **128** seats above `P(>=4) = 0.90` against 121, and sums
1.10 higher on `p_ge4` — while summing **2.20 lower** on the fitted `rank_key` it
was actually sorted by, with a worse floor there (0.4185 against 0.4309). Every
seat clears the q4 bar in both. A rule that improves the judge's raw fourth
cutpoint and costs the fitted key is a rule whose acceptance is a ruling and not a
number's, which is what ckpt 94 was.

Records `artifacts/curation/seat/flip_floored/seat.json` and `.../flip_flat/`;
sheets beside them; the reject autopsy is `scratch/flip_floor_autopsy.html`, which
pairs each of the 23 with the displaced seat it shares a palette group or colour
cell with.

* `mode_policy.STRANGE_SEAT_SHARE = 0.60` is the strange share of a gallery's
  **seats**, declared and not measured. It is **not** `run.STRANGE_SHARE`, which
  carries the same number and splits a release's *mining slots* between the heads
  at `budget.head_slots`. One name over two stages is the confusion this repository
  keeps paying for, so the seat-side name says `SEAT`. The knob is the floor's
  denominator and nothing else: no rule asks a finished gallery whether it realized
  the share.
* Over the **12 accepted strange modes** — `accepted()` less `smooth`, read from
  `colorize.modes_for(budget.STRANGE)` — `2·promoted + 1·normal` sums to 19 and
  distributes the strange budget fully. Each mode's floor is **half** its share, so
  the floors sum to exactly half the budget and the other half is the gallery's to
  spend on whatever is strongest. At `n = 1000`: budget 600, floors summing to 300,
  **16 a normal mode and 31 or 32 a promoted one**.
* **The floors stopped being one integer a weight class on 2026-09-04**, and that
  is the largest-remainder rule working rather than failing. It was 13 modes over
  a total weight of 20, and 300 divides by 20; `exp_smoothing` went to weight 0 and
  left 12 modes over 19, which does not divide, so the three modes with the
  largest fractional remainders — `smooth_mean_angle`, `smooth_angle_min`,
  `itinerary`, ties broken by weight then name — take a spare seat each and read 32
  against the other four promoted modes' 31. The sum is still exactly 300. **A
  reader comparing a mode's floor across two galleries has to read the record's own
  `mode_floors` block** rather than reconstructing it from a weight, which was
  possible while the division was clean and is not any more.
* **The dated reason the weight went to 0**, from `EVAL_exp_smoothing_0904`: over
  914 paired seats rendered both ways at 640x360 ss2, **902 (98.7%)** sit under the
  website's `SEAT_TOLERANCE = 6.0`, the judge's `P(>=4)` correlates at Pearson
  **r 0.99729** with a mean delta of +0.0022, and the twelve pairs at or over the
  tolerance are **eleven varied `phoenix` and one `mandelbrot`** — while
  `phoenix:classic`, the pinned plane, is the *most* identical partition on the
  record. The separation is varied `phoenix` specifically and not the mode, which
  is why this was a standing ruling and not a bar.
* The halves are fractional, so they are integerized by **largest remainder**, ties
  by weight then by name. That is deliberately *not* `supply.apportion`'s rule,
  which is largest-*deficit* sequencing and whose subject is every prefix of a batch
  that may stop early; nothing stops early here and the only property asked is that
  the floors sum. An odd budget rounds the house up: `(budget + 1) // 2`.
* No mode gets a bare 1 by exception, `direct_trap_multiply` included. Smooth is not
  in the table at all — `colorize.modes_for` returns `[SMOOTH_MODE]` unconditionally
  on the smooth branch, so the smooth side is one mode by construction and has no
  distribution to solve.
* **Where a floor collides with a ceiling the ceiling wins and the floor goes
  unfilled.** `solve.solve(floor=...)` takes the
  mapping, and the seating record reports the collision per mode under
  `shortfalls.modes.per_mode` — `clearing` above `seated` means a rule named in
  `refused_by` took the seats, `clearing` at `seated` means the pool held nothing
  more. `starved` (a floor above zero that went unfilled) and `floor_never_needed`
  (a floor of zero, which no gallery can fail) are separate lists, because the old
  single one read as working when the floor was switched off.

**Nothing is deleted.** A niche mode keeps its labels, its ledger rows and its
pictures; it renders by name; `--modes` names it and is taken as given; and a
verdict already exported on it still ingests — which is what let the head-top drop
be counted against the standings it was collected to test, and moved `curvature`
out of the niche set on 2026-08-29.

**Two layers, one word.** The engine's `Tier::Niche` (`de`) is a claim about what
the finished-render corpora were collected over and lives in Rust; this table is a
claim about what is worth collecting next, and it has to express a third value a
two-valued tier cannot. `check()` refuses if a mode carries both.

**Mining one short mode moves seats between the short demands rather than cutting
the shortfall**, because only a leg that adds places adds places —
[`MEASUREMENTS_decisions.md`](MEASUREMENTS_decisions.md)'s *What the two empty
modes actually cost, measured*.

**Arm A's centered roster is declared in `depth.centered_modes()`, and a roster
ruling is not a weight ruling** —
[`MEASUREMENTS_decisions.md`](MEASUREMENTS_decisions.md)'s *What the four knobs
bought, measured overnight 2026-09-01/02*.

**Fresh places clear at about a quarter of the pool's rate, and the near band is a
queue to be priced rather than a clock** —
[`MEASUREMENTS_decisions.md`](MEASUREMENTS_decisions.md)'s *What the aim bought in
SEATS, measured overnight 2026-09-03/04*.

**A themed seat count is read off eight hours and never off one**, the controls'
noise at n=200 being about ±4 seats an hour —
[`MEASUREMENTS_decisions.md`](MEASUREMENTS_decisions.md)'s *A one-hour read cannot
resolve the aim in seats. An eight-hour one can*.

## What the themed leg's quality reads, measured 2026-09-05

Every dark theme **fills** n=200, so count is not the readout — quality is. Read at
the q4 bar over the finished seating:

| theme | seats over the q4 bar, of 200 | median |
|---|--:|--:|
| the rich four | 182-192 | — |
| `dark_vivid_green` | 113 | 0.58 |
| `dark_vivid_yellow` | 79 | 0.19 |

**Recolouring proven places is the cheapest q4 there is** — **12.8 engine-s a kept
clear**, against **67 s** to open a fresh place and **165 s** for a full-render mode.
And it *aims*: a 20-minute arm moved green's median **+0.054** where its controls moved
**+0.003**. What it cannot buy is a seat in the general gallery, because one-per-location
holds — it buys quality **inside** a theme, and places still come from breadth. Two
roster facts off the same legs: `curvature` bought **5% of the clears for 25% of the
roster**, and a cell exclusion narrows the **offer** rather than the outcome —
**43% of a restricted leg's rows landed off-list**.

**An allowance is checked against `ceiling.Rule(k=K).allowed(cell, n)` and never
against the formula on paper**, which loses a seat wherever the product lands on an
integer — [`MEASUREMENTS_decisions.md`](MEASUREMENTS_decisions.md)'s *What the
colour ceiling costs at n=1000, measured 2026-09-06*.

**An allowance is a multiple of the pool's realized memberships a seat and not of a
remembered constant** — [`MEASUREMENTS_decisions.md`](MEASUREMENTS_decisions.md)'s
*What a colour ceiling four times the target rate costs, measured 2026-09-09*.

**`K = 3` with a colour floor of one fair share fills every one of the 48 cells and
pays for it in the worst seat alone** —
[`MEASUREMENTS_decisions.md`](MEASUREMENTS_decisions.md)'s *What `K = 3` and a
colour floor of one fair share cost together, measured 2026-09-09*.

**A thin cell is stock-bound and spiral-bound rather than held down by another
cell's allowance — and NOT carrier-bound**, 942 of 942 drawable maps carrying a
carrier row, which is a mining instruction —
[`MEASUREMENTS_decisions.md`](MEASUREMENTS_decisions.md)'s *The deadlock the floor
was expected to hit, and did not*.

**On the shipped column the live colour constraint is the CEILING and not the
floor**: 12 of the 48 cells sit at the allowance and only three sit on the floor, so
a stamp count reads the scarcity leg's order rather than the floor's worth, and the
spiral cap binds to the last seat at 0.15 as it does at 0.10 —
[`MEASUREMENTS_decisions.md`](MEASUREMENTS_decisions.md)'s *What the colour floor
and the spiral cap actually bind on, measured 2026-09-10*.

## What the palette-group cap costs at n=1000, measured 2026-09-07

**Nothing. It is not a binding constraint and never has been.** Three n=1000
seatings over one pool and one cascade order, everything but the cap identical —
shipped (`max(1, floor(0.025 x n))` = **25**), raised to **50**, and removed
(`1000`, so no cap at all). **Zero seats change**, in either direction, and the
objective is bit-identical at all three: `worst 1.001752, sum 1786.467343`, 1,000
of 1,000 filled, 13 of 13 modes. `group_cap` has **0 refusals** at every rung, the
busiest map takes **23** of an allowed 25, and `at_the_cap` is 0. Relaxing it
buys nothing because nothing is spending it.

⚠ **"942 groups against 1,000 seats" is not a statement about the cap.** 942 is
the width of the drawable colormap pool (`palettes/README.md`), and a gallery
seats **473** distinct groups, not 942: 230 groups hold exactly one seat and the
distribution is 1/2/3/4/5/6/7/8/9/23 over 230/119/53/33/20/8/5/1/3/1 groups. A
count of maps is not a count of seated groups and neither is a cap.

**The weak tail is composition, not supply — and it is not depth either.** The
seated picture's fine-head `P(>=4)`, per group, runs min **0.0018**, p10 0.304,
median **0.9629**, p90 0.9998 over the 473 seated groups; **236** hold a seat
below that median, which is the set a palette-aimed leg (`--draw-maps`,
`--draw-cells`) would be pointed at. But **934 of the 942 groups already hold at
least one row the fine head could read**, a weak-half group holds a **median 34**
of them, and only **70 of the 236 (29.7%)** have their seat as the best row that
group has anywhere in the pool — the median headroom over the seat is **0.075**
and the p90 is **0.672**. **461 groups hold readable rows and take no seat at
all**, at a median 23 rows each and a median best of **0.826**, well above the
weak half's seats. So the pool is not short of maps and not short of depth behind
them: what keeps a strong row out is one-wallpaper-per-location and the cell
allowance — `cell_allowance` is **28,889** refusals against `location`'s 4,204
and `group_cap`'s zero.

**And the two heads disagree hardest exactly at that tail.** The twenty weakest
seated groups carry judge `p_ge4` of 0.59-0.998 — several over 0.99 — against
fine-head readings of 0.0018-0.076. A weak seat here is a picture the gate likes
and the gallery-grade head does not, which is what the cascade exists to catch.

## How much of the prune is settled above the bar, measured 2026-09-07

The cascade is the fine head above `Q4_BAR` and `rank_key` below it, so **below
the bar the two orders are one order** and retention ranking on `rank_key` is
already ranking on the cascade's own lower half. The disagreement can only bite
where a whole pair sits above the bar.

Over 325,099 ledger rows in 134,198 `(location, mode+mode_params)` pairs:
**3,729** pairs sit at or over `RETAIN_PER_PAIR`, holding 18,760 rows, and
**877 (23.5%)** of those are wholly above the bar — **23.6%** weighted by rows,
so the two readings agree. On those 877, the two orders name a **different top
row 70.6%** of the time and a **different most-disposable row 71.3%**, and the
orders are identical in only 13 pairs. **But they almost never disagree about
what to KEEP**: the survivor set differs in **23** pairs, 2.6% of the 877.

⚠ **The reason is when the store is read, and it is a property of the reading.**
A pair at exactly the keep deletes nothing whatever the order, and after a
merge's prune **3,622 of the 3,729 sit exactly at 5**. Only **107** are over it,
and those are pairs a *protection* held above the keep rather than ordinary prune
candidates. Restricted to the **30** all-above pairs that actually delete
something, the survivor set differs in **23 of 30 (76.7%)** and the first
deletion in **21 of 30 (70%)**. So: rare that a prune's whole decision is made
above the bar, and near-certain that the two keys differ once it is.

⚠ **Real prune decisions are not recoverable and this is why.** A merge's
`pruned` block carries counts and names **no dropped key**; the same transaction
rewrites all three store files against the surviving keys, so a dropped row's
flatness and judge score are gone and it can have no `rank_key` value; its
picture is deleted, so it can have no fine-head reading either — `armB2_0907`
kept 3,210 pictures of 16,200 made. And a displaced **incumbent** appears in no
leg's `rows.jsonl`. Both sides of the comparison are missing for exactly the rows
a prune acted on, so the standing-pair reading above is where this stops.

**The fine head reads 11,294 of the 18,760 rows in those pairs**, against 11,298
that are above the bar — a four-row gap. `pool_scores.jsonl` covers
`solve.pool`'s above-bar rows, so a row the pool refuses (rejected, no picture,
off-regime, a mode weighted 0) is above the bar in the ledger with no reading.

This is the number under an argument, and the argument is
[`README.md`](README.md)'s *The prune ranks on `rank_key` and a gallery seats on
the cascade, and below the bar those are one order* — why the seating flip left
retention alone, and why `rank_key` cannot be retired while the cascade runs.

## What the sourcing channels cost in seats, measured

* **Centered share of a solve is mining-invariant, at 0.16-0.23.** It is the one axis
  the solve amplifies unasked, and no mining arm measured has moved it out of that band.
* **Centered places clear more often and cost more**: **38% against 30%**, at **2.6x**
  the cost. An aimed arm buys mode-floor seats and a centered arm buys places.
* **The viewport sampler's survival is about 10%** on the pinned planes, which is the
  only root channel a plane with no parameter has.
* **At the 0.25-turn mix the pinned plane's rows were worth −5 seats at n=1000.** They
  clear well and land only in cells already at allowance, which is why the phoenix
  planes are declared in seconds shares now and not in turn weights.
* ⚠ **Two modes a census prices the same can be 1.9x apart measured.** Allocate per
  mode; a census price is a starting point and never an allocation.
* **`light_vivid_purple` is companion-allowance-bound**: the pool holds **28 of 42**
  and the cell is refused by a full companion cell of the same carriers rather than by
  its own rule.

## What the label stores and the candidate ledger share, measured

* **The join ceiling is about 12%**, by PLACE and never by key — quote the ratio and
  never the counts, and remember the rows that *do* join are the selected top.
* **19.8% of seats sit at a labelled place**, and the four rate there is **38%**
  `[human n=678]`.
* **The render judge orders inside its own top in exactly one slice** — the rare-colour
  one, at **0.45 / 0.49** `[human n=60]`, where the disagreement is colour-shaped:
  purple and lime read 0.99 to the judge and about 2.7-3.0 to Matt's eye.
* **The rank key reads `flatness`, so every seating is busier than the pool by
  construction**: dead space below 0.05 is **24% of the pool and 62% of the seats**.
  Intentional, Matt's ruling of ckpt 107, and not a defect to correct.

## What a rotation of a stored recipe costs, measured 2026-09-11

`rotation_pass_ckpt120`, the whole passing set: **9,402 rows over 6,764 (location,
mode) pairs, 47,010 rotations, 24,244 engine seconds on three below-normal workers
in 9,117 s of wall.** Idle box. **2.579 engine seconds a row and 0.516 a rotation.**

**The dump is the whole of it and the split says so.** Per row, the dearest of its
five rotations against the median of the other four — the first rotation at a pair
pays the iteration pass and everything after it is a colormap lookup over an array
on disk:

| mode | rows | eng s a row | median | dearest rotation, median | recolour, median |
|---|--:|--:|--:|--:|--:|
| `smooth` | 4,214 | 2.111 | 1.864 | 0.693 | 0.2521 |
| `stripe` | 2,634 | 3.610 | 2.656 | 1.446 | 0.2190 |
| `tia` | 2,456 | 2.223 | 1.877 | 0.833 | 0.2073 |
| `curvature` | 98 | 3.858 | 2.465 | 1.363 | 0.1969 |

⚠ **A recolour here is 0.21 s and not the 0.041 s of `curate mine bench`'s bare
recolour**, and the gap is the autolevel operator rather than the engine. Every
candidate derives its own curve, which is a JPEG decode and an Oklab pass in
**Python** plus the operator's second colouring — `measure` + `repaint`, not
`paint`. That is what deriving costs, and it is what buys a picture whose recipe
key a `re-render` reproduces: the key's autolevel member is the operator, the
switch and the band and never the curve, so an *inherited* curve would put a
picture in the store under a name that does not rebuild.

**Six candidates a row costs about one and a quarter renders and not six.** 2.579 s
a row against the 2.0–2.4 s a single full render of these modes costs at this depth.

**Only four of the eight field modes are in it**, and that is the population rather
than the operation: `smooth`, `stripe`, `tia` and `curvature` are the only field
modes with rows above the shipped fine bar. The passing rows on a mode with no field
to dump — the composites and `itinerary` — are **owed** at full render price, which
is six iteration passes a row rather than one.

**An owed rotation costs about 24.3 engine seconds a row and 4.9 a rotation, seven
times the dumpable arm**, and a smoke prices the row and the concurrency as two
estimates with separate error bars —
[`MEASUREMENTS_decisions.md`](MEASUREMENTS_decisions.md)'s *The full arm ran 34%
dearer than the smoke priced it, measured 2026-09-12*, under *What the OWED arm
costs, measured 2026-09-11* there.

## What `Palette.phase` moves, by mode, measured 2026-09-12

`phase_flatness_ckpt122`, seed 0, `curate phase-response` the leg. **228 rows over 76
cells — all 19 production modes at 2 places, 2 maps and 3 phases against phase 0 — in
268.5 engine seconds and 108.5 s of wall** on three below-normal workers, 2.48 engine
seconds a wall second, 304 renders in all. Candidate geometry, and **levelling off throughout**: the
autolevel operator derives its curve off the picture's own histogram, so a phase shift
measured with the switch on is phase *plus* re-levelling and nothing in the reading could
separate them.

**The control passed. 48 of 48 direct-trap cells came back byte-identical** — all four
traps, worst mean exactly 0.0 — which is what the rest of the table rests on: the axis
cannot reach a trap figure, so a pass whose traps had moved would have a harness fault
and no reading at all. `curate phase-response` **fails** on that check rather than only
printing it.

**And nothing else is flat. 0 of 180 non-trap cells were byte-identical**, the smallest
mean ΔE over all of them is **0.056** — 2.8× the 0.02 the `moved` column is counted
against — and the smallest share of frame past that is **0.856**. The axis reaches every
mode the engine gives a field to, at both places, both maps and all three phases.

| mode | kind | mean ΔE | p99 | moved | map low / high |
|---|---|--:|--:|--:|--:|
| the four `direct_trap_*` | direct | **0.00000** | 0.00000 | 0.000 | — |
| `smooth_angle_min` | composite | 0.16681 | 0.43833 | 0.981 | 0.120 / 0.213 |
| `gaussian_int` | field | 0.16800 | 0.44395 | 0.985 | 0.115 / 0.232 |
| `smooth_mean_angle` | composite | 0.17243 | 0.39109 | 0.987 | 0.124 / 0.257 |
| `curvature` | field | 0.20429 | 0.40850 | 0.982 | 0.156 / 0.264 |
| `stripe` | field | 0.21051 | 0.39085 | 0.986 | 0.143 / 0.277 |
| `tail_itinerary` | modulate | 0.22153 | 0.46069 | 0.987 | 0.147 / 0.312 |
| `smooth_stripe` | composite | 0.22510 | 0.38149 | 0.985 | 0.144 / 0.305 |
| `smooth_curvature` | composite | 0.22878 | 0.40250 | 0.989 | 0.155 / 0.317 |
| `threads` | composite | 0.23203 | 0.42859 | 0.992 | 0.156 / 0.314 |
| `smooth_trap_circle` | composite | 0.23378 | 0.43576 | 0.983 | 0.154 / 0.315 |
| `tia` | field | 0.24072 | 0.41193 | 0.986 | 0.155 / 0.344 |
| `itinerary` | modulate | 0.24151 | 0.42603 | 0.985 | 0.155 / 0.333 |
| `trap_circle` | field | 0.24299 | 0.44676 | 0.987 | 0.149 / 0.347 |
| `smooth` | field | 0.25248 | 0.45539 | 0.993 | 0.154 / 0.393 |
| `exp_smoothing` | field | 0.25276 | 0.45525 | 0.993 | 0.154 / 0.394 |

Per-mode figures are the **median over that mode's cells**, and `map low / high` is the
smallest and largest per-map median inside the mode.

**The verdict is two groups and not three, and the ranking above does not separate.** The
fifteen run 1.51x end to end, and the widest multiplicative step between neighbours is
**1.185x against a runner-up of 1.052x** — no gap anywhere in it, so nothing here
supports calling any accepted mode flatter on this axis than any other. `flat` is the
four traps, `live` is the other fifteen, and `uncertain` is **empty**: not one mode landed
near enough to a no-op to be hard to call.

**The spread inside a mode is the MAP'S KIND and not the mode.** Over the non-trap cells
the folded map reads **0.305** against the cyclic map's **0.148**, a 2.07x difference that
accounts for nearly the whole of every `map low / high` pair in the table; the place
barely registers by comparison (0.204 at `julia:mandelbrot`'s cap of 8,306 against 0.176
at `julia:multibrot5`'s 15,819), and the *coloring* kind not at all — field 0.187,
composite 0.182, modulate 0.224.

**The dose is not monotone, and which way it runs is the fold.** Median mean ΔE by phase,
non-trap cells, split on `mirror`:

| phase | cyclic | folded |
|--:|--:|--:|
| 0.05 | 0.115 | 0.084 |
| 0.25 | 0.351 | 0.321 |
| 0.50 | **0.148** | **0.408** |

A folded map is baked as an out-and-back, so a half-turn lands the traversal on the
ramp's reflection and is the **largest** change there; on the cyclic map the half-turn
comes back toward where it started and reads less than half what a quarter-turn does. ⚠
**Two maps is a range and not a distribution** — the direction is mechanism and the
magnitudes are this pair's.

**The interior mechanism is real in the engine and this panel cannot exercise it.**
`coloring.rs`'s `INTERIOR` is hard black and never goes through the map, so the share of
frame the axis can reach is bounded by `1 − interior_fraction` — but every non-trap mode
here reads a median exactly-black share **at or under 1.6%**, because the panel is drawn
from `gallery3`'s shallow half and those are deep exterior views with almost no interior.
A mode flat *at a place with a large interior* is consistent with every row above and is
**not measured**. The traps are the only rows with much black ground (`direct_trap_lines`
21.7%), and they are identical anyway.

**What this does NOT answer**, each because it was out of scope rather than overlooked:
the levelled arm, `Palette.cycles` (the other knob `--vary-palette` draws), and whether a
phase shift a judge can *see* is a phase shift a judge **prefers** — this measures pixels
and reads no head. `curate rotate`'s own passes are the adoption question, and
[`LEGS_decisions.md`](LEGS_decisions.md)'s *What the first pass found* has that reading.

## Every per-candidate rate this project has measured

⚠ **These are historical, measured under different conditions, and not comparable
across rows.** A rate is a joint fact about the mode roster, the width `k`, the
engine count, the picture geometry and whether the field was shared — change any one
and the number moves by more than the spread of this whole table. Nothing here is a
constant, none of it sizes a leg you have not piloted, and the depth roster moved to
five field modes on 2026-08-29, so **every row below predates the current roster**.
Pilot the roster the leg will actually run.

This caveat is stated once, here. Everywhere else in these documents that quotes a
rate should point at this table rather than repeat the warning.

**Read `s/cand` as per ENGINE**, which is what `--rate` wants and what
`budget.seconds_per_candidate` records. A rate read off a three-worker leg carries
that leg's contention: three engines cost about 1.6–1.8x per candidate over one.

| s/cand | mode or roster | eng | k | date | population drawn | record |
|--:|---|:-:|--:|---|---|---|
| 1.26 | production mix, before the shared field | 1 | 3 | 08-26 | 5,684 cand / 7,169 s | `mine1` |
| 0.976 | field, **before** field sharing | 1 | 1 | 08-26 | 9 never-opened places x 8 maps | `curate mine bench` |
| 0.673 | field, after | 1 | 1 | 08-26 | same | `mine bench` |
| 0.217 | field, after | 1 | 8 | 08-26 | same | `mine bench` |
| 0.178 | field, after | 1 | 20 | 08-26 | same | `mine bench` |
| 0.165 | field, after | 1 | 40 | 08-26 | same | `mine bench` |
| 0.041 | a bare recolour, flat in maxiter | 1 | — | 08-26 | same | `mine bench` |
| 0.417 | 6 cycled field modes | 3 | 40 | 08-27 | `dc1`/`dc2`, 61,863 cand | depth curves |
| 0.356 | 3 field modes | 3 | 20 | 08-27 | same | depth curves |
| 0.260 | near band, mode held | 3 | — | 08-27 | same | depth curves |
| 0.898 | `tia` dump, 3-mode roster | 3 | — | 08-27 | same | depth curves |
| 0.497 | 6 breadth field modes | 1 | 24 | 08-28 | seed 20260827 | `curate depth` |
| 0.696 | 2 composites, **no sharing** | 1 | 24 | 08-28 | seed 20260827 | `curate depth` |
| 0.278 | 2 field modes, near-heavy | 1 | 24/127 | 08-28 | `mine1h` field leg | `curate depth` |
| 0.743 | 4 direct traps, near-heavy | 1 | 24/136 | 08-28 | `mine1h` composite leg | `curate depth` |
| 0.270 | `{gaussian_int, curvature}` | 1 | 24/40 | 08-28 | 649 of a 2,416 plan, seed 20260901 | worker bench |
| 0.496 | same | 3 | 24/40 | 08-28 | 1,076 of the same plan | worker bench |
| 0.424 | same, `ENGINE_THREADS_PER_WORKER` 7 | 3 | 24/40 | 08-28 | 1,254 | worker bench |
| 0.442 | same, 4 engine threads | 3 | 24/40 | 08-28 | 1,219 | worker bench |
| 0.2652 | one leg's seed re-run serially | 1 | — | 08-28 | 440 of 440 identical recipes | `mine_weak_modes` |
| 0.4707 | the same leg | 3 | — | 08-28 | location-matched to the row above | `mine_weak_modes` |
| 4.377 | WIDE, weak modes | 3 | 3 | 08-28 | 2,726 renders / 3,988 s | `mine_weak_modes` |
| 0.680 | DEEP, weak modes | 3 | 40 | 08-28 | 4,520 renders / 1,038 s | `mine_weak_modes` |
| 0.285 | NEAR, weak modes | 3 | 96 | 08-28 | 35,306 renders / 3,402 s | `mine_weak_modes` |
| 2.843 | COMP, 3 composites | 3 | 24 | 08-28 | 2,107 renders / 2,002 s | `mine_weak_modes` |
| 1.480 | `direct_trap_lines` alone | 3 | 24 | 08-28 | 849 renders / 422 s | `mine_weak_modes` |
| 0.4505 | `trap_circle`,`gaussian_int`,`curvature` | 3 | 60 | 08-29 | 45,104 cand / 6,833 s | `sparse_mode_harvest` P1 |
| 0.501 | `gaussian_int` | 3 | 60 | 08-29 | 15,035 cand | same leg |
| 0.500 | `curvature` | 3 | 60 | 08-29 | 15,034 cand | same leg |
| 0.350 | `trap_circle` | 3 | 60 | 08-29 | 15,035 cand | same leg |
| 1.646 | `direct_trap_screen` | 3 | 12 | 08-29 | 1,977 cand | `sparse_mode_harvest` P2 |
| 1.469 | `direct_trap_lines` | 3 | 12 | 08-29 | 1,978 cand | same leg |
| 2.360 | `direct_trap_ring` | 3 | 12 | 08-29 | 1,977 cand | same leg |
| 0.953 | `itinerary` — never shareable, full render | 3 | — | 08-29 | `mode_policy` pricing | `mode_policy` |
| 0.239 | `smooth`, priced beside it | 3 | — | 08-29 | same | `mode_policy` |
| 0.3433 | `smooth` alone, whole leg | 3 | 12 | 08-29 | 116,520 cand / 9,710 places | `smooth_500` |
| 0.4777 | `smooth`, that leg's own pilot | 3 | 4 | 08-29 | 11,138 cand | `smooth_500` |
| 0.3558 | `smooth`, ranked-bands arm | 3 | 12 | 08-29 | 84,084 cand / 7,007 places | `smooth_500` |
| 0.3132 | `smooth`, flat arm | 3 | 12 | 08-29 | 24,948 cand / 2,079 places | `smooth_500` |
| 0.3038 | `smooth`, conditioned arm | 3 | 12 | 08-29 | 7,488 cand / 624 places | `smooth_500` |
| 4.676 | production draw, 1 smooth + 2 strange, palette head | 3 | 1 | 09-01 | 2,286 cand / 762 head-q4 nuclei | `reframe_q4` |
| 0.692 | 5 accepted **field** modes | 3 | 40 | 09-01 | 1,400 cand / 35 whole visits | `audit_field40` |
| 1.883 | 3 accepted **direct traps** | 3 | 40 | 09-01 | 1,440 cand / 36 whole visits | `audit_direct40` |
| 7.360 | 5 **composites** + `itinerary` | 3 | 40 | 09-01 | 328 cand / 7 whole visits | `audit_comp40` |
| 0.5461 | 5 accepted **field** modes, all three arms | 3 | 40 | 09-01 | 6,557 cand / 208 blocks | `general20` |
| 56.92 | 9 dear + `smooth` + `exp_smoothing`, **`phoenix:classic`** | 3 | 22 | 09-02 | 16 cand / 20 blocks | `pc_pilot` |
| 53.54 | the same roster, same plane | 3 | 11 | 09-02 | 103 cand / 13 blocks | `pc1` |
| 35.28 | the same roster, same plane, width 3 | 3 | 3 | 09-03 | 103 cand / 35 blocks | `pc20m` |
| 0.5978 | `smooth`, a re-mode leg at **k ≈ 1.6** | 3 | 1–2 | 09-04 | 3,602 cand / 2,302 places | `smooth_twins` |
| 0.5575 | 4 shareable modes, **floor draw** over proven places | 3 | 8 | 09-05 | 6,408 cand / 203 places | `thin_a` |
| 1.371 | the same 4 modes, **breadth** over fresh places | 3 | 12 | 09-05 | 2,634 cand / 222 places | `thin_b1` |
| 1.184 | the same leg re-run on a thinner never-opened pool | 3 | 12 | 09-05 | 1,146 cand / 98 places | `thin_b1b` |
| 0.4036 | near band, mode held, over one night's own places | 3 | 24 | 09-05 | 912 cand / 38 places | `thin_b2` |
| 2.996 | **13 dear modes**, incl. the 5 `direct_trap_multiply` cells | 3 | 3 | 09-05 | 605 cand / 16 places | `thin_c` |
| 1.942 | 4 shareable modes, **breadth** over fresh places | 3 | 8 | 09-05 | 11,090 cand / 1,388 places | `night_a1` |
| 0.353 | near band, mode held, over one leg's own places | 3 | 40 | 09-05 | 8,720 cand / 218 places | `night_a2` |
| 1.764 | `night_a1`'s settings on a 1,388-place thinner pool | 3 | 8 | 09-05 | 4,330 cand / 543 places | `night_a3` |
| 0.515 | **3** shareable modes, floor draw over proven places | 3 | 8 | 09-05 | 51,959 cand / 2,167 places | `night_b` |
| 8.423 | `smooth_angle_min` + `smooth_mean_angle`, **no sharing** | 3 | 3 | 09-05 | 1,923 cand / 322 places | `night_c` |
| 4.618 | 11 dear modes, the 5 `direct_trap_multiply` cells included | 3 | 4 | 09-05 | 2,340 cand / 56 places | `night_d` |
| 1.015 | 3 shareable modes, **breadth** over never-opened places | 3 | 12 | 09-06 | 17,933 cand / 1,497 places | `armA_places_0906` |
| 0.404 | near band, mode held, over the **whole** band | 3 | 12 | 09-06 | 35,448 cand / 2,954 places | `armB_freeslots_0906` |
| 0.737 | the arm A row's own pilot | 3 | 12 | 09-06 | 768 cand / 64 places | `pilotA_places_0906` |
| 0.714 | the arm B row's own pilot | 3 | 12 | 09-06 | 1,001 cand / 86 places | `pilotB_freeslots_0906` |
| 5.391 | **the whole `mined()` roster**, breadth over never-opened places | 3 | 12 | 09-07 | 6,006 cand / 502 places | `armA1_0906` |
| 4.680 | the same, six hours later on a thinner never-opened pool | 3 | 12 | 09-07 | 3,811 cand / 318 places | `armA2_0906` |
| 2.312 | the same roster, near band, mode held, over places WITH ROOM | 3 | 12 | 09-07 | 6,963 cand / 582 places | `armB1_0906` |
| 3.304 | arm A1's own pilot, and it reached three partitions of ten | 3 | 12 | 09-07 | 545 cand / 45 places | `pilotA_0906` |
| 2.523 | arm B1's own pilot | 3 | 12 | 09-07 | 519 cand / 43 places | `pilotB_0906` |
| 4.422 | the same roster, breadth, a day on from `armA1_0906` | 3 | 12 | 09-07 | 2,847 cand / 238 places | `armA_0907` |
| 4.293 | the same, later the same day | 3 | 12 | 09-07 | 1,757 cand / 148 places | `armA2_0907` |
| 2.444 | the same roster, near band, mode held, places WITH ROOM | 3 | 12 | 09-07 | 1,390 cand / 116 places | `armB_0907` |
| **0.795** | the same roster, near band, mode held, places **AT THE KEEP** | 3 | 12 | 09-07 | 16,200 cand / 1,350 places | `armB2_0907` |
| 0.516 | **a rotation of a stored recipe**, 4 field modes, one dump a pair | 3 | 5 rot | 09-11 | 47,010 rot / 9,402 rows / 6,764 pairs | `rotation_pass_ckpt120` |
| 1.593 | **a mined best-of-five**, whole `mined()` roster, per CANDIDATE | 3 | 5 | 09-11 | its own pilot, 177 cand / 45 shots | `rotation_pass_ckpt120` |
| 2.870 | **the 9 dear modes**, floor draw over proven places untried in the angle modes | 3 | 3/mode | 09-13 | 1,883 cand / 72 places, `phoenix:classic` out | `mine_pilot_ckpt124_armA` |
| 4.160 | the same 9, **breadth** over never-opened places | 3 | 1 | 09-13 | 1,282 cand / 1,282 places | `mine_pilot_ckpt124_armB` |
| 1.261 | 3 shareable modes, breadth + **aimed**, over never-opened places | 3 | 12 | 09-14 | 6,413 cand / 537 places | `easy125_wide` |
| **0.759** | `tia`+`stripe`, **floor draw** over proven places, cells aimed | 3 | 5/mode | 09-14 | 10,601 cand / 1,062 places | `easy125_recolour` |
| 1.164 | 3 shareable modes, breadth + **aimed**, over never-opened places | 3 | 12 | 09-15 | 16,392 cand / 1,366 places | `on125_wide1` |
| 1.047 | the same leg on the last 296 never-opened places | 3 | 12 | 09-15 | 3,552 cand / 296 places | `on125_wide2` |
| **0.886** | `tia`+`stripe`, floor draw over **proven** places, cells aimed | 3 | 5/mode | 09-15 | 20,979 cand / 3,945 blocks | `on125_recolour1` |
| 1.010 | the same arm's SECOND pass, same manifest, same night | 3 | 5/mode | 09-15 | 9,995 cand / 2,140 blocks | `on125_recolour2` |
| **3.872** | **`threads` alone**, floor draw over proven places untried in it | 3 | 3 | 09-15 | 2,513 cand / 2,169 blocks | `on125_threads` |
| **20.911** | 3 shareable modes, breadth, **`phoenix:classic` alone** | 3 | 3 | 09-15 | 280 cand / 246 blocks | `on125_phoenix` |

⚠ **`threads` costs 3.872 and its median stored render reads 2.324 — a 67% gap, and
the render figure is the one that misleads.** A composite dumps no field
(`fields_swept: 0`), so a leg pays a whole render a candidate plus the per-candidate
overhead the shareable modes amortise; the ledger's median render is the render
alone. **Size a composite leg off a leg's `seconds_per_candidate`, never off
`hunt.seconds`.**

⚠ **`phoenix:classic` at 20.911 is 18x the pool average and twice the 9.389 s the
flat band carried**, and it splits by mode: `smooth` 7.575, `tia` 19.040, `stripe`
**35.956**. Yield at `SEATING_BAR` is `smooth` **0**, `tia` **0**, `stripe` 15 of 94
(15.96%) — **390.3 engine seconds a clear against the recolour arm's 7.0, 56x**. The
three older `pc*` rows above priced the dear roster there; this prices the cheap one
and the answer does not change. The partition's remaining never-opened places are a
write-off, not a queue.

⚠ **`mine_pilot_ckpt124_armA` and `armB` are the same roster on two populations and
they differ 1.45x in
price and 3.0x in what a clear costs**, measured back to back on one box on 2026-09-13:
the floor draw over proven places returned **111 clears at `SEATING_BAR` in 1,883
candidates (5.89%)** for **48.7 engine seconds a clear**, and breadth over never-opened
places **36 in 1,282 (2.81%)** for **148.1**. Width is part of the first number and
none of the second — a dear mode dumps no field, so its price is flat in width and the
1.45x is the places. **A dear-mode leg is priced by where it stands, not by how wide it
goes.**

⚠ **`easy125_wide` and `easy125_recolour` are the SHAREABLE half of that same
comparison, taken back to back on one box on 2026-09-14, and they say it again at
2.4x.** The floor draw over proven places cleared `P(>=3) >= 0.50` in **6,533 of
10,601 (61.6%) for 1.2 engine seconds a clear**; breadth over never-opened places
cleared **2,795 of 6,413 (43.6%) for 2.9**. Unlike the dear-mode pair, width *is*
part of both numbers — a shareable mode dumps one field and recolours off it, so
the floor draw's five recolours a (place, mode) pair amortise a dump the breadth
arm pays once per mode at a fresh place. **The cheap arm is cheap twice over**:
0.759 against 1.261 engine seconds a candidate, and a hit rate 1.41x higher on top
of it. What it costs is retention — **4,981 of its 10,601 rows were pruned at the
merge (53.0% kept) against the breadth leg's prune-free 100%**, because a proven
place is a place with a pair already filling up. 1,443 incumbent rows were
displaced by the survivors, so the prune is not pure loss.

⚠ **The displacement half of the near band is the CHEAPEST arm this project has
measured on the full roster — 0.795 against the with-room half's 2.444 and breadth's
4.422 — and the cause is which places are in it.** A place already at
`RETAIN_PER_PAIR` is a place that has been mined often, so its incumbent coloring is
one of the cheap shareable modes, and [`depth.plan_held_mode`] then buys twelve
recolours off one field dump. `armB2_0907`'s roster mix says it outright: **`smooth`
is 9,600 of its 16,200 candidates (59%)**, where the with-room half's largest mode
was `tia` at 204 of 1,390. The two halves of one band, on one roster, on one box,
**differ 3.1x in price** — so a leg that sizes them off a single rate will mis-plan
one of them, and it is the cheap half that overruns its plan.

⚠ **`--rate` sizes the PLAN and the plan is what stopped `armB2_0907`.**
`PLAN_HEADROOM * workers * budget / rate` at `--rate 1.6` gave 16,200 candidates for
a 5,400 s share; the arm made all 16,200 in **4,323 s** and stopped with 1,077 s of
its reserved share unspent, because the rate was set below the with-room half's 2.44
and above this half's 0.795. **Set the rate below the cheapest arm the leg will run,
not below the dearest** — the standing advice to under-estimate is right and this is
what it costs to under-estimate by only half.

**The full mined roster is 5.3x the breadth price of the three shareable modes and
6.2x the near band's, and the two rises have different causes.** Twelve modes at
width 12 gives each place one candidate a mode, so the three field modes pay a dump
apiece for a single recolour and the **nine dear modes pay a whole render each**:
they are 75% of arm A's candidates and **82% of its seconds**. The near band's rise
is sharper and is not about width at all — [`depth.plan_held_mode`] renders the
**incumbent's** mode, so a twelve-mode roster admits composite incumbents to a draw
that used to be recolours of a dumped field. Measured on `armB1_0906`'s own rows,
a `smooth_stripe` incumbent costs **13.0 s** a candidate where a `smooth` one costs
0.63.

**The angle share, priced off an observed angle draw rather than off the mix.**
`smooth_mean_angle` + `smooth_angle_min` read **5.407 s** over the 94 of them in
`pilotA_0906` — 17.3% of its candidates and 28.2% of its seconds — against
`night_c`'s **8.423** at width 3. The gap is width and not the modes: a narrow unit
is dump-dominated, and at width 12 the pair rides a block that has already paid.
Neither figure is a mixed-roster price and neither should be read as one.

**`phoenix:classic` confirms at a third sitting, and it is the plane and not the
draw.** `armA1_0906` read it at **31.50 s** a candidate over 168 of them — 2.8% of
the leg's candidates for **16.3% of its seconds** — which sits between `pc1`'s 53.54
and `pc20m`'s 35.28 for a dear roster there. It is already down-weighted to 0.25 in
[`curation.draw_weights`] and still costs a sixth of a three-hour unit.

⚠ **The per-partition price is a fact about the places drawn, not about the plane,
and one leg caught it twice in one night.** The two phoenix planes swapped rank
between the arm-A units six hours apart on one roster: `phoenix` cost **6.68 s** in
`armA1_0906` and **11.92 s** in `armA2_0906`, where it was that unit's dearest
partition, while `phoenix:classic` went 31.50 → 28.60. Read a plane's row here as
the price of the places that leg reached and re-pilot rather than carrying it.

⚠ **A short pilot mis-prices a partition-round-robin draw, and it does so in
whichever direction the dear partitions happen to land.** The two 09-06 pilots above
are the same shape as the two legs beneath them and they miss in *opposite*
directions: arm A's pilot read **0.737** against a realized **1.015** (38% under) and
arm B's read **0.714** against **0.404** (77% over). Neither miss is depth, which is
what [`LEGS.md`](LEGS.md)'s *A forty-place pilot over-priced this leg by 1.7x* had
found — it is the **partition mix**. `hunt.spread` is a round-robin, so at 64 places
each of ten partitions gets six or seven whatever they cost: arm A's pilot drew 12
`phoenix` and **no `phoenix:classic` at all**, while its leg drew 518 phoenix at
1.182 s and **517 phoenix:classic at 4.389 s**; arm B's pilot drew 85 of its 1,001
candidates (8.5%) at `phoenix:classic`'s 3.063 s against the leg's 480 of 35,448
(1.4%). **So read a pilot's `price` block per partition and re-weight it by the
plan's own partition counts, rather than reading its pooled
`seconds_per_candidate`** — the pooled figure prices the pilot's partition mix and
never the leg's.

**The eight-hour night re-measured the same shapes an order of magnitude wider, and
two of the five rows above it did not hold.** The breadth/floor gap survives —
`night_a1` at **1.942** against `night_b`'s **0.515**, 3.8x, on width 8 both sides,
so the dump really is the whole of it. What did not survive is the dear-mode price:
`thin_c` put 13 dear modes at **2.996** over 16 places, and the two angle modes alone
over 322 places read **8.423**, while the 11-mode roster over 56 places read
**4.618**. A dear-mode rate is a fact about *which* dear modes and about the places,
not about dearness — size an angle-mode leg off `night_c` and never off `thin_c`.
`night_a3` reproduces `thin_b1b`'s finding a second time: the same opener settings
re-run after its own places left the never-opened pool read **1.764** against
**1.942**, so a breadth rate drifts *down* as a night proceeds, not up.

**The 09-05 rows are one night on one map cut, and the breadth/floor gap is the
dump and nothing else.** `thin_a` and `thin_b1` run the *same four modes* at
**0.5575** and **1.371** — 2.5x apart — because a floor draw at width 8 pays one dump
per eight recolours and a breadth draw at width 12 over four modes pays one per
three. Width is the knob that moves it and the roster is not. `thin_b1b` is
`thin_b1`'s own settings re-run after 222 places had left the never-opened pool and
reads **1.184**, so the 2.5x is the shape rather than that draw's luck.

**The last row is the shape a `curate remode` leg has, and it is the one leg here
whose width is not a knob.** Its plan is *every* clearing row of the retired mode,
so `k` is however many of them happen to sit at a place — 3,602 twins over 2,302
locations, about 1.6 — and a dumped field is amortised over that and no more. At
**0.5978 s a candidate** it reads between this table's `smooth` k=1 bench (0.673,
one engine) and its k=12 leg (0.3433, three engines), which is where a rate with
almost nothing to share should sit. Concurrency was **2.94 of three workers**, the
highest on this table, because a block is a dump plus one or two recolours and no
worker sat behind a long visit. So: **price a re-mode leg at the k=1 end**, and do
not read a shared-field saving into it.

**The two 09-02 rows are the same roster as arm A at 17x its price, and the plane
is the whole difference.** Arm A ran nine dear modes plus `smooth` and
`exp_smoothing` at **3.155 s** a candidate over never-opened *centered* parameter-plane
locations; the identical roster over `phoenix:classic` reads **53.5**. Nothing about
the roster moved. What moved is **maxiter**: this plane's admitted places sit at
widths around 1e-4 and carry **12,243–21,702** iterations, and nine of the eleven
modes are composites or direct traps with no field to dump, so there is nothing to
amortise the depth against. The pilot predicted the main leg to within **6%** — the
rate is stable, it is simply large.

**So price a leg on the partition it will actually draw, not only on the roster.**
Every other row in this table was measured over parameter-plane or `julia:*`
material, and a leg sized off any of them would have over-planned this one by more
than an order of magnitude. At 53.5 s a candidate, an hour on three engines buys
about 200 candidates here against arm A's 3,400.

**The plane's price is not a constant of the plane, and `pc20m` is the evidence.**
Six hours after `pc1`, the same roster over the same partition read **35.28 s** a
candidate against 53.54 — a **34% fall** — and none of the things that explain a
price moved. Maxiter: mean 15,770 against 14,443, medians 13,445 and 13,494, and
the same 1.3e-2 median frame width. The kind mix: composite 47 both, direct 27
against 28, field 20 against 17, modulate 9 against 11. The stage shares: paint
0.713 → 0.699, repaint 0.208 → 0.223, dump 0.061 → 0.058. Every mode fell by
roughly a third at once — `direct_trap_screen` 20.8 → 14.2, `smooth_stripe` 111.0
→ 56.3, `smooth_mean_angle` 72.2 → 48.6 — which is what a machine moving looks
like and not what a draw moving looks like.

The practical consequence is the *other* direction from the one this table was
built to warn about. A rate carried in from six hours earlier over-priced the leg
by 52%, and only [`depth.PLAN_HEADROOM`]'s 1.6 kept it from stopping early with
its budget unspent: `pc20m` planned 105 and made 103, landing at 1,218.6 s of
render wall against 1,200 allowed. **Pilot the plane again rather than reading a
figure off this table**, and treat the headroom as the thing that absorbs the
error rather than as slack.

**And on this plane the cheap modes are the ones that pay.** Over the 119
candidates of `pc_pilot` + `pc1`, clear rate at `P(>=3) >= 0.50` against mean
seconds a candidate: `direct_trap_screen` **72.7% at 20.8 s**, `direct_trap_lines`
63.6% at 22.3 s, `smooth_stripe` 54.5% at 111.0 s, `smooth_mean_angle` 45.5% at
72.2 s, `smooth` 30.0% at 14.0 s, `smooth_angle_min` / `smooth_curvature` /
`threads` 27.3%, `itinerary` 10.0% at 83.9 s, `exp_smoothing` 9.1%, and
`direct_trap_multiply` **0 of 11 at 84.2 s**. The two cheap direct traps are the best
on both bars and the expensive composites are not earning their 3-5x here, so a
second leg on this plane should be direct-trap-first.

**`pc20m` re-ran that reading over 35 fresh places and it holds at the top and
falls apart in the middle.** Its 103 candidates at width 3 clear `P(>=3) >= 0.50`
at 29.1% against `pc1`'s 33.6%, and `direct_trap_screen` is the best mode on the
plane a second time — **80.0% of 10 at 14.2 s**, the cheapest thing on the roster
and the one that clears most. Below it the order does not survive: `smooth_stripe`
55.6%, `smooth_curvature` 50.0%, `smooth_angle_min` 45.5%, `smooth_mean_angle`
42.9%, `threads` 20.0%, and then **`direct_trap_lines` collapses from 63.6% to
11.1%** while `smooth` goes 30.0% to **0 of 9**. So one claim is reproduced —
the cheapest direct trap pays best here — and the rest of the ranking is noise at
these n.

**What did not reproduce at all is the top end. `P(>=4) >= 0.50` is 0 of 103**,
against `pc1`'s 5 of 103, and the leg's whole maximum is **0.371**. Both legs drew
never-opened places on the same partition under the same roster; this one drew 35
places across all ten rank bands where `pc1` drew 13, so the wider draw reached
further down the location head's rank and found no q4 at all. A per-place maximum
over **three** modes rather than eleven is part of it and cannot be the whole of
it: the ceiling moved from 0.723 to 0.371.

**Every cell of that is n = 10 or 11, which is one pass of the roster at each place,
and it prices an arm rather than a mode** — `MINE_overnight_full_roster_centered`'s
own lesson, where a 40-place pilot read two modes at 1 clearing candidate in 160 and
they returned 51 and 40 over 1,725 each. Read the table as *where to point the next
leg*, not as a ruling on any mode. In particular the `direct_trap_multiply` zero is
**not** evidence against that mode: `AUDIT_direct_trap_multiply_whitewash`, the same
day, re-read 77 of its clearing locations fresh at label geometry and found `P(>=4)`
median **0.805** with only 4 under 0.5. That audit's population is conditioned on
already clearing and this one is a fresh draw, so the two do not contradict — but
eleven candidates on one plane settle nothing about a mode that has 77 good ones
elsewhere.

| 1.500 | 4 `direct_trap_multiply` **variants**, known places | 3 | 4 | 09-02 | 308 cand / the 77 places holding a clearing dtm row | `dtm_known_pilot` |
| 5.280 | the same 4 variants, breadth over never-opened | 3 | 4 | 09-02 | 1,362 cand / 2,403 s, 2,018 unstarted on the clock | `dtm_variants` |

**Those two rows are the same roster over two populations, and they are 3.5x apart.**
The pilot priced the 77 known places — `julia:*` and `multibrot*`, median maxiter about
8k — and the leg it sized then spent most of its clock somewhere else entirely. Its own
per-partition table says where:

| partition | cand | s/cand mean | median | max | share of the leg's engine seconds |
|---|--:|--:|--:|--:|--:|
| `phoenix:classic` | 72 | **51.46** | 26.20 | 280.15 | **51.5%** |
| `phoenix` | 72 | 12.01 | 2.91 | 87.59 | 12.0% |
| `mandelbrot` | 80 | 5.11 | 3.16 | 33.35 | 5.7% |
| `multibrot5` | 96 | 3.26 | 1.98 | 32.06 | 4.4% |
| every `julia:*` | 742 | 1.18-2.70 | ~1.1 | 25.31 | 15.4% |

**144 candidates of 1,362 — 10.6% — took 63.6% of the engine time**, and 72 of them took
half of it on their own. `phoenix:classic` was opened into the candidate ledger for the
first time on 2026-09-02 (`c8a82d6`), which priced its eleven-mode roster at 53.5 s a
candidate against 3.155 on the parameter planes for exactly the reasons that apply here:
its places carry 12k-22k maxiter and a direct trap has no field to dump. Those places are
now in the **never-opened breadth pool**, so every breadth draw taken from this date
forward inherits that tail whether or not it means to.

Two rules follow, and the second is the one that cost a leg. **Pilot the population, not
just the roster** — the standing caveat above says a rate is a joint fact about the roster,
the width and the geometry, and the population belongs in that list ahead of most of them.
And **a pilot over a named, already-opened population does not price a breadth arm at all**:
the known places are selected and shallow, the never-opened pool is neither, and the two
differ here by more than any roster change in this table.

**The three 09-01 rows are one matched pilot** — `ranked_bands` at share 1.0, seed
20260901, the never-opened drawable pool banded across the whole rank range, nothing
merged — so they are the one place in this table where three kinds are comparable.
Per **visit** (40 candidates at a place) they are **27.7 / 75.3 / 212.1 s** mean and
**21.6 / 47.8 / 199.5** median. Their medians are 0.372 / 1.157 / 5.231, which is
where the mean-vs-median warning below bites hardest: sizing a field leg off the
median over-plans it by 86%.

Where the visit goes, and it is not the same shape three times. A field visit is
**9.13 s of dump** — five modes at 1.83 s each, 33% of the leg — then 0.463 s a
candidate for the recolour, judge, colour and autolevel. A direct trap is **86.3%
`paint`** and nothing else: no dump, and `autolevel.applies_to` excludes the kind, so
`repaint` and `measure` are exactly 0. A composite is 59.1% `paint` and **33.6%
`repaint`** — the operator's second pass is a second *full render* there, so a third
of a composite visit is the autolevel curve firing.

On a wall hour at three workers, and applying each mode's own `headroom.bars` rule
over the standing pool, that is **15,133 / 5,601 / 1,448** candidates an hour and
**1,378 / 109 / 99** clearing ones — field buys **13.9x** the seatable pictures of
composite and **12.7x** of direct trap. On these pilots' own fresh clear rates
(4.71% / 4.24% / 1.83%) it is 713 / 237 / 27, which is 27x and 3.0x; the pool's
rates are the higher pair because the pool holds legs that aimed at those modes.

**The direct figure read 330 an hour and 4.2x for half a day, and the bar is why.**
Merging the three pilots put `direct_trap_multiply` over `FALLBACK_LOCATIONS` at
exactly 25, its rule flipped off the `P(>=3)` fallback, and the leg's mixed pool rate
went 5.88% → 1.94%. Nothing about the mode changed and no row was re-rendered. This
is the sharpest example in this file of why a per-mode rate is meaningless apart from
the rule it was taken under — and of why a *ratio* between two modes on different
columns is not a comparison at all.

**Every `s/cand` above is a MEAN, and the flat-vs-ranked comparison needs the
median beside it.** A per-candidate cost is long-tailed — `mine1`'s per-partition
means run 0.67 to 2.06 against medians of 0.42 to 1.05 — so the two answer
different questions and neither substitutes: a **mean** is what sizes a plan,
because `PLAN_HEADROOM * workers * budget / rate` is arithmetic over the *sum*,
and a **median** is what a candidate typically costs. Quoting one alone hides
which. Both read off the rows themselves, `hunt.seconds` on `mine1`'s
`rows.jsonl` and `seconds` on `smooth_500`'s `sequence.jsonl`, per arm:

| leg | arm | n | mean | median | mean/median |
|---|---|--:|--:|--:|--:|
| `mine1` 08-26 | `deepen` | 2,274 | 0.7064 | 0.4690 | 1.51 |
| `mine1` 08-26 | `breadth_ranked` | 1,989 | 1.3000 | 0.7030 | 1.85 |
| `mine1` 08-26 | `breadth_flat` | 1,421 | 2.0848 | 0.8750 | 2.38 |
| `smooth_500` 08-29 | `conditioned` | 7,488 | 0.3038 | 0.1980 | 1.53 |
| `smooth_500` 08-29 | `flat` | 24,948 | 0.3132 | 0.2280 | 1.37 |
| `smooth_500` 08-29 | `ranked_bands` | 84,084 | 0.3558 | 0.2520 | 1.41 |

**"The ranked arm renders 1.6x cheaper than the flat one" is a mean and only a
mean.** On medians the same two arms are **1.24x** apart, so most of that gap is
`breadth_flat`'s tail — an unconditioned draw takes places nobody chose and a few
of them are very dear — rather than its typical candidate. The direction survives
the change of statistic and the size does not, which is the whole reason both are
here.

**And the sign is not a standing fact about the two draws.** On `smooth_500`,
one mode and the whole top half of the head's rank, the ranked arm is the
**dearer** of the two — 1.14x on the mean and 1.11x on the median — because that
leg's ranked draw is spread over five bands and the flat draw is not, so the two
are drawing from differently-stocked partitions. `mine1`'s ordering is `mine1`'s.

**Per-mode dump cost in breadth**, one number a mode, `dc1`/`dc2` 2026-08-27:
`stripe` .378 · `gaussian_int` .285 · `curvature` .268 · `tia` .147 ·
`exp_smoothing` .147 · **`smooth` .056**. Stripe's field costs seven times smooth's
to dump, which is why it is the dearest field mode to draw.

**What the spread is made of, and it is not noise.** The table runs 0.041 to 4.377,
a hundredfold, and four mechanisms account for nearly all of it. **Field sharing**:
one dump amortised over `k` palettes, 0.976 to 0.165 from k=1 to k=40 on the same
places. **Coloring kind**: a mode with no dumpable field pays a full render every
candidate, which is `itinerary` at 0.953 against `smooth`'s 0.239 on the same day.
**Where the draw came from**: a near-band place holds its mode and pays one dump
over the whole set; a breadth place cycles the roster and pays one per mode.
**Contention**: three engines are ~1.7x per candidate over one, and the record's
`concurrency` field is engine-seconds over wall and is **not** a speedup.

**A pilot over-reads a short leg's rate by a knowable amount.** Budget seconds are
`stages.total()` and exclude the fixed start — the population read, the judge load
and the plan build, about 50 s — so a short run's wall carries it and a long run's
does not. `mine1h`'s pilots measured wall/spent at 1.28 where the legs came in at
1.03 and 1.02. Read a pilot's `spent / made`, never its wall. And do not pilot
unlike shapes concurrently: a k=40 pilot sharing the machine with a dump-heavy k=3
pilot came out 42% dear, and a composite pilot including the cheap
`direct_trap_lines` under-priced a leg that dropped it by 89%.

**The clear rate is the other per-candidate rate, and the thin colour cells are where
it was last read.** Over the **169,082 candidates on the ledger 2026-09-03** (21,299
clearing, each against its own mode's `headroom.bars` rule, nothing re-scored), the
five cells thinnest in a 2,000-seat solve:

| cell | delivered | clearing | clear% | carriers | maps >= .10 |
|---|--:|--:|--:|--:|--:|
| `light_vivid_magenta` | 3,207 | 501 | **15.6** | 49 | 78 |
| `dark_vivid_lime` | 2,506 | 158 | 6.3 | 24 | 41 |
| `dark_vivid_yellow` | 2,050 | 186 | 9.1 | 26 | 87 |
| `light_vivid_lime` | 3,034 | 130 | **4.3** | 62 | 86 |
| `light_vivid_cyan` | 2,548 | 179 | 7.0 | 47 | 73 |

against a **ledger-wide 12.6%**. Every one of them has 24+ carriers in the library and
2,050+ rendered candidates on record, so the library can make those colours and the
draw does make them — the ceiling is the **judge**, and `light_vivid_magenta` clears
*above* base rate and is a seating loss rather than a supply one. `--draw-cells` moves
`delivered` and cannot move `clear%`.

**Rates in other units live elsewhere and never belong in this table.** A gallery
release is priced per **row** (3.5 s/row on gallery4's 249 winners at 1280x720 ss2
on three workers, against gallery3's 44.6 s at 2560x1440 ss4 on four), and a
labeling measure pass per **unit** (2.8 s/unit over nine modes, 5.90 s/unit on a
single-mode sheet cut from the top of the pool). A row and a unit are a finished
picture; a candidate is 640x360 ss2. Mixing the three is how a leg gets priced an
order of magnitude wrong.

**The whole 18-mode `color_mass` grid costs 137.8 s a map and the 13 accepts
125.4**, and the spread by kind is carried rather than the mean —
[`MEASUREMENTS_decisions.md`](MEASUREMENTS_decisions.md)'s *What a `color_mass`
close costs a map, measured 2026-09-06*.

## What the solve costs by stage, control and narrowed, measured 2026-09-07

The 277,542-candidate pool (40,127 clearing, the fine head read on every one),
idle box, `--key cascade` and everything else at the defaults, three rungs over
two populations. `PROFILE_solve_stages_0907`. Seconds are wall clock off each
record's own stage blocks; the front half is the same calls, timed where they are
called. **The narrowed population is the whole pool filtered to the fine head's
`p_fine(>=4) >= 0.50` — 10,974 candidates** — and is the previous leg's, seat for
seat: 1000 / 18 / 1.50391 / 1876.60 both times.

| | seed | swap | augment (twins) | re-swap | **solve** | seed filled | chain pairs |
|---|---|---|---|---|---|---|---|
| control n=200 | 1.2 | 0.5 | 2.1 (1.5) | 0.0 | **11.1** | 200 | 0 |
| control n=500 | 4.6 | 2.9 | 1.2 (0.3) | 0.0 | **16.1** | 500 | 0 |
| control n=1000 | 19.2 | 15.8 | 26.0 (23.3) | 6.2 | **74.8** | 993 | 61 |
| ≥0.50 n=200 | 1.1 | 0.5 | 0.4 (0.1) | 0.0 | **4.6** | 200 | 0 |
| ≥0.50 n=500 | 4.1 | 2.3 | 23.5 (20.3) | 1.7 | **34.2** | 442 | 47,760 |
| ≥0.50 n=1000 | 13.8 | 13.7 | 90.7 (43.3) | 12.7 | **133.4** | 792 | 357,906 |

**In front of every one of them, once a process:** pool read **21.6 s**, the
`cascade` order **7.1 s**. Per solve: the bars 0.5 s, the neutral pre-selection
2.2 s, the view 0.4 s, the sidecar read 1.1 s — 4.3 s of a 74.8 s control solve,
and flat in `n`.

**This is growth and not a regression, and the cascade is not the suspect.** The
`cascade` lay-over is **0.35 s** of that 7.1 s — the rank key underneath it is
4.9 s and the pool read dwarfs both. Against `solver_design.md`'s n=1000 reading
on the 2026-09-04 pool (110.4 s: seed 18.1 · swap 6.7 · augment 72.1 · re-swap
10.6), the control at n=1000 is **74.8 s over a pool 70% larger** — the seed is
flat at 19.2 s because the view is sized in seats, and the augment fell 72.1 →
26.0 because the cascade's seed fills 993 rather than 911. What did rise is the
first swap loop, 6.7 → 15.8 s, over a view that grew 19,518 → 21,780 rows.

**The chain stage's cost is what the seed left it**, which is the whole reading:
it is 1.6% of the control's n=1000 solve and 68% of the narrowed one, at the same
`n`, over the *smaller* pool. See `GALLERY.md`'s *A narrowed view is a different
cost regime, and the budget DOES bind there*.

**After the two speedups of the same day**, both bit-identical and both verified
by running the retired spelling beside the shipped one at all six points:

| | before | after | |
|---|---|---|---|
| control n=1000 | 71.7 s | **63.4 s** | 1.13× |
| ≥0.50 n=1000 | 127.7 s | **93.0 s** | **1.37×** |
| ≥0.50 n=1000, chain stage alone | 87.3 s | **60.0 s** | 1.45× |

**A `p_fine >= 0.50` bar on the view still fills n=1000 and lifts both the sum and
the worst seat**, 0.60 fills and 0.70 is open —
[`MEASUREMENTS_decisions.md`](MEASUREMENTS_decisions.md)'s *What a `p_fine` bar on
the view buys at n=1000, measured 2026-09-07*.

**A colour measure over finished pictures reads the 160x90 decode and never a
candidate render**, which moves a swatch by a median 2.1 points and by up to 64 —
[`MEASUREMENTS_decisions.md`](MEASUREMENTS_decisions.md)'s *What the finished
collection expressed, measured 2026-09-06*.

**The scatter under every objective comparison at n=1000 is about 1.4 of sum**,
because a tightened constraint here comes back with a better answer —
[`MEASUREMENTS_decisions.md`](MEASUREMENTS_decisions.md)'s *A tightened constraint
comes back with a BETTER answer, so a shadow price here is a suboptimality
reading*.
