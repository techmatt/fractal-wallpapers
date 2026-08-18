"""Importing the source project's location labels as flat rows.

Eleven thousand human verdicts exist, and they were expensive. They live in
another repository under a store that grew eleven versions of overlay, sidecar
and registry machinery, and none of that machinery is coming here: this module
reads that store **through its own canonical reader**, resolves every label once,
and writes the answer as flat rows this repository's store understands.

Four rules govern the read, and each one is a way the import could be silently
wrong:

* **The label comes from the source's `label_store.resolve_score`, never from a
  batch's `images.jsonl`.** A third of that corpus carries its labels in
  registered sidecar files that were never merged in-row, and a reader that
  looked at the row's own `score` field would drop them — for one family it would
  drop every label there is. The amendment overlay is applied at the same call:
  a thousand rows were re-judged later and the revision is the verdict.
* **Revision rows carry no label of their own.** A row that re-judges another row
  writes its verdict into the amendment stream, and counting it too would double
  the sample it was drawn to correct.
* **The join is the location, not the image id.** Image ids there are unique
  within a batch and collide across batches built at different scales, so a
  label joined by id can reach a same-id crop of a different picture. Locations
  are keyed here through [`fractal_wallpapers.supply.location`] — the same
  adapter the supply census suppresses machine stock through, so the two sides
  cannot disagree about what one place is.
* **A location's label is the maximum over its crops.** One location appears
  several times there, recolored and reframed; the verdict on the *place* is the
  best any of those got.

## What comes across, and what does not

Rows. One flat row per location, carrying its whole join. No overlay, no
sidecars, no registry of which file a batch's labels are hiding in — resolution
happened here, once, and the store on this side has its own append-only revision
rule which owes nothing to that history.

Every batch is renamed on the way in, and every one is registered with the method
that drew it. **The two registration flags are transferred from the source's own
registry, not restated**, and its fail-closed default comes with them: a batch
nobody registered there is not score-unconditioned here either. The import
verifies each transferred flag against that registry row by row and refuses to
write anything if one disagrees.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from fractal_wallpapers.labeling import registry as registry_module
from fractal_wallpapers.labeling import split as split_module
from fractal_wallpapers.labeling import store
from fractal_wallpapers.supply.location import location_key
from fractal_wallpapers.supply.partitions import partition_of_family


class CorpusImportError(RuntimeError):
    """The import cannot proceed, and guessing would be worse than stopping."""


@dataclass(frozen=True)
class Imported:
    """Where one source population lands here, and how it was drawn.

    `partition_prefix` narrows an entry to part of a batch, for the one source
    batch that holds two populations: a base-rate draw over the dynamical planes
    and the screened parameter-plane rows of the same run. Two generation
    methods are two registrations, or the distinction stops being recoverable.
    """

    batch: str
    method: str
    score_unconditioned: bool = False
    anchored: bool = False
    why: str = ""
    partition_prefix: str | None = None


#: Every source batch that holds a location label, the name it lands under here,
#: and its registration. Entries are ordered within a batch: the first whose
#: `partition_prefix` matches wins, so a narrowed entry precedes the catch-all.
#:
#: **The keys are the source project's directory names, verbatim.** They are the
#: only names here the naming rule does not reach: renaming one does not rename a
#: directory in a repository this one may not write to, it breaks the read. The
#: values are where the rule applies, and every one of them is renamed on the way
#: in. `tests/test_banned_vocabulary.py` names the two keys carrying old
#: vocabulary, as literals, so the exception is that wide and no wider.
SOURCES: dict[str, tuple[Imported, ...]] = {
    "2026-06-23_flat_generate_loose0_v3": (
        Imported(
            batch="flat_draw_mandelbrot",
            method="unscreened flat draw over the mandelbrot parameter plane",
            score_unconditioned=True,
            why="no score anywhere in the selection, so a keeper rate read on it is the "
            "plane's own base rate — the only such draw the parameter planes have",
        ),
    ),
    "2026-06-24_guided_descend_rev4": (
        Imported(
            batch="guided_descent_rev4",
            method="guided descent into the mandelbrot plane, screened at every rung",
            why="the descent's own screens chose which frames survived to be judged",
        ),
    ),
    "2026-06-24_guided_descend_rev4occfix_v2filtered": (
        Imported(
            batch="guided_descent_rev4_refiltered",
            method="the same descent re-run with a corrected occupancy gate, then filtered",
            why="screened twice; the filter is a second selection on the same population",
        ),
    ),
    "2026-06-25_mining_v3guided_v1": (
        Imported(
            batch="guided_descent_v3_recolors",
            method="one guided-descent population rendered through several colormaps",
            why="descent-screened, and drawn to vary the coloring rather than the place",
        ),
    ),
    "2026-06-25_scale_2x2_labelset": (
        Imported(
            batch="scale_sweep",
            method="one population rendered at two scales, to read scale against taste",
            why="the population underneath it is a screened descent",
        ),
    ),
    "2026-06-25_scale_controlled_2x2": (
        Imported(
            batch="scale_sweep_controlled",
            method="the scale sweep's control arm, at a fixed scale",
            why="the same screened population as the sweep it controls",
        ),
    ),
    "2026-07-05_gather_v6": (
        Imported(
            batch="gather_v6",
            method="the v6 run's ranked queue, across every family",
            why="rank-ordered by the run's own screen, so no rate on it is a base rate",
        ),
    ),
    "2026-07-11_jm3_band_v1": (
        Imported(
            batch="julia_multibrot3_score_band",
            method="drawn from one band of a head's score on the degree-3 julia plane",
            why="a model's score chose the band, which is the disqualifying selection",
        ),
    ),
    "2026-07-12_jm45_band_v1": (
        Imported(
            batch="julia_multibrot45_score_band",
            method="the same score-band draw on the degree-4 and degree-5 julia planes",
            why="a model's score chose the band",
        ),
    ),
    "2026-07-12_blindspot_v6reject_v1": (
        Imported(
            batch="v6_rejects",
            method="the v6 run's rejected candidates, drawn deliberately",
            why="negative by construction: any separation measured on it is inflated",
        ),
    ),
    "2026-07-17_prospect_run1_baserate_v1": (
        Imported(
            batch="descent_base_rate_julia",
            method="base-rate draw over one descent run's output, dynamical planes",
            score_unconditioned=True,
            partition_prefix="julia:multibrot",
            why="unbiased given the descent that produced the population — the only draw "
            "over descent output with no score in the selection",
        ),
        Imported(
            batch="descent_base_rate_native",
            method="the same run's parameter-plane rows, which the descent screened",
            why="screened by the descent that produced them, so not a base rate",
        ),
    ),
    "2026-07-17_prospect_run1_baserate_R_v1": (
        Imported(
            batch="descent_base_rate_julia",
            method="base-rate draw over one descent run's output, dynamical planes",
            score_unconditioned=True,
            partition_prefix="julia:multibrot",
            why="the replicate half of the same draw; one method, one registration",
        ),
        Imported(
            batch="descent_base_rate_native",
            method="the same run's parameter-plane rows, which the descent screened",
            why="screened by the descent that produced them, so not a base rate",
        ),
    ),
    "2026-07-21_phoenix_grid": (
        Imported(
            batch="phoenix_parameter_grid",
            method="a grid over the phoenix parameter space, stratified on a head's score",
            why="the strata came from a model score; the grid also samples no population "
            "anything downstream draws from",
        ),
    ),
    "2026-07-22_native_multibrot_band_v1": (
        Imported(
            batch="multibrot_score_band",
            method="stratified across a head's score bands on the native multibrot planes",
            why="a model's score chose the strata, rejected rows included",
        ),
    ),
    "2026-07-26_anchor_class4_v1": (
        Imported(
            batch="top_tier_anchor",
            method="a cross-family handful judged together to fix where the top tier sits",
            why="it calibrates a bar and estimates no population",
        ),
    ),
    "2026-07-26_minibrot_roster_v2": (
        Imported(
            batch="minibrot_roster",
            method="one frame per solved nucleus, over the parameter planes",
            why="systematic, but never registered as an instrument in the corpus it came "
            "from, and this import does not promote a population its own project did not",
        ),
    ),
    "2026-07-27_interior_band_v1": (
        Imported(
            batch="interior_band",
            method="uniform over the high-interior band a discovery gate discards",
            why="a hard-negative source by construction; its class mix is the band's, "
            "not any population's",
        ),
    ),
    "2026-08-01_supply_crawl_exemplar_v1": (
        Imported(
            batch="crawl_exemplar",
            method="the crawl rows nearest a chosen exemplar",
            why="selected on a similarity score",
        ),
    ),
    "2026-08-01_supply_crawl_strat_a_v1": (
        Imported(
            batch="crawl_stratified_a",
            method="round robin over degree, operator and screen-score bin",
            why="a screen score chose the strata, so biased by construction — and "
            "deliberately spans every bin, which most train-side material does not",
        ),
    ),
    "2026-08-01_supply_crawl_strat_b_v1": (
        Imported(
            batch="crawl_stratified_b",
            method="round robin over degree, operator and screen-score bin",
            why="the second arm of the same stratified draw",
        ),
    ),
    "2026-08-01_supply_crawl_uniform_v1": (
        Imported(
            batch="crawl_uniform",
            method="uniform over everything one crawl recorded",
            score_unconditioned=True,
            why="no score anywhere in the selection; the only unconditioned read of what "
            "a walk actually emits",
        ),
    ),
    "2026-08-02_label_seeded_v2_a": (
        Imported(
            batch="label_seeded_a",
            method="descended from the corpus's own keepers, queued by a fitted score",
            why="conditioned twice: on the seed locations' labels and on the queue's score",
        ),
    ),
    "2026-08-02_label_seeded_v2_b": (
        Imported(
            batch="label_seeded_b",
            method="descended from the corpus's own keepers, queued by a fitted score",
            why="the second arm of the same seeded draw",
        ),
    ),
    "2026-08-03_q4_harvest_ranked_v1": (
        Imported(
            batch="harvest_ranked",
            method="the top of a harvest run's own ranked queue",
            why="a keeper rate on it is a statement about the ranker",
        ),
    ),
    "2026-08-03_q4_near_minibrot_v1": (
        Imported(
            batch="near_minibrot_ladder",
            method="a ladder around solved nuclei, whose rows still passed the run's screens",
            why="systematic in its geometry, screened in what reached the page",
        ),
    ),
    "2026-08-03_q4_uniform_eval_v1": (
        Imported(
            batch="parameter_space_uniform",
            method="systematic draws over a family's parameter space, taken before the "
            "run scored anything",
            score_unconditioned=True,
            why="no score in the selection, by construction and by timing — but short "
            "everywhere it is needed, and it measures zero keepers on three partitions",
        ),
    ),
    "2026-08-03_v2_sitting_v1": (
        Imported(
            batch="screened_queue_v2",
            method="a record-and-rank queue, tier-sorted and cut by three filters",
            why="screened and rank-ordered; no rate on it is a base rate",
        ),
    ),
    "2026-08-05_steady_state_dive_v1": (
        Imported(
            batch="steady_state_dive",
            method="single-track descent from one crawl's admissions",
            why="biased at the source and at every rung; its two arms are confounded with "
            "the partition they landed in, so the contrast between them is unreadable",
        ),
    ),
    "2026-08-05_steady_state_ranked_v1": (
        Imported(
            batch="steady_state_ranked",
            method="the steady-state crawl's ranked residue, tier-sorted",
            why="a cheap score decided which candidates earned a full confirmation, and "
            "the rank is built from those scores",
        ),
    ),
    "2026-08-07_label_run_correction_v1": (
        Imported(
            batch="correction_page",
            method="a bucketed queue served with a head's own decode prefilled and the "
            "page ordered by its score",
            anchored=True,
            why="the labels are anchored to the head that suggested them, so a rate on it "
            "measures agreement with that head and never a population",
        ),
    ),
    "2026-08-07_steady_state_v2_backfill_v1": (
        Imported(
            batch="correction_page_backfill",
            method="the same correction page, backfilled where a bucket ran short",
            anchored=True,
            why="same page, same anchoring; a separate registration because 'this row is "
            "here because a bucket could not be filled' is part of how it was selected",
        ),
    ),
    "julia_ladder_j0": (
        Imported(
            batch="julia_parameter_ladder",
            method="a ladder over julia parameters at assorted frames",
            why="ranked and banded on the way in",
        ),
    ),
}


def target(source_batch: str, partition: str) -> Imported | None:
    """Where one row lands: the first entry whose prefix matches, else `None`."""
    for entry in SOURCES.get(source_batch, ()):
        if entry.partition_prefix is None or partition.startswith(entry.partition_prefix):
            return entry
    return None


def registrations() -> list[registry_module.Registration]:
    """One registration per landing batch, deduplicated and self-checked."""
    out: dict[str, registry_module.Registration] = {}
    for entries in SOURCES.values():
        for entry in entries:
            registration = registry_module.Registration(
                batch=entry.batch,
                method=entry.method,
                score_unconditioned=entry.score_unconditioned,
                anchored=entry.anchored,
                why=entry.why,
            )
            seen = out.get(entry.batch)
            if seen is not None and (
                seen.score_unconditioned != registration.score_unconditioned
                or seen.anchored != registration.anchored
            ):
                raise CorpusImportError(
                    f"{entry.batch!r} is registered twice with different flags. Two "
                    f"populations that were drawn differently are two batches."
                )
            out.setdefault(entry.batch, registration)
    return [out[name] for name in sorted(out)]


# --------------------------------------------------------------------------- #
# The adapter: one source render block -> this repository's location identity.
# --------------------------------------------------------------------------- #

#: The source's render-family token, and what this repository calls that family.
#: Its degree lives in the token there and in a field here.
FAMILIES = {
    "mandelbrot": ("mandelbrot", 2),
    "multibrot3": ("multibrot", 3),
    "multibrot4": ("multibrot", 4),
    "multibrot5": ("multibrot", 5),
    "julia": ("julia", 2),
    "julia_multibrot3": ("julia", 3),
    "julia_multibrot4": ("julia", 4),
    "julia_multibrot5": ("julia", 5),
    "phoenix": ("phoenix", 2),
}

#: The source's phoenix constant names, in this repository's spelling.
PHOENIX_CONSTANTS = {"c": ("c_re", "c_im"), "p": ("p_re", "p_im"), "z_prev": ("zm1_re", "zm1_im")}


def _decimal(value):
    """A coordinate as the decimal string it should always have been.

    One source batch wrote its seed constants as JSON *numbers* on every row. A
    number is not a coordinate here — the string is the identity and the float is
    a lossy view of it — so it is converted at the reader, where a derived record
    belongs, and counted.
    """
    if value is None or isinstance(value, str):
        return value, False
    return repr(float(value)), True


def location_of(render: dict, fractal_type: str) -> tuple[dict, dict, int]:
    """`(family, viewport, coordinates coerced)` for one source render block."""
    if fractal_type not in FAMILIES:
        raise CorpusImportError(f"unknown source family {fractal_type!r}")
    kind, degree = FAMILIES[fractal_type]
    coerced = 0

    family: dict = {"kind": kind}
    if kind in ("multibrot", "julia"):
        family["degree"] = degree
    if kind == "julia":
        c_re, moved_re = _decimal(render.get("c_re"))
        c_im, moved_im = _decimal(render.get("c_im"))
        coerced += moved_re + moved_im
        if c_re is None or c_im is None:
            raise CorpusImportError("a julia row carries no seed c; half its identity is missing")
        family["c"] = [c_re, c_im]
    if kind == "phoenix":
        for name, (re_key, im_key) in PHOENIX_CONSTANTS.items():
            value_re, moved_re = _decimal(render.get(re_key))
            value_im, moved_im = _decimal(render.get(im_key))
            coerced += moved_re + moved_im
            if value_re is not None and value_im is not None:
                family[name] = [value_re, value_im]

    viewport = {}
    for key, source_key in (("center_re", "cx"), ("center_im", "cy"), ("width", "fw")):
        value, moved = _decimal(render[source_key])
        coerced += moved
        viewport[key] = value
    return family, viewport, coerced


def render_of(render: dict) -> dict:
    """The render parameters that survive the fold onto a location.

    Resolution, sampling and the iteration cap describe the *location* as it was
    judged. The palette and the composition offset do not: they vary across the
    crops of one location, and the location's verdict is the best of them, so
    carrying one crop's coloring would attach it to a label that is not only
    about that crop.
    """
    out = {
        "resolution": [int(render.get("width", 1280)), int(render.get("height", 720))],
        "supersample": int(render.get("ss", 1)),
        "mode": "smooth",
    }
    if render.get("maxiter") is not None:
        out["maxiter"] = int(render["maxiter"])
    return out


# --------------------------------------------------------------------------- #
# The read.
# --------------------------------------------------------------------------- #


def _source_modules(root: Path):
    """Load the source project's own reader, registry and family map.

    Imported rather than reimplemented, on purpose: a second copy of the
    resolution rule is a second answer to "what score does this row have", and
    the whole reason this import routes through their reader is that theirs is
    the one that knows where each batch's labels are.
    """
    for relative in (("tools", "corpus"), ("tools", "scoring")):
        directory = str(Path(root).joinpath(*relative))
        if directory not in sys.path:
            sys.path.insert(0, directory)
    try:
        import batch_registry
        import label_store
        import partitions
    except ModuleNotFoundError as missing:
        raise CorpusImportError(
            f"{root} does not look like the source corpus: {missing}. It needs "
            f"tools/corpus/label_store.py and tools/scoring/batch_registry.py."
        ) from missing
    return label_store, batch_registry, partitions


def _fractal_type(row: dict, fam2ft: dict) -> str:
    """The source's family token for a row: its provenance first, its render second."""
    family = (row.get("provenance") or {}).get("family")
    if family and family in fam2ft:
        return fam2ft[family]
    return row["render"].get("fractal_type") or "mandelbrot"


