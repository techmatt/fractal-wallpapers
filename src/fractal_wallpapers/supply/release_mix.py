"""The release mix: one ratio table, shipped as data, read by everyone.

How much of a finished release should be each partition? That is a policy, it is
one sentence long — *the two degree-2 planes carry it, the higher degrees and
their twins are equal supporting families, classic phoenix is a garnish* — and it
belongs in exactly one place. It is [`data/supply/release_mix.json`], and this
module is the only reader.

**Ratios, never shares.** A ratio table survives a partition being registered or
retired: the shares renormalize on their own. A share table has to be re-summed
by hand every time and is silently wrong in between. The table also has to serve
consumers at completely different scales — a run's currency deficit is counted in
labels, a release's contents in pictures — and the only thing those agree on is
the *relative* intent. Each consumer anchors the ratios to its own scale; the
table never carries one.

**Completeness is checked in both directions, at every load.** A registered
partition with no ratio would be given a target of nothing and read downstream as
"that partition had no demand" — the silent default this whole layer exists to
refuse. A ratio for an unregistered partition is a decision that never reaches an
allocation, which reads as applied and is not, while quietly deflating every
other ratio.

**A ratio of zero is refused.** A partition that should get none of a release is
*retired* from the registry, not zeroed here: zeroing leaves it registered,
floored, censused, and permanently starved, and every report about it afterwards
describes a decision nobody made.

**Externally supplied is the special case, and it is not a zero ratio.** Classic
phoenix keeps its 0.2 — it is still that much of a release, and the intake still
weighs it at that — but no walk can produce a single classic look, because its
one supply channel is a standalone descent of the pinned plane. So it keeps its
ratio and its key everywhere, and loses only the clock: no share, no floor, no
floor carry, and no starvation alarm for a queue whose empty state is normal.
Before that flag existed, three separate readers each concluded the same wrong
thing from the same silence — the census reported a starved partition, the floor
reserved it a slice of every run, and the allocator allocated against a deficit it
could never close. All three were right about what they could see, and all three
were describing a job that was never going to run.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fractal_wallpapers.paths import repo_root
from fractal_wallpapers.supply.partitions import ALL_PARTITIONS

SCHEMA = 1


def table_path() -> Path:
    """Where the shipped ratio table lives."""
    return repo_root() / "data" / "supply" / "release_mix.json"


class ReleaseMixError(ValueError):
    """The ratio table and the partition registry do not describe each other."""


def check_complete(entries: dict, partitions=ALL_PARTITIONS) -> None:
    """Raise unless the table and the registry cover exactly each other, positively.

    Both arguments are read at call time so the guard is provably red by deleting
    either side, and so a test can hand it a broken pair without editing the file.
    """
    missing = [p for p in partitions if p not in entries]
    extra = [p for p in entries if p not in partitions]
    if missing or extra:
        raise ReleaseMixError(
            f"the release mix and the partition registry disagree — registered with no "
            f"ratio: {missing}; ratio for an unregistered partition: {extra}. Every "
            f"partition that can reach a release needs a declared share of it, and a ratio "
            f"for a partition nobody serves silently deflates every other ratio."
        )
    zeroed = sorted(p for p in partitions if not float(entries[p].get("ratio", 0.0)) > 0.0)
    if zeroed:
        raise ReleaseMixError(
            f"non-positive release-mix ratio for {zeroed}. A partition that should get none "
            f"of a release is RETIRED from the registry, not zeroed here — a zero ratio "
            f"leaves it registered, floored, censused and permanently starved. A partition "
            f"the walk cannot feed is marked `externally_supplied` instead, which keeps its "
            f"ratio and takes away only its share of the clock."
        )


@lru_cache(maxsize=1)
def _load(path: str) -> dict:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise ReleaseMixError(f"{path}: schema {document.get('schema')!r}, expected {SCHEMA}")
    entries = document.get("partitions") or {}
    check_complete(entries)
    return entries


def entries(path: Path | None = None) -> dict:
    """The table as `{partition: entry}`, verified. A copy, so no consumer can
    normalize or scale the policy in place for everyone else in the process."""
    loaded = _load(str(path or table_path()))
    return {p: dict(entry) for p, entry in loaded.items()}


def ratios(partitions=ALL_PARTITIONS, path: Path | None = None) -> dict:
    """`{partition: ratio}` over `partitions`, read at call time."""
    table = _load(str(path or table_path()))
    missing = [p for p in partitions if p not in table]
    if missing:
        raise ReleaseMixError(
            f"no release-mix ratio for {missing}. The target vector must not default: a "
            f"defaulted ratio reads downstream as a measured demand."
        )
    return {p: float(table[p]["ratio"]) for p in partitions}


def ratio_of(partition: str, path: Path | None = None) -> float:
    """One partition's ratio. Raises rather than defaulting."""
    return ratios((partition,), path)[partition]


def shares(partitions=ALL_PARTITIONS, path: Path | None = None) -> dict:
    """The ratios normalized to sum to one — the intended mix as fractions.

    Derived, never stored: a stored share table is wrong from the moment a
    partition is registered or retired, and the arithmetic is one line.
    """
    table = ratios(partitions, path)
    total = sum(table.values())
    return {p: v / total for p, v in table.items()} if total > 0 else dict.fromkeys(table, 0.0)


def is_externally_supplied(partition: str, path: Path | None = None) -> bool:
    """Whether this partition's supply comes from a job outside the walk.

    THE predicate. Every skip site imports it rather than testing for a partition
    by name, so a second externally-supplied partition is one table edit and no
    code change.
    """
    table = _load(str(path or table_path()))
    return bool((table.get(partition) or {}).get("externally_supplied", False))


def externally_supplied(partitions=ALL_PARTITIONS, path: Path | None = None) -> set:
    """The flagged subset of `partitions`."""
    return {p for p in partitions if is_externally_supplied(p, path)}


def summary(partitions=ALL_PARTITIONS, path: Path | None = None) -> dict:
    """The whole policy as one record, for a run's config."""
    return {
        "ratio": ratios(partitions, path),
        "share": {p: round(v, 6) for p, v in shares(partitions, path).items()},
        "externally_supplied": sorted(externally_supplied(partitions, path)),
        "source": str((path or table_path()).name),
    }


__all__ = [
    "ReleaseMixError",
    "check_complete",
    "entries",
    "externally_supplied",
    "is_externally_supplied",
    "ratio_of",
    "ratios",
    "shares",
    "summary",
    "table_path",
]
