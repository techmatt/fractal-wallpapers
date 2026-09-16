"""Intake: the ranked offer, the floor that acts on it, and the slots it implies."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fractal_wallpapers import engine_fingerprint
from fractal_wallpapers.curation import floors, intake
from fractal_wallpapers.discovery import ledger as ledger_module
from fractal_wallpapers.supply import location as location_module
from fractal_wallpapers.supply.location import key_of_row


def candidate(center: str, fate: str = ledger_module.SURVIVED, family=None) -> dict:
    return {
        "schema": ledger_module.SCHEMA,
        "kind": "candidate",
        "node_id": center,
        "family": family or {"kind": "mandelbrot"},
        "viewport": {"center_re": center, "center_im": "0", "width": "0.5"},
        "maxiter": 500,
        "fate": fate,
        "score": None,
    }


@pytest.fixture
def ledger(tmp_path):
    """A walk ledger with three survivors and one gate refusal."""
    path = tmp_path / "walk.jsonl"
    rows = [
        candidate("-0.5"),
        candidate("-0.6"),
        candidate("-0.7", family={"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]}),
        candidate("-0.8", fate="flat"),
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def scores_for(rows, values) -> dict:
    return {
        json.dumps(key_of_row(row), ensure_ascii=False): {"p_ge3": value}
        for row, value in zip(rows, values, strict=True)
    }


def test_a_gate_refusal_is_not_supply(ledger) -> None:
    survivors, _ = intake.gate_survivors([ledger])
    assert len(survivors) == 3
    assert all(row["fate"] == ledger_module.SURVIVED for row in survivors)


def test_the_offer_is_best_first_and_the_junk_floor_acts(ledger) -> None:
    survivors, _ = intake.gate_survivors([ledger])
    scores = scores_for(survivors, [0.4, 0.9, 0.05])
    offer, diagnostics = intake.ranked([ledger], scores)
    assert [row["score"] for row in offer["mandelbrot"]] == [0.9, 0.4]
    # The 0.05 row is below the junk floor: found, counted, never offered.
    assert "julia:mandelbrot" not in offer
    assert diagnostics["found_by_partition"] == {"julia:mandelbrot": 1, "mandelbrot": 2}
    assert diagnostics["passing_by_partition"] == {"mandelbrot": 2}


def test_a_location_the_sidecar_has_no_opinion_about_is_counted_and_not_offered(
    ledger,
) -> None:
    """An unscored row has no verdict to spend compute on, and it is not silently
    dropped either — the count is how a reader knows the number is small."""
    offer, diagnostics = intake.ranked([ledger], {})
    assert offer == {}
    assert diagnostics["unscored"] == 3
    assert diagnostics["found"] == 3


def test_every_partition_the_union_saw_gets_a_line_including_the_ones_that_ship_nothing(
    ledger,
) -> None:
    survivors, _ = intake.gate_survivors([ledger])
    scores = scores_for(survivors, [0.4, 0.9, 0.05])
    _, diagnostics = intake.ranked([ledger], scores)
    lines = intake.supply_lines(diagnostics)
    assert any(line.startswith("julia:mandelbrot") for line in lines)
    assert any("thin supply" in line for line in lines)


def test_the_funnel_puts_each_number_over_the_population_it_is_of(ledger) -> None:
    """The first production run printed "22,751 found, 1,245 above the junk floor"
    with every gate survivor as the denominator and only the scored prefix as the
    numerator, which understated the pass rate by a factor of four. The scored
    count sits between the two so a reader can see which is which."""
    survivors, _ = intake.gate_survivors([ledger])
    scores = scores_for(survivors[:2], [0.4, 0.9])
    _, diagnostics = intake.ranked([ledger], scores)

    assert diagnostics["found"] == 3
    assert diagnostics["scored"] == 2
    assert diagnostics["passing"] == 2
    assert diagnostics["unscored"] == 1
    assert diagnostics["scored"] + diagnostics["unscored"] == diagnostics["found"]

    line = intake.funnel_line(diagnostics)
    assert "3 found" in line and "2 scored" in line and "1 found but unscored" in line


def test_a_partition_s_line_names_its_own_scored_denominator(ledger) -> None:
    survivors, _ = intake.gate_survivors([ledger])
    scores = scores_for(survivors[:1], [0.9])
    _, diagnostics = intake.ranked([ledger], scores)
    assert diagnostics["scored_by_partition"] == {"mandelbrot": 1}
    line = next(line for line in intake.supply_lines(diagnostics) if line.startswith("mandelbrot:"))
    assert "2 found, 1 scored, 1 of those above the junk floor" in line


def test_the_guarantee_triggers_on_the_good_floor_not_the_junk_floor(ledger) -> None:
    survivors, _ = intake.gate_survivors([ledger])
    # Read off the two floors rather than typed: the heights move at a head flip
    # and a literal that used to sit between them silently stops testing anything.
    between = (floors.JUNK_FLOOR + floors.GOOD_FLOOR) / 2
    scores = scores_for(survivors, [between, 0.99, 0.0])
    _, diagnostics = intake.ranked([ledger], scores)
    assert floors.passes_junk_floor(between) and not floors.passes_good_floor(between)
    assert diagnostics["good_by_partition"] == {"mandelbrot": 1}
    assert intake.guaranteed(diagnostics) == ["mandelbrot"]


def test_a_guaranteed_partition_is_seated_where_the_mix_alone_would_zero_it() -> None:
    """At small n the mix zeroes the lowest-ratio partitions whatever their supply."""
    partitions = ("mandelbrot", "phoenix:classic")
    bare = intake.slots(partitions, 2)
    assert bare["phoenix:classic"] == 0
    floored = intake.slots(partitions, 2, guarantees=["phoenix:classic"])
    assert floored["phoenix:classic"] == 1
    assert sum(floored.values()) == 2


def test_a_guarantee_is_a_floor_and_not_a_bonus() -> None:
    """A partition the mix already seats gains nothing from being named."""
    partitions = ("mandelbrot", "julia:mandelbrot", "phoenix")
    bare = intake.slots(partitions, 9)
    named = intake.slots(partitions, 9, guarantees=["mandelbrot"])
    assert named == bare


def test_the_release_caps_come_off_the_offers_own_size(ledger) -> None:
    survivors, _ = intake.gate_survivors([ledger])
    scores = scores_for(survivors, [0.4, 0.9, 0.9])
    offer, _ = intake.ranked([ledger], scores)
    assert intake.release_caps(offer) == {"julia:mandelbrot": 0, "mandelbrot": 0}


def test_the_canonical_view_is_the_deploy_map(ledger) -> None:
    """The picture a location is judged on is the one a deployed judge is handed."""
    assert intake.canonical_map() == "twilight_shifted"
    row = intake.view_row(candidate("-0.5"), "twilight_shifted", {"twilight_shifted"})
    assert row["mode"] == "smooth"
    assert row["render"]["resolution"] == [640, 360]
    assert row["recipe"]["mirror"] is False


def test_a_score_read_needs_a_sidecar_before_it_can_rank(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(intake, "store_dir", lambda: tmp_path)
    with pytest.raises(intake.IntakeError):
        intake.read_scores()


# --------------------------------------------------------------------------- #
# The sidecar: one upsert per ledger, never a wholesale rewrite.
# --------------------------------------------------------------------------- #
def written(path, centers) -> object:
    """A walk ledger holding one gate-surviving candidate per centre."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(candidate(c)) + "\n" for c in centers), encoding="utf-8")
    return path


