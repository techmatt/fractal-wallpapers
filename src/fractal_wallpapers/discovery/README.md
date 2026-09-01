Finding places worth rendering: seeded walks, reframing operators, and the record
they leave.

A walk descends from a seed one rung at a time. The engine does the looking —
`fractal-engine expand` draws candidate next frames from a geometric policy and
puts each through the structural gates — and this package does the deciding:
which places to expand next, when to reframe onto a nucleus, what to write down,
and when to stop.

```
pools      the tracked seed pools, and the spacing the julia one has to keep
walk       the frontier, the batch, the two reserved floors, the run loop
nucleus    Newton on a nucleus, the atom instrument, the canonical key
operators  reframing a found view onto the atoms around it
reframing  the channel that makes an operator's OWN view a candidate
ledger     one JSONL record, one schema, a fate on every row
scoring    the seam a trained head arrives through
identity   why the gate render is the picture that head was trained on
boundary   a seeded uniform draw, screened by those same gates
```

The one thing a walk does that is not in this package: when it **closes**, it
refines the framing of its best few finds, through `curation.framing` — the
gallery pass's own step 5a, reused rather than forked. See *The refine leg*
below.

Nothing here judges a picture. The gates are geometry — how much of the frame is
the set's interior, how much variety its escape times have, whether its detail is
spread over the frame or piled in a corner — and the judgement that decides
whether a location is beautiful is a seam (`scoring.py`) with a null
implementation behind it. A walk that runs on the null scorer is a complete walk:
it admits what survives the gates, and its ledger is what the first head gets
trained on, which is the only order the two can be built in.

What follows is what to read before changing anything here.

## The reframing channel: `reframe`, seeded at proven roots

**A walk never scores the frame its own operator built.** `_propose` pushes the
nucleus-centred view onto the frontier as a *node*, and only what `expand` draws
*below* a node becomes a candidate — measured on `harvest_run10`, 0 of 14,678
distinct available reframing viewports appear as a candidate viewport and 0 of
12,163 pushed node ids is a candidate's own node id. The walk then descends
straight into the atom's black body: over twelve production ledgers the 42,904
candidates below a reframing sit at a median frame multiple of **1.66 atom
sizes**, where 9,432 of their 14,109 interior-cap refusals are. That is why the
whole candidate pool holds **14** frames that are minibrot centres in the sense a
gallery wants, and why no seating has ever held more than one.

`fractal-wallpapers reframe` is the other half of the same operators. It fires
them at **seeds**, takes the view they build as a **candidate**, and writes a
walk-shaped ledger at `<out-dir>/walk.jsonl` that the supply union reads like any
other. **Nothing about the walk changes.**

```
fractal-wallpapers reframe --minutes 20 --out-dir artifacts/reframe_g1
fractal-wallpapers curate score --harvest artifacts/reframe_g1
fractal-wallpapers curate embed                    # the merge is these two, in order

# a later leg CONTINUES an earlier one rather than re-deriving its seeds
fractal-wallpapers reframe --prior artifacts/reframe_g1 --out-dir artifacts/reframe_g2   --generations 40 --minutes 480
fractal-wallpapers reframe --prior artifacts/reframe_g2 --out-dir artifacts/reframe_g3   --reprobe --seed 3 --minutes 120
```

**Merging a run into the standing pool is `curate score --harvest <dir>` and then
`curate embed`, in that order, and nothing else.** The union finds a ledger by
looking it up at `<run directory>/walk.jsonl` for every top-level name of the
regenerable tree, so a run directory *is* in the pool the moment it exists; what
the two commands add is the sidecar's read of it and one neutral-render vector per
admitted location. Measured on generation 1, 2026-08-31: the score step took under
a minute for 788 rows and left the sidecar at 91,272 rows; `curate embed` wrote
**663** vectors in 49.5 s and left the store complete over 29,083 admitted
locations with 0 missing.

**`--prior <dir>` continues an earlier run, it is not optional between legs, and
it must name EVERY earlier leg.** The atom-key dedup is per run, so a second leg
that re-derived its seeds off the label store fires the same roots at the same
atoms and writes **every one of the first leg's nuclei a second time** — one
nucleus in two ledgers, which is two location keys the moment the two legs pick
different rungs, which is one atom in two seats. The flag is repeatable and a
chain that names only the last link forgets everything before it: measured
2026-09-01, a fourth leg handed only the third's ledger wrote **192 of its 302
rows** on atoms the first leg already held. `--prior` hands the new leg the atom
keys the chain found (they seed `seen`), the proven root ids it consumed (off the
queue), every seed id it fired at, and its admitted rows as this leg's
promotions, deduplicated on the atom at the better class. Note that "consumed" is
read off the rows, so a root that produced nothing is invisible and is fired
again — which is wanted, because the seed snap's ceiling has moved since.

