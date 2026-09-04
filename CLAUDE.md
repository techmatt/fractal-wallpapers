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
`GALLERY.md:1487`. A line number is not an anchor: it is correct until the next edit
to the file above it and then it is silently wrong, pointing at a real line that says
something else — which is worse than dangling, because nothing looks broken. Two
sites carried `§3709` into `curation/README.md`; by the time the split found them the
number had drifted to a different paragraph and neither citation had ever been
reported as stale. A heading survives every edit that does not rename it, and a
rename is a `git grep` away from being repointed.

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
  `cli/__init__.py` is the list of them plus `main`. The `_commands` suffix on
  those module names is load-bearing: eight top-level commands are also handler
  names, a submodule is set as an attribute of its package, and an attribute is
  one `__getattr__` never sees — so `cli/render.py` would shadow `cli.render`
  for good. Handler names resolve through `__getattr__`, never re-exported, for
  the reason `2dc6a8b` gives.
- **Records are JSONL**: UTF-8, one JSON object per line, carrying an integer
  `schema` field from the very first row. A label row carries its full join — the
  label *and* the complete render parameters in the same row — so a labeled example
  is never split across files. Every random draw is seeded, and the seed is recorded.
- **Git history stays text.** `tests/test_history_purity.py` fails the build if a
  tracked file is binary-by-nature or exceeds 1 MiB. It keeps two allowlists and
  they are not interchangeable: `ALLOWLIST` excuses a file from both rules and is
  empty, `LARGE_TEXT_ALLOWLIST` excuses a *prefix* from the size rule alone and
  still holds it to being text. The only entry is `data/palette_choice/rows/`,
  the palette head's distillation corpus, on Matt's call. Adding to either is a
  decision, not a fix.
- **`.gitignore` keeps its shape**: `scratch/` and `artifacts/` (runtime output),
  `models/**/*.pt` (fetched weights, living beside their tracked metadata), and
  toolchain noise. Do not interleave tracked and ignored content beyond that — a
  tracked file inside an ignored tree is how these rules rot. **There is exactly
  one hole and it is deliberate**, decided in `SET_twin_tau_0p65_and_geometry_gate`:
  a tentative gallery's three *text* files come through
  (`artifacts/curation/tentative/<stamp>/{gallery.jsonl,manifest.json,index.html}`),
  because the site's figures name wallpapers by the IDs in them and a clone that
  cannot resolve those IDs cannot rebuild the site. The pictures stay ignored, the
  un-ignore names the three files one by one rather than by pattern, and
  `.gitignore` carries the whole reasoning. It is not an oversight to tidy up.
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
  command line overflows long before the batch does. Anything writing a tracked
  text file opens it `newline="\n"`: `.gitattributes` normalizes what git
  stores, and this is what stops a Windows run dirtying every line of a file it
  rewrote. **The drift this prevents is invisible to `git status`** — under
  `* text=auto eol=lf` a CRLF worktree file still commits as LF, so `git diff`
  comes back empty while every line waits to change at once. Twenty tracked
  files had drifted before anything looked. `tests/test_line_endings.py` is the
  guard, `git ls-files --eol` is the only detector that works here (Git Bash's
  `grep` reports a CR on every line of a pure-LF file), and checkout is not the
  cause: a fresh clone comes out LF throughout despite `core.autocrlf=true` in
  the system git config.
- **Where a file under `artifacts/` belongs is a three-way decision, and it is
  made once per subtree.** *Hot* (`artifacts/`) is what a live command in the loop
  reads: the pool's pictures and rows, the sidecars, the current records. Its file
  count is the pool's and is not a target to drive down. *Archive*
  (`E:\FractalStorage`, `storage archive <name>`) is finished bulk worth keeping
  that nothing reads routinely — training material, finished legs, look sheets —
  and it must be restored before reuse. *Delete* is everything regenerable from
  what is hot and everything unreferenced; if nothing will want a thing back, its
  builder goes with it. The unit of the first two is a **top-level name**, so a
  subtree that has to move on its own gets promoted to one first — `curation`
  itself can never move, because it is the live pool.
- **A picture with no ledger row is garbage, and there is a sweep for it.**
  `curate candidate-ledger orphans` lists by default and deletes with `--apply`.
  Run it after any killed leg and periodically. **An unmerged leg is listed and
  never swept unread**: it is real work with no row anywhere, so it is taken only
  when somebody reads the listing and names it (`--leg <name>`, or
  `--include-unmerged` for all of them).
