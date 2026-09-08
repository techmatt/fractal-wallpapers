"""The release sheet: what shipped, beside what it shipped instead of.

Distribution review is a person's job by design — no head in this project is
asked whether a *release* is a good release, only whether a picture is a good
picture — so the run's last act is to lay its decisions out where they can be
looked at. Contact-style: every released wallpaper at thumbnail size with its
whole provenance under it, then the near misses, then the rows the caps removed.

**One file, and it carries its own pictures.** The sheet is copied out of the
repository to be read, so a page that pointed at files in an ignored tree would
arrive empty. The thumbnails are embedded, which makes the sheet a few hundred
kilobytes and self-contained — and keeps it out of the tracked tree, where a
binary would not be allowed anyway.

**The provenance is the point, not the decoration.** Under each picture is what a
reader has to have in order to disagree with the run: the location, the mode and
the map, which judge scored it and what it said, which kind of slot it took, and
what the autolevel operator did — including *nothing*, which is the common case
and the one a sheet that only showed acting rows would hide.

**Both cutpoints, because the top one is where a release is judged.** The first
production run's released smooth rows had a median `P(≥3)` of 0.9999: at the top
of the distribution that column is saturated and cannot order anything, which is
precisely the end a reviewer is looking at. `P(≥4)` is a different question — *is
this worth releasing* rather than *is this a wallpaper* — and it is the
unconditional probability, the running product of the head's conditional
cutpoints, never a raw cutpoint sigmoid read as one. A judge whose scale has no
fourth class says so on the line instead of showing a blank.

**A caption never states a cause it did not observe.** This page used to describe
a missing stamp as "palette-indifferent, or the switch was off" — a disjunction
nothing on the row had checked, and on the run where four rows lost their
operator pass to a deadline it was simply false about all four. The kind is on
the row, so the palette-indifferent case is *read*; everything else says that
there is no stamp and stops.

**The released grid is the SERVED set, and a row a review took back is on the
page under its own heading.** Removing it outright would make this sheet
disagree with the records it is drawn from, which is the one thing a review
sheet may not do; leaving it in the released grid would keep serving a picture
somebody rejected. [`from_records`] draws both sections off the accumulated
record rather than off a run's own memory, so the page a run writes and the page
a rejection redraws are the same function over the same rows.
"""

from __future__ import annotations

import base64
import html
import io
from collections.abc import Iterable
from pathlib import Path

#: The long edge of an embedded thumbnail. Big enough to tell two wallpapers
#: apart at a glance, small enough that a dozen of them are one page.
THUMBNAIL_WIDTH = 480

#: What the thumbnails are embedded as. A release picture is a PNG; a page full
#: of PNG thumbnails is several megabytes and says nothing more.
THUMBNAIL_QUALITY = 82


def thumbnail(picture: Path, width: int = THUMBNAIL_WIDTH) -> str:
    """One picture as an embeddable data URI, or an empty string if it is missing."""
    from PIL import Image

    if not Path(picture).is_file():
        return ""
    with Image.open(picture) as opened:
        image = opened.convert("RGB")
        height = max(1, round(image.height * width / image.width))
        image = image.resize((width, height), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=THUMBNAIL_QUALITY)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def autolevel_line(stamp: dict | None, what: str = "", kind: str | None = None) -> str:
    """What the operator did, prefixed by *which render* it did it to.

    A released row has two stamps and they are different renders — the candidate
    the verdict was cast on, and the full-resolution picture on this page. Showing
    one and captioning the other is how a sheet says something false while every
    field on it is true.
    """
    return f"{what}{_did(stamp, kind)}" if what else _did(stamp, kind)


def _did(stamp: dict | None, kind: str | None = None) -> str:
    if stamp is None:
        from fractal_wallpapers.coloring import autolevel

        if kind and not autolevel.applies_to(kind):
            return f"autolevel: not run — a {kind} coloring is palette-indifferent"
        # No claim about WHY. The switch may have been off, the render may have
        # been killed before its operator pass, or the stamp may never have been
        # written — nothing on this row distinguishes them, and the run that
        # guessed described four killed rows as a decision nobody made.
        return "autolevel: no stamp on this render — the row does not say why"
    if not stamp.get("acted"):
        reason = (stamp.get("curve") or {}).get("reason")
        why = f" ({reason})" if reason else ""
        return f"autolevel: in band, identity — the render is the map's own{why}"
    curve = stamp["curve"]
    ends = curve.get("out_ends") or [None, None]
    return (
        f"autolevel: acted — black {curve.get('black_pt'):.3f}→{ends[0]:.3f}, "
        f"white {curve.get('white_pt'):.3f}→{ends[1]:.3f}, exponent {curve.get('exponent'):.3f}"
        f"{', black end guarded' if curve.get('black_guarded') else ''}"
    )


