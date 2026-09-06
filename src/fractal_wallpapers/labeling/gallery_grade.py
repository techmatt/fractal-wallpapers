"""THE gallery-grade store: how good a picture is GIVEN that it already clears the bar.

The two finished-render judges are gates. They answer *is this picture worth
keeping*, they answer it well, and at the good end of their own scale they
saturate: a shipping gallery's released rows have a median `P(>=3)` of 0.9999 and
a `P(>=4)` that separates the top of a page for a while and then does not. So the
solve gets a set of pictures it may seat and **no order inside it**, and every
choice made after the bar — which of two near neighbours takes the seat, which
seat a swap should give up — is made by a quantity that was never fitted to that
question.

This store is the corpus for a head that is. Its estimand is **conditional**:

```text
gallery_grade   1..4, given that the render judge already let this picture through
```

A 1 here is not a 1 over there. Over there a 1 is "this does not work"; here it is
"I am genuinely surprised this cleared the bar". The two scales share a shape and
share nothing else, and everything below exists to keep them apart.

## Three separations, and each of them is asserted rather than intended

**One — it is its own store, beside the two finished ones and never inside them.**
`data/gallery_grade/` with its own registry and its own rows, exactly as
[`fractal_wallpapers.labeling.attributes`] has its own. The name is not in
[`finished.HEADS`], so [`finished.head_of`] raises on it and every reader that
routes through that function — [`fractal_wallpapers.models.finished_train.population`]
first among them, which calls it on its own first line — cannot name this store at
all, let alone pool it. There is nothing to opt out of because there is no path in.

**Two — a row carries `grade` and no `score` key at all.** That absence is the
protection [`attributes`] established and the argument is the same one: every
quality reader in this repository reaches for `score`, so a store whose 1s and 4s
were written under that name would read as a corpus of tiers the day somebody
pooled the stores by field name — and here it would read as a *plausible* one,
because these really are 1s to 4s about finished pictures. [`check`] refuses a row
carrying `score`, so the confusion cannot be created rather than being merely
discouraged. The page still casts ordinals, because a drop is one number per unit
for every store there is; the ordinal becomes a `grade` once, at ingest.

**Three — no batch here is ever eval-eligible, and the store refuses one that
claims to be.** The population is model-selected twice over: every row cleared a
head's bar to be in the pool at all, and every row was then chosen or refused by
the solve's own constraints. A draw from it cannot be a base rate about anything,
so no slice of it can serve as an instrument. [`register`] refuses a registration
carrying `score_unconditioned` or `eval_only`, which are the two flags
[`registry.Registration.eval_eligible`] is derived from — so the derived answer is
`False` for every batch this store can hold. There is no pin file here and no
`assert_pin_holds`, because there is no side to protect.

## Keyed on the picture, like the finished stores and unlike the attribute one

A grade is a verdict about a render. One place carries a dozen of them and the
differences between them are exactly what this head has to learn, so latest-wins
resolves on [`finished.render_key`] — the same identity, through the same
function, so a picture is one picture across all three corpora. Nothing here
re-spells it.

## What a row carries beside its join

Four things the draw knew and the picture does not say:

* `seated` — whether the solve gave this row a seat in the record it was drawn
  from. The 1..4 scale is conditional on clearing the bar and not on being
  seated, so this is a covariate rather than a stratum boundary, and a fit that
  wants to correct for it needs it on the row.
* `refusal` — for an unseated row, the rule that refused it, in
  [`curation.solve`]'s own vocabulary. `null` on a seated row.
* `pre_stamp` — the picture the row's *candidate* was judged as was rendered
  before the autolevel operator stamped its identity, so a fresh render of it is
  a different picture. Flagged rather than dropped: dropping them would bias the
  population away from the places the older legs worked. See
  [`fractal_wallpapers.curation.recipes.stamp_of`] for what an absent stamp is.
* `reading` — what the shipped render judge says about the picture **this sheet
  rendered**, at label geometry. A column and never an order: a page ordered by
  that judge would inject the exact ordering this head exists to replace, and a
  row with no reading at all could not be compared against the gate it is
  conditional on.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from fractal_wallpapers.labeling import finished, store
from fractal_wallpapers.labeling import registry as registry_module
from fractal_wallpapers.paths import repo_root

#: The schema every gallery-grade row carries, from the very first row.
SCHEMA = 1

#: What this store is called, everywhere it is named. Not "tier" — that word is
#: the 1..4 quality scale's and this is a different estimand — and not "seat",
#: because a large minority of these rows were never seated.
NAME = "gallery_grade"

#: The scale a person casts on. The same four ordinals the quality corpora use and
#: emphatically not the same question; [`MEANINGS`] is what the difference is.
SCALE: tuple[int, ...] = (1, 2, 3, 4)

#: What each ordinal means, in the words the first sitting is being asked in.
#: There is no anchor sheet for this scale — this store has never held a row — so
#: the first sitting is what creates the anchors, and these sentences go onto the
#: page verbatim rather than being paraphrased into a rubric.
MEANINGS: tuple[str, ...] = (
    "genuinely surprised this cleared the bar, a clear reject",
    "just above the bar, acceptable but not ideal",
    "quite good, happy with it in the gallery, but not a favorite",
    "an absolute favorite",
)

#: What each button says. A phrase and not the sentence beside it, because the
#: four buttons sit in one row and four sentences is a row nobody can read — the
#: whole meaning is on the rubric above them, verbatim, and that is where a reader
#: of a built sheet finds what its ordinals meant.
BUTTONS: tuple[str, ...] = (
    "surprised it cleared",
    "just above the bar",
    "quite good",
    "an absolute favorite",
)

#: The sentence the page puts under the buttons. Built from [`MEANINGS`] rather
#: than restating them, so the page and the store cannot come to disagree about
#: what a 3 is.
RUBRIC = (
    "<b>Every one of these already cleared the render judge's bar.</b> The question is "
    "how good it is <i>given</i> that — not whether it works. "
    + " · ".join(
        f"<span class='s{ordinal}'>{ordinal}</span> {meaning}"
        for ordinal, meaning in zip(SCALE, MEANINGS, strict=True)
    )
)


class GradeRefused(ValueError):
    """A row that may not enter this store, or one in it that cannot be read."""


def words() -> dict[str, str]:
    """`{ordinal: what that button says}` — what the page prints on each key.

    [`BUTTONS`] and not [`MEANINGS`]: the page's default words are the quality
    scale's, and this store's ordinals do not mean those, so a sheet here ships
    its own map. The full sentence is on [`RUBRIC`], which is on the manifest.
    """
    return {str(ordinal): word for ordinal, word in zip(SCALE, BUTTONS, strict=True)}


def tiers() -> tuple[int, ...]:
    """The ordinals a labeler may cast here."""
    return SCALE


# --------------------------------------------------------------------------- #
# Where everything lives.
# --------------------------------------------------------------------------- #
def store_dir() -> Path:
    """Where this store's tracked records live."""
    return repo_root() / "data" / NAME


