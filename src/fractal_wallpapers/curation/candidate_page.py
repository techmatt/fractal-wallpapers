"""The candidate page: what a merge left in the pool, at a glance.

`curate candidate-ledger browse` writes it after a hunt or a mine has been merged.
It reads the candidate ledger and its score sidecar and draws **nothing**: the
pictures are the ones the legs already rendered, linked by relative path. Three
things are on it, which is what a person checking a pool for sanity asks first:

* **the pool's size** by mode and by fractal family — rows, rows the live render
  judge has scored, rows above the per-mode bar's height, and the median `P(>=4)`;
* **the best N** by the render judge's `P(>=4)`, with the gallery judge's
  `p_fine(>=4)` beside it where `gallery-grade score-pool` has read the row;
* **a seeded random N**, so the page shows the pool and not only its top.

It writes `summary.json` and `index.html` to `artifacts/curation/candidate_page/`
unless told otherwise; neither is a store anything reads back.
"""

from __future__ import annotations

import json
import random
import statistics
from pathlib import Path

from fractal_wallpapers import grid_page
from fractal_wallpapers.paths import Tiers, rehome, tracked_name, under

#: Where the page and its summary land unless a caller names somewhere else.
UNIT = "candidate_page"

#: How many tiles each of the two picture sections shows by default.
SHOWN = 24

#: The two tallies' columns after the first, as the page names them.
TALLY = ["pictures", "judged", "at the bar", "median wallpaper judge P(>=4)", "places drawn"]

#: The first column of each tally.
LABEL = {"mode": "mode", "partition": "family"}

#: A tile's caption labels.
CAPTION = ["wallpaper judge P(>=4)", "wallpaper judge P(>=3)", "gallery judge", "mode", "family"]


def out_dir() -> Path:
    """The page's directory. **The one accessor.**"""
    return under("curation", UNIT)


def _median(values) -> float | None:
    held = [float(value) for value in values if value is not None]
    return round(statistics.median(held), 4) if held else None


def build(
    best: int = SHOWN,
    sample: int = SHOWN,
    seed: int = 0,
    out: Path | None = None,
    log=print,
    bundle: Path | None = None,
):
    """Write the page and its summary. Returns `(page path, summary dict)`."""
    from fractal_wallpapers.curation import candidate_ledger, distinct, mode_policy, solve

    scores = candidate_ledger.scores_by_recipe(candidate_ledger.read_scores())
    fine = distinct.fine_scores()
    tiers = Tiers.current()
    held: list[dict] = []
    for row in candidate_ledger.stream():
        reading = scores.get(str(row["key"])) or {}
        held.append(
            {
                "key": str(row["key"]),
                "mode": mode_policy.routed_mode_of(row),
                "partition": str(row.get("partition")),
                "location": str((row.get("location") or {}).get("key")),
                "picture": row.get("picture"),
                "p_ge4": reading.get("p_ge4"),
                "p_ge3": reading.get("p_ge3"),
                "p_fine": fine.get(str(row["key"])),
            }
        )
    if not held:
        raise FileNotFoundError(
            f"the candidate ledger is empty ({tracked_name(candidate_ledger.rows_path())}). "
            f"A hunt and its merge fill it: `curate hunt run --name <leg>` then "
            f"`curate hunt merge --name <leg>`."
        )

    def tally(column: str) -> list[list]:
        groups: dict[str, list[dict]] = {}
        for row in held:
            groups.setdefault(row[column], []).append(row)
        table = [[LABEL[column], *TALLY]]
        for name in sorted(groups):
            rows = groups[name]
            table.append(
                [
                    name,
                    len(rows),
                    sum(1 for row in rows if row["p_ge4"] is not None),
                    sum(1 for row in rows if (row["p_ge4"] or 0.0) >= solve.Q4_BAR),
                    _median(row["p_ge4"] for row in rows),
                    len({row["location"] for row in rows}),
                ]
            )
        return table

    scored = [row for row in held if row["p_ge4"] is not None]
    top = sorted(scored, key=lambda row: (-float(row["p_ge4"]), row["key"]))[: int(best)]
    drawn = random.Random(int(seed)).sample(held, min(int(sample), len(held)))

    def tile(row: dict) -> grid_page.Tile:
        picture = rehome(row["picture"], tiers) if row["picture"] else None
        return grid_page.Tile(
            picture=picture,
            title=row["key"],
            caption=[
                ("wallpaper judge P(>=4)", row["p_ge4"]),
                ("wallpaper judge P(>=3)", row["p_ge3"]),
                ("gallery judge", row["p_fine"]),
                ("mode", row["mode"]),
                ("family", row["partition"]),
            ],
        )

    summary = {
        "schema": 1,
        "rows": len(held),
        "scored": len(scored),
        "fine_read": sum(1 for row in held if row["p_fine"] is not None),
        "places": len({row["location"] for row in held}),
        "q4_bar": solve.Q4_BAR,
        "by_mode": tally("mode")[1:],
        "by_family": tally("partition")[1:],
        "best": [row["key"] for row in top],
        "sample_seed": int(seed),
        "sample": [row["key"] for row in drawn],
    }
    directory = Path(out) if out is not None else out_dir()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    page = grid_page.write(
        directory / "index.html",
        "Candidate pool",
        [
            f"{len(held):,} candidates over {summary['places']:,} places; {len(scored):,} scored "
            f"by the render judge, {summary['fine_read']:,} read by the gallery judge "
            f"(`gallery-grade score-pool`).",
            f"The wallpaper judge is the render judge; the bar column counts pictures at or "
            f"over {solve.Q4_BAR:g}, the height a mode's own bar starts from.",
        ],
        [
            grid_page.Section(
                "Pool by mode", table=tally("mode"), legend=grid_page.legend("mode", *TALLY)
            ),
            grid_page.Section(
                "Pool by fractal family",
                table=tally("partition"),
                legend=grid_page.legend("family", *TALLY),
            ),
            grid_page.Section(
                f"Best {len(top)} by the wallpaper judge's P(>=4)",
                tiles=[tile(row) for row in top],
                legend=grid_page.legend(*CAPTION),
            ),
            grid_page.Section(
                f"A random {len(drawn)} (seed {int(seed)})",
                tiles=[tile(row) for row in drawn],
                legend=grid_page.legend(*CAPTION),
            ),
        ],
        bundle=bundle,
    )
    log(f"[candidates] {tracked_name(page)}")
    return page, summary
