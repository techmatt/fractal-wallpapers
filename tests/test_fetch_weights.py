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
    return argparse.Namespace(head=head, check=check)


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
