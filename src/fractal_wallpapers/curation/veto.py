"""A human `1` at the fine level takes the picture out of the gallery, for good.

Every other refusal in this project is a reading of a number. A bar moves, a head
is adopted, a floor is re-fitted, and the rows they refused come back. This one
does not: a person looked at a finished picture, said *this is bad*, and that
answer is not a statistic anybody will re-derive. Matt's ruling of 2026-09-14.

## It is ROW-LEVEL, and that is the whole of its reach

The veto names **one candidate, by its recipe key**. It does not veto the place,
the pair, the mode or the map. A neighbouring palette at the same location is a
different picture with its own verdict, and it is seated or refused on its own
merits — which is exactly what [`labeling.gallery_grade`] exists to say, since
the store's whole estimand is *how good is this picture given that it cleared the
gate* and two rows of one place can be a 1 and a 4.

It is also **not a bar**. [`solve.DEFAULT_FINE_BAR`] refuses a row on what the
fine head predicts; this refuses a row on what a person said about that exact
picture, and the two are unrelated. A row can clear every bar there is and still
be vetoed.

## Only a HUMAN label vetoes, and the veto is a CONSUMER of labels

A model score of 1, a low `p_fine`, or anything a judge produced is not a veto
and must never be treated as one. [`render_keys`] reads `origin == store.HUMAN`
and nothing else.

There is **no veto ledger**. A vetoed row is an ordinary gallery-grade row: it
went into the store on the normal path, it trains the fine head exactly as any
other human label does, and nothing here writes anything anywhere. The veto is
derived from the store every time it is asked, which is what makes it
**retroactive** — labels already in the store counted from the moment this
landed, and a label cast tomorrow counts tomorrow with nothing to re-run.

**Latest-wins is the store's rule and it is the veto's too.** The set comes off
[`gallery_grade.resolved`], so a picture graded 1 and later re-graded 3 is not
vetoed: the store's current answer is the veto's current answer. That is a
property worth stating because the alternative — any 1 ever cast — would make the
veto the one thing in this project a person cannot take back.

## Where it acts, and why there is one place

[`solve.pool`] is the single door into a seating: every leg that seats anything
builds its candidates there, and `curate solve run`, `curate solve record`, the
mining legs and `curate headroom` all reach it. So the veto is applied in that
loop, beside the rejection the ledger already carries, and a vetoed row never
becomes a [`solve.Candidate`] at all. It is out of the pool, out of the seating
and out of every future solve by construction rather than by each caller
remembering.

## The join is the render key, and it costs a `Decimal`

A label row and a ledger row are two spellings of one picture, and
[`retention.render_key_of`] is the adapter between them — the same function
[`models.gallery_grade_train.population`] joins the corpus to the pool with, so
the veto reaches exactly the rows a fit reaches and not a sibling of them.

⚠ **It is not free and the number is worth knowing.** Measured 2026-09-14 over
the live store's 417,585 ledger rows: the read alone is 0.72 s, `json.loads` over
it takes it to 5.86 s, and deriving the render key on every row takes it to
**16.42 s** — so the veto adds about **10.6 s, or 25 µs a row**, to a pool build.
Nearly all of it is [`supply.location.location_key`], which normalizes three
coordinates through `Decimal`. A `(mode, colormap)` prefilter projected off the
veto set would be sound — both are components of the render key — and was
measured to pass 42.7% of rows, saving about 6 s; it is **not** here, because the
saving shrinks as the veto grows and one identity with no second spelling is
worth more than six seconds of a leg that runs for hours.

## What it does not touch

Nothing renders less, nothing is deleted, and no picture is swept. A vetoed row
keeps its ledger row, its picture, its scores and its place in every record
already taken — `curation/README.md`'s *Record everything; filter nothing* is
unchanged, and the veto is a reading over the store rather than an edit to it. In
particular the **records already on disk are not rewritten**: a stamp seated
before a label was cast still holds that seat, which is what makes the readout
here — *how many of this record's seats would go* — a question worth asking.
"""

