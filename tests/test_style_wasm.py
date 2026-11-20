"""The style module's bundle, and the module held to the native engine on a small frame."""

from __future__ import annotations

import json
import shutil
import sys

import pytest

from fractal_wallpapers import engine, style_catalog, style_wasm, styles


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
        assert mode["shown"], f"{row['style']} opens nowhere"
        assert [s.get("keep") for s in mode["shown"]] == [s.get("keep") for s in row["show"]]
        keeps = style_catalog.keeps_of(row["style"])
        stacks = style_wasm.keep_stacks(row["style"])
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


#: A post stage on a plain stack: the mosaic on each lattice, every shading member set.
POST_STACKS = {
    "triangles": {
        "largest": 0.25,
        "smallest": 0.01,
        "levels": 6,
        "fold": 0.3,
        "relief": 6.0,
        "inlay": {"levels": 2, "amount": 0.08},
        "opacity": 0.7,
    },
    "rhombi": {
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
@pytest.mark.parametrize("lattice", sorted(POST_STACKS))
def test_the_module_draws_a_post_stage_as_the_native_engine_does(tmp_path, lattice):
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
        "post": [{"kind": "mosaic", **POST_STACKS[lattice]}],
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
