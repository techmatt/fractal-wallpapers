Every leg that settled something. The reasoning half of
[`MEASUREMENTS.md`](MEASUREMENTS.md): one run of one experiment a section — what it
priced, what it changed, and what a later reading bounded or reversed. The standing
quantities are that file's, and a section lands here when the argument is the bulk
of it rather than one clause of it.

**The order is the order the reference file made these sections, which is NOT the
order the legs ran.** The 2026-09-12 rotation reading sits above a 2026-09-06 one
and a 2026-09-01 one, because the split of 2026-09-12 moved them across in place
rather than re-sorting them. A section is found by its heading and never by where it
falls.

**Every section below was moved here on 2026-09-12**, bodies verbatim: nothing was
re-dated, re-argued or merged on the way across, so a figure quoted out of a report
of that day still resolves against the words that reported it. Three things were
touched afterwards and are the whole list. *What the OWED arm costs, measured
2026-09-11* came across as a `###` under a parent that stayed behind and was
promoted to a `##`, its own subsection with it; three sentences that said *the table
above* or *below* of a table the split left in the reference file now cite that file
and heading instead; and the reference file keeps a one-sentence statement of every
rule a moved section was the only home of, carrying the number where the reading
*is* the standing quantity.

**A new entry is APPENDED.** This is a log and not a document: an entry is never
inserted between two older ones, and a reading a later one supersedes stays where it
is and is bounded where it stands. A citation into this file names a heading, so a
heading is not renamed once it is here.

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

**Both of those two are asked for 32 rather than 30 since 2026-09-04.** Dropping
`exp_smoothing` took the strange roster to 12 over a total weight of 19, and both
modes are among the three that take a spare seat from the largest remainder. Read
against the same holdings the shortfall on those two roughly doubles, and the
instruction is the same one, only larger. The table above is the 2026-08-31 census
and has not been re-taken.

`palette_group_cap` used to be short beside it there and **was not really short at
all** — see the note under *The group cap was a second spelling* in
[`GALLERY.md`](GALLERY.md).

**The slack is exactly zero at every rung below that**, which is the shape to
notice rather than the comfort: supply meets the demand and never exceeds it,
because a mode's contribution is capped at its own floor by construction. One place
lost at any floored mode makes the block short. It is the tightest block in the
census.

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

**Arm A's roster is now declared and it is nine, not eleven.** It ran out of a
scratch driver, and this table was the only record of what it drew — a roster
nothing tracks is a roster every ruling about it has to be remembered rather than
read. `depth.centered_modes()` is it: `dear_modes()` plus `CENTERED_FIELD`
(`smooth`, `exp_smoothing`), less `CENTERED_EXCLUDED`, and less whatever
`mode_policy` weights 0 — which since 2026-09-04 is `exp_smoothing` itself, so the
cheap half of this arm is `smooth` alone. Before, the eleven above:
`smooth_mean_angle`, `smooth_angle_min`, `smooth_stripe`, `smooth_curvature`,
`direct_trap_screen`, `direct_trap_multiply`, `direct_trap_lines`, `threads`,
`itinerary`, `smooth`, `exp_smoothing`. After, those eleven less
**`direct_trap_lines`** — Matt's ruling of 2026-09-02, off the eye-check sheet
`8ce5def` reports: every `direct_trap_lines` seat in the newest n=2000 baseline
read against every centered candidate clearing the mode's own bar, and the verdict
is that it is not a centered mode — and less `exp_smoothing`, which is a standing
rather than a roster ruling and is applied by asking the weight.

**That is one arm's draw and nothing else — for `direct_trap_lines`.** That mode is
still `mode_policy` weight 1, still on `dear_modes()`, still drawn by every other
leg, and its seat floor is unmoved; every row, picture and label already taken in
it stands. A roster says where an arm spends and a weight says what a mode is
worth, and `tests/test_depth.py` pins the two apart so the next roster ruling does
not read as a demotion.

**`exp_smoothing` is the other kind of departure, and it is why the two are pinned
apart.** It leaves this arm because it leaves *every* arm: weight 0 is a standing,
not a roster ruling, and `centered_modes()` applies it by asking
`mine._mined_modes()` rather than by editing `CENTERED_FIELD`. Until 2026-09-04
it did not ask, and this was the one roster in the tree where a weight-0 mode
would have gone on being drawn after every other draw had dropped it. That gate
now carries a second standing as well: since 2026-09-06 `mine._mined_modes()` is
`mode_policy.mined()` rather than `accepted()`, so a mode ruled out of the mines
and left in the gallery leaves this nomination by the same sentence.

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

## What the aim bought in SEATS, measured overnight 2026-09-03/04

The section above prices a **win** — a candidate dominant in the thin cell *and*
clearing its mode's bar. `READ_rare_cells_yield_0904` priced the **seat**, and they
are not the same question: the 19-50x lift on wins is real and most of it does not
reach the gallery.

**The read is a counterfactual solve and not an attribution.** BEFORE is the live
pool with the night's whole 16,731-row merge removed by merge stamp, and it
reproduces the tracked `20260904T080248Z` key for key at 941 seats; the live pool
reproduces `20260904T134242Z` key for key at 947. Both columns are re-solves of that
pair, run through the pool-view door under *A scratch driver asks the same two
questions* in [`GALLERY.md`](GALLERY.md).

