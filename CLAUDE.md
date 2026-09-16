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
  an absolute path. It carries **four** exemption lists and **no two of them excuse
  the same rule**, so an entry earns each one separately and moving a name between
  them changes what it is held to. Each is on Matt's call, each has its reason
  written at the site in full, and adding to any of them is a decision, not a fix.
  The lists and the argument for every entry are in `test_history_purity.py` at
  the constants themselves.
- **`.gitignore` keeps its shape**: `scratch/` and `artifacts/` (runtime output),
  `models/**/*.pt` (fetched weights, living beside their tracked metadata), and
  toolchain noise. Do not interleave tracked and ignored content beyond that — a
  tracked file inside an ignored tree is how these rules rot. **There is exactly
  one hole and it is deliberate**: a published tentative gallery's *text* files
  (`artifacts/curation/tentative/<stamp>/{gallery.jsonl,manifest.json}`) come
  through, because a clone that cannot resolve the IDs the site's figures name
  cannot rebuild the site. The pictures stay ignored, the un-ignore names the
  files one by one rather than by pattern, and it is not an oversight to tidy
  up. `index.html` is not tracked for any stamp. **A third file joined it on
  2026-09-14 and for ONE stamp only**: `20260914T171846Z`'s `recipes.jsonl`, a
  `{key, recipe}` row per seat at 0.68 MiB, because 994 of that record's 1,000
  seats could not be drawn from tracked data at all — the key is a one-way digest
  and the recipe behind it lives in the untracked ledger. Its negation line names
  that stamp's path rather than a pattern, so writing another record's is a
  decision each time; `render --recipe FILE --key <seat>` is the door that draws
  one back, and a redraw is byte-identical.
- **A tentative record is PUBLISHED only when Matt names it**, his ruling of
  2026-09-04, and the hole above is per *stamp* because of it. An unpublished
  record is read by naming its stamp, and what it does not get is a Durable-class
  save, check or restore and a place in an archive copy. `tentative.PUBLISHED` and
  `.gitignore`'s negation lines are one list written twice and
  `tests/test_tentative.py` holds them to agreeing. The ruling, what it replaced
  and why `LARGE_TEXT_ALLOWLIST` was not the answer are at
  `curation/tentative.PUBLISHED`. **`20260914T171846Z` is the published n=1000
  record** and the official one, his ruling of 2026-09-14 and the first
  publication since the split — what an unqualified "the record" and an unstamped
  `tentative.latest()` both mean. **The page to open is
  `artifacts/curation/viewer/index.html`**, `curate solve browse --viewer`, which
  carries no stamp so the bookmark survives the role moving.
- **An unpublished record is DISCARDED by default**, Matt's ruling of 2026-09-13,
  which reverses what this file said until then. **Keeping needs a reason;
  discarding does not** — it is not a balance a leg weighs at the end of its run.
  A leg that recorded a gallery to measure something against **deletes it when the
  measurement is taken and says so in its report**: a solve is cheap to run again,
  and what a leftover record costs is misreading hazard, not bytes. **The keep list
  is code**: `tentative.PUBLISHED` plus `tentative.KEPT_UNPUBLISHED`, which carries
  its eight entries with the reason for each written at the site. Everything else
  goes unless Matt says otherwise. **The keep list holds sixteen** — eight
  published and eight not — and a stamp earns its keep from exactly one of the two
  lists, `20260914T171846Z` being in `PUBLISHED` and therefore not in the other.
  ⚠ **The store is not the keep list and on 2026-09-15 it held 96 records, 80 of
  them off it** (61.4 MiB, five batches of solve records from this checkpoint's own
  prompts). None pins anything, since `protected_keys()` reads the two tuples and
  nothing else; what they cost is misreading hazard. **A count of folders is not a
  count of kept records** and a leg that wants to know what is kept reads
  `tentative.kept()`.
