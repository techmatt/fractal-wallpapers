"""What "the same location" means, in one place.

The standing deficit reads two populations — the labels a human wrote and the
finds a walk recorded — and it has to know which rows of the two are *the same
picture*, because a human verdict takes precedence over a machine one and cannot
if the two sides key locations differently. So there is one identity, here, and
every side reaches it through this module rather than building a join tuple of
its own. A precedence rule keyed on anything else is a third opinion about what
the same location is, and the failure it produces — a location counted twice, at
a weight nobody chose — is invisible in every report downstream.

**A location is its family *and* its frame.** Two Julia views at the same
coordinates with different `c` are different fractals; a record that keyed on the
viewport alone would silently merge them. Everything that decides what is drawn
is in the key, and the iteration cap deliberately is not — a re-render at a
different cap is the same location seen for longer.

**Coordinates normalize at the reader, never at the writer.** What a row holds is
the decimal string somebody wrote, and two writers spell one number several ways;
`0.50`, `0.5` and `5E-1` are one coordinate. Canonicalizing here means a row
written by an older or sloppier writer still lands on the right location, where
normalizing on the way in would mean trusting every writer to have done the same
thing and would leave rows that can never be reconciled afterwards. The
canonicalization is exact decimal arithmetic, not a float: at the depths this
project reaches, `f64` has already lost the digits that tell two locations apart.

**A row that cannot express a location gets `None`, and the caller counts it.**
It is never routed to a default, and it is never dropped silently: it is a row
the precedence rule cannot suppress, which is a possible double count, and the
population is how a reader knows the number is small.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from fractal_wallpapers.supply.partitions import partition_of_family

#: The family constants that are part of a location's identity, per family kind.
#: A constant absent from a record is the engine's own default and is recorded as
#: absent rather than guessed at — two rows that both omit it are still equal.
IDENTIFYING_CONSTANTS = {
    "mandelbrot": (),
    "multibrot": (),
    "julia": ("c",),
    "phoenix": ("c", "p", "z_prev"),
}


def canonical(value) -> str:
    """One decimal coordinate, canonicalized without losing a digit."""
    text = str(value)
    try:
        number = Decimal(text)
    except InvalidOperation:
        return text
    if number == 0:
        return "0"
    return format(number.normalize(), "f")


def _constant(value) -> tuple[str, ...] | None:
    if value is None:
        return None
    return tuple(canonical(part) for part in value)


def location_key(family: dict, viewport: dict) -> tuple:
    """THE identity of one location: what is drawn, and where it is framed.

    The partition leads the key so that two records which disagree about the
    family cannot collide on their coordinates alone.
    """
    kind = family.get("kind")
    constants = tuple(_constant(family.get(name)) for name in IDENTIFYING_CONSTANTS.get(kind, ()))
    return (
        partition_of_family(family),
        int(family.get("degree", 2)),
        constants,
        canonical(viewport["center_re"]),
        canonical(viewport["center_im"]),
        canonical(viewport["width"]),
    )


def key_of_row(row: dict) -> tuple | None:
    """The identity of a recorded row, or `None` if it does not carry one.

    **One adapter, not two**, and that is the point rather than a saving: the
    label side and the ledger side write a location the same way — the family
    with every constant and the viewport, on the row itself — so they can reach
    the identity through the same code. A label row that had to be parsed by a
    second reader would be a second definition of the same thing, and the two
    would eventually disagree about one row in a thousand, which is exactly how
    many rows the precedence rule is about.
    """
    family = row.get("family")
    viewport = row.get("viewport")
    if not isinstance(family, dict) or not isinstance(viewport, dict):
        return None
    try:
        return location_key(family, viewport)
    except (KeyError, TypeError, ValueError):
        return None


def key_text(key) -> str:
    """A location key as every store on disk spells it: JSON, so the join is exact.

    THE spelling, and there is one of it. A key is a tuple, and a store that
    wrote `str(key)` would write a Python tuple repr — `('mandelbrot', 2, (), …)`
    — where the sidecar and the embedding store write `["mandelbrot", 2, [], …]`.
    The two are different strings for one location, so a reader that took the
    wrong one gets **zero** matches and no error: `curation.distinct` keeps a
    place with no descriptor by rule, so the whole pre-selection silently becomes
    a no-op. That happened, in `discovery.reframing.distinct_places` over the
    reframing channel's 792 places, and it is why the spelling now has an owner
    instead of two implementations that agreed until they did not.
    """
    return json.dumps(key, ensure_ascii=False)


def text_of_row(row: dict) -> str | None:
    """[`key_text`] of a row's own identity, or `None` where it carries none."""
    key = key_of_row(row)
    return None if key is None else key_text(key)


__all__ = [
    "IDENTIFYING_CONSTANTS",
    "canonical",
    "key_of_row",
    "key_text",
    "location_key",
    "text_of_row",
]
