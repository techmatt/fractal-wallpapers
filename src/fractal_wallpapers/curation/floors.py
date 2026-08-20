"""Every number that removes a picture between a find and a release, in one file.

Curation decides three times — which locations are worth colouring, which
coloured candidates are worth keeping, which kept candidates take one of the
release's slots — and each decision used to be a threshold typed at its own call
site. This module is the single owner of all of them, and the reason it exists is
that a threshold is a point on **one head's probability scale**: `0.20` on the
location head means "confidently junk" and means nothing at all on a head that
has been retrained since. A number with no owner is a number nobody can restate
when the scale under it moves.

## A cut either ACTS or it ANNOTATES, and it says which

Two of the numbers here remove a picture. Every other cut in curation is an
[`Advisory`]: it is computed, written onto the record, and never allowed to drop
a row. That split is deliberate and it is the shape the source project converged
on after a head flip took its intake from about fourteen hundred locations to
sixteen — because the cut that did it was a *frozen verdict*, stamped into a row
on the day it was minted and read as gospel by a pipeline that had moved on.

Nothing here is frozen. Every cut is a comparison against a probability that is
read at the moment it is used, so a different floor, a different order and a
different budget are all a re-read away, and a head flip degrades the *rank
quality* of the old rows instead of deleting them.

## The two that act

* [`JUNK_FLOOR`] — on the location head's `P(≥3)`, at **two** sites now. At
  intake it says *do not spend colorize compute on this*; in the walk it says
  *do not stand on this*, which is the expansion half of a cut that used to do
  expansion and booking together. One number, one meaning — "the judging head is
  confident this is junk" — and both sites read it from here rather than
  restating it. Deliberately coarse: it is not an operating point, no evaluation
  derived it, and it must not be made per-partition. It sits at the
  confidently-junk end of a scale and leaves every judgement of quality to the
  person at the sheet.
* the **good floor**, and it is not declared here. `supply.currency.GOOD_FLOOR`
  already owns "this find is worth keeping" on the same head and the same scale,
  and curation asks the same question at the slot guarantee. A second copy of one
  number under a second name is exactly the six-site restatement this module was
  written to end, so it is re-exported and never restated.

## Both of them, and the great cut beside them, are now restatements

The junk floor was described here for most of a year as the one cut a head flip
could leave alone — coarse, semantic, nothing measured behind it. The 2026-08-20
location flip retired that idea. A head that reads *lower* everywhere keeps the
sentence "the judge is confident this is junk" true at a **different volume**:
0.20 on the retrained head would have removed a far larger share of the standing
supply than 0.20 on the retired one, and a cut whose volume moves at a flip is a
policy change nobody voted for. Semantic is not scale-free.

So all three location cuts are [`Restatement`]s now, each measured the same way —
the candidate score passing the same fraction of one fixed reference pool as the
retired head's cut passed — and each stamped with the artifact it was measured
on, so the *next* flip refuses at the first comparison. What that method fixes is
volume and nothing else: no label was read, and where a keeper starts on the new
scale is still the open question it was.

## The render heads: one bar acts now, the other still only annotates

A render head's floor would be its own production gate — the score above which a
finished picture is worth releasing. This project measured neither: the two render
judges shipped at BORDERLINE and FAIL against their pre-registered bars. So both
shipped as advisories at each head's own natural rank cutpoint, written onto every
release record, on the reasoning that *"was a bar at this height buying anything"*
stays answerable off the accumulating record rather than only off runs made while
a bar was enforcing.

The strange head's advisory was **promoted to an acting bar** on 2026-08-17, by a
review verdict rather than by a measurement: Matt read `run2` and the eleven
released strange rows that sat below 0.50 were all bad, the head had been right
about every one of them, and the path that seated them was padding strange slots
out of thin passing supply. So [`STRANGE_RELEASE_BAR`] acts at release selection —
a strange row below it is not seated, and a strange slot with no passing supply
goes unfilled. The smooth head stays advisory: its own below-advisory rows belong
to a mix-ratio decision that has not been taken.

That bar has since been **restated against the head it is on**, which is the whole
reason this module exists. The 4-class retrain moved the strange head's whole
probability scale, and a float set on the retired head's scale says nothing at all
on the new one — so the value is no longer the advisory's height carried over by
policy, it is a *measurement* off the labels: [`Restatement`] carries the number,
the sha of the head it was read against, how it was read, and when. It is still
a `>=3` bar. The head now emits a `P(>=4)` and that cutpoint gates nothing: a four
is a class the release path prefers where it finds one, not a second floor.

That split is why there are two types, and they live in [`fractal_wallpapers.cuts`]
rather than here: three of the four acting cuts sit on the location head's scale
and two of those belong to the supply engine, so a class imported from this module
would make `supply` depend on `curation`. The numbers stay here; the kinds are
shared. An [`Advisory`] is computed, recorded, and structurally unable to remove a
row — no `gate()`, no `acts()` beside it. A [`Bar`] is the other thing, named as
the other thing, and [`release_cut`] hands out whichever one a head actually has.

Both carry the sha256 of the shipped head they read. That is this repository's
head version: a head is a file with a hash, the manifest names it, and a cut whose
stamp disagrees with the live artifact refuses rather than producing a
plausible-looking column — or, now, a seating decision — about a scale that no
longer exists.

The two kinds stamp themselves differently, and the difference is the same one
that makes them two classes. An advisory is the *natural cutpoint of whatever
scale is live*, so it stamps the live artifact and only catches a re-ship that
lands mid-run. A bar is a number somebody measured on one named head, so it stamps
**that** head — [`Restatement.head_sha256`] — and refuses from the first call after
a flip. Nobody had to remember to restate this one; the check would have said so.
"""

