"""Reframing operators: minibrot moves, as moves rather than as a source.

Seven attempts settled what a minibrot is good for. Every source of them that
was rated viable turned out to be *downstream of a walk*, and every source that
enumerated them from first principles was dead. The measurement that closed it
looked at auto-framed yield one scale per atom and found almost nothing — and
its correction of record is that a minibrot's value is **as a marker of an
interesting, dense region, not as a window that is itself worth shipping**, with
scale the axis that was never varied.

So the operators here are **triggered**, never a source. Each one takes a view
the walk already found and returns a different view of the same neighbourhood:

```text
snap_to_nucleus       probe the view's center → Newton → recenter on the nucleus
lateral_to_sibling    step to a nearby nucleus at comparable scale
expand_neighborhood   enumerate several nearby nuclei at any smaller scale
```

That single decision — operator, not source — fixes everything else. It is why
they need a reserved slot rather than a score (nothing has ever been trained on
the views they produce, so on score alone they are rejected by default and the
material to train the next scorer never gets made). It is why they inherit the
root of whatever triggered them and burn its budget. And it is why **"not
available" has to be a first-class, frequent, named answer**: Newton convergence
on a blind probe runs at a small fraction, and a caller that treats absence as
an error will spend its life handling it.

Two refusals here are geometry rather than taste:

* **A snap must not be a teleport.** The nucleus has to land inside the frame
  being reframed. Otherwise the operator has not reframed *this* view; it has
  jumped to a different one, and the quality it was supposed to inherit is not
  the quality of the place it landed.
* **The `f64` wall is checked before rendering, not after.** A framing whose
  pixel spacing at the walk's own node width would quantize is refused with no
  render attempted, from the atom instrument's a-priori figure.

Nothing here renders, scores, or decides priority. It returns a geometry and its
provenance; what to do with that is the walk's business.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any

import mpmath as mp

from fractal_wallpapers.discovery import nucleus as nuc

#: Ceiling on the atom-domain orbit scan that ranks candidate periods.
MAX_PERIOD = 64

#: Argmins kept per probe; the Newton budget is three times this, since each
#: contributes its divisors.
KEEP_PERIODS = 4

#: The nucleus must land within this many frame widths of the view's center.
SNAP_MAX_WIDTH_MULTIPLE = 1.0

#: The framings a snap emits, in atom sizes. `None` keeps the view's own width.
#:
#: `4` is the "is this atom any good?" frame — the smallest framing that is not
#: mostly the atom's own black body. `16` is in the set because it is the
#: framing worth *labeling*: it is often close to a usable wallpaper by itself,
#: which is the material the corpus actually wants. There is deliberately no
#: small framing, because framing *into* an atom is solid black.
FRAMINGS: tuple[float | None, ...] = (None, 4.0, 16.0)

#: Never reframe wider than a whole-set view. Anything wider is not a reframing
#: of this neighbourhood, it is a different search.
MAX_WIDTH = 3.0

#: The walk's node presentation width, which sets where the `f64` wall is.
NODE_WIDTH = 384

#: Decades of headroom a framing needs above the spacing wall at [`NODE_WIDTH`].
WALL_MARGIN_DECADES = 0.5

#: Sibling probe radii, in units of the parent atom's own window scale.
#:
#: Measured in the parent's scale, so "nearby" means the same thing around a
#: shallow atom and a deep one. A flat radius finds nothing around a deep parent.
PROBE_RADII = (2.0, 8.0, 32.0)

#: Probe seeds a lateral call draws before giving up.
LATERAL_PROBES = 3

#: The period ceiling around a parent is this multiple of the parent's period …
PERIOD_HEADROOM = 3.0
#: … capped here. A flat ceiling silently finds nothing around deep parents.
PERIOD_CAP = 120

#: Periods always swept exactly, below which the atom-domain ranking is weakest.
#:
#: The split is not arbitrary in either direction. The head is where a probe
#: seed sits inside many low-period atom domains at once and "smallest period
#: wins" is the rule that stops the probe handing back the parent itself — so
#: ranking there loses real availability. The tail is where a deep atom has one
#: sharp minimum and the ranking is at its strongest, and it is also where all
#: the cost is. Sweep the cheap head exactly, rank the expensive tail.
LOW_SWEEP = 16

#: "Comparable scale", in decades, for a lateral step. Wider than this and the
#: candidate is not a sibling; it is a different rung.
SCALE_TOLERANCE_DECADES = 1.0

#: Distinct nuclei one neighbourhood enumeration may return.
NEIGHBOURS_FOUND = 8

#: Probes one neighbourhood enumeration may spend.
#:
#: **This is the bound that actually binds, and the found-count is not.** The
#: source project's one standalone run of this mechanism spent 360 probes and
#: got 22 atoms, because 88% of probes returned the parent itself: a seed a few
#: window scales from a nucleus is still inside that nucleus's *atom domain*,
#: which is far larger than the atom. A budget expressed as "find `m`" is an
#: unbounded budget at that miss rate.
NEIGHBOUR_PROBES = 12

#: A neighbour this many decades *larger* than the parent is an ancestor.
#:
#: The window is one-sided on purpose — unbounded below, bounded above. A child
#: two rungs down the period ladder is a legitimate neighbour; a period-2 giant
#: is not, and framing one proposes a near-whole-set view the walk's own roots
#: already cover.
NEIGHBOUR_SCALE_UP_DECADES = 1.0


@dataclass
class Reframing:
    """One operator application. `available = False` is the normal outcome."""

    operator: str
    available: bool
    #: Why not, when not. Empty when available.
    reason: str = ""
    #: The framing, in atom sizes. `None` preserves the parent's width.
    framing: float | None = None
    center_re: str | None = None
    center_im: str | None = None
    width: float | None = None
    #: The atom this is a reframing of.
    key: str | None = None
    period: int | None = None
    log10_abs_A: float | None = None
    window_scale: float | None = None
    #: Headroom, in decades, at the walk's node width.
    node_margin_decades: float | None = None
    #: Headroom at the finished-wallpaper presentation.
    deploy_margin_decades: float | None = None
    parent_node_id: int | None = None
    parent_center_re: str | None = None
    parent_center_im: str | None = None
    parent_width: float | None = None
    newton_solves: int = 0
    extra: dict = field(default_factory=dict)


def _unavailable(operator: str, reason: str, view: dict, solves: int = 0, framing=None, **extra):
    # The framing rides the unavailable path too. Two of the refusals are
    # framing-dependent by construction, so stamping them all as "no framing"
    # would pile exactly the interesting ones into one unreadable bucket.
    return Reframing(
        operator=operator,
        available=False,
        reason=reason,
        framing=None if framing is None else float(framing),
        parent_node_id=view.get("node_id"),
        parent_center_re=str(view["center_re"]),
        parent_center_im=str(view["center_im"]),
        parent_width=float(view["width"]),
        newton_solves=solves,
        extra=extra,
    )


def wall_margin_decades(width: float, pixels: int = NODE_WIDTH) -> float:
    """Decades of headroom before a `width`-wide frame at `pixels` quantizes."""
    if width <= 0:
        return -math.inf
    return math.log10(width / pixels) - math.log10(nuc.SPACING_FLOOR)


def _frame_for(record: dict, framing, parent_width: float, max_width: float):
    """`(width, refusal)` for a view on this atom under this framing."""
    width = float(parent_width) if framing is None else float(framing) * record["window_scale"]
    if not (width > 0.0) or not math.isfinite(width):
        return None, "bad_width"
    if width > max_width:
        return None, "width_over_root_scale"
    if wall_margin_decades(width) < WALL_MARGIN_DECADES:
        return None, "f64_spacing_wall"
    return width, None


def _available(operator, record, framing, width, view, solves, **extra) -> Reframing:
    return Reframing(
        operator=operator,
        available=True,
        framing=None if framing is None else float(framing),
        center_re=record["center_re"],
        center_im=record["center_im"],
        width=width,
        key=record["key"],
        period=record["period"],
        log10_abs_A=record["log10_abs_A"],
        window_scale=record["window_scale"],
        node_margin_decades=round(wall_margin_decades(width), 4),
        deploy_margin_decades=record["f64_margin_decades"],
        parent_node_id=view.get("node_id"),
        parent_center_re=str(view["center_re"]),
        parent_center_im=str(view["center_im"]),
        parent_width=float(view["width"]),
        newton_solves=solves,
        extra=extra,
    )


def _solve_at_center(view: dict, degree: int):
    """The Newton half of a snap: `(record, solves, refusal)`.

    Split out because **the nucleus does not depend on the framing.** A framing
    only chooses a width afterwards, so N framings of one view cost one solve,
    not N — which is what makes adding a framing a design choice rather than a
    cost one.
    """
    nuc.set_precision()
    center = mp.mpc(mp.mpf(str(view["center_re"])), mp.mpf(str(view["center_im"])))
    periods = nuc.period_candidates(center, degree, MAX_PERIOD, KEEP_PERIODS)
    if not periods:
        return None, 0, "orbit_escaped_immediately"

    near = mp.mpf(str(SNAP_MAX_WIDTH_MULTIPLE * float(view["width"])))
    solves = 0
    refusal = "no_converge"
    for period in periods:
        solves += 1
        solve = nuc.newton_nucleus(center, period, degree=degree)
        if not solve.converged:
            refusal = "no_converge"
            continue
        if abs(solve.c - center) > near:
            refusal = "nucleus_outside_frame"
            continue
        record = nuc.make_atom(solve.c, period, degree)
        if record is None:
            refusal = "degenerate_or_not_minimal"
            continue
        record["seed_distance"] = float(abs(solve.c - center))
        return record, solves, ""
    return None, solves, refusal


def snap_to_nucleus(
    view: dict,
    *,
    degree: int = 2,
    framings=FRAMINGS,
    max_width: float = MAX_WIDTH,
) -> list[Reframing]:
    """Recenter a view on the nucleus its center sits on, at each framing.

    `view` is `{center_re, center_im, width, node_id}` with the coordinates as
    decimal strings. One probe, one Newton pass, one [`Reframing`] per framing —
    and the solves are charged to the first row only, so summing them over the
    returned rows is the true cost of the call rather than N copies of one solve.

    The framing verdict stays per-framing: one solve, several answers. A shallow
    atom can take the 4× frame and refuse the 16× one off the same nucleus.
    """
    framings = list(framings) or [None]
    record, solves, refusal = _solve_at_center(view, degree)
    parent_width = float(view["width"])

    rows: list[Reframing] = []
    for index, framing in enumerate(framings):
        charged = solves if index == 0 else 0
        shared: dict[str, Any] = {} if index == 0 else {"reused_solve": True}
        if record is None:
            rows.append(_unavailable("snap_to_nucleus", refusal, view, charged, framing, **shared))
            continue
        width, why = _frame_for(record, framing, parent_width, max_width)
        if width is None:
            rows.append(
                _unavailable(
                    "snap_to_nucleus",
                    why,
                    view,
                    charged,
                    framing,
                    period=record["period"],
                    window_scale=record["window_scale"],
                    **shared,
                )
            )
            continue
        rows.append(
            _available(
                "snap_to_nucleus",
                record,
                framing,
                width,
                view,
                charged,
                seed_distance=record.get("seed_distance"),
                degree=degree,
                **shared,
            )
        )
    return rows


def _probe_seed(rng: random.Random, parent_scale: float, center_re, center_im):
    """One neighbourhood probe seed, and its radius in the plane."""
    radius = PROBE_RADII[rng.randrange(len(PROBE_RADII))] * parent_scale
    angle = rng.random() * 2.0 * math.pi
    seed = mp.mpc(
        center_re + mp.mpf(radius * math.cos(angle)),
        center_im + mp.mpf(radius * math.sin(angle)),
    )
    return seed, radius


def _hybrid_periods(seed, degree: int, period_max: int) -> list[int]:
    """The cheap head swept exactly, the expensive tail ranked."""
    ranked = set(nuc.period_candidates(seed, degree, period_max, KEEP_PERIODS))
    return sorted(ranked | set(range(2, min(LOW_SWEEP, period_max) + 1)))


def _period_ceiling(parent_period: int) -> int:
    return min(PERIOD_CAP, max(24, int(PERIOD_HEADROOM * int(parent_period))))


def _parent_atom(view: dict, degree: int, parent: dict | None):
    """The atom a neighbourhood is measured around: given, or solved for."""
    if parent is not None:
        return parent, 0, ""
    rows = snap_to_nucleus(view, degree=degree, framings=[None])
    snap = rows[0]
    if not snap.available:
        return None, snap.newton_solves, "no_parent_atom:" + snap.reason
    return (
        {
            "key": snap.key,
            "center_re": snap.center_re,
            "center_im": snap.center_im,
            "period": snap.period,
            "window_scale": snap.window_scale,
        },
        snap.newton_solves,
        "",
    )


def lateral_to_sibling(
    view: dict,
    rng: random.Random,
    *,
    degree: int = 2,
    framing: float | None = None,
    parent: dict | None = None,
    max_width: float = MAX_WIDTH,
) -> Reframing:
    """Step to a nearby nucleus at comparable scale.

    Needs a parent atom first — pass one from a snap that already fired at this
    node, or the call solves for its own. "Comparable scale" is enforced: a
    candidate whose window scale differs from the parent's by more than a decade
    is not a sibling, it is a different rung of the same neighbourhood, and
    [`expand_neighborhood`] is the operator that wants those.
    """
    nuc.set_precision()
    width = float(view["width"])
    parent, solves, refusal = _parent_atom(view, degree, parent)
    if parent is None:
        return _unavailable("lateral_to_sibling", refusal, view, solves, framing)

    parent_scale = float(parent["window_scale"])
    center_re = mp.mpf(str(parent["center_re"]))
    center_im = mp.mpf(str(parent["center_im"]))
    period_max = _period_ceiling(parent["period"])
    tried, refusal = 0, "no_sibling_found"

    for _ in range(max(1, LATERAL_PROBES)):
        seed, radius = _probe_seed(rng, parent_scale, center_re, center_im)
        tried += 1
        periods = _hybrid_periods(seed, degree, period_max)
        if not periods:
            refusal = "orbit_escaped_immediately"
            continue
        solves += len(periods)
        record, status = nuc.identify_nucleus(seed, degree=degree, near=radius * 4, periods=periods)
        if record is None:
            refusal = status
            continue
        if record["key"] == parent["key"]:
            refusal = "hit_parent"
            continue
        sibling_scale = float(record["window_scale"])
        if (
            sibling_scale <= 0
            or abs(math.log10(sibling_scale / parent_scale)) > SCALE_TOLERANCE_DECADES
        ):
            refusal = "scale_mismatch"
            continue
        frame, why = _frame_for(record, framing, width, max_width)
        if frame is None:
            refusal = why
            continue
        return _available(
            "lateral_to_sibling",
            record,
            framing,
            frame,
            view,
            solves,
            parent_key=parent["key"],
            parent_period=int(parent["period"]),
            probes_tried=tried,
            scale_ratio_decades=round(math.log10(sibling_scale / parent_scale), 4),
            degree=degree,
        )

    return _unavailable(
        "lateral_to_sibling",
        refusal,
        view,
        solves,
        framing,
        probes_tried=tried,
        parent_key=parent["key"],
    )


def expand_neighborhood(
    view: dict,
    rng: random.Random,
    *,
    degree: int = 2,
    framings=FRAMINGS,
    parent: dict | None = None,
    found_max: int = NEIGHBOURS_FOUND,
    probe_max: int = NEIGHBOUR_PROBES,
    max_width: float = MAX_WIDTH,
) -> list[Reframing]:
    """Enumerate distinct nearby nuclei, at comparable *or smaller* scale.

    The same disc as [`lateral_to_sibling`] — the radii and the period ceiling
    are the parent's, for the same reason — with one difference, and the
    difference *is* the operator: the scale window here is **one-sided**.
    Unbounded below, so a child several rungs down the ladder is a legitimate
    neighbour; bounded above, so a giant that swallows the parent is refused as
    an ancestor.

    It enumerates and selects nothing. Which of the candidates to propose is a
    question about pictures, and the caller is where pictures are looked at.

    Always returns at least one row: an exhausted neighbourhood is one
    unavailable [`Reframing`] with a named reason, never an empty list — because
    an empty list and "the disc kept handing back the parent" are different
    facts, and only one of them means "stop trying here".
    """
    nuc.set_precision()
    width = float(view["width"])
    framings = list(framings) or [None]
    parent, solves, refusal = _parent_atom(view, degree, parent)
    if parent is None:
        return [_unavailable("expand_neighborhood", refusal, view, solves)]

    parent_scale = float(parent["window_scale"])
    center_re = mp.mpf(str(parent["center_re"]))
    center_im = mp.mpf(str(parent["center_im"]))
    period_max = _period_ceiling(parent["period"])

    found: list[dict] = []
    seen = {parent["key"]}
    tried, refusal = 0, "no_neighbour_found"
    refusals: dict[str, int] = {}

    def note(reason: str) -> str:
        refusals[reason] = refusals.get(reason, 0) + 1
        return reason

    for _ in range(max(1, int(probe_max))):
        if len(found) >= int(found_max):
            break
        seed, radius = _probe_seed(rng, parent_scale, center_re, center_im)
        tried += 1
        periods = _hybrid_periods(seed, degree, period_max)
        if not periods:
            refusal = note("orbit_escaped_immediately")
            continue
        solves += len(periods)
        record, status = nuc.identify_nucleus(seed, degree=degree, near=radius * 4, periods=periods)
        if record is None:
            refusal = note(status)
            continue
        if record["key"] in seen:
            # "It handed back the parent" and "the disc is out of distinct
            # nuclei" are different constraints, and the first is the 88% case.
            refusal = note(
                "hit_parent" if record["key"] == parent["key"] else "duplicate_neighbour"
            )
            continue
        scale = float(record["window_scale"])
        if (
            scale > 0
            and parent_scale > 0
            and math.log10(scale / parent_scale) > NEIGHBOUR_SCALE_UP_DECADES
        ):
            refusal = note("scale_too_large")
            continue
        seen.add(record["key"])
        found.append(record)

    if not found:
        return [
            _unavailable(
                "expand_neighborhood",
                refusal,
                view,
                solves,
                probes_tried=tried,
                probe_refusals=refusals,
                parent_key=parent["key"],
            )
        ]

    rows: list[Reframing] = []
    for rank, record in enumerate(found):
        scale = float(record["window_scale"])
        for framing in framings:
            first = not rows
            charged = solves if first else 0
            shared: dict[str, Any] = {} if first else {"reused_solve": True}
            frame, why = _frame_for(record, framing, width, max_width)
            if frame is None:
                rows.append(
                    _unavailable(
                        "expand_neighborhood",
                        why,
                        view,
                        charged,
                        framing,
                        period=record["period"],
                        window_scale=scale,
                        found_rank=rank,
                        **shared,
                    )
                )
                continue
            rows.append(
                _available(
                    "expand_neighborhood",
                    record,
                    framing,
                    frame,
                    view,
                    charged,
                    parent_key=parent["key"],
                    parent_period=int(parent["period"]),
                    probes_tried=tried,
                    found_rank=rank,
                    found_count=len(found),
                    scale_ratio_decades=(
                        round(math.log10(scale / parent_scale), 4)
                        if scale > 0 and parent_scale > 0
                        else None
                    ),
                    degree=degree,
                    **({"probe_refusals": refusals} if first and refusals else {}),
                    **shared,
                )
            )
    return rows


class ProbeGovernor:
    """Bounds how often the probe fires, two ways at once.

    **A probability is used here, and it is a cost governor rather than a
    selection rule.** Which reframing gets expanded is a reserved slot on the
    frontier, decided by the walk; this coin only decides how often the *probe*
    is paid for, and the probe is an enumeration whose cost is a large multiple
    of a screening render's.

    The region cache is the half that matters more. A view is quantized to a
    coarse cell, and a cell that has been probed is skipped whatever the coin
    says — because siblings in a hot lineage all sit in one cell, and probing
    them re-derives the same nucleus at full price. The cache beats the coin.
    """

    def __init__(self, probability: float, rng: random.Random, cell_widths: float = 4.0):
        self.probability = float(probability)
        self.rng = rng
        #: Cell side, in units of the view's own width — so the grid is as
        #: coarse or as fine as the scale being searched.
        self.cell_widths = float(cell_widths)
        self.seen: set[str] = set()
        self.rolled = self.fired = self.coin_skipped = self.cache_skipped = 0

    def cell(self, degree: int, center_re, center_im, width) -> str:
        width = float(width)
        side = width * self.cell_widths
        return (
            f"{degree}|{math.floor(float(center_re) / side)}"
            f"|{math.floor(float(center_im) / side)}|{round(math.log10(width), 1)}"
        )

    def should_probe(self, degree: int, center_re, center_im, width) -> tuple[bool, str]:
        self.rolled += 1
        cell = self.cell(degree, center_re, center_im, width)
        if cell in self.seen:
            self.cache_skipped += 1
            return False, "region_cached"
        if self.probability < 1.0 and self.rng.random() >= self.probability:
            self.coin_skipped += 1
            return False, "cost_governor"
        self.seen.add(cell)
        self.fired += 1
        return True, ""

    def tally(self) -> dict:
        return {
            "rolled": self.rolled,
            "fired": self.fired,
            "coin_skipped": self.coin_skipped,
            "cache_skipped": self.cache_skipped,
        }


#: Multibrot degree per c-plane family. The dynamical families are absent, and
#: that absence is the rule: a Julia or Phoenix viewport is a *z*-plane point,
#: which has no nucleus in the parameter-plane sense at all. The operators are
#: not defined there and are skipped rather than faked.
PARAMETER_PLANE_DEGREE = {
    "mandelbrot": 2,
    "multibrot3": 3,
    "multibrot4": 4,
    "multibrot5": 5,
}


def degree_of(family: str, degree: int = 2) -> int | None:
    """The multibrot degree of a c-plane family, or `None` where reframing is
    undefined."""
    if family == "mandelbrot":
        return 2
    if family == "multibrot":
        return degree if degree in (3, 4, 5) else None
    return None
