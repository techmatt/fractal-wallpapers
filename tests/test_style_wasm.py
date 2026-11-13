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
