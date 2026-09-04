"""`P(spiral)` per location, so a gallery cap has a share to act on.

[`fractal_wallpapers.models.spiral_probe`] answers *is this place a spiral* for one
location at a time, off a picture it renders itself. A share cap in the solve needs
the answer for **every** location it might seat, before it seats any of them, and it
needs it to mean the same thing across all of them. So the answer is persisted here:
one row per location, keyed on `supply.location.location_key`, under the probe's own
frozen regime.

## It costs nothing, because the picture was already read

The shipped probe's feature set is `neutral_dinov2` — DINOv2 ViT-S/14 over the
location's neutral render — and [`curation.embeddings`] **already holds exactly that
vector** for every admitted location, computed once and appended to forever. So a
score for a location the embedding store covers is a 384-column dot product and not
a render: [`build`] is numpy over a file this project already keeps, no engine, no
encoder, no GPU.

The stored vectors are `float16`, and the probe was fitted on `float32`. Measured on
the labeled 500 before this module was written: round-tripping through `float16`
moves `P(spiral)` by at most **1.3e-4**, mean 1.2e-5, and flips **no verdict at all**
at 0.3, 0.5 or 0.7. So reading the packed store is not an approximation worth a
caveat, and it is the reason this store exists rather than a re-render leg.

A location the embedding store has *not* reached still needs its picture drawn, and
[`score_records`] is that path — one neutral render and one encoder pass each, about
0.05 s a location, measured over 9,401 of them. It is the exception; [`build`] is the
ordinary case.

## Two provenances, and a row carries both

A score means nothing without the picture it was read off **and** the coefficients it
was read through, and each of them can move without the other.

* The **picture and the encoder** are [`curation.neutral`]'s frozen choices plus
  DINOv2's variant, dimension and precision, digested together. That is exactly the
  stamp the embedding store already writes on every row, so a row scored from the
  store carries the stamp of the very vector it was scored from rather than a stamp
  recomputed beside it. **Note this is not `manifest.json`'s regime stamp**: that one
  digests the picture recipe alone and names the encoder beside it without digesting
  it, which is enough to identify a *picture* and not enough to identify a *reading*.
* The **probe** is a re-fit away from being a different function of the same vector,
  and nothing about a re-fit changes a picture. So the row carries [`probe_digest`],
  a digest of the intercept, the coefficients and the two standardizing vectors.

[`refuse_a_second_provenance`] refuses an append that would put a second value of
either into the store, for [`curation.embeddings`]'s reason: a file holding two
provenances is a file whose numbers are arithmetic between unrelated readings, and
the failure is silent because every one of them is still a probability.

## Unknown is not `not_spiral`

A location with no row here reads as **unknown**, and every reader is required to
treat it as counting toward nothing. It is not a negative verdict: a place nobody has
scored and a place the probe called flat are different facts, and a cap that conflated
them would quietly stop capping exactly the locations it had never looked at.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from fractal_wallpapers.curation import durability, embeddings
from fractal_wallpapers.paths import archive_root, hot_root, tracked_name, under

#: The schema every stored row carries.
SCHEMA = 1

#: What the store is called, wherever it is.
STORE_NAME = "spiral_scores.jsonl"

#: How many locations are scored before anything is written. Larger than the
#: embedding store's leg because nothing here renders: the batch is one matrix
#: multiply, and the only thing it bounds is how much a crash costs.
LEG = 4096


class StoreRefused(RuntimeError):
    """The spiral score store cannot be read, or cannot be appended to."""


# --------------------------------------------------------------------------- #
# Where everything lives.
# --------------------------------------------------------------------------- #
def store_path() -> Path:
    """The store: one row per scored location, wherever curation's subtree is."""
    return under("curation") / STORE_NAME


def backup_path() -> Path:
    """The durable copy, on the archive tier beside the other two curation stores."""
    archive = archive_root()
    root = hot_root() if archive is None else archive
    return Path(root) / durability.BACKUP_UNIT / STORE_NAME


def manifest_path() -> Path:
    """The tracked manifest: what the store was, last time anybody recorded it."""
    from fractal_wallpapers.paths import repo_root

    return repo_root() / "data" / "curation" / "spiral_scores.manifest.json"


