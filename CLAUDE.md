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
`<head>.<sheet>.json`, not the name of a real drop, or a grep for the live name answers
out of a comment about a different one.

**Cite a heading and a file, never a line number**: `curation/GALLERY.md`'s *What a pass
costs is one store*, not `GALLERY.md:1487`. A line number silently points somewhere else
after the next edit above it.

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
  parameters), so a labeled example is never split across files. Every random draw is
  seeded and the seed recorded.
- **Cross-platform by construction**: `pathlib` only, no absolute paths in tracked code.
  Windows process handling (job objects, priority classes) lives in
  `src/fractal_wallpapers/process_control.py` and nowhere else. A batch subcommand takes
  a **manifest file**, never hundreds of paths as arguments.
- **Formatting is not negotiable**: `ruff` lints and formats Python at line length 100;
  `rustfmt` and `clippy` govern the crates. A repo-wide reformat should never become
  possible.
- **Line endings are LF.** `.gitattributes` normalizes them, and **anything writing a
  tracked text file opens it `newline="\n"`**. CRLF drift is invisible to `git status`
  and `git diff` (under `* text=auto eol=lf` it commits as LF anyway), and Git Bash's
  `grep` reports a CR on every line of a pure-LF file: `git ls-files --eol` is the only
  detector, and `tests/test_line_endings.py` is the guard.
- **Search the source with `git grep` (or `rg`), never `grep -r` from the root.** The
  checkout carries ~100 GB and ~400,000 untracked files against under two thousand
  tracked ones; `grep --include=*` does not honour `.gitignore`.

### Installs

- **The base install stays torch-free.** `pip install -e .` buys the engine, the walk,
  the supply engine and the labeling rig; `fetch-weights --check` runs on it, so its
  whole import graph is stdlib (why `models/roster.py` exists apart from `ship`).
  `tests/test_base_install.py` proves it in a subprocess with those imports refused.
- **`dev` is the suite's install, not the base install**: it carries `numpy` and
  `pillow`, and **never `torch`, `torchvision` or `timm`**. A test reaching one of those
  skips rather than fails: `tests/test_lanes.py` sweeps for unguarded module-level
  imports (one aborts the whole lane at collection), and `conftest.pytest_runtest_call`
  catches call-time arrivals from `src/`. Both read their population from `cli.EXTRA_FOR`
  less `dev`.
- **CUDA is opt-in, never the default**: nothing heavy is installed or run unless
  someone asks. `models` is CPU torch everywhere and CI installs it; `cuda` is the same
  list on cu124, declared conflicting with `models` so one environment holds one torch.
  The commands are the README's *Install* and `src/fractal_wallpapers/models/README.md`.
- **Weights come from GitHub Releases, not LFS.** `fractal-wallpapers fetch-weights`
  reads `models/weights.json` (head → release tag, asset, sha256), downloads into
  `models/<head>/` and verifies the hash. `roster.TAG` is the one spelling of the tag,
  and a published tag is never moved; `models/README.md` has why.

### What git tracks

- **Git history stays text.** `tests/test_history_purity.py` fails the build on a
  tracked file that is binary by nature, over `MAX_TRACKED_BYTES` (2 MiB; prose says
  "the per-file history guard"), or a tracked *record* naming an absolute path. Its
  exemption lists each excuse a different rule, so an entry earns each one separately;
  each is Matt's call with its reason at the constant, and adding to one is a decision,
  not a fix.
- **`.gitignore` keeps its shape**: `scratch/` and `artifacts/` (runtime output),
  `models/**/*.pt` (fetched weights beside tracked metadata), and toolchain noise. A
  tracked file inside an ignored tree is how these rules rot. **The one exception is the
  published records' text**: `.gitignore` un-ignores the published stamps and, inside
  one, `gallery.jsonl`, `manifest.json` and `recipes.jsonl`. A published record is
  tracked whole; one that would break the per-file cap is Matt's to rule on, never an
  allowlist entry. `index.html` is never tracked.

### Records: published, kept, discarded

The saved set is twenty-one records, all published: the `final139_*` set (general
n=1000 and nineteen collections) and `final140_general2000`. This box keeps no
unpublished record.

- **A record is PUBLISHED only when Matt names it.** Publishing is a line in
  `curation.tentative.PUBLISHED` and a line in `.gitignore`; the two are one list written
  twice and `tests/test_tentative.py` holds them to agreeing. Tracking a record's text
  *is* publishing it; there is no third way, and nothing is committed until the work is
  truly finalized. **A forced fill (`--force-fill`) is never published**:
  `tentative.refuse_forced` is called on every collection publish path.
