"""The readers behind a K sweep's two figures.

The drawing itself is not tested and is not meant to be — it is `scratch/` output
a person looks at. What is tested is everything a wrong bar would come from: the
order the cells go in, what a cell no rung seated reads as, and the difference
column, which is the whole of [`k_sweep_plot.DELTA`] written out as text.

`matplotlib` is not imported by any of these, and that is deliberate: it is not in
this project's dependency set, so a guard that needed it would be a guard that
skipped itself on the machine that most needs to run it.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.curation import k_sweep_plot


def sweep(*rungs) -> dict:
    """`{"rungs": [...]}` off `(k, allowance, {cell: seats})` triples."""
    return {
        "rungs": [
            {"k": k, "allowance": allowed, "cells": {"counts": dict(counts)}}
            for k, allowed, counts in rungs
        ]
    }


def test_the_cells_are_ordered_by_the_control_and_not_by_the_widest_arm():
    """Both figures share an axis, so a cell has to sit in one place in both."""
    held = sweep(
        (2.0, 42, {"a": 10, "b": 40, "c": 25}),
        (3.0, 63, {"a": 60, "b": 5, "c": 25}),
    )
    assert k_sweep_plot.cells_of(held) == ["b", "c", "a"]


def test_a_cell_only_a_looser_rung_found_sorts_last_rather_than_being_dropped():
    """It is in the union because the loosening bought it, which is worth seeing."""
    held = sweep((2.0, 42, {"a": 3}), (3.0, 63, {"a": 3, "zz": 9, "mm": 9}))
    assert k_sweep_plot.cells_of(held) == ["a", "mm", "zz"]


def test_a_cell_a_rung_never_seated_reads_as_zero_and_not_as_a_gap():
    """A missing key is a cell that got no seats; a bar of nothing is the answer."""
    held = sweep((2.0, 42, {"a": 5, "b": 1}), (3.0, 63, {"a": 7}))
    _label, _allowed, counts = k_sweep_plot.series(held, ["a", "b"])[1]
    assert counts == [7, 0]


def test_the_series_carries_each_rungs_own_allowance_and_labels_it():
    held = sweep((2.0, 42, {"a": 5}), (3.75, 79, {"a": 5}))
    assert [(label, allowed) for label, allowed, _counts in k_sweep_plot.series(held, ["a"])] == [
        ("K=2 (allowance 42)", 42),
        ("K=3.75 (allowance 79)", 79),
    ]


def test_the_table_signs_the_move_against_the_control_in_both_directions():
    """A fall has to read as a fall in the text as well as in the picture."""
    held = sweep((2.0, 42, {"up": 10, "down": 30}), (3.0, 63, {"up": 20, "down": 12}))
    rows = {line.split("\t")[0]: line.split("\t") for line in k_sweep_plot.table(held).splitlines()}
    assert rows["down"][-1] == "-18"
    assert rows["up"][-1] == "+10"
    assert rows["allowance"][1:3] == ["42", "63"]


def test_a_stamp_no_sweep_ever_wrote_is_refused_rather_than_drawn_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(k_sweep_plot.k_sweep.solve, "solve_dir", lambda name: tmp_path / str(name))
    with pytest.raises(k_sweep_plot.PlotRefused, match="no sweep tables"):
        k_sweep_plot.read("20260101T000000Z")
