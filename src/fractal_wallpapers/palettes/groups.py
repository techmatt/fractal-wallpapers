"""The library's groups: which maps are near enough to be one choice.

Nine hundred maps is not nine hundred *choices*. `cet_linear_kry_0_97_c73` and
`cet_linear_kryw_0_100_c71` are the same red-yellow ramp twice; a colour-vision
variant and its parent differ by a correction nobody looking at a wallpaper can
name. A candidate set that holds both is asking the palette head to break a tie
that does not exist, and a gallery that seats both has spent two slots on one
picture.

This module says which maps those are. It is a **reading of the tracked library**
— no model, no label, no run — so the table it writes is a function of the maps
and the cut, and `tests/test_palette_groups.py` holds the committed file to
regenerating it.

## The metric: M1, the sliced Wasserstein distance between two baked ramps

A map is read as the **cloud of colours it can put on a picture**, and the
distance between two maps is how far one cloud has to move to become the other.

* The cloud is the map **through the engine's own bake**: its stops sorted,
  sRGB8 to Oklab, linearly interpolated at [`SAMPLES`] evenly spaced positions
  with the end colours held. That is `colormap.rs::from_stops_baked` with
  `mirror = false`, and at 4096 positions — the engine's own table size — the
  bake is the identity rather than an approximation of it.
* **Unfolded.** The fold is what a *render* does with a sequential map, and
  folding here would put a second copy of every stop into every sequential map's
  cloud, which pulls all of them towards each other. The fold changes no map's
  *set* of colours, only how often each is spent, so the unfolded read is the one
  that answers "are these the same colours".
* **Hue weighted.** `a` and `b` are scaled by [`HUE_WEIGHT`] before the distance
  is taken, so a hue difference counts four times a lightness difference of the
  same size. Unweighted, the calibration sheet's headroom was 1.23x — too little
  for linkage, which chained the pair Matt called the outer bound of "same" into
  a group. Weighted, it is 1.89x and the chaining stops.
* **Order-free.** Sliced Wasserstein-1 compares two *distributions* of colour,
  not two sequences, so where along the ramp a colour sits does not enter. That
  is deliberate: a cyclic map and the same map phase-shifted hold identical
  colour, and the head choosing between them is choosing nothing.

The slicing is [`DIRECTIONS`] directions of a Fibonacci half-sphere lattice —
half, because W1 along `d` and along the direction opposite it are the same
number and a full sphere would sample each one twice — with each cloud's
projection read at [`QUANTILES`] evenly spaced quantiles. The distance is the
mean over directions of the mean absolute quantile difference, which is the 1-D
W1 exactly.

## The cut: [`CUT`], and it was derived rather than chosen

Average linkage over M1, cut at `0.039735`. That number is not a threshold
somebody liked the look of: it is the midpoint between the widest pair Matt
marked SAME and the nearest pair he marked DIFFERENT on a forty-six pair
calibration sheet — `cet_cyclic_wrwbw_40_90_c42_s25` / `cet_diverging_bwr_40_95_c42`
at 0.03163 below, `Three Candles` / `Twin Sconces` at 0.04784 above. The marks
leave **no inversions**: every SAME pair is tighter than every DIFFERENT pair, so
the cut is the whole ruling and the sheet is the whole evidence.

**Average** linkage rather than single because single linkage chains: one pair
near the cut is enough to weld two groups nobody would call alike. Average asks
whether a candidate is near the group's *members*, which is the question.

## What a group is for, and what it is not

Downstream, one thing reads this: the drawable pool collapses to one member per
group at read time ([`collapse`]). **Nothing is deleted.** Every map stays in the
library, keeps its label rows and can still be named by a record; what the
collapse changes is only which maps a *fresh* draw may reach, and it re-draws per
seed so no member is permanently favoured.

The table is deliberately conservative. Sixty-five groups over 143 maps out of
901 — the other 758 are singletons, and a singleton is not a claim that a map is
unique, only that nothing in the library came within the cut of it.
"""

from __future__ import annotations

import collections
import json
import os
import random
from pathlib import Path

from fractal_wallpapers.paths import colormap_dir

#: The schema every row of the record carries, from its first line.
SCHEMA = 1

#: What the file is called, beside the maps it groups. JSONL, and that is not a
#: style choice: every reader of the colormap library globs `data/palettes/*.json`
#: and takes the stem as a map name, so a `.json` file in there would be read as a
#: colormap by the pool, the cyclic table, this module's own [`library`] and
#: `tests/test_colormaps.py` alike.
RECORD_NAME = "groups.jsonl"

