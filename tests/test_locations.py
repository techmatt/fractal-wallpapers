"""The location record: the three spellings it arrives in, and what it refuses.

Every reader of a manifest — `render --location`, `render --manifest`, `screen`,
`score-locations` and the boundary draw's own output — goes through
[`fractal_wallpapers.locations`], so what this file pins is what all five of them
accept.
"""

from __future__ import annotations

import argparse
import json

import pytest

from fractal_wallpapers import locations
from fractal_wallpapers.paths import repo_root

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


# --------------------------------------------------------------------------- #
# A recipe this shape cannot carry is refused, not dropped.
# --------------------------------------------------------------------------- #
def test_a_row_whose_recipe_says_more_than_a_location_can_is_refused() -> None:
    """★ The silent failure: `render --location <release row>` drew the right
    coordinates through the default palette and exited 0.

    A location record is a place plus a geometry. A real release row also carries
    a curve, a fold, a palette pass and a levelling band, and this reader had
    nowhere to put any of them — so it dropped them, which looks exactly like
    having had nothing to drop. The picture that came out was a wallpaper nobody
    asked for wearing the name of one somebody did.
    """
    row = {
        **RELEASE_ROW,
        "recipe": {**RELEASE_ROW["recipe"], "curve": "log", "mirror": True},
    }

    with pytest.raises(locations.LocationError) as refusal:
        locations.record(row)

    said = str(refusal.value)
    assert "curve" in said and "mirror" in said
    assert "--recipe" in said, "the refusal has to name the door that does take it"


def test_the_defaults_a_candidate_path_produces_are_not_a_refusal() -> None:
    """`mirror: false` and `mode_params: {}` are what this path draws anyway, so
    a row saying so is saying nothing a render would do differently. Refusing
    them would refuse most of the pool for describing the default."""
    row = {**RELEASE_ROW, "recipe": {**RELEASE_ROW["recipe"], "mirror": False, "mode_params": {}}}

    assert locations.record(row)["render"]["mode"] == "smooth_stripe"


def test_a_recipe_this_shape_can_carry_is_read_rather_than_dropped() -> None:
    """The other half of the same defect. A release row has no top-level `render`
    block — its mode and its map are under `recipe` — so this reader saw neither
    and filled in the module's defaults, drawing every release row through
    `smooth`/`twilight_shifted` whatever it said."""
    read = locations.record(RELEASE_ROW)

    assert read["render"]["mode"] == "smooth_stripe"
    assert read["render"]["colormap"] == "magma"


def test_a_row_with_no_recipe_at_all_is_untouched() -> None:
    """The ledger row and the label row, which are most of what this reads."""
    assert locations.record(LEDGER_ROW)["render"]["mode"] == locations.DEFAULT_MODE
    assert locations.record(LABEL_ROW)["render"]["mode"] == "smooth"


# --------------------------------------------------------------------------- #
# A coloring written flat is the fourth spelling, and is read.
# --------------------------------------------------------------------------- #
def test_a_coloring_written_flat_is_read_rather_than_drawn_at_the_defaults() -> None:
    """★ The reported repro: a hand-written manifest drew somebody else's picture.

    `{family, viewport, maxiter, resolution, supersample, mode, colormap}` is what
    an operator writes when they want twelve pictures at a size and a map they
    named. Every one of those seven came back as this module's own default,
    because a flat key is not the `render` block and the unknown-key check looks
    only *inside* that block — so the coloring was neither read nor complained
    about, which is the worst pair a field can have, and the run exited 0.
    """
    read = locations.record(
        {
            "family": {"kind": "mandelbrot"},
            "viewport": {"center_re": "-0.75", "center_im": "0.1", "width": "0.4"},
            "maxiter": 4000,
            "resolution": [3840, 2160],
            "supersample": 4,
            "mode": "stripe",
            "colormap": "magma",
        }
    )
    assert read["render"] == {
        "resolution": [3840, 2160],
        "supersample": 4,
        "mode": "stripe",
        "colormap": "magma",
        "maxiter": 4000,
    }
    # And every member of it reaches the engine, which is the half a reader that
    # merely stopped raising would still have got wrong.
    spec = locations.spec_of(read, "x.png")
    assert (spec["mode"], spec["colormap"], spec["supersample"]) == ("stripe", "magma", 4)


