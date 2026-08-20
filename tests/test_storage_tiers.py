"""Guard: the regenerable tree spans two disks, and never lies about which one.

`artifacts/` is a hundred gigabytes of things a run can always make again. It
lives on two tiers — a hot one where work happens and every write lands, and an
archive on slow bulk storage for what is finished with — and a top-level name is
in exactly one of them. The whole mechanism is `paths`: two settings, a `Tiers`
snapshot that says where a name is, `rehome` to read a stored name against it,
`tracked_name` to write one, plus every consumer asking through `under` instead
of building a path out of `repo_root()`.

Four failures are what these tests are actually about:

* **A silent fallback.** If a configured root is missing — an external disk left
  unplugged — and the code quietly used `artifacts/` under the checkout instead,
  it would find an empty tree. Every cache here reads absence as "not built
  yet", so that does not look like a missing disk; it looks like work that was
  never done, and the next command spends hours redoing it on the wrong drive.

* **A name that moved.** A ledger's name is the key curation's sidecar keeps its
  scored rows under. Spell it one way hot and another way archived and every
  stored row becomes unmatchable, so a re-score adds duplicates beside rows it
  was supposed to replace. `tracked_name` is what keeps both spellings the same,
  and it is tested here rather than trusted.

* **Two copies, one name.** The failure a two-tier store has that nobody sees:
  a subtree left in both tiers, one of them stale, one of them silently winning.
  Refused at resolution, not resolved by preference.

* **A training pass against the archive.** Not wrong, just an order of magnitude
  slower with no symptom other than a job that looks like it hung. The rule
  "restore before you train" is in the tool.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers import cli, paths, storage
from fractal_wallpapers.curation import binding
from fractal_wallpapers.curation import intake as curation_intake
from fractal_wallpapers.curation import run as curation_run
from fractal_wallpapers.discovery import scoring as discovery_scoring
from fractal_wallpapers.models import palette_corpus, regime_flips, renders
from fractal_wallpapers.models import tiles as tile_module
from fractal_wallpapers.supply import ledgers


@pytest.fixture
def tiered(tmp_path, monkeypatch):
    """Both tiers somewhere that is not the checkout, and the package on them."""
    hot = tmp_path / "fast" / paths.ARTIFACTS_NAME
    archive = tmp_path / "slow" / paths.ARTIFACTS_NAME
    hot.mkdir(parents=True)
    archive.mkdir(parents=True)
    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(hot))
    monkeypatch.setenv(paths.ARCHIVE_ROOT_VARIABLE, str(archive))
    return hot, archive


def a_subtree(root, name: str, files: int = 12) -> dict[str, bytes]:
    """A small subtree with a nested directory, and what every file holds."""
    written = {}
    for index in range(files):
        where = root / name / ("deep" if index % 3 else "") / f"{index:04d}.jpg"
        where.parent.mkdir(parents=True, exist_ok=True)
        body = f"{name}-{index}".encode() * (index + 1)
        where.write_bytes(body)
        written[where.relative_to(root / name).as_posix()] = body
    return written


# --------------------------------------------------------------------------- #
# The settings.
# --------------------------------------------------------------------------- #
def test_the_default_is_the_checkout(monkeypatch):
    """Nothing configured is the case CI and a fresh clone are in."""
    monkeypatch.delenv(paths.HOT_ROOT_VARIABLE, raising=False)
    monkeypatch.delenv(paths.ARCHIVE_ROOT_VARIABLE, raising=False)
    monkeypatch.setattr(paths, "local_settings_path", lambda: paths.repo_root() / "absent.toml")
    assert paths.hot_root() == paths.repo_root() / paths.ARTIFACTS_NAME
    assert paths.archive_root() is None
    assert paths.under("tiles") == paths.repo_root() / paths.ARTIFACTS_NAME / "tiles"


def test_the_local_file_configures_it_and_the_variable_wins(tmp_path, monkeypatch):
    """The file is what a machine sets; the variable is for a one-off and a test."""
    from_file = tmp_path / "from_file"
    from_file.mkdir()
    settings = tmp_path / paths.LOCAL_SETTINGS_NAME
    settings.write_text(
        f"{paths.HOT_ROOT_KEY} = {json.dumps(str(from_file))}\n"
        f"{paths.ARCHIVE_ROOT_KEY} = {json.dumps(str(tmp_path / 'cold'))}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(paths, "local_settings_path", lambda: settings)
    monkeypatch.delenv(paths.HOT_ROOT_VARIABLE, raising=False)
    monkeypatch.delenv(paths.ARCHIVE_ROOT_VARIABLE, raising=False)
    assert paths.hot_root() == from_file
    assert paths.archive_root() == tmp_path / "cold"

    from_variable = tmp_path / "from_variable"
    from_variable.mkdir()
    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(from_variable))
    assert paths.hot_root() == from_variable

    # Set to nothing is a statement, not an omission: this machine has no
    # archive, whatever the file says. It is the escape a hot-only session uses.
    monkeypatch.setenv(paths.ARCHIVE_ROOT_VARIABLE, "")
    assert paths.archive_root() is None


def test_the_single_root_this_pair_replaced_is_refused(tmp_path, monkeypatch):
    """A machine still spelling the old key meant to put the tree *somewhere*."""
    settings = tmp_path / paths.LOCAL_SETTINGS_NAME
    settings.write_text(f'{paths.RETIRED_ROOT_KEY} = "{tmp_path.as_posix()}"\n', encoding="utf-8")
    monkeypatch.setattr(paths, "local_settings_path", lambda: settings)
    monkeypatch.delenv(paths.HOT_ROOT_VARIABLE, raising=False)
    with pytest.raises(paths.ArtifactsRootMissing) as refusal:
        paths.hot_root()
    assert paths.HOT_ROOT_KEY in str(refusal.value)
    assert paths.ARCHIVE_ROOT_KEY in str(refusal.value)


def test_a_missing_hot_root_refuses_rather_than_falling_back(tmp_path, monkeypatch):
    """The unplugged-disk case. It must not become an empty tree in the checkout."""
    gone = tmp_path / "unplugged" / paths.ARTIFACTS_NAME
    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(gone))
    monkeypatch.setenv(paths.ARCHIVE_ROOT_VARIABLE, "")
    with pytest.raises(paths.ArtifactsRootMissing) as refusal:
        paths.hot_root()
    assert str(gone) in str(refusal.value)

    # The refusal has to reach the consumers, not just `paths` — and it has to
    # reach them before anything is created anywhere.
    for ask in (tile_module.tile_dir, discovery_scoring.view_dir, palette_corpus.cache_dir):
        with pytest.raises(paths.ArtifactsRootMissing):
            ask()
    assert not gone.exists()


# --------------------------------------------------------------------------- #
# Resolution: hot first, archive fallback, collision refused.
# --------------------------------------------------------------------------- #
def test_every_consumer_follows_the_tiers(tiered):
    """One funnel, one rule: no module builds its own path out of a root."""
    hot, archive = tiered
    (archive / "tiles").mkdir()
    (archive / "palette").mkdir()
    where = {
        "tiles": tile_module.tile_dir(),
        "tile cache": tile_module.cache_root(),
        "palette": palette_corpus.cache_dir(),
        "location views": discovery_scoring.view_dir(),
        "renders": renders.cache_dir("smooth_render"),
        "curation": curation_intake.store_dir(),
        "a curation run": curation_run.run_dir("r"),
        "regime flips": regime_flips.study_dir(),
    }
    strays = {
        name: path
        for name, path in where.items()
        if hot not in path.parents and archive not in path.parents
    }
    assert not strays, f"these did not follow either tier: {strays}"

    # The two that exist are archived; everything else does not exist yet, and
    # what does not exist yet resolves where writes land.
    assert archive in where["tiles"].parents
    assert archive in where["palette"].parents
    assert hot in where["location views"].parents


def test_an_archived_subtree_reads_through_and_a_new_one_lands_hot(tiered):
    """The two halves of the rule, on the same tree at the same time."""
    hot, archive = tiered
    a_subtree(archive, "harvest_run3")
    a_subtree(hot, "curation")
    assert paths.under("harvest_run3") == archive / "harvest_run3"
    assert paths.under("curation") == hot / "curation"
    assert paths.under("nothing_here_yet") == hot / "nothing_here_yet"
    assert paths.under("harvest_run3", "deep", "0001.jpg").is_file()


def test_one_name_in_both_tiers_is_refused_and_named(tiered):
    """The failure nobody sees: two copies, one stale, one silently winning."""
    hot, archive = tiered
    a_subtree(hot, "tiles")
    a_subtree(archive, "tiles")
    with pytest.raises(paths.TierCollision) as refusal:
        paths.under("tiles")
    assert str(hot / "tiles") in str(refusal.value)
    assert str(archive / "tiles") in str(refusal.value)
    # And it is visible rather than fatal in the one place whose job is to show
    # the state of the tree.
    listing = storage.status(sizes=False)
    assert [row["tier"] for row in listing["units"] if row["name"] == "tiles"] == ["BOTH"]


def test_an_unplugged_archive_refuses_only_what_it_could_have_answered(tiered, monkeypatch):
    """The narrowed refusal: hot-only work proceeds with the disk in a drawer."""
    hot, archive = tiered
    a_subtree(hot, "curation")
    monkeypatch.setenv(paths.ARCHIVE_ROOT_VARIABLE, str(archive.parent / "not_plugged_in"))

    assert paths.under("curation") == hot / "curation"
    assert paths.under("curation", "deep", "0001.jpg").is_file()

    with pytest.raises(paths.ArchiveUnreachable) as refusal:
        paths.under("tiles")
    assert "not_plugged_in" in str(refusal.value)
    assert "tiles" in str(refusal.value)


# --------------------------------------------------------------------------- #
# Names, which say nothing about tiers.
# --------------------------------------------------------------------------- #
def test_a_stored_name_rehomes_from_either_spelling(tiered):
    """Both spellings a record can carry reduce to the file that is actually there."""
    hot, archive = tiered
    (archive / "tiles").mkdir()
    below = "tiles/cache/4368512555980148/t00.jpg"
    assert paths.rehome(f"C:/somewhere/else/artifacts/{below}") == archive / below
    assert paths.rehome(f"{paths.ARTIFACTS_NAME}/{below}") == archive / below
    assert paths.rehome(f"D:\\older\\{paths.ARTIFACTS_NAME}\\{below}") == archive / below


def test_rehome_says_nothing_about_what_is_not_ours(tiered):
    """A path with no artifacts component gets `None`, so a caller keeps its own bytes.

    Handing the input back through `Path` would re-spell it in this platform's
    separator, which is a silent edit to a record that named a file somewhere
    else entirely.
    """
    assert paths.rehome("data/anchors.jsonl") is None
    assert paths.rehome("C:/somewhere/else/cache/t00.jpg") is None


def test_a_record_spells_the_tree_the_same_on_either_tier(tiered):
    """The name that is a sidecar key does not change when the tier does.

    This is the property that makes archiving reversible without touching a
    single record: the tracked name is about the tree, and a tier is about a
    disk.
    """
    hot, archive = tiered
    named = "harvest_run3/walk.jsonl"
    assert paths.tracked_name(hot / named) == f"{paths.ARTIFACTS_NAME}/{named}"
    assert paths.tracked_name(archive / named) == f"{paths.ARTIFACTS_NAME}/{named}"


def test_a_manifest_written_before_the_move_still_names_files(tiered):
    """The million stored paths a tile manifest carries, read after archiving."""
    _, archive = tiered
    manifest = archive / "tiles" / "manifest.jsonl"
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
    assert paths.Path(read["path"]) == archive / "tiles" / "cache" / "1" / "t00.jpg"
    assert tile_module.canonical_of([read])["path"] == read["path"]


def test_the_union_finds_a_ledger_on_either_tier(tiered):
    """Archiving a harvest must not remove its supply from the standing census."""
    hot, archive = tiered
    for root, name in ((hot, "harvest_run9"), (archive, "harvest_run3")):
        (root / name).mkdir(parents=True)
        (root / name / ledgers.LEDGER_NAME).write_text("", encoding="utf-8")
    found = [paths.tracked_name(path) for path in ledgers.ledger_paths()]
    assert found == [
        f"{paths.ARTIFACTS_NAME}/harvest_run3/{ledgers.LEDGER_NAME}",
        f"{paths.ARTIFACTS_NAME}/harvest_run9/{ledgers.LEDGER_NAME}",
    ]


def test_a_binding_recorded_before_the_move_still_resolves_after_it(tiered):
    """A curation run plan names its ledgers, and a resume compares those names.

    Both halves have to hold across a move: the name a fresh resolve produces has
    to equal the one the plan recorded, and the recorded one has to still find
    the file. Miss either and `curate --resume` refuses a run it planned itself.
    """
    _, archive = tiered
    ledger = archive / "harvest_run3" / ledgers.LEDGER_NAME
    ledger.parent.mkdir(parents=True)
    ledger.write_text("", encoding="utf-8")

    recorded = "artifacts/harvest_run3/walk.jsonl"
    assert binding.label(ledger) == recorded
    assert binding.anchored(recorded) == ledger
    assert binding.label(binding.anchored(recorded)) == recorded


# --------------------------------------------------------------------------- #
# The command line.
# --------------------------------------------------------------------------- #
def test_the_command_line_follows_the_tree_out_and_back(tiered):
    """A default of `artifacts/walk` lands on the hot tier, and prints short."""
    hot, _ = tiered
    resolved = cli.resolve_output(str(paths.Path(paths.ARTIFACTS_NAME) / "walk"))
    assert resolved == hot / "walk"
    assert cli.display_path(resolved) == "artifacts/walk"
    assert cli.resolve_output("data") == paths.repo_root() / "data"


def test_output_into_an_archived_subtree_is_refused(tiered):
    """Writes land hot. Writing into the archive would split a subtree in two."""
    _, archive = tiered
    a_subtree(archive, "walk_m")
    with pytest.raises(paths.StorageRefusal) as refusal:
        cli.resolve_output("artifacts/walk_m/next.png")
    assert "storage restore walk_m" in str(refusal.value)


def test_the_command_line_reports_the_refusal_instead_of_a_traceback(tmp_path, monkeypatch, capsys):
    """Any subcommand can raise it, so `main` catches it — once, for all of them.

    The message is an instruction, and an operator who has to read a stack trace
    to reach it reads past the part that says nothing fell back to the checkout.
    """
    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(tmp_path / "unplugged"))
    monkeypatch.setenv(paths.ARCHIVE_ROOT_VARIABLE, "")
    assert cli.main(["census"]) == 1
    printed = capsys.readouterr().out
    assert "unplugged" in printed
    assert "Nothing falls back to the checkout" in printed


# --------------------------------------------------------------------------- #
# Moving a subtree, which is the only thing that changes an answer above.
# --------------------------------------------------------------------------- #
def test_a_round_trip_moves_the_bytes_and_nothing_else(tiered):
    """Hot write, archive, read through, restore, hot read — verified at each step."""
    hot, archive = tiered
    written = a_subtree(hot, "renders", files=30)
    manifest = hot / "renders" / "manifest.jsonl"
    manifest.write_text(
        "".join(
            json.dumps({"schema": 1, "path": f"{paths.ARTIFACTS_NAME}/renders/{name}"}) + "\n"
            for name in sorted(written)
        ),
        encoding="utf-8",
        newline="\n",
    )
    written["manifest.jsonl"] = manifest.read_bytes()

    out = storage.move("renders", to=paths.ARCHIVE, log=lambda _: None)
    assert out["moved"] and out["tier"] == paths.ARCHIVE
    assert out["files"] == len(written)
    assert out["manifest_rows"] == len(written) - 1
    assert not (hot / "renders").exists()
    assert paths.under("renders") == archive / "renders"
    for name, body in written.items():
        assert (archive / "renders" / name).read_bytes() == body

    back = storage.move("renders", to=paths.HOT, log=lambda _: None)
    assert back["moved"] and back["tier"] == paths.HOT
    assert not (archive / "renders").exists()
    assert paths.under("renders") == hot / "renders"
    for name, body in written.items():
        assert (hot / "renders" / name).read_bytes() == body


def test_a_move_that_does_not_verify_deletes_nothing(tiered, monkeypatch):
    """Copy, verify, delete — in that order, so a bad copy costs nothing."""
    hot, archive = tiered
    a_subtree(hot, "palette")

    honest = storage.copy_tree

    def corrupt(source, destination, files, log=None):
        written, seconds = honest(source, destination, files, log=log)
        first = sorted(destination.rglob("*.jpg"))[0]
        first.write_bytes(first.read_bytes() + b"one more byte")
        return written, seconds

    monkeypatch.setattr(storage, "copy_tree", corrupt)
    with pytest.raises(storage.StorageError) as refusal:
        storage.move("palette", to=paths.ARCHIVE, log=lambda _: None)
    assert "Nothing was deleted" in str(refusal.value)
    assert (hot / "palette").is_dir()


def test_a_move_to_the_tier_it_is_already_on_does_nothing(tiered):
    """Idempotent, and says so rather than copying a subtree onto itself."""
    hot, _ = tiered
    a_subtree(hot, "smoke")
    assert storage.move("smoke", to=paths.HOT, log=lambda _: None)["moved"] is False


def test_status_names_every_subtree_its_tier_and_its_size(tiered):
    """One screen. The tier is a fact about where the files are, not a record."""
    hot, archive = tiered
    hot_files = a_subtree(hot, "curation")
    cold_files = a_subtree(archive, "tiles")
    listing = storage.status()
    by_name = {row["name"]: row for row in listing["units"]}
    assert by_name["curation"]["tier"] == paths.HOT
    assert by_name["tiles"]["tier"] == paths.ARCHIVE
    assert by_name["curation"]["files"] == len(hot_files)
    assert by_name["tiles"]["bytes"] == sum(len(body) for body in cold_files.values())
    assert listing["archive_reachable"]


# --------------------------------------------------------------------------- #
# The training guard.
# --------------------------------------------------------------------------- #
def test_training_refuses_an_archived_cache_and_names_the_restore(tiered):
    """ "Restore before you train" lives in the tool, not in anybody's memory."""
    _, archive = tiered
    a_subtree(archive, "tiles")
    with pytest.raises(storage.StorageError) as refusal:
        storage.require_hot(archive / "tiles", what="training the location head")
    assert "storage restore tiles" in str(refusal.value)


def test_training_says_nothing_when_the_cache_is_hot(tiered):
    """The guard is silent in the case it is not about, including 'not built'."""
    hot, _ = tiered
    a_subtree(hot, "tiles")
    storage.require_hot(hot / "tiles", hot / "renders", what="training the location head")
