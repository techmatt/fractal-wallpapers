"""Which renders' texture layer said nothing, measured once and written down.

A modulate coloring lays a texture over a base and shifts the base's palette
position by it. Where the texture has no span to normalize against — every
sample at one value, or none of them at a value at all — the shift is zero
everywhere and the picture is **the base spent by rank, bit for bit**. The
engine reports that per render as `RenderReport.texture_flat`, and
[`curation.mode_policy.routed_mode`] is where the consequence is spelled: such a
render routes as `smooth`.

That leaves the rows written before the engine reported it. There are two piles
of them and they cannot be treated the same way. A candidate-ledger row is a
regenerable record and takes the flag onto the row itself. **A label row is
never rewritten** — a stored verdict is an original — so its re-attribution has
to happen at the read, which means the answer has to be somewhere a reader can
find it. This is that somewhere, and it serves both piles because there is
exactly one question and one answer to it.

## What it is keyed on

The flag is a function of the **field side of the render and nothing else**: the
family, the frame, the sample grid, the iteration cap and the coloring. It does
not depend on the colormap or on a single knob of the palette pass — those are
spent after the texture has already been measured, which is the same split
[`models.renders.FIELD_IDENTITY`] draws for a dumped field. So the key is a
digest of the engine spec less its recolour half, and one measurement answers
for all thirty-two maps at a location.

It is **not** [`models.renders.field_job_name`], which is that digest taken over
the whole spec including `colormap_dir` — a path on the machine that took it.
That is fine for naming a file in a cache and useless for a record this
repository tracks; [`KEYED`] below is the checkout-independent half, and
[`curation.recipes.key_of`] is not it either, being finer by the whole recolour
half.

The geometry is in the key on purpose. A candidate is drawn at 640x360ss2 and a
labeled picture at 1280x720ss2, and those are two different sample grids over
one frame: the second may resolve a texture the first flattened. Two renders,
two rows here, no sharing between them.

## What a `True` costs to establish

A render. There is no cheaper probe and no proxy that works: frame width does
not separate the two populations in any partition, and counting distinct values
in a dumped `f32` field is wrong 15.2% of the time in the direction that matters
— the address spends its `f32` after eleven symbols against a catalogued depth
of 26, so whole subtrees of the lamination collapse on the way into the dump.
That is why the modulate carries its texture at `f64` and why `dump-field`
refuses it. So this store exists because the answer is expensive, and it is
tracked because a fresh clone routing the label corpus differently from this one
would be two corpora wearing one name.

```
fractal-wallpapers coloring texture-flat measure   # render what is unmeasured
fractal-wallpapers coloring texture-flat stamp     # carry it onto the ledger rows
fractal-wallpapers coloring texture-flat show      # what the register holds
```
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.paths import repo_root

#: The schema every register row carries, from the first row.
SCHEMA = 1

#: **What the flag is a function of**: the engine spec less the two members a
#: recolour spends after the field exists, and less the two that name a place on
#: the machine rather than a picture. Declared rather than derived, and held to
#: [`models.renders.SPEC_MEMBERS`] by [`field_key`], so a member the engine spec
#: grows is classified here rather than joining or missing the key by accident.
KEYED: tuple[str, ...] = (
    "schema",
    "family",
    "viewport",
    "resolution",
    "supersample",
    "maxiter",
    "coloring",
)

#: The spec members a recolour spends, which the texture is measured before.
#: [`models.renders.RECOLOR_MEMBERS`] names the same split on the row side.
SPENT_AFTER: tuple[str, ...] = ("colormap", "palette")

#: The members that name a place rather than a picture. [`curation.recipes.PINNED`]
#: is the same pair, and for the same reason: a key carrying either would be a key
#: about one machine.
PINNED: tuple[str, ...] = ("output", "colormap_dir")

#: How many hex characters of the digest a key is. The same length
#: [`curation.recipes.key_of`] uses, over a population four orders of magnitude
#: smaller than the ledger's.
KEY_LENGTH = 16

#: The render pool this machine allows. See `CLAUDE.md`: more than three engines
#: at once makes the desktop unusable while the leg runs.
MEASURE_WORKERS = 3


class RegisterError(RuntimeError):
    """A row that cannot be keyed, or a register that cannot be read."""


def path() -> Path:
    """Where the register lives. Tracked, beside the tone band."""
    return repo_root() / "data" / "coloring" / "texture_flat.jsonl"


def field_key(row: dict) -> str:
    """The digest of everything one render's texture flatness depends on.

    `row` is a **render-cache row** — [`curation.recipes.Recipe.row`]'s output, or
    a finished-render label row, which carry the same members because both are
    what [`models.renders.spec_of`] reads.
    """
    from fractal_wallpapers.models import renders

    spec = renders.spec_of(row, Path("_unwritten"))
    loose = set(spec) - set(KEYED) - set(SPENT_AFTER) - set(PINNED)
    if loose:
        raise RegisterError(
            f"{sorted(loose)} is in the engine spec and this register has not classified "
            f"it, so a key does not say whether the texture's flatness depends on it. "
            f"KEYED is what the texture is measured over, SPENT_AFTER is what a recolour "
            f"spends once it has been, PINNED names a place rather than a picture."
        )
    missing = [name for name in KEYED if name not in spec]
    if missing:
        raise RegisterError(f"{missing} is keyed here and the engine spec no longer carries it")
    material = json.dumps({name: spec[name] for name in KEYED}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:KEY_LENGTH]


def has_a_texture(mode: str) -> bool:
    """Whether this mode's coloring has a texture layer that could be flat.

    The engine's own catalog answers it. Every other kind — a field coloring, a
    direct trap — has no second layer at all, and a composite has one but blends
    it in field space rather than shifting a palette position by it, so a flat
    composite texture is a *weaker* picture and not a different render. Only the
    modulate degenerates into an exact spelling of something else.

    **An unbuilt engine answers `False` rather than raising.** This sits on the
    labeling write path, which is otherwise reachable without a compiled crate:
    `finished.check` used to decide a store by comparing two strings and would
    become a command that needs `cargo build` to file a verdict. `False` is the
    routing this repository had before the flag existed, and a checkout that
    cannot ask the engine cannot have measured anything either — so there is
    nothing for it to be wrong about.
    """
    from fractal_wallpapers.models import renders

    try:
        catalogued = renders.catalog()
    except FileNotFoundError:
        return False
    return str(catalogued.get(str(mode), {}).get("kind")) == "modulate"


_REGISTER: dict[str, bool] | None = None


def register(reread: bool = False) -> dict[str, bool]:
    """`{field key: whether the texture was flat}`, read once a process.

    Cached because the readers that take it are per-row over stores of tens of
    thousands, and the file is one small tracked measurement that nothing rewrites
    mid-run. An absent file is an empty register and not an error: a checkout that
    has never measured routes every row as the mode it was rendered in, which is
    what every reader did before this existed.
    """
    global _REGISTER
    if _REGISTER is not None and not reread:
        return _REGISTER
    held: dict[str, bool] = {}
    here = path()
    if here.is_file():
        for line in here.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            held[str(entry["field"])] = bool(entry["flat"])
    _REGISTER = held
    return held


def flat_for(row: dict) -> bool:
    """Whether this render's texture was flat, off the register. Unmeasured is `False`.

    `False` is the honest default and not a guess: it is what every reader
    concluded before the flag existed, so a checkout with no register behaves
    exactly as this repository did the day before this landed. A `True` is always
    a measurement.

    A row this cannot key is `False` too, and the refusal is not swallowed
    quietly so much as answered: a register lookup is not the place a malformed
    render row is discovered, and the callers that take this — `finished.check`
    and `finished_train.population` — each have their own refusal for a row that
    cannot name a render.
    """
    if not has_a_texture(row.get("mode")):
        return False
    try:
        key = field_key(row)
    except (RegisterError, KeyError, TypeError):
        return False
    return register().get(key, False)


def rows_of(entries: dict) -> list[dict]:
    """The register's rows, in key order, from `{key: entry}`."""
    return [entries[key] for key in sorted(entries)]


