# Working in fractal-wallpapers

A Rust engine renders escape-time fractals; Python chooses where to look, how to color
it, and which finished images survive, with small neural judges trained on human labels.
It is the companion repo to a tutorial article, so it is written to be read. `README.md`
is for visitors; this file is the rules an executor here is held to. Each locked
convention is Matt's ruling, and changing one is his call. **`docs/rulings.md` holds his
standing rulings (styles, palettes, checks, the website): read it beside this file.**

## The naming rule

**Nothing ships under a name the article wouldn't teach.** Names say what a thing
*does* (`coloring/`, `discovery/`, `curation/`, `labeling/`); a name that needs a
paragraph of history is the wrong name.

**Comments and docstrings illustrate a shape, never a live instance.** Write
`<head>.<sheet>.json`, not a real drop's name, or a grep for the live name answers out of
a comment about another.

**Cite a heading and a file, never a line number**: `curation/GALLERY.md`'s *What a pass
costs is one store*, not `GALLERY.md:1487`, which drifts after the next edit above it.
`tests/test_doc_citations.py` resolves every citation of that form.

## Locked conventions

### Code shape

- **Rust makes every pixel; Python never renders.** Python reaches the engine only
  through `src/fractal_wallpapers/engine.py`; no other module shells out to the binary
  or computes image data.
- **Everything runnable is a `fractal-wallpapers` subcommand**; there is no `scripts/`.
  One `cli/<group>_commands.py` per command group (handlers and parser);
  `cli/__init__.py` lists them plus `main`; its docstring has why the suffix is
  load-bearing and handlers resolve through `__getattr__`, never re-exported.
- **Records are JSONL**: UTF-8, one object per line, an integer `schema` field from the
  first row. A label row carries its full join (the label *and* the complete render
  parameters), never split across files. Every random draw is seeded, the seed recorded.
- **Cross-platform by construction**: `pathlib` only, no absolute paths in tracked code.
  Windows process handling lives in `process_control.py` alone. A batch subcommand
  takes a **manifest file**, never hundreds of paths as arguments.
- **Formatting is not negotiable**: `ruff` lints and formats Python at line length 100;
  `rustfmt` and `clippy` govern the crates: a repo-wide reformat is never possible.
- **Line endings are LF**, and **anything writing a tracked text file opens it
  `newline="\n"`**. `git ls-files --eol` is the only detector of CRLF drift;
  `tests/test_line_endings.py` is the guard.
- **Search with `git grep` (or `rg`), never `grep -r` from the root**: the checkout
  holds ~100 GB of untracked files `grep` does not skip. Every `git grep` option goes
  before the pattern (`git grep -n -A4 PAT -- path`); after it, `-A4` reads as a revision.

### Installs

- **The base install stays torch-free.** `pip install -e .` buys the engine, the walk,
  the supply engine and the labeling rig; `fetch-weights --check` runs on it, so its
  import graph is stdlib. `tests/test_base_install.py` proves it in a subprocess.
- **`dev` is the suite's install**: `numpy` and `pillow`, **never `torch`,
  `torchvision` or `timm`**. A test reaching one of those skips rather than fails;
  `tests/test_lanes.py` (module-level imports) and `conftest.pytest_runtest_call`
  (call-time imports) enforce it.
