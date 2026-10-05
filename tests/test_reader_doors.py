"""The reader doors of 2026-10-04: the render's palette flags, `palettes list`, the
judges' tracked check cases, the grid page and its legends, `harvest export`'s join,
and what the walkthrough carries beside the pages.

None of these renders or loads a judge; `judges check` itself is exercised by the
fresh-install sample run, and by any install that runs it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from fractal_wallpapers import bundle as bundle_module
from fractal_wallpapers import cli, grid_page, palettes
from fractal_wallpapers.cli import common, judges_commands
from fractal_wallpapers.cli.draw_commands import render_spec

ROOT = Path(__file__).resolve().parent.parent


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


def test_harvest_export_joins_each_kept_place_once_to_the_judges_scores(tmp_path, monkeypatch):
    """Two survivors on one location key are one place: the sample run of 2026-10-04
    showed 4,069 'scored' rows against a sidecar of 4,022, the 47 being repeats."""
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
        {"schema": 1, "kind": "candidate", "root_id": 0, "fate": "survived", "family": family,
         "viewport": near, "maxiter": 500, "image": "node0_c1.jpg", "channel": "share"},
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
    assert held[0]["view"] == "views/node0_c0.jpg"
    record, page = places.stats(tmp_path)
    assert record["families"]["mandelbrot"] == {
        **record["families"]["mandelbrot"],
        "found": 4,
        "places": 2,
        "scored": 1,
    }
    assert record["repeats"] == 1 and record["places"] == 2
    twin = json.loads((page.parent / "page.json").read_text(encoding="utf-8"))
    assert twin["sections"][0]["table"][0][:4] == ["family", "found", "places", "scored"]
    assert [label for label, _ in twin["sections"][0]["legend"]] == twin["sections"][0]["table"][0]


def test_the_scored_column_shows_only_where_it_differs_from_places(tmp_path, monkeypatch):
    from fractal_wallpapers.curation import intake
    from fractal_wallpapers.supply import places

    family = {"kind": "mandelbrot"}
    rows = [
        {"schema": 1, "kind": "candidate", "root_id": 0, "fate": "survived", "family": family,
         "viewport": {"center_re": f"-0.{n}", "center_im": "0.1", "width": "0.01"},
         "maxiter": 500, "image": None, "channel": "share"}
        for n in range(1, 11)
    ]  # fmt: skip
    (tmp_path / "walk.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    monkeypatch.setattr(intake, "scores_path", lambda: tmp_path / "walk.jsonl")
    monkeypatch.setattr(intake, "read_scores", lambda *a, **k: {})
    held = places.rows(tmp_path)
    scores = {row["key"]: {"p_ge3": n / 10, "p_ge4": n / 20} for n, row in enumerate(held)}
    monkeypatch.setattr(intake, "read_scores", lambda *a, **k: scores)
    _record, page = places.stats(tmp_path)
    twin = json.loads((page.parent / "page.json").read_text(encoding="utf-8"))
    assert "scored" not in twin["sections"][0]["table"][0]
    bands = [tile["band"] for tile in twin["sections"][1]["tiles"]]
    assert bands == ["best"] * 4 + ["worst"] * 4
    text = page.read_text(encoding="utf-8")
    assert '<div class="band best"><div class="label">best</div>' in text
    assert '<div class="band worst"><div class="label">worst</div>' in text


def test_a_legend_refuses_a_column_nobody_explained():
    assert grid_page.legend("found", "places") == [
        ("found", "places the walk looked at"),
        ("places", "places it kept"),
    ]
    assert grid_page.legend("x", said={"x": "an x"}) == [("x", "an x")]
    with pytest.raises(KeyError):
        grid_page.legend("no such column")


def test_every_section_of_the_check_and_gallery_pages_states_what_its_columns_mean():
    from fractal_wallpapers.curation import tentative

    labels = [label for label, _ in tentative.TILE_LEGEND]
    assert "rank" in labels and "P(>=4)" in labels
    doc = {
        "stamp": "s", "command": "c", "seats": 0, "asked": 0, "name": "", "forced": False,
        "missing": 0, "at_full": 0, "full_regime": "r", "ordered_by": "o",
        "legend": [["rank", "a number"]], "rows": [],
    }  # fmt: skip
    assert "<b>rank</b>: a number" in tentative._page_html(doc)


def test_a_check_picture_print_is_cell_means_and_its_gap_is_per_channel(tmp_path):
    pytest.importorskip("PIL")
    pytest.importorskip("numpy")
    from PIL import Image

    columns, rows = judges_commands.GRID
    picture = tmp_path / "a.png"
    image = Image.new("RGB", (columns * 20, rows * 20), (10, 20, 30))
    image.putpixel((0, 0), (255, 20, 30))
    image.save(picture)
    cells = judges_commands.picture_print(picture)
    assert len(cells) == columns * rows
    assert cells[1] == [10.0, 20.0, 30.0]
    assert cells[0][0] == pytest.approx(10 + 245 / 400, abs=0.05)
    assert judges_commands.picture_gap(cells, cells) == 0
    moved = [[value + 5 for value in cell] for cell in cells]
    assert judges_commands.picture_gap(cells, moved) == pytest.approx(5)
    assert judges_commands.picture_gap(cells, cells[:-1]) == float("inf")


def test_every_check_case_carries_a_picture_reference_and_a_reference_time():
    for line in judges_commands.check_path().read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        assert case["picture"]["grid"] == list(judges_commands.GRID)
        assert len(case["picture"]["cells"]) == judges_commands.GRID[0] * judges_commands.GRID[1]
        assert case["reference_seconds"] > 0


def test_a_walkthrough_bundle_is_drawn_from_the_page_its_command_left(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image

    from fractal_wallpapers import walkthrough

    picture = tmp_path / "source" / "a.png"
    picture.parent.mkdir()
    Image.new("RGB", (640, 360), (10, 20, 30)).save(picture)
    page = grid_page.write(
        tmp_path / "page" / "index.html",
        "t",
        ["intro"],
        [grid_page.Section("s", tiles=[grid_page.Tile(picture, [("P(>=4)", 0.5)])])],
        command="fractal-wallpapers harvest stats",
    )
    walkthrough.rebundle(page.parent, tmp_path / "out")
    twin = json.loads((tmp_path / "out" / "page.json").read_text(encoding="utf-8"))
    assert twin["command"] == "fractal-wallpapers harvest stats"
    assert twin["sections"][0]["tiles"][0]["picture"] == "pictures/a.jpg"
    assert (tmp_path / "out" / "pictures" / "a.jpg").is_file()
    with pytest.raises(FileNotFoundError):
        walkthrough.rebundle(tmp_path / "never", tmp_path / "out2")


def _readme_commands() -> list[str]:
    """Every command line in the README's fenced blocks, continuation lines joined."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    commands = []
    for block in re.findall(r"^```\n(.*?)^```", text, re.S | re.M):
        for line in block.replace("\\\n", " ").splitlines():
            line = line.split("  #")[0].strip()
            if line:
                commands.append(" ".join(line.split()))
    return commands


