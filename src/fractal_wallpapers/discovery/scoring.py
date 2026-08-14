"""The seam a scorer will arrive through, and the scorer that is here now.

Two slices from now a trained head will judge candidate views, and the walk will
consult it twice: to *steer* — which survivors are worth expanding next — and to
*admit* — which survivors are worth recording as finds. Both of those are
questions about pictures, and nothing in this repository can answer them yet.

So the seam is built and the answer is null. [`NullScorer`] returns no score for
anything, which the walk reads as "structural gates only": survivors are
admitted because they survived, and the order they are expanded in is the order
the gates produced. That is a real policy, not a placeholder — it is exactly the
walk the source project ran before its own head existed, and it is what the
first labels will be collected from.

Two properties of the seam are worth stating, because they are what make the
later slice a change of one file rather than a change of the ledger:

* **A scorer sees a candidate, not a location.** It is handed the row the walk
  is about to record, thumbnail path included, and returns a number or `None`.
  It cannot move the frame, re-render it, or reject it on anything but the
  score, so a scorer swap cannot quietly change what the gates did.
* **`None` is a first-class answer and means "no opinion".** A candidate a
  scorer declines to score is admitted on the structural gates alone and sorted
  as if neutral. That is what keeps a partially-trained head from silently
  becoming a gate on the population it was never trained on — which is exactly
  how a queue matures and starves a whole channel of material.
"""

from __future__ import annotations

from typing import Protocol


class Scorer(Protocol):
    """What the walk asks of a judge of pictures."""

    #: Recorded on every row, so a ledger says which judge produced its scores.
    name: str

    def score(self, candidate: dict) -> float | None:
        """A number for this candidate, or `None` for no opinion.

        Higher is better. The scale is the scorer's own — the walk compares
        scores only against each other, and only within one run.
        """

    def admits(self, candidate: dict, score: float | None) -> bool:
        """Whether this candidate is a find worth recording as one.

        Called only for candidates that already passed every structural gate,
        so a scorer that admits everything is the structural-gates-only policy.
        """


class NullScorer:
    """No opinion about anything: structural gates decide, and nothing else.

    The walk that runs on this is a complete walk. It records what it finds,
    with every fate, and the record is what a scorer is later trained on — which
    is the only order these two things can be built in.
    """

    name = "null"

    def score(self, candidate: dict) -> float | None:
        del candidate
        return None

    def admits(self, candidate: dict, score: float | None) -> bool:
        del candidate, score
        return True
