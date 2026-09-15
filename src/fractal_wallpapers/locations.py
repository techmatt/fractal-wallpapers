"""A location record, and the manifest that holds many of them.

Every record this project writes down says where a place is the same way: a
`family` with all its constants, a `viewport` of three decimal strings, and a
`render` block saying at what size and through which coloring it was drawn. A
walk ledger's candidate rows, the label store's rows and a release's decision
rows are all that shape, which means *most of what anybody wants to do with this
repository is a loop over records that already exist* — draw these twelve, screen
these hundred, score this list.

Nothing could take one. Every command that renders spelled the location out as
flags, so the only way to redraw a row somebody already had was to retype its
constants, and the one caller outside this repository that needed to do it
bypassed [`fractal_wallpapers.engine`] and shelled the binary instead. This
module is the reader that closes that: one place that knows what a location
record is, what it means when a field is missing, and how it becomes an engine
spec.

## What a record has to say, and what it may leave out

`family` and `viewport` are the identity and are required. Everything else is
presentation, and a record that omits it gets the same default the command line
gives a flag nobody passed — so a two-key record is a legal record and draws the
family's own home framing at the standard size.

The one field with a *third* answer is `maxiter`. Absent means "let the
depth-aware policy decide", which is what an engine spec means by leaving it out
and is not the same as any particular number. So it stays absent rather than
being filled in here.

## Four spellings of the same thing, because four records already exist

```text
{"family": ..., "viewport": ..., "render": {...}}       a label row
{"family": ..., "viewport": ..., "maxiter": 13140}      a walk ledger's candidate
{"location": {"family": ..., "viewport": ...}, ...}     a release decision row
{"family": ..., "viewport": ..., "mode": ..., "colormap": ..., "render": {...}}
                                                        a labeled corpus row
```

All four are read. A ledger row keeps its cap at the top level because it has no
render block to put one in — it records a *frame the gates measured*, not a
picture — and a release row nests the location under a key because the rest of
that row is about a wallpaper.

The fourth writes the **coloring flat**, beside `family` rather than inside
`render`, and keeps `render` for the geometry alone — or leaves it out entirely.
It is not a typo and it is not rare: `data/palette_choice/rows/`,
`data/palette_choice/candidate_sets.jsonl`, `models/render/*/scores_*.jsonl` and
`data/palettes/reference_fields.jsonl` are every one of them written that way,
which is tens of thousands of tracked rows and most of what this repository has
to score. A reader that refused it would break `score-locations --manifest` over
the stores that command exists for — the stores are named here rather than a
count, because a count goes stale on the next drop and a name does not.

Which spelling a file uses is the writer's business; a reader that only took one
of them would send half this repository's own records back to being retyped.
Where a row spells one member two ways it has to agree with itself, for the
reason [`refuse_a_member_answered_twice`] gives at the site.

## What this reader refuses, and what only the render door refuses

[`record`] takes a row that names a place and a geometry however much else it is
carrying, because two of its three callers never draw: `screen` keeps the frame
and the cap and throws the rest away — see [`frame_of`] — and `score-locations`
discards the coloring entirely. A corpus row carrying a curve and a palette pass
is a perfectly good input to both, and refusing it here would cost those two a
hazard they do not have.

Drawing is the door where a member this shape cannot carry becomes a wrong
picture, so drawing is where it is refused: [`refuse_a_picture_this_cannot_draw`],
asked for by `read(..., drawing=True)` and by nothing else.
[`refuse_a_recipe_this_cannot_carry`] is the one refusal on the shared path, and
[`record`] says at the site why it was left where it already was.

## Coordinates stay strings

The whole way through, for the reason
[`fractal_wallpapers.discovery.ledger`] gives: the decimal string is the identity
of a location and `f64` is a lossy view of it. A number in a manifest is accepted
and written back out through `repr`, because JSON has no other way to spell one —
but a record written by this project carries strings and gets them back
unaltered.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from fractal_wallpapers.paths import colormap_dir

#: The schema a manifest of location records carries. A file whose rows say
#: nothing is read anyway — the label store and the ledgers stamp their own
#: schema, which is about *those* records rather than about this shape — but a
#: row that names a schema this reader does not know is refused rather than
#: guessed at.
SCHEMA = 1

#: What a location is drawn at when its record does not say. The same numbers the
#: `render` subcommand's flags default to, because a record with no render block
#: and a command line with no render flags are asking the identical question.
DEFAULT_RESOLUTION = (1920, 1080)
DEFAULT_SUPERSAMPLE = 2
DEFAULT_MODE = "smooth"
DEFAULT_COLORMAP = "twilight_shifted"

#: The keys a `render` block may carry. Anything else is a typo or a field from
#: some other record shape, and both are worth refusing: a misspelled
#: `supersamples` that silently drew at the default is a picture nobody can tell
#: from the one they asked for.
RENDER_KEYS = ("resolution", "supersample", "mode", "colormap", "maxiter")

#: What a member is written as when the writer meant nothing by it. Spelling a
#: key is not the same act as answering with it — a row carrying `"colormap":
#: null` beside a `render` block that names a map has left room for a field, not
#: contradicted itself — and every check in this module asks *is this set* rather
#: than *is this present*, because the one that asked about presence would tell
#: that row its picture came out at the default map.
#:
#: `False` and `{}` are in it for the same reason and a real record earns them:
#: `mirror: false` and `mode_params: {}` are what the candidate path produces
#: anyway, so a row saying so is saying nothing a render would do differently,
#: and refusing them would refuse most of the pool for describing the default.
NOT_AN_ANSWER = (None, False, {}, "")

#: What a palette pass is made of when a row writes it out **directly** in
#: `recipe`, rather than nesting it under a `palette` key the way a release
#: recipe does. `data/palette_choice/rows/`, `data/smooth_render/rows/` and
#: `data/gallery_grade/rows/` are all written this way, and a recipe of theirs
#: comes back from [`refuse_a_recipe_this_cannot_carry`] carrying *nothing*: that
#: function asks for a `palette` member by name, there is not one, so the whole
#: pass reads as absent and the picture goes out through this module's own ramp
#: having said so to nobody.
#:
#: `mirror` is deliberately not here even though it is the fifth knob. It is a
#: member in its own right in [`UNCARRIED_RECIPE_MEMBERS`], and a recipe naming
#: only `mirror` is naming a fold rather than writing out a pass — which that
#: entry already decides about, and decides to allow when it is false. Any of
#: these six directly in a recipe can only be the pass with its wrapper missing.
PALETTE_PASS_KNOBS = ("gamma", "cycles", "phase", "reverse", "transfer", "rolloff")

__all__ = [
    "DEFAULT_COLORMAP",
    "DEFAULT_MODE",
    "DEFAULT_RESOLUTION",
    "DEFAULT_SUPERSAMPLE",
    "NOT_AN_ANSWER",
    "PALETTE_PASS_KNOBS",
    "RENDER_KEYS",
    "SCHEMA",
    "UNCARRIED_RECIPE_MEMBERS",
    "LocationError",
    "flat_render_members",
    "frame_of",
    "location_block",
    "maxiter_of",
    "name_of",
    "one_location",
    "read",
    "read_one",
    "record",
    "refuse_a_member_answered_twice",
    "refuse_a_picture_this_cannot_draw",
    "refuse_a_recipe_this_cannot_carry",
    "spec_of",
    "write",
]


class LocationError(RuntimeError):
    """A row that does not describe a location, or describes one impossibly."""


def location_block(row: dict) -> dict:
    """The half of a row that says where the place is.

    A release decision row keeps the location under its own key, because the rest
    of that row is about a wallpaper rather than about a place; every other
    spelling puts `family` at the top. Every reader and every guard below has to
    resolve it the same way, which is why it is resolved once here — a guard that
    looked at one half while the reader took the other would pass exactly the
    rows it was written to catch.
    """
    nested = row.get("location")
    return nested if isinstance(nested, dict) and "family" in nested else row


def flat_render_members(row: dict) -> dict:
    """The render members this row spells flat, beside `family` rather than inside
    `render`.

    The fourth spelling in this module's docstring. Both levels are read, because
    a release row has two top levels and one member can land on either: written
    beside `family` inside the `location` block, or beside `location` itself.
    They are the same claim about the same picture and the inner one wins, that
    being the half the place is in — and where the two make *different* claims
    [`refuse_a_member_answered_twice`] has already sent the row back rather than
    letting this quietly pick one.
    """
    inner = location_block(row)
    found = {}
    for name in RENDER_KEYS:
        for level in (row, inner):
            if level.get(name) not in NOT_AN_ANSWER:
                found[name] = level[name]
    return found


#: What a `recipe` block can say that a location record has no member for, and
#: what each of them decides. A location record is a *place plus a geometry*: the
#: family, the frame, the cap, the resolution, the mode and the map. Everything
#: here is also part of the picture and there is nowhere in this shape to put it.
#:
#: The failure this closes is a silent one. `render --location <release row>`
#: drew the right coordinates through the default palette and exited 0 — a
#: wallpaper nobody asked for under the name of one somebody did — because a
#: reader that drops a member it has no slot for looks exactly like a reader that
#: had nothing to drop. `render --recipe` is the door that takes all of it.
UNCARRIED_RECIPE_MEMBERS: dict[str, str] = {
    "curve": "the transform the mode reads its field through",
    "mirror": "whether the map is folded as an out-and-back",
    "palette": "the seven-knob palette pass — gamma, cycles, phase, reverse, mirror, "
    "transfer, rolloff",
    "mode_params": "the mode's own settings, which only a direct trap carries",
    "autolevel": "the levelling band the picture was tone-mapped onto",
}


def refuse_a_recipe_this_cannot_carry(row: dict, where: str) -> str | None:
    """Say why this row's recipe will not fit in a location record, or `None`.

    Presence and not truthiness, with one exception: `mirror: false` and
    `mode_params: {}` are what this path produces anyway, so a row saying so is
    saying nothing a render would do differently. Anything else — a curve, a
    fold, a palette pass, a trap's settings, a levelling band — changes the
    picture and has no member here to change it through.
    """
    recipe = row.get("recipe")
    if not isinstance(recipe, dict):
        return None
    carried = [name for name in UNCARRIED_RECIPE_MEMBERS if recipe.get(name) not in NOT_AN_ANSWER]
    if not carried:
        return None
    return (
        f"{where}: this row carries a recipe naming "
        + ", ".join(f"{name} ({UNCARRIED_RECIPE_MEMBERS[name]})" for name in carried)
        + ". A location record says a place and a geometry and has nowhere to put any of "
        "that, so rendering it here would draw the right coordinates in the wrong picture. "
        "`render --recipe FILE` takes the whole recipe; a published record's `recipes.jsonl` "
        "is a file of them."
    )


def refuse_a_picture_this_cannot_draw(row: dict, where: str) -> str | None:
    """Say why drawing this row would draw the wrong picture, or `None`.

    **The render door's question, and only the render door's.** [`record`] takes
    anything that names a place and a geometry, because its other two callers do
    not draw: `screen` keeps the frame and the cap and throws the rest away, and
    `score-locations` discards the coloring entirely. A labeled corpus row
    carrying a curve and a palette pass is a perfectly good input to both, so
    asking this question in `record` would refuse tens of thousands of tracked
    rows in order to protect a door those rows never go through.

    Four places a member can hide and [`refuse_a_recipe_this_cannot_carry`]
    looks in one. It reads the keys inside `row["recipe"]` under their own
    names, so three shapes this repository actually writes went straight past
    it:

    - a corpus row's **flat** `curve` or `mode_params`, beside `family` rather
      than inside any recipe at all;
    - a `recipe` that **is** a palette pass — the knobs spelled out where a
      `palette` member would have been — which comes back carrying nothing at
      all, for the reason [`PALETTE_PASS_KNOBS`] gives; and
    - a `recipe` nested inside the `location` block, which is where a release
      row may put it and which a reader of the outer level never opens.

    Either way the picture came out through this module's default ramp and the
    run exited 0, which is the same silent failure that entry was written for
    with the spelling changed.
    """
    inner = location_block(row)
    # Every mapping a member can be written in, nearest spelling first. A recipe
    # on *either* top level is one of them, because a release row nests its
    # location and may nest the recipe beside it — and a check that read only
    # `row["recipe"]` would walk past the nested one exactly as the check this
    # replaces walked past the flat spelling.
    written_in: list[tuple[str, dict]] = [("at the top level", inner)]
    if inner is not row:
        written_in.append(("beside `location`", row))
    for holder, label in ((row, "in `recipe`"), (inner, "in the location's `recipe`")):
        block = holder.get("recipe")
        if isinstance(block, dict):
            written_in.append((label, block))

    found: dict[str, str] = {}
    for name in UNCARRIED_RECIPE_MEMBERS:
        for label, level in written_in:
            if level.get(name) not in NOT_AN_ANSWER:
                found[name] = label
                break
    if "palette" not in found:
        # The knobs are looked for everywhere the pass itself could be, and not
        # in `recipe` alone: a corpus row spells its coloring flat, so a pass
        # written out beside `family` is the same shape as one written out
        # inside a recipe and is the spelling this reader is likeliest to meet.
        # Asked for what is *set* rather than what is spelled, for the reason
        # [`NOT_AN_ANSWER`] gives — a row saying `reverse: false` is describing
        # the default rather than asking for a pass.
        for label, level in written_in:
            if any(level.get(knob) not in NOT_AN_ANSWER for knob in PALETTE_PASS_KNOBS):
                found["palette"] = f"spelled out {label} without its wrapper"
                break
    if not found:
        return None
    return (
        f"{where}: this row names "
        + ", ".join(
            f"{name} {written} ({UNCARRIED_RECIPE_MEMBERS[name]})"
            for name, written in sorted(found.items())
        )
        + ". A location record says a place and a geometry and has nowhere to put any of "
        "that, so drawing it here would draw the right coordinates in the wrong picture. "
        "`render --recipe FILE` takes the whole picture; a published record's "
        "`recipes.jsonl` is a file of them. Reading this row is fine — `screen` and "
        "`score-locations` take it as it stands, because neither of them draws it."
    )


def refuse_a_member_answered_twice(row: dict, block: dict, where: str) -> str | None:
    """Say why this row answers one question about itself twice, or `None`.

    A member answered two ways with two values is two answers about one picture,
    and there is no defensible way to pick between them — exactly the argument
    [`refuse_two_descriptions`] in `fractal_wallpapers.cli.draw_commands` makes
    for a record plus a flag that contradicts it. Agreeing twice is not an error
    and is not refused: a writer that repeats itself is still only saying one
    thing, and the corpora do repeat themselves.

    All three places a member can be written, not two. A release row has a top
    level of its own besides the `location` block it nests, so `supersample`
    beside `location` and `supersample` beside `family` is the same shape of
    contradiction as either one against `render` — and a check that compared only
    flat-against-nested would silently keep whichever of those two it happened to
    read last.

    What is compared is what was *set*, not what was spelled, for the reason
    [`NOT_AN_ANSWER`] gives.
    """
    inner = location_block(row)
    levels = [("inside `render`", block), ("at the top level", inner)]
    if inner is not row:
        levels.append(("beside `location`", row))

    quarrels = []
    for name in RENDER_KEYS:
        answers: list[tuple[str, Any]] = []
        for label, level in levels:
            value = level.get(name)
            if value in NOT_AN_ANSWER:
                continue
            # A pair has one spelling in JSON and two in Python, so `resolution`
            # is compared by value rather than by the type it arrived as.
            value = list(value) if isinstance(value, list | tuple) else value
            if all(value != seen for _, seen in answers):
                answers.append((label, value))
        if len(answers) > 1:
            quarrels.append(
                f"{name} is " + " and ".join(f"{value!r} {label}" for label, value in answers)
            )
    if not quarrels:
        return None
    return (
        f"{where}: {'; '.join(quarrels)}. That is two answers about one picture and there "
        f"is no defensible way to pick between them — the same argument "
        f"`refuse_two_descriptions` makes for a record that a flag contradicts. Delete one "
        f"of the spellings; a row that agrees with itself is read either way."
    )


def record(row: dict, where: str = "record") -> dict:
    """One row as the location record the rest of this module takes.

    Reads all four spellings, checks the two required halves, and fills the
    presentation defaults — so everything downstream sees one shape and no
    caller has to know which kind of file its row came out of.

    This is the reader `screen` and `score-locations` go through as well, so what
    a *render* would refuse a row for is not refused here: that question is
    [`refuse_a_picture_this_cannot_draw`], asked for by `read(..., drawing=True)`
    and by nothing else.

    [`refuse_a_recipe_this_cannot_carry`] is the exception and it is one of
    history rather than of principle. It has refused a recipe naming a curve or a
    fold since before there was a render door to move it to, which is most of the
    tracked release stores; moving it now would newly *admit* rows this reader has
    always sent back, and quietly widening what `screen` and `score-locations`
    accept is a change nobody asked for rather than a fix. So it stays, and
    everything the split added went to the door instead.
    """
    if not isinstance(row, dict):
        raise LocationError(f"{where}: a location is a JSON object, not {type(row).__name__}")
    schema = row.get("schema")
    if schema is not None and not isinstance(schema, int):
        raise LocationError(f"{where}: schema {schema!r} is not an integer")

    inner = location_block(row)

    family = inner.get("family")
    viewport = inner.get("viewport")
    if not isinstance(family, dict) or not family.get("kind"):
        raise LocationError(f"{where}: no family — a location's identity is half its constants")
    if not isinstance(viewport, dict):
        raise LocationError(f"{where}: no viewport")
    for key in ("center_re", "center_im", "width"):
        if viewport.get(key) is None:
            raise LocationError(f"{where}: viewport names no {key}")

    block = inner.get("render") or row.get("render") or {}
    if not isinstance(block, dict):
        raise LocationError(f"{where}: render is not an object")
    complaint = refuse_a_recipe_this_cannot_carry(row, where)
    if complaint is not None:
        raise LocationError(complaint)
    # A row that carries a recipe says its mode, its map and its geometry THERE,
    # and this took neither — a release row has no top-level `render` block, so
    # every one of them read as the module's defaults. The refusal above has
    # already sent back anything a location record cannot express; what is left
    # is a recipe this shape can carry whole, and taking it is the difference
    # between drawing the wallpaper and drawing the place it stands on.
    recipe = row.get("recipe")
    if isinstance(recipe, dict):
        inherited = recipe.get("render") if isinstance(recipe.get("render"), dict) else {}
        block = {
            **{name: value for name, value in inherited.items() if name in RENDER_KEYS},
            **{name: recipe[name] for name in ("mode", "colormap") if recipe.get(name) is not None},
            **block,
        }
    unknown = sorted(set(block) - set(RENDER_KEYS))
    if unknown:
        raise LocationError(
            f"{where}: render carries {', '.join(unknown)}, which nothing here draws. "
            f"A render block says {', '.join(RENDER_KEYS)}"
        )

    # The fourth spelling, read last so the nested one wins where a row carries
    # both — and refused outright where the two disagree, because that is a row
    # that says two things about one picture. This used to be where a flat
    # coloring was silently dropped: a flat key is not the `render` block, and
    # the unknown-key check above looks only *inside* that block, so `mode` and
    # `colormap` beside `family` were neither read nor complained about and the
    # picture came out at the defaults. The cap comes through the same door,
    # which is what makes a walk ledger's candidate readable.
    complaint = refuse_a_member_answered_twice(row, block, where)
    if complaint is not None:
        raise LocationError(complaint)
    block = {**flat_render_members(row), **block}

    resolution = block.get("resolution") or list(DEFAULT_RESOLUTION)
    if len(list(resolution)) != 2:
        raise LocationError(f"{where}: resolution is [width, height], not {resolution!r}")

    # The cap is the one field with a third answer: absent means "the
    # depth-aware policy decides", which is not any particular number.
    maxiter = block.get("maxiter")

    out: dict[str, Any] = {
        "family": family,
        "viewport": {key: str(viewport[key]) for key in ("center_re", "center_im", "width")},
        "render": {
            "resolution": [int(resolution[0]), int(resolution[1])],
            "supersample": int(block.get("supersample") or DEFAULT_SUPERSAMPLE),
            "mode": block.get("mode") or DEFAULT_MODE,
            "colormap": block.get("colormap") or DEFAULT_COLORMAP,
        },
    }
    if maxiter is not None:
        out["render"]["maxiter"] = int(maxiter)
    return out


def read(path: Path, *, drawing: bool = False) -> list[dict]:
    """Every location in a JSONL manifest, in the order it was written.

    Blank lines are skipped and every other line has to be a location, so a file
    that is half something else fails on the row that is, naming it.

    `drawing` asks the render door's extra question of every row — see
    [`refuse_a_picture_this_cannot_draw`] — and is **off by default** because two
    of this function's three callers do not draw. `screen` keeps the frame and
    the cap; `score-locations` discards the coloring entirely. Turning it on for
    those two would refuse most of the labeled corpora for carrying exactly the
    members they throw away.
    """
    path = Path(path)
    rows = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as bad:
                raise LocationError(f"{path}:{number}: not JSON: {bad}") from bad
            rows.append(one_location(row, f"{path}:{number}", drawing=drawing))
    if not rows:
        raise LocationError(f"{path} holds no location")
    return rows


def one_location(row: dict, where: str, *, drawing: bool) -> dict:
    """[`record`], with the render door's question asked first where it applies.

    Asked before the row is read rather than after, so the wider complaint is the
    one that comes back: a corpus row carries a curve *and* a palette pass, and
    being told about the pass alone would send somebody to delete one key and try
    again.
    """
    if drawing and isinstance(row, dict):
        complaint = refuse_a_picture_this_cannot_draw(row, where)
        if complaint is not None:
            raise LocationError(complaint)
    # A row that is not an object at all goes straight to [`record`], which has
    # the one refusal that says so. The question above reads keys off the row,
    # and a manifest line holding a bare string has none — asked first and
    # unguarded, it comes back an `AttributeError` through the door whose whole
    # business is turning a bad row into one clean line and an exit code.
    return record(row, where)


def read_one(path: Path, *, drawing: bool = False) -> dict:
    """One location, from a JSON object or from a manifest holding exactly one.

    Both, because "a location" arrives written both ways and neither spelling is
    wrong — a record copied out of a ledger row is an object, and a one-row
    manifest is what a batch of one looks like. `drawing` is [`read`]'s, for the
    same reason and with the same default.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise LocationError(f"{path} is empty")
    if text.lstrip().startswith("["):
        rows = json.loads(text)
        if len(rows) != 1:
            raise LocationError(f"{path} holds {len(rows)} locations; --manifest takes many")
        return one_location(rows[0], str(path), drawing=drawing)
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) > 1:
        raise LocationError(
            f"{path} holds {len(lines)} rows, and this takes one location. A file of many "
            f"is a manifest — pass it as one."
        )
    return one_location(json.loads(lines[0]), str(path), drawing=drawing)