@pytest.fixture
def score(tmp_path, monkeypatch):
    """`intake.score`, with the renderer and the head stubbed out.

    What is under test is which rows the sidecar keeps across invocations, not
    what the judge said about them, and the real halves need a release engine and
    a shipped head that this question does not depend on.
    """
    from fractal_wallpapers.models import scoring, ship, train

    monkeypatch.setattr(intake, "store_dir", lambda: tmp_path / "curation")
    monkeypatch.setattr(intake, "view_dir", lambda regime=None: tmp_path / "views")
    monkeypatch.setattr(intake.floors, "live_stamp", lambda head: "a-stamp")
    monkeypatch.setattr(intake.location_view, "canonical_map", lambda: "twilight_shifted")
    monkeypatch.setattr(intake.location_view, "cyclic_maps", lambda: set())
    monkeypatch.setattr(
        intake.location_view, "summary", lambda colormap, regime=None: {"map": colormap}
    )
    monkeypatch.setattr(
        intake.location_view,
        "render_view",
        # Named off the viewport rather than off `node_id`: an `opened` row has no
        # node id at all, being a location off the candidate ledger and not a
        # walk's node, and a stub that insisted on one would fail there for a
        # reason that says nothing about what these cases test.
        lambda row, colormap, cyclic, directory, regime=None: (
            directory / f"{row['viewport']['center_re']}.jpg",
            False,
        ),
    )
    monkeypatch.setattr(ship, "shipped_path", lambda head: tmp_path / "head.pt")
    monkeypatch.setattr(scoring, "load", lambda path, device: (None, {"classes": 4}, "cpu"))
    monkeypatch.setattr(scoring, "transform_of", lambda config: None)
    monkeypatch.setattr(
        train, "score", lambda model, pictures, *rest: [[0.9, 0.8, 0.7]] * len(pictures)
    )
    return lambda paths, **kw: intake.score(paths, log=lambda _m: None, **kw)