from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path

from fractal_wallpapers.curation import page as page_module
from fractal_wallpapers.paths import Tiers, rehome, under

#: The schema every record this module writes carries.
SCHEMA = 1

#: The subtree this readout's pages and records land in.
UNIT = "veto"

#: The ordinal a human casts to veto a picture. One value, and it is
#: [`gallery_grade.SCALE`]'s lowest — *genuinely surprised this cleared the bar, a
#: clear reject*. Named here rather than written as a bare `1` at each site, so a
#: reader of any of them can see it is the store's own scale being read.
VETO_GRADE = 1

#: How wide a thumbnail is drawn on the page. [`curation.sheet`]'s, so two pages
#: of this project's pictures are the same size on screen.
THUMBNAIL_WIDTH = 320


class VetoRefused(RuntimeError):
    """A veto that cannot be read, or a readout that cannot be taken."""


def root() -> Path:
    return under("curation", UNIT)


# --------------------------------------------------------------------------- #
# The veto itself.
# --------------------------------------------------------------------------- #
def render_keys(rows=None) -> dict:
    """`{render key: the label row that vetoes it}` — every human `1` standing now.

    Off [`gallery_grade.resolved`] and never off the raw rows: latest-wins is the
    store's rule about what it currently says, and a picture re-graded upward is
    not vetoed any more. `rows` takes a store read a caller already has.

    An empty answer is normal and means nothing has been vetoed yet.
    """
    from fractal_wallpapers.labeling import gallery_grade, store

    resolution = gallery_grade.resolved() if rows is None else gallery_grade.resolve(list(rows))
    out: dict = {}
    for row in resolution.graded():
        if row.get("grade") != VETO_GRADE or row.get("origin") != store.HUMAN:
            continue
        key = gallery_grade.render_key(row)
        if key is not None:
            out[key] = row
    return out


def refuses(row: dict, veto) -> bool:
    """Whether the veto takes this **ledger** row out.

    The one test, and every site asks it through here. `veto` is
    [`render_keys`]'s mapping or any set of its keys; an empty one refuses
    nothing and costs nothing, which is what a synthetic pool in a test gets.
    """
    if not veto:
        return False
    from fractal_wallpapers.curation import retention

    key = retention.render_key_of(row)
    return key is not None and key in veto


def resolve(veto=None, rows=None, log=print) -> dict:
    """`{ledger key: render key}` — which rows of the ledger the veto names.

    One streaming pass, for [`models.gallery_grade_train.population`]'s reason:
    the ledger is the largest store here and parsing it whole costs many times
    its own size for the four fields a join needs.

    Several ledger rows can in principle answer to one render key — the key is
    the recipe and never the regime — so the mapping is many-to-one and the count
    of keys is not the count of vetoed *pictures*. Over the store as it stands it
    is one apiece; the reader is [`reach`], which reports both numbers.
    """
    from fractal_wallpapers.curation import candidate_ledger, retention

    veto = render_keys() if veto is None else veto
    if not veto:
        return {}
    stored = candidate_ledger.stream() if rows is None else rows
    out: dict = {}
    scanned = 0
    for row in stored:
        scanned += 1
        key = retention.render_key_of(row)
        if key is not None and key in veto:
            out[str(row.get("key"))] = key
    log(f"[veto] {scanned:,} ledger rows scanned; {len(out):,} carry one of {len(veto):,} vetoes")
    return out


