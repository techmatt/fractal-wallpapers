"""Putting back a picture the row still names, and reading a score onto it.

The engine-driving half. [`re_render`] makes pixels a row promises and the disk
has lost; [`rescore`] reads the live judge over pictures that have one. Both are
legs — three workers, below-normal, minutes to hours — and both are why this
module and not [`store`] is what imports a judge and a colormap.
"""

from __future__ import annotations

import json
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.curation.candidate_ledger import rows as rows_module
from fractal_wallpapers.curation.candidate_ledger import store
from fractal_wallpapers.curation.candidate_ledger.store import SCHEMA
from fractal_wallpapers.paths import Tiers, rehome, tracked_name, under

# --------------------------------------------------------------------------- #
# Putting back a picture the row still names.
# --------------------------------------------------------------------------- #
#: Where a re-render leg dumps the fields it shares inside one (location, mode),
#: and writes its record. Its own subtree under the regenerable tree rather than
#: a directory inside the store, because the store holds three files and a fourth
#: thing living beside them is how a sweep comes to read one.
RE_RENDER_UNIT = "re_render"


#: How many engines a re-render drives at once. **Three**, this machine's render
#: pool — the same number every leg here takes, and a rule about the desktop
#: rather than a tuning knob. The priority half is [`engine.run`]'s and needs
#: nothing here.
RE_RENDER_WORKERS = 3


def read_keys(path) -> set[str]:
    """The **recipe** keys a key manifest names. `{key}`.

    JSONL like every other record here — one object a line, an integer `schema`, a
    `key` — and a manifest rather than a repeated flag for the reason every batch
    subcommand here takes one: a Windows command line overflows long before a list
    of recipes does. Deliberately not [`curation.intake.read_keys`], which reads the
    same shape holding *location* keys: the two are different identities and a
    reader that took either would join silently wrong.
    """
    path = Path(path)
    if not path.is_file():
        raise store.LedgerError(
            f"{path} is not there, so there is no set of recipes to act on. A key manifest "
            f"is one JSON object a line, each with a `schema` and a `key`."
        )
    keys = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        held = row.get("key") or row.get("recipe_key")
        if not held:
            raise store.LedgerError(f"{path} line {number} names no `key`")
        keys.add(str(held))
    if not keys:
        raise store.LedgerError(f"{path} holds no key, so there is nothing to act on")
    return keys


def re_render_dir() -> Path:
    """The subtree one re-render leg owns: its dumped fields and its record."""
    return under("curation", RE_RENDER_UNIT)


def missing_pictures(rows=None) -> list[dict]:
    """Every row whose picture the store names and the disk does not have.

    **The rule and nothing but the rule.** A row is here because it survived
    [`prune`] and its JPEG is gone, and for no other reason — no bar, no mode
    roster, no clearing test. A picture is kept if and only if its row is, so a
    retained row with no picture is a store that disagrees with itself, whatever
    the row's score happens to be.
    """
    stored = store.read() if rows is None else list(rows)
    present = store.present_pictures(stored)
    return [row for row in stored if str(row["key"]) not in present and row.get("picture")]


def bare_varied(out=None, log=print) -> dict:
    """Every row whose stored picture is the **bare** mode under a varied key.

    The population of the repair `mine.make`'s dropped `mode_params` left behind:
    a row carrying settings whose file was drawn without them, so the picture is
    not the recipe's, the key names one picture and the disk holds another, and
    every score on the row is a reading of the wrong file. There is no way to see
    it by looking — the bare picture is a perfectly good picture of something
    else — which is why this is derived from the row rather than detected.

    **Which maker drew it is read off the picture's path**, because after six days
    of a maker dropping a keyword that is the only durable place the fact lives.
    `hunt` and `label_migration` have always passed the settings, so a picture
    under either is what its key says; everything else with a non-empty
    `mode_params` went through `mine.make` or has not been checked, and is in.
    That is the safe direction and it is [`curation.label_fate.drawn_bare`]'s
    rule, reached rather than restated — the claim about which makers were
    settings-aware is one somebody measured and it has one home.

    **Streams the store.** The pool is hundreds of megabytes and this wants a
    key and two members off each row, so it never holds one: writing a manifest
    of ten thousand keys must not be a pool-holding process.
    """
    from fractal_wallpapers.curation import label_fate

    aware = set(label_fate.SETTINGS_AWARE_SUBTREES)
    out = re_render_dir() / "bare_varied.jsonl" if out is None else Path(out)
    by_leg: dict = {}
    varied = 0
    named: list = []
    for row in store.stream():
        settings = (row.get("recipe") or {}).get("mode_params") or {}
        if not settings:
            continue
        varied += 1
        leg = label_fate.leg_of(row.get("picture"))
        if leg.split("/")[0] in aware:
            continue
        by_leg[leg] = by_leg.get(leg, 0) + 1
        named.append({"schema": SCHEMA, "key": str(row["key"]), "leg": leg})
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        for held in named:
            handle.write(json.dumps(held, ensure_ascii=False) + "\n")
    log(f"[bare-varied] {len(named):,} of {varied:,} varied row(s) — {tracked_name(out)}")
    return {
        "schema": SCHEMA,
        "at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "varied_rows": varied,
        "drawn_bare": len(named),
        "settings_aware": sorted(aware),
        "by_leg": dict(sorted(by_leg.items(), key=lambda item: -item[1])),
        "manifest": tracked_name(out),
    }


