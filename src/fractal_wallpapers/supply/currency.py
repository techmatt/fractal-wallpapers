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

from fractal_wallpapers.cuts import Bar, Restatement

#: What one find of each class is worth. A class 4 is the unit.
CLASS_WEIGHT = {4: 1.0, 3: 0.1}

#: The pool both cuts below were volume-matched over at the 2026-08-20 location
#: flip. The same population `curation.floors` restated the junk floor against,
#: because three cuts on one head's scale restated over three different pools
#: would be three different claims about what a flip cost.
REFERENCE_POOL = (
    "the 28,072-location curation sidecar (artifacts/curation/supply_scores.jsonl), "
    "every row read through the canonical 640x360ss2 view its own stored score was "
    "taken off"
)

#: **The keeper floor**, and the reading that put it here. The one policy cut on
#: the run side: it decides what a walk *keeps*, so moving it moves the supply.
#:
#: It stood at `0.50` for the whole life of the retired head — the midpoint of a
#: probability, chosen as a height rather than measured. The regime-robust
#: retrain moved every probability under it, so the number was restated the only
#: way a supply cut can be restated without a fresh labelling: by holding the
#: **volume** fixed. What "worth keeping" means was not re-derived and is not
#: claimed to have been; what was held is how much of the standing supply the cut
#: keeps.
GOOD_FLOOR_RESTATED = Restatement(
    value=0.385,
    head_sha256="f8f805119a0ff9612b2076f0edafdb4125f0330b3fd48ace71336f93664851ba",
    method=(
        "volume matched on a fixed reference pool. The retired head's 0.50 passed 10,508 of "
        "28,072 canonical reads (37.43%); this is the candidate score that passes that same "
        "count — the 10,508th largest candidate read, 0.387151 — rounded DOWN to the next "
        "0.005, because a floor rounded up removes supply the cut it restates did not. "
        "Realized 10,529 passing (37.51%). NOT a calibration: no label was read here."
    ),
    reference_pool=REFERENCE_POOL,
    date="2026-08-20",
)

#: A scored frame is a keeper at or above this.
GOOD_FLOOR = GOOD_FLOOR_RESTATED.value

#: **The great cut**, on the probability of the top class, and it decides only
#: what a frame is *called* — a class 4 against a class 3, which the currency
#: weights ten to one.
#:
#: This one used to be a different kind of number from the floor: the head's own
#: natural rank cutpoint, 0.50, the midpoint of a scale, never calibrated per
#: family. It cannot be that any more and still be the same cut. The retrained
#: head puts far less mass at the top class, so its midpoint calls almost nothing
#: a 4, and a currency whose class-4 count collapsed at a head flip would have
#: re-priced every partition's deficit without a single new judgement. So it is
#: volume-matched like the two floors, and it has stopped claiming to be a
#: natural cutpoint: it is the height at which this head calls as many frames
#: great as the last one did. Still never per-family.
GREAT_CUT_RESTATED = Restatement(
    value=0.105,
    head_sha256="f8f805119a0ff9612b2076f0edafdb4125f0330b3fd48ace71336f93664851ba",
    method=(
        "volume matched on a fixed reference pool. The retired head's 0.50 on P(>=4) called "
        "3,034 of 28,072 canonical reads great (10.81%); this is the candidate score that "
        "calls that same count great — the 3,034th largest candidate P(>=4), 0.107595 — "
        "rounded DOWN to the next 0.005. Realized 3,062 (10.91%). The absolute height is low "
        "because the retrained head's top-class mass is low; it is a rank statement about "
        "this head and not a claim that these frames are 0.105-probable fours."
    ),
    reference_pool=REFERENCE_POOL,
    date="2026-08-20",
)

#: A keeper is *great* at or above this on the probability of the top class.
GREAT_CUT = GREAT_CUT_RESTATED.value


def good_floor_cut() -> Bar:
    """The keeper floor as the acting cut it is, stamped with the head it was read on.

    Built at call time and stamped with the sha the height was **measured** on
    rather than with whatever is shipped now, so the next location flip refuses
    here on its first call instead of admitting a different share of the supply
    under the same float.
    """
    return Bar(
        name="good_floor",
        value=float(GOOD_FLOOR_RESTATED.value),
        head="location",
        stamp=GOOD_FLOOR_RESTATED.head_sha256,
        basis=f"the keeper cut of the supply engine's currency: {GOOD_FLOOR_RESTATED}",
    )


def great_cut() -> Bar:
    """The great cut, stamped the same way and for the same reason."""
    return Bar(
        name="great_cut",
        value=float(GREAT_CUT_RESTATED.value),
        head="location",
        stamp=GREAT_CUT_RESTATED.head_sha256,
        basis=f"what separates a class 4 from a class 3 in the currency: {GREAT_CUT_RESTATED}",
    )


def passes_good_floor(score) -> bool:
    """THE keeper comparison, with a missing score reading as not passing.

    An unscored frame has no verdict to be kept on. Every admission, census count
    and supply check goes through this one function rather than through a stored
    class, which is what makes moving the floor a one-line change instead of a
    re-score of every ledger ever written.
    """
    return good_floor_cut().acts(score)


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
    return 4 if (great is not None and great_cut().acts(great)) else 3


def units_of(cls) -> float:
    """What one find of this class contributes to the currency."""
    return CLASS_WEIGHT.get(cls, 0.0) if cls is not None else 0.0


def currency_of(counts: dict) -> float:
    """`n4 + 0.1·n3` over a `{class: count}` tally."""
    return sum(CLASS_WEIGHT.get(int(cls), 0.0) * n for cls, n in counts.items())


__all__ = [
    "CLASS_WEIGHT",
    "GOOD_FLOOR",
    "GOOD_FLOOR_RESTATED",
    "GREAT_CUT",
    "GREAT_CUT_RESTATED",
    "REFERENCE_POOL",
    "currency_of",
    "good_class",
    "good_floor_cut",
    "great_cut",
    "passes_good_floor",
    "units_of",
]