- **CUDA is opt-in, never the default.** `models` is CPU torch everywhere; `cuda` is
  cu124 and conflicts with it, so one environment holds one torch (README's *Install*).
- **Weights come from GitHub Releases, not LFS.** `fetch-weights` downloads what
  `models/weights.json` names and verifies each sha256. `roster.TAG` is the one
  spelling of the tag; a published tag is never moved.

### What git tracks

- **Git history stays text.** `tests/test_history_purity.py` fails the build on a
  tracked file that is binary by nature, over `MAX_TRACKED_BYTES` (2 MiB, "the per-file
  history guard"), or a tracked *record* naming an absolute path. Each exemption list
  excuses one rule; every entry is Matt's call with its reason at the constant.
- **`.gitignore` keeps its shape**: `scratch/`, `artifacts/`, `models/**/*.pt` and
  toolchain noise; no tracked file inside an ignored tree **except the published
  records' text** (`gallery.jsonl`, `manifest.json`, `recipes.jsonl`, tracked whole; one
  over the per-file cap is Matt's to rule on, never an allowlist entry). `index.html` is never tracked.

### Records: published, kept, discarded

The saved set is twenty-one published records: `final139_*` (general n=1000 and
nineteen collections) and `final140_general2000`. No unpublished record is kept.

- **A record is PUBLISHED only when Matt names it**: a line in
  `curation.tentative.PUBLISHED` and a `.gitignore` negation covering its stamp, held by
  `tests/test_tentative.py`. Tracking a record's text *is* publishing it. A
  `--force-fill` record is never published (`tentative.refuse_forced`).
- **An unstamped read means `tentative.DEFAULT`** (`final139_general`), never the newest
  stamp: the twenty-one are peers. `portable.REFERENCE` names `final139_green`, as
  `GENERAL_CHECK` names `final139_general`. The page a person opens is the
  `artifacts/curation/viewer/` row of `src/fractal_wallpapers/README.md`'s keep roster.
- **An unpublished record is DISCARDED by default; keeping needs a reason.** An item that
  records a gallery to measure against deletes it once measured, and says so in its
  report. ⚠ **`curate solve record` keeps by default**: pass `--no-keep`, or run
  `curate solve release <stamp>` afterwards.
- **What is kept is `tentative.kept()`**, `PUBLISHED` plus the keep file
  (`tentative.keep_path()`), never a count of store folders; `tentative.protected_keys()`
  reads it and never sweeps the whole store.
- **Durability is a backup, not git**: `storage export` runs only at Matt's direction,
  and no tracked text names an export or a standing instance. Restore is `src/fractal_wallpapers/README.md`'s
  *Continuing on a fresh box*.

### Curation and labels

- **A collection's size is in `curation/targets.py` and nowhere else.** `curate solve
  run|record --collection NAME` take `n` from `TARGETS` and the pool from
  `targets.pool_for`, `--n` overrides, and a collection the table does not name refuses.
  A prompt naming a seat count is retyping a target.
- **Degree 6 is never labelled**: `multibrot6` and `julia:multibrot6` are the mining
  loop's generalization test. `supply.partitions.NEVER_LABELLED` is the list; sheet
  build, ingest and both store writers refuse it, and `plane_seeds.FAMILIES` stops at
  `multibrot5` unless Matt says "with pool" (`labeling/README.md`'s *Degree 6 is never
  labelled*).

### Storage and the box

- **Where a file under `artifacts/` belongs is decided once per top-level name**: *hot*
  (what a live command reads), *archive* (`storage archive <name>`, restored before
  reuse), or *delete* (regenerable or unreferenced, its builder with it). A subtree that
  must move alone becomes a top-level name first. `curation` never moves, except its
  unkept pool pictures, which `storage pictures` mirrors. The tiers are
  `src/fractal_wallpapers/README.md`'s *Two roots*.
- **A picture with no ledger row is garbage**: `curate candidate-ledger orphans` lists,
  `--apply` deletes; run it after a killed run and periodically. An unmerged leg is
  listed, never swept until someone names it (`--leg <name>` or `--include-unmerged`).
- **The render pool is three workers at below-normal priority** for anything driving
  the engine: more makes this desktop unusable. `engine.run` sets the priority; only
  the count is the caller's.
- **One pool-holding process per box.** `curate growth`, `curate solve run`, `curate
  solve record` and the slow test lane each hold the candidate pool whole and never run
  together.

## Checks to run before committing

```
python -m ruff check . && python -m ruff format --check .
python -m pytest
cargo build --manifest-path engine/Cargo.toml
cargo test --manifest-path engine/Cargo.toml
cargo fmt --check --manifest-path engine/Cargo.toml
cargo fmt --check --manifest-path perturbation/Cargo.toml
cargo clippy --manifest-path engine/Cargo.toml -- -D warnings
cargo clippy --manifest-path engine/Cargo.toml --no-default-features -- -D warnings
cargo clippy --manifest-path perturbation/Cargo.toml --all-targets -- -D warnings
cargo test --release --manifest-path perturbation/Cargo.toml
```

**An item that changes `engine/` is done only when the main checkout's release binary is
rebuilt after its last engine commit** (`cargo build --release --manifest-path
engine/Cargo.toml`, run in the main checkout, not a worktree): every render, the walk and
the next item read that binary, and a stale one has twice predated its own engine commit.

**CI lints with the newest stable Rust**: `rustup update stable` before the clippy
lines. CI also compiles on Linux and macOS, where some errors never show on Windows:
an item touching a crate's exports or `cfg(unix)` code repeats its clippy line
with `--target x86_64-unknown-linux-gnu --target-dir out/xtarget` (a linker-free type
check; `rustup target add x86_64-unknown-linux-gnu` once).

An item that touches the style path (`engine/src/style.rs`, `style-wasm/`, a style's
stack or the bundle) also runs:

```
cargo fmt --check --manifest-path style-wasm/Cargo.toml
cargo clippy --manifest-path style-wasm/Cargo.toml --all-targets -- -D warnings
cargo test --release --manifest-path style-wasm/Cargo.toml
cargo build --release --target wasm32-unknown-unknown --manifest-path style-wasm/Cargo.toml
```

Then the parity run it owes, once, after the last code change, read off
`style-wasm/README.md`'s *Parity: which run is owed* table: the whole **`fractal-wallpapers
style wasm-parity`** (38 to 48 minutes) only after engine or module code nothing cheaper
covers; **`style wasm-parity <name>`** after one style's change; **`--member <name>`**
after a name-list edit; nothing for docs and metadata. An engine change also owes
`identity` (`data/styles/README.md` step 2).

Run pytest with the checkout's own `.venv` interpreter: a gallery guard spawns
`sys.executable`, and another fails it like a process-control bug. The walk tests need
a built engine and skip without one (build **release**: a debug binary is found too, after
it, and runs them slowly); a guard asking whether the engine is built
asks `engine.is_built()`; a bare `engine.engine_path()` at module level raises
`FileNotFoundError` and interrupts the lane at collection.

**`perturbation/` is the website's kernel too.** An edit there owes the website a rebake
(`perturbation/README.md`'s *Running it*), the website's own item, and runs the two
commands of `.github/workflows/ci.yml`'s *Check the kernel for wasm32* step. The website also parses the root `README.md`'s explorer links
and cites `perturbation/README.md`'s numbered headings.

**CI** runs `pytest --slow` on three OSes with torch and no weights or store; a test
needing shipped heads skips on a missing file (`tests/README.md`'s *Reading and
reproducing a CI red*).

### The two lanes

`python -m pytest` is the **fast lane** and every item runs it, test written or not.
`python -m pytest --slow` runs everything; CI runs it, and an item runs it only when its
prompt names it, comparing the two lanes' collected counts. `-n 6` (pytest-xdist)
prints no held-back line: read a count off a serial run (`tests/README.md`'s *On a
parallel runner*).

- **Any red is a lane to read**; there is no expected failure.
- **Never repoint a census constant at today's reading.** A census that went red because
  a store deletes by design gets a ratchet (`test_leveled_identity.py` is the example).
- **Zero skips is normal; a skip is a short render cache**, a store condition (`--slow
  -rs` names them). After `label ingest`, run `renders plan` then `renders build`.
- **A reading compares only with one on the same install** (`tests/README.md`'s *What
  "the fast-lane count" means*): an interpreter without `torch` silently collects a
  smaller suite.
- **Measure on an idle box** (beside a render run, commit charge kills the lane).
  A test whose claim is not about time never reads the wall clock. Before believing a
  lane, re-run one untouched engine-bound guard: a tenth off means the box.
- **A lane that moves right after code landed is the code until measured otherwise**
  (`tests/README.md`'s *Where the time goes* has the worktree check).
- **A fixture redirects a store at the tier roots, never per accessor.**
- **Read the candidate ledger once a session**, through `conftest.tracked_ledger`; a
  direct `candidate_ledger.read()` adds ~40 s. A guard sweeping the ledger takes a
  budget: the constant, its measurement, and an assertion that it filled.
- **`@pytest.mark.slow` is for about a second or more of real work**: a render, a
  training loop, a store sweep; arithmetic stays fast.
  `data/palettes` is parametrized, so a colormap drop moves both counts.
- **A guard may be weakened or deleted to make a lane faster**, but the trade is **named
  and priced**: what stopped being covered, at the site and in the report, with the
  seconds it bought (`--durations=0 --durations-min=0` summed by file). Prefer thinning
  a claim to dropping one, and measure after marking.
- **The fast lane prints how many tests it held back** (`tests/conftest.py` owns the
  marker, the flag and the line).

## Standing prompt contract

Each prompt is a conductor queue item; conductor's preamble owns the report's path and
header, the load budget and waiting. This repository adds:

- **The report goes where the preamble says, starting with its header**, ~60 lines of
  findings, numbers, decisions and surprises, written once (one trim pass at most); no
  process narration or
  restated prompt. **Tests are mentioned only for a red you could not fix.**
- **End the console reply with `Report written to <path>`.**
- **Working papers are never committed**: `experiments/` is in this box's
  `.git/info/exclude`, whatever results folder the preamble names; tables go in
  `out/keep/<item>/` and the report.
- **Commit to the branch you are on.**
- **Every clock time is local 12-hour** (`5:25pm`, never `17:25`/UTC). The CLI's
  `[HH:MM:SS]` stamps are 24-hour; convert before quoting.
- **A step over about thirty seconds is backgrounded, with a completion waiter on the
  real process**, never on a launcher.
- **Operational facts learned on the way go into the relevant module README as you pass
  them**, not only into a report.

## Rules

- **No commit ≥20 MB** (one blob or in aggregate) without Matt's prior confirmation.
  Commit the rest; name the drop and its size in the report.
- Every prompt names its target repository; if the working directory is not that
  repository, stop at once and say so.

---

## Build-era workflow *(delete this section at publication)*

The extraction source (`fractal-maker`) is gone; its checks read its checkout from
`FRACTAL_MAKER_SOURCE` (`tests/conftest.py`'s `extraction_source_checkout`) and skip when
it is unset, as on CI.
What only read it goes at publication with its test and subcommand; each is still read
by something live, so deleting one means deciding what its reader does instead:

- `labeling/finished_import.py`: `run` has no caller; its conversions (`recipe_of`,
  `family_of`, …) are read by `models.renders.verify`, `models.palette_sets.extract`
  and two tests.
- `palettes/library_import.py`: only its source-pool reader (`write`, `text_of` and
  `run` have live callers).
- The `--source` commands (`renders verify|preregister`, `palette extract`) first;
  `palette label|score` and `palettes provenance` read the source too.
- `models/acceptance.py`'s extraction half (`INCUMBENT_*`, `beside`,
  `ExtractionSourceGone`, `extraction_source`; `head preregister` calls it); the
  vendored yardstick stays.
