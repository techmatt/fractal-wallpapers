"""The train/evaluation split — drawn once, shipped as data.

A split that is re-derived on demand moves every time the corpus grows, and a
holdout that moves is not a holdout: last month's number and this month's are
measured on different populations and the difference between them is unreadable.
So the split is drawn once, by a seeded draw over location groups, and the
evaluation side is **written down** — `data/labels/eval_split.jsonl`, one row per
location, and `data/labels/split.json` for the recipe that drew it.

## Three rules, in the order they bind

1. **A location already on the evaluation side stays there.** Re-deriving adds;
   it never releases. This is the pin, and [`fractal_wallpapers.labeling.pins`]
   is what enforces it downstream.
2. **A fresh group reaches the evaluation side only if every location in it is
   eval-eligible** — every contributing batch registered score-unconditioned and
   unanchored. A group with one biased member goes train entire. That costs
   eval-eligible material, and the cost is counted rather than worked around: the
   alternative is either a biased row inside the instrument or a group straddling
   the boundary, and both are worse than a smaller instrument.
3. **The draw is seeded and stops at the target share.** Groups are shuffled by
   the seed and taken whole until the evaluation side holds
   [`EVAL_SHARE`] of every labeled location.

## The share is a target, not a realization

There is no rule that says the eligible pool is big enough. When it is not, the
evaluation side takes all of it and the realized share is reported next to the
target it missed — a nominal 20% that realized 8% is a fact about the corpus and
the one number a reader has to have before quoting a confidence interval on
anything measured here.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from fractal_wallpapers.labeling import groups as group_module
from fractal_wallpapers.labeling import registry as registry_module
from fractal_wallpapers.labeling import store
from fractal_wallpapers.supply.location import key_of_row

#: The schema every row of the shipped evaluation side carries.
SCHEMA = 1

#: What share of the labeled corpus the evaluation side is drawn to hold.
EVAL_SHARE = 0.20

#: The seed the shipped split was drawn under. Recorded in `split.json` too; this
#: is the default a re-derivation reuses so that adding material does not reshuffle
#: what is already there.
SEED = 0

RULE = (
    "seeded draw over location groups: a group reaches the evaluation side only if every "
    "location in it is eval-eligible, groups are taken whole until the target share is met, "
    "and a location already pinned to the evaluation side is never released"
)


@dataclass
class Split:
    """One derivation: what is on the evaluation side, and what it cost."""

    #: `{location key: row}` for every location on the evaluation side.
    eval_rows: dict = field(default_factory=dict)
    #: `{location key: group id}` for the same, so the shipped record can say
    #: which group each pinned location was drawn as part of.
    group_of: dict = field(default_factory=dict)
    grouping: group_module.Grouping | None = None
    seed: int = SEED
    share: float = EVAL_SHARE
    n_locations: int = 0
    n_eligible: int = 0
    n_groups: int = 0
    n_eligible_groups: int = 0
    n_eval_groups: int = 0
    n_carried: int = 0
    n_demoted: int = 0
    straddling: list = field(default_factory=list)

    def realized(self) -> float:
        return (len(self.eval_rows) / self.n_locations) if self.n_locations else 0.0

    def recipe(self) -> dict:
        return {
            "schema": SCHEMA,
            "rule": RULE,
            "seed": self.seed,
            "target_eval_share": self.share,
            "realized_eval_share": round(self.realized(), 4),
            "locations": {
                "total": self.n_locations,
                "eval_eligible": self.n_eligible,
                "eval": len(self.eval_rows),
            },
            "groups": {
                "total": self.n_groups,
                "eval_eligible": self.n_eligible_groups,
                "eval": self.n_eval_groups,
                "largest": self.grouping.largest() if self.grouping else 0,
                "straddling": len(self.straddling),
            },
            "carried_forward": self.n_carried,
            "eligible_locations_demoted_by_a_group_mate": self.n_demoted,
        }


def derive(
    rows: list[dict],
    known: dict | None = None,
    seed: int = SEED,
    share: float = EVAL_SHARE,
    pinned: set | None = None,
) -> Split:
    """Draw the split over `rows` — the resolved label rows, one per location."""
    known = store.registry() if known is None else known
    pinned = set() if pinned is None else set(pinned)

    keys = [key_of_row(row) for row in rows]
    grouping = group_module.assign(rows)
    eligible = [
        key is not None and registry_module.eval_eligible(known, str(row.get("batch")))
        for row, key in zip(rows, keys, strict=True)
    ]

    split = Split(
        grouping=grouping,
        seed=seed,
        share=share,
        n_locations=sum(1 for key in keys if key is not None),
        n_eligible=sum(1 for flag in eligible if flag),
        n_groups=grouping.size(),
    )

    eligible_groups = [
        group
        for group, members in sorted(grouping.members.items())
        if all(eligible[index] for index in members)
    ]
    split.n_eligible_groups = len(eligible_groups)
    split.n_demoted = sum(
        1
        for group, members in grouping.members.items()
        if group not in set(eligible_groups)
        for index in members
        if eligible[index]
    )

    # Rule 1: everything already pinned stays, at unit granularity — a pinned
    # location whose group has since gained a biased member keeps its side, and
    # the group straddles on purpose rather than the instrument being spent.
    for index, (row, key) in enumerate(zip(rows, keys, strict=True)):
        if key is not None and key in pinned:
            split.eval_rows[key] = row
            split.group_of[key] = grouping.of_row[index]
            split.n_carried += 1

    # Rule 3: seeded draw over the eligible groups, whole groups, until the target.
    target = round(share * split.n_locations)
    drawn = list(eligible_groups)
    random.Random(seed).shuffle(drawn)
    for group in drawn:
        if len(split.eval_rows) >= target:
            break
        for index in grouping.members[group]:
            key = keys[index]
            if key is not None:
                split.eval_rows[key] = rows[index]
                split.group_of[key] = group
        split.n_eval_groups += 1

    on_eval = set(split.eval_rows)
    for group, members in sorted(grouping.members.items()):
        sides = {keys[i] in on_eval for i in members if keys[i] is not None}
        if len(sides) > 1:
            split.straddling.append(group)
    return split


def rows_of(split: Split) -> list[dict]:
    """The shipped evaluation side, sorted for stable diffs."""
    out = [
        {
            "schema": SCHEMA,
            "group": split.group_of.get(key),
            "batch": row.get("batch"),
            "family": row.get("family"),
            "viewport": row.get("viewport"),
        }
        for key, row in sorted(split.eval_rows.items(), key=lambda item: repr(item[0]))
    ]
    return out


def write(split: Split) -> tuple[Path, Path]:
    """Write the evaluation side and its recipe. Returns both paths."""
    members = store.eval_split_path()
    recipe = store.split_recipe_path()
    members.parent.mkdir(parents=True, exist_ok=True)
    with members.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows_of(split):
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    recipe.write_text(json.dumps(split.recipe(), indent=2) + "\n", encoding="utf-8")
    return members, recipe


def read(path: Path | None = None) -> list[dict]:
    """The shipped evaluation side, schema-checked."""
    path = store.eval_split_path() if path is None else Path(path)
    if not path.is_file():
        return []
    out = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("schema") != SCHEMA:
                raise ValueError(
                    f"{path}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}"
                )
            out.append(row)
    return out


def recipe(path: Path | None = None) -> dict:
    """The recipe the shipped split was drawn under, or `{}` before there is one."""
    path = store.split_recipe_path() if path is None else Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


__all__ = [
    "EVAL_SHARE",
    "RULE",
    "SCHEMA",
    "SEED",
    "Split",
    "derive",
    "read",
    "recipe",
    "rows_of",
    "write",
]
