"""Style keeps: the renders Matt kept from a style's pickers, saved past the picker.

A picker's images live under `artifacts/pickers/`, which git ignores and a later round
retires, so a keep that only lived there would be lost. `style keep` reads a saved
picker's choices and writes two things:

- `data/styles/<name>.keeps.json` (tracked): the style's reference picture and, per kept
  render, everything needed to draw it again: the location record, the colormap, the
  stack it was drawn with, the size, and Matt's note.
- the pictures themselves, full size, with the reference beside them, in
  `fractal-drive-sync/style-keeps/<name>/`, a sibling of this checkout and never git.

The picker manifest says which picture each kept key was; what it was *drawn from* is
the **renders sidecar**, a JSONL the picker's builder writes beside its manifest, one
row per option:

    {"key": "<option key>", "location": {<location record>}, "style": "<style name>",
     "colormap": "<map>", "resolution": [2560, 1600], "supersample": 2,
     "stack": {<the stack as drawn; absent means the style file's own>}}

A row with `mode` in place of `style` is a named mode's render (a baseline tile).

Re-running merges: a keep already recorded stays, a new round's keeps are added, and a
keep picked again gains the new row and note. A picture whose picker image is gone is
drawn again from its record.

**A redraw is not the picture kept.** The record holds what the picture was drawn
from, not the engine that drew it, and the engine's tone pass has moved under it: since
2026-11-04 it measures the block-averaged picture rather than the samples, so a keep
drawn at supersample 2 before then comes back a little darker or lighter (up to ~0.03
of median lightness). The saved picture is the keep; a redraw says so ([`REDRAWN`]).
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from fractal_wallpapers.paths import repo_root

#: The one schema a keeps file carries today.
SCHEMA = 1

#: What `style keep` says when it drew a keep again rather than copying its picture.
REDRAWN = (
    "{count} drawn again from the record under the current engine: a redraw, not the "
    "picture kept. The tone pass measures the averaged picture since 2026-11-04, so a "
    "supersampled keep drawn before then can read up to ~0.03 lighter or darker."
)


class KeepError(ValueError):
    """Choices, a manifest or a sidecar that cannot be turned into keeps."""


def keeps_path(name: str) -> Path:
    """The tracked record of one style's keeps."""
    return repo_root() / "data" / "styles" / f"{name}.keeps.json"


def keeps_folder(name: str) -> Path:
    """Where one style's kept pictures go: beside the reference pictures, never git."""
    return repo_root().parent / "fractal-drive-sync" / "style-keeps" / name


