"""What standing each production mode has, as one table with one owner.

The engine's catalog answers *does this mode exist* and *is it shippable at all*
([`engine.production_modes`], and the tier behind it). It does not answer *is
this mode worth spending on*, and until now nothing did: the answer was two
constants in [`curation.depth`] — `DEMOTED` and `BREADTH_DEMOTED` — that a depth
run read and nothing else in the tree did. A mode could be ruled out of the draw
that measures depth and still be drawn by every mine, every labeling batch and
every gallery, which is a footnote on one leg rather than a standing.

This is the table. Mode to weight, and the weight is one of three:

* **0 — niche.** Out of the labeling rosters, out of the default mining rosters,
  out of gallery emission. Nothing is deleted: a niche mode keeps its labels, its
  ledger rows and its pictures, it still resolves by name, and a verdict already
  exported on one still ingests. It stops being *bought more of*.
* **1 — normal.** Drawn like anything else.
* **2 — promoted.** Recorded and not yet wired. There is no MODE-side cap at
  seating, and the only mode-side floor is [`solve.mode_floor`], `n // 100`, so a
  weight of 2 has nothing to bind on today that would move more than a seat or
  two at `n = 150`. It is written down because the decision was made; what it
  will bind on is a separate question, and pretending it already binds would
  answer it wrongly.

## Two layers, one word

`niche` is also the engine's word, for the tier that keeps `de` renderable by
name and out of every production draw. The two are the same *idea* at different
layers, and they are deliberately not merged. The engine's tier is a claim about
what the corpora were collected over; this table is a claim about what is worth
collecting next, it has to express a third value a two-valued tier cannot, and
moving a mode between them in Rust would change the catalog the finished-render
judges were trained against. So a mode the engine tiers niche never appears here
at all, and [`check`] refuses if one does.

## Reading the table is not syncing it

Several places read this — the mode draw, the mine and hunt rosters, the depth
roster, the gallery pool and the mode floors — because a standing only one leg
honoured is the thing this replaces. What must not happen is a *second* table. If
a mode's standing needs saying anywhere else, it is said by reading this one.
"""

from __future__ import annotations

#: Out of every draw and out of the gallery. Its existing material stands.
NICHE = 0

#: Drawn like anything else.
NORMAL = 1

#: Recorded, not yet wired. See the module docstring.
PROMOTED = 2

WEIGHTS = (NICHE, NORMAL, PROMOTED)

