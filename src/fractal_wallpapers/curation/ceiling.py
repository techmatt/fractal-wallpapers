"""The colour ceiling, and the targets that are the same feature with the sign flipped.

A gallery pass judges each picture on its own and the collection comes out
however the pool happened to be coloured. gallery3's did: red at 2.10x uniform in
the supply before a seat was filled, and seating amplified it to 2.45x while
pushing lime to 0.19x. Seven of the twelve hue families held under one seat in
twelve; one picture in a hundred and fifty was green.

This module is the two levers that act on that, and they are one feature read
twice. [`fractal_wallpapers.palettes.dominance`] says what colour a picture is.
The **ceiling** refuses a candidate that would take a colour past its allowance.
A **target** demands a colour the pass would otherwise never reach. Same reading,
opposite sign, and neither one can drift from the other because there is only one
reading.

## Where it acts

At the **seat**, and it is arithmetic over rows rather than a walk of its own.
[`curation.rules.State`] applies `allowed()` per candidate as the gallery leg
seeds and swaps, and it is the only reader: one derivation, and no second answer
to what the allowance is.

This module used to own a sequential seating of its own — a `Seating` object with
three tests, a least-violating fallback, and a `Lens` that opened each candidate's
render to read its colour and its pixel cloud. That was the pre-solver gallery
pass's machinery and it went with the pass; what is left here is the allowance and
the target arithmetic, which is all either surviving reader ever wanted. The
on-demand extra picks that pass asked the renderer for when a seat's whole slate
was refused are recorded as a design note in the handoff docs: the idea is kept,
the code is not.

The pro-rata form is the fix for what a cumulative budget did. A whole-gallery
budget is denominated in a unit the gallery only fills to 79%, so two thirds of
its range can never fire at all, and the one setting that does fire first fires
at seat 110 of 150 — a curfew rather than a ceiling — and then refuses everything
carrying that colour for the rest of the walk, because the test is on the
after-state and there is no recovery. `floor(K * t * n) + 1` has the warm-up built
into the `+ 1`: the first seat may hold any one colour, and the allowance grows
with the walk instead of being spent against its end.

`K = 2` is the headroom: a colour may run at twice its target rate before the
ceiling acts. Refusing only a **dominant** candidate is the other half of the
cliff's removal — a picture that is a fifth red is not what makes a gallery red.

## Targets, and what they are not

`--target dark_vivid_green=0.05` asks for at least `ceil(0.05 * N)` pictures
dominant in that cell — [`Rule.wanted`], which is what a solve turns into a
constraint row. The seat-by-seat urgency ladder that used to read `u = need /
seats left` and mandate or prefer on it belonged to the deleted seating; a solve
states the ask as a constraint instead, and satisfies it or is infeasible.

A target is not a floor that moves and not a pad. An unmet target is reported
**SHORT**, in the record and in the report, and the seats it could not fill are
filled by the ordinary rule. The lever that actually meets a target is upstream,
where the pictures are made: something has to render a map chosen for the colour,
because that is the only way a colour the palette head declines 83% of the time
reaches a seat at all. [`curation.hunt`]'s conditioned leg is that lever, and
[`curation.depth`]'s conditioned draw is the same lever at width.

Setting a target also **replaces the default allowance** for that cell and for
its family, so the ceiling and the target are denominated in one vector: asking
for green at 5% says green *should* be 5% of the gallery, and the ceiling then
lets it run to twice that.

## And it raises what the target implies

A carrier of one cell is dominant in more than one cell: on the reference fields
a `dark_vivid_lime` delivery lands `dark_muted_lime` 42% of the time and
`light_muted_lime` 34%. So a target that raised only its own cell's allowance
sends its own seats against its companions' untargeted allowance of three, and
the program is refused for a reason nobody chose. A target of `t` therefore also
raises each companion's share by `t` times that companion's **measured**
co-dominance rate ([`palettes.carriers.co_dominance`]), and the companion's
family by the same unless it is the target's own family — which the target has
already raised, and which counts a picture once however many of its cells that
picture is dominant in.

The rates come off the record and never off the hue wheel. An adjacency written
down by hand would say lime borders green and yellow; what the library says is
that lime's carriers land three other *lime* cells before they land anything
green, and that they land `dark_vivid_green` more often than
`dark_vivid_yellow`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from fractal_wallpapers.palettes import dominance

#: Seats one palette group may take, before the exemption.
#:
#: **One.** gallery3's 150 seats named 91 distinct groups and 59 of them sat above
#: this — `wallhaven_wallhaven-1joljg` seven times, `Furnace Rose` four, and one
#: 12-seat cluster of black-to-rose-to-white pictures that reads as a single
#: decision taken twelve times.
GROUP_CAP = 1

#: The **proportional** cap's rate: a group may take this share of the seats.
#:
#: **0.025**, Matt's, at ckpt 88 — `max(1, floor(0.025 * n))`, so 1 up to n=40,
#: 3 at n=150 and 25 at n=1000. **This is the shipped rule**: a pass that names
#: no cap gets it, because [`curation.solve.DEFAULT_GROUP_CAP`] is
#: [`PROPORTIONAL`]. [`GROUP_CAP`] above is still the constant behind
#: [`IDENTITY`], which is what [`group_cap`] returns when a caller asks for that
#: rule by name.
#:
#: What the identity cap was doing beside being a ceiling is the reason to have
#: both. A cap of one forces an n-seat gallery onto n distinct maps, which pushes
#: the seating down the map-quality tail by construction; it is also the only
#: block a census proves short at n=1000, where 822 maps could not fill 1000 seats
#: and the 942 of the pool today still cannot.
#: At 2.5% that ceiling is 20,550 and the block retires — and the cap turns from
#: slack into something a good-map-seeking key will want to spend, so the
#: **realized** maximum per map becomes a number to report rather than assume.
GROUP_CAP_RATE = 0.025

#: The two rules a caller may name, and the default. Spelled rather than passed
#: as a boolean because a record has to say which one a seating ran under, and
#: `group_cap=False` on a record is not an answer to "what was the cap".
IDENTITY = "identity"
PROPORTIONAL = "proportional"
GROUP_CAP_RULES = (IDENTITY, PROPORTIONAL)

#: The **themed** cap's rule name. Not in [`GROUP_CAP_RULES`] on purpose: it is
#: not a rule a caller names, it is the rule a themed pass *has*. A record still
#: has to say which cap ran, so it is spelled here with the others.
THEMED = "themed"

#: The **themed** cap's rate: a share of `n`, as the main gallery's cap is.
#:
#: **0.05**, Matt's ruling of 2026-09-05 — `max(1, floor(0.05 * n))`, so 10 at
#: n=200 and 50 at n=1000. **Twice [`GROUP_CAP_RATE`]**, which is the whole of the
#: argument: a themed pool holds a few dozen palette groups against the whole
#: pool's hundreds, so the general cap is the binding rule at every shipping size
#: over a theme, and the themed pass is given room for exactly that and no more.
#:
#: It **replaced** `ceil(2n/P)` — twice the even share across the `P` groups that
#: could field the theme, measured off the pool at solve time. What that bought
#: was a cap that moved with the pool: two themes at one `n` ran under different
#: caps, and one theme ran under a different cap after a night's mining than
#: before it, so a before/after on a theme was never a controlled read. A rate on
#: `n` is a number written down once, and P stays on the record as a **reading**
#: of the pool rather than as the denominator of a rule.
THEMED_GROUP_CAP_RATE = 0.05

#: How many distinct **places** a palette group has to field in the themed pool
#: before it counts towards `P`.
#:
#: **Three.** `P` was the denominator of the themed cap until 2026-09-05 and is
#: now a **reading** of the pool the record carries — how many palette groups can
#: actually field the theme — so the floor is what keeps that reading honest: a
#: group holding one fluke place can never take more than one seat however high
#: the cap goes, and counting it would report a capacity that does not exist.
#: Measured on 2026-09-01:
#: `dark_vivid_lime` 39 groups of which 29 field three or more, and the ten it
#: drops hold 13 of the pool's 424 places; `dark_vivid_green` 65 of which 50, the
#: fifteen dropped holding 20 of 1,097. So the floor moves `P` by a quarter while
#: giving up under 3% of the places, which is the whole argument for it.
#:
#: **Places and never rows**, because one wallpaper per location is absolute: a
#: group with fifty rows at one place can take exactly one seat.
THEMED_CAP_PLACES = 3


def group_cap(n: int, rule: str = IDENTITY) -> int:
    """How many seats one palette group may take out of `n`, under `rule`.

    [`IDENTITY`] is [`GROUP_CAP`] whatever `n` is — the cap this project has
    always seated under. [`PROPORTIONAL`] is `max(1, floor(GROUP_CAP_RATE * n))`.

    The `max(1, ...)` is not a rounding convenience: below `1 / GROUP_CAP_RATE`
    seats the floor is zero, and a cap of zero is a program with no seats in it.
    So a debug gallery at n=20 keeps the identity cap under either rule, which is
    why a before/after on this has to be taken at a size where the two differ.
    """
    if str(rule) == IDENTITY:
        return GROUP_CAP
    if str(rule) != PROPORTIONAL:
        raise ValueError(f"the group cap rule is one of {GROUP_CAP_RULES}, not {rule!r}")
    return max(1, int(math.floor(GROUP_CAP_RATE * max(0, int(n)))))


def capable_groups(candidates, places: int = THEMED_CAP_PLACES) -> dict:
    """`{group: how many distinct places it fields}`, for the groups over the floor.

    `P`, which a themed record carries as a reading of its own pool — it was
    [`themed_group_cap`]'s denominator until 2026-09-05 and no rule is stated in
    it now. It counts **places** — one wallpaper per location is absolute, so a
    group's capacity is the places it can field and never the rows it holds.
    `places` is the floor a group has to reach before it counts; see
    [`THEMED_CAP_PLACES`].
    """
    held: dict = {}
    for candidate in candidates:
        held.setdefault(str(candidate.group), set()).add(str(candidate.location))
    return {group: len(where) for group, where in sorted(held.items()) if len(where) >= int(places)}


def themed_group_cap(n: int) -> int:
    """`max(1, floor(THEMED_GROUP_CAP_RATE * n))` — the themed cap.

    [`group_cap`]'s [`PROPORTIONAL`] arithmetic at twice its rate, and the
    `max(1, ...)` is the same argument that one makes: `floor(0.05 * n)` is zero
    below twenty seats and a cap of zero is a program with no seats in it. So a
    debug themed gallery at n=10 keeps the identity cap, and a before/after on
    this has to be taken at n=20 or above.

    It takes `n` alone. The pool it will be applied over is not an argument, which
    is the point of the 2026-09-05 ruling: see [`THEMED_GROUP_CAP_RATE`].
    """
    return max(1, int(math.floor(THEMED_GROUP_CAP_RATE * max(0, int(n)))))


#: How far apart two pictures of one palette group have to be for the second to
#: be seated anyway, in the pixel-cloud metric.
#:
#: **0.10**, which is where two pictures are plainly different pictures: the three
#: reference pairs on the twins sheet land at 0.0999-0.1000 and were read that
#: way by eye. It is high on purpose against [`TAU`] below — this is not a twin
#: test with a different number, it is the *exemption* from a cap on the map, and
#: it has to be a distance nobody would argue about. Same-group pairs in gallery3
#: run 0.0121 to 0.4111, so the exemption is a real gate rather than a formality:
#: a group's second seat has to earn it.
TAU_GROUP = 0.10

#: How much headroom a colour gets over its target rate before the ceiling acts.
#:
#: **Two.** At one the ceiling is an exact quota and the walk spends its whole
#: tail on the fallback; at three it never fires against a supply already skewed
#: 2.1x. Twice the target rate is the setting at which the observed maxima —
#: family red at 2.45x uniform, cell `dark_vivid_blue` at 3.25x — are the things
#: it acts on and nothing else is.
K = 2

#: The default target rate per chromatic cell and per hue family: uniform. 48
#: cells and 12 families, so a gallery that spread itself evenly would sit exactly
#: on both. Nothing has ever been near that and nothing is expected to be; it is
#: the denominator the skew is measured in, and the allowance is `K` times it.
CELL_SHARE = 1.0 / 48.0
FAMILY_SHARE = 1.0 / 12.0

#: Pixel-cloud distance under which two pictures are the same wallpaper.
#:
#: **0.034281 since 2026-09-05** — Matt's ruling, exactly 0.90 x the 0.03809 it had
#: been since 2026-09-02, which was itself 0.65 x the 0.0586 read off the twins
#: ladder before that. **Globally and as one number**: the signature is mode-agnostic
#: and so is the rule, so there is no per-mode table here, no per-palette one, and
#: there is not to be one.
#:
#: **The 2026-09-05 move was taken by eye, and that is the whole of its provenance.**
#: `READ_twin_verdicts_and_tau_candidates_0905` priced 0.95x, 0.90x and 0.85x by
#: counterfactual solve and read the sitting on `labels/twin_verdicts.json` — and the
#: sitting cannot carry the ruling, because all 88 of its ruled pairs are pairs the
#: rule ADMITTED. It answers *was the rule right to admit* (9.1% too_close) and says
#: nothing about whether it was wrong to refuse, which is the half a loosening turns
#: on: every pair below the threshold went unruled. There is no crossing in it either
#: — the isotonic fit runs 0.0000-0.1905 over the band and never approaches 0.5. **τ
#: is a taste dial here and no sitting has located a boundary.** What Matt saw as he
#: ruled was the old value refusing pairs that are not similar.
#:
#: What the move costs, priced before it was taken, on the published record's own
#: config (`20260904T233233Z`: n=1000, augment on, spiral cap default): the seating
#: stays full at 1,000 seats with zero shortfall — **the pool is saturated at this
#: size, so a looser threshold cannot buy a seat and moves only which thousand sit**.
#: The sum goes 565.73 to 571.71, the worst seat 0.121677 to 0.124222, twin refusals
#: 520 to 338, and **158 of the thousand seats turn over** against a gallery whose IDs
#: the site's figures already name. Past about 0.85x the objective goes flat and the
#: churn keeps climbing, which is what bounds this from below.
#:
#: What the 2026-09-02 audit found, kept because it is the reading the number is still
#: anchored on. Over `overnight_after`, the n=2000 gallery that closed every
#: census floor and still fell 68 seats short, the pairs the test was refusing stop
#: reading as duplicates at about 0.65 of the old threshold — read off contact sheets
#: of refused beside seated, per mode, and corroborated by a statistic nobody used to
#: reach it: the share of refused pairs made with the **same palette map** runs 93-98%
#: below 0.4 tau and collapses through 55% at 0.5-0.6 to 32% at 0.6-0.7 and 11% at
#: 0.9-1.0, against a 0.2% base rate for two unrelated rows. 66% of all twin refusals
#: sat above the new threshold, and all twenty of the farthest-refused pairs sat at the
#: old one and were plainly different pictures.
#:
#: What that one cost, measured before it was taken: the n=2000 seating goes 1,033 to
#: 1,569 with the shortfall 68 to 7, and the gallery then holds 3,795 pairs the 0.0586
#: threshold would have refused. Those are the pairs the sheets say are not duplicates,
#: and that is the whole of that ruling.
#:
#: **The known failure this does NOT fix** is structural rather than a matter of where
#: the number sits: two near-white pictures with different geometry collapse in a
#: signature over colour alone. A gate that asks colour AND geometry is what addresses
#: that, and it is measured in `SET_twin_tau_0p65_and_geometry_gate` and not shipped.
#:
#: The old reading, kept because the shape of the argument still holds: the curve is
#: steep and the band narrow — over gallery3's walk 0.040 rejected 5 seats, 0.050
#: rejected 14, 0.060 rejected 30. It is a number **in the all-pixel metric** and
#: cannot be carried to the chromatic-only variant, which runs 5-15% lower at every
#: percentile that matters.
TAU = 0.034281

#: How many pictures inside [`TAU`] it takes to refuse. **Two**: one near
#: neighbour is a collection with a pair in it, which is what a gallery of a
#: hundred and fifty looks like when it is working. Three of a kind is the thing
#: a person notices.
TWINS = 2


class TargetRefused(RuntimeError):
    """A target cannot be launched, and starting would spend a pass to find out."""


def parse_target(text: str) -> tuple:
    """`"dark_vivid_green=0.05"` as `(cell, fraction)`. Refuses anything else.

    Refuses here rather than at the seat, because a misspelt cell name is a
    target that can never be met and a pass that discovered it at seat 150 would
    report SHORT for a reason that was a typo.
    """
    cell, _, fraction = str(text).partition("=")
    cell = cell.strip()
    if not _:
        raise TargetRefused(f"--target wants <cell>=<fraction>, not {text!r}")
    if cell not in dominance.cells():
        raise TargetRefused(
            f"{cell!r} is not a chromatic cell of the codebook. A target names one of the "
            f"{len(dominance.cells())} — `dark_vivid_green`, `light_muted_azure` and so on — "
            "and never a family or a neutral."
        )
    try:
        value = float(fraction)
    except ValueError as refusal:
        raise TargetRefused(f"{fraction!r} is not a fraction, in --target {text!r}") from refusal
    if not 0.0 < value <= 1.0:
        raise TargetRefused(f"a target is a fraction in (0, 1]; {text!r} asks for {value}")
    return cell, value


def refuse_targets(targets: dict, pool: list) -> dict:
    """Refuse a target set that cannot be met, before a render is spent.

    Two refusals and both are about being able to *keep the promise*:

    * **The fractions have to fit.** A target is a share of the collection and
      the shares of disjoint cells add up, so a set summing above one is asking
      for more pictures than there are seats.
    * **The cell has to have a carrier the leg can reach.** A colour no map in
      the collapsed palette pool can make is a colour the plan cannot ask for,
      and a leg that started anyway would run to the end and report SHORT for a
      reason nothing on the record names.

    Returns the feasibility block the record carries: how many carriers each
    targeted cell has, and the strongest of them.
    """
    from fractal_wallpapers.palettes import carriers as carrier_table

    if not targets:
        return {}
    total = sum(float(value) for value in targets.values())
    if total > 1.0:
        raise TargetRefused(
            f"the targets ask for {total:.3f} of the collection between them, and there is "
            "only one collection. Lower them or drop one."
        )
    block = {"sum": round(total, 6), "cells": {}}
    for cell in sorted(targets):
        offers = carrier_table.for_cell(cell, within=pool)
        if not offers:
            raise TargetRefused(
                f"no map this leg can draw carries {cell}. The carrier table "
                f"({carrier_table.record_path().name}) is over the whole library and the "
                "pool is one member per palette group, so either the cell has no carrier "
                "at all or every one of its carriers stood down for a group-mate."
            )
        block["cells"][cell] = {
            "fraction": float(targets[cell]),
            "carriers": len(offers),
            "best": [{"map": name, "mean": round(share, 6)} for name, share in offers[:5]],
        }
    return block


#: The tracked table's co-dominance, read once a process. The file is three
#: quarters of a megabyte and a `Rule` is built per solve, per sweep rung and per
#: test; parsing it at each of them would put a disk read inside the fast lane.
_CO_DOMINANCE: dict = {}


def measured_co_dominance(cell: str) -> dict:
    """`{companion cell: rate}` off the tracked carrier table, memoized."""
    from fractal_wallpapers.palettes import carriers

    if cell not in _CO_DOMINANCE:
        _CO_DOMINANCE[cell] = carriers.co_dominance(cell)
    return _CO_DOMINANCE[cell]


@dataclass
class Rule:
    """The constants and the targets. Arithmetic over rows, and no state at all.

    A candidate already carries every colour it is dominant in on its ledger row,
    so nothing here needs a picture opened to ask what a candidate is. That is why
    nothing here reads pixels — a second derivation of `allowed()` would be a
    second answer to what the allowance is.
    """

    #: `{cell: fraction}` as the caller asked for it. Cells only — a target is
    #: never set on a family, though setting one moves a family's allowance.
    targets: dict = field(default_factory=dict)
    group_cap: int = GROUP_CAP
    tau_group: float = TAU_GROUP
    k: int = K
    #: `{cell: {companion cell: rate}}`, the co-dominance a target's implied cells
    #: are derived from. `None` reads it off the tracked carrier table, which is
    #: what a solve and a pass both want; a test hands one in so it does not have
    #: to stand up a table to ask what a target implies.
    co_dominance: dict | None = None

    def __post_init__(self) -> None:
        self.targets = {str(cell): float(value) for cell, value in (self.targets or {}).items()}
        self._share: dict = {}
        #: `{cell or family: how much a target's companions raised it}`, kept apart
        #: from `_share` so a record can say which allowances were *asked for* and
        #: which followed. Read by the gallery leg's own record.
        self.implied: dict = {}
        for cell, value in self.targets.items():
            self._share[cell] = value
            family = dominance.family_of(cell)
            if family is not None:
                # SUMMED and not replaced outright, for the one case the ruling
                # does not spell out: two targeted cells of one family both have
                # to fit under their family's allowance, and a family holding the
                # larger of the two would refuse the smaller one's last seats.
                self._share[family] = self._share.get(family, 0.0) + value
            for companion, rate in self._companions(cell).items():
                self.implied[companion] = self.implied.get(companion, 0.0) + value * rate
                kin = dominance.family_of(companion)
                # A companion in the target's OWN family needs no family raise:
                # the family row counts a picture once however many of its cells
                # that picture is dominant in, and the target already raised it.
                if kin is not None and kin != family:
                    self.implied[kin] = self.implied.get(kin, 0.0) + value * rate
        for name, extra in self.implied.items():
            self._share[name] = self._share.get(name, self._default_share(name)) + extra

    @staticmethod
    def _default_share(name: str) -> float:
        return FAMILY_SHARE if name in dominance.families() else CELL_SHARE

    def _companions(self, cell: str) -> dict:
        """`{cell: rate}` this target's carriers also deliver. **Measured**.

        Off the carrier table's own deliveries and never off the wheel: a hand
        written adjacency would say lime borders green and yellow, and what the
        record says is that a `dark_vivid_lime` carrier lands `dark_muted_lime`
        42% of the time, `light_muted_lime` 34%, and `dark_vivid_green` 8%. The
        rates are not the wheel's, they are the library's.
        """
        if self.co_dominance is not None:
            return {
                str(name): float(rate)
                for name, rate in (self.co_dominance.get(str(cell)) or {}).items()
            }
        return measured_co_dominance(str(cell))

    def share(self, name: str) -> float:
        """The target rate for one cell or family: the set one, or uniform."""
        if name in self._share:
            return self._share[name]
        return FAMILY_SHARE if name in dominance.families() else CELL_SHARE

    def allowed(self, name: str, seats: int) -> int:
        """`floor(K * t * n) + 1` — how many of the first `n` seats may be this colour.

        **Ask this rather than compute the formula on paper.** The product is
        taken in binary floating point, so a `k` and an `n` whose exact product
        lands on an integer lose a seat to the floor: at `k = 2.4`, `n = 1000`
        and the uniform cell share this is `49.99999999999999`, and the answer is
        **50** where the arithmetic says 51. Nothing shipped hits it — `k = 2` at
        the uniform share is `41.67` — and it was found pricing a counterfactual
        (`curation/MEASUREMENTS.md`'s *What the colour ceiling costs at n=1000*).
        """
        return int(math.floor(self.k * self.share(name) * max(0, int(seats)))) + 1

    def wanted(self, cell: str, n: int) -> int:
        """`ceil(t * N)` — how many pictures a target asks for out of `N` seats."""
        return int(math.ceil(self.targets[cell] * int(n)))


def share_of(share: float, seats: int) -> int:
    """`ceil(share * seats)` — a share of the REALIZED seat count, in one place.

    The one spelling of "some fraction of the gallery that actually got filled",
    and it now has three readers: [`curation.solve.Demand.wanted`] for a colour
    target, and [`curation.rules.State`] for the spiral share cap, in both
    directions — a target is a floor under this quantity and a cap is a ceiling
    over it, and they must not be able to disagree about what the quantity is.

    A share of the realized count and never of `n`, for [`solve.target_rule`]'s
    measured reason: this leg does not promise `n` seats, so a demand denominated
    in seats nobody is promising to fill reports nothing at all when the answer
    comes back under-filled. The same argument is why a cap is not denominated in
    `n` either — a cap against 1000 while 941 fill is a cap that is 6% looser than
    the number somebody wrote down.
    """
    return int(math.ceil(float(share) * max(0, int(seats))))


__all__ = [
    "share_of",
    "CELL_SHARE",
    "FAMILY_SHARE",
    "GROUP_CAP",
    "GROUP_CAP_RATE",
    "GROUP_CAP_RULES",
    "IDENTITY",
    "THEMED",
    "THEMED_CAP_PLACES",
    "THEMED_GROUP_CAP_RATE",
    "K",
    "PROPORTIONAL",
    "capable_groups",
    "themed_group_cap",
    "TAU",
    "TAU_GROUP",
    "TWINS",
    "Rule",
    "TargetRefused",
    "group_cap",
    "measured_co_dominance",
    "parse_target",
    "refuse_targets",
]
