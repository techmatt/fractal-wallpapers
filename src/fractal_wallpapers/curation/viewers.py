"""A viewer per planned gallery, and one index page over them.

The published viewer is one record's page written to one place with no stamp in
its name — `curate solve browse --viewer`. A person judging every collection we
plan to publish wants that page twenty-one times over: the general gallery, the
nineteen collections of [`curation.targets`], and whichever comparison sizes are
being weighed. This writes each named record's page to
`<viewer>/<label>/index.html` with [`tentative.page`] — the same builder, the same
presentation order, the same thumbnails out of the ledger's pictures, nothing
rendered — and `<viewer>/all.html` beside them, a plain table linking each one.

## A label is read off the record, never typed

A record says which gallery it is through its solve name, and that is the name the
website's collection panel already reads: `targets_<collection>_n<seats>_<stamp>`
for a collection (`curation/targets.py`'s *Recording a collection the site will
read*). **A set recorded under one name stem reads `<stem>_<collection>`** and is
matched second — the twenty `final139_*` records of 2026-09-21 are spelled that
way, and a mode collection's name is nowhere else in its record: a family pass
carries the family on `config.theme` and a mode pass carries `null`. Anything
else is a general pass — the whole pool, no `--collection` — and
is labelled `general`, with `_n<seats>` appended when it was asked for any size
other than [`tentative.RECORDED_SEATS`], so the official size and a comparison
size never land in one directory. Two named records resolving to one label are
refused rather than the second overwriting the first.

## What the index reads

Per gallery: the seats filled against the target (the table's number for a
collection, the asked size for a general pass), the shortfall the manifest
recorded, and the seated `p_fine` median and lower quartile — the fine head's own
column, `distinct.fine_scores`, read once for every record. A seat the head has no
reading for is counted and left out of both figures rather than read as zero.
"""

from __future__ import annotations

import html
import re
import statistics
from pathlib import Path

from fractal_wallpapers.curation import page as page_module
from fractal_wallpapers.curation import targets, tentative

#: The index page's file name, beside the per-gallery directories.
INDEX_NAME = "all.html"

#: A collection record's solve name — the spelling `builder seats` requires.
_COLLECTION_NAME = re.compile(r"^targets_(?P<collection>.+)_n(?P<seats>\d+)_")

#: The other spelling: a stem and the collection, `<stem>_<collection>`. A set
#: recorded under one name stem is named that way — the twenty `final139_*`
#: records of 2026-09-21 are — and a mode collection carries its name nowhere
#: else, the manifest's `config.theme` being the family for a family pass and
#: `null` for a mode one. Read second, so a name the site's spelling matches
#: still resolves through that one.
_STEM_AND_COLLECTION = re.compile(r"^(?P<stem>[^_]+)_(?P<collection>.+)$")


class ViewersRefused(ValueError):
    """Two named records would share one viewer directory."""


def label_of(manifest: dict) -> str:
    """Which gallery a record is, as the directory its viewer lands in."""
    solve_name = str(manifest.get("solve", {}).get("name") or "")
    named = _COLLECTION_NAME.match(solve_name)
    if named and named["collection"] in targets.TARGETS:
        return named["collection"]
    stemmed = _STEM_AND_COLLECTION.match(solve_name)
    if stemmed and stemmed["collection"] in targets.TARGETS:
        return stemmed["collection"]
    asked = int(manifest["seats"]["asked"])
    return "general" if asked == tentative.RECORDED_SEATS else f"general_n{asked}"


def target_of(label: str, manifest: dict) -> int:
    """The size the gallery is planned at: the table's for a collection, else the ask."""
    if label in targets.TARGETS:
        return targets.seats_for(label)
    return int(manifest["seats"]["asked"])


def quartiles(values) -> tuple[float | None, float | None]:
    """`(median, q1)` of a list, `(None, None)` for an empty one."""
    held = sorted(float(value) for value in values)
    if not held:
        return None, None
    if len(held) == 1:
        return held[0], held[0]
    q1, median, _ = statistics.quantiles(held, n=4, method="inclusive")
    return median, q1


def reading(stamp: str, fine: dict) -> dict:
    """One gallery's line of the index, off its two tracked-shaped files."""
    rows = tentative.read_rows(stamp)
    manifest = tentative.read_manifest(stamp)
    label = label_of(manifest)
    read = [fine[row["key"]] for row in rows if row.get("key") in fine]
    median, q1 = quartiles(read)
    return {
        "label": label,
        "stamp": stamp,
        "solve": manifest.get("solve", {}).get("name"),
        "seats": len(rows),
        "target": target_of(label, manifest),
        "shortfall": manifest["seats"].get("shortfall"),
        "p_fine_median": median,
        "p_fine_q1": q1,
        "unread": len(rows) - len(read),
    }


def build(stamps=None, fine: dict | None = None, log=print) -> Path:
    """Write every named record's viewer and the index over them. Returns the index.

    **No stamp named is the whole keep list**, [`tentative.kept`], so `all.html`
    written that way always lists every kept record and never the subset the last
    caller happened to type. An empty keep list refuses rather than writing an
    index over nothing.
    """
    from fractal_wallpapers.curation import distinct

    stamps = list(stamps or ()) or tentative.kept()
    if not stamps:
        raise ViewersRefused("no stamp was named and the keep list holds no record on this disk")
    fine = distinct.fine_scores() if fine is None else fine
    lines = [reading(str(stamp), fine) for stamp in stamps]
    seen: dict = {}
    for line in lines:
        if line["label"] in seen:
            raise ViewersRefused(
                f"{seen[line['label']]} and {line['stamp']} are both `{line['label']}`; "
                f"name one of them."
            )
        seen[line["label"]] = line["stamp"]
    root = tentative.viewer_dir()
    for line in lines:
        tentative.page(line["stamp"], out=root / line["label"] / tentative.PAGE_NAME, log=log)
    index = root / INDEX_NAME
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(_index(lines), encoding="utf-8", newline="\n")
    log(f"[viewers] {len(lines)} viewer(s) and {INDEX_NAME} under {root}")
    return index


def _figure(value) -> str:
    return "&mdash;" if value is None else f"{value:.3f}"


def _index(lines: list[dict]) -> str:
    body = [
        "<h1>planned galleries</h1>",
        '<p class="lede">One viewer per record, at the size each is planned at. '
        "<code>p_fine</code> is the fine head's column over the seated rows.</p>",
        "<table><tr><th>gallery</th><th>seats / target</th><th>shortfall</th>"
        "<th>p_fine median</th><th>p_fine q1</th><th>stamp</th><th>solve</th></tr>",
    ]
    for line in lines:
        short = line["seats"] < line["target"]
        seats = f"{line['seats']} / {line['target']}"
        body.append(
            f'<tr><td><a href="{html.escape(line["label"])}/{tentative.PAGE_NAME}">'
            f"{html.escape(line['label'])}</a></td>"
            f'<td class="mono{" warn" if short else ""}">{seats}</td>'
            f'<td class="mono">{line["shortfall"] or 0}</td>'
            f'<td class="mono">{_figure(line["p_fine_median"])}</td>'
            f'<td class="mono">{_figure(line["p_fine_q1"])}</td>'
            f'<td class="mono">{html.escape(line["stamp"])}</td>'
            f'<td class="mono dim">{html.escape(str(line["solve"]))}</td></tr>'
        )
    body.append("</table>")
    style = "body { padding: 16px; } .warn { color: var(--warn); } .dim { color: var(--muted); }"
    return page_module.shell("planned galleries", "\n".join(body), style=style)
