"""The shipped location head over a list of places somebody named.

Two things in this repository score locations, and both of them read a *ledger*:
`curate score`, which reads the bound harvest ledgers into curation's sidecar,
and `score-parity`, which takes a batch off one to check the render pool against
itself. Neither can be pointed at a list. So a question as ordinary as "what does
the judge make of these twelve frames" — the question behind every panel that
wants to print `P(≥3)` under a picture — had no command.

This is that command's half. It takes location records, renders each one's
canonical view where the cache does not already hold it, reads the batch through
[`fractal_wallpapers.discovery.scoring.LocationScorer`] — the same class a walk
scores with, so this is not a second judge — and writes one score row per
location.

## What a score row has to say about itself

A number off a head is meaningless without two facts, and both of them move.

* **Which artifact produced it.** `location` names a *slot*, not a model. The
  heads in that slot get retrained and re-shipped, and the floors that read them
  are restated at the flip — `GOOD_FLOOR` and `JUNK_FLOOR` both were, on the same
  day. So every row carries `head_sha256`: the sha256 of the artifact that was
  shipped when the row was written, the same stamp
  [`fractal_wallpapers.cuts.Restatement`] pins a cut to.
* **What picture it read.** One head reads three trained geometries and the whole
  point of that is that a verdict travels between them. Which one a row was read
  at is therefore provenance rather than semantics — but a file holding rows from
  two of them must never leave a reader guessing, so every row carries the regime
  and the digest of the recipe its picture was made from.

A row also carries its own join — the family with every constant and the
viewport — for the reason every store here does: a row keyed on an id whose
meaning lives in another file is orphaned the day that file moves.

## No opinion is an answer

A location whose view would not render gets a row with `error` set and no
probabilities, not a zero. A crashed render and a bad place are different facts,
and a figure that quoted the second when the first happened would be quoting a
number nobody produced.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers import locations

#: The schema every score row carries.
SCHEMA = 1


def read(path: Path) -> list[dict]:
    """One file of location scores, schema-checked."""
    rows = []
    path = Path(path)
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema") != SCHEMA:
            raise ValueError(f"{path}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}")
        rows.append(row)
    return rows


def score(
    rows: list[dict],
    *,
    out: Path,
    regime=None,
    device: str = "auto",
    workers: int = 1,
    batch_size: int = 64,
    views: Path | None = None,
    log=print,
) -> dict:
    """Read every location through the shipped head and write the score rows.

    `regime` is the geometry the pictures are read at, `None` being the deploy
    one. The head is told nothing about which it is: a score that means the same
    thing at two geometries is the property the retrain bought, and telling it
    would be measuring something else.

    Views are addressed by the digest of their own recipe, so a location scored
    twice at one regime is one file and one render — which is what makes a second
    pass over a manifest cost nothing.
    """
    from fractal_wallpapers.discovery import scoring

    if not rows:
        raise ValueError("no locations to score")

    scorer = scoring.LocationScorer(
        directory=views,
        workers=workers,
        device=device,
        batch_size=batch_size,
        regime=regime,
        log=log,
    )
    # The head reads a *view*, and the recipe for one names an iteration cap. A
    # record that did not state one is asked of the engine's policy here rather
    # than defaulted to a number, so the row says what the picture was drawn at.
    candidates = [
        {
            "family": row["family"],
            "viewport": row["viewport"],
            "maxiter": locations.maxiter_of(row),
        }
        for row in rows
    ]
    log(f"[score] {len(candidates)} location(s) at {scorer.regime_name}")
    readings = scorer.read(candidates)

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    scored = 0
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        for index, (row, candidate, reading) in enumerate(
            zip(rows, candidates, readings, strict=True)
        ):
            record = {
                "schema": SCHEMA,
                "index": index,
                "head": "location",
                # The artifact, not the slot. Heads move and floors are restated
                # at the flip; a score that could not name what produced it goes
                # quietly stale instead of loudly.
                "head_sha256": scorer.stamp(),
                "regime": scorer.regime_name,
                "view": scorer.summary()["view"],
                "view_name": reading.view,
                "family": row["family"],
                "viewport": row["viewport"],
                "maxiter": candidate["maxiter"],
                "score": reading.score,
                "score_great": reading.great,
                "probabilities": list(reading.probabilities),
                "error": reading.error,
            }
            if reading.error is None:
                scored += 1
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {
        "locations": len(rows),
        "scored": scored,
        "no_opinion": len(rows) - scored,
        "scorer": scorer.summary(),
        "wrote": str(out),
    }


__all__ = ["SCHEMA", "read", "score"]
