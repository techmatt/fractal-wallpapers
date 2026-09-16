"""Which places are on the atlas, and the greedy pass that thins them to dots.

**The population is one bar.** A place qualifies if it holds at least one row the fine
head reads at or above [`solve.DEFAULT_FINE_BAR`] — the same bar a solve narrows its pool
with — on either partition the plane carries. Nothing else qualifies: no union with the
human verdicts, no top-quarter cut by the candidate judge. That is what makes the gallery
slot honest, because the best row at a qualifying place clears the bar by construction and
so is a wallpaper somebody could seat rather than a location view standing in for one.

**A dot is one place of one kind.** The queue is every seated place first — the named
record's own — then everything else by best `p_fine`, and one greedy pass down it: a place
landing inside the radius of a dot already placed is **dropped**, whichever kind either of
them is. There is no cross-kind merge, so a dot's colour on the page is a fact about the
place rather than about what happened to be near it.

**Reading the stores holds the candidate ledger's location map, so this is a pool-holding
process** — never beside a solve, a growth pass or the slow lane.
"""

from __future__ import annotations

import json
import time

#: The two ledger partitions the Mandelbrot plane carries, and the word the record spells
#: each with. The page colours by that word — one colour for a parameter-plane place,
#: another for a dynamical one — so it is the shorter spelling rather than the ledger's.
MANDELBROT = "mandelbrot"
JULIA = "julia:mandelbrot"
KIND = {MANDELBROT: "mandelbrot", JULIA: "julia"}

#: How many of a place's best `p_fine` rows are kept. The gallery slot wants the best one
#: the ledger can hand back a recipe for, and one is almost always enough; the other two
#: are there so that a row the ledger no longer answers to costs a picture rather than a
#: dot.
FINE_KEPT = 3


