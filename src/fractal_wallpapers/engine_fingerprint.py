"""Which engine build drew a picture, asked as a digest of what it draws.

Every pixel here is made by one Rust binary, and until now nothing in the
identity chain said *which* binary. [`fractal_wallpapers.discovery.identity`]
pins four settings — the colormap, that the map is cyclic, the node frame, and
the iteration cap policy — and all four can hold while the engine underneath
them is a different program. A cached view is a picture some build drew on some
night; a score read off it is a claim about today's engine that nobody checked.

## The build's identity is what it draws

Byte-identity of output is already this engine's contract: the native and wasm
halves are held to the same bytes, and the escape-loop specialization was merged
on the strength of 347 renders hashing the same before and after. So a digest of
a fixed probe set, rendered through the production path, IS the build identity —
and it is a better one than a source revision, because it also catches a binary
rebuilt from unchanged source by a different toolchain, and one whose *mode
catalog* moved without its arithmetic moving.

It needs no build system, no revision plumbing, and no cooperation from the
crate. It costs one render per probe, once per process.

**The probes are pinned, and they are a SAMPLE rather than a cover.** Four
family kinds, six modes, both planes, and one `itinerary` — the mode whose
address opens differently on a dynamical plane — because the escape loop is
written out per family *and per channel set*, and a change to one specialization
would be invisible to a probe set that only drew `smooth` on a Mandelbrot. The
geometry is the node regime's, which is the frame the views this pin protects
are drawn at.

**What that sample does not see.** [`IDENTITY_PROBES`] is six fixed rows and the
mode roster is nineteen, so a change confined to one of the modes nobody probes
moves no pixel this digest reads, and a build that **adds** a mode is invisible to
it outright — the six probes come back byte-identical and the fingerprint does
not move. Same for a family kind, a curve or a palette operator outside the six.
This says *these six renders came back different*, and a fingerprint that has not
moved is evidence about the probed path and not a certificate about the build. It
is not the roster's guard either: the mode catalog is pinned against the engine's
own list by [`curation.mode_policy`], which refuses when the two describe
different rosters, and that is the check a new mode trips.

## Widening the sample costs a re-stamp, so the sample has two halves

The probe set cannot simply grow. [`current`] is a digest over the probes'
`(index, bytes)` pairs, so a seventh row moves it — and every stamp already
written names the old number. On the machine this split was made on that was
**48,571 stamped views under one fingerprint**, across the walk ledgers' views,
their framings and flip samples, the reframing rungs and one gallery pass's
framings; adding a probe would have marked every one of them stale, and a stale
view is one that gets drawn again for a reason that is not a changed engine.

So there are two sets and two digests. [`IDENTITY_PROBES`] is the six, and
[`current`] — the number a stamp carries — digests exactly those, in exactly that
order, for ever. [`TRAP_PROBES`] is what widening the sample looks like: one row
per direct trap, the four colorings whose arithmetic the six could not see at all.
[`coverage`] digests both halves and **nothing stamps it**, so a probe may be
added to the second set at no cost to any picture already on disk. A build whose
coverage digest moved while its identity digest held is a build whose direct
traps changed, which is precisely the question the six could not ask.

**And neither digest reaches the candidate pool.** A stamp is written beside a
*view*; [`curation.candidate_ledger`]'s rows carry no engine at all, so the
hundreds of thousands of candidate pictures name their recipe and nothing names
their build. Widening the probe set makes the fingerprint honest about the direct
traps; it does not put a direct-trap render under guard, and the thing standing
between a changed trap and a ledger full of stale judgements is still
`test_renders.py::test_a_regenerated_picture_is_the_picture_that_was_judged`.

## A picture says which build drew it, beside the picture

A view is addressed by a digest of its own recipe, so the name it is filed under
cannot carry this: putting the fingerprint in the name would rename every view
on every engine change and orphan the `score_view` each ledger row records. The
stamp goes *beside* the picture instead, in one JSONL per view directory —
[`Stamps`] — and a view the manifest says nothing about is [`UNKNOWN`], which is
not the current build and is therefore stale. That is the honest reading: every
view drawn before this module existed was drawn by a build nobody wrote down.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from functools import cache
from pathlib import Path

#: The schema every stamp row carries.
SCHEMA = 1

#: What a view drawn before anything recorded the build is stamped. Never equal
#: to a fingerprint, so such a view is always stale — which is the point: "nobody
#: wrote it down" and "today's engine drew it" are different facts, and a pin
#: that conflated them would be worth nothing.
UNKNOWN = "unknown"

#: How many hex characters a fingerprint is. The same length the render cache
#: names a job with, for the same reason: long enough not to collide, short
#: enough to sit on every row of a ninety-thousand-row record.
LENGTH = 16

#: What a view directory's stamp manifest is called.
STAMPS_NAME = "drawn_by.jsonl"

#: The frame every probe is drawn at, and the field samples under it. The node
#: regime's, spelled here rather than imported: a probe set that moved when the
#: regime table moved would be a fingerprint that changes for a reason which is
#: not the engine.
RESOLUTION = (384, 216)
SUPERSAMPLE = 1

#: The map every probe is drawn through. Cyclic, so nothing is mirrored and the
#: palette pass is the one that does nothing — a probe is about the field and the
#: coloring, and a fold would only add a second thing for it to be about.
COLORMAP = "twilight_shifted"

#: **The stamped half of the probe set: what is drawn to name a build.**
#:
#: [`current`] digests exactly these, in exactly this order, and that is a promise
#: rather than an implementation note — every stamp in every [`STAMPS_NAME`] ever
#: written is a digest of this tuple, so a row added here re-stamps the world. New
#: probes go in [`TRAP_PROBES`]; see the module docstring for what that cost was
#: measured at.
#:
#: Every value is written out, the iteration caps included. The cap *policy* is
#: checked elsewhere and by a different mechanism — `discovery.identity` reads
#: the caps the tile corpus recorded against the caps the engine gives those same
#: widths today — so a probe that asked the engine for its own cap would fold two
#: independent questions into one number and neither would be answerable from it.
#: What this asks is narrower and sharper: given this exact instruction, which
#: bytes come back.
IDENTITY_PROBES: tuple[dict, ...] = (
    {
        "family": {"kind": "mandelbrot"},
        "viewport": {"center_re": "-0.77", "center_im": "0.0", "width": "4.4"},
        "maxiter": 2000,
        "mode": "smooth",
    },
    {
        "family": {"kind": "mandelbrot"},
        "viewport": {"center_re": "-0.75", "center_im": "0.1", "width": "0.05"},
        "maxiter": 12000,
        "mode": "tia",
    },
    {
        "family": {"kind": "multibrot", "degree": 5},
        "viewport": {"center_re": "0.0", "center_im": "0.0", "width": "3.0"},
        "maxiter": 4000,
        "mode": "stripe",
    },
    {
        "family": {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]},
        "viewport": {"center_re": "0.0", "center_im": "0.0", "width": "3.0"},
        "maxiter": 4000,
        "mode": "gaussian_int",
    },
    {
        "family": {"kind": "julia", "degree": 4, "c": ["-0.0643", "0.7209"]},
        "viewport": {"center_re": "0.0", "center_im": "0.0", "width": "2.5"},
        "maxiter": 6000,
        "mode": "itinerary",
    },
    {
        "family": {
            "kind": "phoenix",
            "c": ["-0.0397", "0.3155"],
            "p": ["0.2635", "-0.4210"],
            "z_prev": ["-0.3109", "-0.0169"],
        },
        "viewport": {"center_re": "-0.124", "center_im": "0.4916", "width": "0.4196"},
        "maxiter": 7000,
        "mode": "smooth_trap_circle",
    },
)

#: **The unstamped half: one row per direct trap.**
#:
#: The six above draw a *field* and look it up in the gradient once. A direct trap
#: makes no field at all — it composites a gradient sample into the pixel at every
#: near miss the orbit makes — so none of its arithmetic is on the path they walk,
#: and none of it is in the recipe key either: `renders.spec_of`'s coloring block
#: carries the trap's `shape`, `threshold`, `opacity`, `merge` and `start_color`
#: and no arithmetic. A whole-frame normalization, a gamma before the multiply or
#: a second saturation clamp would change every direct-trap picture in this
#: project while every name and every one of these digests held. That is the gap
#: these four close, and [`coverage`] is where they close it.
#:
#: **One per shape and both blends, because that is the axis a trap can move on.**
#: `Shape::Cross` twice — screened from black, which is the pair `direct_trap`
#: clamps, and multiplied from white, which is the one that whitewashes;
#: `Shape::Lines`, the anisotropic member; and `Shape::Ring`, the only shape whose
#: measure reads the trap radius. The families are secondary here and deliberately
#: so: `Painter::trace` reaches the plane through the same `family.step` the six
#: already exercise, so a family's arithmetic moves them first.
#:
#: The places are real ones — each is a location the candidate ledger holds a
#: clearing row at in that mode, so every probe paints a frame with something in
#: it rather than a shape the orbit never reaches. Measured at the geometry below:
#: 0.053 s, 0.024 s, 0.040 s and 0.110 s, against 1.85 s for the six.
TRAP_PROBES: tuple[dict, ...] = (
    {
        "family": {
            "kind": "julia",
            "degree": 4,
            "c": ["-0.8000969197766781", "0.07666925698290561"],
        },
        "viewport": {
            "center_re": "0.19452143712062242",
            "center_im": "-0.42589400136861216",
            "width": "0.2492067823119563",
        },
        "maxiter": 8307,
        "mode": "direct_trap_multiply",
    },
    {
        "family": {
            "kind": "julia",
            "degree": 2,
            "c": ["-1.2540170796954613", "-0.07161459637319667"],
        },
        "viewport": {
            "center_re": "-0.047306259424992066",
            "center_im": "0.002460367531600033",
            "width": "1.2143381496233348",
        },
        "maxiter": 5565,
        "mode": "direct_trap_screen",
    },
    {
        "family": {
            "kind": "julia",
            "degree": 3,
            "c": ["0.4169190761394084", "0.006933824661843332"],
        },
        "viewport": {
            "center_re": "0.241445298361125",
            "center_im": "-0.6009932805920934",
            "width": "0.28566628404124894",
        },
        "maxiter": 8071,
        "mode": "direct_trap_lines",
    },
    {
        "family": {"kind": "mandelbrot"},
        "viewport": {
            "center_re": "-0.8006991019229008",
            "center_im": "-0.15527152760149932",
            "width": "0.0006270775501623497",
        },
        "maxiter": 18668,
        "mode": "direct_trap_ring",
    },
)

#: Every probe there is, the stamped half first. What [`coverage`] digests, and
#: what a reader asking *which colorings does this fingerprint see* should read.
#:
#: The order matters and is not cosmetic: [`_digest`] takes a **count**, so the
#: identity digest is the first `len(IDENTITY_PROBES)` of this tuple and the two
#: halves cannot drift into hashing different bytes for the same probe.
PROBES: tuple[dict, ...] = IDENTITY_PROBES + TRAP_PROBES


class FingerprintError(RuntimeError):
    """The engine cannot be asked what it draws, so its build cannot be named."""


def probe_row(probe: dict) -> dict:
    """One probe as the render-cache row it is drawn from.

    Through the same shape every other picture in this project is described by,
    so [`fractal_wallpapers.models.renders.spec_of`] stays the one derivation of
    what the engine is told. The fingerprint is a fingerprint of the *production
    path*, not of a second way to ask for pixels.
    """
    from fractal_wallpapers.labeling import finished

    return {
        "family": probe["family"],
        "viewport": probe["viewport"],
        "mode": probe["mode"],
        "mode_params": {},
        "curve": "linear",
        "colormap": COLORMAP,
        "recipe": finished.recipe(mirror=False),
        "render": {
            "resolution": list(RESOLUTION),
            "supersample": SUPERSAMPLE,
            "maxiter": int(probe["maxiter"]),
        },
    }


@cache
def current() -> str:
    """This engine build's fingerprint: [`IDENTITY_PROBES`], drawn and digested.

    **The number a stamp carries**, and the six probes are all of it. Widening the
    sample is [`coverage`]'s job precisely so that this one does not move when the
    sample widens — see the module docstring.

    Cached for the process. A build cannot change under a running command, and
    the alternative — re-rendering six probes at every staleness check — would
    make the check the most expensive thing a scoring pass does.
    """
    return _digest(str(_engine_path()), len(IDENTITY_PROBES))


@cache
def coverage() -> str:
    """What this build draws over **every** probe, [`TRAP_PROBES`] included.

    Nothing stamps this and nothing keys on it, which is what makes the probe set
    growable at all. What it is *for* is the comparison: a build whose coverage
    digest moved while [`current`] held is a build whose direct traps changed, and
    that is a change no recipe key and no stamp anywhere in this project can see.

    The six identity probes are drawn once and their bytes serve both digests, so
    asking for both costs ten renders rather than sixteen.
    """
    return _digest(str(_engine_path()), len(PROBES))


@cache
def _digest(binary: str, count: int) -> str:
    """The digest over the first `count` probes, drawn now.

    Keyed on the path so two builds can be asked about in one process. The digest
    is over the *pairs* — which probe produced which bytes — so a probe reordered
    or dropped is a different fingerprint, and a probe that failed cannot be
    quietly skipped.

    A **count** rather than a probe tuple, so the identity digest is a prefix of
    the coverage one by construction: the two cannot come to disagree about what
    probe 3 is, and the material behind [`current`] is byte for byte the material
    it was before [`TRAP_PROBES`] existed.
    """
    marks = [[index, _mark(binary, index)] for index in range(int(count))]
    material = json.dumps(marks, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:LENGTH]


@cache
def _mark(binary: str, index: int) -> str:
    """One probe's bytes, digested. Drawn at most once per (build, probe)."""
    from fractal_wallpapers import engine
    from fractal_wallpapers.models import renders

    del binary  # The cache key. The engine resolves its own binary below.
    probe = PROBES[index]
    with tempfile.TemporaryDirectory(prefix="engine-fingerprint-") as where:
        output = Path(where) / f"probe{index}.jpg"
        try:
            engine.run("render", renders.spec_of(probe_row(probe), output))
        except (RuntimeError, OSError) as failure:
            raise FingerprintError(
                f"probe {index} ({probe['family']['kind']} through {probe['mode']}) would "
                f"not render, so this engine build cannot be named: {failure}"
            ) from failure
        if not output.is_file():
            raise FingerprintError(f"probe {index} reported success and wrote nothing to {output}.")
        return hashlib.sha256(output.read_bytes()).hexdigest()