def test_a_flat_coloring_is_read_on_either_side_of_a_nested_location() -> None:
    """The release spelling has two top levels and a member lands on either.

    One written beside `family` inside the `location` block and one written beside
    `location` are the same claim about the same picture, and a reader that looked
    at one of them would leave the other door exactly as quiet as it was.
    """
    beside = locations.record({**RELEASE_ROW, "supersample": 3})
    inside = locations.record(
        {**RELEASE_ROW, "location": {**RELEASE_ROW["location"], "supersample": 3}}
    )
    assert beside["render"]["supersample"] == inside["render"]["supersample"] == 3


def test_a_member_answered_twice_with_two_answers_is_refused() -> None:
    """Two answers about one picture, and no defensible way to pick between them.

    The same argument `refuse_two_descriptions` makes in
    [`fractal_wallpapers.cli.draw_commands`] for a record plus a flag that
    contradicts it: silently preferring either one draws a picture the row can be
    read as not having asked for.
    """
    with pytest.raises(locations.LocationError) as refusal:
        locations.record(
            {**LABEL_ROW, "mode": "stripe", "render": {**LABEL_ROW["render"], "mode": "smooth"}}
        )

    said = str(refusal.value)
    assert "mode" in said and "stripe" in said and "smooth" in said
    assert "top level" in said and "render" in said, "the reader has to know which two to compare"


def test_a_release_row_s_two_top_levels_are_compared_against_each_other() -> None:
    """Three places a member can be written, not two. A release row has a top
    level of its own besides the `location` block it nests, so a check that only
    compared flat against nested would silently keep whichever of those two it
    read last — and which one that is is an accident of the loop."""
    with pytest.raises(locations.LocationError) as refusal:
        locations.record(
            {
                **RELEASE_ROW,
                "supersample": 2,
                "location": {**RELEASE_ROW["location"], "supersample": 4},
            }
        )
    said = str(refusal.value)
    assert "supersample" in said and "2" in said and "4" in said
    assert "beside `location`" in said, "and say which of the two top levels said what"


def test_a_member_answered_twice_with_one_answer_is_not_a_quarrel() -> None:
    """A writer that repeats itself is still only saying one thing, and the corpora
    do repeat themselves. Refusing agreement would refuse rows that are perfectly
    clear about what they want."""
    row = {**LABEL_ROW, "mode": "smooth", "resolution": [1280, 720]}
    assert locations.record(row)["render"]["mode"] == "smooth"
    # A pair has one spelling in JSON and two in Python, so the comparison is by
    # value rather than by the type the member arrived as.
    assert locations.record({**row, "resolution": (1280, 720)})["render"]["resolution"] == [
        1280,
        720,
    ]


def test_a_flat_member_written_null_is_absent_rather_than_an_answer() -> None:
    """Spelling a key is not the same act as answering with it.

    A row carrying `"colormap": null` beside a block that names a map has left
    room for a field, not contradicted itself — and a check that counted the key
    would refuse it, or worse, tell it its picture came out at the default map.
    """
    row = {**LABEL_ROW, "colormap": None, "render": {**LABEL_ROW["render"], "colormap": "magma"}}
    assert locations.record(row)["render"]["colormap"] == "magma"

    # And with nothing nested to fall back on, a null is silence and the default
    # answers — which is not the same as the row having asked for the default.
    alone = {name: carried for name, carried in LABEL_ROW.items() if name != "render"}
    assert locations.record({**alone, "colormap": None})["render"]["colormap"] == (
        locations.DEFAULT_COLORMAP
    )


