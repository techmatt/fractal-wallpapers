# tests

The test suite, including the guard that keeps this history text-only and small.

```
python -m pytest                                    # the fast lane, ~2m45s
python -m pytest --slow                             # every test, ~6m30s
cargo test --manifest-path engine/Cargo.toml        # ~7s warm, ~28s cold
```

The walk tests need a **release** engine and skip themselves without one:
`cargo build --release --manifest-path engine/Cargo.toml`. The checks that read
the read-only source project skip where that checkout is absent, which is
everywhere but Matt's machine — CI included.

`cargo test` builds the crate at `opt-level = 2` (`[profile.test]` in
`engine/Cargo.toml`). The tests render, and unoptimized they take eight times as
long to run as the optimization costs to compile.

## The two lanes

`--slow` is the whole suite; the default run holds back the eighty-odd tests
that do real work. A test earns `@pytest.mark.slow` by costing about a second or
more of a render through the engine, a training loop, or a sweep of a store —
the render cache, the tracked pool, the distillation corpus. Arithmetic stays
in the fast lane however much of it there is, and a slow guard **moves lanes rather than
being deleted or weakened**. The marker, the flag and the line the fast lane
prints all live in `conftest.py`; `CLAUDE.md` states the rule.

The line is the part that matters. Every run that holds anything back says how
much, because a lane that went quiet would be a set of guards nobody would
notice had stopped running.

Marking is not free of surprises: several of these guards share a cached
derivation — `absolute_paths_in_records`, `shipped_render_cache`, the engine
fingerprint's probe set — so moving one to the slow lane can simply hand its
cost to whichever sibling reads the cache next. Three of the first round's marks
bought nothing until their partner was marked too. Measure the fast lane after
marking, not before.

## A lane sharing the box with a render leg

`CLAUDE.md` states the rule — run the lane on an idle machine, and after a leg
rather than beside one. This is what was measured to get it.

**Beside a leg the lane does not merely slow, it dies.** Run twice while a leg's
three engines held the pool, it was killed at **77%** with no summary and no
traceback both times. That is the commit charge rather than any guard: the leg's
parent holds ~3.3 GB and each of three workers ~0.9 GB, against a box whose commit
limit `models/render/README.md` works through for the trainer under *The band, and
the study that adopted it*.

**Short of dying it crawls, and one guard turns red rather than slow.** The same
lane sharing this box with a leg reached 41% in the time it normally takes to
finish, and under load
`test_twins.py::test_the_channel_only_ever_hands_over_what_nobody_has_walked`
**fails** — it runs a refill loop against a wall clock. A red there on a busy box
is worth re-running alone before it is worth reading.

**But it survived beside `curate votes build`, and the difference is the parent
rather than the engines.** 2026-09-04, on Matt's say-so: **339.71 s over 3,589,
116 deselected, nothing skipped, all green** — `test_twins` included — beside a
forty-seat kit's three engines at below-normal. Three and a half times the idle
reading and not a death, because the thing that kills the lane is **commit
charge** and a votes build's parent holds almost nothing: it reaches its recipes
through `candidate_ledger.by_key`, which streams the ledger and keeps a few
hundred rows, where a solve's release leg is still holding the pool it selected
from. So the question to ask of a leg before sharing the box with it is what its
**parent** holds, not how many workers it has.

**It is still not a timing.** The same suite on the same install read **99.51 s**
an hour later once that leg had finished — so beside a leg it survives and tells
you nothing about the tests, which is why the rule stands unchanged.

**And the box's own commit charge drifts upward whether anything runs or not.**
The kernel leaks about **4 GiB a day**, attributed to no process, and a reboot is
the only thing that reclaims it — the pagefile was never the cause. What it looks
like when it has gone too far is a launch dying on `WinError 1455` with nothing
naming why, which is a fact about uptime rather than about the leg or the lane.
**Reboot the box before an overnight or any two-job night if its uptime is past a
week**, and read a lane taken on a box near that limit as the box.

## What "the fast-lane count" means

One definition, because three sessions on one tree wrote down three totals and
spent two commits arguing about it. `pytest -q` ends on a line of the shape
`P passed, S skipped, D deselected`, and the count this project records is
**`P + S`, the number pytest selected**, with `D` beside it:

- **Selected** is every test collected and not held back. It is what the clock
  is a price for, so a reading gives it and the clock together or gives neither.
- **Deselected** is the slow lane and nothing else — `conftest.pytest_collection_
  modifyitems` removes exactly the `slow`-marked and says how many.
- **Skipped** is a test that was collected, ran its guard and declined. Two
  conditions do it here: no release engine at `engine/target/release`, which the
  walk and render guards ask through `engine.engine_path`, and an `importorskip`
  *inside* a test body.
- **Not collected** is the one that does not appear in the total at all, and it
  is the trap. A module-level `pytest.importorskip` stops the module being
  imported, so its tests are absent rather than skipped — 8 modules gate that way
  on `torch`, 5 on `PIL`, both of them the `models` extra. The lane now prints a
  red line naming them and what is missing; before it did, they were silent.

**A reading is comparable only against another taken on `.[dev,models]` with a
release engine built.** Anything else is a different suite wearing the same name.

### The 3,383, resolved

It was an interpreter with no `torch`. Masking `torch` and `timm` at `2bde06e`
reproduces the logged reading to the unit — `3371 passed, 14 skipped, 109
deselected`, which at `9a62672`'s two-tests-fewer tree is exactly the **3,369
passed / 14 skipped / 109 deselected** written down that evening. The eight
torch-gated modules drop 65 fast tests and 5 slow ones, which is why the
deselected count fell from 114 to 109 as well; the fourteen skips are those eight
modules plus six test-level ones. Nothing was wrong with the tree, `test_colormaps.py`
was never the variable, and no test had been added or removed — the interpreter
was short two gigabytes of CUDA wheels and the lane had no way to say so.

## Shared readings of the tracked records

`conftest.py` holds session-scoped fixtures over the records this repository
tracks — `shipped_labels`, `shipped_scored`, `shipped_tile_plan`,
`shipped_render_cache`, `shipped_label_pool`, `distillation_rows`, and
`tracked_ledger`. Each is a
second or more to derive and the same every time it is asked, and more than one
file asks. They are fixtures rather than module caches so the sharing is opt-in:
a test that redirects a store to `tmp_path` does not ask for them and cannot be
handed a reading of the tracked corpus by accident. Nothing writes to them.

`shipped_label_pool` is the second one to reach for by reflex, and it is a factory
rather than a value on purpose. `render_deploy.sides_for` assigns `picture.side`
**in place**, so one shared list would carry whichever file ran last into
whichever ran next; the fixture hands back fresh `Picture`s on every call — a
`dataclasses.replace` a row, about ten milliseconds against four seconds — which
is exactly the independence a second `pool()` call used to buy. Its `assignment`
is the real `render_folds.assignment` with the shared pool patched under it, for
`shipped_render_cache`'s reason: a fixture that dealt the folds itself would be a
second opinion about the deal.

`tracked_ledger` is the dear one and the one to reach for by reflex. It carries
`.rows`, `.scores`, `.pool`, `.costs` and `.refused` — one reading, about 40s and
about 6 GB resident, serving `test_solve`, `test_headroom`, `test_distinct`,
`test_retention`, `test_hunt` and `test_candidate_ledger`. It
unsets the hot root while it lays the pool out, so a module that has redirected
the root at its own `tmp_path` cannot have this read an empty tree and report
every picture missing. It skips where the ledger has not been backfilled, which
is every machine but Matt's — CI included, so none of this costs CI anything.

## Redirecting a store: at the roots, never per accessor

There are exactly two roots and everything under `artifacts/` resolves through
one of them. `paths.HOT_ROOT_VARIABLE` and `paths.ARCHIVE_ROOT_VARIABLE` are the
whole redirect: the candidate ledger's two row files, the flatness and signature
sidecars, the supply sidecar and every durable copy all address a root, so setting
the two moves all of them at once. **Set them with
`monkeypatch.setenv` and redirect nothing else you do not have to.**

A per-accessor redirect is complete only against the call graph on the day it was
written, and this suite has now been bitten by that twice.

* The candidate-ledger split left `flatness.durable()` on the real tree while the
  store's own manifest was redirected, and overwrote
  `data/curation/candidate_ledger/{flatness,signatures}.manifest.json` with
  one-row counts off a temporary ledger. A person noticed.
* Moving the three fixtures to the roots on 2026-09-04 immediately showed the
  other half of it: `test_ledger_tracking`, `test_candidate_ledger.isolated` and
  `test_hunt` had all been reading **this machine's real supply sidecar and real
  expressed readout** through the prune, because no accessor list named them.
  Those tests would have failed on a fresh clone, where neither file exists; they
  write both empty now and are hermetic for the first time.
* **A third time, 2026-09-07, and this one is the mirror image**: two files
  redirected the **tracked** tier with `records.use(tmp_path)` and left the
  **artifacts** tier alone, so `rejection.apply` and `rejection.retire_repeats`
  redrew each run's release sheet through `run_layout.run_dir()` onto the live
  tree. `test_release_bar.py` wrote `artifacts/curation/runs/r/` and
  `test_served_locations.py` wrote `artifacts/curation/runs/earlier/`, on every
  run, for as long as either file has existed — two whole run directories nothing
  ever ran, which the orphan sweep and every inventory then had to have an answer
  for. Both fixtures set the two root variables now. **A store has two tiers and
  a fixture is not done when it has moved one of them.**

**Two accessors still have to be patched, and both are the tracked half.**
`candidate_ledger.store.manifest_dir()` resolves off `repo_root()`, not off a
tier, and there is no root to set because `repo_root` is imported *by value* into
three dozen modules. `candidate_ledger.ratchet.log_path()` joined it on 2026-09-07
for the same reason and with a wider blast radius: `prune` writes it at the end of
every merge, so *any* test that prunes would otherwise append a three-row store's
census to a guard's high-water mark. Its redirect is **autouse**
(`conftest.no_tracked_ratchet`) rather than per fixture, because the hazard belongs
to `prune` and not to whichever tests happen to call it today; the two guards that
mean to read the tracked log take the session-scoped `tracked_ratchet_log` fixture
and pass the path in, which is one binding rather than an un-patch.

Under both sits the same backstop: `conftest` hashes every git-tracked
`*manifest.json` — discovered, so a durable added tomorrow is covered — plus the
names in `HELD_STILL`, at session start, re-hashes at session finish, and fails the
run naming any that moved (`pytest_sessionfinish`). 20 files, 104 KB; the cost does
not show up against a three-minute lane.

