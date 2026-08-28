"""The engine build's fingerprint, the stamp beside a view, and the amendment.

The half that needs pixels is marked: CI lints and tests before it compiles the
crate, so a probe render skips rather than fails when the engine is absent.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers import engine, engine_fingerprint
from fractal_wallpapers.curation import amend, intake
from fractal_wallpapers.models import location_view, renders, tiles

try:
    ENGINE = engine.engine_path()
except FileNotFoundError:
    ENGINE = None

needs_engine = pytest.mark.skipif(ENGINE is None, reason="the engine is not built")


@pytest.fixture(autouse=True)
def _fresh_manifests():
    """Each case gets its own directories, so no held manifest may leak between them."""
    engine_fingerprint.forget()
    yield
    engine_fingerprint.forget()


# --------------------------------------------------------------------------- #
# The probe set is pinned.
# --------------------------------------------------------------------------- #
def test_the_probe_set_spans_the_families_and_modes_a_change_can_hide_in() -> None:
    """The whole value of the fingerprint is coverage.

    The escape loop is written out per family *and per channel set*, so a probe
    set that drew one mode on one plane would miss a specialization that moved.
    Pinned as a shape rather than as a list of names: adding a probe is fine and
    dropping to one family is the regression.
    """
    kinds = {probe["family"]["kind"] for probe in engine_fingerprint.PROBES}
    modes = {probe["mode"] for probe in engine_fingerprint.PROBES}
    assert kinds == {"mandelbrot", "multibrot", "julia", "phoenix"}
    assert len(modes) >= 6
    # Both planes, and the mode whose address opens differently on each.
    assert "itinerary" in modes
    assert kinds & engine.DYNAMICAL_KINDS and kinds & engine.PARAMETER_KINDS


def test_every_probe_is_written_out_whole() -> None:
    """No probe leaves a rendering parameter for the engine to decide.

    A probe that asked the engine for its own iteration cap would fold the cap
    policy — which `discovery.identity` checks by a different mechanism — into the
    same number as the pixel arithmetic, and neither would be answerable from it.
    """
    for probe in engine_fingerprint.PROBES:
        assert isinstance(probe["maxiter"], int) and probe["maxiter"] > 0
        assert set(probe["viewport"]) == {"center_re", "center_im", "width"}
        assert all(isinstance(value, str) for value in probe["viewport"].values())


def test_a_probe_becomes_a_spec_through_the_production_path() -> None:
    """The fingerprint is a fingerprint of what production draws, or it is nothing."""
    spec = renders.spec_of(engine_fingerprint.probe_row(engine_fingerprint.PROBES[0]), "x")
    assert spec["resolution"] == list(engine_fingerprint.RESOLUTION)
    assert spec["supersample"] == engine_fingerprint.SUPERSAMPLE
    assert spec["colormap"] == engine_fingerprint.COLORMAP


@pytest.mark.slow
@needs_engine
def test_the_fingerprint_is_stable_and_short() -> None:
    first = engine_fingerprint.current()
    assert len(first) == engine_fingerprint.LENGTH
    assert first != engine_fingerprint.UNKNOWN
    assert first == engine_fingerprint.current()


@pytest.mark.slow
@needs_engine
def test_the_fingerprint_moves_when_a_probe_moves(monkeypatch) -> None:
    """A different probe set is a different number, which is what makes it a digest.

    Stands in for "a different engine": the only other way to move the output is
    to build another binary, which a test cannot do. A probe is *dropped* rather
    than nudged, because the digest is over the (probe, bytes) pairs and dropping
    one is the case that has to move even where two neighbouring parameters draw
    the same picture — which they do: `maxiter` 2000 and 2001 hash the same on
    the first probe.
    """
    was = engine_fingerprint.current()
    monkeypatch.setattr(engine_fingerprint, "PROBES", engine_fingerprint.PROBES[:-1])
    engine_fingerprint.current.cache_clear()
    engine_fingerprint._of.cache_clear()
    try:
        assert engine_fingerprint.current() != was
    finally:
        engine_fingerprint.current.cache_clear()
        engine_fingerprint._of.cache_clear()


# --------------------------------------------------------------------------- #
# The stamp beside the picture.
# --------------------------------------------------------------------------- #
def test_a_view_nothing_stamped_is_drawn_by_an_unknown_build(tmp_path) -> None:
    marks = engine_fingerprint.Stamps(tmp_path, "abc123")
    assert marks.drawn_by("anything.jpg") == engine_fingerprint.UNKNOWN
    assert not marks.is_current("anything.jpg")


def test_a_stamp_is_appended_and_read_back(tmp_path) -> None:
    marks = engine_fingerprint.Stamps(tmp_path, "abc123")
    marks.record("one.jpg", "two.jpg")
    assert engine_fingerprint.Stamps(tmp_path, "abc123").is_current("one.jpg")
    assert engine_fingerprint.Stamps(tmp_path, "def456").drawn_by("two.jpg") == "abc123"


def test_a_re_stamp_appends_and_the_last_row_wins(tmp_path) -> None:
    """Appended, never rewritten: a refresh killed halfway recorded what it finished."""
    engine_fingerprint.Stamps(tmp_path, "old").record("one.jpg")
    engine_fingerprint.Stamps(tmp_path, "new").record("one.jpg")
    lines = (tmp_path / engine_fingerprint.STAMPS_NAME).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert engine_fingerprint.read(tmp_path / engine_fingerprint.STAMPS_NAME)["one.jpg"] == "new"


def test_a_stamp_manifest_of_another_schema_is_refused(tmp_path) -> None:
    path = tmp_path / engine_fingerprint.STAMPS_NAME
    path.write_text(json.dumps({"schema": 99, "view": "a.jpg", "engine": "x"}) + "\n", "utf-8")
    with pytest.raises(engine_fingerprint.FingerprintError):
        engine_fingerprint.read(path)


# --------------------------------------------------------------------------- #
# A stale view is re-rendered rather than scored.
# --------------------------------------------------------------------------- #
def a_location() -> dict:
    return {
        "family": {"kind": "mandelbrot"},
        "viewport": {"center_re": "-0.75", "center_im": "0.1", "width": "0.05"},
        "maxiter": 800,
    }


@pytest.mark.slow
@needs_engine
def test_a_view_no_stamp_claims_is_re_rendered(tmp_path) -> None:
    """The file is there, the digest is right, and it is drawn again anyway.

    This is the whole fix. The digest a view is named by covers the recipe, and
    the build that carried the recipe out is not in the recipe — so a file at the
    right name is not evidence that today's engine made it.
    """
    row, colormap, cyclic = a_location(), "twilight_shifted", {"twilight_shifted"}
    regime = tiles.NODE_REGIME
    picture, made = location_view.render_view(row, colormap, cyclic, tmp_path, regime)
    assert made and picture.is_file()

    # It was stamped on the way out, so a second ask is a cache hit.
    again, made_again = location_view.render_view(row, colormap, cyclic, tmp_path, regime)
    assert again == picture and not made_again

    # Take the stamp away — which is exactly what every view drawn before the
    # stamp existed looks like — and the same call renders it again.
    engine_fingerprint.forget()
    (tmp_path / engine_fingerprint.STAMPS_NAME).unlink()
    _, made_third = location_view.render_view(row, colormap, cyclic, tmp_path, regime)
    assert made_third


@pytest.mark.slow
@needs_engine
def test_a_gate_render_no_stamp_claims_is_not_offered_to_the_head(tmp_path) -> None:
    """`intake.gate_render` refuses a picture whose build nobody wrote down.

    A walk's own frame is the right place at the right size — and drawn by
    whatever binary was current that night. Refusing it costs one render; taking
    it costs a seating decision nobody can audit afterwards.
    """
    colormap, cyclic, regime = "twilight_shifted", {"twilight_shifted"}, tiles.NODE_REGIME
    views = tmp_path / "run" / "views"
    views.mkdir(parents=True)
    row = {**a_location(), "_ledger": str(tmp_path / "run" / "walk.jsonl"), "image": "node1_c3.jpg"}
    row["score_view"] = intake.view_name(row, colormap, cyclic, regime)
    (views / "node1_c3.jpg").write_bytes(b"a picture some build drew")

    assert intake.gate_render(row, colormap, cyclic, regime) is None
    engine_fingerprint.stamps(views).record("node1_c3.jpg")
    assert intake.gate_render(row, colormap, cyclic, regime) == views / "node1_c3.jpg"


# --------------------------------------------------------------------------- #
# The amendment.
# --------------------------------------------------------------------------- #
def amendment_row(key: str, engine_mark: str, **overrides) -> dict:
    row = {
        "schema": amend.SCHEMA,
        "key": key,
        "engine": engine_mark,
        "was_engine": engine_fingerprint.UNKNOWN,
        "was_regime": "640x360ss2",
        "was_view": "gone.jpg",
        "was_p_ge3": 0.9,
        "was_p_ge4": 0.8,
        "stale": "regime",
        "head": "location",
        "head_sha256": "f8f8",
        "regime": "384x216ss1",
        "view": "fresh.jpg",
        "p_ge2": 0.5,
        "p_ge3": 0.2,
        "p_ge4": 0.1,
    }
    return {**row, **overrides}


def test_an_amendment_is_keyed_by_location_and_engine(tmp_path) -> None:
    """Two builds' readings of one place are two rows and neither hides the other."""
    where = tmp_path / amend.AMENDMENTS_NAME
    amend.append([amendment_row("k", "aaa"), amendment_row("k", "bbb", p_ge4=0.4)], where)
    assert amend.read("aaa", where)["k"]["p_ge4"] == 0.1
    assert amend.read("bbb", where)["k"]["p_ge4"] == 0.4
    assert amend.read("ccc", where) == {}


