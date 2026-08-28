"""Where a location's attempts are framed, decided before any of them renders.

The gallery pass spends its attempts on the frames a walk happened to stop on. A
walk stops on a frame because the gates let it through and the head liked it, not
because that is the best crop of what is there — so the same place, a
quarter-frame left or half again as wide, is often a better wallpaper and the
pass has never asked. This asks. Per location in the attempt leg, before that
location's attempts render: scan a small window of framings, read each one
through the shipped location head, and adopt the best **only if it beats the
original by a margin**.

## Where it sits, and what it deliberately cannot touch

It is a step of the **attempt leg** and nothing above it. The slot allocation,
the farthest-point draw, the hard radius and the neighbourhoods are all decided
on unrefined geometry, which is what keeps the pass's diversity claim true: the
embedding store holds one vector per location at its recorded framing, and a
picker that chose points off refined geometry would be choosing distances nobody
has measured. Only the frames that go on to attempts move.

The location's **identity** does not move with the frame. A refined attempt is
still an attempt on that location: it keeps the location key, the
one-wallpaper-per-location cap still counts it against the same place, and the
near-duplicate grouping still keys on the original viewport. What changes is the
picture, and both viewports travel on every row that comes out.

## The window

Separable, and trimmed from the twelve-framing window the maker archive used —
which its own docstring called a first pass that worked on five anchors and never
swept, so neither shape has a measurement behind it.

```text
stage A   width x{0.707, 1.0, 1.414} at the current centre        3 frames
stage B   at the best width, recentre +-0.25 frame, one axis
          at a time: -x, +x, -y, +y                               4 frames
```

Seven frames a location, and [`SCAN_THE_ORIGINAL`] says why the `x1.0` centre is
one of them rather than free.

**A quarter of the frame means a quarter along the axis being moved** — `0.25 x
width` sideways and `0.25 x height` vertically, and the node frame is 16:9, so
the vertical step is `0.5625` of the horizontal one. The maker moved by a quarter
of the *width* on both axes, which is 0.44 frame-heights vertically: a
recentring that is not the same size as the one beside it. This is the one place
the geometry here deliberately differs from the archive's.

## The margin, and why it is not an argmax

The maker took the argmax of the window and leaned on the fact that the window
contains the original, so the answer can never fall below where it started. That
property is real and worth keeping — but it makes the *decision* free of
evidence: several correlated reads of one place, and the best of them wins by
construction, whether or not the head can tell them apart.

So the rule here is **strict improvement by [`MARGIN`], never argmax**: the best
candidate must beat the original's `P(>=4)` by the margin or the original framing
stays. Monotonicity is then free, and it is asserted rather than assumed — a
violation raises [`MonotonicityViolated`] and takes the pass down, because a
refinement that lowered a score is a bug in the arithmetic and not a bad framing.

The comparison is `P(>=4)` with `P(>=3)` breaking ties among the candidates that
clear the margin, which is the statistic the pass seats by — and the reason it is
that one rather than the head's `E[ord]`: a framing chosen on a statistic the
seating does not read is a framing chosen for a different question.

The margin itself is taken in **log-odds** of that probability and not in the
probability, because the population this step sees is the pass's own
neighbourhoods and those are the strongest locations in the pool: `P(>=4)` there
runs 0.93 to 1.00 and sits at 0.9998 in the middle. An absolute margin on a score
pinned against its ceiling refuses everything, however much better the framing
is. [`MARGIN`] carries the measurement.

## What the scan reads, and where its pictures come from

[`fractal_wallpapers.engine.screen`] draws frames a caller names through the same
gate battery at the same geometry an expansion uses, and writes each one at the
node regime — the geometry the shipped head reads and the one the sidecar's own
scores were taken at. So the scan needs no new engine work: one `screen` call per
chunk of frames, and the head over the JPEGs it wrote.

The gates come along with the render and they are not ignored. A candidate
framing the battery refuses is a frame no walk would have admitted, and adopting
one would put a picture in the gallery that the supply engine's own filter says
is not a location. Refused candidates are recorded with their fate and are not
adoptable; the original is never held to it, because it is already in the
admitted population.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from pathlib import Path

from fractal_wallpapers import engine

#: The schema every refinement row carries.
SCHEMA = 1

#: Stage A: what the frame's width is multiplied by, at the current centre. Half
#: an octave either side of where the walk stopped — wide enough that a crop
#: cutting the subject in half can find it, narrow enough that the frame is still
#: the same place.
WIDTH_LADDER = (0.707, 1.0, 1.414)

#: Stage B: how far a recentring moves, as a share of the frame **along the axis
#: it moves on**. See the module docstring: this is where the geometry differs
#: from the archive's.
RECENTRE = 0.25

#: The four recentrings, as (x, y) multiples of [`RECENTRE`]. One axis at a time:
#: the diagonals are four of the five the maker's 3x3 grid had and this window
#: does not, and they are what a separable search buys least from.
AXES = ((-1, 0), (1, 0), (0, -1), (0, 1))

#: Δ: how much better a framing has to read before it is adopted, in **nats of
#: log-odds** on `P(>=4)` — the statistic the pass seats by, on the scale where
#: this head still has resolution at the top of its range.
#:
#: The log-odds and not the probability, and that is a measurement rather than a
#: preference. The population this step actually sees is the gallery pass's
#: neighbourhoods, which are the strongest locations the pool holds: over the
#: twenty that seeded the first scan, `P(>=4)` at the recorded framing ran 0.9285
#: to 1.0000 with a median of 0.9998. There is no room above that for an absolute
#: margin — a Δ of 0.05 on the probability adopted **nothing**, and so would every
#: Δ down to 0.005, not because no framing was better but because a bounded score
#: pinned against its ceiling cannot express how much better. The same twenty
#: framings spread from -1.69 to +6.05 nats.
#:
#: A monotone re-scale, so nothing else moves: the ordering [`rank`] takes, the
#: tie-break on `P(>=3)` and the monotonicity assertion are all the same claims
#: they were on the probability.
#:
#: **2.0 nats** is where it starts, and the flip rate is the reason it is not
#: lower. The head serving now is the regime-robust one adopted on 2026-08-20,
#: whose pooled node-regime flip rate is 4.56% and whose great-cut flip rate is
#: 1.58% — not the 10.36% the audit that proposed this work quoted, which belongs
#: to the head that retired that day. 2.0 nats is a factor of 7.4 in the odds:
#: comfortably outside anything a 1.6%-flip head disagrees with itself about, and
#: it took 7 of the first twenty framings where 3.0 took 3 and 1.0 took 8. The
#: instrument that calibrates it is the pass's own Δ distribution beside the
#: `refined_pairs` sheet, and the sheet is the verdict.
MARGIN = 2.0

#: Frames per [`engine.screen`] call. A batch is one engine process, so this
#: trades the process launch against how long the leg goes without saying
#: anything.
BATCH = 64

#: Whether the `x1.0` centre rung is rendered rather than read off the sidecar.
#:
#: The sidecar already holds this exact frame's score at this exact regime, so
#: the design this was built from counted the rung free. It is rendered anyway,
#: for two reasons worth one extra frame in seven: the margin is then decided
#: entirely inside one render path, and the pass **measures** rather than
#: inherits the claim that the two paths draw the same picture. The agreement is
#: reported on every pass ([`price`]); an exact one is the evidence for turning
#: this off.
SCAN_THE_ORIGINAL = True

#: What the record calls a framing that was not moved.
UNMOVED = "w1_c"

#: Which of a location's two framings a row was rendered at, as [`block`] stamps
#: it. [`REFINED`] is whatever this leg decided for that location — which is the
#: original framing wherever it adopted nothing; [`ORIGINAL`] is the recorded
#: framing, always, and it is what a caller asks for when it wants the frame the
#: walk wrote down rather than the frame the scan chose.
REFINED = "refined"
ORIGINAL = "original"

#: Why a location's framing did not move. Not one reason: a window that held
#: nothing scoreable and a window whose best did not clear the margin are
#: different facts about the same location, and only the second one says the
#: margin was the thing that acted.
BELOW_MARGIN = "below_margin"
NO_CANDIDATE = "no_candidate"
UNSCANNABLE = "unscannable"

REFUSALS = {
    BELOW_MARGIN: "the best framing in the window did not beat the original by the margin",
    NO_CANDIDATE: "no framing in the window rendered, passed the gates and scored",
    UNSCANNABLE: "the original framing itself would not render at the node regime",
}


class MonotonicityViolated(RuntimeError):
    """An adopted framing reads below the framing it replaced.

    Raised, never logged. The window contains the original and the margin is
    strict, so an adopted framing that scores lower is not a bad crop — it is the
    arithmetic having gone wrong, and every row the pass writes after it would
    carry the result.
    """


@dataclass(frozen=True)
class Framing:
    """One candidate framing: where in the window it is, and the frame itself."""

    width_scale: float
    #: Multiples of [`RECENTRE`] along each axis. `(0, 0)` is a ladder rung.
    dx: int
    dy: int
    viewport: dict
    #: The cap this frame is drawn at, or `None` to let the engine's policy give
    #: the width its own. Named only on the rung that reproduces the original.
    maxiter: int | None = None

    @property
    def slug(self) -> str:
        """A framing as a name says it: the width rung, then the move."""
        moved = {(0, 0): "c", (-1, 0): "xm", (1, 0): "xp", (0, -1): "ym", (0, 1): "yp"}
        return f"w{self.width_scale:g}_{moved[(self.dx, self.dy)]}"

    @property
    def unmoved(self) -> bool:
        return self.width_scale == 1.0 and self.dx == 0 and self.dy == 0


def aspect() -> float:
    """The node frame's height as a share of its width, off the regime itself."""
    from fractal_wallpapers.models import tiles as tile_module

    tile = tile_module.NODE_REGIME.tile
    return float(tile[1]) / float(tile[0])


