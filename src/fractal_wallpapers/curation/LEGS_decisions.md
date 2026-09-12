# The legs' decision log

The reasoning behind [`LEGS.md`](LEGS.md), kept apart from it so that *what does
this leg do today* is answered by one file and *how it came to* by this one. Every
section below was moved here **verbatim on 2026-09-12** out of the reference file,
under its own heading and in the order it stood there: a dated reading, a leg's own
record, or a measurement that produced a rule the reference file now states on its
own.

**No finding here is re-dated and no figure is restated.** A section says what it
said the day it was written, which is the whole value of it — every figure in one is
a figure about the store, the keep and the roster of that day, and a leg is sized
off [`LEGS.md`](LEGS.md) and [`MEASUREMENTS.md`](MEASUREMENTS.md) rather than off a
reading here. The move made two edits and no others: a reference that said *above*
at a section still in [`LEGS.md`](LEGS.md) was repointed to name it, and three
sections that had been `####` under a parent which stayed there are `###` here, so
that every entry is a peer and no outline claims a parent it does not have.

**The order here is [`LEGS.md`](LEGS.md)'s, leg by leg, and not the order the
readings were taken in** — `curate depth`'s floor sweep of 09-05 stands ahead of its
mode pricing of 09-10 because the floor draw is documented ahead of the mode roster.
A new entry goes beside the readings for its own leg, and the chronology is in the
dates the sections carry rather than in their order. A heading here is cited the way
everything in this tree is cited — by heading and file, never by line number.

### What a floor leg may stand on is a FREE SLOT, and `smooth` has almost none

Measured 2026-09-05 over 9,901 proven unpinned places, which is the population
`--floor-places` is cut from. Retention keeps
[`candidate_ledger.RETAIN_PER_PAIR`] rows a (location, mode) pair, so what a
floor unit can add prune-free is the *free slots* at its own mode's pairs — and
the four field modes are not remotely alike on that axis. **The table is at the
keep of 3 it was measured under**; the keep is 5 since 2026-09-06 and every row
of it grew, `smooth` most of all in proportion. Re-cut it with
`curate candidate-ledger free-slots --mode <mode>` rather than scaling it:

| mode | high-band places untried | free slots (proven) | places with one |
|---|--:|--:|--:|
| `curvature` | 3,468 | 17,868 | 6,633 |
| `tia` | 2,623 | 14,245 | 5,355 |
| `stripe` | 2,547 | 14,094 | 5,340 |
| **`smooth`** | **80** | **2,237** | **1,510** |

**`smooth` is the mode this pool was opened with**, so 5,682 of the 6,537
high-band places already hold the full keep in it and only 80 have never been
tried. A `smooth` floor unit is therefore bounded at about 2,237 candidates
whatever the clock says, and a leg that asks for more is asking for rows the merge
will drop — `draw_cells_smoke` kept 9.7% of such a pass and `thin_b2` 9.8%. Size
a mode's unit off its free slots, not off its clear rate.

**And a unit's width is its free slots, which is why `smooth` runs at 1.** The
other three fill untried pairs at width 3 and are prune-free by construction; a
`smooth` unit over places holding one or two rows already has one or two slots, so
width 1 over every place with a slot buys the most places per second and keeps
every row. What that gives up is the deeper slots — 727 of the 2,237 — which would
cost a second and third unit at widths 2 and 3 over a quarter as many places.

**The width to run is the one maximising `W * |places with room >= W|`**, and
pairing it with a manifest cut at that same `W` is what makes a unit keep
everything it renders. Width 1 over every place with a slot is that rule's answer
where the room is thin; it is not the rule. `general_leg_0909`'s band cuts held
9/6/14/328 places at room 1/2/3/4, so the four widths absorb 357, 696, 1,026 and
**1,312** rows and the answer is **4** — width 1 there would have left three
quarters of the room unspent. All three of that leg's band merges kept **every row
they rendered**. The room per place is
`curate candidate-ledger free-slots --min-slots N`'s question, asked once per `N`.

### What the twelve modes cost and what they buy, measured 2026-09-10

`smoke_mine_20260910`, 1,834 s of render wall, 5,433 engine seconds, 1,661
candidates, 93 clears at `Q4_BAR`, 31 rows over the shipped fine bar. **n is ~100 a
mode in the ten-mode unit, so this is an ordering and not a set of rates.**

