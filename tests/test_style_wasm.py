"""The style module's bundle, and the module held to the native engine on a small frame."""

from __future__ import annotations

import json
import shutil
import sys

import pytest

from fractal_wallpapers import engine, style_catalog, style_keeps, style_wasm, styles


def test_the_bundle_carries_every_published_mode_whole():
    document = style_wasm.bundle()
    published = style_wasm.published_rows()
    assert document["schema"] == style_wasm.BUNDLE_SCHEMA
    assert [mode["style"] for mode in document["modes"]] == [row["style"] for row in published]
    for mode, row in zip(document["modes"], published, strict=True):
        source = styles.load(row["style"])
        assert mode["name"] == row["public"]["name"]
        assert mode["tier"] == row["tier"] and mode["tier"] in style_catalog.TIERS
        assert mode["stack"] == source["style"]
        assert mode["knobs"] == ((source.get("public") or {}).get("knobs") or [])
        assert mode["palette"] in document["colormaps"]
        # The set a page cycles opens at the mode's own map, kept in or not.
        assert mode["palettes"][0]["colormap"] == mode["palette"], row["style"]
        assert mode["palettes"][0]["values"] == {}, row["style"]
        # Each entry names what a knob rests at there, inside the knob's range: the slider
        # can come back to the entry's own picture (Matt's ruling, 2026-11-25).
        ranges = {knob["name"]: knob["range"] for knob in mode["knobs"]}
        for entry in mode["palettes"]:
            for name, rest in entry.get("rests", {}).items():
                low, high = ranges[name]
                assert low <= rest <= high, (row["style"], entry["colormap"], name)
        # A merged style's old name resolves on the page as `styles.alias_of` resolves it.
        assert mode["aliases"] == row.get("aliases", [])
        for alias in mode["aliases"]:
            entry = styles.alias_of(alias)[1]
            assert entry is None or [
                e["colormap"] for e in mode["palettes"] if e.get("was") == alias
            ] == [entry]
        assert mode["shown"], f"{row['style']} opens nowhere"
        assert [s.get("keep") for s in mode["shown"]] == [s.get("keep") for s in row["show"]]
        keeps = style_catalog.keeps_of(row["style"])
        stacks = style_keeps.read_record(row["style"])["stacks"]
        for shown, item in zip(mode["shown"], row["show"], strict=True):
            assert shown["colormap"] in document["colormaps"]
            if "keep" not in item:  # a lab example: its draft's place, the mode's stack
                assert shown["location"] == item["location"]
                assert shown["stack"] == source["style"]
                continue
            render = keeps[shown["keep"]]["render"]
            assert shown["location"] == render["location"]
            assert shown["stack"] == stacks[render["stack"]]
    tiers = {mode["tier"] for mode in document["modes"]}
    assert tiers == set(style_catalog.TIERS), "the bundle carries both tiers, told apart"
    for name, colormap in document["colormaps"].items():
        assert colormap == style_wasm.colormap_of(name)


def test_the_recolour_check_switches_every_second_entry_of_a_tiled_mode():
    """`wasm-parity --recolour`'s jobs, without Node: per published mode drawn in tiles,
    each kept entry after the default as a plain frame and as the page's switch to it."""
    document = style_wasm.bundle()
    modes = document["modes"]
    jobs = style_wasm.recolour_jobs(document=document)
    frames = {job["id"] for job in jobs if job["draw"] == "frame"}
    switches = [job for job in jobs if "same_as" in job]
    assert {job["same_as"] for job in switches} == frames
    expected = sum(
        len(mode["palettes"]) - 1
        for mode in modes
        if not style_wasm.has_post(mode["stack"]) and len(mode["palettes"]) > 1
    )
    assert expected and len(switches) == expected
    for job in switches:
        assert job["draw"]["from"]["location"] == job["request"]["location"]
        assert job["draw"]["from"]["colormap"] != job["request"]["colormap"] or (
            job["draw"]["from"]["style"] != job["request"]["style"]
        ), f"{job['id']} switches to the picture it started from"
    with pytest.raises(style_wasm.StyleWasmError):
        style_wasm.recolour_jobs(["no_such_style"], document=document)


