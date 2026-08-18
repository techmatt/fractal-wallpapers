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


#: How often a serving thread looks for the stop it has been sent. The default is
#: half a second, and `shutdown` waits for the thread to notice — which in a file
#: of small request tests is longer than everything else in it put together.
POLL = 0.01


@pytest.fixture
def serving(tmp_path):
    """Bind a rig on the loopback address and hand back the URL to reach it at.

    A factory rather than a server, because one test here wants a plain static
    server in place of the rig's own handler and everything about starting and
    stopping it is the same.
    """
    running = []

    def serve(handler_class=server.SheetHandler) -> str:
        handler = functools.partial(handler_class, directory=str(tmp_path))
        bound = server.ExclusiveServer((server.DEFAULT_HOST, 0), handler)
        thread = threading.Thread(
            target=bound.serve_forever, kwargs={"poll_interval": POLL}, daemon=True
        )
        thread.start()
        running.append((bound, thread))
        return f"http://{server.DEFAULT_HOST}:{bound.server_address[1]}"

    try:
        yield serve
    finally:
        for bound, thread in running:
            bound.shutdown()
            bound.server_close()
            thread.join(timeout=5)


@pytest.fixture
def rig(drop, serving):
    """The labeling rig itself, serving, with its export directory redirected."""
    return serving()


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
def test_every_sheet_names_a_head_on_the_roster() -> None:
    """The export's name comes off the manifest, so it cannot be generic."""
    assert sheets.LOCATION_HEAD in HEADS
    assert all(head in HEADS for head in sheets.FINISHED_RUBRIC)


def test_the_page_takes_its_export_name_from_the_head_and_the_sheet() -> None:
    assert 'a.download = "labels.json"' not in PAGE
    assert "export_control.js" in PAGE, "the page has its own copy of the export decision"
    assert "labelExport.save(MANIFEST.head, MANIFEST.batch, out)" in PAGE


def test_one_page_serves_both_row_sources() -> None:
    """A location row hands over two pictures and a finished-render row one. A
    second page is a second answer to what an export is called."""
    assert "row.pictures" in PAGE
    assert "MANIFEST.tiers" in PAGE and "MANIFEST.rubric" in PAGE


def test_the_export_control_is_one_file_and_says_both_halves() -> None:
    assert 'return sheet ? head + "." + sheet + ".json" : head + ".json";' in CONTROL
    assert '"/labels/" + name' in CONTROL
    assert "download(head, sheet, payload)" in CONTROL, (
        "there is no path that leaves the labeler stuck"
    )


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
    assert server.target_of_save("/labels/strange_render.json") == ("strange_render", "")
    assert server.target_of_save("/labels/location.plane_deep.json") == ("location", "plane_deep")
    assert server.target_of_save("/labels/labels.json") is None
    assert server.target_of_save("/labels/smooth_render.png") is None
    assert server.target_of_save("/sheet.json") is None


def test_a_static_server_still_gets_the_named_download(drop, serving) -> None:
    """The fallback is a slower path to the same file, not a different outcome."""
    base = serving(http.server.SimpleHTTPRequestHandler)
    status, _ = put(base, "/labels/smooth_render.json", {"u0001": {"score": 3}})
    assert status in (405, 501), "a dumb static server refuses the save, and the page downloads"
