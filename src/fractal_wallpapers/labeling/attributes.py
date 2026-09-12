"""THE location-attribute stores: what a place *is*, as opposed to how good it is.

Three stores in this project ask a person how good something is, all of them on
one 1..4 scale — the location corpus and the two finished-render corpora. This
module owns a different kind of question entirely:

```text
spiral     is this location a pure enough spiral that a gallery cap should count it
repeat_ab  shown the 1x render beside the repeated one, which is the better picture
```

An **attribute** is a verdict cast into named classes, keyed on a place, and it
exists to be *counted* rather than to be maximized: a share cap in the solve, a
linear probe on the neutral embeddings, a rate about one axis of the recipe.
Nothing here is a tier, nothing here is a floor, and nothing here may ever be
pooled with a quality store.

## The second store asks about a PAIR, and that is a shape and not an exception

`spiral` asks what one place is. `repeat_ab` asks which of two renders of one
place is better, and the difference is [`Attribute.paired`]: the unit is a single
composite picture with the two renders side by side, and the row carries **both**
recipe keys rather than one. Everything else is unchanged — ordered classes, an
ordinal at the page and a class in the store, a location key, latest-wins.

That the classes are *comparative* rather than descriptive is the reason the
absent-`score` guard below matters more here than it does for `spiral`, not less.
`repeat_ab`'s ordinals run 1..3 and its `3` means *the repeat is the better
picture* — a sentence about two renders — where a `3` in `smooth_render` means
tier 3 on the quality scale. Written as a number into a quality store, rescaled,
offset or otherwise, it would corrupt every reading taken off that store, and
there is no transformation that makes the two commensurable because they are
answers to different questions.

## The guard is an absent field, and it is asserted at the writer

A row here carries `class` and **no `score` key at all**. That absence is the
whole protection: every quality reader in this repository reaches for `score`,
and a store whose two classes happened to be written as `1` and `2` would read
as a corpus of ones and twos the day somebody pooled the stores by field name.
`check` refuses a row carrying `score`, so the confusion cannot be created rather
than being merely discouraged.

The page still casts on ordinals — a labeler presses `1` or `2` — because the
rig's export format is a number per unit and a second export shape would be a
second answer to what a drop is. The ordinal is turned into a class **once**, at
ingest, by [`class_of`], and the number does not survive into the store.

## Keyed on the LOCATION, judged from a finished picture

This is the one place the two halves come apart, and it is deliberate. A spiral
is a property of the place, so latest-wins resolves on
[`supply.location.location_key`] exactly as the location corpus does — a second
sitting that re-renders a place under a different palette is a second opinion
about the same place and supersedes the first.

But the *picture* Matt judged was a finished render, chosen because it is the one
the solve would seat, and a verdict about a picture nobody can rebuild is worth
what a label with no join is worth. So the row carries the whole render block
beside the place: the mode with its own settings, the curve, the map, every knob
of the palette pass and the geometry. Nothing keys on it; it is there so the
sitting can be reconstructed, and so a later reading can ask whether a `not_spiral`
verdict was about the place or about one unlucky coloring.

## The pin is intra-batch, which the registry alone cannot express

`eval_only` in [`registry`] is a flag on a *batch*, and a sitting that reserves a
fifth of its own units has no second batch to hang it on — putting the reserved
units in one would print a different batch name on their cards and tell the
labeler which ones they were. So the reservation is drawn seeded at build time
and written to this store's own `eval_split.jsonl`, before a single verdict
exists, and [`assert_pin_holds`] is what a probe asserts against the training
side it built. A registration says how a population was drawn; only the pin file
says which of its members are the instrument.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from fractal_wallpapers.labeling import registry as registry_module
from fractal_wallpapers.labeling import store
from fractal_wallpapers.paths import repo_root
from fractal_wallpapers.supply.location import key_of_row

#: The schema every attribute row carries, from the first row.
SCHEMA = 1


@dataclass(frozen=True)
class Attribute:
    """One attribute: what it is called, what it may be, and what it asks.

    `classes` is ordered, and the order is what the page's buttons and the
    export's ordinals mean — the first class is `1`. Reordering it after a
    sitting would re-interpret every drop already on disk, which is why the
    tuple is spelled once here and read everywhere else.
    """

    name: str
    classes: tuple[str, ...]
    #: What each class means, in the labeler's own words. One entry per class.
    words: tuple[str, ...]
    #: The sentence the page puts under the buttons.
    rubric: str
    #: Whether one unit is **two** renders judged against each other rather than
    #: one render judged on its own. A paired attribute's tile is a single
    #: composite picture and its row carries two recipe keys; a sheet source picks
    #: itself off this rather than off the store's name, so a second paired store
    #: needs no second branch anywhere. See the module docstring.
    paired: bool = False

    @property
    def tiers(self) -> tuple[int, ...]:
        """The ordinals the page casts on: one per class, from 1."""
        return tuple(range(1, len(self.classes) + 1))

    def word_map(self) -> dict[str, str]:
        """`{ordinal: the class's own word}` — what the page prints on a button."""
        return {str(n): word for n, word in zip(self.tiers, self.words, strict=True)}


SPIRAL = Attribute(
    name="spiral",
    classes=("spiral", "not_spiral"),
    words=("spiral", "not a spiral"),
    rubric=(
        "<b>Two classes, and this is not a quality question.</b> "
        "<span class='s1'>1</span> <b>spiral</b> — a pure enough spiral that a gallery cap "
        "should count it · "
        "<span class='s2'>2</span> <b>not a spiral</b> — enough non-spiral content that the "
        "cap should not. Judge the place, not the palette: a spiral badly colored is still a "
        "spiral."
    ),
)

#: The comparative store, and the one paired attribute there is.
#:
#: **Its `3` is not a tier 3 and must never enter a quality store.** The scale
#: answers *which of these two pictures is better*, so it is not the 1..4 quality
#: scale under another name and no transformation makes it into one — see the
#: module docstring. The guard is [`check`]'s refusal of a `score` key, which is
#: the same guard `spiral` stands behind and is why this store could be declared
#: rather than built.
REPEAT_AB = Attribute(
    name="repeat_ab",
    classes=("repeat_worse", "neutral", "repeat_better"),
    words=("the repeat is worse", "no difference", "the repeat is better"),
    rubric=(
        "<b>Which picture is better — and this is not the 1–4 quality scale.</b> "
        "The <b>left</b> half is always the single traversal; the right half repeats the "
        "gradient. Same place, same mode, same map, same frame: the traversal count is the "
        "only thing that moves. "
        "<span class='s1'>1</span> <b>the repeat is worse</b> · "
        "<span class='s2'>2</span> <b>no difference</b> · "
        "<span class='s3'>3</span> <b>the repeat is better</b>. "
        "Every unit starts at 2, so mark only the ones that differ."
    ),
    paired=True,
)

#: Every attribute store this module owns, by name.
ATTRIBUTES: dict[str, Attribute] = {SPIRAL.name: SPIRAL, REPEAT_AB.name: REPEAT_AB}

#: Every attribute store's name, for a caller building a choice list.
NAMES: tuple[str, ...] = tuple(sorted(ATTRIBUTES))


class AttributeRefused(ValueError):
    """A row that may not enter an attribute store, or one in it that cannot be read.

    Not spelled `AttributeError`, which is a builtin every `getattr` in this
    process raises: a module-level shadow of it would turn an ordinary typo
    somewhere else into this store's error class, caught by whoever was catching
    this one.
    """


def attribute(name: str) -> Attribute:
    """Return the attribute `name` names. Raises on one nobody declared."""
    held = ATTRIBUTES.get(name)
    if held is None:
        raise AttributeRefused(f"unknown attribute {name!r} — known: {list(NAMES)}")
    return held


def classes(name: str) -> tuple[str, ...]:
    """The classes a labeler may cast for this attribute."""
    return attribute(name).classes


def class_of(name: str, ordinal: int) -> str:
    """THE ordinal-to-class map: what the page's `1` means in this store.

    One direction only. A caller holding a class and wanting its ordinal is a
    caller about to write a number into a store that holds none.
    """
    held = attribute(name)
    if not isinstance(ordinal, int) or isinstance(ordinal, bool):
        raise AttributeRefused(f"{ordinal!r} is not an ordinal a page casts")
    if ordinal not in held.tiers:
        raise AttributeRefused(
            f"ordinal {ordinal!r} is not one of {list(held.tiers)} for {name!r}, which has "
            f"{len(held.classes)} classes"
        )
    return held.classes[ordinal - 1]


# --------------------------------------------------------------------------- #
# Where everything lives.
# --------------------------------------------------------------------------- #
def store_dir(name: str) -> Path:
    """Where one attribute's tracked records live."""
    return repo_root() / "data" / attribute(name).name


