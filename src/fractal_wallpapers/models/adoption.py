"""Adopting a head: restating the cuts its scale moved, then flipping what serves.

A retrain that passes its bars is not a shipment. The location head's scores are
the scale every acting cut in the supply engine is a point on, so replacing the
artifact moves three thresholds at once — the junk floor, the good floor and the
great cut — and a flip that carried the old numbers over would be reading the new
head's probabilities against the retired head's cutpoints. That is the failure
[`fractal_wallpapers.cuts.Restatement`] exists to make impossible, and this module
is the priced step it demands.

Two commands, in this order, and the order is not a preference.

**[`restate`] is a measurement, and it can only be taken while the incumbent is
still shipped.** It reads the reference pool the incumbent already scored, scores
the same pictures through the candidate, and restates each cut as the candidate
score that passes the **same fraction of the same pool**. Once the flip has
happened the incumbent's reads are gone from the sidecar and the fractions cannot
be recovered, so the record this writes is not a convenience — it is the only
place those numbers will ever exist again. It refuses to run after the flip and
refuses to overwrite itself, for the same reason a pre-registration does.

**[`adopt`] is the flip.** It ships the candidate under the head's own asset name,
checks that what it staged is byte-for-byte the artifact the bars were read on,
retires the candidate file, and records what moved. It refuses unless the
restatement it is priced by is already in the tree and already names the artifact
about to be shipped — which is the same refusal the cuts themselves would make on
their first call, taken one step earlier where it is cheap.

## Volume-matched, and what that does and does not claim

A restated floor here is **not** a re-derivation of what "good" means. Nobody
re-measured where a wallpaper starts on the new scale; there are no labels in
this read at all. What is held fixed is the *volume*: the candidate's junk floor
is placed where it admits the same share of the standing supply the incumbent's
0.20 admitted, so the flip is a change of judgement and not a change of how much
material the pipeline sees. A calibrated height is a different measurement, on a
labelled population, and this is not it — the record says so in as many words.

The rounding goes **down**, which is the opposite of the strange head's release
bar. That bar rounds up because it is a floor on a release and the round should
not seat a row the measurement did not. These are floors on a *supply*, and
rounding one up would remove material the cut being restated did not remove. Both
directions are the same rule — round away from the change nobody measured.
"""

from __future__ import annotations

import json
import math
import time
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers import cuts
from fractal_wallpapers.paths import tracked_name

#: The schema every record here carries.
SCHEMA = 1

#: The head this module was written for. The floors are its scale.
HEAD = "location"

#: The step a restated cut is rounded to, and the direction. Three decimals is
#: what a person can read off a record and type into a module; the direction is
#: the module docstring's.
STEP = 0.005

#: The tag a flip of the location head ships under. Each head's assets live under
#: their own release, so the shipped location artifact moving is a new one.
TAG = "weights-v2"


class AdoptionError(RuntimeError):
    """The restatement or the flip cannot be done as written."""


def restatement_path(head: str = HEAD) -> Path:
    """What the cuts were restated to, and what they were before."""
    from fractal_wallpapers.models import train

    return train.head_dir(head) / "restatement.json"


def adoption_path(head: str = HEAD) -> Path:
    """What the flip moved: the two artifacts, and what survives of the retired one."""
    from fractal_wallpapers.models import train

    return train.head_dir(head) / "adoption.json"


def today() -> str:
    """The day a restatement records itself as. ISO, UTC."""
    return datetime.now(UTC).date().isoformat()


# --------------------------------------------------------------------------- #
# The reference pool.
# --------------------------------------------------------------------------- #
def reference_pool() -> tuple[list[dict], dict]:
    """`(rows, identity)` — the sidecar as it stands, and what it is.

    The whole standing supply, not a draw from it: the fractions being held fixed
    are volumes the pipeline actually sees, and a sample would restate a floor
    against a population no stage reads. Every row carries the canonical view its
    own score was read off, so the candidate arm costs the head and not the
    engine.
    """
    from fractal_wallpapers.curation import intake

    rows = sorted(intake.read_scores().values(), key=lambda row: row["key"])
    if not rows:
        raise AdoptionError(
            f"{intake.scores_path()} holds no rows, so there is no population to restate a "
            f"cut against. Run `fractal-wallpapers curate score` first."
        )
    shas = {row["head_sha256"] for row in rows}
    if len(shas) != 1:
        raise AdoptionError(
            f"the sidecar's {len(rows)} rows were scored by {len(shas)} different artifacts "
            f"({', '.join(sorted(sha[:12] for sha in shas))}). A fraction of a pool means "
            f"nothing when the pool was read by two heads — re-score it whole first."
        )
    ledgers: dict[str, int] = {}
    for row in rows:
        ledgers[row["ledger"]] = ledgers.get(row["ledger"], 0) + 1
    return rows, {
        "population": "every location the curation sidecar holds an opinion about",
        "path": tracked_name(intake.scores_path()),
        "locations": len(rows),
        "scored_by": sorted(shas)[0],
        "by_ledger": dict(sorted(ledgers.items())),
        "views": "the canonical 640x360ss2 view each row's own score was read off",
    }


