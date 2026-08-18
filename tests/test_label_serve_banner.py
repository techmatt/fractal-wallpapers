"""What the server says when it starts, and that anyone can actually read it.

The rig is launched into the background and its stdout redirected to a log, which
is the one mode where an unflushed banner is invisible: a redirected stream is
block-buffered, the banner is some sixty bytes, and the process does not exit
until it is killed. So the URL was printed to a buffer nobody ever read, and
finding the port meant probing the server to discover it was already up.

The banner is also the answer to the two questions a labeler has before typing
into the page — which sheet is this, and where do my verdicts land — because the
alternative was reading four source files to work out the export name.
"""

from __future__ import annotations

import io
from pathlib import Path

from fractal_wallpapers.labeling import server


class RecordingStream(io.StringIO):
    """A stdout that remembers how much of itself has actually been flushed.

    `flushed` is what a redirected log file would hold right now. Anything
    written but not flushed is still in the buffer, which is exactly the state
    this file exists to rule out.
    """

    def __init__(self) -> None:
        super().__init__()
        self.flushed = ""

    def flush(self) -> None:
        self.flushed = self.getvalue()
        super().flush()


class DoneServer:
    """A bound server that stops the moment it is asked to run, and reports what
    a log would have shown by then."""

    def __init__(self, stream: RecordingStream) -> None:
        self.server_address = ("127.0.0.1", 8021)
        self.stream = stream
        self.closed = False
        self.readable_when_running = ""

    def serve_forever(self) -> None:
        self.readable_when_running = self.stream.flushed
        raise KeyboardInterrupt

    def server_close(self) -> None:
        self.closed = True


def run(monkeypatch, banner=()) -> DoneServer:
    """Start and immediately stop a server, capturing what it printed."""
    stream = RecordingStream()
    bound = DoneServer(stream)
    monkeypatch.setattr(server, "bind", lambda *_args, **_kwargs: bound)
    monkeypatch.setattr("sys.stdout", stream)
    server.serve(Path("artifacts/sheet"), banner=banner)
    assert bound.closed, "the port is given back even when the run ends by interrupt"
    bound.printed = stream.getvalue()
    return bound


def test_the_url_is_readable_while_the_server_is_still_running(monkeypatch) -> None:
    """The bug this file exists for. Backgrounded with stdout redirected, an
    unflushed banner reaches the log only when the process exits — and a server
    that runs until it is killed never exits, so the URL was never readable at
    the one time it was wanted."""
    bound = run(monkeypatch, banner=["location · twin · 96 units", "labels -> labels/x.json"])
    log = bound.readable_when_running
    assert "http://127.0.0.1:8021/" in log, "the URL, before the process ends"
    assert "location · twin · 96 units" in log
    assert "labels -> labels/x.json" in log


def test_the_banner_names_the_url_and_then_the_sheet(monkeypatch) -> None:
    """The URL is the thing being looked for, so it comes first; what the sheet
    is follows it, indented under it."""
    bound = run(monkeypatch, banner=["location · twin · 96 units", "labels -> labels/x.json"])
    lines = bound.printed.splitlines()
    assert lines[0].startswith("serving ")
    assert lines[1].strip() == "-> http://127.0.0.1:8021/"
    assert lines[2].strip() == "location · twin · 96 units"
    assert lines[3].strip() == "labels -> labels/x.json"


def test_a_server_told_nothing_about_the_sheet_still_starts(monkeypatch) -> None:
    """The banner is the caller's to compose — this module serves a directory and
    deliberately does not know which kind of sheet it is handing over."""
    bound = run(monkeypatch)
    assert "http://127.0.0.1:8021/" in bound.readable_when_running
