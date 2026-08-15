"""Importing the source project's finished-render corpora as flat rows.

Nearly eight thousand human verdicts on finished pictures exist over there, in
two corpora that were built a month apart under different conventions and are
read by different code. Neither of those readers is coming here. This module
reads both **through the source's own resolution rules**, checks the answer
against the source's own registry, and writes flat rows this repository's
finished-render stores understand.

## What resolves a label, and why it is not the location corpus's rule

The location corpus hides a third of its labels in registered sidecars and needs
an amendment overlay to say what a row's verdict is. **Neither corpus here does
either.** Every finished-render batch exports one file, `labels/<generator
version>.json`, keyed by `image_id`, and every one of them was labeled
**completely** — so the rule is a join by id, and a row without a label or a label
without a row is an error rather than a row to skip. That is the source's own
rule for these corpora, in both of its readers, and it is asserted here in both
directions.

## The join is the picture, not the place

Over in the location store a row is a place and its verdict is the best any crop
of it earned. Here a row **is** a crop: the same location appears a dozen times
at a dozen recipes and the verdicts genuinely differ, so nothing is folded. What
travels with each verdict is everything needed to make that picture again —
family, viewport, iteration cap, geometry, mode, map, and every knob of the
palette pass.

Two things are converted rather than copied, and both are renames of one fact:

* the source's four composite and curvature mode names are this repository's
  own — a name that needs a version number in it is the wrong name;
* the source's `log_premap` is this repository's `transform`, because they are
  the same slot. It **replaces** the mode's own curve, exactly as the source's
  render path replaces it, rather than composing with it.

## The flags travel, and the source registry is the authority

Three registrations reach a row's batch, and each is read from the source rather
than restated here:

* `score_unconditioned` — from `batch_registry`, the source's single owner of
  that classification, per batch. Every finished-render batch is `False` there
  and the reason is worth carrying: quality is conditioned through the *location*
  head before any of these pages was drawn, so no rate on any of them is a
  location base rate. That is a fact about a different head and it is not a
  defect.
* `anchored` — from the batch's own record, which says in its own words whether
  the page served a suggestion prefilled and sorted by a head's score, or was
  served blind. It is the flag that decides train from eval here.
* `eval_only` — from the batch's own record too. Two batches carry it, they are
  the two blind sheets, and they are the whole evaluation side.

Every one is checked against the table below, row by row, and **nothing is
written if a single one disagrees**. A table that quietly lost an argument with
the registry is how a blind sheet ends up in a training split.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from fractal_wallpapers.labeling import finished
from fractal_wallpapers.labeling import registry as registry_module
from fractal_wallpapers.palettes import library_import
from fractal_wallpapers.paths import colormap_dir
from fractal_wallpapers.supply.partitions import partition_of_family


class FinishedImportError(RuntimeError):
    """The import cannot proceed, and guessing would be worse than stopping."""


#: The source's family token, and what this repository calls that family. Its
#: degree lives in the token there and in a field here.
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

#: The source's mode names, in this repository's spelling. Only the four that
#: differ are listed; a name absent from here has to already exist in the mode
#: catalog, and the import refuses one that does not.
MODES = {
    "curv_linear": "curvature",
    "composite_c7_smooth_trap_circle": "smooth_trap_circle",
    "composite_c13_smooth_stripe": "smooth_stripe",
    "composite_c17_smooth_curvature": "smooth_curvature",
}

#: `log_premap` is a curve on the normalized field, which is what this
#: repository calls a transform.
CURVES = {"none": "linear", "log": "log"}

#: A direct trap's own settings, in this repository's spelling. Both are swept
#: across three values each by one sheet, so they separate rows of one place in
#: one mode and are part of the join rather than of the mode's name.
TRAP_SETTINGS = {"direct_opacity": "opacity", "direct_threshold": "threshold"}

#: The highlight rolloff, as the source spells it. `soft_knee@0.35` is the only
#: one either corpus used, and it is how every screening-trap row was rendered
#: rather than a variation across them.
ROLLOFFS = {
    "none": {"kind": "none"},
    "soft_knee@0.35": {"kind": "soft_knee", "knee": 0.35},
}


@dataclass(frozen=True)
class Imported:
    """Where one source batch lands here, and what its registration says."""

    batch: str
    method: str
    anchored: bool
    eval_only: bool
    why: str


#: Every finished-render batch that carries a label, the name it lands under, and
#: its registration. `score_unconditioned` is absent on purpose: it is read from
#: the source registry per batch and is never restated here.
SOURCES: dict[str, dict[str, Imported]] = {
    "smooth_render": {
        "2026-07-05_wallpaper_bootstrap_v1": Imported(
            batch="pool_draw_bootstrap",
            method="the first sheet: locations from the standing pool, colored by a "
            "palette-pool draw",
            anchored=False,
            eval_only=False,
            why="judged before any finished-render head existed, so nothing could have "
            "prefilled it — but its locations came from a pool the location head had "
            "already admitted, which is why it is not an instrument",
        ),
        "2026-07-05_wallpaper_humanq3_v1": Imported(
            batch="pool_draw_human_good",
            method="the same pool narrowed to locations a human had already called good",
            anchored=False,
            eval_only=False,
            why="quality is conditioned on before the page is drawn, by a human rather "
            "than a model; what is left to judge is the coloring",
        ),
        "2026-07-09_wallpaper_headbatch_dramatic_v1": Imported(
            batch="dramatic_palettes",
            method="one location set rendered through the dramatic palette family, at "
            "widely varied recipes",
            anchored=False,
            eval_only=False,
            why="the recipe axis is the point of it: the palette knobs are drawn wide "
            "deliberately, so the tier mix is the draw's and not any population's",
        ),
        "2026-08-05_wallpaper_fresh_sheet_v1": Imported(
            batch="fresh_pool_draw",
            method="locations from the current admitted intake, colored by a pool draw",
            anchored=True,
            eval_only=False,
            why="a correction sheet: the incumbent's suggested tier was prefilled and "
            "the page ordered by its score, so a rate on it measures agreement with it",
        ),
        "2026-08-05_wallpaper_colorize_path_v1": Imported(
            batch="fresh_colorize_path",
            method="the same intake colored the way a release run colors it, one render "
            "per location",
            anchored=True,
            eval_only=False,
            why="same labeling run, same anchoring; a separate registration because the "
            "coloring regime is the contrast the pair was built to read",
        ),
        "2026-08-10_wallpaper_correction_v2": Imported(
            batch="bucketed_correction",
            method="a bucketed sweep of the intake, one render per location at the "
            "incumbent's own best-scoring map",
            anchored=True,
            eval_only=False,
            why="anchored twice over: two of its buckets are cut on the incumbent's "
            "screen score and every row is the map that head liked best",
        ),
        "2026-08-11_wallpaper_blind_minibrot_v1": Imported(
            batch="blind_minibrot",
            method="fresh minibrot-centred locations, colored by the release path, served "
            "blind in a seeded shuffle",
            anchored=False,
            eval_only=True,
            why="THE INSTRUMENT. No suggestion prefilled, no score ordering the page, and "
            "no finished-render head anywhere in the draw or the coloring. Bought to "
            "referee two heads on unanchored labels, and spent the moment it trains",
        ),
    },
    "strange_render": {
        "2026-08-06_render_mode_fresh_sheet_v1": Imported(
            batch="mode_sweep",
            method="the first strange sheet: admitted locations across the whole mode "
            "roster, apportioned by a seeded draw",
            anchored=True,
            eval_only=False,
            why="a correction sheet: the incumbent's tier was prefilled and the page "
            "ordered by its score",
        ),
        "2026-08-10_render_mode_correction_v2": Imported(
            batch="mode_correction",
            method="the unserved mode-and-location pairs of the same population, with the "
            "busy modes deliberately over-drawn at high score",
            anchored=True,
            eval_only=False,
            why="anchored, and non-representative on purpose — it is aimed at where the "
            "incumbent was suspected of being wrong, so no rate on it is a base rate",
        ),
        "2026-08-10_render_mode_rare_palette_v1": Imported(
            batch="rare_palette",
            method="locations carrying a top human tier, rendered through the rare hue "
            "families the pool draw under-serves",
            anchored=True,
            eval_only=False,
            why="anchored, and drawn against the palette distribution rather than from "
            "it; location quality is conditioned on by a human before the page exists",
        ),
        "2026-08-11_render_mode_baserate_audit_v1": Imported(
            batch="baserate_audit",
            method="the blind sheet's draw rule re-run — flat mode apportionment, pool "
            "palette, no head in the selection — and then served anchored",
            anchored=True,
            eval_only=False,
            why="THE DRAW IS UNCONDITIONED AND THE PAGE IS NOT, and the second half is "
            "what decides: the incumbent's tier is prefilled and orders the page, so "
            "its labels are ceilings and it may never join the blind sheet",
        ),
        "2026-08-11_render_mode_blind_v1": Imported(
            batch="blind_modes",
            method="fresh location-and-mode pairs no prior sheet served, pool palette, "
            "served blind in a seeded shuffle",
            anchored=False,
            eval_only=True,
            why="THE INSTRUMENT. Every other strange batch is a correction sheet served "
            "with the incumbent's own verdict, so this is the only unanchored reading of "
            "this population that exists",
        ),
    },
}

#: The source corpus each store is imported from.
CORPORA = {"smooth_render": "wallpaper_corpus", "strange_render": "render_mode_corpus"}


def _source_registry(root: Path):
    """Load the source project's own batch registry — imported, not reimplemented.

    It is the single owner of `score_unconditioned` over there, and a second copy
    of that table here would be a second answer to whether a population may be an
    instrument.
    """
    directory = str(Path(root) / "tools" / "scoring")
    if directory not in sys.path:
        sys.path.insert(0, directory)
    try:
        import batch_registry
    except ModuleNotFoundError as missing:
        raise FinishedImportError(
            f"{root} does not look like the source corpus: {missing}. It needs "
            f"tools/scoring/batch_registry.py, which owns the split classification."
        ) from missing
    return batch_registry


def batch_dir(root: Path, head: str, source_batch: str) -> Path:
    return Path(root) / "data" / CORPORA[head] / "batches" / source_batch


def read_record(root: Path, head: str, source_batch: str) -> dict:
    path = batch_dir(root, head, source_batch) / "batch.json"
    if not path.is_file():
        raise FinishedImportError(f"{path} is missing — that batch has no record of itself")
    return json.loads(path.read_text(encoding="utf-8"))


def anchoring_of(record: dict) -> bool:
    """Whether the page served a head's own verdict, from the batch's own words.

    A batch says which it was in `labeling.mode`, and the two spellings are the
    two things a page can be: a **correction** sheet shows a suggested tier
    prefilled, and a **blind** one shows nothing. A batch that says neither is
    refused rather than assumed unanchored — an early sheet with no such block
    is handled by [`Imported.anchored`] and checked against the absence.
    """
    mode = ((record.get("labeling") or {}).get("mode") or "").strip().lower()
    if not mode:
        return False
    if mode.startswith("blind"):
        return False
    if mode.startswith("correction"):
        return True
    raise FinishedImportError(
        f"batch {record.get('batch_id') or record.get('generator_version')!r} describes its "
        f"page as {mode[:40]!r}, which is neither a correction sheet nor a blind one. "
        f"Whether a head's verdict was prefilled decides which side the batch may reach."
    )


def registrations(root: Path, head: str) -> list[registry_module.Registration]:
    """One registration per landing batch, with every flag checked against the source."""
    source_registry = _source_registry(root)
    out: list[registry_module.Registration] = []
    disagreements: list[str] = []
    for source_batch, entry in sorted(SOURCES[head].items()):
        record = read_record(root, head, source_batch)
        unconditioned = source_registry.lookup(source_batch, "mandelbrot").score_unconditioned
        anchored = anchoring_of(record)
        eval_only = bool(record.get("eval_only"))
        if anchored != entry.anchored:
            disagreements.append(
                f"{source_batch}: the batch record says anchored={anchored}, this table "
                f"says {entry.anchored}"
            )
        if eval_only != entry.eval_only:
            disagreements.append(
                f"{source_batch}: the batch record says eval_only={eval_only}, this table "
                f"says {entry.eval_only}"
            )
        if eval_only and not (record.get("eval_only_note") or "").strip():
            disagreements.append(
                f"{source_batch}: pinned eval-only with no note saying what it was bought "
                f"for — the reason cannot be reconstructed from the flag"
            )
        out.append(
            registry_module.Registration(
                batch=entry.batch,
                method=entry.method,
                score_unconditioned=unconditioned,
                anchored=anchored,
                eval_only=eval_only,
                why=entry.why,
            )
        )
    if disagreements:
        raise FinishedImportError(
            "the registration table disagrees with the source:\n  " + "\n  ".join(disagreements)
        )
    return out


def labels_of(root: Path, head: str, source_batch: str) -> dict[str, int]:
    """A batch's exported verdicts, `{image_id: score}`.

    One file per batch, named for the generator version — the rule both of the
    source's own finished-render readers use. The batch's own `labels_export`
    field is checked against it rather than followed, because these two corpora
    disagree about that field and agree about the rule.
    """
    record = read_record(root, head, source_batch)
    version = record.get("generator_version")
    if not version:
        raise FinishedImportError(f"{source_batch}: its record names no generator version")
    path = Path(root) / "labels" / f"{version}.json"
    if not path.is_file():
        raise FinishedImportError(
            f"{path} is missing — {source_batch} is listed as fully labeled and its "
            f"verdicts are the thing being imported."
        )
    document = json.loads(path.read_text(encoding="utf-8"))
    body = document["labels"] if isinstance(document.get("labels"), dict) else document
    out: dict[str, int] = {}
    for image_id, value in body.items():
        if isinstance(value, dict):
            value = value.get("score")
        if value is not None:
            out[image_id] = int(value)
    return out


def family_of(render: dict, provenance: dict) -> dict:
    """The family block, with every constant that is part of the location."""
    token = render.get("fractal_type")
    if token not in FAMILIES:
        raise FinishedImportError(f"unknown source family {token!r}")
    kind, degree = FAMILIES[token]
    family: dict = {"kind": kind}
    if kind in ("multibrot", "julia"):
        family["degree"] = degree
    if kind == "julia":
        if render.get("c_re") is None or render.get("c_im") is None:
            raise FinishedImportError("a julia row carries no seed c; half its identity is gone")
        family["c"] = [str(render["c_re"]), str(render["c_im"])]
    if kind == "phoenix":
        for name, (re_key, im_key) in (
            ("c", ("c_re", "c_im")),
            ("p", ("p_re", "p_im")),
            ("z_prev", ("zm1_re", "zm1_im")),
        ):
            value_re = render.get(re_key, provenance.get(re_key))
            value_im = render.get(im_key, provenance.get(im_key))
            if value_re is not None and value_im is not None:
                family[name] = [str(value_re), str(value_im)]
    return family


def color_params_of(provenance: dict) -> dict:
    """The recipe block, whichever of its two names this corpus wrote it under."""
    params = provenance.get("color_params")
    if params is None:
        params = provenance.get("params")
    if not isinstance(params, dict):
        raise FinishedImportError("a row carries no coloring parameters — its picture is lost")
    return params


def recipe_of(
    params: dict, dropped: bool, cyclic: bool, colormap: str, rolloff: dict | None = None
) -> dict:
    """The palette pass, in this repository's shape.

    Gamma, the traversal and the flip are carried as the row recorded them.
    **Folding is not**: it is a property of the map rather than of the render —
    over there a sequential map is baked folded and a cyclic one is not, and that
    decision is never written on a row. It is re-read from the map's own kind
    here, and asserted against the traversal, because a folded map traversed more
    than once would be two seam fixes fighting.

    The edge transfer is carried at the weight the row recorded **unless** the
    row stamps that its own render dropped it — that render path could not
    express the transfer, so the picture somebody judged had none in it, and
    honouring the requested weight here would color for a picture nobody saw.
    """
    cycles = float(params.get("n_cycles", 1) or 1)
    phase = float(params.get("phase", 0.0) or 0.0)
    if not cyclic and (cycles != 1.0 or phase != 0.0):
        raise FinishedImportError(
            f"a row asks to traverse {colormap!r} {cycles}x from {phase}, but that map does not "
            f"close on the color it opened with — it is folded to hide its seam, and folding a "
            f"repeated traversal is two seam fixes fighting."
        )
    transfer = {"kind": "value"}
    if params.get("transfer") == "grad" and not dropped:
        transfer = {"kind": "edge", "weight": float(params.get("transfer_gamma") or 0.0)}
    return finished.recipe(
        gamma=float(params.get("gamma", 1.0) or 1.0),
        cycles=cycles,
        phase=phase,
        reverse=bool(params.get("reverse")),
        mirror=not cyclic,
        transfer=transfer,
        rolloff=rolloff,
    )


def mode_params_of(render: dict, provenance: dict) -> dict:
    """A mode's own settings, in this repository's spelling.

    Empty for every mode that has none — an empty object rather than an absent
    key, so a row's identity has the same shape whichever mode it is.
    """
    settings = render.get("mode_params")
    if settings is None:
        settings = provenance.get("mode_params")
    out = {}
    for source_name, value in (settings or {}).items():
        if source_name not in TRAP_SETTINGS:
            raise FinishedImportError(
                f"the source set mode parameter {source_name!r}, which this repository has no "
                f"name for. Known: {sorted(TRAP_SETTINGS)}"
            )
        out[TRAP_SETTINGS[source_name]] = float(value)
    return out


def rolloff_of(render: dict, provenance: dict) -> dict:
    """What the render did to its highlights, in this repository's shape."""
    name = render.get("rolloff", provenance.get("rolloff", "none")) or "none"
    if name not in ROLLOFFS:
        raise FinishedImportError(
            f"the source rendered with rolloff {name!r}, which this repository cannot express. "
            f"Known: {sorted(ROLLOFFS)}"
        )
    return ROLLOFFS[name]


