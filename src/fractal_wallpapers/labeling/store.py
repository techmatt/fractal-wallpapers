"""THE label store: one writer, one reader, and the join on every row.

Everything this repository knows about human taste is in `data/labels/`, and
every read and write of it happens here. That is the whole point of the module:
a second reader is a second opinion about what a label *is*, and the two
disagree about one row in a thousand right when it matters.

## A label row carries its join

The class **and** the complete render parameters, on the same line — the family
with every constant, the viewport, and what was rendered from them. A label keyed
on an id whose meaning lives in another file is orphaned the day that file is
deleted, and the source project paid for that twice: three hundred and
seventy-nine hand labels there survive with their location manifests gone, and
they can never be re-attributed to the pictures they were verdicts on.

So a row is refused at the writer if its location identity cannot be built. That
is stricter than the reader, deliberately: the reader meets rows that already
exist and counts what it cannot key, while the writer meets rows that do not
exist yet and can simply refuse to create the problem.

## Append-only, with resolution at read time

An original is never modified. A verdict that changes is a **new row**, and the
canonical reader resolves latest-wins over a total order — `recorded_at`, then
the file name, then the line number. Nothing is rewritten, so the earlier verdict
stays readable underneath the later one, and any consumer can reconstruct what
the corpus said on a given day by reading past a date.

Latest-wins is keyed on the **location**, not on a row id: a re-render of a place
under a fresh identifier is the same place, and a store that let a fresh id carry
a fresh verdict alongside the old one would hold two live opinions about one
picture.

## The choke point

`tests/test_label_store.py` fails the build if any other module addresses
`data/labels` or opens a file under it. The supply census reads labels through
[`resolved`]; so does the rig; so does the split. Convention would have held for
about a month.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.labeling import registry as registry_module
from fractal_wallpapers.paths import repo_root
from fractal_wallpapers.supply.location import key_of_row

#: The schema every label row carries, from the first row.
SCHEMA = 1

#: The scores a human may cast. A 4 is a picture worth releasing and is the unit
#: of currency; a 3 is a genuine wallpaper; 1 and 2 are recorded and are worth
#: nothing. Four tiers on one scale — a 4 is not a separate head or a new floor.
SCORES = (1, 2, 3, 4)

#: What a row's `origin` says about who cast its score. Anything else is a rule
#: label and spells itself `rule:<rule_id>`, so a stated rule is never mistaken
#: for a human verdict.
HUMAN = "human"
RULE_PREFIX = "rule:"


class LabelError(ValueError):
    """A row that may not enter the store, or one already in it that cannot be read."""


def label_dir() -> Path:
    """Where every tracked label record lives."""
    return repo_root() / "data" / "labels"


def row_dir() -> Path:
    """Where the label rows themselves live, one file per batch."""
    return label_dir() / "rows"


def batch_path(batch: str) -> Path:
    """The file a batch's rows are appended to."""
    return row_dir() / f"{batch}.jsonl"


def registry_path() -> Path:
    """The batch registration record."""
    return label_dir() / "batches.jsonl"


def eval_split_path() -> Path:
    """The shipped evaluation side: one row per pinned location."""
    return label_dir() / "eval_split.jsonl"


def split_recipe_path() -> Path:
    """The recipe that drew the pin, and what it realized."""
    return label_dir() / "split.json"


def now() -> str:
    """The timestamp a fresh row is stamped with: ISO-8601, UTC, to the second.

    Sorted as text, which is why the offset is spelled `Z` and never `+00:00`:
    the total order the reader resolves on is a string comparison, and two
    spellings of one instant would order by their spelling.
    """
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def registry() -> dict[str, registry_module.Registration]:
    """Every batch registration, fail-closed on anything absent."""
    return registry_module.read(registry_path())


def register(registration: registry_module.Registration) -> dict:
    """Register a batch. Appended, so a correction leaves the original readable."""
    if not registration.batch:
        raise registry_module.RegistrationError("a registration must name its batch")
    if not registration.method:
        raise registry_module.RegistrationError(
            f"{registration.batch}: a registration must say how the population was drawn — "
            "that sentence is the only record of why a rate measured on it does or does not "
            "mean anything"
        )
    row = registration.row()
    if row["registered_at"] is None:
        row["registered_at"] = now()
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def check(row: dict) -> dict:
    """Return `row`, having proved it is a label row. Raises otherwise."""
    if row.get("schema") != SCHEMA:
        raise LabelError(f"schema {row.get('schema')!r}, expected {SCHEMA}")
    batch = row.get("batch")
    if not isinstance(batch, str) or not batch:
        raise LabelError("a label row must name the batch it was drawn from")
    score = row.get("score")
    if score is not None and score not in SCORES:
        raise LabelError(f"score {score!r} is not one of {SCORES} or null")
    origin = row.get("origin")
    if origin != HUMAN and not (isinstance(origin, str) and origin.startswith(RULE_PREFIX)):
        raise LabelError(
            f"origin {origin!r}: a label is cast by a human ({HUMAN!r}) or by a stated rule "
            f"({RULE_PREFIX}<rule_id>), and which one it was cannot be recovered later"
        )
    if not isinstance(row.get("recorded_at"), str):
        raise LabelError("a label row must carry the time it was recorded; it is how latest wins")
    if key_of_row(row) is None:
        raise LabelError(
            "this row carries no location identity — a label needs its whole join on the same "
            "line (the family with every constant, and the viewport), or it is a verdict about "
            "a picture nobody can find again"
        )
    return row


