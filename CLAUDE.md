# Working in fractal-wallpapers

This repository generates fractal wallpapers and then decides which ones are worth
keeping. A Rust engine renders escape-time fields; Python steers it, choosing where to
look, how to color what it finds, and which finished images survive, with small neural
judges trained on human labels. It is the companion repo to a tutorial article, so it is
written to be read. `README.md` is for visitors; this file is the rules an agent working
here is held to.

## The naming rule

**Nothing ships under a name the article wouldn't teach.** Directory names, module
names, and vocabulary say what the thing *does* — `coloring/`, `discovery/`,
`curation/`, `labeling/`. If a name needs a paragraph of history to justify, it is
the wrong name. Vocabulary from earlier private versions of this project does not
transfer; rename on the way in.

**Comments and docstrings illustrate a shape, never a live instance.** Write
`<head>.<sheet>.json`, not the name of a drop that exists — otherwise a grep for a
live name answers out of a comment about a different one, confidently and wrongly.

**A citation names a heading and a file, never a line number.** Write
`curation/GALLERY.md`'s *What a pass costs is one store*, not `§1487` or
`GALLERY.md:1487`. A line number goes silently wrong at the next edit above it, pointing
at a real line that says something else; a heading survives every edit that does not
rename it, and a rename is a `git grep` away from being repointed.

**The rule stands and no test here enforces it**: the guard is the website's,
`builder/vocabulary.py` in the `fractal-website` checkout, swept by its
`builder/checks.py`.

## Locked conventions

Each of these is expensive to reverse. Most date from the first commit; the ones
that came later carry the date of Matt's ruling.

- **Rust makes every pixel; Python never renders.** Python reaches the engine only
  through `src/fractal_wallpapers/engine.py`. No other module shells out to the
  binary or computes image data itself.
- **Everything runnable is a subcommand** of `fractal-wallpapers` (see `cli/`).
  There is no `scripts/` directory and there never will be one. One module per
  command group, each holding its handlers and its parser together, and
  `cli/__init__.py` is the list of them plus `main`. The **`_commands` suffix is
  load-bearing**: eight top-level commands are also handler names, and a submodule
  set as an attribute of its package is one `__getattr__` never sees, so
  `cli/render.py` would shadow `cli.render` for good. Handler names resolve
  through `__getattr__`, never re-exported, for the reason `6d55846` gives.
- **Records are JSONL**: UTF-8, one JSON object per line, carrying an integer
  `schema` field from the very first row. A label row carries its full join — the
  label *and* the complete render parameters in the same row — so a labeled example
  is never split across files. Every random draw is seeded, and the seed is recorded.
- **Git history stays text.** `tests/test_history_purity.py` fails the build if a
  tracked file is binary-by-nature or exceeds 2 MiB (Matt's ruling of 2026-09-29,
  up from 1 MiB; `MAX_TRACKED_BYTES` is the one spelling in code and prose says
  "the per-file history guard"), or if a tracked *record* names
  an absolute path. It carries **four** exemption lists and **no two of them excuse
  the same rule**, so an entry earns each one separately and moving a name between
  them changes what it is held to. Each is on Matt's call, each has its reason
  written at the site in full, and adding to any of them is a decision, not a fix.
  The lists and the argument for every entry are in `test_history_purity.py` at
  the constants themselves.
- **`.gitignore` keeps its shape**: `scratch/` and `artifacts/` (runtime output),
  `models/**/*.pt` (fetched weights, living beside their tracked metadata), and
  toolchain noise. Do not interleave tracked and ignored content beyond that — a
  tracked file inside an ignored tree is how these rules rot. **The one tracked
  content under `artifacts/` is the published records' text**, since 2026-09-29:
  `.gitignore` un-ignores the twenty-one stamps of 2026-09-22 as one directory
  pattern and, inside a published stamp, `gallery.jsonl`, `manifest.json` and
  `recipes.jsonl` by name. Publishing another record is a line there and a line in
  `curation.tentative.PUBLISHED`. **Every published record is tracked whole** —
  nothing inside a published stamp is ignored again, and a file that would be over
  the per-file cap is Matt's to rule on, never an allowlist entry.
  `index.html` is never tracked.