def row_dir(name: str) -> Path:
    return store_dir(name) / "rows"


def batch_path(name: str, batch: str) -> Path:
    return row_dir(name) / f"{batch}.jsonl"


def registry_path(name: str) -> Path:
    return store_dir(name) / "batches.jsonl"


def eval_split_path(name: str) -> Path:
    """The reserved evaluation side: one row per pinned location."""
    return store_dir(name) / "eval_split.jsonl"


def split_recipe_path(name: str) -> Path:
    """How the reservation was drawn, and what it realized."""
    return store_dir(name) / "split.json"


def registry(name: str) -> dict[str, registry_module.Registration]:
    """Every batch registration for one attribute, fail-closed on anything absent."""
    return registry_module.read(registry_path(name))


def register(name: str, registration: registry_module.Registration) -> dict:
    """Register a batch. Appended, and refused when it contradicts what stands."""
    if not registration.batch:
        raise registry_module.RegistrationError("a registration must name its batch")
    if not registration.method:
        raise registry_module.RegistrationError(
            f"{registration.batch}: a registration must say how the population was drawn"
        )
    registry_module.refuse_contradiction(registry(name), registration)
    row = registration.row()
    if row["registered_at"] is None:
        row["registered_at"] = store.now()
    path = registry_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


# --------------------------------------------------------------------------- #
# The row.
# --------------------------------------------------------------------------- #
def place_of(row: dict) -> tuple | None:
    """THE identity latest-wins resolves on, and what the pin is asserted at."""
    return key_of_row(row)