def reach(veto=None, rows=None, log=print) -> dict:
    """What the veto covers store-wide: render keys, ledger keys, and the gap.

    The gap is the thing to read. A vetoed render key with **no** ledger row at
    all is a picture a person judged that the pool has since stopped holding —
    which is not an error and not a leak, because a row that is not in the ledger
    is not in the pool either.
    """
    veto = render_keys() if veto is None else veto
    found = resolve(veto, rows=rows, log=log)
    reached = set(found.values())
    return {
        "schema": SCHEMA,
        "render_keys": len(veto),
        "ledger_keys": len(found),
        "render_keys_with_no_ledger_row": len(veto) - len(reached),
        "ledger_keys_per_render_key": (
            None if not reached else round(len(found) / len(reached), 4)
        ),
        "is": (
            "every picture a person has graded 1 at the fine level, and the ledger rows "
            "those pictures are. A render key with no ledger row is a picture the pool no "
            "longer holds, which is not a leak: a row that is not in the ledger is not in "
            "the pool either"
        ),
    }


# --------------------------------------------------------------------------- #
# What the veto takes out of one recorded gallery.
# --------------------------------------------------------------------------- #
def seats(stamp: str, veto=None, rows=None, log=print) -> dict:
    """Which seats of one recorded gallery carry a human `1`, and what they are.

    The record is read for its seats, and the ledger for the recipe behind each —
    the map especially, which a recorded row does not carry and which a person
    looking for a pattern in their own rejections will want first.

    Only the record's own keys are asked for the render key, so this is a cheap
    pass: a thousand derivations rather than four hundred thousand.
    """
    from fractal_wallpapers.curation import candidate_ledger, retention, tentative

    veto = render_keys() if veto is None else veto
    seated = {str(row["key"]): row for row in tentative.read_rows(str(stamp))}
    if not seated:
        raise VetoRefused(f"{stamp} holds no seats to read")
    stored = candidate_ledger.stream() if rows is None else rows
    joined: dict = {}
    for row in stored:
        key = str(row.get("key"))
        if key not in seated:
            continue
        joined[key] = row
        if len(joined) == len(seated):
            break
    missing = sorted(set(seated) - set(joined))
    taken = []
    for key, row in sorted(joined.items()):
        render = retention.render_key_of(row)
        if render is None or render not in veto:
            continue
        label = veto[render]
        recipe = row.get("recipe") or {}
        seat = seated[key]
        taken.append(
            {
                "key": key,
                "alias": seat.get("alias"),
                "seat": seat.get("seat"),
                "mode": seat.get("mode"),
                "partition": seat.get("partition"),
                "cell": seat.get("cell"),
                "hue_family": seat.get("hue_family"),
                "cells": list(seat.get("cells") or ()),
                "families": list(seat.get("families") or ()),
                "colormap": recipe.get("colormap"),
                "curve": recipe.get("curve"),
                "seated_for": seat.get("seated_for"),
                "floor": seat.get("floor"),
                "p_ge4": seat.get("p_ge4"),
                "rank": seat.get("rank"),
                "location": seat.get("location"),
                "picture": seat.get("picture") or row.get("picture"),
                "graded_at": label.get("recorded_at"),
                "graded_in": label.get("batch"),
                "labeler": label.get("labeler"),
            }
        )
    taken.sort(key=lambda row: row["seat"] if row["seat"] is not None else -1)
    log(f"[veto] {len(taken)} of {len(seated):,} seats in {stamp} carry a human 1")
    return {
        "schema": SCHEMA,
        "stamp": str(stamp),
        "seats": len(seated),
        "vetoed": len(taken),
        "seats_with_no_ledger_row": len(missing),
        "rows": taken,
        "by_mode": _counted(row["mode"] for row in taken),
        "by_partition": _counted(row["partition"] for row in taken),
        "by_cell": _counted(row["cell"] for row in taken),
        "by_hue_family": _counted(row["hue_family"] for row in taken),
        "by_colormap": _counted(row["colormap"] for row in taken),
        "is": (
            "the seats of this record a human fine-level 1 takes out. The record itself is "
            "NOT rewritten — a stamp seated before a label was cast still holds that seat, "
            "and this is what a re-solve would drop"
        ),
    }