def row_dir() -> Path:
    return store_dir() / "rows"


def batch_path(batch: str) -> Path:
    return row_dir() / f"{batch}.jsonl"


def registry_path() -> Path:
    return store_dir() / "batches.jsonl"


def registry() -> dict[str, registry_module.Registration]:
    """Every batch registration here, fail-closed on anything absent."""
    return registry_module.read(registry_path())


def register(registration: registry_module.Registration) -> dict:
    """Register a batch. Refused when it contradicts what stands, or claims a side.

    The contradiction rule is [`registry.refuse_contradiction`]'s, shared with
    every other store. The second refusal is this store's own: a registration
    carrying `score_unconditioned` or `eval_only` is refused outright, because
    both are inputs to [`registry.Registration.eval_eligible`] and this population
    can never be an instrument — see the module docstring. An `anchored` batch is
    fine and is the ordinary case; it is the two that could make a batch eligible
    that have no true value here.
    """
    if not registration.batch:
        raise registry_module.RegistrationError("a registration must name its batch")
    if not registration.method:
        raise registry_module.RegistrationError(
            f"{registration.batch}: a registration must say how the population was drawn"
        )
    claimed = [name for name in ("score_unconditioned", "eval_only") if getattr(registration, name)]
    if claimed:
        raise GradeRefused(
            f"{registration.batch!r} claims {', '.join(claimed)}, and no batch in the "
            f"{NAME} store may. Every row here cleared a head's bar to be in the pool and "
            f"was then chosen or refused by the solve's own constraints, so the draw is "
            f"model-selected twice over and no slice of it is a base rate about anything. "
            f"Both flags feed `eval_eligible`; refusing them here is what makes the derived "
            f"answer False for every batch this store can hold."
        )
    registry_module.refuse_contradiction(registry(), registration)
    row = registration.row()
    if row["registered_at"] is None:
        row["registered_at"] = store.now()
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def eval_eligible() -> list[str]:
    """Every batch here a reader could mistake for an instrument. Always empty.

    Derived off the standing registrations rather than asserted, so it is a
    *reading of the file* and not a restatement of [`register`]'s refusal. A
    non-empty answer means a row reached the registry some other way.
    """
    return sorted(batch for batch, held in registry().items() if held.eval_eligible)


