"""The style compositor as WebAssembly: the bundle a page draws from, and its checks.

The module is `style-wasm/` (`engine/README.md`'s *The style module*): the engine's own
`style::measure` and `style::tile` behind a few raw exports, with the three rules
`style render` lays on a style file before the engine sees it. This side writes what a
page needs to draw a published mode without copying one by hand, the **bundle**, and
holds the module to the native engine:

```
fractal-wallpapers style bundle [--out <bundle.json>]
fractal-wallpapers style wasm-parity [--resolution 640 400 --supersample 2]
fractal-wallpapers style wasm-speed
```

`wasm-parity` draws every keep the catalog shows for a published mode both ways and
compares the bytes; `wasm-speed` times one 1280x800 frame per published mode on one
thread. Both run the module under Node (`style-wasm/js/node-render.mjs`), and refuse
without a built module, naming the build.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

#: The bundle's shape. A page reads it and nothing else of this checkout.
BUNDLE_SCHEMA = 1

#: The parity check's default size: a quarter of a keep's 2560x1600 in each axis, at the
#: keep's own supersample. Every frame-wide statistic is measured at whatever size is
#: drawn, so a smaller frame runs the same code; it is the cheap size, not another path.
PARITY_RESOLUTION = (640, 400)
PARITY_SUPERSAMPLE = 2

#: The speed reading's frame: the draft size `style render --draft` checks at.
SPEED_RESOLUTION = (1280, 800)
SPEED_SUPERSAMPLE = 2

#: The tile the parity check's tiled draw cuts the picture into.
PARITY_TILE = (256, 256)

BUILD = (
    "cargo build --release --target wasm32-unknown-unknown --manifest-path style-wasm/Cargo.toml"
)


class StyleWasmError(RuntimeError):
    """The module is not built, or Node is not on the path."""


def crate_dir() -> Path:
    from fractal_wallpapers.paths import repo_root

    return repo_root() / "style-wasm"


def wasm_path() -> Path:
    """Where `cargo build --release --target wasm32-unknown-unknown` leaves the module."""
    return crate_dir() / "target" / "wasm32-unknown-unknown" / "release" / "style_wasm.wasm"


def out_dir() -> Path:
    """The default home of a bundle and of a check's pictures: regenerable, hot."""
    from fractal_wallpapers.paths import hot_root

    return hot_root() / "style-wasm"


def colormap_of(name: str) -> dict[str, Any]:
    """A library map's file, whole: the module takes it in the file's own shape."""
    from fractal_wallpapers.paths import colormap_dir

    return json.loads((colormap_dir() / f"{name}.json").read_text(encoding="utf-8"))


def keep_stacks(style: str) -> dict[str, Any]:
    """A style's keeps' stacks as drawn, by the id each keep's render names."""
    from fractal_wallpapers import styles

    path = styles.styles_dir() / f"{style}.keeps.json"
    return json.loads(path.read_text(encoding="utf-8"))["stacks"]


def published_rows() -> list[dict[str, Any]]:
    from fractal_wallpapers import style_catalog

    return [row for row in style_catalog.load()["modes"] if row.get("status") == "publish"]


def bundle() -> dict[str, Any]:
    """Every published mode as a page draws it, and every map they name.

    A mode is its public name and palette, its knobs (the style file's `public.knobs`
    whole: label, line, default, range, and where each writes), the stack, and the keeps
    the catalog shows, each with the location and map it was drawn at: the places a page
    can open the mode at, known to hold the look.
    """
    from fractal_wallpapers import style_catalog, styles

    modes, maps = [], {}
    for row in published_rows():
        document = styles.load(row["style"])
        keeps = style_catalog.keeps_of(row["style"])
        stacks = keep_stacks(row["style"])
        shown = []
        for item in row.get("show", []):
            render = keeps[item["keep"]]["render"]
            shown.append(
                {
                    "keep": item["keep"],
                    "caption": item["caption"],
                    "location": render["location"],
                    "colormap": render["colormap"],
                    # The stack the keep was drawn with, which an earlier round's keep
                    # may have drawn before the published stack settled: the keep's own
                    # picture is this, and the mode's `stack` at its location is close.
                    "stack": stacks[render["stack"]],
                }
            )
            maps.setdefault(render["colormap"], colormap_of(render["colormap"]))
        palette = row["public"]["palette"]
        maps.setdefault(palette, colormap_of(palette))
        modes.append(
            {
                "name": row["public"]["name"],
                "style": row["style"],
                "palette": palette,
                "variant": row["variant"],
                "what": row.get("what", document["description"]),
                "knobs": document["public"]["knobs"],
                "stack": document["style"],
                "shown": shown,
            }
        )
    return {
        "schema": BUNDLE_SCHEMA,
        "modes": modes,
        "colormaps": {name: maps[name] for name in sorted(maps)},
    }