| drawn mode | s/cand | clear@.50 | gg rows | eng-s a gg row |
|---|--:|--:|--:|--:|
| `smooth_stripe` | 10.81 | 2.94% | 0 | — |
| `smooth_curvature` | 7.79 | **0.00%** | 0 | — |
| `smooth_mean_angle` | 7.36 | 5.26% | 0 | — |
| `smooth_angle_min` | 6.76 | 4.00% | 4 | 169 |
| `threads` | 5.21 | 8.82% | 4 | 133 |
| `itinerary` | 4.92 | 4.12% | 2 | 238 |
| `direct_trap_multiply` | 1.79 | 2.06% | 2 | 87 |
| `direct_trap_lines` | 1.57 | 2.02% | 0 | — |
| `direct_trap_screen` | 1.54 | 5.05% | 2 | 76 |
| `smooth` | 1.48 | **10.75%** | 2 | 69 |
| `stripe` | 1.33 | 8.82% | 6 | **45** |
| `tia` | 0.57 | 6.57% | 9 | **30** |

★ **The scarcity of the non-field modes is a PRICE fact before it is a quality
one.** `tia` and `stripe` took 9.97% of the engine seconds and returned **40.7% of
the rows, 52.7% of the clears and 48.4% of the gallery-grade rows**. The four dear
`smooth_*` composites took **60.1% of the whole leg's clock for 4 gallery-grade
rows**. But the ten are not one population: `threads` and `direct_trap_screen`
clear at ordinary prices and are worth feeding, and a leg meaning *feed the others*
should name them rather than the composites.

**A one-mode unit is much cheaper per candidate than the same mode inside a mixed
cycle**, because the dump amortises over the unit's whole width instead of over the
one or two candidates the cycle gives it: `tia` read **0.573 s** here against 2.49 s
in the twelve-mode leg of 2026-09-09, and `stripe` **1.331** against 5.22. So
splitting by mode buys rows as well as control.

**What a single leg would need to do this natively**: [`draw_weights.converted`]'s
algebra on the mode axis, at these prices, wants turn weights `tia` 4.78 and
`stripe` 2.05 against 1.0 for the other ten. The prices are per-width, so such a
table needs [`hunt.Price.seed_for`]'s band discipline or it repeats the near-band /
breadth mistake the partition side already refuses.

### The opener refills the band at about a FIFTH of what it opens, and that is what bounds arm B

Measured three times over two legs, and the three agree: of the never-opened places
a breadth arm opens, the share that lands in the near band **with room at its own
incumbent pair** is `armA1_0906` **83 of 502 (16.5%)**, `armA2_0906` **59 of 319
(18.5%)**, `armA_0907` **52 of 238 (21.8%)**, `armA1_0908` **50 of 309 (16.2%)**,
and the three breadth arms of `general_leg_0909` **77 of 370 (20.8%)**, **87 of 438
(19.9%)** and **68 of 358 (19.0%)** — seven readings between 16 and 22%.
The other four fifths land in
*neither* half of the band — their best roster candidate is outside
`[SEATING_BAR, PRIMED_BAR)` — and **none of them can land in the at-the-keep half**,
because a pair a breadth arm just opened holds one row against a keep of five. A
breadth arm moves the with-room half and leaves the other exactly where it was:
2,369 places before `armA_0907` and 2,369 after.

The arithmetic closes end to end across the two legs, which is why the share is
worth trusting: 588 places with room after `armA1_0906`'s re-cut, `armB1_0906` drew
**582** of them, **6** survived the night, `armA2_0906` added **59** — and the next
morning's cut read **65**. `armA_0907` added **52** and it read **117**; `armB_0907`
then planned **116 of the 117**, made 1,390 of a planned 1,392, and stopped for
budget at 2.

