"""The real candidate sets, vendored: what the deployed head was actually asked.

A palette head is used exactly once per picture, and always the same way: a
location arrives, a set of candidate maps is put in front of the head, and the
one it scores highest is the one the picture is coloured with. So the only
honest question to ask a distilled student is **would it have chosen the same
palette**, on the sets a production run really put in front of the teacher.

Those sets exist. The source project's last colorize-path batch recorded, for
each of 180 locations, the palette flavour the deficit model assigned it and the
map its own head then picked out of that flavour. This module reconstructs the
set the head chose from, checks the reconstruction against all 180 recorded
decisions, and writes it here as data — so the acceptance read is repeatable
without the other repository, exactly as the finished-render yardsticks are.

## What "the candidate set" is, and how it is rebuilt

Three facts from the source, each read from the file that owns it:

* the **pool** — `data/palettes/pool_colormaps.json`, every map a release run may
  colour with, in library order;
* the **flavour** of each pool map — `data/palettes/palette_categories.json` put
  through the source's own `cell_label`, which is imported rather than restated
  because it is the authority on what a flavour is;
* the **flavour a location was assigned**, recorded on each row of the batch.

The set is then that flavour's pool members, in library order, capped at
[`CAP`]. The cap is the one part of the rule that is restated rather than
imported — it lives in the source's release driver, which is a large module with
a large import cost — so it is *checked* instead of trusted: every one of the 180
recorded winners must fall inside the reconstructed set, and the extraction
refuses to write anything if a single one does not. A cap that was wrong, or an
ordering that was, would put a recorded winner outside its own candidate set.

## These locations are held out, and the maps they name are brought across

None of the 180 may appear in the distillation corpus. They are the instrument:
the whole point of them is that they were never taught, so the agreement read on
them is a reading and not a memory.

Their sets name 576 maps, and 243 of those were not tracked here. A candidate
set naming a map nobody holds is a decision nobody can reproduce, so they arrive
by the same mechanical conversion the finished-render corpora's maps did, and
their `source` line says exactly why they are present.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from fractal_wallpapers.labeling import finished
from fractal_wallpapers.palettes import library_import
from fractal_wallpapers.paths import colormap_dir, repo_root
from fractal_wallpapers.supply.location import location_key
from fractal_wallpapers.supply.partitions import partition_of_family

#: The schema every record this module writes carries.
SCHEMA = 1

#: How many maps of a flavour reach the head. The source's release driver caps
#: the set so one colorize stays cheap; a flavour can hold ninety members and
#: thirty-two is ample to pick a good one from. Restated here rather than
#: imported, and therefore checked — see the module docstring.
CAP = 32

#: The source batch the real decisions come from: its last colorize-path sheet,
#: one render per location, coloured the way a release run colours it.
SOURCE_BATCH = "2026-08-05_wallpaper_colorize_path_v1"

#: Where that batch lives under the source root.
BATCH = Path("data") / "wallpaper_corpus" / "batches"

#: The source's pooled colormap library and its flavour table.
POOL = Path("data") / "palettes" / "pool_colormaps.json"
CATEGORIES = Path("data") / "palettes" / "palette_categories.json"

#: The module that owns what a flavour tag is, imported rather than restated.
CELL_LABEL = Path("tools") / "curation" / "colored_clip_spread.py"

#: The geometry a candidate is rendered at here. Not the sheet's 1280×720: the
#: head reads a 224×224 squash of it, and 640×360 is both the size the source's
#: own colorize descriptor was formed at and the size this repository's tiles are
#: drawn at. The iteration cap travels, because it is a property of how deep the
#: location is rather than of how big the picture is.
RESOLUTION = [640, 360]
SUPERSAMPLE = 2

#: The coloring a candidate is rendered through: the canonical inherited recipe
#: the production colorize path uses and nothing else — the plain smooth field,
#: read straight, gradient spent once from its start, no reversal, no gamma.
#: Folding is not on this list because it is not a property of the render: a map
#: that does not close on the colour it opened with is folded to hide its seam,
#: and that is read off the map, here as everywhere else in this repository.
MODE = "smooth"
CURVE = "linear"


class SetsError(RuntimeError):
    """The candidate sets cannot be rebuilt, and guessing at them would be worse."""


def store_dir() -> Path:
    """Where this head's tracked records live. Not `data/palettes`, which is maps."""
    return repo_root() / "data" / "palette_choice"