# --------------------------------------------------------------------------- #
# The omission guard lives at the render door, not in `record`.
# --------------------------------------------------------------------------- #
def test_a_flat_curve_is_refused_at_the_render_door_and_read_everywhere_else() -> None:
    """★ The division this module turns on.

    `refuse_a_recipe_this_cannot_carry` reads the keys inside `recipe` under their
    own names, so a corpus row's flat `curve` beside `family` went past it and the
    picture came out through the default ramp. But `screen` keeps the frame and
    the cap and `score-locations` discards the coloring entirely, so that row is a
    perfectly good input to both — refusing it in `record` would have cost the one
    documented command that sweeps those stores in order to protect a door the row
    never goes through.
    """
    row = {**LABEL_ROW, "curve": "log"}

    said = locations.refuse_a_picture_this_cannot_draw(row, "here")
    assert said is not None and "curve" in said
    assert "--recipe" in said, "the refusal has to name the door that does take it"

    # Read, all the same: the frame a screening takes and the place a score is
    # about are both still there, and neither of them is about the curve.
    assert locations.record(row)["render"]["mode"] == "smooth"
    assert locations.frame_of(locations.record(row))["maxiter"] == 2000


def test_a_recipe_that_is_a_palette_pass_is_refused_at_the_render_door() -> None:
    """The second thing the recipe check could not see. `UNCARRIED_RECIPE_MEMBERS`
    asks for a `palette` member by name, and the tracked corpora spell the seven
    knobs straight into `recipe` instead — so the whole pass read as absent and the
    picture went out through this module's own ramp having said so to nobody."""
    pass_written_out = {
        "gamma": 1.0,
        "cycles": 1.0,
        "phase": 0.0,
        "reverse": False,
        "mirror": False,
        "transfer": {"kind": "value"},
        "rolloff": {"kind": "none"},
    }
    row = {**LABEL_ROW, "recipe": pass_written_out}

    # Invisible to the older check, which is the defect: every knob but `mirror`
    # is unknown to it, and `mirror: false` is one it allows on purpose.
    assert locations.refuse_a_recipe_this_cannot_carry(row, "here") is None

    said = locations.refuse_a_picture_this_cannot_draw(row, "here")
    assert said is not None and "palette" in said
    assert locations.record(row)["render"]["mode"] == "smooth", "and still read"


def test_a_lone_mirror_is_the_older_check_s_business_and_not_a_palette_pass() -> None:
    """`mirror` is left out of `PALETTE_PASS_KNOBS` because it is a member in its
    own right: a recipe naming only `mirror` is naming a fold, and that entry
    already decides about it — and decides to allow it when it is false. Counting
    it as a pass would refuse most of the pool for describing the default."""
    assert "mirror" not in locations.PALETTE_PASS_KNOBS
    assert "mirror" in locations.UNCARRIED_RECIPE_MEMBERS

    folded = {**RELEASE_ROW, "recipe": {**RELEASE_ROW["recipe"], "mirror": True}}
    flat_ramp = {**RELEASE_ROW, "recipe": {**RELEASE_ROW["recipe"], "mirror": False}}
    assert "mirror" in (locations.refuse_a_picture_this_cannot_draw(folded, "here") or "")
    assert locations.refuse_a_picture_this_cannot_draw(flat_ramp, "here") is None


def test_the_render_door_is_asked_for_and_never_assumed(tmp_path) -> None:
    """`drawing` is off by default, which is the whole arrangement: two of this
    reader's three callers do not draw, and a default of on would have refused
    them for carrying exactly the members they throw away."""
    manifest = tmp_path / "corpus.jsonl"
    manifest.write_text(json.dumps({**LABEL_ROW, "curve": "log"}) + "\n", encoding="utf-8")

    assert locations.read(manifest)[0]["render"]["mode"] == "smooth"
    with pytest.raises(locations.LocationError, match="curve"):
        locations.read(manifest, drawing=True)


