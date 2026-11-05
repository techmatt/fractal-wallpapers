# tests

The test suite, including the guard that keeps this history text-only and small.

```
python -m pytest                                    # the fast lane, ~2m15s
python -m pytest --slow                             # every test, ~8m
cargo test --manifest-path engine/Cargo.toml        # ~7s warm, ~28s cold
```

Run pytest with the checkout's `.venv` interpreter, on `.[dev,models]`, with a release
engine built (`cargo build --release --manifest-path engine/Cargo.toml`); the walk tests
skip without one.

`cargo test` builds the crate at `opt-level = 2` (`[profile.test]` in
`engine/Cargo.toml`): the tests render, and unoptimized they run eight times longer.

## The two lanes

`--slow` is the whole suite; the default run holds back the ~160 tests that do real work.
A test earns `@pytest.mark.slow` by about a second or more of a render, a training loop,
or a store sweep; arithmetic stays fast however much of it there is. **A guard may also
be weakened or deleted for speed when the trade is named and priced** (what stopped being
covered, at the site and in the report, with the seconds it bought). The marker, the flag
and the held-back line live in `conftest.py`; `CLAUDE.md`'s *The two lanes* is the rule.

A flag added to a nested `curate` verb fails `test_nested_verbs.py` until its `SURFACE`
entry names it: fix the table, never the guard.

### The line is the point of the arrangement

Every run that holds anything back says how much: a lane that went quiet would be guards
nobody noticed had stopped running.

### Measure the fast lane after marking, not before