def _counted(values) -> dict:
    """`{value: how many}`, biggest first and then alphabetical."""
    counts = Counter(str(value) for value in values)
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


# --------------------------------------------------------------------------- #
# The concentration readout, which is the same record read for a different worry.
# --------------------------------------------------------------------------- #
def palette_concentration(stamp: str, rows=None, top: int = 10, log=print) -> dict:
    """How many maps hold one record's seats, and what the top of them holds.

    A direct check on whether the collection is converging toward one palette.
    The colormap is on the ledger row and not on the recorded seat, so this takes
    the same join [`seats`] does.
    """
    from fractal_wallpapers.curation import candidate_ledger, tentative

    seated = {str(row["key"]) for row in tentative.read_rows(str(stamp))}
    if not seated:
        raise VetoRefused(f"{stamp} holds no seats to read")
    stored = candidate_ledger.stream() if rows is None else rows
    maps: Counter = Counter()
    found = 0
    for row in stored:
        if str(row.get("key")) not in seated:
            continue
        found += 1
        maps[str((row.get("recipe") or {}).get("colormap"))] += 1
        if found == len(seated):
            break
    ordered = maps.most_common()
    total = sum(maps.values()) or 1
    log(
        f"[veto] {len(maps):,} distinct map(s) hold {total:,} seat(s); the top one holds "
        f"{ordered[0][1]} ({100 * ordered[0][1] / total:.1f}%)"
    )
    return {
        "schema": SCHEMA,
        "stamp": str(stamp),
        "seats": len(seated),
        "seats_joined": found,
        "distinct_colormaps": len(maps),
        "top_share": round(ordered[0][1] / total, 6),
        "top_map": ordered[0][0],
        "top_n": int(top),
        "top_n_share": round(sum(count for _map, count in ordered[:top]) / total, 6),
        "top_maps": [{"colormap": name, "seats": count} for name, count in ordered[:top]],
    }


# --------------------------------------------------------------------------- #
# The rejection plan: a whole recorded gallery, cut for one pass of marking 1s.
# --------------------------------------------------------------------------- #
#: What a rejection plan and its record are called under whatever directory a
#: caller gives. [`curation.pool_draw`]'s two names, because a plan is a plan and
#: `label build --from-plan` reads them both the same way.
PLAN_NAME = "plan.jsonl"
RECORD_NAME = "rejection.json"

#: What a rejection pass's **draw** directory is called, under the gallery-grade
#: store's own plans tree. The leading half of `<draw>/<batch>/plan.jsonl`, which
#: is the shape [`labeling.gallery_grade.plan_paths`] globs for.
#:
#: ⚠ **The plan belongs in that tree and nowhere else**, and it is not a tidiness
#: preference. A stored gallery-grade row carries `leveled` as a *boolean* and
#: never the `<stem>.leveled/` directory, so the plan a sheet was cut from is the
#: only thing on this machine that can say which colormap a picture was judged
#: through — `labeling/README.md`'s *Keep the plan*. A plan written outside the
#: tree is one that accessor cannot see, and the first ingest of the batch it
#: belongs to makes `tests/test_gallery_grade_retention.py` fail with the plan
#: sitting perfectly intact somewhere else.
PLAN_DRAW_PREFIX = "veto_"


def plan_home(stamp: str, batch: str) -> Path:
    """Where a rejection plan lands: `<plans>/veto_<stamp>/<batch>/`.

    [`labeling.gallery_grade.plans_dir`] and not a path spelled here, because that
    store owns where its own records live and a second spelling is one the glob
    that finds them would eventually disagree with.
    """
    from fractal_wallpapers.labeling import gallery_grade

    return gallery_grade.plans_dir() / f"{PLAN_DRAW_PREFIX}{stamp}" / str(batch)