def check(name: str, row: dict) -> dict:
    """Return `row`, having proved it is an attribute row for this store."""
    held = attribute(name)
    if row.get("schema") != SCHEMA:
        raise AttributeRefused(f"schema {row.get('schema')!r}, expected {SCHEMA}")
    batch = row.get("batch")
    if not isinstance(batch, str) or not batch:
        raise AttributeRefused("a row must name the batch it was drawn from")
    if "score" in row:
        raise AttributeRefused(
            f"this row carries a `score`. An attribute is not a tier and this store is never "
            f"pooled with a quality corpus — every quality reader in this project keys on "
            f"`score`, so a {held.name!r} row that carried one would read as a verdict on the "
            f"1..4 scale the moment somebody pooled the stores by field name. Write `class`."
        )
    verdict = row.get("class")
    if verdict is not None and verdict not in held.classes:
        raise AttributeRefused(f"class {verdict!r} is not one of {list(held.classes)} or null")
    origin = row.get("origin")
    if origin != store.HUMAN and not (
        isinstance(origin, str) and origin.startswith(store.RULE_PREFIX)
    ):
        raise AttributeRefused(f"origin {origin!r}: a verdict is a human's or a stated rule's")
    if not isinstance(row.get("recorded_at"), str):
        raise AttributeRefused("a row must carry the time it was recorded; it is how latest wins")
    if place_of(row) is None:
        raise AttributeRefused(
            "this row carries no location identity — an attribute is a fact about a place, and "
            "it needs the family with every constant and the viewport on the same line or it "
            "is a verdict about somewhere nobody can find again"
        )
    return row