def recolour(keys, limit: int | None = None, log=print) -> dict:
    """Re-read the **colour block** of the named rows off their pictures now on disk.

    The third companion of [`re_render`]'s `keys` and [`rescore`]'s, and it exists
    because a corrected picture invalidates more than its score. A ledger row
    carries a colour census — the swatch shares and cells [`rows.colour_block`]
    reduces — read off the picture when the row was made. `re_render` writes no
    row, deliberately, so after a repair that census is a reading of the file that
    *used* to be there.

    **It was found by a guard rather than reasoned about**, which is the honest
    account: `test_the_stored_colour_block_is_what_the_picture_still_reads_as`
    samples eighty rows and decodes them, and two of the eighty disagreed after the
    10,664-row repair — both rows the repair had touched. That test has been in the
    suite since 2026-08-27 and this is the first leg to move enough pictures to
    trip it.

    **Three readings come off a picture and this re-reads all of them**: the colour
    census on the row, the flatness column in its sidecar, and the pixel-cloud
    signature in its own. Only the first was found by a guard; the other two were
    measured after it — 10,664 stale flatness rows and 949 stale signatures — and
    they are here because they fail the same way for the same reason. `flatness`
    feeds [`curation.rank_key`], so a stale column is a seating sorted on the wrong
    picture.

    Nothing else about the row moves: same key, same recipe, same picture path.
    The upsert is by key, so a re-run over unchanged pictures writes the same bytes
    and reports `changed: 0`.
    """
    from fractal_wallpapers.curation import durability
    from fractal_wallpapers.palettes import dominance

    started = time.time()
    named = {str(key) for key in keys}
    wanted = [row for row in store.stream() if str(row["key"]) in named]
    absent = named - {str(row["key"]) for row in wanted}
    if limit is not None:
        wanted = wanted[: max(0, int(limit))]
    log(f"[recolour] {len(wanted):,} of {len(named):,} named row(s) are in the store")
    tiers = Tiers.current()
    fresh, changed, no_picture = [], 0, 0
    for at, row in enumerate(wanted, start=1):
        named_at = row.get("picture")
        picture = None if not named_at else rehome(str(named_at), tiers)
        if picture is None or not picture.is_file():
            no_picture += 1
            continue
        block = rows_module.colour_block(dominance.of_picture(picture))
        if block != row.get("colour"):
            changed += 1
            fresh.append({**row, "colour": block})
        if at % 2000 == 0:
            log(f"[recolour] {at:,} of {len(wanted):,} read in {(time.time() - started) / 60:.1f}m")
    path, total, new = store.write(fresh) if fresh else (store.rows_path(), 0, 0)
    saved = durability.save(store.durable_rows(), log=log) if fresh else None
    record = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "named": len(named),
        "in_the_store": len(wanted),
        "not_in_the_store": len(absent),
        "no_picture_on_disk": no_picture,
        "read": len(wanted) - no_picture,
        "changed": changed,
        "unchanged": len(wanted) - no_picture - changed,
        "unchanged_is": "the picture reads as the census already on the row, which a repair "
        "that moved no pixels for this recipe is: the settings make no difference to it",
        "ledger_rows": total,
        "ledger_new": new,
        "wall_seconds": round(time.time() - started, 1),
        "saved": saved,
        "rows_path": tracked_name(path),
    }
    log(f"[recolour] {changed:,} row(s) re-read in {record['wall_seconds'] / 60:.1f} min")

    # **The other two readings off the same pictures.** Both sidecars are
    # incremental on the KEY, and a re-render keeps the key and the path — so both
    # would go on serving a reading of the file that used to be there. `flatness`
    # feeds `curation.rank_key`, which is what a seating sorts on; `signatures`
    # feeds the diversity rule. Told which keys are stale, each re-reads exactly
    # those instead of the whole store.
    from fractal_wallpapers.curation import flatness, signatures

    touched = {str(row["key"]) for row in wanted}
    record["flatness"] = flatness.sweep(flatness.of_rows(wanted), stale=touched, log=log)
    swept = [row for row in wanted if row.get("picture")]
    record["signatures"] = signatures.sweep(
        _named_pictures(swept), stale=touched & set(signatures.by_recipe()), log=log
    )
    return record


