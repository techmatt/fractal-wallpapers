"""The style compositor as WebAssembly: the bundle a page draws from, and its checks.

The module is `style-wasm/` (`style-wasm/README.md`'s *The style module*): the engine's own
`style::measure`, `style::tile` and `style::paint` (the whole frame in one pass) behind a
few raw exports, with the three rules
`style render` lays on a style file before the engine sees it. This side writes what a
page needs to draw a published mode without copying one by hand, the **bundle**, and
holds the module to the native engine:

```
fractal-wallpapers style bundle [--out <bundle.json>]
fractal-wallpapers style wasm-parity [names…] [--workers N]
                                     [--resolution 640 400 --supersample 2]
fractal-wallpapers style wasm-speed
```

`wasm-parity` draws every keep the catalog shows for a published mode both ways and
compares the bytes, and every style with a post stage or a stir the catalog does not
publish yet at `POST_SEAT` (a style named on the command line whatever its stack);
`wasm-speed` times one 1280x800 frame per published mode on one thread. Both run the
module under Node (`style-wasm/js/node-render.mjs`), and refuse without a built module,
naming the build.

**Which parity run is owed** is `style-wasm/README.md`'s *Parity: which run is owed*:
the full run after engine style-path or module code, `style wasm-parity <name>` after one
style's change, `--member <name>` ([`knob_writers`]) after a name-list edit.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from fractal_wallpapers import engine
from fractal_wallpapers.styles import DRAFT_RESOLUTION, DRAFT_SUPERSAMPLE

#: The bundle's shape. A page reads it and nothing else of this checkout.
BUNDLE_SCHEMA = 1

#: The parity check's default size: a quarter of a keep's 2560x1600 in each axis, at the
#: keep's own supersample. Every frame-wide statistic is measured at whatever size is
#: drawn, so a smaller frame runs the same code; it is the cheap size, not another path.
PARITY_RESOLUTION = (640, 400)
PARITY_SUPERSAMPLE = 2

#: The speed reading's frame: the draft size `style render --draft` checks at.
SPEED_RESOLUTION = DRAFT_RESOLUTION
SPEED_SUPERSAMPLE = DRAFT_SUPERSAMPLE

#: Node worker threads a parity run draws on, beside the native engine's renders, below
#: normal priority. The whole run is as long as the longest of three things: its longest
#: job (one keep's tiled draw), the module's work over the workers, and the native side
#: (at `PARITY_NATIVE_THREADS`). The whole run, 223 jobs, reads 38 to 48 minutes at
#: `--workers 3` (six threads with the native side), and is never shorter than its
#: longest job (`style-wasm/README.md`'s *Parity: which run is owed*). The render pool's
#: count, and its cap as `style cost`'s (Matt, 2026-11-25).
PARITY_WORKERS = engine.POOL_WORKERS

#: Threads the native engine takes for its side of a parity run (`RAYON_NUM_THREADS`,
#: unless the caller's environment already sets one): uncapped it takes every core beside
#: the Node workers, and at two it is the whole run's tail. Three is done in about two
#: thirds of the run (36 thread-minutes), and the workers have the box to themselves after.
PARITY_NATIVE_THREADS = 3

#: The tile the parity check's tiled draw cuts the picture into.
PARITY_TILE = (256, 256)

#: Where the parity check draws a style no published row shows yet (a round-one style has
#: no keep): in the whole run one with a post stage or a stir, and any style named on the
#: command line. A shallow seat with set, lace and far field, so a post pass draws its
#: large facets and its finest.
POST_SEAT = {
    "family": {"kind": "mandelbrot"},
    "viewport": {"center_re": "-0.7453", "center_im": "0.1127", "width": "0.012"},
    "maxiter": 2000,
}

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


def has_post(stack: dict[str, Any]) -> bool:
    """Whether a stack has a post stage: it is drawn whole, never in tiles."""
    return bool(stack.get("post"))


def has_stir(stack: dict[str, Any]) -> bool:
    """Whether a stack stirs its samples before they are iterated (`POST.md`'s *The stir*)."""
    return bool(stack.get("stir"))


def unpublished_post_or_stir_styles() -> list[str]:
    """Every style file with a post stage or a stir that no published row shows."""
    from fractal_wallpapers import styles

    published = {row["style"] for row in published_rows()}
    return [
        name
        for name in styles.names()
        if name not in published
        and (has_post(styles.load(name)["style"]) or has_stir(styles.load(name)["style"]))
    ]


def published_rows() -> list[dict[str, Any]]:
    from fractal_wallpapers import style_catalog

    return [row for row in style_catalog.load()["modes"] if row.get("status") == "publish"]


def knob_writers(members: list[str]) -> list[str]:
    """The published modes with a public knob writing a stack member named in `members`.

    A change to a name list both engines read when a knob writes (`styles.INTEGER_MEMBERS`)
    can move only a `__knobs` job, and only a mode whose knob writes a listed member: these
    are the styles `wasm-parity --member` draws, instead of the whole run.
    """
    from fractal_wallpapers import styles

    wanted, found = set(members), []
    for row in published_rows():
        knobs = (styles.load(row["style"]).get("public") or {}).get("knobs") or []
        pointers = [pointer for knob in knobs for pointer, _ in styles.knob_writes(knob, 0.0)]
        if any(pointer.rsplit("/", 1)[-1] in wanted for pointer in pointers):
            found.append(row["style"])
    return found


def bundle() -> dict[str, Any]:
    """Every published mode as a page draws it, and every map they name.

    A mode is its public name, its tier (`curated` or `lab`, which a page lists apart) and
    palette, its palette set (`palettes`: each kept map and the values tuned for it, which a
    page cycles, and `rests`, what a knob rests at on that entry where not its default,
    `style_palettes.knob_rest`), its knobs (the style file's `public.knobs` whole: label,
    line, default, range, and where each writes; a lab mode's may be empty), the stack,
    and the pictures the catalog shows, each with the location and map it was drawn at:
    the places a page can open the mode at, known to hold the look (a lab example's is a
    draft's).
    """
    from fractal_wallpapers import style_catalog, style_palettes, styles

    modes, maps = [], {}
    for row in published_rows():
        document = styles.load(row["style"])
        shown = []
        # A keep's stack is the one it was drawn with, which an earlier round's keep may
        # have drawn before the published stack settled: the keep's own picture is this,
        # and the mode's `stack` at its location is close. A lab example (no `keep`) is a
        # draft's location under the mode's own stack.
        for item in style_catalog.shown_of(row):
            shown.append({key: value for key, value in item.items() if key != "picture"})
            maps.setdefault(item["colormap"], colormap_of(item["colormap"]))
        palette = row["public"]["palette"]
        maps.setdefault(palette, colormap_of(palette))
        # The set a page cycles: each kept map with the values tuned for it, written over
        # `stack` at their pointers (`style_palettes`), the default first. The default is
        # the mode's own map, there whether or not a keep was drawn in it (a lab mode shows
        # an example), so the page can always switch back to it.
        palettes = []
        knobs = (document.get("public") or {}).get("knobs") or []
        for index, entry in enumerate(row["palettes"]):
            if index and not entry.get("keeps"):
                continue  # still in its first round: not a kept palette yet
            maps.setdefault(entry["colormap"], colormap_of(entry["colormap"]))
            # What each knob rests at on this entry, where not its `default`: the entry's
            # own setting, which the slider shows untouched and can always come back to.
            rests = style_palettes.knob_rests(document["style"], entry.get("values") or {}, knobs)
            palettes.append(
                {
                    "colormap": entry["colormap"],
                    # The old style this entry was before it merged into the mode: a
                    # page resolves a link naming that style to this entry.
                    **({"was": entry["was"]} if entry.get("was") else {}),
                    "values": entry.get("values") or {},
                    **({"rests": rests} if rests else {}),
                    **({"score": entry["score"]} if "score" in entry else {}),
                }
            )
        modes.append(
            {
                "name": row["public"]["name"],
                "style": row["style"],
                # `curated` is the website's *Custom* list, `lab` its *Custom (lab)*.
                "tier": row["tier"],
                "palette": palette,
                "palettes": palettes,
                # Old style names merged into this mode (`styles.alias_of`), each resolving
                # here: to its entry (`was`) or the default.
                "aliases": row.get("aliases") or [],
                "variant": row["variant"],
                "what": row.get("what", document["description"]),
                "knobs": knobs,
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
    knobs: dict[str, float] | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """The native engine's picture of one record, through `style render`'s own spec:
    `knobs` turned after the record's projection, as `style render --knob` turns them."""
    from PIL import Image

    from fractal_wallpapers import locations, styles

    row = locations.one_location(dict(location), "a keep's record", drawing=True)
    row["render"] = {
        **row["render"],
        "resolution": list(resolution),
        "supersample": supersample,
    }
    spec = styles.spec_of(row, document, output, colormap=colormap, knobs=knobs)
    report = engine.render_report(spec)
    with Image.open(output) as picture:
        return picture.convert("RGB").tobytes(), report


def start_node(jobs: list[dict[str, Any]], folder: Path, workers: int = 1) -> subprocess.Popen:
    """Start drawing `jobs` under Node on `workers` threads, below normal priority."""
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
    return subprocess.Popen(
        [node, str(runner), str(module), str(jobs_path), str(folder), str(workers)],
        creationflags=process_control.child_priority_flags(),
    )


def node_results(
    node: subprocess.Popen, jobs: list[dict[str, Any]], folder: Path
) -> list[dict[str, Any]]:
    """Wait for `start_node`'s process; its result rows in the jobs' order."""
    code = node.wait()
    if code:
        raise subprocess.CalledProcessError(code, node.args)
    text = (folder / "results.jsonl").read_text(encoding="utf-8")
    rows = {row["id"]: row for row in map(json.loads, text.splitlines())}
    lost = [job["id"] for job in jobs if job["id"] not in rows]
    if lost:
        raise StyleWasmError(f"Node ended without a result for {', '.join(lost)}")
    return [rows[job["id"]] for job in jobs]


def run_node(jobs: list[dict[str, Any]], folder: Path, workers: int = 1) -> list[dict[str, Any]]:
    """Draw `jobs` under Node on `workers` threads; their result rows in the jobs' order."""
    return node_results(start_node(jobs, folder, workers), jobs, folder)


#: Beside a folder's `parity.jsonl`: what each job last took as WebAssembly, by id, over
#: every run into the folder. A filtered run rewrites `parity.jsonl` with its own rows
#: alone, and the next whole run still needs every job's time to order by.
SECONDS_FILE = "seconds.json"


def read_seconds(folder: Path) -> dict[str, float]:
    """What each job last took in `folder`, by id; empty before its first run."""
    path = folder / SECONDS_FILE
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def write_seconds(folder: Path, rows: list[dict[str, Any]]) -> None:
    """Lay a run's times over the folder's, keeping those of jobs it did not draw."""
    seconds = read_seconds(folder)
    seconds.update({row["id"]: row["wasm_seconds"] for row in rows if "wasm_seconds" in row})
    with (folder / SECONDS_FILE).open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(seconds, indent=1, sort_keys=True) + "\n")


def longest_first(jobs: list[dict[str, Any]], folder: Path) -> list[dict[str, Any]]:
    """`jobs` ordered by what each last took in the folder, the unmeasured first.

    One keep can be a quarter of an hour on its thread: started last, it is the whole
    run's tail with the other workers idle.
    """
    seconds = read_seconds(folder)
    took = {job["id"]: seconds.get(job["id"]) for job in jobs}
    return sorted(jobs, key=lambda job: (took[job["id"]] is not None, -(took[job["id"]] or 0.0)))


def compare(native: bytes, rgba: bytes) -> dict[str, Any]:
    """How far the module's RGBA is from the native RGB: pixels that differ, worst step."""
    if len(rgba) % 4 or len(rgba) // 4 * 3 != len(native):
        why = f"size: the module drew {len(rgba) / 4:g} pixels, native {len(native) // 3}"
        return {"identical": False, "pixels": None, "worst": None, "why": why}
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


def parity_jobs(
    resolution: tuple[int, int] = PARITY_RESOLUTION,
    supersample: int = PARITY_SUPERSAMPLE,
    names: list[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, tuple]]:
    """[`parity`]'s jobs for the module and the native pictures they are held to.

    A function of the catalog and the style files alone, so the job list is read without
    Node or a built module. `natives` maps a job id to `(location, document, colormap,
    settings)`; a `__tiles` job names the frame it must equal in `same_as`.
    """
    from fractal_wallpapers import style_catalog, styles

    jobs, natives = [], {}
    rows_drawn = published_rows()
    unpublished = unpublished_post_or_stir_styles()
    if names:
        # A style asked for by name is drawn whether or not the whole run would draw it.
        known = {row["style"] for row in rows_drawn} | set(styles.names())
        unknown = sorted(set(names) - known)
        if unknown:
            raise StyleWasmError(
                f"nothing to draw for {', '.join(unknown)}: the check covers published modes "
                "and style files"
            )
        published = {row["style"] for row in rows_drawn}
        rows_drawn = [row for row in rows_drawn if row["style"] in names]
        unpublished = [name for name in styles.names() if name in names and name not in published]
    for row in rows_drawn:
        document = styles.load(row["style"])
        for index, render in enumerate(style_catalog.shown_of(row)):
            stack = render["stack"]
            ident = f"{row['style']}__{index}"
            drawn = {**document, "style": stack}
            natives[ident] = (render["location"], drawn, render["colormap"], None)
            colormap = colormap_of(render["colormap"])
            asked = request(render["location"], stack, colormap, resolution, supersample)
            jobs.append({"id": ident, "request": asked, "draw": "frame"})
            if index and not render["location"].get("projection"):
                continue
            if not index and not has_post(stack):
                jobs.append(
                    {
                        "id": f"{ident}__tiles",
                        "request": asked,
                        "draw": {"measure": {}, "tile": list(PARITY_TILE)},
                        "same_as": ident,
                    }
                )
            knobs = (document.get("public") or {}).get("knobs") or []
            settings = midpoints(knobs)
            natives[f"{ident}__knobs"] = (
                render["location"],
                document,
                row["public"]["palette"],
                settings,
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
    for name in unpublished:
        document = styles.load(name)
        posted = has_post(document["style"])
        stirred = has_stir(document["style"])
        ident = f"{name}__{'post' if posted else 'stir' if stirred else 'named'}"
        natives[ident] = (POST_SEAT, document, document["suggested_colormap"], None)
        asked = request(
            POST_SEAT,
            document["style"],
            colormap_of(document["suggested_colormap"]),
            resolution,
            supersample,
        )
        jobs.append({"id": ident, "request": asked, "draw": "frame"})
        if not posted:
            # Without a post stage a stack is a pure function of the sample, stirred or
            # not, so its tiles are the frame's bytes.
            jobs.append(
                {
                    "id": f"{ident}__tiles",
                    "request": asked,
                    "draw": {"measure": {}, "tile": list(PARITY_TILE)},
                    "same_as": ident,
                }
            )
    return jobs, natives


def within_pool(workers: int) -> None:
    """Refuse a Node worker count past the render pool's (`engine.POOL_WORKERS`)."""
    if not 1 <= workers <= PARITY_WORKERS:
        raise StyleWasmError(
            f"--workers {workers}: a parity run draws on 1 to {PARITY_WORKERS} Node threads "
            "(the render pool's count)"
        )


def parity(
    folder: Path,
    resolution: tuple[int, int] = PARITY_RESOLUTION,
    supersample: int = PARITY_SUPERSAMPLE,
    names: list[str] | None = None,
    workers: int = PARITY_WORKERS,
) -> list[dict[str, Any]]:
    """Every shown keep of every published mode, drawn natively and as WebAssembly.

    `names` keeps the check to those styles: a couple of minutes for the one an item
    touched. A named style no row publishes is drawn at `POST_SEAT` whatever its stack (a
    round-one style has no keep), so a new primitive is held to the module before its
    mode is published; a name that is no style is refused rather than passed as a clean
    run. The module's pictures are drawn on
    `workers` Node threads, the longest of the folder's last run first, while this
    process draws the native ones.

    Three kinds of job: each shown keep's own record (its stack as drawn, its map), in
    one pass; the first keep of each mode again in tiles against its own measures, which
    must be the same bytes (a stack with a post stage is drawn whole, so it has no tiled
    job); and the mode's published stack with every knob at its range's
    middle, at that keep and at every keep whose record carries its own projection, which
    holds the module's knob rules to `style render --knob`'s (a knob wins over a record).
    A style with a post stage or a stir that no row publishes yet is drawn at `POST_SEAT`:
    once whole, and one without a post stage again in tiles. [`parity_jobs`] lists them.
    """
    from fractal_wallpapers.engine import THREADS_ENV

    within_pool(workers)
    jobs, natives = parity_jobs(resolution, supersample, names)
    queued = longest_first(jobs, folder)
    node = start_node(queued, folder, workers)
    drawn_natively = {}
    capped = THREADS_ENV not in os.environ
    if capped:
        os.environ[THREADS_ENV] = str(PARITY_NATIVE_THREADS)
    try:
        for ident, (location, drawn, colormap, settings) in natives.items():
            if node.poll():
                # Node already failed (a stale module, a worker's error): not worth the
                # rest of the native pictures to find out.
                raise subprocess.CalledProcessError(node.returncode, node.args)
            started = time.perf_counter()
            native, _ = native_rgb(
                location,
                drawn,
                colormap,
                resolution,
                supersample,
                folder / f"{ident}.native.png",
                knobs=settings,
            )
            drawn_natively[ident] = (native, time.perf_counter() - started)
    except BaseException:
        node.kill()
        node.wait()
        raise
    finally:
        if capped:
            os.environ.pop(THREADS_ENV, None)
    rows = {result["id"]: result for result in node_results(node, queued, folder)}
    out = []
    for job in jobs:
        ident = job["id"]
        result = rows[ident]
        native, native_seconds = drawn_natively[job.get("same_as", ident)]
        if "same_as" in job:
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
    write_seconds(folder, out)
    return out


#: The recolour check's size: the page's switch is size-blind (the same measure code at
#: any size), so it is drawn small; every published mode's entries in about two minutes.
RECOLOUR_RESOLUTION = (96, 60)

#: The tile the recolour check cuts its pictures into: several per frame, so a seam shows.
RECOLOUR_TILE = (40, 25)


def recolour_jobs(
    names: list[str] | None = None,
    resolution: tuple[int, int] = RECOLOUR_RESOLUTION,
    supersample: int = PARITY_SUPERSAMPLE,
    document: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """[`recolour_check`]'s jobs: per published mode drawn in tiles, each kept palette
    entry after the default as the page switches to it (the default measured, recoloured
    to the entry, tiled) beside a plain frame of the entry, from the bundle as a page
    reads it (its stack, knobs, entry values, the first shown place); `document` is that
    bundle when the caller holds it already.

    A mode with a post stage is drawn whole, never recoloured, so it has no jobs.
    """
    from fractal_wallpapers import style_palettes

    document = document or bundle()
    modes = document["modes"]
    if names:
        unknown = sorted(set(names) - {mode["style"] for mode in modes})
        if unknown:
            raise StyleWasmError(f"no published mode {', '.join(unknown)} to recolour")
        modes = [mode for mode in modes if mode["style"] in names]
    jobs = []
    for mode in modes:
        if has_post(mode["stack"]) or not mode["shown"] or len(mode["palettes"]) < 2:
            continue
        location = mode["shown"][0]["location"]

        def asked(entry: dict[str, Any], mode=mode, location=location) -> dict[str, Any]:
            stack = style_palettes.apply(mode["stack"], entry["values"])
            colormap = document["colormaps"][entry["colormap"]]
            return request(location, stack, colormap, resolution, supersample, mode["knobs"])

        default = mode["palettes"][0]
        for index, entry in enumerate(mode["palettes"][1:], 1):
            ident = f"{mode['style']}__{index}_{entry['colormap']}"
            jobs.append({"id": f"{ident}__plain", "request": asked(entry), "draw": "frame"})
            jobs.append(
                {
                    "id": f"{ident}__recoloured",
                    "request": asked(entry),
                    "draw": {"measure": {}, "tile": list(RECOLOUR_TILE), "from": asked(default)},
                    "same_as": f"{ident}__plain",
                }
            )
    return jobs


def recolour_check(
    folder: Path,
    names: list[str] | None = None,
    workers: int = PARITY_WORKERS,
    resolution: tuple[int, int] = RECOLOUR_RESOLUTION,
    supersample: int = PARITY_SUPERSAMPLE,
) -> list[dict[str, Any]]:
    """The page's palette switch held to a plain draw, module against module: one row
    per switch, `identical`, or `refused` with the module's reason (an entry moving what
    the frame gathered, which the page meets by measuring afresh: slower, never wrong).
    Rows also in `recolour.jsonl`.
    """
    within_pool(workers)
    jobs = recolour_jobs(names, resolution, supersample)
    if not jobs:
        raise StyleWasmError("no published mode here has a second palette entry to recolour")
    folder.mkdir(parents=True, exist_ok=True)
    rows = {row["id"]: row for row in run_node(jobs, folder, workers)}
    out = []
    for job in jobs:
        if "same_as" not in job:
            continue
        ident = job["id"].removesuffix("__recoloured")
        plain, switched = rows[job["same_as"]], rows[job["id"]]
        line = {"id": ident, "ok": plain["ok"] and switched["ok"]}
        if not plain["ok"]:
            line["why"] = f"the plain frame failed: {plain['why']}"
        elif not switched["ok"]:
            line.update(
                refused=True, why=switched["why"], ok="measure it afresh" in switched["why"]
            )
        else:
            line["identical"] = (folder / f"{job['id']}.rgba").read_bytes() == (
                folder / f"{job['same_as']}.rgba"
            ).read_bytes()
            line["ok"] = line["identical"]
        out.append(line)
    with (folder / "recolour.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for line in out:
            handle.write(json.dumps(line) + "\n")
    return out


#: Matt's bar for one explorer frame (1280x800 ss2, one thread): about five minutes.
COST_BAR_SECONDS = 300

#: The most Node threads a cost read draws on: the render pool's three (CLAUDE.md).
COST_WORKERS = engine.POOL_WORKERS


def kept_seats(name: str) -> list[dict[str, Any]]:
    """A style's kept seats, deepest `maxiter` first: each keep's location once, by name
    and cap (a keep reopened at a lower cap is a seat of its own). Ties keep the keep
    record's order.

    A style with no keep record offers the catalog's shown locations instead (a lab
    example's draft seats).
    """
    from fractal_wallpapers import style_catalog, style_keeps

    locations = [keep["render"]["location"] for keep in style_keeps.read_record(name)["keeps"]]
    if not locations:
        rows = [row for row in style_catalog.load()["modes"] if row["style"] == name]
        locations = [shown["location"] for row in rows for shown in style_catalog.shown_of(row)]
    seats: dict[tuple, dict[str, Any]] = {}
    for location in locations:
        key = location.get("name") or json.dumps(location, sort_keys=True)
        seats.setdefault((key, location["maxiter"]), location)
    return sorted(seats.values(), key=lambda location: -location["maxiter"])


def cost_resolution(shrink: int = 1) -> tuple[int, int]:
    """The frame a cost read draws: the explorer's 1280x800, each side over `shrink`."""
    width, height = SPEED_RESOLUTION
    if shrink < 1 or width % shrink or height % shrink:
        raise StyleWasmError(f"--shrink {shrink}: it must divide {width}x{height} (1, 2, 4, 8, 16)")
    return width // shrink, height // shrink


def cost_jobs(
    names: list[str],
    seat: str | None = None,
    location: dict[str, Any] | None = None,
    shrink: int = 1,
) -> list[dict[str, Any]]:
    """[`cost`]'s jobs: each style's published stack and map at its deepest kept seat
    (or at `seat`, a kept seat's name, or at `location`, any location record: a round-one
    style has no kept seat), one 1280x800 ss2 frame each, or that frame over `shrink`."""
    from fractal_wallpapers import styles

    resolution = cost_resolution(shrink)
    published = {row["style"]: row for row in published_rows()}
    jobs = []
    for name in names:
        document = styles.load(name)
        # A merged style's old name reads as its mode at the entry that was it
        # (`styles.load`): the mode's seats, the entry's stack and map.
        seats = [location] if location is not None else kept_seats(document["name"])
        if seat is not None and location is None:
            seats = [kept for kept in seats if kept.get("name") == seat]
        if not seats:
            raise StyleWasmError(f"{name} has no kept seat" + (f" named {seat}" if seat else ""))
        row = published.get(name)
        palette = row["public"]["palette"] if row else document["suggested_colormap"]
        chosen = seats[0]
        jobs.append(
            {
                "id": f"{name}__{chosen.get('name', 'seat')}",
                "style": name,
                "seat": chosen.get("name"),
                "request": request(
                    chosen,
                    document["style"],
                    colormap_of(palette),
                    resolution,
                    SPEED_SUPERSAMPLE,
                ),
                "draw": "frame",
            }
        )
    return jobs


def cost(
    folder: Path,
    names: list[str],
    seat: str | None = None,
    workers: int = 1,
    location: dict[str, Any] | None = None,
    shrink: int = 1,
) -> list[dict[str, Any]]:
    """The explorer's cost of each style: one 1280x800 ss2 frame as WebAssembly on one
    thread, at its deepest kept seat, against [`COST_BAR_SECONDS`].

    Each job is one thread's work whatever `workers` is; a reading is a timing only on a
    quiet box with a core left for every worker. Rows go to `cost.jsonl` in `folder`.
    With `shrink` the frame is drawn at 1/shrink of each side and its time scaled by
    shrink² to the full frame (a row's `read_seconds` is what it took): the read for a
    mode already known to be over, whose whole frame would hold a worker for many minutes.
    """
    if not 1 <= workers <= COST_WORKERS:
        raise StyleWasmError(
            f"--workers {workers}: a cost read draws on 1 to {COST_WORKERS} threads "
            "(the render pool's count)"
        )
    jobs = cost_jobs(names, seat, location, shrink)
    results = run_node(jobs, folder, workers)
    out = []
    for job, result in zip(jobs, results, strict=True):
        line = {"style": job["style"], "seat": job["seat"], "ok": result["ok"]}
        if result["ok"]:
            read = round(result["open"] + result["draw"], 2)
            seconds = round(read * shrink * shrink, 2)
            line.update(maxiter=result["maxiter"], seconds=seconds, over=seconds > COST_BAR_SECONDS)
            if shrink > 1:
                line.update(shrink=shrink, read_seconds=read)
        else:
            line["why"] = result["why"]
        out.append(line)
    with (folder / "cost.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
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
        location = style_catalog.shown_of(row)[0]["location"]
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