from __future__ import annotations

from fractal_wallpapers.cuts import (
    Advisory,
    Bar,
    Cut,
    HeadStampMismatch,
    Restatement,
    live_stamp,
)
from fractal_wallpapers.supply.currency import GOOD_FLOOR, GREAT_CUT

#: The reference pool all three location cuts were volume-matched over, named once
#: because three restatements that spelled it three ways would be three claims.
LOCATION_POOL = (
    "the 28,072-location curation sidecar (artifacts/curation/supply_scores.jsonl), "
    "every row read through the canonical 640x360ss2 view its own stored score was "
    "taken off"
)

#: **The junk floor**, and the reading that put it here.
#:
#: On the location head's `P(≥3)`, at **two** sites: at intake it says *do not
#: spend colorize compute on this*, and in the walk it says *do not stand on
#: this*. One number, one meaning — "the judging head is confident this is junk".
#:
#: It used to be `0.20` on the retired head, and it used to be described as the
#: one cut a head flip could leave alone: coarse, semantic, no evaluation behind
#: it. That was wrong in the only way that matters. The regime-robust retrain
#: moved the whole `P(≥3)` scale down, and 0.20 on the new head removes a
#: different — much larger — share of the standing supply than 0.20 on the old
#: one did. A cut whose *volume* moves is not a cut a flip left alone; it is a
#: policy change nobody voted for. So this one is restated with the other two,
#: and it is still coarse and still not an operating point: what the measurement
#: fixes is how much material it removes, and nothing else.
JUNK_FLOOR_RESTATED = Restatement(
    value=0.100,
    head_sha256="f8f805119a0ff9612b2076f0edafdb4125f0330b3fd48ace71336f93664851ba",
    method=(
        "volume matched on a fixed reference pool. The retired head's 0.20 passed 15,161 of "
        "28,072 canonical reads (54.01%); this is the candidate score that passes that same "
        "count — the 15,161st largest candidate read, 0.100580 — rounded DOWN to the next "
        "0.005, because a floor rounded up removes supply the cut it restates did not. "
        "Realized 15,182 passing (54.08%). NOT a calibration: no label was read here and "
        "nothing re-measured where junk ends on the new scale."
    ),
    reference_pool=LOCATION_POOL,
    date="2026-08-20",
)

