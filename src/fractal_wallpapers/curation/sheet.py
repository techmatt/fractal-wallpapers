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
"""

from __future__ import annotations

import base64
import html
import io
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


def _autolevel_line(stamp: dict | None, what: str = "") -> str:
    """What the operator did, prefixed by *which render* it did it to.

    A released row has two stamps and they are different renders — the candidate
    the verdict was cast on, and the full-resolution picture on this page. Showing
    one and captioning the other is how a sheet says something false while every
    field on it is true.
    """
    return f"{what}{_did(stamp)}" if what else _did(stamp)


def _did(stamp: dict | None) -> str:
    if stamp is None:
        return (
            "autolevel: not run — this coloring kind is palette-indifferent, or the switch was off"
        )
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
    facts = [
        f"{location.get('partition')} · {recipe.get('mode')} · {recipe.get('colormap')}",
        f"centre {viewport.get('center_re')}, {viewport.get('center_im')} · "
        f"width {viewport.get('width')} · maxiter {location.get('maxiter')}",
        f"{scores.get('head')} P(≥3) {_number(scores.get('p_ge3'))}"
        + (f" · P(≥4) {_number(scores.get('p_ge4'))}" if scores.get("p_ge4") is not None else "")
        + f" · location head P(≥3) {_number(scores.get('location_p_ge3'))}",
        f"slot: {row.get('slot_source') or '—'} · look group {row.get('group') or '—'} · "
        f"palette anchor {(row.get('palette') or {}).get('anchor')} of "
        f"{len((row.get('palette') or {}).get('candidates') or [])} candidates",
    ]
    if row.get("release_autolevel") is not None:
        facts.append(_autolevel_line(row["release_autolevel"], "this picture — "))
        facts.append(_autolevel_line(row.get("autolevel"), "the render judged — "))
    else:
        facts.append(_autolevel_line(row.get("autolevel")))
    if advisory:
        clears = advisory.get("clears")
        facts.append(
            f"advisory {advisory.get('name')} {advisory.get('value')}: "
            + ("clears" if clears else "below" if clears is False else "no score")
            + " (annotation only — it removed nothing)"
        )
    if row.get("reason"):
        facts.append(f"reason: {row['reason']}")
    return facts


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
) -> Path:
    """Write the sheet. `directory` is what the rows' picture paths are relative to."""
    directory = Path(directory)
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
    if passed_over:
        lines += [
            f"<h2>Passed over ({len(passed_over)})</h2>",
            "<p class='lede'>Scored, eligible, and beaten — by a better candidate in the "
            "same partition, by a slot the mix gave elsewhere, or by a supply cap.</p>",
            "<div class='grid'>" + "".join(_card(row, directory) for row in passed_over) + "</div>",
        ]
    if skipped:
        lines += [
            f"<h2>Removed by the look cap ({len(skipped)})</h2>",
            "<p class='lede'>Good enough to take a slot, but a third picture of a look the "
            "release had already taken twice.</p>",
            "<div class='grid'>" + "".join(_card(row, directory) for row in skipped) + "</div>",
        ]
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return output


def _table(summary: dict) -> str:
    rows = "".join(
        f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>"
        for key, value in summary.items()
    )
    return f"<table>{rows}</table>"


__all__ = ["THUMBNAIL_QUALITY", "THUMBNAIL_WIDTH", "build", "thumbnail"]