def _facts(row: dict) -> list[str]:
    location = row.get("location") or {}
    recipe = row.get("recipe") or {}
    scores = row.get("scores") or {}
    viewport = location.get("viewport") or {}
    advisory = row.get("advisory") or {}
    kind = recipe.get("mode_kind")
    facts = [
        f"{location.get('partition')} · {recipe.get('mode')} · {recipe.get('colormap')}",
        f"centre {viewport.get('center_re')}, {viewport.get('center_im')} · "
        f"width {viewport.get('width')} · maxiter {location.get('maxiter')}",
        f"{scores.get('head')} — P(≥3) {_number(scores.get('p_ge3'))} · {top_end(scores)}",
        f"location head P(≥3) {_number(scores.get('location_p_ge3'))} · "
        f"slot: {row.get('slot_source') or '—'} · look group {row.get('group') or '—'} · "
        f"palette anchor {(row.get('palette') or {}).get('anchor')} of "
        f"{len((row.get('palette') or {}).get('candidates') or [])} candidates",
    ]
    if row.get("release_autolevel") is not None:
        facts.append(autolevel_line(row["release_autolevel"], "this picture — ", kind))
        facts.append(autolevel_line(row.get("autolevel"), "the render judged — ", kind))
    else:
        facts.append(autolevel_line(row.get("autolevel"), "", kind))
    if advisory:
        facts.append(_cut_line(advisory, "advisory", "annotation only — it removed nothing"))
    if row.get("bar"):
        facts.append(_cut_line(row["bar"], "bar", "ACTING — a row below it is not seated"))
    if row.get("rejected"):
        taken = row["rejected"]
        facts.append(
            f"REJECTED by {taken.get('rejector')} on {taken.get('date')}: {taken.get('reason')}"
            " — recorded, not deleted; this row is no longer served"
        )
        # A rejection that is a comparison names the row it lost to. Without it
        # the page states that this wallpaper is no longer served and gives no
        # way to see that the place still is.
        if taken.get("survivor"):
            facts.append(f"the wallpaper that keeps this location: {taken['survivor']}")
    if row.get("reason"):
        facts.append(f"reason: {row['reason']}")
    return facts


def _cut_line(cut: dict, kind: str, what: str) -> str:
    """One release cut as the sheet states it: the height, the verdict, the standing."""
    clears = cut.get("clears")
    return (
        f"{kind} {cut.get('name')} {cut.get('value')}: "
        + ("clears" if clears else "below" if clears is False else "no score")
        + f" ({what})"
    )


def top_end(scores: dict) -> str:
    """`P(≥4)`, which is the only column that can order a saturated top end.

    Present and null are different states and the line says which. A judge with
    three classes has no fourth cutpoint at all — that is a fact about its scale,
    not a missing number — and a scored row whose `P(≥4)` is absent for any other
    reason is a record that predates this column.
    """
    if scores.get("p_ge4") is not None:
        return f"P(≥4) {_number(scores['p_ge4'])} (unconditional)"
    if scores.get("p_ge3") is None:
        return "P(≥4) — (no score: this row has a reason instead)"
    return "P(≥4) — (not on this judge's scale)"


def _number(value) -> str:
    return "—" if value is None else f"{float(value):.4f}"


def _card(row: dict, directory: Path) -> str:
    picture = row.get("picture")
    source = thumbnail(directory / picture) if picture else ""
    image = (
        f'<img src="{source}" alt="">'
        if source
        else '<div class="missing">no picture on disk</div>'
    )
    facts = "".join(f"<li>{html.escape(line)}</li>" for line in _facts(row))
    return (
        f'<figure><div class="frame">{image}</div>'
        f"<figcaption><b>{html.escape(row.get('candidate', ''))}</b>"
        f"<ul>{facts}</ul></figcaption></figure>"
    )


STYLE = """
:root { color-scheme: light dark; }
body { font: 14px/1.5 system-ui, sans-serif; margin: 2rem auto; max-width: 1100px;
       padding: 0 1rem; }
h1 { font-size: 1.4rem; margin-bottom: .25rem; }
h2 { font-size: 1.1rem; margin-top: 2.5rem; border-top: 1px solid #8886; padding-top: 1rem; }
.lede { opacity: .8; margin-top: 0; }
.grid { display: grid; gap: 1.5rem; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); }
figure { margin: 0; }
.frame { background: #0003; border-radius: 4px; overflow: hidden; }
img { display: block; width: 100%; height: auto; }
.missing { padding: 3rem 1rem; text-align: center; opacity: .6; }
figcaption b { font-family: ui-monospace, monospace; }
figcaption ul { list-style: none; margin: .4rem 0 0; padding: 0; font-size: 12px; opacity: .85; }
figcaption li { overflow-wrap: anywhere; }
table { border-collapse: collapse; font-size: 13px; }
td, th { text-align: left; padding: .15rem .8rem .15rem 0; vertical-align: top; }
"""


