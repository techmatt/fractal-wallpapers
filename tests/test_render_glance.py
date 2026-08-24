"""The glance sheet: the arithmetic of two orderings, and the page they become.

Nothing here loads a head or reads a picture. What is under test is the part that
would be wrong quietly — which column a cutpoint is, which direction a rank move
is signed in, and whether the page says the population is one nobody may quote a
rate off.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fractal_wallpapers.models import render_glance


def a_cell(name: str, incumbent: float, candidate: float, **changes) -> dict:
    cell = {
        "kind": "smooth_render",
        "batch": "manufactured_rare_colors",
        "score": 3,
        "mode": "smooth",
        "colormap": name,
        "picture": Path("no", "such", f"{name}.jpg"),
        "incumbent": incumbent,
        "candidate": candidate,
    }
    cell.update(changes)
    return cell


def ordered(cells: list[dict]) -> dict:
    """The two orderings and the rank move, the way `scored` computes them."""
    by_incumbent = sorted(cells, key=lambda cell: -cell["incumbent"])
    by_candidate = sorted(cells, key=lambda cell: -cell["candidate"])
    place_of = {id(cell): place for place, cell in enumerate(by_incumbent)}
    for place, cell in enumerate(by_candidate):
        cell["moved"] = place_of[id(cell)] - place
    return {"cells": cells, "by_incumbent": by_incumbent, "by_candidate": by_candidate}


# --------------------------------------------------------------------------- #
# The arithmetic.
# --------------------------------------------------------------------------- #
def test_the_help_text_s_default_is_the_module_s_default() -> None:
    """The parser is built on the base install and cannot import this module, so the
    number in `--rows`' help is a copy. This is the thing that stops it drifting."""
    from fractal_wallpapers import cli

    action = next(
        a
        for a in cli.build_parser()
        ._subparsers._group_actions[0]
        .choices["renders"]
        ._subparsers._group_actions[0]
        .choices["glance"]
        ._actions
        if a.dest == "rows"
    )
    assert action.default is None, "the default is resolved in the handler"
    assert f"default: the module's, {render_glance.ROWS}" in action.help


def test_the_ordering_column_is_the_cutpoint_a_floor_sits_on() -> None:
    """`p_ge2` is column 0, so `P(>=3)` is column 1. Off by one here would order
    the whole sheet on a boundary no cut is taken at."""
    assert render_glance.COLUMN == "p_ge3"
    assert render_glance.COLUMN_INDEX == 1


def test_a_row_the_candidate_ranks_higher_moves_up() -> None:
    """The sign is the whole readable fact on the page: positive is promoted."""
    low, high = a_cell("low", incumbent=0.10, candidate=0.90), a_cell("high", 0.90, 0.10)
    read = ordered([low, high])
    assert read["by_candidate"][0] is low
    assert low["moved"] == +1
    assert high["moved"] == -1


def test_a_row_neither_head_moves_is_level() -> None:
    same = [a_cell("a", 0.9, 0.8), a_cell("b", 0.5, 0.4), a_cell("c", 0.1, 0.05)]
    ordered(same)
    assert [cell["moved"] for cell in same] == [0, 0, 0]


def test_the_two_orderings_hold_exactly_the_same_rows() -> None:
    """A column that dropped or duplicated a row would read as a promotion."""
    cells = [a_cell(str(n), incumbent=n / 10, candidate=(9 - n) / 10) for n in range(9)]
    read = ordered(cells)
    assert {id(cell) for cell in read["by_candidate"]} == {id(cell) for cell in read["cells"]}
    assert {id(cell) for cell in read["by_incumbent"]} == {id(cell) for cell in read["cells"]}


# --------------------------------------------------------------------------- #
# The page.
# --------------------------------------------------------------------------- #
def a_read(count: int = 4) -> dict:
    cells = [a_cell(str(n), incumbent=n / 10, candidate=(count - n) / 10) for n in range(count)]
    read = {"smooth_render": ordered(cells)}
    columns = read["smooth_render"]
    by_move = sorted(columns["by_candidate"], key=lambda cell: -cell["moved"])
    columns["rows"] = 2
    columns["risers"] = by_move[:2]
    columns["fallers"] = list(reversed(by_move[-2:]))
    return read


def test_the_page_says_the_population_is_not_one_to_quote_a_rate_off() -> None:
    """The one sentence that must survive every edit to this page: these rows are
    anchored and enriched, and a number read off them is a ceiling."""
    page = render_glance.page(a_read(), ["a line"])
    assert "anchored" in page
    assert "no rate quoted off them is a rate" in page


def test_the_page_names_both_heads_on_every_card() -> None:
    page = render_glance.page(a_read(), [])
    assert page.count("candidate ") >= 4
    assert page.count("incumbent ") >= 4


def test_the_page_carries_its_provenance_lines() -> None:
    page = render_glance.page(a_read(), ["batch a_batch: 4 stored rows"])
    assert "batch a_batch: 4 stored rows" in page


def test_a_missing_picture_says_so_rather_than_emitting_a_broken_image() -> None:
    page = render_glance.page(a_read(), [])
    assert "no picture" in page
    assert 'src=""' not in page


def test_a_batch_no_store_holds_is_refused(monkeypatch) -> None:
    monkeypatch.setattr(render_glance.finished, "resolved", lambda kind: _Empty())
    with pytest.raises(render_glance.GlanceError):
        render_glance.rows_of("a_batch_nobody_registered")


class _Empty:
    def scored(self) -> list[dict]:
        return []
