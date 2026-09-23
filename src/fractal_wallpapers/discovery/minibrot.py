"""Is there a minibrot in this frame, and how big is it against the frame.

A *minibrot descent* is the move a person means when they say a zoom "went into a
minibrot and came out with a picture": the frame ends up holding a small copy of
the whole set, big enough to see and small enough not to be solid black. This
module makes that question a number, over frames this project already has, and it
answers it the way [`discovery.operators`] already answers it for a reframing —
[`discovery.nucleus`]' Newton and its atom instrument, no second nucleus finder.

## Three readings, and the two that are kept

**(a) The frame holds an atom of comparable size** — [`probe`]. Solve for the
nucleus the frame's centre sits on, measure the atom's linear scale `1/|A|`, and
ask what the frame's width is in atom sizes. A copy seen from *outside*: it is a
property of the frame and of nothing else, so two rows at one place answer
identically and a frame that arrived by hand, by a reframing or by ten rungs of a
walk all get the same reading.

**(b) The row descended far below its root** — [`descent`]. Join the pool row
back to the walk ledger that found it, take the node's `depth` and the decades
between its width and its root's. This is a property of the *route*, and three
things are wrong with it as a census criterion: **25,172 of the pool's 55,884
locations join to no walk row at all** ([`descent`] returns `None` for them, and
a reframing's own view is one of them by construction), the same frame reached
twice reads twice, and descending is what a walk does — at *depth ≥ 5 and two
decades below the root*, **8,935 of the 30,712** joinable locations clear it.

**(c) The frame is decoration OF a copy** — [`enclosing`]. The same copy seen
from *inside*: the frame sits within a small copy of the set that is very much
bigger than it is, which is what a tuned seahorse descent does by construction.
(a) and (c) are different questions and they mostly disagree; (c) is the one that
answers *how many frames are inside a minibrot's filigree*.

`minibrot_descent_census_ckpt140` censused (a); `minibrot_enclosed_census_ckpt140`
added (c) and censused it. Its subject row satisfies all three: a **period-1026**
nucleus 0.15 frame widths off centre and the frame **11.8** atom sizes wide for
(a), depth 6 and 1.88 decades below its root for (b), and **enclosed by the
period-27 satellite at a ratio of 754** for (c).

## What (c) is, and the two things the obvious reading gets wrong

The enclosing copy of a frame `(centre, w)` is a period `q > 1` whose nucleus
`n_q` sits within [`ENCLOSE_K`] of *its own* atom sizes of the centre and whose
atom is at least as big as the frame — `size_q ≥ w`, and `size_q / w` is the
ratio reported. The main body, `q = 1`, never counts.

**The candidates are the record minima of `|z_k|`, not the ranked periods (a)
uses.** Along the critical orbit at the centre, each `k` at which `|z_k|` sets a
new record low is a period whose copy contains the frame, and they arrive nested,
lowest first: at the named row the whole chain is `2, 27, 54, 1026`. That makes
(c) the cheap end of the scan — four Newton solves where (a) ranked 71 periods
and solved 24 — and it is a chain rather than a set, which is what the next
paragraph needs. Over all 1,200 `tuned129x_*` walk rows the chain holds the
descent's own satellite period every time.

**Lowest-period-wins alone answers `2` on every frame in seahorse valley, and a
bulb is not a copy.** The period-2 bulb's atom is 0.5 wide and its nucleus sits
about half of that from every tuned place, so it qualifies on distance at any
usable `K` while being eight decades too big to be what the frame decorates. It
is also not a minibrot: it is attached to the main body, so its decorations are
the main body's decorations, and the main body never counts. A first census pass
taken without this paragraph read **618 of 804** enclosed record seats as period
2 and another 140 as period 3.

So the chain is split into **generations** — a copy, and the bulbs hanging off
it — with the main body prepended to it as `period 1, size 1.0`. An entry is a
bulb of one above it in its generation when its period is a multiple `m` of that
one's and its size is within [`BULB_SLACK`] of [`bulb_scale`]; otherwise it
starts a new generation, which is to say it is a copy. **The enclosing copy is
the head of the last generation, and a frame whose only generation is the main
body's own is enclosed by nothing.** At the named row the generations are
`[1, 2]` and `[27, 54]`, so the answer is `27`.

## Why the period ceiling moves, and what makes that affordable

[`operators._solve_at_center`] sweeps to [`operators.MAX_PERIOD`] — 64 — which is
right for a walk deciding where to go next and **blind to every minibrot this
census is about**. The named row sits inside a period-27 satellite, so the atoms
in its frame have periods that are multiples of 27; the one that is there is
1026, sixteen times the ceiling. Raise the ceiling and the cost arrives with it:
Newton at period `p` walks a `p`-step orbit at 60 decimal digits, up to
[`nucleus.NEWTON_STEPS`] times.

So the ranked candidate periods are **screened before Newton, in `f64`, for
free**. `log|A| ≈ (d/(d−1)) · Σ log(d·|z_k|^(d−1))` over the critical orbit at the
frame's centre is one prefix sum over magnitudes the orbit scan already computed,
and a period whose atom cannot be anywhere near the frame's own scale never
reaches the solver. The approximation is loose — it read 8.37 against the true
9.96 at the named row's period 1026, because the frame's centre is not the
nucleus and `|z'_p|` is not `|Λ|` — so [`SCREEN_SLACK`] is three decades, twice
the worst error seen. Measured over 60 pool locations it cut the pass from
**158.2 s to 35.5 s** and changed **no** verdict: same 56 nuclei, same periods,
same ratios, and the worst single probe fell from 101.3 s to 13.3 s.

## What the census can and cannot be asked about

Only the parameter planes. A Julia or Phoenix view has no embedded copy of a
parameter-plane set to find and no nucleus to solve for, so [`PLANES`] is the
whole eligible population — 21,049 of the pool's 55,884 locations — and a caller
that hands in a dynamical partition gets `None` with the reason, never a zero.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from fractal_wallpapers.discovery import nucleus as nuc
from fractal_wallpapers.supply import partitions as partitions_module

#: Iterations of the `f64` critical orbit the period ranking is read off.
#:
#: The scan stops at escape, which is what happens at almost every frame; this is
#: the ceiling for a centre that is *interior* — inside the set or inside one of
#: its atoms — where the orbit never escapes and the ranking has to be cut
#: somewhere. It bounds the period this instrument can name, and 40,000 is four
#: times past anything the pool holds: over 27,578 probes the deepest atom named
#: was **period 9,966**.
ORBIT_CAP = 40_000

#: Argmins of `|z_k|` kept from the scan, each contributing its divisors.
#:
#: [`nucleus.period_candidates`]' own `keep`, raised from its 4. The reason is
#: this census's population rather than a disagreement: a frame inside a
#: period-`q` satellite has its whole minimum structure on multiples of `q`, so
#: the useful argmins are further down the sorted list than they are for the
#: shallow views an operator fires at.
KEEP_ARGMINS = 6

#: How far off centre the nucleus may land, in frame widths.
#:
#: [`operators.SNAP_MAX_WIDTH_MULTIPLE`], and deliberately the same number: a
#: nucleus further from the centre than the frame is wide was not in the picture,
#: which is the same claim a snap makes when it refuses `nucleus_outside_frame`.
NEAR_MULTIPLE = 1.0

#: The frame's width in atom sizes, below which the frame is *inside* the atom.
#:
#: Framing into an atom is solid black — [`operators.FRAMINGS`] says so and has no
#: small framing for the same reason — so a reading under this is not a minibrot
#: in a frame, it is a minibrot the frame is in. Counted and reported apart.
FRAME_MIN = 1.0

#: The frame's width in atom sizes, above which the atom is a speck.
#:
#: The project's own framings bracket it: [`nucleus.FRAME_MULTIPLE`] is 4, the
#: "is this atom any good" frame, and 16 is [`operators.FRAMINGS`]' "worth
#: labeling" one. 32 is one doubling past the larger of those, which keeps a
#: frame that holds the atom plus a ring of its decorations and drops one where
#: the atom is a thousandth of the picture's area. **The census reports the whole
#: ratio distribution**, so this cut is a line to move and never a reading to
#: re-take: `minibrot_descent_census_ckpt140` read **10,603** locations in band at
#: 32 against **13,939** at 64, over 27,578 probed.
FRAME_MAX = 32.0

#: Decades of slack the `f64` screen allows around the band above.
#:
#: Twice the worst error the approximation was measured at. See the module
#: docstring: it is loose by construction and the slack is what keeps it a
#: screen rather than a second, worse criterion.
SCREEN_SLACK = 3.0

#: Newton solves one probe may spend, whatever the screen leaves.
#:
#: A backstop and not the working bound — the screen is what makes the pass
#: affordable, and over the census **374 probes of 27,578** reached it — 1.4%, on
#: 197,254 Newton solves in all, which is 7.2 a probe. It is
#: here because a pathological centre can rank dozens of large periods that all
#: survive a three-decade screen, and one of those cost 101 s before the screen
#: existed.
MAX_SOLVES = 24

#: How far off centre an ENCLOSING copy's nucleus may sit, in *its own* atom
#: sizes. Criterion (c)'s one threshold.
#:
#: **2.0, the geometric extent of a copy**, Matt's ruling of 2026-09-22: a copy
#: spans `[-2, 0.25]` in its own coordinates, so 2.0 holds its whole filigree and
#: nothing a frame on the copy's antenna decorates is refused. The calibrated
#: reading below is [`TIGHT_ENCLOSE_K`] and stays documented as that — it is what
#: the deep rows of tuned descents read, not how far a copy reaches.
#:
#: The tight reading was calibrated on the 202 `tuned129x_*` pool places, which
#: are inside a period 22, 27, 33 or 35 satellite by construction and must read
#: enclosed by it. Their own
#: readings are **0.6414 to 0.8184**, median 0.7747 — a much tighter band than
#: anything else here. *The smallest K that reads ≥ 95% of them right*, which is
#: how `minibrot_enclosed_census_ckpt140` was told to pick it, gives **0.81 at
#: 96.5%**; one more hundredth reads **all 202**, so the hundredth is taken.
#:
#: ⚠ **The calibration set visits one part of a copy and this bound is the
#: distance to it.** A copy of the set spans `[-2, 0.25]` in its own coordinates
#: with the nucleus at the origin, so its filigree reaches **2.0** atom sizes out
#: and a frame on the copy's antenna is well past 0.82. That the 202 places land
#: in `0.64–0.82` is not a property of being inside a copy, it is a property of
#: how deep they are: the same four descents' own *root* frames, at 25.89 atom
#: sizes, read **1.216, 1.289, 1.290, 1.297** — one for one with their four
#: satellites, and every one of them outside this bound. A descent starts near
#: the copy's edge and works inward, and 0.82 is where it ended up. That is why
#: it is not the default.
#:
#: **Every census row carries `chain_table`**, the whole solved chain with each
#: entry's distance, so the cut is re-swept off the output — `discovery/README.md`'s
#: *Criterion (c)* has what the count does between 0.82 and 2.25. ⚠ A cut that
#: drops a copy but keeps its period doubling answers the **doubling**: those
#: four root frames read `q = 70, 44, 66, 54` at the tight reading, the copy in
#: each case being the entry that was cut, and `35, 22, 33, 27` here.
#:
#: It is not [`NEAR_MULTIPLE`] and must not be confused with it: that one is in
#: *frame* widths and bounds where (a)'s atom may be, this one is in *atom* sizes
#: and bounds how far outside a copy the frame may sit and still be its
#: decoration.
ENCLOSE_K = 2.0

#: The tight reading of [`ENCLOSE_K`]: the smallest cut that reads all 202 tuned
#: descent rows enclosed, which was the default until 2026-09-22. Kept as a named
#: cut so a census summary still reports the count at it.
TIGHT_ENCLOSE_K = 0.82

#: How far under [`bulb_scale`] a chain entry may sit and still be read as a bulb
#: of the copy above it rather than as a copy of its own.
#:
#: The law is tight and the two populations are far apart. Measured against
#: `1.0` — the main body's own atom scale — the bulbs attached to it read
#: **0.98 to 1.40** of the law across all five planes and every `m` from 2 to 11,
#: while degree 2's primitive minibrots on the real antenna read **0.099** of it
#: at period 3 and fall away from there: 0.016 at 4, 0.020 at 5, 0.0042 at 6,
#: 1.1e-5 at 7. A third of the law is between the two with a factor of three to
#: spare on the near side, which is period 3, the largest primitive there is.
BULB_SLACK = 3.0

#: Newton solves one enclosing read may spend. A backstop, like [`MAX_SOLVES`]:
#: the screened chain is 2 to 8 entries on everything measured here.
ENCLOSE_MAX_SOLVES = 12

#: The partitions this instrument can be asked about at all: the parameter
#: planes, where a small copy of the set is a thing that exists.
PLANES = partitions_module.PARAMETER_PLANES

#: What a probe over a dynamical partition is refused with.
NOT_A_PLANE = "not a parameter plane: a julia or phoenix view has no embedded copy"

#: What a probe whose orbit escapes at once is refused with.
ESCAPED = "orbit_escaped_immediately"

#: What a probe that solved nothing near its centre is refused with. Spelled the
#: way [`operators._solve_at_center`] spells it, because it is the same refusal.
OUTSIDE = "nucleus_outside_frame"

#: What an enclosing read that found no copy around the frame is refused with.
NOT_ENCLOSED = "no_enclosing_copy"

#: Where `minibrots examples` writes the example set, under the hot tier.
#:
#: **Untracked, and that is the decision**: at the widest cut the set is 2,709
#: places and a row that carries a place key, a link and the solved chain is about
#: 650 bytes, so the file is 1.7 MiB against [`test_history_purity`]'s 1 MiB — and
#: widening that list is not a thing a prompt does. It is regenerable from a census
#: output by one command, the command is tracked, and Matt's ruling of 2026-09-22
#: is that an example set is an artifact and not a record.
EXAMPLES_NAME = "minibrot_examples.jsonl"


def degree_of(partition: str) -> int | None:
    """The degree a partition's frames iterate at, or `None` if it has no atoms."""
    if partition not in PLANES:
        return None
    return partitions_module.degree_of_plane(partition)


