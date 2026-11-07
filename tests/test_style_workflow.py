"""The style workflow's tools: a gallery scout that never draws a spiral, the render log
`style render` keeps, and the picker built from it that `style keep` can read."""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers import cli, style_keeps, style_picker, style_scout


def seat(key, partition, spiral=False, p=0.05, width="0.01", kind="mandelbrot", degree=2):
    family = {"kind": kind, "degree": degree}
    if kind == "julia":
        family["c"] = ["-0.1", "0.65"]
    row = {
        "key": key,
        "alias": key[:8],
        "seat": int(key[-2:], 16),
        "partition": partition,
        "mode": "smooth",
        "spiral": spiral,
        "p_spiral": p,
    }
    recipe = {
        "family": family,
        "viewport": {"center_re": "-0.5", "center_im": "0", "width": width},
        "maxiter": 500,
    }
    return row, recipe


@pytest.fixture
def gallery(monkeypatch):
    """Two published records sharing one seat, read through `tentative`'s own readers."""
    from fractal_wallpapers.curation import tentative

    held = {
        "A": [
            seat("aaaaaaaaaaaaaa01", "mandelbrot"),
            seat("aaaaaaaaaaaaaa02", "mandelbrot", spiral=True, p=0.9),
            seat("aaaaaaaaaaaaaa03", "julia:multibrot3", kind="julia", degree=3),
            seat("aaaaaaaaaaaaaa04", "multibrot4", degree=4, p=0.25),
            seat("aaaaaaaaaaaaaa05", "mandelbrot", width="1e-12"),
        ],
        "B": [
            seat("aaaaaaaaaaaaaa01", "mandelbrot"),
            seat("bbbbbbbbbbbbbb06", "julia:multibrot3", kind="julia", degree=3),
        ],
    }
    monkeypatch.setattr(tentative, "published", lambda: ["A", "B"])
    monkeypatch.setattr(
        tentative, "read_manifest", lambda stamp: {"solve": {"name": f"record_{stamp.lower()}"}}
    )
    monkeypatch.setattr(tentative, "read_rows", lambda stamp: [row for row, _ in held[stamp]])
    monkeypatch.setattr(
        tentative, "read_recipes", lambda stamp: {row["key"]: recipe for row, recipe in held[stamp]}
    )
    return held


def test_a_scout_never_draws_a_spiral_or_a_seat_too_deep_to_render(gallery):
    seats, passed = style_scout.candidates(["record_a", "B"])
    keys = [seat["row"]["key"] for seat in seats]
    assert "aaaaaaaaaaaaaa02" not in keys and "aaaaaaaaaaaaaa05" not in keys
    assert keys.count("aaaaaaaaaaaaaa01") == 1
    assert passed == {"spiral": 1, "p_spiral": 0, "deep": 1, "filtered": 0, "repeat": 1}


def test_a_scout_filters_for_the_structure_a_style_needs(gallery):
    def keys(**filters):
        return {seat["row"]["key"][-2:] for seat in style_scout.candidates(["A"], **filters)[0]}

    assert keys(kinds=["julia"]) == {"03"}
    assert keys(degrees=[4]) == {"04"}
    assert keys(partitions=["mandelbrot"]) == {"01"}
    assert keys(max_p_spiral=0.2) == {"01", "03"}


def test_a_spiral_scout_draws_only_spirals_for_a_spiral_reference(gallery):
    seats, passed = style_scout.candidates(["A"], spiral=True, max_p_spiral=0.2)
    assert [seat["row"]["key"][-2:] for seat in seats] == ["02"]
    assert passed["spiral"] == 4


def test_the_draw_is_seeded_and_takes_every_partition_in_turn(gallery):
    seats, _ = style_scout.candidates(["A", "B"])
    first = [row["name"] for row in style_scout.draw(seats, 3, seed=7)[0]]
    assert first == [row["name"] for row in style_scout.draw(seats, 3, seed=7)[0]]
    partitions = [name.rsplit("_", 1)[0] for name in first]
    assert len(set(partitions)) == 3


def test_a_measured_draw_keeps_the_thin_or_the_thinnest(gallery, monkeypatch, tmp_path):
    readings = {"01": 0.30, "03": 0.02, "04": 0.08, "06": 0.05}
    monkeypatch.setattr(
        style_scout, "ink", lambda location, scratch: readings[location["gallery"]["key"][-2:]]
    )
    seats, _ = style_scout.candidates(["A", "B"])
    thin, read = style_scout.draw(seats, 2, seed=0, max_ink=0.06, scratch=tmp_path)
    assert {row["ink"] for row in thin} == {0.02, 0.05} and len(read) <= 4
    best, read = style_scout.draw(seats, 2, seed=0, thinnest=True, scratch=tmp_path)
    assert [row["ink"] for row in best] == [0.02, 0.05] and len(read) == 4


