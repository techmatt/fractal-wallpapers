"""The walk's record: one file, one schema, and a fate on every row.

A discovery run's whole output is this ledger. It is JSONL — UTF-8, one object
per line, an integer `schema` from the first row — and it is append-only, so a
run that is killed halfway leaves a valid record of everything up to the kill.

Four things are decided here, and each of them is a decision the source project
paid to learn.

**Record and rank, never gate and forget.** A candidate the structural gates
refused is written down, with the gate that refused it. A walk that logged only
its survivors could never afterwards distinguish "the gates were too tight" from
"there was nothing there", and both of those look like a low yield. The rejects
are the larger half of the record and they are the half that says whether the
search is working.

**A row carries its full identity, not a reference to one.** The family with
every constant, and the viewport, on the same line — so a candidate is a
complete location and is never split across two files that have to be joined
later. For the dynamical families this is what makes the row mean anything at
all: two Julia views at the same coordinates with different `c` are different
fractals, and a row that recorded only the viewport would silently merge them.

**Coordinates are decimal strings, verbatim.** The string is the identity of a
location; `f64` is a lossy view of it that is good enough at today's depths and
will not be forever. Whatever was written is what is recorded, unaltered, and
[`fractal_wallpapers.discovery.nucleus.key_from_strings`] is what normalizes at
the *reader* — never by trusting the writer.

**A row carries the verdict as well as the frame.** `scorer` names the judge,
`score` is its `P(≥3)` and `score_great` its `P(≥4)` — two numbers rather than
one because the supply currency weights a class 4 ten times a class 3, so a row
carrying only the first would make every machine-classed find a 3 forever.
`score_error` says why there is no verdict, which is a different fact from a low
one. All four are `null` on a row written under the null scorer, which is what
keeps a corpus mixed across the day the head was wired in readable: the reader
asks the row what judged it rather than assuming.

## Expanding from a place and booking it are two decisions, and the fate says both

A candidate that clears every structural gate reaches the scorer, and the scorer
answers two different questions about it. *May the walk continue from here?* is
about the frontier, and it is asked at the junk floor. *Is this a find worth
counting?* is about the books — the census, the deficit, the word "admitted" —
and it is asked at the good floor. One cut used to do both jobs, which meant a
place too ordinary to keep was also a place the walk could not stand on, and a
frontier fed only by its own admissions shrinks at any realized pass rate under
one over the branching factor.

So there are three scored fates rather than two, and every row carries the one it
earned:

```text
score ≥ good floor   survived      admitted: on the frontier and in the books
score ≥ junk floor   expandable    on the frontier, not in the books
otherwise            not_admitted  neither — recorded, and not walked from
```

[`SCORED`] is the three of them together, and it is what "the structural gates
passed" means to a reader. Nothing downstream keys on `survived` to mean *the
gates passed*: that would silently re-couple the two decisions at the reader
after they were separated at the writer.

## Three more fields, because one channel's floor is waived by depth

A parameter-plane root starts four or five rungs above the widths its labelled
material lives at, so the first rungs below one are exempt from the expansion
floor. That makes the fate alone ambiguous — an `expandable` row under a plane
root either cleared the junk floor or was carried past it — so every gate
survivor carries the three facts that disambiguate it and, together, are the
survival-by-rung table:

* `plane_rung` — rungs below a plane-seed root, `0` being the root itself and
  `null` under every other kind of root;
* `cleared_junk` — the junk floor's own verdict, recorded whether or not it was
  the one that decided;
* `grace` — whether the waiver was in force at this rung.

A row where `grace` is true and `cleared_junk` is false is one the grace stood
on. A depth-aware floor, if the cliff turns out to be the wrong shape, is fitted
from these and nothing else.

## A reframing says which node it pushed

A `reframing` row's `node_id` is the node the operator was fired *from*. What it
put on the frontier is `pushed_node_id` — the id of the child, or `null` where
the firing produced none. Written because the alternative is reconstruction: with
only the viewport to go on, a reader chaining through a reframing has to match
that frame against every later row's parent geometrically, and the website's
figure maker doing exactly that recovered 283 of 1,965 and dropped 123.

**Readers treat it as optional and the schema does not move.** A ledger written
before the field existed carries rows without it, those runs are not re-written,
and a reader that requires it would refuse a record that is not wrong. Absent
means *this ledger predates the field*, never *no node was pushed* — `used` is
what says that.
"""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path, PurePosixPath
from typing import Any

