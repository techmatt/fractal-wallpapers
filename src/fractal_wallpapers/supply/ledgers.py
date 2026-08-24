"""The union of everything every walk has ever found.

A walk writes one ledger. The supply engine reads *all of them*, and this module
is the one reader — the machine leg of the standing deficit and the cross-run
saturation memory both come through here, so there is exactly one answer to
"what supply exists".

**Admitted means three things at once**, and they are checked in this order:

* *the gates passed* — a candidate any structural gate refused is a recorded
  refusal, not supply. The gates are the *structural* ones only: a candidate the
  walk stood on but did not book passed them too, and is filtered out by the next
  line rather than by this one;
* *the score clears the keeper floor* — a candidate the scorer declined to score
  has no verdict to be kept on, so it is not admitted and is counted as such;
* *the location has not already been admitted* — the ledgers overlap, because a
  location found by one run can be found again by the next, and a union that
  counted it twice would let re-running a walk inflate a partition's stock.

**Deduplication is on location identity, never on a row id.** A ledger's node
ids are scoped to their run, so two runs mint the same id for different places.
Keying the union on identity is what makes it a statement about *places* rather
than about rows.

**The original files are only ever read.** Nothing here rewrites a ledger, mints
a prefixed copy of one, or re-keys a row. A union that edits its inputs cannot be
re-derived, and a copy under a scratch tree is a population that a cleanup
deletes.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.discovery import ledger as ledger_module
from fractal_wallpapers.paths import Tiers, tracked_name
from fractal_wallpapers.supply import currency as money
from fractal_wallpapers.supply.location import key_of_row

#: The file every walk writes its record to. Re-exported from the writer rather
#: than restated: this reader looks the file up by name at a fixed depth, so the
#: two modules agreeing about the name is the whole of why it is found.
LEDGER_NAME = ledger_module.LEDGER_NAME


def ledger_dirs() -> list[Path]:
    """Every run directory, on whichever tier it currently sits.

    A walk's run directory is a top-level name of the regenerable tree, so it is
    also the unit the storage tiers move: some are hot, some are archived, and
    the union has to be the same population either way. Asking `Tiers` for the
    names rather than globbing one root is what makes that true — and it is what
    makes the union's answer independent of what anybody archived this week,
    which is the whole point of archiving being reversible.
    """
    tiers = Tiers.current()
    return [tiers.unit(name) for name in tiers.names()]


def ledger_paths(root: Path | None = None, exclude: Path | None = None) -> list[Path]:
    """Every walk ledger under the tree, minus one — usually this run's own.

    `root` narrows the search to one directory, for a caller that has one; the
    default searches both tiers.

    `exclude` is resolved before comparison, because the caller's path came from a
    run directory and ours came from a directory walk: two spellings of one file
    is how a run ends up seeded with its own finds.

    **Looked up, never searched for.** A walk's run directory is a top-level name
    of the regenerable tree and its ledger is [`LEDGER_NAME`] directly inside it
    ([`ledger_dirs`], and [`ledger.Ledger`] refuses to write anywhere else), so
    finding every ledger is one `stat` per run directory. It used to be an
    `rglob` per root, which on a tree that is overwhelmingly `views/`, `fields/`
    and `tiles/` walked a hundred gigabytes of cache to find thirty-two small
    text files: **734.6 s** over run10's own tiers, 728 of them inside `tiles/`
    alone, against **0.08 s** here — and the harvest paid it three times before
    its first batch, which is the whole of what `schedule.LEDGER_LOAD_SECONDS`
    had grown to reserve.
    """
    own = Path(exclude).resolve() if exclude is not None else None
    found = [path for here in _ledger_homes(root) if (path := here / LEDGER_NAME).is_file()]
    # Sorted by the *tracked* name, not by the absolute path. That name does not
    # change when a run directory is archived, and the order here is not
    # cosmetic: the union credits a location to the first ledger that admits it,
    # so sorting by drive letter would re-attribute half the supply the day
    # something moved tiers.
    found.sort(key=tracked_name)
    return [path for path in found if own is None or path.resolve() != own]


def _ledger_homes(root: Path | None) -> list[Path]:
    """Every directory a walk ledger may sit directly inside.

    With no `root` that is the run directories themselves. With one it is the
    directory named *and* its immediate children, because the one caller that
    passes a root passes either a single run directory (`--harvest`) or a whole
    artifacts tree (`--ledgers`), and both spellings have to mean the same set of
    ledgers as the default does.
    """
    if root is None:
        return ledger_dirs()
    root = Path(root)
    if not root.is_dir():
        return []
    return [root, *sorted(entry for entry in root.iterdir() if entry.is_dir())]


def rows(path: Path, kind: str | None = None):
    """Yield a ledger's rows, checking the schema on each.

    A tolerant reader on purpose in one respect only: a ledger is append-only and
    a run killed mid-write can leave a truncated final line, which is a real state
    and not a corrupt file. Everything else raises.
    """
    with Path(path).open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                if not line.endswith("}"):
                    continue  # a killed run's half-written last line
                raise
            if row.get("schema") != ledger_module.SCHEMA:
                raise ValueError(
                    f"{path}:{number}: schema {row.get('schema')!r}, "
                    f"expected {ledger_module.SCHEMA}"
                )
            if kind is None or row.get("kind") == kind:
                yield row


def passes_gates(row: dict) -> bool:
    """Whether every structural gate let this candidate through.

    All three *scored* fates pass here, because the scorer's two floors are a
    different question from the gates and are asked of the row's own score a line
    later. Reading `survived` for this would quietly re-apply the good floor at
    the reader: curation's junk floor, at a third of the height, would then be
    comparing against a population the walk had already cut above it.
    """
    return row.get("fate") in ledger_module.SCORED


def is_admitted(row: dict) -> bool:
    """THE admission predicate: the gates, then the keeper floor."""
    return passes_gates(row) and money.passes_good_floor(row.get("score"))


def refined_of(row: dict, refinements: dict) -> dict:
    """A candidate row with its refinement applied, or the row itself.

    **THE reader that prefers the later row.** A walk cannot refine a framing
    before it writes the candidate — "the best three frames of this walk" is not
    knowable until the walk has finished — and a ledger is append-only, so the
    refinement is a [`ledger.REFINED`] row after the candidates and this is where
    it is joined back on.

    What moves is the frame and the verdict on it: `viewport`, `maxiter`,
    `score`, `score_great`, and the fate that score now earns. The frame the walk
    actually stood on is kept under `framing.original` and the row on disk is
    untouched either way.

    **The location key moves with the frame, and that is deliberate.** A key is
    built from the family and the viewport, so a refined row is a different
    location — which is this project's existing stance, stated where the
    reframing operators dedup: *the framing is part of the identity, and the same
    atom at two framings is two views*. It is the opposite of what the gallery
    pass does with a refinement, and the two are not in conflict: a pass refines a
    location the pool **already holds** at its recorded frame, so pinning identity
    is what stops one place taking two seats, while a walk refines a frame nothing
    downstream has seen yet and the refined frame simply is the location it found.

    The fate is re-derived rather than carried, because a refinement is only ever
    an improvement — the window contains the original frame and the margin is
    strict — so a row can cross a floor upward here and can never fall.
    """
    key = key_of_row(row)
    refinement = refinements.get(key) if key is not None else None
    if refinement is None:
        return row
    out = dict(row)
    out["framing"] = {
        "adopted": True,
        "original": {
            "viewport": row.get("viewport"),
            "maxiter": row.get("maxiter"),
            "score": row.get("score"),
            "score_great": row.get("score_great"),
        },
        "gain": refinement.get("gain"),
        "margin": refinement.get("margin"),
        "width_scale": refinement.get("width_scale"),
        "dx": refinement.get("dx"),
        "dy": refinement.get("dy"),
        "slug": refinement.get("framing"),
        "refined_by": refinement.get("run_seed"),
    }
    out["viewport"] = refinement["refined_viewport"]
    out["maxiter"] = refinement.get("refined_maxiter", row.get("maxiter"))
    out["score"] = refinement.get("score")
    out["score_great"] = refinement.get("score_great")
    out["score_regime"] = refinement.get("score_regime", row.get("score_regime"))
    # The digest names a picture of the *original* frame, so carrying it onto a
    # row that is now about another frame would be a name that promises the wrong
    # file — which is the one thing `score_view` exists to prevent.
    out["score_view"] = None
    if row.get("fate") in ledger_module.SCORED:
        out["fate"] = _fate_of(out["score"])
    return out


def _fate_of(score: float | None) -> str:
    """Which of the three scored fates a score earns, on the floors as they stand.

    Both floors through their owners rather than restated: the keeper floor is
    the supply currency's and the junk floor is curation's, which is the same
    pair [`discovery.scoring.LocationScorer`] asks when it decides a fate the
    first time. Curation is reached lazily, the way every reach from this half of
    the project into it is.
    """
    from fractal_wallpapers.curation import floors

    if money.passes_good_floor(score):
        return ledger_module.SURVIVED
    if floors.passes_junk_floor(score):
        return ledger_module.EXPANDABLE
    return ledger_module.NOT_ADMITTED


def refinements(path: Path) -> dict:
    """`{location key: row}` for every adopted refinement in one ledger.

    Only the adopted ones. A refinement whose window did not clear the margin is
    on the record — it is the evidence the margin is set where it should be — and
    it changes nothing about the location it is about, so a reader that acted on
    it would be acting on a decision that was deliberately not taken.
    """
    out: dict = {}
    for row in rows(path, kind=ledger_module.REFINED):
        if not row.get("adopted") or not row.get("refined_viewport"):
            continue
        key = key_of_row(row)
        if key is not None:
            out[key] = row
    return out


def admitted(path: Path, admit=None) -> list[dict]:
    """Every admitted candidate row of one ledger, refinements preferred.

    `admit` replaces the whole predicate with a caller-supplied `row -> bool`. It
    exists so a second consumer can share this reader — and therefore the
    schema check, the namespacing and the deduplication — instead of growing a
    second walker that could disagree about what the population is.

    One pass over the file, and only the **gate survivors** are held while it
    runs: the refinements are appended *after* the candidates they are about, so
    a scored row cannot be decided on the way past. Everything else is decided as
    it is read and put back in ledger order afterwards, because a candidate the
    structural gates refused can never be refined into passing — a refinement
    moves a score, and the gates are not a score — so no predicate can want a
    different answer about one than it would have got before.
    """
    predicate = is_admitted if admit is None else admit
    decided: list[tuple[int, dict]] = []
    pending: list[tuple[int, dict]] = []
    found: dict = {}
    position = 0
    for row in rows(path):
        kind = row.get("kind")
        if kind == "candidate":
            if row.get("fate") in ledger_module.SCORED:
                pending.append((position, row))
            elif predicate(row):
                decided.append((position, row))
            position += 1
        elif kind == ledger_module.REFINED and row.get("adopted") and row.get("refined_viewport"):
            key = key_of_row(row)
            if key is not None:
                found[key] = row
    for at, row in pending:
        row = refined_of(row, found) if found else row
        if predicate(row):
            decided.append((at, row))
    decided.sort(key=lambda cell: cell[0])
    return [row for _at, row in decided]


def admitted_union(paths=None, admit=None) -> tuple[list[dict], dict]:
    """`(rows, diagnostics)` — the admitted union, in ledger order.

    Each returned row is the ledger's own row with `_ledger` added, naming the
    file it came from. The diagnostics carry what a census wants to print: the
    size, the per-ledger contribution, and how many rows an earlier ledger had
    already admitted the same location for. Of those, the ones a ledger duplicated
    against *itself* are counted separately and kept out of `overlap_sample`,
    which is a statement about which ledgers overlap.
    """
    paths = ledger_paths() if paths is None else [Path(p) for p in paths]
    seen: dict = {}
    kept: list[dict] = []
    overlaps: list[str] = []
    repeats = 0
    per_ledger: dict = {}
    unkeyed = 0
    for path in paths:
        # `tracked_name`, not a second spelling of it: this label is the key
        # curation's sidecar keeps a scored row under, so it has to survive the
        # artifacts tree being moved to another disk. A private
        # `relative_to(repo_root())` here did not — it turned every ledger's name
        # into an absolute path the moment the tree left the checkout, which
        # would have made every stored row unmatchable and quietly un-replaced.
        label = tracked_name(path)
        taken = 0
        for row in admitted(path, admit):
            key = key_of_row(row)
            if key is None:
                # Counted, and kept: a row whose identity cannot be built is real
                # supply, and dropping it would understate a partition's stock.
                # What it cannot be is deduplicated, which is why it is reported.
                unkeyed += 1
            elif key in seen:
                # A ledger that found one place twice is a repeat, not an
                # overlap: the sample exists to say which ledgers cover the same
                # ground, and "x vs x" answers a question nobody asked. Counted
                # either way — the row is dropped either way.
                if seen[key] == label:
                    repeats += 1
                else:
                    overlaps.append(f"{seen[key]} vs {label}")
                continue
            else:
                seen[key] = label
            out = dict(row)
            out["_ledger"] = label
            kept.append(out)
            taken += 1
        per_ledger[label] = taken
    return kept, {
        "size": len(kept),
        "ledgers": len(paths),
        "per_ledger": per_ledger,
        "location_overlaps": len(overlaps) + repeats,
        "same_ledger_repeats": repeats,
        "overlap_sample": overlaps[:5],
        "unkeyed_rows": unkeyed,
    }


__all__ = [
    "LEDGER_NAME",
    "admitted",
    "admitted_union",
    "is_admitted",
    "ledger_dirs",
    "ledger_paths",
    "passes_gates",
    "rows",
]
