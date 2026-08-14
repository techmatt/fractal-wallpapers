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
  tracked file is binary-by-nature or exceeds 1 MiB. Its allowlist starts empty;
  adding to it is a decision, not a fix.
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
  `src/fractal_wallpapers/process_control.py` and nowhere else.

## Checks to run before committing

```
python -m ruff check . && python -m ruff format --check .
python -m pytest
cargo build --manifest-path engine/Cargo.toml
cargo test --manifest-path engine/Cargo.toml
```

CI runs the same thing on Ubuntu and Windows. The Python suite's walk tests need
a **release** engine (`cargo build --release --manifest-path engine/Cargo.toml`)
and skip themselves without one.

## Standing prompt contract

Each prompt in this project ends the same way:

- Write the final report to `scratch/<prompt_name>_report.md`. **~60 lines is a soft
  target** — write it once, allow at most one trim pass, and never iterate to squeeze
  under the line. Going over is fine; padding and re-editing are not.
- Report findings, numbers, decisions, and surprises only. No process narration, no
  restating the prompt back.
- Then copy the report to `C:\Code\fractal-drive-sync\reports\`.

## Rules

- Commit to `main` only.
- **No commit ≥20 MB** — single blob or aggregate — without Matt's explicit prior
  confirmation.
- Every prompt names its target repository; if the working directory is not that
  repository, stop immediately and say so rather than guessing.

---

## Build-era workflow *(delete this section at publication)*

`C:\Code\fractal-maker` is the **read-only** extraction source for this rewrite:
read from it freely, never write to it. Code arriving from there gets renamed to fit
the naming rule and cleaned before it lands here — nothing is copied wholesale.