#: The schema every row in this file carries, from the first row.
SCHEMA = 1

#: A candidate that passed every structural gate and cleared the good floor: it
#: is on the frontier *and* in the books, which is what "admitted" means
#: everywhere in this project.
SURVIVED = "survived"

#: A candidate that passed every structural gate and cleared the junk floor but
#: not the good floor. The walk may continue from it; nothing counts it as
#: supply. This is the tier that keeps a frontier alive between admissions.
EXPANDABLE = "expandable"

#: A candidate the structural gates passed and the scorer would not stand on:
#: below the junk floor, or carrying no score at all. Recorded, never walked from.
NOT_ADMITTED = "not_admitted"

#: The three fates of a candidate that reached the scorer — i.e. that every
#: structural gate let through. THE answer to "did the gates pass", because
#: reading [`SURVIVED`] for that would re-couple expansion to booking at the
#: reader after they were separated at the writer.
SCORED = (SURVIVED, EXPANDABLE, NOT_ADMITTED)

#: The fates a candidate can be recorded with. Everything outside [`SCORED`]
#: names the gate that refused it — the *furthest* gate it reached, so the tally
#: reads as a picture of what the search is actually spending its refusals on.
FATES = (
    SURVIVED,
    EXPANDABLE,
    #: Too much of the frame is the set's interior.
    "interior_cap",
    #: The whole frame escapes almost at once: far exterior, nothing in it.
    "instant_escape",
    #: No variety in the escape times: a flat wash.
    "flat",
    #: Detail present but confined to a corner; the frame is mostly empty.
    "occupancy_floor",
    NOT_ADMITTED,
)

#: A refinement of a location this ledger already holds: the same place, at a
#: better frame, decided after the walk closed.
#:
#: **It is a row, not an edit.** A ledger is append-only and nothing rewrites one,
#: so a scan taken at close cannot go back and change the candidate row it is
#: about — and the walk's shape leaves no earlier place to put it, because "the
#: best three frames of this walk" is not knowable until the walk has finished.
#: So the refinement is appended after the candidates and **the reader prefers
#: it**: [`fractal_wallpapers.supply.ledgers.admitted`] joins it onto the
#: candidate row on the location's own identity and hands on the refined frame,
#: the refined score and the fate that score earns.
#:
#: The row's `family` and `viewport` are the **original** ones, because that is
#: the identity every reader already dedups on — a refinement is a statement
#: about a location the ledger holds, never a second location. `refined_viewport`
#: and `score`/`score_great` are what to prefer, and they are `null` on a row
#: whose window did not clear the margin: such a row is kept because what the
#: margin refused is the evidence the margin is set where it should be.
REFINED = "refined"

#: Why a node produced no child at all.
NODE_CAUSES = (
    "width_floor",
    "interior_cap",
    "instant_escape",
    "flat",
    "occupancy_floor",
    "no_candidate",
)


#: What a walk's record is called, wherever one is written. The supply union
#: looks a ledger up at `<run directory>/<this>` rather than searching for it, so
#: this name and [`refuse_a_nested_run_directory`] are two halves of one rule.
LEDGER_NAME = "walk.jsonl"


