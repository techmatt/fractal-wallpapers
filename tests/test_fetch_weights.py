"""`fetch-weights` reports what it could not get, rather than dying on head one.

It is the first command `README.md` tells a fresh clone to run, and the releases
it resolves are cut by hand — so one head missing while the rest are there is the
ordinary state and not a rare one. On 2026-09-14 a clean clone ran it and got an
uncaught `HTTPError: 404` on the first head in alphabetical order, learned nothing
about the other two, and read a stack trace instead of an instruction.

What these pin is the reporting, not the network: every case here fakes
`urlretrieve`, because what went wrong was never the download.
"""

from __future__ import annotations

import argparse
import json
import urllib.error

import pytest

from fractal_wallpapers.cli import weights_commands
from fractal_wallpapers.models import roster


@pytest.fixture
def manifest(tmp_path, monkeypatch):
    """Three heads in a manifest of our own, and a `models/` tree of our own."""
    root = tmp_path
    (root / "models").mkdir()
    document = {
        "schema": 1,
        "heads": {
            name: {
                "tag": f"weights-v{index}",
                "asset": f"{name}.fp16.pt",
                "sha256": "0" * 64,
                "bytes": 4,
                "precision": "fp16",
                "run": "a_run",
                "source_commit": "c" * 40,
                "provenance": {"supervision": "human verdicts", "corpus": "data/x"},
            }
            for index, name in enumerate(("alpha", "beta", "gamma"), start=1)
        },
    }
    path = root / "models" / "weights.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(weights_commands, "manifest_path", lambda: path)
    monkeypatch.setattr(weights_commands, "repo_root", lambda: root)
    return root


def args(head=None, check=False):
    return argparse.Namespace(head=head, check=check, verify_release=False)


def refusing(codes: dict):
    """A `urlretrieve` that fails the named heads and writes a file for the rest."""

    def fake(url, destination):
        for name, code in codes.items():
            if f"/{name}.fp16.pt" in url:
                raise urllib.error.HTTPError(url, code, "Not Found", {}, None)
        destination.write_bytes(b"ok!\n")

    return fake


def test_a_missing_release_does_not_stop_the_other_heads(manifest, monkeypatch, capsys):
    """★ The defect. `alpha` 404s and `beta` and `gamma` were never attempted."""
    monkeypatch.setattr(weights_commands.urllib.request, "urlretrieve", refusing({"alpha": 404}))
    monkeypatch.setattr(weights_commands, "sha256_of", lambda _path: "0" * 64)

    code = weights_commands.fetch_weights(args())

    said = capsys.readouterr().out
    assert code == 1, "a head that did not arrive is a non-zero exit"
    assert "beta: verified" in said and "gamma: verified" in said
    assert "2 of 3 head(s) present" in said


def test_the_refusal_names_the_tag_the_asset_and_the_url(manifest, monkeypatch, capsys):
    """Each of the three is a different repair by a different person: an uncut
    release, an asset that was never uploaded or was renamed, or this machine's
    network. `HTTPError: 404` says which of those to nobody."""
    monkeypatch.setattr(weights_commands.urllib.request, "urlretrieve", refusing({"beta": 404}))
    monkeypatch.setattr(weights_commands, "sha256_of", lambda _path: "0" * 64)

    weights_commands.fetch_weights(args())

    said = capsys.readouterr().out
    assert "weights-v2" in said and "beta.fp16.pt" in said
    assert "https://github.com/techmatt/fractal-wallpapers/releases/download/" in said
    assert "has not been cut" in said


def test_a_download_that_hashes_wrong_is_removed_and_the_rest_still_run(
    manifest, monkeypatch, capsys
):
    """A file that is not what the manifest describes is worse than no file: it
    would be scored through and believed. It goes, and the leg carries on."""
    monkeypatch.setattr(weights_commands.urllib.request, "urlretrieve", refusing({}))
    monkeypatch.setattr(weights_commands, "sha256_of", lambda _path: "f" * 64)

    code = weights_commands.fetch_weights(args())

    said = capsys.readouterr().out
    assert code == 1
    assert said.count("hashes to") == 3
    for name in ("alpha", "beta", "gamma"):
        assert not (manifest / "models" / name / f"{name}.fp16.pt").exists()


def test_a_head_that_is_not_in_the_manifest_is_said_so(manifest, capsys):
    assert weights_commands.fetch_weights(args(head="delta")) == 1
    assert "not a head" in capsys.readouterr().out


