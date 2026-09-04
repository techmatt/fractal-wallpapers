# fractal-wallpapers

An ML-steered fractal wallpaper generator: a fast Rust escape-time renderer paired with neural judges trained on human taste to find, color, and select striking wallpapers across five fractal families. Companion repo to a full tutorial article (link TBD) — built with Claude.

## Running it

Python 3.11+ in a virtualenv at `.venv`, the package installed editable, and the engine built
in release. Release is not optional in practice: a debug engine is found and used, but runs
about ten times slower, and the Python walk tests skip themselves unless a release build
exists.

```
python -m venv .venv
.venv/Scripts/pip install -e ".[dev,models]"      # Linux/macOS: .venv/bin/pip
cargo build --release --manifest-path engine/Cargo.toml
```

**Everything runnable is a subcommand of one entry point**, installed into the venv as
`fractal-wallpapers`. Activate `.venv` and call it by name, or call it by path without
activating:

```
.venv/Scripts/fractal-wallpapers --help          # Linux/macOS: .venv/bin/fractal-wallpapers
```

A bare `python -m fractal_wallpapers.cli` runs only inside that venv; from a system Python it
fails with `No module named 'fractal_wallpapers'`. Prefer the entry point.

Fetch the trained judges before anything that scores:

```
.venv/Scripts/fractal-wallpapers fetch-weights
```

