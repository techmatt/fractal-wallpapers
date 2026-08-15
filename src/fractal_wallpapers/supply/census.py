"""The standing deficit: what each partition already holds, and what it is owed.

This is the demand side of the supply engine. It answers one question per
partition — *how far below its intended share of the release is this partition's
stock?* — and the allocator spends the clock on the answer.

## Stock is two legs, and a location belongs to exactly one of them

```text
stock(p) = Σ over LABELED   locations  currency(the human's class)
         + Σ over UNLABELED locations  DISCOUNT × currency(the machine's class)
```

The labeled leg alone was the whole rule for a long time, on the sound ground
that a class count from a scorer measures the scorer and not the family. The cost
was an allocator that could not see its own output: a run that finds fourteen
hundred locations and is never labelled moves the standing deficit by exactly
zero, so the next allocation reads that partition as empty and spends the clock
there again. The machine leg closes that loop, and the discount is what bounds
the damage if the scorer is wrong.

**Precedence, never addition, and it is the whole correctness argument.** The
labelled corpus and the walk ledgers *overlap* — a labelling sheet is cut out of
ledger rows, so a location can be both. Adding the two legs would count those
locations twice, at a weight nobody chose. A human label therefore suppresses the
machine leg for that location outright: where a human has looked, the scorer's
opinion contributes nothing. That is also the only reading under which the
discount means what it says.

**The discount is deliberately below the survival rate.** Roughly half of
machine-called keepers survive a human look, so a *fair* discount would be near a
half. [`MACHINE_STOCK_DISCOUNT`] is well under that on purpose: a
machine-filled partition must keep a mild standing appetite until human labels
re-anchor it, and the failure this fixes — a partition worked forever because
unlabelled supply is invisible — is much cheaper to have half-fixed than its
mirror, a partition retired on the scorer's own say-so. It is a coarse constant,
not an operating point: it is not per-partition and it is not derived against an
evaluation.

## The target is ratio-weighted, and the stock anchors it

```text
target(p) = anchor × ratio(p) / max(ratio),   anchor = the richest partition's stock
```

A uniform target would say that a pinned single-parameter plane and the degree-2
parameter plane are owed the same number of labels. They are not, and the release
mix already says so. The richest maximum-ratio partition lands at exactly zero
deficit, which is not a degenerate case here but the case the universal floor is
written for — the two rules meet cleanly instead of fighting.

**Both sides of the subtraction read the same stock.** Anchoring the target on
labels alone while subtracting labels-plus-machine would put two different
definitions of stock inside one deficit.

## Failing open

A ledger row whose location identity cannot be built still counts toward its
partition's machine stock, and the population is reported. Dropping real supply
over a missing field would understate a partition's stock and re-open exactly the
failure the machine leg fixes. The cost is that such a row cannot be *suppressed*
by a human label, so if it is also labelled it is counted twice — which is why
the number is a reported population and not a silence.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from fractal_wallpapers.paths import repo_root
from fractal_wallpapers.supply import currency as money
from fractal_wallpapers.supply import release_mix
from fractal_wallpapers.supply.ledgers import admitted_union
from fractal_wallpapers.supply.location import key_of_row
from fractal_wallpapers.supply.partitions import ALL_PARTITIONS, partition_of_row

#: What an unlabelled machine-scored location is worth against the standing
#: deficit, as a fraction of what the same class would be worth as a human label.
#: One flat constant across every partition and class — per-partition survival
#: rates exist, but they are measured per scorer, so nine of them would be nine
#: numbers to re-derive at every retrain in exchange for a second-order
#: correction to a coarse number.
MACHINE_STOCK_DISCOUNT = 0.2

#: The schema every label row carries.
LABEL_SCHEMA = 1

TARGET_RULE = (
    "ratio-weighted: target = anchor × ratio / max(ratio), anchor = the richest partition's "
    f"stock (labelled currency + {MACHINE_STOCK_DISCOUNT:g} × unlabelled machine currency)"
)


def label_dir() -> Path:
    """Where tracked label records live."""
    return repo_root() / "data" / "labels"


def label_rows(paths=None) -> list[dict]:
    """Every label row, from the tracked label records.

    A label row carries its whole join — the class *and* the complete render
    parameters — so a labelled example is never split across two files. Absent
    records are an empty corpus, which is this repository's normal state today
    and is reported as a zero rather than raising: a cold start is a state, not
    an error.
    """
    if paths is None:
        directory = label_dir()
        paths = sorted(directory.glob("*.jsonl")) if directory.is_dir() else []
    rows = []
    for path in paths:
        with Path(path).open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if row.get("schema") != LABEL_SCHEMA:
                    raise ValueError(
                        f"{path}:{number}: schema {row.get('schema')!r}, expected {LABEL_SCHEMA}"
                    )
                if row.get("score") is not None:
                    rows.append(row)
    return rows


@dataclass
class MachineStock:
    """The unlabelled machine-scored leg, per partition.

    `currency` is **undiscounted** — the raw `n4 + 0.1·n3` of the machine classes,
    in the same units as the labelled leg. The discount is applied by
    [`contribution`] and nowhere else, so "what the ledgers hold" and "what the
    deficit is allowed to read" are two numbers a reader can compare rather than
    one that has already been scaled.

    Every counter here is a population and not a percentage, because each one is a
    different way this leg can be quietly wrong: `n_labelled` is precedence doing
    its job (a suppressed row is not a lost row), `n_unclassed` is supply the
    scorer had no opinion about, and `n_unresolved` is the only genuinely bad one.
    """

    counts: dict
    currency: dict
    discount: float
    partitions: tuple
    n_admitted: int = 0
    n_labelled: int = 0
    n_unclassed: int = 0
    n_unresolved: int = 0
    ledgers: dict = field(default_factory=dict)
    union: dict = field(default_factory=dict)

    def contribution(self) -> dict:
        """THE discounted stock this leg contributes. The only place it multiplies."""
        return {p: self.discount * float(self.currency.get(p, 0.0)) for p in self.partitions}

    def summary(self) -> dict:
        return {
            "discount": self.discount,
            "currency": {p: round(self.currency.get(p, 0.0), 3) for p in self.partitions},
            "contribution": {p: round(v, 3) for p, v in self.contribution().items()},
            "counts": {p: self.counts.get(p, {}) for p in self.partitions},
            "admitted": self.n_admitted,
            "suppressed_by_label": self.n_labelled,
            "unclassed": self.n_unclassed,
            "unresolved": self.n_unresolved,
            "per_ledger": self.ledgers,
            "union": self.union,
        }

    @classmethod
    def empty(cls, partitions=ALL_PARTITIONS, discount: float | None = None) -> MachineStock:
        """A leg that holds nothing — explicit rather than `None`, so a zero
        machine contribution is a stated fact and never an unread default."""
        return cls(
            counts={},
            currency=dict.fromkeys(partitions, 0.0),
            discount=MACHINE_STOCK_DISCOUNT if discount is None else float(discount),
            partitions=tuple(partitions),
        )


@dataclass
class Census:
    """What each partition holds, and enough provenance to argue about it."""

    counts: dict
    currency: dict
    partitions: tuple
    sources: dict = field(default_factory=dict)
    labelled_keys: frozenset = frozenset()
    unkeyed_label_rows: int = 0
    machine: MachineStock | None = None

    def machine_leg(self) -> MachineStock:
        return self.machine if self.machine is not None else MachineStock.empty(self.partitions)

    def stock(self) -> dict:
        """THE effective stock the deficit reads: the labelled currency plus the
        machine leg's discounted contribution.

        Precedence has already been applied inside the machine leg, so this is a
        sum over disjoint sets of locations and not over two overlapping ones.
        """
        contribution = self.machine_leg().contribution()
        return {
            p: float(self.currency.get(p, 0.0)) + float(contribution.get(p, 0.0))
            for p in self.partitions
        }

    def summary(self) -> dict:
        stock = self.stock()
        return {
            "currency": {p: round(self.currency.get(p, 0.0), 3) for p in self.partitions},
            "counts": {p: self.counts.get(p, {}) for p in self.partitions},
            "weights": {str(k): v for k, v in money.CLASS_WEIGHT.items()},
            "sources": self.sources,
            "labelled_locations": len(self.labelled_keys),
            "unkeyed_label_rows": self.unkeyed_label_rows,
            "machine": self.machine_leg().summary(),
            "stock": {p: round(stock.get(p, 0.0), 3) for p in self.partitions},
        }


def label_currency(partitions=ALL_PARTITIONS, paths=None) -> Census:
    """Census the human-label currency per partition. Labels only, no machine leg.

    The same walk collects the location identities the machine leg is suppressed
    against. Derived here rather than in a second pass, because a precedence set
    built from a different walk of the corpus is a precedence set that can
    disagree with the currency it is supposed to take precedence over.
    """
    counts: dict = {p: Counter() for p in partitions}
    keys: set = set()
    unkeyed = 0
    rows = label_rows(paths)
    for row in rows:
        counts.setdefault(partition_of_row(row), Counter())[int(row["score"])] += 1
        key = key_of_row(row)
        if key is None:
            unkeyed += 1
        else:
            keys.add(key)
    return Census(
        counts={p: dict(c) for p, c in counts.items()},
        currency={p: money.currency_of(counts.get(p, {})) for p in set(partitions) | set(counts)},
        partitions=tuple(partitions),
        sources={"labels": len(rows)},
        labelled_keys=frozenset(keys),
        unkeyed_label_rows=unkeyed,
    )


def machine_stock(
    partitions=ALL_PARTITIONS,
    labelled_keys: frozenset = frozenset(),
    ledger_paths=None,
    discount: float | None = None,
) -> MachineStock:
    """The unlabelled machine-scored stock per partition, over the ledger union.

    The same reader the run side uses, so a location present in two ledgers is
    counted once and the deficit cannot be moved by re-registering a run's
    ledgers. A second walker would be a second definition of what supply exists.
    """
    rows, union = admitted_union(ledger_paths)
    counts: dict = {}
    labelled = unclassed = unresolved = 0
    for row in rows:
        key = key_of_row(row)
        if key is None:
            unresolved += 1
        elif key in labelled_keys:
            labelled += 1
            continue
        cls = money.good_class(row.get("score"), row.get("score_great"))
        if cls is None:
            unclassed += 1
            continue
        counts.setdefault(partition_of_row(row), Counter())[int(cls)] += 1
    return MachineStock(
        counts={p: dict(c) for p, c in counts.items()},
        currency={p: money.currency_of(counts.get(p, {})) for p in set(partitions) | set(counts)},
        discount=MACHINE_STOCK_DISCOUNT if discount is None else float(discount),
        partitions=tuple(partitions),
        n_admitted=len(rows),
        n_labelled=labelled,
        n_unclassed=unclassed,
        n_unresolved=unresolved,
        ledgers=union.pop("per_ledger", {}),
        union=union,
    )


def stock_census(
    partitions=ALL_PARTITIONS,
    label_paths=None,
    ledger_paths=None,
    discount: float | None = None,
) -> Census:
    """THE census the deficit reads: the labelled leg with the machine leg attached.

    One function, so the precedence set and the leg it suppresses are wired
    together in exactly one place.
    """
    census = label_currency(partitions, label_paths)
    census.machine = machine_stock(
        partitions, census.labelled_keys, ledger_paths, discount=discount
    )
    return census


def targets(stock: dict, partitions=ALL_PARTITIONS, ratios: dict | None = None) -> tuple:
    """`(target per partition, the anchor level)` under the release-mix ratios.

    `ratios` is read at call time so a change to the policy moves the next
    allocation; a table cached at import would keep a running walk on the mix it
    was launched with. A partition with no declared ratio raises rather than
    defaulting — a defaulted ratio gives it a plausible target nobody decided,
    and every read downstream would be about the default.
    """
    have = {p: float(stock.get(p, 0.0)) for p in partitions}
    anchor = max(have.values()) if have else 0.0
    ratios = release_mix.ratios(partitions) if ratios is None else ratios
    missing = [p for p in partitions if p not in ratios]
    if missing:
        raise release_mix.ReleaseMixError(f"no release-mix ratio for {missing}")
    top = max((float(ratios[p]) for p in partitions), default=0.0)
    if top <= 0:
        return dict.fromkeys(partitions, 0.0), anchor
    return {p: anchor * float(ratios[p]) / top for p in partitions}, anchor


def deficits(stock: dict, partitions=ALL_PARTITIONS, ratios: dict | None = None) -> dict:
    """Shortfall against the ratio-weighted target.

    Two properties worth stating: every deficit is non-negative without a clamp —
    a clamp would make the allocation depend on how many partitions happen to sit
    above their target — and the partition that sets the anchor lands at exactly
    zero, which is the case the universal floor exists to serve.
    """
    target, _anchor = targets(stock, partitions, ratios)
    return {p: max(0.0, target[p] - float(stock.get(p, 0.0))) for p in partitions}


__all__ = [
    "LABEL_SCHEMA",
    "MACHINE_STOCK_DISCOUNT",
    "TARGET_RULE",
    "Census",
    "MachineStock",
    "deficits",
    "label_currency",
    "label_dir",
    "label_rows",
    "machine_stock",
    "stock_census",
    "targets",
]