**It asks the same question on the regenerable tier since 2026-09-07, through the
same hook.** `LIVE_LEG_DIRS` lists the immediate children of
`artifacts/curation/runs` at session start and again at finish, and a name that
appeared fails the run beside the manifests, under one heading and one writer.
That is the leak above caught rather than trusted: a fixture that moves one tier
looks complete, and nothing on the artifacts tier is hashed or tracked, so a
difference of two listings is the only detector there is. **A name at a fixed
depth and never a walk** — one `scandir` of about a dozen entries, twice a
session, over the tree `CLAUDE.md` says a recursive grep takes tens of minutes
across. One mechanism and two snapshots, deliberately: a second hook reporting the
same class of fault through a second writer is what goes quiet when somebody moves
one of them. `tests/test_lanes.py` guards the detector, including that it stays a
`scandir`.

`signatures.sidecar_path` is patched in
those fixtures for an unrelated reason: to undo the autouse
`no_signature_sidecar`, which the roots cannot reach because the function has
already been replaced.

## Where the time goes

The lane is a handful of tests and never a broad tax, and that is measurable
rather than a figure of speech: at 2026-08-31 the **top eighty tests were 490.6s
of a 563.5s lane**, and the other three thousand and sixty-eight were 72.9s
between them. So the question to ask of a slow lane that has grown is never
"what got slower"; it is **which store grew**, or **which derivation is being
paid twice**, and never a broad hunt.

That 563.5s is now **345.8s**, over the same 3,152 tests on the same machine the
same day, and no guard was deleted or moved lanes to get there. Four things came
out of the durations list, in the order they were worth:

| was | is | what |
| --- | --- | --- |
| 116.6s | 5.7s | `test_curation_colorize`'s byte-identity leg, on [`EXACTNESS_GEOMETRY`] |
| 29.5s | — | its fallback leg, the same |
| 52.4s | 6.3s | eight derivations of `render_folds.pool` collapsed to one — `conftest.shipped_label_pool` |
| ~10.5s a call | 9ms | `served_locations.build` asking `current_pass` once instead of once a row |

And what is left, which is the list to read before touching this again:

| s | what |
| --- | --- |
| 31 | `test_autolevel_identity`'s 28 pinned probes — **pinned to production geometry**, so it is not the colorize leg's trade |
| 12 | **the one reading of the candidate ledger**, wherever it lands first |
| ~10 each | `test_render_head`, `test_distinct`, `test_candidate_ledger`, `test_hunt` |
| ~7 each | `test_train`'s two epochs, `test_renders`' regeneration, `test_ledger_tracking`'s merges |

`test_ledger_tracking`'s merges are the honest kind: a merge reads the tracked
release sidecar through `intake.read_scores` once, and a test that merges twice
pays for two. That is what the door does in production and it is not a bug.

### A cost paid once per test scales with the suite, and hides from every reading

**The framing above is right about the slow lane and was wrong about the fast
one.** Profiled on its own for the first time on 2026-09-04, the fast lane's top
sixty were **49.7 s of 119.92 s** and the other 3,505 tests were **70.2 s between
them** — a broad tax, which is exactly what the paragraph above says never
happens here. Most of it was one line.

`tmp_path_factory.mktemp` is `numbered=True`, and pytest numbers a new directory
by iterating the whole basetemp for the highest suffix already there.
`conftest.no_signature_sidecar` is autouse, so it called that once per test:
basetemp grew an entry per test and every later test read all of them. Quadratic
in the number of tests.

Measured synthetically, every test also taking `tmp_path`, fresh basetemp each
run:

| 3,500 tests | clock |
| --- | --- |
| `mktemp` per test | **43.27 s** |
| the path taken off one session directory | **15.12 s** |
| that, and an O(1) `tmp_path` override | **5.38 s** |

The scaling is what proves it is the listing rather than the directory: 2,000
trivial tests cost 5.4 s of it and 4,000 cost 19.7 s — twice the tests, 3.6x the
price. On the real lane it was **12.86 s of 119.92 s**.

**It could not have been found from this log.** A store that grows steps the
digit on the day it grows; this grew three milliseconds at a time, with the
suite, and every reading in the log priced it as part of whatever else landed
that week. It never reached a durations list either, for the same reason. So the
question to ask of a lane, beside *which store grew* and *which derivation is
paid twice*, is **what does every test pay** — and the way to ask it is to sum a
`--durations=0 --durations-min=0` run by file, which is how this one was found.

### A derivation paid twice is the thing to look for

`served_locations.build` is the one to remember, because it was not a test
problem at all. `current_pass(rows)` sat **inside the list comprehension that
filters `rows`**, so it re-ranked the whole store once per row: 1,186 calls to
`records.score_rank` where one was meant, on every merge, every seating and every
gallery build. It is a pure function of `rows` and `rows` does not move under the
filter, so hoisting it is the same answer for a thousandth of the work. Nothing
about the test suite made that visible — a profile of one 10s test did.

### A lane that moves right after code landed is the code until measured otherwise

The three questions above — which store grew, which derivation is paid twice,
what does every test pay — are all questions about the *box and the stores*, and
reaching for them first has cost this project a session. On 2026-09-04 the fast
lane read **300.7 s** where it had been reading about 165, and the same run
failed `test_training_resume.py` on a CUDA OOM with six other processes holding
the GPU. "Measure it on an idle machine" was the obvious diagnosis and the wrong
one.

The extra **135 s** was `hunt.recorded_prices` walking the leg records and
parsing a `sequence.jsonl` per band — 0.65 s a band, 3.35 s for the five
`depth.DRAWS`, and `depth.plan` asks for four of them, so every guard that plans
a leg paid it. Caching it took the lane back to flat;
`curation/LEGS.md`'s *The two phoenix planes are declared in SECONDS now, and the
price is per band* carries the memo and the `forget_recorded_prices` rule that
goes with it.

So the cheap check when a lane moves right after a commit is **to re-run one slow
file under a profile**, not to re-run the whole lane hoping for a quieter box.

### The candidate ledger is the thing that grows

It went from 15,362 rows and 41 MB on 2026-08-26 to **366,236 rows and 1.11 GB on
2026-08-29** — 24x in three days, and it grew with every mine, hunt and depth leg.
**The lane went with it: 160 s on the 26th, 18:07 on the 29th, over the same
tests**, because seven guards each read the whole of it. That is the clearest
case this log holds of a lane pricing data rather than code, and it is why the
standing advice is to re-measure after a **merge** and not only after writing a
test. One `candidate_ledger.read()` of that file was 21.9s, `read_scores()` 4.2s,
`present_pictures()` 13.0s and laying the pool out over them 13.4s, so a cold
`headroom.population()` was about 46 seconds.

**Those figures are the wide store's, and it was deleted on 2026-08-29.** What
stands in its place is 122,516 rows and 150.8 MiB — the top three per (location,
mode) under five protections, each row cut to what the readers consume.
Re-measured on this machine: `read()` **3.9s**, `read_scores()` **0.8s**,
`solve.pool()` end to end **7.1s** against **29.3s** over the wide file. Reading
is no longer what this lane pays for.

**And it now has a ceiling, which is new.** `candidate_ledger.prune` runs inside
`candidate_ledger.merge`, so rows per (location, mode) are bounded by
`RETAIN_PER_PAIR` plus whatever the five protections carry, and are no longer a
function of the attempts made. A leg that opens new locations still grows the
file; a leg that deepens old ones no longer does. The two rules below stand as
written — a bound is not a licence to read the store in a fast test — but the
digit is no longer expected to move on its own.

Two rules follow, and they are why this lane is 7 minutes instead of 18:

* **The ledger is read once a session.** `conftest.tracked_ledger` holds the
  rows, the sidecar and the pool laid out over them. Seven guards used to derive
  that independently — four module fixtures at ~46s each and three more that read
  the rows again to census them. Ask the fixture; never call `read()` in a test.
* **A guard that sweeps the ledger takes a budget, not the store.** Two did not,
  and both had lost their own docstring's estimate by an order of magnitude:
  `test_solve`'s cutting plane was super-linear (1.3s at 2,000 candidates, 1.9s at
  20,000, 18.8s at 100,000, **185.6s at 275,822**) — that guard went with the exact
  solve it measured, on 2026-08-31 — and `test_hunt` rebuilt a recipe key for all
  344,923 levelled rows at half a millisecond each. `test_hunt` states a constant,
  `SAMPLE`, with the measurement that set it and an assertion that the budget was
  actually filled. This is the one place the
  suite trades coverage for time, and it is written down at each site rather than
  implied.

Four things that used to dominate and no longer do, in case they come back:

* **A bootstrap is linear in its draws.** A read that asserts a point statistic
  or a verdict does not need the shipped five thousand resamples; tests that
  reduce it say so at the constant and pin the shipped number against the
  document that declares it.
* **A sweep over every tracked file is a sweep over tens of megabytes.** The
  palette corpus is most of this tree by bytes. Reject cheaply first.
* **A stage that is a pure read of tracked data can be read once.** The colour
  census's `library` stage folds six hundred colormaps onto the codebook, and
  five tests ran it eight times between them for 21s. It is a module fixture now
  and every number they assert is still the real stage's.
* **A fixture that redirects a store must redirect all of it.** The neutral
  embeddings fixture redirected the store, the copy and the manifest but not the
  picture directory, so every `save` counted and sized this machine's thirty
  thousand neutral renders — 5.3s to measure something no test asserts.

### The lane's readings, in order

Every reading this lane has taken, in the order they were written, moved here
from `CLAUDE.md` on 2026-09-04 — that file is loaded into every session in this
repository and a chronological log is not a rule. The rules the log produced
stayed there; this is the evidence under them. The order is the one they were
appended in, because several entries say "the reading below" and mean the one
that was below them.

**+6, and a store the lane started reading once a test.**
`PRESELECT_ckpt117_fold_on_the_seating_key_0909`, 2026-09-09, idle box, taken after
the solve leg. The tree held **4,097 at 124.06 s** before the change and **4,103 at
122.54 s** after, 132 deselected either way, all green — **4,235 collected**. The
six are `distinct`'s fine-key guards, and the 4,097 is where the +10 entry below
left the lane plus the two commits after it. **The slow lane read 4,235 of 4,235
green in 448.94 s (7:28)**, same box, taken after the fast one, zero skips — 12 s
and eighteen tests above the 7:16 below.