@dataclass
class Location:
    """One imported location, folded over every crop that carried a verdict."""

    family: dict
    viewport: dict
    render: dict
    score: int
    origin: str
    labeler: str | None
    batches: set
    recorded_at: str


def read_corpus(root: Path) -> tuple[dict, dict]:
    """`({location key: Location}, report)` — every labeled location, resolved."""
    label_store, batch_registry, partitions = _source_modules(root)
    root = Path(root)
    batches = sorted((root / "data" / "label_corpus" / "batches").glob("*/images.jsonl"))
    if not batches:
        raise CorpusImportError(f"no batches under {root / 'data' / 'label_corpus' / 'batches'}")

    locations: dict = {}
    report = {
        "batches": len(batches),
        "rows": 0,
        "labeled_rows": 0,
        "revision_rows": 0,
        "coerced_coordinates": 0,
        "unmapped": Counter(),
        "flag_disagreements": [],
        "per_batch": Counter(),
    }

    for path in batches:
        source_batch = path.parent.name
        sidecar = label_store.sidecar_for(source_batch)
        amendments = label_store.amendments_for(source_batch)
        created = _created(path.parent)
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                report["rows"] += 1
                provenance = row.get("provenance") or {}
                if provenance.get("revises_batch_id") and provenance.get("revises_image_id"):
                    report["revision_rows"] += 1
                    continue
                score = label_store.resolve_score(row, sidecar, amendments)
                if score is None:
                    continue
                report["labeled_rows"] += 1

                fractal_type = _fractal_type(row, partitions.FAM2FT)
                family, viewport, coerced = location_of(row["render"], fractal_type)
                report["coerced_coordinates"] += coerced
                partition = partition_of_family(family)
                entry = target(source_batch, partition)
                if entry is None:
                    report["unmapped"][source_batch] += 1
                    continue
                registered = batch_registry.lookup(source_batch, fractal_type)
                if registered.score_unconditioned != entry.score_unconditioned:
                    report["flag_disagreements"].append(
                        f"{source_batch}/{fractal_type} -> {entry.batch}: source says "
                        f"score_unconditioned={registered.score_unconditioned}, this table "
                        f"says {entry.score_unconditioned}"
                    )
                    continue

                report["per_batch"][entry.batch] += 1
                key = location_key(family, viewport)
                labeler = (row.get("label") or {}).get("labeler")
                origin = store.HUMAN
                if isinstance(labeler, str) and labeler.startswith(store.RULE_PREFIX):
                    origin, labeler = labeler, None
                found = locations.get(key)
                if found is None:
                    locations[key] = Location(
                        family=family,
                        viewport=viewport,
                        render=render_of(row["render"]),
                        score=int(score),
                        origin=origin,
                        labeler=labeler,
                        batches={entry.batch},
                        recorded_at=created,
                    )
                    continue
                found.batches.add(entry.batch)
                found.recorded_at = max(found.recorded_at, created)
                if int(score) > found.score:
                    # The verdict on a place is the best any of its crops earned,
                    # and the render block recorded is the one that earned it.
                    found.score = int(score)
                    found.render = render_of(row["render"])
                    found.origin = origin
                    found.labeler = labeler

    if report["unmapped"]:
        raise CorpusImportError(
            "these source batches carry labels and are not in SOURCES: "
            f"{dict(report['unmapped'])}. A batch imported without a registration would "
            "arrive with no record of how its rows were chosen."
        )
    if report["flag_disagreements"]:
        raise CorpusImportError(
            "the registration table disagrees with the source registry:\n  "
            + "\n  ".join(sorted(set(report["flag_disagreements"])))
        )
    report["locations"] = len(locations)
    report["per_batch"] = dict(report["per_batch"])
    del report["unmapped"]
    del report["flag_disagreements"]
    return locations, report


