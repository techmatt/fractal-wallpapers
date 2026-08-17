"""Where a labeling page's export goes, and what it is called.

Both halves are one decision and it is easy to get wrong in a way nobody notices
for an hour: a generic `labels.json` is two sheets exporting over each other in a
download directory, and an export that only ever reaches the download directory
is a session that ends with a step somebody has to remember. So the name is the
head, the rig writes the drop itself, and the download is the fallback rather
than the design.
"""

from __future__ import annotations

import functools
import http.server
import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from fractal_wallpapers.labeling import intake, server, sheets, store
from fractal_wallpapers.models.roster import HEADS

PAGE = Path(server.PAGE).read_text(encoding="utf-8")
CONTROL = Path(server.CONTROL).read_text(encoding="utf-8")


@pytest.fixture
def drop(tmp_path, monkeypatch):
    directory = tmp_path / "labels"
    monkeypatch.setattr(store, "export_dir", lambda: directory)
    return directory


@pytest.fixture
def rig(tmp_path, drop):
    """A bound rig on the loopback address, and the base URL to reach it at."""
    handler = functools.partial(server.SheetHandler, directory=str(tmp_path))
    bound = server.ExclusiveServer((server.DEFAULT_HOST, 0), handler)
    thread = threading.Thread(target=bound.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://{server.DEFAULT_HOST}:{bound.server_address[1]}"
    finally:
        bound.shutdown()
        bound.server_close()
        thread.join(timeout=5)


def put(base: str, path: str, payload) -> tuple[int, str]:
    request = urllib.request.Request(
        base + path,
        method="PUT",
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as answer:
            return answer.status, answer.read().decode("utf-8")
    except urllib.error.HTTPError as refused:
        return refused.code, refused.read().decode("utf-8")


# --------------------------------------------------------------------------- #
# The name.
# --------------------------------------------------------------------------- #
def test_a_sheet_names_the_head_it_was_cut_for() -> None:
    """The export's name comes off the manifest, so it cannot be generic."""
    assert sheets.HEAD in HEADS


def test_the_page_takes_its_export_name_from_the_head_and_never_a_generic_one() -> None:
    assert 'a.download = "labels.json"' not in PAGE
    assert "export_control.js" in PAGE, "the page has its own copy of the export decision"
    assert 'const HEAD = "location"' in PAGE
    assert "labelExport.save(head, out)" in PAGE


def test_the_export_control_is_one_file_and_says_both_halves() -> None:
    assert 'return head + ".json";' in CONTROL
    assert '"/labels/" + name' in CONTROL
    assert "download(head, payload)" in CONTROL, "there is no path that leaves the labeler stuck"


# --------------------------------------------------------------------------- #
# The endpoint.
# --------------------------------------------------------------------------- #
def test_the_rig_writes_the_drop_itself(rig, drop) -> None:
    status, body = put(rig, "/labels/smooth_render.json", {"u0001": {"score": 3, "revealed": 0}})
    assert status == 200
    assert json.loads(body)["units"] == 1
    assert intake.read_export(drop / "smooth_render.json") == {"u0001": 3}


def test_a_save_that_would_lose_a_verdict_is_refused_and_says_so(rig, drop) -> None:
    put(rig, "/labels/smooth_render.json", {"u0001": {"score": 3}, "u0002": {"score": 2}})
    held = (drop / "smooth_render.json").read_bytes()
    status, body = put(rig, "/labels/smooth_render.json", {"u0001": {"score": 3}})
    assert status == 409, body
    assert (drop / "smooth_render.json").read_bytes() == held


def test_the_endpoint_writes_one_name_per_head_and_nothing_else(rig, drop) -> None:
    for path in ("/labels/nobody.json", "/labels/../escape.json", "/sheet.jsonl"):
        status, _ = put(rig, path, {"u0001": {"score": 3}})
        assert status == 404, path
    assert not drop.exists() or not list(drop.iterdir())


def test_a_body_that_is_not_an_export_is_refused(rig, drop) -> None:
    request = urllib.request.Request(
        rig + "/labels/location.json", method="PUT", data=b"not json at all"
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as answer:
            status = answer.status
    except urllib.error.HTTPError as refused:
        status = refused.code
    assert status == 400


def test_the_page_and_the_control_are_served_by_the_rig(rig) -> None:
    for path, expected in (("/", "<title>"), ("/export_control.js", "labelExport")):
        with urllib.request.urlopen(rig + path, timeout=10) as answer:
            assert expected in answer.read().decode("utf-8"), path


def test_a_head_name_is_read_off_the_roster(tmp_path) -> None:
    assert server.head_of_save("/labels/strange_render.json") == "strange_render"
    assert server.head_of_save("/labels/labels.json") is None
    assert server.head_of_save("/labels/smooth_render.png") is None
    assert server.head_of_save("/sheet.json") is None


def test_a_static_server_still_gets_the_named_download(tmp_path, drop) -> None:
    """The fallback is a slower path to the same file, not a different outcome."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp_path))
    bound = server.ExclusiveServer((server.DEFAULT_HOST, 0), handler)
    thread = threading.Thread(target=bound.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://{server.DEFAULT_HOST}:{bound.server_address[1]}"
        status, _ = put(base, "/labels/smooth_render.json", {"u0001": {"score": 3}})
        assert status in (405, 501), "a dumb static server refuses the save, and the page downloads"
    finally:
        bound.shutdown()
        bound.server_close()
        thread.join(timeout=5)
