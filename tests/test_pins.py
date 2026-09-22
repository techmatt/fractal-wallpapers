"""The pinned list: how an explorer link becomes the ledger row a solve seats first.

Synthetic ledger rows throughout. What is pinned here is the resolution rule —
plane, mode and place, a tolerance relative to the link's own width, and the three
tiers that choose among rows sharing a place — and the two ways the solver's read
of the file fails soft. What a pin does inside a solve is `tests/test_solve.py`'s
*Pinned seats* section.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import pins, tentative


def row(
    key,
    *,
    kind="mandelbrot",
    degree=2,
    c=None,
    mode="smooth",
    x="-0.75",
    y="0.1",
    w="0.001",
    colormap="BuGn",
    phase=0.0,
):
    """One ledger row, spelled the way the ledger spells it."""
    family = {"kind": kind, "degree": degree}
    if c is not None:
        family["c"] = [str(c[0]), str(c[1])]
    return {
        "schema": 1,
        "key": str(key),
        "partition": kind,
        "recipe": {
            "family": family,
            "viewport": {"center_re": str(x), "center_im": str(y), "width": str(w)},
            "mode": mode,
            "colormap": colormap,
            "palette": {"phase": phase},
        },
    }


def link(query: str) -> str:
    return "http://localhost:8000/explorer/?v=3&" + query


def quiet(*_args, **_rest) -> None:
    """A `log` that says nothing."""


# --------------------------------------------------------------------------- #
# Reading a link.
# --------------------------------------------------------------------------- #
def test_a_link_that_names_no_family_or_mode_is_the_explorers_defaults():
    view = pins.parse(link("x=-0.75&y=0.1&w=0.001&p=abstract-3d-wallpapers&phase=0.25"))
    assert view["family"] == "mandelbrot"
    assert view["mode"] == "smooth"
    assert view["phase"] == 0.25
    assert view["constants"] == {}


def test_a_palette_name_is_read_percent_decoded():
    view = pins.parse(link("m=threads&x=0&y=0&w=1&p=Verdant%20Ascent"))
    assert view["palette"] == "Verdant Ascent"


def test_a_link_with_no_frame_names_no_place_and_is_refused():
    with pytest.raises(pins.PinsRefused):
        pins.parse(link("f=julia&cx=0&cy=0&p=BuGn"))


def test_a_plane_is_named_the_way_a_link_names_it():
    assert pins.family_of("multibrot", 2) == "mandelbrot"
    assert pins.family_of("mandelbrot", 2) == "mandelbrot"
    assert pins.family_of("multibrot", 4) == "multibrot4"
    assert pins.family_of("julia", 2) == "julia"
    assert pins.family_of("julia", 3) == "julia3"
    assert pins.family_of("phoenix", 2) == "phoenix"


# --------------------------------------------------------------------------- #
# Writing one.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "view",
    [
        {
            "family": "mandelbrot",
            "constants": {},
            "mode": "smooth",
            "x": "-0.75",
            "y": "0.1",
            "w": "0.001",
            "palette": None,
            "phase": 0.0,
        },
        {
            "family": "multibrot4",
            "constants": {},
            "mode": "threads",
            "x": "0.4463839370384832",
            "y": "0.6581804592603596",
            "w": "0.00000016659688118789476",
            "palette": "Sapphire Against Rose",
            "phase": 0.326013,
        },
        {
            "family": "julia",
            "constants": {"cx": "-0.7488551646997019", "cy": "-0.13572339871672048"},
            "mode": "stripe",
            "x": "0.435675577907737",
            "y": "0.06312318776094998",
            "w": "0.009812625699590332",
            "palette": "glowdon",
            "phase": 0.0,
        },
    ],
)
def test_a_query_written_here_reads_back_as_the_view_it_was_written_from(view):
    """[`pins.query_of`] is [`pins.parse`]'s inverse, and that is the whole claim.

    A writer emitting thousands of links — `minibrots examples` is the one that
    needed this — has no other way to know its links open the places it meant. The
    coordinates go in as the decimal strings a ledger wrote and come back as the
    floats they spell, so the check is on the value and not on the spelling.
    """
    back = pins.parse(pins.EXPLORER_BASE + pins.query_of(view))
    assert back["family"] == view["family"]
    assert back["mode"] == view["mode"]
    assert back["palette"] == view["palette"]
    assert back["phase"] == pytest.approx(view["phase"])
    for key in ("x", "y", "w"):
        assert back[key] == float(view[key])
    for key, value in view["constants"].items():
        assert back["constants"][key] == float(value)


def test_a_written_query_leaves_out_the_two_keys_the_explorer_defaults():
    """A link to a `mandelbrot` `smooth` view carries no `f` and no `m`.

    Not cosmetic: every link in `pins.txt` is shaped this way, and a writer that
    spelled the defaults would make a file of links that do not compare equal to
    the ones a person pastes out of the explorer.
    """
    plain = {
        "family": pins.DEFAULT_FAMILY,
        "constants": {},
        "mode": pins.DEFAULT_MODE,
        "x": "-0.5",
        "y": "0.0",
        "w": "3.0",
        "palette": None,
        "phase": 0.0,
    }
    assert pins.query_of(plain) == "x=-0.5&y=0.0&w=3.0"
    assert pins.query_of({**plain, "mode": "threads"}).startswith("m=threads&")
    assert pins.query_of({**plain, "family": "multibrot3"}).startswith("f=multibrot3&")
    # A phase of zero is the explorer's own default too, and a palette without one
    # is how most of the list reads.
    assert pins.query_of({**plain, "palette": "BuGn"}) == "x=-0.5&y=0.0&w=3.0&p=BuGn"
    assert "phase=" not in pins.query_of({**plain, "palette": "BuGn", "phase": 0.0})
    # A space in a map name is percent-encoded, which is what `parse` decodes.
    assert "p=Cobalt%20Furnace" in pins.query_of({**plain, "palette": "Cobalt Furnace"})


# --------------------------------------------------------------------------- #
# Matching a place.
# --------------------------------------------------------------------------- #
def test_a_place_matches_inside_a_thousandth_of_the_links_width_and_not_outside_it():
    view = pins.parse(link("x=-0.75&y=0.1&w=0.001"))
    inside = pins._row_view(row("a", x=-0.75 + 0.5e-6))
    outside = pins._row_view(row("b", x=-0.75 + 2e-6))
    assert pins.at_place(view, inside)
    assert not pins.at_place(view, outside)


def test_the_same_place_in_another_mode_or_plane_is_not_the_link():
    view = pins.parse(link("m=stripe&x=-0.75&y=0.1&w=0.001"))
    assert not pins.at_place(view, pins._row_view(row("a", mode="smooth")))
    assert not pins.at_place(view, pins._row_view(row("b", mode="stripe", kind="julia")))
    assert pins.at_place(view, pins._row_view(row("c", mode="stripe")))


def test_a_julia_place_matches_only_at_its_own_constant():
    view = pins.parse(link("f=julia&cx=-0.75&cy=0.1&x=0&y=0&w=1"))
    same = pins._row_view(row("a", kind="julia", c=(-0.75, 0.1), x=0, y=0, w=1))
    other = pins._row_view(row("b", kind="julia", c=(-0.74, 0.1), x=0, y=0, w=1))
    assert pins.at_place(view, same)
    assert not pins.at_place(view, other)


# --------------------------------------------------------------------------- #
# Choosing among rows at one place.
# --------------------------------------------------------------------------- #
def test_several_rows_at_a_place_prefer_the_links_palette_and_phase():
    view = pins.parse(link("x=-0.75&y=0.1&w=0.001&p=BuGn&phase=0.5"))
    held = [
        row("best", colormap="YlGn"),
        row("map_only", colormap="BuGn", phase=0.0),
        row("exact", colormap="BuGn", phase=0.5),
    ]
    fine = {"best": 0.9, "map_only": 0.5, "exact": 0.1}
    assert pins.choose(view, held, fine) == (held[2], pins.BY_PALETTE_AND_PHASE)
    assert pins.choose(view, held[:2], fine) == (held[1], pins.BY_PALETTE)


def test_with_no_palette_match_the_highest_fine_reading_wins():
    view = pins.parse(link("x=-0.75&y=0.1&w=0.001&p=Nothing"))
    held = [row("low", colormap="A"), row("high", colormap="B"), row("unread", colormap="C")]
    chosen, how = pins.choose(view, held, {"low": 0.2, "high": 0.7})
    assert chosen["key"] == "high"
    assert how == pins.BY_P_FINE


def test_a_lone_row_is_chosen_whatever_its_palette():
    view = pins.parse(link("x=-0.75&y=0.1&w=0.001&p=Nothing"))
    assert pins.choose(view, [row("a", colormap="A")], {}) == (
        row("a", colormap="A"),
        pins.ONLY_ROW,
    )


# --------------------------------------------------------------------------- #
# Resolving the list.
# --------------------------------------------------------------------------- #
def test_resolution_names_the_row_and_leaves_an_empty_place_unresolved():
    ledger = [row("here"), row("elsewhere", x="0.3")]
    document = pins.resolve(
        links=[link("x=-0.75&y=0.1&w=0.001"), link("x=0.9&y=0.9&w=0.001")],
        rows=ledger,
        fine={"here": 0.4},
        seatable={"here", "elsewhere"},
        log=quiet,
    )
    first, second = document["pins"]
    assert first["key"] == "here"
    assert first["status"] == "resolved"
    assert first["p_fine"] == 0.4
    assert second["key"] is None
    assert second["status"] == "unresolved"
    assert "no ledger row" in second["why"]


def test_a_row_the_pool_would_refuse_is_never_a_pin():
    """A vetoed, rejected or pictureless row at the place is not seatable, and
    pinning it would be a person's no overridden by a list."""
    document = pins.resolve(
        links=[link("x=-0.75&y=0.1&w=0.001")],
        rows=[row("vetoed")],
        fine={},
        seatable=set(),
        log=quiet,
    )
    (only,) = document["pins"]
    assert only["key"] is None
    assert "none is in the seatable pool" in only["why"]


