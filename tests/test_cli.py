"""The command line is the project's only entry point, so it is smoke-tested here."""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers import cli


def test_every_runnable_thing_is_a_subcommand() -> None:
    parser = cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_fetch_weights_is_registered() -> None:
    args = cli.build_parser().parse_args(["fetch-weights"])
    assert args.handler is cli.fetch_weights


def test_weights_manifest_is_valid_and_versioned() -> None:
    manifest_path = cli.repo_root() / cli.WEIGHTS_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema"] == 1
    assert isinstance(manifest["heads"], dict)
