"""A fixed battery of renders, hashed, for holding an engine change to zero behaviour.

An engine change that claims to move no pixel — a skip, a specialization, an inlining —
is held to that claim by rendering the same frames before and after and comparing the
bytes. Every such change until 2026-09-24 did it by hand, with a script that lived in an
ignored directory and was rewritten each time. This is that script, kept.

**The workflow is two recordings and a comparison.** Record a tag with the engine as
built, change the engine, rebuild it, record a second tag, and compare them:

    fractal-wallpapers identity before
    (edit, cargo build --release)
    fractal-wallpapers identity after --against before

Each recording is the build [`engine.engine_path`] finds, so the two tags are two builds
of one checkout and never two binaries side by side. Timing is a different question, with
a different method (alternated runs of both binaries), and is not asked here: the seconds
recorded beside each hash are a reading of one run three at a time on a busy machine.

**What the battery draws.** Every family's home view at the site's shipped constants and
at the two older Julia constants the first battery used, the three tracked anchors, and a
frame over the Mandelbrot interior; every mode in the engine's catalog, production and
niche; at 384x216 ss1, and the anchors, the interior frame and the degree-3 to degree-6
Julia homes again at 640x360 ss2. `--edges` adds the frames where an interior test is
riskiest instead — see [`edges`].
"""

from __future__ import annotations

import cmath
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fractal_wallpapers import engine
from fractal_wallpapers.paths import anchors_file, hot_root

#: The site explorer's shipped Julia constant, every degree: the tracked Julia anchor's.
SHIPPED_C = ("-0.07810228973371881", "-0.6514609012382414")

#: The constants the first battery drew the Julia degrees at (profiling_pass_ckpt146).
OLDER_C = {
    3: ("-0.4", "0.6"),
    4: ("-0.4", "0.6"),
    5: ("0.4", "0"),
    6: ("0.4", "0"),
}

#: The render pool's shape (CLAUDE.md): three engines at a time, below-normal priority,
#: which `engine.run` sets.
WORKERS = 3


def battery_dir() -> Path:
    """Where recordings land: `identity/` under the hot root."""
    return hot_root() / "identity"


def locations() -> dict[str, dict]:
    """The battery's frames by name: a family and, where it is not the home view, a viewport."""
    locs = {}
    for line in anchors_file().read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        loc = {"family": row["family"]}
        if "viewport" in row:
            loc["viewport"] = row["viewport"]
        locs["anchor-" + row["anchor"]] = loc
    locs["mandelbrot-home"] = {"family": {"kind": "mandelbrot"}}
    for degree in (3, 4, 5, 6):
        locs[f"multibrot{degree}-home"] = {"family": {"kind": "multibrot", "degree": degree}}
        locs[f"julia{degree}-home"] = {
            "family": {"kind": "julia", "degree": degree, "c": list(OLDER_C[degree])}
        }
        locs[f"julia{degree}-shipped"] = {
            "family": {"kind": "julia", "degree": degree, "c": list(SHIPPED_C)}
        }
    locs["phoenix_m-home"] = {"family": {"kind": "phoenix_m"}}
    locs["fractional2.5-home"] = {"family": {"kind": "fractional_multibrot", "degree": "2.5"}}
    # Inside the main cardioid, reaching the period-2 bulb's edge.
    locs["mandelbrot-interior"] = {
        "family": {"kind": "mandelbrot"},
        "viewport": {"center_re": "-0.75", "center_im": "0.1", "width": "0.3"},
    }
    return locs


def julia_disk(degree: int, c: complex) -> tuple[complex, float] | None:
    """The engine's `iterate::julia_disk`, step for step, for placing frames on its rim.

    A mirror rather than a call, because the engine exposes the disk to nothing but its
    own loop. It needs to agree to far better than the narrowest edge frame's width
    (1e-9), not to the bit: a frame that straddles the rim is the whole requirement. If
    the engine's constants move, move these with them.
    """
    settle, longest, close, slop, margin, smallest = 10_000, 64, 1e-9, 1e-10, 1e-3, 1e-6

    def step(z: complex) -> complex:
        acc = z
        for _ in range(1, degree):
            acc = acc * z
        return acc + c

    z = 0j
    for _ in range(settle):
        z = step(z)
        if not (z.real * z.real + z.imag * z.imag <= 16.0):
            return None
    cycle, w = [z], step(z)
    while abs(w - z) > close:
        if len(cycle) == longest:
            return None
        cycle.append(w)
        w = step(w)
    p = len(cycle)
    links = [(abs(cycle[i]), abs(step(cycle[i]) - cycle[(i + 1) % p])) for i in range(p)]

    def returns(r0: float) -> float:
        r = r0
        for modulus, residual in links:
            spread, binomial = 0.0, 1.0
            for k in range(1, degree + 1):
                binomial = binomial * (degree - k + 1) / k
                spread += binomial * modulus ** (degree - k) * r**k
            r = spread + residual + slop
            if not r <= 1.0:
                return float("inf")
        return r

    def closes(r0: float) -> bool:
        return returns(r0) <= (1.0 - margin) * r0

    low = 0.5
    while not closes(low):
        low *= 0.5
        if low < smallest:
            return None
    high = 2.0 * low
    for _ in range(30):
        middle = 0.5 * (low + high)
        if closes(middle):
            low = middle
        else:
            high = middle
    return cycle[0], low * (1.0 - 1e-6)