# --------------------------------------------------------------------------- #
# The row.
# --------------------------------------------------------------------------- #
def render_key(row: dict) -> tuple | None:
    """THE identity latest-wins resolves on: the picture, through the one owner of it.

    [`finished.render_key`] and not a second spelling — a picture is one picture
    across every corpus that holds verdicts about pictures, and two spellings of
    an identity agree until one of them is edited.
    """
    return finished.render_key(row)


def place_of(row: dict) -> tuple | None:
    """The location half of a row's identity. Nothing keys on it; readers group by it."""
    return finished.place_of(row)


def check(row: dict) -> dict:
    """Return `row`, having proved it is a gallery-grade row."""
    if row.get("schema") != SCHEMA:
        raise GradeRefused(f"schema {row.get('schema')!r}, expected {SCHEMA}")
    batch = row.get("batch")
    if not isinstance(batch, str) or not batch:
        raise GradeRefused("a row must name the batch it was drawn from")
    if "score" in row:
        raise GradeRefused(
            f"this row carries a `score`. A {NAME} verdict is conditional on the render "
            f"judge having already passed the picture, so its 1 is 'surprised this cleared "
            f"the bar' where a quality corpus's 1 is 'this does not work'. Every quality "
            f"reader in this project keys on `score`, and these numbers would read as tiers "
            f"the moment somebody pooled the stores by field name — plausibly, which is "
            f"worse than obviously. Write `grade`."
        )
    grade = row.get("grade")
    if grade is not None and grade not in SCALE:
        raise GradeRefused(
            f"grade {grade!r} is not one of {list(SCALE)} or null. This store is cast on one "
            f"scale and a verdict outside it is not a grade anybody could have meant."
        )
    origin = row.get("origin")
    if origin != store.HUMAN and not (
        isinstance(origin, str) and origin.startswith(store.RULE_PREFIX)
    ):
        raise GradeRefused(f"origin {origin!r}: a verdict is a human's or a stated rule's")
    if not isinstance(row.get("recorded_at"), str):
        raise GradeRefused("a row must carry the time it was recorded; it is how latest wins")
    if render_key(row) is None:
        raise GradeRefused(
            "this row carries no render identity — a gallery-grade verdict needs the place, "
            "the mode with its own settings and its curve, the map, and every knob of the "
            "palette pass on the same line, or it is a verdict about a picture nobody can "
            "rebuild"
        )
    return row


def grade_row(
    batch: str,
    grade: int | None,
    family: dict,
    viewport: dict,
    mode: str,
    mode_params: dict,
    curve: str,
    colormap: str,
    recipe_: dict,
    render: dict,
    origin: str = store.HUMAN,
    labeler: str | None = None,
    recorded_at: str | None = None,
    **extra,
) -> dict:
    """Build one gallery-grade row. The only shape the writer accepts.

    Shaped like [`finished.render_row`] on purpose — same join, same order, same
    names — so a reader holding one kind of row can read the other. The one field
    that differs is the one that must: `grade` where that carries `score`.
    """
    row = {
        "schema": SCHEMA,
        "batch": batch,
        "recorded_at": recorded_at or store.now(),
        "labeler": labeler,
        "origin": origin,
        "grade": grade,
        "family": family,
        "viewport": viewport,
        "mode": mode,
        "mode_params": mode_params,
        "curve": curve,
        "colormap": colormap,
        "recipe": recipe_,
        "render": render,
        **extra,
    }
    return check(row)