**Seats per 1,000 engine seconds at n = 1000**, ALL column: **C near band 4.52 ·
A aimed 1.02 · A2 aimed 0.70 · B flat control 0.58**. The near band — places
adjacent to ones already clearing, aimed at nothing — is the best seat-buyer of the
four by about **4x**, on the arm the mine report had called the wrong instrument. On
matched clocks the aim beats its control 2.05x in seats and 4x in listed-cell seats,
far more than the +14% the same night read off clearing rows alone.

**The aim's advantage does not survive the rung.** At n = 2000 the two converge to
**1.353 against 1.209** per 1,000 s, within 12%, and the aimed cells go the wrong way
(net -7 against the unlisted cells' +18). At n = 1000, 35 of 48 cells sit at the
allowance and the aimed cells are the only ones with room; at n = 2000 only 26 of 48
are, nothing is capped, and the best rows win regardless of colour. **The whole
measurable worth of conditioning the palette is an artefact of the rung.**

Three standing figures the night settled, each of which outlives its report:

* **Fresh places clear at about a quarter of the pool's rate** — 3.5-4.4% against the
  ledger-wide 12.6%. Size any never-opened draw on the lower number.
* **The near band is exhaustible and the aimed arms are not.** It spent its 88
  places in **446 s of a 2,700 s cap** and had nothing left to draw; the instrument
  is a queue, so a leg that means to lean on it prices the queue rather than the
  clock.
* **What stops the supply is the colour ceiling, decisively.** Of the 228 places the
  night opened holding a clearing row, 49 seated and **157 (69%) were refused by
  `cell_allowance`**; row-wise, of 731 clearing rows, 49 seated and 415 went the same
  way. Not the bar, and not held places — the night touched 467 places and **all 467
  were new**, so no row it made ever competed with an incumbent at its own location.

**This is seats per engine second and belongs nowhere near a `s/cand` rate** —
those are [`MEASUREMENTS.md`](MEASUREMENTS.md)'s *Every per-candidate rate this
project has measured*, and they are per engine. A seat is an outcome of the whole
leg plus a solve; a candidate is one 640x360 ss2 render. Mixing them prices a mine
off a gallery's scarcity.

### A one-hour read cannot resolve the aim in seats. An eight-hour one can

**Measured 2026-09-05, and it reverses a conclusion.** `MINE_thin_cells_1h_0905`
re-solved six themed n=200 records after an hour aimed at three of them and found
the three UNAIMED controls moving as many seats as the aimed cells — `dark_vivid_orange`
+4 against `dark_vivid_green` +3 and `dark_vivid_rose` +3 — and concluded that *where
the aim shows is the median and not the seat count*. Eight hours over the same
fifteen cells, same six themes, same rig:

| | aimed: green / yellow / rose | controls: blue / purple / orange |
|---|---|---|
| seats over the q4 bar, after 1 h | +3 / +7 / +3 | +2 / +1 / +4 |
| seats over the q4 bar, after 8 h | **+36 / +16 / +9** | **+1 / +1 / −4** |

So the hour was **too short to resolve the difference and not measuring an absence
of one**. Read a themed seat count off a clock long enough that the aimed cells move
by more than the controls' noise, which at n=200 is about ±4 seats an hour.

**What eight hours still did not buy is the floor.** All six themes fill 200 of 200
throughout, and the worst seat in the two thin themes stayed at ~0.001
(`dark_vivid_green` 0.0001 → 0.0007). The gain is entirely in the middle — median
+0.238 and +0.269 on green and yellow, p10 up on five of six. **A themed n=200 ends
in near-zero pictures no matter how much supply is thrown at it**, so a themed
gallery's tail is a rung problem and not a mining one.

## What the colour ceiling costs at n=1000, measured 2026-09-06

`SWEEP_K_allowance_0906`: four n=1000 seatings over one pool, everything but `K`
identical to `20260906T133236Z`, whose seating the `K = 2` arm **reproduces
exactly** — the same 1,000 keys in the same order, the same objective, the same
refusal table. There is no `--k` on `run` or `record` and there should not be;
`solve.solve(rule=...)` is the override path, and `curate solve k-sweep`
([`curation.k_sweep`]) is the leg that drives it. **The four records were deleted
on 2026-09-06** once Matt decided not to read them — the sweep is to be rerun
under the changed pool, and the command is what carries it rather than a driver in
`scratch/`. **Every number in this section was re-derived from a fresh run of that
command on the same pool and came back identical**, the control rung included, so
what is written here is what the leg produces and not what a deleted driver once
said. `curate solve k-sweep --control <stamp>` takes that check itself and exits
non-zero when the first rung does not reproduce the record it names.

| K | allowance | cells at it | short | worst | sum | seats moved |
|---|--:|--:|--:|--:|--:|--:|
| 2.0 | 42 | 39 | 9 | 0.210413 | 594.78 | — |
| 2.25 | 47 | 32 | 16 | 0.337511 | 618.30 | 178 |
| 2.4 | **50** | 27 | 21 | 0.375682 | 628.07 | 215 |
| 2.5 | 53 | 23 | 25 | 0.401621 | 634.38 | 245 |

**The ceiling is expensive in the objective and it buys muted pictures.** The worst
seat nearly doubles, 0.2104 → 0.4016, and the sum rises 6.7%, with every rung
filling all 1,000 seats and meeting every demand. Across the four, cell
memberships go 1,904 → 2,021 and **all of the growth is muted**: muted 1,008 →
1,129 while vivid sits at 896 → 892. By leading cell the gallery flips from
vivid-majority to muted-majority, 509/488 to 471/527.

⚠ **BOUNDED, 2026-09-09: that tone reading holds to `K ≤ 2.5` and reverses above
it.** It was taken over 2.0 → 2.5 and does not extend. Carried out to 3.75 on the
later pool the growth over 2.0 → 2.5 is even (muted +141, vivid +136) rather than
all muted, and from 2.5 to 3.75 it is **entirely vivid**, +142 vivid against **−90**
muted, with the leading split going 483/516 vivid/muted to **559/441** — past
uniform and back the other way. So *loosening `K` hands the gallery to the muted
cells* is true of the range measured here and false of the range beyond it, and it
must not be quoted as a property of the ceiling. See *What a colour ceiling four
times the target rate costs, measured 2026-09-09* below.

**Twenty-three of the 48 cells track the allowance exactly** — 42/47/50/53 at every
rung, which is also the count still pinned at K=2.5. Warm and blue: all four
`*_orange` and `*_red`, three of four `*_azure`, `*_blue` and `*_purple`, both
dark `*_rose`, `light_*_yellow`, `dark_vivid_magenta`, `light_muted_cyan`. By hue
family over the same four rungs, `orange` goes 112 → 137 and `red` 101 → 125,
against `lime` **83 → 46** and `teal` 106 → 91. The nine cells that were short
at K=2 mostly get **shorter in absolute seats**, because the headroom is spent
where the supply is and one-per-location makes each of those seats displace a
scarce one: `light_vivid_teal` 40 → 18, `dark_vivid_lime` 31 → 12,
`light_vivid_lime` 31 → 13, `light_vivid_cyan` 29 → 13, `dark_vivid_yellow` 27 →
14. `light_vivid_magenta` is flat at 18 → 17 and is the pool's floor, not the
rule's. **So a looser ceiling does not buy the short cells anything; it buys the
long ones more room, and the short cells pay for it.** That half *does* extend —
fourteen of the sixteen cells short at `K = 2` end shorter in absolute seats out at
3.75, four to six times further out — and it is only the **tone** of the growth that
reverses.

**Nothing else becomes binding.** `cell_allowance` stays the top refusal at every
rung — 15,021 → 10,697 → 8,782 → 7,985, still 3.6x `location` at K=2.5 — while
`location` (2,487 → 2,195), `spiral` (518 → 575), `twin` (371 → 405) and
`mode_ceiling` (52 → 49) barely move, and `group_cap` and `family_allowance` stay
at **zero** as they always have. What grows instead is
`the_leg_had_no_seat_left`, 26 → 1,730: the pass stops being colour-bound and
starts being seat-bound. No family comes near its allowance either (top 137 of
209 at K=2.5), and the group cap of 25 never fires — the busiest map takes 7-11
seats at every rung, over 527-539 distinct maps. **The five modes sitting exactly
on their floor — `curvature`, the three `direct_trap_*`, `itinerary` — do not move
at any K**, so the ceiling was not what was holding them down.

⚠ **`K = 2.4` gives an allowance of 50, not the 51 the arithmetic says.**
`floor(k * t * n) + 1` is evaluated in binary floating point and
`2.4 * (1/48) * 1000` comes out `49.99999999999999`, so the floor loses a seat at
exactly the boundary. Every `K` whose product lands on an integer has this, and
`K = 2` does not because `41.67` is nowhere near one. A `K` set for a particular
allowance should be checked against `ceiling.Rule(k=K).allowed(cell, n)` rather
than against the formula on paper.

## What a colour ceiling four times the target rate costs, measured 2026-09-09

`k_sweep_20260909`: six n=1000 seatings over one pool, `K` from the shipped **2**
out to **3.75**, everything else identical to `20260909T173957Z`, whose seating the
`K = 2` arm **reproduces exactly** — the same 1,000 keys in the same order, the
same objective, the same refusal table. Sweep stamp `20260909T203636Z`, six rungs
in 362 s. **Unforced throughout**: `--forced` is a separate axis and mixing the two
would confound this. **Nothing here is adopted** — `ceiling.K` is untouched, every
record is unpublished, and the control is not re-based.

⚠ **The reproduction is the finding people will want first.** Two commits landed
between the control and this sweep — the `--locations` cut moved after the fold and
onto the cluster, and `--forced` staged at the fine column — and an unforced pass
is still seat-for-seat what it was, which is what the `--forced` commit claimed.

**The allowance is a multiple of the *realized* mean and not of a remembered
constant.** The control seats 1,000 wallpapers carrying **1,802 cell memberships**,
**1.802 a seat**, so the mean cell holds **37.54** of them. The `~1.9 a seat` in
this file's 2026-09-06 section is not a rounding of that: it is 1,904/1,000 read
off a different pool, and the figure has fallen since. Every multiple below is
against 37.54.

| K | allowance | x realized mean | family allowance | worst | sum | cells at it | short | seats moved |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| 2.0 | 42 | 1.12 | 167 | 1.503910 | 1891.21 | 32 | 16 | — |
| 2.5 | 53 | 1.41 | 209 | 1.503910 | 1916.17 | 22 | 26 | 293 |
| 3.0 | 63 | 1.68 | 251 | 1.713590 | 1939.09 | 14 | 34 | 380 |
| 3.25 | 68 | 1.81 | 271 | 1.760127 | 1945.08 | 11 | 37 | 395 |
| 3.5 | 73 | 1.95 | 292 | 1.777384 | 1949.38 | 10 | 38 | 401 |
| 3.75 | 79 | 2.10 | 313 | 1.787097 | 1953.61 | 10 | 38 | 423 |

Every rung fills all 1,000 seats, meets every demand at a shortfall of zero, and
seats all 13 modes at or above their floor. Memberships go **1,802 → 2,131**, so a
seat carries 1.802 colours at the shipped `K` and 2.131 at 3.75.

**The pass stops being colour-bound and becomes seat-bound.** `cell_allowance`
falls 8,662 → 3,824 while `the_leg_had_no_seat_left` goes **3 → 825**, and the
crossing is between `K = 2.5` (7 unseated) and `K = 3` (379). `spiral` rises 754 →
1,126 and `twin` 423 → 597 as the loosening pushes the walk further down the
ranking; `location` barely moves (1,487 → 1,167). `group_cap`, `family_allowance`
and `mode_ceiling` are **zero at every rung**, as they always have been.

**The family allowance reads the same `K` and never binds.** `Rule.allowed` is one
function over cells and families alike — `floor(K x share x n) + 1`, with
`FAMILY_SHARE` four times `CELL_SHARE` — so raising `K` raises both in step and the
*relative* slack is fixed. The busiest family runs **135 of 167 (81%)** at `K = 2`
and **180 of 313 (58%)** at 3.75: it gets slacker, not tighter. The arithmetic says
it can never take over either — four cells at their allowance is `4 x 42 = 168`
against a family allowance of 167, one seat apart, and only with *zero* overlap
between the four; real overlap is nothing like that.

**The tone finding of 2026-09-06 reverses above 2.5.** Over 2.0 → 2.5 the growth is
even (muted +141, vivid +136) rather than all muted; from 2.5 to 3.75 it is
**entirely vivid** — vivid +142, muted **-90**. By leading cell the gallery goes
483/516 vivid/muted at `K = 2` to **559/441** at 3.75, so the flip the earlier sweep
saw toward muted turns round and goes further the other way.

**Twenty-three of the 48 cells end lower than they began**, and the losses are cyan,
lime, azure, teal and the cool yellows: by family, `cyan` **83 → 49**, `lime` 52 →
29, `azure` 93 → 69, `teal` 105 → 90, `blue` 93 → 81, `green` 109 → 97, `yellow`
108 → 98, against `red` 135 → **180**, `orange` 132 → 179, `rose` 120 → 152,
`purple` 97 → 127 and `magenta` 101 → 125. **Fourteen of the sixteen cells short at
`K = 2` end shorter in absolute seats**, which extends the earlier sweep's eight of
nine four to six times further out. The worst falls are `light_muted_lime` 38 → 21,
`dark_vivid_cyan` 26 → **9**, `dark_muted_lime` 32 → 16, `dark_muted_cyan` 42 → 27
and `light_muted_cyan` 42 → 28.

⚠ **No cell falls for want of supply, and none for want of its own allowance.**
Every one of the 23 sits strictly below its allowance at `K = 3.75`, so the rule is
not what holds it down; and every one has more unseated clearing places than its
whole deficit, so the pool could have filled it. The rejection ledger says what
took them instead: at `K = 2` their places were refused `cell_allowance` 57-79% of
the time, and at 3.75 that column is `location` (19-46%) and
`the_leg_had_no_seat_left` (12-45%). One seat per cluster is the binding fact, and
the loosening spends the clusters on the colours the supply is skewed toward.

**Five of the 23 are the exception and are worth naming**, because
`cell_allowance` is still their top column at 3.75 — `light_muted_rose` 53%,
`light_muted_purple` 44%, `dark_vivid_yellow` 42%, `light_muted_magenta` 36%,
`dark_muted_yellow` 24%. None of the five is itself at its allowance, so the rule
that fired was a **co-dominant** cell's: their carriers also carry a warm cell
sitting on 79. Those five are held down by another colour's ceiling and not by
their own.

**Nothing else moves.** Distinct palette maps go 467 → 430 against a cap of 25 that
never fires (busiest map 20 → 22). The five modes that sit exactly on their floor —
`curvature`, the three `direct_trap_*`, `itinerary` — do not move at any `K`, as
they did not in the earlier sweep; the mode mix moves by `stripe` +11, `smooth` +9,
`tia` -10 and `smooth_mean_angle` -6, and no mode goes below a floor at any arm.
Seat churn against the control is 293/380/395/401/423 of 1,000.

The two figures are `curate solve k-sweep-plot <stamp>`
([`curation.k_sweep_plot`]), scratch only: per-cell membership with the control
beside every arm, and the same as a difference against the control so a colour that
**falls** reads as a bar below zero rather than as a small one.

## What `K = 3` and a colour floor of one fair share cost together, measured 2026-09-09

`k3_floor_20260909`: one unforced n=1000 seating at the two adopted values,
`20260909T215815Z`, against two arms over the same pool — the published-shape
control `20260909T173957Z` (`K = 2`, no floor) and the sweep's `K = 3` rung with
no floor. Everything else identical; `--forced` staged and off.

| | seats | worst seat | sum | shortfall | seconds |
|---|---|---|---|---|---|
| `K = 2`, no floor (control) | 1000 | 1.503910 | 1891.212 | 0 | 100.1 |
| `K = 3`, no floor | 1000 | 1.713590 | 1939.087 | 0 | 40.9 |
| **`K = 3` + floor 20** | 1000 | 1.548138 | 1938.170 | 0 | 68.1 |

**Every one of the 48 cells reached its floor. The shortfall is zero and so is the
deadlock count.** That is the finding and it was not the expected one: the sweep's
`K = 3` arm left eight cells under 20 seats with `dark_vivid_lime` at 10 and
`dark_vivid_cyan` at 15, and the floor closed all eight without costing a seat.
Six cells sit **exactly** at 20 — `dark_vivid_lime`, `dark_muted_lime`,
`dark_vivid_cyan`, `light_vivid_cyan`, `light_vivid_azure`, `light_muted_blue` —
which is the pool being scarce there rather than the floor being slack.

**The price is the worst seat and almost nothing else.** The sum gives up **0.92
of 1938** against the un-floored arm, and the worst seated score falls
**1.713590 → 1.548138**. That is the shape the tier order predicts: a floor is
paid for in tier 3, and the seats it drags in are by construction not near the top
of anything. Against the `K = 2` control both still rise — sum +46.96, worst
+0.044.

**287 of the 1,000 seats carry a `cell_floor:` stamp**, over 30 of the 48 cells,
the busiest being `light_vivid_teal` and `light_muted_blue` at 18 each. A further
11 seats are held by the floor without having been mandated by it — placed by
another leg and dominant in a cell now sitting at its floor, so tier 2 refuses
every swap that would remove them. The scarcity leg's share of the seed goes
**300 → 520** and the ranked walk's **506 → 426**.

**The augmenting chain found nothing to do**, 194 seats gained in the control
against **0** here: the seed already filled all thousand, which it did not before.
Seat churn against the control is **398 of 1,000**, and against the un-floored
`K = 3` arm **162** — so most of the movement is the ceiling's and the floor moves
a sixth of the gallery.

**`cell_allowance` stays the largest refusal column** and falls with the ceiling:
8,662 at `K = 2`, 5,346 at `K = 3` unfloored, **4,565** here. `spiral` rises 754 →
1,266 and `twin` 423 → 662, both being rules that only get to act once the
allowance stops acting first.

### The deadlock the floor was expected to hit, and did not

A seat charges about 2.1 cells — 2.118 measured on this run, against 1.802 at
`K = 2` on the same pool the same day; the ratio is a reading and moves with both
the pool and `K` — so a row that would fill a starving cell is often
dominant in a second cell already at its allowance. Counted over the finished
state — `shortfalls.cell_floors.per_cell.<cell>.deadlocked` — it is **8,962 rows
across 47 cells**, and **not one of them is in a cell that went short**: the shape
is real and it is concentrated in the *fat* cells, led by `light_vivid_red` (1,060
rows, 778 of them refused for `dark_vivid_red`) and `light_vivid_orange` (948).
Those cells are at 63 and losing nothing they need.

Over the six cells that landed exactly on the floor it is 3, 2, 2, 6, 38 and 0
rows. What actually refuses a thin cell's rows here is `spiral` and
`the_leg_had_no_seat_left`, not another cell's allowance — `dark_vivid_lime`'s 50
clearing rows go 9 `spiral`, 7 `twin`, 6 out of seats. So the thin cells are
**carrier-bound and spiral-bound**, which is a mining instruction rather than a
ceiling one, and the `K` sweep's feasibility reading — taken against each cell's
`K = 2` deficit — did not answer the question a target of 20 asks.

## What the OWED arm costs, measured 2026-09-11

`owed_smoke_ckpt120`, 40 whole groups of the owed population, idle box, three
below-normal workers: **60 rows, 300 rotations, 1,086.3 engine seconds in 416.3 s of
wall — 18.105 engine seconds a row and 3.621 a rotation.** No field is dumped and
none is swept, so every one of the five rotations pays its own iteration pass.

**7.0x the dumpable arm's 2.579 s a row**, which is the prediction — six iteration
passes a row against one and a quarter — arriving within a rounding error of it. At
that rate the whole owed population of **1,989 rows is 36,011 engine seconds, about
3 h 50 m of wall on three workers**, against the 2 h 32 m the dumpable arm spent on
nearly five times as many rows.

### The full arm ran 34% dearer than the smoke priced it, measured 2026-09-12

`owed_ckpt121`, the same population and the same three below-normal workers, stopped
by its 14,400 s budget at **1,600 of 1,605 groups: 1,752 rows, 8,760 rotations,
42,566 engine seconds in 14,455 s of wall.** That is **24.296 engine seconds a row
and 4.859 a rotation** against the smoke's 18.105 and 3.621 — the smoke under-priced
the arm by a third, and the whole 1,989 rows is about **4 h 33 m** rather than the
3 h 50 m above. The 237 rows it did not reach are the arm's remainder.

**A 40-group smoke prices the concurrency as badly as it prices the row.** The gap
is not all in the row: the smoke ran at **2.61** engine seconds a wall second and
the full leg at **2.945**, so the smoke was simultaneously slow per row and slow to
overlap, and the two errors point opposite ways. Size an owed leg off a leg, and
where only a smoke exists, take its seconds-a-row and its concurrency as **separate**
estimates with separate error bars rather than multiplying one wall figure out.

**What the arm decides reproduced almost exactly, which is the part a smoke can
carry.** 528 adopted with the row removed, 450 adopted beside a row a guard held,
774 where phase 0 won and 0 refused by the tolerance — **55.8%** of visited rows won
by a rotation against the smoke's 56.7% over 60. So a smoke is worth running for the
verdict rate and is not worth running for the clock.

**The rotation wins a little more often here, not less**: 34 of 60 rows, **56.7%**,
against the dumpable arm's 51.7% over 9,402 — 19 adopted with the row removed, 15
held by a protection, 26 where none of the five beat phase 0, and the tolerance
refused none, as it structurally cannot. Too few rows to read as a mode effect.

The transaction resolves on this arm exactly as on the other: a dry-run merge found
all 19 named removals in the store and would upsert 34 rows over 26 locations. It was
**not** applied — merging the smoke would carve its 60 rows out of the deferred full
leg's population as already-rotated — so the leg was swept instead and holds its
record and no pictures. `curation/README.md`'s *Sweeping a leg does not un-decide it*.

## What a `color_mass` close costs a map, measured 2026-09-06

**The carried price was 253.6 s a map and the measurement is 137.8 — 1.84x high.**
The measurement wins and this row is it. Read per **MAP**, which is the whole
18-mode grid over the two-location panel;
[`MEASUREMENTS.md`](MEASUREMENTS.md)'s *Every per-candidate rate this project has
measured* is per engine render and the two are not convertible by eye.

| | 2026-08-26, carried | **2026-09-06, measured** | ratio |
|---|--:|--:|--:|
| the whole 18-mode grid | 253.6 | **137.8** | 0.54 |
| the 13 `mode_policy` accepts | 230.4 | **125.4** | 0.54 |

Population: the `classic-pairs-2026-09` drop's **120 maps**, every drawable map
with no row — 16,537 engine seconds over 5,571 s of wall at this box's three
workers, 4,320 rows, **zero failures**. The carried figure was priced off the
2026-08-26 sweep's own rows over the same panel.

**The spread by kind is material and the mean hides it, so it is kept**:

| kind | 08-26 | 09-06 | ratio |
|---|--:|--:|--:|
| the seven field modes together | 5.0 | 4.8 | **0.96** |
| the four direct traps | 48.7 | 24.2 | **0.50** |
| `threads`, `smooth_trap_circle` | 25.7 | 13.2 | **0.51** |
| the four big composites | 169.3 | 82.6 | **0.49** |
| `itinerary` | 4.6 | **13.0** | **2.86** |

Everything that iterates is about **half** what it was and every field mode is
where it was — the field modes are dominated by the colormap lookup and the
census, which did not move — so this is what a faster engine looks like from
here. **`itinerary` went the other way and by more than any mode moved down**,
which is why the split is carried rather than a single ratio.

⚠ **The two readings are not strictly commensurable.** The 09-06 figure is
per-render wall inside a three-worker pool, so contention is in it, and it is
still the smaller number. Five modes are 70% of the bill — `smooth_stripe` 23.1 s
a map, `smooth_mean_angle` 20.8, `smooth_angle_min` 20.3, `smooth_curvature`
18.5, `itinerary` 13.0 — nearly all of it at the `mandelbrot` panel location,
whose cap is 22,794 against `julia:multibrot5`'s 5,467. So a drop of maps that
lands on a different panel is not priced by this row.

[`palettes/README.md`](../palettes/README.md)'s *`color_mass` — how much of each
colour a (group, mode) pair actually makes* carries the close in full. This row
exists because the stale 253.6 survived in a second document for a day, which is
the failure this file was split out to prevent.

## What the gallery leg costs at n=150 on this machine

Measured 2026-09-01 over the 100,743-candidate pool, idle machine, `--no-render`:
**`curate solve run --n 150` is 44.6 s** — pool and view 11.2 s, the seed 24.5 s and
the swap loop 8.9 s, over a view of 6,818 rows. The five-minute figure this
paragraph used to carry was the leg before `curation.signatures` and the two swap
prunes; the table under *What it costs* is the one to read. The retired history is the
comparison worth keeping: on 2026-08-29 over a 275,822-candidate pool the exact
solve was 238 s at n=150 and **did not terminate at all** at n=1000, while the
sequential `curate seat` was 51 s at n=150 and had no objective to report.

## What a `p_fine` bar on the view buys at n=1000, measured 2026-09-07

`AUDIT_ckpt114_filtered_view_resolve_at_p_fine`. Four n=1000 seatings over the
277,542-candidate pool, `--key cascade`, `--no-render`, idle box, everything else at
the defaults. The control is the whole pool; each other arm is the whole pool
filtered to the fine head's `p_fine(>=4) >= X` before anything else runs.

**Coverage is total, which is what makes the experiment clean.** 40,127 rows clear
their mode's bar and the fine head has read **every one** — `clearing == above_bar`
set for set, every accepted mode on the `p_ge4` rule and none on the fallback — so
the filter narrows the seatable pool and opens no coverage hole. Of the 40,127:
**10,974** read >=0.50, 9,646 >=0.60, 8,271 >=0.70, 6,821 >=0.80, 4,875 >=0.90.

| run | view | after preselect | places | **filled** | seed alone |
|---|--:|--:|--:|--:|--:|
| control (unfiltered) | 277,542 | 34,272 | 9,165 | **1000** | 993 |
| >=0.50 | 10,974 | 8,845 | 5,058 | **1000** | 792 |
| >=0.60 | 9,646 | 7,725 | 4,645 | **1000** | 775 |
| >=0.70 | 8,271 | 6,605 | 4,177 | **943** | 719 |

| run | shortfall | worst | sum | `p_fine` min / median / mean | shared seats / places |
|---|--:|--:|--:|---|--:|
| control | 0 | 1.0018 | 1786.5 | 0.0018 / 0.9343 / 0.7865 | — |
| >=0.50 | 18 | 1.5039 | **1876.6** | 0.5039 / 0.9314 / 0.8766 | 581 / 649 |
| >=0.60 | 24 | 1.6012 | **1887.0** | 0.6012 / 0.9270 / 0.8870 | 554 / 628 |
| >=0.70 | 37 | 1.7008 | 1804.3 | 0.7008 / 0.9390 / 0.9134 | 511 / 586 of 943 |

⚠ **The 943 at 0.70 is a budget floor and not that pool's answer.** Its chain stage
stopped on `augment.DEFAULT_SECONDS` at **300.8 s** with sweep 2 still finding 26
chains; 0.50 and 0.60 exhausted (87.7 s and 187.2 s, final sweep 0 chains) and are
trustworthy. **0.80 and 0.90 were never run.** The defensible statement is *0.60
fills and 0.70 is open*, never a ceiling.

**The seed alone never fills, and the chain stage is what makes any of these
galleries.** That is where the whole cost went: 71.8 / 128.5 / 220.6 / 332.3 s of
wall clock across the four arms, on the leg's own clock. Those seconds are the
**audit's** and are superseded twice over — by
[`MEASUREMENTS.md`](MEASUREMENTS.md)'s *What the solve costs by stage, control and
narrowed, measured 2026-09-07*, taken on a separate profiled leg, and by that day's
two speedups. Read a cost from that table and a *ratio* from this one.

Composition across the same four runs is [`GALLERY.md`](GALLERY.md)'s *Which axes
are held up by a rule, and which are emergent*, and the two hues that collapse under
the bar are the sub-section beneath it:

| hue, % of seats | pool | control | 0.50 | 0.60 | 0.70 |
|---|--:|--:|--:|--:|--:|
| **lime** | 5.3 | **15.0** | 9.3 | 9.0 | **7.7** |
| **cyan** | 9.5 | **15.6** | 12.8 | 12.5 | **11.1** |
| red | 35.3 | 16.8 | 16.8 | 16.8 | 17.8 |
| green | 8.0 | 16.8 | 16.8 | 16.8 | 17.2 |

Every other hue holds within a point.

### The `>=0.50` row reproduced exactly a day and 11,411 rows later

`general_breadth_0908`'s counterfactual took the same seating over the same view out
of a scratch driver, and its **control** — the pool with the night's four merge stamps
held out — reads **10,974 kept, shortfall 18, worst 1.50391, sum 1876.602, median
`p_fine` 0.9314, seed 792**: the `>=0.50` row above to six figures. That is worth
knowing for its own sake, because it says the view is a deterministic function of the
pool and a counterfactual over it is a clean instrument.

With the night in, the same view reads **11,120 kept over 6,297 places against 10,974
over 6,191**, shortfall **14**, sum **1877.205**, median **0.9331**, seed **803**. So a
5.7-hour general leg moves this experiment by **+146 rows, +106 places, −4 shortfall and
+11 seats at the seed** — and the worst seat and the filled count not at all, which is
the n=1000 saturation the two overnight legs now agree on.

## What the finished collection expressed, measured 2026-09-06

**The last reading of the colour-expression census, and the reason it is here rather
than in a module.** The census counted COVERAGE(s) — the fraction of finished
full-size wallpapers in which at least a tenth of the pixels are assigned to swatch
`s`, read off the shipped render at its own resolution rather than off the candidate
behind it. Its policy half went at ckpt 112 with `stratum_score`; the measurement
went on 2026-09-06, Matt's ruling, having decided nothing since. This is the fact
about the release that went with it.

**Twenty-one cells down to one, over 645 released pictures.** The shipped thin list
was cut over 246 pictures on 2026-08-24 at a threshold of five expressing pictures.
Re-cut over the 645 released by 2026-09-06: **ENTER 0, LEAVE 20, STAY 1** — the one
being `dark_muted_lime`, at exactly 5 of 645.

* **The threshold was a count, so it tightened as the collection grew.** Five of 246
  is 2.033% and five of 645 is 0.775% — less than half as much asked of the larger
  population. Held at the shipped *rate* instead of the shipped count, **14 of the 21
  would still be thin**: seven cells left on their own merits and thirteen left
  because the denominator grew.
* **The aim worked, and that is what emptied the list.** Of the 20 cells that left,
  the two release passes aimed at thin cells supply nearly every expression —
  `dark_muted_cyan` 11 of 11, `dark_vivid_cyan` 12 of 12, `dark_muted_teal` 8 of 8,
  `light_vivid_teal` 6 of 6, all four from `gallery3` and `gallery4`, whose winners
  are on record at `data/curation/release/<pass>/`. An absolute count of five turns
  *hit it twice on purpose* into *stop aiming*, which is the shape of failure that
  ended the apparatus.
* **The budget barely moved**: mean swatches expressed **3.2033 -> 3.1566** (2.2543
  non-neutral) over 2.6x the pictures. A uniform per-swatch floor `f` over `k`
  swatches asks the average picture for `f * k`, so the largest floor that can exist
  is `mean / k` — and that ceiling did not move with the collection either.

**Two instrument readings worth keeping, because they price every future colour
measure over finished pictures.** The census read each release PNG at its own
resolution, and the two cheap alternatives were measured against that rather than
assumed. The **160x90 decode** [`palettes/codebook.py`](../palettes/codebook.py)'s
`of_picture` uses moves a swatch by at most **0.7 of a point** over the released
population and flips **12 of 12,792** threshold cells — cheap enough to substitute.
The **candidate render** is not: half the supersampling at a sixteenth of the area,
levelled off its own histogram, it moves a median of **2.1 points and up to 64**.
Which is why a recolor pass screens at candidate geometry and never *measures*
there.

**Runtime**: 645 pictures in **455 s**, 0.71 s a picture, against 246 in about 180 s.
A second run the same day read 437 s over the same population; the 455 is the one
these numbers were taken from.

## What the colour floor and the spiral cap actually bind on, measured 2026-09-10

`cell_deltas_20260910`: eleven n=1000 solves over one pool (308,885 candidates), all
through the pool-view door with an in-memory column and **no record written**. The
column is `best_head_20260910`'s `B2_raw` ensemble at its own bar **0.022689**, which
admits 11,743; the reference seating reproduces that leg's `best_arm` **seat for seat
and in the same order**, so everything below is one controlled before/after.

**The active set, and it is much smaller than the machinery suggests.** At `Kf = 1`
the floor is 20 seats a cell against an allowance of 63, and **three cells sit exactly
on it** — `dark_muted_lime`, `dark_vivid_lime`, `light_vivid_lime` — with none below.
Solved with the floor switched off, **those same three are the only cells that fall
under 20**, at **6, 12 and 13**, and the fourth-thinnest holds 22 unaided. So a leg
that stamps **256 seats** `cell_floor:` is *holding* 29 memberships in three cells:
the stamp count reads the scarcity leg's order, not the floor's worth. Meanwhile
**12 of the 48 cells sit at the allowance**, and `cell_allowance` is the largest
refusal column at 6,593 rows — on this column the ceiling is the live colour
constraint and the floor is not.

| arm | cells at floor | worst seat | sum | seats moved |
|---|---|---|---|---|
| floor 20 (shipped) | 3 | 1.052173 | 1484.765 | — |
| floor 15 (`kf = 0.75`) | 2 | 1.083438 | 1486.158 | 88 |
| floor 12 (`kf = 0.6`) | 1 | 1.101868 | 1488.309 | 108 |
| floor off (`kf = 0`) | 0 | 1.101868 | 1493.510 | 130 |
| spiral cap 0.15 | 4 | 1.064127 | 1494.777 | 113 |

**The spiral cap binds to the last seat at 0.15 as it does at 0.10**, 151 of 151
allowed and taken, and the `spiral` refusal column does not move with it — 481 → 480.
Fifty more seats went in and the same rows were still refused, because
`ceil(cap x (filled + 1))` is met at *every* seat of a scarcity-ordered walk rather
than at the end of one. **It does not relieve the thin cells**: all three lime cells
sit at exactly 20 under the looser cap, and `dark_vivid_yellow` joins them there.

### ★ A tightened constraint comes back with a BETTER answer, so a shadow price here is a suboptimality reading

One more seat demanded of each binding cell, everything else held: `dark_vivid_lime`
20 → 21 moves 48 seats for **worst −0.003173, sum +0.591**; `dark_muted_lime` moves 55
for **worst unchanged, sum +0.339**; `light_vivid_lime` moves 52 for **worst
unchanged, sum +1.426**. A superset of constraints cannot raise a true optimum, so
**two of the three dominate the shipped answer outright** and the seed-plus-1-swap is
that far from optimal at this rung. **Read it as the scatter under every objective
comparison the leg makes: about 1.4 of sum at n=1000.** The control says it is not the
instrument — raising `dark_vivid_orange`'s floor 20 → 21 on a cell holding 63 changes
**not one seat** and is bit-identical in the objective.

So the floor doses' gains (+1.393 and +3.544) sit at and just over that scatter, and
the cap's **+10.011** is the only reading here clearly outside it. The cap's own
marginal seat is **+3.315** against +6.70 for the next forty-nine between them.