- **The render pool is three workers at below-normal priority.** That is the
  standard shape of every leg that drives the engine — a measure pass, a sheet
  build, a hunt, a mine — and it is a rule about this machine rather than a
  tuning knob: more than three `fractal-engine.exe` at once, or any of them at
  normal priority, makes the desktop unusable while the leg runs. `engine.run`
  spawns below-normal by construction through
  [`process_control.child_priority_flags`], so the priority half is not
  something a caller has to remember; the worker count is the caller's and
  three is the number.
- **ONE POOL-HOLDING PROCESS PER BOX.** Anything that loads the candidate pool —
  `curate growth`, `curate solve run`, `curate solve record`, and the slow test lane
  counts as one — never runs concurrently with another on the same machine. The
  pool is hundreds of megabytes read whole and held whole; two of them at once is
  the box swapping rather than two legs finishing sooner, and a lane sharing the
  machine with one is a lane whose wall-clock guards start failing for a reason
  that is not in the code.
- **Search the source with `git grep`, never `grep -r` from the root.** This checkout
  carries a hundred gigabytes and four hundred thousand files of untracked
  `artifacts/`, plus `.venv/`, `models/` and `engine/target/`, against under two
  thousand tracked files. A recursive grep reads all of it and takes tens of minutes;
  `git grep` walks the index and answers in a fraction of a second. `rg` is fine too —
  it honours `.gitignore` — but `grep --include=*` does not, and that is the trap.
- **The base install stays torch-free on the `fetch-weights` path.** `pip install
  -e .` buys the engine, the walk, the supply engine and the labeling rig; the
  `models` extra is two gigabytes of CUDA wheels a clone that only renders should
  never pay for. `fetch-weights --check` has to run on that install, so its whole
  import graph is stdlib — which is why `models/roster.py` exists apart from
  `ship`. `tests/test_base_install.py` proves it in a subprocess with those
  imports refused, because every machine that runs the suite has torch.

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
and skip themselves without one. They skip only because each of them asks
whether the engine is built through a `try`/`except FileNotFoundError` —
`engine.engine_path` **raises** rather than returning None, so a guard that
asks it bare (`not engine.engine_path().is_file()`) explodes while pytest is
still collecting and interrupts the **whole lane**, not just its own file.
`tests/test_palette_strip.py` was that guard once. So `cargo clean` costs a
rebuild *and* the fast lane until you do it.

### The two lanes

`python -m pytest` runs the **fast lane**, about three minutes. `python -m pytest
--slow` runs every test there is, about six and a half, and that is
what CI runs and what runs before a checkpoint. The fast lane is for the
edit-run loop and nothing else.