def test_a_link_written_twice_is_one_pin(tmp_path):
    listed = tmp_path / "pins.txt"
    same = link("x=-0.75&y=0.1&w=0.001")
    listed.write_text(f"# a comment\n{same}\n\n{same}\n", encoding="utf-8")
    assert pins.read_links(listed) == [same]


def test_the_file_round_trips_through_write_and_read(tmp_path):
    document = pins.resolve(
        links=[link("x=-0.75&y=0.1&w=0.001")],
        rows=[row("here")],
        fine={},
        seatable={"here"},
        log=quiet,
    )
    path = pins.write(document, tmp_path / "pins.json")
    assert json.loads(path.read_text(encoding="utf-8")) == document
    assert b"\r\n" not in path.read_bytes()


# --------------------------------------------------------------------------- #
# What a solve reads.
# --------------------------------------------------------------------------- #
@pytest.fixture
def a_list_of_our_own(tmp_path, monkeypatch):
    """The two tracked files redirected, so the guard reads a list it wrote."""
    monkeypatch.setattr(pins, "links_path", lambda: tmp_path / "pins.txt")
    monkeypatch.setattr(pins, "resolved_path", lambda: tmp_path / "pins.json")
    return tmp_path


def test_a_list_with_no_resolution_pins_nothing_and_says_so(a_list_of_our_own):
    (a_list_of_our_own / "pins.txt").write_text(link("x=0&y=0&w=1") + "\n", encoding="utf-8")
    said = []
    assert pins.pinned(log=said.append) == ()
    assert any("NOTHING is pinned" in line for line in said)


