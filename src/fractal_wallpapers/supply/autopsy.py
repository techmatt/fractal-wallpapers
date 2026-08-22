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

#: The batch trace the quota writes as it goes, beside the ledger. It is what
#: turns "this node was never expanded" into a reason: it says, per batch, which
#: partitions were capped, which were guaranteed and how many slots each took.
TRACE_NAME = "quota.jsonl"

#: What a refused card can say about itself. Each is a fact somewhere in the run
#: data — the row's own fate, or the batch trace of the batches it sat through —
#: and a card that fits none of them says nothing rather than guessing.
JUNK_FLOOR = "floor-killed — below the junk floor, so the walk never stood on it"
GOOD_FLOOR = "below the good floor — the walk expanded it and it booked nothing"
NEVER_EXPANDED = "below the good floor — it joined the frontier and was never expanded"
CAPPED = "capped — its partition was priced out of every batch after it"
OUTBID_PARTITION = "outbid on partition — its partition took no slot after it joined the frontier"
OUTBID_RANK = "outbid on node rank — its partition was served and it was never the pick"
DISCOUNTED = "discounted lineage — its root had already booked, so the contest priced it down"
UNSPENT = "the run ended before its partition was served again"

#: What each **structural** gate refused a candidate for, in one sentence apiece.
#: These used to say nothing at all on the card, on the reasoning that the `fate`
#: line already named the gate — which is true and is not the same as telling a
#: reader what the gate is. They are the majority of any run's refusals, so the
#: page's whole reject half was the half with no explanation on it.
GATES = {
    "interior_cap": "interior-capped — too much of the frame is the set's interior",
    "instant_escape": (
        "instant escape — the whole frame leaves at once: far exterior, nothing in it"
    ),
    "flat": "flat — no variety in the escape times, so the frame is one wash of colour",
    "occupancy_floor": (
        "below the occupancy floor — the detail is real but confined to a corner and "
        "most of the frame is empty"
    ),
}

#: What a card with a fate this file has never heard of says. A gate added to the
#: ledger and not to [`GATES`] leaves a card that names the gate and admits it
#: cannot explain it, which is a page saying what it knows rather than a page
#: silently dropping a column.
UNNAMED_GATE = "refused by the {fate} gate, which this page has no sentence for"


def _buckets(path: Path) -> tuple[dict, Counter, dict]:
    """`(pictured rows, every row, run facts)` — candidates keyed `(channel, verdict)`.

    `verdict` is `admitted` or `refused`, and the middle tier goes with the
    refusals: `expandable` is a row the walk stood on and did not book, which is
    what "refused" means to the books this page is about.

    The third return is what [`Reasons`] needs and what only a pass over the whole
    ledger can supply: which nodes were ever expanded, and which batch each root's
    lineage first booked in. Collected here rather than in a second read because a
    production ledger is tens of thousands of rows and this page is not worth two
    passes over one.
    """
    rows: dict = {}
    totals: Counter = Counter()
    expanded: set = set()
    booked: dict = {}
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or not line.endswith("}"):
                continue
            row = json.loads(line)
            if row.get("kind") != "candidate":
                continue
            channel = row.get("channel") or "unchanneled"
            admitted = row.get("fate") == ledger_module.SURVIVED
            verdict = "admitted" if admitted else "refused"
            totals[(channel, verdict)] += 1
            expanded.add(row.get("parent_node_id"))
            if admitted:
                root, batch = row.get("root_id"), int(row.get("batch") or 0)
                booked[root] = min(batch, booked.get(root, batch))
            if row.get("image"):
                rows.setdefault((channel, verdict), []).append(row)
    return rows, totals, {"expanded": expanded, "booked": booked}


def _traces(run_dir: Path) -> dict:
    """`{batch: trace}` — what the quota decided, batch by batch.

    Absent for a run written before the quota kept one, which is a real state:
    the page then says what the row itself says and no more.
    """
    path = Path(run_dir) / TRACE_NAME
    if not path.is_file():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or not line.endswith("}"):
            continue
        row = json.loads(line)
        out[int(row["batch"])] = row
    return out