class _NamedPicture:
    """A `(key, picture)` pair in the shape both sidecar sweeps read."""

    __slots__ = ("key", "picture")

    def __init__(self, key: str, picture: str) -> None:
        self.key, self.picture = key, picture


def _named_pictures(rows) -> list:
    """Ledger rows as the sweeps' candidate shape. Order preserved."""
    return [_NamedPicture(str(row["key"]), str(row["picture"])) for row in rows]


#: One worker process's copy of the cyclic-colormap set, built on first use.
#: A module global because that is what a spawned worker keeps between tasks.
_CYCLIC: set | None = None


def render_pair(payload: dict) -> dict:
    """One (location, mode) pair's missing pictures, in a worker. **Module level.**

    A Windows pool *spawns*, so a closure over the work list would not pickle;
    this takes a plain dict and re-imports what it needs once per worker.

    The pair is the unit rather than the row because a shareable mode's field is
    dumped once per (location, mode) and every map at it after that is a recolour
    — so two rows of one pair rendered in two workers would each pay the dump,
    and would race to write it. One pair, one worker, one dump.

    ## What a restored picture has to be, and the member this forgot

    A put-back is only a put-back if the file reproduces the **key** the row is
    filed under, and that key digests every member of [`recipes.KEYED`]. This built
    its engine spec by naming four of them, so `mode_params` was silently dropped
    and a varied row's restored picture was the bare mode's — the same defect
    [`curation.mine.make`] carried, one function away, and it would have quietly
    undone that fix on any row this leg touched.

    `mode_params` is passed now, and the two members it still does not pass —
    `curve` and `palette` — are **checked instead of assumed**: they are
    [`colorize.render`]'s overrides, which refuse a `fields` directory, so passing
    them would cost this leg its field sharing on every row to serve a case the
    pool does not hold. A row whose recipe names anything but the candidate path's
    own curve and palette is counted as failed with the reason, rather than
    restored as a picture that is not it. `mode_params` needs no such trade: a
    non-empty one already takes the render path in [`colorize._shared_field`], so
    an unvaried row keeps its dump and a varied one never wanted one.
    """
    from fractal_wallpapers.curation import colorize, recipes

    # Read once per WORKER and not once per pair. A pool task is one (location,
    # mode) and there are thirty-two thousand of them; the cyclic set is a read
    # of the colormap library, and paying it per task put the pool's concurrency
    # at 1.42 of three workers — half the machine idle behind a file read.
    global _CYCLIC
    if _CYCLIC is None:
        _CYCLIC = colorize.cyclic()
    cyclic = _CYCLIC
    fields = Path(payload["fields"]) if payload.get("fields") else None
    out = {"made": 0, "failed": 0, "seconds": 0.0, "why": []}
    started = time.time()
    for job in payload["rows"]:
        stored = job["recipe"]
        row = {
            "family": stored["family"],
            "viewport": stored["viewport"],
            "maxiter": int(stored["maxiter"]),
        }
        colormap = str(stored["colormap"])
        # [`colorize.is_candidate_path`] and not the test spelled again: three
        # places need to know whether a stored recipe is one the candidate path
        # could have made, and each had worked it out for itself. `mode_params` is
        # part of that rule and is NOT a reason to refuse here — a non-empty one
        # already takes the render path, so it is served correctly; the curve and
        # the palette are what the field cache cannot carry.
        if not colorize.is_candidate_path({**stored, "mode_params": {}}, cyclic):
            out["failed"] += 1
            out["why"].append(
                f"{job['key']}: its recipe names a curve or palette the candidate path does "
                f"not spend, and this leg serves those out of the field cache, which would "
                f"put back the plain picture under this row's name"
            )
            continue
        try:
            colorize.render(
                row,
                str(stored["mode"]),
                colormap,
                cyclic,
                Path(job["picture"]),
                level=True,
                fields=fields,
                # The member this forgot. Without it a varied row's put-back is the
                # bare mode's picture under the variant's key — see the docstring.
                mode_params=dict(stored.get("mode_params") or {}),
            )
        except Exception as failure:  # noqa: BLE001 — a failed render is a recorded fact
            out["failed"] += 1
            out["why"].append(f"{job['key']}: {failure!r}"[:200])
            continue
        out["made"] += 1
    out["seconds"] = round(time.time() - started, 3)
    out["recipes"] = recipes.SCHEMA
    return out