- **A tentative record is PUBLISHED only when Matt names it**, his ruling of
  2026-09-04. An unpublished record is read by naming its stamp, and what it does
  not get is a Durable-class save, check or restore and a place in an archive copy.
  `tentative.PUBLISHED` and `.gitignore`'s negation lines are one list written twice
  and `tests/test_tentative.py` holds them to agreeing; the ruling and why
  `LARGE_TEXT_ALLOWLIST` was not the answer are at `curation/tentative.PUBLISHED`.
  **`tentative.PUBLISHED` is the twenty-one kept records since 2026-09-29**, Matt's
  ruling that the saved set is truly finalized, and `KEPT_UNPUBLISHED` is empty.
  **An unstamped read means `tentative.DEFAULT`**, `final139_general`, and never the
  newest published stamp: the twenty-one are peers, and the newest is the n=2000,
  which is not the default gallery. The page a
  person opens, and how it is written, is the `artifacts/curation/viewer/` row of
  `src/fractal_wallpapers/README.md`'s keep roster and `curation/GALLERY.md`.
- **An unpublished record is DISCARDED by default**, Matt's ruling of 2026-09-13.
  **Keeping needs a reason; discarding does not** — it is not a balance a leg weighs
  at the end of its run. A leg that recorded a gallery to measure something against
  **deletes it when the measurement is taken and says so in its report**: a solve is
  cheap to run again, and what a leftover record costs is misreading hazard, not
  bytes. **The keep list is code**: `tentative.PUBLISHED` plus
  `tentative.KEPT_UNPUBLISHED`, with the reason written at the site. Everything else
  goes unless Matt says otherwise. **The keep list holds twenty-one, all of them
  published since 2026-09-29**: the `final139_*` set (the general n=1000 and the nineteen collections,
  seated over the pool as mining closed on 2026-09-21) and `final140_general2000`, the
  general pass at n=2000 over the same pool, kept so the website can offer it beside
  the n=1000 default. The store holds exactly the kept records and no separate
  reference: `fractal_wallpapers.portable.REFERENCE` (top-level `portable.py` beside
  `engine.py`, **not** under `curation/`) names the kept `final139_green`, as
  `GENERAL_CHECK` names `final139_general`. ⚠ **The store is not the keep list**, and
  a count of folders is not a count of kept records — they have diverged before —
  so a leg that wants to know what is kept reads `tentative.kept()`.
- **Preservation of the saved set is a portable instance Matt backs up, and not
  git.** The twenty-one kept records live on this box and in the backups Matt
  takes with `fractal-wallpapers storage export`. **An export is Matt's, taken only
  at his direction**: he holds the copies off-box and deletes the local instance at
  once, so no tracked text names an export stamp or a standing instance. Restore is
  `storage import --from <path to the backup> --root <hot root>`.
  **Nothing is committed until the work is truly finalized**: tracking a record's
  text is publishing its stamp and there is no third way
  (`curation/GALLERY.md`'s *All twenty kept records carry one, and publication
  tracked them*). The saved set's text was committed on 2026-09-29, but the backup
  is still what makes the set durable — it carries the pictures, which git does
  not — and `tentative.kept()` is only what stops a prune taking its pictures.
- **Publication, durability and retention are three questions and not one.**
  `tentative.protected_keys()` reads `tentative.kept()` — `PUBLISHED` plus
  `KEPT_UNPUBLISHED` — **and nothing else**, so preservation is a line in a tuple
  and never a folder existing. A record off that list is readable by naming its
  stamp and pins nothing. The test for a `KEPT_UNPUBLISHED` entry is that something
  **resolves** the record — code reading its rows, a figure naming `<stamp>|<key>`
  — not that something mentions it. It must never sweep the whole store again: that
  let an ephemeral artifact confer preservation.
- **A collection's size is in `curation/targets.py` and nowhere else**, Matt's cut
  of 2026-09-15. Nineteen collections — twelve hue families, seven modes — and a
  prompt that names a seat count is a prompt retyping one of them.
  `curate solve run --collection NAME` and `curate solve record --collection NAME`
  take `n` from it, splice a family or filter a mode through `targets.pool_for`, and
  `--n` still overrides. **A collection the table does not name refuses** rather
  than seating a plausible number. Changing a target is a one-line edit to
  `TARGETS`, and the reason for each tier is written at the constant.