def viewport_at(viewport: dict, scale: float, dx: int, dy: int) -> dict:
    """The frame `scale` times as wide, moved `dx`/`dy` quarter-frames.

    The move is taken **at the new width**, which is what makes the window
    separable: stage B recentres the frame stage A chose, not the one it started
    from.
    """
    width = float(viewport["width"]) * float(scale)
    height = width * aspect()
    return {
        "center_re": repr(float(viewport["center_re"]) + dx * RECENTRE * width),
        "center_im": repr(float(viewport["center_im"]) + dy * RECENTRE * height),
        "width": repr(width),
    }


def ladder(row: dict) -> list[Framing]:
    """Stage A: the width ladder at the location's own centre."""
    out = []
    for scale in WIDTH_LADDER:
        unmoved = float(scale) == 1.0
        out.append(
            Framing(
                width_scale=float(scale),
                dx=0,
                dy=0,
                # The rung that IS the original is spelled the way the record
                # spells it, cap included, so what the scan draws there is the
                # picture the sidecar was read off rather than a re-derivation.
                viewport=(
                    dict(row["viewport"]) if unmoved else viewport_at(row["viewport"], scale, 0, 0)
                ),
                maxiter=int(row["maxiter"]) if unmoved else None,
            )
        )
    return out


def recentres(row: dict, best: Framing) -> list[Framing]:
    """Stage B: the four one-axis recentrings, at the width stage A chose."""
    return [
        Framing(
            width_scale=best.width_scale,
            dx=dx,
            dy=dy,
            viewport=viewport_at(row["viewport"], best.width_scale, dx, dy),
        )
        for dx, dy in AXES
    ]


