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

`tests/test_banned_vocabulary.py` enforces the first paragraph. It matches a term
wherever letters do not touch it, so `_` and path separators count: the names this
rule is about are snake_case, and a `\b`-anchored guard cannot see them.

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
and skip themselves without one.

### The two lanes

`python -m pytest` runs the **fast lane**, about a minute. `python -m pytest
--slow` runs every test there is, about eleven minutes, and that is
what CI runs and what runs before a checkpoint. The fast lane is for the
edit-run loop and nothing else.

The eleven minutes is measured, not estimated: 3,058 tests in **11:08** on this
machine at `fcad496`, 2026-08-28, with the fast lane at 53.4 s over the 2,952 it
holds. It has been climbing — 7:20, 8:05, 8:45, 9:25, 9:46 and 9:52 were the six
runs before it — so read it as the order of magnitude and re-measure rather than
trusting the digit.

**The last step up is the one worth reading, because the suite did not move.**
9:52 and 11:08 are the *same 3,058 tests*; what grew in between was the store
they sweep, by 5,200 rows of candidate ledger. Nothing here proves the ledger is
the whole of it, but a lane that slows with no test added is a lane pricing data
rather than code — so re-measure after a **merge**, not only after writing
tests, and suspect the stores first when the digit moves on its own.
Measure it on an **idle** machine: the same lane sharing this one with a render
leg crawled to 41% in the time it normally takes to finish.

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