- **Publication, durability and retention are three questions and not one.**
  `tentative.protected_keys()` reads `tentative.kept()` — `PUBLISHED` plus
  `KEPT_UNPUBLISHED` — **and nothing else**, so preservation is a line in a tuple
  and never a folder existing. A record off that list is readable by naming its
  stamp and pins nothing. The test for a `KEPT_UNPUBLISHED` entry is that something
  **resolves** the record — code reading its rows, a figure naming `<stamp>|<key>`
  — not that something mentions it. ⚠ It swept the whole store until 2026-09-13,
  which made an ephemeral artifact confer preservation and is why sweeping kept
  landing on Matt's desk as a recurring approval; there is no sweep step to carry
  forward any more.
- **A collection's size is in `curation/targets.py` and nowhere else**, Matt's cut
  of 2026-09-15. Sixteen collections — twelve hue families, four modes — and a
  prompt that names a seat count is a prompt retyping one of the sixteen, which is
  how they drifted before the table existed. `curate solve run --collection NAME`
  and `curate solve record --collection NAME` take `n` from it, splice a family or
  filter a mode through `targets.pool_for`, and `--n` still overrides. **A
  collection the table does not name refuses** rather than seating a plausible
  number. Changing a target is a one-line edit to `TARGETS`, and the reason for
  each tier is written at the constant.
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
- **`dev` is the suite's install and is not the base install.** It carries `numpy`
  and `pillow` since 2026-09-15, because the suite does not run without them —
  `pillow`'s absence was 113 failures and, once three modules imported it at module
  level, the entire CI run at collection. Three megabytes against the `models`
  extra's two gigabytes is the whole of the argument, and it moves nothing on the
  package's own path. **What stays out is `torch`, `torchvision` and `timm`**, and
  a test reaching one of those is held to skipping rather than failing, two ways:
  `tests/test_lanes.py` sweeps every test module for an unguarded module-level
  import — one of those aborts the **whole lane** at collection, not its own file —
  and `conftest.pytest_runtest_call` catches the call-time arrivals, which no sweep
  of `tests/` can see because sixteen modules under `src/` import torch inside a
  function body. Both read their population from `cli.EXTRA_FOR` less `dev`.
- **CI's red is readable without `gh` and without admin rights.** The repository is
  public: `api.github.com/repos/techmatt/fractal-wallpapers/actions/runs` gives the
  runs and `runs/<id>/jobs` gives **step-level** conclusions. Job *logs* need
  admin and 403; step conclusions do not, and they are enough to say which step
  failed on which job. Reproducing the failure is a mask at `sys.meta_path` —
  `tests/test_base_install.py` already carries the finder — and the block list for
  a `check` job is `torch,torchvision,timm`, **not** `numpy`, which `scipy` brings.

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

Both are measured, not estimated. The tree holds **4,895 collected — 4,740 fast,
155 slow — since `portable_stores_ckpt127` added 14 tests on 2026-09-16**, on a
`.[dev,models]` install with a release engine built. **Fast: 4,740 in 153.05 s
(2:33)** with 155 deselected. **Slow: 4,895 in 529.77 s (8:49).** The two lanes
agree on the count and read zero skips. ⚠ Each carried **one** red, the same one — an
`E:/` path in a README that `test_no_absolute_paths_in_source` caught — fixed and
re-run green with its neighbours (183 of 183), not by re-taking the pair.
`tests/README.md` carries the reading.

The pair before it, `rotation_tone_curve_ckpt127`'s 4,881 / 4,726 in 137.99 s and
502.25 s, was green throughout.

**That pair closes the ⚠ two half-measurements left here** on 2026-09-16:
`overnight_mine_ckpt126` (+8, `curate score --graded`) and
`preclose_atlas_maker_ckpt126` (+17 in `tests/test_atlas.py`, +1 colormap parametrize)
were both told to skip the slow lane, so the tree was *believed* at 4,876 / 4,721. It
was: 4,881 is that plus this prompt's five. `tests/README.md` carries the reading.