def attribute_row(
    name: str,
    batch: str,
    verdict: str | None,
    family: dict,
    viewport: dict,
    render: dict | None = None,
    origin: str = store.HUMAN,
    labeler: str | None = None,
    recorded_at: str | None = None,
    **extra,
) -> dict:
    """Build one attribute row. The only shape the writer accepts.

    `render` is the whole join of the picture the labeler was shown — the mode
    with its settings, the curve, the map, the palette pass and the geometry.
    Nothing keys on it; see the module docstring for why it travels anyway.
    """
    row = {
        "schema": SCHEMA,
        "attribute": attribute(name).name,
        "batch": batch,
        "recorded_at": recorded_at or store.now(),
        "labeler": labeler,
        "origin": origin,
        "class": verdict,
        "family": family,
        "viewport": viewport,
        "render": render or {},
        **extra,
    }
    return check(name, row)


def append(name: str, rows: list[dict], known: dict | None = None) -> Path:
    """THE writer. Append checked rows to their batch's file and return its path."""
    if not rows:
        raise AttributeRefused("nothing to append")
    batches = {row.get("batch") for row in rows}
    if len(batches) != 1:
        raise AttributeRefused(f"one call writes one batch's rows, not {sorted(batches)}")
    batch = batches.pop()
    known = registry(name) if known is None else known
    if batch not in known:
        raise AttributeRefused(
            f"batch {batch!r} has no registration in the {name} store. Register it before its "
            "first row exists — afterwards, how its population was drawn is answered from "
            "memory."
        )
    checked = [check(name, row) for row in rows]
    path = batch_path(name, batch)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for row in checked:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def row_paths(name: str) -> list[Path]:
    directory = row_dir(name)
    return sorted(directory.glob("*.jsonl")) if directory.is_dir() else []


def read(name: str, paths=None) -> list[dict]:
    """Every row of one store, schema-checked and stamped with where it came from."""
    paths = row_paths(name) if paths is None else [Path(p) for p in paths]
    out: list[dict] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if row.get("schema") != SCHEMA:
                    raise AttributeRefused(
                        f"{path}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}"
                    )
                out.append({**row, "_file": path.name, "_line": number})
    return out


@dataclass
class Resolution:
    """What one attribute store currently says, and what it could not say it about."""

    current: dict = field(default_factory=dict)
    n_rows: int = 0
    n_superseded: int = 0
    n_unkeyed: int = 0
    unkeyed: list = field(default_factory=list)

    def cast(self) -> list[dict]:
        """The resolved rows carrying a verdict, in location-key order.

        Ordered on the key's text: an absent family constant is recorded as
        absent, so two keys can hold a tuple and a `None` in one position and
        refuse to compare.
        """
        return [
            row
            for _key, row in sorted(self.current.items(), key=lambda item: repr(item[0]))
            if row.get("class") is not None
        ]

    def counts(self) -> dict[str, int]:
        """`{class: how many places currently carry it}`."""
        out: dict[str, int] = {}
        for row in self.cast():
            out[row["class"]] = out.get(row["class"], 0) + 1
        return dict(sorted(out.items()))

    def summary(self) -> dict:
        return {
            "rows": self.n_rows,
            "locations": len(self.current),
            "cast": len(self.cast()),
            "classes": self.counts(),
            "superseded": self.n_superseded,
            "unkeyed": self.n_unkeyed,
        }


