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
parabolic  where a component touches its neighbour, and a ring of julia c around it
minibrot   is there a minibrot in this frame, and how big is it against the frame
operators  reframing a found view onto the atoms around it
reframing  the channel that makes an operator's OWN view a candidate
ledger     one JSONL record, one schema, a fate on every row
scoring    the seam a trained head arrives through
identity   why the gate render is the picture that head was trained on
boundary   a seeded uniform draw, screened by those same gates
viewport_sampler  the same idea as a root channel: a ladder on the pinned plane, a boundary refinement on a parameter plane
```

Nothing here judges a picture: the gates are geometry, and the judgement is a seam
(`scoring.py`) with a null scorer behind it. Module docstrings hold the mechanics.

## Which of the three commands to reach for

| command | what it needs to start | what it is for |
| --- | --- | --- |
| `walk` | the tracked seed pools for a dynamical family; on a parameter plane an explicit `--seeds` file, `--root-channel viewport_sampler --roots N`, or both | one descent, keeping what survives the structural gates |
| `reframe` | locations a **human** already scored a keeper | the operators' own nucleus-centred views, which a walk builds and never scores |
| `harvest` | nothing beyond the seed pools — it divides its clock by how far each partition sits below its share of the release | the production loop, and the one command for **cold exploration**: `harvest --partition FAMILY --minutes N` |

A harvest **is** a walk with an economics layer, and `reframe` fires the walk's
operators from outside. On a machine with no tiles built, add `--no-scoring` and run
`curate score --harvest <out-dir>` afterwards, the same two-step `reframe` uses.

```
fractal-wallpapers walk --seeds my_locations.jsonl --no-neighborhood --plane-grace-rungs 0
```

## The reframing channel: `reframe`, seeded at proven roots

A walk pushes an operator's nucleus-centred view as a frontier *node*, never a
candidate, and descends into the atom's black body below it. `fractal-wallpapers
reframe` fires the operators at **seeds** and takes the view they build as a
**candidate**, writing a walk-shaped `<out-dir>/walk.jsonl` the supply union reads
like any other. `reframing.py`'s docstring has the rulings and the ladder in full.

```
fractal-wallpapers reframe --minutes 20 --out-dir artifacts/<leg>
fractal-wallpapers curate score --harvest artifacts/<leg>
fractal-wallpapers curate embed                    # the merge is these two, in order
fractal-wallpapers reframe --out-dir artifacts/<leg> --generations 40 --minutes 480 --seed 3
```

**Merging a run into the standing pool is `curate score --harvest <dir>` and then
`curate embed`, in that order, and nothing else.** ⚠ Nothing runs it for you, and an
unmerged leg looks exactly like one that found nothing: `curate score --ledger
<run>/walk.jsonl --unscored --limit 0` reports `outstanding` against `bound` in
seconds, 0 for a merged leg. Check it at the end of every leg.

A row's `image` names collide within a leg and nothing reads them (scoring re-renders
every row); re-draw a leg's frames from each row's `viewport` and `maxiter`.

**`--prior` defaults to every earlier leg the ledgers hold** (found by the
`kind: "reframing_run"` header, never by name; both tiers when the archive is mounted).
The atom-key dedup is per run, so a leg not handed the chain writes one atom into two
seats. A list that omits a leg warns; `--no-prior` starts a chain.

**`--reprobe` defaults to a reading of the chain**, recorded under `reprobe_because`:
it re-fires spent roots (`expand_neighborhood` probes at random, so a second pass is a
new sample) when the chain is **exhausted** (no seed left) or **saturated** (the latest
leg consumed at least `SATURATION_FLOOR` seeds and already held `SATURATED`, 90%, of
the nuclei its operators reached; `counts.nucleus_already_found`). Give the leg its own
`--seed`; `--no-reprobe`/`--reprobe` override. **After `supply.proven` widens, the
saturation reading is stale until one leg has fired at what it added.**

### A root that was fired and got nothing

Every seed fired gets a `reframing_fire` row, written per seed-batch, invisible to the
supply union. Outcomes are `productive`, `barren`, `no_converge` (Newton or the period
scan failed, `reframing.UNRESOLVED`), `not_drawn` (the screen batch crashed twice) and
`undefined`. **Only `barren` consumes a root**, and consumed is relative to the ladder
(operators, rung span, period ceiling, read off the header by `reframing.ladder_of`):

- an unresolved root is **held** while `--seed-max-period` stands
  (`reframing.unsettled_under`), re-offered when it rises;
- `reframing.covers` re-opens a barren root only for a ladder that reaches further;
- a plain continuation allows one barren fire per `(root, ladder)`, `--reprobe` two;
- re-offered roots fire last (`reframing.queued`): unfired `matt_q4`, `matt_q3`,
  `head_q4`, `head_keeper`, then the re-offered in the same order.

The summary's `fires` and the seed query's `ladder_rule` read these through
`reframing.refusal`, the one place the queue's rules live. Compare `seeds_available`
with `seeds_consumed` before reading a leg's split as a fact about the supply. **The
eval pin acts at three places**: the seed query, the carry of earlier promotions
(`reframing.unpinned`; pins grow as splits are labelled), and
`Channel.refuse_a_pinned_frame`.

**What it stands on.** Seeds are `supply.proven` q3/q4 roots on parameter planes only,
minus `labeling.pins.every_pinned`. The rungs (`reframing.RUNGS`, 16x to 256x the atom)
are framings of **one** location: one row at the head's pick, every rung's reading
under `rungs_drawn`. A nucleus row is `centered`: a `curation.framing` refinement may
move its scale only.

**Running it.** One `engine.screen` process at a time, below normal, not the
three-worker pool. A crashed batch is retried `SCREEN_RETRIES` times, then counted
`nucleus_not_drawn`; a supervisor tells a **nonzero exit** (crash) from a **clean exit
with few rows** (queue done; an overnight is a chain of legs). The header carries
`invocation` and `ledgers_read`. **Record and rank, never gate**: distinctness applies
where a sheet is cut, never to the ledger.

## The refine leg: `--refine-per-walk`, at close, top-k

When a walk closes it scans framings around its best `k` gate survivors
(`--refine-per-walk`, default 3, `0` off) through `curation.framing`, the gallery
pass's own step 5a: width `x{0.707, 1.0, 1.414}`, then a `+-0.25` frame recentring,
seven frames at the node regime, adopted **only if it beats the recorded framing by
`--refine-margin`** in log-odds on `P(>=4)`. Nothing feeds back into the walk.

### A written row is never edited, so the refinement is a later row

The leg appends a `refined` row per scanned location (a window under the margin
too), and `supply.ledgers.admitted` joins it onto the candidate row. Admission reads
the refined score, and the location key moves with the frame (`framing.original` keeps
the old one). Its cost is its own bucket, `refine_minutes`.

## Operators, gates and fates

**Reframing operators are triggered, never a source.** `snap_to_nucleus` emits one
`Reframing` per `operators.FRAMINGS` rung (own width, 4x, 16x the atom), never inward.
The probe is about a third of a harvest's active clock, mostly `expand_neighborhood`;
never price it by a short A/B leg (batch variance is ±23%).
`--neighborhood`/`--no-neighborhood` is a tri-state; the default lives on
`walk.Reframings`.

**A root's frame is the engine's** (`engine.home_view`; `tests/test_home_views.py`).
`julia:multibrot3`–`5` have no pool: `supply.twins` makes their roots per run, so only
a harvest reaches them.

**A walk scores the gate render** (byte-identical to the node-regime tile).
`identity.enforce` refuses a run whose `--colormap` is not the tile pool's cyclic floor
palette, whose `--node-width` is not the node frame, or whose engine cap disagrees with
the tile corpus; the engine build is recorded (`drawn_by.jsonl` beside every view), so
`curate score` re-renders what no stamp claims.

**Every candidate is recorded with the gate that refused it**; a survivor's fate is
`admitted` (frontier and books), `expandable` (frontier only, past the junk floor) or
`not_admitted`. `artifacts/location_views/` is a frozen record.
`Limits.lineage_admissions` caps one root's bookings per row (`lineage_capped: true`);
off here, on in [the deep run mode](../deep/README.md) and under `--lineage-cap`.

### A parameter-plane root starts above the depths its material lives at

Labelled plane material sits four or five rungs below a plane seed root, so the first
`--plane-grace-rungs` (5) rungs under a `walk.PLANE_ROOT_SOURCES` root skip the junk
floor; booking is untouched. Dynamical roots get no grace — they have no cliff, and
what stops them is the budget: `Limits.root_expansions` 12 for parameter planes,
`dynamical_root_expansions` 36 for every `z₀` family (`engine.DYNAMICAL_KINDS`).
**Below `min_width` (`1e-9`) is [the deep run mode](../deep/README.md)**, not a lower
floor here.

### Screening a named frame, and sampling the boundary

`screen` runs the walk's own battery on a record and reports per gate;
`--waive-occupancy` is the walk's first-rung waiver. `sample-boundary` draws in
`boundary.home_box` and writes `draws.jsonl` (every attempt) and `kept.jsonl` (a
manifest for `render --manifest`).

```
fractal-wallpapers screen --manifest rows.jsonl --out-dir artifacts/screen/frames
fractal-wallpapers sample-boundary --keep 12 --attempts 1024 --seed 1
```

## The viewport sampler: a root channel that makes places

A pinned plane (`phoenix:classic`) has one parameter, so a parameter pool gives it one
root. `viewport_sampler` makes places: it draws viewports, screens each through
`engine.screen`, and hands survivors over as roots, unranked, every attempt a
`sampler_draw` row. On the pinned plane the draw is an octave ladder, rung `k` a
jittered `2^k x 2^k` grid; the default four rungs are 340 frames in about eight
seconds, paid at every session start. `--sampler-rungs` adds `4^k` frames a rung, so
add one only when a leg has walked its shelf out.

```
fractal-wallpapers harvest --minutes 10 --partition phoenix:classic --root-channel proven --root-channel viewport_sampler
```

### A parameter plane: straddle refinement, and it does not run out

A quad-tree refined only where a child **straddles** (interior and escaped samples
both, off one `engine.dump_field` probe of its parent); every straddler between
`--sampler-widest` (0.1) and `--sampler-narrowest` (1e-3) is screened and served
round-robin over the band's rungs, a rung grown `CHUNK` (256) parents at a time. About
39% survive the screen; admissions are new places, concentrated on a few lineages.

**Degree 6 has no labels and this is its whole supply** (`labeling/README.md`'s
*Degree 6 is never labelled*). On `multibrot6` the yield climbs as the band narrows to
about `0.001`–`0.00023`. The working arm: `--sampler-widest 0.002 --sampler-narrowest
0.00023 --low-water 24 --cooldown 4 --lineage-cap 6` (`--low-water` is roots a refill
hands over).

```
fractal-wallpapers walk --family multibrot --degree 3 --root-channel viewport_sampler --roots 40
fractal-wallpapers harvest --partition multibrot5 --root-channel viewport_sampler
```

#### The straddle probe

`PROBE_RESOLUTION` is 64 x 36 at maxiter 256: the same ~6 ms as 32 x 18 (a probe is
process start), 99.2% agreement with `interior_cap`, and 2 of 176 screen survivors
missed, where 32 x 18 drops the filament an exterior child hangs on.

**`--foci`** (`walk`, `harvest`) adds a `foci` row per expanded node; candidate rows
are byte-identical either way.

## Parabolic parameters: aiming a Julia `c` at an implosion

`parabolic.py` solves exactly, degree 2 only, for where a component touches its
neighbour (a cusp or an `r/q` bulb root), and `parabolic.offsets` rings Julia
parameters around it: rich Julia sets at a shallow zoom. The door is `--seeds`. ⚠
`walk --seeds` does not enforce `pools.C_SPACING_FLOOR` (3.2e-2), and an aimed ring
sits inside it; a channel would have to answer that.

```
fractal-wallpapers walk --family julia --degree 2 --seeds aimed.jsonl --batch 16 --batches 152
```

## Is there a minibrot in this frame: the census instrument

`minibrot.py` answers two different questions, and `minibrots census` asks them of a
population: **(a) the frame HOLDS a minibrot** (`--reading band`, `minibrot.probe`: a
nucleus within a frame width of centre, its atom 1 to 32 frame widths smaller), and
**(c) the frame IS decoration of one** (`--reading enclosing`, `minibrot.enclosing`).
(b), depth below the walk's root, is route not frame; `minibrot.descent` keeps it as
provenance.

```
fractal-wallpapers minibrots probe --link "<an explorer link>"
fractal-wallpapers minibrots census --population records --out records.jsonl
fractal-wallpapers minibrots census --population pool --budget 7200 \
    --reading enclosing --skip records.jsonl --skip verdicts.jsonl --out pool.jsonl
fractal-wallpapers minibrots examples --census records.jsonl --census verdicts.jsonl \
    --census pool.jsonl --k 2.0 --descents '<leg>_*'
```

The example set (`artifacts/discovery/minibrot_examples.jsonl`, `--k 2.0`) is an
artifact, never tracked. A `--budget` pass is a seeded-shuffle sample. (c) is several
times faster than (a), and both slow with depth.

### Criterion (c): the copy a frame is decoration of

The candidates are the record minima of `|z_k|` along the critical orbit, nested
outermost first, cut into generations (a copy and its bulbs, by `minibrot.bulb_scale`
within `BULB_SLACK`); **the enclosing copy is the head of the last generation**, and
main-body decoration is enclosed by nothing. **`ENCLOSE_K` is 2.0, a copy's geometric
extent**; `TIGHT_ENCLOSE_K` (0.82) is where deep descents end, not a bound. ⚠ A cut
that drops a copy but keeps its doubling answers the doubling. Every row carries
`chain_table`, so a cut is re-swept off the output. `operators.MAX_PERIOD` (64) is why
the operators answer `nucleus_outside_frame` inside a copy (`deep/README.md`'s *The
reframing operators find nothing inside a copy*): its atoms sit at multiples of `q`.