def test_the_amendment_carries_what_the_old_view_was_drawn_under(tmp_path) -> None:
    where = tmp_path / amend.AMENDMENTS_NAME
    amend.append([amendment_row("k", "aaa")], where)
    kept = amend.read("aaa", where)["k"]
    assert kept["was_engine"] == engine_fingerprint.UNKNOWN
    assert (kept["was_p_ge3"], kept["was_p_ge4"]) == (0.9, 0.8)


def test_the_overlay_replaces_the_reading_and_says_what_it_was() -> None:
    standing = {
        "k": {
            "key": "k",
            "regime": "640x360ss2",
            "view": "gone.jpg",
            "p_ge3": 0.9,
            "p_ge4": 0.8,
            "partition": "mandelbrot",
        }
    }
    out = amend.overlay(standing, {"k": amendment_row("k", "aaa")})
    assert (out["k"]["p_ge3"], out["k"]["p_ge4"]) == (0.2, 0.1)
    assert out["k"]["view"] == "fresh.jpg" and out["k"]["regime"] == "384x216ss1"
    assert out["k"]["amended"]["was_p_ge4"] == 0.8
    # Everything the readers join on survives, because a reader that had to learn
    # a second shape is a reader that will not.
    assert out["k"]["partition"] == "mandelbrot"


