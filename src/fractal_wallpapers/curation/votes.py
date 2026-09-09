"""The voting kit: a recorded gallery as a folder somebody who is not here can rate.

Matt hands a thousand seats to friends. What travels is a zip -- two JPEGs per
seat, one HTML file and a paragraph of instructions -- and what comes back is one
small JSON file per person. Nothing in between needs a server, an account, or this
repository.

## The picture a friend sees is made here, never copied

A seat's stored candidate is 640x360, the size the judges read, and it is far too
small to vote on. So every seat in a kit is **rendered again** at [`FRAME`]
through [`curation.release`], exactly the way a shipped wallpaper is, and the
thumbnail is a downscale of *that*. Never of the candidate: the two are different
pictures at different sizes, and a grid of candidate thumbnails over a fullscreen
of fresh renders would be asking people to vote on one picture while showing them
another.

**A kit inherits the candidate's levelling curve and does not measure its own**,
since 2026-09-08 — [`_borrowed`], and [`curation.stamps`] for where the curve is
found. This module said the opposite until then, and the opposite is what made a
kit's picture levelled by a rule nobody judged: the tone of a 2560x1440 PNG is
not the tone of the 640x360 JPEG the seat was chosen on. `depth.levelling_of` is
therefore a question about **both** pictures now, and a seat whose candidate
curve was never recorded is the one case that still decides for itself.

## The full is lossless first and JPEG second

`colorize.render` writes PNG and the kit ships JPEG, so encoding is a second step
over the render's own bytes rather than something the renderer is told. That is
what lets a pilot price the quality grid against a reference that is not itself a
JPEG, and it is why [`encode`] is the one encoder both sides call. The PNG is
deleted as soon as its two JPEGs exist: a thousand of them is ten gigabytes and
the whole point of a kit is that it fits in a message.

**`subsampling` is passed on every encode and never left to Pillow.** Pillow picks
4:2:0 below quality 95 and 4:4:4 at or above it, silently, so a grid that named
only the quality would be comparing two chroma decisions it never made.

## The page is opened by double-clicking, and that rules out almost everything

`file://` refuses `fetch` of a sibling file, so the seat list is embedded in the
page as JSON. No server, no build step, no CDN: the only external references are
relative paths to JPEGs in the folder beside it. This is
[`curation.tentative.page`]'s constraint, met the same way.

## A filename carries the seat's position and nothing else

No rank, no key, no mode. A friend who can read a rank off a filename has been
told the answer, and a friend who can read the mode is being invited to vote on
the mode. The **export** carries the recipe key, which is the ID that survives
every later merge ([`curation.tentative`]'s first property), so an ingest written
months from now joins on something that still names the same picture.

**The supersample goes in the page's seat list for the same reason.** A kit may
render one mode finer than the rest ([`seat_supersample`]), so the seats are no
longer all the same picture-making, and a kit that did not record which seat got
which would be un-reproducible at the seat. It rides in the inlined list beside
the key rather than in the filename, where it would be a second thing a friend
can read off a tile and sort by.

## The order is per-viewer and it is a permutation, not a shuffle of a window

Seeded from the viewer's own name, so reopening the folder resumes the same walk
rather than re-randomising what they have already seen. There is no sort, no
filter and no search: this is the one place in the project where a person is asked
what they like, and every affordance for finding a particular picture is an
affordance for voting on something other than the picture in front of them.

**The per-page counts under the pager are the one exception, and they are about
the person rather than about the pictures.** A page nobody has opened and a page
somebody worked and liked nothing on are the same blank from the outside, and only
the first is worth going back to — so each page button carries how many votes that
viewer has given on it, zero drawn as `0`. It is a count over the *walk* and not
over the record: two people's page 3 hold different pictures. Nothing in it says
which picture, which mode, or which vote, so there is still nothing to sort by.

## Two people, one computer

A name is a slot: ratings are kept under `votes/<record>/<name>`, so a partner
taking a turn types their own name and gets their own walk and their own storage,
and the first person gets theirs back by typing theirs. **Handing the computer
over needs nothing destructive**, which is why the *Start over* button is not
that: it exists for leaving the computer clean, it erases every name's ratings
for this record, and it asks twice — an in-page band carrying the count of what
would go, then the browser's own dialog. Two steps of different kinds, because
two of the same kind is one habit.

It clears this record's keys and not the whole store: another kit's folder on the
same browser is somebody else's evening.

## What ingest will be handed, fixed here

`{viewer, record, name, order_seed, votes: {<recipe key>: 1 | 2}, pages_visited,
exported_at}` -- [`VIEWER`] names the shape. An export is the **complete** state
every time, so it is idempotent by name and the latest file per person wins. There
is no ingest in this module and there is not meant to be one yet: the schema is the
contract and the votes have to exist before anything reads them.
"""

from __future__ import annotations

import html
import json
import shutil
import time
import zipfile
from pathlib import Path

from fractal_wallpapers.curation import release, tentative

#: The shape of an exported label file. It travels on every export and an ingest
#: reads it before anything else, because the friends' copies of a kit outlive
#: this checkout's memory of what version wrote them.
#:
#: **`"2.0"` from 2026-09-05**, Matt's spelling, and it is deliberately not
#: `votes/v2`: the first version spelled itself `votes/v1` and an ingest telling
#: the two apart is telling `"votes/v1"` from `"2.0"`, which is a comparison no
#: parser can get subtly wrong. What changed under it is the viewer and not the
#: schema — a v1 export and a 2.0 export carry the same seven fields and the same
#: vote values, so the version says which page a person was looking at rather
#: than how to read what came back.
VIEWER = "2.0"

#: What every seat is rendered at. The frame and not a [`release.Regime`]: the
#: supersample under it is the caller's, priced by `scratch/votes_pilot`, and the
#: frame is not -- a wallpaper is voted on at the size it will be used at.
FRAME = (2560, 1440)

#: The supersample a kit builds at unless told another. **4**, and it is the
#: expensive default in this file: **76.2 s a picture** on the locked three
#: workers, measured over the forty-seat kit, so a thousand seats is **21.2 h**
#: against something near 5.4 at ss2.
#:
#: It is the default anyway because the supersample is the **only** decision here
#: a person can see. ss2 against ss4 is a mean absolute difference of **6.28**
#: over the six pilot seats and **4.81** after fitting to 1080p, where the whole
#: quality axis from q95 to q80 moves the busiest crop by 3.71 to 6.09 — so
#: dropping to ss2 to save fifteen hours costs more picture than dropping five
#: quality steps does, and it costs it as aliasing rather than as softness.
SUPERSAMPLE = 4