**`--reprobe` fires at the roots an earlier leg already spent.**
`expand_neighborhood` probes at random, so a second pass at one root is a
different sample of the same neighbourhood and reaches atoms the first missed. It
is the lever that keeps the channel yielding after the promotion queue converges,
and it does converge: generation 1 returned 496 promotions on 1,056 seeds, so each
round is roughly half the last. Give the leg its own `--seed` or it draws the same
probes.

**Seeds are `proven` roots, q3 and q4, parameter planes only, minus every eval
pin.** Off `supply.proven` rather than a second query over the label store; the
dynamical partitions are never served, because a Julia viewport is a z-plane point
with no nucleus in the parameter-plane sense. The pin is the **union over every
store that ships an evaluation side** — `labeling.pins.every_pinned`, which is the
location split plus both finished-render splits, so `blind_minibrot`'s 197 places
and `blind_modes`' are excluded as seeds *and* as derived frames. Measured
2026-08-31: 1,452 pinned places, 1,252 proven parameter-plane locations at tier
>= 3, **76 of them pinned, 1,176 seeds available** (184 q4, 992 q3).

**The rungs are 16x, 24x, 32x, 48x and 64x the atom size, and they are framings of
one location rather than five locations.** Every rung is drawn through
`engine.screen` at the node regime, every one is read through the location head,
one row is written, and its score is the rung the head picked — every rung's own
reading rides on the row under `reframing.rungs_drawn`. They are offered directly
rather than walked to: `curation.framing.WIDTH_LADDER` moves x1.414 a step and
cannot reach 64x from 16x in anything a window that size can express. The band
that reads as *a minibrot with detail around it* is 50-100 px of body at 1280,
which is the 32x rung; the walk's widest rung, 16x, lands at 115-183 px and is a
factor of two too tight, and 48x and 64x sit below the band at roughly 38-61 px
and 28-45 px. The outer two were added after generation 1's head-q4 rate rose
monotone outward over the three rungs it had — 2.1% at 16x, 2.9% at 24x, 3.5% at
32x — which left the ladder's own end the thing that had never been tested.

**Tested, on 6,590 locations over the night of 2026-09-01: the rate plateaus at
32x and the pick keeps moving outward anyway.** Head-q4 as a share of what was
drawn at each rung reads **2.0 / 5.0 / 7.3 / 7.1 / 7.6%** at 16 / 24 / 32 / 48 /
64x — 48x and 64x are inside a rounding of 32x rather than above it, so
generation 1's monotone read was the ladder ending too early and not a trend. But
the outer two take **596 of the 1,305 q4 picks (46%)**, and the median chosen
frame is 32 atom sizes with quartiles at 24 and 48, so the ladder is used across
its whole width. Both outer rungs draw about 790 fewer frames than the inner
three: a wider frame trips `width_over_root_scale` on the largest atoms. What
none of this settles is whether a 64x frame is a better *minibrot* picture or
merely one the head likes; that is what the `reframe_nuclei` sheet is cut for.

**A nucleus location is `centered`, and the field is a contract with
`curation.framing`.** The centre is the atom the operators solved for and it is
the whole of what the location is, so a framing refinement over one of these rows
may move the **scale** and nothing else: `curation.framing.recentres` returns
nothing for a centered row and `refine` plans no stage-B frames for one, three
frames a location instead of seven. The flag is read off the row rather than off
the channel name, so a hand-placed nucleus frame carries it for the same reason.

**These places were once out of reach of the curation pool, and since 2026-09-01
they are not.** `curation.hunt.drawable` — the population `curate hunt`,
`curate mine` and `curate depth` all take — used to drop a location the pool-wide
refinement scan held no row for, and the scan holds none for any of these: it
predates the channel, and a centered row wants no scan row anyway, because its
frame is the rung the head already picked. The population is now bounded by the
location ledger's ratings alone and a framing is an attribute rather than an
admission ticket, so the channel's **7,686** never-opened places are in the
ordinary pool and draw at the frame they already carry. `reframe_q4` (below) is
the location-list draw that was needed before that; see
`curation/README.md`'s *What bounds the minable population*.

**Drawn as wallpapers, the q4 slice clears at nine times the breadth rate, and the
rung question comes back with an answer.** `reframe_q4` (2026-09-01) spent an hour
of the standard per-location draw over the head-q4 nuclei surviving
`PRESELECT_RADIUS`, top-down: **2,286 candidates over 762 of the 1,252 places**,
15.62% clearing raw `P(>=4) >= 0.50` against a fresh breadth draw's 1.72% at the
same cost a candidate, and 38.1% of places producing at least one such row. Per the
rung the head picked:

| rung | 16x | 24x | 32x | 48x | 64x |
|---|---|---|---|---|---|
| places drawn | 61 | 122 | 216 | 157 | 206 |
| candidates clearing q4 | 9.3% | 14.2% | **18.7%** | 17.0% | 14.1% |
| places with a q4 row | 25% | 34% | **45%** | 44% | 33% |