#: The height itself, for every reader that only wants the number.
JUNK_FLOOR = JUNK_FLOOR_RESTATED.value

#: Why the junk floor sits where it does, carried onto every row it stamps.
JUNK_FLOOR_BASIS = (
    "the confidently-junk end of the location head's own scale, restated by volume at the "
    f"2026-08-20 head flip and never per-partition: {JUNK_FLOOR_RESTATED}"
)

#: A partition emits at most `floor(passing supply / this)` pictures. The rule is
#: *show me one only if there were four to choose from*, and its whole point is
#: the zero: a partition with three floor-passing candidates ships nothing rather
#: than shipping its own least-bad row, and the run says so in one line.
THIN_SUPPLY_DIVISOR = 4

#: At most this many release picks from one near-duplicate group, per run. A cap,
#: not a quota — a group with one strong row still ships one. This is the whole
#: of the diversity rule, and it is deliberately something a person can read off
#: a sheet ("no more than two of one look") rather than a marginal-gain number.
CLUSTER_CAP = 2

#: Colorize attempts per release slot. A head's attempt budget is this times the
#: slots it is asked to fill, so the two heads are sized against release need and
#: never against each other.
#:
#: The same coarse four as [`THIN_SUPPLY_DIVISOR`], and the two meeting is not a
#: coincidence worth collapsing: they are about different populations — attempts
#: spent against candidates available — and a partition whose slots respect its
#: emit cap has `4·slots ≤ 4·floor(supply/4) ≤ supply`, so the two rules agree
#: exactly when they should. Moving either alone is a real change and reads as one.
ATTEMPT_MULTIPLIER = 4

#: Where a render head's advisory sits: the natural rank cutpoint of a CORN
#: probability, which is the midpoint of the scale and not an operating point.
#: It answers "would this head call the picture a wallpaper", which is a sentence
#: about the head rather than a bar somebody measured.
RELEASE_ADVISORY = 0.50

#: **The strange head's ACTING release bar**, and the reading that set it.
#:
#: Not the advisory's height any more. The bar was promoted at 0.50 because that
#: was where the advisory sat, and the retrain that widened the head to four
#: classes moved every probability under it — so the number was restated the only
#: way a release bar can honestly be restated, off the verdicts a person actually
#: cast, and it landed well above where policy had left it.
STRANGE_RELEASE_BAR = Restatement(
    value=0.685,
    head_sha256="a011188bbcaaeef49421146e31b7eb411db57044d653c2e0986d5040d32e35de",
    method=(
        "the labels-derived crossover. Isotonic regression of P(the human said >=3) against "
        "this head's own P(>=3), over all 3,085 labeled strange_render pictures scored through "
        "the staged artifact, ties pooled, non-decreasing; the crossing is the LOWEST score "
        "whose fitted agreement reaches a half, and the bar is that crossing rounded up to the "
        "next 0.005. Crossing 0.6809, 95% cluster bootstrap over places [0.540, 0.776]; the "
        "held-out selection slice crosses at 0.6987 on its own. Declared before it was read, "
        "and the roundings go up because a bar is a floor. STILL A >=3 BAR: the head's fourth "
        "class is preferred where it appears and gates nothing."
    ),
    reference_pool="all 3,085 labeled strange_render pictures, over 850 places",
    date="2026-08-17",
)

#: Which render heads' release cut ACTS, and at what height. Everything not in
#: here gets an [`Advisory`]. Spelled out rather than imported from `budget.HEADS`
#: only because that module already imports this one; the suite checks the
#: spelling against it.
ACTING_RELEASE_BARS = {"strange_render": STRANGE_RELEASE_BAR}