- **Degree 6 is never labelled**, Matt's ruling of 2026-09-16: `multibrot6` and
  `julia:multibrot6` are the mining loop's generalization test on a fractal no human
  has labelled. `partitions.NEVER_LABELLED` is the list, sheet build, ingest and both
  store writers refuse a row on it, and its roots come from the viewport sampler
  alone — `plane_seeds.FAMILIES` stays at 5 unless Matt says "with pool".
  `labeling/README.md`'s *Degree 6 is never labelled* has the doors.
- **CUDA is opt-in, never the default**, Matt's principle of 2026-09-25: nothing
  heavy is installed or run unless someone asks for it. `models` is CPU torch on
  every platform and CI installs it; `cuda` is the same list on cu124 for a box
  that trains, declared conflicting with `models` in `[tool.uv] conflicts` so one
  environment holds one torch. A box that trains syncs `--extra cuda` in place of
  `--extra models`, and a `--extra models` re-sync swaps its torch back to CPU. The
  install commands, and why pip cannot opt in, are `models/README.md`'s under
  `src/fractal_wallpapers/`.
- **Weights come from GitHub Releases, not LFS.** `fractal-wallpapers fetch-weights`
  reads `models/weights.json` (head → dated release tag, asset name, sha256),
  downloads into `models/<head>/`, and verifies the hash before keeping the file.
  `roster.TAG` is the one spelling of the tag, and a published tag is never moved;
  `models/README.md` has why.
- **Formatting is not negotiable**: `ruff` lints and formats Python at line length
  100; `rustfmt` and `clippy` govern the crate; `.gitattributes` normalizes line
  endings to LF. A repo-wide reformat should never become possible.
- **Cross-platform by construction**: `pathlib` only, no absolute paths in tracked
  code. Windows-specific process handling (job objects, priority classes) lives in
  `src/fractal_wallpapers/process_control.py` and nowhere else. A batch subcommand
  takes a **manifest file**, never hundreds of paths as arguments — a Windows
  command line overflows long before the batch does.
- **Anything writing a tracked text file opens it `newline="\n"`**, which is what
  stops a Windows run dirtying every line of a file it rewrote. **The drift is
  invisible to `git status`**: under `* text=auto eol=lf` a CRLF worktree file
  commits as LF anyway, so `git diff` is empty while every line waits to change at
  once. `tests/test_line_endings.py` is the guard and `git ls-files --eol` the only
  detector that works here — Git Bash's `grep` reports a CR on every line of a
  pure-LF file.
- **Where a file under `artifacts/` belongs is a three-way decision, made once per
  subtree.** *Hot* (`artifacts/`) is what a live command in the loop reads, and its
  file count is not a target to drive down. *Archive* (`E:\Fractals\FractalStorage`,
  `storage archive <name>`) is finished bulk nothing reads routinely, restored
  before reuse. *Delete* is everything regenerable from what is hot and everything
  unreferenced — if nothing will want a thing back, its builder goes with it. The
  unit of the first two is a **top-level name**, so a subtree that has to move on
  its own is promoted to one first; `curation` can never move, being the live pool.
  **Its pool pictures are the one exception finer than a name**, since 2026-09-30:
  `storage pictures` mirrors every unkept candidate JPEG to `pool_pictures/` on the
  archive, `paths.Tiers.resolve` answers a picture hot-then-mirror, and with the
  archive unplugged a picture whose hot copy is gone raises rather than reading as
  absent. `src/fractal_wallpapers/picture_mirror.py` has the rules.
  How the tiers are configured is `src/fractal_wallpapers/README.md`'s *Two roots*.
- **A picture with no ledger row is garbage, and there is a sweep for it.**
  `curate candidate-ledger orphans` lists by default and deletes with `--apply`;
  run it after any killed leg and periodically. **An unmerged leg is listed and
  never swept unread** — it is real work with no row anywhere, so it is taken only
  when somebody reads the listing and names it (`--leg <name>`, or
  `--include-unmerged` for all of them).
- **The render pool is three workers at below-normal priority.** That is the shape
  of every leg that drives the engine — a measure pass, a sheet build, a hunt, a
  mine — and it is a rule about this machine, not a tuning knob: more than three
  `fractal-engine.exe` at once, or any at normal priority, makes the desktop
  unusable while the leg runs. `engine.run` spawns below-normal through
  `process_control.child_priority_flags`, so only the count is the caller's.