def read_json(path: Path, what: str) -> Any:
    """One JSON document, or a refusal naming what it was meant to be."""
    if not path.is_file():
        raise KeepError(f"no {what} at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_of(choices: dict[str, Any]) -> Path:
    """The picker manifest a choices file names, relative to this checkout's parent."""
    named = choices.get("manifest")
    if not named:
        raise KeepError(f"choices '{choices.get('name')}' name no manifest; pass --manifest")
    return repo_root().parent / named


def read_renders(path: Path) -> dict[str, dict[str, Any]]:
    """The renders sidecar, by option key."""
    if not path.is_file():
        raise KeepError(f"no renders sidecar at {path}; pass --renders")
    rows: dict[str, dict[str, Any]] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if "key" not in row or "location" not in row or ("style" in row) == ("mode" in row):
            raise KeepError(f"{path.name} line {number}: a row is key, location, style or mode")
        rows[row["key"]] = row
    return rows


def stack_key(style: str, stack: dict[str, Any]) -> str:
    """A stack's name in the keeps file: its style and the first bytes of its hash."""
    text = json.dumps(stack, sort_keys=True, separators=(",", ":"))
    return f"{style}@{hashlib.sha256(text.encode('utf-8')).hexdigest()[:8]}"


def kept(
    choices: dict[str, Any],
    manifest: dict[str, Any],
    renders: dict[str, dict[str, Any]],
    manifest_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Each kept picture once, with its render record; and the stacks they name.

    A picture kept under two keys (a baseline row reusing a shortlist tile) is one keep
    picked twice. Returns `(keeps, stacks)`; each keep carries a `source`, its picker
    image's path, which the caller drops before writing.
    """
    from fractal_wallpapers import styles

    picker = choices["name"]
    options = {
        row["id"]: {option["key"]: option for option in row["options"]} for row in manifest["rows"]
    }
    keeps: dict[str, dict[str, Any]] = {}
    stacks: dict[str, dict[str, Any]] = {}
    for row in choices["rows"]:
        row_notes = row.get("notes") or {}
        for key in row["keys"]:
            option = (options.get(row["id"]) or {}).get(key)
            if option is None:
                raise KeepError(f"{picker}: row '{row['id']}' has no option '{key}'")
            drawn = renders.get(key)
            if drawn is None:
                raise KeepError(f"{picker}: no render row for kept key '{key}'")
            image = Path(option["image"])
            ident = f"{picker}/{image.with_suffix('').as_posix()}"
            render: dict[str, Any] = {"location": drawn["location"]}
            if "style" in drawn:
                stack = drawn.get("stack") or styles.load(drawn["style"])["style"]
                name = stack_key(drawn["style"], stack)
                stacks[name] = stack
                render.update(style=drawn["style"], stack=name)
            else:
                render["mode"] = drawn["mode"]
            render.update(
                colormap=drawn["colormap"],
                resolution=list(drawn["resolution"]),
                supersample=int(drawn["supersample"]),
            )
            note = (row_notes.get(key) or row.get("note") or "").strip()
            entry = keeps.setdefault(
                ident,
                {
                    "id": ident,
                    "picker": picker,
                    "picked": [],
                    "label": option.get("label", ""),
                    "image": f"{picker}__{image.stem}{image.suffix}",
                    "render": render,
                    "source": manifest_dir / image,
                },
            )
            entry["picked"].append({"row": row["id"], "key": key})
            if note:
                entry["note"] = note
    return list(keeps.values()), stacks


def merge(old: dict[str, Any], keeps: list[dict[str, Any]], stacks: dict) -> dict[str, Any]:
    """The keeps file with a round's keeps laid over it; nothing recorded is dropped."""
    by_id = {entry["id"]: entry for entry in old.get("keeps", [])}
    for entry in keeps:
        entry = {k: v for k, v in entry.items() if k != "source"}
        previous = by_id.get(entry["id"])
        if previous is not None:
            picked = list(previous["picked"])
            picked += [pick for pick in entry["picked"] if pick not in picked]
            entry["picked"] = picked
            if "note" not in entry and "note" in previous:
                entry["note"] = previous["note"]
        by_id[entry["id"]] = entry
    merged_stacks = {**old.get("stacks", {}), **stacks}
    return {
        "keeps": [by_id[ident] for ident in sorted(by_id)],
        "stacks": {name: merged_stacks[name] for name in sorted(merged_stacks)},
    }


def spec_for(entry: dict[str, Any], stacks: dict[str, Any], output: Path) -> dict[str, Any]:
    """The engine spec that draws one keep again from its record."""
    from fractal_wallpapers import locations, styles

    render = entry["render"]
    row = locations.one_location(render["location"], entry["id"], drawing=True)
    row["render"] = {
        **row["render"],
        "resolution": list(render["resolution"]),
        "supersample": render["supersample"],
    }
    if "mode" in render:
        row["render"].update(mode=render["mode"], colormap=render["colormap"])
        return locations.spec_of(row, output)
    document = {"style": stacks[render["stack"]], "suggested_colormap": render["colormap"]}
    return styles.spec_of(row, document, output, colormap=render["colormap"])


def keep(
    name: str,
    choices_path: Path,
    *,
    manifest_path: Path | None = None,
    renders_path: Path | None = None,
    folder: Path | None = None,
    record: Path | None = None,
) -> dict[str, Any]:
    """Record a picker's keeps for style `name` and copy (or redraw) their pictures.

    Returns `{record, folder, kept, copied, drawn}`: the counts are this round's.
    """
    from fractal_wallpapers import engine, styles

    document = styles.load(name)
    choices = read_json(choices_path, "choices file")
    manifest_path = manifest_path or manifest_of(choices)
    manifest = read_json(manifest_path, "picker manifest")
    renders = read_renders(renders_path or manifest_path.parent / "renders.jsonl")
    keeps, stacks = kept(choices, manifest, renders, manifest_path.parent)

    folder = folder or keeps_folder(name)
    record = record or keeps_path(name)
    folder.mkdir(parents=True, exist_ok=True)
    reference = styles.reference_path(document)
    if not reference.is_file():
        raise KeepError(f"no reference picture at {reference}")
    shutil.copy2(reference, folder / reference.name)

    copied = drawn = 0
    for entry in keeps:
        target = folder / entry["image"]
        if entry["source"].is_file():
            shutil.copy2(entry["source"], target)
            copied += 1
        elif not target.is_file():
            engine.render_report(spec_for(entry, stacks, target))
            drawn += 1

    old = json.loads(record.read_text(encoding="utf-8")) if record.is_file() else {}
    merged = merge(old, keeps, stacks)
    written = {
        "schema": SCHEMA,
        "name": name,
        "reference": document["reference"],
        "folder": f"fractal-drive-sync/style-keeps/{name}",
        **merged,
    }
    with record.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(written, indent=2, ensure_ascii=False) + "\n")
    return {
        "record": record,
        "folder": folder,
        "kept": len(keeps),
        "copied": copied,
        "drawn": drawn,
        "total": len(merged["keeps"]),
    }