The reading between the two is the one worth keeping. `distinct.preselect` resolves
the fine head's `pool_scores.jsonl` itself now — it has to, because it runs on
passes where nothing upstream read it — so every synthetic `headroom.census` and
`solve.solve` in this suite paid a 9.2 MiB, 42,300-row parse, 0.21 s a call. That
read **129.13 s**: green, +5.07 s, and a real-store read newly paid per test rather
than per pass. `conftest.the_pool_scores_are_read_once` gives the session one
reading of the real store and hands it back, which is `tracked_ledger`'s
arrangement at a smaller scale, and it took the lane back under where it started.
**A call naming a `path` is left alone** — a test writing its own column is asking
about that file.

**+10, and one of them exists because the other four nearly cost the lane ten
seconds.** `SOLVE_ckpt117_resolve_and_fate_0908`, 2026-09-09, idle box, taken after
the render leg. **128.56 s over 4,085 held, 132 deselected — 4,217 collected**, all
green. Six are `label-fate`'s rung movement between two records; four are
`headroom.bars`' `with_p_fine` column.

**The slow lane read 4,217 of 4,217 green in 436.12 s (7:16)**, same box, taken
after the fast one and after the render leg — **a clock and no red in the same
reading**, which the entry below could not give. **Zero skips**, so the render cache
is full, and 7:16 against the 6:45 of a cache-short lane is the forty seconds of
engine those nineteen cost plus the fifteen guards since.