def edges() -> list[tuple[str, dict, str, list[int], int]]:
    """Frames on the edges of every interior test the engine makes before the cap.

    The main cardioid and the period-2 bulb (the cusp, the junction, points round both
    boundaries); each Multibrot degree's disk where it touches the main component and on
    the component's rim; and each Julia plane's attracting-cycle disk, at three points of
    its rim, at the shipped constant and the older ones. Four widths, 1e-2 to 1e-9, at the
    policy cap and at 50,000, in `smooth` and `stripe` (which the tests serve) and
    `smooth_trap_circle` (which they must not touch).
    """
    points: dict[str, tuple[dict, complex]] = {}
    mandelbrot = {"kind": "mandelbrot"}
    points["cusp"] = (mandelbrot, 0.25 + 0j)
    points["junction"] = (mandelbrot, -0.75 + 0j)
    for k, t in enumerate((0.3, 1.1, 2.0, 2.9)):
        w = cmath.exp(1j * t)
        points[f"card{k}"] = (mandelbrot, w / 2 - w * w / 4)
    for k, t in enumerate((0.4, 1.4, 2.6)):
        points[f"bulb{k}"] = (mandelbrot, -1 + 0.25 * cmath.exp(1j * t))
    for d in (3, 4, 5, 6):
        family = {"kind": "multibrot", "degree": d}
        rho = d ** (-1 / (d - 1))
        touch = rho * (1 - 1 / d)
        for k, turn in enumerate((0.0, 1.0 / (d - 1))):
            points[f"d{d}touch{k}"] = (family, touch * cmath.exp(2j * cmath.pi * turn))
        lam = cmath.exp(1j * cmath.pi / (d - 1) * 0.7)
        z = (lam / d) ** (1 / (d - 1))
        points[f"d{d}rim"] = (family, z * (1 - lam / d))
    constants = {"shipped": SHIPPED_C, **{f"older{d}": c for d, c in OLDER_C.items()}}
    for d in (2, 3, 4, 5, 6):
        for label, c in constants.items():
            disk = julia_disk(d, complex(float(c[0]), float(c[1])))
            if disk is None:
                continue
            center, radius = disk
            family = {"kind": "julia", "degree": d, "c": list(c)}
            for k, t in enumerate((0.3, 1.9, 3.7)):
                points[f"julia{d}-{label}-rim{k}"] = (family, center + radius * cmath.exp(1j * t))
    out = []
    for name, (family, point) in points.items():
        for width in ("1e-2", "1e-4", "1e-6", "1e-9"):
            for cap in (None, 50000):
                loc = {
                    "family": family,
                    "viewport": {
                        "center_re": repr(point.real),
                        "center_im": repr(point.imag),
                        "width": width,
                    },
                }
                if cap:
                    loc["maxiter"] = cap
                for mode in ("smooth", "stripe", "smooth_trap_circle"):
                    out.append(
                        (f"edge-{name}-{width}-{cap}.{mode}.256ss1", loc, mode, [256, 144], 1)
                    )
    return out


def jobs(edge_frames: bool) -> list[tuple[str, dict, str, list[int], int]]:
    """The battery as `(name, location, mode, resolution, supersample)` rows."""
    if edge_frames:
        return edges()
    locs = locations()
    modes = [mode["name"] for mode in engine.modes()]
    out = []
    for name, loc in locs.items():
        for mode in modes:
            out.append((f"{name}.{mode}.384ss1", loc, mode, [384, 216], 1))
    twice = ["anchor-julia", "anchor-mandelbrot", "anchor-phoenix", "mandelbrot-interior"]
    twice += [f"julia{d}-shipped" for d in (3, 4, 5, 6)]
    for name in twice:
        for mode in modes:
            out.append((f"{name}.{mode}.640ss2", locs[name], mode, [640, 360], 2))
    return out


def draw(job, scratch: Path) -> tuple[str, str, float]:
    """Render one row and return its name, the PNG's sha256 and the wall time."""
    name, loc, mode, resolution, supersample = job
    png = scratch / f"{name}.png"
    spec = {
        "schema": 1,
        **loc,
        "resolution": resolution,
        "supersample": supersample,
        "mode": mode,
        "colormap": "twilight_shifted",
        "output": str(png),
    }
    started = time.perf_counter()
    try:
        engine.render(spec)
    except RuntimeError as refusal:
        return name, "ERROR " + str(refusal)[-200:], time.perf_counter() - started
    seconds = time.perf_counter() - started
    digest = hashlib.sha256(png.read_bytes()).hexdigest()
    png.unlink()
    return name, digest, seconds


def record(tag: str, edge_frames: bool = False, log=print) -> Path:
    """Draw the battery through the built engine and write `<tag>.json` of hashes."""
    directory = battery_dir()
    scratch = directory / f"{tag}.renders"
    scratch.mkdir(parents=True, exist_ok=True)
    todo = jobs(edge_frames)
    log(f"{len(todo)} renders through {engine.engine_path()}, {WORKERS} at a time")
    started = time.perf_counter()
    with ThreadPoolExecutor(WORKERS) as pool:
        results = list(pool.map(lambda job: draw(job, scratch), todo))
    scratch.rmdir()
    document = {
        "schema": 1,
        "edges": edge_frames,
        "hashes": {name: digest for name, digest, _ in results},
        "seconds": {name: round(seconds, 3) for name, _, seconds in results},
    }
    path = directory / f"{tag}.json"
    path.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8", newline="\n")
    errors = sum(1 for _, digest, _ in results if digest.startswith("ERROR"))
    log(f"{len(results)} renders, {errors} refused, {time.perf_counter() - started:.0f} s")
    return path


def compare(tag: str, other: str) -> list[str]:
    """The names whose hashes differ between two recordings, or that one of them lacks."""
    a = json.loads((battery_dir() / f"{tag}.json").read_text(encoding="utf-8"))["hashes"]
    b = json.loads((battery_dir() / f"{other}.json").read_text(encoding="utf-8"))["hashes"]
    return sorted(name for name in a.keys() | b.keys() if a.get(name) != b.get(name))
