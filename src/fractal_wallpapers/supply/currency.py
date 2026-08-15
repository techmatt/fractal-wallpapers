"""The currency: what a find is worth, and where the cuts are.

Everything the supply engine decides is denominated in one quantity, and it is
not images. An image nobody would hang is not supply, so the currency counts
*keepers*:

```text
currency(partition) = count(class 4) + 0.1 × count(class 3)
```

A class 4 is a picture worth releasing; a class 3 is worth a tenth of one. Ten to
one is coarse on purpose — it says a great find is an order of magnitude more of
the point than a good one, which is the whole shape of the judgement, and no
finer number is defensible.

The three readers that matter — the standing deficit, the in-run price, and the
readout — all weight a class 3 through this one table, because the deficit and
the price have to be denominated in the same thing or dividing one by the other
means nothing.

**A class is one cut, applied identically in every partition.** No probability is
ever compared across partitions: each scored frame is reduced to a class by cuts
that are the same number everywhere, and only the *counts* cross a partition
boundary. That bound is what lets a machine-scored find contribute to the deficit
at all — a count of classes is the same shape of object a human label
contributes, where a probability is a statement about the head that produced it.

**Below the floor there is no class.** A frame the run would not keep has no
verdict about *how* unkeepable it is, so [`good_class`] answers `None` rather
than 1 or 2. A row with no class contributes nothing, which is a different fact
from contributing zero and is counted as one.
"""

from __future__ import annotations

#: What one find of each class is worth. A class 4 is the unit.
CLASS_WEIGHT = {4: 1.0, 3: 0.1}

#: A scored frame is a keeper at or above this. The one policy cut on the run
#: side: it decides what a walk *keeps*, so moving it moves the supply.
GOOD_FLOOR = 0.50

#: A keeper is *great* at or above this on the probability of the top class. A
#: different kind of number from the floor — a head's own natural rank cutpoint,
#: never calibrated per family — and it decides only what a frame is called.
GREAT_CUT = 0.50


def passes_good_floor(score) -> bool:
    """THE keeper comparison, with a missing score reading as not passing.

    An unscored frame has no verdict to be kept on. Every admission, census count
    and supply check goes through this one function rather than through a stored
    class, which is what makes moving the floor a one-line change instead of a
    re-score of every ledger ever written.
    """
    return score is not None and float(score) >= GOOD_FLOOR


def good_class(score, great=None) -> int | None:
    """The class of a scored frame: `None` below the floor, `4` when it also
    clears the great cut, else `3`.

    `great` is the probability of the top class and is `None` for a head that
    does not estimate one — which is every head this repository has today, so
    every machine-classed find is a 3 until a head arrives that can say
    otherwise. That is a real answer and not a placeholder: a scorer that cannot
    tell a 4 from a 3 must not be allowed to guess, because the currency weights
    the two ten to one.
    """
    if not passes_good_floor(score):
        return None
    return 4 if (great is not None and float(great) >= GREAT_CUT) else 3


def units_of(cls) -> float:
    """What one find of this class contributes to the currency."""
    return CLASS_WEIGHT.get(cls, 0.0) if cls is not None else 0.0


def currency_of(counts: dict) -> float:
    """`n4 + 0.1·n3` over a `{class: count}` tally."""
    return sum(CLASS_WEIGHT.get(int(cls), 0.0) * n for cls, n in counts.items())


__all__ = [
    "CLASS_WEIGHT",
    "GOOD_FLOOR",
    "GREAT_CUT",
    "currency_of",
    "good_class",
    "passes_good_floor",
    "units_of",
]