def store() -> durability.Durable:
    """The store as a [`durability.Durable`], which is how it is saved and checked."""
    return durability.Durable(
        name="the spiral score store",
        live=store_path(),
        copy=backup_path(),
        manifest=manifest_path(),
        why_not_tracked=(
            "one row per admitted location and it grows by an append every time a harvest "
            "adds admissions, so it tracks the embedding store's size rather than a fixed "
            "one. The manifest is what the history keeps: the row count, the bytes, the "
            "sha256, both provenances every score was read under, and the share called "
            "spiral at each cut the sweep reports."
        ),
        save_command="fractal-wallpapers curate spiral-scores save",
        restore_command="fractal-wallpapers curate spiral-scores restore",
        rebuild_command="fractal-wallpapers curate spiral-scores build",
        facts=_facts,
    )


def _facts(path: Path) -> dict:
    """The columns this store adds to its manifest: what read it, and what it found.

    The shares are in here rather than only in a report because they are what the
    cap acts on: a manifest that recorded the row count alone would say the store
    was healthy while the population under the cut had moved by ten points.
    """
    stamps: dict[str, int] = {}
    digests: dict[str, int] = {}
    probes: dict[str, int] = {}
    values: list[float] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            stamps[str(row.get("stamp"))] = stamps.get(str(row.get("stamp")), 0) + 1
            digests[str(row.get("probe_digest"))] = digests.get(str(row.get("probe_digest")), 0) + 1
            probes[str(row.get("probe"))] = probes.get(str(row.get("probe")), 0) + 1
            values.append(float(row.get("p_spiral") or 0.0))

    # One value is the ordinary case and it is a bare field; more than one is the
    # failure the guard exists for, and it gets the counts instead of a `null`
    # column on every healthy manifest. [`curation.embeddings._facts`]'s rule.
    def told(name: str, counts: dict) -> dict:
        if len(counts) == 1:
            return {name: next(iter(counts))}
        return {name: None, f"{name}_counts": dict(sorted(counts.items()))}

    return {
        **told("stamp", stamps),
        **told("probe_digest", digests),
        **told("probe", probes),
        "shares": {
            str(cut): {
                "spiral": sum(1 for value in values if value >= cut),
                "share": (
                    round(sum(1 for value in values if value >= cut) / len(values), 4)
                    if values
                    else None
                ),
            }
            for cut in sorted({0.3, 0.5, 0.7, cut_at()})
        },
        "mean_probability": round(sum(values) / len(values), 4) if values else None,
        "acting_cut": cut_at(),
    }


# --------------------------------------------------------------------------- #
# Provenance.
# --------------------------------------------------------------------------- #
def probe_digest(document: dict) -> str:
    """Twelve hex characters over everything that turns a vector into a probability.

    The intercept, the coefficients and the two standardizing vectors — the whole
    of what [`spiral_probe.score`] reads. A re-fit on one more sitting changes every
    number this store holds while changing nothing about any picture, so the picture
    stamp cannot be the only thing guarding it.
    """
    material = json.dumps(
        {
            "feature_set": document.get("feature_set"),
            "intercept": document.get("intercept"),
            "coefficients": document.get("coefficients"),
            "mean": document.get("mean"),
            "deviation": document.get("deviation"),
        },
        sort_keys=True,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]


def cut_at() -> float:
    """The acting threshold, off the probe manifest. Never hard-coded at a reader.

    stdlib only, so a caller deciding whether a location is a spiral does not pull
    numpy in to ask where the line is.
    """
    from fractal_wallpapers.models import spiral_probe

    document = json.loads(spiral_probe.manifest_path().read_text(encoding="utf-8"))
    shipped = document["shipped"]
    return float(document["probes"][shipped]["threshold"])


def row_of(key: str, probability: float, stamp: str, probe: str, digest: str) -> dict:
    """One stored row. Both provenances ride on it, for [`_facts`]'s reason."""
    return {
        "schema": SCHEMA,
        "key": str(key),
        "probe": str(probe),
        "p_spiral": round(float(probability), 6),
        "stamp": str(stamp),
        "probe_digest": str(digest),
    }


