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

## Where it acts, and why it could not act anywhere else

At the **seat**, sequentially. A pass is two legs — every slot's attempts are made
and judged, and then the slots are filled — and the ceiling lives in the second.
That is not a convenience:

* Moving it into the attempt leg would buy nothing. That leg is a serial loop
  that is already the whole cost of a pass; the seating is arithmetic over rows
  in hand.
* The anchor draw and the resume index are pinned to a plan fixed before the
  first attempt, and a plan that grew as the walk proceeded would break both.
* Seating is path-dependent under a ceiling, so a re-seat replays the sequence.
  Replaying arithmetic is free; replaying renders is not.

**One thing the seat does render**, and it is what stops a ceiling from being a
rule that can only refuse. When every candidate a seat holds has been rejected,
the seating asks for up to [`curation.gallery.EXTRA_PICKS`] more pictures at that
seat's own location — the palette head's next-best maps of the set it already
scored, screened for a hue family nothing tried has been — before it falls back.
The cost lands only on the seats the ceiling actually bit, and it lands as a
render rather than as an attempt: the field is dumped and the thirty-two recolours
are already scored, so what is missing is one picture. Rendering the same material
up front would have been 3,632 renders bought to change at most 150 decisions.
They are cached by `(location, mode, map)`, which is what keeps the re-seat replay
free.

The other half of the same problem is solved one step earlier and for free: when
the head picks a map whose **palette group another attempt of the plan has already
picked**, its next-ranked candidate takes the attempt instead. That is a pure
identity filter — no pixels, no state about pictures — and it makes the group cap
a property of the plan rather than something the seat has to refuse its way to.

## The three tests, in order, first failure naming the rejection

```text
group       one seat per palette group, unless this candidate's pixel cloud is
            more than TAU_GROUP from EVERY picture that group already seated.
dominance   pro rata: with n seats filled including this one, a colour may hold
            floor(K * t * n) + 1 of them. Only a candidate DOMINANT in an
            over-allowance colour is refused; carrying some of it is fine.
twin        no picture within TAU of TWINS already-shipped ones.
```

The order a seat takes them in is: every candidate that already exists, then the
extra picks it asks the renderer for, then the least-violating fallback, flagged.

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
dominant in that cell. At every seat the pass reads `u = need / seats left`:
above 1 the target **mandates** — only candidates dominant in the cell are
eligible; above 0.5 it **prefers** — dominant candidates rank ahead of the rest,
and the judge's order breaks the tie inside each half. Below that the judge
decides alone.

A target is not a floor that moves and not a pad. An unmet target is reported
**SHORT**, in the record and in the report, and the seats it could not fill are
filled by the pass's ordinary rule. The lever that actually meets a target is
upstream, at the plan: a carrier attempt renders a map chosen for the colour,
which is the only way a colour the palette head declines 83% of the time ever
reaches a seat at all. The extra picks above are the same lever at the other end
of the pass — the plan asks for the colours a target named, and the seat asks for
whatever colour it turns out to be missing.

Setting a target also **replaces the default allowance** for that cell and for
its family, so the ceiling and the target are denominated in one vector: asking
for green at 5% says green *should* be 5% of the gallery, and the ceiling then
lets it run to twice that.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from fractal_wallpapers.palettes import dominance, pixel_clouds

#: Seats one palette group may take, before the exemption.
#:
#: **One.** gallery3's 150 seats named 91 distinct groups and 59 of them sat above
#: this — `wallhaven_wallhaven-1joljg` seven times, `Furnace Rose` four, and one
#: 12-seat cluster of black-to-rose-to-white pictures that reads as a single
#: decision taken twelve times.
GROUP_CAP = 1

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
#: **0.0586**, Matt's, off the twins ladder. The curve there is steep and the
#: band is narrow: over gallery3's walk 0.040 rejects 5 seats, 0.050 rejects 14,
#: 0.060 rejects 30. Between those the test goes from a trim to a policy, and this
#: sits just under the policy end. It is a number **in the all-pixel metric** and
#: cannot be carried to the chromatic-only variant, which runs 5-15% lower at
#: every percentile that matters.
TAU = 0.0586

#: How many pictures inside [`TAU`] it takes to refuse. **Two**: one near
#: neighbour is a collection with a pair in it, which is what a gallery of a
#: hundred and fifty looks like when it is working. Three of a kind is the thing
#: a person notices.
TWINS = 2

#: The three tests, in the order they run. The first to fail names the rejection.
TESTS = ("group", "dominance", "twin")