#: The supersamples either flag takes. **2 and 4 are the priced pair** — the whole
#: argument above is a comparison between those two, and they are the cells of the
#: pilot's grid somebody has looked at.
#:
#: **1 is the debugging cell and it is not one of them.** It buys a kit in minutes
#: rather than hours, which is what makes the friends' flow — paging, voting,
#: export — something a person can exercise end to end in an afternoon, and it
#: pays for that in exactly the currency the ss2-against-ss4 measurement says is
#: the visible one: aliasing. Nothing has priced its bytes or its picture and
#: nothing should ship from it. A kit at ss1 is for driving, not for sending.
SUPERSAMPLES = (1, 2, 4)

#: How wide a thumbnail is. 512 at 16:9 is 512x288 -- two of them across a phone,
#: five across the grid this page lays out, and small enough that a thousand of
#: them is a fraction of the fulls.
THUMB_WIDTH = 512

#: The JPEG quality a kit encodes at unless told another, and the chroma with it.
#: **85 at 4:2:0**, on the pilot's grid, and the reasoning is size rather than
#: fidelity: a thousand fulls at ss4 measures **1.13 GB** here against a projected
#: 1.31 at q90 and 1.82 at q95, and the busiest 1:1 crop at this cell is not
#: visibly apart from its own PNG. Chroma is the cheaper half of the same trade —
#: 4:2:0 is 24% smaller than 4:4:4 for 0.66 of mean absolute difference in the
#: busiest window, on pictures nobody will view at 1:1.
#:
#: **The zip is the constraint this record has not answered.** Every cell of the
#: grid puts a thousand seats between 0.88 and 2.88 GB, which is more than a
#: person sends a friend. Lowering the quality does not fix it; the frame or the
#: seat count would have to.
QUALITY = 85
CHROMA = "420"

#: What a chroma name means to Pillow. Two, because a wallpaper is either given
#: full colour resolution or the one every camera and every phone already uses,
#: and 4:2:2 is a third answer nobody asked for.
SUBSAMPLING = {"444": 0, "420": 2}

#: How many seats a page of the viewer holds. A thousand seats is ten pages, which
#: is a number a person can hold in their head while deciding whether to carry on.
PAGE = 100

#: The three names a kit's folder holds beside its two picture directories.
PAGE_NAME = "index.html"
READ_ME = "README.txt"
FULLS, THUMBS, STAGING = "full", "thumbs", "_png"


class VotesRefused(RuntimeError):
    """A voting kit cannot be built from what was named."""


# --------------------------------------------------------------------------- #
# Names and bytes.
# --------------------------------------------------------------------------- #
def seat_name(index: int) -> str:
    """A seat's filename stem: its **position** in the record, zero-padded.

    Four digits, which covers the thousand this exists for and the two thousand
    the next solve is reaching at. Nothing else is in the name on purpose -- see
    the module docstring.
    """
    return f"s{int(index):04d}"


def encode(image, path: Path, quality: int = QUALITY, chroma: str = CHROMA) -> int:
    """Write `image` as JPEG and return its byte count. **THE encoder.**

    The pilot's grid and the kit's own pictures come through here, so a cell Matt
    chose off a sheet is the cell a friend is looking at rather than something
    that resembles it.
    """
    if chroma not in SUBSAMPLING:
        raise VotesRefused(f"{chroma!r} is not a chroma; it is one of {sorted(SUBSAMPLING)}.")
    path.parent.mkdir(parents=True, exist_ok=True)
    writing = Path(str(path) + ".writing")
    image.convert("RGB").save(
        writing,
        format="JPEG",
        quality=int(quality),
        subsampling=SUBSAMPLING[chroma],
        optimize=True,
    )
    writing.replace(path)
    return path.stat().st_size


# --------------------------------------------------------------------------- #
# The seats, and the pictures under them.
# --------------------------------------------------------------------------- #
def parse_supersample_for(text: str) -> tuple[str, int]:
    """`"smooth_mean_angle=4"` as `(mode, 4)`. Refuses anything else.

    Refuses here rather than at the render, for [`ceiling.parse_target`]'s reason:
    a misspelt mode is an override that can never fire, and a leg that discovered
    it after twenty hours would have rendered the whole kit at the default and
    said nothing about it.
    """
    mode, _, spelled = str(text).partition("=")
    mode = mode.strip()
    if not _ or not mode:
        raise VotesRefused(f"--ss-for wants <mode>=<supersample>, not {text!r}")
    try:
        supersample = int(spelled)
    except ValueError:
        raise VotesRefused(
            f"{spelled!r} is not a supersample, so {text!r} is not an override."
        ) from None
    if supersample not in SUPERSAMPLES:
        raise VotesRefused(
            f"{supersample} is not one of the supersamples this kit is priced at, "
            f"{list(SUPERSAMPLES)}."
        )
    return mode, supersample


def seat_supersample(mode: str, supersample: int, overrides: dict | None) -> int:
    """What one seat renders at: its mode's override, or the kit's default.

    **Per mode and never per seat.** The supersample is the one decision in a kit
    a person can see, and the modes are what a person can say a sentence about —
    so an override is taken over a whole mode at a time, and a table with single
    seats in it would be a kit nobody could describe. Which modes are worth the
    finer render is a judgement off the pictures and is the caller's; nothing
    here has an opinion about it.

    An override naming a mode the record does not hold is **not** refused, and
    that is deliberate: a kit cut with `--limit` holds whatever modes the first N
    seats happen to carry, so a mode missing from one cut is the ordinary case
    rather than a mistake. The manifest counts the seats at each supersample
    beside the overrides it was asked for, which is where one that fired on
    nothing shows up.
    """
    return int((overrides or {}).get(str(mode), supersample))