def append(rows: list[dict], known: dict | None = None) -> Path:
    """THE writer. Append checked rows to their batch's file and return its path."""
    if not rows:
        raise GradeRefused("nothing to append")
    batches = {row.get("batch") for row in rows}
    if len(batches) != 1:
        raise GradeRefused(f"one call writes one batch's rows, not {sorted(batches)}")
    batch = batches.pop()
    known = registry() if known is None else known
    if batch not in known:
        raise GradeRefused(
            f"batch {batch!r} has no registration in the {NAME} store. Register it before "
            "its first row exists — afterwards, how its population was drawn is answered "
            "from memory."
        )
    checked = [check(row) for row in rows]
    path = batch_path(batch)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for row in checked:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def row_paths() -> list[Path]:
    directory = row_dir()
    return sorted(directory.glob("*.jsonl")) if directory.is_dir() else []


def read(paths=None) -> list[dict]:
    """Every row of the store, schema-checked and stamped with where it came from."""
    paths = row_paths() if paths is None else [Path(path) for path in paths]
    out: list[dict] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if row.get("schema") != SCHEMA:
                    raise GradeRefused(
                        f"{path}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}"
                    )
                out.append({**row, "_file": path.name, "_line": number})
    return out


@dataclass
class Resolution:
    """What this store currently says, and what it could not say it about."""

    current: dict = field(default_factory=dict)
    n_rows: int = 0
    n_superseded: int = 0
    n_unkeyed: int = 0
    unkeyed: list = field(default_factory=list)

    def graded(self) -> list[dict]:
        """The resolved rows carrying a verdict, in render-key order.

        Ordered on the key's *text*, for [`finished.Resolution.scored`]'s reason:
        an absent family constant is recorded as absent, so two keys can hold a
        tuple and a `None` in one position and refuse to compare.
        """
        return [
            row
            for _key, row in sorted(self.current.items(), key=lambda item: repr(item[0]))
            if row.get("grade") is not None
        ]

    def counts(self) -> dict[str, int]:
        """`{grade: how many pictures currently carry it}`."""
        out: dict[str, int] = {}
        for row in self.graded():
            out[str(row["grade"])] = out.get(str(row["grade"]), 0) + 1
        return dict(sorted(out.items()))

    def summary(self) -> dict:
        graded = self.graded()
        return {
            "rows": self.n_rows,
            "renders": len(self.current),
            "graded": len(graded),
            "locations": len({place_of(row) for row in graded}),
            "seated": sum(1 for row in graded if row.get("seated")),
            "grades": self.counts(),
            "superseded": self.n_superseded,
            "unkeyed": self.n_unkeyed,
        }


def resolve(rows: list[dict], known: dict | None = None) -> Resolution:
    """THE resolution rule: per render, the latest row wins.

    Through [`store.resolution_order`] like every other corpus here, so the clock
    is one clock. The pin half of that order is inert by construction — no batch
    here can be `eval_only`, [`register`] refuses one — and it is still asked
    through the shared function rather than shortcut, so this store cannot come to
    resolve in an order of its own.
    """
    eval_only = store.eval_side_batches(known)
    resolution = Resolution(n_rows=len(rows))
    for row in sorted(rows, key=lambda row: store.resolution_order(row, eval_only)):
        key = render_key(row)
        if key is None:
            resolution.n_unkeyed += 1
            resolution.unkeyed.append(row)
            continue
        if key in resolution.current:
            resolution.n_superseded += 1
        resolution.current[key] = row
    return resolution


def resolved(paths=None) -> Resolution:
    """THE reader every consumer of this store routes through."""
    return resolve(read(paths), known=registry())


__all__ = [
    "BUTTONS",
    "MEANINGS",
    "NAME",
    "RUBRIC",
    "SCALE",
    "SCHEMA",
    "GradeRefused",
    "Resolution",
    "append",
    "batch_path",
    "check",
    "eval_eligible",
    "grade_row",
    "place_of",
    "read",
    "register",
    "registry",
    "registry_path",
    "render_key",
    "resolve",
    "resolved",
    "row_dir",
    "row_paths",
    "store_dir",
    "tiers",
    "words",
]
