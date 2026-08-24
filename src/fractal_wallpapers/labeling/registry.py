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

**And a contradiction aborts.** Registering one batch twice is fine while both
rows say the same thing — re-running a registration step is how anybody finds out
it already ran — but a second row that disagrees about the method or the flags is
refused by [`read`], naming both rows. It used to win silently, which meant a
batch could change sides between two readings of one file with nothing red. An
omission fails closed; a contradiction cannot, because there is no safe side to
fail to when the file itself holds both answers.

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

**And what a registration deliberately does not carry lives beside the registries,
in `data/batch_caveats.md`.** The two flags answer one question about the draw and
one about the page; how a live population was actually assembled — a pair drawn to
share no locations, a draw over candidates rather than admissions, a row put in by
name — shapes what its rows can be asked and is prose rather than data. Nothing
here parses it, on purpose: a check that satisfied a flag would skip the paragraph.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

#: The schema every registration row carries.
SCHEMA = 1


class RegistrationError(ValueError):
    """A registration that cannot be written, or a batch name that is not one."""


class RegistrationContradiction(RegistrationError):
    """One batch registered twice, saying two different things about its draw.

    A named subclass, so a test can assert the reason rather than the wording, and
    a subclass of [`RegistrationError`] so every existing handler still catches it.
    """


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

    @property
    def claim(self) -> tuple:
        """What this registration *asserts* — the part a second row may not change.

        The method sentence and the three flags. `why` is the rationale beside the
        claim and `registered_at` is when it was written down, so neither is here:
        a re-registration stamps a fresh time by construction, and comparing on it
        would make "identical" unreachable.
        """
        return (self.method, self.score_unconditioned, self.anchored, self.eval_only)

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

    **A batch registered twice has to say the same thing twice.** An identical
    re-registration is a no-op — the file is append-only and re-running a
    registration step is the ordinary way anybody finds out it already ran — but a
    second row that *disagrees* is refused here, with both rows named, rather than
    silently winning.

    Silently winning is what it used to do, and it is the wrong default for this
    file specifically. A registration is the answer to "was a model score in the
    selection", it is written before the rows exist because afterwards it is
    answered from memory, and it is the input to which side a population may reach.
    A later row quietly moving a batch from `eval` to `train` — or the other way,
    which spends an instrument — is a change to what every number measured on that
    batch means, and nothing downstream reads the file twice to notice. If a
    registration really was wrong, the fix is to correct the row in place and say
    so in `why`: this store's append-only rule is about *labels*, whose originals
    are evidence, and a registration nobody can contradict has no evidence to
    preserve.

    Missing file is an empty registry, which is the state a fresh checkout is in.
    """
    path = Path(path)
    if not path.is_file():
        return {}
    out: dict[str, Registration] = {}
    seen: dict[str, int] = {}
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                registration = registration_of(json.loads(line))
            except RegistrationError as complaint:
                raise RegistrationError(f"{path}:{number}: {complaint}") from complaint
            batch = registration.batch
            standing = out.get(batch)
            if standing is not None and standing.claim != registration.claim:
                raise RegistrationContradiction(
                    f"{path}: {batch!r} is registered twice and the two rows disagree.\n"
                    f"  line {seen[batch]}: {_claim_line(standing)}\n"
                    f"  line {number}: {_claim_line(registration)}\n"
                    f"A registration says how a population was drawn and which side it may "
                    f"reach, and it is written before the rows exist for exactly that reason. "
                    f"Correct the row in place — do not append a second answer."
                )
            if standing is None:
                seen[batch] = number
                out[batch] = registration
    return out


def _claim_line(registration: Registration) -> str:
    """One registration's claim, for a refusal that has to show two of them."""
    return (
        f"method={registration.method!r} score_unconditioned="
        f"{registration.score_unconditioned} anchored={registration.anchored} "
        f"eval_only={registration.eval_only} -> {registration.side}"
    )


def refuse_contradiction(registry: dict[str, Registration], registration: Registration) -> None:
    """Raise if `registration` disagrees with the one already standing for its batch.

    The same rule [`read`] enforces, asked one step earlier — at the *writer*, so
    the contradicting row never reaches the file. Without this the read-side guard
    is a trap rather than a guard: the append succeeds, and every read of that
    registry afterwards raises until somebody edits the file by hand.
    """
    standing = registry.get(registration.batch)
    if standing is None or standing.claim == registration.claim:
        return
    raise RegistrationContradiction(
        f"{registration.batch!r} is already registered, saying something else.\n"
        f"  standing: {_claim_line(standing)}\n"
        f"  offered:  {_claim_line(registration)}\n"
        f"A registration is written before the rows exist because afterwards how a "
        f"population was drawn is answered from memory. If the standing row is wrong, "
        f"correct it in place and say so in `why` — do not append a second answer."
    )


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
    "RegistrationContradiction",
    "RegistrationError",
    "eval_eligible",
    "lookup",
    "read",
    "refuse_contradiction",
    "registration_of",
    "summary",
]