def _pictures(rows: list[dict]) -> list[Path]:
    """Each row's canonical view, checked to still be the picture the recipe makes.

    Recomputed rather than trusted, the same check the flip read makes: if the
    deploy recipe has moved since the sidecar was written, the candidate arm would
    be reading different pictures from the ones the incumbent's fractions were
    measured over, and every restated height would be against a baseline that no
    longer exists.
    """
    from fractal_wallpapers.curation import intake
    from fractal_wallpapers.models import location_view

    colormap = intake.canonical_map()
    cyclic = location_view.cyclic_maps()
    directory = intake.view_dir()
    out, renamed, absent = [], [], []
    for row in rows:
        expected = location_view.view_name(row, colormap, cyclic)
        if f"{expected}.jpg" != row["view"]:
            renamed.append(row["key"])
        path = directory / row["view"]
        if not path.is_file():
            absent.append(row["view"])
        out.append(path)
    if renamed:
        raise AdoptionError(
            f"{len(renamed)} sidecar row(s) name a canonical view the deploy recipe no "
            f"longer makes (first: {renamed[0]}). The incumbent's fractions were measured "
            f"on those files; restating against different pictures would not be a "
            f"volume match."
        )
    if absent:
        raise AdoptionError(
            f"{len(absent)} canonical view(s) the sidecar names are not on this machine "
            f"(first: {absent[0]}). The pool is the sidecar's own scoring pass and its "
            f"pictures are supposed to still be cached — re-run `curate score` to remake "
            f"them rather than restating a cut against a subset."
        )
    return out


def read_through(artifact: Path, pictures: list[Path], device: str = "auto", log=print) -> list:
    """Every picture through one artifact, in the order given.

    Serially, in one process. Fanning the *renders* out has measured slower twice
    in this repository and there is nothing to fan out here anyway: the pictures
    are already on disk and the cost is one head over one device. Progress is
    logged off an observed rate across the whole pool rather than off its first
    batch — a sidecar is written smallest-cell-first often enough that a prefix
    prices the cheap end.
    """
    from fractal_wallpapers.models import scoring as scoring_module
    from fractal_wallpapers.models import train

    model, config, where = scoring_module.load(artifact, device)
    transform = scoring_module.transform_of(config)
    classes = int(config["classes"])
    log(f"[adopt] {artifact.name} on {where}: {len(pictures)} canonical reads")
    out: list = []
    started = time.monotonic()
    chunk = 2000
    for index in range(0, len(pictures), chunk):
        batch = pictures[index : index + chunk]
        out.extend(train.score(model, batch, transform, where, classes, {"batch_size": 64}))
        elapsed = time.monotonic() - started
        rate = len(out) / max(elapsed, 1e-9)
        log(
            f"[adopt] {len(out)}/{len(pictures)} read in {elapsed:.0f}s "
            f"({rate:.0f}/s, {(len(pictures) - len(out)) / max(rate, 1e-9):.0f}s left)"
        )
    return out


