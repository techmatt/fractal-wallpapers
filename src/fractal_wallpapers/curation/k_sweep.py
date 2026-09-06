"""One n=1000 seating per colour-ceiling `K`, so the trade can be looked at.

[`ceiling.K`] is the headroom a colour gets over its target rate before the ceiling
refuses a candidate dominant in it, and the allowance it produces is
[`ceiling.Rule.allowed`] — `floor(K * t * n) + 1`. Moving it is a taste decision
that has to be taken off pictures, and this is the leg that makes the pictures:
one solve per `K` over one pool, everything else held.

## Why this exists rather than a `--k` flag

There is no `--k` on `curate solve run` or `curate solve record`, and there should
not be: `K` is a shipped constant, not a per-pass setting, and a record taken under
a `K` nobody set would be a gallery that cannot be reproduced from the constant.
What this leg writes instead is a **counterfactual**, named as one — each rung's
solve record is `sweepK_k<K>_n<n>_<stamp>` — and **no default moves**.
[`solve.solve`]'s `rule` parameter is the override path, it already existed, and
this passes [`ceiling.Rule`] with a `k` rather than editing the module constant.

## What is held, and what is not

Everything but `K` is what [`cli.curate_commands`]'s `curate solve record` passes,
so a rung at the shipped `K` reproduces the record a `curate solve record` at that
`n` would have written — the `K = 2` rung of 2026-09-06 came back bit-identical to
`20260906T133236Z`, the same 1,000 keys in the same seat order with the same
objective and the same refusal table, and that reproduction is the check that makes
the other rungs worth reading. **Run the shipped `K` as a rung and check it**; a
control that misses is itself the finding.

The pool and the ranking are resolved **once** and shared across the rungs, which
is sound because [`solve.Candidate`] is `@dataclass(frozen=True)`: a rung cannot
leave a mark on the next one's pool. It also makes the leg one pool-holding process
rather than four, which is the rule this machine has.

## What it found the first time

`curation/MEASUREMENTS.md`'s *What the colour ceiling costs at n=1000*: the worst
seat nearly doubles between `K = 2` and `K = 2.5` while every rung still fills, all
of the growth is muted, and the cells that were short at `K = 2` end **shorter**,
because the headroom is spent where the supply is. The refusal table says nothing
else takes over — `cell_allowance` is still the top refusal at 2.5.

⚠ **Read the allowance off [`ceiling.Rule.allowed`] and not off the formula.** The
product is taken in binary floating point, so `K = 2.4` at `n = 1000` allows **50**
where the arithmetic on paper says 51. This leg prints the allowance per rung for
exactly that reason.
"""

from __future__ import annotations

import time

from fractal_wallpapers.curation import ceiling, solve, tentative

#: The rungs the 2026-09-06 sweep ran, and the default set.
#:
#: The first is the **shipped** `K` and is the control: it reproduces the record a
#: `curate solve record` at the same `n` writes, and nothing above it is worth
#: reading until it does. The other three are the loosenings Matt asked to see.
RUNGS: tuple[float, ...] = (2.0, 2.25, 2.4, 2.5)

#: The seat count a rung is taken at. [`tentative.RECORDED_SEATS`] and not a second
#: opinion about it: a counterfactual read at a size no record is kept at would not
#: be comparable with the record it is a counterfactual on.
SEATS = tentative.RECORDED_SEATS


def tag_of(k: float) -> str:
    """`2.25` as `2p25` — a `K` as a directory name. No dot, because a solve record
    is a directory and a dot in one reads as an extension."""
    return f"{float(k):g}".replace(".", "p")


def name_of(k: float, n: int, stamp: str) -> str:
    """What a rung's solve record is called. **Obviously a sweep**: these are
    disposable counterfactuals and the store holds a hundred real ones."""
    return f"sweepK_k{tag_of(k)}_n{int(n)}_{stamp}"


def allowance(k: float, n: int) -> int:
    """The per-cell allowance one rung runs under, asked of the rule that applies it.

    Asked and never computed here — see the module note on the float. The cell is
    any untargeted one, since this leg carries no target and they all share
    [`ceiling.CELL_SHARE`].
    """
    return ceiling.Rule(k=k).allowed("dark_vivid_blue", int(n))


def sweep(rungs=RUNGS, n: int = SEATS, log=print) -> list[dict]:
    """One recorded seating per `K`. Returns a row per rung, in order.

    Each rung writes both halves under one stamp, exactly as `curate solve record`
    does: the solve record under [`name_of`] and the tentative gallery under the
    stamp, with its page. Every rung is **unpublished** — a tentative record is
    published only when Matt names it — and every one holds prune protection
    through [`tentative.protected_keys`] until its folder is deleted, published or
    not. A sweep is disposable and this is the thing to remember about deleting it.
    """
    started = time.monotonic()
    held = [float(k) for k in rungs]
    log(
        f"[k-sweep] allowance at n={n}: " + ", ".join(f"K={k:g} -> {allowance(k, n)}" for k in held)
    )

    candidates, refused = solve.pool(log=log)
    order, coverage = solve.ranking_for(candidates, solve.DEFAULT_KEY, log=log)
    log(f"[k-sweep] pool and ranking in {time.monotonic() - started:.1f}s")

    out: list[dict] = []
    for k in held:
        at = time.monotonic()
        rule = ceiling.Rule(targets={}, k=k)
        log(f"[k-sweep] === K={k:g} (allowance {allowance(k, n)}) ===")
        record = solve.solve(
            candidates,
            n=int(n),
            rule=rule,
            order=order,
            coverage=coverage,
            key=solve.DEFAULT_KEY,
            spiral_cap=solve.DEFAULT_SPIRAL_CAP,
            mode_ceilings=dict(solve.DEFAULT_MODE_CEILINGS),
            augment_chains=solve.DEFAULT_AUGMENT,
            log=log,
        )
        stamp = tentative.stamp_now()
        name = name_of(k, n, stamp)
        log(f"[k-sweep] {solve.write_record(name, record)}")
        tentative.write(
            record,
            candidates=candidates,
            solve_name=name,
            pool_refused=refused,
            stamp=stamp,
            log=log,
        )
        page = tentative.page(stamp, log=log)
        out.append(
            {
                "k": k,
                "allowance": allowance(k, n),
                "n": int(n),
                "stamp": stamp,
                "solve_name": name,
                "page": str(page),
                "filled": record["filled"],
                "objective": record["objective"]["final"],
                "refusals": record["rules"]["refusals_while_choosing"],
                "seconds": round(time.monotonic() - at, 2),
            }
        )
        log(f"[k-sweep] {page}")
    log(f"[k-sweep] {len(out)} rung(s) in {time.monotonic() - started:.1f}s")
    return out


__all__ = ["RUNGS", "SEATS", "allowance", "name_of", "sweep", "tag_of"]
