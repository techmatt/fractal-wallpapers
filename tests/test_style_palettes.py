"""Palette sets: a mode is one stack and the maps kept in it, each with its tuned values."""

from __future__ import annotations

import copy

import pytest

from fractal_wallpapers import style_catalog, style_palettes, styles

STACK = {
    "name": "m",
    "tone": {"median": 0.2, "p10": 0.05},
    "layers": [
        {"kind": "palette", "channel": {"field": {"kind": "smooth"}}, "opacity": 1.0},
        {
            "kind": "glow",
            "channel": {"field": {"kind": "de"}},
            "color": {"rgb": "#ffffff"},
            "blend": "screen",
            "opacity": 0.5,
        },
        {
            "kind": "glow",
            "channel": {"field": {"kind": "de"}},
            "color": {"palette": 0.9},
            "blend": "screen",
            "opacity": 0.7,
        },
    ],
}


def test_values_are_the_numbers_and_colours_between_two_stacks_and_apply_back():
    other = copy.deepcopy(STACK)
    other["name"] = "other"
    other["tone"]["median"] = 0.3
    other["layers"][1]["color"] = {"palette": 0.4}
    values = style_palettes.values_between(STACK, other)
    assert values == {"/tone/median": 0.3, "/layers/1/color": {"palette": 0.4}}
    drawn = style_palettes.apply(STACK, values)
    assert {**drawn, "name": "other"} == other
    assert STACK["tone"]["median"] == 0.2, "apply writes a copy"


def test_a_missing_layer_is_its_opacity_at_zero_and_a_second_is_structure():
    one_less = copy.deepcopy(STACK)
    del one_less["layers"][1]
    values = style_palettes.values_between(STACK, one_less)
    assert values == {"/layers/1/opacity": 0.0}
    two_less = copy.deepcopy(STACK)
    del two_less["layers"][1:]
    with pytest.raises(style_palettes.Incompatible):
        style_palettes.values_between(STACK, two_less)


def test_another_channel_or_blend_is_another_mode():
    for path, value in (("channel", {"field": {"kind": "smooth"}}), ("blend", "multiply")):
        other = copy.deepcopy(STACK)
        other["layers"][2][path] = value
        with pytest.raises(style_palettes.Incompatible):
            style_palettes.values_between(STACK, other)


def test_a_value_naming_nothing_refuses():
    with pytest.raises(styles.StyleError):
        style_palettes.apply(STACK, {"/layers/9/opacity": 0.0})


def _row():
    keeps = {
        "a": {"render": {"style": "m", "colormap": "yas", "stack": "m@1"}},
        "b": {"render": {"style": "m", "colormap": "magma", "stack": "m@2"}},
        "c": {"render": {"mode": "smooth", "colormap": "hsv"}},
    }
    row = {
        "style": "m",
        "score": 3,
        "palettes": [
            {"colormap": "yas", "values": {}, "keeps": ["a"], "score": 3},
            {"colormap": "magma", "values": {"/tone/median": 0.3}, "keeps": ["b"], "score": 2},
        ],
    }
    return row, keeps


def test_a_row_holds_its_set_to_its_keeps_and_its_score_to_its_best_palette():
    row, keeps = _row()
    assert style_palettes.check_row(row, STACK, keeps) == []
    row["score"] = 2
    assert any("best palette" in p for p in style_palettes.check_row(row, STACK, keeps))
    row, keeps = _row()
    row["palettes"][1]["keeps"] = []
    assert any(
        "'b' (magma) is in no palette" in p for p in style_palettes.check_row(row, STACK, keeps)
    )
    row, keeps = _row()
    row["palettes"][0]["values"] = {"/tone/p10": 0.1}
    assert any("stack's own" in p for p in style_palettes.check_row(row, STACK, keeps))


def test_a_kept_tile_lays_its_map_into_the_set_once():
    row, _ = _row()
    other = copy.deepcopy(STACK)
    other["tone"]["p10"] = 0.07
    keep = {"id": "d", "render": {"style": "m", "colormap": "hsv", "stack": "m@3"}}
    baseline = {"id": "e", "render": {"mode": "smooth", "colormap": "pink"}}
    added = style_palettes.add_keeps(row, STACK, [keep, baseline], {"m@3": other})
    assert added == ["hsv"]
    assert row["palettes"][-1] == {"colormap": "hsv", "values": {"/tone/p10": 0.07}, "keeps": ["d"]}
    assert style_palettes.add_keeps(row, STACK, [keep], {"m@3": other}) == []
    assert row["palettes"][-1]["keeps"] == ["d"]


def test_every_merged_style_still_opens_as_its_palette_of_the_mode():
    """Old style names keep resolving, so keeps, pickers and links do not break."""
    for row in style_catalog.load()["modes"]:
        mode = styles.load(row["style"])
        for alias in row.get("aliases", []):
            assert alias not in styles.names()
            document = styles.load(alias)
            assert document["name"] == row["style"]
            entry = next((e for e in row["palettes"] if e.get("was") == alias), None)
            if entry is None:
                assert document["style"] == mode["style"]
                continue
            assert document["suggested_colormap"] == entry["colormap"]
            assert document["style"] == style_palettes.apply(mode["style"], entry["values"])


def test_a_score_is_a_whole_number_and_a_map_is_spelled_exactly():
    """`4.0` passed `in range(1, 6)` and crashed the gallery's stars; a wrong-case map
    passed a Windows path test and was never found by `entry_for`."""
    assert style_palettes.is_score(4) and not style_palettes.is_score(4.0)
    assert not style_palettes.is_score(True) and not style_palettes.is_score(6)
    row = {"style": "m", "palettes": [{"colormap": "HSV", "values": {}, "keeps": []}]}
    problems = style_palettes.check_row(row, STACK, {})
    assert any("no colormap 'HSV'" in problem for problem in problems)


def test_a_palette_round_refuses_a_merged_name_and_a_discarded_mode(tmp_path, capsys):
    """Refused before the map is read: a merged name points at its mode, and a discarded
    mode takes no palette round."""
    from fractal_wallpapers import cli

    rows = styles.catalog_rows()
    alias = next(a for row in rows for a in row.get("aliases", []))
    gone = next(row["style"] for row in rows if row.get("status") == "discarded")
    unread = tmp_path / "map.json"
    assert cli.main(["palettes", "add", str(unread), "--mode", alias]) == 1
    assert "merged into" in capsys.readouterr().out
    assert cli.main(["palettes", "add", str(unread), "--mode", gone]) == 1
    assert "discarded" in capsys.readouterr().out