- **An unstamped read means `tentative.DEFAULT`** (`final139_general`), never the newest
  stamp: the twenty-one are peers. `portable.REFERENCE` (top-level `portable.py`, not
  under `curation/`) names `final139_green`, as `GENERAL_CHECK` names `final139_general`.
  The page a person opens is the `artifacts/curation/viewer/` row of
  `src/fractal_wallpapers/README.md`'s keep roster.
- **An unpublished record is DISCARDED by default. Keeping needs a reason; discarding
  does not.** An item that records a gallery to measure against deletes it once the
  measurement is taken, and says so in its report. ⚠ **`curate solve record` keeps by
  default**, so pass `--no-keep` or run `curate solve release <stamp>` afterwards.
- **The keep list is `tentative.kept()`**: `PUBLISHED` plus the keep file
  (`tentative.keep_path()`, `keep.jsonl` in the store root), which lets a clone keep its
  own record without editing code. ⚠ **The store is not the keep list**; a count of
  folders is not a count of kept records, so read `tentative.kept()`.
- **Publication, durability and retention are three questions.**
  `tentative.protected_keys()` reads `tentative.kept()` and nothing else, so preservation
  is a named row, never a folder existing; it must never sweep the whole store again.
- **Durability is a backup Matt takes, not git.** `fractal-wallpapers storage export` is
  run only at Matt's direction; he holds the copies off-box and deletes the local
  instance, so no tracked text names an export stamp. Restore is the
  `src/fractal_wallpapers/README.md` section *Continuing on a fresh box*.

### Curation and labels

- **A collection's size is in `curation/targets.py` and nowhere else.** Nineteen
  collections (twelve hue families, seven modes); `curate solve run|record --collection
  NAME` take `n` from `TARGETS` and the pool from `targets.pool_for`, `--n` overrides,
  and a collection the table does not name refuses. A prompt that names a seat count is
  retyping a target.
- **Degree 6 is never labelled**: `multibrot6` and `julia:multibrot6` are the mining
  loop's generalization test. `partitions.NEVER_LABELLED` is the list, and sheet build,
  ingest and both store writers refuse a row on it; their roots come from the viewport
  sampler alone, so `plane_seeds.FAMILIES` stops at `multibrot5` unless Matt says "with
  pool". `labeling/README.md`'s *Degree 6 is never labelled* has the doors.

### Storage and the box

- **Where a file under `artifacts/` belongs is decided once per top-level name**: *hot*
  (`artifacts/`, what a live command reads; its file count is not a target), *archive*
  (`storage archive <name>`, finished bulk restored before reuse), or *delete*
  (regenerable or unreferenced, and its builder goes with it). A subtree that must move
  alone is promoted to a top-level name first; `curation` never moves. Its unkept pool
  pictures are the exception: `storage pictures` mirrors them to the archive and
  `paths.Tiers.resolve` reads hot-then-mirror (`picture_mirror.py` has the rules). The
  tiers are `src/fractal_wallpapers/README.md`'s *Two roots*.
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
`sys.executable` and imports the package, and any other interpreter fails that one test
in a way that reads as a process-control bug. The walk tests need a **release** engine
(`cargo build --release --manifest-path engine/Cargo.toml`) and skip without one. A guard
asking whether the engine is built uses `try`/`except FileNotFoundError`:
`engine.engine_path` raises, and a bare call interrupts the whole lane at collection.

