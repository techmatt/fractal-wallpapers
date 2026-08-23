"""The colour census: what colours this project can make, picks, keeps and has labelled.

A standing, re-runnable **record-and-rank**. Nothing here filters, scores, gates or
removes anything — there is no cut in this module and there is not meant to be
one. It describes the colour distribution at four stages so that a claim about
colour bias can be checked against numbers instead of impressions.

Some colour bias is correct by design: icy and fiery palettes make genuinely good
wallpapers and a pipeline that picks them often is working. What the census
exists to separate is four situations that look identical from the outside and
have completely different fixes:

```text
can't be expressed     the library has no map that carries the colour     -> augment the library
never picked           maps carry it, the palette head does not choose    -> the head's taste
picked but dying       chosen, and the render heads reject the result     -> geometry, or real
never labelled         no human verdict exists on it either way           -> label before claiming
```

The four stages answer those in order, and the readout is the disagreement
between them.

## The four populations, and why they are not one population

1. **Library footprint** — the colormap tables themselves, folded exactly as
   production folds them. No rendering: this is what the library *could* say.
2. **Picks against availability** — every candidate set the pool ever offered and
   which member the palette head took. This isolates the head's taste from the
   library's gaps, because the denominator is what was actually on the table.
3. **Render-head survival** — the candidate renders, by dominant colour, split
   per judge. Descriptive only, and the colour-versus-geometry confound is named
   in the readout rather than modelled away.
4. **Human label distribution** — the render-head corpora through their canonical
   resolver. This is the stage that decides whether a bias claim is *falsifiable*:
   if Matt's 3s and 4s contain no dark-green example at all, no amount of
   downstream counting can say whether dark green is bad or merely unseen.

## Stage 3 restricts to one scale rather than pooling two

A judge's score is calibrated against its own training prior, so a number from a
retired checkpoint is not on the same scale as one from the shipped one, and the
committed floors are defined on the shipped scale. Reading a stored old-scale
score against today's floor is not a floor-pass verdict, and tagging the rows and
pooling them anyway would invite exactly that comparison.

So the stage splits in two. Everything **score-free** — which colours the pool's
candidate renders actually are — runs over the whole pool. Everything that
references a floor runs over the rows carrying `scores_current` only, and this
module *asserts* that each such row's score stamp is the very artifact its floor
was measured on rather than assuming it. A row whose stamps disagree is refused,
not counted.

When the pool is next re-scored, the restricted half widens by itself and the
census re-run picks it up. That is a later session's decision and this module
does not take it.

## Re-runnable over a grown pool, and stamped with the population it read

Every table is derived at read time from whatever the stores currently hold; the
artifact records the population it was taken over — counts, stores, floors, head
stamps — so that two runs of this command a month apart can be told apart by
something better than their dates.

**A partial run merges rather than replaces.** `--stage library` recomputes one
quarter of the census, and writing only that quarter would silently delete the
other three — the same shape of mistake as a `curate score` binding clearing
another binding's rows, which is why `intake` upserts. So the stages this run
computed replace what was there and every other stage is carried whole, rows
included. A carried stage keeps its own date in `stage_taken_at`, because a table
dated today over a pool that has since grown is worse than a visibly stale one;
the manifest reports `stages_this_run` beside `stages_carried` for the same
reason.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.palettes import codebook

#: The artifact's schema, carried from the first row.
SCHEMA = 1

#: The four stages, in the order the readout reads them.
STAGES = ("library", "picks", "survival", "labels")

#: What this population is, for a later run to compare against. The census was
#: built to be re-run over a grown pool, so the baseline says which pool it saw.
BASELINE = "pre-run11"


class CensusError(RuntimeError):
    """The census cannot be taken over the stores as they are."""


# --------------------------------------------------------------------------- #
# Where it lands.
# --------------------------------------------------------------------------- #
def census_dir() -> Path:
    """Where the census artifact lives. Ignored, and regenerable in about five minutes."""
    from fractal_wallpapers.paths import under

    return under("curation", "colors")


def readout_path() -> Path:
    """The census itself: codebook, population, per-stage tables, pre-registered metrics."""
    return census_dir() / "census.json"


def rows_path() -> Path:
    """One row per censused unit — a map, a candidate render, a labelled crop.

    Kept beside the readout so a later question can re-aggregate the census
    without decoding twelve thousand JPEGs again. It is the file the tracked
    manifest describes.
    """
    return census_dir() / "rows.jsonl"


def manifest_path() -> Path:
    """The tracked manifest: what the last census was, and what it was taken over.

    A manifest rather than the tracked rows, because the rows are megabytes
    against a 1 MiB per-file history guard. A manifest **without** an archive
    copy, unlike the supply sidecar and the embedding store: those cost a GPU leg
    or a standing supply that the checkout cannot rebuild, and this costs about
    five minutes over inputs that are all either tracked or regenerable. What the
    history needs here is provenance, not a second disk.
    """
    from fractal_wallpapers.paths import repo_root

    return repo_root() / "data" / "curation" / "colors" / "census.manifest.json"


def _write_jsonl(path: Path, rows) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


def _measured_json(path: Path) -> dict:
    """Bytes and digest for a JSON document, and deliberately no row count.

    `durability.measure` counts newlines, which is the row count of a JSONL and is
    nothing at all for a pretty-printed JSON object — five thousand there is a
    statement about the indenting. A field that means nothing is worse than an
    absent one, because a reader will compare it to something.
    """
    from fractal_wallpapers.curation import durability

    measured = durability.measure(path)
    return {"bytes": measured["bytes"], "sha256": measured["sha256"]}


def _write_json(path: Path, document: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return path


# --------------------------------------------------------------------------- #
# The metrics, pre-registered.
# --------------------------------------------------------------------------- #
def thresholded(vectors: list[dict]) -> dict:
    """Per swatch: how many of these share vectors clear each pre-registered threshold.

    Both thresholds are always reported. The 10% figure asks whether a colour is
    *present* in a picture and the 25% figure asks whether it can *dominate* one,
    and the second is expected to be sparse — that sparsity is the reading, not a
    fault in it.
    """
    names = codebook.names()
    total = len(vectors)
    table = {}
    for name in names:
        cell = {"present_share_mean": 0.0}
        for threshold in codebook.SHARE_THRESHOLDS:
            cell[f"at_{int(threshold * 100)}pct"] = sum(
                1 for vector in vectors if vector.get(name, 0.0) >= threshold
            )
        cell["present_share_mean"] = round(
            sum(vector.get(name, 0.0) for vector in vectors) / total if total else 0.0, 6
        )
        table[name] = cell
    return {"n": total, "swatches": table}


def _tally(rows: list[dict], key: str = "dominant") -> dict:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row[key]] = counts.get(row[key], 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _spread(values: list[float]) -> dict:
    """Mean and median of a list, or nulls where there is nothing to average."""
    if not values:
        return {"mean": None, "median": None}
    ordered = sorted(values)
    middle = len(ordered) // 2
    median = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2.0
    return {"mean": round(sum(ordered) / len(ordered), 6), "median": round(median, 6)}


def _families(rows: list[dict]) -> dict:
    """The dominant-swatch tally rolled onto the twelve hue families and the neutrals."""
    by_swatch = {entry["swatch"]: entry for entry in codebook.swatches()}
    counts: dict[str, int] = {}
    for row in rows:
        entry = by_swatch[row["dominant"]]
        family = "neutral" if entry["kind"] == "neutral" else entry["hue"]
        counts[family] = counts.get(family, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


# --------------------------------------------------------------------------- #
# Stage 1 — what the library can express at all.
# --------------------------------------------------------------------------- #
def library(log=print) -> tuple[dict, list[dict]]:
    """Census every tracked colormap over the ramp production really spends.

    No render is made and none is needed: a map's colours are its table, and the
    fold is a property of the map. What this answers is the first of the four
    questions — whether a colour is *expressible* — and a colour absent here
    cannot be picked, survive or be labelled by anything downstream.
    """
    from fractal_wallpapers.models import palette_sets
    from fractal_wallpapers.paths import colormap_dir

    pool = set(_pool_maps())
    cyclic = palette_sets.cyclic()
    names = sorted(path.stem for path in colormap_dir().glob("*.json"))
    rows = []
    for name in names:
        try:
            read = codebook.of_ramp(name)
        except codebook.CodebookError as refusal:
            raise CensusError(f"{name} could not be censused: {refusal}") from refusal
        rows.append(
            {
                "schema": SCHEMA,
                "stage": "library",
                "colormap": name,
                "kind": "cyclic" if name in cyclic else "sequential",
                "mirror": name not in cyclic,
                "in_pool": name in pool,
                **read,
            }
        )
    log(f"[library] {len(rows)} maps censused ({sum(r['in_pool'] for r in rows)} in the pool)")
    vectors = [row["shares"] for row in rows]
    return {
        "maps": len(rows),
        "cyclic": sum(1 for row in rows if row["kind"] == "cyclic"),
        "sequential": sum(1 for row in rows if row["kind"] == "sequential"),
        "in_pool": sum(1 for row in rows if row["in_pool"]),
        "fold_rule": "mirror = the map is not cyclic (palette_sets.recipe_for)",
        "ramp_samples": codebook.RAMP_SAMPLES,
        "metrics": thresholded(vectors),
        "pool_metrics": thresholded([row["shares"] for row in rows if row["in_pool"]]),
        "dominant": _tally(rows),
        "families": _families(rows),
        "entropy": _spread([row["entropy_bits"] for row in rows]),
    }, rows


def _pool_maps() -> list[str]:
    """The maps a colorize may actually choose between, from the shipped pool record."""
    from fractal_wallpapers.paths import repo_root

    path = repo_root() / "data" / "palette_choice" / "pool.json"
    if not path.is_file():
        raise CensusError(f"{path} is missing — the pool is what stage 2's denominator is")
    return list(json.loads(path.read_text(encoding="utf-8")).get("pool") or [])


# --------------------------------------------------------------------------- #
# Stage 2 — what the palette head picks, against what it was offered.
# --------------------------------------------------------------------------- #
def picks(map_rows: list[dict], log=print) -> tuple[dict, list[dict]]:
    """Pick rate per colour region, against availability in the same candidate sets.

    The denominator is the whole point. A colour that is rarely picked because it
    is rarely offered is a library fact; a colour that is offered constantly and
    never taken is the head's taste, and only a rate against the *offered* set
    can tell them apart.

    The **selection ratio** is that rate made readable: a set offers 32 maps and
    the head takes one, so a colour carried by a share of the offers would be
    taken at that share if picking were blind. One means blind, above one means
    the head reaches for the colour, below one means it avoids it.

    Every score scale is irrelevant here — a pick is a pick — so this stage reads
    the whole pool, both stores, and takes no position on any floor.
    """
    shares_of = {row["colormap"]: row["shares"] for row in map_rows}
    rows, offered, taken = [], {}, {}
    names = codebook.names()
    for name in names:
        offered[name] = taken[name] = 0
    considered = missing = 0
    for row in _pool_rows():
        palette = row.get("palette") or {}
        candidates = list(palette.get("candidates") or [])
        chosen = (row.get("recipe") or {}).get("colormap")
        if not candidates or not chosen:
            continue
        if chosen not in shares_of or any(name not in shares_of for name in candidates):
            missing += 1
            continue
        considered += 1
        for name in names:
            hits = sum(1 for candidate in candidates if shares_of[candidate].get(name, 0.0) >= 0.10)
            offered[name] += hits
            if shares_of[chosen].get(name, 0.0) >= 0.10:
                taken[name] += 1
        rows.append(
            {
                "schema": SCHEMA,
                "stage": "picks",
                "run": row.get("run"),
                "candidate": row.get("candidate"),
                "chosen": chosen,
                "offered": len(candidates),
                "anchor": palette.get("anchor"),
                "dominant": max(shares_of[chosen], key=shares_of[chosen].get),
            }
        )
    log(f"[picks] {considered} candidate sets read; {missing} skipped for an unknown map")
    table = {}
    for name in names:
        seen, took = offered[name], taken[name]
        expected = seen / 32.0
        table[name] = {
            "offered": seen,
            "picked": took,
            "expected_if_blind": round(expected, 3),
            "selection_ratio": round(took / expected, 4) if expected else None,
        }
    return {
        "sets": considered,
        "skipped_unknown_map": missing,
        "candidates_per_set": 32,
        "threshold": 0.10,
        "note": (
            "a candidate set is an anchor's neighbourhood, so its 32 members are alike by "
            "construction and the offers inside one set are strongly correlated; the ratio "
            "is a rate and not a binomial test"
        ),
        "swatches": table,
        "picked_dominant": _tally(rows),
        "picked_families": _families(rows),
    }, rows


def _pool_rows() -> list[dict]:
    """Every pool row, both stores: a run's release rows and a gallery pass's attempts."""
    from fractal_wallpapers.curation import gallery_store, records

    return [*records.read_decisions(records.RELEASE), *gallery_store.read()]


def _reader():
    """A picture census that remembers, and reports an absent file as `None`.

    The pool's halves overlap: a render counted in the score-free tally is very
    often the same file a floor-referenced row points at, and the raise-only read
    is a subset of that again. Decoding each of them separately would read twelve
    thousand JPEGs to census four and a half thousand pictures, and the count
    would be identical. One memo per census run, deliberately not a module-level
    cache — a re-run inside one process must see a re-rendered picture.
    """
    memo: dict[str, dict | None] = {}

    def read(picture) -> dict | None:
        key = str(picture)
        if key not in memo:
            path = Path(key)
            memo[key] = codebook.of_picture(path) if path.is_file() else None
        return memo[key]

    return read


# --------------------------------------------------------------------------- #
# Stage 3 — what survives the render heads, by colour.
# --------------------------------------------------------------------------- #
def survival(log=print) -> tuple[dict, list[dict]]:
    """Colour of the candidate pool, and floor-pass rate by colour on the current scale.

    Two halves on two populations, and they are never pooled — see the module
    docstring. The score-free half is every distinct candidate render the pool
    holds; the floor half is the rows carrying a score from the artifact each
    head's floor was measured on.
    """
    from fractal_wallpapers.curation import floors, rescore

    read_picture = _reader()
    seen: dict[str, dict] = {}
    for row in _pool_rows():
        if ((row.get("scores") or {}).get("p_ge3")) is None:
            continue
        try:
            picture = rescore.picture_of(row)
        except (KeyError, TypeError):
            continue
        seen.setdefault(str(picture), row)
    rows, absent = [], 0
    for path, row in sorted(seen.items()):
        read = read_picture(path)
        if read is None:
            absent += 1
            continue
        location = row.get("location") or {}
        rows.append(
            {
                "schema": SCHEMA,
                "stage": "survival",
                "picture": path,
                "run": row.get("run"),
                "candidate": row.get("candidate"),
                "head": (row.get("scores") or {}).get("head"),
                "partition": location.get("partition"),
                "colormap": (row.get("recipe") or {}).get("colormap"),
                "mode": (row.get("recipe") or {}).get("mode"),
                **read,
            }
        )
    log(f"[survival] {len(rows)} candidate renders censused; {absent} named but not on disk")

    scored = _floor_referenced(log=log)
    by_head = {}
    for head, cells in scored.items():
        floor = floors.gallery_floor(head)
        graded = []
        for cell in cells:
            read = read_picture(str(rescore.picture_of(cell["row"])))
            if read is None:
                continue
            graded.append(
                {
                    "dominant": read["dominant"],
                    "partition": (cell["row"].get("location") or {}).get("partition"),
                    "score": cell["score"],
                    "clears": cell["score"] >= floor.value,
                }
            )
        by_head[head] = {
            "floor": floor.value,
            "floor_name": floor.name,
            "head_sha256": floor.stamp,
            "n": len(graded),
            "clears": sum(1 for entry in graded if entry["clears"]),
            "by_swatch": _survival_table(graded),
            "by_family": _survival_table(graded, family=True),
        }
        log(
            f"[survival] {head}: n={len(graded)} floor={floor.value} "
            f"clears={by_head[head]['clears']}"
        )

    return {
        "pool": {
            "renders": len(rows),
            "named_but_absent": absent,
            "dominant": _tally(rows),
            "families": _families(rows),
            "metrics": thresholded([row["shares"] for row in rows]),
            "note": "score-free: every distinct candidate render the pool holds, both stores",
        },
        "floor_referenced": by_head,
        "raise_only": _raise_only(scored, read_picture, log=log),
        "confound": (
            "colour is not independent of geometry or of mode here: a map is chosen for a "
            "location by a head that saw the location, and the strange judge owns every "
            "mode but smooth. A colour's survival rate carries its material's survival "
            "rate with it, and nothing in this stage separates them"
        ),
        "restriction": (
            f"floor-referenced cells read only rows whose score stamp is the artifact the "
            f"floor was measured on; {sum(len(cells) for cells in scored.values())} of the "
            f"{len(_pool_rows())} pool rows qualify. Re-scoring the pool widens this"
        ),
    }, rows


def _floor_referenced(log=print) -> dict:
    """The rows a floor may legitimately be read against, per head, refusing a scale mix.

    A row qualifies when it carries `scores_current` **and** that reading's own
    head stamp is the artifact this head's floor was measured on. The stamp is
    checked rather than assumed: a row from a different checkpoint carries a
    number on a different calibration, and a floor applied across that boundary
    is not a verdict about anything.
    """
    from fractal_wallpapers.curation import floors, records

    wanted = {}
    for head in ("smooth_render", "strange_render"):
        wanted[head] = floors.gallery_floor(head).stamp
    out: dict[str, list[dict]] = {head: [] for head in wanted}
    mismatched = 0
    for row in records.read_decisions(records.RELEASE):
        current = row.get("scores_current") or {}
        head = (row.get("scores") or {}).get("head")
        score = current.get("p_ge3")
        if head not in wanted or score is None:
            continue
        if current.get("head_sha256") != wanted[head]:
            mismatched += 1
            continue
        out[head].append({"row": row, "score": float(score)})
    if mismatched:
        raise CensusError(
            f"{mismatched} row(s) carry a current score from an artifact that is not the one "
            f"their head's floor was measured on. A floor read across that boundary is not a "
            f"floor-pass verdict. Re-run `fractal-wallpapers curate rescore` before censusing."
        )
    log("[survival] floor-referenced rows: " + ", ".join(f"{k}={len(v)}" for k, v in out.items()))
    return out


def _survival_table(graded: list[dict], family: bool = False) -> dict:
    """Per colour cell: how many candidates, how many cleared, and the score spread."""
    by_swatch = {entry["swatch"]: entry for entry in codebook.swatches()}

    def cell_of(entry: dict) -> str:
        if not family:
            return entry["dominant"]
        described = by_swatch[entry["dominant"]]
        return "neutral" if described["kind"] == "neutral" else described["hue"]

    buckets: dict[str, list[dict]] = {}
    for entry in graded:
        buckets.setdefault(cell_of(entry), []).append(entry)
    table = {}
    for name, entries in buckets.items():
        clears = sum(1 for entry in entries if entry["clears"])
        table[name] = {
            "n": len(entries),
            "clears": clears,
            "rate": round(clears / len(entries), 4),
            "score": _spread([entry["score"] for entry in entries]),
        }
    return dict(sorted(table.items(), key=lambda item: -item[1]["n"]))


def _raise_only(scored: dict, read_picture, log=print) -> dict:
    """The raise-only read: mandelbrot smooth rejects against keeps, by colour.

    Are the candidates the smooth judge still rejects on mandelbrot plausibly
    *palette* verdicts — a colour the judge dislikes — or are they spread across
    colour the way the keeps are? Reported at hue-family granularity because the
    reject pile is small and fifty-two cells over it is noise wearing a number.
    """
    from fractal_wallpapers.curation import floors, rescore

    head = "smooth_render"
    floor = floors.gallery_floor(head).value
    graded = []
    for cell in scored.get(head, []):
        if (cell["row"].get("location") or {}).get("partition") != "mandelbrot":
            continue
        read = read_picture(str(rescore.picture_of(cell["row"])))
        if read is None:
            continue
        graded.append(
            {"dominant": read["dominant"], "score": cell["score"], "clears": cell["score"] >= floor}
        )
    keeps = [entry for entry in graded if entry["clears"]]
    rejects = [entry for entry in graded if not entry["clears"]]
    log(
        f"[survival] raise-only: mandelbrot smooth n={len(graded)} "
        f"keeps={len(keeps)} rejects={len(rejects)}"
    )
    return {
        "head": head,
        "partition": "mandelbrot",
        "floor": floor,
        "n": len(graded),
        "keeps": {"n": len(keeps), "families": _families(keeps), "dominant": _tally(keeps)},
        "rejects": {"n": len(rejects), "families": _families(rejects), "dominant": _tally(rejects)},
        "granularity": (
            "read the families; the fifty-two-cell tally is carried for the artifact and is "
            "too thin at this n to rank"
        ),
    }


# --------------------------------------------------------------------------- #
# Stage 4 — what a person has actually judged, by colour.
# --------------------------------------------------------------------------- #
def labels(log=print) -> tuple[dict, list[dict]]:
    """Human verdicts by dominant colour and class, per render head.

    Through the canonical resolver and its own render cache: a label row carries
    its whole coloring join, and the picture that join makes is the one the judge
    was trained on. This is the stage that says whether a bias claim can be
    falsified at all — a colour with no 3s and no 4s has no exemplar to argue
    from, whichever way somebody wants to argue.
    """
    from fractal_wallpapers.labeling import finished
    from fractal_wallpapers.models import renders

    rows, out = [], {}
    for head in ("smooth_render", "strange_render"):
        plan = renders.plan(head)
        crops = renders.crop_dir(head)
        absent = 0
        graded = []
        for job in plan:
            picture = crops / f"{job['name']}.jpg"
            if not picture.is_file():
                absent += 1
                continue
            read = codebook.of_picture(picture)
            entry = {
                "schema": SCHEMA,
                "stage": "labels",
                "head": head,
                "name": job["name"],
                "batch": job.get("batch"),
                "score": job.get("score"),
                "partition": job.get("partition"),
                "colormap": job.get("colormap"),
                "mode": job.get("mode"),
                **read,
            }
            graded.append(entry)
            rows.append(entry)
        resolution = finished.resolved(head).summary()
        by_class = {}
        for tier in finished.tiers(head):
            of_tier = [entry for entry in graded if entry["score"] == tier]
            by_class[str(tier)] = {
                "n": len(of_tier),
                "dominant": _tally(of_tier),
                "families": _families(of_tier),
            }
        keepers = [entry for entry in graded if (entry["score"] or 0) >= 3]
        out[head] = {
            "store": resolution,
            "pictures": len(graded),
            "absent": absent,
            "by_class": by_class,
            "keepers": {
                "n": len(keepers),
                "dominant": _tally(keepers),
                "families": _families(keepers),
                "unrepresented_swatches": sorted(
                    set(codebook.names()) - {entry["dominant"] for entry in keepers}
                ),
            },
            "metrics": thresholded([entry["shares"] for entry in graded]),
        }
        log(
            f"[labels] {head}: {len(graded)} judged pictures, {absent} absent, "
            f"{len(keepers)} at 3 or 4"
        )
    return out, rows


# --------------------------------------------------------------------------- #
# The whole census.
# --------------------------------------------------------------------------- #
def take(stages=STAGES, log=print) -> dict:
    """Run the census and write the artifact, the rows and the tracked manifest."""
    from fractal_wallpapers.curation import durability

    chosen = tuple(stage for stage in STAGES if stage in set(stages))
    if not chosen:
        raise CensusError(f"no stage named: {sorted(set(stages))}; known stages are {STAGES}")

    readout: dict = {
        "schema": SCHEMA,
        "baseline": BASELINE,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "codebook": codebook.document(),
        "stages": {},
    }
    rows: list[dict] = []

    map_rows: list[dict] = []
    if "library" in chosen:
        table, map_rows = library(log=log)
        readout["stages"]["library"] = table
        rows.extend(map_rows)
    if "picks" in chosen:
        if not map_rows:
            _, map_rows = library(log=log)
        table, pick_rows = picks(map_rows, log=log)
        readout["stages"]["picks"] = table
        rows.extend(pick_rows)
    if "survival" in chosen:
        table, survival_rows = survival(log=log)
        readout["stages"]["survival"] = table
        rows.extend(survival_rows)
    if "labels" in chosen:
        table, label_rows = labels(log=log)
        readout["stages"]["labels"] = table
        rows.extend(label_rows)

    readout["population"] = _population(chosen)
    carried = _carry_forward(readout, rows, chosen, log=log)
    written = _write_jsonl(rows_path(), rows)
    _write_json(readout_path(), readout)
    manifest = {
        "schema": SCHEMA,
        "baseline": BASELINE,
        "taken_at": readout["taken_at"],
        "stages": sorted(readout["stages"]),
        "stages_this_run": list(chosen),
        "stages_carried": carried,
        "rows": durability.measure(rows_path()),
        "readout": _measured_json(readout_path()),
        "population": readout["population"],
        "codebook": {
            "sigma": codebook.SIGMA,
            "swatches": len(codebook.names()),
            "census_size": list(codebook.CENSUS_SIZE),
        },
        "why_not_tracked": (
            "the rows are megabytes against the 1 MiB per-file history guard, and the census "
            "re-runs in about five minutes from tracked inputs plus the render caches, so what "
            "the history keeps is provenance rather than the file"
        ),
        "rebuild_command": "fractal-wallpapers curate colors",
    }
    _write_json(manifest_path(), manifest)
    log(f"[census] {written} rows -> {rows_path()}")
    log(f"[census] readout -> {readout_path()}")
    log(f"[census] manifest -> {manifest_path()}")
    return readout


def _carry_forward(readout: dict, rows: list[dict], chosen: tuple[str, ...], log=print) -> list:
    """Keep the stages this run did not compute, instead of deleting them.

    A `--stage library` run recomputes one quarter of the census, and writing only
    that quarter would silently throw the other three away — the same shape of
    mistake as a `curate score` binding that cleared another binding's rows, and
    the reason `intake._upsert_scores` upserts. So a partial run **merges**: its
    own stages replace what was there, and every other stage is carried whole
    from the artifact already on disk, rows included.

    A carried stage is **stamped with the run that actually computed it**, because
    the alternative is worse than a stale number: a table dated today, derived
    from a pool that has since grown, with nothing on it to say so. `stages_this
    _run` and [`readout["stage_taken_at"]`] are what a reader compares.

    The stamps live in a map beside the tables rather than inside them. A stage
    table is whatever shape its stage needs — `labels` is keyed by head and
    nothing else — so writing a timestamp into it puts a string where every
    reader expects a cell, which is exactly the crash the first version of this
    produced.
    """
    stamps = {name: readout["taken_at"] for name in chosen}
    if set(chosen) == set(STAGES) or not readout_path().is_file():
        readout["stage_taken_at"] = {name: stamps[name] for name in STAGES if name in stamps}
        return []
    previous = json.loads(readout_path().read_text(encoding="utf-8"))
    before = previous.get("stage_taken_at") or {}

    carried = []
    for name in STAGES:
        if name in chosen or name not in previous.get("stages", {}):
            continue
        readout["stages"][name] = previous["stages"][name]
        stamps[name] = before.get(name) or previous.get("taken_at")
        carried.append({"stage": name, "taken_at": stamps[name]})
    readout["stage_taken_at"] = {name: stamps[name] for name in STAGES if name in stamps}
    if carried:
        held = {entry["stage"] for entry in carried}
        rows.extend(row for row in _stored_rows() if row.get("stage") in held)
        readout["carried"] = carried
        readout["population"] = {**previous.get("population", {}), **readout["population"]}
        log(f"[census] carried forward: {', '.join(sorted(held))}")
    # The stages are written in the census's own order however they were merged, so
    # two artifacts are diffable whichever stages each run computed.
    ordered = {name: readout["stages"][name] for name in STAGES if name in readout["stages"]}
    readout["stages"] = ordered
    return carried


def _stored_rows() -> list[dict]:
    """Whatever the rows file already holds, or nothing if it is not there."""
    path = rows_path()
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _population(chosen: tuple[str, ...]) -> dict:
    """What this census was taken over, so two runs can be told apart by more than a date."""
    from fractal_wallpapers.curation import gallery_store, records

    population: dict = {"baseline": BASELINE}
    if {"picks", "survival"} & set(chosen):
        release = records.read_decisions(records.RELEASE)
        store = gallery_store.read()
        population["pool"] = {
            "release_rows": len(release),
            "gallery_store_rows": len(store),
            "runs": sorted({str(row.get("run")) for row in release}),
            "passes": sorted({str(row.get("run")) for row in store}),
        }
    return population