#: `u = need / seats left` at or above this and only dominant candidates are
#: eligible; at or above [`PREFER`] and they merely rank first.
MANDATE = 1.0
PREFER = 0.5


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


class Lens:
    """What the ceiling needs to know about a candidate, read once and kept.

    Three questions — what colour is it, where is its pixel cloud, which palette
    group is it — and one implementation over the candidate renders. It is a class
    rather than three functions so a caller can hand the seating a different one:
    the tests do, and the dry replay does, and neither of them should have to put
    a render on disk to ask what a synthetic candidate is dominant in.

    `render_of(candidate)` is the **candidate render**, 640x360 ss2, and the same
    picture on both readings. A candidate whose render is not on disk reads as no
    colour and no cloud, and the seating lets it through untested rather than
    refusing it: a colour decision taken on no evidence is not a colour decision.
    """

    def __init__(self, render_of, group_of, cache: int = pixel_clouds.CACHE):
        self.render_of = render_of
        self.group_of = group_of
        #: `name -> render`, filled the first time a candidate is looked at, so
        #: the cloud cache can be addressed by the caller's own ids.
        self._paths: dict = {}
        self.clouds = pixel_clouds.Clouds(self._paths.get, cache=cache)
        self._readings: dict = {}
        self.unreadable: set = set()

    @staticmethod
    def name_of(candidate: dict) -> str:
        return str(candidate["candidate"])

    def see(self, candidate: dict) -> str:
        """Register where this candidate's render is, and return its id."""
        name = self.name_of(candidate)
        if name not in self._paths:
            self._paths[name] = self.render_of(candidate)
        return name

    def reading(self, candidate: dict):
        """This candidate's [`dominance.Reading`], or `None` if it has no picture."""
        name = self.see(candidate)
        if name not in self._readings:
            picture = self._paths[name]
            try:
                self._readings[name] = None if picture is None else dominance.of_picture(picture)
            except dominance.DominanceError:
                self._readings[name] = None
            if self._readings[name] is None:
                self.unreadable.add(name)
        return self._readings[name]

    def cloud(self, candidate: dict):
        """This candidate's pixel-cloud signature, or `None` if it has no picture."""
        return self.clouds.of(self.see(candidate))

    def group(self, candidate: dict) -> str:
        """Which palette group this candidate's map belongs to."""
        return self.group_of(candidate)

    def hold(self, candidate: dict) -> None:
        """Keep this picture's cloud: it is seated, and everything after is compared to it."""
        self.clouds.hold(self.see(candidate))

    def release(self) -> None:
        """Nothing is seated any more. A seating round begins here."""
        self.clouds.release()

    def price(self) -> dict:
        return {
            **self.clouds.price(),
            "readings": len(self._readings),
            "unreadable": len(self.unreadable),
        }


@dataclass
class Rule:
    """The constants and the targets. One per pass; carries no seating state."""

    lens: Lens
    #: `{cell: fraction}` as the caller asked for it. Cells only — a target is
    #: never set on a family, though setting one moves a family's allowance.
    targets: dict = field(default_factory=dict)
    group_cap: int = GROUP_CAP
    tau_group: float = TAU_GROUP
    k: int = K
    tau: float = TAU
    twins: int = TWINS

    def __post_init__(self) -> None:
        self.targets = {str(cell): float(value) for cell, value in (self.targets or {}).items()}
        self._share: dict = {}
        for cell, value in self.targets.items():
            self._share[cell] = value
            family = dominance.family_of(cell)
            if family is not None:
                # SUMMED and not replaced outright, for the one case the ruling
                # does not spell out: two targeted cells of one family both have
                # to fit under their family's allowance, and a family holding the
                # larger of the two would refuse the smaller one's last seats.
                self._share[family] = self._share.get(family, 0.0) + value

    def share(self, name: str) -> float:
        """The target rate for one cell or family: the set one, or uniform."""
        if name in self._share:
            return self._share[name]
        return FAMILY_SHARE if name in dominance.families() else CELL_SHARE

    def allowed(self, name: str, seats: int) -> int:
        """`floor(K * t * n) + 1` — how many of the first `n` seats may be this colour."""
        return int(math.floor(self.k * self.share(name) * max(0, int(seats)))) + 1

    def wanted(self, cell: str, n: int) -> int:
        """`ceil(t * N)` — how many pictures a target asks for out of `N` seats."""
        return int(math.ceil(self.targets[cell] * int(n)))

    def begin(self, seats: int) -> Seating:
        """A fresh sequential seating over `seats` slots. Every round starts here."""
        self.lens.release()
        return Seating(self, int(seats))

    def config(self) -> dict:
        """Every constant, for `config.ceiling` on the pass record."""
        return {
            "acts": "the seating leg, sequentially in the slots' walk order",
            "group_cap": int(self.group_cap),
            "tau_group": float(self.tau_group),
            "k": int(self.k),
            "cell_share": CELL_SHARE,
            "family_share": FAMILY_SHARE,
            "allowance": "floor(k * t_c * n) + 1, n = seats filled including this one",
            "reject": "only a candidate that is itself DOMINANT in an over-allowance "
            "cell or family",
            "tau": float(self.tau),
            "twins": int(self.twins),
            "tests": list(TESTS),
            "mandate": MANDATE,
            "prefer": PREFER,
            "dominance": dominance.RULE,
            "metric": pixel_clouds.METRIC,
            "targets": dict(sorted(self.targets.items())),
            "target_share": dict(sorted(self._share.items())),
        }