def entry(key: str, row: dict, flat: bool, partition: str | None = None) -> dict:
    """One register row: the key, the answer, and enough beside it to read the file.

    The three carried members decide nothing — the key is the whole of the join —
    and they are here because a file of two thousand digests and two thousand
    booleans is a file nobody can check by looking at it. The frame width in
    particular is what the first attempt at a *rule* for this was read off, and
    keeping it means the next reader can re-take that reading without re-rendering
    anything.
    """
    viewport = row.get("viewport") or {}
    render = row.get("render") or {}
    return {
        "schema": SCHEMA,
        "field": str(key),
        "flat": bool(flat),
        "mode": str(row.get("mode")),
        "partition": partition,
        "resolution": list(render.get("resolution") or ()),
        "supersample": render.get("supersample"),
        "width": str(viewport.get("width")),
    }


def write(entries: dict, log=print) -> Path:
    """Ship the register. Whole-file, sorted by key, `\\n` line endings.

    Rewritten rather than appended so that the file is a pure function of what has
    been measured: two runs that measured the same identities produce the same
    bytes whichever order they ran in, and a Windows run cannot dirty every line
    of a file it only added to the end of.
    """
    here = path()
    here.parent.mkdir(parents=True, exist_ok=True)
    with here.open("w", encoding="utf-8", newline="\n") as handle:
        for stored in rows_of(entries):
            handle.write(json.dumps(stored, ensure_ascii=False) + "\n")
    log(f"[texture-flat] {len(entries):,} identities in {here}")
    global _REGISTER
    _REGISTER = None
    return here


