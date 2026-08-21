"""The location record: the three spellings it arrives in, and what it refuses.

Every reader of a manifest — `render --location`, `render --manifest`, `screen`,
`score-locations` and the boundary draw's own output — goes through
[`fractal_wallpapers.locations`], so what this file pins is what all five of them
accept.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers import locations

LABEL_ROW = {
    "schema": 1,
    "batch": "flat_draw_mandelbrot",
    "labeler": "matt",
    "score": 1,
    "family": {"kind": "mandelbrot"},
    "viewport": {"center_re": "-0.009", "center_im": "0.711", "width": "0.00205"},
    "render": {"resolution": [1280, 720], "supersample": 2, "mode": "smooth", "maxiter": 2000},
}

LEDGER_ROW = {
    "schema": 1,
    "kind": "candidate",
    "family": {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]},
    "viewport": {"center_re": "0.1", "center_im": "-0.2", "width": "0.5"},
    "maxiter": 13140,
    "fate": "survived",
}

RELEASE_ROW = {
    "schema": 1,
    "verdict": "released",
    "location": {
        "family": {"kind": "phoenix"},
        "viewport": {"center_re": "0.0", "center_im": "0.0", "width": "1.0"},
        "maxiter": 4000,
    },
    "recipe": {"mode": "smooth_stripe", "colormap": "magma"},
}


def test_all_three_records_this_project_writes_are_readable() -> None:
    """A label row, a walk ledger's candidate and a release decision are the same
    location written three ways, and every one of them is already on disk in this
    repository. A reader that took one of the three would send the other two back
    to being retyped, which is the whole reason nothing could take a record."""
    label = locations.record(LABEL_ROW)
    assert label["family"] == {"kind": "mandelbrot"}
    assert label["render"]["resolution"] == [1280, 720]
    assert label["render"]["maxiter"] == 2000

    ledger = locations.record(LEDGER_ROW)
    assert ledger["family"]["c"] == ["-0.4", "0.6"]
    # The cap is at the top level on a ledger row: that row records a frame the
    # gates measured, not a picture, so it has no render block to put one in.
    assert ledger["render"]["maxiter"] == 13140
    assert ledger["render"]["resolution"] == list(locations.DEFAULT_RESOLUTION)

    release = locations.record(RELEASE_ROW)
    assert release["family"] == {"kind": "phoenix"}
    assert release["viewport"]["width"] == "1.0"
    assert release["render"]["maxiter"] == 4000


def test_a_two_key_record_is_a_legal_record() -> None:
    """Family and viewport are the identity; everything else is presentation and
    defaults to what the flag nobody passed would have meant."""
    row = locations.record(
        {
            "family": {"kind": "mandelbrot"},
            "viewport": {"center_re": "-0.75", "center_im": "0.1", "width": "0.4"},
        }
    )
    assert row["render"] == {
        "resolution": list(locations.DEFAULT_RESOLUTION),
        "supersample": locations.DEFAULT_SUPERSAMPLE,
        "mode": locations.DEFAULT_MODE,
        "colormap": locations.DEFAULT_COLORMAP,
    }
    # And no cap at all, which is not the same as any particular number: absent
    # means the depth-aware policy decides, which is what an engine spec means by
    # leaving it out.
    assert "maxiter" not in row["render"]
    assert "maxiter" not in locations.spec_of(row, "x.png")


def test_coordinates_come_back_as_the_strings_they_went_in_as() -> None:
    """The decimal string is the identity of a location and `f64` is a lossy view
    of it. A reader that parsed on the way in would throw that away at the one
    point in the pipeline that still has it."""
    written = "-0.0090552453182706421828174"
    row = locations.record(
        {
            "family": {"kind": "mandelbrot"},
            "viewport": {"center_re": written, "center_im": "0", "width": "1e-9"},
        }
    )
    assert row["viewport"]["center_re"] == written
    assert locations.spec_of(row, "x.png")["viewport"]["center_re"] == written


def test_a_row_missing_half_its_identity_is_refused() -> None:
    for row, says in (
        ({"viewport": {"center_re": "0", "center_im": "0", "width": "1"}}, "no family"),
        ({"family": {"kind": "mandelbrot"}}, "no viewport"),
        (
            {
                "family": {"kind": "mandelbrot"},
                "viewport": {"center_re": "0", "center_im": "0"},
            },
            "width",
        ),
    ):
        with pytest.raises(locations.LocationError, match=says):
            locations.record(row)


def test_a_misspelled_render_key_is_refused_rather_than_ignored() -> None:
    """A `supersamples` that silently drew at the default is a picture nobody can
    tell from the one they asked for."""
    with pytest.raises(locations.LocationError, match="supersamples"):
        locations.record(
            {
                **LABEL_ROW,
                "render": {"supersamples": 4},
            }
        )


def test_a_manifest_names_the_row_that_is_not_a_location(tmp_path) -> None:
    path = tmp_path / "manifest.jsonl"
    path.write_text(
        json.dumps(LABEL_ROW) + "\n" + json.dumps({"note": "not a location"}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(locations.LocationError, match=r"manifest\.jsonl:2"):
        locations.read(path)


def test_one_location_is_read_from_an_object_or_from_a_one_row_manifest(tmp_path) -> None:
    """Both, because a record copied out of a ledger row is an object and a batch
    of one is what a one-row manifest looks like."""
    one = tmp_path / "one.json"
    one.write_text(json.dumps(LABEL_ROW), encoding="utf-8")
    assert locations.read_one(one) == locations.record(LABEL_ROW)

    many = tmp_path / "many.jsonl"
    many.write_text(json.dumps(LABEL_ROW) + "\n" + json.dumps(LEDGER_ROW) + "\n", encoding="utf-8")
    with pytest.raises(locations.LocationError, match="manifest"):
        locations.read_one(many)


def test_two_records_that_would_draw_one_picture_name_one_file() -> None:
    """The name is a digest of everything the engine is told and nothing else, so
    a batch is resumable and two spellings of one picture do not make two."""
    row = locations.record(LABEL_ROW)
    twin = locations.record({**LABEL_ROW, "batch": "something else", "score": 4})
    assert locations.name_of(row) == locations.name_of(twin)

    wider = locations.record({**LABEL_ROW, "render": {**LABEL_ROW["render"], "supersample": 4}})
    assert locations.name_of(wider) != locations.name_of(row)


def test_the_frame_a_screening_reads_carries_the_cap_and_nothing_else_about_the_render() -> None:
    """The gates read a frame at *their* geometry, so what a record says about
    resolution and coloring is not a fact about the frame being screened. The cap
    is the exception: it decides what counts as interior, which is what the first
    gate measures."""
    frame = locations.frame_of(locations.record(LABEL_ROW))
    assert frame == {
        "family": {"kind": "mandelbrot"},
        "center_re": "-0.009",
        "center_im": "0.711",
        "width": "0.00205",
        "maxiter": 2000,
    }


def test_a_written_manifest_reads_back_as_what_was_written(tmp_path) -> None:
    rows = [locations.record(LABEL_ROW), locations.record(LEDGER_ROW)]
    path = locations.write(rows, tmp_path / "out.jsonl")
    assert locations.read(path) == rows