def test_an_amendment_for_a_location_the_sidecar_does_not_hold_is_ignored() -> None:
    assert amend.overlay({}, {"k": amendment_row("k", "aaa")}) == {}


def test_staleness_names_the_three_ways_a_standing_score_stops_describing_a_picture() -> None:
    class Marks:
        def __init__(self, current):
            self.current = current

        def is_current(self, _name):
            return self.current

    regime = tiles.NODE_REGIME
    current = {"regime": regime.spelled, "view": "want.jpg"}
    assert amend.staleness({"regime": "640x360ss2"}, "want.jpg", regime, Marks(True)) == "regime"
    assert (
        amend.staleness({**current, "view": "node1_c3.jpg"}, "want.jpg", regime, Marks(True))
        == "picture"
    )
    assert amend.staleness(current, "want.jpg", regime, Marks(False)) == "engine"
    assert amend.staleness(current, "want.jpg", regime, Marks(True)) is None


def test_the_wanted_view_is_a_file_name_and_not_a_bare_digest() -> None:
    """The sidecar records a file name. Comparing it with the digest alone called
    every row in the supply stale, which is how this was found."""
    name = amend.wanted_view(
        a_location(), "twilight_shifted", {"twilight_shifted"}, tiles.NODE_REGIME
    )
    assert name.endswith(".jpg")


# --------------------------------------------------------------------------- #
# The amendment wins at every read site.
# --------------------------------------------------------------------------- #
@pytest.fixture
def amended_supply(tmp_path, monkeypatch):
    """A two-location sidecar with an amendment that reverses which one is better.

    Reversed on purpose. A read site that merely *reports* the amended number
    would pass a test where the order is unchanged; every site listed below picks
    or cuts, so the check that means anything is that the pick moves.
    """
    sidecar = tmp_path / "supply_scores.jsonl"
    standing = [
        {
            "schema": intake.SCHEMA,
            "key": "high",
            "partition": "mandelbrot",
            "family": {"kind": "mandelbrot"},
            "viewport": {"center_re": "-0.5", "center_im": "0", "width": "0.5"},
            "maxiter": 500,
            "regime": "640x360ss2",
            "view": "gone.jpg",
            "p_ge2": 0.99,
            "p_ge3": 0.95,
            "p_ge4": 0.90,
        },
        {
            "schema": intake.SCHEMA,
            "key": "low",
            "partition": "mandelbrot",
            "family": {"kind": "mandelbrot"},
            "viewport": {"center_re": "-0.6", "center_im": "0", "width": "0.5"},
            "maxiter": 500,
            "regime": "384x216ss1",
            "view": "here.jpg",
            "p_ge2": 0.5,
            "p_ge3": 0.30,
            "p_ge4": 0.20,
        },
    ]
    sidecar.write_text(
        "".join(json.dumps(row) + "\n" for row in standing), encoding="utf-8", newline="\n"
    )
    amendments = tmp_path / amend.AMENDMENTS_NAME
    amend.append(
        [
            amendment_row(
                "high", "eng", p_ge2=0.10, p_ge3=0.01, p_ge4=0.005, was_p_ge3=0.95, was_p_ge4=0.90
            )
        ],
        amendments,
    )
    monkeypatch.setattr(intake, "scores_path", lambda: sidecar)
    monkeypatch.setattr(amend, "path", lambda: amendments)
    monkeypatch.setattr(engine_fingerprint, "current", lambda: "eng")
    return standing