def refuse_a_second_provenance(path: Path, stamp: str, digest: str) -> None:
    """Refuse an append under a picture stamp or a probe the store does not carry.

    Reads one line rather than the store: the first row settles it, and this file
    is one short row per location.
    """
    for row in _first_row(path):
        for field, marked, what in (
            ("stamp", stamp, "the picture and the encoder it was read through"),
            ("probe_digest", digest, "the probe's own coefficients"),
        ):
            if str(row.get(field)) != marked:
                raise StoreRefused(
                    f"{path} holds rows whose {field} is {row.get(field)!r} and this leg "
                    f"would append {marked!r}. {what.capitalize()} moved, so the two are "
                    f"not readings of one thing and a share taken across them means "
                    f"nothing. Move the store aside and rebuild it with "
                    f"`fractal-wallpapers curate spiral-scores build`, or put the choice "
                    f"back."
                )


# --------------------------------------------------------------------------- #
# Reading.
# --------------------------------------------------------------------------- #
def _first_row(path: Path) -> list[dict]:
    """`[the store's first row]`, or `[]` where there is no store. One line read."""
    path = Path(path)
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                return [json.loads(line)]
    return []


def read(path: Path | None = None) -> list[dict]:
    """Every stored row."""
    path = store_path() if path is None else Path(path)
    if not path.is_file():
        return []
    out = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema") != SCHEMA:
            raise StoreRefused(f"{path}:{number}: schema {row.get('schema')!r}")
        out.append(row)
    return out


def by_key(path: Path | None = None) -> dict[str, float]:
    """`{location key: P(spiral)}` — what a join reads. Last row wins.

    Last-wins rather than first, so a store somebody re-scored in place reads as the
    re-score. The provenance guard is what stops that being two different questions.
    """
    return {str(row["key"]): float(row["p_spiral"]) for row in read(path)}


def spirals(path: Path | None = None, cut: float | None = None) -> set[str]:
    """The location keys at or above the cut. **Unknown locations are absent.**

    A set and not a predicate, because every reader wants membership and a
    predicate would invite `spiral(key) is False` to be read as `not_spiral`.
    """
    line = cut_at() if cut is None else float(cut)
    return {key for key, value in by_key(path).items() if value >= line}


def stored_keys(path: Path | None = None) -> set[str]:
    """Which locations the store already holds."""
    return {str(row["key"]) for row in read(path)}


# --------------------------------------------------------------------------- #
# Scoring.
# --------------------------------------------------------------------------- #
def score_vectors(document: dict, rows: list[dict]):
    """`P(spiral)` for embedding-store rows, from the vectors they already carry.

    The whole point of this module: no render, no encoder, no GPU. `rows` are
    [`curation.embeddings`]'s, each carrying its packed `float16` vector.
    """
    import numpy

    from fractal_wallpapers.models import spiral_probe

    if not rows:
        return numpy.zeros((0,), dtype=numpy.float64)
    matrix = numpy.stack([embeddings.unpack(row["vector"]) for row in rows])
    return numpy.asarray(spiral_probe.score(document, matrix))


