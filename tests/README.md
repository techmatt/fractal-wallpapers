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
sidecars, the supply sidecar, the expressed readout and every durable copy all
address a root, so setting the two moves all of them at once. **Set them with
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

**One accessor still has to be patched, and it is the tracked half.**
`candidate_ledger.store.manifest_dir()` resolves off `repo_root()`, not off a
tier, and there is no root to set because `repo_root` is imported *by value* into
three dozen modules. That is the one path a fixture can miss while looking
complete — so `conftest` hashes every git-tracked `*manifest.json` at session
start, re-hashes at session finish, and fails the run naming any that moved
(`pytest_sessionfinish`). 20 files, 104 KB; the cost does not show up against a
three-minute lane. `signatures.sidecar_path` is patched in those fixtures for an
unrelated reason: to undo the autouse `no_signature_sidecar`, which the roots
cannot reach because the function has already been replaced.

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
