"""Resuming an interrupted run: the seam, and everything it refuses to trust."""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import run as run_module


def log_lines():
    said: list = []
    return said, said.append


def write_log(path, rows) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8", newline="\n")


def test_the_candidate_log_says_which_attempts_are_done(tmp_path) -> None:
    path = tmp_path / "candidates.jsonl"
    write_log(path, [{"attempt": 0, "p_ge3": 0.5}, {"attempt": 2, "p_ge3": None}])
    done = run_module._completed(path, lambda _m: None)
    assert sorted(done) == [0, 2]
    assert run_module._completed(tmp_path / "nothing.jsonl", lambda _m: None) == {}


def test_a_torn_last_row_is_dropped_and_the_log_repaired(tmp_path) -> None:
    """A log left torn is not one row short: the next append lands on the same
    line and turns two rows into one unparseable one."""
    path = tmp_path / "candidates.jsonl"
    path.write_text(
        json.dumps({"attempt": 0, "p_ge3": 0.5}) + '\n{"attempt": 1, "p_g',
        encoding="utf-8",
        newline="\n",
    )
    said, log = log_lines()
    done = run_module._completed(path, log)
    assert sorted(done) == [0]
    assert any("repairing" in line for line in said)

    run_module._append(path, {"attempt": 1, "p_ge3": 0.1})
    assert sorted(run_module._completed(path, lambda _m: None)) == [0, 1]


def test_a_log_without_its_final_newline_is_repaired_before_anything_appends(tmp_path) -> None:
    path = tmp_path / "candidates.jsonl"
    path.write_text(json.dumps({"attempt": 0}), encoding="utf-8", newline="\n")
    run_module._completed(path, lambda _m: None)
    run_module._append(path, {"attempt": 1})
    assert sorted(run_module._completed(path, lambda _m: None)) == [0, 1]


def test_a_dumped_field_is_intact_only_at_the_size_its_own_record_states(tmp_path) -> None:
    field = tmp_path / "f.f32"
    field.write_bytes(b"\0" * (4 * 6 * 4))
    assert run_module._intact_field(field) is False, "no record beside it"

    field.with_suffix(".json").write_text(json.dumps({"samples": [6, 4]}), encoding="utf-8")
    assert run_module._intact_field(field) is True

    field.write_bytes(b"\0" * 12)
    assert run_module._intact_field(field) is False


def test_the_unfinished_attempt_s_own_output_is_discarded_rather_than_trusted(tmp_path) -> None:
    """The log says which attempts finished; it says nothing about what the one
    that did not was in the middle of."""
    pictures = tmp_path / "pictures"
    pictures.mkdir()
    (pictures / "0000.jpg").write_bytes(b"finished")
    (pictures / "0001.jpg").write_bytes(b"half")
    (pictures / "0001.leveled").mkdir()
    (pictures / "0001.leveled" / "map.json").write_text("{}", encoding="utf-8")
    fields = tmp_path / "fields"
    fields.mkdir()
    (fields / "short.f32").write_bytes(b"\0" * 8)
    (fields / "short.json").write_text(json.dumps({"samples": [64, 36]}), encoding="utf-8")

    said, log = log_lines()
    scrubbed = run_module._discard_partials(tmp_path, 3, {0: {}}, log)
    assert (pictures / "0000.jpg").is_file(), "a finished attempt's picture is its own"
    assert not (pictures / "0001.jpg").exists()
    assert not (pictures / "0001.leveled").exists()
    assert not (fields / "short.f32").exists()
    assert not (fields / "short.json").exists()
    assert scrubbed == {"pictures": 1, "candidates": 0, "fields": 1}
    assert any("discarded partial output" in line for line in said)


def test_a_candidate_recolor_that_cannot_be_read_is_made_again(tmp_path) -> None:
    pytest.importorskip("PIL")
    from PIL import Image

    where = tmp_path / "candidates" / "field"
    where.mkdir(parents=True)
    Image.new("RGB", (4, 4)).save(where / "good.jpg")
    (where / "half.jpg").write_bytes(b"\xff\xd8\xff truncated")

    scrubbed = run_module._discard_partials(tmp_path, 0, {}, lambda _m: None)
    assert (where / "good.jpg").is_file()
    assert not (where / "half.jpg").exists()
    assert scrubbed["candidates"] == 1