#: Why the one acting bar acts, and what its height now rests on. Carried onto
#: every row it stamps: the two halves have different provenance and a row that
#: reported one of them would misstate the other.
STRANGE_BAR_BASIS = (
    "an ACTING bar by Matt's review verdict of 2026-08-17 — every one of run2's eleven "
    "released strange rows below the advisory was bad, the head was right about all eleven, "
    "and the release path that seated them was padding strange slots from thin passing "
    f"supply. THAT the cut acts is that verdict; WHERE it sits is a measurement: "
    f"{STRANGE_RELEASE_BAR}"
)


def release_cut(head: str) -> Advisory | Bar:
    """The release cut on a finished-render head's score — whichever kind it has.

    THE dispatcher, and the reason a caller never decides for itself whether a
    head gates: [`ACTING_RELEASE_BARS`] is the one place that answers it, and
    every other site reads the answer off the returned type.

    Built at call time so its stamp is the live artifact's, which is the whole
    point of the stamp: a cut object cached at import would carry the hash of
    whatever was shipped when the process started.
    """
    if head in ACTING_RELEASE_BARS:
        restated = ACTING_RELEASE_BARS[head]
        return Bar(
            name=f"{head}_release",
            value=float(restated.value),
            head=head,
            # The head the height was MEASURED on, not the one that happens to be
            # shipped. That is what makes the stamp check bite on a flip.
            stamp=restated.head_sha256,
            basis=STRANGE_BAR_BASIS,
        )
    return release_advisory(head)


def release_bar(head: str) -> Bar | None:
    """The acting bar this head is gated on, or `None` where nothing gates it.

    What the release selection asks. `None` is not a weaker bar — it is no bar,
    and the selection must go on picking exactly as it did before.
    """
    cut = release_cut(head)
    return cut if isinstance(cut, Bar) else None


def release_advisory(head: str) -> Advisory:
    """The advisory a finished-render head's score is annotated against.

    Only the heads with no acting bar have one. Asking for an advisory on a head
    whose cut acts is a category error rather than a weaker reading of it, so it
    refuses: a caller that got an object with no `acts` back would go on to seat
    a row the bar had rejected.
    """
    if head in ACTING_RELEASE_BARS:
        raise ValueError(
            f"{head!r}'s release cut ACTS at {ACTING_RELEASE_BARS[head]} — it is a Bar, not an "
            f"advisory. Call release_cut() and read the type, or release_bar() if the question "
            f"is whether this head gates."
        )
    return Advisory(
        name=f"{head}_release",
        value=RELEASE_ADVISORY,
        head=head,
        stamp=live_stamp(head),
        basis="the natural rank cutpoint of this head's own P(>=3) — not an operating point "
        "and no evaluation derived it. No release gate has been measured for this head, and "
        "an advisory that pretended to be one would be a bar nobody could defend. It "
        "annotates so the question stays answerable off the record.",
    )


def junk_floor_cut() -> Bar:
    """The junk floor as the acting cut it is, stamped with the head it was read on.

    Built at call time and stamped with [`JUNK_FLOOR_RESTATED`]'s sha rather than
    with whatever is shipped now — the same rule the release bar follows, and for
    the same reason: the next location flip must refuse here on its first call
    instead of spending a colorize budget against a scale nobody restated.
    """
    return Bar(
        name="junk_floor",
        value=float(JUNK_FLOOR_RESTATED.value),
        head="location",
        stamp=JUNK_FLOOR_RESTATED.head_sha256,
        basis=JUNK_FLOOR_BASIS,
    )


def passes_junk_floor(score) -> bool:
    """THE intake comparison. A missing score reads as not passing.

    A function rather than a bare `>=` at each site, for the same reason the good
    floor is one: an unscored candidate has no verdict to spend compute on, and
    that has to be decided in one place rather than three.
    """
    return junk_floor_cut().acts(score)


def passes_good_floor(score) -> bool:
    """THE slot-guarantee trigger, on the same score at the higher of the two heights.

    Deliberately the good floor and not the junk floor. The guarantee asks *does
    this partition have anything worth keeping*, where intake only asks *is this
    not obvious junk*; a guarantee triggered at the junk floor would seat a
    partition whose whole supply the run itself would not call good.
    """
    from fractal_wallpapers.supply import currency

    return currency.passes_good_floor(score)


