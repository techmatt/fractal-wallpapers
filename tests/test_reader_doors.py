"""The reader doors of 2026-10-04: the render's palette flags, `palettes list`, the
judges' tracked check cases, the grid page, and `harvest export`'s join.

None of these renders or loads a judge; `judges check` itself is exercised by the
fresh-install sample run, and by any install that runs it.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers import bundle as bundle_module
from fractal_wallpapers import cli, grid_page, palettes
from fractal_wallpapers.cli import common, judges_commands
from fractal_wallpapers.cli.draw_commands import render_spec


def parse(argv):
    return cli.build_parser().parse_args(argv)


def test_a_render_naming_no_knob_writes_no_palette_and_no_params():
    spec = render_spec(parse(["render", "--out", "x.png"]))
    assert "palette" not in spec and "params" not in spec


def test_the_render_knobs_land_in_the_spec_as_the_engine_spells_them():
    spec = render_spec(
        parse(
            [
                "render",
                "--mode",
                "stripe",
                "--param",
                "density=3",
                "--cycles",
                "2",
                "--phase",
                "0.25",
                "--transfer",
                "edge:0.5",
                "--rolloff",
                "soft_knee:0.2",
                "--lambda",
                "0.5",
                "--reverse",
                "--out",
                "x.png",
            ]
        )
    )
    assert spec["params"] == {"density": 3.0}
    assert spec["palette"] == {
        "cycles": 2.0,
        "phase": 0.25,
        "lambda": 0.5,
        "reverse": True,
        "transfer": {"kind": "edge", "weight": 0.5},
        "rolloff": {"kind": "soft_knee", "knee": 0.2},
    }


@pytest.mark.parametrize(
    "argv",
    [["--transfer", "bogus"], ["--rolloff", "aces:1"], ["--param", "density"]],
)
def test_a_malformed_knob_is_a_refusal_and_not_a_traceback(argv):
    with pytest.raises(ValueError):
        common.palette_of(parse(["render", *argv]))


def test_every_drawable_name_is_a_colormap_file_and_an_unknown_one_is_refused():
    held = palettes.drawable()
    assert "twilight_shifted" in held
    assert set(held.values()) <= {"cyclic", "sequential"}
    assert palettes.refuse_unknown("twilight_shifted") is None
    assert "palettes list" in palettes.refuse_unknown("no such map")


def test_the_check_cases_are_text_recipes_that_still_compute_to_their_keys():
    """A case whose recipe no longer computes to its key would render a different
    picture under the same name, and the check would then compare scores of two
    different pictures."""
    from fractal_wallpapers.curation import recipes

    cases = [
        json.loads(line)
        for line in judges_commands.check_path().read_text(encoding="utf-8").splitlines()
    ]
    assert len(cases) >= 6
    assert len({case["recipe"]["family"]["kind"] for case in cases}) >= 3
    for case in cases:
        assert recipes.key_of(recipes.of_record(case["recipe"])) == case["key"]
        assert set(case["expected"]) == {"render", "gallery_grade", "palette", "location"}


def test_the_grid_page_links_its_pictures_relatively(tmp_path):
    picture = tmp_path / "pictures" / "a.jpg"
    picture.parent.mkdir()
    picture.write_bytes(b"\xff\xd8")
    page = grid_page.write(
        tmp_path / "page" / "index.html",
        "t",
        ["intro"],
        [grid_page.Section("s", tiles=[grid_page.Tile(picture, [("P(>=4)", 0.5)])])],
    )
    text = page.read_text(encoding="utf-8")
    assert 'src="../pictures/a.jpg"' in text and "<script" not in text


def test_a_page_has_a_twin_and_a_bundle_that_refers_to_nothing_outside_it(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image

    picture = tmp_path / "source" / "a.png"
    picture.parent.mkdir()
    Image.new("RGB", (1280, 720), (40, 80, 120)).save(picture)
    sections = [
        grid_page.Section(
            "s",
            tiles=[grid_page.Tile(picture, [("P(>=4)", 0.5)])],
            records=[grid_page.Record("rows.jsonl", {"key": "k1", "x": 1}, "key", "k1")],
        )
    ]
    bundle = tmp_path / "bundle"
    page = grid_page.write(
        tmp_path / "page" / "index.html", "t", ["intro"], sections, command="cmd", bundle=bundle
    )
    twin = json.loads((page.parent / "page.json").read_text(encoding="utf-8"))
    assert twin["command"] == "cmd" and twin["sections"][0]["tiles"][0]["caption"] == [
        ["P(>=4)", 0.5]
    ]
    assert "cmd" in page.read_text(encoding="utf-8")
    text = (bundle / "index.html").read_text(encoding="utf-8")
    assert 'src="pictures/a.jpg"' in text and str(tmp_path) not in text
    assert "<mark>&quot;key&quot;: &quot;k1&quot;</mark>" in text
    with Image.open(bundle / "pictures" / "a.jpg") as small:
        assert small.size == (bundle_module.WIDTH, round(720 * bundle_module.WIDTH / 1280))
    assert sorted(p.name for p in bundle.rglob("*") if p.is_file()) == [
        "a.jpg",
        "index.html",
        "page.json",
    ]


def test_harvest_export_joins_admitted_places_to_the_judges_scores(tmp_path, monkeypatch):
    from fractal_wallpapers.curation import intake
    from fractal_wallpapers.supply import places
    from fractal_wallpapers.supply.location import key_of_row, key_text

    family = {"kind": "mandelbrot"}
    near = {"center_re": "-0.75", "center_im": "0.1", "width": "0.01"}
    far = {"center_re": "-0.5", "center_im": "0.5", "width": "0.02"}
    rows = [
        {"schema": 1, "kind": "root", "root_id": 0, "provenance": {"channel": "seed_file"}},
        {"schema": 1, "kind": "candidate", "root_id": 0, "fate": "survived", "family": family,
         "viewport": near, "maxiter": 500, "image": "node0_c0.jpg", "channel": "share"},
        {"schema": 1, "kind": "candidate", "root_id": 0, "fate": "survived", "family": family,
         "viewport": far, "maxiter": 500, "image": None, "channel": "contest"},
        {"schema": 1, "kind": "candidate", "root_id": 0, "fate": "flat", "family": family,
         "viewport": far, "maxiter": 500, "image": None},
    ]  # fmt: skip
    (tmp_path / "walk.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    scored = key_text(key_of_row({"family": family, "viewport": near}))
    sidecar = tmp_path / "supply_scores.jsonl"
    sidecar.write_text("")
    monkeypatch.setattr(intake, "scores_path", lambda: sidecar)
    monkeypatch.setattr(
        intake, "read_scores", lambda *a, **k: {scored: {"p_ge3": 0.7, "p_ge4": 0.2}}
    )
    path, held = places.export(tmp_path)
    assert path.name == "locations.jsonl"
    assert [row["p_ge3"] for row in held] == [0.7, None]
    assert [row["slot_channel"] for row in held] == ["share", "contest"]
    assert held[0]["root_channel"] == "seed_file"
    record, page = places.stats(tmp_path)
    assert record["families"]["mandelbrot"] == {
        **record["families"]["mandelbrot"],
        "found": 3,
        "admitted": 2,
        "scored": 1,
    }
    assert page.is_file()
