"""The band: what a finished wallpaper's tone looks like when it is already good.

The autolevel operator moves a render's tone toward an acceptable set. This
module is that set, and it is a *measurement* rather than a taste: three
statistics read off a folder of wallpapers Matt already keeps, and the middle
eighty percent of each one's spread taken as the band.

```text
black point   P0.5 of Oklab L over the NEUTRAL pixels
white point   P99.5 of Oklab L, every pixel
midtone       median Oklab L over the structure mask (L > MASK_L)
```

**The band is a percentile across images, not across pixels.** [`BAND`] is
`[P10, P90]` over the reference set, which keeps the middle eighty percent of a
population already judged good. The two alternatives are in the record beside it
and neither was taken: the inter-quartile range calls one reference image in four
out of range, and the full min–max is one image's opinion at each edge.

**Nothing derives it but this module, and it derives nothing else.** The record
ships as tracked data and [`autolevel`] only ever reads it. A re-derivation that
moves an edge is a new band, which is a new decision about what the operator does
to every render — so it is a deliberate command with a `--write`, and the record
carries the date, the image count and the per-image measurements that produced
it.

**The reference set lives outside this repository and is only ever read.** It is
a folder of finished wallpapers, named on the command line; what is tracked is
the measurement, the file names it was taken over, and a digest of the set. A
tracked record that named someone's home directory would be a record about one
machine.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from fractal_wallpapers.paths import repo_root

#: The schema the record carries.
SCHEMA = 1

#: The percentiles across images that become each statistic's band.
BAND = (10.0, 90.0)

#: Pictures the deriver will read. A reference set is a folder of finished
#: wallpapers, whatever they were saved as.
SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


class BandError(RuntimeError):
    """The band cannot be derived, or cannot be read."""


def record_path() -> Path:
    """Where the derived band lives, tracked."""
    return repo_root() / "data" / "coloring" / "levels_band.json"


def images_of(folder: Path) -> list[Path]:
    """The reference set's pictures, in name order."""
    folder = Path(folder)
    if not folder.is_dir():
        raise BandError(f"{folder} is not a directory, so there is no reference set to measure")
    found = sorted(p for p in folder.iterdir() if p.suffix.lower() in SUFFIXES)
    if not found:
        raise BandError(
            f"{folder} holds no picture this can read ({', '.join(SUFFIXES)}). A band derived "
            f"from nothing would be a band nobody measured."
        )
    return found


def set_digest(paths: list[Path]) -> str:
    """A digest of the reference set: every file's name and its own sha256.

    Names alone would not notice an edited image and bytes alone would not notice
    a renamed one, and the record has to be able to say that a re-derivation was
    over the same set.
    """
    outer = hashlib.sha256()
    for path in paths:
        inner = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                inner.update(chunk)
        outer.update(path.name.encode("utf-8"))
        outer.update(inner.digest())
    return outer.hexdigest()


def measure(path: Path) -> dict:
    """One reference picture's three statistics, through the operator's own reader."""
    import numpy
    from PIL import Image

    from fractal_wallpapers.coloring import autolevel

    with Image.open(path) as opened:
        array = numpy.asarray(opened.convert("RGB"), dtype=numpy.uint8)
    return autolevel.tone_stats(array)


def derive(folder: Path, band: tuple[float, float] = BAND, on=None) -> dict:
    """Measure the reference set and return the record it ships as.

    A statistic no image could be measured on gets **no band at all** rather than
    a defaulted one — see [`autolevel.derive_curve`], which leaves that end of the
    curve alone when the band is absent. The black point is the one this can
    happen to: its own chroma guard declines to read it on a picture whose dark
    tail is coloured rather than neutral.
    """
    import numpy

    from fractal_wallpapers.coloring import autolevel

    paths = images_of(folder)
    per_image, unmeasurable = [], []
    for path in paths:
        statistics = measure(path)
        per_image.append({"image": path.name, **{k: statistics[k] for k in autolevel.STATISTICS}})
        if statistics.get("black_unmeasurable"):
            unmeasurable.append({"image": path.name, "why": statistics["black_unmeasurable"]})
        if on is not None:
            on(f"{path.name}: {len(per_image)}/{len(paths)}")

    bands = {}
    for name in autolevel.STATISTICS:
        values = [row[name] for row in per_image if row[name] is not None]
        if not values:
            continue
        array = numpy.asarray(values, dtype=numpy.float64)
        bands[name] = {
            "n": len(values),
            "band": [float(numpy.percentile(array, edge)) for edge in band],
            "median": float(numpy.median(array)),
            "iqr": [float(numpy.percentile(array, 25.0)), float(numpy.percentile(array, 75.0))],
            "minmax": [float(array.min()), float(array.max())],
        }
    if not bands:
        raise BandError("no statistic could be measured on any reference image")

    return {
        "schema": SCHEMA,
        "what": (
            "The tone band the autolevel operator projects a render onto, read off a reference "
            "set of finished wallpapers. A render whose three statistics all sit inside these "
            "bands is left EXACTLY untouched."
        ),
        "source": f"{Path(folder).name}, read only, {len(paths)} pictures",
        "source_digest": set_digest(paths),
        "n_images": len(paths),
        "band_percentiles": list(band),
        "band_choice": (
            f"[P{band[0]:g}, P{band[1]:g}] across images keeps the middle "
            f"{band[1] - band[0]:g}% of a set already judged good. The inter-quartile range "
            f"beside it calls one reference image in four out of range; the min-max is one "
            f"image's opinion at each edge. Stated, not derived — the sensitivity is in this "
            f"record."
        ),
        "definitions": autolevel.DEFINITIONS,
        "measured_by": "coloring.autolevel.tone_stats — the operator's own measurement",
        "derived": date.today().isoformat(),
        "bands": bands,
        "black_unmeasurable": unmeasurable,
        "per_image": per_image,
    }


def write(record: dict) -> Path:
    path = record_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def load(path: Path | None = None) -> dict:
    """The shipped band, schema-checked, with its own sha256 on it.

    The digest rides along because every stamp the operator writes names the band
    it projected onto, and a stamp that named a file rather than its contents
    could not say whether the band had moved since.
    """
    path = record_path() if path is None else Path(path)
    if not path.is_file():
        raise BandError(
            f"{path} is missing. It is the tracked tone band the autolevel operator projects "
            f"onto; derive it with `fractal-wallpapers coloring derive-band --from <folder>`."
        )
    raw = path.read_bytes()
    record = json.loads(raw.decode("utf-8"))
    if record.get("schema") != SCHEMA:
        raise BandError(f"{path}: schema {record.get('schema')!r}, expected {SCHEMA}")
    record["_sha256"] = hashlib.sha256(raw).hexdigest()
    record["_path"] = path.name
    return record


def bands(record: dict) -> dict:
    """`{statistic: (lo, hi)}` from a loaded record.

    A statistic with no band is **absent** rather than defaulted, and the curve
    leaves that end of the tone range alone — the same refusal the chroma guard
    makes one level down.
    """
    from fractal_wallpapers.coloring import autolevel

    table = record.get("bands") or {}
    return {
        name: (float(table[name]["band"][0]), float(table[name]["band"][1]))
        for name in autolevel.STATISTICS
        if table.get(name)
    }


__all__ = [
    "BAND",
    "SCHEMA",
    "SUFFIXES",
    "BandError",
    "bands",
    "derive",
    "images_of",
    "load",
    "measure",
    "record_path",
    "set_digest",
    "write",
]