To hand a built sheet to a labeler, see [the labeling rig](src/fractal_wallpapers/labeling/README.md#serving-a-sheet-to-label).

## The five loops

There are about a hundred and fifty subcommands and they serve five jobs. Each
block below is the spine of one; every step has its own `--help`, and the package
README it links to is where the reasoning lives.

**Find new places**, so the candidate ledger has somewhere new to render — a walk
over parameter space, scored by the location head, and the frames worth keeping
folded in. See [discovery](src/fractal_wallpapers/discovery/README.md) and
[supply](src/fractal_wallpapers/supply/README.md).

```
fractal-wallpapers census                              # what each partition is owed
fractal-wallpapers harvest --finish-by 07:00           # the production loop, all night
fractal-wallpapers reframe --minutes 20 --out-dir artifacts/reframe_g1
fractal-wallpapers curate score --harvest artifacts/reframe_g1
fractal-wallpapers curate embed                        # a vector per admitted location
```

**Collect human taste**, which is what every judge here is trained on. See
[the labeling rig](src/fractal_wallpapers/labeling/README.md).

```
fractal-wallpapers label register --batch NAME --method "how the population was drawn"
fractal-wallpapers label build --from-plan artifacts/places.jsonl --batch NAME
fractal-wallpapers label serve --sheet artifacts/sheet
fractal-wallpapers label ingest --sheet artifacts/sheet --labeler matt --write
```

**Find good renderings of places already found** — the same location at other
modes, palettes and depths, priced against what the extra candidates buy. Three
legs, same shape: plan, run, merge. See
[curation](src/fractal_wallpapers/curation/README.md).

```
fractal-wallpapers curate hunt  run --name h1 --budget 1200    # breadth where the ledger is thin
fractal-wallpapers curate mine  run --name m1 --rate <measured> --budget 7200
fractal-wallpapers curate depth run --name d1 --rate 0.35 --budget 5400
fractal-wallpapers curate <leg> merge --name <name>            # fold into the ledger
fractal-wallpapers curate candidate-ledger census              # what is still thin
```

**Train a judge** and ship it, against a bar written down before the candidate
exists. See [models](src/fractal_wallpapers/models/README.md).

```
fractal-wallpapers tiles build                                 # or `renders build`, per head
fractal-wallpapers head preregister                            # the bar, first
fractal-wallpapers head train --run seed0_all_regimes --seed 0
fractal-wallpapers head score --run seed0_all_regimes
fractal-wallpapers head accept                                 # the band, against the bar
fractal-wallpapers head ship
fractal-wallpapers fetch-weights                               # what a fresh clone runs
```

**Choose a gallery** out of everything the ledger holds, and record it under a
name that never moves.

```
fractal-wallpapers curate headroom                     # what is short, and what one more costs
fractal-wallpapers curate solve run --n 150            # decide, then render the seats
fractal-wallpapers curate gallery record               # THAT solve, recorded
fractal-wallpapers curate gallery browse <stamp>       # the page, off the rows
```

## Putting the regenerable tree on another disk

Everything a run can always make again — tile caches, location views, render
caches, the pictures a study looked at — lands under `artifacts/`, which grows to
a hundred gigabytes or so. Everything that matters lives in the checkout instead:
records, labels, weights, code. So the tree is a setting, in two halves, and both
live in one untracked file at the repository root:

```toml
# local.toml — gitignored, one machine's own business
hot_root = "D:/Fast/fractal-wallpapers/artifacts"       # omit for artifacts/ in the checkout
archive_root = "E:/Slow/fractal-wallpapers/artifacts"   # omit if this machine has one disk
```

* **hot** is where work happens and where every write lands. Omit it and it is
  `artifacts/` under the checkout — which is what CI and a fresh clone get, and
  why neither has to know any of this exists.
* **archive** is slow bulk storage for subtrees nothing is using. Optional.

`FRACTAL_WALLPAPERS_HOT_ROOT` and `FRACTAL_WALLPAPERS_ARCHIVE_ROOT` override the
file for a one-off invocation. Setting one to *nothing* is a statement rather than
an omission: it says this machine has no such root, whatever the file says, which
is how a hot-only session says it does not want the archive consulted.

**A top-level subtree lives in exactly one tier**, and its tier is simply where
its files are — there is no registry to fall out of step with the disks. Reading
resolves hot first and falls through to the archive; writing always lands hot.
One name present in both tiers is refused by name rather than resolved by
preference, because a stale copy that silently wins is the one failure a
two-tier store has that nobody sees.

```
fractal-wallpapers storage status              # every subtree, its tier, its size
fractal-wallpapers storage archive tiles       # hot -> archive
fractal-wallpapers storage restore tiles       # archive -> hot
```

Every move copies, verifies — per-directory counts and bytes, every manifest row
resolving to a file that is there, a seeded sha256 sample — and only then deletes
the source, so an interruption costs time and never data. It measures its own
throughput on the first files and prints an estimate before it commits to the
wait.

**Restore before you train.** An archive on a USB hard drive serves a random
small-file read at about a fiftieth the rate of an NVMe, so a training pass over
an archived tile cache is tens of minutes an epoch with no symptom other than a
job that looks like it hung. `head train`, `renders train` and `palette train`
refuse outright when their cache resolves through the archive, and name the
restore command. Output is refused there too: writing into an archived subtree
would split it across both tiers.

**A configured root that is not there is refused, not worked around.** If the hot
root names an external disk that is unplugged, every command that needs the tree
stops and says so. It does not fall back to the checkout: an empty tree there
would read as a cache nobody had built yet, and the next build would spend hours
filling the wrong drive. An absent *archive* is narrower — work whose names are
all hot proceeds, and only a name the hot tier does not hold refuses, because
from there "archived" and "never built" are the same observation.

Records keep naming files under the tree as `artifacts/...` wherever the tree
actually is and whichever tier a subtree is on, and are resolved back through
`paths.rehome` when they are read — so a manifest, a ledger name or an acceptance
record means the same thing before and after a move. See
[the package README](src/fractal_wallpapers/README.md).

## Where things are documented

**Every directory explains itself, next to the code it explains.** There is no
`docs/` tree; a paragraph about a component lives in that component's own README,
where the thing it describes cannot move away from it.

```
engine/                     the Rust renderer: the spec it reads, what it makes
src/                        the Python side, one README per package —
  fractal_wallpapers/         coloring, curation, deep, discovery, labeling,
                              models, palettes, supply
data/                       the records: one README per store, plus what a row means
models/                     the trained judges, one README per head
tests/                      what the suite guards, and why each guard exists
```

## Checks

```
python -m ruff check . && python -m ruff format --check .
python -m pytest
cargo test --manifest-path engine/Cargo.toml
```