def test_two_ledgers_scored_in_two_invocations_hold_their_union(tmp_path, score) -> None:
    """Scoping a run's scoring to its own ledger used to be destructive: it took
    the sidecar from 12,580 rows to 6,907 and reported nothing about the 5,673."""
    first = written(tmp_path / "a" / "walk.jsonl", ["-0.5", "-0.6"])
    second = written(tmp_path / "b" / "walk.jsonl", ["-0.7"])
    score([first])
    report = score([second])
    assert (report["sidecar"]["rows_scored"], report["sidecar"]["rows_kept"]) == (1, 2)
    assert len(intake.read_scores()) == 3


def test_re_scoring_one_ledger_replaces_its_own_rows_and_touches_no_other(tmp_path, score) -> None:
    first = written(tmp_path / "a" / "walk.jsonl", ["-0.5", "-0.6"])
    second = written(tmp_path / "b" / "walk.jsonl", ["-0.7"])
    score([first])
    score([second])
    before = intake.scores_path().read_bytes()

    report = score([first])
    assert report["sidecar"]["rows_scored"] == 2, "its own rows, minted again"
    assert report["sidecar"]["rows_kept"] == 1, "the other ledger's row, untouched"
    assert intake.scores_path().read_bytes() == before, "an idempotent re-score"


def test_a_ledger_that_lost_a_location_loses_its_row(tmp_path, score) -> None:
    """The replacement is per ledger rather than per row, so a re-score is the
    ledger's whole current answer and not a merge with its old one."""
    first = written(tmp_path / "a" / "walk.jsonl", ["-0.5", "-0.6"])
    written(tmp_path / "b" / "walk.jsonl", ["-0.7"])
    score([first])
    score([tmp_path / "b" / "walk.jsonl"])
    written(first, ["-0.5"])
    score([first])
    assert sorted(row["node_id"] for row in intake.read_scores().values()) == ["-0.5", "-0.7"]


def test_a_limited_pass_upserts_what_it_looked_at_and_clears_nothing(tmp_path, score) -> None:
    """A prefix is not an answer about the rows it never reached."""
    ledger = written(tmp_path / "a" / "walk.jsonl", ["-0.5", "-0.6"])
    score([ledger])
    report = score([ledger], limit=1)
    assert report["sidecar"]["scoped_ledgers"] == []
    assert len(intake.read_scores()) == 2


def test_an_unscored_pass_reads_the_backlog_and_nothing_else(tmp_path, score) -> None:
    """The population that had no door: bound, and with no sidecar row at all.

    `curate reach --write` looks like this door and is not — it is built from
    release decision rows, so it cannot see a location that was found, opened and
    never scored.
    """
    first = written(tmp_path / "a" / "walk.jsonl", ["-0.5", "-0.6"])
    second = written(tmp_path / "b" / "walk.jsonl", ["-0.7", "-0.8"])
    score([first])

    report = score([first, second], unscored=True)
    assert report["outstanding"] == 2, "the second ledger's two, and neither of the first's"
    assert report["gate_survivors"] == 2
    assert sorted(row["node_id"] for row in intake.read_scores().values()) == [
        "-0.5",
        "-0.6",
        "-0.7",
        "-0.8",
    ]