def plan(
    stamp: str | None = None,
    limit: int | None = None,
    supersample: int = SUPERSAMPLE,
    supersample_for: dict | None = None,
) -> tuple[str, list[dict]]:
    """`(stamp, jobs)` -- the record's seats in seat order, cut to `limit`.

    A job carries the position, the key, the name, the mode and the supersample
    it will be rendered at, and it is what everything below joins on. The
    supersample is resolved **here** rather than at the render leg so that a job
    is complete from the moment it exists: the page inlines it, the manifest
    counts it and the legs group by it, and three readings of one table is three
    chances for them to disagree. The record's own row rides along under `row` for
    the manifest and for nothing the page ever sees.
    """
    stamp = tentative.latest() if stamp is None else str(stamp)
    rows = tentative.read_rows(stamp)
    if not rows:
        raise VotesRefused(f"{stamp} holds no seats to vote on.")
    if limit is not None:
        rows = rows[: max(0, int(limit))]
    jobs = []
    for index, row in enumerate(rows):
        # The record's own mode and not the ledger recipe's, because the
        # supersample has to be decided before any recipe is read: a kit groups
        # its render legs by mode and `recipes_for` is a lookup inside one of
        # them. The two agree — the record's row is written off the recipe — and
        # if they ever did not, the record is what a seat IS.
        mode = str(row.get("mode") or "")
        jobs.append(
            {
                "index": index,
                "key": str(row["key"]),
                "name": seat_name(index),
                "mode": mode,
                "ss": seat_supersample(mode, supersample, supersample_for),
                "row": row,
            }
        )
    return stamp, jobs


def rows_for(jobs: list[dict]) -> dict:
    """`{key: ledger row}` for the jobs that still need rendering.

    [`candidate_ledger.by_key`] and not a read: this wants a few hundred rows
    out of a store of hundreds of thousands, and reading the whole ledger for them
    would hold every other row in memory for the length of a render leg.

    **The whole row and not just its recipe**, since 2026-09-08. A kit needs two
    things off the ledger now — the recipe to render and the leg that made it, so
    [`_borrowed`] can find the levelling curve to inherit — and asking twice is a
    second stream of a 458 MB store for rows already in hand.
    """
    from fractal_wallpapers.curation import candidate_ledger

    wanted = [job["key"] for job in jobs]
    rows = candidate_ledger.by_key(wanted)
    missing = set(wanted) - set(rows)
    if missing:
        raise VotesRefused(
            f"{len(missing)} seat(s) name a recipe the ledger does not hold -- "
            f"{sorted(missing)[:3]}. A seat cannot be rendered without its recipe."
        )
    return rows


def recipes_for(jobs: list[dict]) -> dict:
    """`{key: recipe}` — [`rows_for`] with everything but the recipe dropped."""
    return {key: row["recipe"] for key, row in rows_for(jobs).items()}


def _borrowed(rows: dict, log=print) -> dict:
    """`{key: borrowed}` — the levelling each seat in a kit inherits.

    A kit is a release at another size, so it inherits for the same reason a
    release does. This module's own docstring said the opposite until 2026-09-08
    — "nothing in a kit replays a curve" — and that sentence is what made
    `depth.levelling_of` a question about the candidate and never about the kit's
    picture. It is a question about both now, and a seat the store has no curve
    for is simply absent from this.
    """
    from fractal_wallpapers.curation import backfill, recipes
    from fractal_wallpapers.curation import stamps as stamps_module

    out = stamps_module.for_release(
        rows, backfill.read(), regime=recipes.CANDIDATE_REGIME.spelled, store="sequence"
    )
    log(f"[votes] {len(out)}/{len(rows)} seat(s) inherit a levelling curve")
    return out


def render_fulls(jobs, staging: Path, regime, workers: int, arrived, log=print) -> dict:
    """Render each job's full-size PNG into `staging`, `arrived(job, png)` per row.

    **Module level and replaceable**, which is what lets the fast lane drive the
    whole of [`build`] -- the encode, the downscale, the page, the zip -- without
    an engine. Everything downstream of a picture is exercised either way, because
    `arrived` is called on this side of the seam rather than beyond it.

    `arrived` runs in the parent, once per job, in plan order: it is
    [`release.run_pass`]'s sink, and the reason a kit encodes and deletes as it
    goes instead of at the end is that a thousand of these PNGs is ten gigabytes.
    """
    staging.mkdir(parents=True, exist_ok=True)
    rows = rows_for(jobs)
    recipes = {key: row["recipe"] for key, row in rows.items()}
    by_key = {job["key"]: job for job in jobs}
    borrowed = _borrowed(rows, log)
    tasks, standing = [], []
    for job in jobs:
        recipe = recipes[job["key"]]
        picture = staging / f"{job['key']}.png"
        if picture.is_file():
            standing.append(job)
            continue
        tasks.append(
            release.task_for(
                id=job["key"],
                row=recipe,
                mode=recipe["mode"],
                colormap=recipe["colormap"],
                mode_params=recipe.get("mode_params"),
                curve=recipe.get("curve"),
                palette=recipe.get("palette"),
                autolevel=borrowed.get(job["key"]),
                output=picture,
                geometry={**regime.geometry(), "maxiter": int(recipe["maxiter"])},
            )
        )
    for job in standing:
        arrived(job, staging / f"{job['key']}.png")
    failed = []

    def sink(task, result):
        if result.ok:
            arrived(by_key[task.id], Path(result.info["picture"]))
        else:
            failed.append({"key": task.id, "error": result.error})
            log(f"[votes] {task.id} failed at {regime.spelled}: {result.error}")

    started = time.monotonic()
    record = release.run_pass(tasks, workers, sink, log)
    seconds = time.monotonic() - started
    made = len(tasks) - len(failed)
    return {
        "regime": regime.spelled,
        "workers": int(workers),
        "planned": len(tasks),
        "standing": len(standing),
        "made": made,
        "failed": failed,
        "leg_seconds": round(seconds, 1),
        "seconds_per_picture": round(seconds / max(1, made), 1),
        "pass_record": record,
    }