def test_the_check_covers_every_head_the_roster_names():
    """The dry run a release is cut after, on the real manifest. It is what
    `pip install -e .` runs before a clone has any reason to own torch, so a head
    added to the roster without a manifest row is caught here rather than by a
    404 six commands later."""
    document = json.loads(roster.manifest_path().read_text(encoding="utf-8"))

    assert set(roster.HEADS) <= set(document["heads"]), (
        "a head on the roster with no manifest row is a release that would omit it"
    )
    for name in roster.HEADS:
        row = document["heads"][name]
        for field in weights_commands.REQUIRED_FIELDS:
            assert field in row, f"{name} names no {field}"


# --------------------------------------------------------------------------- #
# One package, one tag — the failure the single release introduced.
# --------------------------------------------------------------------------- #
def test_a_head_left_on_an_older_tag_is_a_gap(manifest, capsys):
    """★ The failure per-head numbering could not have had.

    Four heads on four tags is fine when each has its own release. One dated
    package means a row left behind 404s while the other three come down clean,
    so a clone gets three working judges and one that does not exist — and the
    only symptom is an exit code somebody has to read. Caught in `--check`, which
    is the dry run a release is cut after and where the repair is a manifest edit
    rather than a download.
    """
    document = json.loads((manifest / "models" / "weights.json").read_text(encoding="utf-8"))
    for name, entry in document["heads"].items():
        entry["tag"] = roster.TAG if name != "beta" else "weights-v1"
    (manifest / "models" / "weights.json").write_text(json.dumps(document), encoding="utf-8")

    assert weights_commands.check_weights(document) == 1

    said = capsys.readouterr().out
    assert "3 different tags" in said or "2 different tags" in said
    assert roster.TAG in said


def test_one_tag_passes_the_guard(manifest, capsys):
    document = json.loads((manifest / "models" / "weights.json").read_text(encoding="utf-8"))
    for entry in document["heads"].values():
        entry["tag"] = roster.TAG

    weights_commands.check_weights(document)

    assert "different tags" not in capsys.readouterr().out


def test_the_shipped_manifest_names_exactly_one_tag_and_it_is_the_rosters():
    """The real manifest, which is what a clone resolves. `roster.TAG` is the one
    spelling — `ship`, `gallery_grade_train` and every `--tag` default read it —
    so a row that disagrees means a stage wrote a release nothing points at."""
    document = json.loads(roster.manifest_path().read_text(encoding="utf-8"))
    tags = {entry["tag"] for entry in document["heads"].values()}

    assert tags == {roster.TAG}
    assert len(document["heads"]) == len(roster.HEADS)


def test_the_tag_is_dated_and_never_reused():
    """Dated rather than numbered, which is the decision of 2026-09-14: a head's
    version history is its sha256 and this file's git history, and a number
    implies a sequence a reader has to trace back. The shape is asserted because
    the rule that a published tag is never moved only means anything if the next
    package gets a different name, and a date is what guarantees that."""
    import re

    assert re.fullmatch(r"weights-\d{4}-\d{2}-\d{2}", roster.TAG), roster.TAG


def test_every_ship_verb_defaults_to_the_one_tag():
    """Four heads ship and three of them wrote the tag out by hand, so the day the
    scheme changed it had to be found in four places and was found in two.
    `common.tag_flag` is the one definition and this is what holds them to it."""
    from fractal_wallpapers import cli
    from fractal_wallpapers.models import gallery_grade_train, ship

    assert ship.TAG == gallery_grade_train.TAG == roster.TAG

    parser = cli.build_parser()
    top = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    found = 0
    for group, verbs in (("head", "ship"), ("palette", "ship"), ("renders", "ship")):
        steps = next(
            a for a in top.choices[group]._actions if isinstance(a, argparse._SubParsersAction)
        )
        tag = next(a for a in steps.choices[verbs]._actions if a.dest == "tag")
        assert tag.default == roster.TAG, f"{group} {verbs} defaults to {tag.default}"
        found += 1
    assert found == 3


def test_verify_release_clones_the_public_url_and_not_the_push_remote():
    """What is being verified is what a stranger gets, and a stranger has no
    deploy key. A `git@` default would pass on this machine and on no other."""
    assert weights_commands.PUBLIC_REPO.startswith("https://")
    assert "git@" not in weights_commands.PUBLIC_REPO
