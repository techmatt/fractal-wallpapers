"""A mode's palette set: one stack, the maps Matt kept it in, and the values each was tuned to.

A custom render mode is a **stack plus a palette set**. Styles whose stacks have the same
layers and channels, differing only in numbers or a colour, are one mode: the stack is
the mode's style file, and each palette entry in its `catalog.json` row is a map with
the few values tuned for it, its keeps and its score:

    {"colormap": "<library map>", "was": "<an old style name, optional>",
     "reference": "<the reference this entry was fitted to, optional>",
     "values": {"/layers/3/color": {"rgb": "#5a7cff"}, "/tone/median": 0.238},
     "keeps": ["<keep id in <mode>.keeps.json>", ...], "score": 1-5}

The first entry is the mode's default and is the stack's own (`values` empty); the
mode's score is its best entry's. A value is a pointer into the stack (`/`-separated,
list indices as numbers, as a public knob's) and what it writes there whole: a number,
or a colour as `{"rgb": ...}` or `{"palette": ...}`. A layer one entry does without is
its `opacity` at 0.

**A palette joins a set only through a kept tile** (Matt's rule): `style keep` adds each
kept map to the mode's set, and a map no tile kept leaves the library
(`palettes remove`). `palettes add --mode <mode>` admits a map for a mode's next round as
an entry with no keeps yet: the round in flight, which its keeps fill or its removal ends.
"""

from __future__ import annotations

import copy
from typing import Any

#: The members of a colour value: a whole value, never compared member by member.
COLOR_KEYS = {"rgb", "palette"}

#: How many whole layers an entry may do without (each at opacity 0) and still be the
#: same structure: `golden_petals` in `glossy_spirals`, which lacks only the spine glow
#: its three siblings were tuned with. More is a superset stack wearing unused layers,
#: which is never a merge (Matt's ruling, item 038): the stacks must already match.
MOST_DROPPED = 1


class Incompatible(ValueError):
    """Two stacks that differ in their layers or channels, not only in values."""


def is_color(node: Any) -> bool:
    return isinstance(node, dict) and bool(node) and set(node) <= COLOR_KEYS


def _walk(base: Any, other: Any, path: str, out: dict[str, Any]) -> None:
    if is_color(base) and is_color(other):
        if base != other:
            out[path] = copy.deepcopy(other)
        return
    if isinstance(base, bool) or isinstance(other, bool):
        if base != other:
            raise Incompatible(f"{path or '/'}: {base!r} against {other!r}")
        return
    if isinstance(base, (int, float)) and isinstance(other, (int, float)):
        if base != other:
            out[path] = other
        return
    if isinstance(base, dict) and isinstance(other, dict):
        if set(base) != set(other):
            raise Incompatible(f"{path or '/'}: members {sorted(set(base) ^ set(other))}")
        for key in base:
            if key != "name" or path:
                _walk(base[key], other[key], f"{path}/{key}", out)
        return
    if isinstance(base, list) and isinstance(other, list):
        if len(base) != len(other):
            raise Incompatible(f"{path or '/'}: {len(base)} members against {len(other)}")
        if all(isinstance(v, (int, float)) for v in base + other):
            if base != other:
                out[path] = list(other)
            return
        for index, (one, two) in enumerate(zip(base, other, strict=True)):
            _walk(one, two, f"{path}/{index}", out)
        return
    if base != other:
        raise Incompatible(f"{path or '/'}: {base!r} against {other!r}")


def values_between(base: dict[str, Any], other: dict[str, Any]) -> dict[str, Any]:
    """The values that turn stack `base` into `other`; `Incompatible` when they differ in
    structure.

    `other` may lack whole layers `base` has: each is written as its `opacity` at 0,
    which draws the same picture. Any other difference (a kind, a channel, a blend, a
    member present in one) is structure, and refused.
    """
    layers, theirs = base.get("layers", []), other.get("layers", [])
    missing = len(layers) - len(theirs)
    if missing < 0 or missing > MOST_DROPPED:
        raise Incompatible(f"/layers: {len(layers)} layers against {len(theirs)}")
    best: Incompatible | None = None
    for dropped in _drops(len(layers), missing):
        kept = [layer for index, layer in enumerate(layers) if index not in dropped]
        out: dict[str, Any] = {}
        try:
            _walk({**base, "layers": kept}, other, "", out)
        except Incompatible as refusal:
            best = best or refusal
            continue
        # Pointers were taken against the kept layers: put them back on the base's.
        index_of = [index for index in range(len(layers)) if index not in dropped]
        values = {f"/layers/{index}/opacity": 0.0 for index in sorted(dropped)}
        for pointer, value in out.items():
            steps = pointer.split("/")
            if len(steps) > 2 and steps[1] == "layers":
                steps[2] = str(index_of[int(steps[2])])
            values["/".join(steps)] = value
        return dict(sorted(values.items(), key=lambda item: _order(item[0])))
    raise best or Incompatible("/layers: no alignment")