def stamp(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def position(key_text: str):
    """`(partition, place, x, y)` for a location key as every store spells it, or `None`.

    A parameter-plane place is its whole location key — its frame is what it is. A
    dynamical place is its `c` alone, because the dynamical plane is a different fractal
    for every parameter and a hundred frames of one `c` are a hundred views of one point
    of the plane the plate draws: 13,030 julia location keys land on 181 parameters.
    """
    try:
        key = json.loads(key_text)
    except (TypeError, ValueError):
        return None
    if not isinstance(key, list) or len(key) < 6:
        return None
    try:
        if key[0] == MANDELBROT:
            return MANDELBROT, key_text, float(key[3]), float(key[4])
        if key[0] == JULIA:
            constants = key[2]
            if not constants or not constants[0]:
                return None
            return JULIA, json.dumps(constants[0]), float(constants[0][0]), float(constants[0][1])
    except (TypeError, ValueError, IndexError):
        return None
    return None


class Place:
    """One point of the plane, and everything the record says about it."""

    __slots__ = (
        "partition",
        "place",
        "x",
        "y",
        "location",
        "p_ge4",
        "judged_rows",
        "fine_rows",
        "fine_at_bar",
        "seat",
    )

    def __init__(self, partition: str, place: str, x: float, y: float) -> None:
        self.partition, self.place, self.x, self.y = partition, place, x, y
        self.location: str | None = None
        self.p_ge4: float | None = None
        self.judged_rows = 0
        #: The best [`FINE_KEPT`] rows by `p_fine`, descending.
        self.fine_rows: list[tuple[float, str]] = []
        #: How many of this place's rows clear the bar. One is enough to qualify.
        self.fine_at_bar = 0
        self.seat: dict | None = None

    def offer(self, value: float, key: str) -> None:
        self.fine_rows.append((value, key))
        self.fine_rows.sort(key=lambda row: (-row[0], row[1]))
        del self.fine_rows[FINE_KEPT:]

    @property
    def p_fine(self) -> float | None:
        return self.fine_rows[0][0] if self.fine_rows else None


def collect(record: str, partitions: tuple[str, ...]) -> dict:
    """Every qualifying place on the plane, with its judges' readings and its seat."""
    from fractal_wallpapers.curation import solve, tentative
    from fractal_wallpapers.curation.candidate_ledger import store
    from fractal_wallpapers.models import gallery_grade_train

    bar = float(solve.DEFAULT_FINE_BAR)
    places: dict[tuple[str, str], Place] = {}
    #: A location key parses to the same place every time and there are twenty rows to a
    #: place, so the parse is memoised: without it this spends most of its time in
    #: `json.loads` on text it has already read.
    parsed: dict[str, tuple | None] = {}

    def where_of(key_text: str):
        if key_text not in parsed:
            parsed[key_text] = position(key_text)
        return parsed[key_text]

    def held_at(key_text: str) -> Place | None:
        where = where_of(key_text)
        return None if where is None else places.get((where[0], where[1]))

    def place_of(key_text: str) -> Place | None:
        where = where_of(key_text)
        if where is None:
            return None
        partition, place, x, y = where
        held = places.get((partition, place))
        if held is None:
            held = places[(partition, place)] = Place(partition, place, x, y)
        if held.location is None:
            held.location = key_text
        return held

    stamp("streaming the candidate ledger")
    location_of: dict[str, str] = {}
    rows_seen = 0
    for row in store.stream():
        rows_seen += 1
        if row.get("partition") not in partitions:
            continue
        key = (row.get("location") or {}).get("key")
        if key:
            location_of[str(row["key"])] = str(key)
    stamp(f"{rows_seen:,} ledger rows, {len(location_of):,} on the plane")

    stamp(f"reading the fine head's pool scores at the bar {bar:g}")
    pool = gallery_grade_train.read_pool_scores()
    readings = 0
    for key, row in pool.items():
        where = location_of.get(str(key))
        if where is None:
            continue
        value = row.get("p_ge4")
        if value is None:
            continue
        value = float(value)
        readings += 1
        if value < bar:
            continue
        held = place_of(where)
        if held is None:
            continue
        held.fine_at_bar += 1
        held.offer(value, str(key))
    stamp(
        f"{len(pool):,} p_fine readings, {readings:,} on the plane, "
        f"{len(places):,} places at or above the bar"
    )

    # The live judge is not a population here — it is a reading the record carries beside
    # the fine head's, on the places the bar already admitted.
    live = store.live_artifact()
    stamp(f"streaming the score sidecar on {live[:16]}…")
    for row in store.stream_scores():
        if str(row.get("judge_artifact")) != live:
            continue
        where = location_of.get(str(row.get("recipe_key")))
        if where is None:
            continue
        held = held_at(where)
        if held is None:
            continue
        held.judged_rows += 1
        value = row.get("p_ge4")
        if value is None:
            continue
        value = float(value)
        if held.p_ge4 is None or value > held.p_ge4:
            held.p_ge4 = value

    stamp(f"reading the record {record}")
    seats = unqualified = 0
    for row in tentative.read_rows(record):
        if row.get("partition") not in partitions:
            continue
        held = held_at(str(row["location"]))
        if held is None:
            unqualified += 1
            continue
        seats += 1
        held.location = str(row["location"])
        if held.seat is None or float(row.get("p_ge4") or 0) > float(held.seat.get("p_ge4") or 0):
            held.seat = {
                "key": str(row["key"]),
                "alias": str(row["alias"]),
                "seat": int(row["seat"]),
                "mode": str(row["mode"]),
                "p_ge4": row.get("p_ge4"),
                "cell": row.get("cell"),
            }
    stamp(f"{seats:,} seats land on a qualifying place, {unqualified:,} on one under the bar")
    return {
        "places": places,
        "live": live,
        "fine_bar": bar,
        "ledger_rows": rows_seen,
        "seats_under_bar": unqualified,
    }


class Dot:
    __slots__ = ("px", "py", "place", "dropped")

    def __init__(self, px: float, py: float, place: Place) -> None:
        self.px, self.py = px, py
        self.place = place
        self.dropped = 0


def thin(places, view: dict, resolution, radius_px: float) -> tuple[list[Dot], dict]:
    """One queue, one pass, and the survivors.

    Seated places go first and everything else follows by best `p_fine`, ties broken on
    the place's own text so the pass is a function of its inputs. A newcomer inside
    `radius_px` of a dot already standing is dropped and counted against the nearest one —
    **whichever kind either of them is**, because two places one pixel apart are one place
    to a reader.
    """
    width_px, height_px = resolution
    cx, cy = float(view["center_re"]), float(view["center_im"])
    per_px = float(view["width"]) / width_px

    def to_px(x: float, y: float) -> tuple[float, float]:
        return ((x - cx) / per_px + width_px / 2.0, (cy - y) / per_px + height_px / 2.0)

    queue = [
        (0 if held.seat is not None else 1, -(held.p_fine or 0.0), held.place, held)
        for held in places
    ]
    queue.sort(key=lambda row: row[:3])

    dots: list[Dot] = []
    dropped = 0
    radius2 = radius_px * radius_px
    for _tier, _score, _name, held in queue:
        px, py = to_px(held.x, held.y)
        nearest, best = None, None
        for dot in dots:
            distance = (dot.px - px) ** 2 + (dot.py - py) ** 2
            if distance <= radius2 and (best is None or distance < best):
                nearest, best = dot, distance
        if nearest is None:
            dots.append(Dot(px, py, held))
            continue
        nearest.dropped += 1
        dropped += 1
    tally = {
        "queued": len(queue),
        "dropped": dropped,
        "dots": len(dots),
        "mandelbrot": sum(1 for d in dots if KIND[d.place.partition] == "mandelbrot"),
        "julia": sum(1 for d in dots if KIND[d.place.partition] == "julia"),
        "seated": sum(1 for d in dots if d.place.seat is not None),
    }
    return dots, tally
