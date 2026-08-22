"""How a colormap in this repository came to exist, for the two kinds that were made.

The dense sRGB8 file under `data/palettes` is the render truth: it is what the
engine bakes and what every row naming a map resolves to. It says nothing about
where the map came from beyond a one-line `source`, and for two groups that is a
real loss.

* **Authored** maps were written as OKLCH control points against a stated brief —
  a mood, a value key, a complexity, a lightness skeleton, a colour architecture —
  and then densified. The brief is the interesting part and the dense file has
  none of it: by the time a map is 512 sRGB8 stops, "wine and slate on a pale
  bone field" is unrecoverable.
* **Extracted** maps were recovered from a picture somebody else made. There the
  only fact worth keeping is *which picture*, and the map's own name carries it —
  it is the image file's stem — so the record restores the extension and stops.

Everything else in the library — the matplotlib ramps, the maps a labeled corpus
named — has a `source` line that already says all there is to say, and carries no
row here. A map with no row is not a gap; it is a map nobody authored.

## The record is provenance and never a second gradient

An authored row carries its OKLCH stops because those are what the author wrote.
They are **not** an alternative to the dense file and nothing renders from them:
the densifier is the engine's own bake, and re-deriving a picture from these
control points here would be a second answer to "what colour is this map at
0.4". The dense file wins by construction, because it is the only one anything
reads.

## Matching is by name, and a miss is reported rather than guessed

The archive holds more authored maps than this repository ships, because the
shipped pool is a subset somebody chose. A name in the archive with no map here
is expected and counted; a map here that claims to be authored and has no archive
entry is a hole in the provenance and is counted too. Neither is closed by a
fuzzy match — two palettes one edit apart in name are two palettes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from fractal_wallpapers.paths import colormap_dir

#: The record every row in the provenance file carries, from the first row.
SCHEMA = 1

#: What the file is called, beside the maps it describes.
RECORD_NAME = "provenance.jsonl"

#: The two kinds of provenance a row can carry.
AUTHORED = "authored"
EXTRACTED = "extracted"

#: The archive's batch files, relative to the source project's root. One file per
#: run of the generator, holding the whole batch that run emitted.
BATCHES = Path("dramatic_palettes") / "results"

#: The source project's pooled library, which is what says whether a map was
#: authored, extracted, or neither.
POOL = Path("data") / "palettes" / "pool_colormaps.json"

#: The pool's own words for the two groups. Read here and nowhere else: they are
#: that project's vocabulary and they stop at this module's edge.
POOL_WORDS = {"dramatic": AUTHORED, "extracted": EXTRACTED}

#: `<mood family>_c<complexity band>_v<major>_<minor>` — the batch file name the
#: generator's own run conditioning produces. The mood family is a name off its
#: roster, or `span` for a run told to vary the mood across the batch.
BATCH_NAME = re.compile(r"^(?P<family>.+)_c(?P<band>[^_]+)_v(?P<major>\d+)_(?P<minor>\d+)$")

#: What counts as one of the pictures an extracted map was read from. A map's
#: name is its picture's stem, so the only thing left to recover is which file on
#: disk that stem belongs to — i.e. its extension.
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".bmp")


class ProvenanceError(RuntimeError):
    """The record cannot be built, and writing a partial one would be worse."""


def record_path(directory: Path | None = None) -> Path:
    """Where the provenance record lives: beside the maps it describes."""
    return (directory or colormap_dir()) / RECORD_NAME


def batch_conditioning(stem: str) -> dict:
    """The run knobs a batch file's own name records.

    The generator's run lines are the batch's identity — its file name is how they
    were written down — so a map's mood family and the generator version that
    emitted it are read off the file rather than off the map.
    """
    matched = BATCH_NAME.match(stem)
    if matched is None:
        raise ProvenanceError(
            f"{stem!r} is not a batch file name. The generator writes "
            f"`<mood family>_c<complexity band>_v<major>_<minor>.json`, and a file that "
            f"does not say which run made it cannot date the maps inside it."
        )
    return {
        "mood_family": matched["family"],
        "complexity_band": matched["band"],
        "generator": f"{matched['major']}.{matched['minor']}",
    }


def read_batches(root: Path) -> dict[str, dict]:
    """`{map name: authored row}` for every map the archive's batches hold.

    A name in two batches is refused rather than resolved: the name is the join
    key the dense file, the pool and this record all meet on, so two entries
    claiming it means one of the two briefs is about to be attached to the wrong
    gradient.
    """
    directory = Path(root) / BATCHES
    if not directory.is_dir():
        raise ProvenanceError(
            f"{directory} is missing. It is the archive of generator batches, and it is "
            f"the only place an authored map's brief still exists."
        )
    out: dict[str, dict] = {}
    for path in sorted(directory.glob("*.json")):
        conditioning = batch_conditioning(path.stem)
        for entry in json.loads(path.read_text(encoding="utf-8")):
            name = entry["name"]
            if name in out:
                raise ProvenanceError(
                    f"{name!r} is in two batches ({out[name]['batch']} and {path.name}). "
                    f"The name is the join key, so two briefs under it would attach one of "
                    f"them to the wrong gradient."
                )
            out[name] = {
                "schema": SCHEMA,
                "name": name,
                "source": AUTHORED,
                **conditioning,
                "batch": path.name,
                "mood": entry["mood"],
                "architecture": entry["architecture"],
                "skeleton": entry["skeleton"],
                "value_key": entry["value_key"],
                "complexity": int(entry["complexity"]),
                "stops": [_stop(stop) for stop in entry["stops"]],
            }
    return out


def _stop(stop: dict) -> dict:
    """One authored control point, with its optional keys kept only when present.

    `segment` says a stop opens a cliff rather than a smooth ramp and `keypoint`
    names one the author called out; both are absent on most stops, and writing
    them as nulls would make an ordinary stop look like a decision.
    """
    lightness, chroma, hue = stop["oklch"]
    out = {
        "pos": float(stop["pos"]),
        "oklch": [float(lightness), float(chroma), float(hue)],
        "role": stop["role"],
    }
    for key in ("segment", "keypoint"):
        if stop.get(key) is not None:
            out[key] = stop[key]
    return out


def read_pool(root: Path) -> dict[str, str]:
    """`{map name: this module's source word}` for the pool's two made groups.

    The pool is what knows which group a map is in; the dense file here does not
    carry it. Names outside the two groups are dropped, which is what makes "no
    row" mean "nobody made this map, it was converted".
    """
    path = Path(root) / POOL
    if not path.is_file():
        raise ProvenanceError(
            f"{path} is missing. It is the source project's pooled library, and it is what "
            f"says whether a map was authored or extracted."
        )
    entries = json.loads(path.read_text(encoding="utf-8"))
    return {
        entry["name"]: POOL_WORDS[entry["source"]]
        for entry in entries
        if entry.get("source") in POOL_WORDS
    }


def image_names(directory: Path | None) -> dict[str, str]:
    """`{stem: file name}` for the pictures the extracted maps were read from.

    An extracted map's name *is* its picture's stem, so the directory is only
    consulted to put the extension back. Absent, every extracted row records the
    stem it carries and says the extension was not recovered — which is a smaller
    fact than guessing `.jpg` three hundred times.
    """
    if directory is None:
        return {}
    directory = Path(directory)
    if not directory.is_dir():
        raise ProvenanceError(f"{directory} is not a directory of images")
    return {
        path.stem: path.name
        for path in sorted(directory.iterdir())
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    }


def rows(root: Path, images: Path | None = None, directory: Path | None = None) -> tuple:
    """`(rows, report)` — the provenance of every made map this repository ships.

    Sorted by name, which is the order the file is written in and the order a
    diff of it reads in.
    """
    directory = Path(directory) if directory is not None else colormap_dir()
    held = sorted(path.stem for path in directory.glob("*.json"))
    pool = read_pool(root)
    briefs = read_batches(root)
    pictures = image_names(images)

    out: list[dict] = []
    unmatched: list[str] = []
    without_image: list[str] = []
    for name in held:
        source = pool.get(name)
        if source == AUTHORED:
            brief = briefs.get(name)
            if brief is None:
                unmatched.append(name)
                continue
            out.append(brief)
        elif source == EXTRACTED:
            picture = pictures.get(name)
            if picture is None:
                without_image.append(name)
            out.append(
                {
                    "schema": SCHEMA,
                    "name": name,
                    "source": EXTRACTED,
                    "image": picture or name,
                    "image_suffix_recovered": picture is not None,
                }
            )
    written = {row["name"] for row in out}
    return out, {
        "maps": len(held),
        "authored": sum(1 for row in out if row["source"] == AUTHORED),
        "extracted": sum(1 for row in out if row["source"] == EXTRACTED),
        "authored_without_brief": unmatched,
        "extracted_without_image": without_image,
        "briefs_unused": sorted(set(briefs) - written),
        "no_provenance": sorted(name for name in held if name not in pool),
    }


def text_of(records: list[dict]) -> str:
    """The record file, one row to a line, in the shape every JSONL here has."""
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records)


def write(records: list[dict], directory: Path | None = None) -> Path:
    """Write the provenance record beside the maps it describes."""
    path = record_path(directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text_of(records), encoding="utf-8", newline="\n")
    return path


def read(directory: Path | None = None) -> dict[str, dict]:
    """`{map name: row}` — the tracked record, for a reader that wants one map's."""
    path = record_path(directory)
    if not path.is_file():
        return {}
    return {
        row["name"]: row
        for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())
    }


def run(root: Path, images: Path | None = None, directory: Path | None = None) -> dict:
    """Rebuild the provenance record from the archive, and say what it matched."""
    records, report = rows(root, images, directory)
    report["path"] = str(write(records, directory))
    return report


__all__ = [
    "AUTHORED",
    "BATCHES",
    "EXTRACTED",
    "IMAGE_SUFFIXES",
    "POOL",
    "POOL_WORDS",
    "RECORD_NAME",
    "SCHEMA",
    "ProvenanceError",
    "batch_conditioning",
    "image_names",
    "read",
    "read_batches",
    "read_pool",
    "record_path",
    "rows",
    "run",
    "text_of",
    "write",
]
