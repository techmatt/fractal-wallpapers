# Working in fractal-wallpapers

This repository generates fractal wallpapers and then decides which ones are worth
keeping. A Rust engine renders escape-time fields fast; Python steers it — choosing
where to look, how to color what it finds, and which finished images survive — with
small neural judges trained on human labels. It is the companion repo to a tutorial
article, so it is written to be read: every directory says what it does, every
runnable step has a name, and the git history stays small enough to clone without
thinking about it.

Almost all of the code here was written with Claude Code. That works best when you
give it a whole component to build at once and hold it to the conventions below,
rather than asking for edits line by line.

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
`GALLERY.md:1487`. A line number is correct until the next edit to the file above it
and then it is silently wrong, pointing at a real line that says something else —
worse than dangling, because nothing looks broken, which is how `curation/README.md`
carried two stale ones undetected. A heading survives every edit that does not
rename it, and a rename is a `git grep` away from being repointed.

**The rule stands and no test here enforces it**: the guard is the website's,
`builder/vocabulary.py` in the `fractal-website` checkout, swept by its
`builder/checks.py`.

## Locked conventions

These were decided once, at the first commit, because each is expensive to reverse.

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
  through `__getattr__`, never re-exported, for the reason `2dc6a8b` gives.
- **Records are JSONL**: UTF-8, one JSON object per line, carrying an integer
  `schema` field from the very first row. A label row carries its full join — the
  label *and* the complete render parameters in the same row — so a labeled example
  is never split across files. Every random draw is seeded, and the seed is recorded.
- **Git history stays text.** `tests/test_history_purity.py` fails the build if a
  tracked file is binary-by-nature or exceeds 1 MiB, or if a tracked *record* names
  an absolute path. Its **three** exemption lists are not interchangeable and each
  excuses a different rule: `ALLOWLIST` excuses a file from the first two and is
  empty; `LARGE_TEXT_ALLOWLIST` excuses a *prefix* from the size rule alone and
  still holds it to being text, its three entries being `data/palette_choice/rows/`,
  `data/curation/rank_key/population.jsonl` and `data/gallery_grade/corpus/`;
  `RECORD_EXEMPT_PREFIXES` excuses a *prefix* from the absolute-path rule alone and
  holds it to carrying a `checksums.json`, its one entry being the same frozen
  corpus — kept byte for byte because that sha256 is the only thing saying which
  rows a shipped column was fitted on, and re-spelling a member would verify
  nothing. `RECORD_EXEMPT_KEYS` is the fourth and is by key rather than by file.
  Each is on Matt's call and each has its reason written at the site. Adding to any
  of them is a decision, not a fix.
- **`.gitignore` keeps its shape**: `scratch/` and `artifacts/` (runtime output),
  `models/**/*.pt` (fetched weights, living beside their tracked metadata), and
  toolchain noise. Do not interleave tracked and ignored content beyond that — a
  tracked file inside an ignored tree is how these rules rot. **There is exactly
  one hole and it is deliberate**, decided in `SET_twin_tau_0p65_and_geometry_gate`:
  a tentative gallery's two *text* files
  (`artifacts/curation/tentative/<stamp>/{gallery.jsonl,manifest.json}`)
  come through, because a clone that cannot resolve the IDs the site's figures name
  cannot rebuild the site. The pictures stay ignored, the un-ignore names the two
  files one by one rather than by pattern, and it is not an oversight to tidy up.
  **`index.html` was the third until 2026-09-05** and is not tracked for any stamp:
  Matt's ruling that a record is its rows plus its manifest and the page is a
  browse view `curate solve browse <stamp>` regenerates from them.
- **A tentative record is PUBLISHED only when Matt names it**, his ruling of
  2026-09-04, and the hole above is per *stamp* because of it: the store is
  ignored by default and each published stamp is one negation line. Recording a
  gallery and committing it used to be a single act, which meant a record too
  large to track was a record that could not be made — an n=2000 record's
  `gallery.jsonl` is over `MAX_TRACKED_BYTES`. Now every
  other record **stays in the store, ignored and kept**; what it does not get is
  a Durable-class save, check or restore and a place in an archive copy. It is
  read by naming its stamp, `tentative.latest()` resolves over published stamps
  only, and `curate solve list` marks each line. **Publication and durability
  are different questions**: `tentative.protected_keys()` sweeps the whole store
  published or not, so deleting a record is the only thing that releases its
  seats to the prune. `tentative.PUBLISHED` and `.gitignore`'s negation lines
  are one list written twice and `tests/test_tentative.py` holds them to
  agreeing. **`LARGE_TEXT_ALLOWLIST` was not the answer and was not touched.**
