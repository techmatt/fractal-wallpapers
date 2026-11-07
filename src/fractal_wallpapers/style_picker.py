"""Style pickers: the manifest Matt picks from, and the record of what each tile was drawn from.

`style render` writes a **render log** beside the pictures it draws, `renders.jsonl` in
the output folder, one row per picture:

    {"picture": "<file name>", "location": {<location record>}, "style": "<name>",
     "colormap": "<map>", "resolution": [w, h], "supersample": n, "stack": {<as drawn>}}

`style picker <plan.json>` turns pictures into a picker: it converts each to a JPEG under
the picker's folder, writes the manifest (every row `"kind": "many"`, `"default": []`, so
Matt selects the few he likes) and writes the **renders sidecar** `style keep` reads, by
looking each picture up in the render log beside it. A picture with no log row is
refused rather than shown, because a tile nobody can draw again is a keep that cannot
be saved. The plan is

    {"name": "style_<name>_r<N>", "title": "...", "intro": "...",
     "rows": [{"id": "...", "label": "...", "note": "...",
               "options": [{"picture": "<path>", "key": "...", "label": "..."}]}]}

`key` defaults to the picture's stem and must be unique across the whole picker (the
sidecar is keyed by it alone); `label` and `note` are optional. An option whose picture
was drawn by something other than `style render` (a named-mode baseline) carries its own
`"render": {"location", "mode", "colormap", "resolution", "supersample"}` in place of a
log row.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: The render log's name, beside the pictures it describes.
LOG_NAME = "renders.jsonl"

#: JPEG quality for a picker tile: what every style picker so far was built at.
QUALITY = 92


class PickerError(ValueError):
    """A plan that cannot become a picker."""


def log_row(
    picture: Path,
    location: dict[str, Any],
    style: str,
    colormap: str,
    resolution: list[int],
    supersample: int,
    stack: dict[str, Any],
) -> dict[str, Any]:
    """One render log row; the location is the record as written, less what drew it.

    Its cap stays, lifted out of the render when that is where the record kept it, so
    a redraw iterates exactly as the picture did.
    """
    place = {key: value for key, value in location.items() if key != "render"}
    cap = (location.get("render") or {}).get("maxiter")
    if "maxiter" not in place and cap is not None:
        place["maxiter"] = cap
    return {
        "picture": picture.name,
        "location": place,
        "style": style,
        "colormap": colormap,
        "resolution": list(resolution),
        "supersample": int(supersample),
        "stack": stack,
    }


def records_as_written(path: Path) -> list[dict[str, Any]]:
    """The location records in a file exactly as written: one JSON object, a JSON array
    of them (as `locations.read_one` takes), or JSONL.

    What a render log keeps, because a record read for drawing has its cap folded into
    the render and its `name`, `note` and provenance dropped, and a redraw from that
    would pick its own cap.
    """
    text = Path(path).read_text(encoding="utf-8")
    try:
        whole = json.loads(text)
    except json.JSONDecodeError:
        rows = []
        for number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"line {number} is a {type(row).__name__}, not a record") from None
            rows.append(row)
        return rows
    if isinstance(whole, list):
        return [row for row in whole if isinstance(row, dict)]
    return [whole] if isinstance(whole, dict) else []


def read_log(directory: Path) -> dict[str, dict[str, Any]]:
    """A folder's render log, by picture file name (empty when there is none)."""
    path = directory / LOG_NAME
    if not path.is_file():
        return {}
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            rows[row["picture"]] = row
    return rows


def append_log(rows: list[dict[str, Any]], directory: Path) -> Path:
    """Lay rows into a folder's render log: a picture drawn again replaces its row."""
    from fractal_wallpapers.paths import writing_path

    held = read_log(directory)
    for row in rows:
        held[row["picture"]] = row
    path = directory / LOG_NAME
    # Built beside and swapped in: the whole log is rewritten after every picture, and a
    # run killed mid-write would otherwise leave every picture in the folder unrecorded.
    scratch = writing_path(path)
    with scratch.open("w", encoding="utf-8", newline="\n") as handle:
        for name in sorted(held):
            handle.write(json.dumps(held[name], ensure_ascii=False) + "\n")
    scratch.replace(path)
    return path