def build(
    run: str,
    released: list[dict],
    passed_over: list[dict],
    skipped: list[dict],
    summary: dict,
    directory: Path,
    output: Path,
    rejected: list[dict] | None = None,
) -> Path:
    """Write the sheet. `directory` is what the rows' picture paths are relative to.

    `released` is the **served** set — a row a later review rejected belongs in
    `rejected`, which draws its own section rather than disappearing.
    """
    directory = Path(directory)
    rejected = list(rejected or ())
    lines = [
        "<!doctype html><meta charset='utf-8'>",
        f"<title>release {html.escape(run)}</title>",
        f"<style>{STYLE}</style>",
        f"<h1>release {html.escape(run)}</h1>",
        f"<p class='lede'>{len(released)} released of {summary.get('requested', '?')} "
        f"asked for, out of {summary.get('scored', '?')} scored candidates over "
        f"{summary.get('attempts', '?')} attempts. Distribution review is yours.</p>",
        _table(summary),
        "<h2>Released</h2>",
        "<div class='grid'>" + "".join(_card(row, directory) for row in released) + "</div>",
    ]
    if rejected:
        lines += [
            f"<h2>Rejected after review ({len(rejected)})</h2>",
            "<p class='lede'>Seated by the run, taken back by a person afterwards. The rows "
            "are still in the records with their scores untouched — they are not served, and "
            "they are here so the page and the record agree about what happened.</p>",
            "<div class='grid'>" + "".join(_card(row, directory) for row in rejected) + "</div>",
        ]
    if passed_over:
        lines += [
            f"<h2>Passed over ({len(passed_over)})</h2>",
            "<p class='lede'>Scored, eligible, and beaten — by a better candidate in the "
            "same partition, by a slot the mix gave elsewhere, or by a supply cap.</p>",
            "<div class='grid'>" + "".join(_card(row, directory) for row in passed_over) + "</div>",
        ]
    if skipped:
        lines += [
            f"<h2>Already in the collection ({len(skipped)})</h2>",
            "<p class='lede'>Good enough to take a slot, but a second wallpaper of a place "
            "the collection has already released one of.</p>",
            "<div class='grid'>" + "".join(_card(row, directory) for row in skipped) + "</div>",
        ]
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return output


#: Near misses shown when a run seated fewer pictures than this. A floor and not
#: a count: a release that seated two rows still wants a page a reviewer can
#: disagree with, and two cards is not one.
NEAR_MISSES = 6


def from_records(run: str, rows: list[dict], summary: dict, directory: Path, output: Path) -> Path:
    """The sheet for a run, drawn off its accumulated release records alone.

    THE one place a sheet's sections are decided, used by the run that makes the
    records and by anything that later changes them. Everything it needs is on the
    rows — the served set, what a review took back, what the location rule removed —
    which is exactly the property the records were written to have.

    Deterministic in the rows it is given, so redrawing an unchanged run rewrites
    the same bytes.
    """
    from fractal_wallpapers.curation import records

    served = records.served(rows)
    rejected = records.score_rank(row for row in rows if records.is_rejected(row))
    capped = records.REASONS["location_served"]
    # Score rank within partition, not raw score across the page. The near-miss
    # section is a *prefix* of this list, and the two judges do not share a scale
    # — sorting both heads' probabilities together handed the whole section to
    # whichever head's scale runs higher, which is the same failure a single
    # selection pass over both heads once made one stage upstream.
    passed_over = records.score_rank(
        row for row in rows if row.get("verdict") == "passed_over" and row.get("reason") != capped
    )
    return build(
        run,
        served,
        passed_over[: max(NEAR_MISSES, len(served))],
        [row for row in rows if row.get("reason") == capped],
        summary,
        directory,
        output,
        rejected=rejected,
    )