def refuse_a_nested_run_directory(path: Path) -> None:
    """Refuse a ledger written deeper than one level under the regenerable tree.

    A walk's run directory is a *top-level name* of that tree: it is the unit the
    storage tiers move, and it is why `supply.ledgers` can find every ledger with
    one `stat` per run directory instead of walking a hundred gigabytes of cache.
    Nothing enforced it until now, and the failure it leaves is the quiet kind —
    a run under `artifacts/studies/tonight/` writes a perfectly good ledger that
    no later census, saturation memory or novelty pool ever reads, and the supply
    it found simply is not there.

    Silent about a path outside the tree, which is every test's `tmp_path` and
    every one-off somewhere else: this is a rule about the tree's own shape.
    """
    from fractal_wallpapers.paths import ARTIFACTS_NAME, tracked_name

    parts = PurePosixPath(tracked_name(Path(path).parent)).parts
    if len(parts) > 2 and parts[0] == ARTIFACTS_NAME:
        raise ValueError(
            f"a walk's run directory has to be a top-level name of the regenerable tree, and "
            f"{'/'.join(parts)} is {len(parts) - 1} levels down. The supply union looks each "
            f"ledger up at <run directory>/{LEDGER_NAME}, so a ledger written here would be "
            f"invisible to every census, saturation memory and novelty pool afterwards — the "
            f"run would work and its supply would not exist. Use "
            f"--out-dir {ARTIFACTS_NAME}/{'_'.join(parts[1:])} instead."
        )


def invocation() -> dict:
    """How this process was launched, as a run header carries it.

    A record that does not say this is a record whose flags have to be inferred
    from the values it happens to have written, against whatever the defaults
    were that week. It worked once — `SMOKE_location_run_1h_0906` resolved a
    standing walk's whole command line off `refill.proven` being populated and
    `quota.partitions` being null — and it works only while no default moves.

    Three spellings of one fact, because they answer different questions. `argv`
    is the arguments verbatim, which is what a reader compares against a default.
    `program` is how the entry point was named, which separates a console-script
    leg from `python -m` and from a leg a test drove. `line` is the pair joined
    for pasting; it quotes POSIX-style, which is the shell this project's
    commands are written for on both platforms.
    """
    program = Path(sys.argv[0]).name if sys.argv else ""
    args = [str(arg) for arg in sys.argv[1:]]
    return {"program": program, "argv": args, "line": shlex.join([program, *args])}


class Ledger:
    """An append-only JSONL record of one walk."""

    def __init__(self, path: Path):
        self.path = Path(path)
        refuse_a_nested_run_directory(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a", encoding="utf-8", newline="\n")
        self.counts: dict[str, int] = {}

    def header(self, kind: str, *, ledgers_read: dict | None = None, **fields: Any) -> dict:
        """Write a run's first row: what the leg was told, and how it was reached.

        Every leg kind's header comes through here rather than through
        [`write`], and that is the whole point of the method existing: the
        invocation and the ledger tiers are facts about *any* run record, so a
        third leg kind gets them by writing its header the way the first two do
        rather than by somebody remembering to add two fields.

        `ledgers_read` is what [`supply.ledgers.tiers_read`] returns over the
        earlier ledgers this leg actually opened, and `None` means it opened
        none. It matters because two halves of one night can read different
        populations without saying so — measured 2026-09-06, a harvest read the
        12 hot ledgers while the reframe leg beside it read 47 across both tiers,
        and every figure comparing the two halves was comparing populations.

        The header is the first row by construction: a run's configuration is
        what its rows have to be read against, so a record whose first line is
        already data is one that can be read wrongly before it can be read at
        all.
        """
        if self.counts:
            raise ValueError(
                f"{self.path} already holds {sum(self.counts.values())} row(s) from this "
                f"process, so this is not its header. A run record's first row is its "
                f"configuration; write everything else through `write`."
            )
        return self.write(kind, **fields, invocation=invocation(), ledgers_read=ledgers_read)

    def write(self, kind: str, **fields: Any) -> dict:
        """Append one row. The schema and the kind are stamped here, not by
        callers, so no row can be written without them."""
        row = {"schema": SCHEMA, "kind": kind, **fields}
        self._handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._handle.flush()
        self.counts[kind] = self.counts.get(kind, 0) + 1
        return row

    def close(self) -> None:
        self._handle.close()

    def __enter__(self) -> Ledger:
        return self

    def __exit__(self, *exception) -> None:
        self.close()


def read(path: Path) -> list[dict]:
    """Read a ledger back, checking the schema on every row."""
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("schema") != SCHEMA:
                raise ValueError(
                    f"{path}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}"
                )
            rows.append(row)
    return rows


def viewport(center_re: str, center_im: str, width: str) -> dict:
    """A viewport, as the decimal strings that are its identity."""
    return {"center_re": str(center_re), "center_im": str(center_im), "width": str(width)}