def test_an_unscored_pass_clears_nothing(tmp_path, score) -> None:
    """It is a partial pass, like `limit` and `keys`, so it scopes no ledger."""
    first = written(tmp_path / "a" / "walk.jsonl", ["-0.5"])
    second = written(tmp_path / "b" / "walk.jsonl", ["-0.7"])
    score([first])
    score([second])
    written(first, ["-0.5", "-0.6"])

    report = score([first, second], unscored=True)
    assert report["sidecar"]["scoped_ledgers"] == [], "a backlog pass is not a re-score"
    assert len(intake.read_scores()) == 3, "the two already-scored rows both survive"


def test_an_unscored_pass_with_nothing_outstanding_is_complete_and_not_an_error(
    tmp_path, score
) -> None:
    """A backlog of nothing is the outcome, not a refusal to have one."""
    ledger = written(tmp_path / "a" / "walk.jsonl", ["-0.5", "-0.6"])
    score([ledger])
    before = intake.scores_path().read_bytes()

    report = score([ledger], unscored=True)
    assert (report["outstanding"], report["scored"], report["complete"]) == (0, 0, True)
    assert report["gate_survivors"] == 2, "the denominator the backlog is nothing out of"
    assert intake.scores_path().read_bytes() == before, "and it wrote nothing"


def test_an_unscored_pass_reports_the_backlog_before_a_limit_truncates_it(tmp_path, score) -> None:
    """A truncated pass that reported its own scored count as the backlog would
    read as a finished one."""
    ledger = written(tmp_path / "a" / "walk.jsonl", ["-0.5", "-0.6", "-0.7"])
    report = score([ledger], unscored=True, limit=1)
    assert report["outstanding"] == 3, "how much the backlog IS"
    assert report["sidecar"]["rows_scored"] == 1, "how much of it this pass took"


def test_a_backlog_truncated_to_nothing_does_not_read_as_a_backlog_of_nothing(
    tmp_path, score
) -> None:
    """`--limit 0` and `nothing outstanding` reach the same branch and are not the
    same answer. Reporting both as `complete` would call an untouched backlog done."""
    ledger = written(tmp_path / "a" / "walk.jsonl", ["-0.5", "-0.6", "-0.7"])
    report = score([ledger], unscored=True, limit=0)
    assert (report["outstanding"], report["scored"]) == (3, 0)
    assert report["complete"] is False


# --------------------------------------------------------------------------- #
# The population no binding reaches: opened, and on no walk ledger at all.
# --------------------------------------------------------------------------- #
def opened_row(center: str, family=None) -> dict:
    """A candidate-ledger row as `curate label-migration merge` writes one."""
    recipe = {
        "family": family or {"kind": "mandelbrot"},
        "viewport": {"center_re": center, "center_im": "0", "width": "0.5"},
        "maxiter": 500,
    }
    place = location_module.key_text(key_of_row(recipe))
    return {"key": f"recipe{center}", "location": {"key": place}, "recipe": recipe}


@pytest.fixture
def opened(monkeypatch):
    """A candidate ledger of our own, streamed the way the real one is."""
    rows: list[dict] = []
    from fractal_wallpapers.curation import candidate_ledger

    monkeypatch.setattr(candidate_ledger, "stream", lambda path=None: iter(list(rows)))
    return rows


def test_the_opened_pass_reads_the_places_no_walk_ledger_names(tmp_path, score, opened) -> None:
    """★ The 1,607: opened by `label-migration merge`, on no ledger, so every draw
    standing on `hunt.scanned` stepped over them and no binding could reach them."""
    opened.extend([opened_row("-0.5"), opened_row("-0.6")])

    report = score(None, opened=True)

    assert (report["opened"], report["outstanding"], report["complete"]) == (True, 2, True)
    assert report["sidecar"]["rows_scored"] == 2
    assert {row["ledger"] for row in intake.read_scores().values()} == {intake.OPENED_LEDGER}


def test_the_opened_pass_skips_a_place_the_sidecar_already_holds(tmp_path, score, opened) -> None:
    """It is the backlog and not a re-score: a place with a row is not re-read."""
    opened.extend([opened_row("-0.5"), opened_row("-0.6")])
    score(None, opened=True)
    opened.append(opened_row("-0.7"))

    report = score(None, opened=True)
    assert report["outstanding"] == 1, "the third place, and neither of the first two"
    assert len(intake.read_scores()) == 3