def curve_of(params: dict) -> str:
    """The curve the field is read through, in this repository's spelling.

    The source calls it `log_premap` and it takes two values. It is not an extra
    stage on top of a mode's own curve — over there it **replaces** it, for every
    mode, on the way to the renderer — so it lands as this repository's
    `transform` and the mode's own value is overwritten by it.
    """
    name = params.get("log_premap", "none")
    if name not in CURVES:
        raise FinishedImportError(f"unknown curve {name!r} — the source writes one of {CURVES}")
    return CURVES[name]


def render_of(render: dict) -> dict:
    """The geometry a picture was made at: what it takes to frame it again."""
    return {
        "resolution": [int(render["width"]), int(render["height"])],
        "supersample": int(render.get("ss", 1)),
        "maxiter": int(render["maxiter"]),
        "filter": str(render.get("filter", "lanczos3")),
    }


def mode_of(render: dict, provenance: dict, known: set[str]) -> str:
    """This repository's name for the coloring the source rendered through."""
    source_mode = render.get("render_mode") or provenance.get("render_mode") or "smooth"
    name = MODES.get(source_mode, source_mode)
    if name not in known:
        raise FinishedImportError(
            f"the source rendered mode {source_mode!r}, which this repository has no name for. "
            f"Known modes: {sorted(known)}"
        )
    return name