Both are measured, not estimated, and **the readings live in
[`tests/README.md`](tests/README.md#the-lanes-readings-in-order)** — every one this
lane has taken, with what the machine was doing at the time. They are there and not
here because this file is loaded into every session in this repository and a
chronological log is not a rule. What stays here is the current figure and the rules
the log produced.

The fast lane is **122.97 s over the 3,565 it holds**, on this machine, idle,
2026-09-04, at the re-mode leg — twenty-seven tests more than the solve speedups'
120.29 s and 2.68 s over it, about a tenth of a second a test. The slow lane is
**6:31 over 3,681, nothing skipped**, on this machine, idle, 2026-09-04, at the
same commit — thirty-three tests more than the `exp_smoothing` drop's 6:54 over
3,648 and **24 s under it**. That is the first slow reading to fall while gaining
tests, and the cause is the solve speedups of `4300e4b` rather than anything the
re-mode leg did: this lane holds guards that run a solve pass, and that pass got
faster. **A lane that gets cheaper with no test removed is benign only when
something it prices got faster** — the rule below about suspecting a defect is
about a lane getting *slower*, and this reading is its counter-example.

**What the count means is defined once, in
[`tests/README.md`](tests/README.md#what-the-fast-lane-count-means)**, and a reading
is comparable only against another taken on a `.[dev,models]` install with a release
engine built. Selected and deselected both, or neither — the clock alone has been
written down here twice and both times it was the count that settled the argument.

**The 118.50 s this figure came off was a third off, and not an optimisation.** The
same tree at
`9a62672`, measured the same evening on the same idle box, is **177.48 s** over the
same tests. The difference is three test files that had been reading this machine's
**real** 67k-row supply sidecar and its real expressed readout on every test, because
they redirected the ledger store per accessor and no accessor list named those two.
Redirecting at the tier roots instead moved them, and the price went with them. So the
figure is a lane that stopped pricing data it was never meant to read — and the rule
that follows is the one below about redirecting at the roots.

**The 57 that would not reproduce were an interpreter with no `torch`, and the lane
now says so out loud.** Masking `torch` and `timm` reproduces the whole logged reading
to the unit — 3,369 passed / 14 skipped / 109 deselected. A module-level
`pytest.importorskip` does not skip a module's tests, it stops the module being
collected at all, so eight torch-gated files took 65 fast tests and 5 slow ones out of
the totals and left eight "skipped" behind. The tree was never the variable and
`test_colormaps.py` never was either. `conftest` prints a red line naming the missing
import now, because the whole failure was that nothing on screen said the suite had
shrunk. **A count is not stable across interpreters, only across installs**, which is
why the standing figure names the install it was taken on.

**Its first reading that session was 300.7 s and the extra 135 s was a defect, not the
box.** That run also failed `test_training_resume.py` on a CUDA OOM with six other
processes holding the GPU, which made "measure it on an idle machine" the obvious
diagnosis and the wrong one. The cost was `hunt.recorded_prices` walking the leg
records and parsing a `sequence.jsonl` per band — 0.65 s a band, 3.35 s for the five
`depth.DRAWS`, and `depth.plan` asks for all five, so every guard that plans a leg paid
it. Caching it took the lane back to flat. So the rules below about suspecting the
disk, the stores and the load are right and they are **not** the first thing to reach
for: a lane that moves right after code landed is the code until measured otherwise,
and the cheap check is to re-run one slow file with a profile rather than to re-run the
whole lane hoping for a quieter box.

**The lane does not merely slow beside a render leg on this box — it dies.** Run twice while
the leg's three engines held the pool, it was killed at 77% with no summary and no traceback
both times. That is the commit-charge ceiling `models/render/README.md` documents (the leg's
parent holds ~3.3 GB and each of three workers ~0.9 GB), not the wall-clock guard the
paragraph below describes. Run the lane after the leg, never beside it.

Measure it on an **idle** machine, and take that literally. The same lane sharing
this one with a render leg crawled to 41% in the time it normally takes to
finish, and under load
`test_twins.py::test_the_channel_only_ever_hands_over_what_nobody_has_walked`
**fails** rather than merely slows — it runs a refill loop against a wall clock.
A red there on a busy box is worth re-running alone before it is worth reading.

**A lane that slows with no test added is a lane pricing data rather than code**,
and this one has done it twice. It was 160 s on 2026-08-26 and **18:07** on
2026-08-29 over the same tests, because `artifacts/curation/candidate_ledger/`
went from 15,362 rows and 41 MB to 366,236 rows and 1.11 GB in those three days —
and seven guards each read the whole of it. So: re-measure after a **merge**, not
only after writing tests, and suspect the stores first when the digit moves on
its own.

**And suspect the disk after anything that moves hundreds of thousands of paths.**
On 2026-08-30 the lane nearly doubled right after 194,058 levelled colormap
directories came off `artifacts/` — the stores got *smaller* — and came back on its
own hours later with nothing reverted. Suspected NTFS metadata settling after a bulk
small-directory delete; never proven, and the reason to re-run a slow lane before
believing one. The whole episode is in
[`tests/README.md`](tests/README.md#the-lanes-readings-in-order).

Two rules came out of that and `tests/README.md` argues both. **The candidate
ledger is read once a session**, through `conftest.tracked_ledger`; a test that
calls `candidate_ledger.read()` itself is a test adding forty seconds to the
lane. And **a guard that sweeps it takes a budget rather than the store** — the
two that did not had each lost their own docstring's cost estimate by an order of
magnitude, and both now state the constant, the measurement behind it, and an
assertion that the budget was filled. That is the one place this suite trades
coverage for time, it is written down at each site, and it is not a licence
elsewhere: the rule below still stands.

A test earns `@pytest.mark.slow` by costing about a second or more of **real
work** — a render through the engine, a training loop, or a sweep of a store:
the render cache, the tracked pool, the distillation corpus. Arithmetic stays in
the fast lane however much of it there is. **A slow guard moves lanes; it is
never deleted or weakened to make a lane faster** — the tests are this project's
memory and every pin in them was bought by an incident.

The fast lane prints how many tests it held back, on every run that holds any
back. That line is the point of the arrangement rather than a decoration: a lane
that went quiet would be a set of guards nobody would notice had stopped
running. `tests/conftest.py` owns the marker, the flag and the line.

One trap worth knowing before marking anything: several of these guards share a
cached derivation, so moving one to the slow lane can simply hand its cost to
whichever sibling reads the cache next. Measure the fast lane after marking, not
before — a mark that bought nothing is a guard given up for nothing.

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
  commits next. That is not hypothetical — `915ede6` carries `seating.py`,
  `test_seating.py` and the old `test_solve.py`, deleted by a prompt that was still
  running, under a message about something else entirely. Nothing was lost and the
  history is wrong anyway, which is the cheap version of this failure.

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
