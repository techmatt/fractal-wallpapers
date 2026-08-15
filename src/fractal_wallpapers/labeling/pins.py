"""The evaluation pin: a location on the evaluation side is on it, always.

An instrument is spent the moment it trains, and the failure is silent — the head
trains on it, every number read off it afterwards is inflated, and nothing is
red. So the pin is a constraint that outranks whatever a split pass decides, and
it lives in one module because "unconditionally, everywhere" across several
consumers means one owner.

**The pin is asserted at unit granularity, on the location coordinate — never on
a row id, a batch name or a file name.** That is the whole design. A location can
be drawn again tomorrow by a different batch, rendered at a different size, and
written under a fresh identifier; if the pin were keyed on any of those, the copy
would train while the original sat in the evaluation side, and the instrument
would be spent by a row that never named it. The coordinate is
`c`-inclusive — two Julia views at one viewport with different seeds are
different fractals and must not trade sides — and it is the same key the supply
census suppresses machine stock on, reached through the same adapter.

**[`pin`] and [`assert_eval`] are deliberately two functions.** `pin` corrects a
split and reports what it moved; `assert_eval` refuses a split that needed
correcting. A pass that never calls `pin` still dies at `assert_eval` rather than
passing quietly, and `n_moved` is worth a line in any report that prints it: it
means some other rule tried to train on an instrument, and which rule is worth
knowing.
"""

from __future__ import annotations

from fractal_wallpapers.labeling import split as split_module
from fractal_wallpapers.supply.location import key_of_row

EVAL = "eval"
TRAIN = "train"


class EvalPinViolation(AssertionError):
    """A pinned location reached the training side.

    `AssertionError`, so a pass that swallows its own exceptions still dies; a
    named subclass, so a test can assert the reason rather than the wording.
    """


def pinned(rows=None) -> set:
    """Every pinned location key, read off the shipped evaluation side.

    Read from the record rather than re-derived: a pin that is recomputed is a
    pin that moves when the corpus does, which is the one thing it exists not to
    do.
    """
    rows = split_module.read() if rows is None else rows
    keys = set()
    for row in rows:
        key = key_of_row(row)
        if key is not None:
            keys.add(key)
    return keys


def side_of(row: dict, keys: set | None = None) -> str:
    """Which side one row's location is on. The reading every consumer wants."""
    keys = pinned() if keys is None else keys
    key = key_of_row(row)
    return EVAL if key is not None and key in keys else TRAIN


def pin(sides: dict, keys: set | None = None, where: str = "") -> dict:
    """Force every pinned key in `sides` to the evaluation side, in place.

    The report is the point: silently correcting a split hides the fact that
    something wanted to train on an instrument.
    """
    keys = pinned() if keys is None else keys
    moved = []
    for key in keys:
        if key not in sides:
            continue
        if sides[key] != EVAL:
            moved.append({"key": repr(key), "was": sides[key]})
            sides[key] = EVAL
    return {
        "where": where,
        "pinned": len(keys),
        "present": sum(1 for key in keys if key in sides),
        "moved_to_eval": len(moved),
        "moved": moved[:20],
        "rule": "a pinned location is on the evaluation side unconditionally",
    }


def assert_eval(sides: dict, keys: set | None = None, where: str = "") -> dict:
    """Raise unless every pinned key present in `sides` is on the evaluation side."""
    keys = pinned() if keys is None else keys
    bad = [{"key": repr(key), "side": sides[key]} for key in keys if sides.get(key, EVAL) != EVAL]
    if bad:
        raise EvalPinViolation(
            f"[{where or 'split'}] {len(bad)} pinned location(s) landed on the training side, "
            f"e.g. {bad[:3]}. An instrument is spent the moment it trains — fix the pass, "
            f"never the pin."
        )
    return {"where": where, "pinned": len(keys), "present": sum(1 for k in keys if k in sides)}


__all__ = [
    "EVAL",
    "TRAIN",
    "EvalPinViolation",
    "assert_eval",
    "pin",
    "pinned",
    "side_of",
]
