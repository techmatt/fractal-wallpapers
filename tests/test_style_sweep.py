"""`style sweep`: the checker's picture checks, its plan, and one small engine run."""

from __future__ import annotations

import pytest

from fractal_wallpapers import cli, engine, style_sweep, styles


def picture(path, colour, size=(40, 25), half=None):
    """A flat picture, its right half another colour when `half` is given."""
    from PIL import Image

    image = Image.new("RGB", size, colour)
    if half is not None:
        image.paste(Image.new("RGB", (size[0] // 2, size[1]), half), (size[0] // 2, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return path


def test_a_flat_frame_a_wash_and_a_void_are_flagged(tmp_path):
    assert style_sweep.flags_of(style_sweep.look(picture(tmp_path / "g.png", (90, 90, 90)))) == [
        "flat"
    ]
    assert "washed" in style_sweep.flags_of(
        style_sweep.look(picture(tmp_path / "w.png", (255,) * 3))
    )
    assert "drowned" in style_sweep.flags_of(
        style_sweep.look(picture(tmp_path / "b.png", (0,) * 3))
    )
    split = picture(tmp_path / "s.png", (20, 40, 90), half=(230, 200, 120))
    assert style_sweep.flags_of(style_sweep.look(split)) == []


def test_two_pictures_compare_by_their_pixels(tmp_path):
    a = picture(tmp_path / "a.png", (10, 20, 30))
    assert style_sweep.difference(a, picture(tmp_path / "b.png", (10, 20, 30))) == 0.0
    assert style_sweep.difference(a, picture(tmp_path / "c.png", (10, 20, 31))) > 0.0
    assert style_sweep.difference(a, picture(tmp_path / "d.png", (10, 20, 30), (8, 8))) == 1.0


def test_a_knob_whose_ends_match_is_dead_and_a_slow_end_is_named(tmp_path):
    low = picture(tmp_path / "low.png", (10, 20, 30), half=(200, 100, 50))
    high = picture(tmp_path / "high.png", (10, 20, 30), half=(200, 100, 50))
    other = picture(tmp_path / "other.png", (10, 20, 30), half=(200, 100, 51))
    todo = [
        {"style": "s", "variant": "seat0", "knobs": {}, "against": None},
        {"style": "s", "variant": "k_low", "knobs": {"k": 0}, "against": None},
        {"style": "s", "variant": "k_high", "knobs": {"k": 1}, "against": "k_low"},
        {"style": "s", "variant": "palette1_x", "knobs": {}, "against": "seat0"},
    ]
    rows = [
        {"style": "s", "variant": "seat0", "picture": str(other), "flags": [], "per_msample": 1},
        {"style": "s", "variant": "k_low", "picture": str(low), "flags": [], "per_msample": 1},
        {"style": "s", "variant": "k_high", "picture": str(high), "flags": [], "per_msample": 1},
        {
            "style": "s",
            "variant": "palette1_x",
            "picture": str(other),
            "flags": [],
            "per_msample": 20,
        },
    ]
    style_sweep.compare(rows, todo)
    assert rows[2]["flags"] == ["dead_knob"]
    assert rows[3]["flags"] == ["same_palette", "slow"]
    assert rows[0]["flags"] == [] and rows[1]["flags"] == []


def test_the_plan_draws_seats_both_knob_ends_and_every_palette_entry():
    name = "lit_petals"
    document = styles.load(name)
    todo = style_sweep.plan([name], 2, [])
    variants = [item["variant"] for item in todo]
    knobs = (document.get("public") or {}).get("knobs") or []
    assert knobs, "a published mode with knobs"
    for knob in knobs:
        assert f"knob_{knob['name']}_low" in variants and f"knob_{knob['name']}_high" in variants
    row = next(r for r in styles.catalog_rows() if r["style"] == name)
    assert sum(v.startswith("palette") for v in variants) == len(row["palettes"])
    assert all(item["location"] for item in todo)


def test_a_style_with_no_keeps_draws_gallery_seats():
    seats = style_sweep.seats_of("no_such_style_keeps", [{"name": "g0"}, {"name": "g1"}], 1)
    assert seats == [{"location": {"name": "g0"}, "colormap": None}]


def test_the_cli_parses_a_sweep_and_scout_refuses_a_count_below_one(capsys):
    from fractal_wallpapers.cli import style_commands

    args = cli.build_parser().parse_args(["style", "sweep", "yas", "--out", "x"])
    assert args.what == "sweep" and args.names == ["yas"] and args.resolution == [320, 200]
    scout = cli.build_parser().parse_args(["style", "scout", "--out", "x.jsonl", "--n", "-3"])
    assert style_commands.scout_style(scout) == 1
    assert "at least 1" in capsys.readouterr().out


@pytest.mark.slow
@pytest.mark.skipif(not engine.is_built(), reason="the engine is not built")
def test_a_sweep_draws_checks_and_lays_out_one_style(tmp_path):
    rows = style_sweep.sweep(
        tmp_path, ["yas"], seats=1, resolution=(48, 30), supersample=1, log=None
    )
    assert rows and all("failed" not in row["flags"] for row in rows)
    assert (tmp_path / "sweep.jsonl").is_file()
    assert (tmp_path / "sheets" / "yas.jpg").is_file()