# --------------------------------------------------------------------------- #
# The restatement.
# --------------------------------------------------------------------------- #
def matched(prior: float, incumbent: list[float], candidate: list[float]) -> dict:
    """One cut, restated as the candidate score passing the same share of the pool.

    `k` is what the incumbent's cut passes. The crossing is the k-th largest
    candidate score — the height at which the candidate passes exactly those k
    rows, whichever rows they are — and the restated value is that crossing
    rounded down to [`STEP`]. Rounded down because a floor rounded up removes
    supply the cut being restated did not remove; the realized count is reported
    beside the target so the cost of the rounding is visible rather than assumed.
    """
    total = len(incumbent)
    passing = sum(1 for score in incumbent if score >= prior)
    ordered = sorted(candidate, reverse=True)
    crossing = ordered[passing - 1] if 0 < passing <= total else (1.0 if passing == 0 else 0.0)
    value = round(math.floor(crossing / STEP + 1e-9) * STEP, 3)
    realized = sum(1 for score in candidate if score >= value)
    return {
        "prior": prior,
        "incumbent_passing": passing,
        "incumbent_share": passing / total,
        "crossing": crossing,
        "value": value,
        "realized_passing": realized,
        "realized_share": realized / total,
        "share_delta": (realized - passing) / total,
    }


def method_of(gate: dict, match: dict, identity: dict) -> str:
    """The sentence a restated cut carries, in enough detail to be re-run."""
    return (
        f"volume matched against the incumbent on a fixed reference pool. The prior cut "
        f"{gate['reads']} passed {match['incumbent_passing']} of {identity['locations']} "
        f"({match['incumbent_share']:.2%}) of the pool's canonical reads under "
        f"{identity['scored_by'][:12]}; this is the candidate score passing that same "
        f"count — the {match['incumbent_passing']}th largest candidate read, "
        f"{match['crossing']:.6f} — rounded DOWN to the next {STEP} because a floor rounded "
        f"up removes supply the cut it restates did not. Realized "
        f"{match['realized_passing']} passing ({match['realized_share']:.2%}). NOT a "
        f"calibration: no label was read, and nothing here re-measures where a keeper "
        f"starts on the new scale."
    )


def restate(head: str = HEAD, device: str = "auto", log=print) -> dict:
    """Measure every location cut against the staged candidate, and record it.

    Runs exactly once per flip, between two refusals.

    The first is the obvious one: after the artifact moves, the pool holds the
    candidate's reads and the fractions being matched against no longer exist.

    The second is the one that had to be found. A prior is only a prior while the
    modules that own these cuts still declare them on the **retired** head, and
    the natural order of this work — measure, type the numbers in, flip — leaves
    a window where the code already carries the new heights and the artifact has
    not moved. A second run in that window restates the candidate against itself,
    reports a tidy volume match, and means nothing. It is caught here rather than
    read in a report, because every number it produces looks exactly like a
    number that was measured.
    """
    from fractal_wallpapers.models import regime_flips, ship

    live = cuts.live_stamp(head)
    staged = candidate_record(head)
    if live == staged["sha256"]:
        raise AdoptionError(
            f"{staged['artifact']} is already the shipped {head} head ({live[:12]}), so the "
            f"pool holds its reads and not the retired head's. The fractions a restatement "
            f"matches against no longer exist to be measured — {restatement_path(head)} is "
            f"the record of them."
        )
    ahead = {
        name: declared
        for name, declared in declared_cuts(head).items()
        if declared.head_sha256 != live
    }
    if ahead:
        raise AdoptionError(
            f"the {', the '.join(sorted(ahead))} — already declared against "
            f"{sorted(ahead.values(), key=lambda cut: cut.value)[0].head_sha256[:12]} while "
            f"{live[:12]} is still shipped. The prior a restatement matches is whatever the "
            f"owning module declares, so measuring now would match the new heights against "
            f"themselves and call it a volume match. Restate before the values are typed in, "
            f"or restore them and re-measure."
        )
    artifact = ship.candidate_path(head)
    if not artifact.is_file():
        raise AdoptionError(f"{artifact} is not on this machine: there is no candidate to read.")

    rows, identity = reference_pool()
    if identity["scored_by"] != live:
        raise AdoptionError(
            f"the sidecar was scored by {identity['scored_by'][:12]} and the shipped head is "
            f"{live[:12]}. The pool has to be the shipped head's own read of the standing "
            f"supply — re-score it before restating anything against it."
        )
    pictures = _pictures(rows)
    probabilities = read_through(artifact, pictures, device, log)

    gates = regime_flips.gates()
    fields = {gate["field"] for gate in gates}
    candidate_by_field = {
        field: [float(row[int(field.removeprefix("p_ge")) - 2]) for row in probabilities]
        for field in fields
    }
    incumbent_by_field = {field: [float(row[field]) for row in rows] for field in fields}

    restated = {}
    for gate in gates:
        match = matched(
            float(gate["edge"]),
            incumbent_by_field[gate["field"]],
            candidate_by_field[gate["field"]],
        )
        restated[gate["gate"]] = {
            **match,
            "field": gate["field"],
            "reads": gate["reads"],
            "decides": gate["decides"],
            "declared_in": gate["owner"],
            "method": method_of(gate, match, identity),
        }

    return {
        "schema": SCHEMA,
        "head": head,
        "date": today(),
        "priced": "the flip of the shipped location head to the regime-robust candidate",
        "incumbent": {"artifact": ship.shipped_path(head).name, "sha256": live},
        "candidate": {
            "artifact": staged["artifact"],
            "sha256": staged["sha256"],
            "run": staged["run"],
            "record": tracked_name(ship.candidate_record_path(head)),
        },
        "judged_by": judged_by(head),
        "reference_pool": identity,
        "rounding": {"step": STEP, "direction": "down"},
        "holds_fixed": "volume: the share of this pool each cut passes, not what the cut means",
        "cuts": restated,
    }


