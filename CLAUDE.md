# Working in fractal-wallpapers

A Rust engine renders escape-time fractals; Python chooses where to look, how to color
it, and which finished images survive, with small neural judges trained on human labels.
It is the companion repo to a tutorial article, so it is written to be read. `README.md`
is for visitors; this file is the rules an executor here is held to. Each locked
convention is Matt's ruling, and changing one is his call.

## The naming rule

**Nothing ships under a name the article wouldn't teach.** Names say what a thing
*does* (`coloring/`, `discovery/`, `curation/`, `labeling/`); a name that needs a
paragraph of history is the wrong name. Vocabulary from earlier private versions of this
project does not transfer: rename on the way in.

**Comments and docstrings illustrate a shape, never a live instance.** Write
`<head>.<sheet>.json`, not a real drop's name, or a grep for the live name answers out of
a comment about another.

**Cite a heading and a file, never a line number**: `curation/GALLERY.md`'s *What a pass
costs is one store*, not `GALLERY.md:1487`, which drifts after the next edit above it.

No test here enforces this; the guard is `builder/vocabulary.py` in the `fractal-website`
checkout, swept by its `builder/checks.py`.

## Locked conventions

### Code shape

- **Rust makes every pixel; Python never renders.** Python reaches the engine only
  through `src/fractal_wallpapers/engine.py`; no other module shells out to the binary
  or computes image data.
- **Everything runnable is a `fractal-wallpapers` subcommand.** There is no `scripts/`
  and never will be. One `cli/<group>_commands.py` per command group, holding its
  handlers and parser; `cli/__init__.py` is the list of them plus `main`. The
  `_commands` suffix is load-bearing and handler names resolve through `__getattr__`,
  never re-exported: `cli/__init__.py`'s docstring has why.
- **Records are JSONL**: UTF-8, one object per line, an integer `schema` field from the
  first row. A label row carries its full join (the label *and* the complete render
  parameters), never split across files. Every random draw is seeded, the seed recorded.
- **Cross-platform by construction**: `pathlib` only, no absolute paths in tracked code.
  Windows process handling (job objects, priority classes) lives in
  `src/fractal_wallpapers/process_control.py` and nowhere else. A batch subcommand takes
  a **manifest file**, never hundreds of paths as arguments.
- **Formatting is not negotiable**: `ruff` lints and formats Python at line length 100;
  `rustfmt` and `clippy` govern the crates. A repo-wide reformat should never become
  possible.
- **Line endings are LF**, and **anything writing a tracked text file opens it
  `newline="\n"`**. CRLF drift is invisible to `git status` and `git diff`, and Git
  Bash's `grep` sees a CR on every line of a pure-LF file: `git ls-files --eol` is the
  only detector, `tests/test_line_endings.py` the guard.
- **Search with `git grep` (or `rg`), never `grep -r` from the root**: the checkout
  holds ~100 GB of untracked files, and `grep --include=*` ignores `.gitignore`.

### Installs

- **The base install stays torch-free.** `pip install -e .` buys the engine, the walk,
  the supply engine and the labeling rig; `fetch-weights --check` runs on it, so its
  whole import graph is stdlib (why `models/roster.py` exists apart from `ship`).
  `tests/test_base_install.py` proves it in a subprocess with those imports refused.
- **`dev` is the suite's install**: `numpy` and `pillow`, **never `torch`,
  `torchvision` or `timm`**. A test reaching one of those skips rather than fails;
  `tests/test_lanes.py` (module-level imports, which abort the whole lane) and
  `conftest.pytest_runtest_call` (call-time imports) enforce it.