def re_render(
    limit: int | None = None,
    workers: int = RE_RENDER_WORKERS,
    share_fields: bool = True,
    keys=None,
    log=print,
) -> dict:
    """Render every picture the store names and cannot find. Writes no row.

    **`keys` names rows to render whether or not their file is there**, and that is
    the one case for it: a stored picture that is not its own recipe's picture is
    worse than a missing one, because nothing looks broken. It is how the seats
    exposed by `mine.make`'s dropped `mode_params` were put right — the file was on
    disk, decodable, and of another coloring. The population is then exactly those
    rows and the record says which selector ran, so a re-render over named keys is
    never confused with a sweep for absent files. The key guard below runs
    unchanged: a named row that does not reproduce its own key is refused like any
    other.

    The ledger's second invariant, run as a repair: **the picture stays
    re-renderable from the row alone**. `recipes.of_record` rebuilds the recipe
    off the row and `Recipe.row` is the engine spec, so a row that survived
    [`prune`] can always have its pixels put back — which is the argument the
    prune was taken on, and this is the first thing to ever test it at scale.

    **The same pixels, not similar ones.** Each row is checked before it is
    rendered: the recipe the render path derives — the palette knobs from the
    cyclic set, the autolevel stamp from the shipped band — is digested, and the
    row is rendered only if that digest is the row's own key. A row whose stored
    recipe and the live checkout disagree would otherwise get *different* pixels
    under its own name, which is worse than having no picture. Those are counted
    and reported, never rendered.

    Nothing here writes to the ledger, its sidecars or their manifests. The
    pictures are the only thing that moves, which is what makes this safe to run
    beside anything except another leg driving the same three engines.
    """
    from concurrent.futures import ProcessPoolExecutor

    from fractal_wallpapers.curation import colorize, recipes
    from fractal_wallpapers.labeling import finished
    from fractal_wallpapers.palettes import groups as groups_module

    started = time.time()
    if keys is None:
        selector = "rows whose picture is not on disk"
        wanted = missing_pictures()
        log(f"[re-render] {len(wanted):,} row(s) name a picture that is not on disk")
    else:
        named = {str(key) for key in keys}
        selector = f"{len(named):,} named row(s), on disk or not"
        wanted = [row for row in store.stream() if str(row["key"]) in named]
        absent = named - {str(row["key"]) for row in wanted}
        log(
            f"[re-render] {len(wanted):,} of {len(named):,} named row(s) are in the store"
            + (f"; {len(absent):,} are not and cannot be rendered" if absent else "")
        )

    # ---- the guard, before any engine runs ---------------------------------- #
    cyclic = colorize.cyclic()
    band = colorize.band()
    table = groups_module.member_groups()
    # Once above the loop, for [`fractal_wallpapers.paths.rehome`]'s 246x.
    tiers = Tiers.current()
    jobs = []
    refused = []
    for row in wanted:
        stored = row["recipe"]
        mode, colormap = str(stored["mode"]), str(stored["colormap"])
        try:
            again = recipes.key_of(
                recipes.Recipe(
                    family=stored["family"],
                    viewport=stored["viewport"],
                    maxiter=int(stored["maxiter"]),
                    regime=recipes.CANDIDATE_REGIME,
                    mode=mode,
                    # The row's own, not `{}`. This guard rebuilds the members the
                    # render path *derives* — the palette off the cyclic set, the
                    # stamp off the shipped band — and there is nothing in the
                    # checkout to re-derive a leg's chosen settings from, so the
                    # row is the only source. Pinned empty, a varied row's rebuilt
                    # key never matched its own and every one of them was refused:
                    # protective by accident, and it would have gone on refusing
                    # them after the pictures were correct.
                    mode_params=dict(stored.get("mode_params") or {}),
                    curve=colorize.CURVE,
                    colormap=colormap,
                    palette=finished.recipe(mirror=colormap not in cyclic),
                    autolevel=recipes.live_stamp(mode, band),
                    palette_group=groups_module.group_of(colormap, table),
                )
            )
        except Exception as failure:  # noqa: BLE001
            refused.append({"key": str(row["key"]), "why": repr(failure)[:160]})
            continue
        if again != str(row["key"]):
            refused.append({"key": str(row["key"]), "the_render_path_would_make": again})
            continue
        where = rehome(str(row["picture"]), tiers)
        if where is None:
            refused.append({"key": str(row["key"]), "why": "the stored name is not under the tree"})
            continue
        jobs.append(
            {
                "key": str(row["key"]),
                "picture": str(where),
                "recipe": stored,
                "pair": (str((row.get("location") or {}).get("key")), mode),
            }
        )
    log(f"[re-render] {len(jobs):,} reproduce their own key; {len(refused):,} refused")
    # ---- one task per (location, mode) -------------------------------------- #
    fields = re_render_dir() / "fields"
    if share_fields:
        fields.mkdir(parents=True, exist_ok=True)
    grouped: dict = {}
    for job in jobs:
        grouped.setdefault(job["pair"], []).append(job)
    if limit is not None:
        # **Whole pairs.** A pilot that sliced the job list in row order would take
        # one picture from each of many pairs, and a dumped field pays for itself
        # only across the maps that follow it — so such a pilot pays every dump
        # and amortises none of them, and prices a leg that does not exist. The
        # first pilot did exactly that and read 2.23 s a picture at 1.03 pictures
        # a pair against the leg's real 1.78.
        held: dict = {}
        taken = 0
        for pair, rows_of in grouped.items():
            if taken >= int(limit):
                break
            held[pair] = rows_of
            taken += len(rows_of)
        grouped = held
        jobs = [job for rows_of in grouped.values() for job in rows_of]
        log(f"[re-render] limited to {len(jobs):,} over {len(grouped):,} whole pair(s)")
    payloads = [
        {"fields": str(fields) if share_fields else None, "rows": held} for held in grouped.values()
    ]
    log(
        f"[re-render] {len(payloads):,} (location, mode) pair(s) over {int(workers)} worker(s); "
        f"{len(jobs) / max(1, len(payloads)):.2f} picture(s) a pair"
    )

    made = 0
    failed = 0
    why: list = []
    engine_seconds = 0.0
    with ProcessPoolExecutor(max_workers=int(workers)) as pool:
        for done, out in enumerate(pool.map(render_pair, payloads), start=1):
            made += out["made"]
            failed += out["failed"]
            engine_seconds += out["seconds"]
            why += out["why"][: max(0, 20 - len(why))]
            if done % 250 == 0 or done == len(payloads):
                wall = time.time() - started
                rate = made / max(1e-9, wall)
                left = (len(jobs) - made) / max(1e-9, rate)
                log(
                    f"[re-render] {made:,} of {len(jobs):,} made in {wall / 60:.1f} min "
                    f"({rate:.1f}/s, ~{left / 60:.0f} min left), {failed:,} failed"
                )

    shutil.rmtree(fields, ignore_errors=True)
    wall = time.time() - started
    record = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "share_fields": bool(share_fields),
        # Which population ran, so a re-render over named keys is never read as a
        # sweep for absent files. `named_but_absent` keeps its name and counts the
        # population either way, which is what it always was.
        "selector": selector,
        "named_but_absent": len(wanted),
        "reproduce_their_own_key": len(jobs) if limit is None else None,
        "refused": refused[:20],
        "refused_count": len(refused),
        "asked": len(jobs),
        "made": made,
        "failed": failed,
        "why": why,
        "pairs": len(payloads),
        "workers": int(workers),
        "wall_seconds": round(wall, 1),
        "engine_seconds": round(engine_seconds, 1),
        "seconds_per_picture": round(engine_seconds / max(1, made), 4),
        "seconds_per_picture_is": "per ENGINE. Wall a picture is this over the concurrency",
        "concurrency": round(engine_seconds / max(1e-9, wall), 2),
    }
    path = re_render_dir() / "re_render.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    log(f"[re-render] {made:,} made, {failed:,} failed in {wall / 60:.1f} min")
    return record