def window(row: dict) -> list[Framing]:
    """Every framing the window holds, both stages, taking the ladder's `x1.0`.

    Not what [`refine`] runs — the point of a separable search is that stage B is
    planned after stage A answers — but what the window *is*, which is the thing a
    test about the geometry has to be able to ask.
    """
    rungs = ladder(row)
    centre = next(rung for rung in rungs if rung.unmoved)
    return [*rungs, *recentres(row, centre)]


# --------------------------------------------------------------------------- #
# Drawing the window and reading it.
# --------------------------------------------------------------------------- #
def _frame_spec(row: dict, framing: Framing) -> dict:
    frame = {"family": row["family"], **framing.viewport}
    if framing.maxiter is not None:
        frame["maxiter"] = int(framing.maxiter)
    return frame


def screen(pairs: list[tuple], directory: Path, log=print) -> list[dict]:
    """Draw every `(row, framing)` pair at the node regime and say what it is.

    One [`engine.screen`] call per [`BATCH`] frames. Each answer carries the
    picture, the fate the gate battery gave it and the frame the engine says it
    drew — read back rather than restated, so the record holds the decimals the
    render actually used.
    """
    from fractal_wallpapers.models import location_view
    from fractal_wallpapers.models import tiles as tile_module

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    colormap = location_view.canonical_map()
    node_width = int(tile_module.NODE_REGIME.tile[0])
    out: list[dict] = []
    for start in range(0, len(pairs), BATCH):
        chunk = pairs[start : start + BATCH]
        report = engine.screen(
            {
                "schema": 1,
                "frames": [_frame_spec(row, framing) for row, framing in chunk],
                "colormap": colormap,
                "colormap_dir": str(engine.colormap_dir()),
                "node_width": node_width,
                "out_dir": str(directory),
            }
        )
        for offset, (screened, (_row, framing)) in enumerate(
            zip(report["frames"], chunk, strict=True)
        ):
            picture = None
            if screened.get("image"):
                # `screen` names its frames by position in its own batch, so the
                # second chunk would overwrite the first's. Renamed to something
                # that says which frame it is, which is what the pairs sheet
                # reads it back by.
                name = f"{start + offset:05d}_{framing.slug}.jpg"
                (directory / screened["image"]).replace(directory / name)
                picture = name
            out.append(
                {
                    "framing": framing,
                    "picture": picture,
                    "fate": screened["fate"],
                    "passed": bool(screened["passed"]),
                    "viewport": {
                        "center_re": screened["center_re"],
                        "center_im": screened["center_im"],
                        "width": screened["width"],
                    },
                    "maxiter": int(screened["maxiter"]),
                    "p_ge3": None,
                    "p_ge4": None,
                    "error": None,
                }
            )
        log(f"[refine] {min(start + BATCH, len(pairs))}/{len(pairs)} frame(s) drawn")
    return out