#: The two kinds of row the record holds: one header, then one row per group.
METHOD_ROW = "method"
GROUP_ROW = "group"

#: Where the **marks the cut was read off** live, beside the table they decide.
#: JSONL like everything else here, and for the same reason.
#:
#: Forty-six pairs put in front of Matt on 2026-08-25 and marked SAME or
#: DIFFERENT by eye, drawn in five blocks — the tightest pairs in the library,
#: pairs straddling the candidate cut, pairs at twice it, far pairs as a control,
#: and six anchors he named himself. [`CUT`] is the midpoint of the widest SAME
#: and the nearest DIFFERENT among them, and [`cut_from_marks`] recomputes it, so
#: the number in this file is checkable against the evidence rather than
#: remembered from a session.
MARKS_RECORD_NAME = "groups_marks.jsonl"
MARK_ROW = "mark"
SAME, DIFFERENT = "same", "different"

#: How many positions of each ramp the cloud is read at. The engine's own
#: `TABLE_SIZE`, which is what makes the sampling the bake rather than a
#: resampling of it.
SAMPLES = 4096

#: How much harder a hue difference counts than a lightness difference of the
#: same size. Applied to Oklab `a` and `b` before the distance is taken.
HUE_WEIGHT = 4.0

#: Directions the sliced distance is taken along, and how many quantiles each
#: projection is read at.
DIRECTIONS = 1024
QUANTILES = 128

#: The cut, derived from Matt's forty-six pair calibration sheet on 2026-08-25:
#: the midpoint of `t08` (`cet_cyclic_wrwbw_40_90_c42_s25` /
#: `cet_diverging_bwr_40_95_c42`, M1 0.03163, marked SAME — the widest SAME pair)
#: and `s10` (`Three Candles` / `Twin Sconces`, M1 0.04784, marked DIFFERENT —
#: the nearest DIFFERENT pair). The marks leave zero inversions, so the midpoint
#: is the only cut consistent with all forty-six of them; headroom is 1.51x.
#: Every merge it makes was reviewed by eye and approved.
CUT = 0.039735

#: Decimals the distance matrix is rounded to before linkage. The projection runs
#: through a matrix product, that is not bit-identical across BLAS implementations,
#: and rounding turns a platform difference into an exact tie that merges in index
#: order — which is what makes the committed table a function of the library alone.
PLACES = 9

#: The read-time collapse's switch, and its one override. Shipping on; the
#: environment variable turns it off for one run without editing source, which is
#: how an uncollapsed pool is drawn for comparison. Same shape as the autolevel
#: operator's switch, for the same reason.
COLLAPSE_DEFAULT = True
COLLAPSE_ENV = "FRACTAL_WALLPAPERS_PALETTE_GROUPS"

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}

#: The method, carried in the file so a reader never has to find this module.
METHOD = (
    "average linkage over M1, cut at {cut}. M1 is the sliced Wasserstein-1 distance between "
    "two maps' colour clouds: each map read at {samples} unfolded positions through the "
    "engine's own bake (stops sorted, sRGB8 to Oklab, linear interpolation, ends held — "
    "colormap.rs from_stops_baked with mirror=false), Oklab a and b scaled by {weight} so a "
    "hue difference counts {weight_int} times a lightness difference, then W1 averaged over "
    "{directions} directions of a Fibonacci half-sphere lattice, each projection read at "
    "{quantiles} evenly spaced quantiles. The cut is the midpoint of the nearest DIFFERENT "
    "pair and the widest SAME pair below it, on a 46-pair calibration sheet marked by eye "
    "(2026-08-25) and kept beside this file as {marks}: no pair marked DIFFERENT falls "
    "below the cut, and the two marked SAME that sit above it are named there. A group's "
    "`canonical` member is the one carrying the most finished-render label rows, ties "
    "broken by name. Regenerated by `fractal-wallpapers palettes groups`."
)


class GroupError(RuntimeError):
    """The library cannot be grouped, or its groups cannot be read."""


# --------------------------------------------------------------------------- #
# The metric.
# --------------------------------------------------------------------------- #
def library(directory: Path | None = None) -> list[str]:
    """Every tracked map, by name, in sorted order.

    A glob of `*.json` and the stem of each, which is what every other reader of
    the library does — and the reason [`RECORD_NAME`] is a `.jsonl`.
    """
    directory = Path(directory) if directory is not None else colormap_dir()
    return sorted(path.stem for path in directory.glob("*.json"))


