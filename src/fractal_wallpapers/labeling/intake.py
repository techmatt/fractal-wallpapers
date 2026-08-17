"""What a labeling page exported, and how it becomes rows nothing else is needed to read.

A finished-render sheet is cut somewhere untracked, its pictures are rendered
somewhere untracked, and the page that serves it is a file in a scratch
directory. **None of that may survive as part of what a label means.** A verdict
keyed on `u0137` is a verdict about a picture nobody can find once the sheet
directory is swept, and swept is what a scratch directory is for.

So this module is the seam: it reads the sheet's own row file, which carries each
unit's whole join beside its id, joins the export to it **by id, once, here**, and
writes rows that carry the join and nothing that points outward. After it has
run, the sheet, the pictures and the page are all disposable, and the store still
says exactly what a person said.

## The drop

A page writes what it exported to `labels/<head>.json` — the head's own name,
through [`store.export_path`]. [`write_export`] is the only writer of that file
and it refuses one shape: a payload that does not carry every unit the file
already holds. Everything else about a session is repeatable, and that one is
not.

## What reaching the store costs

* **Both counts are checked, in both directions.** Every exported unit has to be
  on the sheet, every candidate row has to be accounted for as written or already
  present, and the store is re-read afterwards and asked whether it now says what
  the export said. A reader that produced the rows and then certified them would
  agree with itself about a row it silently dropped.
* **Nothing is modified.** An ingest appends or it does nothing at all. A verdict
  that changed since the last ingest is a **new row**, resolved latest-wins by
  [`finished.resolve`], and the earlier one stays readable underneath it.
* **A second ingest of the same export is a no-op.** The current row for a
  picture already saying what the export says is the whole test — so the step is
  safe to re-run, which is the only reason a labeler ever re-runs it after
  finding a mistake.
* **Registration comes first.** [`finished.append`] refuses a batch nobody
  registered, so the flags that decide train from eval are on record before the
  first row exists rather than reconstructed after it.

## Only what a person acted on

The page prefills a head's own tier as a suggestion and exports only what the
labeler accepted or overrode. A unit absent from the export is absent from the
store: an unreviewed suggestion is not a verdict, and this step has no way to
turn one into one.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from fractal_wallpapers.labeling import finished, store
from fractal_wallpapers.labeling import registry as registry_module
from fractal_wallpapers.paths import writing_path
from fractal_wallpapers.supply.partitions import partition_of_family

#: The schema a sheet's manifest and row file carry.
SCHEMA = 1

#: Every part of the join a sheet row has to hand over. A sheet that is short one
#: of them cannot produce a row this repository will store, and finding that out
#: at the writer one row at a time is finding it out too late.
JOIN_KEYS = (
    "family",
    "viewport",
    "mode",
    "mode_params",
    "curve",
    "colormap",
    "recipe",
    "render",
)

#: How big an export may be. A labeling session is hundreds of units of two small
#: numbers each; anything past this is not one.
MAX_EXPORT_BYTES = 4 * 1024 * 1024


class IntakeError(ValueError):
    """An export, or a sheet, that cannot become rows — and guessing would be worse."""


# --------------------------------------------------------------------------- #
# The drop.
# --------------------------------------------------------------------------- #
def read_export(path: Path) -> dict[str, int]:
    """`{unit: score}` from a page's export, in either shape a page writes.

    A page writes `{"u0001": {"score": 3, "revealed": 0}}`; an older one writes
    `{"u0001": 3}`. Both are read, a null score is read as *not acted on* and
    dropped, and anything else is refused rather than coerced — a score that
    arrived as the string `"3"` is a page that changed under us.
    """
    path = Path(path)
    if not path.is_file():
        raise IntakeError(f"{path} does not exist; that is the file a page exports")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise IntakeError(f"{path} holds {type(document).__name__}, not an object of units")
    out: dict[str, int] = {}
    for unit, verdict in document.items():
        score = verdict.get("score") if isinstance(verdict, dict) else verdict
        if score is None:
            continue
        if isinstance(score, bool) or not isinstance(score, int):
            raise IntakeError(f"{path}: unit {unit!r} carries score {score!r}, which is not a tier")
        out[str(unit)] = score
    return out


def write_export(head: str, payload: dict) -> Path:
    """Write `head`'s drop, and refuse the one write that loses a verdict.

    A page exports everything it holds, so a payload is always a superset of the
    last one — unless the labeler's page lost its state, which is exactly when
    overwriting the file would throw away the only copy of an hour's work. So a
    payload missing a unit the file already carries is refused, and the page
    falls back to a download it can reconcile by hand.

    Written to a temporary and renamed into place, so the file is never the
    half-written one a killed process leaves.
    """
    path = store.export_path(head)
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if len(body.encode("utf-8")) > MAX_EXPORT_BYTES:
        raise IntakeError(f"{head}: an export of {len(body)} bytes is not a labeling session")
    incoming = {unit for unit, score in _scores(payload).items() if score is not None}
    if path.is_file():
        held = set(read_export(path))
        lost = sorted(held - incoming)
        if lost:
            raise IntakeError(
                f"{path.name} already carries {len(lost)} unit(s) this save does not, e.g. "
                f"{lost[:5]}. A page exports everything it holds, so a shorter one is a page "
                f"that lost its state — the drop is not overwritten with it."
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = writing_path(path)
    temporary.write_text(body + "\n", encoding="utf-8", newline="\n")
    temporary.replace(path)
    return path


def _scores(payload: dict) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise IntakeError(f"an export is an object of units, not {type(payload).__name__}")
    return {
        str(unit): (verdict.get("score") if isinstance(verdict, dict) else verdict)
        for unit, verdict in payload.items()
    }


# --------------------------------------------------------------------------- #
# The sheet.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Sheet:
    """A built sheet, read back: what it says about itself, and its rows."""

    name: str
    manifest: dict
    rows: list[dict]

    @property
    def head(self) -> str:
        return self.manifest["head"]

    @property
    def by_unit(self) -> dict[str, dict]:
        return {row["unit"]: row for row in self.rows}


def sheet_paths(path: Path) -> tuple[Path, Path]:
    """The manifest and the row file, from whichever of the three a caller names."""
    path = Path(path)
    stem = path.with_suffix("") if path.suffix in (".json", ".jsonl") else path
    return stem.with_suffix(".json"), stem.with_suffix(".jsonl")


def read_sheet(path: Path) -> Sheet:
    """Read a sheet back, having proved it can answer for every unit it holds."""
    manifest_path, rows_path = sheet_paths(path)
    for needed in (manifest_path, rows_path):
        if not needed.is_file():
            raise IntakeError(f"{needed} is missing; a sheet is a manifest and a row file")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA:
        raise IntakeError(f"{manifest_path}: schema {manifest.get('schema')!r}, expected {SCHEMA}")
    finished.head_of(manifest.get("head") or "")  # a sheet is cut for one judge, and names it

    rows: list[dict] = []
    seen: set[str] = set()
    with rows_path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            unit = row.get("unit")
            if not isinstance(unit, str) or not unit:
                raise IntakeError(f"{rows_path}:{number}: a sheet row must name its unit")
            if unit in seen:
                raise IntakeError(f"{rows_path}:{number}: unit {unit!r} appears twice")
            if not isinstance(row.get("batch"), str) or not row["batch"]:
                raise IntakeError(f"{rows_path}:{number}: unit {unit!r} names no batch")
            join = row.get("join")
            missing = [key for key in JOIN_KEYS if not isinstance(join, dict) or key not in join]
            if missing:
                raise IntakeError(
                    f"{rows_path}:{number}: unit {unit!r} carries no {', '.join(missing)}. A "
                    f"sheet row hands over the whole join or its verdict is about a picture "
                    f"nobody can rebuild once this file is swept."
                )
            seen.add(unit)
            rows.append(row)

    stated = manifest.get("units")
    if stated is not None and stated != len(rows):
        raise IntakeError(
            f"{manifest_path} says {stated} units and {rows_path.name} holds {len(rows)}"
        )
    if not rows:
        raise IntakeError(f"{rows_path} holds no units")
    return Sheet(name=manifest_path.stem, manifest=manifest, rows=rows)


# --------------------------------------------------------------------------- #
# The rows.
# --------------------------------------------------------------------------- #
def row_of(sheet: Sheet, unit: str, score: int, labeler: str, recorded_at: str | None) -> dict:
    """One store row, resolved through the sheet and carrying nothing that points at it.

    The unit id, the sheet's name and the tier the head suggested travel as
    provenance — nothing keys on them, and [`finished.render_key`] cannot see
    them. What the head suggested is the one fact about the page that is
    recoverable nowhere else once the sheet is gone, and it is the difference
    between "the labeler agreed" and "the labeler judged".
    """
    source = sheet.by_unit[unit]
    join = source["join"]
    family = join["family"]
    partition = partition_of_family(family)
    stated = join.get("partition")
    if stated is not None and stated != partition:
        raise IntakeError(
            f"unit {unit!r} says it is partition {stated!r} and its family is {partition!r}. "
            f"The family is the join; a disagreeing label on top of it is a second answer."
        )
    return finished.render_row(
        head=sheet.head,
        batch=source["batch"],
        score=int(score),
        family=family,
        viewport=join["viewport"],
        mode=join["mode"],
        mode_params=join["mode_params"],
        curve=join["curve"],
        colormap=join["colormap"],
        recipe_=join["recipe"],
        render=join["render"],
        origin=store.HUMAN,
        labeler=labeler,
        recorded_at=recorded_at,
        partition=partition,
        sheet=sheet.name,
        unit=unit,
        suggested=source.get("suggestion"),
    )


def rows_of(sheet: Sheet, export: dict[str, int], labeler: str, recorded_at=None) -> list[dict]:
    """Every exported verdict as a store row, or nothing at all.

    Built before a file is opened, so an export that names a unit the sheet does
    not hold leaves the store exactly as it was.
    """
    unknown = sorted(set(export) - set(sheet.by_unit))
    if unknown:
        raise IntakeError(
            f"{len(unknown)} exported unit(s) are not on this sheet, e.g. {unknown[:5]} — a "
            f"verdict whose unit cannot be found is a verdict about an unknown picture"
        )
    stamp = recorded_at or store.now()
    return [row_of(sheet, unit, export[unit], labeler, stamp) for unit in sorted(export)]


def already_says(current: dict, row: dict) -> bool:
    """Whether the store already says, of this picture, what this row says.

    The verdict is the tier, cast by whom — a human or a named rule — out of
    which population. A second person casting the same tier on the same picture
    from the same batch adds no verdict, and re-running an ingest is exactly that
    case, so this is what makes the step repeatable.
    """
    seen = current.get(finished.render_key(row))
    if seen is None:
        return False
    return (
        seen.get("score") == row.get("score")
        and seen.get("origin") == row.get("origin")
        and seen.get("batch") == row.get("batch")
    )


def classify(head: str, rows: list[dict]) -> dict[str, list[dict]]:
    """Split candidate rows into what the store does not have, has differently, and has."""
    current = finished.resolved(head).current
    out: dict[str, list[dict]] = {"fresh": [], "revised": [], "unchanged": []}
    for row in rows:
        key = finished.render_key(row)
        if key not in current:
            out["fresh"].append(row)
        elif already_says(current, row):
            out["unchanged"].append(row)
        else:
            out["revised"].append(row)
    return out


# --------------------------------------------------------------------------- #
# The step.
# --------------------------------------------------------------------------- #
def run(sheet: Path, labels=None, labeler: str = "", write: bool = False) -> dict:
    """Ingest one sheet's export. Returns what happened, or what would.

    `labels` defaults to the head's own drop, which is where a page saves and
    what a session is named after.
    """
    if not labeler:
        raise IntakeError("an ingest records who cast the verdicts; there is no default labeler")
    read = read_sheet(sheet)
    head = read.head
    export_file = Path(labels) if labels else store.export_path(head)
    export = read_export(export_file)
    if not export:
        raise IntakeError(f"{export_file} carries no scored unit; nothing to record")

    candidates = rows_of(read, export, labeler=labeler)
    if len(candidates) != len(export):
        raise IntakeError(
            f"{len(export)} exported verdicts produced {len(candidates)} rows; the join is "
            f"not one to one"
        )

    known = finished.registry(head)
    unregistered = sorted({row["batch"] for row in candidates} - set(known))
    if unregistered:
        raise IntakeError(
            f"these batches have no registration in the {head} store: {unregistered}. Register "
            f"a batch before its first row exists — afterwards, how its population was drawn "
            f"is answered from memory. See `fractal-wallpapers label register --head {head}`."
        )

    sorted_out = classify(head, candidates)
    writing = sorted_out["fresh"] + sorted_out["revised"]
    before = finished.resolved(head)

    report = {
        "head": head,
        "sheet": read.name,
        "export": str(export_file),
        "labeler": labeler,
        "units": {
            "on the sheet": len(read.rows),
            "exported": len(export),
            "not acted on": len(read.rows) - len(export),
        },
        "rows": {
            "fresh": len(sorted_out["fresh"]),
            "revised": len(sorted_out["revised"]),
            "already stored": len(sorted_out["unchanged"]),
            "to write": len(writing),
        },
        "by batch": {
            batch: {
                "rows": count,
                "anchored": registry_module.lookup(known, batch).anchored,
                "eval_only": registry_module.lookup(known, batch).eval_only,
                "score_unconditioned": registry_module.lookup(known, batch).score_unconditioned,
                "side": registry_module.lookup(known, batch).side,
            }
            for batch, count in sorted(Counter(row["batch"] for row in candidates).items())
        },
        "tiers": {
            str(tier): sum(1 for row in candidates if row["score"] == tier)
            for tier in finished.tiers(head)
        },
        "store before": before.summary(),
    }
    if not write:
        report["written"] = 0
        report["note"] = "dry run — pass --write to append these rows"
        return report

    written = 0
    for batch in sorted({row["batch"] for row in writing}):
        batched = [row for row in writing if row["batch"] == batch]
        finished.append(head, batched, known=known)
        written += len(batched)

    after = finished.resolved(head)
    if after.n_rows != before.n_rows + written:
        raise IntakeError(
            f"the {head} store held {before.n_rows} rows and holds {after.n_rows} after writing "
            f"{written}. The count is the only thing that proves nothing was dropped."
        )
    if after.n_unkeyed:
        raise IntakeError(f"{after.n_unkeyed} row(s) in the {head} store carry no render identity")
    disagreements = [
        row["unit"]
        for row in candidates
        if (after.current.get(finished.render_key(row)) or {}).get("score") != row["score"]
    ]
    if disagreements:
        raise IntakeError(
            f"{len(disagreements)} unit(s) do not read back at the tier they were exported at, "
            f"e.g. {disagreements[:5]}"
        )

    scored = after.scored()
    train = [row for row in scored if not registry_module.lookup(known, row["batch"]).eval_only]
    report["written"] = written
    report["store after"] = after.summary()
    report["pin"] = finished.assert_pin_holds(head, train)
    report["registry"] = registry_module.summary(known)
    return report


__all__ = [
    "JOIN_KEYS",
    "MAX_EXPORT_BYTES",
    "SCHEMA",
    "IntakeError",
    "Sheet",
    "already_says",
    "classify",
    "read_export",
    "read_sheet",
    "row_of",
    "rows_of",
    "run",
    "sheet_paths",
    "write_export",
]