def test_a_named_parity_run_lists_only_that_style_s_jobs():
    """The job list needs neither Node nor the module: each job is its style's, every
    picture a job is compared with is drawn natively, and a tiled job names its frame."""
    style = style_wasm.published_rows()[0]["style"]
    jobs, natives = style_wasm.parity_jobs(names=[style])
    assert jobs and all(job["id"].startswith(f"{style}__") for job in jobs)
    frames = {job["id"] for job in jobs if "same_as" not in job}
    assert frames == set(natives)
    assert all(job["same_as"] in frames for job in jobs if "same_as" in job)
    with pytest.raises(style_wasm.StyleWasmError):
        style_wasm.parity_jobs(names=["no_such_style"])


def test_a_member_names_the_published_modes_whose_knobs_write_it():
    """`wasm-parity --member` draws exactly the modes a knob of which writes that member."""
    from fractal_wallpapers import styles

    for row in style_wasm.published_rows():
        knobs = (styles.load(row["style"]).get("public") or {}).get("knobs") or []
        pointers = [pointer for knob in knobs for pointer, _ in styles.knob_writes(knob, 0.0)]
        if pointers:
            member = pointers[0].rsplit("/", 1)[-1]
            assert row["style"] in style_wasm.knob_writers([member])
            break
    assert style_wasm.knob_writers(["no_such_member"]) == []


def test_the_module_s_integer_members_are_the_ones_the_style_files_write_as_integers():
    """`styles.with_knobs` rounds where a file writes an integer; the module, whose stack
    has lost that spelling to `JSON.parse`, rounds by name. The two must name the same."""
    import re

    source = (style_wasm.crate_dir() / "src" / "lib.rs").read_text(encoding="utf-8")
    listed = re.search(r"INTEGER_MEMBERS: \[&str; \d+\] = \[([^\]]*)\]", source)
    named = set(re.findall(r'"(\w+)"', listed.group(1)))
    whole, fractional = set(), set()

    def walk(node, key=None):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, k)
        elif isinstance(node, list):
            for v in node:
                walk(v, key)
        elif isinstance(node, bool) or key is None:
            return
        elif isinstance(node, int):
            whole.add(key)
        elif isinstance(node, float):
            fractional.add(key)

    for name in styles.names():
        walk(styles.load(name)["style"])
    assert whole <= named, whole - named
    assert not named & fractional, named & fractional
    # Both sides round by the same names, never by how a file spelled the number.
    assert set(styles.INTEGER_MEMBERS) == named