#: **Mode to weight, and the only place a mode's standing is written.**
#:
#: Counted over the ingested `strange_render` store as it stood on 2026-08-29 —
#: 5,110 rows resolving to 4,656 renders — and counted as the **tier-4 rate**,
#: because a 4 is the unit of currency and a standing is a claim about how often a
#: mode buys one.
#:
#: **Every count below is over the 4,656 renders, one label a render**, which is
#: the basis [`floors`] states its cuts on too. Per *row* each reads a little
#: differently — `itinerary` is 46 fours in 208 rows against 44 in 201 renders —
#: and a figure quoted off one basis beside sixteen quoted off the other is a
#: ranking nobody can read. Two numbers here said `rows` and meant renders.
#:
#: The four at 0 are the modes a round of human labels could not make a case for:
#: `gaussian_int` 7 fours in 296 renders (2.4%), `smooth_trap_circle` 10 in 256 (3.9%),
#: `trap_circle` 12 in 260 (4.6%) and `direct_trap_ring` 20 in 342 (5.8%).
#:
#: **The cut is not a pure ranking on that rate and cannot be read as one.**
#: `direct_trap_multiply` (2.0%) and `direct_trap_lines` (2.8%) are accepted and read
#: below all four. What separates the four is tier-3-or-better, where they are the
#: bottom four at 9.1%, 17.5%, 19.2% and 19.9% and no accepted mode reads under 25.9%:
#: the two `direct_trap_*` modes rarely buy a 4 but reliably return a usable picture,
#: and a mode that returns neither is the one there is no case for.
#:
#: The seven at 2 are the ones that did: `itinerary` 44 fours in 201 renders
#: (21.9%), `threads` 36 in 167 (21.6%), `smooth_angle_min` 30 in 159 (18.9%),
#: `smooth_mean_angle` 34 in 193 (17.6%), `smooth_stripe` 34 in 239 (14.2%),
#: `stripe` 26 in 203 (12.8%) and `tia` 31 in 310 (10.0%).
#:
#: **A pooled rate for a mode that was aimed at is not a base rate.** Nine of the
#: seventeen were drawn by a head-top leg — per mode, the best rows the rank key
#: could find after a leg aimed at that mode, which is a best-of draw and not a
#: sample of what the mode returns unprompted. That arm is a quarter to a third of
#: every row the store holds about six of the nine and 55% of `trap_circle`'s, and it
#: is the whole of the difference: `curvature` reads 10.3% pooled (31 fours in 301)
#: but 28.3% on the arm against 2.4% on the 209 rows outside it, and
#: `smooth_curvature` 21.6% on the arm against **no fours at all** in 183. Read the
#: pooled figure for `curvature`, `smooth_curvature`, `itinerary`,
#: `direct_trap_screen`, `direct_trap_lines` and the four niche modes as a ceiling
#: rather than as a rate.
#:
#: The two that moved on 2026-08-29 moved on that arm. `itinerary` 1 → 2: the highest
#: pooled tier-4 rate of the seventeen, and 38 of the 60 the aimed leg drew for it
#: came back a 4 (63.3%), the best yield of the nine. **Its one flat draw reads
#: 3.6%** — `itinerary_promotion`, 4 fours in 110 over 08-17/18 (5 in 111, 4.5%, per
#: row), an independent admitted-stock draw sharing no location with the aimed arm —
#: and that batch's own record in `data/strange_render/batches.jsonl` says even
#: *that* measures agreement with the head rather than a base rate. The 21.9% is a
#: ceiling with a 3.6% underneath it, and neither end is a flat rate.
#: `curvature` 0 → 1: 31 fours pooled, level with `tia`'s 31, on the third-best aimed
#: yield of the nine. Neither is a base rate; a mode promoted on a best-of draw is a
#: mode to re-count once it has been drawn flat.
#:
#: **`itinerary`'s 21.9% was over a population half of which was not `itinerary`,
#: and the weight has NOT been changed here on that.** 107 of its 201 renders are
#: modulates whose texture said nothing, which [`routed_mode`] below rules smooth —
#: measured 2026-08-31 against the engine's own report, reproducing the shift-pair
#: audit's ledger figures partition by partition. Read on the 94 that remain,
#: `itinerary` is **16 fours in 94 (17.0%)**, fourth of the seventeen behind
#: `threads` 21.6%, `smooth_angle_min` 18.9% and `smooth_mean_angle` 17.6%; the 107
#: that left read 26.2% and are the smooth judge's. Its tier-3-or-better is
#: unmoved — 54.2% recorded against 54.3% after — so the split is entirely in where
#: the fours sat. It is still above every weight-1 mode (`exp_smoothing`, the best
#: of them, is 14.7%), so nothing here is obviously wrong; what is gone is the claim
#: that it is the top of the seventeen, which is the sentence the 1 → 2 was written
#: on. **Moving the weight is a ruling and not a repair**, and this figure is
#: recorded so that whoever takes it is taking it on a number that is about the
#: mode.
MODE_POLICY: dict[str, int] = {
    # --- 0: niche ---
    "trap_circle": NICHE,
    "gaussian_int": NICHE,
    "smooth_trap_circle": NICHE,
    "direct_trap_ring": NICHE,
    # --- 1: normal ---
    "smooth": NORMAL,
    "exp_smoothing": NORMAL,
    "curvature": NORMAL,
    "smooth_curvature": NORMAL,
    "direct_trap_screen": NORMAL,
    "direct_trap_multiply": NORMAL,
    "direct_trap_lines": NORMAL,
    # --- 2: promoted ---
    "tia": PROMOTED,
    "stripe": PROMOTED,
    "threads": PROMOTED,
    "smooth_stripe": PROMOTED,
    "smooth_mean_angle": PROMOTED,
    "smooth_angle_min": PROMOTED,
    "itinerary": PROMOTED,
}