def write(rows, path: Path) -> Path:
    """Write a manifest of location records, one per line."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps({"schema": SCHEMA, **row}, ensure_ascii=False) + "\n")
    return path


def maxiter_of(row: dict) -> int:
    """This location's iteration cap, asking the engine's policy where the record
    does not say. A number rather than `None`, for the callers that have to record
    what a picture was actually drawn at."""
    from fractal_wallpapers import engine

    cap = row["render"].get("maxiter")
    if cap is not None:
        return int(cap)
    return engine.maxiter_for([row["viewport"]["width"]])[0]


def spec_of(row: dict, output: Path) -> dict:
    """The JSON object the engine's `render` reads, for one location record."""
    render = row["render"]
    spec: dict[str, Any] = {
        "schema": 1,
        "family": row["family"],
        "viewport": row["viewport"],
        "resolution": list(render["resolution"]),
        "supersample": int(render["supersample"]),
        "mode": render["mode"],
        "colormap": render["colormap"],
        "colormap_dir": str(colormap_dir()),
        "output": str(output),
    }
    if render.get("maxiter") is not None:
        spec["maxiter"] = int(render["maxiter"])
    return spec


def frame_of(row: dict) -> dict:
    """The JSON object the engine's `screen` reads, for one location record.

    The render block is not in it, and that is the point: the gates read a frame
    at *their* geometry — the one an expansion draws every candidate at — so what
    a record says about resolution and coloring is not a fact about the frame
    being screened. The cap is the exception, because it decides what counts as
    interior and therefore what the first gate measures.
    """
    frame = {"family": row["family"], **row["viewport"]}
    if row["render"].get("maxiter") is not None:
        frame["maxiter"] = int(row["render"]["maxiter"])
    return frame


#: Characters of the digest a location's picture is named by. Long enough that a
#: batch of thousands will not collide, short enough to read off a directory.
NAME_LENGTH = 16


def name_of(row: dict) -> str:
    """A stable file name for one location's picture: a digest of what makes it.

    Everything the engine is told goes in and nothing else does, the same rule
    the finished-render cache names by — so two records that would produce the
    same picture name one file, and a record that differs anywhere gets its own.
    """
    material = json.dumps(spec_of(row, Path("x")), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:NAME_LENGTH]