def examples_path():
    """Where the example set lands: `<hot>/discovery/`[`EXAMPLES_NAME`]."""
    from fractal_wallpapers.paths import hot_root

    return hot_root() / "discovery" / EXAMPLES_NAME


def read_examples(path=None) -> tuple[dict, list[dict]]:
    """`(the summary row, every row after it)`, or `({}, [])` where nothing is written.

    Empty rather than raising, because the caller that matters is a writeup asking
    what the census found: a missing file means nobody has run `minibrots examples`
    on this box, which is a thing to say in one line and not a traceback.
    """
    where = Path(examples_path() if path is None else path)
    if not where.is_file():
        return {}, []
    rows = [
        json.loads(line) for line in where.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if not rows or "summary" not in rows[0]:
        return {}, rows
    return rows[0], rows[1:]


def enclosing_at(row: dict, k: float, *, bulb_slack: float = BULB_SLACK):
    """[`enclosing`]'s verdict re-read off a census row's `chain_table`, at cut `k`.

    **No Newton and no orbit pass**: every candidate was solved when the census ran
    and its distance recorded, so moving the cut is arithmetic over rows that are
    already on disk. `None` where the frame's only generation is the main body's.

    Returns `(the enclosing copy, the generations, every solved entry)`, each entry
    a dict with `period`, `window_scale` and `distance_atoms` — [`generations`]'
    shape, so the two agree by construction rather than by a second spelling of the
    rule.
    """
    degree = degree_of(row["partition"]) or 2
    width = float(row["width"])
    solved = [
        {"period": int(period), "window_scale": ratio * width, "distance_atoms": float(atoms)}
        for period, atoms, ratio in (row.get("chain_table") or [])
    ]
    held = [main_body(degree), *(one for one in solved if one["distance_atoms"] <= k)]
    groups = generations(held, degree, slack=bulb_slack)
    if groups[-1][0]["period"] == 1:
        return None
    return groups[-1][0], groups, solved


@dataclass
class Scan:
    """One `f64` pass over the critical orbit at a frame's centre."""

    #: Candidate periods, ascending: the divisors of the kept argmins.
    periods: list[int]
    #: `log₁₀ Π_{j≤k} (d·|z_j|^(d−1))`, indexed by `k`. The screen's whole input.
    prefix: list[float]
    #: The iteration the orbit escaped at, or [`ORBIT_CAP`] if it never did.
    escaped_at: int
    #: Every `k > 1` at which `|z_k|` set a new record low, ascending: criterion
    #: (c)'s candidates, and the nesting order of the copies around the frame.
    #: `k = 1` is dropped with the main body it stands for.
    chain: list[int] = field(default_factory=list)

    def approx_log10_abs_a(self, period: int, degree: int) -> float | None:
        """`log₁₀|A|` at `period`, off the prefix sum. Loose by decades; see above."""
        if period - 1 >= len(self.prefix):
            return None
        return (degree / (degree - 1)) * self.prefix[period - 1]


def scan(center_re, center_im, degree: int, *, cap: int = ORBIT_CAP, keep: int = KEEP_ARGMINS):
    """Rank the periods worth solving at a centre, and keep the screen's input.

    [`nucleus.period_candidates`]' argument, at this census's ceiling and without
    its truncation: that function keeps the twelve *smallest* divisors, which is
    right for an operator whose answer is a shallow atom and wrong here, where the
    atom that is actually in the frame is the largest divisor of the deepest
    argmin. The divisors are returned whole and the screen does the cutting.
    """
    point = complex(float(center_re), float(center_im))
    escape = 2.0 ** (1.0 / max(degree - 1, 1)) * 2.0
    z = complex(0.0, 0.0)
    seen: list[tuple[float, int]] = []
    prefix = [0.0]
    chain: list[int] = []
    record = math.inf
    step = 0
    for step in range(1, cap + 1):
        z = (z * z + point) if degree == 2 else (z**degree + point)
        magnitude = abs(z)
        if not math.isfinite(magnitude) or magnitude > escape:
            break
        seen.append((magnitude, step))
        if magnitude < record:
            record = magnitude
            if step > 1:
                chain.append(step)
        prefix.append(
            prefix[-1] + math.log10(degree) + (degree - 1) * math.log10(magnitude)
            if magnitude > 0
            else prefix[-1]
        )
    if not seen:
        return Scan([], prefix, step, chain)
    seen.sort()
    periods: set[int] = set()
    for _magnitude, multiple in seen[:keep]:
        periods.update(d for d in range(2, multiple + 1) if multiple % d == 0)
    return Scan(sorted(periods), prefix, step, chain)


def screened(held: Scan, width: float, degree: int, *, slack: float = SCREEN_SLACK) -> list[int]:
    """The candidate periods whose atom could be near the frame's own scale.

    `f64` and free: the band is [`FRAME_MIN`]–[`FRAME_MAX`] widened by `slack`
    decades either way, and the test is `log₁₀(width) + log₁₀|A|`, which is
    `log₁₀` of the frame's width in atom sizes.
    """
    low = math.log10(FRAME_MIN) - slack
    high = math.log10(FRAME_MAX) + slack
    if width <= 0:
        return []
    at = math.log10(width)
    kept = []
    for period in held.periods:
        approx = held.approx_log10_abs_a(period, degree)
        if approx is not None and low <= at + approx <= high:
            kept.append(period)
    return kept


def probe(
    center_re,
    center_im,
    width,
    degree: int,
    *,
    near_multiple: float = NEAR_MULTIPLE,
    max_solves: int = MAX_SOLVES,
    slack: float = SCREEN_SLACK,
    held: Scan | None = None,
) -> tuple[dict | None, dict]:
    """`(the atom this frame holds, what it cost)` — the census's one measurement.

    The atom record is [`nucleus.make_atom`]'s, with `seed_distance` beside it and
    two readings added: `frame_sizes`, the frame's width in atom sizes, and
    `in_frame`, whether that lands in the band. `None` with a reason where there
    is no atom to name.

    **Smallest period wins, among those the screen left** — [`nucleus`]' own rule,
    and it is the `near_multiple` bound that stops it handing back the parent: at
    the named row, period 27 and period 54 both converge to minimal nuclei and
    both are refused, at 582 and 193 frame widths off centre, before period 1026
    is reached at 0.15.
    """
    import mpmath as mp

    width = float(width)
    cost = {"solves": 0, "ranked": 0, "screened": 0, "escaped_at": 0}
    if held is None:
        held = scan(center_re, center_im, degree)
    cost["ranked"] = len(held.periods)
    cost["escaped_at"] = held.escaped_at
    if not held.periods:
        return None, {**cost, "refused": ESCAPED}
    periods = screened(held, width, degree, slack=slack)[:max_solves]
    cost["screened"] = len(periods)
    if not periods:
        return None, {**cost, "refused": OUTSIDE}

    nuc.set_precision()
    center = mp.mpc(mp.mpf(str(center_re)), mp.mpf(str(center_im)))
    near = mp.mpf(str(near_multiple * width))
    refusal = OUTSIDE
    for period in periods:
        cost["solves"] += 1
        solve = nuc.newton_nucleus(center, period, degree=degree)
        if not solve.converged or abs(solve.c - center) > near:
            continue
        record = nuc.make_atom(solve.c, period, degree)
        if record is None:
            continue
        distance = float(abs(solve.c - center))
        sizes = width / record["window_scale"] if record["window_scale"] > 0 else float("inf")
        record["seed_distance"] = distance
        record["seed_distance_frames"] = distance / width if width else float("inf")
        record["frame_sizes"] = sizes
        record["in_frame"] = bool(FRAME_MIN <= sizes <= FRAME_MAX)
        return record, cost
    return None, {**cost, "refused": refusal}


# --------------------------------------------------------------------------- #
# Criterion (c): the copy this frame is decoration of.
# --------------------------------------------------------------------------- #
def screened_chain(
    held: Scan,
    width: float,
    degree: int,
    *,
    slack: float = SCREEN_SLACK,
    max_solves: int = ENCLOSE_MAX_SOLVES,
) -> list[int]:
    """The chain periods whose atom could still be at least the frame's width.

    [`screened`]' screen with only the lower edge of the band: an enclosing copy
    is *bigger* than the frame, so the test is `log₁₀(w) + log₁₀|A| ≤ slack` and
    there is no upper bound to apply. The exact `size_q ≥ w` is re-asked after
    Newton, which is what the slack is for.
    """
    if width <= 0:
        return []
    at = math.log10(width)
    kept = []
    for period in held.chain:
        approx = held.approx_log10_abs_a(period, degree)
        if approx is not None and at + approx <= slack:
            kept.append(period)
    return kept[:max_solves]


def bulb_scale(m: int, degree: int) -> float:
    """How big a satellite bulb of index `m` is against the component it hangs off.

    `2·sin(π/m) / (m²·(d−1))`, the smallest such bulb — the one at internal angle
    `1/m`; the others run up to `m/π` times larger and pass the same test with
    room to spare. Measured against the main body's own scale of 1.0 it reads
    within a few per cent on every plane: at degree 2 the bulbs from `m = 2` to
    `m = 11` read 1.00, 0.98, 0.99, 1.01, 1.02, 1.03 of it, and the `1/(d−1)` is
    what makes degree 3 to 6 read the same rather than 0.53, 0.37, 0.27, 0.21.

    This is what separates a **bulb** from a **copy**, which is the whole of what
    criterion (c) needs the chain for: a bulb's decorations belong to the
    component it is attached to, a copy's belong to itself.
    """
    if m < 2:
        return math.inf
    return 2.0 * math.sin(math.pi / m) / (m * m * max(degree - 1, 1))


def generations(qualifying, degree: int, *, slack: float = BULB_SLACK) -> list[list[dict]]:
    """Split a nested chain into `[copy, its bulbs…]` groups, outermost first.

    An entry joins the generation above it when it is a bulb of **any** member of
    it — not only of the last, because a copy's period doubling and its `1/m`
    bulb both hang off the copy and arrive in that order.
    """
    groups: list[list[dict]] = []
    for record in qualifying:
        if groups and any(_is_bulb_of(record, prior, degree, slack) for prior in groups[-1]):
            groups[-1].append(record)
        else:
            groups.append([record])
    return groups


def _is_bulb_of(record: dict, prior: dict, degree: int, slack: float) -> bool:
    """Whether `record` is a satellite bulb hanging off `prior`'s component."""
    above, below = prior["period"], record["period"]
    if above <= 0 or below <= above or below % above:
        return False
    floor = prior["window_scale"] * bulb_scale(below // above, degree) / slack
    return record["window_scale"] >= floor


def main_body(degree: int) -> dict:
    """The chain's head: period 1 at `c = 0`, whose atom scale is exactly 1.

    `A = Λ^(1/(d−1))·z'_1` with an empty `Λ` and `z'_1 = 1`, so `|A| = 1` on
    every plane — and 1.0 *is* the main cardioid's width at degree 2. It is
    prepended rather than solved for: [`nucleus.make_atom`] refuses period 1 as
    the `c = 0` degenerate, which is right for every other caller.
    """
    return {"period": 1, "window_scale": 1.0, "degree": degree}


def enclosing(
    center_re,
    center_im,
    width,
    degree: int,
    *,
    k: float = ENCLOSE_K,
    bulb_slack: float = BULB_SLACK,
    max_solves: int = ENCLOSE_MAX_SOLVES,
    slack: float = SCREEN_SLACK,
    held: Scan | None = None,
) -> tuple[dict | None, dict]:
    """`(the copy this frame is inside, what it cost)` — criterion (c).

    The atom record is [`nucleus.make_atom`]'s with four readings added:
    `size_over_width`, the ratio the census reports; `seed_distance_atoms`, how
    far off centre the nucleus sits in its own atom sizes; `chain_periods`, every
    period of the nested chain that qualified, the main body's 1 among them; and
    `generation`, the copy and the bulbs on it that the answer came from. `None`
    with a reason where the frame is decoration of the main body and of nothing
    smaller.

    `held` is an already-taken [`scan`] at this centre, so a caller asking both
    criteria pays for one orbit pass rather than two.
    """
    import mpmath as mp

    width = float(width)
    cost = {"chain": 0, "chain_screened": 0, "enclose_solves": 0}
    if held is None:
        held = scan(center_re, center_im, degree)
    cost["chain"] = len(held.chain)
    periods = screened_chain(held, width, degree, slack=slack, max_solves=max_solves)
    cost["chain_screened"] = len(periods)
    if not periods:
        return None, {**cost, "enclose_refused": NOT_ENCLOSED}

    nuc.set_precision()
    center = mp.mpc(mp.mpf(str(center_re)), mp.mpf(str(center_im)))
    solved: list[dict] = []
    for period in periods:
        cost["enclose_solves"] += 1
        solve = nuc.newton_nucleus(center, period, degree=degree)
        if not solve.converged:
            continue
        record = nuc.make_atom(solve.c, period, degree)
        if record is None:
            continue
        size = record["window_scale"]
        if not (size >= width > 0):
            continue
        distance = float(abs(solve.c - center))
        record["seed_distance"] = distance
        record["seed_distance_atoms"] = distance / size
        record["size_over_width"] = size / width
        solved.append(record)
    # Every copy bigger than the frame, whatever `k` says, so a census row carries
    # the whole table and the cut can be moved without re-probing anything. See
    # [`ENCLOSE_K`]: the calibration set only ever visits one part of a copy.
    cost["chain_table"] = [
        [record["period"], round(record["seed_distance_atoms"], 5), record["size_over_width"]]
        for record in solved
    ]
    qualifying = [main_body(degree), *(r for r in solved if r["seed_distance_atoms"] <= k)]

    groups = generations(qualifying, degree, slack=bulb_slack)
    chosen = dict(groups[-1][0])
    if chosen["period"] == 1:
        # Every copy the frame sits in is the main body or a bulb on it, so what
        # the frame decorates is the main body — which never counts.
        return None, {**cost, "enclose_refused": NOT_ENCLOSED}
    chosen["enclosed"] = True
    chosen["chain_periods"] = [record["period"] for record in qualifying]
    chosen["generation"] = [record["period"] for record in groups[-1]]
    chosen["generations"] = [[record["period"] for record in group] for group in groups]
    chosen["innermost_period"] = qualifying[-1]["period"]
    return chosen, cost


# --------------------------------------------------------------------------- #
# The other reading: where the frame came from.
# --------------------------------------------------------------------------- #
@dataclass
class Descent:
    """What the walk ledgers say about how a frame was reached."""

    run: str
    depth: int | None
    fate: str | None
    branch: str | None
    root_width: float | None
    root_source: str | None
    root_provenance: dict = field(default_factory=dict)
    #: `log₁₀(root width / this width)`, or `None` with no root row.
    decades: float | None = None


def walk_index(paths=None) -> dict:
    """`{(center_re, center_im): [row, …]}` over every walk ledger on both tiers.

    Keyed on the coordinate **strings**, which is the identity a ledger writes and
    a pool row carries forward unaltered; the width is compared by the caller,
    relatively, because one place is reached at several widths. Over the 86
    ledgers this checkout can see it is 311,085 centres and 13 s.
    """
    from fractal_wallpapers.supply import ledgers

    index: dict[tuple[str, str], list[dict]] = {}
    for path in ledgers.ledger_paths() if paths is None else [Path(p) for p in paths]:
        run = Path(path).parent.name
        rows = []
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("kind") in ("candidate", "root"):
                rows.append(row)
        roots = {row.get("root_id"): row for row in rows if row.get("kind") == "root"}
        for row in rows:
            if row.get("kind") != "candidate":
                continue
            viewport = row.get("viewport") or {}
            root = roots.get(row.get("root_id")) or {}
            index.setdefault(
                (str(viewport.get("center_re")), str(viewport.get("center_im"))), []
            ).append(
                {
                    "run": run,
                    "width": viewport.get("width"),
                    "depth": row.get("depth"),
                    "fate": row.get("fate"),
                    "branch": row.get("branch"),
                    "root_width": (root.get("viewport") or {}).get("width"),
                    "root_source": root.get("source"),
                    "root_provenance": root.get("provenance") or {},
                }
            )
    return index


def descent(index: dict, center_re, center_im, width, *, tolerance: float = 1e-9) -> Descent | None:
    """The walk row a frame is, or `None` where no ledger holds it.

    `tolerance` is relative to the width, because the two strings being compared
    were written by different writers at different times and only ever mean the
    same `f64`.
    """
    rows = index.get((str(center_re), str(center_im)))
    if not rows:
        return None
    want = float(width)
    for row in rows:
        try:
            held = float(row["width"])
        except (TypeError, ValueError):
            continue
        if abs(held - want) > tolerance * abs(want):
            continue
        root = row.get("root_width")
        decades = None
        if root:
            try:
                decades = math.log10(float(root) / want)
            except (TypeError, ValueError, ZeroDivisionError):
                decades = None
        return Descent(
            run=row["run"],
            depth=row.get("depth"),
            fate=row.get("fate"),
            branch=row.get("branch"),
            root_width=float(root) if root else None,
            root_source=row.get("root_source"),
            root_provenance=row.get("root_provenance") or {},
            decades=decades,
        )
    return None


# --------------------------------------------------------------------------- #
# The census.
# --------------------------------------------------------------------------- #
#: The bin edges the ratio distribution is reported on, in atom sizes. Open at
#: both ends: the first bin is "the frame is inside the atom" and the last is
#: "the atom is a speck", and both are counts a reader of the band wants.
BANDS = (1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 256.0, 1024.0)


def band_of(sizes: float) -> str:
    """Which reporting bin a frame-in-atom-sizes reading falls in."""
    if sizes < BANDS[0]:
        return f"<{BANDS[0]:g}"
    for low, high in zip(BANDS, BANDS[1:], strict=False):
        if sizes < high:
            return f"{low:g}-{high:g}"
    return f">={BANDS[-1]:g}"


def ratio_decade(ratio: float) -> str:
    """Which decade of `size_q / w` an enclosing reading falls in, as `10^n`.

    The ratio spans nine decades over this pool — a frame can be a tenth of its
    copy or a billionth of it — so the reporting bin is the decade and not a
    band. `1e0` holds `1 ≤ r < 10`, which is a frame nearly as big as the copy
    it sits in.
    """
    if not (ratio > 0) or not math.isfinite(ratio):
        return "n/a"
    return f"1e{int(math.floor(math.log10(ratio)))}"


#: Which criteria a census pass takes. `band` is (a), `enclosing` is (c), and
#: `both` shares one orbit scan between them.
READINGS = ("both", "band", "enclosing")


def _one(task: tuple) -> dict:
    """One census row, in a worker. Arguments are plain data so they pickle."""
    location, partition, center_re, center_im, width, reading = task
    degree = degree_of(partition)
    if degree is None:
        return {"location": location, "refused": NOT_A_PLANE}
    row = {"location": location, "partition": partition, "width": float(width)}
    held = scan(center_re, center_im, degree)
    if reading in ("both", "band"):
        record, cost = probe(center_re, center_im, width, degree, held=held)
        row.update(cost)
        if record is not None:
            row.update(
                {
                    "period": record["period"],
                    "window_scale": record["window_scale"],
                    "frame_sizes": record["frame_sizes"],
                    "seed_distance_frames": record["seed_distance_frames"],
                    "in_frame": record["in_frame"],
                    "band": band_of(record["frame_sizes"]),
                    "nucleus": record["key"],
                }
            )
    if reading in ("both", "enclosing"):
        record, cost = enclosing(center_re, center_im, width, degree, held=held)
        row.update(cost)
        row["enclosed"] = record is not None
        if record is not None:
            row.update(
                {
                    "enclosing_period": record["period"],
                    "enclosing_scale": record["window_scale"],
                    "size_over_width": record["size_over_width"],
                    "enclosing_distance_atoms": record["seed_distance_atoms"],
                    "enclosing_chain": record["chain_periods"],
                    "enclosing_generation": record["generation"],
                    "innermost_period": record["innermost_period"],
                    "enclosing_nucleus": record["key"],
                    "ratio_decade": ratio_decade(record["size_over_width"]),
                }
            )
    if reading == "enclosing":
        row["escaped_at"] = held.escaped_at
    return row


def _initializer() -> None:
    from fractal_wallpapers import process_control

    process_control.set_background_priority()


def census(tasks, *, workers: int = 3, budget: float | None = None, log=print):
    """Probe a population of frames, yielding one row each, oldest task first.

    `tasks` is `(location key, partition, center_re, center_im, width)`. Three
    workers at below-normal priority, which is the render pool's shape and this
    box's rule — this leg drives no engine, but it saturates three cores for an
    hour and the desktop has to stay usable through it.

    `budget` is wall seconds; the pass stops handing out work when it is spent and
    the caller reports how far it got, which is what a capped scan owes its
    reader.
    """
    import time
    from concurrent.futures import ProcessPoolExecutor

    held = list(tasks)
    started = time.time()
    done = 0
    if workers <= 1:
        for task in held:
            if budget is not None and time.time() - started > budget:
                log(f"[census] budget spent after {done:,} of {len(held):,}")
                return
            yield _one(task)
            done += 1
        return
    with ProcessPoolExecutor(max_workers=workers, initializer=_initializer) as pool:
        for row in pool.map(_one, held, chunksize=8):
            yield row
            done += 1
            if budget is not None and time.time() - started > budget:
                log(f"[census] budget spent after {done:,} of {len(held):,}")
                return