**The pair before it** (`survivors_humanplaces_ckpt126`, 4,850 / 4,695, 140.80 s and
486.11 s) **closed the ⚠ that stood here then**, which asked for exactly it:
`consolidate_ckpt125` read 4,685 fast on 2026-09-15 and Matt said skip the slow
lane, so the figure was deliberately left pointing at 4,676. The arithmetic between
the two is **4,685 + 5 new guards for `curate score --opened` + 5 the three commits
after `consolidate_ckpt125` added without re-measuring**, and the five nobody
measured are what *take the pair whether or not the prompt wrote a test* exists to
catch — they were found by the two lanes meeting and not by anybody noticing.

**Neither lane moved outside the noise.** Fast +5.03 s and slow +9.18 s against
figures taken on other days and other box states; the five new guards are stub-row
arithmetic and cost nothing measurable. ⚠ **This pair was taken on a box twenty
minutes after a render leg and a pool merge**, so the page cache was warm for the
stores and cold for nothing that matters; read the deltas as box and not as tree
unless a third reading agrees with them.

**The slow lane fell 15.8 s while the tree grew by ten tests**, and the likely cause
is that same change generalized: `conftest.no_live_supply_sidecar` now stops **every**
test reading `artifacts/curation/supply_scores.jsonl`, and `tests/README.md` prices
that read at 4.5–10 s for each of `test_ledger_tracking`'s merges alone. ⚠ Not
decisively measured — no profile was taken either side — so it is a lead and not a
finding.

**The slow lane fell 4.7 s while the tree grew by fourteen tests**, which closes
`targets_ckpt125`'s ⚠ the cheap way: it read 513.49 s and did not chase the residue
after finding the ledger's overnight growth and a warm box between them. Nothing
here was done to make it faster — the fourteen are all fast-lane arithmetic and no
guard moved lanes — so the 33.0 s it could not account for was the box, and a second
pair on a quieter one was the decisive check rather than the `git worktree` that was
planned. The +14 cost the fast lane **+3.19 s**, which is what fourteen guards over
an `ast` sweep and a store-free derivation cost.

⚠ **The figure stood at 4,630 and the tree was already at 4,639**, because three
commits after `PRECLOSEOUT_ckpt123_wallpapers` added tests without re-measuring.
That is what *take the pair whether or not the prompt wrote a test* is for, and the
drift was caught by the two lanes meeting rather than by anybody noticing. The fast
lane has landed on `lane_speedup_ckpt122`'s 125.12 s to a tenth twice — which
settles that its ~9 s and ~12 s were the box and not the tree.

`lane_speedup_ckpt122`'s own pair is **34.3 s and 80.8 s faster** than the baseline
taken on the same tree an hour before it, and **no guard was deleted or weakened** to get there: one production
derivation was memoized and sixteen guards that cost a second or more of real store
work moved to the lane the marking rule already put them in. **A slow lane that
absorbed sixteen guards and still fell** is the shape to expect from that trade.
`tests/README.md`'s *lane_speedup_ckpt122* carries the measurements, and the two
speedups it **refused** — collapsing `test_colormaps.py`'s 1,021-case parametrize,
which is 22% of the suite's count and **0.00 s** of its clock, and sharing the package
sweep, which is **35 ms**. **A count is not a cost.**

