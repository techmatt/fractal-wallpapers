"""A recorded gallery traced back through every file a reader inspects.

`curate solve trace <stamp>` takes each seat of a record and follows it backward,
one join at a time, to the walk rows that found its place:

```text
gallery.jsonl  key ──► candidate_ledger/rows.jsonl      key
                       candidate_ledger/scores.jsonl    recipe_key
                       candidate_ledger/flatness.jsonl  recipe_key
                       gallery_grade_head/pool_scores   key
rows.jsonl  location.key ──► supply_scores.jsonl        key
                             <run>/locations.jsonl      key
supply_scores  ledger + node_id ──► <run>/walk.jsonl    the candidate row, each
                                                        ancestor up to the root
```

It writes **sliced copies** of those files holding only the rows on the chains,
copied byte for byte, with `counts.json` saying how many rows each full file held.
It also writes **a page** that shows each seat's picture beside its row from every
file in order, with the joining field marked. Beside the seats it follows a few
places and candidates that did *not* make it, each with where and why it stopped:

* the three lowest-scored places by the location judge,
* three candidates under the pool gate (the render judge's `P(>=4)` against
  `headroom.DEFAULT_BAR`), the nearest misses,
* three that cleared the gate and missed the fine bar (the gallery judge's
  `p_fine(>=4)` against `solve.DEFAULT_FINE_BAR`), again the nearest.

The slices also carry one row of every walk row kind the chains did not reach, so a
reader sees the whole vocabulary of `walk.jsonl` once. A seat whose chain cannot be
followed to the end is listed as such, with the file it stopped at.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from fractal_wallpapers.paths import Tiers, rehome, tracked_name, under

#: Where a trace lands unless a caller names somewhere else: `<UNIT>/<stamp>/`.
UNIT = "trace"

#: How many of each kind of reject the trace follows.
REJECTS = 3

#: The slices' folder inside a trace, and in its bundle.
FILES = "files"


def out_dir(stamp: str) -> Path:
    """A trace's directory. **The one accessor.**"""
    return under("curation", UNIT, stamp)


@dataclass
class Source:
    """One full file: every raw line, parsed once, and the lines a chain took."""

    name: str
    path: Path | None
    lines: list[str] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)
    taken: list[int] = field(default_factory=list)

    @classmethod
    def read(cls, name: str, path: Path | None) -> Source:
        source = cls(name, path)
        if path is not None and Path(path).is_file():
            with Path(path).open(encoding="utf-8", newline="") as handle:
                for line in handle:
                    if line.strip():
                        source.lines.append(line if line.endswith("\n") else line + "\n")
                        source.rows.append(json.loads(line))
        return source

    def index(self, column) -> dict:
        """`{value: [line numbers]}` over one column, or a function of the row."""
        held: dict = {}
        for at, row in enumerate(self.rows):
            value = column(row) if callable(column) else row.get(column)
            if value is not None:
                held.setdefault(value, []).append(at)
        return held

    def take(self, at: int) -> dict:
        if at not in self.taken:
            self.taken.append(at)
        return self.rows[at]

    def write_slice(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / self.name).open("w", encoding="utf-8", newline="") as handle:
            for at in sorted(self.taken):
                handle.write(self.lines[at])

    def counted(self) -> dict:
        return {
            "source": None if self.path is None else tracked_name(Path(self.path)),
            "rows": len(self.rows),
            "sliced": len(self.taken),
        }


class Stores:
    """Every file a chain walks, read once."""

    def __init__(self, stamp: str):
        from fractal_wallpapers.curation import candidate_ledger, flatness, intake, tentative
        from fractal_wallpapers.models import gallery_grade_train

        self.stamp = stamp
        self.gallery = Source.read("gallery.jsonl", tentative.rows_path(stamp))
        self.manifest_path = tentative.manifest_path(stamp)
        self.ledger = Source.read("rows.jsonl", candidate_ledger.rows_path())
        self.scores = Source.read("scores.jsonl", candidate_ledger.scores_path())
        self.flatness = Source.read("flatness.jsonl", flatness.sidecar_path())
        self.pool = Source.read("pool_scores.jsonl", gallery_grade_train.pool_scores_path())
        self.supply = Source.read("supply_scores.jsonl", intake.scores_path())
        self.by_key = self.ledger.index("key")
        self.scores_by = self.scores.index("recipe_key")
        self.flat_by = self.flatness.index("recipe_key")
        self.pool_by = self.pool.index("key")
        self.supply_by = self.supply.index("key")
        # The harvests the places came from, read lazily: a ledger is named on each
        # supply row, and the places of one gallery usually come from one harvest.
        self.walks: dict[str, Source] = {}
        self.locations: dict[str, Source] = {}

    def walk(self, stored: str) -> tuple[Source, Source] | None:
        """`(walk.jsonl, locations.jsonl)` of the harvest a supply row names."""
        if stored not in self.walks:
            path = rehome(stored) or Path(stored)
            if not path.is_file():
                return None
            self.walks[stored] = Source.read("walk.jsonl", path)
            self.locations[stored] = Source.read("locations.jsonl", path.parent / "locations.jsonl")
        return self.walks[stored], self.locations[stored]

    def sources(self) -> list[Source]:
        held = [self.gallery, self.ledger, self.scores, self.flatness, self.pool, self.supply]
        held += list(self.locations.values()) + list(self.walks.values())
        return held