def read_batch(
    root: Path,
    head: str,
    source_batch: str,
    entry: Imported,
    known_modes: set[str],
    cyclic_maps: set[str],
) -> tuple[list[dict], dict]:
    """Every labeled row of one source batch, as rows for this store."""
    directory = batch_dir(root, head, source_batch)
    labels = labels_of(root, head, source_batch)
    created = read_record(root, head, source_batch).get("created") or source_batch[:10]
    ceiling = finished.HEADS[head]

    rows: list[dict] = []
    seen: set[str] = set()
    dropped_transfers = 0
    for line in (directory / "images.jsonl").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        image_id = row["image_id"]
        if image_id not in labels:
            raise FinishedImportError(
                f"{source_batch}: row {image_id!r} carries no verdict. This is a completed "
                f"sheet, and a silently dropped row is a corpus nobody can reproduce."
            )
        score = labels[image_id]
        if not 1 <= score <= ceiling:
            raise FinishedImportError(
                f"{source_batch}: {image_id!r} scored {score}, outside the 1..{ceiling} scale "
                f"{head} was collected on"
            )
        seen.add(image_id)

        render, provenance = row["render"], row.get("provenance") or {}
        params = color_params_of(provenance)
        colormap = render["palette"]
        dropped = bool(provenance.get("transfer_dropped"))
        dropped_transfers += dropped
        family = family_of(render, provenance)
        rows.append(
            finished.render_row(
                head=head,
                batch=entry.batch,
                score=score,
                family=family,
                viewport={
                    "center_re": str(render["cx"]),
                    "center_im": str(render["cy"]),
                    "width": str(render["fw"]),
                },
                mode=mode_of(render, provenance, known_modes),
                mode_params=mode_params_of(render, provenance),
                curve=curve_of(params),
                colormap=colormap,
                recipe_=recipe_of(
                    params,
                    dropped,
                    colormap in cyclic_maps,
                    colormap,
                    rolloff_of(render, provenance),
                ),
                render=render_of(render),
                labeler=None,
                recorded_at=str(created),
                partition=partition_of_family(family),
            )
        )

    extra = sorted(set(labels) - seen)
    if extra:
        raise FinishedImportError(
            f"{source_batch}: {len(extra)} verdicts name no row, e.g. {extra[:5]}. A label "
            f"that cannot reach a picture is a join that has already broken."
        )
    return rows, {
        "source_rows": len(seen),
        "written": len(rows),
        "transfers_dropped_at_the_source": dropped_transfers,
    }