def cloud(name: str, samples: int = SAMPLES):
    """One map's colour cloud: `[samples, 3]` Oklab, unfolded, through the bake.

    The engine's `from_stops_baked` with `mirror = false`, in Oklab and stopping
    one step short of it — the engine's last act is `oklab_to_linear_srgb` on
    each entry, and coming back out of Oklab to measure a distance in it would be
    a round trip through a clip.
    """
    import numpy

    from fractal_wallpapers.palettes import space

    positions, colours, _kind = space.ramp(name)
    order = numpy.argsort(positions, kind="stable")
    positions, lab = positions[order], space.oklab(colours[order])
    where = numpy.linspace(0.0, 1.0, samples)
    # `numpy.interp` holds the end values outside the sampled range, which is what
    # `interpolate` in colormap.rs does above and below the outermost stops. A map
    # whose stops do not span [0, 1] is coloured by that rule in the engine and so
    # has to be read by it here.
    return numpy.stack(
        [numpy.interp(where, positions, lab[:, channel]) for channel in range(3)], axis=-1
    )


def weighted(points, weight: float = HUE_WEIGHT):
    """An Oklab cloud with its chroma axes scaled, so hue counts `weight` times."""
    import numpy

    scale = numpy.asarray([1.0, weight, weight], dtype=numpy.float64)
    return numpy.asarray(points, dtype=numpy.float64) * scale


def directions(count: int = DIRECTIONS):
    """`[count, 3]` unit directions, a Fibonacci lattice over the half-sphere.

    Half rather than the whole sphere because the 1-D distance along a direction
    and along its opposite are the same number: a full sphere would sample every
    direction twice and call it twice the coverage. The heights are placed at the
    cell midpoints — `(i + 0.5) / count` — so neither pole is a sample, and the
    azimuth advances by the golden angle, which is what makes the lattice even
    rather than banded.
    """
    import numpy

    index = numpy.arange(count, dtype=numpy.float64)
    height = 1.0 - (index + 0.5) / count
    radius = numpy.sqrt(numpy.maximum(1.0 - height * height, 0.0))
    angle = index * numpy.pi * (3.0 - numpy.sqrt(5.0))
    return numpy.stack([radius * numpy.cos(angle), radius * numpy.sin(angle), height], axis=-1)


def _quantile_positions(samples: int, quantiles: int):
    """Where in a sorted run of `samples` values the `quantiles` readings sit."""
    import numpy

    probability = (numpy.arange(quantiles, dtype=numpy.float64) + 0.5) / quantiles
    return probability * (samples - 1)


def clouds(names, samples: int = SAMPLES, weight: float = HUE_WEIGHT):
    """Every named map's weighted cloud, stacked `[maps, samples, 3]`."""
    import numpy

    return numpy.stack([weighted(cloud(name, samples), weight) for name in names]).astype(
        numpy.float32
    )


def m1(
    names,
    samples: int = SAMPLES,
    weight: float = HUE_WEIGHT,
    count: int = DIRECTIONS,
    quantiles: int = QUANTILES,
    chunk: int = 128,
    log=None,
):
    """The full `[n, n]` M1 matrix over the named maps.

    Chunked over *directions* rather than over maps, which is what keeps this
    inside a gigabyte: the projections of nine hundred clouds onto a thousand
    directions are half a gigabyte on their own, and none of them is needed twice
    once its share of the distance has been added in.
    """
    import numpy

    names = list(names)
    total = len(names)
    if total < 2:
        raise GroupError(f"{total} map(s) cannot be grouped; the metric is pairwise")
    points = clouds(names, samples, weight)
    lattice = directions(count).astype(numpy.float32)
    where = _quantile_positions(samples, quantiles)
    low = numpy.floor(where).astype(numpy.intp)
    high = numpy.minimum(low + 1, samples - 1)
    fraction = (where - low).astype(numpy.float32)

    out = numpy.zeros((total, total), dtype=numpy.float64)
    for start in range(0, count, chunk):
        block = lattice[start : start + chunk]
        # [maps, samples, directions], sorted along the samples axis and read at
        # the quantile positions. The sort is the whole cost of the pass.
        projected = numpy.sort(points @ block.T, axis=1)
        signature = numpy.ascontiguousarray(
            (
                projected[:, low, :] * (1.0 - fraction)[None, :, None]
                + projected[:, high, :] * fraction[None, :, None]
            ).reshape(total, -1)
        )
        for index in range(total - 1):
            out[index, index + 1 :] += numpy.abs(signature[index + 1 :] - signature[index]).sum(
                axis=1, dtype=numpy.float64
            )
        if log is not None:
            log(f"[m1] directions {min(start + chunk, count)}/{count}")
    out /= float(count) * float(quantiles)
    out += out.T
    numpy.fill_diagonal(out, 0.0)
    return numpy.round(out, PLACES)