def read(scanned: list[dict], families: list[dict], scorer, directory: Path) -> None:
    """Score every drawn frame through the head, in place.

    The picture is handed over rather than named, so the head reads the frame
    `screen` drew instead of rendering a second one of the same place — the
    identity a walk already relies on, at the regime it relies on it at.
    """
    wanted = [index for index, cell in enumerate(scanned) if cell["picture"]]
    if not wanted:
        return
    candidates = [
        {
            "family": families[index],
            "viewport": scanned[index]["viewport"],
            "maxiter": scanned[index]["maxiter"],
        }
        for index in wanted
    ]
    pictures = [Path(directory) / scanned[index]["picture"] for index in wanted]
    for index, reading in zip(wanted, scorer.read(candidates, pictures=pictures), strict=True):
        scanned[index]["p_ge3"] = reading.score
        scanned[index]["p_ge4"] = reading.great
        scanned[index]["error"] = reading.error


# --------------------------------------------------------------------------- #
# The decision.
# --------------------------------------------------------------------------- #
def rank(cell: dict):
    """Best first among framings: `P(>=4)`, then `P(>=3)`.

    The seating's order minus the candidate id — a tie among the framings of one
    location is broken by the window's own order, which is deterministic.
    """
    return (
        -(cell.get("p_ge4") if cell.get("p_ge4") is not None else -1.0),
        -(cell.get("p_ge3") if cell.get("p_ge3") is not None else -1.0),
    )


