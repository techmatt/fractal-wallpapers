"""How much of a breadth draw each partition is owed, in one table.

A breadth draw — [`curation.hunt`]'s unconditional leg, [`curation.mine`]'s two
`breadth_*` arms, [`curation.depth`]'s ranked draw and the two matched arms sized
off it — spreads over partitions round-robin rather than proportionally to what
each holds, because what it buys is *places* and every partition's places are
equally thin against the scan. That is right about places and blind about time.

**Blind about time is what this table fixes.** `dtm_variants`, 2026-09-02, drew
every partition equally and spent **3,705.1 s of 7,190.6 s — 51.5% of the leg's
clock — on the 72 `phoenix:classic` candidates of 1,362**, at 51.46 s a candidate
against 1.18 for `julia:multibrot5`. `phoenix` took a further 12.0% at the same
72. So the pinned plane and its varied family carry [`DOWNWEIGHTED`] by default
and every breadth arm inherits it, rather than each leg remembering to pass a
weight it will only pass after somebody reads a price table.

**What the quarter actually bought, measured over the nine legs that have run under
it** (2026-09-04, `depth.json`'s `price` block against `budget.engine_seconds`;
`pc20m` excluded as an aimed leg): `phoenix:classic` took **24.0% of 57,339 engine
seconds** on 1,111 candidates at 12.41 s each, against a turns share of 1 of 34 —
**2.94%**. So the downweight moved the pinned plane from the 51.5% above to 24.0%
and it is **still 8.2x its turn**. `phoenix` proper is 6.7% and 2.3x, and its
per-candidate price is inside the field; it is not what this table is for.

Two things the pooled number hides, and both change what a further cut would buy.
**The cost is the deep arms, not the draw**: the breadth and floor arms run 17-31 s
a `phoenix:classic` candidate and reached 51.8% of one whole leg, while the near
band and the `--draw-cells` legs run 1.2-1.5 s and sit at 8.6-16.7%. Same weight,
same plane, an order of magnitude apart, because a near-band re-render is shallow.
And **a `--centered only` leg draws no phoenix at all** — `centered_drawable` is 0
for both planes against 591 and 617 drawable — so the weight is moot there and the
plane cannot be bought on a centered leg at any weight.

**A weight scales a share and never removes a partition.** The default table
holds no zero: a partition that should get none of a release is *retired* from
[`supply.partitions`], which is the same rule `data/supply/release_mix.json`
states for its ratios. A caller may still name a zero — `dtm_breadth2` did — and
then the partition is out of that leg's draw by explicit ask, which is a
different thing from a default that starves it.

## A different axis from the release mix, and both are declared

`release_mix.json` says how much of a *release* a family is owed; this says how
much of a *draw* one is worth **given what it costs to render**. They are read
at different stages and neither derives the other: a leg may lean toward the
release mix with `--partition-weights` on top of this table, and the two multiply
rather than one overriding the other.

## Fractional weights need turns, and turns are integers

Every draw here is a round-robin, so a weight has to become *turns a round*. The
three sites that did that arithmetic each did it as `int(round(weight))`, which
silently makes 0.25 either **zero turns** — the partition gone, which the rule
above forbids — or **one turn**, which is no lean at all. [`turns_of`] scales the
whole table so the smallest positive weight buys one turn and the ratios survive,
and [`order`] lays the round out so every *prefix* is proportional too: a
production leg is clock-bound and always truncates, so a lean that only acts over
a whole round is a lean that never acts.
"""

from __future__ import annotations

from fractal_wallpapers.supply.partitions import ALL_PARTITIONS

#: What a partition is worth in a breadth draw when nothing says otherwise.
DEFAULT_WEIGHT = 1.0

#: The partitions this project buys less breadth in than their turn would give
#: them, and why, ruled 2026-09-02 on the clock shares in the module docstring.
#: A quarter and not a zero: both partitions stay drawable, stay in the census,
#: and stay able to be aimed at — see [`table`] for the override.
DOWNWEIGHTED: dict[str, float] = {
    "phoenix": 0.25,
    "phoenix:classic": 0.25,
}

#: The longest round [`turns_of`] will build, per partition. A weight table of
#: 1.0 against 0.001 would otherwise ask for a thousand turns a round and a draw
#: whose round is longer than the leg is a draw nobody can read a prefix of.
MAX_TURNS = 32