def test_a_measurement_keeps_every_point_in_order_and_a_floor_keeps_the_dense(
    monkeypatch, tmp_path
):
    readings = {"a": 0.30, "b": 0.02, "c": 0.08}
    monkeypatch.setattr(style_scout, "ink", lambda location, scratch: readings[location["name"]])
    points = [{"name": name} for name in ("a", "b", "c")]
    every, read = style_scout.measure(points, 1, 0.05, False, tmp_path, every=True)
    assert [row["name"] for row in every] == ["a", "b", "c"] and len(read) == 3
    assert [row["ink"] for row in every] == [0.30, 0.02, 0.08]
    dense, _ = style_scout.measure(points, 5, None, False, tmp_path, min_ink=0.05)
    assert [row["name"] for row in dense] == ["a", "c"]


def test_a_drawn_seat_is_a_location_record_naming_its_seat(gallery):
    seats, _ = style_scout.candidates(["A"], partitions=["mandelbrot"])
    (record,) = style_scout.draw(seats, 5, seed=0)[0]
    assert {"family", "viewport", "maxiter"} <= set(record)
    assert record["gallery"]["record"] == "record_a" and record["gallery"]["seat"] == 1


def test_an_unknown_record_is_refused_by_name(gallery):
    with pytest.raises(style_scout.ScoutError, match="record_a"):
        style_scout.candidates(["nope"])


def test_a_degree_filter_never_answers_for_a_family_without_one(gallery):
    from fractal_wallpapers.curation import tentative

    phoenix = seat("cccccccccccccc07", "phoenix", kind="phoenix")
    phoenix[1]["family"].pop("degree")
    gallery["A"].append(phoenix)
    keys = {seat["row"]["key"][-2:] for seat in style_scout.candidates(["A"], degrees=[2])[0]}
    assert keys == {"01"} and tentative.read_rows("A")[-1]["partition"] == "phoenix"


def test_the_render_log_keeps_the_record_as_written_cap_and_all(tmp_path):
    from fractal_wallpapers import locations

    written = {
        "schema": 1,
        "name": "m_x",
        "family": {"kind": "mandelbrot"},
        "viewport": {"center_re": "-0.5", "center_im": "0", "width": "3"},
        "maxiter": 5000,
    }
    path = tmp_path / "x.json"
    path.write_text(json.dumps(written), encoding="utf-8")
    assert style_picker.records_as_written(path) == [written]
    listed = tmp_path / "listed.json"
    listed.write_text(json.dumps([written]), encoding="utf-8")
    assert style_picker.records_as_written(listed) == [written]
    read = locations.read_one(path, drawing=True)
    folded = style_picker.log_row(tmp_path / "a.png", read, "yas", "yas", [8, 5], 1, {})
    assert folded["location"]["maxiter"] == 5000
    kept = style_picker.log_row(tmp_path / "a.png", written, "yas", "yas", [8, 5], 1, {})
    assert kept["location"] == written


def test_the_render_log_keeps_one_row_a_picture(tmp_path):
    location = {"family": {"kind": "mandelbrot"}, "maxiter": 9, "render": {"mode": "x"}}
    first = style_picker.log_row(tmp_path / "a.png", location, "yas", "yas", [8, 5], 1, {"n": 1})
    again = {**first, "colormap": "hsv"}
    style_picker.append_log([first], tmp_path)
    style_picker.append_log([again], tmp_path)
    held = style_picker.read_log(tmp_path)
    assert list(held) == ["a.png"] and held["a.png"]["colormap"] == "hsv"
    assert "render" not in held["a.png"]["location"]


def picture(path):
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 10), (40, 80, 120)).save(path)
    return path


def test_a_picker_is_built_with_nothing_selected_and_a_sidecar_keep_reads(tmp_path):
    drawn = tmp_path / "renders"
    location = {"family": {"kind": "mandelbrot"}, "maxiter": 9}
    for name in ("a", "b"):
        png = picture(drawn / f"{name}.png")
        row = style_picker.log_row(png, location, "yas", "yas", [16, 10], 1, {"name": "yas"})
        style_picker.append_log([row], drawn)
    baseline = picture(tmp_path / "base.png")
    plan = {
        "name": "style_yas_r9",
        "title": "t",
        "rows": [
            {
                "id": "locations",
                "options": [{"picture": "renders/a.png"}, {"picture": "renders/b.png"}],
            },
            {
                "id": "baseline",
                "options": [
                    {
                        "picture": str(baseline),
                        "render": {
                            "location": location,
                            "mode": "smooth",
                            "colormap": "yas",
                            "resolution": [16, 10],
                            "supersample": 1,
                        },
                    }
                ],
            },
        ],
    }
    folder = tmp_path / "picker"
    done = style_picker.build(plan, folder, tmp_path)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert done["options"] == 3
    assert all(row["kind"] == "many" and row["default"] == [] for row in manifest["rows"])
    assert (folder / "locations" / "a.jpg").is_file()
    renders = style_keeps.read_renders(folder / "renders.jsonl")
    assert set(renders) == {"a", "b", "base"} and renders["base"]["mode"] == "smooth"