def plan(stamp: str, rows=None, fine=None, log=print) -> tuple[list[dict], dict]:
    """`(units, the record)` — one gallery-grade unit per seat of a recorded gallery.

    **The population is the whole record and nothing is sampled**, which is what a
    rejection pass is: a person looks at every seat once and marks the bad ones.
    The seats already carrying a verdict are kept too, and that is deliberate —
    the store is latest-wins, so a seat re-marked is a verdict updated and a seat
    left alone keeps the one it has. A plan that dropped the graded seats would
    make a second pass unable to change its own mind.

    Each unit is the ledger row's recipe whole, so the sheet re-serves the picture
    the solve actually seated rather than a rebuild of it, and carries the fine
    head's decode as [`labeling.sheets`]' `suggestion` plus the expected grade it
    orders on. A seat the head has no reading for carries neither and sorts after
    every seat it could read — `solve.at_fine_bar`'s rule for the same column.
    """
    from fractal_wallpapers.curation import candidate_ledger, pool_draw, tentative
    from fractal_wallpapers.models import gallery_grade_train

    seated = {str(row["key"]): row for row in tentative.read_rows(str(stamp))}
    if not seated:
        raise VetoRefused(f"{stamp} holds no seats to cut a sheet over")
    fine = gallery_grade_train.read_pool_scores() if fine is None else fine
    run = gallery_grade_train.pool_scores_run()
    stored = candidate_ledger.stream() if rows is None else rows
    found: dict = {}
    for row in stored:
        key = str(row.get("key"))
        if key in seated:
            found[key] = row
            if len(found) == len(seated):
                break
    missing = sorted(set(seated) - set(found))
    if missing:
        raise VetoRefused(
            f"{len(missing)} of {stamp}'s seats are not in the ledger, e.g. {missing[:3]}. The "
            f"record was chosen out of the ledger, so this is a store that moved under it."
        )
    tiers = Tiers.current()
    units: list[dict] = []
    read = 0
    for key, seat in sorted(seated.items(), key=lambda item: item[1].get("seat") or 0):
        row = found[key]
        recipe = row.get("recipe") or {}
        missing_fields = [
            name
            for name in ("family", "viewport", "maxiter", "mode", "curve", "colormap", "palette")
            if recipe.get(name) is None
        ]
        if missing_fields:
            raise VetoRefused(
                f"ledger row {key!r} names no {', '.join(missing_fields)}; its picture cannot be "
                f"rebuilt and a verdict cast on it would be about nothing"
            )
        reading = fine.get(key) or {}
        suggestion, expected = _decoded(reading)
        read += int(suggestion is not None)
        units.append(
            {
                "family": recipe["family"],
                "viewport": recipe["viewport"],
                "maxiter": int(recipe["maxiter"]),
                "mode": recipe["mode"],
                "mode_params": dict(recipe.get("mode_params") or {}),
                "curve": recipe["curve"],
                "colormap": recipe["colormap"],
                "recipe": recipe["palette"],
                "leveled": pool_draw.leveled_dir(row.get("picture"), tiers),
                # Every unit here took a seat, so `seated` is true and `refusal`
                # null on all of them by construction rather than by a lookup.
                "seated": True,
                "refusal": None,
                "pre_stamp": False,
                "suggestion": suggestion,
                "suggestion_score": expected,
                "selected_on": {
                    "block": str(stamp),
                    "candidate": key,
                    "regime": recipe.get("regime"),
                    "p_ge4": seat.get("p_ge4"),
                    "p_fine": reading.get("p_ge4"),
                    "fine_rank": reading.get("rank_score"),
                    "fine_head": run,
                    "rank": seat.get("rank"),
                    "seat": seat.get("seat"),
                    "seated_for": seat.get("seated_for"),
                },
            }
        )
    log(f"[veto] {len(units):,} seat(s) cut; {read:,} carry the fine head's decode")
    record = {
        "schema": SCHEMA,
        "stamp": str(stamp),
        "units": len(units),
        "with_a_decode": read,
        "fine_head": run,
        "suggestions": _counted(
            unit["suggestion"] for unit in units if unit["suggestion"] is not None
        ),
        "is": (
            "a REJECTION plan over every seat of one recorded gallery. The population is the "
            "whole record and nothing is sampled: a rejection pass looks at every seat once "
            "and marks only the bad ones, and a seat left unmarked writes nothing"
        ),
    }
    return units, record