def test_a_cost_read_draws_each_style_at_its_deepest_kept_seat(tmp_path):
    published = [row["style"] for row in style_wasm.published_rows()]
    jobs = style_wasm.cost_jobs(published)
    assert [job["style"] for job in jobs] == published
    for job in jobs:
        seats = style_wasm.kept_seats(job["style"])
        depths = [seat["maxiter"] for seat in seats]
        assert depths == sorted(depths, reverse=True)
        asked = job["request"]
        assert asked["location"] == seats[0]
        assert asked["style"] == styles.load(job["style"])["style"]
        assert (asked["resolution"], asked["supersample"]) == (
            list(style_wasm.SPEED_RESOLUTION),
            style_wasm.SPEED_SUPERSAMPLE,
        )
    name = published[0]
    shallowest = style_wasm.kept_seats(name)[-1]
    (job,) = style_wasm.cost_jobs([name], seat=shallowest.get("name"))
    assert job["request"]["location"] == shallowest
    with pytest.raises(style_wasm.StyleWasmError, match="no kept seat named"):
        style_wasm.cost_jobs([name], seat="no such seat")
    with pytest.raises(style_wasm.StyleWasmError, match="render pool"):
        style_wasm.cost(tmp_path, [name], workers=style_wasm.COST_WORKERS + 1)
    # Any location record reads in place of the kept seats (a round-one style has none),
    # and every style named is read there, not only the first; `shrink` divides each side.
    (one, two) = style_wasm.cost_jobs(published[:2], location=shallowest, shrink=4)
    for job in (one, two):
        assert job["request"]["location"] == shallowest
        assert job["request"]["resolution"] == [s // 4 for s in style_wasm.SPEED_RESOLUTION]
    (first, second) = style_wasm.cost_jobs(published[:2])
    assert second["request"]["location"] == style_wasm.kept_seats(published[1])[0]
    with pytest.raises(style_wasm.StyleWasmError, match="must divide"):
        style_wasm.cost_jobs([name], shrink=3)
    # A parity run and a recolour check are held to the same pool (Matt, 2026-11-25).
    assert style_wasm.PARITY_WORKERS == engine.POOL_WORKERS
    with pytest.raises(style_wasm.StyleWasmError, match="render pool"):
        style_wasm.parity(tmp_path, names=[name], workers=style_wasm.PARITY_WORKERS + 1)
    with pytest.raises(style_wasm.StyleWasmError, match="render pool"):
        style_wasm.recolour_check(tmp_path, [name], workers=0)
    # A merged style's old name opens as its mode at the entry that was it, so it is read
    # at the mode's seats in that entry's stack and map.
    row = next(r for r in style_wasm.published_rows() if r.get("aliases"))
    alias = row["aliases"][0]
    (job,) = style_wasm.cost_jobs([alias])
    assert job["request"]["location"] == style_wasm.kept_seats(row["style"])[0]
    assert job["request"]["style"] == styles.load(alias)["style"]


def test_a_parity_run_of_a_name_with_nothing_to_draw_is_refused(tmp_path):
    """A filtered run that drew nothing would read as a clean one."""
    with pytest.raises(style_wasm.StyleWasmError, match="nothing to draw for no_such_style"):
        style_wasm.parity(tmp_path, names=["no_such_style"])


def test_a_parity_run_draws_the_longest_of_the_last_run_first(tmp_path):
    """One keep can be a quarter of an hour: started last it is the run's whole tail."""
    jobs = [{"id": name} for name in ("quick", "new", "slow", "middling")]
    assert style_wasm.longest_first(jobs, tmp_path) == jobs
    last = [
        {"id": "quick", "wasm_seconds": 2.0},
        {"id": "slow", "wasm_seconds": 900.0},
        {"id": "middling", "wasm_seconds": 40.0},
        {"id": "failed"},
    ]
    style_wasm.write_seconds(tmp_path, last)
    # A filtered run in between lays its own times over the folder's and keeps the rest.
    style_wasm.write_seconds(tmp_path, [{"id": "quick", "wasm_seconds": 3.0}])
    assert style_wasm.read_seconds(tmp_path) == {"quick": 3.0, "slow": 900.0, "middling": 40.0}
    order = [job["id"] for job in style_wasm.longest_first(jobs, tmp_path)]
    assert order == ["new", "slow", "middling", "quick"]


def test_the_bundle_command_writes_it(tmp_path):
    from fractal_wallpapers import cli

    out = tmp_path / "bundle.json"
    assert cli.main(["style", "bundle", "--out", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8")) == style_wasm.bundle()


@pytest.mark.slow
@pytest.mark.skipif(
    not (style_wasm.wasm_path().is_file() and shutil.which("node")),
    reason="needs the built module (style_wasm.BUILD) and node",
)
def test_a_job_past_its_limit_is_abandoned_and_the_rest_still_draw(tmp_path):
    """080's two runaway frames held a cost read 20 minutes; with a limit the runner
    abandons a frame past it, writes it `over`, and a fresh worker draws the next job."""
    row = style_wasm.published_rows()[0]
    document = styles.load(row["style"])
    location = style_catalog.keeps_of(row["style"])[row["show"][0]["keep"]]["render"]["location"]
    colormap = style_wasm.colormap_of(row["public"]["palette"])

    def asked(size, supersample):
        return style_wasm.request(location, document["style"], colormap, size, supersample, [], {})

    jobs = [
        {"id": "huge", "request": asked((3840, 2400), 4), "draw": "frame"},
        {"id": "small", "request": asked((32, 20), 1), "draw": "frame"},
    ]
    huge, small = style_wasm.run_node(jobs, tmp_path, workers=1, limit=1)
    assert huge["ok"] is False and huge["over"] is True, huge
    assert small["ok"], small


@pytest.mark.slow
@pytest.mark.skipif(
    not (engine.is_built() and style_wasm.wasm_path().is_file() and shutil.which("node")),
    reason="needs the release engine, the built module (style_wasm.BUILD) and node",
)
def test_the_module_draws_the_native_picture_with_its_knobs_turned(tmp_path):
    """One published mode at a small frame, its knobs at their middles, both ways."""
    row = style_wasm.published_rows()[0]
    document = styles.load(row["style"])
    shown = row["show"][0]["keep"]
    location = style_catalog.keeps_of(row["style"])[shown]["render"]["location"]
    knobs = document["public"]["knobs"]
    settings = style_wasm.midpoints(knobs)
    palette = row["public"]["palette"]
    size = (96, 60)
    asked = style_wasm.request(
        location, document["style"], style_wasm.colormap_of(palette), size, 2, knobs, settings
    )
    jobs = [
        {"id": "frame", "request": asked, "draw": "frame"},
        {"id": "tiles", "request": asked, "draw": {"measure": {}, "tile": [40, 25]}},
    ]
    results = style_wasm.run_node(jobs, tmp_path)
    assert all(result["ok"] for result in results), results
    native, _ = style_wasm.native_rgb(
        location, document, palette, size, 2, tmp_path / "n.png", knobs=settings
    )
    for job in ("frame", "tiles"):
        rgba = (tmp_path / f"{job}.rgba").read_bytes()
        found = style_wasm.compare(native, rgba)
        if sys.platform == "win32":
            # Measured: every shown keep byte-identical (`style wasm-parity`).
            assert found["identical"], (job, found)
        else:
            # The native engine's `ln`, `exp`, `powf` here are the platform's libm and
            # the module's are Rust's own; they may part by a unit in the last place on
            # a few samples, which reaches a byte only on a rounding edge. Unmeasured
            # off Windows, so the bar is a step on a few pixels, never a drift.
            assert found["pixels"] is not None, (job, found)
            assert found["worst"] <= 2 and found["pixels"] * 200 <= len(native) // 3, found


#: A post stage on a plain stack: the mosaic on each lattice, every shading member set,
#: and the paper pass with its brush, accent and shadow. Each pass names its `kind`.
POST_STACKS = {
    "paper": {
        "kind": "paper",
        "levels": 7,
        "taper": 0.9,
        "hop": 0.3,
        "ragged": {
            "reach": 0.03,
            "length": 0.15,
            "width": 0.004,
            "azimuth": 50.0,
            "accent": {"color": {"palette": 1.0}, "share": 0.2},
        },
        "shadow": {"width": 0.02, "offset": 0.006, "azimuth": 120.0, "opacity": 0.5},
    },
    "triangles": {
        "kind": "mosaic",
        "largest": 0.25,
        "smallest": 0.01,
        "levels": 6,
        "fold": 0.3,
        "relief": 6.0,
        "inlay": {"levels": 2, "amount": 0.08},
        "faces": [1.0, 0.7, 0.42],
        "opacity": 0.7,
    },
    "rhombi": {
        "kind": "mosaic",
        "rhombi": True,
        "tilt": -20.0,
        "fill": "turned",
        "turn": 6.0,
        "shift": 0.25,
        "largest": 0.3,
        "smallest": 0.04,
        "levels": 1,
    },
    "spiral": {
        "kind": "mosaic",
        "spiral": {"arms": 9, "twist": 0.5},
        "smallest": 0.02,
        "fill": "turned",
        "turn": 40.0,
        "height": {"field": {"kind": "smooth"}},
        "relief": 20.0,
        "seam": {"width": 0.002, "color": {"palette": 0.0}, "opacity": 0.8},
    },
}


@pytest.mark.slow
@pytest.mark.skipif(
    not (engine.is_built() and style_wasm.wasm_path().is_file() and shutil.which("node")),
    reason="needs the release engine, the built module (style_wasm.BUILD) and node",
)
@pytest.mark.parametrize("name", sorted(POST_STACKS))
def test_the_module_draws_a_post_stage_as_the_native_engine_does(tmp_path, name):
    """A post pass reads the whole frame, so it is drawn whole on both sides (`frame`),
    and the module refuses it in tiles."""
    stack = {
        "name": "posted",
        "tone": {"median": 0.4, "p10": 0.15},
        "layers": [
            {
                "kind": "palette",
                "channel": {"field": {"kind": "smooth"}},
                "palette": {"transfer": {"kind": "rank"}},
            }
        ],
        "post": [POST_STACKS[name]],
    }
    assert style_wasm.has_post(stack)
    palette = style_wasm.published_rows()[0]["public"]["palette"]
    document = {"name": "posted", "suggested_colormap": palette, "style": stack}
    size = (160, 100)
    asked = style_wasm.request(
        style_wasm.POST_SEAT, stack, style_wasm.colormap_of(palette), size, 2
    )
    jobs = [
        {"id": "frame", "request": asked, "draw": "frame"},
        {"id": "tiles", "request": asked, "draw": {"measure": {}, "tile": [80, 50]}},
    ]
    frame, tiles = style_wasm.run_node(jobs, tmp_path)
    assert frame["ok"], frame
    assert not tiles["ok"] and "post stage" in tiles["why"], tiles
    native, _ = style_wasm.native_rgb(
        style_wasm.POST_SEAT, document, palette, size, 2, tmp_path / "n.png"
    )
    found = style_wasm.compare(native, (tmp_path / "frame.rgba").read_bytes())
    if sys.platform == "win32":
        assert found["identical"], found
    else:
        # As above, and a unit in the last place can also move one facet's edge or
        # split: a few pixels by any step, never the frame.
        assert found["pixels"] is not None and found["pixels"] * 50 <= len(native) // 3, found


@pytest.mark.slow
@pytest.mark.skipif(
    not (style_wasm.wasm_path().is_file() and shutil.which("node")),
    reason="needs the built module (style_wasm.BUILD) and node",
)
def test_the_shared_measure_and_the_recolour_draw_the_plain_picture(tmp_path):
    """A worker taking another's measure report, and a picture recoloured to another
    palette entry from its kept frame, each tile to the bytes of a plain draw."""
    from fractal_wallpapers import style_palettes

    row = next(r for r in style_wasm.published_rows() if r["style"] == "lace_holes")
    document = styles.load(row["style"])
    kept = [entry for entry in row["palettes"] if entry.get("keeps")]
    default, other = kept[0], next(entry for entry in kept[1:] if entry.get("values"))
    location = style_catalog.keeps_of(row["style"])[row["show"][0]["keep"]]["render"]["location"]

    def asked(entry):
        stack = style_palettes.apply(document["style"], entry.get("values") or {})
        colormap = style_wasm.colormap_of(entry["colormap"])
        return style_wasm.request(location, stack, colormap, (96, 60), 2)

    tiled = {"measure": {}, "tile": [40, 25]}
    jobs = [
        {"id": "plain", "request": asked(other), "draw": "frame"},
        {"id": "shared", "request": asked(other), "draw": {**tiled, "shared": True}},
        {"id": "recoloured", "request": asked(other), "draw": {**tiled, "from": asked(default)}},
        {"id": "before", "request": asked(default), "draw": "frame"},
    ]
    results = style_wasm.run_node(jobs, tmp_path)
    assert all(result["ok"] for result in results), results
    plain = (tmp_path / "plain.rgba").read_bytes()
    assert plain != (tmp_path / "before.rgba").read_bytes(), "the entry is another picture"
    for job in ("shared", "recoloured"):
        assert (tmp_path / f"{job}.rgba").read_bytes() == plain, job