def _record(file: str, row, joined_on: str = "", key=None, note: str = ""):
    from fractal_wallpapers.grid_page import Record

    return Record(file=file, row=row, joined_on=joined_on, key=key, note=note)


def chain(stores: Stores, key: str) -> tuple[list, str | None]:
    """`(records, stopped)` — one candidate's rows from the ledger back to the walk.

    `stopped` names the file the chain could not be followed into, or `None` for
    a chain followed to the walk's root row.
    """
    records = []
    found = stores.by_key.get(key)
    if not found:
        records.append(_record("rows.jsonl", None, "key", key, "no ledger row"))
        return records, "rows.jsonl"
    row = stores.ledger.take(found[-1])
    records.append(_record("rows.jsonl", row, "key", key))
    for source, index in (
        (stores.scores, stores.scores_by),
        (stores.flatness, stores.flat_by),
    ):
        for at in index.get(key, []):
            records.append(_record(source.name, source.take(at), "recipe_key", key))
    pooled = stores.pool_by.get(key)
    if pooled:
        records.append(_record("pool_scores.jsonl", stores.pool.take(pooled[-1]), "key", key))
    else:
        records.append(
            _record("pool_scores.jsonl", None, "key", key, "the gallery judge never read it")
        )
    behind, stopped = place_chain(stores, (row.get("location") or {}).get("key"))
    return records + behind, stopped


def place_chain(stores: Stores, place) -> tuple[list, str | None]:
    """A place's rows from the location judge's sidecar back to the walk's root."""
    records = []
    at = stores.supply_by.get(place)
    if not at:
        records.append(_record("supply_scores.jsonl", None, "key", place, "no location score"))
        return records, "supply_scores.jsonl"
    supply = stores.supply.take(at[-1])
    records.append(_record("supply_scores.jsonl", supply, "key", place))
    found = stores.walk(str(supply.get("ledger")))
    if found is None:
        records.append(
            _record("walk.jsonl", None, "", None, f"its harvest {supply.get('ledger')} is gone")
        )
        return records, "walk.jsonl"
    walk, locations = found
    held = locations.index("key").get(place)
    if held:
        records.append(_record("locations.jsonl", locations.take(held[-1]), "key", place))
    else:
        records.append(
            _record("locations.jsonl", None, "key", place, "not exported (`harvest export`)")
        )
    nodes = walk.index(lambda row: row.get("node_id") if row.get("kind") == "candidate" else None)
    node = supply.get("node_id")
    if node not in nodes:
        records.append(_record("walk.jsonl", None, "node_id", node, "no candidate row"))
        return records, "walk.jsonl"
    # The place's own row, then each ancestor up the lineage, then its root.
    candidate = walk.take(nodes[node][-1])
    records.append(_record("walk.jsonl", candidate, "node_id", node))
    parent = candidate.get("parent_node_id")
    while parent in nodes:
        above = walk.take(nodes[parent][-1])
        records.append(_record("walk.jsonl", above, "node_id", parent, "ancestor"))
        parent = above.get("parent_node_id")
    roots = walk.index(lambda row: row.get("root_id") if row.get("kind") == "root" else None)
    root = candidate.get("root_id")
    if root in roots:
        records.append(_record("walk.jsonl", walk.take(roots[root][-1]), "root_id", root, "root"))
    return records, None


def _rejects(stores: Stores, seated: set) -> list[tuple[str, str, list, str]]:
    """`(heading, picture key or place, records, why)` for each reject followed."""
    from fractal_wallpapers.curation import candidate_ledger, distinct, headroom, solve

    out = []
    scored = [row for row in stores.supply.rows if row.get("p_ge3") is not None]
    lowest = sorted(scored, key=lambda row: (float(row["p_ge3"]), row["key"]))[:REJECTS]
    opened = {(row.get("location") or {}).get("key"): 0 for row in stores.ledger.rows}
    for row in stores.ledger.rows:
        opened[(row.get("location") or {}).get("key")] += 1
    for place in lowest:
        records, _ = place_chain(stores, place["key"])
        rendered = opened.get(place["key"], 0)
        why = (
            f"location judge P(>=3) {float(place['p_ge3']):.4f}, among the {REJECTS} lowest of "
            f"{len(scored):,} scored places; "
            + (
                f"{rendered} candidate(s) were rendered here and none was seated"
                if rendered
                else "no candidate was rendered here, so it stops at the location judge"
            )
        )
        out.append(("lowest-scored place", None, records, why))
    render = candidate_ledger.scores_by_recipe(candidate_ledger.read_scores())
    fine = distinct.fine_scores()
    gate, fine_bar = headroom.DEFAULT_BAR, solve.DEFAULT_FINE_BAR
    under_gate, under_fine = [], []
    for row in stores.ledger.rows:
        key = str(row["key"])
        p4 = (render.get(key) or {}).get("p_ge4")
        if key in seated or p4 is None:
            continue
        if p4 < gate:
            under_gate.append((gate - p4, key, p4))
        elif key in fine and fine[key] < fine_bar:
            under_fine.append((fine_bar - fine[key], key, fine[key]))
    for _, key, p4 in sorted(under_gate)[:REJECTS]:
        records, _ = chain(stores, key)
        why = (
            f"render judge P(>=4) {p4:.4f} under the pool gate {gate:g}: "
            f"a solve never sees it, so it stops at the candidate ledger"
        )
        out.append(("candidate under the pool gate", key, records, why))
    for _, key, p_fine in sorted(under_fine)[:REJECTS]:
        records, _ = chain(stores, key)
        why = (
            f"cleared the pool gate, then the gallery judge's p_fine(>=4) {p_fine:.4f} under the "
            f"fine bar {fine_bar:g}: it stops at pool_scores.jsonl"
        )
        out.append(("cleared the gate, missed the fine bar", key, records, why))
    return out