def table(overrides: dict | None = None) -> dict[str, float]:
    """The weight table a leg runs under: [`DOWNWEIGHTED`] with `overrides` over it.

    Every registered partition appears, so a table read off this says what the
    draw thinks of each of them rather than only of the ones somebody named.

    **Merged and not replaced**, which is what makes the override cheap. A leg
    aimed at a phoenix plane says `{"phoenix:classic": 1.0}` and gets its full
    weight back without also having to restate the release-mix lean it was
    already carrying; a leg that leans mandelbrot does not silently re-inflate
    the pinned plane by forgetting to mention it.
    """
    out = {name: float(DOWNWEIGHTED.get(name, DEFAULT_WEIGHT)) for name in ALL_PARTITIONS}
    for name, weight in dict(overrides or {}).items():
        out[str(name)] = float(weight)
    return out


def turns_of(names, weights: dict | None, floor: int = 0) -> dict[str, int]:
    """`{name: turns a round}` — the weights as integers, ratios kept.

    Scaled only where it is needed: a table whose smallest positive weight is
    already a whole turn is used as it stands, so every integer work order this
    project has ever passed comes out of here as the turns it always was. A
    table holding a fraction is scaled so its smallest positive weight buys
    exactly one turn — `{1.0, 0.25}` is four turns against one, and not
    `int(round(0.25)) == 0`, which is what the three copies of this arithmetic
    each did before. Capped at [`MAX_TURNS`].

    **`floor` is the difference between the two rules this project already
    holds, and it is a parameter because both are right where they stand.** At
    the *draw*, `floor=0`: a caller who names a weight of zero has asked for the
    partition to be out of this leg, which `dtm_breadth2` did deliberately. At
    the *interleave*, `floor=1`: the places are already drawn, and dropping a
    partition the draw kept would starve one the leg meant to buy.

    A negative weight reads as zero rather than as an error, for the reason a
    weight is never a gate: the worst a malformed table may do here is drop a
    partition the caller named, not refuse the leg.
    """
    held = {
        str(name): max(0.0, float((weights or {}).get(str(name), DEFAULT_WEIGHT))) for name in names
    }
    positive = [weight for weight in held.values() if weight > 0.0]
    if not positive:
        return dict.fromkeys(held, int(floor))
    smallest = min(positive)
    scale = 1.0 if smallest >= 1.0 else 1.0 / smallest
    if max(positive) * scale > MAX_TURNS:
        scale = MAX_TURNS / max(positive)
    return {
        name: (max(1, round(weight * scale)) if weight > 0 else int(floor))
        for name, weight in held.items()
    }


def order(names, weights: dict | None, floor: int = 0) -> list[str]:
    """One round of the draw, each name as often as its turns, **interleaved**.

    Interleaved and not blocked, which is [`hunt._turns`]'s reason and now the
    only copy of it: a round reading `julia:mandelbrot 19, mandelbrot 6, ...` as
    nineteen consecutive turns spends its opening nineteen on one partition, and
    a leg shorter than the round never reaches the second. Each name's k-th turn
    is placed at `(k + 0.5) / turns` and the round is sorted on that, so every
    prefix is proportional too.

    A name with no turns is absent from the round and present in the tally the
    caller reports: absence here is the draw not taking it, which is what a zero
    weight asked for, and it is never how the *count* is reported.
    """
    turns = turns_of(names, weights, floor=floor)
    placed = [((at + 0.5) / turns[name], name) for name in turns for at in range(turns[name])]
    return [name for _at, name in sorted(placed, key=lambda item: (item[0], item[1]))]


def tallied(names, drawn: dict) -> dict[str, int]:
    """`drawn` reported over every one of `names`, a partition it missed at **zero**.

    A draw that took nothing from a partition and a draw that was never offered
    one read identically in a `Counter`, and the second is the interesting one:
    `dtm_breadth2` ran `phoenix: 0` and its record simply has no key for phoenix,
    so the leg cannot be told apart from one taken before the partition existed.
    """
    return {str(name): int(drawn.get(str(name), 0)) for name in sorted({str(one) for one in names})}


__all__ = [
    "DEFAULT_WEIGHT",
    "DOWNWEIGHTED",
    "MAX_TURNS",
    "order",
    "table",
    "tallied",
    "turns_of",
]