# --------------------------------------------------------------------------- #
# The score sheet: whatever a leg made, laid out worst-to-best by one score.
# --------------------------------------------------------------------------- #
#
# The release sheet above answers *what shipped*. This answers a different
# question — **how good is the pile** — and it is the page every leg since
# 2026-09-07 has rebuilt by hand: the rows sorted on the gallery-grade head's
# `p_fine(>=4)` descending, cut into bands with a sticky separator saying how
# many sit in each and how many are above the line, one tile a row.
#
# **The row shape is the caller's and never this module's.** A ledger row and a
# gallery seat row carry the score, the picture and the caption under different
# names, and the sheet that assumed one shape is the reason every leg copied a
# script instead of calling a function. So the score, the picture and the caption
# lines all arrive as callables over whatever the caller holds.

#: The bands a score sheet separates on, good to bad. A row falls in the FIRST
#: band whose floor it clears, so the label states where that floor sits and the
#: last entry has to be `0.0` or a row below every floor lands in no band at all.
#:
#: These six are the cuts the gallery-grade head is read at everywhere else:
#: 0.50 is the bar Matt adopted at n=1000, and 0.75 and 0.90 are what a mining
#: leg reports its clears against.
BANDS: tuple[tuple[float, str], ...] = (
    (0.90, "0.90 and up"),
    (0.75, "0.75 &ndash; 0.90"),
    (0.50, "0.50 &ndash; 0.75"),
    (0.25, "0.25 &ndash; 0.50"),
    (0.10, "0.10 &ndash; 0.25"),
    (0.00, "below 0.10"),
)

#: The caption vocabulary a caller may name, and nothing else. A caption line is
#: either plain text or `(style, text)` with the style one of these — which is
#: what keeps a caller from handing this module markup it would then have to
#: trust. Everything is escaped on the way in either way.
LINE_STYLES = ("plain", "strong", "muted", "mono")

#: The score sheet's long edge. Narrower than [`THUMBNAIL_WIDTH`] because this
#: page carries hundreds of tiles where a release sheet carries dozens, and the
#: thumbnails are embedded in both.
SCORE_THUMBNAIL_WIDTH = 320

SCORE_STYLE = """
body { background:#14161a; color:#e6e8eb; margin:0;
       font:13px/1.45 ui-sans-serif, system-ui, "Segoe UI", sans-serif; }
header { padding:14px 16px; background:#1b1e24; border-bottom:1px solid #2c313a; }
h1 { font-size:16px; margin:0 0 6px; }
.lede { color:#9aa4b1; max-width:78rem; margin:0 0 6px; }
.lede b { color:#e6e8eb; }
code { font-family:ui-monospace, monospace; color:#c8b98a; }
h2.band { position:sticky; top:0; z-index:2; margin:0; padding:8px 16px;
          background:#22262e; border-top:1px solid #3a4150;
          border-bottom:1px solid #2c313a; font-size:13px; font-weight:600;
          letter-spacing:.04em; text-transform:uppercase; }
h2.band span { float:right; color:#8a939f; font-weight:400; text-transform:none;
               letter-spacing:0; }
.grid { display:grid; gap:12px; padding:12px 16px;
        grid-template-columns:repeat(auto-fill, minmax(300px,1fr)); }
figure { margin:0; background:#1c1f26; border:1px solid #2c313a; border-radius:6px;
         overflow:hidden; }
img { display:block; width:100%; background:#0e1013; }
.missing { padding:40px 10px; text-align:center; color:#6b7480; }
figcaption { display:flex; flex-direction:column; gap:2px; padding:7px 9px 9px; }
.top { display:flex; justify-content:space-between; align-items:baseline; }
.score { font-size:17px; font-weight:600; font-family:ui-monospace, monospace;
         color:#d8e4f0; }
.rank { color:#6b7480; font-family:ui-monospace, monospace; }
.strong { color:#8fc7a0; font-weight:600; }
.muted { color:#8a939f; }
.mono { font-family:ui-monospace, monospace; font-size:10.5px; color:#6b7480;
        white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
"""


def by_score(rows: Iterable[dict], score) -> list[dict]:
    """`rows` ordered on `score` descending, the ones it cannot read last.

    `score` is `row -> float | None`. A row with no score sorts to the tail
    rather than being dropped: a missing score is a coverage reading, and a sheet
    that hid it would hide the reading. Ties break on `repr` of the row's `key`
    where it has one, so redrawing an unchanged pile writes the same bytes.
    """
    held = list(rows)
    return sorted(
        held,
        key=lambda row: (
            score(row) is None,
            -(score(row) or 0.0),
            str(row.get("key", "")) if isinstance(row, dict) else "",
        ),
    )


