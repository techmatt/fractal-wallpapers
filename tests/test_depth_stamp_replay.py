"""A depth run's own record is enough to redraw the picture it made.

`sequence.jsonl` is the record the seat of a depth candidate resolves through —
the ledger row keeps only the **reduced** stamp, because the curve is derived
from the render and is not part of a recipe's identity, so the curve has to be on
the run's record or nowhere. Until 2026-09-02 it was nowhere: the row said
`acted` and dropped everything the operator did, and 241,552 of the 457,143 rows
across 51 runs are still that way.

This is the guard that the new rows are not. It goes the whole distance on
purpose — render a real candidate through `colorize.render`, put the stamp
through JSON exactly as the record does, read it back and rebuild the picture out
of the row alone — because every cheaper version of it passes on a stamp that
could not actually replay. What is deliberately *not* used is the `.leveled`
directory the operator leaves beside the picture: that is the operator's own
working, and a replay that read it would be checking the run against itself.

**Re-measuring is not the same thing and that is the whole point.** The same
frame redrawn and re-measured derives a different curve — 0.6336 against the
0.5953 a run stamped, on `ed49980b` — so a redraw off a re-measurement publishes
a different picture under the same name. Replay reads the numbers the run wrote.

Slow lane, and it needs a **release** engine: three renders.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers import engine
from fractal_wallpapers.coloring import autolevel
from fractal_wallpapers.coloring import band as band_module
from fractal_wallpapers.curation import colorize, depth
from fractal_wallpapers.paths import colormap_dir

try:
    ENGINE = engine.engine_path()
except FileNotFoundError:
    ENGINE = None

needs_engine = pytest.mark.skipif(ENGINE is None, reason="the engine is not built")

#: A real location off a production draw, at a map the same draw spent, where the
#: operator **fires**. Shared with `tests/test_autolevel_identity.py`'s pinned set
#: — the same probe, so a change that moved the operator moves both guards rather
#: than leaving this one quietly passing against a picture that also moved.
PROBE = {
    "family": {
        "c": ["0.2995601657228102", "-0.024825619193795445"],
        "degree": 2,
        "kind": "julia",
    },
    "viewport": {
        "center_re": "-0.436866950370211",
        "center_im": "0.23054661143294045",
        "width": "0.12305352558744842",
    },
    "maxiter": 9529,
    "mode": "smooth",
    "colormap": "Faded Salon",
}

#: The geometry the probe is drawn at. Small and supersampled: this is about the
#: record, not the resolution, and the resample filter is in both renders.
RESOLUTION = (480, 270)
SUPERSAMPLE = 2

#: How far apart two pictures of one render may be and still be that render.
#: Both are JPEGs the same encoder wrote from the same buffer, so the honest
#: expectation is **zero** and the test asserts that too; this is the codec noise
#: the tolerance is stated in, and it is here so an encoder setting that rounds
#: one channel differently reports a near miss rather than a failure that reads
#: like a broken replay.
CODEC_NOISE = 2


def _geometry() -> dict:
    return {
        "resolution": list(RESOLUTION),
        "supersample": SUPERSAMPLE,
        "maxiter": PROBE["maxiter"],
    }


def _row() -> dict:
    return {key: PROBE[key] for key in ("family", "viewport", "maxiter")}


def _made(where):
    """The probe rendered through the real candidate path. `(picture, stamp)`."""
    picture, stamp = colorize.render(
        _row(),
        PROBE["mode"],
        PROBE["colormap"],
        colorize.cyclic(),
        where,
        render_geometry=_geometry(),
        level=True,
        band=band_module.load(),
        fields=None,
    )
    assert stamp is not None and stamp["acted"], (
        "this probe was chosen because the operator fires on it; if it has stopped "
        "firing the probe is stale, and that is not the replay's failure"
    )
    return picture, stamp


def _stops():
    entry = json.loads((colormap_dir() / f"{PROBE['colormap']}.json").read_text(encoding="utf-8"))
    return entry


def _pixels(path):
    numpy = pytest.importorskip("numpy")
    image = pytest.importorskip("PIL.Image")

    with image.open(path) as handle:
        return numpy.asarray(handle.convert("RGB"), dtype=numpy.int16)


@needs_engine
@pytest.mark.slow
def test_a_depth_row_that_acted_replays_to_the_picture_the_run_made(tmp_path) -> None:
    numpy = pytest.importorskip("numpy")
    from fractal_wallpapers.models import renders

    picture, stamp = _made(tmp_path / "made.jpg")

    # Through JSON and back, which is the record rather than a paraphrase of it:
    # a stamp that survives in memory and loses a number to `json.dumps` would
    # replay here and not on disk. Spelled the way `depth.run` writes the row.
    written = tmp_path / "sequence.jsonl"
    written.write_text(
        json.dumps(
            {"schema": depth.SCHEMA, "at": 0, "key": "probe", "acted": True, "autolevel": stamp},
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    stored = json.loads(written.read_text(encoding="utf-8").splitlines()[0])
    assert depth.levelling_of(stored) == depth.REPLAYED

    # The replay: the stop list out of the row's own curve, and a render through
    # it with the operator never consulted. No image is opened and nothing is
    # measured — see the module docstring for why that is the whole distinction.
    entry = _stops()
    stops = autolevel.stops_from_stamp(stored["autolevel"], entry["stops"])
    where = tmp_path / "replayed.colormap"
    autolevel.overriding_colormap(PROBE["colormap"], stops, entry.get("kind"), where)
    again = tmp_path / "again.jpg"
    spec = renders.spec_of(
        colorize.render_row(
            _row(), PROBE["mode"], PROBE["colormap"], colorize.cyclic(), _geometry()
        ),
        again,
    )
    engine.run("render", {**spec, "colormap_dir": str(where)})

    apart = int(numpy.abs(_pixels(picture) - _pixels(again)).max())
    assert apart <= CODEC_NOISE, f"the replay is {apart} of 255 from the picture the run made"
    # And the expectation the tolerance is not meant to be spent on: same engine,
    # same spec, same stops, so the two files are the same bytes.
    assert picture.read_bytes() == again.read_bytes()


@needs_engine
@pytest.mark.slow
def test_the_curve_the_row_carries_rebuilds_the_map_the_operator_rendered_through(
    tmp_path,
) -> None:
    """The intermediate, pinned apart from the picture.

    A replay can land on the right pixels through a ramp that is not the
    operator's — two stop lists differing below the encoder's precision make one
    JPEG — so the rebuilt list is held to the map the run wrote beside its own
    picture. That file is the operator's working, and this is the one test that
    reads it, for exactly that reason.
    """
    made = tmp_path / "made.jpg"
    _picture, stamp = _made(made)
    rebuilt = autolevel.stops_from_stamp(json.loads(json.dumps(stamp)), _stops()["stops"])
    rendered_through = json.loads(
        (made.parent / f"{made.stem}.leveled" / f"{PROBE['colormap']}.json").read_text(
            encoding="utf-8"
        )
    )
    assert rebuilt == rendered_through["stops"]
