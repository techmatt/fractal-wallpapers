"""The named colorings, and the dump/recolor pair that only some of them allow.

The engine owns the mode catalog, so these tests ask it rather than restating
it: a list written down twice is a list that will disagree with itself. The
half that needs a built binary skips when there is none, as elsewhere.
"""

from __future__ import annotations

import argparse

import pytest

from fractal_wallpapers import cli, engine

try:
    ENGINE = engine.engine_path()
except FileNotFoundError:
    ENGINE = None

needs_engine = pytest.mark.skipif(ENGINE is None, reason="the engine is not built")

#: Small, cheap, and structured enough that every mode has something to say
#: about it: the whole of a Julia set with both an interior and a wide exterior.
ANCHOR = {
    "schema": 1,
    "family": {"kind": "julia", "c": ["-0.8", "0.156"]},
    "resolution": [64, 36],
    "supersample": 1,
    "maxiter": 300,
    "colormap": "twilight_shifted",
}


#: The teaching field, written out in full — the only way to ask for it, because
#: it is deliberately not in the catalog a mode name is looked up in.
DISCRETE = {"kind": "field", "field": {"kind": "discrete"}}


def spec(mode: str, output, **overrides) -> dict:
    return {**ANCHOR, "mode": mode, "output": str(output), **overrides}


def arguments(command: str, **overrides) -> argparse.Namespace:
    """A parsed command line for one of the location subcommands."""
    args = cli.build_parser().parse_args([command])
    for key, value in overrides.items():
        setattr(args, key, value)
    return args


def test_the_new_subcommands_are_registered() -> None:
    parser = cli.build_parser()
    assert parser.parse_args(["dump-field"]).handler is cli.dump_field
    assert parser.parse_args(["recolor", "--field", "f.f32"]).handler is cli.recolor
    assert parser.parse_args(["modes"]).handler is cli.modes


def test_a_render_names_the_mode_it_wants() -> None:
    assert cli.render_spec(arguments("render"))["mode"] == "smooth"
    assert cli.render_spec(arguments("render", mode="tia"))["mode"] == "tia"


def test_a_discrete_render_writes_its_coloring_out_instead_of_naming_a_mode() -> None:
    """The integer count has no name in the catalog, so the spec carries the
    coloring itself — and carries no `mode` key, which the engine would refuse
    alongside it."""
    plain = cli.render_spec(arguments("render", discrete=0))
    assert "mode" not in plain
    assert plain["coloring"] == {"kind": "field", "field": {"kind": "discrete"}}

    banded = cli.render_spec(arguments("render", discrete=24))
    assert banded["coloring"]["field"] == {"kind": "discrete", "cycle": 24}


def test_a_render_that_asks_for_both_a_mode_and_the_integer_count_is_refused() -> None:
    assert cli.render(arguments("render", mode="tia", discrete=0)) == 1
    assert cli.render(arguments("render", discrete=-3)) == 1


def test_a_dump_is_the_same_spec_as_the_render_it_stops_short_of() -> None:
    """Only the output differs, which is what makes the two comparable at all."""
    render = cli.render_spec(arguments("render", mode="stripe"))
    dump = cli.render_spec(arguments("dump-field", mode="stripe", out="artifacts/f.f32"))
    assert {k: v for k, v in render.items() if k != "output"} == {
        k: v for k, v in dump.items() if k != "output"
    }
    assert dump["output"].endswith("f.f32")


@needs_engine
def test_the_catalog_is_the_engines_and_covers_all_three_shapes() -> None:
    names = [mode["name"] for mode in engine.modes()]
    assert names[0] == "smooth", "the spine comes first"
    assert len(names) == len(set(names))
    for expected in ("tia", "smooth_stripe", "direct_trap_multiply"):
        assert expected in names
    assert all(mode["identity"] for mode in engine.modes())


@needs_engine
def test_the_integer_count_is_reachable_and_renders_a_picture(tmp_path) -> None:
    """It is a real coloring: it renders, it dumps like any other field, and its
    record carries the coloring rather than a name.

    What it renders — flat bands rather than a gradient — is a property of the
    *field* and is pinned in the crate, where the comparison against the smooth
    count is exact. Here the claim is only that the whole path is open, so this
    reads the same "not one flat color" size floor every named mode is held to.
    """
    location = {key: value for key, value in ANCHOR.items() if key != "mode"}
    discrete = tmp_path / "discrete.png"
    report = engine.render_report({**location, "coloring": DISCRETE, "output": str(discrete)})
    assert report.get("mode") is None, "a written-out coloring has no mode name"
    assert report["coloring"] == {
        "kind": "field",
        # The echo carries the field's whole state, `cycle` included, the way
        # every other field's constants are echoed: the record is what a render
        # is repeated from.
        "field": {"kind": "discrete", "cycle": None},
        "transform": "linear",
    }
    assert discrete.stat().st_size > 1500, "the discrete render is nearly uniform"

    field = tmp_path / "discrete.f32"
    dumped = engine.dump_field({**location, "coloring": DISCRETE, "output": str(field)})
    assert dumped["samples"] == [64, 36]

    banded = {"kind": "field", "field": {"kind": "discrete", "cycle": 12}}
    report = engine.render_report(
        {**location, "coloring": banded, "output": str(tmp_path / "b.png")}
    )
    assert report["coloring"]["field"]["cycle"] == 12