def test_a_stale_resolution_is_still_used_and_is_called_stale(a_list_of_our_own):
    (a_list_of_our_own / "pins.txt").write_text(link("x=0&y=0&w=1") + "\n", encoding="utf-8")
    document = {"links_sha256": "something older", "pins": [{"key": "k1"}, {"key": None}]}
    (a_list_of_our_own / "pins.json").write_text(json.dumps(document), encoding="utf-8")
    said = []
    assert pins.pinned(log=said.append) == ("k1",)
    assert any("has changed" in line for line in said)
    assert any("unresolved" in line for line in said)


def test_a_solve_that_names_its_keys_reads_no_file(a_list_of_our_own):
    assert pins.keys_for(("b", "a", "b"), log=quiet) == ("b", "a")
    assert pins.keys_for((), log=quiet) == ()


def test_the_prune_keeps_every_pinned_row(a_list_of_our_own, monkeypatch):
    monkeypatch.setattr(tentative, "kept", lambda: [])
    document = {"pins": [{"key": "pinned1"}, {"key": None}]}
    (a_list_of_our_own / "pins.json").write_text(json.dumps(document), encoding="utf-8")
    assert tentative.protected_keys() == {"pinned1"}


def test_a_recorded_row_says_whether_it_was_pinned():
    seat = {"key": "k", "cells": [], "families": [], "seated_for": "pinned", "pinned": True}
    old = {"key": "j", "cells": [], "families": [], "seated_for": "general_pool"}
    rows = tentative.rows_of({"seated": [seat, old]}, centered=frozenset())
    assert [held["pinned"] for held in rows] == [True, False]
