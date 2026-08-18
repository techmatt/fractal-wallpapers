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

## Checks

```
python -m ruff check . && python -m ruff format --check .
python -m pytest
cargo test --manifest-path engine/Cargo.toml
```
