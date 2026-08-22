"""The library's grouping: a tracked file that has to be the command's own output.

The clustering is a figure input, and a figure input nobody can regenerate is a
picture with a claim attached to it. So the file is committed *and* the command
that writes it is checked against it here — the two halves of "regenerable" that
are only worth anything together.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.palettes import clusters
from fractal_wallpapers.paths import colormap_dir


def test_the_committed_grouping_is_what_the_command_writes() -> None:
    """The whole point of the tracked file: it is not a snapshot of a run that
    happened once, it is what `palettes clusters` produces from this library."""
    pytest.importorskip("numpy")
    committed = clusters.read()
    assert committed, f"{clusters.record_path()} is missing"
    assert clusters.text_of(clusters.record()) == clusters.text_of(committed)


def test_every_map_is_in_exactly_one_cluster() -> None:
    """A partition of the library, not a sample of it. A map that fell out would
    be a map the figure silently claims does not exist."""
    rows = clusters.read()
    assert rows, f"{clusters.record_path()} is missing"
    header, *groups = rows
    assert header["kind"] == clusters.METHOD_ROW
    assert len(groups) == header["clusters"]

    seen: list[str] = []
    for group in groups:
        assert group["kind"] == clusters.CLUSTER_ROW
        assert group["size"] == len(group["members"])
        seen.extend(group["members"])
    assert sorted(seen) == clusters.library()
    assert len(seen) == len(set(seen)) == header["maps"]


def test_a_cluster_is_shown_by_members_it_actually_holds() -> None:
    """The five central names are the figure's shorthand for the group. One of
    them belonging to another group would make the shorthand a lie."""
    rows = clusters.read()
    header, *groups = rows
    for group in groups:
        assert group["central"], f"cluster {group['cluster']} has no shorthand"
        assert len(group["central"]) == min(header["central"], group["size"])
        assert set(group["central"]) <= set(group["members"])


def test_the_record_never_lands_where_a_colormap_would_be_read() -> None:
    """Every reader of the library globs `*.json` in this directory and takes the
    stem as a map name. A grouping written as `.json` would be read as a map with
    no stops by the pool, the cyclic table and this module's own `library`."""
    assert clusters.record_path().suffix != ".json"
    assert clusters.record_path().name not in [path.name for path in colormap_dir().glob("*.json")]
    assert clusters.record_path().stem not in clusters.library()


def test_ward_reproduces_a_grouping_a_hand_check_can_confirm() -> None:
    """Four points in two obvious pairs, far apart. Ward has to find the pairs —
    and it has to find them the same way twice, which is what the tracked file
    depends on."""
    numpy = pytest.importorskip("numpy")
    points = numpy.array([[0.0, 0.0], [0.0, 0.1], [10.0, 0.0], [10.0, 0.1]])
    gaps = numpy.linalg.norm(points[:, None, :] - points[None, :, :], axis=-1)
    assert clusters.ward(gaps, 2) == [[0, 1], [2, 3]]
    assert clusters.ward(gaps, 4) == [[0], [1], [2], [3]]
    assert clusters.ward(gaps, 1) == [[0, 1, 2, 3]]


def test_the_method_travels_with_the_file() -> None:
    """A reader who opens the record should not have to find the module to learn
    what made it — the number of clusters is a reading, and a reading with no
    stated method is a claim."""
    header = clusters.read()[0]
    assert "Ward" in header["method"]
    assert str(header["clusters"]) in header["method"]
    assert json.loads(json.dumps(header)) == header