- **Weights come from GitHub Releases, not LFS.** `fractal-wallpapers fetch-weights`
  reads `models/weights.json` (head → release tag `weights-vN`, asset name, sha256),
  downloads into `models/<head>/`, and verifies the hash before keeping the file.
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
  file count is not a target to drive down. *Archive* (`E:\FractalStorage`,
  `storage archive <name>`) is finished bulk nothing reads routinely, restored
  before reuse. *Delete* is everything regenerable from what is hot and everything
  unreferenced — if nothing will want a thing back, its builder goes with it. The
  unit of the first two is a **top-level name**, so a subtree that has to move on
  its own is promoted to one first; `curation` can never move, being the live pool.
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
  [`process_control.child_priority_flags`], so only the count is the caller's.
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
  `models` extra is two gigabytes of CUDA wheels a clone that only renders should
  never pay for. `fetch-weights --check` has to run on that install, so its whole
  import graph is stdlib — which is why `models/roster.py` exists apart from `ship`.
  `tests/test_base_install.py` proves it in a subprocess with those imports refused,
  because every machine that runs the suite has torch.

## Checks to run before committing

```
python -m ruff check . && python -m ruff format --check .
python -m pytest --slow
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

CI runs the same thing on Ubuntu and Windows. The Python suite's walk tests need
a **release** engine (`cargo build --release --manifest-path engine/Cargo.toml`)
and skip themselves without one, so `cargo clean` costs a rebuild *and* the fast
lane until you do it. **A guard that asks whether the engine is built asks through
`try`/`except FileNotFoundError`**: `engine.engine_path` **raises** rather than
returning None, so a guard that asks it bare (`not engine.engine_path().is_file()`)
explodes while pytest is still collecting and interrupts the **whole lane**, not
just its own file.

### The two lanes

`python -m pytest` runs the **fast lane**; `python -m pytest --slow` runs every
test there is, and that is what CI runs and what runs before a checkpoint. The
fast lane is for the edit-run loop and nothing else.

Both are measured, not estimated. The tree holds **4,371 collected — 4,235 fast,
136 slow — since `palette_variant_mine_ckpt120` landed on 2026-09-11**, and the
pair was taken on this machine on an idle box after a render leg, on a
`.[dev,models]` install with a release engine built: the **fast** lane **141.28 s**
and the **slow** lane **4,371 of 4,371 in 510.20 s (8:30)**, both **green**,
**zero skips**.

The ten over the previous reading are all that prompt's, and they are **7 fast to 3
slow** while the clock moved **+0.64 s** and **+27.3 s**: the fast seven are
arithmetic over a seeded draw, and the slow three each render a recipe through
every renderer in the tree. A guard that costs nine seconds is not a guard to
regret — it is `tests/test_renderer_agreement.py`'s, the file that exists because
the same defect has now been found seven times.

**`5665ae6` left three reds that only the slow lane could see, and they are closed.**
Nine green fast lanes went past them. Two were the *guard* and not the tree — the
frozen corpus's absolute paths are a decision `data/gallery_grade/corpus/README.md`
had already argued out and the guard had never been told, and the 99
`p_fine_correction_20260909` rows naming no candidate are the `low_anchor` block,
which was never drawn from the pool. The third was real: `gallery_grade_train` spelled
the gallery-grade store's own directory itself, and
`labeling.gallery_grade.corpus_dir` owns it now.

The idle pair before it, 2026-09-09 at **4,277 collected**: **fast** 129.99 s over
the 4,145 it holds, 132 deselected; **slow** 4,277 of 4,277 green in 459.94 s (7:39),
zero skips. **200.85 s over 4,295** on the same era was a busy box and not the tree.
The two before that were 4,271 in 450.28 s and 4,235 in 448.94 s.
**The two lanes normally agree on the collected count**, which is what that
number is for, and they **do**: the pair above is one tree read twice.

**The long-standing red is closed and there is no expected failure any more**: a
lane with any red in it is a lane to read. `test_leveled_identity.py`'s census
held `run_index_named >= 13,526` as a **floor**, and a floor reads *the store only
grows* over a store that deletes by design — so it went red the first time mining
displaced rows and the gap widened with every merge. It is a **ratchet** since
2026-09-07: the count now, plus every deletion a transaction wrote down since the
high-water mark, still reaches that mark, with the mark advanced by `prune`
mechanically. **Repointing a census constant at today's reading is still the
forbidden edit**, and the ratchet is what makes it unnecessary rather than what
excuses it. **Zero skips is the normal reading now and 19 was the render cache
being short** — a **store** condition, not a tree fault, confirmed by the first
lane to read a full cache: `renders plan` then `renders build` is what fills it.
The 19 were worth roughly forty seconds of engine renders and a training loop, so
6:45 is not a regression against the 5:52 that skipped them. **A lane that skips
again is a short cache**, `--slow -rs` names them, and they are all inside the
slow-only tests over six `test_render_*` and `test_finished_train` files.
**`data/palettes` is a
parametrized guard**, so a drop moves both counts: `classic-pairs-2026-09` added
120 maps and therefore 120 collected tests with no test written, and a reading
taken across a drop is not comparable with one taken before it. Every reading this lane has taken is in
[`tests/README.md`](tests/README.md#the-lanes-readings-in-order), with what the box
was doing at the time — they are there and not here because this file loads into
every session and a chronological log is not a rule. What stays here is the current
figure and the rules the log produced.

- **A reading is comparable only against one taken on the same install**, and
  [`tests/README.md`](tests/README.md#what-the-fast-lane-count-means) defines the
  count once: selected and deselected both, or neither. **A count is not stable
  across interpreters** — a module-level `pytest.importorskip` stops a module being
  collected at all rather than skipping its tests, so an interpreter without `torch`
  silently runs a smaller suite; `conftest` prints a red line naming the missing
  import.
- **Measure on an idle machine, and take that literally.** Beside a render leg the
  lane does not merely slow, it is killed outright on commit charge, so **run the
  lane after a leg, never beside it**. Short of that,
  `test_twins.py::test_the_channel_only_ever_hands_over_what_nobody_has_walked`
  **fails** rather than slows under load, because it runs a refill loop against a
  wall clock — a red there on a busy box is worth re-running alone before it is
  worth reading.
  [`tests/README.md`](tests/README.md#a-lane-sharing-the-box-with-a-render-leg) has
  the measurements.
- **Re-run one untouched, engine-bound guard before believing a lane.** Forty
  seconds against seven minutes, and it answers *box or tree* on its own: a tenth
  either way on an invariant guard means the box.
- **A lane that moves right after code landed is the code until measured
  otherwise**, and the cheap check is one slow file re-run under a profile rather
  than the whole lane re-run hoping for a quieter box. Reaching for the box first
  has cost a session:
  [`tests/README.md`](tests/README.md#a-lane-that-moves-right-after-code-landed-is-the-code-until-measured-otherwise).
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
  Arithmetic stays in the fast lane however much of it there is. **A slow guard
  moves lanes; it is never deleted or weakened to make a lane faster** — the tests
  are this project's memory and every pin in them was bought by an incident.
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
  restating the prompt back.
- Then copy the report to `C:\Code\fractal-drive-sync\reports\`.
- **Operational facts learned on the way — launch commands, ports, drop paths,
  conventions — get promoted into the relevant module README as you pass them**, not
  left only in a scratch report. `scratch/` is defined as disposable; a fact worth
  writing down twice belongs in tracked documentation once.
- **A step estimated over about thirty seconds is backgrounded, not waited on.** Say
  what it was estimated at, launch it in the background, and poll — a training band,
  a render leg or a sweep over the tracked records is minutes to hours, and a prompt
  that blocks on one reports nothing until it lands.
- **The commit gate is part of the contract, not a step after it.** Commit to `main`,
  and when another prompt is in flight in this repository — anything `git status`
  lists as modified or untracked that is not yours — commit **only your own files, by
  explicit path**: `git add <path> …`, never `git add -A` or `git add .`.
- **One prompt at a time in this repository.** A second prompt does not start while
  another has uncommitted changes — wait for `git status` to come back clean. The
  by-explicit-path rule above is necessary and it is *not* sufficient: it governs
  what a commit adds and says nothing about what the index already holds, so a
  prompt that has staged a **deletion** has it swept into whatever the other prompt
  commits next. `915ede6` is what that looks like — three files deleted by a prompt
  that was still running, carried under a message about something else entirely.

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

- `src/fractal_wallpapers/labeling/corpus_import.py` (`import-labels`, with
  `tests/test_corpus_import.py`) — the location corpus brought across through the
  source's own sidecar and amendment rules. The store it wrote is tracked; the
  reader of the source is not needed again.
- `src/fractal_wallpapers/labeling/finished_import.py` (`import-finished`; no test
  file of its own, exercised through `tests/test_modes.py`) — the same for the two
  finished-render corpora. It calls `library_import`, so the two go together.
- `src/fractal_wallpapers/palettes/library_import.py` (with
  `tests/test_library_import.py`) — colormaps converted out of the source's pooled
  library, because an imported row names maps this repository did not hold. **Two
  live callers first**: `palettes/authored_import.py` and `models/palette_sets.py`
  both reach for it, so deleting it means answering what those do instead.
- `src/fractal_wallpapers/cli/import_commands.py` — the parsers and handlers for
  both of the above, and nothing else. The `cli` split made the two commands one
  file precisely so this is a file deletion plus its name in `cli/__init__.py`'s
  module list, rather than surgery inside a module that has other work to do.
- `src/fractal_wallpapers/models/acceptance.py`'s extraction path —
  `INCUMBENT_SCORES`, `INCUMBENT_MANIFEST`, `beside`, `ExtractionSourceGone`,
  `extraction_source` — reads `fractal-maker` and `fractal-maker-artifacts` beside
  this checkout to write a bar the first time. **Only the extraction half goes**:
  every *read* of a bar already runs against the vendored yardstick, which is
  tracked and stays.