def test_a_manifest_the_render_door_refuses_is_a_message_and_an_exit_code(tmp_path) -> None:
    """`render --manifest` let the refusal out as a traceback while every other
    door on this path printed one line and returned 1. The same bad file answered
    `--location` with a complaint about the file and `--manifest` with a stack,
    which reads as a crash in the tool rather than as something to go and fix."""
    from fractal_wallpapers.cli import draw_commands

    manifest = tmp_path / "corpus.jsonl"
    manifest.write_text(json.dumps({**LABEL_ROW, "curve": "log"}) + "\n", encoding="utf-8")
    args = argparse.Namespace(
        manifest=str(manifest), limit=None, out_dir=str(tmp_path / "out"), resume=False
    )
    assert draw_commands.render_manifest(args) == 1

    # A row that is not an object at all takes the same door the same way. It
    # reached this handler as an `AttributeError` while the draw question was
    # asked ahead of the one refusal that says what a location is.
    bare = tmp_path / "bare.jsonl"
    bare.write_text('"hello"\n', encoding="utf-8")
    assert (
        draw_commands.render_manifest(argparse.Namespace(**{**vars(args), "manifest": str(bare)}))
        == 1
    )


# --------------------------------------------------------------------------- #
# The claim this module makes about the store, checked against the store.
# --------------------------------------------------------------------------- #
#: One tracked store per shape this module's docstring says it takes, and what
#: reading its first row has to produce. The point of naming files rather than
#: writing fixtures: a hand-written fixture agrees with whatever the reader does,
#: so three of them were green while every row of these stores came back through
#: the default ramp. A claim about the store is only ever checked by the store.
#:
#: `render` is what `record` must return for the first row, and `draws` is whether
#: the render door will take it — a corpus row carries a whole picture and belongs
#: at `render --recipe FILE`, while `screen` and `score-locations` read it as it
#: stands. Values are written out rather than derived from the row, because a
#: guard that recomputes what it is checking passes whatever the reader does.
TRACKED_SHAPES: dict[str, dict] = {
    # A label row: the coloring nested, which is the first spelling.
    "data/labels/rows/crawl_exemplar.jsonl": {
        "render": {
            "resolution": [1280, 720],
            "supersample": 4,
            "mode": "smooth",
            "colormap": "twilight_shifted",
            "maxiter": 5490,
        },
        "draws": True,
    },
    # A two-key record: family and viewport and nothing else, which is legal and
    # draws the family's own home framing at the standard size.
    "data/labels/eval_split.jsonl": {
        "render": {
            "resolution": list(locations.DEFAULT_RESOLUTION),
            "supersample": locations.DEFAULT_SUPERSAMPLE,
            "mode": locations.DEFAULT_MODE,
            "colormap": locations.DEFAULT_COLORMAP,
        },
        "draws": True,
    },
    # The fourth spelling, partway: the mode flat, the geometry nested.
    "data/palette_choice/candidate_sets.jsonl": {
        "render": {
            "resolution": [640, 360],
            "supersample": 2,
            "mode": "smooth",
            "colormap": locations.DEFAULT_COLORMAP,
            "maxiter": 40584,
        },
        "draws": False,
    },
    # The fourth spelling in full: mode and map flat, geometry nested, and a
    # `recipe` that is the seven-knob palette pass written out.
    "data/palette_choice/rows/mandelbrot.jsonl": {
        "render": {
            "resolution": [640, 360],
            "supersample": 2,
            "mode": "smooth",
            "colormap": "garcya.us_fantasy_wallpaper074",
            "maxiter": 8000,
        },
        "draws": False,
    },
    # The fourth spelling with no `render` block at all, which is what a score
    # row writes: the geometry defaults and the coloring comes entirely from the
    # flat keys.
    "models/render/enlarged_corpus_seed0/scores_smooth_render.jsonl": {
        "render": {
            "resolution": list(locations.DEFAULT_RESOLUTION),
            "supersample": locations.DEFAULT_SUPERSAMPLE,
            "mode": "smooth",
            "colormap": "02595_oiawindmills_2560x1600",
        },
        "draws": False,
    },
}