def banded(ordered: list[dict], score, bands: tuple = BANDS) -> list[tuple]:
    """`[(label, rows, above)]` — the separators a score sheet is cut at.

    `ordered` must already be through [`by_score`]; this walks it once and never
    re-sorts, so a caller that wants a different order gets its bands in that
    order. A band holding nothing is **left out**, which is what makes the page
    read as a distribution rather than as a form with empty sections. `above` is
    how many rows precede the band, which is the number a reader actually wants
    off a separator — *how much of this page is better than what follows*.

    A row with no score falls in the last band, with the rows below every floor:
    it is unplaceable rather than bad, and the tile says so by drawing an em dash
    where a score would be.
    """
    out: list[tuple] = []
    for at, (floor, label) in enumerate(bands):
        ceiling = bands[at - 1][0] if at else None
        held = [
            row
            for row in ordered
            if (score(row) is None and at == len(bands) - 1)
            or (
                score(row) is not None
                and (score(row) or 0.0) >= floor
                and (ceiling is None or (score(row) or 0.0) < ceiling)
            )
        ]
        if held:
            out.append((label, held, sum(len(other) for _l, other, _a in out)))
    return out


def _line(line) -> str:
    style, text = ("plain", line) if isinstance(line, str) else line
    if str(style) not in LINE_STYLES:
        raise ValueError(f"a caption line's style is one of {LINE_STYLES}, not {style!r}")
    body = html.escape(str(text))
    return f"<div>{body}</div>" if style == "plain" else f'<div class="{style}">{body}</div>'


def tile(picture, lines, *, score=None, index=None, width: int = SCORE_THUMBNAIL_WIDTH) -> str:
    """One tile: the picture embedded, then the score, the rank, and `lines`.

    `picture` is a path or `None`; a picture this machine does not hold draws a
    placeholder rather than a broken image, because a sheet is read on whichever
    box has the store and the tiers move. `lines` is the caption the caller
    names — see [`LINE_STYLES`] — and this escapes every one of them.
    """
    data = thumbnail(Path(picture), width=width) if picture and Path(picture).is_file() else ""
    image = (
        f'<img loading="lazy" src="{data}" alt="">'
        if data
        else '<div class="missing">picture not on disk</div>'
    )
    reading = "&mdash;" if score is None else f"{float(score):.4f}"
    rank = "" if index is None else f'<span class="rank">#{int(index)}</span>'
    caption = "".join(_line(line) for line in lines)
    return (
        f"<figure>{image}<figcaption>"
        f'<div class="top"><span class="score">{reading}</span>{rank}</div>'
        f"{caption}</figcaption></figure>"
    )


def score_sheet(
    rows: Iterable[dict],
    *,
    score,
    lines,
    picture,
    title: str,
    lede: str,
    output: Path,
    bands: tuple = BANDS,
    width: int = SCORE_THUMBNAIL_WIDTH,
) -> Path:
    """The whole page: `rows` ordered on `score`, cut into `bands`, one tile a row.

    The four callables are the whole of the row shape — `score`, `picture` and
    `lines` each take one row — so a ledger row and a gallery seat row reach this
    through their own three functions and not through a converter. `lede` is HTML
    the caller composed and is NOT escaped; `title` is text and is.
    """
    ordered = by_score(rows, score)
    pieces: list[str] = []
    index = 0
    for label, held, above in banded(ordered, score, bands):
        pieces.append(
            f'<h2 class="band">{label}<span>{len(held)} row(s) &middot; '
            f"{above} above this line</span></h2><div class='grid'>"
        )
        for row in held:
            index += 1
            pieces.append(
                tile(picture(row), lines(row), score=score(row), index=index, width=width)
            )
        pieces.append("</div>")
    if not pieces:
        pieces.append('<p class="missing">nothing to lay out</p>')
    page = (
        "<!doctype html>\n"
        '<meta charset="utf-8">\n'
        f"<title>{html.escape(title)}</title>\n"
        f"<style>{SCORE_STYLE}</style>\n"
        f'<header>\n <h1>{html.escape(title)}</h1>\n <p class="lede">{lede}</p>\n</header>\n'
        + "".join(pieces)
        + "\n"
    )
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding="utf-8", newline="\n")
    return output


def _table(summary: dict) -> str:
    rows = "".join(
        f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>"
        for key, value in summary.items()
    )
    return f"<table>{rows}</table>"


__all__ = [
    "BANDS",
    "LINE_STYLES",
    "NEAR_MISSES",
    "SCORE_STYLE",
    "SCORE_THUMBNAIL_WIDTH",
    "THUMBNAIL_QUALITY",
    "THUMBNAIL_WIDTH",
    "autolevel_line",
    "banded",
    "build",
    "by_score",
    "from_records",
    "score_sheet",
    "thumbnail",
    "tile",
    "top_end",
]
