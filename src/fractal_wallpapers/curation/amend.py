"""Re-reading a location whose standing score was read off a picture nobody has.

The supply sidecar ([`curation.intake`]) holds one row per location the location
head has an opinion about, and the gallery pass seats on those numbers. Each row
names the picture its score was read off — a regime and a view name — and for
tens of thousands of rows that name no longer describes anything on this machine:
the view was drawn at a geometry the read no longer uses, or under a recipe whose
digest has since moved, or by an engine build nobody wrote down. The score is
still a number, it still sorts, and nothing about it looks wrong.

So a location's score is **stale** unless all three hold:

* the row was read at the regime the sidecar reads at today ([`intake.READ_REGIME`]);
* the view it names is the one today's recipe produces for that location; and
* a stamp beside that view says today's engine drew it
  ([`fractal_wallpapers.engine_fingerprint`]).

The third is the one nothing could ask before. The first two are digests and a
digest is only ever about the *instruction*; which program carried the
instruction out is not in it.

## The re-read lands in an amendment, and the sidecar is not touched

`supply_scores.jsonl` is what the head said on the night it said it, joined to
the picture it was said about. That is the right thing for a record to hold and
the wrong thing to edit: a pass that overwrote it would delete the only evidence
of what the seating was actually decided on, and it would do so for a population
whose old pictures are already gone.

The amendment is a second file, append-only, keyed by **(location key, engine
fingerprint)**. It carries the old score, the new score, and the fingerprint the
old view was drawn under — [`engine_fingerprint.UNKNOWN`] wherever that was never
recorded, which is every row written before the stamp existed. Two engines'
readings of one location are two rows and neither hides the other, so a build can
be rolled back without re-rendering anything.

**Readers of a seating score prefer the amendment.** They get it for free:
[`intake.read_scores`] overlays it, and every reader of a seating score in this
project goes through that one door — `curate score`'s own offer, the gallery
pass's admission cut, its slot guarantee, its quality sort and its rank table.
The harvest side does not, and is deliberately left alone: a walk scores the gate
render it *just made*, so its floor reads are already current by construction and
have no cached picture to be stale about.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from fractal_wallpapers import engine_fingerprint
from fractal_wallpapers.models import location_view

#: The schema every amendment row carries.
SCHEMA = 1

#: What the amendment is called, beside the sidecar it amends.
AMENDMENTS_NAME = "score_amendments.jsonl"

#: How many pictures the head reads at once. The sidecar's own batch size, so the
#: re-read is the same arithmetic on the same device as the reading it replaces.
BATCH = 64

#: How often the refresh says where it is. Ninety thousand renders is the best
#: part of an hour and a leg that says nothing until it lands is a leg nobody can
#: tell from a hung one.
PROGRESS = 500


class AmendError(RuntimeError):
    """The amendment cannot be read, or the supply cannot be re-read."""


def path() -> Path:
    """Where the amendment lives: beside the sidecar, under the ignored tree."""
    from fractal_wallpapers.curation import intake

    return intake.store_dir() / AMENDMENTS_NAME


def rows(where: Path | None = None) -> list[dict]:
    """Every amendment row ever appended, in the order they were written."""
    where = path() if where is None else Path(where)
    if not where.is_file():
        return []
    out = []
    for number, line in enumerate(where.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema") != SCHEMA:
            raise AmendError(f"{where}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}")
        out.append(row)
    return out


def read(fingerprint: str | None = None, where: Path | None = None) -> dict[str, dict]:
    """`{location key: row}` for one engine build. Last row for a key wins.

    Filtered by build rather than merged across builds, because two builds'
    readings of one location are two different measurements and a reader that
    took whichever was written last would be ranking one against the other.

    An empty amendment is answered **without asking the engine what it is**. The
    fingerprint costs six renders, `intake.read_scores` comes through here on
    every call, and a checkout that has never run `curate redraw` would otherwise
    need a built binary to read a score off a file.
    """
    every = rows(where)
    if not every:
        return {}
    mark = engine_fingerprint.current() if fingerprint is None else str(fingerprint)
    return {row["key"]: row for row in every if row.get("engine") == mark}


def append(minted: list[dict], where: Path | None = None) -> Path:
    """Append these rows. Never rewrites, so an interrupted refresh keeps what it did."""
    where = path() if where is None else Path(where)
    if not minted:
        return where
    where.parent.mkdir(parents=True, exist_ok=True)
    with where.open("a", encoding="utf-8", newline="\n") as handle:
        for row in minted:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return where


def overlay(scores: dict, amendments: dict | None = None) -> dict:
    """`scores` with every amended location's reading replacing the sidecar's.

    The row that comes out is the sidecar's row with the new cutpoints, the new
    picture and the new geometry written over it, plus an `amended` block naming
    what it was. Same shape in and out: every reader of a seating score already
    reads a sidecar row, and an amendment that came back as a different kind of
    object would be an amendment each of them had to learn about.
    """
    amendments = read() if amendments is None else amendments
    if not amendments:
        return scores
    out = dict(scores)
    for key, amendment in amendments.items():
        was = out.get(key)
        if was is None:
            continue
        fresh = dict(was)
        for name in ("p_ge2", "p_ge3", "p_ge4"):
            fresh[name] = amendment.get(name)
        fresh["regime"] = amendment.get("regime")
        fresh["view"] = amendment.get("view")
        fresh["head_sha256"] = amendment.get("head_sha256", was.get("head_sha256"))
        fresh["amended"] = {
            "engine": amendment.get("engine"),
            "was_engine": amendment.get("was_engine"),
            "was_regime": amendment.get("was_regime"),
            "was_view": amendment.get("was_view"),
            "was_p_ge3": amendment.get("was_p_ge3"),
            "was_p_ge4": amendment.get("was_p_ge4"),
        }
        out[key] = fresh
    return out


# --------------------------------------------------------------------------- #
# Which rows are stale.
# --------------------------------------------------------------------------- #
def wanted_view(row: dict, colormap: str, cyclic: set[str], regime) -> str:
    """The **file name** today's recipe files this location's view under, at `regime`.

    Off `view_path` and not off `view_name`: the sidecar records the picture's
    file name and `view_name` is the digest without the suffix, so comparing the
    two directly declares every row in the supply stale by recipe. It did.
    """
    return location_view.view_path(row, colormap, cyclic, Path(), regime).name


def staleness(row: dict, want: str, regime, marks) -> str | None:
    """Why this row's score is stale, or `None` where it is current.

    A reason and not a boolean, because the three ways a standing score stops
    describing a picture are three different facts about how this supply was
    assembled and the report is worth being able to split by them.

    * `regime` — the row was read at another geometry, which for this supply means
      the deploy one, before old stock started falling to the node regime.
    * `picture` — the file the score was read off is not the one today's recipe
      names. Either the walk's own gate render, which is filed under the run's
      node id rather than under a digest, or a view whose digest has since moved.
    * `engine` — the right file, and no stamp saying today's engine drew it.
    """
    if str(row.get("regime") or "") != regime.spelled:
        return "regime"
    if str(row.get("view") or "") != want:
        return "picture"
    if not marks.is_current(want):
        return "engine"
    return None


# --------------------------------------------------------------------------- #
# The refresh.
# --------------------------------------------------------------------------- #
def refresh(
    device: str = "auto",
    limit: int | None = None,
    resume: bool = True,
    log=print,
) -> dict:
    """Re-render every stale view at the node regime, re-read it, and amend.

    Serial on purpose: the engine threads inside a single render, so a pool of
    them is the same total work with several ramp-ups — the measurement is in
    [`fractal_wallpapers.discovery.scoring`] and it went the other way from the
    guess. A render at this regime is about thirty milliseconds.

    Idempotent and resumable. A second call over an unchanged supply through an
    unchanged engine finds every row current and writes nothing; an interrupted
    call has appended exactly the rows it finished, and `resume` is what makes
    those rows a reason to skip rather than work to repeat.
    """
    from fractal_wallpapers.curation import floors, intake
    from fractal_wallpapers.models import scoring, ship, train

    standing = intake.stored_scores()
    if not standing:
        raise AmendError(
            f"{intake.scores_path()} holds no row, so there is no standing score to amend. "
            f"Run `fractal-wallpapers curate score` first."
        )

    regime = intake.READ_REGIME
    colormap = intake.canonical_map()
    cyclic = location_view.cyclic_maps()
    directory = intake.view_dir(regime)
    directory.mkdir(parents=True, exist_ok=True)
    build = engine_fingerprint.current()
    marks = engine_fingerprint.stamps(directory, build)
    already = read(build) if resume else {}
    log(f"[amend] engine {build}; {len(standing):,} standing score(s), {len(already):,} amended")

    stale: list[tuple[dict, str, str]] = []
    reasons: dict[str, int] = {}
    for row in standing:
        want = wanted_view(row, colormap, cyclic, regime)
        why = staleness(row, want, regime, marks)
        if why is None or row["key"] in already:
            continue
        reasons[why] = reasons.get(why, 0) + 1
        stale.append((row, want, why))
    if limit is not None:
        stale = stale[: max(0, int(limit))]
    log(
        f"[amend] {len(stale):,} stale: "
        + ", ".join(f"{count:,} by {name}" for name, count in sorted(reasons.items()))
    )
    if not stale:
        return _report(build, standing, already, [], reasons, 0.0, 0.0, marks)

    clock = time.monotonic()
    pictures: list[Path] = []
    drawn = 0
    for index, (row, _want, _why) in enumerate(stale, start=1):
        picture, made = location_view.render_view(row, colormap, cyclic, directory, regime)
        pictures.append(picture)
        drawn += int(made)
        if index % PROGRESS == 0:
            rate = index / max(1e-9, time.monotonic() - clock)
            left = (len(stale) - index) / max(1e-9, rate)
            log(f"[amend] {index:,}/{len(stale):,} drawn, {rate:.1f}/s, ~{left / 60:.0f} min left")
    render_seconds = time.monotonic() - clock

    clock = time.monotonic()
    model, config, where = scoring.load(ship.shipped_path("location"), device)
    classes = int(config["classes"])
    stamp = floors.live_stamp("location")
    log(f"[amend] {len(pictures):,} view(s) through the location head {stamp[:12]} on {where}")
    probabilities = train.score(
        model, pictures, scoring.transform_of(config), where, classes, {"batch_size": BATCH}
    )
    score_seconds = time.monotonic() - clock

    minted = []
    for (row, _want, why), picture, probability in zip(stale, pictures, probabilities, strict=True):
        record = {
            "schema": SCHEMA,
            "key": row["key"],
            "engine": build,
            # What the standing score was read off. `unknown` is not a gap: it is
            # the honest name for a build nothing wrote down, which is every view
            # drawn before the stamp existed.
            "was_engine": engine_fingerprint.UNKNOWN,
            "was_regime": row.get("regime"),
            "was_view": row.get("view"),
            "was_p_ge3": row.get("p_ge3"),
            "was_p_ge4": row.get("p_ge4"),
            "stale": why,
            "head": "location",
            "head_sha256": stamp,
            "regime": regime.spelled,
            "view": picture.name,
        }
        for index in range(classes - 1):
            record[f"p_ge{index + 2}"] = float(probability[index])
        minted.append(record)
    append(minted)
    log(f"[amend] {len(minted):,} amendment row(s) appended to {path()}")
    return _report(build, standing, already, minted, reasons, render_seconds, score_seconds, marks)


def _report(build, standing, already, minted, reasons, render_seconds, score_seconds, marks):
    """What one refresh did, and what it did to the population."""
    return {
        "schema": SCHEMA,
        "engine": build,
        "standing": len(standing),
        "already_amended": len(already),
        "stale_by": dict(sorted(reasons.items())),
        "amended": len(minted),
        "views": marks.summary(),
        "seconds": {
            "render": round(render_seconds, 1),
            "score": round(score_seconds, 1),
        },
        "shift": shift(minted),
        "amendment": str(path()),
    }


def shift(minted: list[dict], moved: float = 0.02) -> dict:
    """What the re-read did to `P(>=4)`, and how many locations crossed a floor.

    The whole point of the pass, as one block: how far the population moved, which
    way, and — the question seating actually turns on — how many places changed
    side of the admission floor in each direction.
    """
    from fractal_wallpapers.curation import floors

    deltas = [
        (float(row["p_ge4"]) - float(row["was_p_ge4"]), row)
        for row in minted
        if row.get("p_ge4") is not None and row.get("was_p_ge4") is not None
    ]
    admitted_before = admitted_after = 0
    rose = fell = 0
    for row in minted:
        was = floors.passes_junk_floor(row.get("was_p_ge3"))
        now = floors.passes_junk_floor(row.get("p_ge3"))
        admitted_before += int(was)
        admitted_after += int(now)
        rose += int(now and not was)
        fell += int(was and not now)
    if not deltas:
        return {"rows": 0}
    values = sorted(delta for delta, _row in deltas)
    return {
        "rows": len(values),
        "moved_over": moved,
        "fraction_moved": round(sum(1 for x in values if abs(x) > moved) / len(values), 4),
        "fraction_lower": round(sum(1 for x in values if x < 0) / len(values), 4),
        "max_abs": round(max(abs(values[0]), abs(values[-1])), 6),
        "median": round(values[len(values) // 2], 6),
        "junk_floor": {
            "admitted_before": admitted_before,
            "admitted_after": admitted_after,
            "rose_over": rose,
            "fell_under": fell,
        },
    }


# --------------------------------------------------------------------------- #
# Keeping it. The amendment is the one file here nothing can make again cheaply.
# --------------------------------------------------------------------------- #
def backup_path() -> Path:
    """The durable copy, beside the sidecar's on the archive tier.

    The same [`curation.durability.BACKUP_UNIT`] as the sidecar this file amends,
    and for that module's reason: a copy resolved through `under()` would land on
    the tier the original is already on, which is the one place a second copy is
    no use.
    """
    from fractal_wallpapers.curation import durability
    from fractal_wallpapers.paths import archive_root, hot_root

    archive = archive_root()
    root = hot_root() if archive is None else archive
    return Path(root) / durability.BACKUP_UNIT / AMENDMENTS_NAME


def manifest_path() -> Path:
    """The tracked manifest: what the amendment was, last time anybody recorded it."""
    from fractal_wallpapers.paths import repo_root

    return repo_root() / "data" / "curation" / "score_amendments.manifest.json"


def durable():
    """The amendment as a [`curation.durability.Durable`] — saved, checked, restored.

    It gets what the sidecar gets, and the case is sharper than the sidecar's. A
    row here is a re-read of a location through the shipped location head over a
    view **re-rendered for it**, so rebuilding the file is [`refresh`] over the
    whole supply: about ninety thousand renders, the best part of an hour, and
    only on a machine whose engine still fingerprints the same — a build that has
    moved on cannot reproduce these rows at all, it can only write different ones
    beside them. Tracking it is out for the usual reason and by a wide margin:
    tens of megabytes against a 1 MiB per-file history guard.

    Unlike every other durable here it is **append-only**, which is what makes
    [`durables.guard`] worth extending to it: a shorter file is always a loss
    and never an ordinary state.
    """
    from fractal_wallpapers.curation import durability

    return durability.Durable(
        name="the score amendment",
        live=path(),
        copy=backup_path(),
        manifest=manifest_path(),
        why_not_tracked=(
            "tens of megabytes of re-read scores against a 1 MiB per-file history guard, "
            "and it grows by an append every time a build change makes a standing score "
            "stale. The manifest is what the history keeps: the row count, the bytes, the "
            "sha256, and how many rows each engine build contributed."
        ),
        save_command="fractal-wallpapers curate amendments save",
        restore_command="fractal-wallpapers curate amendments restore",
        rebuild_command="fractal-wallpapers curate redraw",
        facts=_facts,
    )


def _facts(where: Path) -> dict:
    """The columns this file adds to its manifest: which engine build read what.

    Per build and not in total, because the amendment is keyed on (location,
    engine) and two builds' readings of one location are two measurements. A
    manifest that gave one number would be describing a population that does not
    exist.
    """
    from collections import Counter

    builds: Counter = Counter()
    keys = set()
    with Path(where).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            builds[str(row.get("engine"))] += 1
            keys.add(str(row.get("key")))
    return {"locations": len(keys), "rows_by_engine": dict(sorted(builds.items()))}


__all__ = [
    "AMENDMENTS_NAME",
    "BATCH",
    "PROGRESS",
    "SCHEMA",
    "AmendError",
    "append",
    "backup_path",
    "durable",
    "manifest_path",
    "overlay",
    "path",
    "read",
    "refresh",
    "rows",
    "shift",
    "staleness",
    "wanted_view",
]