def test_a_picture_nobody_can_draw_again_is_refused(tmp_path):
    picture(tmp_path / "lost.png")
    plan = {"name": "style_x_r1", "rows": [{"id": "r", "options": [{"picture": "lost.png"}]}]}
    with pytest.raises(style_picker.PickerError, match="no row"):
        style_picker.build(plan, tmp_path / "picker", tmp_path)


def test_a_key_used_in_two_rows_is_refused(tmp_path):
    png = picture(tmp_path / "a.png")
    row = style_picker.log_row(png, {"family": {}}, "yas", "yas", [16, 10], 1, {})
    style_picker.append_log([row], tmp_path)
    plan = {
        "name": "style_x_r1",
        "rows": [
            {"id": "one", "options": [{"picture": "a.png"}]},
            {"id": "two", "options": [{"picture": "a.png"}]},
        ],
    }
    with pytest.raises(style_picker.PickerError, match="twice"):
        style_picker.build(plan, tmp_path / "picker", tmp_path)
    plan["rows"][1]["options"][0]["key"] = "A"
    with pytest.raises(style_picker.PickerError, match="twice"):
        style_picker.build(plan, tmp_path / "picker", tmp_path)


def test_a_picture_offered_twice_is_one_image_and_one_keep_picked_twice(tmp_path):
    """Each option once got its own JPEG, so `style keep` recorded and copied one
    picture twice, never the one keep picked twice its docstring promised."""
    png = picture(tmp_path / "a.png")
    location = {"schema": 1, "family": {"kind": "mandelbrot"}, "maxiter": 9}
    row = style_picker.log_row(png, location, "yas", "yas", [16, 10], 1, {"name": "yas"})
    style_picker.append_log([row], tmp_path)
    plan = {
        "name": "style_x_r1",
        "rows": [
            {"id": "one", "options": [{"picture": "a.png"}]},
            {"id": "two", "options": [{"picture": "a.png", "key": "a_again"}]},
        ],
    }
    folder = tmp_path / "picker"
    style_picker.build(plan, folder, tmp_path)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    images = [row["options"][0]["image"] for row in manifest["rows"]]
    assert images == ["one/a.jpg", "one/a.jpg"]
    choices = {
        "name": "style_x_r1",
        "rows": [{"id": "one", "keys": ["a"]}, {"id": "two", "keys": ["a_again"]}],
    }
    renders = style_keeps.read_renders(folder / "renders.jsonl")
    keeps, _ = style_keeps.kept(choices, manifest, renders, folder)
    assert len(keeps) == 1 and len(keeps[0]["picked"]) == 2


def test_a_key_or_a_render_that_could_not_be_kept_is_refused_at_build(tmp_path):
    png = picture(tmp_path / "a.png")
    plan = {"name": "style_x_r1", "rows": [{"id": "r", "options": [{"picture": "a.png"}]}]}
    plan["rows"][0]["options"][0]["render"] = {"location": {}, "mode": "smooth"}
    with pytest.raises(style_picker.PickerError, match="lacks colormap"):
        style_picker.build(plan, tmp_path / "picker", tmp_path)
    row = style_picker.log_row(png, {"family": {}}, "yas", "yas", [16, 10], 1, {})
    style_picker.append_log([row], tmp_path)
    plan["rows"][0]["options"][0] = {"picture": "a.png", "key": "a/b"}
    with pytest.raises(style_picker.PickerError, match="file name"):
        style_picker.build(plan, tmp_path / "picker", tmp_path)


def test_a_points_file_with_a_line_that_is_no_record_is_refused(tmp_path):
    points = tmp_path / "points.jsonl"
    points.write_text('{"name": "a"}\n"just a string"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        style_picker.records_as_written(points)


def test_the_cli_parses_scout_picker_sheet_draft_and_the_identity_battery():
    parser = cli.build_parser()
    args = parser.parse_args(
        ["style", "scout", "--out", "x.jsonl", "--kind", "julia", "--max-ink", "0.03"]
    )
    assert args.what == "scout" and args.kind == ["julia"] and args.max_ink == 0.03
    assert parser.parse_args(["style", "picker", "plan.json"]).what == "picker"
    assert parser.parse_args(["style", "render", "yas", "--location", "l.json", "--draft"]).draft
    measured = parser.parse_args(
        ["style", "scout", "--out", "x.jsonl", "--points", "p.jsonl", "--measure"]
    )
    assert measured.measure and measured.min_ink is None
    sheet = parser.parse_args(["style", "sheet", "s.png", "drafts", "--columns", "4"])
    assert sheet.what == "sheet" and sheet.sources == ["drafts"] and sheet.tile_width == 640
    battery = parser.parse_args(["identity", "t"])
    assert battery.threads == 2 and battery.workers == 3