def cut(png: Path, job: dict, fulls: Path, thumbs: Path, quality: int, chroma: str) -> dict:
    """One render into the two JPEGs a kit ships, and the PNG gone after.

    The thumbnail is a `LANCZOS` reduction of the **full render** and there is no
    path here that reads the candidate: that is the claim the fast lane checks by
    building a kit whose candidates do not exist on disk at all.

    The `<stem>.leveled/` directory goes with the PNG. `colorize.render` writes one
    beside every acted render -- the operator's overriding colormap, ~76 KiB --
    and it is spelled here the way the writer spells it, because a staging tree
    that kept a thousand of those would be most of what a deleted PNG saved.
    """
    from PIL import Image

    with Image.open(png) as opened:
        opened.load()
        full_bytes = encode(opened, fulls / f"{job['name']}.jpg", quality, chroma)
        height = max(1, round(opened.height * THUMB_WIDTH / opened.width))
        small = opened.resize((THUMB_WIDTH, height), Image.LANCZOS)
    thumb_bytes = encode(small, thumbs / f"{job['name']}.jpg", quality, chroma)
    png.unlink(missing_ok=True)
    shutil.rmtree(png.parent / f"{png.stem}.leveled", ignore_errors=True)
    return {"full_bytes": full_bytes, "thumb_bytes": thumb_bytes}


# --------------------------------------------------------------------------- #
# The folder a friend opens.
# --------------------------------------------------------------------------- #
def page(directory: Path, stamp: str, jobs: list[dict]) -> Path:
    """Write `index.html`. Self-contained, and openable over `file://`.

    The inlined seat list is `{"key": ..., "ss": ...}` per seat, in seat order.
    The key is the join every export is written against; the supersample is what
    that seat's two JPEGs were actually made at, and the page never reads it —
    it is there so a kit can say what it is at the seat rather than only in
    aggregate. **The mode is not in it**: a page carrying the mode is a page a
    friend can group by, which is the module docstring's whole objection to
    putting anything but the position in a filename.
    """
    path = directory / PAGE_NAME
    seats = [{"key": job["key"], "ss": int(job.get("ss", SUPERSAMPLE))} for job in jobs]
    writing = Path(str(path) + ".writing")
    writing.write_text(
        _PAGE.replace("__RECORD__", html.escape(str(stamp)))
        .replace("__VIEWER__", html.escape(VIEWER))
        .replace("__PAGE__", str(int(PAGE)))
        .replace("__SEATS__", json.dumps(seats, ensure_ascii=False)),
        encoding="utf-8",
        newline="\n",
    )
    writing.replace(path)
    return path


def read_me(directory: Path) -> Path:
    """The paragraph the friends read. One, and no jargon in it."""
    path = directory / READ_ME
    path.write_text(_READ_ME, encoding="utf-8", newline="\n")
    return path


def archive(directory: Path, log=print) -> Path:
    """Zip the kit beside itself, deflated, with nothing from the staging tree.

    Named off the folder rather than through `with_suffix`, which would eat
    everything after a dot in a folder somebody called `kit.v2`.

    **The JPEGs are stored and only the text is deflated.** Deflate on an already
    compressed picture is minutes of CPU for a fraction of a percent, and a kit is
    a gigabyte of pictures beside twenty kilobytes of page.
    """
    path = directory.parent / f"{directory.name}.zip"
    writing = Path(str(path) + ".writing")
    with zipfile.ZipFile(writing, "w") as bundle:
        for item in sorted(directory.rglob("*")):
            if item.is_dir() or STAGING in item.relative_to(directory).parts:
                continue
            bundle.write(
                item,
                Path(directory.name, item.relative_to(directory)).as_posix(),
                compress_type=(
                    zipfile.ZIP_STORED
                    if item.suffix.lower() in {".jpg", ".jpeg", ".png"}
                    else zipfile.ZIP_DEFLATED
                ),
            )
    writing.replace(path)
    log(f"[votes] {path} — {path.stat().st_size / 1e6:.1f} MB")
    return path


def build(
    stamp: str | None = None,
    out: Path | str | None = None,
    limit: int | None = None,
    quality: int = QUALITY,
    chroma: str = CHROMA,
    supersample: int = SUPERSAMPLE,
    supersample_for: dict | None = None,
    workers: int | None = None,
    log=print,
) -> dict:
    """The whole kit: render, encode, thumbnail, page, paragraph, zip.

    Resumable at the seat: a seat whose two JPEGs are already there is not
    rendered again, so a killed leg picks up where it stopped and a kit rebuilt at
    another quality has to be built somewhere else -- which is the honest
    behaviour, because the quality is not in the filename either. **A kit rebuilt
    at another supersample is the same case**, and the resume cannot tell the two
    apart: the JPEG on disk does not say what made it, so a kit at new
    supersamples goes in a new directory or the standing seats stay as they were.

    `supersample_for` is `{mode: supersample}`, and it makes the leg **one render
    pass per distinct supersample** rather than one pass overall. They run
    cheapest first so the fulls a person can look at start landing early, each is
    the locked three workers in turn and never two pools at once, and every seat
    is encoded and its PNG deleted as it arrives regardless of which pass made it.
    """
    if out is None:
        raise VotesRefused("a kit is built into a directory; name one with --out.")
    if chroma not in SUBSAMPLING:
        raise VotesRefused(f"{chroma!r} is not a chroma; it is one of {sorted(SUBSAMPLING)}.")
    directory = Path(out)
    workers = release.DEFAULT_WORKERS if workers is None else int(workers)
    overrides = {str(mode): int(value) for mode, value in (supersample_for or {}).items()}
    regime = release.Regime(FRAME, int(supersample))
    stamp, jobs = plan(stamp, limit, int(supersample), overrides)
    fulls, thumbs = directory / FULLS, directory / THUMBS
    for where in (fulls, thumbs, directory / STAGING):
        where.mkdir(parents=True, exist_ok=True)

    def done(job: dict) -> bool:
        return (fulls / f"{job['name']}.jpg").is_file() and (
            thumbs / f"{job['name']}.jpg"
        ).is_file()

    standing = [job for job in jobs if done(job)]
    wanted = [job for job in jobs if not done(job)]
    sizes: list[dict] = []

    def arrived(job, png):
        sizes.append({"name": job["name"], **cut(png, job, fulls, thumbs, quality, chroma)})

    seats_at = {
        value: len([job for job in jobs if job["ss"] == value])
        for value in sorted({job["ss"] for job in jobs})
    }
    log(
        f"[votes] {stamp}: {len(jobs)} seat(s), "
        f"{', '.join(f'{count} at ss{value}' for value, count in seats_at.items())}, "
        f"{len(standing)} already encoded, {len(wanted)} to render on {workers} worker(s)"
    )
    legs = []
    for value in sorted({job["ss"] for job in wanted}):
        held = [job for job in wanted if job["ss"] == value]
        one = release.Regime(FRAME, value)
        log(f"[votes] rendering {len(held)} seat(s) at {one.spelled}")
        legs.append(render_fulls(held, directory / STAGING, one, workers, arrived, log))
    rendered = {
        "regime": regime.spelled,
        "planned": sum(int(leg.get("planned", 0)) for leg in legs),
        "made": sum(int(leg.get("made", 0)) for leg in legs),
        "failed": [row for leg in legs for row in leg.get("failed", ())],
        # One entry per supersample the leg actually rendered at, cheapest first.
        # The aggregate above is what the resume reads and the legs are what a
        # budget is taken off, so both are here rather than one derived twice.
        "legs": legs,
    }
    written = page(directory, stamp, jobs)
    read_me(directory)
    staging = directory / STAGING
    if staging.is_dir() and not any(staging.iterdir()):
        staging.rmdir()
    bundle = archive(directory, log)
    full_bytes = [row["full_bytes"] for row in sizes]
    manifest = {
        "schema": 1,
        "viewer": VIEWER,
        "record": stamp,
        "seats": len(jobs),
        "encoding": {
            "quality": int(quality),
            "chroma": chroma,
            # `regime` is what a seat gets unasked; `regime_for` is the modes told
            # otherwise; `seats_at` is what the record's own modes turned that
            # into. An override naming a mode this cut does not hold is legal, and
            # this is where it shows: `regime_for` names a supersample that
            # `seats_at` has no entry for.
            "regime": regime.spelled,
            "regime_for": {
                mode: release.Regime(FRAME, value).spelled
                for mode, value in sorted(overrides.items())
            },
            "seats_at": {f"ss{value}": count for value, count in seats_at.items()},
        },
        "where": str(directory),
        "page": str(written),
        "zip": str(bundle),
        "zip_bytes": bundle.stat().st_size,
        "render": rendered,
        "full_bytes": {
            "mean": round(sum(full_bytes) / len(full_bytes)) if full_bytes else None,
            "max": max(full_bytes) if full_bytes else None,
        },
    }
    log(
        f"[votes] {len(jobs)} seat(s) at q{quality} {chroma}, "
        f"{manifest['zip_bytes'] / 1e6:.1f} MB zipped"
    )
    return manifest