def _decoded(reading: dict) -> tuple[int | None, float | None]:
    """`(the suggested ordinal, the expected grade)` off one fine-head reading.

    The ordinal is **the highest tier the column puts at or above even odds**,
    which is how `gallery_top_20260910`'s sheet read the same column and is the
    only decode of a CORN head that does not need a threshold nobody fitted. The
    expected grade is the head's own `rank_score` — `1 + p(≥2) + p(≥3) + p(≥4)` —
    and it is what the page orders on, because two rows that both decode to 4 are
    still ordered by how confidently.

    `(None, None)` where the head has not read the row, and that is not a zero:
    the fine head is defined over rows clearing the render bar and has no output
    anywhere else.
    """
    cutpoints = [reading.get("p_ge2"), reading.get("p_ge3"), reading.get("p_ge4")]
    if any(value is None for value in cutpoints):
        return None, None
    ordinal = 1 + sum(1 for value in cutpoints if float(value) >= 0.5)
    expected = reading.get("rank_score")
    return ordinal, None if expected is None else float(expected)


def write_plan(directory: Path, units: list[dict], record: dict) -> tuple[Path, Path]:
    """Write the plan and its record. Returns both paths."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    where = directory / PLAN_NAME
    with where.open("w", encoding="utf-8", newline="\n") as handle:
        for unit in units:
            handle.write(json.dumps(unit, ensure_ascii=False) + "\n")
    document = directory / RECORD_NAME
    document.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return where, document


# --------------------------------------------------------------------------- #
# The page.
# --------------------------------------------------------------------------- #
PAGE_STYLE = """
 .wrap { padding: 18px 20px 40px; max-width: 1500px; }
 .lede { color: var(--muted); max-width: 64rem; margin: 0 0 1.2rem; }
 .lede b { color: var(--ink); }
 .grid { display: grid; gap: 14px; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); }
 figure { margin: 0; background: var(--panel); border-radius: 6px; overflow: hidden;
          border: 1px solid var(--rule); }
 img { display: block; width: 100%; background: var(--well); }
 .gone { padding: 3rem 1rem; text-align: center; color: var(--faint); }
 figcaption { display: flex; flex-direction: column; gap: .12rem; padding: .5rem .6rem .65rem; }
 .seat { color: var(--accent); font-weight: 600; }
 .fact { color: var(--muted); }
 .fact b { color: var(--ink); font-weight: 600; }
 .key { font-family: ui-monospace, monospace; color: var(--faint); font-size: .72rem; }
 .tally { display: flex; flex-wrap: wrap; gap: 6px 18px; margin: 0 0 1.2rem; padding: 0;
          list-style: none; color: var(--muted); }
 .tally li { background: var(--raised); border-radius: 4px; padding: .2rem .5rem; }
 .tally b { color: var(--ink); }
 h2 { color: var(--muted); font-weight: 600; }
