"""Which colours a picture is **of**. One definition, read everywhere.

A gallery that ships a hundred and fifty wallpapers has a colour distribution
whether anybody chose one or not, and gallery3's was measured: red at 2.10x
uniform in the pool before anything was seated, lime at 0.21x, and seating
amplified the skew rather than flattening it. Steering that needs one question
answered per picture — *what colour is this?* — and the answer has to be the same
answer at every site that asks, or a ceiling and a target read two different
features and argue about a picture neither of them is describing.

So this module is the whole of it, and there is exactly one rule:

```text
share      the codebook's 52-cell census of the picture, NEUTRALS DROPPED from
           the numerator and from the denominator, so the shares are of the
           picture's COLOUR rather than of its pixels.
dominant   a cell is dominant when it leads the picture and holds at least
           CELL_LEAD of the colour, OR when it holds CELL_ALONE on its own.
           A picture may be dominant in more than one cell, and in none.
family     the same rule one level up, over `codebook.rollup`, at FAMILY_LEAD
           and FAMILY_ALONE.
```

## Why the neutrals come out

Mean neutral share over gallery3's hundred and fifty is 0.210 and p95 is 0.443:
a fractal is mostly black more often than it is mostly anything else. Left in,
"the largest cell" would answer `black` for a third of the gallery and the
feature would be a brightness measure wearing a colour's name. Dropped, the one
green-dominant picture gallery3 shipped reads 0.270 green out of its colour and
0.209 out of its pixels. The first number is the one a person means by "that one
is the green one", and it is the number this module returns.

The cost of dropping them is real and is named here rather than discovered later:
a picture that is 80% black and 20% green is green-dominant by this rule. There
is **no floor** under the raw share, on Matt's call and with that picture as the
reference — a floor high enough to disqualify it would disqualify the only green
seat the gallery has.

## Why two thresholds and not one

`CELL_LEAD` alone would make dominance a pure argmax, and an argmax over 48 cells
is decided by noise the moment the top two are within a percent of each other.
`CELL_ALONE` alone would leave a picture whose largest cell holds 0.12 with no
dominant cell at all, which is most pictures. The pair says: *lead, and be worth
naming* — or *be so large that leading is beside the point*. The second clause is
what lets a picture carry two colours, which the two-colour maps this library is
full of really do.

The family thresholds are twice the cell ones because a family is four cells: a
hue holding a fifth of a picture's colour is the same claim about the picture as
a cell holding a tenth.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fractal_wallpapers.palettes import codebook

#: A cell is dominant if it **leads** and holds at least this much of the colour.
CELL_LEAD = 0.10

#: ...or if it holds this much, whether or not it leads. The second clause is what
#: lets one picture carry two colours.
CELL_ALONE = 0.15

#: The same pair one level up, over the twelve hue families. Twice the cell
#: numbers, because a family is four cells.
FAMILY_LEAD = 0.20
FAMILY_ALONE = 0.30

#: The rule, carried in every record that reads it so a reader never has to find
#: this module.
RULE = (
    "chromatic share per codebook cell, neutrals out of the numerator and the "
    f"denominator. A cell is DOMINANT when it is the largest chromatic cell and holds "
    f">= {CELL_LEAD}, or when it holds >= {CELL_ALONE} on its own; a picture may have "
    "more than one and may have none. The same rule over codebook.rollup families at "
    f"{FAMILY_LEAD} / {FAMILY_ALONE}. No floor on the raw share."
)


class DominanceError(RuntimeError):
    """A picture cannot be read for the colours it is of."""


@dataclass(frozen=True)
class Reading:
    """What one picture is of: the dominant names, and the shares behind them."""

    #: Dominant cells, largest first. Possibly empty.
    cells: tuple[str, ...]
    #: Dominant families, largest first. Possibly empty.
    families: tuple[str, ...]
    #: Every chromatic cell's share of the picture's colour, largest first.
    cell_shares: dict[str, float]
    #: The same, rolled onto the twelve hue families.
    family_shares: dict[str, float]
    #: What was dropped to get there: the neutral share of the pixels. Carried
    #: because it is the one number that says how much of the picture the reading
    #: is a reading OF, and a caller wanting a raw-share floor needs it.
    neutral: float

    def share_of(self, name: str) -> float:
        """One cell's or one family's share of the picture's colour; 0.0 for neither."""
        if name in self.cell_shares:
            return self.cell_shares[name]
        return self.family_shares.get(name, 0.0)

    def carries(self, name: str) -> bool:
        """Is this picture dominant in that cell or that family?"""
        return name in self.cells or name in self.families