#: What the friends read before they open anything. One paragraph, and every
#: sentence in it is something they have to do -- there is no explanation of what
#: a fractal is, what a seat is, or what happens to the file afterwards, because
#: none of that changes what they should click.
_READ_ME = """Thanks for helping pick wallpapers.

Unzip this folder somewhere and open index.html — it opens in your browser and
needs nothing installed. Type your name when it asks. You'll see pages of
pictures. If you like one, click the thumbs-up under it; if you really like one,
click the star instead. Skip everything else — most of them should be skipped,
and there's no number you're trying to reach. Click a picture to see it large —
the same three choices are buttons underneath it, Average, thumbs-up and star —
and press Escape to come back. Your choices are saved as you go, so you can close
the page and come back to it later.

The keyboard does the same three things to whichever picture you're pointing at,
or to the large one if you have one open: 2 for the thumbs-up, 3 for the star,
and 1 for an average one. Any of the three closes the large picture, so you can
go straight on to the next.

When you're done, click Export at the top. Your browser will save a small file.
Send that file back and you're finished.

If somebody else wants a turn on the same computer, they can just type their own
name — everyone's choices are kept separately, so you won't be in each other's
way. "Start over" at the top is the other thing: it erases every rating on the
computer, yours and theirs, and it asks you twice before it does. Export first.
"""