def census_of(root: Path, head: str) -> dict[str, int]:
    """Rows per source batch, counted straight off `images.jsonl`.

    The number every export is merged against. Counted separately from the read
    on purpose: a reader that both produced the rows and certified the count
    would agree with itself about a row it silently skipped.
    """
    out = {}
    for source_batch in sorted(SOURCES[head]):
        path = batch_dir(root, head, source_batch) / "images.jsonl"
        with path.open(encoding="utf-8") as handle:
            out[source_batch] = sum(1 for line in handle if line.strip())
    return out


def engine_modes() -> set[str]:
    """Every mode this repository has a name for, from the engine's own catalog."""
    from fractal_wallpapers import engine

    return {mode["name"] for mode in engine.modes()}


def cyclic_maps(names: set[str], directory: Path) -> set[str]:
    """Which of these maps close on the color they opened with.

    The one bit that decides both traversal and folding, and it is read off the
    tracked colormap file rather than off the row: a row records the knob values
    it was rendered with, and this says which of them the map could act on.
    """
    out = set()
    for name in names:
        path = directory / f"{name}.json"
        if not path.is_file():
            raise FinishedImportError(f"{path} is missing — a row names a map nobody holds")
        if json.loads(path.read_text(encoding="utf-8"))["kind"] == "cyclic":
            out.add(name)
    return out