def build(limit: int | None = None, path: Path | None = None, log=print) -> dict:
    """Score every embedded location this store does not hold yet, and append.

    Idempotent and resumable at a batch boundary, like the store it reads. Running
    it twice over an unchanged embedding store appends nothing and says so.
    """
    from fractal_wallpapers.models import spiral_probe

    started = time.monotonic()
    path = store_path() if path is None else Path(path)
    document = spiral_probe.read(spiral_probe.probe_path(spiral_probe.SHIPPED))
    digest = probe_digest(document)

    stored = stored_keys(path)
    population = embeddings.read()
    outstanding = [row for row in population if str(row["key"]) not in stored]
    if limit is not None:
        outstanding = outstanding[: int(limit)]
    log(
        f"[spiral-scores] {len(population):,} embedded, {len(stored):,} already scored, "
        f"{len(outstanding):,} outstanding"
    )
    if not outstanding:
        return {
            "embedded": len(population),
            "already_scored": len(stored),
            "wrote": 0,
            "seconds": round(time.monotonic() - started, 2),
        }

    # Every row of the embedding store carries the stamp of the vector it holds, and
    # a score read off that vector inherits it rather than recomputing one beside it
    # — which is what makes the guard exact instead of merely plausible.
    marked = {str(row.get("stamp")) for row in outstanding}
    if len(marked) != 1:
        raise StoreRefused(
            f"the embedding store's outstanding rows carry {len(marked)} stamps "
            f"({sorted(marked)}), so they are not one reading and a score taken across "
            f"them would not be either."
        )
    stamp = next(iter(marked))
    refuse_a_second_provenance(path, stamp, digest)

    wrote = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for start in range(0, len(outstanding), LEG):
            chunk = outstanding[start : start + LEG]
            probability = score_vectors(document, chunk)
            for row, value in zip(chunk, probability, strict=True):
                handle.write(
                    json.dumps(
                        row_of(row["key"], value, stamp, document["feature_set"], digest),
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            wrote += len(chunk)
            handle.flush()
            log(f"[spiral-scores] {wrote:,} of {len(outstanding):,}")

    held = by_key(path)
    report = {
        "embedded": len(population),
        "already_scored": len(stored),
        "wrote": wrote,
        "rows": len(held),
        "stamp": stamp,
        "probe": document["feature_set"],
        "probe_digest": digest,
        "acting_cut": cut_at(),
        "shares": {
            str(cut): {
                "spiral": sum(1 for value in held.values() if value >= cut),
                "share": round(sum(1 for value in held.values() if value >= cut) / len(held), 4),
            }
            for cut in sorted({0.3, 0.5, 0.7, cut_at()})
        },
        "store": tracked_name(path),
        "seconds": round(time.monotonic() - started, 2),
    }
    log(
        f"[spiral-scores] {wrote:,} written in {report['seconds']:.1f}s — "
        f"{report['shares'][str(cut_at())]['share']:.1%} spiral at {cut_at()}"
    )
    return report


def score_records(records: list[dict], directory=None, path: Path | None = None, log=print) -> dict:
    """Score locations the embedding store has not reached. **Renders and encodes.**

    The exception path, and the expensive one: about 0.05 s a location against a dot
    product. `records` carry a family, a viewport and a maxiter, as
    [`spiral_probe.features`] wants them, each also carrying the location `key` this
    store rows on.

    Its rows land under the same two provenances as [`build`]'s, so a store filled
    both ways is still one reading. The picture stamp is recomputed here because
    there is no embedding row to inherit one from, and it is the encoder-inclusive
    digest and not the manifest's regime stamp — see the module docstring.
    """
    import torch

    from fractal_wallpapers.curation import neutral
    from fractal_wallpapers.models import embedding, spiral_probe

    started = time.monotonic()
    path = store_path() if path is None else Path(path)
    document = spiral_probe.read(spiral_probe.probe_path(spiral_probe.SHIPPED))
    digest = probe_digest(document)

    stored = stored_keys(path)
    outstanding = [record for record in records if str(record["key"]) not in stored]
    log(f"[spiral-scores] {len(outstanding):,} of {len(records):,} record(s) need a render")
    if not outstanding:
        return {"asked": len(records), "wrote": 0, "seconds": round(time.monotonic() - started, 2)}

    model = embedding.build()
    where = "cuda" if torch.cuda.is_available() else "cpu"
    encoder = embedding.describe(model.to(where), device=where)
    stamp = neutral.stamp(
        {"variant": encoder["variant"], "dim": encoder["dim"], "precision": encoder["precision"]}
    )
    refuse_a_second_provenance(path, stamp, digest)

    features = spiral_probe.features(
        outstanding, spiral_probe.SHIPPED, directory=directory, log=log
    )
    probability = spiral_probe.score(document, features)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for record, value in zip(outstanding, probability, strict=True):
            handle.write(
                json.dumps(
                    row_of(record["key"], value, stamp, document["feature_set"], digest),
                    ensure_ascii=False,
                )
                + "\n"
            )
    seconds = time.monotonic() - started
    log(f"[spiral-scores] {len(outstanding):,} rendered and scored in {seconds:.0f}s")
    return {
        "asked": len(records),
        "wrote": len(outstanding),
        "stamp": stamp,
        "probe_digest": digest,
        "seconds_per_location": round(seconds / max(1, len(outstanding)), 4),
        "seconds": round(seconds, 2),
    }


__all__ = [
    "LEG",
    "SCHEMA",
    "STORE_NAME",
    "StoreRefused",
    "build",
    "by_key",
    "cut_at",
    "manifest_path",
    "probe_digest",
    "read",
    "refuse_a_second_provenance",
    "row_of",
    "score_records",
    "score_vectors",
    "spirals",
    "store",
    "store_path",
    "stored_keys",
]