**The render judge peaks at 32x and falls away at 64x**, where the location head's
own pick rate merely plateaued — so the outer rungs are, on this evidence, frames
the location head likes more than the wallpaper judge does. It is an observation
and not a controlled comparison: the rung on each row is the one the head *chose*
for that place, so a rung column is partly a column about which places chose it.
The `reframe_nuclei` sheet is still what settles it against a person's verdict.

**The seed snap scans to period 256**, over `operators.MAX_PERIOD`'s 64.
Measured on 60 generation-1 seeds: 64 found 24 nuclei in 5.1 s, 128 found 30 in
8.6 s, 256 found **35 in 17.7 s** — a 58% hit rate against 40% at 3.5x the Newton
cost. It is the right trade here and the wrong one in the walk, because the snap
is a tenth of this channel's operator clock and seeds are the scarce thing.

**The seed queue has four classes and every row says which one it came from**:
`matt_q4`, `matt_q3`, `head_q4`, `head_keeper`, in that order. A human verdict
outranks the head's because it is the thing being inherited, and inside the human
half q4 outranks q3 on measurement — over generation 1's 1,056 consumed seeds a q4
root returned a head-q4 at **11.4%** against a q3 root's **4.2%**, so a q4 seed is
worth 2.7 of the others. Both promotion classes fire: generation 1 found 58 nuclei
over the q4 bar and 496 over the keeper floor, and a loop that promoted only the
first runs its queue dry inside an hour of an overnight leg.

**`operators.snap_at_seed` is the ported operator.** The maker's set was
`snap_at_seed`, `snap_to_nucleus`, `neighborhood_expand`; this repository had the
second (`snap_to_nucleus`) and the third under the name `expand_neighborhood`, and
was missing the first. It is `snap_to_nucleus` at `SNAP_AT_SEED_MAX_WIDTH_MULTIPLE
= 0.75` — the source project's `snap_max_fw_mult` — with a refusal of its own
name, `nucleus_outside_seed_view`, because a judged view is a claim about a
picture and a nucleus a whole frame width off centre was not in it.
`snap_to_nucleus` itself is **not** fired at seeds: at a seed it is `snap_at_seed`
with the looser radius, so firing both would return one atom under two names for
every seed the tighter one accepts and buy only the annulus between 0.75 and 1.0
frame widths, at a second full Newton pass. The maker did not fire it at seeds
either — its `snap_to_nucleus` rows are all walk-triggered.

**A crashed `engine.screen` batch costs its frames, not the leg.** One engine
process died two minutes into an eight-hour leg on 2026-08-31 — nonzero with
empty stdout *and* stderr, a hard crash rather than a refusal it could describe —
and took the leg with it. A batch is retried `SCREEN_RETRIES` times and then
given up on, its nuclei counted as `nucleus_not_drawn` and left in `seen`. An
unattended leg that stops on one frame has spent the night, which is worse than
sixty-four missing rows. A supervisor over these legs must tell a **nonzero exit**
(a crash, retry it) from a **clean exit with few rows** (the queue is done).

**It is operator-bound, not render-bound, so the three-worker render pool does not
apply.** One `engine.screen` process at a time, below-normal by construction, the
same shape `curation.framing`'s refine leg has. On the generation-1 smoke the
operators were 53% of the leg's clock and the neighbourhood enumeration was the
expensive half of that: **`expand_neighborhood` cost 17x what `snap_at_seed` cost
per nucleus** (4.6 s against 0.27 s on the pilot), because most of its probes hand
back the parent atom. Over the whole of 2026-09-01's night the operators were
**92%** of the leg (26,742 s of 29,014 s) and the split was starker still:
`expand_neighborhood` **15,541 s for 5,974 locations at 2.60 s each and 1,316,304
Newton solves**, against `snap_at_seed`'s **61 s for 616 locations at 0.10 s
each** — 99.6% of the operator clock for 91% of the locations.

**Generations, and why a round is not a generation.** A nucleus the head scores at
or above the q4 admission bar — `supply.currency`'s keeper floor on `P(>=3)` *and*
its great cut on `P(>=4)`, never a third reading of the two — becomes a `head_q4`
seed for the next generation; one that merely clears the keeper floor becomes a
`head_keeper` seed behind it. A row's **generation** is its seed's plus one and is
on the row. The loop's `--generations` bounds *rounds*, and a round is not a
generation once `--prior` is in play: an earlier leg's promotions enter the first
round's queue beside whatever is left of the label store, so one round writes rows
of two generations. The summary spells the loop's entries `rounds` for that reason
and carries a `by_generation` block beside them.

**The head-q4 rate does not decay with generation — it rises.** Over 28
generations on the night of 2026-09-01 it went 14.0% at generation 1 to 21.3% at
3, 25.6% at 5 and 32.0% at 16, and each generation is a fresh promotion set off
the one before rather than one surviving lineage. Read it as the head agreeing
with itself about what it liked one step ago rather than as the channel getting
better, and price it on a person's verdicts before believing it. The other half
of the same measurement: a `head_q4` seed returns q4 at **42.5%** against a
`matt_q4` seed's **41.3%**, and a `head_keeper` seed matches a `matt_q3` seed at
**17.3%** exactly, so one generation on the head's class buys what the person's
class buys.