def build(plan: dict[str, Any], folder: Path, base: Path, resolve=None) -> dict[str, Any]:
    """Write the picker for `plan` into `folder`.

    A relative picture path resolves through `resolve` when given (the CLI passes its
    tier-aware `resolve_input`, so `artifacts/...` finds the hot root), else against
    `base`.

    Returns `{manifest, renders, rows, options}`.
    """
    from PIL import Image

    name = plan.get("name") or ""
    if not name or not all(ch.islower() or ch.isdigit() or ch in "_-" for ch in name):
        raise PickerError(f"a picker name is a lowercase slug, got {name!r}")
    if not plan.get("rows"):
        raise PickerError(f"picker {name} has no rows")
    keys: set[str] = set()
    ids: set[str] = set()
    # One image per picture: a picture offered twice (a baseline row reusing a shortlist
    # tile) shows the same JPEG, so `style keep` records it as one keep picked twice.
    images: dict[Path, str] = {}
    rows, sidecar, todo = [], [], []
    for row in plan["rows"]:
        ident = row.get("id") or ""
        if not ident or ident.casefold() in ids:
            raise PickerError(f"picker {name}: row id {ident!r} is empty or repeated")
        ids.add(ident.casefold())
        options = []
        for option in row.get("options") or []:
            picture = Path(option["picture"])
            if not picture.is_absolute():
                picture = Path(resolve(option["picture"])) if resolve else base / picture
            if not picture.is_file():
                raise PickerError(f"picker {name}: no picture at {picture}")
            key = option.get("key") or picture.stem
            # Folded, because a key is a file name and Windows reads two spellings as one.
            if key.casefold() in keys:
                raise PickerError(f"picker {name}: key {key!r} is used twice; keys are global")
            if any(ch in key for ch in '/\\:*?"<>|'):
                raise PickerError(f"picker {name}: key {key!r} is a file name; no / or :")
            keys.add(key.casefold())
            drawn = option.get("render") or read_log(picture.parent).get(picture.name)
            if drawn is None:
                raise PickerError(
                    f"picker {name}: {picture.name} has no row in {picture.parent / LOG_NAME} "
                    "and no 'render' of its own, so a keep of it could not be saved"
                )
            lacking = [
                member
                for member in ("location", "colormap", "resolution", "supersample")
                if member not in drawn
            ]
            if lacking or ("style" in drawn) == ("mode" in drawn):
                raise PickerError(
                    f"picker {name}: {picture.name}'s render lacks {', '.join(lacking) or 'one'}"
                    " of style or mode, so a keep of it could not be saved"
                )
            same = picture.resolve()
            image = images.get(same)
            if image is None:
                image = images[same] = f"{ident}/{key}.jpg"
                todo.append((picture, folder / image))
            sidecar.append({"key": key, **{k: v for k, v in drawn.items() if k != "picture"}})
            entry = {"key": key, "image": image}
            if option.get("label"):
                entry["label"] = option["label"]
            options.append(entry)
        if not options:
            raise PickerError(f"picker {name}: row {ident!r} has no options")
        out = {"id": ident, "label": row.get("label", ident)}
        if row.get("note"):
            out["note"] = row["note"]
        rows.append({**out, "kind": "many", "default": [], "options": options})

    for source, target in todo:
        target.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(source) as picture:
            picture.convert("RGB").save(target, quality=QUALITY)
    manifest = {"name": name, "title": plan.get("title", name)}
    if plan.get("intro"):
        manifest["intro"] = plan["intro"]
    manifest["rows"] = rows
    manifest_path = folder / "manifest.json"
    with manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    renders_path = folder / "renders.jsonl"
    with renders_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in sidecar:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {
        "manifest": manifest_path,
        "renders": renders_path,
        "rows": len(rows),
        "options": len(sidecar),
    }