def adoptable(cell: dict) -> bool:
    """Whether a drawn framing may be adopted at all, gates included."""
    return bool(cell.get("picture")) and cell.get("p_ge4") is not None and cell["passed"]


#: How far a probability is held off 0 and 1 before its log-odds are taken. The
#: head reads 1.0 exactly on the strongest locations in the pool — at fp16 through
#: a running product of three cutpoints it has nowhere else to go — and a
#: difference of infinities is not a margin anything can act on.
EPSILON = 1e-12


def logit(probability: float) -> float:
    """One probability in nats of log-odds, clamped off both ends."""
    value = min(max(float(probability), EPSILON), 1.0 - EPSILON)
    return math.log(value / (1.0 - value))


def gain_of(candidate: dict, original: dict) -> float:
    """How much better a framing reads than the one it would replace, in nats.

    THE quantity the margin acts on. See [`MARGIN`] for why it is the log-odds
    and not the difference of the probabilities: on the population this step sees
    the probability is pinned against its ceiling and the difference between a
    framing that is better and one that is much better is four decimal places.
    """
    return logit(candidate["p_ge4"]) - logit(original["p_ge4"])


def decide(original: dict, candidates: list[dict], margin: float) -> tuple:
    """`(best, refusal)` — the window's best framing, and why it was not taken.

    Strict improvement, never argmax: `P(>=4)` has to rise by `margin` nats of
    log-odds ([`gain_of`]). Among the candidates that clear it the order is
    [`rank`], so what breaks the tie is the statistic the seating breaks ties on.
    `refusal` of `None` means the best is adopted.
    """
    live = [cell for cell in candidates if adoptable(cell)]
    if not live:
        return None, NO_CANDIDATE
    best = min(live, key=rank)
    if gain_of(best, original) < float(margin):
        return best, BELOW_MARGIN
    return best, None


def _side(cell: dict | None) -> dict | None:
    """One framing as a row carries it: the frame, the cap and the two scores."""
    if cell is None:
        return None
    return {
        "viewport": cell["viewport"],
        "maxiter": cell["maxiter"],
        "p_ge4": cell["p_ge4"],
        "p_ge3": cell["p_ge3"],
        "picture": cell["picture"],
        "fate": cell["fate"],
    }


def _record(row: dict, original: dict | None, best: dict | None, refusal, margin, seconds, scanned):
    """One location's whole refinement, as the log keeps it."""
    adopted = refusal is None and best is not None
    framing = best["framing"] if best is not None else None
    return {
        "schema": SCHEMA,
        "key": str(row["key"]),
        "adopted": bool(adopted),
        "refused": refusal,
        "why": REFUSALS.get(refusal) if refusal else None,
        "margin": float(margin),
        # What the margin acted on, in nats. The probability difference is beside
        # it because it is the number a person reads, and on this population it is
        # four zeros and a digit — which is the whole reason the margin is not
        # taken on it.
        "gain": (None if (best is None or original is None) else round(gain_of(best, original), 6)),
        "gain_p_ge4": (
            None
            if (best is None or original is None)
            else round(best["p_ge4"] - original["p_ge4"], 8)
        ),
        "width_scale": float(framing.width_scale) if adopted else 1.0,
        "dx": int(framing.dx) if adopted else 0,
        "dy": int(framing.dy) if adopted else 0,
        "slug": framing.slug if adopted else UNMOVED,
        "original": _side(original),
        # The window's best, adopted or not. A framing the margin refused is the
        # evidence the margin is set where it should be, and a record that kept
        # only the adopted ones could not show it.
        "best": _side(best),
        "scanned": int(scanned),
        "seconds": round(float(seconds), 3),
        "sidecar": None,
    }