def _walk_examples(stores: Stores) -> None:
    """One row of every walk row kind no chain reached, into each walk's slice."""
    for walk in stores.walks.values():
        kinds = {walk.rows[at].get("kind") for at in walk.taken}
        for at, row in enumerate(walk.rows):
            if row.get("kind") not in kinds:
                kinds.add(row.get("kind"))
                walk.take(at)


def build(
    stamp: str, out: Path | None = None, bundle: Path | None = None, log=print
) -> tuple[Path, dict]:
    """Write the slices, `counts.json` and the page. Returns `(page, counts)`."""
    from fractal_wallpapers import grid_page
    from fractal_wallpapers.curation import tentative

    stores = Stores(stamp)
    if not stores.gallery.rows:
        raise FileNotFoundError(f"no record at {tracked_name(tentative.rows_path(stamp))}")
    tiers = Tiers.current()
    directory = Path(out) if out is not None else out_dir(stamp)
    manifest = tentative.read_manifest(stamp)
    sections = []
    broken = []
    for seat, at in enumerate(range(len(stores.gallery.rows)), start=1):
        row = stores.gallery.take(at)
        key = str(row.get("key"))
        records, stopped = chain(stores, key)
        if stopped is not None:
            broken.append({"seat": seat, "key": key, "stopped_at": stopped})
        picture = rehome(row["picture"], tiers) if row.get("picture") else None
        sections.append(
            grid_page.Section(
                f"seat {seat} · {row.get('alias') or key} · {row.get('mode')}",
                note=(
                    "chain followed to the walk's root"
                    if stopped is None
                    else f"CHAIN BROKEN: it could not be followed into {stopped}"
                ),
                tiles=[grid_page.Tile(picture, [("seat", seat), ("mode", row.get("mode"))])],
                records=[_record("gallery.jsonl", row, "key", key), *records],
            )
        )
    seated = {str(row.get("key")) for row in stores.gallery.rows}
    for heading, key, records, why in _rejects(stores, seated):
        picture = None
        if key is not None:
            held = stores.ledger.rows[stores.by_key[key][-1]]
            picture = rehome(held["picture"], tiers) if held.get("picture") else None
        tiles = [grid_page.Tile(picture, [("why", why)])] if key is not None else []
        sections.append(grid_page.Section(f"not made it: {heading}", why, tiles, records=records))
    _walk_examples(stores)
    files = directory / FILES
    if files.is_dir():
        shutil.rmtree(files)
    for source in stores.sources():
        source.write_slice(files)
    shutil.copyfile(stores.manifest_path, files / "manifest.json")
    counts = {
        "schema": 1,
        "stamp": stamp,
        "seats": len(stores.gallery.rows),
        "broken_chains": broken,
        "files": {source.name: source.counted() for source in stores.sources()},
    }
    (directory / "counts.json").write_text(
        json.dumps(counts, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    intro = [
        f"Record {stamp}"
        + (" (FORCED FILL)" if tentative.is_forced(manifest) else "")
        + f": {counts['seats']} seat(s), each followed from gallery.jsonl back to the walk "
        f"row that found its place. Every row is shown whole, as copied into {FILES}/, "
        f"with the field it was joined on marked.",
        f"{len(broken)} chain(s) could not be followed to the end"
        + (
            ": " + ", ".join(f"seat {b['seat']} at {b['stopped_at']}" for b in broken)
            if broken
            else "."
        ),
        "Full files held: "
        + ", ".join(f"{name} {block['rows']:,}" for name, block in counts["files"].items())
        + ". The slices hold only the rows shown, plus one walk row of every other kind.",
    ]
    page = grid_page.write(
        directory / "index.html",
        f"Trace of {stamp}",
        intro,
        [grid_page.Section("The record", records=[_record("manifest.json", manifest)]), *sections],
        bundle=bundle,
    )
    if bundle is not None:
        if (Path(bundle) / FILES).is_dir():
            shutil.rmtree(Path(bundle) / FILES)
        shutil.copytree(files, Path(bundle) / FILES)
        shutil.copyfile(directory / "counts.json", Path(bundle) / "counts.json")
    log(f"[trace] {tracked_name(page)}")
    return page, counts