#: The stores above whose first row names a map this module would never have
#: defaulted to. **The line that actually catches the defect**: every other
#: assertion here would have passed against a reader that dropped the flat
#: coloring on the floor, because `smooth` is both what those rows say and what
#: this module fills in when a row says nothing. `mode` cannot do this job — no
#: tracked store has a readable first row naming a mode other than the default.
READ_AND_NOT_DEFAULTED = (
    "data/palette_choice/rows/mandelbrot.jsonl",
    "models/render/enlarged_corpus_seed0/scores_smooth_render.jsonl",
)


def first_row(store: str) -> dict:
    """The first row of one tracked store, read as a line rather than as a file.

    One row, because what is being checked is the *shape* a store writes and one
    writer wrote every row of it; and one *line*, because the largest of these is
    a few megabytes and `read_text().splitlines()[0]` would parse the whole store
    to answer a question about its head. The whole guard is five opens and five
    `json.loads`, which is why it can sit in the fast lane at all.
    """
    with (repo_root() / store).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                return json.loads(line)
    raise AssertionError(f"{store} holds no row")


@pytest.mark.parametrize("store", sorted(TRACKED_SHAPES))
def test_every_shape_the_tracked_stores_write_is_read_as_what_it_says(store) -> None:
    """★ The guard the last one should have been.

    Its predecessor asserted a claim about this repository's records using three
    hand-written fixtures, so it stayed green while tens of thousands of tracked
    rows went from readable to refused — the fixtures were written to match the
    reader rather than the store, which is a check that can only ever agree with
    itself. This reads the store.
    """
    expected = TRACKED_SHAPES[store]
    row = first_row(store)
    assert locations.record(row, store)["render"] == expected["render"]
    if store in READ_AND_NOT_DEFAULTED:
        assert expected["render"]["colormap"] != locations.DEFAULT_COLORMAP, (
            "this entry is here to prove the flat coloring was READ, and a default "
            "map in it proves nothing — the reader that dropped the key agreed too"
        )


@pytest.mark.parametrize("store", sorted(TRACKED_SHAPES))
def test_the_render_door_takes_the_places_and_sends_the_pictures_to_recipe(store) -> None:
    """The other half of the division, also against the store. A row that carries
    a curve or a palette pass is a picture and goes to `render --recipe FILE`; a
    row that carries a place and a geometry is drawn. Both are read either way,
    which is what `screen` and `score-locations` depend on."""
    row = first_row(store)
    complaint = locations.refuse_a_picture_this_cannot_draw(row, store)
    assert (complaint is None) is TRACKED_SHAPES[store]["draws"], complaint
    assert locations.record(row, store), "and every one of them is still read"


def test_the_stores_held_to_a_non_default_map_are_stores_this_file_reads() -> None:
    """A name misspelled in `READ_AND_NOT_DEFAULTED` is a name the membership test
    above never matches, so the one assertion that can tell reading from
    defaulting would stop running and nothing would go red."""
    assert set(READ_AND_NOT_DEFAULTED) <= set(TRACKED_SHAPES)


def test_a_release_store_row_is_refused_at_the_shared_reader_and_not_only_at_the_door() -> None:
    """Why no tracked store above is the release spelling: every one of them
    carries a curve inside `recipe`, which `refuse_a_recipe_this_cannot_carry` has
    refused since it was written. `RELEASE_ROW` above is the readable shape of it.
    Pinned so that a session widening the flat reading knows this is old behaviour
    it is looking at rather than something it just broke.

    The render door refuses it too, and on more members — the name used to say it
    did not, which was false in the one direction that matters: a reader who
    believed it would think the door was the only thing standing between a release
    row and a render, when the shared reader has turned it away all along."""
    row = first_row("data/curation/release/gallery3/mandelbrot.jsonl")
    assert "curve" in row["recipe"]
    with pytest.raises(locations.LocationError, match="curve"):
        locations.record(row)
    assert locations.refuse_a_picture_this_cannot_draw(row, "x") is not None
