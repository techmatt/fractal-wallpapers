"""A labeling sheet: the rows to be judged, rendered twice, in one directory.

A sheet is one cut, one manifest, one export. It is built into an untracked run
directory, served by [`fractal_wallpapers.labeling.server`], and comes back as a
single `labels.json` that [`record`] turns into store rows. Nothing else writes a
label.

## Two renders, and the labeler judges from the second

Every unit is rendered twice from the same location: once through the
**canonical** colormap, which is what a head will see, and once through the
**vivid** one, which is what a person judges from. A crushing palette makes good
material look dead, and the verdict is about the location, not about one unlucky
map — so the label is *cast* on the vivid render and *stored* against the
canonical one.

Both maps are read off the committed library in `data/palettes/` by name, and the
sheet refuses to build if either is missing. Neither is derived, fitted or
generated here: a sheet built against a colormap that existed only in the process
that built it is a sheet whose renders can never be reproduced.

## Correction mode is the design, and it is head-optional today

The intended sheet serves a head's own decode as a **prefilled suggestion**,
orders the page good→bad by its score, and offers a sweep that accepts every
suggestion below a chosen row behind a confirmation. That is what makes a
labeling hour worth more than a blind one once a head exists: the labeler spends
it on the rows the head got wrong.

No head exists in this repository yet, and the sheet says so rather than
pretending: with the null scorer there are no suggestions, no sweep, and no
score order — the page serves a **seeded shuffle**, which is unsorted with
respect to anything but is still reproducible, and is not draw order, because
draw order arrives in blocks and a block of one source's material drags the bar.

**A suggestion is not a label.** A sheet row carries no score field at all. The
only thing that becomes a label is what a person exported from the page, and
[`record`] refuses anything else, so an unreviewed suggestion cannot leave the
page as a verdict.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from fractal_wallpapers import engine
from fractal_wallpapers.labeling import store
from fractal_wallpapers.paths import colormap_dir

#: The schema every sheet row carries.
SCHEMA = 1

#: The map a head sees, and the one a label is stored against.
CANONICAL_COLORMAP = "twilight_shifted"

#: The map a person judges from.
VIVID_COLORMAP = "blue_orange"

#: What a sheet renders at. Big enough to judge as a wallpaper, small enough that
#: a thousand of them is an afternoon rather than a night.
SHEET_RESOLUTION = (1280, 720)
SHEET_SUPERSAMPLE = 2

MANIFEST_NAME = "sheet.json"
ROWS_NAME = "sheet.jsonl"


class SheetError(ValueError):
    """A sheet that cannot be built, served or recorded."""


def colormap(name: str) -> str:
    """Return `name`, having proved the committed library holds that map."""
    if not (colormap_dir() / f"{name}.json").is_file():
        raise SheetError(
            f"colormap {name!r} is not in the committed library ({colormap_dir().name}/). A "
            f"sheet renders through named, tracked maps only — a map that exists just in the "
            f"process that built the sheet cannot re-render a single one of its rows."
        )
    return name


def render_spec(row: dict, name: str, output: Path, resolution, supersample: int) -> dict:
    """The engine spec for one of a unit's two renders."""
    spec: dict = {
        "schema": 1,
        "family": row["family"],
        "viewport": row["viewport"],
        "resolution": list(resolution),
        "supersample": supersample,
        "mode": "smooth",
        "colormap": name,
        "colormap_dir": str(colormap_dir()),
        "output": str(output),
    }
    if row.get("maxiter") is not None:
        spec["maxiter"] = row["maxiter"]
    return spec


def render_pair(row: dict, canonical: Path, vivid: Path, resolution, supersample: int) -> dict:
    """Render one unit twice through the engine. The default renderer."""
    report = engine.render_report(
        render_spec(row, CANONICAL_COLORMAP, canonical, resolution, supersample)
    )
    engine.render_report(render_spec(row, VIVID_COLORMAP, vivid, resolution, supersample))
    return report


@dataclass
class Sheet:
    """A built sheet: where it is, what it holds, and how it was ordered."""

    directory: Path
    manifest: dict
    rows: list

    def path(self, name: str) -> Path:
        return self.directory / name


def units_from_ledger(path: Path, admitted_only: bool = False) -> list[dict]:
    """Sheet units from a walk ledger — the material a run actually found.

    Read through the supply engine's ledger reader, so "what a walk found" has
    one definition and a sheet cannot be cut from a population the census does
    not agree exists. What is passed in is the *predicate*, so the schema check,
    the row-kind filter and the reader stay shared.

    **The default population is everything the structural gates let through**,
    which is not the same as everything the supply engine admits. Admission also
    requires a score above the keeper floor, and no scorer in this repository
    produces one yet — so admitted material is empty today, and the survivors are
    exactly the population the first labels have to be collected from. Once a
    head exists, `admitted_only` cuts the sheet to what it kept.
    """
    from fractal_wallpapers.supply import ledgers

    predicate = ledgers.is_admitted if admitted_only else ledgers.passes_gates
    rows = ledgers.admitted(Path(path), admit=predicate)
    return [
        {
            "family": row["family"],
            "viewport": row["viewport"],
            "maxiter": row.get("maxiter"),
            "score": row.get("score"),
        }
        for row in rows
    ]


def units_from_batch(batch: str) -> list[dict]:
    """Sheet units from a batch already in the store — the material to re-judge.

    Routed through the canonical reader, so a location whose verdict has already
    been revised is served at its current verdict and not at its first one.
    """
    resolution = store.resolved([store.batch_path(batch)])
    return [
        {
            "family": row["family"],
            "viewport": row["viewport"],
            "maxiter": (row.get("render") or {}).get("maxiter"),
            "score": None,
        }
        for _key, row in sorted(resolution.current.items())
    ]


