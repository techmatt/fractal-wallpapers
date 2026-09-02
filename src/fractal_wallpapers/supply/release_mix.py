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

**There is no second kind of entry.** A row is a ratio and nothing else, and
every registered partition is served by the walk on the same terms. This table
carried an `externally_supplied` flag until 2026-09-02, on `phoenix:classic`
alone: it kept its ratio and lost the clock — no share, no floor, no floor carry,
no starvation alarm — on the ground that a job outside the walk supplied it. That
job never existed in this repository (`AUDIT_phoenix_classic_funnel`), so the
flag bought silence rather than accuracy: the partition was zero at every stage
from the walk onward and nothing reported it, because the flag also took it out
of the census that would have. The flag and its plumbing are gone rather than set
false, and what stands in their place is the ordinary machinery — a partition the
walk cannot feed *is* starved, and says so.
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
            f"leaves it registered, floored, censused and permanently starved, and every "
            f"report about it afterwards describes a decision nobody made."
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


def summary(partitions=ALL_PARTITIONS, path: Path | None = None) -> dict:
    """The whole policy as one record, for a run's config."""
    return {
        "ratio": ratios(partitions, path),
        "share": {p: round(v, 6) for p, v in shares(partitions, path).items()},
        "source": str((path or table_path()).name),
    }


__all__ = [
    "ReleaseMixError",
    "check_complete",
    "entries",
    "ratio_of",
    "ratios",
    "shares",
    "summary",
    "table_path",
]