def palette_names(root: Path, head: str) -> set[str]:
    """Every map any row of this corpus names."""
    out = set()
    for source_batch in SOURCES[head]:
        path = batch_dir(root, head, source_batch) / "images.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.add(json.loads(line)["render"]["palette"])
    return out


def pin_document(head: str, rows: list[dict], known: dict) -> dict:
    """How the evaluation side was decided, written down beside it."""
    pinned = sorted({batch for batch, entry in known.items() if entry.eval_only})
    return {
        "schema": finished.SCHEMA,
        "head": head,
        "rule": (
            "PINNED, not drawn. A batch registered eval_only is the evaluation side and may "
            "never train, for this generation of heads or any later one. No other batch here "
            "is eligible: every one of them conditions on quality through the location head "
            "before its page is drawn, and every one but the blind sheet served a head's own "
            "verdict prefilled."
        ),
        "asserted_on": (
            "the location — family with every constant, and the viewport — so a later batch "
            "that re-renders a pinned place under a fresh identifier cannot spend the "
            "instrument by not naming it"
        ),
        "eval_only_batches": pinned,
        "renders": len(rows),
        "locations": len({finished.place_of(row) for row in rows}),
        "tiers": {
            str(tier): sum(1 for row in rows if row.get("score") == tier)
            for tier in finished.tiers(head)
        },
    }


