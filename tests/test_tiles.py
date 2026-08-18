"""The training tiles: the population, the ids, and the picture at slot zero.

The last two tests build real tiles through the real engine, because everything
above them can be true of a build that never rendered anything. They are sized to
a couple of seconds.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers import engine
from fractal_wallpapers.labeling import pins
from fractal_wallpapers.models import tiles as tile_module
from fractal_wallpapers.paths import colormap_dir
from fractal_wallpapers.supply.location import location_key

MANDELBROT = {"kind": "mandelbrot"}
JULIA = {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]}
VIEW = {"center_re": "-0.5", "center_im": "0", "width": "3.0"}


def engine_is_built() -> bool:
    try:
        engine.engine_path()
    except FileNotFoundError:
        return False
    return True


needs_engine = pytest.mark.skipif(
    not engine_is_built(),
    reason="the engine is not built: cargo build --release --manifest-path engine/Cargo.toml",
)


def test_a_locations_id_is_a_function_of_the_location() -> None:
    """The id seeds every draw in the fan-out, so it must not move when the
    corpus does. A row number would renumber the whole build on one new label."""
    first = tile_module.location_id(location_key(JULIA, VIEW))
    again = tile_module.location_id(location_key(dict(JULIA), dict(VIEW)))
    assert first == again
    restated = {"kind": "julia", "degree": 2, "c": ["-0.40", "0.600"]}
    assert tile_module.location_id(location_key(restated, VIEW)) == first
    assert tile_module.location_id(location_key(MANDELBROT, VIEW)) != first


def test_an_id_survives_a_json_round_trip_exactly() -> None:
    """It crosses the engine boundary as a JSON number, twice. A value a parser
    rounds is an id that silently collides."""
    identifier = tile_module.location_id(location_key(JULIA, VIEW))
    assert identifier < 2**53
    assert json.loads(json.dumps({"id": identifier}))["id"] == identifier


def test_the_ids_of_the_shipped_corpus_do_not_collide(shipped_scored, shipped_tile_plan) -> None:
    assert len(shipped_tile_plan) == len(shipped_scored)
    assert len({row["location_id"] for row in shipped_tile_plan}) == len(shipped_tile_plan)


def test_the_plan_holds_the_evaluation_side_too(shipped_tile_plan) -> None:
    """A held-out location has to be scored through the same pictures the
    training side was learned from, or the number measures the render as well."""
    sides = {row["side"] for row in shipped_tile_plan}
    assert sides == {pins.TRAIN, pins.EVAL}
    assert sum(1 for row in shipped_tile_plan if row["side"] == pins.EVAL) == len(pins.pinned())


def test_the_plan_is_shuffled_so_a_prefix_is_a_fair_sample(shipped_tile_plan) -> None:
    """Sorted by coordinate the deep, expensive material lands contiguously and
    any bounded rehearsal measures the cheap end of the corpus."""
    prefix = [row["partition"] for row in shipped_tile_plan[:400]]
    assert len(set(prefix)) >= 6, "a prefix that holds one partition is not a fair sample"


def test_the_seed_is_what_the_shuffle_comes_out_of(shipped_scored) -> None:
    """Asked on a slice rather than the whole store: laying a plan out assigns
    every row to a neighbourhood group, which is quadratic-ish in the rows, and
    the property here is about the shuffle rather than about the corpus."""
    slice_of_it = shipped_scored[:400]
    first = [row["location_id"] for row in tile_module.plan(slice_of_it, seed=0)]
    again = [row["location_id"] for row in tile_module.plan(slice_of_it, seed=0)]
    other = [row["location_id"] for row in tile_module.plan(slice_of_it, seed=1)]
    assert first == again, "the same seed is the same order"
    assert first != other
    assert sorted(first) == sorted(other), "a reseed reorders and does not requalify"


def test_the_palette_pool_is_the_draw_the_floor_and_the_holdout() -> None:
    pool = tile_module.palette_pool()
    draw = set(pool["draw"])
    held = set(pool["invariance_holdout"])
    assert draw and held
    assert not (draw & held), "a held-out map that is also drawn is not held out"
    for name, count in pool["floor"]:
        assert count >= 1
        assert (colormap_dir() / f"{name}.json").is_file()
    for name in draw | held:
        assert (colormap_dir() / f"{name}.json").is_file(), name


def test_the_canonical_tile_is_refused_when_it_is_not_canonical() -> None:
    """A location whose deploy view is a draw has no deploy view, and an aliased
    or reframed stand-in is a quieter version of the same wrong answer."""
    good = [{"location_id": 1, "tile": 0, "level": "antialiased", "scale": 1.0, "shift_frac": 0.0}]
    assert tile_module.canonical_of(good) is good[0]
    for broken in ({"level": "aliased"}, {"scale": 1.05}, {"shift_frac": 0.01}):
        with pytest.raises(ValueError, match="canonical"):
            tile_module.canonical_of([{**good[0], **broken}])
    with pytest.raises(ValueError, match="no canonical tile"):
        tile_module.canonical_of([{**good[0], "tile": 3}])


@needs_engine
def test_a_build_writes_every_tile_of_every_location(tmp_path) -> None:
    plan = tmp_path / "plan.jsonl"
    plan.write_text(
        "\n".join(
            json.dumps({"schema": 1, "location_id": identifier, "family": family, "viewport": VIEW})
            for identifier, family in ((7, MANDELBROT), (11, JULIA))
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    pool = tile_module.palette_pool()
    report = engine.tiles(
        {
            "schema": 1,
            "locations": str(plan),
            "out_root": str(tmp_path / "cache"),
            "manifest": str(tmp_path / "manifest.jsonl"),
            "colormap_dir": str(colormap_dir()),
            "seed_tag": "a-test",
            "recipe": {
                "tiles": 4,
                "tile": [128, 72],
                "palette_pool": pool["draw"],
                "floor_palette": [[name, count] for name, count in pool["floor"]],
            },
        }
    )
    assert report["tiles_written"] == 8
    assert report["containment"]["required"] <= report["containment"]["declared"] + 1e-9
    rows = tile_module.read_manifest(tmp_path / "manifest.jsonl", keep=None)
    assert len(rows) == 8
    grouped = tile_module.tiles_by_location(rows)
    assert set(grouped) == {7, 11}
    for tiles in grouped.values():
        canonical = tile_module.canonical_of(tiles)
        assert canonical["palette"] == "twilight_shifted"
        assert canonical["quality"] == 90
        # Forward slashes, whichever platform wrote the row: the trainer reads
        # this record on the other operating system as often as on this one.
        assert "\\" not in canonical["path"]

    # A second run rebuilds the manifest and re-renders nothing.
    again = engine.tiles(
        {
            "schema": 1,
            "locations": str(plan),
            "out_root": str(tmp_path / "cache"),
            "manifest": str(tmp_path / "manifest.jsonl"),
            "colormap_dir": str(colormap_dir()),
            "seed_tag": "a-test",
            "recipe": {
                "tiles": 4,
                "tile": [128, 72],
                "palette_pool": pool["draw"],
                "floor_palette": [[name, count] for name, count in pool["floor"]],
            },
        }
    )
    assert again["tiles_written"] == 0
    assert again["locations_skipped"] == 2


@needs_engine
def test_the_canonical_tile_is_the_render_a_deployed_judge_would_make(tmp_path) -> None:
    """The one property the whole evaluation rests on: a location scored out of
    the tile cache and the same location rendered fresh are the same picture.

    Compared against the lossless render, because both sides are JPEGs and the
    encoder's own error is larger than the geometry's. The tile may not disagree
    with the truth by more than a plain JPEG of it does.
    """
    numpy = pytest.importorskip("numpy")
    image_module = pytest.importorskip("PIL.Image")

    plan = tmp_path / "plan.jsonl"
    plan.write_text(
        json.dumps({"schema": 1, "location_id": 0, "family": MANDELBROT, "viewport": VIEW}) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    engine.tiles(
        {
            "schema": 1,
            "locations": str(plan),
            "out_root": str(tmp_path / "cache"),
            "manifest": str(tmp_path / "manifest.jsonl"),
            "colormap_dir": str(colormap_dir()),
            "seed_tag": "a-test",
            "recipe": {"tiles": 1, "palette_pool": ["twilight_shifted"]},
        }
    )
    tile = tile_module.canonical_of(
        tile_module.read_manifest(tmp_path / "manifest.jsonl", keep=None)
    )
    common = {
        "schema": 1,
        "family": MANDELBROT,
        "viewport": VIEW,
        "resolution": [tile["tile_size"][0], tile["tile_size"][1]],
        "supersample": tile["field"]["supersample"],
        "mode": "smooth",
        "colormap": "twilight_shifted",
        "colormap_dir": str(colormap_dir()),
        "maxiter": tile["maxiter"],
    }
    truth = engine.render({**common, "output": str(tmp_path / "plain.png")})
    lossy = engine.render({**common, "output": str(tmp_path / "plain.jpg")})

    def read(path):
        with image_module.open(path) as opened:
            return numpy.asarray(opened.convert("RGB"), dtype=int)

    exact = read(truth)
    tile_error = numpy.abs(read(tile["path"]) - exact).mean()
    encoder_error = numpy.abs(read(lossy) - exact).mean()
    assert tile_error <= encoder_error * 1.1, (
        f"the canonical tile is {tile_error:.4f} from the lossless render where a plain JPEG "
        f"of it is {encoder_error:.4f} — the difference is geometry, not the encoder"
    )