def test_the_sidecar_itself_is_never_edited(amended_supply, tmp_path) -> None:
    """The record of what the seating was actually decided on survives the fix."""
    intake.read_scores()
    raw = intake.stored_scores()
    assert [row["p_ge4"] for row in raw] == [0.90, 0.20]
    assert [row["view"] for row in raw] == ["gone.jpg", "here.jpg"]


def test_read_scores_prefers_the_amendment(amended_supply) -> None:
    scores = intake.read_scores()
    assert scores["high"]["p_ge4"] == 0.005
    assert scores["high"]["amended"]["was_p_ge4"] == 0.90
    # A location with no amendment is untouched and carries no `amended` block.
    assert scores["low"]["p_ge4"] == 0.20 and "amended" not in scores["low"]


def test_the_un_amended_read_is_available_for_the_measurement(amended_supply) -> None:
    assert intake.read_scores(amended=False)["high"]["p_ge4"] == 0.90


def test_the_admission_cut_drops_a_location_the_amendment_calls_junk(amended_supply) -> None:
    """The cut every leg that draws from the embedding store reads through.

    Two readers of the amendment used to be pinned beside this one — the retired
    gallery pass's quality sort and its slot guarantee — and both went with that
    pass on 2026-08-28. The cut moved to [`embeddings.admitted_only`], where the
    hunt reaches it, and this follows it there rather than being deleted with the
    seating: it is the reader that can spend renders on a place the supply phase
    has already withdrawn.
    """
    import numpy

    from fractal_wallpapers.curation import embeddings, floors

    assert not floors.passes_junk_floor(0.01)
    rows = [{"key": "high", "partition": "mandelbrot"}, {"key": "low", "partition": "mandelbrot"}]
    matrix = numpy.eye(2, dtype=numpy.float32)
    kept, _matrix, dropped = embeddings.admitted_only(
        rows, matrix, intake.read_scores(), log=lambda _line: None
    )
    assert dropped == 1 and [row["key"] for row in kept] == ["low"]


def test_the_embedding_denominator_reads_the_amendment(amended_supply) -> None:
    from fractal_wallpapers.curation import embeddings

    assert [row["key"] for row in embeddings.admitted()] == ["low"]


def test_the_manufacture_extension_reads_the_amendment(amended_supply) -> None:
    from fractal_wallpapers.curation import manufacture

    assert [row["key"] for row in manufacture.admitted_locations(set())] == ["low"]


def test_the_ranked_offer_reads_the_amendment(amended_supply, monkeypatch) -> None:
    """`curate plan` and `curate run` both rank through `intake.ranked`."""
    survivors = [
        {
            "family": {"kind": "mandelbrot"},
            "viewport": {"center_re": "-0.5", "center_im": "0", "width": "0.5"},
            "maxiter": 500,
        }
    ]
    monkeypatch.setattr(intake, "gate_survivors", lambda _paths=None: (survivors, {}))
    monkeypatch.setattr(intake, "_key_text", lambda _row: "high")
    monkeypatch.setattr(intake, "partition_of_row", lambda _row: "mandelbrot")
    offer, _diagnostics = intake.ranked(["a"])
    # Amended to 0.01, which is under the junk floor, so it is not offered at all.
    assert offer.get("mandelbrot", []) == []


# --------------------------------------------------------------------------- #
# The build joins the identity chain.
# --------------------------------------------------------------------------- #
def test_the_identity_record_names_the_build(monkeypatch) -> None:
    from fractal_wallpapers.discovery import identity

    monkeypatch.setattr(engine_fingerprint, "current", lambda: "aaaabbbbccccdddd")
    assert identity._engine() == "aaaabbbbccccdddd"


def test_an_engine_that_cannot_be_named_breaks_the_identity(monkeypatch) -> None:
    """A run that cannot say which program drew its pictures cannot claim the
    identity those pictures are scored under."""
    from fractal_wallpapers.discovery import identity

    def refuse():
        raise engine_fingerprint.FingerprintError("no binary")

    monkeypatch.setattr(engine_fingerprint, "current", refuse)
    with pytest.raises(identity.IdentityBroken):
        identity._engine()