- **ONE POOL-HOLDING PROCESS PER BOX.** Anything that loads the candidate pool —
  `curate growth`, `curate solve run`, `curate solve record`, and the slow test lane
  counts as one — never runs concurrently with another on the same machine. The pool
  is hundreds of megabytes read whole and held whole, so two at once is the box
  swapping rather than two legs finishing sooner.
- **Search the source with `git grep`, never `grep -r` from the root.** This checkout
  carries a hundred gigabytes and four hundred thousand untracked files against under
  two thousand tracked ones, so a recursive grep takes tens of minutes where the index
  answers in a fraction of a second. `rg` is fine too — it honours `.gitignore` — but
  `grep --include=*` does not, and that is the trap.
- **The base install stays torch-free on the `fetch-weights` path.** `pip install
  -e .` buys the engine, the walk, the supply engine and the labeling rig; the
  `models` extra is hundreds of megabytes of torch a clone that only renders should
  never pay for. `fetch-weights --check` has to run on that install, so its whole
  import graph is stdlib — which is why `models/roster.py` exists apart from `ship`.
  `tests/test_base_install.py` proves it in a subprocess with those imports refused,
  because every machine that runs the suite has torch.
- **`dev` is the suite's install and is not the base install.** It carries `numpy`
  and `pillow` since 2026-09-15, because the suite does not run without them; three
  megabytes against the `models` extra's hundreds is the whole of the argument, and
  it moves nothing on the package's own path. **What stays out is `torch`,
  `torchvision` and `timm`**, and a test reaching one of those is held to skipping
  rather than failing, two ways: `tests/test_lanes.py` sweeps every test module for
  an unguarded module-level import — one of those aborts the **whole lane** at
  collection, not its own file — and `conftest.pytest_runtest_call` catches the
  call-time arrivals, which no sweep of `tests/` can see because modules under
  `src/` import torch inside a function body. Both read their population from
  `cli.EXTRA_FOR` less `dev`.
- **CI's red is readable without `gh` and without admin rights.** The repository is
  public: `api.github.com/repos/techmatt/fractal-wallpapers/actions/runs` gives the
  runs and `runs/<id>/jobs` gives **step-level** conclusions. Job *logs* need
  admin and 403; step conclusions do not, and they are enough to say which step
  failed on which job. **Reproducing a failed Test step is a fresh clone with no
  store and no weights**: `git clone` the checkout into a scratch directory, copy
  the release engine binary into its `engine/target/release/`, set
  `FRACTAL_WALLPAPERS_HOT_ROOT` and `FRACTAL_WALLPAPERS_ARCHIVE_ROOT` to empty, and
  run `pytest --slow` there with this checkout's interpreter. That is what a runner
  has. Reproducing the lean install is a mask at `sys.meta_path` —
  `tests/test_base_install.py` carries the finder — blocking `torch,torchvision,timm`,
  **not** `numpy`, which `scipy` brings.

## Checks to run before committing

```
python -m ruff check . && python -m ruff format --check .
python -m pytest
cargo build --manifest-path engine/Cargo.toml
cargo test --manifest-path engine/Cargo.toml
```

Run the Python suite with the checkout's own interpreter — `.venv` — rather than
whatever `python` resolves to on the path. `pythonpath = ["src"]` in
`pyproject.toml` gets pytest itself importing the package from any interpreter,
but one gallery guard spawns `sys.executable` and imports `fractal_wallpapers`
inside it, which needs an interpreter carrying the editable install. The wrong
one fails that single test and nothing else, so it reads as a process-control
bug rather than as the environment it is.

CI runs the same thing on Ubuntu, macOS (Apple silicon) and Windows, installed as the
README's *Install* gives it — `uv sync` with all three extras — so every CI job has torch
and none has fetched weights; a test that needs the shipped heads skips on a missing
file rather than failing. The Python suite's walk tests need
a **release** engine (`cargo build --release --manifest-path engine/Cargo.toml`)
and skip themselves without one, so `cargo clean` costs a rebuild *and* the fast
lane until you do it. **A guard that asks whether the engine is built asks through
`try`/`except FileNotFoundError`**: `engine.engine_path` **raises** rather than
returning None, so a guard that asks it bare (`not engine.engine_path().is_file()`)
explodes while pytest is still collecting and interrupts the **whole lane**, not
just its own file.

### The two lanes