def judged_by(head: str = HEAD) -> list[dict]:
    """The two pre-registered reads of this candidate, each with its own verdict.

    Both, and the verdict beside each, because they did not say the same thing.
    The split bar reads FAIL — three of its four consistency slices could not
    clear zero on a population that agrees with itself trivially — and the stock
    bar reads PASS on the flips the supply engine actually acts at. A record that
    listed the two paths and no verdicts would read as *passed both*, which is
    the one thing this adoption must not be able to claim.
    """
    from fractal_wallpapers.models import regime_acceptance, regime_flips

    out = []
    for module, population in (
        (regime_acceptance, "the evaluation split"),
        (regime_flips, "production stock, at the acting gates"),
    ):
        path = module.acceptance_path(head)
        out.append(
            {
                "record": tracked_name(path),
                "population": population,
                "verdict": json.loads(path.read_text(encoding="utf-8"))["verdict"],
            }
        )
    return out


# --------------------------------------------------------------------------- #
# The flip.
# --------------------------------------------------------------------------- #
def candidate_record(head: str = HEAD) -> dict:
    """What the staged candidate is, off its tracked record."""
    from fractal_wallpapers.models import ship

    path = ship.candidate_record_path(head)
    if not path.is_file():
        raise AdoptionError(
            f"{path} is missing: nothing has staged a candidate for {head!r}, so there is "
            f"nothing to adopt."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def restatement(head: str = HEAD) -> dict:
    """The measurement this flip is priced by, off its tracked record."""
    path = restatement_path(head)
    if not path.is_file():
        raise AdoptionError(
            f"{path} is missing: nothing has restated the cuts this head's scale moves. "
            f"Run `fractal-wallpapers regime restate` before the flip — afterwards the "
            f"population it measures against is gone."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def declared_cuts(head: str = HEAD) -> dict:
    """What the modules that own the three location cuts say right now.

    Read off the owners rather than restated here, so this step cannot pass a
    flip whose code still carries the retired head's numbers.
    """
    del head
    from fractal_wallpapers.curation import floors
    from fractal_wallpapers.supply import currency

    return {
        "junk floor": floors.JUNK_FLOOR_RESTATED,
        "good floor": currency.GOOD_FLOOR_RESTATED,
        "great cut": currency.GREAT_CUT_RESTATED,
    }


def _agrees(head: str, priced: dict) -> dict:
    """Every acting location cut, checked against the restatement that priced it."""
    out = {}
    for name, declared in declared_cuts(head).items():
        measured = priced["cuts"].get(name)
        if measured is None:
            raise AdoptionError(f"{restatement_path(head)} restates no cut named {name!r}.")
        if declared.head_sha256 != priced["candidate"]["sha256"]:
            raise AdoptionError(
                f"the {name} is declared against {declared.head_sha256[:12]} and the "
                f"candidate is {priced['candidate']['sha256'][:12]}. The code still carries "
                f"a cut on another head's scale; the flip would refuse on its first call."
            )
        if abs(float(declared.value) - float(measured["value"])) > 1e-12:
            raise AdoptionError(
                f"the {name} is declared at {declared.value} and the restatement measured "
                f"{measured['value']}. One of the two is a number nobody read."
            )
        out[name] = {
            "value": declared.value,
            "prior": measured["prior"],
            "restated_against": declared.head_sha256,
            "restated_on": declared.date,
            "reference_pool": declared.reference_pool,
            "share": measured["realized_share"],
            "prior_share": measured["incumbent_share"],
        }
    return out


def adopt(
    head: str = HEAD,
    tag: str = TAG,
    log=print,
) -> dict:
    """Ship the staged candidate as this head's artifact, and record what moved.

    The candidate's bytes are promoted under the shipped name — see
    [`fractal_wallpapers.models.ship.promote`] for why a flip copies instead of
    re-casting. What this adds on top is the arithmetic nobody else checks: that
    the restatement in the tree priced *this* artifact, that the modules owning
    the three location cuts already declare the heights it measured, and that the
    bar written on production stock did not say FAIL. Every one of those would
    otherwise surface as a refusal at the first comparison of the next run, with
    the manifest already moved.
    """
    from fractal_wallpapers.models import regime_flips, ship

    staged = candidate_record(head)
    priced = restatement(head)
    verdict = json.loads(regime_flips.acceptance_path(head).read_text(encoding="utf-8"))
    if verdict["verdict"] == "FAIL":
        raise AdoptionError(
            f"{regime_flips.acceptance_path(head)} says {verdict['verdict']}. Adopting a "
            f"candidate that failed the bar written for it is a decision this step will not "
            f"take on its own."
        )
    if priced["candidate"]["sha256"] != staged["sha256"]:
        raise AdoptionError(
            f"the restatement priced {priced['candidate']['sha256'][:12]} and the staged "
            f"candidate is {staged['sha256'][:12]}. Restate against the artifact that is "
            f"actually going to serve."
        )
    agreed = _agrees(head, priced)

    retiring = json.loads(ship.manifest_path().read_text(encoding="utf-8"))["heads"][head]
    retired = cuts.live_stamp(head)
    shipment = ship.promote(name=head, tag=tag, run=staged["run"])
    landed = shipment["manifest_entry"]["sha256"]
    if landed != staged["sha256"]:
        raise AdoptionError(
            f"the flip landed {landed[:12]} under {shipment['manifest_entry']['asset']}, but "
            f"the two bars judged {staged['sha256'][:12]}. Nothing may serve an artifact no "
            f"read has seen."
        )
    log(f"[adopt] {head}: {retired[:12]} retired, {landed[:12]} serving under {tag}")

    candidate_file = ship.candidate_path(head)
    candidate_file.unlink(missing_ok=True)
    record = {
        **staged,
        "adopted": True,
        "adopted_on": today(),
        "not_in": (
            f"nothing. This candidate was adopted: its bytes are now "
            f"{ship.shipped_path(head).name} in the manifest under {tag}, and "
            f"{staged['artifact']} has been removed rather than left as a second copy of "
            f"the shipped head."
        ),
        "priced_by": tracked_name(restatement_path(head)),
    }
    write_json(ship.candidate_record_path(head), record)

    return {
        "schema": SCHEMA,
        "head": head,
        "date": today(),
        "flipped": {
            "retired": {
                "sha256": retired,
                "run": retiring.get("run"),
                "tag": retiring.get("tag"),
                "keeps": (
                    "its heights, as this record's prior, and its reads of the reference "
                    "pool as the shares those heights were restated to hold. Its bytes are "
                    "the asset published under its own tag and nothing else: a re-cast of "
                    "its checkpoint reproduces the weights but not the hash"
                ),
            },
            "serving": {
                "sha256": landed,
                "run": staged["run"],
                "asset": shipment["manifest_entry"]["asset"],
                "tag": tag,
            },
        },
        "judged_by": priced["judged_by"],
        "priced_by": tracked_name(restatement_path(head)),
        "cuts": agreed,
        "half_precision_agreement": staged["agreement"]["decisions"],
        "candidate_record": tracked_name(ship.candidate_record_path(head)),
    }


def write_json(path: Path, document: dict) -> Path:
    """A tracked record, with the line endings git keeps."""
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


__all__ = [
    "HEAD",
    "SCHEMA",
    "STEP",
    "TAG",
    "AdoptionError",
    "adopt",
    "adoption_path",
    "candidate_record",
    "declared_cuts",
    "matched",
    "read_through",
    "reference_pool",
    "restate",
    "restatement",
    "restatement_path",
    "write_json",
]