# --------------------------------------------------------------------------- #
# The shape of a run, fixed once.
# --------------------------------------------------------------------------- #
def shape_of(tmp_path, resume=False, log=None, **given) -> dict:
    asked = {name: given.get(name) for name in run_module.SHAPE}
    return run_module._shape(tmp_path, "v1", resume, asked, log or (lambda _m: None))


def test_a_fresh_run_writes_its_shape_down(tmp_path) -> None:
    shape = shape_of(tmp_path, n=4, seed=7)
    assert (shape["n"], shape["seed"]) == (4, 7)
    assert shape["strange_share"] == run_module.STRANGE_SHARE
    stored = json.loads((tmp_path / "run_plan.json").read_text(encoding="utf-8"))
    assert stored == shape and stored["schema"] == run_module.PLAN_SCHEMA


def test_a_second_run_under_the_same_name_is_a_refusal_not_a_restart(tmp_path) -> None:
    shape_of(tmp_path, n=4)
    with pytest.raises(run_module.RunRefused, match="--resume"):
        shape_of(tmp_path, n=4)


def test_a_resume_with_nothing_to_resume_says_so(tmp_path) -> None:
    with pytest.raises(run_module.RunRefused, match="never started"):
        shape_of(tmp_path, resume=True)


def test_a_resumed_run_takes_its_shape_from_its_own_plan(tmp_path) -> None:
    """A resume that re-derived its plan from the command line would be one
    forgotten flag away from colorizing a different set of locations."""
    shape_of(tmp_path, n=4, seed=7, attempts=9)
    said, log = log_lines()
    resumed = shape_of(tmp_path, resume=True, log=log)
    assert (resumed["n"], resumed["seed"], resumed["attempts"]) == (4, 7, 9)
    assert any("plan from" in line for line in said)


def test_a_flag_that_contradicts_the_plan_is_refused(tmp_path) -> None:
    shape_of(tmp_path, n=4)
    with pytest.raises(run_module.RunRefused, match="different shape"):
        shape_of(tmp_path, resume=True, n=5)
    assert shape_of(tmp_path, resume=True, n=4)["n"] == 4, "agreeing is not conflicting"


# --------------------------------------------------------------------------- #
# How a run ended, and the seam it has to balance.
# --------------------------------------------------------------------------- #
class Stopped:
    budget = None

    def elapsed(self):
        return 1.0


def test_the_three_endings_are_distinguishable_afterwards(tmp_path) -> None:
    with run_module._state(tmp_path, "v1", Stopped()) as state:
        assert json.loads((tmp_path / "state.json").read_text())["outcome"] == "running"
        state["outcome"] = "budget_stopped"
    assert "budget_stopped" in run_module._previous(tmp_path)

    with pytest.raises(ValueError), run_module._state(tmp_path, "v1", Stopped()):
        raise ValueError("the engine went away")
    assert "crashed" in run_module._previous(tmp_path)
    assert "went away" in run_module._previous(tmp_path)


def test_a_run_that_never_recorded_an_ending_is_reported_as_one(tmp_path) -> None:
    assert "never wrote one" in run_module._previous(tmp_path)
    (tmp_path / "state.json").write_text(json.dumps({"outcome": "running"}), encoding="utf-8")
    assert "crashed or was killed" in run_module._previous(tmp_path)


def test_the_seam_balances_or_says_so_loudly() -> None:
    """A resume that re-made a finished attempt is invisible in every other
    number a run prints. It shows up here or nowhere."""
    counts = {"planned": 10, "resumed": 4, "made": 3, "failed": 1, "not_started": 2}
    said, log = log_lines()
    held = run_module._reconcile(counts, {"counts": dict(counts)}, log)
    assert held["holds"] is True
    assert held["colorize"]["resumed"] == 4
    assert not any("MISMATCH" in line for line in said)

    said, log = log_lines()
    lost = run_module._reconcile({**counts, "made": 2}, {"counts": counts}, log)
    assert lost["holds"] is False and lost["release"]["holds"] is True
    assert any("MISMATCH on the colorize leg" in line for line in said)
