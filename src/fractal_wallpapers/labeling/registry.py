"""What generated a batch — registered before the batch has any rows.

A **batch** is one population drawn by one method. Its registration says how the
rows were chosen, and that is the fact that decides whether anything measured on
them can be read as a rate about the world rather than a rate about a model.

**Registration comes first, and the writer enforces it.** A batch is registered
before its first label row exists, because the honest answer to "was a score in
the selection" is only available to the person drawing the population — after the
labels are in, the question is answered from memory. [`store.append`] refuses a
row whose batch is unregistered, so the ordering is a property of the store and
not of anybody's discipline.

**Reading fails closed.** A batch nobody registered resolves to
[`UNREGISTERED`]: not score-unconditioned, therefore not eval-eligible,
therefore train-side. An omission is safe; the only thing an omission cannot do
is put a population into the evaluation side by accident.

**Two independent facts, and eligibility follows from them.**

* `score_unconditioned` — was the *draw* free of any model score? This is the
  disqualifying property for an instrument, and the disqualifier is
  model-driven selection, not non-randomness: a systematic ladder or a
  parameter-space sweep is score-unconditioned, while "the top of the run's own
  ranked queue" is not.
* `anchored` — did the *page* serve a head's own verdict as a prefilled
  suggestion, or order the rows by its score? An anchored batch's labels measure
  agreement with that head, so they are train-side however the draw was made.
  The two halves genuinely come apart: a score-unconditioned draw served on an
  anchored page is the common case and is train-side.

`eval_eligible` is derived from both and never stored. A stored third fact is
how a table grows a row that contradicts itself.

**And one pin, which is not a third fact about the draw.** `eval_only` says a
batch was bought as an instrument and may never train — not for this generation
of heads and not for a later one. It is a decision made when the population was
commissioned rather than a property of how it was selected, it outranks whatever
the two flags above imply, and it exists because the failure it prevents is
silent: a blind slice that enters a training split is spent, every later reading
off it is inflated, and nothing is red.

**Eligibility is permission, not membership.** Which locations are *in* the
evaluation side is decided once, by a seeded draw over location groups, and
shipped as data — see [`fractal_wallpapers.labeling.split`].
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

#: The schema every registration row carries.
SCHEMA = 1


class RegistrationError(ValueError):
    """A registration that cannot be written, or a batch name that is not one."""


@dataclass(frozen=True)
class Registration:
    """One batch's classification. `method` is prose; the two flags are data."""

    batch: str
    method: str
    score_unconditioned: bool = False
    anchored: bool = False
    eval_only: bool = False
    why: str = ""
    registered_at: str | None = None

    @property
    def eval_eligible(self) -> bool:
        """Whether this batch's locations *may* be an evaluation instrument.

        Derived, never stored: an unconditioned draw judged on an unanchored
        page, and nothing else. A pinned batch is eligible whatever its draw —
        the pin is the decision, and it is the one that outranks.
        """
        return self.eval_only or (self.score_unconditioned and not self.anchored)

    @property
    def side(self) -> str:
        """The side this batch's locations may reach: `eval` or `train`."""
        return "eval" if self.eval_eligible else "train"

    def row(self) -> dict:
        return {
            "schema": SCHEMA,
            "batch": self.batch,
            "method": self.method,
            "score_unconditioned": self.score_unconditioned,
            "anchored": self.anchored,
            "eval_only": self.eval_only,
            "why": self.why,
            "registered_at": self.registered_at,
        }


#: What an unregistered batch resolves to. Biased by assumption, so train-side.
UNREGISTERED = Registration(
    batch="",
    method="unregistered",
    score_unconditioned=False,
    anchored=False,
    why=(
        "FAIL CLOSED. Being unconditioned is a claim about a draw, so it has to be made "
        "explicitly. A batch nobody registered is read as though a model chose its rows, "
        "which keeps it out of the evaluation side and costs nothing else."
    ),
)


def registration_of(row: dict) -> Registration:
    """One registration row, read back."""
    if row.get("schema") != SCHEMA:
        raise RegistrationError(f"registration schema {row.get('schema')!r}, expected {SCHEMA}")
    batch = row.get("batch")
    if not isinstance(batch, str) or not batch:
        raise RegistrationError("a registration must name its batch")
    return Registration(
        batch=batch,
        method=str(row.get("method", "")),
        score_unconditioned=bool(row.get("score_unconditioned")),
        anchored=bool(row.get("anchored")),
        eval_only=bool(row.get("eval_only")),
        why=str(row.get("why", "")),
        registered_at=row.get("registered_at"),
    )


def read(path: Path) -> dict[str, Registration]:
    """`{batch: Registration}` from a registration record.

    Later rows replace earlier ones for the same batch, which is what makes the
    file append-only: a registration corrected on the day it was found wrong
    leaves the original readable underneath it. Missing file is an empty
    registry, which is the state a fresh checkout is in.
    """
    path = Path(path)
    if not path.is_file():
        return {}
    out: dict[str, Registration] = {}
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                registration = registration_of(json.loads(line))
            except RegistrationError as complaint:
                raise RegistrationError(f"{path}:{number}: {complaint}") from complaint
            out[registration.batch] = registration
    return out


def lookup(registry: dict[str, Registration], batch: str) -> Registration:
    """The registration for `batch`, fail-closed on one nobody wrote down."""
    found = registry.get(batch)
    return UNREGISTERED if found is None else found


def eval_eligible(registry: dict[str, Registration], batch: str) -> bool:
    """Whether `batch` may contribute locations to the evaluation side."""
    return lookup(registry, batch).eval_eligible


def summary(registry: dict[str, Registration]) -> dict:
    """What is registered, split by the permission it carries."""
    eligible = sorted(b for b, r in registry.items() if r.eval_eligible)
    return {
        "batches": len(registry),
        "eval_eligible": eligible,
        "anchored": sorted(b for b, r in registry.items() if r.anchored),
        "eval_only": sorted(b for b, r in registry.items() if r.eval_only),
        "train_side": sorted(b for b, r in registry.items() if not r.eval_eligible),
    }


__all__ = [
    "SCHEMA",
    "UNREGISTERED",
    "Registration",
    "RegistrationError",
    "eval_eligible",
    "lookup",
    "read",
    "registration_of",
    "summary",
]