class Reasons:
    """Why one refused card is refused, derived and never guessed.

    A refused row is one of three things, and the ledger already says which:

    * a **structural gate** refused it before the scorer saw it — [`GATES`] says
      which gate and what the gate is about. These are most of any run's
      refusals and they used to be the ones with nothing written on them.
    * **`not_admitted`** — the scorer put it below the junk floor. It never
      reached the frontier, so no allocation ever had the chance to pass it over.
    * **`expandable`** — it cleared the junk floor, joined the frontier and did
      not clear the good floor. That is why it is not in the books; the second
      half of the question is why the run never came back to it, and *that* is
      what the quota's batch trace answers.

    **Every refused card carries one.** A card that could say nothing was a card
    a reader had to already know the pipeline to read.

    The second half has four possible answers and every one is read off the trace
    of the batches the node actually sat through: its partition was **capped**
    for all of them, it took **no slot** in any of them, its lineage had booked
    and the contest **discounted** it, or its partition was served and it simply
    ranked below what was taken. A node still on the frontier when the run
    stopped is none of those and says so.

    A row whose family belongs to no registered partition, and a run with no
    trace at all, get the floor half and nothing more.
    """

    def __init__(self, facts: dict, traces: dict, summary: dict):
        self.expanded = facts["expanded"]
        self.booked = facts["booked"]
        self.traces = traces
        self.last = max(traces) if traces else None
        self.discounting = (summary.get("lineage_discount") or {}).get("status") == "on"

    def of(self, row: dict) -> str | None:
        """The sentence a refused card carries. `None` only for a row that was
        not refused at all — an admitted row has no refusal to explain, and this
        is asked about the refused half of the page."""
        fate = row.get("fate")
        if fate == ledger_module.SURVIVED:
            return None
        if fate == ledger_module.NOT_ADMITTED:
            return JUNK_FLOOR
        if fate != ledger_module.EXPANDABLE:
            # A structural gate refused it. The `fate` line on the card names the
            # gate; this says what the gate is, which is the half a reader who
            # does not already know the pipeline needs.
            return GATES.get(str(fate), UNNAMED_GATE.format(fate=fate))
        if row.get("node_id") in self.expanded:
            return GOOD_FLOOR
        passed_over = self._passed_over(row)
        return f"{NEVER_EXPANDED}; {passed_over}" if passed_over else NEVER_EXPANDED

    def _passed_over(self, row: dict) -> str | None:
        """Why the run never expanded a node it had put on the frontier."""
        from fractal_wallpapers.supply import partitions

        if not self.traces:
            return None
        try:
            partition = partitions.partition_of_row(row)
        except partitions.UnregisteredPartition:
            return None
        after = [
            trace for batch, trace in self.traces.items() if batch > int(row.get("batch") or 0)
        ]
        if not after:
            return UNSPENT
        if all(partition in (trace.get("capped") or []) for trace in after):
            return CAPPED
        if not any(_slots_in(trace, partition) for trace in after):
            return OUTBID_PARTITION
        first = self.booked.get(row.get("root_id"))
        if self.discounting and first is not None and self.last is not None and first < self.last:
            return DISCOUNTED
        return OUTBID_RANK


def _slots_in(trace: dict, partition: str) -> int:
    """How many nodes one partition was handed in one batch, both channels."""
    contest = (trace.get("slots") or {}).get(partition, 0)
    share = ((trace.get("share") or {}).get("slots") or {}).get(partition, 0)
    return int(contest) + int(share)


def _card(row: dict, directory: Path, reason: str | None = None) -> str:
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
    if reason:
        body += f"<div class='why'>{html.escape(reason, quote=False)}</div>"
    image = f"<img src='{source}' alt=''>" if source else "<div class='missing'>no picture</div>"
    return f"<figure>{image}<figcaption>{body}</figcaption></figure>"


_STYLE = """
body { font: 13px/1.45 system-ui, sans-serif; margin: 2rem; background: #14161a; color: #e8e8ea; }
h1 { font-size: 1.2rem; } h2 { font-size: 1rem; margin-top: 2rem; color: #9fd3ff; }
.grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); }
figure { margin: 0; background: #1d2027; padding: .5rem; border-radius: 4px; }
img { width: 100%; display: block; border-radius: 2px; }
figcaption { font-size: 11px; color: #a9adb8; margin-top: .4rem; word-break: break-all; }
.why { color: #ffc9a3; margin-top: .35rem; word-break: normal; }
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
    rows, totals, facts = _buckets(ledger_path)
    if not totals:
        return None
    directory = views_dir(run_dir)
    reasons = Reasons(facts, _traces(run_dir), summary)
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
                "<div class='grid'>"
                + "".join(
                    _card(row, directory, reasons.of(row) if verdict == "refused" else None)
                    for row in taken
                )
                + "</div>"
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


__all__ = [
    "CAPPED",
    "DISCOUNTED",
    "GOOD_FLOOR",
    "JUNK_FLOOR",
    "NEVER_EXPANDED",
    "OUTBID_PARTITION",
    "OUTBID_RANK",
    "SAMPLE",
    "SHEET_NAME",
    "THUMBNAIL_WIDTH",
    "TRACE_NAME",
    "UNSPENT",
    "Reasons",
    "write",
]