def _dominant(shares: dict, lead: float, alone: float) -> tuple[str, ...]:
    """The names this share vector is dominant in, largest first.

    Order matters to the caller — a target's urgency is read off the most urgent
    name and a rejection names one — so the result is sorted by share and ties
    break on the name rather than on whatever order the dict arrived in.
    """
    if not shares:
        return ()
    ranked = sorted(shares.items(), key=lambda item: (-item[1], item[0]))
    top, top_share = ranked[0]
    out = {name for name, share in ranked if share >= alone}
    if top_share >= lead:
        out.add(top)
    return tuple(sorted(out, key=lambda name: (-shares[name], name)))


def of_shares(share: dict) -> Reading:
    """One picture's reading, off the codebook's 52-cell share vector.

    Takes the census rather than the picture so a caller already holding a share
    vector — a carrier table, a re-read of a recorded census — never re-decodes a
    JPEG to ask the same question.
    """
    kinds = {entry["swatch"]: entry["kind"] for entry in codebook.swatches()}
    chromatic = {name: float(value) for name, value in share.items() if kinds.get(name) == "hue"}
    neutral = sum(float(value) for name, value in share.items() if kinds.get(name) == "neutral")
    total = sum(chromatic.values())
    if total <= 0.0:
        return Reading((), (), {}, {}, float(neutral))
    cells_ = {name: value / total for name, value in chromatic.items() if value > 0.0}
    rolled = codebook.rollup(cells_)
    families_ = {name: value for name, value in rolled.items() if name != "neutral" and value > 0.0}
    return Reading(
        cells=_dominant(cells_, CELL_LEAD, CELL_ALONE),
        families=_dominant(families_, FAMILY_LEAD, FAMILY_ALONE),
        cell_shares=dict(sorted(cells_.items(), key=lambda item: (-item[1], item[0]))),
        family_shares=dict(sorted(families_.items(), key=lambda item: (-item[1], item[0]))),
        neutral=float(neutral),
    )


def of_block(block: dict) -> Reading:
    """One reading back out of the `colour` block a ledger row stores.

    The store's own spelling — `cells` and `families` — read back without a
    picture, so a pass that already has the row does not decode the JPEG to ask
    what it is dominant in. [`curation.candidate_ledger.colour_block`] is the
    other direction and the two round-trip on what the store keeps: the block
    holds the dominant names outright rather than re-deriving them, so a
    threshold that moved since the row was written cannot quietly re-decide it
    here.

    The **shares come back empty**, because the store stopped keeping them: they
    were 678 bytes a row and nothing had ever read one — the ceiling asks a
    reading for its `cells` and its `families` and for nothing else. A block
    written under the old shape still reads its shares back through here, which
    is why they are still named.
    """
    return Reading(
        cells=tuple(block.get("cells") or ()),
        families=tuple(block.get("families") or ()),
        cell_shares={str(k): float(v) for k, v in (block.get("cell_shares") or {}).items()},
        family_shares={str(k): float(v) for k, v in (block.get("family_shares") or {}).items()},
        neutral=float(block.get("neutral") or 0.0),
    )


def of_picture(picture: Path) -> Reading:
    """One picture's reading, at [`codebook.CENSUS_SIZE`], over its distinct colours.

    The picture is the **candidate render** everywhere this is asked at a seat:
    640x360 ss2, which decodes to the census size exactly. A release PNG at
    another geometry is a different population and its numbers are not
    interchangeable with these.
    """
    from fractal_wallpapers.palettes import space

    path = Path(picture)
    try:
        colours, counts = codebook.distinct(codebook.pixels(path))
    except codebook.CodebookError as refusal:
        raise DominanceError(str(refusal)) from refusal
    share = codebook.shares(space.oklab(colours), counts)
    names = codebook.names()
    return of_shares({names[index]: float(share[index]) for index in range(len(names))})


def family_of(cell: str) -> str | None:
    """Which hue family a chromatic cell rolls up into; `None` for a neutral one.

    The join a target needs: `--target dark_vivid_green=0.05` sets a target on the
    cell **and** on the family it belongs to, and that edge has to be read off the
    codebook rather than off the name's spelling.
    """
    for entry in codebook.swatches():
        if entry["swatch"] == cell:
            return None if entry["kind"] == "neutral" else str(entry["hue"])
    return None


def cells() -> tuple[str, ...]:
    """Every chromatic cell name, in the codebook's own order. Forty-eight of them."""
    return tuple(entry["swatch"] for entry in codebook.swatches() if entry["kind"] == "hue")


def families() -> tuple[str, ...]:
    """Every hue family name, in the codebook's own order. Twelve of them."""
    return tuple(name for name, _degrees in codebook.HUES)


__all__ = [
    "CELL_ALONE",
    "CELL_LEAD",
    "FAMILY_ALONE",
    "FAMILY_LEAD",
    "RULE",
    "DominanceError",
    "Reading",
    "cells",
    "families",
    "family_of",
    "of_block",
    "of_picture",
    "of_shares",
]