- **CUDA is opt-in, never the default.** `models` is CPU torch everywhere; `cuda` is
  cu124 and conflicts with it, so one environment holds one torch (README's *Install*).
- **Weights come from GitHub Releases, not LFS.** `fetch-weights` reads
  `models/weights.json` (head → release tag, asset, sha256), downloads into
  `models/<head>/` and verifies the hash. `roster.TAG` is the one spelling of the tag,
  and a published tag is never moved (`models/README.md`).

### What git tracks

- **Git history stays text.** `tests/test_history_purity.py` fails the build on a
  tracked file that is binary by nature, over `MAX_TRACKED_BYTES` (2 MiB, "the per-file
  history guard"), or a tracked *record* naming an absolute path. Each exemption list
  excuses one rule; every entry is Matt's call with its reason at the constant.
- **`.gitignore` keeps its shape**: `scratch/` and `artifacts/` (runtime output),
  `models/**/*.pt` (fetched weights), and toolchain noise; no tracked file inside an
  ignored tree. **The one exception is the published records' text**: the published
  stamps' `gallery.jsonl`, `manifest.json` and `recipes.jsonl` are un-ignored, tracked
  whole; one over the per-file cap is Matt's to rule on, never an allowlist entry.
  `index.html` is never tracked.

### Records: published, kept, discarded

The saved set is twenty-one records, all published: the `final139_*` set (general
n=1000 and nineteen collections) and `final140_general2000`. This box keeps no
unpublished record.

- **A record is PUBLISHED only when Matt names it**: a line in
  `curation.tentative.PUBLISHED` and one in `.gitignore`, held to agreeing by
  `tests/test_tentative.py`. Tracking a record's text *is* publishing it. A
  `--force-fill` record is never published (`tentative.refuse_forced`).
- **An unstamped read means `tentative.DEFAULT`** (`final139_general`), never the newest
  stamp: the twenty-one are peers. `portable.REFERENCE` (`fractal_wallpapers/portable.py`) names
  `final139_green`, as `GENERAL_CHECK` names `final139_general`. The page a person opens
  is the `artifacts/curation/viewer/` row of `src/fractal_wallpapers/README.md`'s keep
  roster.
- **An unpublished record is DISCARDED by default; keeping needs a reason.** An item that
  records a gallery to measure against deletes it once measured, and says so in its
  report. ⚠ **`curate solve record` keeps by default**: pass `--no-keep`, or run
  `curate solve release <stamp>` afterwards.
- **What is kept is `tentative.kept()`**, `PUBLISHED` plus the keep file
  (`tentative.keep_path()`), never a count of store folders. `tentative.protected_keys()`
  reads it and nothing else: preservation is a named row, never a folder existing.
- **Durability is a backup, not git**: `storage export` runs only at Matt's direction,
  and no tracked text names an export or a standing instance. Restore is
  `src/fractal_wallpapers/README.md`'s *Continuing on a fresh box*.

### Curation and labels

- **A collection's size is in `curation/targets.py` and nowhere else.** Nineteen
  collections (twelve hue families, seven modes); `curate solve run|record --collection
  NAME` take `n` from `TARGETS` and the pool from `targets.pool_for`, `--n` overrides,
  and a collection the table does not name refuses. A prompt that names a seat count is
  retyping a target.
- **Degree 6 is never labelled**: `multibrot6` and `julia:multibrot6` are the mining
  loop's generalization test. `partitions.NEVER_LABELLED` is the list; sheet build,
  ingest and both store writers refuse it. Their roots come from the viewport sampler
  alone (`plane_seeds.FAMILIES` stops at `multibrot5` unless Matt says "with pool");
  `labeling/README.md`'s *Degree 6 is never labelled* has the doors.

### Storage and the box

- **Where a file under `artifacts/` belongs is decided once per top-level name**: *hot*
  (what a live command reads), *archive* (`storage archive <name>`, restored before
  reuse), or *delete* (regenerable or unreferenced, its builder with it). A subtree that
  must move alone becomes a top-level name first. `curation` never moves, except its
  unkept pool pictures, which `storage pictures` mirrors. The tiers are
  `src/fractal_wallpapers/README.md`'s *Two roots*.
- **A picture with no ledger row is garbage**: `curate candidate-ledger orphans` lists,
  `--apply` deletes. Run it after any killed run and periodically. An unmerged leg is
  listed and never swept unread; it goes only when someone names it (`--leg <name>` or
  `--include-unmerged`).
- **The render pool is three workers at below-normal priority**, for anything that
  drives the engine (measure pass, sheet build, hunt, mine). More than three
  `fractal-engine.exe`, or any at normal priority, makes this desktop unusable.
  `engine.run` sets the priority; only the count is the caller's.
- **One pool-holding process per box.** `curate growth`, `curate solve run`, `curate
  solve record` and the slow test lane each hold the candidate pool whole (hundreds of
  MB) and never run beside each other.

## Checks to run before committing

```
python -m ruff check . && python -m ruff format --check .
python -m pytest
cargo build --manifest-path engine/Cargo.toml
cargo test --manifest-path engine/Cargo.toml
cargo clippy --manifest-path perturbation/Cargo.toml --all-targets -- -D warnings
cargo test --release --manifest-path perturbation/Cargo.toml
```

Run pytest with the checkout's own `.venv` interpreter: one gallery guard spawns
`sys.executable` and imports the package, and any other interpreter fails it in a way
that reads as a process-control bug. The walk tests need a **release** engine
(`cargo build --release --manifest-path engine/Cargo.toml`) and skip without one. A guard
asking whether the engine is built catches `FileNotFoundError` from `engine.engine_path`;
a bare call interrupts the whole lane at collection.

**`perturbation/` is the website's kernel too.** An edit there owes the website a rebake
(`perturbation/README.md`'s *Running it*), the website's own item; website items never
commit here. The website also reads this repo's docs: its `builder/checks.py` parses the
root `README.md`'s explorer links, and it cites `perturbation/README.md`'s numbered
headings, so neither is renamed casually.

**CI** runs `pytest --slow` on three OSes with torch and no weights or store; a test
needing shipped heads skips on a missing file. Reading a red without `gh` and
reproducing it locally is `tests/README.md`'s *Reading and reproducing a CI red*.

### The two lanes

`python -m pytest` is the **fast lane** and every item runs it, test written or not.
`python -m pytest --slow` runs everything; CI runs it, and an item runs it only when its
prompt names it, comparing the two lanes' collected counts when it does. The
measurements behind these rules are in `tests/README.md`.

- **Any red is a lane to read**; there is no expected failure.
- **Never repoint a census constant at today's reading.** A census that went red because
  a store deletes by design gets a ratchet (`test_leveled_identity.py` is the example).
- **Zero skips is normal; a skip is a short render cache**, a store condition (`--slow
  -rs` names them). After `label ingest`, run `renders plan` then `renders build
  --workers 3`.
- **A reading compares only with one on the same install** (`tests/README.md`'s *What
  "the fast-lane count" means*): an interpreter without `torch` silently collects a
  smaller suite, and `conftest` prints a red line naming the missing import.
- **Measure on an idle box, literally**: beside a render run the lane is killed on commit
  charge. A test whose claim is not about time never reads the wall clock.
- **A lane that moves right after code landed is the code until measured otherwise.**
  The decisive check is a `git worktree` at `HEAD` with `FRACTAL_WALLPAPERS_HOT_ROOT` on
  the real store; with no test added, ask which store grew, which derivation is paid
  twice, and what is paid once per test.
- **A fixture redirects a store at the tier roots, never per accessor.**
- **Read the candidate ledger once a session**, through `conftest.tracked_ledger`; a
  direct `candidate_ledger.read()` adds ~40 s. A guard sweeping the ledger takes a
  budget: the constant, its measurement, and an assertion that it filled.
- **`@pytest.mark.slow` is for about a second or more of real work**: a render, a
  training loop, a store sweep; arithmetic stays fast however much there is.
  `conftest.shipped_cyclic_maps` is the model of a shared read. `data/palettes` is
  parametrized, so a colormap drop moves both counts.
- **A guard may be weakened or deleted to make a lane faster**, but the trade is **named
  and priced**: what stopped being covered, at the site and in the report, with the
  seconds it bought (`--durations=0 --durations-min=0` summed by file). Prefer thinning a
  claim (a smaller sample) to dropping one (fewer modes), and measure after marking.
- **The fast lane prints how many tests it held back**, and that line is the point:
  `tests/conftest.py` owns the marker, the flag and the line.

## Standing prompt contract

Each prompt is a conductor queue item; conductor's preamble owns the report's path and
header, the load budget and how to wait. This repository adds:

- **The report goes where the preamble says, starting with its header**, ~60 lines,
  written once with at most one trim pass: findings, numbers, decisions and surprises; no process narration or restated prompt.
  **Tests are mentioned only for a red you could not fix.**
- **End the console reply with `Report written to <path>`.**
- **Commit to the branch you are on.**
- **Every clock time is local 12-hour** (`5:25pm`, never `17:25` or UTC), in chat, ETAs
  and reports. The CLI's `[HH:MM:SS]` stamps are 24-hour; convert before quoting.
- **A step over about thirty seconds is backgrounded, with a completion waiter on the
  real process**, never on a launcher (`nohup … &` returns at once).
- **Operational facts learned on the way** (launch commands, ports, drop paths,
  conventions) **go into the relevant module README as you pass them**, not only into a
  report.

## Rules

- **No commit ≥20 MB** (one blob or in aggregate) without Matt's prior confirmation.
  Commit the rest, and name the drop and its size in the report.
- Every prompt names its target repository; if the working directory is not that
  repository, stop at once and say so.

---

## Build-era workflow *(delete this section at publication)*

`C:\Code\fractal-maker` was the read-only extraction source for this rewrite; it is no
longer on this box, so the checks that read it skip here as on CI. What only read it goes
at publication, with its test and subcommand. Each is still read by something live, so
deleting one means deciding what its reader does instead:

- `labeling/finished_import.py`: `run` has no caller; its conversions (`recipe_of`,
  `family_of`, `mode_of`, `engine_modes`, …) are read by `models.renders.verify`,
  `models.palette_sets.extract` and two tests.
- `palettes/library_import.py`: `authored_import.py` writes every authored drop through
  its `write`, `palettes add` (`admit.py`) through its `text_of`; `palette_sets.run` and
  `finished_import.run` call its `run`. Only its source-pool reader is build-era.
- The `--source` commands `renders verify`, `renders preregister`
  (`finished_acceptance.vendor`) and `palette extract` are those readers, so they go
  first. `palette label` and `palette score` reach the source through
  `palette_teacher`'s pointer, and `palettes provenance` reads its `BATCHES`.
- `models/acceptance.py`'s extraction half (`INCUMBENT_*`, `beside`,
  `ExtractionSourceGone`, `extraction_source`), called by `head preregister`; every read
  of a bar runs on the vendored yardstick, which stays.