def test_the_opened_pass_clears_nothing_a_walk_binding_scored(tmp_path, score, opened) -> None:
    """A partial pass like the other three, and over another population entirely."""
    score([written(tmp_path / "a" / "walk.jsonl", ["-0.5"])])
    opened.append(opened_row("-0.9"))

    report = score(None, opened=True)
    assert report["sidecar"]["scoped_ledgers"] == []
    assert len(intake.read_scores()) == 2, "the walk's row survives"


def test_a_candidate_whose_recipe_does_not_key_back_to_its_place_is_not_scored(
    tmp_path, score, opened
) -> None:
    """A row scored under a key nothing joins on is worse than no row: the join is
    what the whole sidecar is for, so it is counted and dropped."""
    row = opened_row("-0.5")
    row["location"]["key"] = location_module.key_text(key_of_row(opened_row("-0.6")["recipe"]))
    opened.append(row)

    report = score(None, opened=True)
    assert (report["outstanding"], report["complete"]) == (0, True)


def test_opened_is_a_population_and_refuses_every_flag_that_narrows_a_binding(
    tmp_path, score, opened
) -> None:
    """There is no walk binding here for `--ledger`, `--limit`, `--key-file` or
    `--unscored` to narrow, so asking for both is refused rather than resolved."""
    opened.append(opened_row("-0.5"))
    ledger = written(tmp_path / "a" / "walk.jsonl", ["-0.5"])
    for asked in ({"paths": [ledger]}, {"limit": 1}, {"unscored": True}, {"keys": set()}):
        with pytest.raises(intake.IntakeError, match="population and not a filter"):
            score(asked.pop("paths", None), opened=True, **asked)


# --------------------------------------------------------------------------- #
# The population BEHIND that one: graded, and never opened at all.
#
# A place somebody scored a keeper that nothing has ever rendered a candidate at.
# No walk ledger names it, so no binding reaches it; no candidate row stands on
# it, so `opened` does not either. Measured 2026-09-16: 3,110 of the 6,202 places
# at a human verdict >= 3 were in neither the sidecar nor the embedding store,
# which is what makes `curate hunt --places` refuse a manifest of them outright.
# --------------------------------------------------------------------------- #
def graded_row(center: str, score_at: int = 4, maxiter: int = 500, family=None) -> dict:
    """A label row as either store writes one: a verdict, a family and a viewport."""
    return {
        "schema": 1,
        "origin": "human",
        "score": score_at,
        "family": family or {"kind": "mandelbrot"},
        "viewport": {"center_re": center, "center_im": "0", "width": "0.5"},
        "render": {"resolution": [1280, 720], "supersample": 2, "maxiter": maxiter},
    }


@pytest.fixture
def graded(monkeypatch):
    """Label stores of our own, streamed the way `graded_rows` streams the real three."""
    rows: list[dict] = []
    monkeypatch.setattr(
        intake,
        "graded_rows",
        lambda log=print: iter(
            [(location_module.text_of_row(row), row) for row in list(rows)],
        ),
    )
    return rows


def test_the_graded_pass_reads_the_places_nothing_has_ever_opened(tmp_path, score, graded) -> None:
    """★ The 3,110. Behind the 1,607: those had a candidate row and no ledger, these
    have neither, so `opened` cannot see them and no binding ever could."""
    graded.extend([graded_row("-0.5"), graded_row("-0.6")])

    report = score(None, graded=True)

    assert (report["graded"], report["outstanding"], report["complete"]) == (True, 2, True)
    assert report["sidecar"]["rows_scored"] == 2
    assert {row["ledger"] for row in intake.read_scores().values()} == {intake.GRADED_LEDGER}


def test_the_graded_pass_takes_one_row_per_place_at_its_best_verdict(score, graded) -> None:
    """A place graded twice is one place. The verdicts survive only as the order."""
    graded.extend(
        [
            graded_row("-0.5", score_at=3),
            graded_row("-0.5", score_at=4),
            graded_row("-0.6", score_at=3),
        ]
    )

    rows = intake.graded_backlog(log=lambda *_args: None)
    assert [row["_verdict"] for row in rows] == [4, 3], "best verdict first"
    assert score(None, graded=True)["sidecar"]["rows_scored"] == 2


