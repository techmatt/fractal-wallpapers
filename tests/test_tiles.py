"""The training tiles: the population, the ids, the regime, and slot zero.

The last four tests build real tiles through the real engine, because everything
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

#: The tile name as it was written before the name carried a regime. A literal,
#: not a call into the code under test: the corpus on disk is named this way and
#: the point of the test below is that the canonical regime still writes it.
LEGACY_NAME = "t{index:02d}_{palette}_s{scale:.4f}_sh{shift:.4f}_{level}_q{quality}.jpg"

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


def write_one_location(tmp_path, family=MANDELBROT, identifier=7):
    plan = tmp_path / "plan.jsonl"
    plan.write_text(
        json.dumps({"schema": 1, "location_id": identifier, "family": family, "viewport": VIEW})
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return plan


def regime_spec(plan, tmp_path, regime, tiles=4):
    """A tiles spec at one regime, through the module's own spec shape."""
    pool = tile_module.palette_pool()
    return {
        "schema": 1,
        "locations": str(plan),
        "out_root": str(tmp_path / "cache"),
        "manifest": str(tmp_path / f"manifest{regime.tag}.jsonl"),
        "colormap_dir": str(colormap_dir()),
        "seed_tag": "a-test",
        "recipe": {
            "tiles": tiles,
            "tile": list(regime.tile),
            "field_supersample": regime.supersample,
            "palette_pool": pool["draw"],
            "floor_palette": [[name, count] for name, count in pool["floor"]],
        },
    }


def test_only_the_canonical_regime_elides() -> None:
    assert tile_module.CANONICAL_REGIME.tag == ""
    assert tile_module.Regime(tile=(640, 360), supersample=2).tag == ""
    assert tile_module.Regime(tile=(640, 360), supersample=1).tag == "_640x360ss1"
    assert tile_module.Regime(tile=(384, 216), supersample=1).tag == "_384x216ss1"
    assert tile_module.manifest_path() == tile_module.tile_dir() / "manifest.jsonl"
    ss1 = tile_module.Regime(tile=(384, 216), supersample=1)
    assert tile_module.manifest_path(ss1).name == "manifest_384x216ss1.jsonl"
    assert tile_module.build_record_path(ss1).name == "build_384x216ss1.json"


def test_the_spec_states_the_geometry_it_used_to_leave_to_the_engine() -> None:
    """A build that did not say which regime it wanted got the default silently,
    and the record it wrote could not be told apart from one that asked."""
    canonical = tile_module.spec()["recipe"]
    assert canonical["tile"] == [640, 360]
    assert canonical["field_supersample"] == 2
    small = tile_module.spec(regime=tile_module.Regime(tile=(384, 216), supersample=1))
    assert small["recipe"]["tile"] == [384, 216]
    assert small["recipe"]["field_supersample"] == 1
    assert small["manifest"].endswith("manifest_384x216ss1.jsonl")


@needs_engine
def test_the_canonical_regime_writes_the_names_the_corpus_already_has(tmp_path) -> None:
    """Every tile of the shipped cache is named without a regime segment. If the
    canonical regime stopped writing that name, 380,000 files would be orphaned
    and the next build would render the corpus again from nothing."""
    plan = write_one_location(tmp_path)
    engine.tiles(regime_spec(plan, tmp_path, tile_module.CANONICAL_REGIME))
    rows = tile_module.read_manifest(tmp_path / "manifest.jsonl", keep=None)
    assert len(rows) == 4
    for row in rows:
        legacy = LEGACY_NAME.format(
            index=row["tile"],
            palette=row["palette"],
            scale=row["scale"],
            shift=row["shift_frac"],
            level=row["level"],
            quality=row["quality"],
        )
        assert row["path"].endswith(f"/7/{legacy}"), row["path"]


@needs_engine
def test_a_second_regime_cannot_skip_over_the_first_ones_pictures(tmp_path) -> None:
    """The planted red: run this against a build whose names carry no regime and
    the ss1 leg reports 4 skipped and 0 written, exits 0, and records a geometry
    that is not what is on disk. That silent no-op is what the regime segment
    makes impossible."""
    plan = write_one_location(tmp_path)
    ss1 = tile_module.Regime(tile=(640, 360), supersample=1)
    engine.tiles(regime_spec(plan, tmp_path, tile_module.CANONICAL_REGIME))
    report = engine.tiles(regime_spec(plan, tmp_path, ss1))

    assert report["tiles_written"] == 4, "an ss1 build skipped over ss2 pictures"
    assert report["tiles_skipped"] == 0
    assert report["locations_skipped"] == 0
    assert report["recipe"]["field_supersample"] == 1

    ss2_paths = {r["path"] for r in tile_module.read_manifest(tmp_path / "manifest.jsonl")}
    ss1_paths = {
        r["path"] for r in tile_module.read_manifest(tmp_path / "manifest_640x360ss1.jsonl")
    }
    assert not (ss2_paths & ss1_paths), "two regimes wrote the same file"
    assert all("_640x360ss1.jpg" in path for path in ss1_paths)

    # And the second regime is itself resumable: its own names are present now.
    again = engine.tiles(regime_spec(plan, tmp_path, ss1))
    assert again["tiles_written"] == 0
    assert again["locations_skipped"] == 1


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