`python -m pytest` runs the **fast lane**, and it is the lane every prompt runs.
`python -m pytest --slow` runs every test there is; CI runs it, and a prompt runs it
only when the prompt names it — Matt's ruling of 2026-09-16.

**Every reading this lane has taken is in
[`tests/README.md`](tests/README.md#the-lanes-readings-in-order)**, with what the box
was doing at the time, and so are the measurements behind the rules below. This file
holds rules only — Matt's ruling of 2026-09-23.

- **Take the fast lane whether or not the prompt wrote a test**, and the slow lane only
  when the prompt names it. A reading is only ever a reading of the tree in front of it;
  *the two lanes agree on the collected count* is the check that catches drift, so a
  prompt that does run the slow lane compares the counts.
- **A lane with any red in it is a lane to read.** There is no expected failure any more.
- **Repointing a census constant at today's reading is the forbidden edit.** A census
  that went red because a store deletes by design is fixed by a **ratchet** —
  `test_leveled_identity.py` is the worked example — and the ratchet is what makes the
  repoint unnecessary rather than what excuses it.
- **Zero skips is the normal reading, and a lane that skips is a short render cache** —
  a store condition, not a tree fault. `--slow -rs` names them. **An ingest shortens
  the cache by exactly the rows it lands and a sheet build does not** (a sheet's pictures
  land under `artifacts/sheet/` and no store gains a row until `label ingest` runs), so
  run `renders plan` then `renders build --workers 3` after an ingest.
- **Ask what a new test file pays per test before accepting its clock.** A fixture that
  reads one tracked answer once can be worth more than the tests it serves cost —
  `conftest.shipped_cyclic_maps` is the worked example.
- **`data/palettes` is a parametrized guard**, so a colormap drop moves both counts with
  no test written, and a reading taken across a drop is not comparable with one before it.
- **A reading is comparable only against one taken on the same install**, and
  [`tests/README.md`](tests/README.md#what-the-fast-lane-count-means) defines the
  count once: selected and deselected both, or neither. **A count is not stable
  across interpreters** — a module-level `pytest.importorskip` stops a module being
  collected at all rather than skipping its tests, so an interpreter without `torch`
  silently runs a smaller suite; `conftest` prints a red line naming the missing
  import.
- **Measure on an idle machine, and take that literally.** Beside a render leg the
  lane does not merely slow, it is killed outright on commit charge, so **run the
  lane after a leg, never beside it**. **A test whose claim is not about time never
  reads the wall clock.**
  [`tests/README.md`](tests/README.md#a-lane-sharing-the-box-with-a-render-leg) has
  the measurements.
- **Re-run one untouched, engine-bound guard before believing a lane.** Forty
  seconds against seven minutes, and it answers *box or tree* on its own: a tenth
  either way on an invariant guard means the box.
- **A lane that moves right after code landed is the code until measured
  otherwise**, and the cheap check is one slow file re-run under a profile rather
  than the whole lane re-run hoping for a quieter box
  ([`tests/README.md`](tests/README.md#a-lane-that-moves-right-after-code-landed-is-the-code-until-measured-otherwise)).
  **The cheapest decisive check is a `git worktree` at `HEAD`** with
  `FRACTAL_WALLPAPERS_HOT_ROOT` pointed at the real store: it measures the OLD code
  on TODAY's box, which is the one comparison a re-run of the new code cannot make.
- **When a lane moves with no test added, ask three questions**: **which store
  grew**, **which derivation is paid twice**, and **what is paid once per test**.
  Re-measure after a **merge**, not only after writing tests. And suspect the
  **disk** after anything that moves hundreds of thousands of paths.
- **A fixture that redirects a store redirects it at the tier roots, never per
  accessor.** An accessor list is a list something will be missing from, and what it
  misses is this machine's real store, read at full size on every test.
- **The candidate ledger is read once a session**, through `conftest.tracked_ledger`.
  A test that calls `candidate_ledger.read()` itself adds forty seconds to the lane.
- **A guard that sweeps the ledger takes a budget rather than the store**, and states
  the constant, the measurement behind it, and an assertion that the budget was
  filled. That is the one place this suite trades coverage for time, it is written
  down at each site, and it is not a licence elsewhere.
- **A test earns `@pytest.mark.slow` by costing about a second or more of real
  work** — a render through the engine, a training loop, or a sweep of a store.
  Arithmetic stays in the fast lane however much of it there is.
- **A guard may be weakened or deleted to make a lane faster**, Matt's ruling of
  2026-09-15: the slow lane is too slow to run as often as it should be, and that
  costs more than a thin guard does. **Slight loss of fidelity is acceptable; a 1:1
  equivalent is not required.** What is still required is that the trade is **named
  and priced**, so the suite never quietly gets weaker with nobody able to say where:
  - **Say what stopped being covered, at the site and in the report** — a sample
    where there was a census, four modes where there were twenty, a claim dropped.
  - **Price it.** A cut with no seconds beside it is not a speedup, it is a
    deletion; `--durations=0 --durations-min=0` summed by file is how this repo
    finds its time and `tests/README.md` carries the method.
  - **Take the pure wins first.** They cost nothing and they are usually there.
    Reach for coverage only once those are gone.
  - **Prefer thinning a claim to dropping one.** A guard pinned per mode is twenty
    claims and cutting it to four drops sixteen of them; a guard that samples 80
    rows of a store is one claim and sampling 20 is the same claim, cheaper. The
    first needs a reason, the second needs a number.
- **Measure the fast lane after marking, not before.** Several of these guards share
  a cached derivation, so moving one to the slow lane can hand its cost to whichever
  sibling reads the cache next, and a mark that bought nothing is a guard given up
  for nothing.
- **The fast lane prints how many tests it held back**, on every run that holds any
  back. That line is the point of the arrangement rather than a decoration: a lane
  that went quiet would be a set of guards nobody would notice had stopped running.
  `tests/conftest.py` owns the marker, the flag and the line.

## Standing prompt contract

Each prompt in this project ends the same way:

- Write the final report to `scratch/<prompt_name>_report.md`. **~60 lines is a soft
  target** — write it once, allow at most one trim pass, and never iterate to squeeze
  under the line. Going over is fine; padding and re-editing are not.
- Report findings, numbers, decisions, and surprises only. No process narration, no
  restating the prompt back. **A report mentions tests only for a red it could not
  fix** — no test counts, no lane readings.
- **Every clock time is local 12-hour** — `5:25pm`, never `17:25` or UTC — in chat, ETAs,
  heartbeats and reports alike, Matt's ask of 2026-09-16. The CLI's own `[HH:MM:SS]`
  stamps are 24-hour, so convert before quoting one.
- Then copy the report to `C:\Code\fractal-drive-sync\reports\`.
- **Operational facts learned on the way — launch commands, ports, drop paths,
  conventions — get promoted into the relevant module README as you pass them**, not
  left only in a scratch report. `scratch/` is defined as disposable; a fact worth
  writing down twice belongs in tracked documentation once.
- **A step estimated over about thirty seconds is backgrounded, not waited on.** Say
  what it was estimated at, launch it in the background, and poll — a training band,
  a render leg or a sweep over the tracked records is minutes to hours, and a prompt
  that blocks on one reports nothing until it lands.
- **Arm a completion waiter in the same breath as the launch, and wait on the REAL
  process.** A launcher wrapper exits first and its exit code says nothing about the
  leg: `nohup … &` returns instantly and reports success while the leg has barely
  begun. A long run also carries a **15-minute heartbeat with a wall-clock
  timestamp**. ⚠ **A heartbeat detects nothing on its own**, so the heartbeat is for
  the reader and the waiter is what wakes the session.
- **What arms a waiter is a step that WAITS, not a step that LAUNCHES**, and the
  case the rule above misses is a **handover**: waiting on another checkout to go
  clean, on another session, or on a person. A stated intention is not a mechanism:
  the only thing that returns control to a session is a tool call completing, so
  **an idle turn IS the stall**. Block in the foreground on the real condition
  (`until [ -z "$(git -C <repo> status --short)" ]; do sleep 60; done`) with a
  generous timeout, or background that same loop so its exit fires one notification.
  ⚠ A handover is the one moment with **no launch to hang the waiter off**, which is
  exactly why it is the moment it gets skipped.
- **The commit gate is part of the contract, not a step after it.** Commit to `main`,
  and when another prompt is in flight in this repository — anything `git status`
  lists as modified or untracked that is not yours — commit **only your own files, by
  explicit path**: `git add <path> …`, never `git add -A` or `git add .`.
- **Commit with a pathspec (`git commit -- <paths>`), never a bare `git commit` after staging**, because another prompt may have staged files in the same index.
- **One prompt at a time in this repository.** A second prompt does not start while
  another has uncommitted changes — wait for `git status` to come back clean. The
  by-explicit-path rule above is necessary and it is *not* sufficient: it governs
  what a commit adds and says nothing about what the index already holds, so a
  prompt that has staged a **deletion** has it swept into whatever the other prompt
  commits next.

### Staging a prompt

**"stage `<prompt>.md`" means prepare, not run.** It is how a second prompt gets
written and thought through while the first one still holds the repository, and the
whole point is that it costs the live prompt nothing:

- Read the named prompt file and whatever tracked code, records and READMEs it
  points at. Reading is unlimited; run read-only commands freely.
- **Do not dirty the tree.** No edits to tracked files, no new files in the
  checkout, nothing staged, no commits, no branch. Anything that has to be written
  while staging — notes, a scratch script, sample output — goes to the scratchpad
  directory outside the checkout, never to `scratch/` or `artifacts/`.
- **Do not touch what the live prompt is using.** No render legs, no training, no
  pool-holding process, no slow lane — the one-pool-holding-process rule and the
  three-worker rule both still bind, and the process holding them is somebody
  else's. `git status` coming back dirty is expected; leave every file in it alone
  and do not try to work out whose it is.
- Produce a plan: what will change, in which files, in what order, what gets
  measured or rendered, what the report will have to answer, and which steps are
  long enough to background.
- **Then stop and wait.** Say the plan is ready and that the tree is not yours yet.
  Matt hands over the lock explicitly; `git status` going clean on its own is not
  the handover.

On being given the lock, re-check `git status` and re-read anything the other
prompt committed under you before executing — a plan staged against the old tree
is a plan that may have been overtaken.

## Rules

- Commit to `main` only.
- **No commit ≥20 MB** — single blob or aggregate — without Matt's explicit prior
  confirmation. Stop and ask; do not commit and report it afterwards.
- Every prompt names its target repository; if the working directory is not that
  repository, stop immediately and say so rather than guessing.

---

## Build-era workflow *(delete this section at publication)*

`C:\Code\fractal-maker` is the **read-only** extraction source for this rewrite:
read from it freely, never write to it. Code arriving from there gets renamed to fit
the naming rule and cleaned before it lands here — nothing is copied wholesale.

### What goes with it

Scaffolding that only ever reads the source project. Each ran, each wrote what it
was for, and none of it is reachable from a clone with no sibling checkout — so
each goes at publication, with its test and its subcommand.

**Gone on 2026-09-30**: the location-corpus importer and its test, and the `cli`
module that held `import-labels` and `import-finished`. Nothing else read them.

**Still here, each because something live reads it** — deleting one means
answering what its reader does instead, which is a decision and not a cleanup:

- `src/fractal_wallpapers/labeling/finished_import.py` — the two finished-render
  corpora's importer. Its command is gone and its `run` has no caller, but its
  conversions (`recipe_of`, `family_of`, `mode_of`, `engine_modes` and the rest)
  are read by `models.renders.verify`, by `models.palette_sets.extract`, and by
  `tests/test_label_round_trip.py` and `tests/test_modes.py`.
- `src/fractal_wallpapers/palettes/library_import.py` (with
  `tests/test_library_import.py`) — colormaps converted out of the source's pooled
  library. `palettes/authored_import.py` writes every authored drop through its
  `write`, which is not build-era work at all; `models/palette_sets.run` and
  `finished_import.run` call its `run`.
- **Three commands the first list missed**, each taking the source as `--source`:
  `renders verify` (`models.renders.verify`), `renders prereg`
  (`finished_acceptance.preregister`) and the palette head's set extraction
  (`models.palette_sets.run`). They are the readers above, so they go first.
- `src/fractal_wallpapers/models/acceptance.py`'s extraction path —
  `INCUMBENT_SCORES`, `INCUMBENT_MANIFEST`, `beside`, `ExtractionSourceGone`,
  `extraction_source` — reads `fractal-maker` and `fractal-maker-artifacts` beside
  this checkout to write a bar the first time, and `head prereg` still calls it
  through `preregister`. **Only the extraction half goes**: every *read* of a bar
  already runs against the vendored yardstick, which is tracked and stays.