def _drops(count: int, missing: int):
    """Every way of dropping `missing` of `count` layers, fewest early drops first."""
    from itertools import combinations

    yield from (set(chosen) for chosen in combinations(range(count), missing))


def _order(pointer: str) -> list:
    return [int(step) if step.isdigit() else step for step in pointer.split("/")]


def apply(stack: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    """The stack with each value written at its pointer; a pointer naming nothing refuses."""
    from fractal_wallpapers import styles

    stack = copy.deepcopy(stack)
    for pointer, value in values.items():
        places = styles.targets(stack, pointer)
        if not places or "*" in pointer:
            raise styles.StyleError(f"value {pointer} names nothing in the stack")
        for node, key in places:
            node[key] = copy.deepcopy(value)
    return stack


def entry_for(row: dict[str, Any], colormap: str) -> dict[str, Any] | None:
    """The row's palette entry for `colormap`, or None."""
    return next((e for e in row.get("palettes", []) if e["colormap"] == colormap), None)


def is_score(value: Any) -> bool:
    """A score Matt gives: a whole number 1 to 5. `4.0` passed `in range(1, 6)` and then
    crashed the gallery's stars."""
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 5


def library_maps() -> set[str]:
    """The library's map names, exactly as spelled: a path test on Windows let a
    wrong-case name pass, which `entry_for`'s exact match then never found."""
    from fractal_wallpapers.paths import colormap_dir

    return {path.stem for path in colormap_dir().glob("*.json")}


def score_of(row: dict[str, Any]) -> int | None:
    """The mode's score: its best entry's."""
    scores = [entry["score"] for entry in row.get("palettes", []) if "score" in entry]
    return max(scores) if scores else None


def add_keeps(
    row: dict[str, Any],
    stack: dict[str, Any],
    keeps: list[dict[str, Any]],
    stacks: dict[str, dict[str, Any]],
) -> list[str]:
    """Lay a round's keeps into the row's palette set; the maps newly in it.

    Each kept tile drawn in the style joins its map's entry, which is made when the set
    lacks it, with the values its drawn stack holds against the mode's (none when the
    tile was a formulation of another structure: the keep's record holds that stack).
    A baseline tile (a named mode's render) is no palette of this mode's.
    """
    added = []
    palettes = row.setdefault("palettes", [])
    for keep in keeps:
        render = keep["render"]
        if "style" not in render:
            continue
        entry = entry_for(row, render["colormap"])
        if entry is None:
            try:
                values = values_between(stack, stacks[render["stack"]])
            except Incompatible:
                values = {}
            entry = {"colormap": render["colormap"], "values": values, "keeps": []}
            palettes.append(entry)
            added.append(render["colormap"])
        if keep["id"] not in entry["keeps"]:
            entry["keeps"].append(keep["id"])
    return added


def check_row(row: dict[str, Any], stack: dict[str, Any], keeps: dict[str, Any]) -> list[str]:
    """Each way a row's palette set disagrees with its stack, keeps and score."""
    from fractal_wallpapers import styles

    name = row.get("style", "?")
    palettes = row.get("palettes")
    discarded = row.get("status") == "discarded"
    if not isinstance(palettes, list) or (not palettes and not discarded):
        return [f"{name}: names no palettes (a mode is a stack and a palette set)"]
    problems = []
    seen = set()
    maps = library_maps()
    for index, entry in enumerate(palettes):
        colormap = entry.get("colormap")
        if colormap in seen:
            problems.append(f"{name}: palette {colormap} is in the set twice")
        seen.add(colormap)
        if colormap not in maps:
            problems.append(f"{name}: no colormap '{colormap}' in the library")
        values = entry.get("values")
        if not isinstance(values, dict):
            problems.append(f"{name}: palette {colormap} has no values map")
            continue
        if index == 0 and values:
            problems.append(f"{name}: the default palette {colormap} is the stack's own")
        try:
            apply(stack, values)
        except styles.StyleError as refusal:
            problems.append(f"{name}: palette {colormap}: {refusal}")
        if "score" in entry and not is_score(entry["score"]):
            problems.append(f"{name}: palette {colormap} scores {entry['score']}, not 1 to 5")
        for ident in entry.get("keeps", []):
            keep = keeps.get(ident)
            if keep is None:
                problems.append(f"{name}: palette {colormap} names '{ident}', not in its keeps")
            elif keep["render"]["colormap"] != colormap:
                problems.append(f"{name}: keep '{ident}' was drawn in another map")
    for ident, keep in keeps.items():
        render = keep["render"]
        if "style" in render and not any(ident in e.get("keeps", []) for e in palettes):
            problems.append(f"{name}: keep '{ident}' ({render['colormap']}) is in no palette")
    best = score_of(row)
    if best is not None and row.get("score") != best:
        problems.append(f"{name}: score {row.get('score')}, its best palette's is {best}")
    public = row.get("public")
    if public and palettes and public.get("palette") != palettes[0]["colormap"]:
        problems.append(f"{name}: public palette {public.get('palette')} is not the set's first")
    return problems
