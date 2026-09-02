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

**The rule stands and no test here enforces it**: the guard is the website's,
`builder/vocabulary.py` in the `fractal-website` checkout, swept by its
`builder/checks.py`.

## Locked conventions

These were decided once, at the first commit, because each is expensive to reverse.

- **Rust makes every pixel; Python never renders.** Python reaches the engine only
  through `src/fractal_wallpapers/engine.py`. No other module shells out to the
  binary or computes image data itself.
- **Everything runnable is a subcommand** of `fractal-wallpapers` (see `cli.py`).
  There is no `scripts/` directory and there never will be one.
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
  tracked file inside an ignored tree is how these rules rot.
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
  rewrote.
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
  `curate growth`, `curate solve`, `curate gallery record`, and the slow test lane
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

`python -m pytest` runs the **fast lane**, about five minutes. `python -m pytest
--slow` runs every test there is, about sixteen, and that is
what CI runs and what runs before a checkpoint. The fast lane is for the
edit-run loop and nothing else.

Both are measured, not estimated: **3,152 tests in 5:45**, with the fast lane at
**98.3 s over the 3,039 it holds**. On this machine, idle, 2026-08-31, at the
commit that cut the lane — which is the entry to read first, because that
prompt found the lane was never a broad tax: the **top eighty tests were 490.6 s
of the 563.5 s** it started at, and the other three thousand were 72.9 s between
them. It came down by collapsing derivations paid many times over and by taking
one pixel-exactness pin off production's raster, and **no guard was deleted or
moved lanes**. `tests/README.md` carries the table and the reasoning; the one
worth knowing here is that `served_locations.build` was asking `current_pass`
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
