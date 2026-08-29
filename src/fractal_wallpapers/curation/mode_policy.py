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
#: The five at 0 are the modes a round of human labels could not make a case for,
#: counted over the ingested `strange_render` store: `trap_circle` has never been
#: given a 4 in 118 rows, `gaussian_int` has 4 in 209, `curvature` 5 in 217,
#: `smooth_trap_circle` 6 in 200 and `direct_trap_ring` 5 in 273.
#:
#: The six at 2 are the ones that did: `tia` 31 fours in 310 rows, `stripe` 26 in
#: 203, `threads` 36 in 167, `smooth_stripe` 34 in 239, `smooth_mean_angle` 34 in
#: 193 and `smooth_angle_min` 30 in 159.
MODE_POLICY: dict[str, int] = {
    # --- 0: niche ---
    "trap_circle": NICHE,
    "gaussian_int": NICHE,
    "curvature": NICHE,
    "smooth_trap_circle": NICHE,
    "direct_trap_ring": NICHE,
    # --- 1: normal ---
    "smooth": NORMAL,
    "exp_smoothing": NORMAL,
    "smooth_curvature": NORMAL,
    "direct_trap_screen": NORMAL,
    "direct_trap_multiply": NORMAL,
    "direct_trap_lines": NORMAL,
    "itinerary": NORMAL,
    # --- 2: promoted ---
    "tia": PROMOTED,
    "stripe": PROMOTED,
    "threads": PROMOTED,
    "smooth_stripe": PROMOTED,
    "smooth_mean_angle": PROMOTED,
    "smooth_angle_min": PROMOTED,
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


def record() -> dict:
    """What a run writes down about the policy it drew under."""
    return {
        "weights": dict(MODE_POLICY),
        "accepted": accepted(),
        "niche": niche(),
        "promoted": promoted(),
        "wired": "weight 0 only: out of the labeling rosters, the default mining rosters "
        "and gallery emission. Weights 1 and 2 are recorded and read the same.",
    }


__all__ = [
    "MODE_POLICY",
    "NICHE",
    "NORMAL",
    "PROMOTED",
    "WEIGHTS",
    "PolicyRefused",
    "accepted",
    "at",
    "check",
    "is_accepted",
    "niche",
    "promoted",
    "record",
    "weight_of",
]