**`perturbation/` is the website's kernel too.** An edit there owes the website a rebake
(`perturbation/README.md`'s *Running it*), which is the website's own item; website
items never commit into this repository.

**CI** runs `pytest --slow` on three OSes with torch and no weights or store; a test
needing shipped heads skips on a missing file. Reading a red without `gh` and
reproducing it locally is `tests/README.md`'s *Reading and reproducing a CI red*.

### The two lanes

`python -m pytest` is the **fast lane** and every item runs it, test written or not.
`python -m pytest --slow` runs everything; CI runs it, and an item runs it only when its
prompt names it, comparing the two lanes' collected counts when it does. The readings
and the measurements behind these rules are in `tests/README.md`; this file holds rules.

- **Any red is a lane to read**; there is no expected failure.
- **Never repoint a census constant at today's reading.** A census that went red because
  a store deletes by design gets a ratchet (`test_leveled_identity.py` is the example).
- **Zero skips is normal; a skip is a short render cache**, a store condition, not a tree
  fault (`--slow -rs` names them). `label ingest` shortens it by the rows it lands (a
  sheet build does not), so run `renders plan` then `renders build --workers 3` after.
- **A reading compares only with one on the same install**: `tests/README.md`'s *What
  "the fast-lane count" means*. A module-level `importorskip` drops a module from
  collection, so an interpreter without `torch` silently runs a smaller suite; `conftest`
  prints a red line naming the missing import.
- **Measure on an idle box, literally.** Beside a render run the lane is killed on commit
  charge, so run it after, never beside. A test whose claim is not about time never reads
  the wall clock. Before believing a lane, re-run one untouched engine-bound guard: a
  tenth off on an invariant guard means the box.
- **A lane that moves right after code landed is the code until measured otherwise.**
  Re-run one slow file under a profile; the decisive check is a `git worktree` at `HEAD`
  with `FRACTAL_WALLPAPERS_HOT_ROOT` on the real store. With no test added, ask **which
  store grew**, **which derivation is paid twice**, **what is paid once per test**;
  re-measure after a merge, and suspect the disk after moving hundreds of thousands of
  paths.
- **A fixture redirects a store at the tier roots, never per accessor.**
- **Read the candidate ledger once a session**, through `conftest.tracked_ledger`; a
  direct `candidate_ledger.read()` adds ~40 s. A guard that sweeps the ledger takes a
  budget, and states the constant, its measurement, and an assertion the budget filled.
- **`@pytest.mark.slow` is for about a second or more of real work**: a render, a
  training loop, a store sweep. Arithmetic stays fast however much there is. Ask what a
  new test file pays per test (`conftest.shipped_cyclic_maps` is the model of a shared
  read). `data/palettes` is parametrized, so a colormap drop moves both counts.
- **A guard may be weakened or deleted to make a lane faster**; a 1:1 equivalent is not
  required, but the trade is **named and priced**: say what stopped being covered at the
  site and in the report, with the seconds it bought (`--durations=0 --durations-min=0`
  summed by file). Take pure wins first, and prefer thinning a claim (a smaller sample)
  to dropping one (fewer modes). Measure the fast lane after marking: shared cached
  derivations can hand a moved guard's cost to a sibling.
- **The fast lane prints how many tests it held back**, and that line is the point:
  `tests/conftest.py` owns the marker, the flag and the line.

## Standing prompt contract

Each prompt is a conductor queue item; conductor's preamble owns the report's path and
header, the load budget and how to wait. This repository adds:

- **The report goes where the preamble says, starting with its header**, ~60 lines as a
  soft target: write it once, at most one trim pass. Findings, numbers, decisions and
  surprises only; no process narration or restated prompt. **Tests are mentioned only
  for a red you could not fix.**
- **End the console reply with `Report written to <path>`.**
- **Commit to the branch you are on.**
- **Every clock time is local 12-hour** (`5:25pm`, never `17:25` or UTC), in chat, ETAs
  and reports. The CLI's `[HH:MM:SS]` stamps are 24-hour; convert before quoting.
- **A step over about thirty seconds is backgrounded, with a completion waiter on the
  real process**, never on a launcher: `nohup … &` returns at once and says nothing
  about the run.
- **Line endings are LF** (see *Code shape*).
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

`C:\Code\fractal-maker` was the **read-only** extraction source for this rewrite (never
written to; code from it was renamed and cleaned, never copied wholesale). It is no
longer on this box, so the checks that read it skip here as they do on CI.

What only ever read it goes at publication, with its test and subcommand. Each item
below is still read by something live, so deleting it means deciding what its reader
does instead:

- `labeling/finished_import.py`: its `run` has no caller, but its conversions
  (`recipe_of`, `family_of`, `mode_of`, `engine_modes`, …) are read by
  `models.renders.verify`, `models.palette_sets.extract`, `tests/test_label_round_trip.py`
  and `tests/test_modes.py`.
- `palettes/library_import.py` (and `tests/test_library_import.py`):
  `palettes/authored_import.py` writes every authored drop through its `write`;
  `models/palette_sets.run` and `finished_import.run` call its `run`.
- Three commands taking the source as `--source`: `renders verify`, `renders
  preregister` (`finished_acceptance.preregister`) and the palette set extraction
  (`models.palette_sets.run`). They are the readers above, so they go first.
- `models/acceptance.py`'s extraction half (`INCUMBENT_SCORES`, `INCUMBENT_MANIFEST`,
  `beside`, `ExtractionSourceGone`, `extraction_source`), still called by `head
  preregister`. Every *read* of a bar runs on the vendored yardstick, which stays.