**A leg exits when its queue empties, and that is completion.** Both full legs of
that night ran their queues out before their clocks — 3h22m and 2h48m — which is
why an overnight is a *chain* of legs under one supervisor rather than one long
`--minutes`.

**Record and rank, never gate.** Every derived nucleus is scored and written
whatever the head said. Neutral pre-selection distinctness (`curation.distinct`,
`PRESELECT_RADIUS`) is applied where a **sheet** is cut, through
`reframing.distinct_places`, and never to the ledger — so a sitting never sees
fifty lookalikes off one seed and the record still says what the channel found.
Note that the neutral store is built from the *admitted* supply sidecar, so places
this leg finds have no descriptor until `curate score` and `curate embed` have run
over its ledger.

## The refine leg: `--refine-per-walk`, at close, top-k

A walk stops on a frame because the gates let it through and the head liked it,
not because that is the best crop of what is there. So when the walk closes it
takes its best `k` gate survivors — `--refine-per-walk`, default **3** — and
scans a small window of framings around each: width `x{0.707, 1.0, 1.414}` at the
current centre, then at the best of those a recentring of `+-0.25` frame one axis
at a time. Seven frames a location, drawn through `engine.screen` at the node
regime, read through the shipped location head, and the best **adopted only if it
beats the recorded framing by `--refine-margin`** — a strict improvement in nats
of log-odds on `P(>=4)`, never an argmax. Monotonicity is asserted and a violation
raises.

**It is the gallery pass's step 5a, at the other end of the pipeline and through
the same code.** One window, one margin, one gate requirement, one provenance
shape; `curation/framing.py` owns all of them and neither site restates any. What
differs is only *which* frames are scanned — a pass scans the neighbourhoods it is
about to colour, a walk scans the handful it is most likely to have found — and
that is why the leg is bought once per run rather than once per admission.

**Best is the seating statistic**: `logit P(>=4)`, `P(>=3)` breaking the tie,
which is the order a gallery slot is filled in. A full tie falls to the order the
ledger wrote, so one seed refines the same frames twice. Three is the archive's
own number: the maker reframed each walk's top `KRAW = 3` and took the walk's
reward as the max over them.

**Nothing feeds back into the walk.** No priority moves, no score term is re-read,
no descent is re-taken. `--refine-per-walk 0` is the walk this repository ran
before the leg existed, exactly.

### A written row is never edited, so the refinement is a later row

The walk's shape leaves nowhere earlier to put it: *the best three frames of this
walk* is not knowable until the walk has finished, and a ledger is append-only. So
the leg appends a `refined` row per scanned location after the candidates, and
**the reader prefers it** — `supply.ledgers.admitted` joins it onto the candidate
row and hands on the refined frame, the refined cap, the refined score and the
fate that score earns. The candidate row on disk is byte-for-byte what was
written. A window that did **not** clear the margin still gets a row: what the
margin refused is the evidence the margin is set where it should be, and such a
row changes nothing about the location it is about.

**Admission reads the refined score**, so a row the scan lifts over the keeper
floor is admitted at its refined viewport and — only where it *crosses*, never
where it was admitted already — gets the triggered operators any admission gets.
Those fire at the refined centre onto the frontier the run is **closing with**, so
this walk expands none of them and the checkpoint is already written: they are a
record of what the operator found, not a feed into a descent.

**The location key moves with the frame**, and that is deliberate. A key is the
family and the viewport, so a refined row is a different location — which is this
package's existing stance, stated where the operators dedup: *the framing is part
of the identity, and the same atom at two framings is two views*. It is the
opposite of what the gallery pass does, and the two are not in conflict: a pass
refines a location the pool **already holds** at its recorded frame and has to pin
identity so one place cannot take two seats, while a walk refines a frame nothing
downstream has seen yet. The frame the walk stood on is kept on the row under
`framing.original` either way.

**Priced in its own bucket.** `_charge("refine_framing", seconds)` puts it beside
the reframing operators in `harvest._operator_report`, and the harvest tally
carries `refine_minutes` as a **third** bucket rather than a share of
`reframe_minutes` — the operators fire per batch off admissions and this fires
once per run off the whole walk, so folding it in would make the operator suite
look more expensive on exactly the runs that refined most.

**Reading a walk's own gate render against a fresh one.** The gallery pass found
its scan disagreeing with the supply sidecar by up to 0.029 on `P(>=4)` and could
not say why: 19 of its 20 locations had been scored off a walk's gate render, and
that picture is not on the view-cache path. Here it is — this run drew it — so
every scanned location's `refined` row carries `gate_render`: both pictures'
sha256, both byte counts, both readings and their difference. It is a measurement
and nothing acts on it.