def emit_cap(passing: int) -> int:
    """The most a partition may release: `floor(passing supply / THIN_SUPPLY_DIVISOR)`."""
    return max(0, int(passing)) // THIN_SUPPLY_DIVISOR


def summary() -> dict:
    """Every cut, what it is on, and whether it acts. For a run's own banner."""
    from fractal_wallpapers.supply import currency

    return {
        "acting": {
            "junk_floor": {
                "value": JUNK_FLOOR,
                "head": "location",
                "restated_against": JUNK_FLOOR_RESTATED.head_sha256,
                "restated_on": JUNK_FLOOR_RESTATED.date,
                "reference_pool": JUNK_FLOOR_RESTATED.reference_pool,
                "method": JUNK_FLOOR_RESTATED.method,
                "where": "intake, the colorize draw; and the walk's expansion tier",
            },
            "good_floor": {
                "value": GOOD_FLOOR,
                "head": "location",
                "restated_against": currency.GOOD_FLOOR_RESTATED.head_sha256,
                "restated_on": currency.GOOD_FLOOR_RESTATED.date,
                "reference_pool": currency.GOOD_FLOOR_RESTATED.reference_pool,
                "method": currency.GOOD_FLOOR_RESTATED.method,
                "where": "the slot guarantee's trigger; and the walk's booking tier",
                "owner": "supply.currency.GOOD_FLOOR — re-exported, never restated",
            },
            "great_cut": {
                "value": GREAT_CUT,
                "head": "location",
                "restated_against": currency.GREAT_CUT_RESTATED.head_sha256,
                "restated_on": currency.GREAT_CUT_RESTATED.date,
                "reference_pool": currency.GREAT_CUT_RESTATED.reference_pool,
                "method": currency.GREAT_CUT_RESTATED.method,
                "where": "the currency: a keeper at or above it is a class 4, weighted ten "
                "to one against a class 3",
                "owner": "supply.currency.GREAT_CUT — re-exported, never restated",
            },
            **{
                f"{head}_release_bar": {
                    "value": restated.value,
                    "head": head,
                    "restated_against": restated.head_sha256,
                    "restated_on": restated.date,
                    "method": restated.method,
                    "where": "release selection: a row below it is not seated, and a slot "
                    "with no passing supply goes unfilled",
                    "basis": STRANGE_BAR_BASIS,
                }
                for head, restated in sorted(ACTING_RELEASE_BARS.items())
            },
        },
        "advisory": {
            "render heads with no acting bar": RELEASE_ADVISORY,
            "acting instead": sorted(ACTING_RELEASE_BARS),
        },
        "caps": {
            "thin_supply_divisor": THIN_SUPPLY_DIVISOR,
            "cluster_cap": CLUSTER_CAP,
            "attempt_multiplier": ATTEMPT_MULTIPLIER,
        },
    }


__all__ = [
    "ACTING_RELEASE_BARS",
    "ATTEMPT_MULTIPLIER",
    "CLUSTER_CAP",
    "GOOD_FLOOR",
    "GREAT_CUT",
    "JUNK_FLOOR",
    "JUNK_FLOOR_BASIS",
    "JUNK_FLOOR_RESTATED",
    "LOCATION_POOL",
    "RELEASE_ADVISORY",
    "STRANGE_BAR_BASIS",
    "STRANGE_RELEASE_BAR",
    "THIN_SUPPLY_DIVISOR",
    "Advisory",
    "Bar",
    "Cut",
    "HeadStampMismatch",
    "Restatement",
    "emit_cap",
    "junk_floor_cut",
    "live_stamp",
    "passes_good_floor",
    "passes_junk_floor",
    "release_advisory",
    "release_bar",
    "release_cut",
    "summary",
]