"""


def page(readout: dict, output: Path, log=print) -> Path:
    """Write the page of vetoed seats. Pictures are the ledger's stored candidates.

    Nothing is re-rendered and nothing here is a label instrument: the captions
    are open, which is the property that keeps it from being mistaken for one. It
    is the ordinary instrument shell every other page in this package uses, at the
    geometry the pictures already exist at.
    """
    from fractal_wallpapers.curation import sheet

    rows = readout.get("rows") or []
    if not rows:
        raise VetoRefused(
            f"no seat in {readout.get('stamp')} carries a human 1, so there is nothing to "
            "show. That is a reading and not a failure — report it rather than building a page"
        )
    tiers = Tiers.current()
    cards = []
    for row in rows:
        where = rehome(str(row.get("picture") or ""), tiers)
        source = "" if where is None else sheet.thumbnail(where, THUMBNAIL_WIDTH)
        facts = [
            f"<b>{html.escape(str(row['mode']))}</b> &middot; {html.escape(str(row['partition']))}",
            f"map <b>{html.escape(str(row['colormap']))}</b>",
            f"cell <b>{html.escape(str(row['cell']))}</b> &middot; family "
            f"<b>{html.escape(str(row['hue_family']))}</b>",
            f"judge P(&ge;4) {_number(row.get('p_ge4'))} &middot; rank {_number(row.get('rank'))}",
            f"seated for {html.escape(str(row.get('seated_for')))}"
            + (f" &middot; floor {html.escape(str(row['floor']))}" if row.get("floor") else ""),
            f"graded 1 in {html.escape(str(row.get('graded_in')))} on "
            f"{html.escape(str(row.get('graded_at') or '')[:10])}",
        ]
        cards.append(
            "<figure>"
            + (
                f'<img loading="lazy" src="{source}">'
                if source
                else '<div class="gone">no picture on this tier</div>'
            )
            + f'<figcaption><span class="seat">seat {row["seat"]} &middot; '
            + f"{html.escape(str(row['alias']))}</span>"
            + "".join(f'<span class="fact">{fact}</span>' for fact in facts)
            + f'<span class="key">{html.escape(str(row["key"]))}</span>'
            + "</figcaption></figure>"
        )
    lede = (
        f"<b>{readout['vetoed']}</b> of the <b>{readout['seats']:,}</b> seats in "
        f"<b>{html.escape(readout['stamp'])}</b> carry an explicit human <b>1</b> at the fine "
        "level &mdash; the pictures the veto takes out of this gallery. The record itself is "
        "not rewritten; this is what a re-solve drops. Pictures are the ledger's stored "
        "640&times;360 candidates, nothing was re-rendered, and this page ingests nowhere."
    )
    body = (
        '<div class="wrap"><h1>Vetoed seats &mdash; '
        + html.escape(readout["stamp"])
        + f'</h1><p class="lede">{lede}</p>'
        + _tally("by mode", readout.get("by_mode"))
        + _tally("by family", readout.get("by_partition"))
        + _tally("by colour cell", readout.get("by_cell"))
        + _tally("by hue family", readout.get("by_hue_family"))
        + _tally("by map", readout.get("by_colormap"))
        + '<div class="grid">'
        + "".join(cards)
        + "</div></div>"
    )
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        page_module.shell(f"Vetoed seats — {readout['stamp']}", body, style=PAGE_STYLE),
        encoding="utf-8",
        newline="\n",
    )
    log(f"[veto] wrote {output}")
    return output


def _tally(what: str, counts: dict | None) -> str:
    if not counts:
        return ""
    items = "".join(
        f"<li>{html.escape(name)} <b>{count}</b></li>" for name, count in counts.items()
    )
    return f"<h2>{html.escape(what)}</h2><ul class='tally'>{items}</ul>"


def _number(value) -> str:
    return "&mdash;" if value is None else f"{float(value):.4f}"


def write_record(readout: dict, output: Path) -> Path:
    """One readout beside its page, so a number on it can be quoted without it."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(readout, indent=2) + "\n", encoding="utf-8", newline="\n")
    return output


__all__ = [
    "PAGE_STYLE",
    "PLAN_DRAW_PREFIX",
    "PLAN_NAME",
    "RECORD_NAME",
    "SCHEMA",
    "THUMBNAIL_WIDTH",
    "UNIT",
    "VETO_GRADE",
    "VetoRefused",
    "page",
    "plan",
    "plan_home",
    "write_plan",
    "palette_concentration",
    "reach",
    "refuses",
    "render_keys",
    "resolve",
    "root",
    "seats",
    "write_record",
]
