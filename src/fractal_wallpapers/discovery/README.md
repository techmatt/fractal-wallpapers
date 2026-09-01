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