def write_bundle(path: Path) -> dict[str, Any]:
    document = bundle()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, indent=1, ensure_ascii=False) + "\n")
    return document


def request(
    location: dict[str, Any],
    stack: dict[str, Any],
    colormap: dict[str, Any],
    resolution: tuple[int, int],
    supersample: int,
    knobs: list[dict[str, Any]] | None = None,
    settings: dict[str, float] | None = None,
) -> dict[str, Any]:
    """What the module's `open` reads: the CLI's inputs, not the engine's spec."""
    return {
        "schema": 1,
        "location": location,
        "style": stack,
        "knobs": knobs or [],
        "settings": settings or {},
        "colormap": colormap,
        "resolution": list(resolution),
        "supersample": supersample,
    }


def native_rgb(
    location: dict[str, Any],
    document: dict[str, Any],
    colormap: str,
    resolution: tuple[int, int],
    supersample: int,
    output: Path,
) -> tuple[bytes, dict[str, Any]]:
    """The native engine's picture of one record, through `style render`'s own spec."""
    from PIL import Image

    from fractal_wallpapers import engine, locations, styles

    row = locations.one_location(dict(location), "a keep's record", drawing=True)
    row["render"] = {
        **row["render"],
        "resolution": list(resolution),
        "supersample": supersample,
    }
    spec = styles.spec_of(row, document, output, colormap=colormap)
    report = engine.render_report(spec)
    with Image.open(output) as picture:
        return picture.convert("RGB").tobytes(), report


def run_node(jobs: list[dict[str, Any]], folder: Path) -> list[dict[str, Any]]:
    """Draw `jobs` under Node, one thread, below normal priority; their result rows."""
    from fractal_wallpapers import process_control

    module = wasm_path()
    if not module.is_file():
        raise StyleWasmError(f"no module at {module}; build it first:\n  {BUILD}")
    node = shutil.which("node")
    if node is None:
        raise StyleWasmError("the check runs the module under Node, and no `node` is on PATH")
    folder.mkdir(parents=True, exist_ok=True)
    results = folder / "results.jsonl"
    results.unlink(missing_ok=True)
    jobs_path = folder / "jobs.json"
    with jobs_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(jobs, handle, ensure_ascii=False)
    runner = crate_dir() / "js" / "node-render.mjs"
    subprocess.run(
        [node, str(runner), str(module), str(jobs_path), str(folder)],
        check=True,
        creationflags=process_control.child_priority_flags(),
    )
    return [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines()]


def compare(native: bytes, rgba: bytes) -> dict[str, Any]:
    """How far the module's RGBA is from the native RGB: pixels that differ, worst step."""
    if len(rgba) % 4 or len(rgba) // 4 * 3 != len(native):
        return {"identical": False, "pixels": None, "worst": None}
    rgb = bytearray(len(native))
    rgb[0::3], rgb[1::3], rgb[2::3] = rgba[0::4], rgba[1::4], rgba[2::4]
    differ, worst = 0, 0
    if bytes(rgb) != native:
        for i in range(0, len(native), 3):
            step = max(abs(native[i + k] - rgb[i + k]) for k in range(3))
            if step:
                differ += 1
                worst = max(worst, step)
    return {"identical": differ == 0, "pixels": differ, "worst": worst}


def midpoints(knobs: list[dict[str, Any]]) -> dict[str, float]:
    """Every knob at the middle of its range, in the order the style lists them."""
    return {knob["name"]: (knob["range"][0] + knob["range"][1]) / 2 for knob in knobs}