def sets_path() -> Path:
    return store_dir() / "candidate_sets.jsonl"


def pool_path() -> Path:
    return store_dir() / "pool.json"


def _cell_label(root: Path):
    """The source's own flavour-tag function, loaded by path."""
    path = Path(root) / CELL_LABEL
    if not path.is_file():
        raise SetsError(f"{path} is missing — it is what a palette flavour means")
    name = "fractal_wallpapers._source_cell_label"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SetsError(f"{path} could not be loaded as a module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module.cell_label, module.DEFAULT_CELL_LEVEL


def _flavours(root: Path) -> tuple[dict[str, str], list[str]]:
    """`{map: flavour}` over the source pool, and the pool in library order."""
    pool_file = Path(root) / POOL
    categories_file = Path(root) / CATEGORIES
    for path in (pool_file, categories_file):
        if not path.is_file():
            raise SetsError(f"{path} is missing — the candidate sets resolve against it")
    order = [entry["name"] for entry in json.loads(pool_file.read_text(encoding="utf-8"))]
    table = json.loads(categories_file.read_text(encoding="utf-8"))["palettes"]
    label, level = _cell_label(root)
    flavours = {}
    for name, entry in table.items():
        clusters = entry.get("cluster") or {}
        flavours[name] = label(
            {
                "special": entry.get("special"),
                "k8": clusters.get("8"),
                "k12": clusters.get("12"),
                "k16": clusters.get("16"),
                "leaf_pos": entry.get("leaf_pos"),
            },
            level,
        )
    return flavours, order


def members_of(flavour: str, flavours: dict[str, str], order: list[str]) -> list[str]:
    """One flavour's candidate set: its pool members in library order, capped."""
    return [name for name in order if flavours.get(name) == flavour][:CAP]


def _rows_of(root: Path) -> list[dict]:
    path = Path(root) / BATCH / SOURCE_BATCH / "images.jsonl"
    if not path.is_file():
        raise SetsError(
            f"{path} is missing. It is the source project's colorize-path sheet, and its "
            f"rows are the only record of what a production run really asked the head."
        )
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def extract(root: Path) -> list[dict]:
    """Every real candidate set the source recorded, as rows for this store."""
    from fractal_wallpapers.labeling import finished_import

    flavours, order = _flavours(root)
    out, missed = [], []
    for index, source_row in enumerate(_rows_of(root)):
        render = source_row["render"]
        colorize = (source_row.get("provenance") or {}).get("colorize") or {}
        flavour = colorize.get("palette_flavor")
        if not flavour:
            raise SetsError(f"{source_row.get('image_id')!r} records no palette flavour")
        candidates = members_of(flavour, flavours, order)
        chosen = render["palette"]
        if chosen not in candidates:
            missed.append((source_row.get("image_id"), flavour, chosen, len(candidates)))
            continue
        family = finished_import.family_of(render, source_row.get("provenance") or {})
        out.append(
            {
                "schema": SCHEMA,
                "set": f"{index:04d}",
                "source_batch": SOURCE_BATCH,
                "source_id": source_row.get("image_id"),
                "family": family,
                "partition": partition_of_family(family),
                "viewport": {
                    "center_re": str(render["cx"]),
                    "center_im": str(render["cy"]),
                    "width": str(render["fw"]),
                },
                "render": {
                    "resolution": list(RESOLUTION),
                    "supersample": SUPERSAMPLE,
                    "maxiter": int(render["maxiter"]),
                },
                "mode": MODE,
                "curve": CURVE,
                "flavour": flavour,
                "candidates": candidates,
                "chosen": chosen,
                # The score the deployed head gave its own pick, under the source's
                # key for it. Carried as a fact about that run, not as a yardstick:
                # it was measured on the source's own picture of this location and
                # this repository's picture of it is a different picture.
                "chosen_score": colorize.get("pref_fit"),
            }
        )
    if missed:
        raise SetsError(
            f"{len(missed)} of the source's recorded decisions name a map that is not in the "
            f"candidate set rebuilt for them, e.g. {missed[:3]}. The set is rebuilt from the "
            f"pool, the flavour table and a cap of {CAP}; a recorded winner outside its own "
            f"set means one of those three is wrong, and every number read on these sets "
            f"afterwards would be about a question nobody asked."
        )
    return out


def cyclic() -> set[str]:
    """Which tracked maps close on the colour they opened with."""
    names = {path.stem for path in colormap_dir().glob("*.json")}
    out = set()
    for name in names:
        document = json.loads((colormap_dir() / f"{name}.json").read_text(encoding="utf-8"))
        if document.get("kind") == "cyclic":
            out.add(name)
    return out


def recipe_for(colormap: str, cyclic_maps: set[str]) -> dict:
    """The canonical colorize recipe for one map.

    Every knob is the identity except folding, which is not a knob at all: a
    sequential map is folded to hide the seam its two ends would otherwise show,
    and a cyclic one is not. Read off the map, never off a row — the same rule
    the finished-render import applies, so a picture means one thing here.
    """
    return finished.recipe(mirror=colormap not in cyclic_maps)


def candidate_row(set_row: dict, colormap: str, cyclic_maps: set[str]) -> dict:
    """One candidate of one set, in the shape the render cache reads.

    The set says where and how deep; the map says how it is folded; everything
    else is canonical. This is the one place a candidate becomes a picture, and
    both the distillation corpus and the acceptance sets go through it.
    """
    return {
        "family": set_row["family"],
        "viewport": set_row["viewport"],
        "mode": set_row.get("mode", MODE),
        "mode_params": {},
        "curve": set_row.get("curve", CURVE),
        "colormap": colormap,
        "recipe": recipe_for(colormap, cyclic_maps),
        "render": set_row["render"],
    }


def write(rows: list[dict], pool: dict) -> tuple[Path, Path]:
    """Ship the vendored sets and the pool they were drawn from."""
    store_dir().mkdir(parents=True, exist_ok=True)
    with sets_path().open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    pool_path().write_text(json.dumps(pool, indent=2) + "\n", encoding="utf-8", newline="\n")
    return sets_path(), pool_path()


def read() -> list[dict]:
    """The vendored candidate sets, schema-checked."""
    path = sets_path()
    if not path.is_file():
        raise SetsError(f"{path} is missing — extract the production candidate sets first")
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema") != SCHEMA:
            raise SetsError(f"{path}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}")
        rows.append(row)
    return rows


def pool() -> dict:
    """The shipped palette pool: the maps a colorize may choose between."""
    path = pool_path()
    if not path.is_file():
        raise SetsError(f"{path} is missing — extract the pool from the source library first")
    return json.loads(path.read_text(encoding="utf-8"))


def places() -> set[tuple]:
    """Every location the vendored sets hold — what the corpus draw must avoid."""
    return {location_key(row["family"], row["viewport"]) for row in read()}


def run(root: Path) -> dict:
    """Extract the sets, bring the maps they name across, and write both files."""
    root = Path(root)
    rows = extract(root)
    named = sorted({name for row in rows for name in row["candidates"]})
    brought = library_import.run(root, named)

    _, order = _flavours(root)
    held = {path.stem for path in colormap_dir().glob("*.json")}
    members = [name for name in order if name in held]
    document = {
        "schema": SCHEMA,
        "rule": (
            "the maps a colorize-time candidate set may hold: the source project's production "
            "pool, as this repository holds it. A map is here because a tracked corpus row or "
            "a vendored candidate set names it — nothing was brought across to round the "
            "number up, so this is a subset of that pool rather than a copy of it."
        ),
        "pool": members,
        "of_source_pool": len(order),
        "source": str(Path(root) / POOL),
    }
    write(rows, document)
    return {
        "sets": len(rows),
        "locations": len({location_key(row["family"], row["viewport"]) for row in rows}),
        "candidates": sum(len(row["candidates"]) for row in rows),
        "set_sizes": sorted({len(row["candidates"]) for row in rows}),
        "flavours": len({row["flavour"] for row in rows}),
        "distinct_maps": len(named),
        "colormaps": brought,
        "pool": {"members_here": len(members), "in_the_source_pool": len(order)},
        "wrote": [str(sets_path()), str(pool_path())],
    }


__all__ = [
    "BATCH",
    "CAP",
    "CATEGORIES",
    "CELL_LABEL",
    "CURVE",
    "MODE",
    "POOL",
    "RESOLUTION",
    "SCHEMA",
    "SOURCE_BATCH",
    "SUPERSAMPLE",
    "SetsError",
    "candidate_row",
    "cyclic",
    "extract",
    "members_of",
    "places",
    "pool",
    "pool_path",
    "read",
    "recipe_for",
    "run",
    "sets_path",
    "store_dir",
    "write",
]
