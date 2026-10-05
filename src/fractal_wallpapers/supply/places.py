"""What a harvest found, as one flat file and one page a reader can open.

A harvest's places are spread across two stores: the walk ledger
(`<run>/walk.jsonl`, ten row kinds, the places as `candidate` rows with their
refinements appended later) and the location judge's sidecar
(`artifacts/curation/supply_scores.jsonl`, written by `curate score`). Neither is
something a reader should have to join by hand, so `harvest export` joins them
once into `<run>/locations.jsonl` and `harvest stats` summarises that per fractal
family with the best and worst places drawn. **The stores are only read.**

**A place is a location key, kept once.** It is kept when a candidate row's fate
is `survived`, with any adopted refinement applied (`ledgers.refined_of`): on a
scored harvest a gate survivor the location judge admitted, on a `--no-scoring`
harvest every gate survivor. Two survivors can be one place — two children of one
node proposed on the same frame — and the file holds the first; the second is
counted as a repeat and not as a second place, which is what the location judge's
sidecar does too, since it is keyed on the place. The judge's scores come from that
sidecar; a place `curate score` has not read yet is in the file with nulls.

`view` is relative to the run directory the file is written into, so the file names
no machine's paths and moves with its run.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

#: The flat file `export` writes, beside the run's own ledger.
EXPORT_NAME = "locations.jsonl"

#: The schema every exported row carries.
SCHEMA = 1

#: How many places each end of a family's ranking shows on the stats page.
ENDS = 4


def export_path(run_dir: Path) -> Path:
    return Path(run_dir) / EXPORT_NAME


def rows(run_dir: Path) -> list[dict]:
    """One joined row per kept place of the harvest at `run_dir`, in ledger order."""
    return _rows_and_repeats(run_dir)[0]


def _rows_and_repeats(run_dir: Path) -> tuple[list[dict], int]:
    """`(rows, repeats)`: a survivor whose place is already a row is a repeat."""
    from fractal_wallpapers.curation import intake
    from fractal_wallpapers.discovery import walk
    from fractal_wallpapers.supply import ledgers
    from fractal_wallpapers.supply.location import key_of_row, key_text
    from fractal_wallpapers.supply.partitions import partition_of_family

    ledger = Path(run_dir) / ledgers.LEDGER_NAME
    if not ledger.is_file():
        raise FileNotFoundError(
            f"{ledger} is not there: `harvest export` reads a harvest's own walk.jsonl. "
            f"Run `fractal-wallpapers harvest` first, or name the run with --out-dir."
        )
    roots = {
        row.get("root_id"): (row.get("provenance") or {}).get("channel") or row.get("source")
        for row in ledgers.rows(ledger, kind="root")
    }
    scores = intake.read_scores() if intake.scores_path().is_file() else {}
    views = walk.views_dir(run_dir)
    out = []
    seen: set[str] = set()
    repeats = 0
    for row in ledgers.admitted(ledger, admit=lambda held: held.get("fate") == "survived"):
        key = key_of_row(row)
        if key is None:
            continue
        text = key_text(key)
        if text in seen:
            repeats += 1
            continue
        seen.add(text)
        scored = scores.get(text) or {}
        image = row.get("image")
        out.append(
            {
                "schema": SCHEMA,
                "key": text,
                "partition": partition_of_family(row["family"]),
                "family": row["family"],
                "viewport": row["viewport"],
                "maxiter": row.get("maxiter"),
                "depth": row.get("depth"),
                "root_id": row.get("root_id"),
                "root_channel": roots.get(row.get("root_id")),
                "slot_channel": row.get("channel"),
                "origin": row.get("origin"),
                "refined": bool(row.get("framing")),
                "view": None if not image else (views / image).relative_to(run_dir).as_posix(),
                "walk_p_ge3": row.get("score"),
                "walk_p_ge4": row.get("score_great"),
                "p_ge2": scored.get("p_ge2"),
                "p_ge3": scored.get("p_ge3"),
                "p_ge4": scored.get("p_ge4"),
                "score_regime": scored.get("regime"),
                "score_view": scored.get("view"),
            }
        )
    return out, repeats


def export(run_dir: Path) -> tuple[Path, list[dict]]:
    """Write `<run>/locations.jsonl` whole and return `(path, rows)`."""
    held = rows(run_dir)
    path = export_path(run_dir)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in held:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path, held


def _found(run_dir: Path) -> dict:
    """`{partition: candidate rows the walk found}`, every fate."""
    from fractal_wallpapers.supply import ledgers
    from fractal_wallpapers.supply.partitions import partition_of_family

    counted: dict[str, int] = {}
    for row in ledgers.rows(Path(run_dir) / ledgers.LEDGER_NAME, kind="candidate"):
        partition = partition_of_family(row["family"])
        counted[partition] = counted.get(partition, 0) + 1
    return counted


def _quantiles(values: list[float]) -> dict | None:
    if not values:
        return None
    ordered = sorted(values)
    cuts = statistics.quantiles(ordered, n=4) if len(ordered) > 1 else [ordered[0]] * 3
    return {
        "min": round(ordered[0], 4),
        "q1": round(cuts[0], 4),
        "median": round(cuts[1], 4),
        "q3": round(cuts[2], 4),
        "max": round(ordered[-1], 4),
        "over_half": sum(1 for value in ordered if value > 0.5),
    }


def stats(
    run_dir: Path, out_dir: Path | None = None, bundle: Path | None = None
) -> tuple[dict, Path]:
    """Per-family counts, the location judge's score distribution, the best and worst.

    Written as `<out>/stats.json` and `<out>/index.html`, `<out>` defaulting to
    `<run>/stats/`. Ranks on the judge's `P(>=3)`, the number every floor in the
    project is a point on; an unscored family shows its counts and no ends.
    """
    from fractal_wallpapers import grid_page
    from fractal_wallpapers.paths import tracked_name

    held, repeats = _rows_and_repeats(run_dir)
    found = _found(run_dir)
    families: dict[str, dict] = {}
    for partition in sorted(set(found) | {row["partition"] for row in held}):
        mine = [row for row in held if row["partition"] == partition]
        scored = [row for row in mine if row["p_ge3"] is not None]
        ranked = sorted(scored, key=lambda row: (-float(row["p_ge3"]), row["key"]))
        families[partition] = {
            "found": found.get(partition, 0),
            "places": len(mine),
            "scored": len(scored),
            "p_ge3": _quantiles([float(row["p_ge3"]) for row in scored]),
            "p_ge4": _quantiles(
                [float(row["p_ge4"]) for row in scored if row["p_ge4"] is not None]
            ),
            "best": [row["key"] for row in ranked[:ENDS]],
            "worst": [row["key"] for row in ranked[-ENDS:]][::-1] if len(ranked) > ENDS else [],
        }
    record = {
        "schema": SCHEMA,
        "run": tracked_name(run_dir),
        "found": sum(found.values()),
        "places": len(held),
        "repeats": repeats,
        "scored": sum(1 for row in held if row["p_ge3"] is not None),
        "families": families,
    }
    directory = Path(out_dir) if out_dir is not None else Path(run_dir) / "stats"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "stats.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    by_key = {row["key"]: row for row in held}

    def tile(key: str, band: str) -> grid_page.Tile:
        row = by_key[key]
        return grid_page.Tile(
            picture=Path(run_dir) / row["view"] if row["view"] else None,
            caption=[
                ("P(>=3)", row["p_ge3"]),
                ("P(>=4)", row["p_ge4"]),
                ("width", row["viewport"].get("width")),
                ("root channel", row["root_channel"]),
            ],
            band=band,
        )

    # A scored column only where it says something places does not: on a run
    # `curate score` has read whole, the two are one number.
    split = any(block["scored"] != block["places"] for block in families.values())
    columns = ["family", "found", "places", *(["scored"] if split else [])]
    columns += ["median P(>=3)", "P(>=3) > .5", "P(>=4) > .5"]
    table = [columns]
    sections = []
    for partition, block in families.items():
        table.append(
            [
                partition,
                block["found"],
                block["places"],
                *([block["scored"]] if split else []),
                (block["p_ge3"] or {}).get("median"),
                (block["p_ge3"] or {}).get("over_half"),
                (block["p_ge4"] or {}).get("over_half"),
            ]
        )
        if block["best"]:
            sections.append(
                grid_page.Section(
                    f"{partition}: best {len(block['best'])} and worst {len(block['worst'])}",
                    note="ranked on P(>=3); the picture is the walk's gate render",
                    tiles=[tile(key, "best") for key in block["best"]]
                    + [tile(key, "worst") for key in block["worst"]],
                    legend=grid_page.legend("P(>=3)", "P(>=4)", "width", "root channel"),
                )
            )
    kept = f"{record['found']:,} candidates found, {record['places']:,} places kept"
    if repeats:
        kept += f" ({repeats:,} more survivors landed on a place already kept)"
    page = grid_page.write(
        directory / "index.html",
        "Harvest stats",
        [
            kept + f", {record['scored']:,} of them scored by the location judge (`curate score`).",
            "Scores are the location judge's P(>=3) and P(>=4) off supply_scores.jsonl.",
        ],
        [
            grid_page.Section("Per fractal family", table=table, legend=grid_page.legend(*columns)),
            *sections,
        ],
        bundle=bundle,
    )
    return record, page