def _created(directory: Path) -> str:
    """The date a source batch says it was created, for the row's `recorded_at`.

    Its labels carry no timestamp of their own — every one of them is null — so
    the batch's own date is the most precise honest answer, and it is enough for
    the store's total order because it sorts before any timestamp written here.
    """
    manifest = directory / "batch.json"
    if manifest.is_file():
        created = json.loads(manifest.read_text(encoding="utf-8")).get("created")
        if isinstance(created, str) and created:
            return created
    return directory.name[:10] if directory.name[:4].isdigit() else "1970-01-01"


def owning_batch(batches: set, known: dict) -> str:
    """Which batch a location belongs to when several labeled it.

    The conservative one: if any contributor is not eval-eligible, the location
    is owned by the first such batch and can never reach the evaluation side.
    Eligibility over a location is an AND over everything that touched it, and
    routing the fold through the owning batch means the store carries it as one
    fact on the row instead of as a rule every reader has to remember.
    """
    ordered = sorted(batches)
    for name in ordered:
        if not registry_module.eval_eligible(known, name):
            return name
    return ordered[0]


def rows_of(locations: dict, known: dict) -> dict[str, list[dict]]:
    """`{batch: [label row, ...]}` — one row per location, ready for the writer."""
    out: dict[str, list[dict]] = {}
    for _key, location in sorted(locations.items(), key=lambda item: repr(item[0])):
        owner = owning_batch(location.batches, known)
        extra = {}
        others = sorted(location.batches - {owner})
        if others:
            extra["also_labeled_in"] = others
        out.setdefault(owner, []).append(
            store.label_row(
                batch=owner,
                score=location.score,
                family=location.family,
                viewport=location.viewport,
                render=location.render,
                origin=location.origin,
                labeler=location.labeler,
                recorded_at=location.recorded_at,
                **extra,
            )
        )
    return out