class Seating:
    """What the seats before this one have accumulated, and the three tests.

    One per seating round and never reused: a re-seat replays the whole sequence,
    which is the same thing as beginning again over the same slots in the same
    order.
    """

    def __init__(self, rule: Rule, seats: int):
        self.rule = rule
        self.seats = int(seats)
        #: Shipped pictures in seat order, by candidate name.
        self.shipped: list = []
        #: The clouds of the shipped pictures that HAVE one, and their names beside
        #: them. Two lists rather than one with holes: the twin test is a single
        #: subtraction over a stacked array, and a `None` in it would be a branch
        #: inside the hottest loop of the seating.
        self._clouds: list = []
        self._cloud_names: list = []
        #: `colour -> pictures shipped that are dominant in it`, cells and families.
        self.counts: dict = {}
        #: `palette group -> [candidate names]`.
        self.groups: dict = {}
        #: Every refusal, in order: the pass record's own rows.
        self.rejections: list = []
        #: Seats that took the least-violating candidate because nothing cleared.
        self.fallbacks: list = []
        #: Seats where a mandate could not be honoured because nothing carried it.
        self.unmet: list = []
        #: Every group-cap exemption used, with the distance that earned it.
        self.exemptions: list = []
        #: What the targets did at each seat that one of them steered.
        self.steered: list = []
        #: Which slot is being decided, and how many seats are left including it.
        self.seat_id: str = ""
        self.remaining = int(seats)
        self.decided = 0
        #: Shipped pictures the dominance rule names no cell for.
        self.colourless = 0

    # --- the reading ------------------------------------------------------- #
    def colours(self, candidate: dict) -> tuple:
        """`(cells, families)` this candidate is dominant in; empty where unreadable."""
        reading = self.rule.lens.reading(candidate)
        return ((), ()) if reading is None else (reading.cells, reading.families)

    def carries(self, candidate: dict, name: str) -> bool:
        reading = self.rule.lens.reading(candidate)
        return reading is not None and reading.carries(name)

    # --- targets ----------------------------------------------------------- #
    def urgency(self) -> dict:
        """`{cell: need / seats left}` for every target still short. Empty when none are."""
        left = max(1, int(self.remaining))
        out = {}
        for cell in self.rule.targets:
            need = self.rule.wanted(cell, self.seats) - self.counts.get(cell, 0)
            if need > 0:
                out[cell] = need / left
        return out

    def steer(self, pool: list) -> tuple:
        """The pool in the order this seat should try it, and what the targets did.

        Stable throughout: the judge's order is what arrives and what survives
        inside every tier, so a target reorders candidates and never re-ranks them.
        """
        urgent = self.urgency()
        if not urgent:
            return pool, {}
        ranked = sorted(urgent.items(), key=lambda item: (-item[1], item[0]))
        note = {"urgency": {cell: round(value, 4) for cell, value in ranked}}
        mandated = [cell for cell, value in ranked if value >= MANDATE]
        sequence = pool
        if mandated:
            note["mandated"] = mandated
            eligible = [
                candidate
                for candidate in pool
                if any(self.carries(candidate, cell) for cell in mandated)
            ]
            if eligible:
                # Dominant in ANY mandating cell and not in all of them: two cells
                # both demanding every remaining seat cannot both be honoured, and
                # an intersection would empty the seat for both instead of filling
                # it for one.
                sequence = eligible
            else:
                note["mandate_unmet"] = mandated
                self.unmet.append({"seat": self.seat_id, "cells": list(mandated)})
        prefer = next((cell for cell, value in ranked if value >= PREFER), None)
        if prefer is not None:
            note["preferred"] = prefer
            sequence = sorted(
                sequence, key=lambda candidate: 0 if self.carries(candidate, prefer) else 1
            )
        self.steered.append({"seat": self.seat_id, **note})
        return sequence, note

    # --- the three tests ---------------------------------------------------- #
    def _group_failure(self, candidate: dict, cloud) -> dict | None:
        """Test one: the palette group cap, and the distance that exempts it."""
        group = self.rule.lens.group(candidate)
        seated = self.groups.get(group, [])
        if len(seated) < self.rule.group_cap:
            return None
        if cloud is None:
            return {
                "test": "group",
                "which": group,
                "seated": len(seated),
                "cap": self.rule.group_cap,
                "nearest": None,
                "strain": 1.0,
            }
        rows = [
            self._clouds[self._cloud_names.index(name)]
            for name in seated
            if name in self._cloud_names
        ]
        if not rows:
            return None
        nearest = min(pixel_clouds.distances(cloud, rows))
        if nearest > self.rule.tau_group:
            # The exemption, and the one place the ceiling lets something past
            # rather than refusing it. Recorded, because "how often did the cap
            # not act" is the question that says whether the exemption is a gate
            # or a formality.
            self.exemptions.append(
                {
                    "seat": self.seat_id,
                    "candidate": self.rule.lens.name_of(candidate),
                    "group": group,
                    "seated": len(seated),
                    "nearest": round(nearest, 6),
                }
            )
            return None
        return {
            "test": "group",
            "which": group,
            "seated": len(seated),
            "cap": self.rule.group_cap,
            "nearest": round(nearest, 6),
            "tau_group": self.rule.tau_group,
            "strain": round((self.rule.tau_group - nearest) / self.rule.tau_group, 6),
        }

    def _dominance_failure(self, candidate: dict) -> dict | None:
        """Test two: the pro-rata allowance, against what this candidate is OF."""
        cells, families = self.colours(candidate)
        seats = len(self.shipped) + 1
        worst = None
        for level, names in (("cell", cells), ("family", families)):
            for name in names:
                allowed = self.rule.allowed(name, seats)
                have = self.counts.get(name, 0)
                if have + 1 <= allowed:
                    continue
                failure = {
                    "test": "dominance",
                    "level": level,
                    "which": name,
                    "have": have,
                    "allowed": allowed,
                    "seats": seats,
                    "target_share": round(self.rule.share(name), 6),
                    "strain": round((have + 1 - allowed) / allowed, 6),
                }
                if worst is None or failure["strain"] > worst["strain"]:
                    worst = failure
        return worst

    def _twin_failure(self, cloud) -> dict | None:
        """Test three: how many shipped pictures this one is inside [`TAU`] of."""
        if cloud is None or not self._clouds:
            return None
        near = [
            value for value in pixel_clouds.distances(cloud, self._clouds) if value < self.rule.tau
        ]
        if len(near) < self.rule.twins:
            return None
        return {
            "test": "twin",
            "which": len(near),
            "m": self.rule.twins,
            "tau": self.rule.tau,
            "nearest": round(min(near), 6),
            "strain": round((len(near) - self.rule.twins + 1) / self.rule.twins, 6),
        }

    def failures(self, candidate: dict) -> list:
        """Every test this candidate fails, in [`TESTS`] order. Empty means it clears.

        All three and not the first, deliberately. The **rejection** names the
        first — that is what a person reads — but the least-violating fallback has
        to compare candidates that failed different tests, and a cost read off
        whichever test happens to run first would rank by the test order rather
        than by how badly anything was broken.
        """
        cloud = self.rule.lens.cloud(candidate)
        found = [
            self._group_failure(candidate, cloud),
            self._dominance_failure(candidate),
            self._twin_failure(cloud),
        ]
        return [entry for entry in found if entry is not None]

    # --- the state one seat leaves behind ------------------------------------ #
    def at(self, seat_id: str, remaining: int) -> None:
        """Begin one seat: which slot it is, and how many are left including it."""
        self.seat_id = str(seat_id)
        self.remaining = max(1, int(remaining))

    def reject(self, candidate: dict, failures: list) -> dict:
        """Record one refusal and return the row the pass record keeps.

        The row names the **first** failing test, which is the answer to "why was
        this refused"; the rest are on it too, because a candidate that fails all
        three is a different finding from one that fails a cap by a hair, and a
        record that kept only the first could not tell them apart afterwards.
        """
        first = failures[0]
        row = {
            "seat": self.seat_id,
            "candidate": self.rule.lens.name_of(candidate),
            "test": first["test"],
            "margin": {name: value for name, value in first.items() if name != "test"},
        }
        if len(failures) > 1:
            row["also"] = [entry["test"] for entry in failures[1:]]
        self.rejections.append(row)
        return row

    def fell_back(self, candidate: dict, failures: list) -> dict:
        """Record a seat that had to take the least-violating candidate."""
        row = {
            "seat": self.seat_id,
            "candidate": self.rule.lens.name_of(candidate),
            "failed": [entry["test"] for entry in failures],
            "strain": strain(failures)[1],
        }
        self.fallbacks.append(row)
        return row

    def take(self, candidate: dict) -> None:
        """Seat one candidate: it is now part of what everything after it is tested against."""
        name = self.rule.lens.name_of(candidate)
        cloud = self.rule.lens.cloud(candidate)
        if cloud is not None:
            self.rule.lens.hold(candidate)
            self._clouds.append(cloud)
            self._cloud_names.append(name)
        self.shipped.append(name)
        cells, families = self.colours(candidate)
        if not cells:
            # A picture the rule names no colour for. Counted, because a ceiling
            # that never fires and a gallery whose pictures are all under the
            # dominance thresholds are the same log line and different findings.
            self.colourless += 1
        for colour in (*cells, *families):
            self.counts[colour] = self.counts.get(colour, 0) + 1
        self.groups.setdefault(self.rule.lens.group(candidate), []).append(name)

    def done(self) -> None:
        """One slot decided, filled or not. The walk moves on either way."""
        self.decided += 1

    # --- what it all came to -------------------------------------------------- #
    def targets(self) -> list:
        """Every target, met or **SHORT**. Never padded and never lowered."""
        out = []
        for cell in sorted(self.rule.targets):
            wanted = self.rule.wanted(cell, self.seats)
            have = self.counts.get(cell, 0)
            out.append(
                {
                    "cell": cell,
                    "fraction": self.rule.targets[cell],
                    "wanted": wanted,
                    "have": have,
                    "verdict": "met" if have >= wanted else "SHORT",
                    "short_by": max(0, wanted - have),
                }
            )
        return out

    def report(self) -> dict:
        """The whole of what the ceiling did, for the pass record."""
        by_test = dict.fromkeys(TESTS, 0)
        for row in self.rejections:
            by_test[row["test"]] = by_test.get(row["test"], 0) + 1
        cells = {
            name: count for name, count in self.counts.items() if name in set(dominance.cells())
        }
        families = {
            name: count for name, count in self.counts.items() if name in set(dominance.families())
        }
        over = {
            group: len(names)
            for group, names in self.groups.items()
            if len(names) > self.rule.group_cap
        }
        return {
            "seats": self.seats,
            "shipped": len(self.shipped),
            "rejections": list(self.rejections),
            "rejections_by_test": by_test,
            "fallbacks": list(self.fallbacks),
            "exemptions": list(self.exemptions),
            "mandate_unmet": list(self.unmet),
            "steered": list(self.steered),
            "targets": self.targets(),
            "dominance": {
                "cells": dict(sorted(cells.items(), key=lambda item: (-item[1], item[0]))),
                "families": dict(sorted(families.items(), key=lambda item: (-item[1], item[0]))),
                "no_dominant_cell": self.colourless,
            },
            "groups": {
                "distinct": len(self.groups),
                "over_cap": dict(sorted(over.items(), key=lambda item: (-item[1], item[0]))),
            },
            "lens": self.rule.lens.price(),
        }


def strain(failures: list) -> tuple:
    """How badly a candidate breaks the ceiling. Least-violating is least of this.

    `(tests failed, total strain)`, where each test's strain is its excess in
    units of what it was allowed — a group seat over a cap of one, a colour over
    its allowance, a twin over `m` — so three numbers in three different units
    become comparable without any of them being scaled by a constant somebody
    chose. Ties fall through to the judge's order at the call site, which is what
    makes the fallback deterministic.
    """
    return (len(failures), round(sum(float(entry["strain"]) for entry in failures), 6))


__all__ = [
    "CELL_SHARE",
    "FAMILY_SHARE",
    "GROUP_CAP",
    "K",
    "MANDATE",
    "PREFER",
    "TAU",
    "TAU_GROUP",
    "TESTS",
    "TWINS",
    "Lens",
    "Rule",
    "Seating",
    "TargetRefused",
    "parse_target",
    "strain",
]