⚠ **So arm B cannot be given more clock than arm A earns for it, however efficient
it is.** At 4,200 s of render wall `armA_0907` bought 52 band places, and `armB_0907`
cleared the whole 117-place band in **1,205 s** — the opener spends three and a half
times the clock to stock a band the near arm empties. Weighting a night toward the
near band is a decision about **which half of the near band**, not about the split
between the arms: only [`the displacement half`](#the-displacement-half-is-not-supply-limited-and-that-is-what-it-is-for)
has supply to absorb it.

⚠ **The figure this replaces was a misreading and it reached a prompt.** "327 of 502
opened places landed in `[0.50, 0.90)`" was quoted as arm A's refill rate; 327 is the
count of `smooth`/`tia`/`stripe` among the **542** places the *pre*-leg cut held, and
has nothing to do with the 502. A prompt sized on it would give arm B four times the
clock its supply can take.

### The displacement half is not supply-limited, and that is what it is for

The band's two halves are supply asymmetric by two orders of magnitude and the
asymmetry is stable: on 2026-09-07 the with-room half held **117** places against the
at-the-keep half's **2,369**, and a breadth arm cannot add to the second. So the
half that is measured by the arithmetic above is the half that runs out, and the
half where a row can only enter by **beating an incumbent** is the one with room for
a night's clock. What it buys is not stock — net ledger change is zero by
construction, one incumbent deleted per row kept — but **quality inside the pair**,
and that is a different purchase from every other arm this project runs.

### What the near band buys, decomposed by the incumbent mode, measured 2026-09-07

**The band never chooses a mode.** [`plan_held_mode`] renders each place at its
own `best_mode`, so a unit's mode *is* its incumbent's, and widening the roster
changes which incumbent wins the per-place argmax rather than adding modes to
try. That identity is checkable and was checked: over `armB_0907` and
`armB2_0907`, **0 of 116 and 0 of 1,350 places carry more than one mode**, so the
arms' own `by_mode` block *is* a decomposition by incumbent mode.

Split on `colorize.shareable` — the engine catalog's **`field`** kind, the one
coloring with a single scalar field behind it, so one iteration pass serves every
palette at that pair. Everything else (composite, modulate, direct) re-renders
per candidate, and that dump is the whole of the price difference.

| arm | half | cand | eng s | s/cand | clear | kept clears | s a kept clear | seats |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| B | field | 528 | 386 | **0.730** | 17.0% | 74 | **5.21** | 2 |
| B | non-dumping | 862 | 3,012 | **3.494** | 22.7% | 147 | 20.49 | 8 |
| B2 | field | 14,784 | 7,869 | **0.532** | 6.9% | 885 | **8.89** | 11 |
| B2 | non-dumping | 1,416 | 5,016 | **3.542** | 11.1% | 121 | 41.45 | 11 |

**The dump is worth 4.8x-6.7x on price and the dear modes convert 1.3x-1.6x
better, and the price wins.** A field mode is 3.9-8.9 engine seconds a kept clear
against 20-41; per engine-hour, B2's field half returns **405** kept clears
against the non-dumping half's 87.

**On SEATS the two halves are level, and that is the finding.** B's ten seats are
**8 non-dumping to 2 field** off 11.4% of the clock; B2's twenty-two are **11 and
11** off 38.9%. So the dear half takes half the seats for a third to a ninth of
the candidates — the conversion advantage is real all the way through to the
gallery, and it is not big enough to beat the dump on rate. Neither half
dominates and the mix is not a knob the band has: which half a place falls in is
its incumbent's mode, decided before the leg starts.

**Which modes:** B2's field half is `smooth` (9,600 candidates, 800 places),
`tia` (2,748) and `stripe` (2,436) — a place already at the keep has been mined
often, so its incumbent is cheap and shareable. Its dearest per candidate are
`smooth_stripe` **8.13 s** and `smooth_mean_angle` **6.84 s**, at 139 and 104
engine seconds a kept clear. `direct_trap_multiply` clears best in both arms
(100% at B, 35.4% at B2) and has taken **no seat in either**.

### The aim is not what fails, and `direct_trap_multiply` has no vivid half

`dtm_lc_smoke`, 2026-09-07, tested the reading left open by [`LEGS.md`](LEGS.md)'s
*`--draw-cells` is the same filter cut by RULE instead of by hand* — its ruling that
a leg wanting a thin cell should not spend its clock on the direct traps. The test
was the same mode aimed at the cells it *can* reach. Both halves came back clearly.

**The mode is structurally muted.** Of 942 pool maps, the number expected to deliver
any **vivid** lime or cyan cell at [`palettes.dominance.CELL_LEAD`] is **zero** for all
four, and 0/0/1/2 at a 0.05 cutoff. Realized history agrees over 13,938 unaimed rows
(previously-aimed excluded on `hunt.drawn_for`/`drawn_cells`): `light_vivid_cyan` **0**,
`light_vivid_lime` 3, `dark_vivid_cyan` 10, `dark_vivid_lime` 24, while every one of the
mode's top eighteen realized cells is `*_muted_*`. So a vivid cell is not a thin target
for this mode, it is an **absent** one, and `thin_cells_1h_0905`, the fifteen-cell
leg that ruling was cut from, was aimed at cells nothing could have delivered.

**Aimed at the muted cells the aim works and the clear rate still dies.** Conditioned
arm **48.4%** in the target union against a matched flat control's 15.3% — lift
**3.15x**; per cell `light_muted_cyan` 54.3% vs 6.6% and `light_muted_lime` 40.3% vs
8.7%. And the conditioned arm cleared **0 of 1,160**, in all four quarters, where the
flat arm cleared 11. Rows both dominant and clearing: **2**, both unaimed. So that
ruling stands for a reason it did not state — the delivery is fine, it is the
**pictures** the carrier maps make in this mode that never clear.

**An unaimed leg already lands 27.3%** of its rows in the eight lime/cyan cells, so the
ceiling on aiming here is 3.7x and the measured figure is 3.15x. Two further readings:
the aimed arm's map supply **exhausts inside seven minutes** (new maps by quarter
**129 → 28 → 6 → 4**, 167 distinct maps against the flat arm's 670), and it makes 22x
more colourless pictures — 13.19% of its rows carry no dominant cell against 0.60%.
Whole leg: 2,320 candidates, 11 clears (0.47% against a ledger-wide 14.39%), **none
reaching `p_fine(>=4) >= 0.50`**, the best at 0.264.

**And price a `direct_trap_multiply` breadth draw off a breadth draw.** `night_d`'s
floor draw reads 3.4572-3.7538 s a candidate per engine; this breadth draw ran at
**2.105**. `PLAN_HEADROOM` absorbed the 1.7x and the leg made its whole plan on 94.1%
of the clock, but a rate carried across draw shapes over-reads for this mode.

**And the cut is one-sided in the other direction too**: `dark_vivid_blue`, the
richest cell in the library and deliberately excluded from that leg's draw, took
**1,099 rows — more than any of the three cells the leg was aimed at** — with 43.1%
of the night's rows landing no listed cell at all. Narrowing the offer moves the
distribution and never truncates it, so a leg aimed at a thin cell still feeds the
rich ones and a seating taken after it will show the rich cells moving too.

**Every row a narrowed leg writes is stamped `hunt.drawn_cells`**, on the same
contamination rule as `drawn_for` and for a wider reason: `--draw-cells` cuts
the pool *all five* draws offer, so no row of such a leg is a base rate, the flat
control arm's included. `drawn_for` beside it stays the aimed arm's alone. The two
are `candidate_ledger.ASKED_FOR` and both are written only when there is an ask, so
an unnarrowed row carries the two fields the block has always carried.

### What the first leg bought, measured

`smooth_twins`, 2026-09-04, `exp_smoothing` → `smooth`, the whole clearing
population and no sampling:

| | |
|---|--:|
| `exp_smoothing` rows in the ledger | 22,603 |
| of them clearing, at 2,318 places | **3,647** |
| twins already in the ledger, skipped | 45 |
| twins rendered, 0 failed | **3,602** |
| of them clearing `smooth`'s own bar | **3,463 (96.1%)** |
| surviving the retention rule | **3,152** |
| stranded places that regained a clearing row | **546 of 574** |
| render wall / engine seconds / concurrency | 732 s / 2,153 s / 2.94 |

**Two of those rows are the ones to read.** 3,463 twins cleared and only **3,152**
survived — the other 311 were absorbed by `RETAIN_PER_PAIR` at places already
holding three better-ranked `smooth` rows, which is the retention rule working and
not a loss. And the places figure reconciles by two independent routes: clearing
places in accepted modes went **8,740 → 9,286**, and `574 − 28 still stranded =
546`. The 28 that stay stranded are places whose twin did not clear.

**The 96.1% is a carry rate and not a mode comparison.** Every source is in the
plan because it cleared, so the 139 twins that fell below the bar are all the
crossings there are — a downward-only count by construction. `read` reports the
crossings both ways all the same, and **`crossed_up` is zero by construction and is
read as an assertion rather than as a result**: a non-zero one means a source that
did not clear reached the plan, which is a defect in `remode.population` and not a
finding about a mode. A reader who takes the pair as a symmetry test has read a
selection effect as evidence. The paired `delta`
has a mean of **−0.0098** and a median of **−0.0010** for the same reason: a
source selected on a high noisy reading has a twin that regresses, which is
`shrinkage`'s winner's curse arriving by another route. Neither number is evidence
about `smooth` against `exp_smoothing`; the unselected comparison is
`EVAL_exp_smoothing_0904`'s.

### What the first pass found

`rotation_pass_ckpt120`, 2026-09-11, the whole rotatable passing set: 9,402 rows,
47,010 rotations, 2.579 engine seconds a row. **3,468 adopted with the row removed,
1,391 adopted beside a row a guard held, 4,543 left alone, 0 refused by the
tolerance.** A rotation wins 51.7% of rows and a *single* rotation wins 19.0%, so
the width is the whole result. `curation/MEASUREMENTS.md`'s *What a rotation of a
stored recipe costs* has the prices.

⚠ **The winning rotation is usually a SMALL one — and that is the selection rather
than the curve.** Inside 0.05 turns of phase 0 a rotation wins 41.3% of the time
against 12–15% past 0.20. On the mining arm, whose control nothing selected on, the
same table is **flat** across the turn at 50–55%. A store row is above the bar
*because its phase-0 reading was*, so phase 0 sits on a hill and a near neighbour is
still on it. `palette_variant_mine_ckpt120` measured the phase win as absent below
0.125 turns and was measuring the other population.

**The tolerance has never fired and structurally cannot while the re-score agrees.**
Phase 0's fresh reading reproduced its stored column to 5.0e-7 over all 9,402 rows,
so a winner has already beaten 1.0x it. That is what the knob is *for* — it is a
guard against a levelling, a head or a picture having moved, and a pass where it
starts refusing is a pass to read rather than a factor to lower.

### What the first batch came to

`repeat_ckpt120`, 2026-09-11, seed 20260911. 311,494 controls at 32,144 locations
after five exclusions (50,492 direct traps, 2,234 already repeated, 9,918 rotated,
48 rejected, 0 off-regime). 125 pairs drawn — 40 folded, 85 cyclic at 43/42 over
the two rungs — across 14 modes and 9 partitions. 125 rendered, 0 failed, 2 pruned
on the way in. **246 tiles on the page in 123 pairs**, split 70 `smooth_render` /
176 `strange_render` at deliberately unequal sizes.

**It holds the pool** three times — the population read, the merge, and the sheet
plan's ledger check — and the one-pool-holding-process rule binds on all three.

### What the first sitting came to

`repeat_ab_ckpt121`, 2026-09-11, seed 20260911. 374,309 ledger rows, 11,985 above
the bar, **2,549 askable at 2,082 places** after four refusals (7,647 not smooth
routed, 1,447 already rotated, 273 already labelled, 69 already repeated; nothing
lost to a rejection, a regime or a missing picture). **250 tiles at 250 places**,
189 cyclic (a 2× traversal) and 61 folded (4×) — the split is whatever the
population above the bar holds, 20.3% folded, and balancing it would have spent
the reading. 172 distinct maps, 9 partitions, every tile `smooth`.

**500 renders in 595 s of wall on one engine — 2.38 s a tile**, plus 25 s for 500
judge reads and 250 thumbnails: 620 s and 535 MB for the sheet. The draw itself is
10 s of ledger stream.

**It holds the pool once**, in the population read, and the one-pool-holding-process
rule binds on it.

⚠ **That sitting was part-labelled and then let go, on 2026-09-12.** Matt parked
palette replication and ruled the partial verdicts released rather than kept, so the
sheet, its 1,000 pictures and the registration were deleted and **no row was ever
ingested** — `data/repeat_ab/` is a declared and empty store. The numbers above are a
reading about the *draw* and stand; there are no verdicts to read. The command is
unchanged and a later sitting registers its own batch.