#: The viewer, as one string with four substitutions: `__SEATS__`, `__RECORD__`,
#: `__VIEWER__` and `__PAGE__`, all filled by [`page`]. Kept here
#: rather than in a tracked asset file for [`tentative`]'s reason -- a second file
#: is a second thing to find -- and it is the second and last page this project
#: writes for a person to drive.
_PAGE = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>pick the wallpapers you like</title>
<style>
  /* The two vote colours, named once and read everywhere a vote is shown: the
     tile border, the button that cast it, the count strip. A person learns the
     pair on the first page and every later screen has to keep the promise. */
  :root { color-scheme: dark; --up: #fbbf24; --star: #16a34a; --ink: #101216; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #101216; color: #e8eaed;
         font: 14px/1.5 ui-sans-serif, system-ui, "Segoe UI", sans-serif; }
  header { position: sticky; top: 0; z-index: 3; background: #181b21;
           border-bottom: 1px solid #2a2f38; padding: 9px 14px;
           display: flex; gap: 14px; align-items: center; flex-wrap: wrap; }
  header .who { font-weight: 600; }
  header .grow { flex: 1; }
  .tally { font-variant-numeric: tabular-nums; color: #c6cbd3; }
  .tally .up { color: var(--up); }
  .tally .star { color: var(--star); }
  .pager { display: flex; gap: 5px; flex-wrap: wrap; }
  .pager button { display: flex; flex-direction: column; align-items: center;
                  gap: 1px; line-height: 1.15; min-width: 36px; padding: 4px 9px; }
  /* Small type, and the only thing it has to do is answer "have I worked this
     page" across the strip at a glance. So the distinction is brightness and
     weight rather than a third colour: the two colours above already mean the
     two votes, and a worked page is not a third kind of vote. */
  .pager .count { font-size: 10px; font-variant-numeric: tabular-nums;
                  color: #666e7c; }
  .pager .count.worked { color: #e8eaed; font-weight: 700; }
  button { background: #262b34; color: #e8eaed; border: 1px solid #39404b;
           border-radius: 5px; padding: 5px 10px; font: inherit; cursor: pointer; }
  button:hover { background: #333a45; }
  button.on { background: #3d5cc4; border-color: #6f8ae8; }
  /* The confirm band, and it is a band rather than a browser dialog on purpose:
     the count of what is about to go has to be on screen next to the button that
     takes it. The second step IS a browser dialog, so the two acts are different
     in kind and muscle memory cannot carry through both. */
  #confirm { background: #3b1416; border-bottom: 1px solid #7f1d1d;
             padding: 9px 14px; display: flex; gap: 10px; align-items: center;
             flex-wrap: wrap; color: #fecaca; }
  #confirm b { color: #fff1f2; }
  button.danger { background: #b91c1c; border-color: #ef4444; color: #fff5f5; }
  button.danger:hover { background: #dc2626; }
  main { display: grid; gap: 12px; padding: 14px 14px 70px;
         grid-template-columns: repeat(5, minmax(0, 1fr)); }
  @media (max-width: 1100px) { main { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
  @media (max-width: 680px) { main { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  .tile { border: 3px solid transparent; border-radius: 8px; overflow: hidden;
          background: #181b21; }
  .tile.up { border-color: var(--up); }
  .tile.star { border-color: var(--star); }
  .tile img { display: block; width: 100%; aspect-ratio: 16 / 9; object-fit: cover;
              background: #0b0d10; cursor: zoom-in; }
  .bar { display: flex; gap: 6px; padding: 6px; }
  .bar button { flex: 1; padding: 4px 0; font-size: 15px; line-height: 1.2; }
  /* `data-v="0"` is the neutral, and it keeps the strip's own blue: it is the
     button that says nothing about the picture, so giving it a vote colour
     would be the one lie this bar can tell. */
  .bar button.on { background: #3d5cc4; border-color: #6f8ae8; }
  .bar button.on[data-v="1"] { background: var(--up); border-color: #fcd34d;
                               color: var(--ink); }
  .bar button.on[data-v="2"] { background: var(--star); border-color: #22c55e;
                               color: #f2fdf5; }
  #big { position: fixed; inset: 0; z-index: 5; background: #06070a;
         display: flex; flex-direction: column; align-items: center;
         justify-content: center; gap: 10px; }
  #big img { max-width: 100vw; max-height: calc(100vh - 62px); object-fit: contain; }
  #big .bar { width: min(560px, 94vw); }
  #gate { position: fixed; inset: 0; z-index: 9; background: #101216;
          display: grid; place-items: center; padding: 20px; }
  #gate div { max-width: 460px; }
  #gate h1 { font-size: 19px; margin: 0 0 10px; }
  #gate p { color: #aeb5bf; }
  #gate input { background: #0b0d10; color: #e8eaed; border: 1px solid #39404b;
                border-radius: 5px; padding: 8px 10px; font: inherit; width: 220px; }
  [hidden] { display: none !important; }
</style>
<header hidden id="strip">
  <span class="who" id="who"></span>
  <span class="tally"><span class="up" id="tallyup"></span>
    <span class="star" id="tallystar"></span></span>
  <span class="grow"></span>
  <span class="pager" id="pager"></span>
  <button id="reset">Start over</button>
  <button id="export">Export</button>
</header>
<div id="confirm" hidden>
  <b>Erase every rating on this computer?</b>
  <span id="confirmwhat"></span>
  <span class="grow"></span>
  <button id="erase" class="danger">Erase everything</button>
  <button id="keep">Cancel</button>
</div>
<main id="grid" hidden></main>
<div id="big" hidden>
  <img id="bigimg" alt="">
  <div class="bar">
    <button data-v="0">Average <small>(1)</small></button>
    <button data-v="1">&#128077; Thumbs up <small>(2)</small></button>
    <button data-v="2">&#9733; Star <small>(3)</small></button>
  </div>
</div>
<div id="gate">
  <div>
    <h1>Pick the wallpapers you like</h1>
    <p>Type your name, then rate the ones you like with the thumbs-up, and the
       ones you really like with the star. Skip everything else.</p>
    <p>Keys: <b>2</b> thumbs-up, <b>3</b> star, <b>1</b> average — on whichever
       picture you are pointing at. Any of the three closes a large picture.</p>
    <p>Click a picture to see it large; the same three are buttons under it.</p>
    <p><input id="name" placeholder="your name" autofocus>
       <button id="start">Start</button></p>
  </div>
</div>
<script>
// One entry per seat, in the record's own seat order: the recipe key an export
// joins on, and the supersample that seat's pictures were rendered at. Nothing
// on the page reads `ss` — it is here so a kit says what it is at the seat, and
// the mode that decided it is deliberately not here.
const SEATS = __SEATS__;
const KEYS = SEATS.map((seat) => seat.key);
const RECORD = "__RECORD__";
const VIEWER = "__VIEWER__";
const PER_PAGE = __PAGE__;
const PAGES = Math.max(1, Math.ceil(KEYS.length / PER_PAGE));
// Every person's ratings live under SLOTS + their name, and the remembered name
// lives beside that prefix rather than inside it. A COLON and not a slash, and
// that is a fix rather than a style: `slot()` joins with "/", so the old
// `.../name` key was one a person actually called "name" would have overwritten
// with their votes object. Nothing can type a colon into this position.
const SLOTS = "votes/" + RECORD + "/";
const NAME_KEY = "votes/" + RECORD + ":name";

let who = "";
let votes = {};
let visited = [];
let order = [];
let seed = 0;
let page = 0;
let hovered = null;
let open = null;
let scrolled = 0;

function pad(index) { return "s" + String(index).padStart(4, "0"); }

// FNV-1a over the name, so the same person gets the same walk every time they
// open the folder — a fresh shuffle on reopening would re-show what they had
// already decided about.
function seedOf(text) {
  let hash = 2166136261;
  for (let i = 0; i < text.length; i++) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function permutation(count, source) {
  const out = Array.from({length: count}, (_, i) => i);
  for (let i = count - 1; i > 0; i--) {
    const j = Math.floor(source() * (i + 1));
    const swap = out[i]; out[i] = out[j]; out[j] = swap;
  }
  return out;
}

function slot() { return SLOTS + who; }

function save() {
  try {
    localStorage.setItem(slot(), JSON.stringify({votes: votes, pages: visited}));
  } catch (e) { /* a private window keeps nothing; the page still works */ }
}

function load() {
  try {
    const held = JSON.parse(localStorage.getItem(slot()) || "{}");
    votes = held.votes || {};
    visited = held.pages || [];
  } catch (e) { votes = {}; visited = []; }
}

function tally() {
  let up = 0, star = 0;
  for (const key in votes) { if (votes[key] === 2) star++; else if (votes[key] === 1) up++; }
  document.getElementById("tallyup").textContent = "\\u{1F44D} " + up;
  document.getElementById("tallystar").textContent = "\\u2605 " + star;
}

// Votes given on each page of THIS viewer's own walk, thumbs-up and stars
// together. Over the order and not over the record, because the pages are the
// permutation's pages: two people's page 3 hold different pictures, and a count
// read off the record would be a number about somebody else's screen.
//
// Recomputed whole on every vote. A thousand seats is a thousand lookups, which
// is nothing beside the repaint it happens next to, and the alternative — an
// incremental count kept beside the votes — is a second copy of the truth that
// can drift from `votes` in exactly the case nobody would notice: a page turned
// under a fullscreen.
function pageCounts() {
  const counts = new Array(PAGES).fill(0);
  for (let p = 0; p < PAGES; p++) {
    for (const index of order.slice(p * PER_PAGE, (p + 1) * PER_PAGE)) {
      if (votes[KEYS[index]]) counts[p]++;
    }
  }
  return counts;
}

// The kind a key means. 1 clears, 2 is the thumbs-up, 3 is the star — and the
// VOTE values are still 1 and 2, which is what the export carries and what an
// ingest joins on. The two numberings are apart on purpose: adding a key that
// means "no" could not be done by shifting the votes without invalidating every
// label file already exported against this record.
//
// A Map and not an object literal, because the test is `does this key bind` and
// an object answers yes for `constructor` and every other name on the prototype.
const BY_KEY = new Map([["1", 0], ["2", 1], ["3", 2]]);

// A key SETS and a GRID button TOGGLES, and that difference is the reason there
// is a third key at all: a grid button somebody has already pressed has to
// un-press, having no neutral of its own, but a key that toggled would make 2
// mean "like" on one picture and "un-like" on the next, which is the one thing a
// person rating a thousand pictures fast must not have to keep track of. The
// fullscreen bar sets like the keys, because from 2.0 it has the third button.
// `kind` 0 is neutral.
function setVote(index, kind) {
  const key = KEYS[index];
  if (kind) votes[key] = kind; else delete votes[key];
  save();
  tally();
  paintTile(index);
  paintPager();
  // The fullscreen bar is not repainted here: every vote taken while it is up
  // closes it, and `enlarge` paints it on the way in. There is no state in which
  // an open bar is out of date.
}

function vote(index, kind) {
  setVote(index, votes[KEYS[index]] === kind ? 0 : kind);
}

function paintTile(index) {
  const tile = document.querySelector('[data-i="' + index + '"]');
  if (!tile) return;
  const kind = votes[KEYS[index]];
  tile.classList.toggle("up", kind === 1);
  tile.classList.toggle("star", kind === 2);
  for (const button of tile.querySelectorAll(".bar button")) {
    button.classList.toggle("on", Number(button.dataset.v) === kind);
  }
}

function drawPage(next) {
  page = Math.max(0, Math.min(PAGES - 1, next));
  if (!visited.includes(page)) { visited.push(page); save(); }
  const grid = document.getElementById("grid");
  grid.textContent = "";
  for (const index of order.slice(page * PER_PAGE, (page + 1) * PER_PAGE)) {
    const tile = document.createElement("figure");
    tile.className = "tile";
    tile.dataset.i = index;
    tile.style.margin = "0";
    const image = document.createElement("img");
    image.src = "thumbs/" + pad(index) + ".jpg";
    image.loading = "lazy";
    image.alt = "";
    image.addEventListener("click", () => enlarge(index));
    const bar = document.createElement("div");
    bar.className = "bar";
    for (const [kind, face] of [[1, "\\u{1F44D}"], [2, "\\u2605"]]) {
      const button = document.createElement("button");
      button.dataset.v = kind;
      button.textContent = face;
      button.addEventListener("click", () => vote(index, kind));
      bar.appendChild(button);
    }
    tile.appendChild(image);
    tile.appendChild(bar);
    tile.addEventListener("mouseenter", () => { hovered = index; });
    tile.addEventListener("mouseleave", () => { if (hovered === index) hovered = null; });
    grid.appendChild(tile);
    paintTile(index);
  }
  drawPager();
  window.scrollTo(0, 0);
}

function drawPager() {
  const pager = document.getElementById("pager");
  pager.textContent = "";
  for (let p = 0; p < PAGES; p++) {
    const button = document.createElement("button");
    button.dataset.p = p;
    if (p === page) button.className = "on";
    const number = document.createElement("span");
    number.textContent = String(p + 1);
    const count = document.createElement("span");
    count.className = "count";
    button.appendChild(number);
    button.appendChild(count);
    button.addEventListener("click", () => drawPage(p));
    pager.appendChild(button);
  }
  paintPager();
}

// Zero is drawn as `0` rather than left blank, and that is the whole point of
// the strip: a page nobody has voted on and a page somebody worked and liked
// nothing on look the same from the outside, and only the first is worth going
// back to. Blank would mean "unknown" and there is nothing unknown here.
function paintPager() {
  const counts = pageCounts();
  for (const button of document.getElementById("pager").querySelectorAll("button")) {
    const count = button.querySelector(".count");
    const given = counts[Number(button.dataset.p)] || 0;
    count.textContent = String(given);
    count.classList.toggle("worked", given > 0);
  }
}

// The three buttons are a radio group and Average is a state rather than an
// absence, so an unrated picture lights Average — `votes` holds no entry for one,
// which is why the read is `|| 0` and not the raw value the tiles compare on.
function paintBig(index) {
  const kind = votes[KEYS[index]] || 0;
  for (const button of document.querySelectorAll("#big .bar button")) {
    button.classList.toggle("on", Number(button.dataset.v) === kind);
  }
}

function enlarge(index) {
  if (open === null) scrolled = window.scrollY;
  open = index;
  document.getElementById("bigimg").src = "full/" + pad(index) + ".jpg";
  document.getElementById("big").hidden = false;
  paintBig(index);
}

function shut() {
  open = null;
  document.getElementById("big").hidden = true;
  window.scrollTo(0, scrolled);
}

function step(by) {
  const at = order.indexOf(open);
  const next = at + by;
  if (at < 0 || next < 0 || next >= order.length) return;
  const wanted = Math.floor(next / PER_PAGE);
  // Stepping off the end of a page turns the page under the fullscreen. The
  // scroll position to come back to is that page's top, not the offset held
  // from the page they opened the picture on.
  if (wanted !== page) { drawPage(wanted); scrolled = 0; }
  enlarge(order[next]);
}

// The fullscreen bar SETS, exactly as the keys do, and it is the one place a
// button does not toggle. From 2.0 there is an Average button to un-rate with,
// so a toggle would be a second way to reach the same state and a worse one: it
// would make "Thumbs up" mean *un-like* on a picture already liked, which is the
// ambiguity the three keys were introduced to remove. The grid tiles still
// toggle, because they have no third button.
function press(index, kind) {
  setVote(index, kind);
  // **All three close, and Average is not an exception**, Matt's ruling of
  // 2026-09-05 after driving 2.0. The earlier reading was that clearing undoes a
  // decision rather than taking one, so it should leave the picture up; in the
  // hand it is a decision like the others — Average IS the verdict "this one is
  // ordinary" — and a key that sometimes closed and sometimes did not was the
  // thing that had to be tracked. One rule: press any of the three and the
  // fullscreen gives way to the next picture.
  if (open === index) shut();
}

document.getElementById("start").addEventListener("click", begin);
document.getElementById("name").addEventListener("keydown", (event) => {
  if (event.key === "Enter") begin();
});

function begin() {
  const typed = document.getElementById("name").value.trim();
  if (!typed) return;
  who = typed;
  try { localStorage.setItem(NAME_KEY, who); } catch (e) { /* nothing kept */ }
  start();
}

function start() {
  seed = seedOf(who);
  order = permutation(KEYS.length, mulberry32(seed));
  load();
  document.getElementById("gate").hidden = true;
  document.getElementById("strip").hidden = false;
  document.getElementById("grid").hidden = false;
  document.getElementById("who").textContent = who;
  tally();
  // The furthest page they reached, not the first: reopening the folder is
  // carrying on, and starting them again at page one is asking them to scroll
  // past everything they have already decided about.
  drawPage(visited.length ? Math.max(...visited) : 0);
}

for (const button of document.querySelectorAll("#big .bar button")) {
  button.addEventListener("click", () => {
    if (open !== null) press(open, Number(button.dataset.v));
  });
}

// --------------------------------------------------------------------------- //
// Handing the computer over.
// --------------------------------------------------------------------------- //
// What this browser is holding for this record, across every name that has used
// it. Read at the moment of asking rather than kept, because the whole question
// is what would be lost RIGHT NOW.
function heldOnThisComputer() {
  let names = 0, ratings = 0;
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (!key || !key.startsWith(SLOTS)) continue;
      names++;
      const held = JSON.parse(localStorage.getItem(key) || "{}");
      ratings += Object.keys(held.votes || {}).length;
    }
  } catch (e) { /* a private window keeps nothing, so there is nothing to lose */ }
  return {names: names, ratings: ratings};
}

// **Somebody else's turn does not need this button.** A different name is a
// different slot and a different walk already, so handing the laptop to a partner
// is: Start over, then they type their name. What the button is FOR is leaving the
// computer clean — and because that is destructive and the handover is not, the
// count of what goes is put on screen before anything is touched.
function askReset() {
  const held = heldOnThisComputer();
  document.getElementById("confirmwhat").textContent =
    held.ratings + " rating" + (held.ratings === 1 ? "" : "s") +
    " from " + held.names + " name" + (held.names === 1 ? "" : "s") +
    " on this computer. Anything not exported cannot be got back.";
  document.getElementById("confirm").hidden = false;
  window.scrollTo(0, 0);
}

function doReset() {
  // The browser's own dialog is the SECOND step deliberately: the first was a
  // button in the page, so a person cannot arrive here by clicking twice in the
  // same place.
  if (!window.confirm("Erase every rating on this computer? This cannot be undone.")) return;
  try {
    const drop = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      // The record's prefix and not the whole store: another kit's folder is
      // somebody else's evening and this page has no business clearing it.
      if (key && key.startsWith("votes/" + RECORD)) drop.push(key);
    }
    for (const key of drop) localStorage.removeItem(key);
  } catch (e) { /* nothing was kept, so nothing needs removing */ }
  who = "";
  votes = {};
  visited = [];
  order = [];
  seed = 0;
  page = 0;
  open = null;
  hovered = null;
  scrolled = 0;
  document.getElementById("confirm").hidden = true;
  document.getElementById("big").hidden = true;
  document.getElementById("strip").hidden = true;
  document.getElementById("grid").hidden = true;
  document.getElementById("grid").textContent = "";
  document.getElementById("gate").hidden = false;
  const typed = document.getElementById("name");
  typed.value = "";
  typed.focus();
}

document.getElementById("reset").addEventListener("click", askReset);
document.getElementById("keep").addEventListener("click", () => {
  document.getElementById("confirm").hidden = true;
});
document.getElementById("erase").addEventListener("click", doReset);

document.addEventListener("keydown", (event) => {
  if (document.getElementById("gate").hidden === false) return;
  if (event.key === "Escape" && open !== null) { shut(); return; }
  if (open !== null && event.key === "ArrowRight") { step(1); return; }
  if (open !== null && event.key === "ArrowLeft") { step(-1); return; }
  if (!BY_KEY.has(event.key)) return;
  const target = open !== null ? open : hovered;
  if (target !== null) press(target, BY_KEY.get(event.key));
});

document.getElementById("export").addEventListener("click", () => {
  const payload = {
    viewer: VIEWER,
    record: RECORD,
    name: who,
    order_seed: seed,
    votes: votes,
    pages_visited: visited.slice().sort((a, b) => a - b),
    exported_at: new Date().toISOString(),
  };
  const blob = new Blob([JSON.stringify(payload, null, 1)], {type: "application/json"});
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = who.replace(/[^A-Za-z0-9_-]+/g, "_") + "_labels.json";
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 5000);
});

const remembered = (function () {
  try { return localStorage.getItem(NAME_KEY); } catch (e) { return null; }
})();
if (remembered) { who = remembered; start(); }
</script>
"""

__all__ = [
    "CHROMA",
    "FRAME",
    "PAGE",
    "QUALITY",
    "SUPERSAMPLE",
    "SUPERSAMPLES",
    "THUMB_WIDTH",
    "VIEWER",
    "VotesRefused",
    "archive",
    "build",
    "cut",
    "encode",
    "page",
    "parse_supersample_for",
    "plan",
    "read_me",
    "recipes_for",
    "rows_for",
    "render_fulls",
    "seat_name",
    "seat_supersample",
]
