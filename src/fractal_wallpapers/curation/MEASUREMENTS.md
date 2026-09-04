Every dated reading this stage has taken, in the order the document made them.
Split out of [`README.md`](README.md) so a rate is quoted from one place rather than
restated beside each mechanism — those live there, in [`GALLERY.md`](GALLERY.md) and
in [`LEGS.md`](LEGS.md). The caveat under *Every per-candidate rate this project has
measured* is stated once and governs every row in this file.

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

## What the flip found, measured 2026-08-31

One pool — 97,423 candidates, 11,137 clearing, 4,480 places after the neutral
pre-selection — censused both ways (`floor_default` beside `floor_flat`).

| n | floors ask | supply | short? | the flat floor asked |
|---:|---:|---:|:---|---:|
| 20 | 6 across 6 modes | 6 | no, slack 0 | 0 |
| 150 | 45 across 13 | 45 | no, slack 0 | 14 |
| 500 | 150 across 13 | 150 | no, slack 0 | 70 |
| 1000 | 300 across 13 | 296 | **short by 4** | 140 |

**At `n = 1000` the pool is provably short on the mode floors, and the flat reading
said nothing.** `smooth_mean_angle` holds 27 of the 30 it is asked for and
`smooth_angle_min` 29 of 30. It is a cheap mine instruction: 53.6 and 40.0 seconds
per win on those two modes, so the four places are about 201 render-seconds, ~67 s
of wall clock over the three-worker pool. The estimator is the unconditioned
ledger-wide rate and an aimed leg beats it.

`palette_group_cap` used to be short beside it there and **was not really short at
all** — see the note under *The group cap was a second spelling* in
[`GALLERY.md`](GALLERY.md).

**The slack is exactly zero at every rung below that**, which is the shape to
notice rather than the comfort: supply meets the demand and never exceeds it,
because a mode's contribution is capped at its own floor by construction. One place
lost at any floored mode makes the block short. It is the tightest block in the
census.

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
* Over the **13 accepted strange modes** — `accepted()` less `smooth`, read from
  `colorize.modes_for(budget.STRANGE)` — `2·promoted + 1·normal` sums to 20 and
  distributes the strange budget fully. Each mode's floor is **half** its share, so
  the floors sum to exactly half the budget and the other half is the gallery's to
  spend on whatever is strongest. At `n = 1000`: budget 600, floors summing to 300,
  30 a promoted mode and 15 a normal one.
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

## What the two empty modes actually cost, measured

`smooth_mean_angle` and `smooth_angle_min` are the pair the n=2000 census called "nothing in the
pool". They are **composites, not field modes** — no dump to amortise, a full render a candidate —
and the dearest pair on the roster after `smooth_stripe`. `empty_modes`, 2026-09-01, this machine
idle, three engines below-normal, `--width 8 --floor-width 4`, seed 20260827, 979 candidates in
1,813.5 s render wall at concurrency 2.989:

| arm | population | `smooth_angle_min` | `smooth_mean_angle` |
|---|---|---|---|
| `ranked_bands` | never-opened, head-ranked | 0.090 · **75 s** | 0.059 · **129 s** |
| `mode_floor` | proven places | 0.097 · **66 s** | 0.032 · 229 s |
| `flat` | never-opened, unconditioned | 0.040 · 202 s | 0.040 · 218 s |
| **all arms** | | **10 wins · 85 s** | **6 wins · 160 s** |

Location clear rate · **wall** seconds a clearing location; engine seconds are 2.989x these. The
bar is each mode's own `headroom.bars` rule, `P(>=4) >= 0.50` for both since they came off the
`P(>=3)` fallback that morning — a rate quoted against the older rule is a different number.

