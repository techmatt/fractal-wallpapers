"""The walk's record: one file, one schema, and a fate on every row.

A discovery run's whole output is this ledger. It is JSONL — UTF-8, one object
per line, an integer `schema` from the first row — and it is append-only, so a
run that is killed halfway leaves a valid record of everything up to the kill.

Four things are decided here, and each of them is a decision the source project
paid to learn.

**Record and rank, never gate and forget.** A candidate the structural gates
refused is written down, with the gate that refused it. A walk that logged only
its survivors could never afterwards distinguish "the gates were too tight" from
"there was nothing there", and both of those look like a low yield. The rejects
are the larger half of the record and they are the half that says whether the
search is working.

**A row carries its full identity, not a reference to one.** The family with
every constant, and the viewport, on the same line — so a candidate is a
complete location and is never split across two files that have to be joined
later. For the dynamical families this is what makes the row mean anything at
all: two Julia views at the same coordinates with different `c` are different
fractals, and a row that recorded only the viewport would silently merge them.

**Coordinates are decimal strings, verbatim.** The string is the identity of a
location; `f64` is a lossy view of it that is good enough at today's depths and
will not be forever. Whatever was written is what is recorded, unaltered, and
[`fractal_wallpapers.discovery.nucleus.key_from_strings`] is what normalizes at
the *reader* — never by trusting the writer.

**Score fields are present and null.** The scorer arrives two slices from now.
`score` and `scorer` are on every candidate row today, holding `null` and the
name of the scorer that declined to have an opinion, so the head can be wired in
without a schema break and a mixed corpus stays readable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: The schema every row in this file carries, from the first row.
SCHEMA = 1

#: A candidate that passed every structural gate.
SURVIVED = "survived"

#: The fates a candidate can be recorded with. Everything but [`SURVIVED`] names
#: the gate that refused it — the *furthest* gate it reached, so the tally reads
#: as a picture of what the search is actually spending its refusals on.
FATES = (
    SURVIVED,
    #: Too much of the frame is the set's interior.
    "interior_cap",
    #: The whole frame escapes almost at once: far exterior, nothing in it.
    "instant_escape",
    #: No variety in the escape times: a flat wash.
    "flat",
    #: Detail present but confined to a corner; the frame is mostly empty.
    "occupancy_floor",
    #: Structurally fine, and the scorer declined to admit it.
    "not_admitted",
)

#: Why a node produced no child at all.
NODE_CAUSES = (
    "width_floor",
    "interior_cap",
    "instant_escape",
    "flat",
    "occupancy_floor",
    "no_candidate",
)


class Ledger:
    """An append-only JSONL record of one walk."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a", encoding="utf-8", newline="\n")
        self.counts: dict[str, int] = {}

    def write(self, kind: str, **fields: Any) -> dict:
        """Append one row. The schema and the kind are stamped here, not by
        callers, so no row can be written without them."""
        row = {"schema": SCHEMA, "kind": kind, **fields}
        self._handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._handle.flush()
        self.counts[kind] = self.counts.get(kind, 0) + 1
        return row

    def close(self) -> None:
        self._handle.close()

    def __enter__(self) -> Ledger:
        return self

    def __exit__(self, *exception) -> None:
        self.close()


def read(path: Path) -> list[dict]:
    """Read a ledger back, checking the schema on every row."""
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("schema") != SCHEMA:
                raise ValueError(
                    f"{path}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}"
                )
            rows.append(row)
    return rows


def viewport(center_re: str, center_im: str, width: str) -> dict:
    """A viewport, as the decimal strings that are its identity."""
    return {"center_re": str(center_re), "center_im": str(center_im), "width": str(width)}