def run(root: Path, head: str) -> dict:
    """Read one source corpus, bring its maps across, and write the rows. The whole import."""
    root = Path(root)
    head = finished.head_of(head)
    prepared = registrations(root, head)

    occupied = [
        str(finished.batch_path(head, r.batch))
        for r in prepared
        if finished.batch_path(head, r.batch).exists()
    ]
    if occupied:
        raise FinishedImportError(
            f"these files already hold rows: {occupied}. Run the import into a clean store "
            f"rather than appending a second copy of every render."
        )

    wanted = palette_names(root, head)
    brought = library_import.run(root, sorted(wanted))
    cyclic = cyclic_maps(wanted, colormap_dir())
    known_modes = engine_modes()

    for registration in prepared:
        finished.register(head, registration)
    known = finished.registry(head)
    landing = {entry.batch: source for source, entry in SOURCES[head].items()}

    census = census_of(root, head)
    per_batch, written = {}, {}
    for registration in prepared:
        source_batch = landing[registration.batch]
        entry = SOURCES[head][source_batch]
        rows, report = read_batch(root, head, source_batch, entry, known_modes, cyclic)
        if report["written"] != census[source_batch]:
            raise FinishedImportError(
                f"{source_batch}: the source holds {census[source_batch]} rows and the export "
                f"wrote {report['written']}. Every row of a finished sheet travels or none "
                f"of it does."
            )
        finished.append(head, rows, known=known)
        per_batch[registration.batch] = report
        written[registration.batch] = len(rows)

    resolution = finished.resolved(head)
    scored = resolution.scored()
    pinned_rows = [row for row in scored if registry_module.lookup(known, row["batch"]).eval_only]
    finished.write_pin(head, pinned_rows, pin_document(head, pinned_rows, known))

    tier_counts = Counter(row["score"] for row in scored)
    return {
        "head": head,
        "corpus": CORPORA[head],
        "source_census": census,
        "written": written,
        "per_batch": per_batch,
        "palettes": {
            "named": len(wanted),
            "already_tracked": brought["already_tracked"],
            "converted": brought["written"],
            "cyclic": len(cyclic),
        },
        "store": resolution.summary(),
        "tiers": {str(tier): tier_counts.get(tier, 0) for tier in finished.tiers(head)},
        "partitions": dict(sorted(Counter(row["partition"] for row in scored).items())),
        "modes": dict(sorted(Counter(row["mode"] for row in scored).items())),
        "eval_side": {
            "renders": len(pinned_rows),
            "locations": len({finished.place_of(row) for row in pinned_rows}),
            "batches": sorted({row["batch"] for row in pinned_rows}),
        },
        "registry": registry_module.summary(known),
    }


__all__ = [
    "CORPORA",
    "CURVES",
    "FAMILIES",
    "MODES",
    "SOURCES",
    "FinishedImportError",
    "Imported",
    "anchoring_of",
    "census_of",
    "color_params_of",
    "curve_of",
    "cyclic_maps",
    "engine_modes",
    "family_of",
    "labels_of",
    "mode_of",
    "mode_params_of",
    "palette_names",
    "read_batch",
    "recipe_of",
    "registrations",
    "render_of",
    "rolloff_of",
    "run",
]
