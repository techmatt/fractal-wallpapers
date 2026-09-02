"""What a judge's score becomes: four outcomes, and one frame of each.

A head returns probabilities. Nothing downstream acts on a probability — the walk
acts on *decisions*, and there are four of them, cut out of one scale by three
heights this repository already owns:

```text
P(≥3) < junk floor .................. refused     recorded, never walked from
junk floor ≤ P(≥3) < good floor ..... expandable  stood on, not booked
good floor ≤ P(≥3), P(≥4) < great ... find        supply, a class 3
P(≥4) ≥ great cut ................... exceptional a class 4, worth ten of a find
```

[`decision_of`] is a *composition* of the three owners and never a restatement:
`curation.floors.passes_junk_floor`, `supply.currency.passes_good_floor` and
`supply.currency.good_class`. Moving a height still moves it in one place, and
this module follows.

## The frames

The figure that shows this ladder needs one picture per outcome, and they have to
be pictures somebody can check. So they are drawn from **held-out human-labeled
rows** — the evaluation side of the split, which no head was trained on — of one
family, and each frame is that location's own canonical view: the same recipe,
the same geometry and the same map the head read it through, rendered rather than
copied out of a tile cache so a fresh clone can make the figure again.

**The human label is carried, not used to pick.** A frame's human class is
whatever the person said; the outcome is what the head decided. The figure is
about the second, and hiding the disagreements would be the one thing that made
it dishonest — so the sidecar puts both on every row.

**The pick inside an outcome is the median**, by `P(≥3)`, ties broken by the row
key. A typical member of the bucket rather than its best or its worst, chosen by
a rule rather than by eye, so re-running the command draws the same four frames.
"""

from __future__ import annotations

import json
from pathlib import Path

#: The four outcomes, in the order the ladder climbs.
REFUSED = "refused"
EXPANDABLE = "expandable"
FIND = "find"
EXCEPTIONAL = "exceptional"
DECISIONS = (REFUSED, EXPANDABLE, FIND, EXCEPTIONAL)

#: The schema the sidecar carries, from its first row.
SCHEMA = 1

#: What the figure's subtree is called under the regenerable tree, and what the
#: sidecar beside its frames is called. The directory is [`figure_dir`] and not a
#: constant: `under()` reads which tier that subtree is on, and a constant would
#: have to answer that at import time.
FIGURE_UNIT = ("figures", "judges_score_to_decision")
SIDECAR = "frames.jsonl"


def figure_dir() -> Path:
    """Where the figure's frames land when no directory is named.

    Through `under()` rather than a bare `Path("artifacts")`, which is what this
    was until 2026-09-02 — a path relative to the **shell's** working directory,
    which on a machine that has moved its hot root is a fourth place that is
    neither tier.
    """
    from fractal_wallpapers.paths import under

    return under(*FIGURE_UNIT)


class DecisionError(RuntimeError):
    """The frames cannot be drawn."""


def decision_of(score, great=None) -> str:
    """Which of the four a reading lands in.

    A missing score is [`REFUSED`], for the reason the keeper comparison already
    reads that way: an unscored frame has no verdict to be kept on. It is not a
    fifth outcome, because nothing downstream treats it as one.
    """
    from fractal_wallpapers.curation import floors
    from fractal_wallpapers.supply import currency

    if score is None:
        return REFUSED
    if not floors.passes_junk_floor(score):
        return REFUSED
    if not currency.passes_good_floor(score):
        return EXPANDABLE
    return EXCEPTIONAL if currency.good_class(score, great) == 4 else FIND


def heights() -> dict:
    """The three cuts, as the figure has to label them."""
    from fractal_wallpapers.curation import floors
    from fractal_wallpapers.supply import currency

    return {
        "junk_floor": floors.JUNK_FLOOR,
        "good_floor": currency.GOOD_FLOOR,
        "great_cut": currency.GREAT_CUT,
    }


def shipped_run(head: str = "location") -> str:
    """Which training run's read the shipped weights came from.

    Read out of `models/weights.json`, which is the one place that says what
    shipped — so the frames are drawn from the same head production uses rather
    than from whichever run last wrote a scores file.
    """
    from fractal_wallpapers.paths import repo_root

    manifest = json.loads((repo_root() / "models" / "weights.json").read_text(encoding="utf-8"))
    entry = (manifest.get("heads") or {}).get(head)
    if not entry or not entry.get("run"):
        raise DecisionError(
            f"models/weights.json names no run for the {head!r} head, so nothing says "
            f"which read of the evaluation side belongs to the shipped weights."
        )
    return str(entry["run"])


def held_out(head: str = "location", run: str | None = None) -> list[dict]:
    """Every evaluation-side row of the shipped head's read, human label included.

    The rows are the tracked scores file: one per held-out location, carrying the
    person's class, the head's probabilities and the whole join needed to render
    the place again.
    """
    from fractal_wallpapers.models import scoring

    path = scoring.scores_path(head, run or shipped_run(head))
    if not path.is_file():
        raise DecisionError(f"{path} is missing — no read, no frames")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return [row for row in rows if row.get("side") == "eval" and row.get("score") is not None]