#: How many pictures go through the judge between one checkpoint and the next.
#: A chunk is the finest safe interruption point a re-score has: the readings so
#: far are on disk, and a kill costs the chunk in flight and nothing else.
SCORE_CHUNK = 4096


#: The judge reads this many pictures at once. 7.4 ms a picture at 128 against
#: 8.3 at 64, over 512 of this store's own pictures on this machine's GPU,
#: 2026-08-31 — the pass is JPEG decode and not the forward, so the batch buys
#: little past here.
SCORE_BATCH = 128


def partial_scores_path() -> Path:
    """Where a re-score in flight keeps the chunks it has already read.

    Beside the sidecar and not inside it: a half-finished re-score is not a
    reading of the store, and a reader that joined on the live artifact would
    otherwise see a pool that grows while it is being read. [`rescore`] folds it
    in at the end and deletes it.
    """
    return store.store_root() / "scores.partial.jsonl"


def rescore(
    artifact: str | None = None,
    limit: int | None = None,
    batch: int = SCORE_BATCH,
    device: str = "auto",
    keys=None,
    log=print,
) -> dict:
    """Read every row whose picture is on disk through the judge shipped now.

    **`keys` reads the named rows even where the sidecar already holds a reading**,
    and it is the companion of [`re_render`]'s own `keys`: a row whose picture has
    just been *corrected* carries a reading of the picture it used to be, and the
    skip-what-is-held rule below would leave that reading standing forever. The
    upsert keys on `(recipe, artifact, regime)`, so a re-read replaces the stale
    number in place rather than adding a second one — which is right here and is why
    it is not the default: on an ordinary pass a held reading is a fact about the
    same picture and re-reading it would buy nothing.

    **The step a judge adoption makes necessary and nothing else does.** Scores
    are keyed on `(recipe, artifact, regime)` and
    [`scores_by_recipe`] joins on the live artifact alone, so the morning after a
    flip this store holds a full set of readings and the pool is *empty* — every
    row omitted as read on a head that no longer ships. Nothing is overwritten:
    the retired artifact's rows stay where they are, because a picture read by
    two judges is two facts.

    A row with no picture on disk is skipped rather than guessed at, the same
    rule [`curation.rescore`] holds over the release pool. There is one judge for
    both kinds since 2026-08-23, so the head is loaded once; `head` on the row
    still says which kind's floor and slot the row belongs to.

    **Resumable by chunk.** Each [`SCORE_CHUNK`] pictures are appended to
    [`partial_scores_path`] as they are read, and a re-run skips what that file
    already holds. The sidecar itself is written once, at the end, through the
    same upsert every other writer uses.

    **The skip set is keyed on the recipe alone and is therefore regime-blind.**
    `held` below holds `recipe_key` filtered by artifact and nothing else, while
    the reading this pass writes stamps the *recipe's* own regime. That is right
    for exactly as long as `recipe_key -> regime` is a function — the condition
    [`rows.scores_by_recipe`] states under *The regime half has no filter to fall
    back on, so it raises*. The day something scores a picture at a geometry that
    is not its recipe's, a recipe read only at that other geometry reads here as
    already done, and this pass leaves it unscored at the geometry the pool joins
    on — counted into `already_held` and logged as read, which is the shape of it
    that makes it quiet. Naming the regime here is part of the same fix as naming
    it at the unnamed read sites, not a separate one. Recorded 2026-09-06 and not
    fixed: there is one regime in the sidecar today, so nothing is wrong yet.
    """
    import time

    from fractal_wallpapers.curation import colorize, durability, hunt

    started = time.time()
    want = store.live_artifact() if artifact is None else str(artifact)
    stored = store.read()
    present = store.present_pictures(stored)
    held = {
        str(row["recipe_key"])
        for row in store.read_scores()
        if str(row.get("judge_artifact")) == want
    }
    done_partial = _partial_keys(want)
    if keys is None:
        wanted = [
            row
            for row in stored
            if str(row["key"]) in present
            and str(row["key"]) not in held
            and str(row["key"]) not in done_partial
        ]
        log(
            f"[rescore] {len(stored):,} row(s), {len(present):,} with a picture; "
            f"{len(held):,} already read on {want[:8]}, {len(done_partial):,} in the partial; "
            f"{len(wanted):,} to read"
        )
    else:
        # Named rows, held reading or not — see the docstring. The picture still has
        # to be there: a reading of a file that is not on disk is not a reading.
        named = {str(key) for key in keys}
        wanted = [row for row in stored if str(row["key"]) in named and str(row["key"]) in present]
        log(
            f"[rescore] {len(wanted):,} of {len(named):,} named row(s) have a picture and "
            f"will be re-read on {want[:8]}, {len(named & held):,} of them over a reading "
            f"the sidecar already holds"
        )
    if limit is not None:
        wanted = wanted[: int(limit)]
    if wanted:
        from fractal_wallpapers.models import scoring, train

        model, config, where = colorize.load_judge(device)
        transform = scoring.transform_of(config)
        classes = int(config["classes"])
        log(f"[rescore] judge on {where}, {classes} classes, batch {int(batch)}")
        # Once above the chunking, for [`fractal_wallpapers.paths.rehome`]'s 246x.
        tiers = Tiers.current()
        for at in range(0, len(wanted), SCORE_CHUNK):
            chunk = wanted[at : at + SCORE_CHUNK]
            paths = [rehome(str(row["picture"]), tiers) for row in chunk]
            probabilities = train.score(
                model, paths, transform, where, classes, {"batch_size": int(batch)}
            )
            _append_partial(
                [
                    rows_module.score_row(
                        key=str(row["key"]),
                        artifact=want,
                        regime=str((row["recipe"] or {})["regime"]),
                        head=hunt.kind_of(str((row["recipe"] or {})["mode"])),
                        read=_reading_of(probabilities[index]),
                        source={
                            "scores_current": True,
                            "run": (row.get("provenance") or {}).get("run"),
                            "candidate": (row.get("provenance") or {}).get("candidate"),
                        },
                    )
                    for index, row in enumerate(chunk)
                ]
            )
            read_so_far = at + len(chunk)
            wall = time.time() - started
            rate = read_so_far / max(1e-9, wall)
            left = (len(wanted) - read_so_far) / max(1e-9, rate)
            log(
                f"[rescore] {read_so_far:,} of {len(wanted):,} in {wall / 60:.1f} min "
                f"({rate:.0f}/s, ~{left / 60:.0f} min left)"
            )
    fresh = list(store._stream_of(partial_scores_path()))
    path, total, new = store.write_scores(fresh)
    saved = durability.save(store.durable_scores(), log=log)
    partial_scores_path().unlink(missing_ok=True)
    record = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifact": want,
        "rows": len(stored),
        "with_picture": len(present),
        "already_held": len(held),
        "read": len(fresh),
        "sidecar_rows": total,
        "sidecar_new": new,
        "wall_seconds": round(time.time() - started, 1),
        "saved": saved,
        "scores_path": tracked_name(path),
    }
    log(
        f"[rescore] {len(fresh):,} reading(s) on {want[:8]} merged; sidecar holds "
        f"{total:,} row(s) in {record['wall_seconds'] / 60:.1f} min"
    )
    return record


def _reading_of(probabilities) -> dict:
    """One judge output as [`score_row`] takes it: every cutpoint, and the sum.

    [`curation.colorize.score_picture`]'s body over an already-scored row rather
    than a second spelling of it — the rank score is the sum of the unconditional
    cutpoints and a second derivation of that is a second scale.
    """
    row = {f"p_ge{index + 2}": float(value) for index, value in enumerate(probabilities)}
    row["rank_score"] = float(sum(float(value) for value in probabilities))
    return row


def _partial_keys(artifact: str) -> set:
    """The recipes a partial re-score of THIS artifact has already read."""
    return {
        str(row["recipe_key"])
        for row in store._stream_of(partial_scores_path())
        if str(row.get("judge_artifact")) == str(artifact)
    }


def _append_partial(rows) -> None:
    """One chunk onto the partial file. Appended, so a kill costs one chunk."""
    path = partial_scores_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