def parity(
    folder: Path,
    resolution: tuple[int, int] = PARITY_RESOLUTION,
    supersample: int = PARITY_SUPERSAMPLE,
) -> list[dict[str, Any]]:
    """Every shown keep of every published mode, drawn natively and as WebAssembly.

    Three kinds of job: each shown keep's own record (its stack as drawn, its map), in
    one pass; the first keep of each mode again in tiles against its own measures, which
    must be the same bytes; and the mode's published stack at that keep with every knob
    at its range's middle, which holds the module's knob rules to `styles.with_knobs`.
    """
    from fractal_wallpapers import style_catalog, styles

    jobs, natives = [], {}
    for row in published_rows():
        document = styles.load(row["style"])
        keeps = style_catalog.keeps_of(row["style"])
        stacks = keep_stacks(row["style"])
        for index, item in enumerate(row.get("show", [])):
            render = keeps[item["keep"]]["render"]
            stack = stacks[render["stack"]]
            ident = f"{row['style']}__{index}"
            drawn = {**document, "style": stack}
            natives[ident] = (render["location"], drawn, render["colormap"])
            colormap = colormap_of(render["colormap"])
            asked = request(render["location"], stack, colormap, resolution, supersample)
            jobs.append({"id": ident, "request": asked, "draw": "frame"})
            if index:
                continue
            jobs.append(
                {
                    "id": f"{ident}__tiles",
                    "request": asked,
                    "draw": {"measure": {}, "tile": list(PARITY_TILE)},
                    "same_as": ident,
                }
            )
            knobs = document["public"]["knobs"]
            settings = midpoints(knobs)
            turned = styles.with_knobs(document, settings)
            natives[f"{ident}__knobs"] = (
                render["location"],
                turned,
                row["public"]["palette"],
            )
            jobs.append(
                {
                    "id": f"{ident}__knobs",
                    "request": request(
                        render["location"],
                        document["style"],
                        colormap_of(row["public"]["palette"]),
                        resolution,
                        supersample,
                        knobs,
                        settings,
                    ),
                    "draw": "frame",
                }
            )
    rows = {result["id"]: result for result in run_node(jobs, folder)}
    out = []
    for job in jobs:
        ident = job["id"]
        result = rows[ident]
        base = job.get("same_as", ident)
        location, drawn, colormap = natives[base]
        native_png = folder / f"{base}.native.png"
        if not native_png.is_file() or "same_as" not in job:
            started = time.perf_counter()
            native, _ = native_rgb(location, drawn, colormap, resolution, supersample, native_png)
            native_seconds = time.perf_counter() - started
        else:
            from PIL import Image

            with Image.open(native_png) as picture:
                native = picture.convert("RGB").tobytes()
            native_seconds = None
        line = {"id": ident, "ok": result["ok"], "native_seconds": native_seconds}
        if result["ok"]:
            rgba = (folder / f"{ident}.rgba").read_bytes()
            line.update(compare(native, rgba))
            line["wasm_seconds"] = round(result.get("measure", 0.0) + result["draw"], 3)
        else:
            line["why"] = result["why"]
        out.append(line)
    with (folder / "parity.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for line in out:
            handle.write(json.dumps(line) + "\n")
    return out


def speed(folder: Path) -> list[dict[str, Any]]:
    """One 1280x800 frame per published mode, as WebAssembly on one thread.

    The published stack at the mode's first shown keep, with its matched map: what a
    page opening the mode draws first.
    """
    from fractal_wallpapers import style_catalog, styles

    jobs = []
    for row in published_rows():
        if not row.get("show"):
            continue
        document = styles.load(row["style"])
        first = row["show"][0]["keep"]
        location = style_catalog.keeps_of(row["style"])[first]["render"]["location"]
        jobs.append(
            {
                "id": row["style"],
                "request": request(
                    location,
                    document["style"],
                    colormap_of(row["public"]["palette"]),
                    SPEED_RESOLUTION,
                    SPEED_SUPERSAMPLE,
                ),
                "draw": "frame",
            }
        )
    results = run_node(jobs, folder)
    with (folder / "speed.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for line in results:
            handle.write(json.dumps(line) + "\n")
    return results
