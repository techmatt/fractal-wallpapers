"""τ_h: how good a cheap look has to be before the walk pays for a real one.

A walk sees every candidate at a small, fast resolution. Confirming one costs a
full render, and confirmation is where a run's time actually goes — so there is a
cut on the cheap score, per partition, and only what clears it is confirmed.

```text
τ_h(p) = the (1 − keep) quantile of the CHEAP score,
         over the frames whose CANONICAL score cleared the keeper floor
```

Read it as: *the cheap cut that retains `keep` of the frames a full render would
have kept*. At `keep = 0.90` the cut is chosen to shed a tenth of the good ones,
which is the price of not confirming everything.

**One population, and it is the walk's own outcomes.** A walk's candidates are
gate survivors, never selected on any cut, so the ledger is an untruncated sample
of the stream this cut is about to be applied to. The tempting second population —
frames that already cleared a *previous* run's τ_h — is left-truncated at a level
that differed per run, so its quantile is an upper bound of unknown tightness. A
smaller unbiased sample is a better estimator than a larger one with a bias nobody
can quantify.

**Below [`MIN_N`] good rows a partition is not cut at all.** It gets 0.0 and
confirms everything. Fail *open*, deliberately: a cut that is too high sheds
supply invisibly, where one that is too low shows up as render minutes in the
run's own telemetry. Five is the smallest count at which a tenth percentile is a
statement rather than a restatement of the minimum.

**Never pooled across families.** A partition with no arm of its own gets the
fail-open value, not a neighbour's number: a cut derived on other families' frames
is a number about a population that is not this one.

**Derived here, never transferred.** τ_h is a point on one scorer's probability
scale. A value carried in from another project's scorer is a number about nothing,
which is why this repository ships a deriver and an explicitly underived state
rather than a table of values.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.paths import repo_root
from fractal_wallpapers.supply import ledgers
from fractal_wallpapers.supply.currency import GOOD_FLOOR
from fractal_wallpapers.supply.partitions import ALL_PARTITIONS, partition_of_row

SCHEMA = 1

#: The fraction of canonically-good frames the cut is chosen to retain.
KEEP = 0.90

#: Below this many good rows a partition is not cut at all.
MIN_N = 5


def table_path() -> Path:
    """Where the derived cut lives."""
    return repo_root() / "data" / "supply" / "tau_h.json"


def quantile(values, q: float) -> float:
    """The `q` quantile of `values` by linear interpolation between order
    statistics.

    Written out rather than pulled from a numerical library, because this is the
    one place in the project that needs one and the definition matters: an
    estimator whose interpolation rule is whatever a dependency defaults to is an
    estimator nobody can reproduce.
    """
    ordered = sorted(float(v) for v in values)
    if not ordered:
        raise ValueError("no values")
    if len(ordered) == 1:
        return ordered[0]
    position = min(max(float(q), 0.0), 1.0) * (len(ordered) - 1)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def derive(
    rows,
    partitions=ALL_PARTITIONS,
    keep: float = KEEP,
    good_floor: float = GOOD_FLOOR,
    min_n: int = MIN_N,
) -> tuple[dict, dict]:
    """`(τ_h, detail)` — the cut per partition, and what it was derived from.

    A row is `{partition, cheap, canonical}`. Both arms must be present: a row
    with no canonical score cannot say whether it was good, and a row with no
    cheap score cannot contribute to a cut on cheap scores.
    """
    by_partition: dict = {}
    for row in rows:
        by_partition.setdefault(row["partition"], []).append(row)
    cut, detail = {}, {}
    for partition in partitions:
        pool = by_partition.get(partition, [])
        good = [
            float(row["cheap"])
            for row in pool
            if row.get("cheap") is not None
            and row.get("canonical") is not None
            and float(row["canonical"]) >= good_floor
        ]
        if len(good) >= min_n:
            cut[partition] = float(quantile(good, 1.0 - keep))
            source = "own"
        else:
            cut[partition] = 0.0
            source = "fail-open"
        detail[partition] = {
            "n_rows": len(pool),
            "n_good": len(good),
            "value": cut[partition],
            "source": source,
        }
    return cut, detail


def rows_from_ledgers(paths=None) -> list[dict]:
    """The derivation population, off this repository's own walks.

    A walk's thumbnail *is* the cheap arm — that is what the frontier is steered
    on — so a candidate row carries the cheap score directly. The canonical arm is
    the confirmation render's score, recorded on the row when a run confirmed it.
    A row with neither is a row from a run with no scorer, which is every run this
    repository has produced so far.
    """
    paths = ledgers.ledger_paths() if paths is None else [Path(p) for p in paths]
    out = []
    for path in paths:
        for row in ledgers.rows(path, kind="candidate"):
            out.append(
                {
                    "partition": partition_of_row(row),
                    "cheap": row.get("score"),
                    "canonical": row.get("score_canonical"),
                }
            )
    return out


def artifact(
    rows, partitions=ALL_PARTITIONS, keep: float = KEEP, min_n: int = MIN_N, scorer=None
) -> dict:
    """The derived table as the record it ships as."""
    cut, detail = derive(rows, partitions, keep=keep, min_n=min_n)
    derived = [p for p in partitions if detail[p]["source"] == "own"]
    return {
        "schema": SCHEMA,
        "_doc": (
            "The per-partition CHEAP cut: how good a node's cheap score has to look before "
            "the walk pays for a full-resolution confirmation of it. Derived from this "
            "repository's own walks by `fractal-wallpapers derive-tau-h`, never transferred."
        ),
        "scorer": scorer,
        "state": "DERIVED" if derived else "UNDERIVED",
        "state_note": (
            "Every partition is at the fail-open value and the walk confirms everything it "
            "reaches. An absent table and a table of zeros read identically to a run, and "
            "only the second one says which partitions were considered."
            if not derived
            else f"{len(derived)} of {len(partitions)} partitions carry a derived cut."
        ),
        "keep": keep,
        "good_floor": GOOD_FLOOR,
        "min_n": min_n,
        "n_rows": len(rows),
        "tau_h": cut,
        "detail": detail,
        "definition": (
            "good outcome = the canonical score clears good_floor; tau_h = the (1 - keep) "
            "quantile of the CHEAP score among those frames, per partition."
        ),
        "fail_open": (
            "A partition with fewer than min_n good rows gets 0.0 and confirms everything. "
            "There is no pooled cross-family fallback and there never was a defensible one — "
            "a cut derived on other families' frames is a number about a different "
            "population. Fail OPEN, which costs visible render minutes in a run's own "
            "telemetry, never invisible supply."
        ),
    }


def load(path: Path | None = None) -> dict:
    """The shipped cut, `{partition: τ_h}`."""
    path = table_path() if path is None else Path(path)
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise ValueError(f"{path}: schema {document.get('schema')!r}, expected {SCHEMA}")
    return {p: float(v) for p, v in (document.get("tau_h") or {}).items()}


__all__ = [
    "KEEP",
    "MIN_N",
    "SCHEMA",
    "artifact",
    "derive",
    "load",
    "quantile",
    "rows_from_ledgers",
    "table_path",
]
