"""The channel autopsy: what each claim on the batch bought, and what it refused.

A harvest's summary says how many admissions the exploration share returned
against the contest. It cannot say whether they were *the same picture*, and that
is the entire question the share was added to answer — a share whose finds are
novel by lineage and identical by eye has bought nothing anybody wanted.

So every harvest lays a seeded sample of both channels out side by side, in four
grids:

```text
share    admitted    what the protected slots booked
share    refused     what they spent themselves on and did not book
contest  admitted    the same two, for the deficit-priced remainder
contest  refused
```

**The pictures already exist.** `expand` draws every gate survivor at the node
regime and the run keeps them under `views/`, so this page costs a thumbnail
resize per sampled row and draws nothing. A refused row's picture is there for
the same reason an admitted one's is: the walk records and ranks, and a refusal
with no picture is a verdict nobody can disagree with.

**The sample is seeded off the run's own seed**, so the page is a function of the
run and re-writing it gives the same rows. A sample rather than everything
because a production leg refuses tens of thousands of candidates and a page with
all of them in it is a page nobody opens.

**One file, carrying its own pictures**, on the same rule as the release sheet:
it is copied out of the repository to be read, and a page pointing at files under
an ignored tree arrives empty.

**The grids are over the *pictured* population and the header says so.** The
engine draws a frame for every gate survivor and for nothing else, so a candidate
a structural gate refused has no picture to show — it is the majority of any
run's rejects, and a page that silently dropped it would report a reject rate
several times lower than the run's. Each heading carries both counts.

A row that carries no `channel` came from a walk that had no channels — every
ledger written before the exploration share existed — and the page says so
rather than filing it under the contest.
"""

from __future__ import annotations

import html
import json
import random
from collections import Counter
from pathlib import Path

from fractal_wallpapers.discovery import ledger as ledger_module
from fractal_wallpapers.discovery.walk import views_dir
from fractal_wallpapers.supply import novelty

#: Rows sampled per grid. Enough that one composition repeated is obvious at a
#: glance, few enough that the page stays a couple of megabytes.
SAMPLE = 12

#: The long edge of an embedded thumbnail. A gate render is 384 wide; this is
#: half of it, which is where a texture is still readable and a grid of four
#: still fits a screen.
THUMBNAIL_WIDTH = 192

#: The file a run's autopsy lands at, beside its summary.
SHEET_NAME = "channel_autopsy.html"


def _buckets(path: Path) -> tuple[dict, Counter]:
    """`(pictured rows, every row)` — candidates keyed `(channel, verdict)`.

    `verdict` is `admitted` or `refused`, and the middle tier goes with the
    refusals: `expandable` is a row the walk stood on and did not book, which is
    what "refused" means to the books this page is about.
    """
    rows: dict = {}
    totals: Counter = Counter()
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or not line.endswith("}"):
                continue
            row = json.loads(line)
            if row.get("kind") != "candidate":
                continue
            channel = row.get("channel") or "unchanneled"
            verdict = "admitted" if row.get("fate") == ledger_module.SURVIVED else "refused"
            totals[(channel, verdict)] += 1
            if row.get("image"):
                rows.setdefault((channel, verdict), []).append(row)
    return rows, totals


def _card(row: dict, directory: Path) -> str:
    from fractal_wallpapers.curation.sheet import thumbnail

    picture = directory / row["image"]
    source = thumbnail(picture, THUMBNAIL_WIDTH) if picture.is_file() else ""
    viewport = row.get("viewport") or {}
    family = row.get("family") or {}
    score = row.get("score")
    lines = [
        f"{family.get('kind', '?')} d{family.get('degree', '?')}",
        f"{viewport.get('center_re', '?')}, {viewport.get('center_im', '?')}",
        f"w {viewport.get('width', '?')}",
        f"root {row.get('root_id')} · rung {row.get('depth')} · {row.get('origin')}",
        f"fate {row.get('fate')} · P(&ge;3) {'—' if score is None else f'{float(score):.4f}'}",
    ]
    body = "".join(f"<div>{html.escape(line, quote=False)}</div>" for line in lines)
    image = f"<img src='{source}' alt=''>" if source else "<div class='missing'>no picture</div>"
    return f"<figure>{image}<figcaption>{body}</figcaption></figure>"


_STYLE = """
body { font: 13px/1.45 system-ui, sans-serif; margin: 2rem; background: #14161a; color: #e8e8ea; }
h1 { font-size: 1.2rem; } h2 { font-size: 1rem; margin-top: 2rem; color: #9fd3ff; }
.grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); }
figure { margin: 0; background: #1d2027; padding: .5rem; border-radius: 4px; }
img { width: 100%; display: block; border-radius: 2px; }
figcaption { font-size: 11px; color: #a9adb8; margin-top: .4rem; word-break: break-all; }
.missing { color: #6d7280; padding: 2rem 0; text-align: center; }
.empty { color: #6d7280; }
table { border-collapse: collapse; margin: 1rem 0; }
td, th { padding: .2rem .8rem .2rem 0; text-align: left; }
"""


def write(run_dir: Path, summary: dict, sample: int = SAMPLE) -> Path | None:
    """Write the run's channel autopsy. Returns the path, or `None` for a run
    whose ledger holds no pictured candidate at all."""
    run_dir = Path(run_dir)
    ledger_path = run_dir / "walk.jsonl"
    if not ledger_path.is_file():
        return None
    rows, totals = _buckets(ledger_path)
    if not totals:
        return None
    directory = views_dir(run_dir)
    draw = random.Random(int((summary.get("walk") or {}).get("seed", 0)))

    parts = [
        f"<style>{_STYLE}</style>",
        "<h1>channel autopsy</h1>",
        _bought_table(summary),
    ]
    channels = [novelty.SHARE, novelty.CONTEST]
    channels += sorted({key[0] for key in totals} - set(channels))
    for channel in channels:
        for verdict in ("admitted", "refused"):
            found = rows.get((channel, verdict)) or []
            whole = totals.get((channel, verdict), 0)
            parts.append(
                f"<h2>{html.escape(channel)} · {verdict} — {whole} row(s), "
                f"{len(found)} of them pictured</h2>"
            )
            if not found:
                parts.append(
                    "<p class='empty'>nothing pictured here: the engine draws a frame for a "
                    "gate survivor and for nothing else</p>"
                )
                continue
            taken = found if len(found) <= sample else draw.sample(found, sample)
            parts.append(
                "<div class='grid'>" + "".join(_card(row, directory) for row in taken) + "</div>"
            )
    path = run_dir / SHEET_NAME
    path.write_text("\n".join(parts) + "\n", encoding="utf-8", newline="\n")
    return path


def _bought_table(summary: dict) -> str:
    """What the summary already says about the two channels, above the pictures,
    so the page is readable without the JSON beside it."""
    bought = ((summary.get("exploration") or {}).get("bought")) or {}
    if not bought:
        return "<p class='empty'>this run allocated no exploration share</p>"
    header = "<tr><th>channel</th><th>slots</th><th>distinct</th><th>per slot</th></tr>"
    body = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{row.get('slots')}</td>"
        f"<td>{row.get('distinct')}</td><td>{row.get('distinct_per_slot')}</td></tr>"
        for name, row in sorted(bought.items())
    )
    return f"<table>{header}{body}</table>"


__all__ = ["SAMPLE", "SHEET_NAME", "THUMBNAIL_WIDTH", "write"]