def by_decision(rows: list[dict]) -> dict[str, list[dict]]:
    """The rows filed under the outcome the head's reading puts them in."""
    out: dict[str, list[dict]] = {name: [] for name in DECISIONS}
    for row in rows:
        out[decision_of(row.get("p_ge3"), row.get("p_ge4"))].append(row)
    return out


def coverage(rows: list[dict]) -> dict[str, dict[str, int]]:
    """How each partition's held-out rows spread across the four outcomes.

    What picking a family for the figure turns on: a family whose rows do not
    reach all four cannot show the ladder, and this is how that is checked rather
    than assumed.
    """
    out: dict[str, dict[str, int]] = {}
    for row in rows:
        counts = out.setdefault(row["partition"], dict.fromkeys(DECISIONS, 0))
        counts[decision_of(row.get("p_ge3"), row.get("p_ge4"))] += 1
    return out


def median_row(rows: list[dict]) -> dict:
    """The bucket's median row by `P(≥3)`, ties broken by the row key.

    The lower of the two middles on an even count, which is a choice and is stated
    rather than left to a floating-point average of two rows that do not average.
    """
    ordered = sorted(rows, key=lambda row: (float(row["p_ge3"]), int(row["location_id"])))
    return ordered[(len(ordered) - 1) // 2]


def chosen(rows: list[dict], partition: str) -> dict[str, dict]:
    """One row per outcome for one family, or a refusal naming what is missing."""
    members = [row for row in rows if row.get("partition") == partition]
    if not members:
        raise DecisionError(f"no held-out human-labeled rows in {partition!r}")
    filed = by_decision(members)
    empty = [name for name in DECISIONS if not filed[name]]
    if empty:
        raise DecisionError(
            f"{partition!r} has no held-out row the head calls {', '.join(empty)} — "
            f"it cannot show all four outcomes. Its spread is "
            f"{ {name: len(filed[name]) for name in DECISIONS} }."
        )
    return {name: median_row(filed[name]) for name in DECISIONS}


def frame_row(decision: str, row: dict, picture: Path, made: bool, view: dict) -> dict:
    """One frame's provenance: which row, what the person said, what the head read.

    `view` is the recipe the picture was drawn through, and it is on **every** row
    rather than in a header. A frame is a claim about a place read at one geometry
    through one map, and a sidecar whose rows named the place but not the reading
    would be four rows nobody could rebuild without knowing which command wrote
    them — the same reason every other record in this project carries its whole
    join on one line.
    """
    from fractal_wallpapers.paths import tracked_name

    return {
        "schema": SCHEMA,
        "decision": decision,
        "location_id": row["location_id"],
        "partition": row["partition"],
        "batch": row.get("batch"),
        "human_class": row["score"],
        "p_ge2": row.get("p_ge2"),
        "p_ge3": row.get("p_ge3"),
        "p_ge4": row.get("p_ge4"),
        "rank_score": row.get("rank_score"),
        "family": row["family"],
        "viewport": row["viewport"],
        "picture": tracked_name(picture),
        "rendered": made,
        "view": dict(view),
    }


def draw(
    partition: str,
    directory: Path | None = None,
    head: str = "location",
    run: str | None = None,
) -> dict:
    """Draw the four frames and write the sidecar. Returns what it wrote."""
    from fractal_wallpapers import locations
    from fractal_wallpapers.models import location_view

    run = run or shipped_run(head)
    rows = held_out(head, run)
    picks = chosen(rows, partition)

    directory = Path(directory) if directory is not None else figure_dir()
    directory.mkdir(parents=True, exist_ok=True)
    colormap = location_view.canonical_map()
    cyclic = location_view.cyclic_maps()
    view = location_view.summary(colormap)

    # The view cache is addressed by the digest of its own recipe and the figure's
    # frames are named for the outcome they show. Both, rather than one renamed
    # into the other: a renamed digest is a cache entry that can never be found
    # again, and a second run of this command would redraw all four.
    views = directory / "views"
    records = []
    for index, decision in enumerate(DECISIONS):
        row = picks[decision]
        place = {
            "family": row["family"],
            "viewport": row["viewport"],
            "maxiter": locations.maxiter_of({**row, "render": {}}),
        }
        drawn, made = location_view.render_view(place, colormap, cyclic, views)
        picture = directory / f"{index}_{decision}.jpg"
        picture.write_bytes(drawn.read_bytes())
        records.append(frame_row(decision, row, picture, made, view))

    sidecar = directory / SIDECAR
    sidecar.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
        newline="\n",
    )
    return {
        "partition": partition,
        "head": head,
        "run": run,
        "directory": str(directory),
        "sidecar": str(sidecar),
        "view": view,
        "heights": heights(),
        "frames": records,
    }


__all__ = [
    "DECISIONS",
    "EXCEPTIONAL",
    "EXPANDABLE",
    "FIGURE_UNIT",
    "FIND",
    "REFUSED",
    "SCHEMA",
    "SIDECAR",
    "DecisionError",
    "by_decision",
    "chosen",
    "coverage",
    "decision_of",
    "draw",
    "frame_row",
    "heights",
    "held_out",
    "median_row",
    "shipped_run",
]