def test_the_walkthrough_draws_the_readme_s_render_examples_as_the_readme_spells_them():
    import shlex

    from fractal_wallpapers import walkthrough

    commands = _readme_commands()
    for example in walkthrough.RENDERS:
        assert shlex.join(example["argv"]).replace("'", '"') in commands
    first = [line for line in commands if " render" in line][:2]
    assert [shlex.split(line)[1] for line in first] == ["render", "render-link"]


def test_every_command_on_the_readme_s_path_has_its_help_in_the_walkthrough():
    from fractal_wallpapers import walkthrough

    helped = {" ".join(path) for path in walkthrough.HELP}
    for line in _readme_commands():
        words = line.split()
        if words[0] != "fractal-wallpapers":
            continue
        verbs = [word for word in words[1:] if not word.startswith(("-", "<", "artifacts"))]
        named = " ".join(verbs[:3])
        assert any(named.startswith(path) for path in helped), line
    for path in walkthrough.HELP:
        assert walkthrough.subparser(path).format_help().startswith("usage:")


def test_parameters_name_every_family_and_palette_key_the_engine_takes():
    from fractal_wallpapers import parameters

    spec = (ROOT / "engine" / "src" / "spec.rs").read_text(encoding="utf-8")
    enum = re.search(r"pub enum FamilySpec \{(.*?)\n\}", spec, re.S)
    declared = {
        re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
        for name in re.findall(r"^\s{4}([A-Z]\w*)", enum.group(1), re.M)
    }
    assert set(parameters.FAMILIES) == declared
    choices = next(a for a in parameters.render_parser()._actions if a.dest == "family").choices
    assert {kind for kind, block in parameters.FAMILIES.items() if block["flag"]} == set(choices)

    def fields(path: str, struct: str) -> set[str]:
        text = (ROOT / "engine" / "src" / path).read_text(encoding="utf-8")
        body = re.search(rf"pub struct {struct} \{{(.*?)\n\}}", text, re.S)
        return set(re.findall(r"^\s*pub (\w+):", body.group(1), re.M))

    knobs = (fields("coloring.rs", "Palette") - {"bake"}) | fields("colormap.rs", "Bake")
    # `period` and `knee` are the absolute scale's own, carried inside `Scale`.
    assert set(common.PALETTE_KNOBS) == knobs | {"period", "knee"}