def label_row(
    batch: str,
    score: int | None,
    family: dict,
    viewport: dict,
    render: dict | None = None,
    origin: str = HUMAN,
    labeler: str | None = None,
    recorded_at: str | None = None,
    **extra,
) -> dict:
    """Build one label row. The only shape the writer accepts."""
    row = {
        "schema": SCHEMA,
        "batch": batch,
        "recorded_at": recorded_at or now(),
        "labeler": labeler,
        "origin": origin,
        "score": score,
        "family": family,
        "viewport": viewport,
        "render": render or {},
        **extra,
    }
    return check(row)


def append(rows: list[dict], batch: str | None = None, known: dict | None = None) -> Path:
    """THE writer. Append checked rows to their batch's file and return its path.

    Every row is checked before the file is opened, so a rejected batch of rows
    leaves nothing half-written. The batch's registration is required to already
    exist: a population's generation method is a fact about how it was drawn, and
    it stops being recoverable the moment the labels are in.
    """
    if not rows:
        raise LabelError("nothing to append")
    batches = {row.get("batch") for row in rows}
    if batch is not None:
        batches.add(batch)
    if len(batches) != 1:
        raise LabelError(f"one call writes one batch's rows, not {sorted(batches)}")
    name = batches.pop()
    known = registry() if known is None else known
    if name not in known:
        raise LabelError(
            f"batch {name!r} has no registration. Register it before its first row exists — "
            "afterwards, 'was a model in the selection' is answered from memory. See "
            "`fractal-wallpapers label register`."
        )
    checked = [check(row) for row in rows]
    path = batch_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for row in checked:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def row_paths() -> list[Path]:
    """Every batch file, in name order."""
    directory = row_dir()
    return sorted(directory.glob("*.jsonl")) if directory.is_dir() else []


def read(paths=None) -> list[dict]:
    """Every label row, schema-checked, each stamped with where it came from.

    `_file` and `_line` are added because they are two thirds of the total order
    resolution runs on, and a reader that had to re-derive them from a second
    walk of the same files could disagree with this one about which row is last.
    """
    paths = row_paths() if paths is None else [Path(p) for p in paths]
    out: list[dict] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if row.get("schema") != SCHEMA:
                    raise LabelError(
                        f"{path}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}"
                    )
                out.append({**row, "_file": path.name, "_line": number})
    return out


def order_of(row: dict) -> tuple:
    """THE total order rows resolve in: when, then where, then which line."""
    return (
        str(row.get("recorded_at") or ""),
        str(row.get("_file") or ""),
        int(row.get("_line", 0)),
    )


@dataclass
class Resolution:
    """What the store currently says, and what it could not say it about."""

    #: `{location key: the winning row}`.
    current: dict = field(default_factory=dict)
    #: Rows read, rows superseded by a later verdict about the same location.
    n_rows: int = 0
    n_superseded: int = 0
    #: Rows whose location identity could not be built. Counted, never dropped
    #: silently and never routed to a default — see the module docstring.
    n_unkeyed: int = 0
    unkeyed: list = field(default_factory=list)

    def scored(self) -> list[dict]:
        """The resolved rows that carry a verdict, in location-key order.

        A row whose latest verdict is `null` is a location somebody looked at and
        did not judge; it is read past rather than counted, and withdrawing a
        label is what writing one is for.
        """
        return [row for _key, row in sorted(self.current.items()) if row.get("score") is not None]

    def summary(self) -> dict:
        return {
            "rows": self.n_rows,
            "locations": len(self.current),
            "scored": len(self.scored()),
            "superseded": self.n_superseded,
            "unkeyed": self.n_unkeyed,
        }


def resolve(rows: list[dict]) -> Resolution:
    """THE resolution rule: latest row wins, per location."""
    resolution = Resolution(n_rows=len(rows))
    for row in sorted(rows, key=order_of):
        key = key_of_row(row)
        if key is None:
            resolution.n_unkeyed += 1
            resolution.unkeyed.append(row)
            continue
        if key in resolution.current:
            resolution.n_superseded += 1
        resolution.current[key] = row
    return resolution


def resolved(paths=None) -> Resolution:
    """THE reader every consumer routes through."""
    return resolve(read(paths))


__all__ = [
    "HUMAN",
    "RULE_PREFIX",
    "SCHEMA",
    "SCORES",
    "LabelError",
    "Resolution",
    "append",
    "batch_path",
    "check",
    "eval_split_path",
    "label_dir",
    "label_row",
    "now",
    "order_of",
    "read",
    "register",
    "registry",
    "registry_path",
    "resolve",
    "resolved",
    "row_dir",
    "row_paths",
    "split_recipe_path",
]