class PolicyRefused(RuntimeError):
    """The table and the engine's catalog do not describe the same roster."""


def _production() -> list[str]:
    """Every mode the engine's own tier lets a production draw pick, in catalog order."""
    from fractal_wallpapers import engine

    return list(engine.production_modes())


def weight_of(mode: str) -> int:
    """One mode's weight. A mode the table does not name is refused.

    Refused rather than defaulted to [`NORMAL`]: a mode added to the engine and
    not to this table has no standing, and quietly giving it one is how a table
    that is meant to be exhaustive stops being read.
    """
    name = str(mode)
    if name not in MODE_POLICY:
        raise PolicyRefused(
            f"{name!r} carries no weight in MODE_POLICY. Every production mode has a "
            f"standing, and a mode that has just arrived in the engine's catalog needs one "
            f"written here before anything can draw it."
        )
    return MODE_POLICY[name]


def at(weight: int) -> list[str]:
    """Every mode at one weight, in the engine's catalog order.

    Catalog order and not table order, so a report over these reads the way every
    other per-mode table in this project reads.
    """
    held = {name for name, value in MODE_POLICY.items() if value == int(weight)}
    return [name for name in _production() if name in held]


def niche() -> list[str]:
    """The weight-0 modes: out of the draws and out of the gallery."""
    return at(NICHE)


def promoted() -> list[str]:
    """The weight-2 modes. Recorded; nothing reads this to make a decision yet."""
    return at(PROMOTED)


def accepted() -> list[str]:
    """**Every mode a draw may pick and a gallery may seat**, in catalog order.

    The roster every wired consumer reads. It is the engine's production roster
    less [`niche`], so a mode the engine retires leaves this by itself and a mode
    ruled niche here leaves it without an edit to the engine.
    """
    out = set(niche())
    return [name for name in _production() if name not in out]


def is_accepted(mode: str) -> bool:
    """Whether one mode may be drawn and seated. Cheap: no engine crossing.

    A mode the table does not name is not accepted, which is the safe half of
    [`weight_of`]'s refusal: this one is asked per candidate row over a ledger of
    a quarter of a million, and raising there would make an unnamed mode a crash
    rather than a row that is simply not gallery material.
    """
    return MODE_POLICY.get(str(mode)) not in (None, NICHE)


def check() -> dict:
    """Refuse unless the table and the engine's catalog name the same roster.

    Four ways they can disagree, and each is a mistake rather than a state to
    tolerate: a production mode with no weight, a weight on a mode the engine does
    not have, a weight on a mode the engine tiers **niche** — that one is a
    standing written at two layers, which is what the table exists to stop — and a
    weight outside [`WEIGHTS`].
    """
    from fractal_wallpapers import engine

    production = _production()
    catalogued = {entry["name"] for entry in engine.modes()}
    unweighted = [name for name in production if name not in MODE_POLICY]
    if unweighted:
        raise PolicyRefused(
            f"{unweighted} are production modes with no weight in MODE_POLICY. A mode a "
            f"draw can pick and nobody has ruled on is a mode with no standing."
        )
    absent = sorted(name for name in MODE_POLICY if name not in catalogued)
    if absent:
        raise PolicyRefused(
            f"{absent} carry a weight and the engine has no such mode. Rename or remove "
            f"them here: a weight on a mode nothing can render is a rule that reads as "
            f"applied and never is."
        )
    tiered = sorted(name for name in MODE_POLICY if name not in set(production))
    if tiered:
        raise PolicyRefused(
            f"{tiered} are tiered niche by the engine and also carry a weight here, so "
            f"their standing is written twice. The engine's tier is what the corpora were "
            f"collected over; this table is what is worth collecting next. Pick one."
        )
    bad = sorted(name for name, value in MODE_POLICY.items() if value not in WEIGHTS)
    if bad:
        raise PolicyRefused(f"{bad} carry a weight outside {WEIGHTS}.")
    return {
        "production": len(production),
        "accepted": accepted(),
        "niche": niche(),
        "promoted": promoted(),
    }