def _engine_path() -> Path:
    """The binary [`current`] is keyed on, or a refusal naming the build command."""
    from fractal_wallpapers import engine

    try:
        return engine.engine_path()
    except FileNotFoundError as absent:
        raise FingerprintError(str(absent)) from absent


# --------------------------------------------------------------------------- #
# The stamp beside the picture.
# --------------------------------------------------------------------------- #
class Stamps:
    """Which build drew each picture in one view directory.

    A JSONL beside the pictures, one row per view, last row winning — so a view
    re-rendered under a new build is a row appended rather than a file rewritten,
    and a refresh interrupted halfway has recorded exactly what it finished.

    Read once and held, because the callers are loops of tens of thousands over a
    manifest of tens of thousands of rows. Held per directory by [`stamps`],
    which is what makes "is this view current" a dictionary lookup.
    """

    def __init__(self, directory, fingerprint: str | None = None):
        self.directory = Path(directory)
        self.fingerprint = current() if fingerprint is None else str(fingerprint)
        self._drawn: dict[str, str] | None = None
        self._handle = None

    @property
    def path(self) -> Path:
        return self.directory / STAMPS_NAME

    def drawn(self) -> dict[str, str]:
        """`{view name: fingerprint}` as the manifest stands."""
        if self._drawn is None:
            self._drawn = read(self.path)
        return self._drawn

    def drawn_by(self, name) -> str:
        """The build that drew this view, or [`UNKNOWN`] where nothing says."""
        return self.drawn().get(str(name), UNKNOWN)

    def is_current(self, name) -> bool:
        """Whether this view was drawn by the build asking."""
        return self.drawn_by(name) == self.fingerprint

    def record(self, *names) -> None:
        """Stamp these views as drawn by this build. Appends; never rewrites.

        The handle is opened once and held, flushed after every row. A bulk
        refresh calls this once per render — ninety thousand times — and opening
        and closing the file each time cost 18 ms a view on Windows, which is
        more than half of what the render itself costs. Flushed rather than
        buffered, because a stamp that a kill loses is a view that gets drawn
        twice for no reason.
        """
        fresh = [str(name) for name in names]
        if not fresh:
            return
        if self._handle is None:
            self.directory.mkdir(parents=True, exist_ok=True)
            self._handle = self.path.open("a", encoding="utf-8", newline="\n")
        for name in fresh:
            row = {"schema": SCHEMA, "view": name, "engine": self.fingerprint}
            self._handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._handle.flush()
        self.drawn().update({name: self.fingerprint for name in fresh})

    def close(self) -> None:
        """Let go of the manifest. The process exit does this too."""
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def summary(self) -> dict:
        """What a record says about this directory's stamps."""
        drawn = self.drawn()
        return {
            "directory": str(self.directory),
            "engine": self.fingerprint,
            "stamped": len(drawn),
            "current": sum(1 for mark in drawn.values() if mark == self.fingerprint),
        }