**Every reading this lane has taken is in
[`tests/README.md`](tests/README.md#the-lanes-readings-in-order)**, with what the box
was doing at the time. They are there and not here because this file loads into every
session and a chronological log is not a rule. What follows is the current figure above
and the rules that log produced.

- **Take the pair whether or not the prompt wrote a test**, and *the two lanes agree on
  the collected count* is the check that catches a stale figure — a reading is only ever
  a reading of the tree in front of it, and counts have drifted here across prompts that
  never re-measured.
- **A lane with any red in it is a lane to read.** There is no expected failure any more.
- **Repointing a census constant at today's reading is the forbidden edit.** A census
  that went red because a store deletes by design is fixed by a **ratchet** —
  `test_leveled_identity.py` is the worked example — and the ratchet is what makes the
  repoint unnecessary rather than what excuses it.
- **Zero skips is the normal reading, and a lane that skips is a short render cache** —
  a store condition, not a tree fault. `--slow -rs` names them; they are all slow-only
  tests over six `test_render_*` and `test_finished_train` files. **An ingest shortens
  the cache by exactly the rows it lands and a sheet build does not** (a sheet's pictures
  land under `artifacts/sheet/` and no store gains a row until `label ingest` runs), so
  run `renders plan` then `renders build --workers 3` after an ingest. The per-crop cost
  is the store's and varies by head; `tests/README.md` has the measurements.
- **A fixture that reads one tracked answer once can be worth more than the tests it
  serves cost.** `models.palette_sets.cyclic` parses all 1,021 colormap documents on
  every call, and anything that builds a recipe reaches it, so a file that resolves one
  per test pays it per test — `conftest.shipped_cyclic_maps` is the fix and it cut
  `tests/test_repetition.py` by two thirds. Ask what a new file pays per test before
  accepting its clock.
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
  **The cheapest decisive check is a `git worktree` at `HEAD`** with
  `FRACTAL_WALLPAPERS_HOT_ROOT` pointed at the real store: it measures the OLD code
  on TODAY's box, which is the one comparison a re-run of the new code cannot make.
  `repo_bootstrap_fixes_ckpt124` split a 35 s move into 15 s of box and 20 s of tree
  that way in five minutes, then found the 20 s in one file.
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
  2026-09-15, which reverses what this file said until then. It said *a slow guard
  moves lanes; it is never deleted or weakened* — the tests are this project's
  memory — and the thing that changed is that the slow lane is now too slow to run
  as often as it should be, which costs more than a thin guard does. **Slight loss
  of fidelity is acceptable; a 1:1 equivalent is not required.**
  What is still required is that the trade is **named and priced**, because the
  failure this replaces one rule with another to avoid is a suite that quietly got
  weaker and nobody could say where:
  - **Say what stopped being covered, at the site and in the report** — a sample
    where there was a census, four modes where there were twenty, a claim dropped.
  - **Price it.** A cut with no seconds beside it is not a speedup, it is a
    deletion; `--durations=0 --durations-min=0` summed by file is how this repo
    finds its time and `tests/README.md` carries the method.
  - **Take the pure wins first.** They cost nothing and they are usually there:
    `present_pictures` gave 5.1 s of the pool layout on the day this rule changed,
    by keying a dict on a string instead of a `Path`, and it sped every production
    solve with it. Reach for coverage only once those are gone.
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
- **Arm a completion waiter in the same breath as the launch, and wait on the REAL
  process.** A launcher wrapper exits first and its exit code says nothing about the
  leg — waiting on one has started a unit on top of a still-running merge twice in
  one night, and it caught this checkout again on 2026-09-15 (`nohup … &` returned
  instantly and reported success while the leg had barely begun). A long run also
  carries a **15-minute heartbeat with a wall-clock timestamp**: a night once lost
  two units to a session that went quiet for two and three quarter hours with budget
  remaining. ⚠ **A heartbeat detects nothing on its own** — that stall wrote
  `engines=0` six times and nothing read it — so the heartbeat is for the reader and
  the waiter is what wakes the session.
- **What arms a waiter is a step that WAITS, not a step that LAUNCHES**, and the
  case the rule above misses is a **handover**: waiting on another checkout to go
  clean, on another session, or on a person. `overnight_mine_ckpt126` was staged
  against a held tree, said it would watch `fractal-website` for the lock, and armed
  nothing — no background job, no `until` loop, no scheduled wake-up. That checkout
  committed twice and went clean, and **nine hours of producing budget were lost**
  with the repository still at the same HEAD in the morning. A stated intention is
  not a mechanism: the only thing that returns control to a session is a tool call
  completing, so **an idle turn IS the stall**. Block in the foreground on the real
  condition (`until [ -z "$(git -C <repo> status --short)" ]; do sleep 60; done`)
  with a generous timeout, or background that same loop so its exit fires one
  notification. ⚠ A handover is the one moment with **no launch to hang the waiter
  off**, which is exactly why it is the moment it gets skipped.
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