**Three things to carry forward.** The head's rank buys money: `ranked_bands` beats the
unconditioned `flat` control 2.2x and 1.5x, and flat is the worst arm for both. The census priced
the two within 0.4 s of each other and **`smooth_mean_angle` actually costs 1.9x per win**, being
both the slower render and the thinner clear rate (1.84% against 2.66%) — allocate to them
separately. And the census's own figure was **76.5 / 76.9 s a win against a realized 113 s pooled,
1.47x optimistic**, because it was carried in from another leg's rates.

**Mining one short mode does not necessarily cut the shortfall.** The 16 clearing locations this
leg bought moved `smooth_mean_angle` 21 -> 25 and `smooth_angle_min` 18 -> 22 at n=2000, and the
total shortfall stayed at **200**: `smooth_curvature` lost 6, `smooth_stripe` 3 and `threads` 1 in
the same pass. A place seated in one mode is a place not seated in another, so in a gallery where
ten demands are short, a mine that does not add **places** moves seats between them. These 16
added only 9 to the view (4,750 -> 4,759) — the `mode_floor` wins were at places the view already
held. What refuses these two is `below_its_mode_bar` and then `one_per_location`, at 2-3x what
twin refuses; that is the opposite of the gallery-wide ranking and it is a supply problem.

## What the four knobs bought, measured overnight 2026-09-01/02

`MINE_overnight_full_roster_centered`: four arms as four separate legs, each with its
own wall budget and its own pilot, 88,022 candidates in 40,825 s of render wall
(11.34 h) and 122,055 engine seconds at concurrency 2.990.

| arm | roster | population | cand | places | s/cand pilot → main | share of seconds |
|---|---|---|---|---|---|---|
| A | 9 dear + `smooth` + `exp_smoothing`, width 22 | never-opened `centered` | 17,694 | 807 | 3.095 → 3.155 | 45.6% (50 asked) |
| B | 6 short dear, `--floor-width 4` | opened, no dear attempt | 11,313 | 472 | 2.547 → 2.722 | 25.1% (25) |
| C | 5 field, width 40 | never-opened, non-centered | 45,675 | 1,146 | 0.585 → 0.618 | 23.0% (20) |
| D | 5 field, aimed at 6 thin cells | never-opened, top half | 13,340 | 544 | 0.567 → 0.575 | 6.3% (5) |

**Arm A's roster is now declared and it is ten, not eleven.** It ran out of a
scratch driver, and this table was the only record of what it drew — a roster
nothing tracks is a roster every ruling about it has to be remembered rather than
read. `depth.centered_modes()` is it: `dear_modes()` plus `CENTERED_FIELD`
(`smooth`, `exp_smoothing`), less `CENTERED_EXCLUDED`. Before, the eleven above:
`smooth_mean_angle`, `smooth_angle_min`, `smooth_stripe`, `smooth_curvature`,
`direct_trap_screen`, `direct_trap_multiply`, `direct_trap_lines`, `threads`,
`itinerary`, `smooth`, `exp_smoothing`. After, those ten less
**`direct_trap_lines`** — Matt's ruling of 2026-09-02, off the eye-check sheet
`8ce5def` reports: every `direct_trap_lines` seat in the newest n=2000 baseline
read against every centered candidate clearing the mode's own bar, and the verdict
is that it is not a centered mode.

**That is one arm's draw and nothing else.** The mode is still `mode_policy`
weight 1, still on `dear_modes()`, still drawn by every other leg, and its seat
floor is unmoved; every row, picture and label already taken in it stands. A
roster says where an arm spends and a weight says what a mode is worth, and
`tests/test_depth.py` pins the two apart so the next roster ruling does not read
as a demotion.

**It closed every mode floor at n=2000**: the census went from `mode_floors` short by
56 to `nothing provably short`. `smooth_mean_angle` 35 → 78 seats, `smooth_angle_min`
37 → 90, `direct_trap_multiply` 23 → 74, `itinerary` 59 → 109. That is the sequel to
*A GENERAL leg cannot close a floor* in [`LEGS.md`](LEGS.md): the diagnosis was right
and the fix is
`--modes` naming the dear half, which arms A and B did.