def read_entries() -> dict[str, dict]:
    """`{field key: the whole register row}` — what [`write`] takes back."""
    here = path()
    if not here.is_file():
        return {}
    out: dict[str, dict] = {}
    for line in here.read_text(encoding="utf-8").splitlines():
        if line.strip():
            stored = json.loads(line)
            out[str(stored["field"])] = stored
    return out


# --------------------------------------------------------------------------- #
# The measurement.
# --------------------------------------------------------------------------- #
def probe(job: dict) -> dict:
    """One render, for its report alone. Runs in a worker process.

    The picture is written because the engine's `render` writes one — there is no
    subcommand that iterates and colors and keeps nothing — and it is deleted
    here. Nothing downstream reads it: a probe at a geometry the pool does not use
    would otherwise leave a picture nobody can name.
    """
    from fractal_wallpapers import engine
    from fractal_wallpapers.models import renders

    output = Path(job["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    try:
        report = engine.run("render", renders.spec_of(job["row"], output))
    except Exception as failure:  # noqa: BLE001 — a failed probe is a recorded fact
        return {"field": job["field"], "why": repr(failure)[:200]}
    finally:
        output.unlink(missing_ok=True)
    if "texture_flat" not in report:
        return {
            "field": job["field"],
            "why": "the engine reported no texture_flat, so this coloring has no texture "
            "layer and should never have been probed",
        }
    return {
        "field": job["field"],
        "flat": bool(report["texture_flat"]),
        "seconds": round(time.monotonic() - started, 3),
    }


def unmeasured(rows: list[dict], entries: dict | None = None) -> dict[str, dict]:
    """`{field key: one row standing for it}` for every identity not yet measured.

    One row per identity, not one job per row: the answer is a property of the
    field side, so thirty-two maps at a location are one render here. That is the
    whole of why this is minutes rather than an hour.
    """
    held = read_entries() if entries is None else entries
    wanted: dict[str, dict] = {}
    for row in rows:
        if not has_a_texture(row.get("mode")):
            continue
        key = field_key(row)
        if key in held or key in wanted:
            continue
        wanted[key] = row
    return wanted


def measure(
    rows: list[dict],
    partitions: dict | None = None,
    workers: int = MEASURE_WORKERS,
    limit: int | None = None,
    log=print,
) -> dict:
    """Render every unmeasured identity in `rows` and write the register.

    `rows` are render-cache rows; `partitions` is `{field key: partition}` where a
    caller has one, purely so the file reads. Rows in a mode with no texture are
    skipped rather than refused — a caller hands over a whole store and this is
    what decides which of it is a question.
    """
    from concurrent.futures import ProcessPoolExecutor

    from fractal_wallpapers.paths import under

    started = time.time()
    entries = read_entries()
    wanted = unmeasured(rows, entries)
    log(f"[texture-flat] {len(rows):,} row(s) offered; {len(wanted):,} unmeasured identities")
    keys = sorted(wanted)
    if limit is not None:
        keys = keys[: int(limit)]
        log(f"[texture-flat] limited to {len(keys):,}")
    scratch = under("coloring", "texture_flat_probe")
    jobs = [
        {"field": key, "row": wanted[key], "output": str(scratch / f"{key}.jpg")} for key in keys
    ]

    made, failed, why = 0, 0, []
    engine_seconds = 0.0
    named = dict(partitions or {})
    with ProcessPoolExecutor(max_workers=int(workers)) as pool:
        for done, out in enumerate(pool.map(probe, jobs), start=1):
            if "flat" not in out:
                failed += 1
                why += [out][: max(0, 20 - len(why))]
                continue
            made += 1
            engine_seconds += float(out.get("seconds") or 0.0)
            key = out["field"]
            entries[key] = entry(key, wanted[key], out["flat"], named.get(key))
            if done % 100 == 0 or done == len(jobs):
                wall = time.time() - started
                rate = done / max(1e-9, wall)
                log(
                    f"[texture-flat] {done:,} of {len(jobs):,} probed in {wall / 60:.1f} min "
                    f"({rate:.2f}/s, ~{(len(jobs) - done) / max(1e-9, rate) / 60:.0f} min left)"
                )
    if jobs:
        write(entries, log=log)
    with contextlib.suppress(OSError):
        scratch.rmdir()
    wall = time.time() - started
    return {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "offered": len(rows),
        "unmeasured": len(wanted),
        "probed": len(jobs),
        "measured": made,
        "failed": failed,
        "why": why,
        "register": len(entries),
        "flat": sum(1 for stored in entries.values() if stored["flat"]),
        "workers": int(workers),
        "wall_seconds": round(wall, 1),
        "engine_seconds": round(engine_seconds, 1),
        "seconds_per_probe": round(engine_seconds / max(1, made), 4),
    }


# --------------------------------------------------------------------------- #
# The two stores that carry renders, and what a measurement is taken over.
# --------------------------------------------------------------------------- #
#: The two stores whose rows name a render this could be a question about, and the
#: word the CLI takes for each. `ledger` rows are drawn at the candidate regime and
#: `labels` at the shipping one, so a place that appears in both is two identities
#: and two probes.
STORES: tuple[str, ...] = ("ledger", "labels")


def candidate_rows(log=print) -> tuple[list[dict], dict]:
    """Every candidate-ledger row in a mode with a texture, as render-cache rows.

    Streamed rather than read, and filtered on the mode before the recipe is
    rebuilt: `recipes.of_record` over a hundred and twenty thousand rows is a
    minute nobody needs to spend to find the one mode this asks about.
    """
    from fractal_wallpapers.curation import candidate_ledger, recipes

    out, named = [], {}
    for stored in candidate_ledger.stream():
        recipe = stored.get("recipe") or {}
        if not has_a_texture(recipe.get("mode")):
            continue
        row = recipes.of_record(recipe).row()
        out.append(row)
        named.setdefault(field_key(row), str(stored.get("partition")))
    log(f"[texture-flat] {len(out):,} ledger row(s) in a mode with a texture")
    return out, named


def label_rows(log=print) -> tuple[list[dict], dict]:
    """Every finished-render label row in a mode with a texture.

    Both stores, and the **resolved** read each consumer routes through, so a
    superseded verdict does not buy a second probe of the render it was about. A
    label row is already the render-cache row shape.
    """
    from fractal_wallpapers.labeling import finished

    out, named = [], {}
    for head in finished.HEADS:
        held = [row for row in finished.resolved(head).scored() if has_a_texture(row.get("mode"))]
        log(f"[texture-flat] {len(held):,} resolved {head} row(s) in a mode with a texture")
        for row in held:
            out.append(row)
            named.setdefault(field_key(row), str(row.get("partition")))
    return out, named


def measure_stores(
    stores: tuple[str, ...] = STORES,
    workers: int = MEASURE_WORKERS,
    limit: int | None = None,
    log=print,
) -> dict:
    """Fill the register from whichever stores were named. THE measurement leg."""
    rows: list[dict] = []
    named: dict = {}
    for name in stores:
        if name not in STORES:
            raise RegisterError(f"{name!r} is not one of {list(STORES)}")
        held, from_here = (candidate_rows if name == "ledger" else label_rows)(log=log)
        rows += held
        named.update(from_here)
    record = measure(rows, partitions=named, workers=workers, limit=limit, log=log)
    return {**record, "stores": list(stores)}


def stamp_ledger(log=print) -> dict:
    """Write the measured flag onto the candidate-ledger rows that carry a texture.

    The ledger's half of the backfill, and it renders nothing: every answer is
    already in the register, keyed on the field side of the render, so this is a
    stream, a lookup and an upsert.

    **Only the rows in a mode with a texture are rewritten.** A row of any other
    mode has no texture layer to be flat and reads `False` through the `.get` every
    consumer takes, so touching a hundred and twenty thousand of them to write a
    constant would be a hundred and twenty thousand lines of diff saying nothing.
    Rows mined since the engine began reporting it already carry their own flag
    and are re-stamped with the same value.

    It goes through [`curation.candidate_ledger.merge`] and not through the row
    writer beneath it, because a store written without being recorded is what that
    door exists to stop: the manifests are the only thing the history keeps about
    this store, and adding a member to a row moves the sha256 of the file they
    describe.
    """
    from fractal_wallpapers.curation import candidate_ledger, recipes

    held = register()
    rows, changed, unmeasured_count = [], 0, 0
    for stored in candidate_ledger.stream():
        recipe = stored.get("recipe") or {}
        if not has_a_texture(recipe.get("mode")):
            continue
        measured = held.get(field_key(recipes.of_record(recipe).row()))
        if measured is None:
            unmeasured_count += 1
            measured = bool(stored.get("texture_flat"))
        changed += int(bool(measured) != bool(stored.get("texture_flat")))
        rows.append({**stored, "texture_flat": bool(measured)})
    log(
        f"[texture-flat] {len(rows):,} ledger row(s) carry a texture; "
        f"{sum(1 for r in rows if r['texture_flat']):,} flat, {changed:,} moved, "
        f"{unmeasured_count:,} unmeasured"
    )
    written = candidate_ledger.merge(rows, [], log=log) if rows else {}
    return {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stamped": len(rows),
        "flat": sum(1 for stored in rows if stored["texture_flat"]),
        "moved": changed,
        "unmeasured": unmeasured_count,
        "ledger": written.get("ledger"),
        "recorded": written.get("recorded"),
    }


def summary(entries: dict | None = None) -> dict:
    """What the register holds, over the axes a reader asks about."""
    held = read_entries() if entries is None else entries
    by_mode: dict = {}
    by_partition: dict = {}
    by_regime: dict = {}
    for stored in held.values():
        for table, name in (
            (by_mode, str(stored.get("mode"))),
            (by_partition, str(stored.get("partition"))),
            (
                by_regime,
                f"{'x'.join(str(n) for n in stored.get('resolution') or [])}"
                f"ss{stored.get('supersample')}",
            ),
        ):
            seen = table.setdefault(name, {"identities": 0, "flat": 0})
            seen["identities"] += 1
            seen["flat"] += int(bool(stored.get("flat")))
    return {
        "schema": SCHEMA,
        "path": str(path()),
        "identities": len(held),
        "flat": sum(1 for stored in held.values() if stored.get("flat")),
        "by_mode": dict(sorted(by_mode.items())),
        "by_regime": dict(sorted(by_regime.items())),
        "by_partition": dict(sorted(by_partition.items())),
    }


__all__ = [
    "KEYED",
    "STORES",
    "KEY_LENGTH",
    "MEASURE_WORKERS",
    "PINNED",
    "SCHEMA",
    "SPENT_AFTER",
    "RegisterError",
    "candidate_rows",
    "entry",
    "field_key",
    "flat_for",
    "has_a_texture",
    "label_rows",
    "measure",
    "measure_stores",
    "path",
    "probe",
    "read_entries",
    "register",
    "rows_of",
    "stamp_ledger",
    "summary",
    "unmeasured",
    "write",
]