def read(path) -> dict[str, str]:
    """`{view name: fingerprint}` from one stamp manifest. Last row wins."""
    path = Path(path)
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema") != SCHEMA:
            raise FingerprintError(
                f"{path}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}"
            )
        out[str(row["view"])] = str(row["engine"])
    return out


#: One [`Stamps`] per (directory, fingerprint), for the process.
_HELD: dict[tuple[str, str], Stamps] = {}


def stamps(directory, fingerprint: str | None = None) -> Stamps:
    """The [`Stamps`] for one directory, made once per process.

    A scoring pass asks about one directory tens of thousands of times, and every
    one of those questions would otherwise re-read a manifest as long as the
    cache it describes.
    """
    mark = current() if fingerprint is None else str(fingerprint)
    key = (str(Path(directory).resolve()), mark)
    held = _HELD.get(key)
    if held is None:
        held = _HELD[key] = Stamps(directory, mark)
    return held


def forget() -> None:
    """Drop every held manifest. For tests, which make a directory per case."""
    for held in _HELD.values():
        held.close()
    _HELD.clear()


__all__ = [
    "COLORMAP",
    "IDENTITY_PROBES",
    "LENGTH",
    "PROBES",
    "RESOLUTION",
    "SCHEMA",
    "STAMPS_NAME",
    "SUPERSAMPLE",
    "TRAP_PROBES",
    "UNKNOWN",
    "FingerprintError",
    "Stamps",
    "coverage",
    "current",
    "forget",
    "probe_row",
    "read",
    "stamps",
]