def test_graded_rows_reads_all_three_stores_and_only_the_paid_human_verdicts(
    tmp_path, monkeypatch
) -> None:
    """The cut is `graded_rows`' and not `graded_backlog`'s, so it is tested where it
    lives: over files, at the three store names. `GRADED_FLOOR` is three — both of
    the currency's paid classes and nothing below them, the same floor `reframe
    --tier-floor` seeds from — and a row the labeling rig generated is not a human
    verdict however high it reads."""
    import fractal_wallpapers.paths as paths_module

    monkeypatch.setattr(paths_module, "repo_root", lambda: tmp_path)
    wrote = {
        "labels": [graded_row("-0.1", score_at=4), graded_row("-0.2", score_at=2)],
        "smooth_render": [graded_row("-0.3", score_at=3)],
        "strange_render": [graded_row("-0.4", score_at=4)],
    }
    for store, rows in wrote.items():
        directory = tmp_path / "data" / store / "rows"
        directory.mkdir(parents=True)
        (directory / "batch.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
    # A machine verdict in the store the human rows share, to prove `origin` cuts.
    machine = dict(graded_row("-0.5", score_at=4), origin="model")
    (tmp_path / "data" / "labels" / "rows" / "machine.jsonl").write_text(
        json.dumps(machine) + "\n", encoding="utf-8"
    )

    held = [row for _text, row in intake.graded_rows(log=lambda *_args: None)]

    assert sorted(row["viewport"]["center_re"] for row in held) == ["-0.1", "-0.3", "-0.4"]


def test_a_store_that_is_not_there_is_not_an_error(tmp_path, monkeypatch) -> None:
    """A clone that has never fetched a finished corpus still has a location store,
    and a graded pass over what it does have is the right answer rather than a crash."""
    import fractal_wallpapers.paths as paths_module

    monkeypatch.setattr(paths_module, "repo_root", lambda: tmp_path)
    directory = tmp_path / "data" / "labels" / "rows"
    directory.mkdir(parents=True)
    (directory / "batch.jsonl").write_text(json.dumps(graded_row("-0.1")) + "\n", encoding="utf-8")

    assert len(list(intake.graded_rows(log=lambda *_args: None))) == 1


def test_the_graded_pass_skips_a_place_the_sidecar_already_holds(score, graded) -> None:
    """The backlog and not a re-score, exactly as the opened pass is."""
    graded.extend([graded_row("-0.5"), graded_row("-0.6")])
    score(None, graded=True)
    graded.append(graded_row("-0.7"))

    report = score(None, graded=True)
    assert report["outstanding"] == 1, "the third place, and neither of the first two"
    assert len(intake.read_scores()) == 3


def test_the_graded_pass_clears_nothing_a_walk_binding_scored(tmp_path, score, graded) -> None:
    """A partial pass over another population entirely, so it scopes no ledger."""
    score([written(tmp_path / "a" / "walk.jsonl", ["-0.5"])])
    graded.append(graded_row("-0.9"))

    report = score(None, graded=True)
    assert report["sidecar"]["scoped_ledgers"] == []
    assert len(intake.read_scores()) == 2, "the walk's row survives"


def test_graded_is_a_population_and_refuses_every_flag_that_narrows_a_binding(
    tmp_path, score, graded
) -> None:
    """The same refusal `opened` makes, and for the same reason: no binding here."""
    graded.append(graded_row("-0.5"))
    ledger = written(tmp_path / "a" / "walk.jsonl", ["-0.5"])
    for asked in ({"paths": [ledger]}, {"limit": 1}, {"unscored": True}, {"keys": set()}):
        with pytest.raises(intake.IntakeError, match="population and not a filter"):
            score(asked.pop("paths", None), graded=True, **asked)


def test_graded_and_opened_are_two_populations_and_refuse_each_other(score, graded) -> None:
    """★ They OVERLAP — at every place that is both graded and opened — so a pass
    claiming both would mint that place twice under two different `ledger` names.
    That is the one way these two differ from the three filters, which merely have
    no binding to narrow."""
    graded.append(graded_row("-0.5"))
    with pytest.raises(intake.IntakeError, match="two populations rather than two filters"):
        score(None, graded=True, opened=True)


# --------------------------------------------------------------------------- #
# The regime a row is re-scored at.
#
# A walk scores its own gate render now, so the sidecar reads a row at the regime
# the row names — and never demands a deploy-geometry render for a row that was
# never scored at one.
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def a_named_engine_build(monkeypatch):
    """One build, named, for every case in this file.

    The gate renders here are bytes a test wrote, not pictures an engine drew, so
    the fingerprint is stubbed: what these cases are about is the regime and the
    digest, and a real probe render would make each of them depend on a built
    crate to say nothing extra. The one case that IS about the stamp says so.
    """
    monkeypatch.setattr(engine_fingerprint, "current", lambda: "testbuild0000000")
    engine_fingerprint.forget()
    yield
    engine_fingerprint.forget()


def node_row(tmp_path, image="node7_c1.jpg", digest=None, made=True, stamped=True) -> dict:
    """One node-regime ledger row, with the gate render its run left behind."""
    from fractal_wallpapers.models import location_view
    from fractal_wallpapers.models import tiles as tile_module

    row = candidate("-0.5")
    row["_ledger"] = str(tmp_path / "run" / "walk.jsonl")
    row["image"] = image
    row["score_regime"] = tile_module.NODE_REGIME.spelled
    row["score_view"] = digest or location_view.view_name(
        row, "twilight_shifted", set(), tile_module.NODE_REGIME
    )
    if made:
        picture = tmp_path / "run" / "views" / image
        picture.parent.mkdir(parents=True, exist_ok=True)
        picture.write_bytes(b"a finished picture")
        if stamped:
            engine_fingerprint.stamps(picture.parent).record(image)
    return row


def test_a_row_scored_at_the_node_regime_reads_the_picture_the_walk_already_made(
    tmp_path,
) -> None:
    """The whole saving: the second render per survivor is gone, and the re-score
    does not quietly put it back."""
    from fractal_wallpapers.models import tiles as tile_module

    row = node_row(tmp_path)
    found = intake.gate_render(row, "twilight_shifted", set(), tile_module.NODE_REGIME)
    assert found == tmp_path / "run" / "views" / "node7_c1.jpg"


def test_a_recipe_that_moved_costs_a_re_render_rather_than_the_wrong_picture(tmp_path) -> None:
    """The digest is what tells a gate render apart from a frame that sits at the
    same coordinates and was drawn some other way."""
    from fractal_wallpapers.models import tiles as tile_module

    stale = node_row(tmp_path, digest="0000000000000000")
    assert intake.gate_render(stale, "twilight_shifted", set(), tile_module.NODE_REGIME) is None


def test_a_gate_render_the_run_no_longer_has_costs_a_re_render(tmp_path) -> None:
    from fractal_wallpapers.models import tiles as tile_module

    gone = node_row(tmp_path, made=False)
    assert intake.gate_render(gone, "twilight_shifted", set(), tile_module.NODE_REGIME) is None


def test_a_gate_render_no_build_claims_costs_a_re_render(tmp_path) -> None:
    """The right place, the right size, the right digest — and drawn by a program
    nobody wrote down. Every gate render made before the stamp existed looks like
    this, which is what `curate redraw` is for."""
    from fractal_wallpapers.models import tiles as tile_module

    unstamped = node_row(tmp_path, stamped=False)
    assert intake.gate_render(unstamped, "twilight_shifted", set(), tile_module.NODE_REGIME) is None


def test_a_row_states_a_regime_or_it_does_not_and_none_is_not_the_deploy_one(tmp_path) -> None:
    """`regime_of` reports what the row says and nothing else. Every row of the
    standing stock predates a walk saying, and what to do about that is
    `_picture_for`'s decision rather than a default hidden in the reader."""
    assert intake.regime_of(candidate("-0.5")) is None
    assert intake.regime_of(node_row(tmp_path)) == intake.READ_REGIME


def test_a_row_that_names_something_that_is_not_a_regime_refuses(tmp_path) -> None:
    row = node_row(tmp_path)
    row["score_regime"] = "enormous"
    with pytest.raises(intake.IntakeError):
        intake.regime_of(row)


def test_a_node_regime_row_is_scored_without_one_engine_call(tmp_path, score, monkeypatch) -> None:
    """The claim `curate score` makes about a new run's ledger, end to end: no
    deploy-geometry render is ever demanded, and the picture is the walk's own."""
    row = node_row(tmp_path)
    ledger = tmp_path / "run" / "walk.jsonl"
    ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")

    drew = []
    monkeypatch.setattr(
        intake.location_view,
        "render_view",
        lambda *a, **k: drew.append(a) or (tmp_path / "never.jpg", True),
    )
    report = score([ledger])
    assert drew == [], "a row whose picture already exists cost an engine call"
    assert report["pictures"] == {"gate": 1, "cached": 0, "rendered": 0}
    assert report["by_regime"] == {"384x216ss1": 1}
    assert next(iter(intake.read_scores().values()))["regime"] == "384x216ss1"


def test_a_regime_less_row_is_scored_at_the_node_regime_and_never_touches_location_views(
    tmp_path, monkeypatch
) -> None:
    """Matt's ruling, end to end. A row with no `score_regime` has never been
    scored at all, so it is read like every walk node — into
    `artifacts/node_views/<regime>/`, and the sidecar row says so. The deploy
    cache is a record of what was scored there before a walk scored its own
    frames; a first read of old stock must not make it grow again.

    The roots are redirected rather than `view_dir` stubbed, because *which
    directory* is the whole claim and a stub would be the test asserting its own
    answer.
    """
    from fractal_wallpapers.models import scoring, ship, train
    from fractal_wallpapers.paths import ARCHIVE_ROOT_VARIABLE, HOT_ROOT_VARIABLE

    (tmp_path / "artifacts").mkdir()
    monkeypatch.setenv(HOT_ROOT_VARIABLE, str(tmp_path / "artifacts"))
    monkeypatch.setenv(ARCHIVE_ROOT_VARIABLE, "")
    monkeypatch.setattr(intake.floors, "live_stamp", lambda head: "a-stamp")
    monkeypatch.setattr(intake.location_view, "canonical_map", lambda: "twilight_shifted")
    monkeypatch.setattr(intake.location_view, "cyclic_maps", lambda: set())
    monkeypatch.setattr(ship, "shipped_path", lambda head: tmp_path / "head.pt")
    monkeypatch.setattr(scoring, "load", lambda path, device: (None, {"classes": 4}, "cpu"))
    monkeypatch.setattr(scoring, "transform_of", lambda config: None)
    monkeypatch.setattr(train, "score", lambda *rest: [[0.9, 0.8, 0.7]])

    drawn = []

    def drew(row, colormap, cyclic, directory, regime=None):
        picture = Path(directory) / "drawn.jpg"
        picture.parent.mkdir(parents=True, exist_ok=True)
        picture.write_bytes(b"a finished picture")
        drawn.append((picture, regime))
        return picture, True

    monkeypatch.setattr(intake.location_view, "render_view", drew)

    ledger = written(tmp_path / "old" / "walk.jsonl", ["-0.5"])
    report = intake.score([ledger], log=lambda _m: None)

    (picture, regime) = drawn[0]
    assert regime == intake.READ_REGIME
    assert picture.parent == tmp_path / "artifacts" / "node_views" / "384x216ss1"
    assert not (tmp_path / "artifacts" / "location_views").exists()
    assert report["by_regime"] == {"384x216ss1": 1}
    assert next(iter(intake.read_scores().values()))["regime"] == "384x216ss1"


def test_a_location_key_has_one_spelling_on_disk_and_it_is_json() -> None:
    """The join every store makes, and the silent way it can fail.

    A key is a tuple. `str(key)` writes a Python repr — `('mandelbrot', 2, (), …)`
    — where the sidecar and the embedding store write JSON. The two are different
    strings for one location and nothing raises: `curation.distinct` keeps a place
    with no descriptor by rule, so a reader on the wrong spelling turns the whole
    pre-selection into a no-op. It did, over the reframing channel's 792 places,
    and this is the guard that says the spelling has one owner.
    """
    row = {
        "family": {"kind": "mandelbrot", "degree": 2},
        "viewport": {"center_re": "-0.75", "center_im": "0.1", "width": "0.01"},
    }
    text = location_module.text_of_row(row)
    assert text == location_module.key_text(key_of_row(row))
    assert text.startswith("[") and text.endswith("]")
    assert json.loads(text)[0] == "mandelbrot"
    assert text != str(key_of_row(row))
    # And the sidecar's own writer is that function rather than a second one.
    assert intake._key_text(row) == text
    assert location_module.text_of_row({"family": None, "viewport": None}) is None
