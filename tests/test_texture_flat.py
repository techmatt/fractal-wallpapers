"""A modulate whose texture said nothing routes as smooth, everywhere.

The engine's half of this is proved in the engine, by
`coloring::tests::a_flat_texture_is_reported_and_makes_the_base_spent_by_rank`:
a texture at one value everywhere is reported flat and the pixels it produces
**are** `shade` at `Transfer::Rank`, compared as bits rather than as a
similarity. It has to be there rather than here, because the claim is about
colours a Python test would have to spend a render to see.

Everything below is the other half, and none of it renders: the flag's journey
from the engine's report to the ledger row, and every reader that takes a mode or
a kind off that row. It is arithmetic and a stubbed engine, so it is fast-lane.

**The register is stubbed in every test that needs one.** The tracked one is a
measurement over this repository's own stores, and a guard that read it would be
asserting today's ledger rather than the rule — and would go red the day a new
identity was measured.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.coloring import texture_flat
from fractal_wallpapers.curation import budget, candidate_ledger, colorize, hunt, mode_policy
from fractal_wallpapers.labeling import finished

#: The production modes whose coloring has a texture layer that can be flat.
#: `MODULATE` is the one every test below is written against; `TAIL_MODULATE` is
#: the second, and it is here to hold the rule to being about the *shape* rather
#: than about a name — see `test_the_rule_is_about_the_modulate_shape_and_not_a_name`.
MODULATE = "itinerary"
TAIL_MODULATE = "tail_itinerary"


# --------------------------------------------------------------------------- #
# The rule, in one function.
# --------------------------------------------------------------------------- #
def test_a_flat_texture_routes_as_smooth_and_nothing_else_moves():
    assert mode_policy.routed_mode(MODULATE, texture_flat=True) == colorize.SMOOTH_MODE
    assert mode_policy.routed_mode(MODULATE, texture_flat=False) == MODULATE
    assert mode_policy.routed_mode(MODULATE) == MODULATE, "the default is the mode as drawn"
    for mode in ("smooth", "stripe", "direct_trap_lines"):
        assert mode_policy.routed_mode(mode, texture_flat=False) == mode


def test_the_row_form_of_the_rule_reads_a_missing_flag_as_not_flat():
    """Every row written before the flag existed carries no `texture_flat`, and
    reading one as flat would re-route the whole store on an absence."""
    drawn = {"recipe": {"mode": MODULATE}}
    assert mode_policy.routed_mode_of(drawn) == MODULATE
    assert mode_policy.routed_mode_of({**drawn, "texture_flat": False}) == MODULATE
    assert mode_policy.routed_mode_of({**drawn, "texture_flat": True}) == colorize.SMOOTH_MODE


def test_the_rule_is_about_the_modulate_shape_and_not_a_name():
    """A second modulate arrived and nothing here was written for it.

    `routed_mode` names no mode, so `tail_itinerary` routes by the same sentence
    `itinerary` does — a degenerate tail address is the smooth base spent by rank,
    bit for bit, for exactly the reason a degenerate head one is. This is the
    guard that would go red the day the rule acquired a name.
    """
    assert texture_flat.has_a_texture(TAIL_MODULATE)
    assert mode_policy.routed_mode(TAIL_MODULATE, texture_flat=True) == colorize.SMOOTH_MODE
    assert mode_policy.routed_mode(TAIL_MODULATE, texture_flat=False) == TAIL_MODULATE
    assert mode_policy.routed_mode(TAIL_MODULATE) == TAIL_MODULATE

    drawn = {"recipe": {"mode": TAIL_MODULATE}}
    assert mode_policy.routed_mode_of(drawn) == TAIL_MODULATE
    assert mode_policy.routed_mode_of({**drawn, "texture_flat": True}) == colorize.SMOOTH_MODE


def test_only_a_modulate_can_have_a_flat_texture():
    """A composite has two layers too, and a flat one there is a weaker picture
    rather than an exact spelling of another mode. Only the modulate degenerates."""
    assert texture_flat.has_a_texture(MODULATE)
    for mode in ("smooth", "smooth_stripe", "threads", "direct_trap_ring"):
        assert not texture_flat.has_a_texture(mode), mode
    assert not texture_flat.has_a_texture("no_such_mode")


# --------------------------------------------------------------------------- #
# The engine's report reaching Python at all.
# --------------------------------------------------------------------------- #
def _stub_engine(monkeypatch, report: dict):
    """An engine that writes bytes and reports what the test says it reported."""
    from pathlib import Path

    from fractal_wallpapers.models import renders

    def run(subcommand, spec=None, log=None):
        Path(spec["output"]).parent.mkdir(parents=True, exist_ok=True)
        Path(spec["output"]).write_bytes(b"render")
        return {"output": spec["output"], **report}

    monkeypatch.setattr(colorize.engine, "run", run)
    monkeypatch.setattr(
        renders, "spec_of", lambda recipe, output: {"output": str(output), "recipe": recipe}
    )
    monkeypatch.setattr(colorize, "render_row", lambda *a, **k: {"recipe": {"mirror": False}})
    monkeypatch.setattr(colorize, "kind_of", lambda mode: "direct")


ROW = {"family": {"kind": "mandelbrot"}, "viewport": {}, "maxiter": 100}


@pytest.mark.parametrize("flat", [True, False])
def test_the_engine_s_report_reaches_the_caller_instead_of_the_floor(tmp_path, monkeypatch, flat):
    """The whole of the plumbing: `colorize.render` used to parse the engine's
    report and drop it, so a fact the engine had already computed could not be
    written down by anything downstream."""
    _stub_engine(monkeypatch, {"texture_flat": flat, "interior_fraction": 0.25})
    reported: dict = {}
    colorize.render(ROW, MODULATE, "x", set(), tmp_path / "a.jpg", reported=reported)
    assert reported["texture_flat"] is flat
    assert reported["interior_fraction"] == 0.25


def test_a_caller_that_wants_nothing_reported_is_unchanged(tmp_path, monkeypatch):
    """`reported` is optional in the same way `meter` is, and the two callers that
    do not pass one must not pay for it or notice it."""
    _stub_engine(monkeypatch, {"texture_flat": True})
    picture, stamp = colorize.render(ROW, MODULATE, "x", set(), tmp_path / "a.jpg")
    assert picture.is_file() and stamp is None


def test_a_recoloured_candidate_reports_nothing_and_that_is_not_a_gap(tmp_path, monkeypatch):
    """A dumped field is re-coloured in this process, so there is no engine to
    report. It cannot happen for a mode with a texture — `shareable` is false for
    every one of them — and a report that came back empty must read as absent
    rather than as `False` measured."""
    _stub_engine(monkeypatch, {"texture_flat": True})
    output = tmp_path / "b.jpg"
    monkeypatch.setattr(colorize, "_shared_field", lambda *a, **k: object())
    monkeypatch.setattr(
        colorize, "recolored", lambda *a, **k: colorize.writing_path(output).touch()
    )
    reported: dict = {}
    colorize.render(ROW, "smooth", "x", set(), output, reported=reported)
    assert reported == {}
    assert not texture_flat.has_a_texture("smooth"), "a shareable mode has no texture anyway"


# --------------------------------------------------------------------------- #
# The row.
# --------------------------------------------------------------------------- #
def _recipe(mode=MODULATE):
    from fractal_wallpapers.curation import recipes, release

    return recipes.Recipe(
        family={"kind": "mandelbrot"},
        viewport={"center_re": "0", "center_im": "0", "width": "3"},
        maxiter=500,
        regime=release.Regime((640, 360), 2),
        mode=mode,
        mode_params={},
        curve="linear",
        colormap="viridis",
        palette=finished.recipe(mirror=False),
        autolevel=None,
        palette_group="map:viridis",
    )


@pytest.mark.parametrize("flat", [True, False])
def test_the_ledger_row_carries_the_flag_as_a_bare_boolean(flat):
    """`at_candidate_regime`'s shape, and for `at_candidate_regime`'s reason: it
    is a bare boolean nothing can re-derive from the row. Re-deriving this one
    would cost a render."""
    stored = candidate_ledger.row(recipe=_recipe(), key="k", source={}, texture_flat=flat)
    assert stored["texture_flat"] is flat
    assert json.loads(json.dumps(stored))["texture_flat"] is flat


def test_a_row_built_without_the_flag_is_not_flat():
    assert candidate_ledger.row(recipe=_recipe(), key="k", source={})["texture_flat"] is False


# --------------------------------------------------------------------------- #
# Every reader that takes a mode or a kind.
# --------------------------------------------------------------------------- #
def test_the_label_store_router_sends_a_flat_modulate_to_the_smooth_judge():
    assert hunt.kind_of(MODULATE) == budget.STRANGE
    assert hunt.kind_of(MODULATE, texture_flat=True) == budget.SMOOTH
    assert hunt.kind_of(colorize.SMOOTH_MODE) == budget.SMOOTH
    assert finished.routed_to(MODULATE) == "strange_render"
    assert finished.routed_to(MODULATE, texture_flat=True) == "smooth_render"


def _register(monkeypatch, entries: dict):
    """Stand up a register without touching the tracked one."""
    monkeypatch.setattr(texture_flat, "_REGISTER", dict(entries))


def _label_row(mode=MODULATE):
    return {
        "schema": finished.SCHEMA,
        "batch": "a_batch",
        "recorded_at": "2026-08-31T00:00:00",
        "origin": "human",
        "score": 3,
        "family": {"kind": "mandelbrot"},
        "viewport": {"center_re": "0", "center_im": "0", "width": "3"},
        "mode": mode,
        "mode_params": {},
        "curve": "linear",
        "colormap": "viridis",
        "recipe": finished.recipe(mirror=True),
        "render": {"resolution": [1280, 720], "supersample": 2, "maxiter": 500},
        "partition": "mandelbrot",
    }


def test_a_labelled_row_routes_on_the_register_and_the_store_refuses_to_take_it(monkeypatch):
    """The reader-side re-attribution the label law asks for: the row on disk is
    never rewritten, and the store it belongs to is decided at every read."""
    row = _label_row()
    _register(monkeypatch, {})
    assert finished.routes_to(row) == "strange_render"
    assert finished.check("strange_render", row) is row

    _register(monkeypatch, {texture_flat.field_key(row): True})
    assert finished.routes_to(row) == "smooth_render"
    with pytest.raises(finished.FinishedError, match="smooth_render"):
        finished.check("strange_render", row)
    assert finished.check("smooth_render", row) is row


def test_a_mode_with_no_texture_never_reaches_the_register(monkeypatch):
    """`flat_for` asks the catalog first, so sixteen of the seventeen production
    modes cost no lookup and cannot be re-routed by a stray register row."""
    row = _label_row(mode="smooth")
    _register(monkeypatch, {texture_flat.field_key(row): True})
    assert texture_flat.flat_for(row) is False
    assert finished.routes_to(row) == "smooth_render"


@pytest.fixture(autouse=True)
def artifacts_on_disk(tmp_path, monkeypatch):
    """A hot root these fixtures can plant a picture in. [`test_solve`]'s fixture,
    for its reason: `solve.pool` refuses a row whose named picture is not on disk,
    so a fixture that only names a path is a fixture the pool drops."""
    from fractal_wallpapers import paths

    root = tmp_path / "artifacts"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(root))


def _ledger_row(key, *, mode=MODULATE, flat=False):
    from fractal_wallpapers import paths

    made = paths.hot_root() / f"{key}.jpg"
    made.parent.mkdir(parents=True, exist_ok=True)
    made.touch()
    return {
        "key": key,
        "partition": "mandelbrot",
        "location": {"key": f"place-{key}"},
        "recipe": {"mode": mode, "palette_group": "map:one"},
        "at_candidate_regime": True,
        "texture_flat": flat,
        "colour": {"cells": ["dark_vivid_blue"], "families": ["blue"]},
        "picture": f"artifacts/{key}.jpg",
        "rejected": None,
    }


def _score(key):
    return {
        "recipe_key": key,
        "p_ge4": 0.9,
        "p_ge3": 0.99,
        "head": "smooth_render",
        "judge_artifact": "judge-under-test",
    }


def test_the_seating_pool_counts_a_flat_modulate_as_smooth():
    """`solve.pool` is where a ledger row's mode becomes the seating pool's, and
    the per-mode bars, the mode floors and the seated census all read it off
    there — so routing it here is what routes it everywhere downstream."""
    from fractal_wallpapers.curation import solve

    rows = [_ledger_row("a", flat=True), _ledger_row("b", flat=False)]
    candidates, refused = solve.pool(
        rows=rows,
        scores=[_score("a"), _score("b")],
        artifact="judge-under-test",
        log=lambda *_: None,
    )
    by_key = {c.key: c.mode for c in candidates}
    assert by_key == {"a": colorize.SMOOTH_MODE, "b": MODULATE}
    assert not refused["niche_mode"]


def test_the_per_mode_bars_follow_the_pool():
    """[`headroom.bars`] keys on `candidate.mode`, so it takes the routing from
    the pool rather than from a second reading of the ledger."""
    from fractal_wallpapers.curation import headroom, solve

    rows = [_ledger_row(str(at), flat=at % 2 == 0) for at in range(6)]
    candidates, _ = solve.pool(
        rows=rows,
        scores=[_score(str(at)) for at in range(6)],
        artifact="judge-under-test",
        log=lambda *_: None,
    )
    table = headroom.bars(candidates)
    assert table["modes"][colorize.SMOOTH_MODE]["rows"] == 3
    assert table["modes"][MODULATE]["rows"] == 3
    assert len(headroom.clearing(candidates, table)) == 6


def test_the_census_counts_a_flat_modulate_as_smooth(monkeypatch):
    """A census that counted it as `itinerary` would report a fill the gallery
    cannot spend: three of those rows are the same picture `smooth` makes."""
    rows = [
        {**_ledger_row("a", flat=True), "provenance": {}},
        {**_ledger_row("b", flat=False), "provenance": {}},
        {**_ledger_row("c", mode="smooth"), "provenance": {}},
    ]
    monkeypatch.setattr(candidate_ledger.inventory, "feasibility", lambda *a, **k: {})
    taken = candidate_ledger.census(rows=rows, log=lambda *_: None)
    assert taken["modes"]["recipes"][colorize.SMOOTH_MODE] == 2
    assert taken["modes"]["recipes"][MODULATE] == 1
    assert taken["population"]["texture_flat"] == 1


# --------------------------------------------------------------------------- #
# The register's key.
# --------------------------------------------------------------------------- #
def test_the_key_is_the_field_side_of_the_render_and_nothing_else():
    """One probe answers for every map at a location, which is the whole of why
    the measurement is minutes rather than an hour — and it is only true if the
    recolour half is out of the key."""
    row = _recipe().row()
    same = texture_flat.field_key(row)
    for spent in (
        {"colormap": "magma"},
        {"recipe": finished.recipe(mirror=True, cycles=3.0, phase=0.25)},
    ):
        assert texture_flat.field_key({**row, **spent}) == same, spent

    for moved in (
        {"mode": "smooth"},
        {"curve": "log"},
        {"render": {**row["render"], "maxiter": 501}},
        {"render": {**row["render"], "supersample": 3}},
        {"render": {**row["render"], "resolution": [1280, 720]}},
        {"viewport": {**row["viewport"], "width": "2.9"}},
        {"family": {"kind": "multibrot", "degree": 3}},
    ):
        assert texture_flat.field_key({**row, **moved}) != same, moved


def test_the_key_refuses_a_spec_member_nobody_has_classified():
    """The declaration is held to the live engine spec, so an axis the engine
    grows is a decision taken in the register rather than a member that quietly
    joined the key or quietly did not."""
    from pathlib import Path

    from fractal_wallpapers.models import renders

    spec = set(renders.spec_of(_recipe().row(), Path("_unwritten")))
    classified = set(texture_flat.KEYED) | set(texture_flat.SPENT_AFTER) | set(texture_flat.PINNED)
    assert spec <= classified, sorted(spec - classified)
    assert set(texture_flat.KEYED) <= spec, sorted(set(texture_flat.KEYED) - spec)


def test_the_two_geometries_are_two_identities():
    """A candidate is drawn at 640x360ss2 and a labelled picture at 1280x720ss2.
    They are different sample grids over one frame and the second may resolve a
    texture the first flattened, so one may never answer for the other."""
    candidate = _recipe().row()
    labelled = {**candidate, "render": {**candidate["render"], "resolution": [1280, 720]}}
    assert texture_flat.field_key(candidate) != texture_flat.field_key(labelled)


def test_an_unmeasured_render_reads_as_not_flat(monkeypatch):
    """What every reader concluded before this existed, which is what a checkout
    that has never measured has to keep doing."""
    _register(monkeypatch, {})
    assert texture_flat.flat_for(_label_row()) is False


def test_unmeasured_asks_one_probe_per_identity(monkeypatch):
    row = _recipe().row()
    rows = [row, {**row, "colormap": "magma"}, {**row, "curve": "log"}, {**row, "mode": "smooth"}]
    wanted = texture_flat.unmeasured(rows, entries={})
    assert len(wanted) == 2, "the two maps are one identity and `smooth` has no texture"
    already = {texture_flat.field_key(row): {"field": texture_flat.field_key(row), "flat": True}}
    assert len(texture_flat.unmeasured(rows, entries=already)) == 1


def test_the_register_round_trips_and_is_written_in_key_order(tmp_path, monkeypatch):
    """Whole-file and sorted, so two runs that measured the same identities write
    the same bytes and a Windows run cannot dirty a line it did not change."""
    monkeypatch.setattr(texture_flat, "path", lambda: tmp_path / "texture_flat.jsonl")
    row = _recipe().row()
    entries = {
        "ffff": texture_flat.entry("ffff", row, True, "mandelbrot"),
        "0000": texture_flat.entry("0000", {**row, "mode": "smooth"}, False, "phoenix"),
    }
    texture_flat.write(entries, log=lambda *_: None)
    written = (tmp_path / "texture_flat.jsonl").read_bytes()
    assert [json.loads(line)["field"] for line in written.splitlines()] == ["0000", "ffff"]
    assert b"\r\n" not in written
    assert texture_flat.read_entries() == entries
    assert texture_flat.register(reread=True) == {"ffff": True, "0000": False}


# --------------------------------------------------------------------------- #
# The register self-extends at ingest.
# --------------------------------------------------------------------------- #
def test_a_register_miss_at_ingest_is_measured_and_appended_rather_than_defaulted(
    tmp_path, monkeypatch
):
    """**The hole this closes.** The candidate geometry and the label geometry are
    two identities by `field_key`, and the second is only ever created by somebody
    putting a picture on a sheet — so an ingest is exactly where a MISS appears.
    Measured 2026-09-03, 23 of the 224 label rows in a mode with a texture had no
    entry, and each routed on `flat_for`'s unmeasured `False`.

    A flat one among them is the failure: the picture is the smooth field spent by
    rank bit for bit, the row belongs in the smooth store, and it lands in the
    strange one under a default nothing downstream can tell from a measurement.
    """
    monkeypatch.setattr(texture_flat, "path", lambda: tmp_path / "texture_flat.jsonl")
    monkeypatch.setattr(texture_flat, "_REGISTER", None)
    row = _label_row()
    key = texture_flat.field_key(row)
    probed = []

    def probe(job):
        probed.append(job["field"])
        return {"field": job["field"], "flat": True, "seconds": 4.2}

    monkeypatch.setattr(texture_flat, "probe", probe)

    assert finished.routes_to(row) == "strange_render", "the plain read still defaults"
    assert probed == [], "a reader must never render"

    assert finished.routes_to(row, extend=True) == "smooth_render"
    assert probed == [key], "one render, at the row's own geometry"
    stored = texture_flat.read_entries()
    assert stored[key]["flat"] is True
    assert stored[key]["resolution"] == [1280, 720] and stored[key]["supersample"] == 2

    # The register now answers, so the plain read agrees with the measured one and
    # the second ingest of the same identity costs nothing.
    assert finished.routes_to(row) == "smooth_render"
    assert finished.routes_to(row, extend=True) == "smooth_render"
    assert probed == [key], "an entry already held is never re-measured"


def test_extending_never_rewrites_an_entry_and_never_re_keys_a_row(tmp_path, monkeypatch):
    """A second measurement of one identity would be a second answer to a question
    that has one, and the first is the answer every stored routing was decided
    under. So a held key comes back off the register without a render, even when a
    fresh probe would disagree."""
    monkeypatch.setattr(texture_flat, "path", lambda: tmp_path / "texture_flat.jsonl")
    monkeypatch.setattr(texture_flat, "_REGISTER", None)
    row = _label_row()
    key = texture_flat.field_key(row)
    texture_flat.write(
        {key: texture_flat.entry(key, row, False, "mandelbrot")}, log=lambda *_: None
    )

    def refuse(job):
        raise AssertionError("a held identity must not be re-probed")

    monkeypatch.setattr(texture_flat, "probe", refuse)
    assert texture_flat.extend_with(row, log=lambda *_: None) is False
    assert texture_flat.read_entries()[key]["flat"] is False


def test_a_failed_span_test_refuses_rather_than_routing_on_the_default(tmp_path, monkeypatch):
    """A row routed on a failed probe would be routed on `flat_for`'s default while
    looking like a measurement, and nothing downstream could tell the two apart."""
    monkeypatch.setattr(texture_flat, "path", lambda: tmp_path / "texture_flat.jsonl")
    monkeypatch.setattr(texture_flat, "_REGISTER", None)
    monkeypatch.setattr(
        texture_flat, "probe", lambda job: {"field": job["field"], "why": "engine died"}
    )
    with pytest.raises(texture_flat.RegisterError, match="engine died"):
        texture_flat.extend_with(_label_row(), log=lambda *_: None)
    assert texture_flat.read_entries() == {}, "a failure leaves no entry behind"


def test_a_mode_with_no_texture_is_answered_without_a_render(tmp_path, monkeypatch):
    """Sixteen of the seventeen production modes have no texture layer at all, and
    an ingest of them must not pay a probe to be told so."""
    monkeypatch.setattr(texture_flat, "path", lambda: tmp_path / "texture_flat.jsonl")
    monkeypatch.setattr(texture_flat, "_REGISTER", None)
    monkeypatch.setattr(
        texture_flat, "probe", lambda job: pytest.fail("a textureless mode was probed")
    )
    assert texture_flat.extend_with(_label_row(mode="smooth")) is False


def test_the_writer_extends_and_every_reader_does_not(tmp_path, monkeypatch):
    """`append` is the one caller that measures a miss. A default that rendered on
    a read would turn `finished_train.population`'s per-row routing over 4,235 rows
    into a render leg, silently, on a machine that may already be running one."""
    monkeypatch.setattr(texture_flat, "path", lambda: tmp_path / "texture_flat.jsonl")
    monkeypatch.setattr(texture_flat, "_REGISTER", None)
    asked = []
    monkeypatch.setattr(
        texture_flat, "extend_with", lambda row, log=print: asked.append("extended") or False
    )
    monkeypatch.setattr(texture_flat, "flat_for", lambda row: asked.append("read") or False)
    row = _label_row()
    finished.check("strange_render", row)
    assert asked == ["read"]
    finished.check("strange_render", row, extend=True)
    assert asked == ["read", "extended"]