Guards share cached derivations (`absolute_paths_in_records`, `shipped_render_cache`,
the engine fingerprint's probe set, any `functools.cache` in production code), so
marking one slow can hand its cost to whichever sibling reads the cache next.

## A lane sharing the box with a render leg

`CLAUDE.md`'s rule is to run the lane on an idle box, after a leg rather than beside one.
What it rests on:

- **Beside a leg the lane is killed on commit charge**, around 77% with no summary or
  traceback: the leg's parent holds ~3.3 GB and each worker ~0.9 GB (the commit limit is
  `models/render/README.md`'s).
- **What kills it is the parent, not the worker count.** A `curate votes build` can share
  the box (its parent streams the ledger through `candidate_ledger.by_key`); a solve
  cannot (its release leg holds the pool).
- **A lane that survived beside a leg is still not a timing** (~3x slower; a `cargo
  build` beside it ~2.5x).
- **A guard that reads the wall clock turns red under load, not slow.** Declare loops
  too long to bind (`loop_seconds=1e6`) and count work in batches, not minutes
  (`time.monotonic` on Windows ticks at 15.625 ms).
- **Commit charge drifts upward on uptime alone**, ~4 GiB a day, reclaimed only by a
  reboot; the symptom is a launch dying on `WinError 1455`. Reboot before an overnight if
  uptime is past a week.

## What "the fast-lane count" means

`pytest -q` ends on a line of the shape `P passed, S skipped, D deselected`, and the count
this project records is **`P + S`, the number pytest selected**, with `D` beside it:

- **Selected** is every test collected and not held back. It is what the clock is a price
  for, so a reading gives it and the clock together or gives neither.
- **Deselected** is the slow lane and nothing else: `conftest.pytest_collection_modifyitems`
  removes exactly the `slow`-marked and says how many.
- **Skipped** is a test that was collected, ran its guard and declined: no release engine
  at `engine/target/release` (asked through `engine.engine_path`), a missing shipped file,
  or an optional import absent at call time (below).
- **Not collected** does not appear in the total at all, and it is the trap. A
  module-level `pytest.importorskip` stops the module being imported, so its tests are
  absent rather than skipped. The lane prints a red line naming those modules and what is
  missing (`conftest.SKIPPED_WHOLE`).

### A reading is comparable only against the same install

**Compare a reading only against another on `.[dev,models]` with a release engine
built**; an interpreter without `torch` silently collects a smaller suite. **And the same
kind of run**: `--slow`'s durations minus the slow-marked rows is not a fast lane, because
a shared derivation is paid by whichever test reads it first, which differs between
lanes. To attribute your own change, re-baseline on the same tree (stash, take the lane,
restore, take it again, clean `git status`); to answer *box or tree*, profile one file.
To split a count delta (your tests or the tree's), `git stash -u` then `pytest
--collect-only -q`: a count needs no worktree, a clock does.

### The lane refuses the wrong interpreter at the door

Where the checkout holds a `.venv` and pytest is not running on it, `pytest_configure`
raises a `UsageError` naming the interpreter it wants (CI has no `.venv` and never sees
it). `FRACTAL_WALLPAPERS_ANY_INTERPRETER=1` measures on another one on purpose. Without
it, `pythonpath = ["src"]` lets any interpreter collect and pass a smaller suite.

### An extra reaches a lane two ways, and they are different faults

- **A module-level import aborts the whole lane, not its own file**: pytest reports the
  uncollectable module as a collection error and stops (`Interrupted: N errors during
  collection`, nothing run). It is visible in the source, so `test_lanes.py` sweeps every
  test module for a bare import of an optional extra; the fix is `pytest.importorskip`.
- **A call-time import is visible nowhere**: production code carries lazy `import torch`
  inside function bodies, reached several calls deep from a test that never names it.
  `conftest.pytest_runtest_call` catches `ModuleNotFoundError` for a genuinely absent
  optional dependency and skips. On `.[dev,models]` it is inert.

Both guards read their population from `cli.EXTRA_FOR` less `dev`.

## Shared readings of the tracked records

`conftest.py` holds session-scoped fixtures over the tracked records: `shipped_labels`,
`shipped_scored`, `shipped_tile_plan`, `shipped_render_cache`, `shipped_label_pool`,
`shipped_cyclic_maps`, `distillation_rows` and `tracked_ledger`. Each costs a second or
more and is asked by more than one file. Fixtures rather than module caches, so the
sharing is opt-in: a test that redirects a store never asks and cannot be handed the
tracked corpus. Nothing writes to them. A new test file reaches for these first.

### `shipped_label_pool` hands back fresh pictures on every call

A factory, because `render_deploy.sides_for` assigns `picture.side` **in place**: each
call returns fresh `Picture`s (~10 ms against ~4 s to derive). Its `assignment` is the
real `render_folds.assignment` over the shared pool, never a second deal.

### `tracked_ledger` is the dear one and the one to reach for by reflex

`.rows`, `.scores`, `.pool`, `.costs` and `.refused`: one reading, ~40 s and ~6 GB
resident, for every ledger guard. **Never call `candidate_ledger.read()` in a test.** It
unsets the hot root while laying the pool out, so a redirected module cannot make it read
an empty tree, and skips where the ledger is not backfilled (every machine but Matt's).

## Redirecting a store: at the roots, never per accessor

There are exactly two roots and everything under `artifacts/` resolves through one of
them. `paths.HOT_ROOT_VARIABLE` (`FRACTAL_WALLPAPERS_HOT_ROOT`) and
`paths.ARCHIVE_ROOT_VARIABLE` (`FRACTAL_WALLPAPERS_ARCHIVE_ROOT`) are the whole redirect:
the candidate ledger's row files, the flatness and signature sidecars, the supply sidecar
and every durable copy address a root, so setting the two moves all of them. **Set them
with `monkeypatch.setenv` and redirect nothing else you do not have to.**

A per-accessor redirect is complete only against the call graph the day it was written:
they have overwritten tracked manifests, read this machine's live sidecars, and (moving
only the tracked tier with `records.use(tmp_path)`) written run directories into the live
`artifacts/curation/runs/`. **A store has two tiers; a fixture is not done at one.**

### Two accessors still have to be patched, and both are the tracked half

- `candidate_ledger.store.manifest_dir()` resolves off the tracked tree
  (`records.default_root()`, off `repo_root()`), not off a tier, and `repo_root` is
  imported by value into dozens of modules, so there is no root to set.
- `candidate_ledger.ratchet.log_path()`, for the same reason and with a wider blast
  radius: `prune` writes it at the end of every merge. Its redirect is **autouse**
  (`conftest.no_tracked_ratchet`), because the hazard belongs to `prune`, not to the tests
  that call it today. The guards that mean to read the tracked log take the
  session-scoped `tracked_ratchet_log` fixture and pass the path in.

### Autouse doors: the supply and signature sidecars

- `conftest.no_live_supply_sidecar` is autouse for the same reason: production code
  reaches `intake.read_scores` through `solve.ranking_for` and `curation.rank_key`, and
  `artifacts/curation/supply_scores.jsonl` exists on one machine. **It redirects one path,
  not the accessor**: only the answer that *is* this machine's live sidecar is swapped,
  so a test that moved `HOT_ROOT` to its own `tmp_path` still reads the store it wrote.
  Better still, a test hands the order in (`solve(order=...)`) and never reaches the door.
- `conftest.no_signature_sidecar` is autouse too, and the roots cannot undo it because
  the function has already been replaced: a fixture that wants a real signature sidecar
  patches `signatures.sidecar_path` back explicitly.

### The backstop hashes every tracked manifest twice a session

`conftest` hashes every git-tracked `*manifest.json` (discovered, so a new durable is
covered) plus the names in `HELD_STILL` at session start, re-hashes at finish, and fails
the run naming any that moved (`pytest_sessionfinish`). The same hook asks it of the
regenerable tier: `LIVE_LEG_DIRS` lists the immediate children of
`artifacts/curation/runs` at start and finish, and a name that appeared fails the run.
**A name at a fixed depth, never a walk**: one `scandir` twice a session. One mechanism
and two snapshots, deliberately, under one heading and one writer; `test_lanes.py`
guards the detector, including that it stays a `scandir`.

## Where the time goes

A slow lane is a handful of tests, never a broad tax. When it grows, ask **which store
grew**, **which derivation is paid twice**, and **what every test pays**, and answer from
a durations list (`--durations=0 --durations-min=0` summed by file), never a collection
summary.

What dominates today, in order:

| cost | what |
| --- | --- |
| ~40 s | the one reading of the candidate ledger (`tracked_ledger`), wherever it lands first |
| ~30 s | `test_autolevel_identity`'s pinned probes, pinned to production geometry |
| ~10 s each | `test_render_head`, `test_distinct`, `test_candidate_ledger`, `test_hunt` |
| ~7 s each | `test_train`'s two epochs, `test_renders`' regeneration, `test_ledger_tracking`'s merges |

`test_ledger_tracking`'s merges are honest: each reads the release sidecar once, as
production does.

### A cost paid once per test scales with the suite, and hides from every reading

A growing store steps the lane the day it grows; a per-test cost grows milliseconds at a
time and never reaches a durations list (the case was `tmp_path_factory.mktemp` in an
autouse fixture, quadratic in the test count; `conftest`'s comment at its `tmp_path`
override has the numbers). Only a by-file sum of every test finds it.

### A derivation paid twice is the thing to look for

Often production code: a pure function recomputed inside the loop over the rows it
depends on, or a `functools.cache`d join over a store a synthetic test world cannot hit
(stub it empty, as a clone reads). A profile of one slow test finds it.

### A lane that moves right after code landed is the code until measured otherwise

**Re-run one slow file under a profile**, twice and beside an untouched control, not the
whole lane hoping for a quieter box. The decisive check is a `git worktree` at `HEAD`
with `FRACTAL_WALLPAPERS_HOT_ROOT` on the real store. A memo that hides a production cost
carries a `forget_*` for tests that redirect the tree (`hunt.forget_recorded_prices`).

### A count is not a cost

**Collected-item share predicts nothing about run time.** `test_colormaps.py`'s
parametrize over `data/palettes` is about a fifth of the count and ~0.1 s of the clock. A
count predicts what a reading is comparable with, which is why
[the lanes' own count](#what-the-fast-lane-count-means) is kept: a colormap drop moves
both counts.

### The candidate ledger is the thing that grows

The store a lane pays for most, so re-measure after a **merge**. `candidate_ledger.prune`
runs inside `merge`, bounding rows per (location, mode) by `RETAIN_PER_PAIR` plus the
protections, but a bound is not a licence: **the ledger is read once a session**
(`conftest.tracked_ledger`), and **a guard that sweeps it takes a budget**, stating the
constant, its measurement and an assertion the budget filled (`test_hunt.SAMPLE`).

Also rejected on sight: full bootstrap resamples for a point statistic (reduce, say so
at the constant), a sweep of every tracked file (palette corpus; reject cheaply first), a
pure read of tracked data per test (make it a module fixture), and a store redirect that
misses part of the store.

## Reading and reproducing a CI red

CI runs `pytest --slow -rs` on Ubuntu, macOS (Apple silicon) and Windows after
`uv sync --extra dev --extra models --extra solve`, so every job has torch and none has
fetched weights or a store; a test that needs the shipped heads skips on a missing file
rather than failing.

The repository is public, so a red is readable without `gh` and without admin rights:
`api.github.com/repos/techmatt/fractal-wallpapers/actions/runs` gives the runs and
`runs/<id>/jobs` gives **step-level** conclusions. Job *logs* need admin and 403; the
step conclusions are enough to say which step failed on which job.

**Reproducing a failed Test step is a fresh clone with no store and no weights**, which
is what a runner has: `git clone` the checkout into a scratch directory, copy the release
engine binary into its `engine/target/release/`, set `FRACTAL_WALLPAPERS_HOT_ROOT` and
`FRACTAL_WALLPAPERS_ARCHIVE_ROOT` to empty, and run `pytest --slow` there with this
checkout's interpreter. Reproducing the lean install is a mask at `sys.meta_path`
(`test_base_install.py` carries the finder) blocking `torch,torchvision,timm` and **not**
`numpy`, which `scipy` brings.

## On a parallel runner

`pytest-xdist` is not used. Under it the controller prints neither the deselection nor
the held-back line (the hooks run in the workers), so the fast lane goes quiet; and
`--slow`'s big costs drive an engine already rayon across every core, plus a ~6 GB
ledger read every worker would pay again.
