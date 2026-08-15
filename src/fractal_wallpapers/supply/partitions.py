"""The partition registry: what the supply engine keeps separate books for.

A **partition** is the unit everything downstream is keyed on — the ratio table,
the currency census, the price, the floor, the τ_h cut. It is not quite a family:
two of the distinctions here exist because a family label would merge populations
that behave nothing alike.

**A dynamical plane is namespaced away from its parameter plane.** `mandelbrot`
and `julia:mandelbrot` are one recurrence at one degree, and they are different
supply: the parameter plane is a single map that a walk descends into, and the
dynamical plane is a *different fractal for every `c`*, fed by a pool of
parameters. Merging them would let one of the two pay for the other's floor.

**Phoenix splits on its parameter point.** The classic instance is the one pinned
Ushiki point, and it is structurally a pinned-parameter dynamical family — the
same shape as a Julia twin, which is already namespaced for exactly this reason.
`phoenix` from here on means *varied* phoenix: a swept six-dimensional space.
They are different supply, different scarcity, different objectives.

**The split happens at the reader.** Nothing on disk is re-keyed and no writer
has to know: [`partition_of_family`] reads the whole family record, and a phoenix
family that names no parameters at all resolves to the classic point, because
that is what the engine renders when it is told nothing.

**Registration is refused, never defaulted.** A resolver that can emit a
partition key the per-partition tables were never extended for produces a silent
extra bucket: no ratio, no floor, no price, no τ_h row — and every one of those
reads as "that partition had nothing" rather than as a missing decision.
"""

from __future__ import annotations

#: The Phoenix instance that is its own partition: Ushiki's pinned point, as the
#: engine's own defaults spell it — `c`, `p`, `z₋₁` in that order.
#:
#: Exact equality, and there must never be a tolerance. A tolerance would quietly
#: annex varied points near the classic one into a partition whose entire content
#: is one parameter value.
CLASSIC_PHOENIX_POINT = ((0.5667, 0.0), (-0.5, 0.0), (0.0, 0.0))

#: The pinned-parameter phoenix partition.
CLASSIC_PHOENIX = "phoenix:classic"

#: The parameter-plane partitions, in canonical report order. `mandelbrot` is the
#: multibrot at degree 2 and keeps its own name because that is what it is called.
PARAMETER_PLANES = ("mandelbrot", "multibrot3", "multibrot4", "multibrot5")

#: The dynamical twin of each parameter plane.
DYNAMICAL_PLANES = tuple(f"julia:{plane}" for plane in PARAMETER_PLANES)

#: Every partition that can reach a release, in canonical report order.
#:
#: Derivations and tallies walk this, so a partition that got nothing is stamped
#: with a zero rather than being silently absent — a table that omits a partition
#: and a table that reports it empty are different statements.
ALL_PARTITIONS = (*PARAMETER_PLANES, *DYNAMICAL_PLANES, "phoenix", CLASSIC_PHOENIX)


class UnregisteredPartition(KeyError):
    """A partition key nobody registered reached a per-partition table."""


def registered(partition: str) -> str:
    """Return `partition`, having proved it is in [`ALL_PARTITIONS`] first."""
    if partition not in ALL_PARTITIONS:
        raise UnregisteredPartition(
            f"{partition!r} is not a registered partition. Register it in "
            f"partitions.ALL_PARTITIONS and extend every per-partition table — the release "
            f"mix, the price seed, τ_h — before any resolver can emit it. A partition that "
            f"reaches a table it has no row in reads as a measured zero."
        )
    return partition


def is_dynamical(partition: str) -> bool:
    """Whether this partition is a Julia plane — fed only through its parent."""
    return partition.startswith("julia:")


def parameter_plane_of(partition: str) -> str | None:
    """The parameter plane a Julia twin hangs off, or `None` for anything else.

    A `julia:X` partition cannot be walked into existence: its supply is a pool of
    `c` values, or a c-plane descent that reached somewhere worth taking the twin
    of. That is why its demand has somewhere to fold to when its own queue is
    empty — see `allocation.fold_dynamical_intent`.
    """
    return partition.split(":", 1)[1] if is_dynamical(partition) else None


def dynamical_twin(partition: str) -> str:
    """The Julia partition that hangs off this parameter plane."""
    return f"julia:{registered(partition)}"


def _pair(value, default: tuple[float, float]) -> tuple[float, float]:
    """A `[re, im]` family constant as floats, or `default` when it is absent.

    Absent is not unknown here. A family record that names no constant is one the
    engine will render at its own default, so reading the default *is* reading
    what will be drawn.
    """
    if value is None:
        return default
    return (float(value[0]), float(value[1]))


def is_classic_phoenix(family: dict) -> bool:
    """Whether this phoenix family is the pinned classic point.

    Reads all three constants, because all three are the seed: `z₋₁` is carried
    forward by the recurrence, so a non-zero one is a different fractal from the
    same `(c, p)`, and a resolver that looked only at `c` would annex it.
    """
    c, p, z_prev = CLASSIC_PHOENIX_POINT
    return (
        _pair(family.get("c"), c) == c
        and _pair(family.get("p"), p) == p
        and _pair(family.get("z_prev"), z_prev) == z_prev
    )


def partition_of_family(family: dict) -> str:
    """The partition a family record belongs to.

    Takes the whole record rather than a family name, because two of the four
    rules need a constant: the degree tells a multibrot from a mandelbrot, and the
    parameter point tells classic phoenix from varied.
    """
    kind = family.get("kind")
    degree = int(family.get("degree", 2))
    if kind == "mandelbrot":
        return "mandelbrot"
    if kind == "multibrot":
        return registered("mandelbrot" if degree == 2 else f"multibrot{degree}")
    if kind == "julia":
        return registered(dynamical_twin("mandelbrot" if degree == 2 else f"multibrot{degree}"))
    if kind == "phoenix":
        return CLASSIC_PHOENIX if is_classic_phoenix(family) else "phoenix"
    raise UnregisteredPartition(
        f"family kind {kind!r} belongs to no registered partition; the engine renders "
        f"mandelbrot, multibrot, julia and phoenix"
    )


def partition_of_row(row: dict) -> str:
    """The partition of a ledger or label row — whichever way it carries its family.

    One resolver for both sides, because a row that reaches a per-partition tally
    through a second rule is a row that can be counted in two partitions.
    """
    family = row.get("family")
    if isinstance(family, str):
        return registered(family)
    if isinstance(family, dict):
        return partition_of_family(family)
    raise UnregisteredPartition(
        "row carries no family record, so it belongs to no partition. A row whose partition "
        "cannot be resolved must be counted and reported, never routed to a default."
    )


__all__ = [
    "ALL_PARTITIONS",
    "CLASSIC_PHOENIX",
    "CLASSIC_PHOENIX_POINT",
    "DYNAMICAL_PLANES",
    "PARAMETER_PLANES",
    "UnregisteredPartition",
    "dynamical_twin",
    "is_classic_phoenix",
    "is_dynamical",
    "parameter_plane_of",
    "partition_of_family",
    "partition_of_row",
    "registered",
]