def resolve(rows: list[dict], known: dict | None = None) -> Resolution:
    """THE resolution rule: per location, an evaluation row wins, then the latest.

    The same order the quality stores resolve in, through the same function —
    see [`store.resolution_order`]. An attribute is a different question and it
    is not a different clock.
    """
    eval_only = store.eval_side_batches(known)
    resolution = Resolution(n_rows=len(rows))
    for row in sorted(rows, key=lambda row: store.resolution_order(row, eval_only)):
        key = place_of(row)
        if key is None:
            resolution.n_unkeyed += 1
            resolution.unkeyed.append(row)
            continue
        if key in resolution.current:
            resolution.n_superseded += 1
        resolution.current[key] = row
    return resolution


def resolved(name: str, paths=None) -> Resolution:
    """THE reader every consumer of an attribute store routes through."""
    return resolve(read(name, paths), known=registry(name))


# --------------------------------------------------------------------------- #
# The pin.
# --------------------------------------------------------------------------- #
def pin_row(unit: dict) -> dict:
    """One reserved place, in the shape [`eval_split_path`] holds them.

    The place and nothing else that could move: the batch it was drawn under, and
    the family and viewport the key is built from. A pin that carried the whole
    render block would be a pin somebody could read as being about a picture.
    """
    family = unit.get("family")
    viewport = unit.get("viewport")
    if key_of_row(unit) is None:
        raise AttributeRefused("a reserved unit carries no location")
    return {
        "schema": SCHEMA,
        "batch": unit.get("batch"),
        "family": family,
        "viewport": viewport,
    }


def write_pin(name: str, rows: list[dict], recipe_document: dict) -> tuple[Path, Path]:
    """Ship the reserved evaluation side and the record of how it was drawn."""
    members = eval_split_path(name)
    members.parent.mkdir(parents=True, exist_ok=True)
    with members.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    document = split_recipe_path(name)
    document.write_text(
        json.dumps(recipe_document, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return members, document


def pinned(name: str) -> dict[tuple, str]:
    """`{location: batch}` for every place this store's evaluation side holds."""
    path = eval_split_path(name)
    if not path.is_file():
        return {}
    out: dict[tuple, str] = {}
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            place = place_of(row)
            if place is None:
                raise AttributeRefused(f"{path}:{number}: a pinned row carries no location")
            out[place] = row.get("batch", "")
    return out


def assert_pin_holds(name: str, train_rows: list[dict]) -> dict:
    """Raise unless no training row sits on a reserved location.

    What a probe asserts on the split it *built*. The reservation here is
    intra-batch, so — unlike the finished stores — an ordinary ingest does not
    trespass by writing a verdict at a pinned place: collecting the label is the
    point, and the pin only forbids *training* on it.
    """
    keys = pinned(name)
    if not keys:
        return {"pinned_locations": 0, "checked_rows": len(train_rows), "ok": True}
    caught = [row for row in train_rows if place_of(row) in keys]
    if caught:
        raise AttributeRefused(
            f"{len(caught)} training row(s) sit on a location reserved to the {name} "
            f"evaluation side, e.g. batch {caught[0].get('batch')!r}. A blind slice is spent "
            f"the moment it trains — fix the split, never the pin."
        )
    return {"pinned_locations": len(keys), "checked_rows": len(train_rows), "ok": True}


__all__ = [
    "ATTRIBUTES",
    "NAMES",
    "REPEAT_AB",
    "SCHEMA",
    "SPIRAL",
    "Attribute",
    "AttributeRefused",
    "Resolution",
    "append",
    "assert_pin_holds",
    "attribute",
    "attribute_row",
    "batch_path",
    "check",
    "class_of",
    "classes",
    "eval_split_path",
    "pin_row",
    "pinned",
    "place_of",
    "read",
    "register",
    "registry",
    "registry_path",
    "resolve",
    "resolved",
    "row_dir",
    "row_paths",
    "split_recipe_path",
    "store_dir",
    "write_pin",
]
