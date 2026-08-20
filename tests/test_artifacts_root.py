"""Guard: the regenerable tree can live on another disk, and says so when it cannot.

`artifacts/` is a hundred gigabytes of things a run can always make again, and on
a machine whose system drive is smaller than that it belongs elsewhere. The whole
mechanism is three functions in `paths` — the root is a setting, `rehome` reads a
stored name against it, `tracked_name` writes one — plus every consumer asking
for the root instead of building it out of `repo_root()`.

Two failures are what these tests are actually about:

* **A silent fallback.** If a configured root is missing — an external disk left
  unplugged — and the code quietly used `artifacts/` under the checkout instead,
  it would find an empty tree. Every cache here reads absence as "not built
  yet", so that does not look like a missing disk; it looks like work that was
  never done, and the next command spends hours redoing it on the wrong drive.

* **A name that moved.** A ledger's name is the key curation's sidecar keeps its
  scored rows under. Spell it one way in the checkout and another way on an
  external disk and every stored row becomes unmatchable, so a re-score adds
  duplicates beside rows it was supposed to replace. `tracked_name` is what
  keeps both spellings the same, and it is tested here rather than trusted.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers import cli, paths
from fractal_wallpapers.curation import binding
from fractal_wallpapers.curation import intake as curation_intake
from fractal_wallpapers.curation import run as curation_run
from fractal_wallpapers.discovery import scoring as discovery_scoring
from fractal_wallpapers.models import palette_corpus, regime_flips, renders
from fractal_wallpapers.models import tiles as tile_module
from fractal_wallpapers.supply import ledgers


@pytest.fixture
def relocated(tmp_path, monkeypatch):
    """An artifacts tree somewhere that is not the checkout, and the package on it."""
    root = tmp_path / "elsewhere" / "artifacts"
    root.mkdir(parents=True)
    monkeypatch.setenv(paths.ARTIFACTS_ROOT_VARIABLE, str(root))
    return root


def test_the_default_is_the_checkout(monkeypatch):
    """Nothing configured is the case CI and a fresh clone are in."""
    monkeypatch.delenv(paths.ARTIFACTS_ROOT_VARIABLE, raising=False)
    monkeypatch.setattr(paths, "local_settings_path", lambda: paths.repo_root() / "absent.toml")
    assert paths.configured_artifacts_root() is None
    assert paths.artifacts_root() == paths.repo_root() / paths.ARTIFACTS_NAME


def test_every_consumer_follows_the_root(relocated):
    """One root, one rule: no module builds its own out of the repository root."""
    where = {
        "tiles": tile_module.tile_dir(),
        "tile cache": tile_module.cache_root(),
        "location views": discovery_scoring.view_dir(),
        "renders": renders.cache_dir("smooth_render"),
        "palette": palette_corpus.cache_dir(),
        "curation": curation_intake.store_dir(),
        "a curation run": curation_run.run_dir("r"),
        "regime flips": regime_flips.study_dir(),
        "walk ledgers": ledgers.ledger_root(),
    }
    strays = {name: path for name, path in where.items() if relocated not in (path, *path.parents)}
    assert not strays, f"these did not follow the artifacts root: {strays}"


def test_a_missing_root_refuses_rather_than_falling_back(tmp_path, monkeypatch):
    """The unplugged-disk case. It must not become an empty tree in the checkout."""
    gone = tmp_path / "unplugged" / "artifacts"
    monkeypatch.setenv(paths.ARTIFACTS_ROOT_VARIABLE, str(gone))
    with pytest.raises(paths.ArtifactsRootMissing) as refusal:
        paths.artifacts_root()
    assert str(gone) in str(refusal.value)

    # The refusal has to reach the consumers, not just `paths` — and it has to
    # reach them before anything is created anywhere.
    for ask in (tile_module.tile_dir, discovery_scoring.view_dir, ledgers.ledger_root):
        with pytest.raises(paths.ArtifactsRootMissing):
            ask()
    assert not gone.exists()


def test_the_local_file_configures_it_and_the_variable_wins(tmp_path, monkeypatch):
    """The file is what a machine sets; the variable is for a one-off and a test."""
    from_file = tmp_path / "from_file"
    from_file.mkdir()
    settings = tmp_path / paths.LOCAL_SETTINGS_NAME
    settings.write_text(
        f"{paths.ARTIFACTS_ROOT_KEY} = {json.dumps(str(from_file))}\n", encoding="utf-8"
    )
    monkeypatch.setattr(paths, "local_settings_path", lambda: settings)
    monkeypatch.delenv(paths.ARTIFACTS_ROOT_VARIABLE, raising=False)
    assert paths.artifacts_root() == from_file

    from_variable = tmp_path / "from_variable"
    from_variable.mkdir()
    monkeypatch.setenv(paths.ARTIFACTS_ROOT_VARIABLE, str(from_variable))
    assert paths.artifacts_root() == from_variable


def test_a_stored_name_rehomes_from_either_spelling(relocated):
    """Both spellings a record can carry reduce to the file that is actually there."""
    below = "tiles/cache/4368512555980148/t00.jpg"
    assert paths.rehome(f"C:/somewhere/else/artifacts/{below}") == relocated / below
    assert paths.rehome(f"{paths.ARTIFACTS_NAME}/{below}") == relocated / below
    assert paths.rehome(f"D:\\older\\{paths.ARTIFACTS_NAME}\\{below}") == relocated / below


def test_rehome_says_nothing_about_what_is_not_ours(relocated):
    """A path with no artifacts component gets `None`, so a caller keeps its own bytes.

    Handing the input back through `Path` would re-spell it in this platform's
    separator, which is a silent edit to a record that named a file somewhere
    else entirely.
    """
    assert paths.rehome("data/anchors.jsonl") is None
    assert paths.rehome("C:/somewhere/else/cache/t00.jpg") is None


def test_a_record_spells_the_tree_the_same_wherever_it_is(tmp_path, monkeypatch):
    """The name that is a sidecar key does not change when the disk does."""
    monkeypatch.delenv(paths.ARTIFACTS_ROOT_VARIABLE, raising=False)
    monkeypatch.setattr(paths, "local_settings_path", lambda: tmp_path / "absent.toml")
    in_checkout = paths.tracked_name(paths.artifacts_root() / "harvest_run3" / "walk.jsonl")

    root = tmp_path / "elsewhere" / paths.ARTIFACTS_NAME
    root.mkdir(parents=True)
    monkeypatch.setenv(paths.ARTIFACTS_ROOT_VARIABLE, str(root))
    relocated_name = paths.tracked_name(root / "harvest_run3" / "walk.jsonl")

    assert relocated_name == in_checkout == "artifacts/harvest_run3/walk.jsonl"


def test_a_manifest_written_on_another_disk_still_names_files(relocated):
    """The million stored paths a tile manifest carries, read after a move."""
    manifest = relocated / "tiles" / "manifest.jsonl"
    manifest.parent.mkdir(parents=True)
    row = {
        "schema": tile_module.SCHEMA,
        "location_id": 1,
        "tile": 0,
        "path": "C:/an/older/checkout/artifacts/tiles/cache/1/t00.jpg",
        "level": "antialiased",
        "scale": 1.0,
        "shift_frac": 0.0,
        "partial": False,
    }
    manifest.write_text(json.dumps(row) + "\n", encoding="utf-8", newline="\n")

    (read,) = tile_module.read_manifest()
    assert paths.Path(read["path"]) == relocated / "tiles" / "cache" / "1" / "t00.jpg"
    assert tile_module.canonical_of([read])["path"] == read["path"]


def test_the_command_line_follows_the_tree_out_and_back(relocated):
    """A default of `artifacts/walk` lands on the disk the tree is on, and prints short."""
    resolved = cli.resolve_output(str(paths.Path(paths.ARTIFACTS_NAME) / "walk"))
    assert resolved == relocated / "walk"
    assert cli.display_path(resolved) == "artifacts/walk"
    assert cli.resolve_output("data") == paths.repo_root() / "data"


def test_a_binding_recorded_before_the_move_still_resolves_after_it(relocated):
    """A curation run plan names its ledgers, and a resume compares those names.

    Both halves have to hold across a move: the name a fresh resolve produces has
    to equal the one the plan recorded, and the recorded one has to still find
    the file. Miss either and `curate --resume` refuses a run it planned itself.
    """
    ledger = relocated / "harvest_run3" / ledgers.LEDGER_NAME
    ledger.parent.mkdir(parents=True)
    ledger.write_text("", encoding="utf-8")

    recorded = "artifacts/harvest_run3/walk.jsonl"
    assert binding.label(ledger) == recorded
    assert binding.anchored(recorded) == ledger
    assert binding.label(binding.anchored(recorded)) == recorded


def test_the_command_line_reports_the_refusal_instead_of_a_traceback(tmp_path, monkeypatch, capsys):
    """Any subcommand can raise it, so `main` catches it — once, for all of them.

    The message is an instruction, and an operator who has to read a stack trace
    to reach it reads past the part that says nothing fell back to the checkout.
    """
    monkeypatch.setenv(paths.ARTIFACTS_ROOT_VARIABLE, str(tmp_path / "unplugged"))
    assert cli.main(["census"]) == 1
    printed = capsys.readouterr().out
    assert "unplugged" in printed
    assert "Nothing falls back to the checkout" in printed