# --------------------------------------------------------------------------- #
# The leg.
# --------------------------------------------------------------------------- #
def refine(
    rows: list[dict],
    *,
    directory: Path,
    scorer,
    margin: float = MARGIN,
    scores=None,
    log=print,
) -> list[dict]:
    """Scan every row's window and decide its framing. One record per row, in order.

    `rows` are the location rows the attempt leg is about to colorize — family,
    viewport, maxiter and key. `scores` is the supply sidecar, and it is read for
    one thing only: the reading it already holds of the `x1.0` rung, recorded
    beside the scan's own so the two render paths can be compared. Nothing is
    decided off it.

    Both stages are batched **across locations**, not within one: stage A is one
    sweep of the ladder over every row, and stage B is one sweep of the
    recentrings at the widths stage A chose. That is what makes the leg a handful
    of engine calls rather than two per location — and it is why the seconds on a
    record are the leg's own clock divided by the rows, which is a share and not a
    measurement of that location.
    """
    directory = Path(directory)
    if not rows:
        return []
    started = time.monotonic()

    log(f"[refine] stage A: the width ladder over {len(rows)} location(s)")
    pairs = [(row, framing) for row in rows for framing in ladder(row)]
    rungs = screen(pairs, directory, log)
    read(rungs, [row["family"] for row, _ in pairs], scorer, directory)

    rung_count = len(WIDTH_LADDER)
    stage_a = [rungs[index * rung_count : (index + 1) * rung_count] for index in range(len(rows))]
    originals = [
        next((cell for cell in cells if cell["framing"].unmoved), None) for cells in stage_a
    ]

    # Stage B only for the rows whose own frame drew — a location whose `x1.0`
    # rung would not render has nothing to compare a candidate against, and
    # spending four more frames on it would buy an answer nobody can judge.
    live = [
        index
        for index, cell in enumerate(originals)
        if cell is not None and cell.get("p_ge4") is not None
    ]
    pairs_b: list[tuple] = []
    stage_b: dict[int, list] = {}
    for index in live:
        pool = [cell for cell in stage_a[index] if adoptable(cell)]
        widest = (min(pool, key=rank) if pool else originals[index])["framing"]
        stage_b[index] = []
        pairs_b += [(rows[index], framing) for framing in recentres(rows[index], widest)]

    log(f"[refine] stage B: recentring {len(live)} location(s) at the width the ladder chose")
    moved = screen(pairs_b, directory, log) if pairs_b else []
    read(moved, [row["family"] for row, _ in pairs_b], scorer, directory)
    for position, cell in enumerate(moved):
        stage_b[live[position // len(AXES)]].append(cell)

    seconds = time.monotonic() - started
    share = seconds / len(rows)
    out = []
    for index, row in enumerate(rows):
        original = originals[index]
        cells = [*stage_a[index], *stage_b.get(index, [])]
        best, refusal = None, UNSCANNABLE
        if original is not None and original.get("p_ge4") is not None:
            best, refusal = decide(
                original, [cell for cell in cells if not cell["framing"].unmoved], margin
            )
            if refusal is None:
                _assert_monotone(row, original, best)
        record = _record(row, original, best, refusal, margin, share, len(cells))
        record["sidecar"] = _sidecar(row, scores)
        out.append(record)
    adopted = sum(1 for record in out if record["adopted"])
    log(
        f"[refine] {adopted}/{len(out)} location(s) adopted a new framing at margin {margin:g}, "
        f"{len(rungs) + len(moved)} frame(s) in {seconds:.1f}s"
    )
    return out


def _assert_monotone(row: dict, original: dict, best: dict) -> None:
    """The claim the maker's caller made, kept: an adopted framing never reads lower."""
    if rank(best) <= rank(original):
        return
    raise MonotonicityViolated(
        f"the framing adopted for {row.get('key')} reads BELOW the one it replaces: "
        f"P(>=4) {best['p_ge4']!r} / P(>=3) {best['p_ge3']!r} against the original's "
        f"{original['p_ge4']!r} / {original['p_ge3']!r}. The window contains the original and "
        f"the margin is strict, so this cannot happen unless the arithmetic is wrong — and "
        f"every attempt the pass renders after it would be framed on the result."
    )


def _sidecar(row: dict, scores) -> dict | None:
    """What the supply sidecar already says about this location, for comparison only.

    The sidecar's reading of the `x1.0` frame and the scan's are the same picture
    if the two render paths agree, and this is the field that lets a pass say
    whether they did rather than assume it.
    """
    if not scores:
        return None
    read_ = scores.get(str(row["key"]))
    if not read_:
        return None
    return {
        "regime": read_.get("regime"),
        "head_sha256": read_.get("head_sha256"),
        "p_ge4": read_.get("p_ge4"),
        "p_ge3": read_.get("p_ge3"),
    }


# --------------------------------------------------------------------------- #
# What a refinement leaves on the rows it moves.
# --------------------------------------------------------------------------- #
def block(record: dict, used: str) -> dict:
    """The provenance block an attempt row and a gallery row carry.

    Both viewports and both scores on the row, because the whole point of the
    step is that a reader can see what the frame was before and disagree. `used`
    says which of the two THIS row was rendered at, which is the one thing the
    two viewports do not answer between them — the fallback leg renders the
    original framing of a location whose refinement was adopted.
    """
    return {
        "adopted": bool(record["adopted"]),
        "used": used,
        "margin": record["margin"],
        "gain": record["gain"],
        "width_scale": record["width_scale"],
        "dx": record["dx"],
        "dy": record["dy"],
        "refused": record["refused"],
        "original": _thin(record["original"]),
        "refined": _thin(record["best"]) if record["adopted"] else None,
    }


def _thin(side: dict | None) -> dict | None:
    """One side of the block: the frame and its two scores, without the picture."""
    if side is None:
        return None
    return {
        "viewport": side["viewport"],
        "maxiter": side.get("maxiter"),
        "p_ge4": side.get("p_ge4"),
        "p_ge3": side.get("p_ge3"),
    }


def apply_to(row: dict, record: dict) -> dict:
    """The colorizer's row, re-framed. The original row where nothing was adopted.

    The **key is untouched**, and that is the whole of the identity rule: this is
    the same location, rendered somewhere else inside itself.
    """
    if not record["adopted"]:
        return row
    return {
        **row,
        "viewport": record["best"]["viewport"],
        "maxiter": record["best"]["maxiter"],
    }


# --------------------------------------------------------------------------- #
# The price, and the log it is read off.
# --------------------------------------------------------------------------- #
def log_path(directory: Path) -> Path:
    """Where a pass keeps every refinement it decided. Untracked, resumable."""
    return Path(directory) / "framings.jsonl"


def completed(path: Path, log=print) -> dict:
    """`{key: record}` for every refinement already decided, a torn tail dropped.

    The same repair [`curation.run.completed_attempts`] takes and for the same
    reason: a leg killed mid-append leaves a partial line, and the next append
    would land on it and make one unparseable row out of two.
    """
    path = Path(path)
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    out, kept, torn = {}, [], 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            torn += 1
            continue
        out[str(row["key"])] = row
        kept.append(line)
    if torn or (text and not text.endswith("\n")):
        log(f"[resume] repairing {path.name}: {torn} torn row(s) dropped, {len(kept)} kept")
        path.write_text("".join(line + "\n" for line in kept), encoding="utf-8", newline="\n")
    return out


def append(path: Path, record: dict) -> None:
    """One refinement onto the log. The write that makes a location's framing decided."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def quantiles(values: list[float]) -> dict | None:
    """The five numbers a distribution is read by, plus the mean. `None` on nothing."""
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None

    def at(share: float) -> float:
        return round(ordered[min(len(ordered) - 1, int(share * (len(ordered) - 1) + 0.5))], 6)

    return {
        "n": len(ordered),
        "min": round(ordered[0], 6),
        "q25": at(0.25),
        "median": at(0.5),
        "q75": at(0.75),
        "max": round(ordered[-1], 6),
        "mean": round(sum(ordered) / len(ordered), 6),
    }


def price(records: list[dict]) -> dict:
    """What the leg cost and what it bought, as the pass record carries it.

    Everything here is an aggregate on purpose. The per-location detail is a row
    per location in [`log_path`], under the regenerable tree with the attempts,
    because the pass record is tracked and a block that grew with `n x m`
    locations is the shape that put a pass record against the history's size
    guard once already.
    """
    if not records:
        return {"locations": 0}
    adopted = [record for record in records if record["adopted"]]
    refusals: dict[str, int] = {}
    widths: dict[str, int] = {}
    moves: dict[str, int] = {}
    for record in records:
        if record["refused"]:
            refusals[record["refused"]] = refusals.get(record["refused"], 0) + 1
    for record in adopted:
        name = f"{record['width_scale']:g}"
        widths[name] = widths.get(name, 0) + 1
        move = record["slug"].split("_")[-1]
        moves[move] = moves.get(move, 0) + 1
    seconds = sum(record["seconds"] for record in records)
    frames = sum(record["scanned"] for record in records)
    gains = [record["gain"] for record in records if record["gain"] is not None]
    return {
        "locations": len(records),
        "frames": frames,
        "seconds": round(seconds, 1),
        "seconds_per_location": round(seconds / len(records), 2),
        "seconds_per_frame": round(seconds / frames, 3) if frames else None,
        "margin": records[0]["margin"],
        "adopted": len(adopted),
        # THE number the whole step is priced by: how often the window found
        # something the margin agreed was better.
        "adopted_share": round(len(adopted) / len(records), 4),
        "refused": dict(sorted(refusals.items())),
        "chosen_width": dict(sorted(widths.items())),
        "chosen_move": dict(sorted(moves.items())),
        # Over every location, including the ones that kept their framing — a
        # distribution over the adopted alone is a distribution conditioned on
        # the decision it is meant to calibrate.
        # In nats, which is what the margin acts on, and in probability beside it.
        "gain": quantiles(gains),
        "gain_adopted": quantiles(
            [record["gain"] for record in adopted if record["gain"] is not None]
        ),
        "gain_p_ge4": quantiles(
            [record["gain_p_ge4"] for record in records if record.get("gain_p_ge4") is not None]
        ),
        "sidecar_agreement": _agreement(records),
    }


def _agreement(records: list[dict]) -> dict:
    """The scan's read of the `x1.0` frame against the sidecar's, over the leg.

    The evidence for or against [`SCAN_THE_ORIGINAL`]. The two are the same
    picture if `engine.screen` and the location view render identically at this
    regime, which is the identity a walk already relies on — measured here rather
    than inherited.
    """
    pairs = [
        (record["original"]["p_ge4"], record["sidecar"]["p_ge4"])
        for record in records
        if record.get("sidecar")
        and record.get("original")
        and record["original"].get("p_ge4") is not None
        and record["sidecar"].get("p_ge4") is not None
    ]
    if not pairs:
        return {"compared": 0}
    deltas = [abs(scan - stored) for scan, stored in pairs]
    return {
        "compared": len(pairs),
        "exact": sum(1 for delta in deltas if delta == 0.0),
        "max_abs_delta_p_ge4": round(max(deltas), 8),
        "mean_abs_delta_p_ge4": round(sum(deltas) / len(deltas), 8),
    }


__all__ = [
    "AXES",
    "BATCH",
    "BELOW_MARGIN",
    "MARGIN",
    "NO_CANDIDATE",
    "RECENTRE",
    "SCAN_THE_ORIGINAL",
    "SCHEMA",
    "UNSCANNABLE",
    "WIDTH_LADDER",
    "Framing",
    "MonotonicityViolated",
    "EPSILON",
    "adoptable",
    "append",
    "apply_to",
    "aspect",
    "block",
    "completed",
    "decide",
    "gain_of",
    "ladder",
    "logit",
    "log_path",
    "price",
    "quantiles",
    "rank",
    "read",
    "recentres",
    "refine",
    "screen",
    "viewport_at",
    "window",
]