**Reframing operators are triggered, never a source.** They apply to a place the
walk already found and admitted, and they inherit both its provenance and its
budget. Every source that enumerated minibrots from first principles was measured
and found dead; what a minibrot is good for is being a *marker* of a dense
neighbourhood, at a scale the search can compute before rendering anything.

**That verdict is about one enumerator at one scale, and there is a counter-fact
worth carrying beside it.** The measurement that closed it is the source
project's `minibrot_roster_v2` — 487 human-blind labels on screen-selected,
G-framed windows at **one scale per atom**, class-4 yield 2, both windows of one
atom. Its own file records the correction that scale was never varied. Against
that, `data/smooth_render/rows/blind_minibrot.jsonl` — 197 rows, `eval_only`,
unanchored, drawn from **maneuver views taken directly as locations** — came back
**96 fours, 95 threes, 6 twos: 48.7% q4**, against 3.1% for `fresh_pool_draw` and
0% for `pool_draw_bootstrap` on the same store. Minibrot *supply* has been
measured to work; minibrot *auto-framed windows at one scale* have been measured
not to. They are different claims.

**`snap_to_nucleus` is the outward framing ladder**, and it is the operator that
turns that marker into views. It recenters on the nucleus the view's centre sits
on — one probe, one Newton pass — and emits a `Reframing` per rung of
`operators.FRAMINGS`: `None` (keep the view's own width), then **4×** and **16×**
the atom's own size. Outward and never inward, deliberately: framing *into* an
atom is solid black, so there is no small rung. `4` is the "is this atom any
good?" frame, the smallest that is not mostly the atom's own body; `16` is the
one worth **labeling**, often close to a usable wallpaper by itself, which is the
material the corpus wants. The verdict is per rung off one solve — a shallow atom
can take 4× and be refused 16× — and nothing is reframed wider than
`MAX_WIDTH` (3.0), a whole-set view, because wider than that is a different
search rather than a reframing of this neighbourhood.

**A reframing's own frame is never a candidate, and that is the shape of the
whole operator suite.** `_propose` pushes the nucleus-centred view onto the
frontier as a *node*; only what `expand` draws **below** a node becomes a
candidate, and curation reads candidate rows alone
(`supply.ledgers.passes_gates`). Measured in `harvest_run10`: **0 of 14,678
distinct available reframing viewports appear as a candidate viewport, and 0 of
12,163 pushed node ids is a candidate's own node id.** So the picture the
operator constructs is a place to stand and never a place to ship — it cannot be
scored, labelled, coloured or released — which is a design fact worth stating
because every count of "what the operators bought" is a count of their
*descendants*.

**And the descendants are inside the atom.** `Policy.zoom` is `(0.35, 0.50)`, so
a 16× frame's children land at 5.6–8× atom sizes and its grandchildren at 2–4×.
Over twelve production ledgers the 42,904 candidates descended from a reframing
have a **median frame multiple of 1.66 atom sizes**, 59% of them below 2×, and
that is where 9,432 of their 14,109 `interior_cap` refusals sit.

**How wide a nucleus reads, per rung, measured.** Eleven ring-seeded atoms at a
1280 px frame — which is both label geometry and `release.RELEASE_REGIME`; halve
it for the head's own 640 px view:

```text
framing        2x       4x       8x      16x      32x      64x     128x
body px      ~1050  460-740  230-370  115-183   57-92    28-45    14-22
interior   .50-.75  .16-.24  .04-.06  .01-.02    ~.003    ~.001    ~.000
```

The 2× frame is half interior or more and is refused by `Gates.interior_cap`
(0.30), which is the arithmetic behind "there is no small rung". The top rung,
16×, puts the body at 115–183 px. `scratch/AUDIT_minibrot_pipeline_report.md`
(2026-08-31) argues that a *minibrot as a subject with detail around it* is the
50–100 px band, which is a **32× rung this ladder does not have**.

**And curation's refinement scan cannot supply it.** `curation.framing`'s window
is half an octave either side — it has adopted 19,041 of its 28,090 scans at
Δ = 2.0, and moved outward on 161 of the 809 nucleus-centred places it saw, but
always at ×1.414. A frame two rungs too tight for its subject stays two rungs too
tight, so the rung has to be right when the operator emits it.

**What the probe costs, measured.** A harvest charges `expand` and
`trigger_reframings` as one number, so the ledger cannot break the operators out.
Replaying every firing of a one-active-hour scored run against the four parameter
planes — 1,379 firings at the default `--probe 0.25` — prices them:

```text
                       s/firing   median      p90   share of active clock   s/admission
expand_neighborhood       0.623    0.074     1.87                   23.9%          2.93
lateral_to_sibling        0.204    0.068     0.54                    7.8%         56.15
snap_to_nucleus           0.101    0.046     0.19                    3.9%          0.96
untriggered descent           —        —        —                   64.5%          0.81
```

Three things that table settles. **The probe is a third of a harvest's active
clock** at the default firing rate, and neighborhood alone is a quarter of it.
**The cost is a tail, not a level** — neighborhood's median firing is 0.074 s and
its worst was 8.2 s, so a mean is the only honest summary. And **the operators buy
admissions at three to four times what ordinary descent pays**, which is the trade
the reserved floor exists to justify rather than to hide: what they produce is
material nothing has been trained on.

There is no need to take the timer's word for it. Each operator's cost divided by
the `newton_solves` its own ledger rows recorded lands on one constant — 8.6, 10.7
and 11.6 ms per solve — so the solve counts alone reproduce the same shares.

**Neighborhood is on in production at that price, and the table is the reason it
is a decision rather than a default.** A quarter of the active clock buys views
of a kind nothing has been trained on, which is what the frontier's reserved
operator slot exists to make; `--no-neighborhood` is the per-run opt-out and
there is no cheaper operator that produces the same material. `--neighborhood`
and `--no-neighborhood` are one **tri-state** and both default to saying nothing:
the shipped default lives on `walk.Reframings`, so a flag nobody passed cannot
overrule it and moving the default is one edit rather than two.

**What the table paid for that was pure waste has been removed.** The parent atom
— which atom is this view on — is a deterministic function of the view, and all
three operators start from it, but each disc operator used to solve for its own.
Behind a snap that *missed*, which was 954 of the 1,379 firings, both then paid a
full Newton pass to be told the same "no". One firing now resolves it once
(`operators.ParentAtom`) and the rest read it, refusal included. Replayed over the
same 240 firings, before against after, with the proposals compared row for row:

```text
                       s/firing          median firing        Newton solves
lateral_to_sibling     0.231 -> 0.142    0.072 s -> 30 us      4,841 -> 3,371
expand_neighborhood    0.734 -> 0.646    0.084 s ->  1 us     17,824 -> 16,354
whole firing           1.078 -> 0.899   (-16.6%)
```

**Zero proposal differences over the whole replay** — same rows, same order, same
refusals, same atoms. Read the ratios, not the levels: this replay times both arms
interleaved and draws its probe seeds per operator, so its "before" column sits
above the priced table's own figures for the same work. Scaled onto the priced
run, the three operators fall from 35.5% of the active clock to about 29.6%, and
`lateral_to_sibling` from 7.8% to 4.8%. The median firing is where to look: a
no-parent firing used to cost each disc operator a full solve pass and now costs
neither anything at all.

**Do not try to price this with a short A/B leg.** Batch-to-batch variance in
expansion cost runs ±23% over runs of dozens of batches, so a three-batch run with
the operator off and one with it on differ by less than the noise — measured, they
came out 0.511 against 0.520 active minutes, where the effect being looked for was
a tenth of that. Cost is also flat-to-falling in trigger depth, so a short leg is
not cheap for the reason it looks like it should be.

**Where a root starts is not decided here.** A root given no view comes home to
its family's frame, and that frame is the engine's — `fractal-engine home-view`,
read through `engine.home_view`. This package holds no framing literal, and the
guard for that is in `tests/test_home_views.py`. It held one once, `{0, 0, 3.0}`,
which agreed with the engine until the engine's Phoenix row moved: after that a
phoenix root framed 66% of its own set with both lobes cut, and nothing in either
half could have noticed.

**Three partitions have no pool here at all, and are harvest-only.**
`julia:multibrot3`, `julia:multibrot4` and `julia:multibrot5` have no tracked
`c`-pool and no back-catalogue to draw one from — the two pools in
`data/discovery/` are degree 2 and Phoenix, and nothing in a walk crosses a
family. Their roots are **manufactured per run** by
[`fractal_wallpapers.supply.twins`], which takes the centre of an admitted
degree-`d` parameter-plane location as a `c` for the degree-`d` Julia family,
skipping any parameter inside the pool's own c-spacing floor of one already taken.
That is a supply-engine channel, so `fractal-wallpapers walk` cannot reach these
three: a harvest is where they get roots, and a run that never serves their parent
plane never serves them either.

**A seed pool cannot ask for anywhere else.** `JuliaSeed` carries a `c` and
`PhoenixSeed` a `(c, p, z₋₁)`; both are *parameters*, so every dynamical root
either pool hands over comes home — the whole plane at width 3.0, the classic
Ushiki extent at 5.0 — and the walk descends to anything worth seeing from
there. The one dynamical supply that names a frame is
[`fractal_wallpapers.supply.proven`], which hands over the viewport a human
scored and reaches `add_root`'s `view` with it.

**A walk scores the picture it already made, and no longer renders a second
one.** `expand` draws every gate survivor at 384x216, one field sample per pixel,
and that frame is byte-identical to the same location's cached tile at the same
regime — one of the three the shipped location head was trained over. So the head
is handed the gate render. What that removed was the *dominant* line of a run's
clock: the deploy-geometry steering view was 8,810 s of one three-hour production
leg, 58.7% of the whole run's clean wall, and nothing but the scorer ever read its
pixels.

**The identity is enforced, not coincidental.** It rests on five things, none of
which announces itself when it moves: the run's `--colormap` is the tile pool's
floor palette, that map is **cyclic**, `--node-width` is the node regime's frame,
the engine's iteration cap still matches the cap the tile corpus recorded, and —
the one the other four cannot see — the **engine build itself**.
The cyclic requirement is about the *deploy view* rather than the tile: the tile
build and the walk's own `expand` both load a colormap unbaked, so neither ever
folds one, but `location_view` bakes `mirror` into any map that does not wrap —
so a non-cyclic walk colormap would leave the head's node-regime picture and its
deploy-geometry picture of one place two different pictures. It is refused rather
than folded.

The first four are checked before a run writes its first row, and each refuses
with the flag to change; the engine also states the geometry it drew every batch
at, and a report that disagrees ends the run. The cap is *asked* through
`fractal-engine maxiter` rather than restated here, for the same reason the home
table is.

**The build is recorded rather than compared, and the refusal it buys is on the
read side.** There is nothing to compare it against at run start — the gate
renders this run is about to make are made by this engine by construction — so
`identity.enforce` puts `engine` on the run header and every view the run writes
carries the same mark in a `drawn_by.jsonl` beside it. The build is named by what
it draws (`fractal_wallpapers.engine_fingerprint`: six pinned probes over four
family kinds and six modes, digested to sixteen hex characters, ~0.35 s and
cached per process), because byte-identity of output is already this engine's
contract and a digest of output also catches a rebuild from unchanged source and
a moved mode catalog, which a revision would not. What that record is *for* is
`curate score` and `curate redraw`: a cached view or a past run's gate render
that no stamp claims is `unknown`, which is not a fingerprint, so it is
re-rendered rather than scored. A picture outlives the run that drew it, and
until this existed nothing could tell one build's picture from another's.

**With the views gone, the rest of a rung's clock is the focus finder.** Inside
`expand` the escape-time iteration is the *smaller* half: the focus finder —
twenty smoothing passes over the node field, no iteration in it at all — was 47%
of expansion before it was read once per node instead of once per draw, and is now
the first place to look when a walk is slow.

**Once a run, the claim is measured rather than only checked.** A seeded sample of
about a hundred survivors is scored a second time at the deploy geometry and the
two verdicts are compared at the three acting gates. The count lands in the run
summary as one line and **nothing acts on it** — the pre-registered bars in
`models/regime_flips.py` are where a decision about this head gets made.

**Every candidate is recorded, with the gate that refused it.** A walk that
logged only its survivors could never afterwards tell "the gates were too tight"
from "there was nothing there", and both look like a low yield. A gate survivor
then carries one of three **fates**, and the ledger's word for each is the word
the books use: `admitted` is on the frontier *and* in the books, `expandable` is
on the frontier and in no book, `not_admitted` is neither — recorded, and not
walked from. A row also records the regime and the picture its score was read
off (`score_regime`, `score_view`), because the head reads three geometries and a
score that cannot say which one it came from is a number about nothing.

**The pictures a score was read off are two trees, and only one of them still
grows.** `artifacts/location_views/` is the deploy geometry — the cache walks
filled before they scored their own gate renders, and what the sidecar, the flip
study and the restatement all read. It is a read-only record, and since
2026-08-22 that holds for **old stock's first read too**: `curate score` reads a
row that states no regime at the node one rather than falling to the deploy
geometry, so scoring three pre-regime ledgers whole wrote 1.48 GB into
`artifacts/node_views/384x216ss1/` and not one file into the frozen tree. The one
command that still renders into it is the regime-flip study, whose canonical arm
reads production's own pictures on purpose.

**Standing on a place and booking it are two decisions, at two heights.** The
scorer is asked twice about every gate survivor: *may the walk continue from
here?* at the junk floor, and *is this a find worth counting?* at the good floor.
One cut used to answer both, which meant a place too ordinary to keep was also a
place the walk could not stand on — and a frontier fed only by its own admissions
shrinks whenever the pass rate falls below one over the branching factor. The
middle tier carries its own fate (`expandable`), so it reaches the frontier and
no book in the project can see it.

**A lineage may be capped on what it books, and off by default it is not.**
`Limits.lineage_admissions` is the ceiling on admissions from one root; past it
the lineage stops expanding and its standing frontier nodes are evicted at the
crossing, recorded as a `lineage_capped` row. It is `None` here and set by the
[deep run mode](../deep/README.md), where the measurement that motivated it was
taken: 741 admissions off 15 of 48 roots, 85 on one, and a finished frame set that
was largely one composition. Nothing is retro-refused when it fires — the rows a
capped lineage already wrote keep the fates they earned.

**A parameter-plane root starts above its own material, so its first rungs are
ungated.** Labelled class-3/4 plane locations sit at width 1e-4 to 1e-5, four or
five rungs below where a plane seed root begins, and the head scores the shallow
end near zero — so every rung was refused at the junk floor and plane nodes
reached the frontier at a measured 1.2%. The first `--plane-grace-rungs` rungs
below a plane-seed root are exempt from that floor and the floor resumes below
them. Booking is untouched at every rung, dynamical roots are untouched
altogether, and every gate survivor under a plane root records its rung and its
raw junk-floor verdict — which is the survival-by-rung table a depth-aware floor
would have to be shaped from.

**Below `min_width` is another mode, not a lower floor here.** The walk's
`1e-9` stays where it is. What is under it —
[the deep run mode](../deep/README.md) — reuses this package's engine door,
gates, ledger and scorer, and changes only where it stands: its roots are nuclei
produced by high-precision Newton rather than seeds, so its first frame is
already below this floor. It is a separate mode because reaching depth by
lowering this one spends the whole budget on the space between atoms, which is
the finding that parked the idea in the first place.

**The gates are reachable without proposing anything.** `expand` runs the
structural battery on frames *it* drew, so for a long time the only way to ask
what the filter made of a frame somebody named was to go looking for it in a
ledger. `fractal-wallpapers screen` points the same battery at a location record
and reports, per gate, what it read and what it read that against — and the ones a
refusal came before report nothing, because they did not run. It is not a second
copy: `screen.rs` owns one `Battery` and both callers spend it, held to that by
`a_named_frame_gets_the_same_fate_the_walk_gave_it` in the crate.

Checked against the live `harvest_run9` ledger: of 40 candidates whose recorded
fate is a gate, `screen` reproduced **40**. The 20 rows carrying a *scorer* fate
(`expandable`, `not_admitted`) passed every gate by definition and come back
`survived` — except six, which are first-rung candidates. **A walk waives the
occupancy floor at its first rung**, where it over-fires on a root frame still
resolving structure the tighter child has not entered yet, so screening one
against three gates reports a refusal its run never made. `--waive-occupancy` is
that waiver, and with it all 20 come back `survived`.

```
fractal-wallpapers screen --location row.json
fractal-wallpapers screen --manifest rows.jsonl --out-dir artifacts/screen/frames
fractal-wallpapers screen --manifest first_rung.jsonl --waive-occupancy
```

**A random draw plus those gates is a boundary sampler.** A frame that clears all
three is not mostly set, not far exterior and has its detail spread over it —
which is what being on the boundary *is*, so there is nothing else to find it
with. `sample-boundary` draws uniformly inside a family's home frame at a
log-uniform width, screens each draw, and records every attempt with the gate that
refused it. Measured over the c-plane at widths 1e-3 to 1e-1: **1.4% of uniform
draws clear every gate** — 13 survivors in 832 attempts, 31 seconds — and the
refusals are 81% `flat`, 17% `interior_cap`, under 1% `occupancy_floor`.

**It draws from 90% of the home frame, and `boundary.home_box` is the only place
in this project that shrinks it.** The box is the family's own home view — read
through `engine.home_view`, because this side keeps no framing literal — with each
axis scaled by `boundary.HOME_SHARE` (0.9) and the height taken at 16:9 off the
shrunken width. The reason is that the home framing carries a margin of empty
plane around the set **on purpose** (the engine contains the measured set at 16:9
with a tenth of its deciding extent in margin), so a draw spending attempts out
there would be measuring the margin rather than the set. It is a property of
*this sampler* and not of the home table: everything else in the project — a walk
root, a render with no viewport — takes the engine's frame whole.

It writes two files, because one could not be both: `draws.jsonl` is the record
(a run header, one row per attempt, a summary) and `kept.jsonl` is a plain
location manifest that feeds straight into `render --manifest` or
`score-locations`.

```
fractal-wallpapers sample-boundary --keep 12 --attempts 1024 --seed 1
```

**A node's foci are recorded only if asked.** The focus set — the peaks of the
smoothed escape field a rung is aiming at — is read once per node either way, and
`ExpandReport` kept only the chosen target's score. `--foci`, on both `walk` and
`harvest`, adds one `foci` ledger row per expanded node carrying every kept peak:
its position in pixels and in the plane, the blurring scales that detected it, its
isolation, and the distance to the nearest kept neighbour. Off by default and
**every candidate row is byte-identical either way** — the reading consumes
nothing from the node's random stream, so a run with it on descends into exactly
the same places. It costs about one row per four candidate rows — measured over a
one-hour scored harvest, 2,219 `foci` rows against 8,876 candidates, which is that
ratio to two figures. Those rows carried 28,878 peaks found and 13,663 kept, about
six kept per row.

```
fractal-wallpapers walk --family julia --roots 20 --batches 8
fractal-wallpapers walk --seeds my_locations.jsonl --no-neighborhood
fractal-wallpapers walk --seeds my_locations.jsonl --plane-grace-rungs 0
```