def run(root: Path, seed: int = split_module.SEED, share: float = split_module.EVAL_SHARE) -> dict:
    """Read the source corpus, write the rows, and draw the split. The whole import."""
    locations, report = read_corpus(Path(root))
    prepared = registrations()

    # Nothing is written until every landing file is known to be absent: this
    # import writes each batch once, and a second run that appended would double
    # every location it had already brought across.
    occupied = [
        str(store.batch_path(r.batch)) for r in prepared if store.batch_path(r.batch).exists()
    ]
    if occupied:
        raise CorpusImportError(
            f"these files already hold rows: {occupied}. Run the import into a clean store "
            f"rather than appending a second copy of every location."
        )

    for registration in prepared:
        store.register(registration)
    known = store.registry()

    written = {}
    for batch, rows in sorted(rows_of(locations, known).items()):
        store.append(rows, known=known)
        written[batch] = len(rows)

    resolution = store.resolved()
    drawn = split_module.derive(resolution.scored(), known=known, seed=seed, share=share)
    split_module.write(drawn)

    scores = Counter(row["score"] for row in resolution.scored())
    partitions = Counter(partition_of_family(row["family"]) for row in resolution.scored())
    report["written"] = written
    report["store"] = resolution.summary()
    report["scores"] = {str(k): scores[k] for k in sorted(scores)}
    report["partitions"] = dict(sorted(partitions.items()))
    report["split"] = drawn.recipe()
    return report


__all__ = [
    "FAMILIES",
    "PHOENIX_CONSTANTS",
    "SOURCES",
    "CorpusImportError",
    "Imported",
    "Location",
    "location_of",
    "owning_batch",
    "read_corpus",
    "registrations",
    "render_of",
    "rows_of",
    "run",
    "target",
]