def order(units: list[dict], scorer_scores: list, seed: int) -> tuple[list[int], str]:
    """The page's order: good→bad where a head has an opinion, seeded shuffle otherwise."""
    if any(score is not None for score in scorer_scores):
        indices = sorted(
            range(len(units)),
            key=lambda i: (scorer_scores[i] is None, -(scorer_scores[i] or 0.0), i),
        )
        return indices, "score"
    indices = list(range(len(units)))
    random.Random(seed).shuffle(indices)
    return indices, "shuffle"


def build(
    units: list[dict],
    directory: Path,
    batch: str,
    seed: int = 0,
    scorer=None,
    resolution=SHEET_RESOLUTION,
    supersample: int = SHEET_SUPERSAMPLE,
    renderer=None,
) -> Sheet:
    """Build a sheet into `directory`. Returns what was written."""
    if not units:
        raise SheetError("no units: there is nothing to judge")
    canonical_map, vivid_map = colormap(CANONICAL_COLORMAP), colormap(VIVID_COLORMAP)
    renderer = render_pair if renderer is None else renderer

    if scorer is None:
        from fractal_wallpapers.discovery.scoring import NullScorer

        scorer = NullScorer()
    scores = [scorer.score(unit) for unit in units]
    indices, order_mode = order(units, scores, seed)

    directory = Path(directory)
    (directory / "canonical").mkdir(parents=True, exist_ok=True)
    (directory / "vivid").mkdir(parents=True, exist_ok=True)

    rows = []
    for position, index in enumerate(indices, start=1):
        unit = units[index]
        # The id is assigned AFTER the order is fixed, so it encodes the page
        # position and nothing else — not the draw, not the score, not the fate.
        name = f"u{position:04d}"
        canonical_png = directory / "canonical" / f"{name}.png"
        vivid_png = directory / "vivid" / f"{name}.png"
        report = renderer(unit, canonical_png, vivid_png, resolution, supersample) or {}
        rows.append(
            {
                "schema": SCHEMA,
                "unit": name,
                "batch": batch,
                "family": unit["family"],
                "viewport": unit["viewport"],
                "render": {
                    "resolution": list(resolution),
                    "supersample": supersample,
                    "mode": "smooth",
                    "colormap": canonical_map,
                    "maxiter": report.get("maxiter", unit.get("maxiter")),
                },
                "judged_from": vivid_map,
                "canonical": f"canonical/{name}.png",
                "vivid": f"vivid/{name}.png",
                "suggestion": None,
                "suggestion_score": scores[index],
            }
        )

    manifest = {
        "schema": SCHEMA,
        "batch": batch,
        "seed": seed,
        "order": order_mode,
        "scorer": getattr(scorer, "name", "null"),
        "units": len(rows),
        "canonical_colormap": canonical_map,
        "vivid_colormap": vivid_map,
        "resolution": list(resolution),
        "supersample": supersample,
        "built_at": store.now(),
    }
    directory.mkdir(parents=True, exist_ok=True)
    (directory / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    with (directory / ROWS_NAME).open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return Sheet(directory=directory, manifest=manifest, rows=rows)


def read(directory: Path) -> Sheet:
    """Read a built sheet back."""
    directory = Path(directory)
    manifest_path = directory / MANIFEST_NAME
    if not manifest_path.is_file():
        raise SheetError(f"{directory} holds no {MANIFEST_NAME}; it is not a sheet")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = []
    with (directory / ROWS_NAME).open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("schema") != SCHEMA:
                raise SheetError(f"{directory / ROWS_NAME}:{number}: schema {row.get('schema')!r}")
            rows.append(row)
    return Sheet(directory=directory, manifest=manifest, rows=rows)


def record(
    sheet: Sheet, labels: dict, labeler: str, known: dict | None = None, recorded_at=None
) -> list[dict]:
    """Turn a page's export into store rows and append them. Returns the rows.

    `labels` is what the page downloaded: `{unit: {"score": 1..4, "revealed":
    0|1}}`. Only units it names become labels — a unit the person never acted on
    contributes nothing, whatever the head suggested for it.
    """
    by_unit = {row["unit"]: row for row in sheet.rows}
    unknown = sorted(set(labels) - set(by_unit))
    if unknown:
        raise SheetError(
            f"{len(unknown)} exported unit(s) are not on this sheet, e.g. {unknown[:3]} — "
            f"a label whose unit cannot be found is a label about an unknown picture"
        )
    rows = []
    for unit in sorted(labels):
        verdict = labels[unit]
        score = verdict.get("score") if isinstance(verdict, dict) else verdict
        if score is None:
            continue
        source = by_unit[unit]
        rows.append(
            store.label_row(
                batch=source["batch"],
                score=int(score),
                family=source["family"],
                viewport=source["viewport"],
                render=source["render"],
                origin=store.HUMAN,
                labeler=labeler,
                recorded_at=recorded_at,
                judged_from=source.get("judged_from"),
                revealed=bool(verdict.get("revealed")) if isinstance(verdict, dict) else False,
            )
        )
    if not rows:
        raise SheetError("the export carries no scored unit; nothing to record")
    store.append(rows, known=known)
    return rows


__all__ = [
    "CANONICAL_COLORMAP",
    "MANIFEST_NAME",
    "ROWS_NAME",
    "SCHEMA",
    "SHEET_RESOLUTION",
    "SHEET_SUPERSAMPLE",
    "VIVID_COLORMAP",
    "Sheet",
    "SheetError",
    "build",
    "colormap",
    "order",
    "read",
    "record",
    "render_pair",
    "render_spec",
    "units_from_batch",
    "units_from_ledger",
]