**A share is a share of seconds when each arm is its own leg.** The warning under
*`sequence.jsonl` carries the whole autolevel stamp* in [`LEGS.md`](LEGS.md) — a
5%-declared arm taking 25% of the budget — is a property of `weave`
holding arm proportions in *counts* inside one plan. Across legs it cannot arise: the
budget is wall seconds and the clock is the share. Every arm landed within 4.4 points
of its declared share, and every pilot priced its main leg to within 7%.

**Rank-conditioning is worth more on a dear roster than on a field one.** Both arms
drew a top-4-band ranked arm against an unconditioned flat control over the same pool:

| arm | ranked clearing places | flat control | lift | engine s a clearing place |
|---|---|---|---|---|
| A, dear roster | 332/565 = 58.8% | 70/188 = 37.2% | **1.58x** | 119.3 against 179.2 |
| C, field roster | 388/743 = 52.2% | 99/248 = 39.9% | **1.31x** | 45.3 against 69.3 |

Not comparable to `general20`'s 1.07x, and the difference is the draw rather than the
population: that leg's ranked arm spanned the whole rank range, so it and its uniform
control covered one population and could not differ. A's fitted slope over ten bands
is an odds ratio of **0.837 a band**, 0.626 clearing at band 0 to 0.252 at band 9.

**The near band has no unconditioned control from this era, and the one of record is
`mine_diverse_0903_d2`.** It is the leg a `--draw-cells` near-band arm is read against
— same seed, same `--near-width` — but it was itself narrowed, by a hand-cut open-cell
manifest of **416 maps**, so a comparison against it prices a sharp colour cut against a
coarse one and never against base rate. The two share 28 of 163 places. Read a lift over
it as a lift over another narrowing.

**A pilot prices an arm's pooled rate and not its modes.** B's 40-place pilot read
`smooth_angle_min` and `smooth_mean_angle` at 1 clearing candidate in 160 each — and
over 1,725 each they returned 51 and 40. At a ~1% rate a 160-candidate sample expects
1.6 and measures nothing. A_pilot erred the other way: `direct_trap_screen` read 6.6%
on 54 places and 0.73% on 753. Size a pilot for the rate that sizes the plan; do not
demote a mode on one.

**Aiming the palette buys a thin cell 19-50x cheaper than the census prices it.** Win
here is dominant in the cell *and* clearing its mode's bar:

| cell | aimed hit | flat hit | lift | aimed engine s a win | flat s a win | census estimate |
|---|---|---|---|---|---|---|
| `light_vivid_lime` | 62.1% | 3.6% | 17.4x | **34.0** | 839 | 1,015 |
| `dark_vivid_lime` | 48.8% | 1.7% | 29.1x | **45.5** | 1,678 | 1,495 |
| `dark_vivid_yellow` | 52.9% | 1.5% | 34.7x | **33.1** | 1,678 | 632 |
| `light_vivid_teal` | 50.8% | 1.9% | 26.8x | **19.9** | no wins | 676 |

The flat control's realized cost brackets the census's estimate, which is a check on
the census. But that estimate is **unconditioned**, and a census row for a thin colour
cell is therefore not the cost of buying that colour — it is the cost of waiting for
it. Nothing downstream of the census knows this.

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


## What the gallery leg costs at n=150 on this machine

Measured 2026-09-01 over the 100,743-candidate pool, idle machine, `--no-render`:
**`curate solve run --n 150` is 44.6 s** — pool and view 11.2 s, the seed 24.5 s and
the swap loop 8.9 s, over a view of 6,818 rows. The five-minute figure this
paragraph used to carry was the leg before `curation.signatures` and the two swap
prunes; the table under *What it costs* is the one to read. The retired history is the
comparison worth keeping: on 2026-08-29 over a 275,822-candidate pool the exact
solve was 238 s at n=150 and **did not terminate at all** at n=1000, while the
sequential `curate seat` was 51 s at n=150 and had no objective to report.