**The `with_p_fine` column read its own store first, and `test_headroom.py` went
2.10 s to 12.60 s.** Nine tests in that file call `bars` directly and `clearing` and
`census` call it on every census, so a five-megabyte `pool_scores.jsonl` read inside
it was a fifth of a second on each of dozens of calls, for a column none of them
asked about. The fix is the module's own character rather than a fixture: `bars`
takes the scores as an argument and the CLI reads the store. **A fixture would have
fixed one file** — the callers are spread over `test_headroom.py`,
`test_texture_flat.py`, `test_candidate_ledger.py` and everything that censuses —
which is *[A derivation paid twice is the thing to look for](#a-derivation-paid-twice-is-the-thing-to-look-for)*
answered at the derivation instead of at the reader.
`test_the_census_never_reads_the_pool_scores_store_itself` is the guard, and it
monkeypatches the reader to raise.

**+18, and the slow lane has a count but no clock — deliberately.**
`PRECLOSEOUT_ckpt116_renderer_holes_and_repair_0908`, 2026-09-08. Fast:
**126.34 s over 4,075 held, 132 deselected — 4,207 collected**, idle box, taken
after the render legs. Slow: **4,200 of 4,202 green**, taken *while* a store-wide
`curate autolevel backfill` was rendering, at Matt's instruction, so **no seconds
are recorded for it** — a lane beside a leg answers green and red and not the
timing, which is
*[A lane sharing the box with a render leg](#a-lane-sharing-the-box-with-a-render-leg)*
being used rather than broken. The five between 4,202 and 4,207 landed after that
slow lane, closing its two reds.

**Both of that lane's reds were real and only one was the prompt's own.**
`test_the_stored_colour_block_is_what_the_picture_still_reads_as` went red because
re-rendering 10,664 pictures left their stored colour census reading the files that
used to be there — the guard that told this project a repair invalidates *every*
picture-derived reading and not only the score. `test_a_hunt_names_a_pass_s_pictures_the_way_the_pass_did`
went red because `MERGE_ckpt116` had put 3,015 authored-recipe rows into the pool
and no slow lane had run since; the guard rebuilt them from a plan that cannot
name a curve or a palette. **A latent red survived a whole prompt because the
fast lane does not hold either guard** — both are slow, and the slow lane is what
a checkpoint runs.

The eighteen: `test_renderer_agreement.py` is six (two fast, four slow) and
**replaces** one slow guard that moved out of `test_mine.py`, so the deselected
count goes 129 to 132. Then twelve fast — three over `release.task_for` being the
tree's only task builder, four over the stamp stores and the backfill's seat
selector, five over `colorize.is_candidate_path`. `test_nested_verbs.py`'s declared
surface caught both new `candidate-ledger` verbs before either lane did, which is
the cheaper guard doing its job first.

**+12 more, for the pairing and the split.** `SHOW_ckpt116_label4_fate_v2_0908`,
2026-09-08, idle box. **129.82 s over 4,060, 129 deselected** — **4,189**. The twelve
are `label-fate`'s second pass: the rule-by-rule pairing, the page split, and the
guard that pins which of two definitions of *the row that beat it* the page uses.
Clock 127.81 -> 129.82 s for 12 more arithmetic tests, which is the same page-cache
spread the entries below argue about.

**+32, and the clock did not move at all.** `SHOW_ckpt116_label4_fate_0908`,
2026-09-08, idle box, `.[dev,models]` with a release engine. **127.81 s over 4,048,
129 deselected** fast — **4,177** against the 4,145 the entry below this one left,
the 32 being `tests/test_label_fate.py`, all of them arithmetic over rows the test
hands in. Against that entry's 126.04 s over 4,016 the clock is 1.77 s *slower* for
32 more tests, which is inside the page-cache spread those two entries already
argue about and is not a reading that 32 fast guards cost anything.

**Taken after a two-hour render leg and not beside one**, which is the rule, and the
same lane run *beside* that leg an hour earlier read 219.21 s with
`test_twins.py::test_the_channel_only_ever_hands_over_what_nobody_has_walked` red —
green again in 1.96 s re-run alone. That is the documented load failure behaving
exactly as documented, on a box whose three engines were busy, and it is the second
time it has been the thing that goes red first.

**+1, and it is the deselected count that moves.**
`FIX_ckpt116_mine_mode_params_0908`, 2026-09-08, idle box, `.[dev,models]` with a
release engine. **126.04 s over 4,016, 129 deselected** fast — **4,145** against the
4,144 the entry below this one left. The one test is
`test_mine.py::test_the_two_makers_draw_the_same_picture_for_one_recipe`, which
renders one recipe through all three of this project's renderers and compares the
bytes; it costs about nine seconds of engine and is marked slow, so the *held* count
does not move at all and the deselected one goes 128 to 129. (Three was the whole
tree as it was understood that day. It is eight, and that test is now
`test_renderer_agreement.py` — see the entry for
`PRECLOSEOUT_ckpt116_renderer_holes_and_repair_0908` above.) That is the marking rule
working: a guard that drives the engine earns the mark whatever it is guarding.

The clock came back to 126.04 s from the 127.93 s below it with nothing removed,
which is the page-cache reading that entry warned about being right.

**+8, fast lane only, and four seconds nobody should read as a regression.**
`MERGE_ckpt116_label_rows_and_resolve_0908`, 2026-09-08, idle box, `.[dev,models]`
with a release engine, taken **after** the merge and the `score-pool` leg rather
than beside them. **127.93 s over 4,016, 128 deselected** fast — **4,144** against
the 4,136 the entry below this one left. Matt's prompt did not ask for the slow
lane and the diff is a new CLI verb plus arithmetic, so **4,144 is a projection for
the next slow lane and not a reading**.

The +8 are all `test_label_migration.py`: five over the `merge` stage — the
`POOL_SUBTREES` membership that makes the merged pictures reachable, the leg name,
the empty-store refusal and two over the engine stamp — and three over
`fine_by_expressibility`. Every one is arithmetic over a dict or a `tmp_path`, so
the deselected count does not move, 128 either side.

The clock is 127.93 s against 123.99 s over eight more tests, which is **not
per-test cost**: four seconds over eight arithmetic guards would be half a second
each. It is the box, and the reason is on the record rather than guessed — this
lane ran minutes after a merge that rewrote a 462 MB `rows.jsonl`, a 167 MB score
sidecar and a 42 MB flatness sidecar, and after a pass that decoded 41,407 JPEGs.
*Measure on an idle machine* means idle **including the page cache**, and a lane
taken in the wake of half a gigabyte of writes is reading the disk, not the tree.
Worth a re-run before anybody prices a guard off it.

**+45, both lanes, and the two counts agree.**
`FIX_ckpt116_autolevel_replay_0908`, 2026-09-08, idle box, `.[dev,models]` with a
release engine, both taken **after** the backfill and comparison legs rather than
beside them. **123.99 s over 4,008, 128 deselected** fast — **4,136** against the
4,091 the entry below this one left — and **4,136 passed, 0 skipped, 0 red, 7:05**
slow. The slow lane's total is exactly the fast lane's collected total, which is
[*What "the fast-lane count" means*](#what-the-fast-lane-count-means)' rule
holding rather than a coincidence to note.

The +45 is `test_stamps.py` (10) and `test_backfill.py` (12) whole, plus the
levelling-replay guards spread over four existing files: `test_autolevel` +6,
`test_candidate_ledger` +13 — ten of those the parametrized proof that each keyed
member *moves* the key — `test_curation_release` +2 and `test_depth` +2. **All 45
are fast and the deselected count does not move**, 128 either side: every one is
arithmetic over a fixture or a stub, and the two legs that did real work — 277
backfill renders and 24 release-geometry renders — are legs rather than guards.

The clock is 123.99 s against 122.79 s over forty-five more tests, so the
per-test cost is flat. The slow lane's **7:05 against 7:17 over ninety-three more
tests** is the one worth a sentence: it is not a saving anything here bought, it
is the render cache being warm where the earlier reading had paid for
`renders plan`/`renders build` inside its own window. Zero skips on both, which
is the normal reading now.

**+28 that reconciles exactly, fast lane only, and the surface table caught the
group.** `MIGRATE_ckpt116_label_recipes_0908`, 2026-09-08, idle box,
`.[dev,models]` with a release engine, taken **after** the render leg rather than
beside it. **122.79 s over 3,963, 128 deselected** fast — **4,091** against the
4,063 the entry below this one left. The +28 is the whole of
`tests/test_label_migration.py`, all fast: the derivation's "geometry and nothing
else" asserted member by member, the `curve`/`palette` override door and its
refusal of the field cache, the expressibility cross-tab, and the population rule.
**The deselected count does not move**, 128 either side, because none of the 28
earns the slow mark — every one is arithmetic over a fixture, and the leg's own
engine work is a leg rather than a guard.

The clock is 122.79 s against 121.32 s over twenty-eight more tests, which is
noise and not a cost, and the two guards that first read a store were the reason:
they swept the real colormap library at about a second each until `expressibility`
and `seat_expressibility` took `cyclic` as a parameter, the shape `solve.pool`'s
`spirals` already had. That took the new file 9.52 s → 1.98 s before it was ever
measured into the lane, which is [*Measure the fast lane after marking, not
before*](#measure-the-fast-lane-after-marking-not-before) applied to a store read
instead of a mark.

**Two reds, one cause, and the guard was right.** `test_nested_verbs.py` failed
twice — `test_every_nested_verb_is_a_real_subparser` and
`test_a_nested_verb_carries_only_the_flags_its_handler_reads` — because `SURFACE`
did not name the new `curate label-migration` group. Nothing was broken: the table
is the pin on what the command line *is*, and a group appearing in it is a
decision somebody writes down. It went to 18 groups and 77 verbs, and the count
assertion moved 71 → 77 with it. Matt skipped the slow lane, so **4,091 is a
derivation and not a reading**, on the same terms as the entry below.

**+14 that reconciles exactly, fast lane only, and the slow lane deliberately not
run.** `FIX_ckpt115_feasibility_group_cap_0908`, 2026-09-08, idle box,
`.[dev,models]` with a release engine. **121.32 s over 3,935, 128 deselected**
fast — **4,063** against the 4,049 the entry below this one left. The +14 is
**+4 slow**, this prompt's four guards on the feasibility row's group cap, which
is the whole of the deselected move 124 → 128; and **+10 fast**, all of them
`23d1d15`'s, the only commit to touch `tests/` between the two readings. The
clock is 121.32 s against 122.86 s over ten more tests, so nothing here is a
cost. Matt skipped the slow lane mid-prompt, so **4,063 is a derivation and not a
reading** — it is the fast lane's own collected total, which is what the slow
lane counts when nothing skips.

**+6 that reconciles exactly, fast lane only, and one flag table caught it.**
`FIX_ckpt114_recorded_p_fine_bar_0907`, 2026-09-07, idle box, `.[dev,models]` with
a release engine. **122.86 s over 3,925, 124 deselected** fast — 4,049 against the
4,043 the entry below this one left. The +6 is all arithmetic and all fast: **5**
in `test_solve.py` for the quality bar as a recorded parameter, and **1** in
`test_cli.py` for the flag on both verbs. **The slow lane was not run**, Matt's
instruction, so 4,043 is still the last slow reading and the next one should read
**4,049**. 122.86 against 120.68 and 122.01 is nothing. The one red the first pass
took was `test_nested_verbs.py`'s `SURFACE` table, which pins each verb's flag
list in printed order — it is the guard doing its job on a new flag and the fix
was the two table entries, not the parser.

**+7 that reconciles exactly, and both lanes moved less than the spread.**
`FIX_ckpt114_wallpapers_leftovers_0907`, 2026-09-07, idle box, `.[dev,models]`
with a release engine. **120.68 s over 3,919, 124 deselected** fast and **7:17
over 4,043, 0 skipped and 0 red** slow — 4,043 against the 4,036 the entry above
this one left. The +7 is all arithmetic and all fast: **4** orphan-sweep guards in
`test_candidate_ledger.py` for the reference set becoming a union, and **3** in
`test_lanes.py` for the session backstop's new half. **The 4,036 this is +7 of is
not an entry here**: the solve-profiling leg immediately below in the history
(`5ccf60b`, three tests added) reported 121.50 s over 3,912 fast and 4,036 in 6:55
slow in its **commit message** and did not append here, so that reading is in
`git log` and nowhere else. 120.68 against 121.50 and
122.01 is nothing. The slow lane's 7:17 against 6:55 is 22 s on a lane that has
read 6:43 to 7:38 across idle boxes with fewer tests in it than this — and the
diff's own engine work happened **before** the lane rather than beside it
(`curate re-render` of 38 pictures, 23.3 s, finished and confirmed idle), so this
is the box's spread and not a leg sharing it.

**+23 that reconciles exactly, and the long-standing red is closed rather than
retaken.** `FIX_ckpt114_named_picture_ratchet_0907`, 2026-09-07, idle box,
`.[dev,models]` with a release engine. **122.01 s over 3,909, 124 deselected**
fast — 4,033 against the 4,010 below. The +23 is all arithmetic: **18** in a new
`test_ratchet.py`, **3** prune-facing guards in `test_candidate_ledger.py`, **1**
fast provenance guard in `test_leveled_identity.py` reading the seeded mark
against that file's own `READING`, and **1** `LINES` case in `test_nested_verbs.py`
for the new `curate candidate-ledger ratchet`. 122.01 against 118.32–121.89 across
the three readings below is nothing, on a lane that has run 130.15 on a disturbed
disk. Slow **7:06 over 4,033, 0 skipped and 0 red** — the arithmetic's own
prediction to the test, taken after the last edit on an idle box, and **the first
all-green slow lane since the floor below went red**. 7:06 against the 7:38 below
is a lane 28 tests larger running half a minute faster, which is the spread this
lane shows between idle readings rather than anything the diff did.

**The red below is gone and the fix was not a retake.** The floor had drifted
another 6 to **13,504** by the time this prompt ran, which is the argument in one
number: a retaken constant goes stale inside a week, because *the store only grows*
is not true of a store `prune` deletes from on purpose. The census is held by a
**ratchet** now — count now, plus deletions recorded since the high-water mark,
reaches the mark, per counter — and the 22 rows already gone were entered once as
an explicit reconciliation with the mark left at 13,526. It reconciles at exactly
zero headroom, which is what an honest close looks like: no slack invented to make
it comfortable. The full entry is on the red below.

**+4 in one prompt, and the clock did not move.**
`FIX_ckpt113_cascade_records_and_pool_reads_0907`, 2026-09-07, idle box,
`.[dev,models]` with a release engine. **120.37 s over 3,886, 124 deselected**
fast — 4,010 against the 4,006 below. The +4 is two arithmetic tests in
`test_solve.py` over the record fields that name a seating's key, and a new
`tests/test_pool_draw.py` of two, which stands in for the draw's three
store-facing collaborators and so is arithmetic too. 120.37 against 118.32 below
is two seconds over a lane that has run 130.15 on a disturbed disk, so nothing
here is a cost. Slow lane not run — the diff is two modules, their tests and
three documents, and the one slow guard the prompt touches was run alone: the
known red still fails, at **13,504** against its floor of 13,526, having moved
DOWN 6 from 13,510 under last night's merges. **The next slow lane should read
4,010** and that red should still be the only one.

**+1, and the first reading of this file taken right after a four-hour render
leg rather than before one.**
`MINE_ckpt113_band_weighted_with_displacement_0907`, 2026-09-07, box idle again
by then, `.[dev,models]` with a release engine. **118.32 s over 3,882, 124
deselected** fast — 4,006 against the 4,005 below. The +1 is one arithmetic test
in `test_seat_sheet.py` for the diff's new place split, which is why the count
moved and the clock did not: 118.32 against 118.80 two prompts down, a spread of
half a second over a lane that ran 130.15 once on a disturbed disk. Slow lane not
run — the tracked diff is two documents, one module and its test, and Matt's
standing rule is the fast lane for a diff of that shape. **The next slow lane
should read 4,006** and the one red below should still be the only red.

**+2 that reconciles exactly, and a first reading taken 8 s dear right after a
sweep.** `ADOPT_ckpt113_cascade_and_cleanups_0907`, 2026-09-07, idle box,
`.[dev,models]` with a release engine. **121.89 s over 3,881, 124 deselected**
fast — 4,005 against the 4,003 below. The +2 is +3 landing and 1 going, all
arithmetic: one in `test_depth.py` over `depth.field_modes_only`, and in
`test_seat_sheet.py` the cascade's default-key guard **rewritten as two** — the
adoption itself, and a new one reading `_prune_ranks`'s source to prove the flip
could not reach retention. Slow **7:38 over 4,005**, and it is the reading that
does NOT come back clean: see the entry below this one.

**The 8 s is the sweep, not the code, and this is what the two-reading rule is
for.** The first fast lane of the prompt read **130.15 s** — +11.35 s on a +2 of
pure arithmetic, which is exactly the shape the rules say to distrust. Profiling
the two touched files put neither new test in the top eight durations (the
slowest of 126 is 4.39 s and both new ones are under a tenth), and a second lane
on a settled box read 121.89 s. What sat between the baseline and the first
reading was `curate candidate-ledger orphans --apply` deleting **1,032 pictures
and 555 colormap directories**; *suspect the disk after anything that moves
hundreds of thousands of paths* covers it at a smaller scale. Attributed to the
sweep by elimination and not by measurement.

**One slow guard is RED and it predates this prompt.**
`test_leveled_identity.py::test_no_two_ledger_rows_name_one_picture` asserts
`run_index_named >= 13,526` as a floor — *the store only grows* — and the live
store reads **13,510**. It fails identically on a stashed, clean tree at the
commit below, in 44 s, so it is not this prompt's code and was not this prompt's
sweep either: the sweep deletes pictures and colormap directories and writes no
ledger row. What moved is the ledger, between the reading being written and now,
and the census the constant records is 16 run-index-named rows out of date. It is
a **reading to retake, not a guard to weaken** — the row total is over its own
floor, so the store did grow; a shape it once had shrank. Left red and named here
rather than repointed, because repointing a census constant to make a lane green
is the one move that would make the guard worthless.

**CLOSED 2026-09-07 by `FIX_ckpt114_named_picture_ratchet_0907`, and not by a
retake.** Two more merges took it to **13,504**, which is the tell: a retaken
constant would have gone stale again the same week, because the thing being
asserted — *the store only grows* — is not true of this store and no number makes
it true. The floor is a **ratchet** now
([`candidate_ledger.ratchet`](../src/fractal_wallpapers/curation/candidate_ledger/ratchet.py)):
the count now, plus every deletion a transaction wrote down since the high-water
mark, must still reach that mark, per counter. `prune` advances the mark and
records its drops at the end of its own transaction, which it can do because it is
the **only** writer that removes a row — `store.write` is an upsert and the orphan
sweep takes pictures. The 22 rows already gone were entered once, by hand, as an
explicit reconciliation naming them unrecorded displacement-mining loss of the
ckpt 113–114 era; the mark stayed at 13,526 rather than being re-based to 13,504,
so the store now reconciles at exactly zero headroom on that counter (13,504 + 22)
and the history of the loss is a committed line rather than a changed constant.

**-17 that reconciles exactly, and the 8 s of the entry below came back.**
`FIX_ckpt113_legs_k_rot_and_retirements_0906`, 2026-09-07, idle box,
`.[dev,models]` with a release engine. **118.80 s over 3,879, 124 deselected**
fast — 4,003 against the 4,020 below. The -17 is two retirements and nothing else:
**14** in `test_expressed.py`, deleted whole with the colour-expression census
Matt ruled out, and **3** parametrized `gallery-store` rows in
`test_nested_verbs.py`, deleted with the retired gallery passes' gate store. Slow
**6:49 over 4,003, 0 skipped**, taken after the last edit. Both lanes ran with no
render leg on the box.

**Two guards changed shape rather than going, and the distinction is the point.**
`test_curation_rescore`'s store-routing test pinned `_write` sending a `gate` row
to a pass's own store; there is one store now, so it pins that instead and fails
if a second appears. `test_unfilled_reason` read its whole population — nine empty
seats over four passes — out of the deleted slot rows, and now carries those nine
rows' four counters as a table. Neither is a weakening: the population cannot
grow, nothing can write a tenth empty seat, and the reader under test is
unchanged. **The 8.45 s the entry below could not attribute is gone**, on a lane
17 tests smaller — which is not enough to call it, and the honest reading is still
that both figures sit inside this lane's idle spread.

**+20 that reconciles exactly, and a fast lane that moved 8 s with no slow test
added.** `REFIT_ckpt113_fine_tier_head_and_seat_sheet_0906`, 2026-09-07, idle box,
`.[dev,models]` with a release engine. **126.99 s over 3,896, 124 deselected**
fast — 4,020 against the 4,000 below. The +20 is +22 landing and 2 going: eleven
new guards in `test_gallery_grade_train.py` over the band, the stopping rule and
the pre-registered bar, eleven in a new `test_seat_sheet.py` over the cascade
order and the diff, and **two deleted** — both pinned behaviour this prompt
removed rather than behaviour it broke, and both have a stronger replacement
beside them. Slow **7:07 over 4,020, 0 skipped**, and it was taken before the last
edit of the prompt; that edit's own tests are in the fast lane.

**The +8.45 s is not attributed and is the honest reading.** `test_seat_sheet.py`
is 0.21 s for its eleven and the new guards in `test_gallery_grade_train.py` cost
under a second between them, so the file-level arithmetic accounts for about one
second of the eight. The two lanes ran on the same idle box with the same install
either side of a GPU band and a 320-second pool read, which is the shape of a
reading taken on a box that has been busy rather than one that is busy — worth
re-taking before anything is concluded from it, and worth not concluding anything
from meanwhile.

**+28 that reconciles exactly, and the first slow lane in five prompts.**
`TRAIN_ckpt113_fine_tier_head_0906`, 2026-09-06, idle box, `.[dev,models]` with a
release engine. **118.54 s over 3,876, 124 deselected** fast — 4,000 against the
3,972 below, and the +28 is exactly `test_gallery_grade_train.py`, all of it fast.
Slow **7:12 over 4,000, 0 skipped**, which is the arithmetic's own prediction to
the test and the first slow lane taken since the reading five entries below.

Two things are worth having from it. The new file costs **0.40 s** of the fast
lane for 28 tests, because 26 of them share one module-scoped un-pretrained
backbone build and the other two read tracked JSON — a whole head's guard for the
price of one engine-bound test. And the **slow lane did not move**: 6:43 over
3,958 then, 7:12 over 4,000 now, with 42 more tests and none of them slow. The
29 s is not attributed and is inside the noise this lane has shown between idle
readings; nothing here added a render, a training loop or a store sweep.

**+6 that reconciles exactly, and one of the two new fast guards is worth its
second.** `PROTECT_ckpt112_gallery_grade_keys_0906`, 2026-09-06, idle box,
`.[dev,models]` with a release engine. **118.94 s over 3,848, 124 deselected**
fast — 3,972 against the 3,966 below, and the +6 is exactly
`test_gallery_grade_retention.py`: five fast and one slow. No slow lane; the new
file was run alone with `--slow`, **27.40 s over 6**, of which 24.06 s is
`conftest.tracked_ledger`'s reading and 0.78 s is the guard itself.

**+1.23 s for two calls of a reader that now sweeps a third store.**
`retention.labeled_renders` reads `gallery_grade` beside the two finished heads,
which took it from 11,849 keys to 12,766 and from about 0.45 s to about 0.57 s;
two fast tests call it and a third pays it inside a synthetic `prune`. That is
the whole of the +1.23 s and it is the shape *A cost paid once per test scales
with the suite* warns about — three tests is fine, and a fourth wanting the same
reader should take it from a fixture rather than call it again.

**+13 that reconciles exactly, on a box serving three label pages.**
`FOLLOWUP_ckpt112_identity_pin_rehome_dedup_0906`, 2026-09-06, `.[dev,models]`
with a release engine, three `label serve` processes up on 8020-8022 while it ran.
**117.71 s over 3,843, 123 deselected** fast — 3,966 against the 3,953 below, and
the +13 is exactly what landed: `test_leveled_identity.py`'s ten (nine fast, one
slow) plus three in `test_rank_key.py`. The new file's fast half is 1.36 s of the
+4.11 s; the rest is not attributed, and the label servers are the obvious
candidate — this is a reading taken beside something, which is why it says so.
No slow lane; the one slow guard added was run alone, **32.47 s over 10** with the
fast nine beside it.

**A -11 that reconciles exactly, and the first reading here with no slow lane
beside it.** `REMOVE_ckpt112_stratum_score_0906`, 2026-09-06, idle box,
`.[dev,models]` with a release engine. **113.60 s over 3,831, 122 deselected**
fast. The prompt asked for the fast lane and only the fast lane ran, so there is
no slow figure for this date and the next slow reading should be compared against
the 3,958 above rather than against anything here.

**The count needs two moves to read, and both are accounted for.** The 3,836
below was taken at `BUILD_ckpt112_gallery_grade_sheets_0906`, and `d701596`
landed *after* it with six drift-guard tests in `test_expressed.py` — so the
baseline this prompt started from was 3,842, not 3,836. Eleven went: nine in
`test_expressed.py` (two thin-list, one recolor-cost, six drift-guard, which is
every test `d701596` wrote) and two stratum guards in `test_rank_key.py`.
3,842 - 11 = 3,831. **A reading taken against 3,836 would look like -5 and would
be wrong about which tests moved**, which is the same trap as comparing across a
palette drop.

**113.60 s against 112.00 s with eleven fewer tests is noise, and the log itself
is the evidence.** The last four fast readings here are 115.01, 111.47, 112.00
and this one — a 3.5 s spread with no code cause behind any of it, and 113.60
sits inside it. Nothing in this prompt could plausibly cost time: the removal
takes a store read *out* of `features_for`, which no longer opens
`expressed.json` at all.

**A +35 that is entirely one new store's, and the slow lane got *faster*.**
`BUILD_ckpt112_gallery_grade_sheets_0906`, 2026-09-06, idle box (both lanes run
after the render legs, never beside them), `.[dev,models]` with a release engine.
**112.00 s over 3,836, 122 deselected** fast and **6:43 over 3,958, 0 skipped**
slow. 3,836 + 122 is 3,958, so the count definition holds; the +35 against the
reading below is exactly the tests written — 28 in a new `test_gallery_grade.py`
(one of them slow, the choke-point sweep), 6 in `test_palette_carriers.py`, 1 in
`test_cli.py` — and the fast lane took 34 of them for +0.53 s.

**The slow lane read 6:43 against 6:52 with 35 more tests in it**, which is the
lane moving the *right* way for once and is worth writing down as noise rather
than as a win: nothing in this prompt made anything faster, and `carriers.jsonl`
losing 191 KB is not a store any slow guard sweeps. Nine seconds on a seven-minute
lane is inside the spread this log already shows.

**Two readings a prompt apart, and the second is the first plus this prompt's own
tests.** `BUILD_ckpt112_retention_freeslots_and_TODOs_0906`, 2026-09-06, idle box,
`.[dev,models]` with a release engine. Before any edit: `--slow -rs` read **6:46
over 3,917, 0 skipped**, which reproduces the reading below to the second and
confirms zero skips is now the resting state rather than one lucky box. After the
work: **6:52 over 3,923, 0 skipped** slow and **111.47 s over 3,802, 121
deselected** fast — and 3,802 + 121 is 3,923, the count definition holding again.

**The +6 is entirely this prompt's and every one of them is arithmetic**, so the
fast lane took all six and the slow lane's 6:46 → 6:52 is noise rather than
those tests: five free-slot guards in `test_retention.py` and one `LINES` case in
`test_nested_verbs.py`. **This is the first reading taken across a store that
SHRANK**, and it moved nothing: the ledger's score sidecar went 574,162 rows to
284,517 (the two retired judge artifacts dropped, 142 MB) and no slow guard over
the live store noticed, which is the answer to *which store grew* asked in the
other direction. `RETAIN_PER_PAIR` moved 3 → 5 in the same commit and no lane
guard reads the value, only the constant. Compare the next lane against 3,923 and
zero skips.

**Zero skips, and that is the store condition confirmed rather than argued.**
`--slow -rs` at `GUARD_score_regime_0906`, 2026-09-06, read **6:45 over 3,917, 0
skipped** on an idle box, on the same `.[dev,models]` install with a release
engine, with the fast lane at **115.01 s over 3,796, 121 deselected** — and
3,796 + 121 is 3,917, which is the count definition holding. The reading below predicted exactly this — the 19 were the render cache
being short, so a box with a full cache skips zero — and this is the first lane
to actually take it. The cache was filled by a prompt that ran between the two
readings, not by anything here. **It prices them too**: 6:45 against 6:05 is
those 19 guards *running* — engine renders and a training loop — plus 21 more
tests, so the skips were hiding roughly forty seconds and every future reading
on a full cache carries it. A lane that skips 19 again is a short cache, not a
regression.

The count moved 3,896 to 3,917. **One of the 21 is this prompt's**, and a
`--collect-only` with its three files stashed read **3,916** at `f1b2c1d`, so the
other twenty landed in the three commits that went in beside it — 19 of them the
two new files `test_top_slice_probe.py` and `test_activations.py`, collected
directly. Compare the next lane against 3,917 and zero skips.

**The 19 slow-lane skips are named, and they are one cause.** `--slow -rs` at
`SHOW_n1000_gallery_0906`, 2026-09-06, read **6:05 over 3,896, 19 skipped** — the
3,894 below plus this prompt's two — on an idle box, and every one of the 19 is
the **render cache being short**: `{'smooth_render': 240, 'strange_render': 237}`
against what the guards want, over `test_render_deploy.py` (5), `test_render_dose.py`
(5), `test_render_grade.py` (3), `test_render_head.py` (3), `test_finished_train.py`
(2) and `test_renders.py` (1). Not a tree fault and nothing to fix in the suite:
`renders plan` then `renders build` fills the cache and they run. The reading
before this one said the skips were unexplained; they are a **store** condition,
so a clone with a full cache sees 19 fewer skips and no count change. 6:05 against
5:52 is the two added tests and noise, not a regression.

It read **112.44 s over 3,778, 116 deselected** fast and **5:52 over 3,894, 19
skipped** slow at `SWEEP_color_mass_and_MINE_thin_themes_0906`, 2026-09-06, on the
same `.[dev,models]` install with a release engine. **Eight tests were written** —
seven in `test_palette_mass_sweep.py` and one case added to `test_nested_verbs`'
`LINES` — and **the counts moved by fifteen**. The other seven are not this
prompt's and were already in the tree: a stash of this prompt's work and a
`--collect-only` read the fast lane at **3,770** before any of it, so the 3,763
above was already seven behind when it was written. Compare the next lane against
3,778 and 3,894.

**The 19 skips are still the 19** and still unnamed, which is now two readings in
a row. A lane read at a moving count is a lane whose skips nobody can attribute,
so the next prompt with a slow lane to spend should spend it with `--slow -rs`.

⚠ **The slow lane has a test that fails by the CLOCK and it fired here.**
`test_cli.py::test_a_derived_plan_reserves_the_release_the_run_will_actually_ask_for`
asked `--finish-by 07:00` against the real time of day, and `harvest_minutes`
refuses a plan whose remaining clock cannot cover its own 29-minute reservation —
so the test failed at **06:53** for no reason but the hour, and would have failed
for anyone running the lane in the half hour before seven in the morning. It is
fixed here: the finish time is three hours from `now`, which fits the reservation
at every hour. Nothing in that test was ever about seven o'clock. **A red in that
one file is worth checking the wall clock before it is worth checking the tree.**

It read **114.16 s over 3,763, 116 deselected** fast and **6:03 over 3,879, 19
skipped** slow at `PRE_CLOSEOUT_wallpapers_0906`, 2026-09-06, on the same
`.[dev,models]` install with a release engine. **Six tests were written** — the
`mode_policy.UNMINED` guards — and the counts move by exactly six on both lanes,
which is the arithmetic doing what it should.

**The 19 skips are the entry.** The reading below says *nothing skipped* and this
one does not, and the movement is **not** this prompt's: the fast lane skips
nothing at all here, so all 19 sit inside the 116 slow-only tests, and the six
added are in `test_mode_policy.py` where none of them is slow. A release engine is
present, so it is not the usual cause. **Nobody has looked at which 19**, because
naming them is another slow lane and this prompt had no reason to spend one; it is
recorded so the next lane to be read is compared against 19 rather than against
zero, and so that whoever wants the answer knows it costs `--slow -rs` and nothing
cleverer.

**The slow lane's 6:03 is under the 6:34 below and was taken on a busier box**, so
it is not evidence of anything getting faster. It ran beside a `cargo test` and in
the wake of a 269 s palette re-cut, and it *stalled* — 5% in the first five
minutes, then the remaining 95% in one. A lane whose progress is that lumpy is a
lane whose total is a poor summary, and the reason the total is quoted anyway is
that it is what the gate reads.

It read **111.54 s over 3,757, 116 deselected** fast at
`INGEST_new_maps_labels_0905`, 2026-09-05, on a box idle but for the two-store
ingest that had just finished — no render leg, no probe, the sitting's four modes
carrying no modulate. **The count did not move and no test was written**: what
landed is 477 finished-render label rows, 240 in `smooth_render` and 237 in
`strange_render`, roughly 4% on each store. That is the *which store grew* answer
to the three questions, and it is where a guard that sweeps either store would pay
— but **3.57 s over the settled reading is 3.3%, and this log's own same-tree
spread is 3.8%**, so the movement is not separable from the box at this size and
is recorded rather than attributed. The slow lane was not run: the diff is label
rows and two store READMEs.

It read **107.97 s over 3,757, 116 deselected** fast and **6:34 over 3,873,
nothing skipped** slow at `SHEET_new_palettes_0905`, 2026-09-05, on the same
`.[dev,models]` install with a release engine. **The slow lane's clock had been
unread since an older and smaller tree** — `CLAUDE.md` carried 6:11 over 3,716 and
said so — and this is the reading that replaces it: 157 more tests for 23 more
seconds, which is the fairest evidence this log holds that the count has grown and
the clock has not. Neither lane moved on the day's work: no test was added, and
what the day *did* add is 19,200 candidate rows (2,534 net after the prune), 100
label rows and 100 render crops.

**And the fast lane was read twice, forty minutes apart, at 112.06 s and 107.97 s
over the identical tree.** The first was taken within the hour after a 64-minute
render leg and a 580-unit measure pass; the second after the box had been idle
through a slow lane. 4.1 s, 3.8%, on an unchanged tree — which is the size of the
"re-run before believing a lane that moves right after a leg" rule, measured
rather than asserted. The figure carried forward is the settled one.

It read **107.65 s over 3,757, 116 deselected** fast at `INGEST_new_palettes_0905`,
2026-09-05, on an idle box. **Every one of the 120 added tests is the colormap
guard's**: `classic-pairs-2026-09` put 120 files into `data/palettes` and
`test_colormaps.py` parametrizes over the directory, so `3,637 + 120 = 3,757` with
no test written. The 2.21 s over the reading below is those 120 well-formedness
checks and the two carrier and ceiling guards this prompt re-read, and it is the
one lane movement in this log that is a *data* diff rather than a code one.

It read **105.44 s over 3,637, 116 deselected** fast at `FIX_owed_minor_0905`,
same day, on an idle box once that prompt's counterfactual solves had finished.
The fifteen guards added there cost **1.68 s** of it, measured directly rather
than by difference — `-k` over the fifteen reads 7.03 s against a
nothing-matches run's 5.35 s of collection, which is the way to price a handful
of tests when the reading they would be differenced against was taken two
prompts ago on a different tree. HEAD held 3,622 before them. The slow lane was
not run: the diff is a rule, a cap, an un-ignore and a task rebuild, all of them
guarded in the fast lane.

It read **101.72 s over 3,600, 116 deselected** fast and **6:11 over 3,716, nothing
skipped** slow at the τ ruling, 2026-09-05, both on an idle box once the n40 kit's
leg had finished. **2.21 s for eleven more tests**, all of them in `test_votes.py`,
and the shape is why it is that cheap: five are pure arithmetic over
`parse_supersample_for` and the other six build a two-seat kit whose renders are
stubbed, so the only real work is two 2560x1440 encodes and a downscale apiece.

**Count the totals and not the passes when a lane came back red.** The first
reading of this pair was taken from a run that failed one guard — the nested-verb
flag table did not yet know about `--ss-for` — and its summary line reads
`1 failed, 3599 passed`, which was read once here as a total of 3,599 and made the
lane look one test short of what had been added. **3,599 + 1 + 116 is 3,716**, and
3,716 is eleven over the reading below's 3,705, which is exactly what was written.
A red lane still gives a count; it gives it in two numbers.

**The slow lane is the first full reading since 2026-09-04's 6:31 over 3,681**, and
it is *20 s faster over 35 more tests*. Nothing was marked and no store moved
between them, so on this file's own rule that is the box rather than the tree.

It read **99.51 s over 3,589, 116 deselected, nothing skipped** at the voting kit,
2026-09-04 — **ten tests more** than the reading below and **3.34 s over** its
96.17 s, on an idle box once the forty-seat kit's leg had finished. The ten are six
kit guards, two on the release task's mode settings, and two nested-verb lines, and
the 3.34 s is where you would put it: the kit guards render nothing —
`votes.render_fulls` is replaced — but each encodes two 2560x1440 JPEGs and
downscales one, which is about 0.4 s of Pillow apiece and the rest is arithmetic.
The most expensive fast-lane guards in this suite are now picture guards that never
open the engine.

**The same lane read 339.71 s an hour earlier, run beside that leg on Matt's
say-so** — three and a half times, all green, `test_twins` included. That reading
is in *A lane sharing the box with a render leg* above, where it says something
about legs rather than about tests.

It read **96.17 s over 3,579, 116 deselected, nothing skipped** at the publication
ruling, 2026-09-04 — **six tests more** than the reading below and **1.44 s under**
its 97.61 s, taken on an idle box minutes after a 34-minute n=2000 solve leg had
finished. The six are the publication guards, and every one is arithmetic or a
handful of synthetic stamps in `tmp_path`; two of them read tracked files off the
checkout (`.gitignore`, and each published stamp's three names) and neither opens a
record. A lane that moved *down* while gaining tests is the box being quieter than
the reading below, not the guards paying for themselves — the honest reading is
that the six cost nothing measurable.

It read **97.61 s over 3,573, 116 deselected, nothing skipped** at the augmenting
chain, 2026-09-04 — **eight tests more** than the reading below and **1.17 s under**
its 98.78 s. The eight are the new stage's guards, and the reading is the answer to
the obvious worry about it: the chain stage runs on **every** `solve.solve` call in
the suite, of which there are 94, and it costs the lane nothing measurable. The
pools these tests build are three to forty rows, where the index is a dictionary
walk and the diversity rule is asked about almost nothing. A stage whose real cost
is 46 s at n=750 is free at n=3, and that is the shape to expect from anything
priced per candidate rather than per pass.

One reading in the middle of that session was **134.28 s for `test_solve.py` alone**
against 14.24 s and then 7.32 s for the same file minutes either side, with no
single test over 0.36 s in the durations. It was the box and not the file, and it is
written down because the first instinct — a new stage had just landed in exactly
that file — was wrong, and the cheap check that settled it was re-running the one
file rather than reasoning about the change.

It read **104.29 s over 3,565, 116 deselected, nothing skipped** at the `CLAUDE.md`
tidy, 2026-09-04 — the same 3,565 as the reading below and **5.51 s over it**, on a
diff of three tracked `.md` files and no code at all. It is recorded rather than
explained: the standing rule is to ask when the digit moves with no test added, and
here nothing the lane prices changed, so what is left is the box. 5.6% is at the top
of the spread this log has carried between adjacent readings of an unchanged tree
(3% and 1% are the two below it), which is worth knowing the next time a reading of
this size is taken for a signal.

The **fast** lane read **98.78 s over 3,565, 116 deselected, nothing skipped** at
the temporary-directory fix, 2026-09-04 — the same 3,565 as the reading below and
**21.14 s under** the 119.92 s taken on that tree, the same afternoon, before
anything was touched. Both figures are this session's, so the comparison is one
box in one hour rather than one entry against another. Three parts, measured
apart: the temporary directories **12.86 s** (the section above), `test_depth`'s
fixture scale about **7 s**, and one shared parser for the nested-verb pin
**2.5 s**. Nothing was deleted, nothing moved lanes, and the one guard whose
assertion was in the way — that three engines buy three times the plan — kept its
band and was given back the wide world it needs, because the population binds
before the clock does and at 120 places it reads 1.45x.

**The slow lane could not be re-read that day and the failed attempt is the
useful part.** It came back 7:00 against the re-mode leg's 6:31, right after the
fast lane had fallen a fifth — which no change here can do, since the slow lane
runs every fast test too. A website run had the box at 65% CPU.
`test_autolevel_identity` settled it: thirty-odd engine renders, untouchable by
any of this, reading **31.08 s / 34.24 s / 32.31 s** across the three runs. A
tenth either way on an invariant guard is the whole of the anomaly. **Re-run one
untouched engine-bound guard before believing a lane** — forty seconds against
seven minutes, and it answers *box or tree* by itself.

It read **122.97 s over 3,565, 116 deselected** at the re-mode leg,
idle, 2026-09-04 — twenty-seven tests more than the reading below it and 2.68 s
over it, which is about a tenth of a second a test and the ordinary shape. Twenty
of the twenty-seven are `test_remode.py`, all of them arithmetic over a fake
ledger wired at `candidate_ledger.stream`/`stream_scores`; the leg itself renders
3,602 pictures and **none of that is in this lane**, which is the arrangement
working rather than a gap.

The **slow** lane read **6:31 (390.59 s) over 3,681, nothing skipped** at the same
commit, idle, 2026-09-04 — thirty-three tests more than the reading below and
**24 s under it**, which is the first slow reading to drop while gaining tests.
The cause is not this drop's work: it is `4300e4b`'s three solve speedups, which
took the n=2000 pass from 275 s to 119 s, and the slow lane holds guards that run
a pass. So a lane that got cheaper here is a lane pricing *code that got faster* —
the one benign reason for the digit to fall, and the opposite of the two occasions
it rose on its own. Worth recording because the standing rule is to suspect a
defect when the lane moves with no test added: that rule is about a lane getting
*slower*, and this is the counter-example.

It read **120.29 s over 3,538, 116 deselected** at the solve
speedups, idle, 2026-09-04 — six tests more than the reading below it and 1.12 s
under it. The six are the identity pins on the three changes, and the reading is
worth having precisely because it does **not** move: all three speedups are in a
pass over the real candidate pool, and the fast lane never builds one. A lane that
had got faster here would have meant a guard stopped running, not that the solve
got quicker. The wall clock those changes did move is in
`curation/GALLERY.md`'s *Three prunes in the swap loop, and all three are sound*.

The **slow** lane read **6:54 (414.76 s) over 3,648, nothing skipped** at the
`exp_smoothing` drop, idle, 2026-09-04 — seventy-four tests more than the reading
below and seven hundredths of a second over it, which is the closest two readings of
this lane have ever landed. All seventy-four are the nested-subparser split's
`test_nested_verbs.py`, which the fast lane had already priced at 1.55 s; the slow
lane's own clock did not notice them. The drop itself added no test, moved one to a
derived floor and one to a derived colormap count, and changed nothing measurable —
which is the point of recording it: a roster ruling that shrinks the accepted modes
from fourteen to thirteen does **not** show up as a lane that got cheaper, because
what the guards read is the stores and the stores did not move.

It read **6:54 (414.69 s) over 3,574, nothing skipped** at the
line-ending guard, idle, 2026-09-04 — the first slow reading since the `run_layout`
extraction's 7:14 over 3,552, twenty-two tests later and twenty seconds under it. Two
of the twenty-two are `test_line_endings.py`; the other twenty came in with the merges
between the two readings. The guard costs ~1.1 s, one `git ls-files --eol` sweep of the
tree shared by both its tests, which is what puts it in this lane rather than the fast
one. Nothing here moved the digit: a slow lane flat across twenty-two added tests is
the expected shape, and it is recorded because the figure above it had gone stale.

It read **121.41 s over 3,532, 116 deselected, nothing skipped** at the nested-subparser
split, idle, 2026-09-04 — seventy-four tests more than the reading below and 1.55 s over
it, which is noise. All seventy-four are `test_nested_verbs.py`, and seventy-one of them
are one parametrised guard: one representative command line per nested `curate` verb,
parsed and compared against the namespace it resolved to before the split. Each costs a
whole `build_parser()`, which is why seventy-four tests are 1.55 s rather than nothing,
and why they are still fast-lane tests — a parser build reads no store and makes no
picture. The two extra deselected are not theirs: they are `test_line_endings.py`'s two
slow guards, which landed between this reading and the one below it.

It read **119.86 s over 3,458, 114 deselected, nothing skipped** at the seconds-share
fix, idle, 2026-09-04 — four tests more than the reading below and 0.56 s over it,
which is noise. Three of the four are the ruling's own guards and the fourth pins
that every prefix of a weighted round leans the way the round does.

It read **119.30 s over 3,454, 114 deselected, nothing skipped** at the rare-cell mine,
idle, 2026-09-04 — three tests more than the reading below, all three the guards on
`curate depth --near-places`, and 2.5 s under it. Flat, and taken after four render
legs and four merges had put 16,731 rows into the candidate ledger: the store grew
8.6% and the lane did not move, which is the first reading that says so since the
tier-root redirect took the ledger out of the lane's price.

It read **121.82 s over 3,451, 114 deselected, nothing skipped** at the wrapup, idle,
2026-09-04. Nine tests more than the reading below — five for the lane's own new
reporting, one for the pool, three for the recorded gallery — and 0.23 s under it,
which is flat.

**And it closes the 57.** They were an interpreter without `torch`. Masking `torch`
and `timm` on this tree collects 3,377 / 3,486 with 109 deselected and runs `3371
passed, 14 skipped, 109 deselected`; subtract the two guards the help grouping added
and that is **3,369 passed / 14 skipped / 109 deselected**, the reading three entries
down, to the unit. Eight modules gate on `torch` with a module-level
`importorskip` and five on `PIL`, and a module-level `importorskip` is not a skip of
that module's tests — the module never imports, so its tests are missing from the
collected total rather than counted. Those eight carry 65 fast tests and 5 slow ones,
which is the 57 (65 less the 8 that came back as skips) *and* the 114 → 109 fall in
the deselected count that made the reading look like a different suite. `def test_` is
2,556 at every commit from `9a62672` to here and `data/palettes` holds 901 colormaps
at every one of them, so neither the suite nor `test_colormaps.py` ever moved. **The
second half of that stopped being true on 2026-09-05**: `classic-pairs-2026-09` put
120 maps in the directory and therefore 120 parametrizations into that module, which
is the first time in this log the colormap guard has moved a count. A reading across
a drop is not comparable with one before it, and the drop is the whole difference. The
lane now prints a red line naming the missing import; before this it went short in
silence, which is the only reason a reading like that could be written down.

It read **122.05 s over 3,442** at the help grouping, idle, 2026-09-04 — 3.55 s over
the reading below, across the two guards that prompt added, which is what a change that
only regroups `--help` text should cost. **The collection count is the interesting
half.** With those two guards stashed the tree collects **3,440** — the `cli` split's
figure, three entries down — and not the **3,383** the reading below records, though
none of the three commits between them adds a test function. So the 57 the warning
below calls unaccounted for came back, on an unchanged suite, pointing the other way:
that warning says `9a62672` and HEAD both collected 3,375 the evening it was written,
and HEAD collects 3,440 today, twice in a row. `tests/test_colormaps.py` parametrizes
over the colormaps on disk and is the one collection here that data could move — it is
902 today and `data/palettes` has held 912 tracked JSONs across all four commits, so it
is not that. Left unexplained rather than edited — and it was right not to be: the
entry above resolves it, and this one had already narrowed it to everything except the
interpreter.

It read **118.50 s over 3,383** at the manifest guard, idle, 2026-09-04 — against
**177.48 s over the same 3,383**, measured the same evening on the same idle box by
checking `9a62672` back out into the tree and running it. A third off, and none of it
an optimisation: `test_ledger_tracking`, `test_candidate_ledger.isolated` and
`test_hunt` redirected the ledger store **per accessor**, and no accessor list named
the supply sidecar or the expressed readout that `prune` reads through `rank_key`. All
three had been reading this machine's real 67k-row supply and its real coverage vector
on every test, and would have failed outright on a clone that has neither. Redirecting
at the tier roots moved those two as well; they are written empty now, and the 59
seconds went with them. The three commits before it — the durables split and the three
top-level layering fixes, 49 modules of largest SCC down to 44 — moved the lane from
177.48 s to **175.40 s**, which is to say not at all, which is what an import-graph
change should cost.

⚠ **The reading below does not reproduce and has not been edited.** `9a62672` collects
**3,375 selected / 3,484 total** today and runs 3,369 passed / 14 skipped; the line
below records 3,440. Nothing since has added or removed a test — HEAD collects the same
3,375. The 57 are unaccounted for.

It read **170.30 s over 3,440** at the `cli` split, idle, 2026-09-04 — 0.9% over the
reading below, across two more collected tests, one of which is the guard this split
added: that no two modules of the package define one name and no module is named after
a name the package must resolve. The reading is worth the line for the same reason the
ledger split's was: 10,181 lines became twenty-two modules, every handler now reached
through a `__getattr__` instead of off the module, `build_parser` builds by importing
nineteen modules rather than running one function, and the lane did not notice. The
slow lane was not re-run and its **7:14 over 3,552** stands.

It read **168.70 s over 3,438** at the census follow-ups, idle, 2026-09-04 — the same
3,438 as the reading below, 1.2% apart, which is noise and not a figure to restate.
The commit renamed a command, moved twenty-five run directories into a map and
re-routed one constant; none of it added or removed a test, and the lane says so.

It read **167.79 s over 3,439** at the candidate-ledger split, idle, 2026-09-04 — 0.7%
over the reading below across the one test the split added, which is the guard that no
module of the package is named after something it exports. Worth the line because of what
the reading is *of*: 2,738 lines became a package of seven modules and a resolving
`__init__`, every name now reached through a `__getattr__` rather than off the module
directly, and the lane did not notice. The slow lane was not re-run and its **7:14 over
3,552** stands.

It read **166.63 s over 3,438** fast and **7:14 over 3,552** slow at the `run_layout`
extraction, idle, 2026-09-04. The fast lane is flat — 0.5% over the reading below
across one more test, which is the packaging guard. The **slow** figure is the one
worth having: it had not been re-run since the viewport sampler, where it read 6:27
over 3,388, so this is 12% more clock over 4.8% more tests. Every reading between
those two was a fast-lane reading, which is how a slow lane drifts a tenth without
anybody seeing it. Re-run the slow lane on its own schedule, not only when the fast
one moves.

Both are measured, not estimated. The fast lane is **142.06 s over the 3,307 it
holds**, of 3,423 there are — on this machine, idle, 2026-09-02, at the commit
that gave the depth record its autolevel stamp. It read **140.12 s over 3,302**
two commits earlier, and **139.0 s over 3,276** at the commit that added the
viewport sampler. The slow lane has **not** been re-run since that last one and
its reading stands: **6:27** over 3,388 tests. So the fast lane is flat across 31
more tests — 3.1 s and 2.2% apart — and this entry is re-measured rather than
moved.

It read **156.01 s over 3,336** immediately after the phoenix band sitting landed
200 rows across both finished-render stores, idle, 2026-09-02 — 9.8% over the
figure above across 29 more tests, which is the per-test cost holding flat and is
recorded here because it is a reading taken right after a store grew.

It read **157.21 s over 3,345** at the end of the `MINE_diverse_0903` leg, idle,
2026-09-03 — four more tests than the reading below and 2.2% *under* it, taken right after a
session that put **18,940 candidates into the ledger (182,235 -> 201,174 recipes)** and grew
the score sidecar past half a million rows. Two store growths in one day and the lane has not
moved for either.

It read **170.45 s over 3,362** at the texture-route tidy, idle, 2026-09-03 — 4.0%
over the reading below across **one** more test. The new guard is 1.49 s of that and
the rest is data: the same session put 13 revision rows and 13 crops into
`smooth_render` and 23 entries into the texture register. Worth having because the
guard was **13.88 s** before one stub — `candidate_ledger.prune` reaches
`intake.read_scores`, which the ledger's isolation fixture does not redirect, so a
three-row store in `tmp_path` still swept this machine's real 428,000-row location
score store, twice. That is `tests/README.md`'s rule about a guard taking a budget
rather than a store, hiding one call deep inside production code rather than in the
test — every merge test in `tests/test_ledger_tracking.py` pays 4.5-10 s of the same
read today.

It read **165.17 s over 3,420** at the reframe defaults, idle, 2026-09-03 —
fifteen more tests than the reading below and **1.4% under** it. The thirteen new
guards cost 1.4 s between them: they decide two defaults off ledgers that are two
rows each in `tmp_path`, and neither reads a store. Nothing grew this session.

It read **165.85 s over 3,437** at the spiral share cap, idle, 2026-09-04 — 0.6%
over the reading below across **23 more tests**, which is thirty-one new guards over a
new location store, a new solve rule and the seconds-share conversion costing this lane
nothing.

It read **164.85 s over 3,414** at the `render_cv` delete, idle, 2026-09-04 — 0.2%
under the reading below across **six fewer** tests, which is `test_render_cv.py`'s six
fast guards going with the harness. Worth having only for what it says about the two
guards that changed underneath it: `test_render_dose` and `test_render_grade` now
*derive* the lineage deal instead of reading the written one, and that cost the lane
nothing because both are slow-lane and the derivation is the session's one pool read
either way.

**The reading before it, 173.35 s over the same 3,414, was taken beside a second
copy of itself** — a backgrounded lane that had not finished when a foreground one
started — and is 5.2% over this one. That is the "measure it on an idle machine"
paragraph below priced at its cheapest: the other process does not have to be a
render leg, and two pytest lanes are enough to move the digit.

It read **167.53 s over 3,405** at the spiral probe, idle, 2026-09-03 — nine more
tests than the reading below and **1.8% under** it, taken right after the spiral
store's first sitting landed: 500 verdicts, 472 KB of rows, and the store went
from four tracked files to five. The nine new guards are 3.0 s of it. A label
store's *first drop* is the growth this lane has historically noticed, and it did
not notice this one — five hundred rows is three orders off the ledger the seven
ledger guards sweep, which is the thing that actually prices this lane.

It read **170.58 s over 3,396** at the spiral attribute store, idle, 2026-09-03 —
4.1% over the reading below across thirty-five more tests, of which thirty-one are
new guards over a store that did not exist that morning. A fourth label store,
a fourth `--head`, and the lane did not notice: an attribute store is four tracked
files and a hundred pinned rows, which is nothing beside the corpora the seven
ledger guards already sweep.

It read **163.85 s over 3,361** at the `--draw-cells` build, idle, 2026-09-03 —
1.9% over the reading below across twenty more tests, taken right after a
ten-minute near-band leg merged 4,204 candidates and the prune took the ledger
194,037 -> 198,241 -> 194,114. Another merge, another flat lane.

It read **160.75 s over 3,341** at the weights-v6 flip, idle, 2026-09-03 — 3.0%
over that across five more tests. This one is worth having because of what had just
happened to the stores it reads: the two label corpora had grown to 11,272 pictures,
the render cache to 11,272 crops, and **the candidate ledger's score sidecar had
gone from 306,431 rows and 150 MB to 486,666 rows and 239 MB** in the same session,
because a judge flip writes a second full set of readings beside the first and
retires nothing. That is the largest single-session growth this store has seen since
the 2026-08-29 episode above, and the lane did not move for it. So a judge adoption
is **not** one of the things that prices this lane, and the seven guards that sweep
the ledger read it through `conftest.tracked_ledger` once whatever it holds.

**A reading taken beside a leg is a reading of the leg.** The same lane read
**404.6 s over 3,281** earlier that day with a mining leg holding the render pool,
which is 2.9x the idle figure over the same tests. That is the paragraph below
about an idle machine, priced: before believing a lane has slowed, check what else
is on the box, and re-run it alone.

It read **3,371 tests in 6:41** with the fast lane at **136.2 s over 3,260**,
idle, 2026-09-02, at the commit that swept `artifacts/`. That reading was taken
**right after** 41.5 GiB
and 31,426 paths came off the hot tier and 7.4 GiB moved to the archive — the
conditions the paragraphs below say to suspect — and it did not move: it is 16%
over the 5:45 below across 219 more tests, which is the per-test cost holding
flat. So the 2026-08-30 doubling stays attributed to the disk settling and not to
anything a sweep does on its own.

The reading it replaces was **3,152 tests in 5:45** with the fast lane at **98.3 s
over 3,039**, idle, 2026-08-31, at the commit that cut the lane — which is still
the entry to read first, because that prompt found the lane was never a broad
tax: the **top eighty tests were 490.6 s of the 563.5 s** it started at, and the
other three thousand were 72.9 s between them. It came down by collapsing
derivations paid many times over and by taking one pixel-exactness pin off
production's raster, and **no guard was deleted or moved lanes**.
`tests/README.md` carries the table and the reasoning; the one worth knowing
here is that `served_locations.build` was asking `current_pass`
once per row instead of once, which was ~10.5 s on every merge, seating and
gallery build in **production** and not only under test.

The figures below are the history that got it here, and they are kept because
each is a way this lane has moved without code moving.

It read **3,121 tests in 8:23** at the commit that added `renders deploy`, idle,
2026-08-30, with the fast lane at 116.8 s.
**It read 3,126 in 14:26 on 2026-08-31**, idle,
at the commit that closed the pool re-score — twice in a row (12:45 then 14:26) and
over five *more* tests than the 8:23. That is the third time this lane has moved
without code moving; the store that grew in between is the release pool's, whose
16,029 rows were rewritten and whose 3,484 candidate pictures were put back on
disk that morning. The entry here read 64.3 s and 7:20 at
`0b53e15`, then **3,101 in 16:25 with the fast lane at 290-320 s** at `9560862`
later the same day; what happened in between and what undid it are the next two
paragraphs, and they are why a stale figure here is worth correcting rather than
living with.

**A third move on 2026-08-30 went the other way and is recorded unsolved.** The
fast lane went 163.6 s to 289.8 s and the slow lane 8:22 to 16:25, over the same
tests on an idle machine, right after 194,058 levelled colormap directories and
14 GiB came off `artifacts/` — so the stores got *smaller*. It is not a test: the
ten slowest sum to 99 s on both sides of the sweep, and the extra ~130 s is a
~45 ms constant spread across all 2,998. It is not that day's code either, which
was checked by measuring 317.5 s at `7383b63` with the working tree stashed.
Suspected: NTFS metadata after a bulk small-directory delete. So also re-measure
after anything that moves hundreds of thousands of paths, and suspect the **disk**
as well as the stores.

**And it came back on its own, later the same day, with nobody doing anything to
it.** The slow lane read 8:23 and the fast lane 116.8 s over twenty *more* tests
than the 16:25 and 289.8 s above — the slow lane is back to its pre-sweep 8:22 to
within a second and the fast lane is well under its pre-sweep 163.6 s. No code
was reverted and no store moved between the two readings; the only thing that
happened in between is that hours passed. That is the strongest evidence the
doubling was the disk settling after the delete rather than anything in this
repository, and it is the reason to re-run a slow lane before believing one. It
is still not *proven*, so the paragraph above stays.

## On a parallel runner

`pytest-xdist` was measured rather than argued about, and the answer is still
**no** — but the reasons have changed, so here is both the old measurement and
what is left of it.

| 2026-08-26 | serial | `-n 4` | `-n 8` |
| --- | --- | --- | --- |
| fast lane | 44.7s | 37.3s | 39.7s |
| full lane | 160.3s | 79.4s | 76.4s |

The fast lane gains seven seconds at four workers and gets *slower* at eight,
because per-process imports are paid again and torch is most of them. That has
not changed and it is the lane that gets run all day.

The deciding fact was never the clock. Under xdist the held-back count **does not
print**, and neither does the deselection: `pytest_collection_modifyitems` and
the stash live in the workers, so the controller reports `4 passed` where the
serial run reports `4 passed, 2 deselected` and names the number. A runner that
makes the lane go quiet is buying seven seconds with the one property the lane
exists for.

That objection does not reach `--slow`, which deselects nothing and so has
nothing to go quiet about — which is why it was worth asking again at 18 minutes.
The answer is still no, for a new reason: **what is left of the lane does not
parallelise.** 160s of the 440s is `colorize` and `autolevel_identity` driving the
engine, and the engine is rayon across all twelve cores already — three concurrent
`fractal-engine.exe` were measured at 126s against 105s, a fifth and not a third,
because they contend rather than spread. Another 40s is one ledger read that every
worker would simply pay again, and 6 GB apiece with it. A dependency that bought a
fifth of a third of the lane, at four copies of a six-gigabyte read, is not a
trade.
