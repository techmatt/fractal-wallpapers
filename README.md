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

### Putting the regenerable tree on another disk

Everything a run can always make again — tile caches, location views, render
caches, the pictures a study looked at — lands under `artifacts/`, which grows to
a hundred gigabytes or so. Everything that matters lives in the checkout instead:
records, labels, weights, code. So the artifacts root is a setting, and moving
the tree to another drive is one untracked file at the repository root:

```toml
# local.toml — gitignored, one machine's own business
artifacts_root = "D:/SomeDisk/fractal-wallpapers/artifacts"
```

`FRACTAL_WALLPAPERS_ARTIFACTS_ROOT` in the environment overrides the file, for a
one-off invocation. Set neither — which is what CI and a fresh clone do — and the
tree is `artifacts/` under the checkout, exactly as before.

**A configured root that is not there is refused, not worked around.** If the
setting names an external disk that is unplugged, every command that needs the
tree stops and says so. It does not fall back to the checkout: an empty tree
there would read as a cache nobody had built yet, and the next build would spend
hours filling the wrong drive.

Records keep naming files under the tree as `artifacts/...` wherever the tree
actually is, and are resolved back through `paths.rehome` when they are read — so
a manifest, a ledger name or an acceptance record means the same thing on either
disk. See [the package README](src/fractal_wallpapers/README.md).

## Where things are documented

**Every directory explains itself, next to the code it explains.** There is no
`docs/` tree; a paragraph about a component lives in that component's own README,
where the thing it describes cannot move away from it.

```
engine/                     the Rust renderer: the spec it reads, what it makes
src/                        the Python side, one README per package —
  fractal_wallpapers/         coloring, curation, discovery, labeling,
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