#: The share of a gallery's seats the **strange** side is meant to hold, and the
#: denominator every mode floor is computed against.
#:
#: **Declared, not measured, and six tenths.** It is the size of the pie the floors
#: divide and nothing else: no rule anywhere asks a finished gallery whether it
#: realized this share, and adding one is a separate decision.
#:
#: **It is not [`curation.run.STRANGE_SHARE`]**, which carries the same number and
#: answers a different question — how a release's *mining slots* split between the
#: two heads, at [`curation.budget.head_slots`]. That one is about attempts bought
#: before anything is rendered; this one is about seats in a finished gallery. The
#: two are free to move apart, and one name over two stages is the confusion this
#: repository keeps paying for, so the name here says `SEAT`.
STRANGE_SEAT_SHARE = 0.60


def strange_modes() -> list[str]:
    """The accepted modes on the strange side, in catalog order.

    Read from [`curation.colorize.modes_for`] rather than filtered here: that is
    where the two-way split of the roster is defined, and a second copy of it is
    what the naming rule exists to stop.
    """
    from fractal_wallpapers.curation import budget, colorize

    return list(colorize.modes_for(budget.STRANGE))


def strange_seats(n: int, share: float = STRANGE_SEAT_SHARE) -> int:
    """How many of `n` seats the strange side is declared to hold."""
    n = max(0, int(n))
    return max(0, min(n, int(round(n * float(share)))))


def seat_floors(n: int, share: float = STRANGE_SEAT_SHARE) -> dict[str, int]:
    """`{strange mode: the seats its floor asks for}` at `n`.

    **One shipped caller, and it is a flag**: `curate seat --seat-floors`. An
    unflagged seating still takes [`solve.mode_floor`]'s flat one, so a gallery
    is seated under this rule only where somebody named it.

    ## The rule

    Weight is a claim about how much of a gallery a mode is worth, so it is the
    thing a target is proportional to. Over the accepted strange modes, `2 *
    promoted + 1 * normal` distributes [`strange_seats`] fully: each mode's
    *target* is its share of that budget. Each mode's **floor is half its
    target**, so the floors sum to exactly half the strange budget by construction
    and the other half is the gallery's to spend on whatever is strongest.

    Every accepted strange mode is floored by that one formula. There is no bare-1
    exception for a weight-1 mode and none for `direct_trap_multiply`: a floor
    that is a special case for somebody is a table pretending to be a rule.

    ## Two things it is not

    **Smooth is not in it.** [`curation.colorize.modes_for`] returns
    `[SMOOTH_MODE]` unconditionally on the smooth branch, so the smooth side is
    one mode by construction and has no distribution problem to solve. Floors
    concern the strange side; the smooth side's seats are `n` less
    [`strange_seats`].

    **A floor is not a ceiling.** Where one collides with the per-cell allowance or
    the palette-group cap, the ceiling wins and the floor goes unfilled — a bar
    outranks a guarantee, and an unfilled floor beats a padded gallery. The
    seating records the shortfall per mode rather than repairing it.

    ## Why largest remainder

    Half a target is fractional, and the halves have to add back up to the half
    budget or the construction above is not what shipped. So the integer part
    first and the leftover seats to the largest fractional remainders, ties by
    weight then by name so the answer is a pure function of `n`. Truncating each
    mode's half instead would quietly lose a seat per mode with a remainder, which
    over thirteen modes is most of them.

    Note this is **not** the rule [`supply.apportion`] uses. That one is
    largest-*deficit* sequencing, and its subject is every prefix of a batch that
    may stop early. Here nothing stops early: the whole house is handed out at
    once and the only property asked of it is that it sums.
    """
    modes = strange_modes()
    budget = strange_seats(n, share)
    house = (budget + 1) // 2
    weight = {name: weight_of(name) for name in modes}
    total = sum(weight.values())
    if house <= 0 or total <= 0:
        return dict.fromkeys(modes, 0)
    exact = {name: house * weight[name] / total for name in modes}
    out = {name: int(exact[name]) for name in modes}
    left = house - sum(out.values())
    order = sorted(modes, key=lambda name: (-(exact[name] - out[name]), -weight[name], name))
    for name in order[:left]:
        out[name] += 1
    return out