@needs_engine
def test_the_integer_count_is_not_a_named_mode_and_curation_cannot_draw_it() -> None:
    """The guard the whole teaching mode rests on.

    A production render picks its coloring by name out of the engine's catalog,
    so a field that is not in the catalog cannot be picked — not by the mode
    draw, not by the render cache, not by a corpus row. This asserts the absence
    at all three readers rather than only at the one that would be noticed.
    """
    from fractal_wallpapers.curation import budget, colorize
    from fractal_wallpapers.labeling import finished_import
    from fractal_wallpapers.models import renders

    assert "discrete" not in {mode["name"] for mode in engine.modes()}
    assert "discrete" not in renders.catalog()
    assert "discrete" not in finished_import.engine_modes()
    for head in (budget.SMOOTH, budget.STRANGE):
        assert "discrete" not in colorize.modes_for(head)
    with pytest.raises(renders.RenderCacheError, match="no mode named"):
        renders.coloring_of({"mode": "discrete", "curve": "linear"})


@needs_engine
def test_every_named_mode_renders_something_that_is_not_one_flat_color(tmp_path) -> None:
    """A mode that resolves but paints a single color is worse than one that
    fails: it looks like a render until someone looks at it.

    A PNG is the measure. Structure does not compress and flatness does: every
    mode here lands between three and seven kilobytes at this size, while a
    uniform frame would be a few hundred bytes.
    """
    for mode in engine.modes():
        name = mode["name"]
        output = tmp_path / f"{name}.png"
        report = engine.render_report(spec(name, output))
        assert report["mode"] == name
        assert output.stat().st_size > 1500, f"{name} rendered a nearly uniform image"


@needs_engine
def test_a_dumped_field_recolors_to_exactly_the_render_it_came_from(tmp_path) -> None:
    """The whole claim of the dump: coloring the field again reproduces the
    render bit for bit, so exploring palettes against it is not an approximation
    of what a re-render would give."""
    for name in ("smooth", "tia", "stripe", "trap_circle", "gaussian_int"):
        rendered = tmp_path / f"{name}.png"
        engine.render_report(spec(name, rendered, supersample=2))

        field = tmp_path / f"{name}.f32"
        dumped = engine.dump_field(spec(name, field, supersample=2))
        assert (tmp_path / f"{name}.json").is_file()
        assert dumped["samples"] == [128, 72]

        again = tmp_path / f"{name}_again.png"
        engine.recolor({"schema": 1, "field": str(field), "output": str(again)})
        assert again.read_bytes() == rendered.read_bytes(), name


@needs_engine
def test_recoloring_through_another_colormap_changes_the_picture(tmp_path) -> None:
    field = tmp_path / "stripe.f32"
    engine.dump_field(spec("stripe", field))
    outputs = []
    for colormap in ("twilight_shifted", "blue_orange"):
        output = tmp_path / f"{colormap}.png"
        report = engine.recolor(
            {
                "schema": 1,
                "field": str(field),
                "colormap": colormap,
                "output": str(output),
            }
        )
        assert report["colormap"] == colormap
        outputs.append(output.read_bytes())
    assert outputs[0] != outputs[1]


@needs_engine
def test_the_modes_with_no_scalar_field_refuse_to_be_dumped(tmp_path) -> None:
    """And say which of the two reasons it is, because they are different
    reasons and the fix differs with them."""
    with pytest.raises(RuntimeError, match="composite normalizes"):
        engine.dump_field(spec("smooth_trap_circle", tmp_path / "no.f32"))
    with pytest.raises(RuntimeError, match="color-valued"):
        engine.dump_field(spec("direct_trap_ring", tmp_path / "no.f32"))


@needs_engine
def test_an_unknown_mode_is_refused_with_the_list_of_real_ones() -> None:
    with pytest.raises(RuntimeError, match="unknown mode"):
        engine.render_report(spec("nautilus", "unreachable.png"))


@needs_engine
def test_a_field_cannot_be_dumped_over_its_own_record(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="record"):
        engine.dump_field(spec("smooth", tmp_path / "field.json"))