# --------------------------------------------------------------------------- #
# The linkage.
# --------------------------------------------------------------------------- #
def average_linkage(distance, stop: float):
    """Average linkage until the nearest live pair exceeds `stop`.

    Lance-Williams in distance space, weighted by cluster size — the recurrence
    that makes a merged cluster's distance the mean over its members' pairs rather
    than the mean of two cluster distances. Returns `(height, one, other)` per
    merge, in the order they happened.
    """
    import numpy

    count = distance.shape[0]
    live = numpy.array(distance, dtype=numpy.float64)
    numpy.fill_diagonal(live, numpy.inf)
    sizes = numpy.ones(count)
    merges = []
    for _ in range(count - 1):
        flat = int(numpy.argmin(live))
        one, other = divmod(flat, count)
        if one > other:
            one, other = other, one
        height = live[one, other]
        if not numpy.isfinite(height) or height > stop:
            break
        merges.append((float(height), one, other))
        combined = (sizes[one] * live[one] + sizes[other] * live[other]) / (
            sizes[one] + sizes[other]
        )
        sizes[one] += sizes[other]
        live[one] = combined
        live[:, one] = combined
        live[one, one] = numpy.inf
        live[other] = numpy.inf
        live[:, other] = numpy.inf
    return merges


def cut_at(merges, count: int, cut: float) -> list[list[int]]:
    """Every merge at or below `cut`, applied — the groups as lists of indices."""
    parent = list(range(count))

    def root(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for height, one, other in merges:
        if height > cut:
            break
        parent[root(other)] = root(one)
    found: dict[int, list[int]] = collections.defaultdict(list)
    for index in range(count):
        found[root(index)].append(index)
    return [sorted(group) for group in found.values()]


# --------------------------------------------------------------------------- #
# What a group's canonical member is.
# --------------------------------------------------------------------------- #
def label_rows() -> collections.Counter:
    """`{map: rows}` over the finished-render stores, as they resolve.

    Resolved rather than raw, because a render judged twice is one verdict and
    counting it twice would let a re-labeled batch move which member of a group is
    canonical without anybody deciding to.
    """
    from fractal_wallpapers.labeling import finished

    counter: collections.Counter = collections.Counter()
    for head in finished.HEADS:
        for row in finished.resolved(head).current.values():
            name = row.get("colormap")
            if name is not None:
                counter[name] += 1
    return counter


def canonical(members: list[str], rows: collections.Counter | None = None) -> str:
    """The member of a group that stands for it: most label rows, ties by name.

    "Most rows" rather than "most central" because the canonical name is what a
    record and a figure say out loud, and the map the corpus already talks about
    is the one a reader has seen before. It is **not** what the pool draws — see
    [`collapse`], which draws at random inside the group on purpose.
    """
    rows = label_rows() if rows is None else rows
    return min(members, key=lambda name: (-rows[name], name))


# --------------------------------------------------------------------------- #
# The record.
# --------------------------------------------------------------------------- #
def record_path(directory: Path | None = None) -> Path:
    """Where the table lives: beside the maps it groups."""
    return (Path(directory) if directory is not None else colormap_dir()) / RECORD_NAME


def record(directory: Path | None = None, cut: float = CUT, log=None) -> list[dict]:
    """The whole grouping, as the rows the tracked file holds.

    Singletons are counted in the header and not written as rows. A group of one
    is the map itself: it names no decision, it collapses to nothing, and seven
    hundred rows saying so would bury the sixty-five that do.
    """
    import numpy

    names = library(directory)
    if not names:
        raise GroupError("the colormap library is empty, so there is nothing to group")
    matrix = m1(names, log=log)
    merges = average_linkage(matrix, cut)
    found = cut_at(merges, len(names), cut)
    multi = [group for group in found if len(group) > 1]
    rows = label_rows()

    built = []
    for group in multi:
        inside = matrix[numpy.ix_(group, group)]
        members = [names[index] for index in group]
        built.append(
            {
                "size": len(group),
                "members": members,
                "canonical": canonical(members, rows),
                "label_rows": sum(rows[name] for name in members),
                "max_m1": round(float(inside.max()), 6),
                "mean_m1": round(float(inside[numpy.triu_indices(len(group), 1)].mean()), 6),
            }
        )
    # Tightest first, so the ids run from the merge nobody would argue with to the
    # one standing closest to the cut. Ties break on the first member's name, so the
    # numbering is a function of the library rather than of the merge order.
    built.sort(key=lambda group: (group["max_m1"], group["members"][0]))

    return [
        {
            "schema": SCHEMA,
            "kind": METHOD_ROW,
            "maps": len(names),
            "cut": cut,
            "groups": len(built),
            "grouped": sum(group["size"] for group in built),
            "singletons": len(found) - len(built),
            "largest": max((group["size"] for group in built), default=1),
            "samples": SAMPLES,
            "hue_weight": HUE_WEIGHT,
            "directions": DIRECTIONS,
            "quantiles": QUANTILES,
            "linkage": "average",
            "method": METHOD.format(
                cut=cut,
                samples=SAMPLES,
                weight=HUE_WEIGHT,
                weight_int=int(HUE_WEIGHT),
                directions=DIRECTIONS,
                quantiles=QUANTILES,
                marks=MARKS_RECORD_NAME,
            ),
            "marks": MARKS_RECORD_NAME,
        },
        *(
            {"schema": SCHEMA, "kind": GROUP_ROW, "group": f"m{number:02d}", **group}
            for number, group in enumerate(built, start=1)
        ),
    ]


def text_of(rows: list[dict]) -> str:
    """The file's text: one row to a line, the header first."""
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


def write(rows: list[dict], directory: Path | None = None) -> Path:
    path = record_path(directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text_of(rows), encoding="utf-8", newline="\n")
    return path


def read(directory: Path | None = None) -> list[dict]:
    """The committed grouping's rows, or an empty list if it was never written."""
    path = record_path(directory)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def groups(directory: Path | None = None) -> list[dict]:
    """Just the group rows of the committed table."""
    return [row for row in read(directory) if row.get("kind") == GROUP_ROW]


def marks_path(directory: Path | None = None) -> Path:
    """`<dir>/groups_marks.jsonl`, beside the grouping it decided."""
    from fractal_wallpapers.paths import colormap_dir

    return (Path(directory) if directory is not None else colormap_dir()) / MARKS_RECORD_NAME


def marks(directory: Path | None = None) -> list[dict]:
    """The marked pairs, in the order they were shown. Empty if the file is absent."""
    path = marks_path(directory)
    if not path.is_file():
        return []
    return [
        row
        for row in (
            json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line
        )
        if row.get("kind") == MARK_ROW
    ]


def cut_from_marks(rows: list[dict] | None = None, directory: Path | None = None) -> float | None:
    """The cut the marks imply: the midpoint of the widest SAME and the nearest DIFFERENT.

    **Below it**, and that qualifier is the whole of the honesty here. The marks
    do not sort cleanly: two pairs Matt called SAME sit *above* the nearest pair
    he called DIFFERENT, so no height agrees with all forty-six. The rule the cut
    is read by is one-sided — never merge a pair marked DIFFERENT — and the two
    SAME pairs above the line are the price, on record rather than rounded away.
    A cut derived by ignoring them would be the same number reported as though it
    had cost nothing.

    `None` where there are no marks, or where every SAME pair sits above the
    nearest DIFFERENT one, which would leave no height that keeps the one-sided
    rule and merges anything at all.
    """
    rows = marks(directory) if rows is None else rows
    same = [float(row["m1"]) for row in rows if row.get("mark") == SAME]
    different = [float(row["m1"]) for row in rows if row.get("mark") == DIFFERENT]
    if not same or not different:
        return None
    nearest = min(different)
    under = [value for value in same if value < nearest]
    if not under:
        return None
    return round((max(under) + nearest) / 2, 6)


def member_groups(directory: Path | None = None) -> dict[str, str]:
    """`{map: group id}` for every map the committed table puts in a group.

    Singletons are absent, because the record does not write them: a group of one
    names no decision. A caller that needs a total function over the library —
    the gallery pass's group cap does — reads a missing name as its own group,
    which is what a singleton is.
    """
    return {name: str(row["group"]) for row in groups(directory) for name in row["members"]}


def group_of(name: str, table: dict | None = None, directory: Path | None = None) -> str:
    """Which group one map belongs to; its own name where it is a group of one.

    The **total** form of [`member_groups`], and it is spelled here rather than at
    each call site so two callers cannot disagree about what a singleton is called.
    `table` is [`member_groups`] already read, for a caller asking this per row.
    """
    lookup = member_groups(directory) if table is None else table
    return lookup.get(str(name), f"map:{name}")


def run(directory: Path | None = None, cut: float = CUT, log=None) -> dict:
    """Recompute the grouping and write it. Returns what it wrote, in one line."""
    rows = record(directory, cut, log)
    path = write(rows, directory)
    header = rows[0]
    return {
        "path": str(path),
        "maps": header["maps"],
        "cut": header["cut"],
        "groups": header["groups"],
        "grouped": header["grouped"],
        "singletons": header["singletons"],
        "largest": header["largest"],
        "sizes": dict(sorted(collections.Counter(row["size"] for row in rows[1:]).items())),
    }


# --------------------------------------------------------------------------- #
# The read-time collapse.
# --------------------------------------------------------------------------- #
def enabled() -> bool:
    """Is the collapse on for *this* read? Read at call time, never at import.

    An unparseable value reads as the default and never as its own state: a typo
    in an environment variable must not silently widen a production pool.
    """
    raw = os.environ.get(COLLAPSE_ENV)
    if raw is None:
        return COLLAPSE_DEFAULT
    raw = raw.strip().lower()
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return False
    return COLLAPSE_DEFAULT


def collapse(names, seed: int, directory: Path | None = None) -> tuple[list[str], dict]:
    """`(pool, record)` — one member per group, drawn at random on `seed`.

    **At random inside the group, not the canonical member.** Matt's rule, and the
    reason is what a group means: its members are near enough that nobody can tell
    them apart, so no member of one deserves the slot more than another. Always
    drawing the canonical one would quietly retire every other member of every
    group from production while leaving it in the library; the collapse is meant to
    spend one slot on one look, not to pick a winner.

    The draw is seeded on the run's own seed, so two runs of one seed hold the same
    pool and two seeds spread across the group. A map the library holds but this
    pool does not is left alone, and a group with one member present is not a group.
    """
    names = list(names)
    present = set(names)
    draw = random.Random(seed)
    kept: dict[str, str] = {}
    dropped: dict[str, str] = {}
    for row in sorted(groups(directory), key=lambda row: row["group"]):
        members = sorted(name for name in row["members"] if name in present)
        if len(members) < 2:
            continue
        picked = members[draw.randrange(len(members))]
        kept[picked] = row["group"]
        for name in members:
            if name != picked:
                dropped[name] = row["group"]
    pool = [name for name in names if name not in dropped]
    return pool, {
        "collapsed": True,
        "seed": int(seed),
        "record": record_path(directory).name,
        "library": len(names),
        "pool": len(pool),
        "groups_collapsed": len(kept),
        "maps_stood_down": len(dropped),
        # Which map is standing for which group, so a run record answers "why is
        # this map absent" without its reader re-running the draw.
        "drawn": {group: name for name, group in sorted(kept.items(), key=lambda row: row[1])},
    }


__all__ = [
    "COLLAPSE_DEFAULT",
    "COLLAPSE_ENV",
    "CUT",
    "DIRECTIONS",
    "GROUP_ROW",
    "HUE_WEIGHT",
    "METHOD",
    "METHOD_ROW",
    "PLACES",
    "QUANTILES",
    "RECORD_NAME",
    "SAMPLES",
    "SCHEMA",
    "GroupError",
    "average_linkage",
    "canonical",
    "cloud",
    "clouds",
    "collapse",
    "cut_at",
    "directions",
    "enabled",
    "MARKS_RECORD_NAME",
    "MARK_ROW",
    "cut_from_marks",
    "group_of",
    "groups",
    "marks",
    "marks_path",
    "member_groups",
    "label_rows",
    "library",
    "m1",
    "read",
    "record",
    "record_path",
    "run",
    "text_of",
    "weighted",
    "write",
]