# --------------------------------------------------------------------------- #
# What a row routes as, which is not always the mode it was rendered in.
# --------------------------------------------------------------------------- #
def routed_mode(mode: str, texture_flat: bool = False) -> str:
    """The mode one render **counts as**, given whether its texture said anything.

    A modulate lays a texture over a base and shifts the base's palette position
    by it. When the texture has no span — every sample at one value, or none of
    them at a value at all — the shift is zero everywhere and the picture is the
    base spent by rank, *bit for bit*. The engine reports that as
    `RenderReport.texture_flat`, the ledger row carries it, and this is the one
    place the consequence is spelled: such a render is `smooth` at
    `transfer: {"kind": "rank"}`, so it routes as `smooth` wherever a mode or a
    kind is decided — the seating pool, the census, the per-mode bars, the mode
    floors and the two label stores.

    **It holds because every catalogued modulate is built on the smooth field.**
    That is an engine invariant rather than an assumption made here: `mode.rs`'s
    `smooth_is_the_default_and_the_base_of_every_composite` asserts it over the
    whole catalog. A modulate on some other base would still degenerate, and it
    would degenerate to that other base by rank — so the day one exists, this
    function is where it is answered rather than a place that would silently be
    wrong.

    Nothing is renamed and no picture moves. The recipe still says `itinerary`,
    the row still records it, and the file on disk is untouched; what changes is
    only which pile the row is counted in. A caller wanting the mode that was
    *asked for* reads `recipe["mode"]` as it always did.
    """
    from fractal_wallpapers.curation import colorize

    return colorize.SMOOTH_MODE if texture_flat else str(mode)


def routed_mode_of(row: dict) -> str:
    """[`routed_mode`] off a candidate-ledger row, so no reader spells the join.

    A row written before the flag existed carries no `texture_flat` and reads as
    `False` — which is the mode it was rendered in, and which is right for every
    row of every mode but a modulate. The backfill that fills those in is
    [`fractal_wallpapers.coloring.texture_flat`].
    """
    return routed_mode(str((row.get("recipe") or {}).get("mode")), bool(row.get("texture_flat")))


def record() -> dict:
    """What a run writes down about the policy it drew under."""
    return {
        "weights": dict(MODE_POLICY),
        "accepted": accepted(),
        "niche": niche(),
        "promoted": promoted(),
        "wired": "weight 0 only: out of the labeling rosters, the default mining rosters "
        "and gallery emission. Weights 1 and 2 are recorded and read the same: "
        "`seat_floors` is what would make them differ and nothing calls it.",
    }


__all__ = [
    "MODE_POLICY",
    "NICHE",
    "NORMAL",
    "PROMOTED",
    "STRANGE_SEAT_SHARE",
    "WEIGHTS",
    "PolicyRefused",
    "accepted",
    "at",
    "check",
    "is_accepted",
    "niche",
    "promoted",
    "record",
    "routed_mode",
    "routed_mode_of",
    "seat_floors",
    "strange_modes",
    "strange_seats",
    "weight_of",
]
