"""Serving one sheet, to one browser, on one port.

The rig is a local page over local files, so this is a static server and nothing
more. Two things about it are deliberate.

**It binds exclusively.** The standard library's server sets `SO_REUSEADDR`, and
on Windows that lets a *second* launcher bind a port the first already holds;
requests then split between the two processes nondeterministically. If the two
were started from different directories the page shows one unit's canonical
render beside another unit's vivid one, which looks like a rendering bug and is
not. Binding exclusively turns that into a second launcher that fails to start.
If the requested port is taken, it walks upward and prints the port it got.

**It serves the sheet, and the page, and nothing else.** The document root is
the sheet directory; `/` is the rig page, read out of the package. One page
serves both row sources — it reads the manifest for the scale, the rubric and
the order, and each row for its own pictures — so there is nothing here that
knows which kind of sheet it is handing over. A server rooted at the repository
would work just as well and would also serve every file in the checkout to
anything that can reach the port.

**It takes one write, and it is the export.** `PUT /labels/<head>.<sheet>.json`
hands the page's verdicts to [`fractal_wallpapers.labeling.intake.write_export`],
which writes that sheet's drop directly. That is the whole reason the endpoint exists: a
session that ends with a file in a browser's download directory ends with a step
somebody has to remember, and the file is named after whichever sheet was
exported last. The head is checked against the roster, the body is checked as an
export, and nothing else on this server accepts a method other than GET.
"""

from __future__ import annotations

import functools
import http.server
import json
import socket
import socketserver
import sys
from pathlib import Path
from urllib.parse import urlsplit

from fractal_wallpapers.models.roster import HEADS

PAGE = Path(__file__).with_name("page.html")

#: The shared export control every sheet page loads. One file decides what an
#: export is called and where it goes; see [`export_control.js`].
CONTROL = Path(__file__).with_name("export_control.js")

#: Where the rig lands by default. Nothing is bound outside the loopback address:
#: a labeling page is a local tool and has no business on a network interface.
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8010
PORT_SCAN = 20

#: The one path this server writes to, and the only shape of it.
SAVE_PREFIX = "/labels/"


def target_of_save(path: str) -> tuple[str, str] | None:
    """The `(head, sheet)` a save request names, or `None` if it names no head.

    `labels/<head>.<sheet>.json`, and `labels/<head>.json` for a page cut before
    a drop carried its sheet. The head is the part before the first dot because
    no head name holds one and no sheet name may.
    """
    relative = urlsplit(path).path
    if not relative.startswith(SAVE_PREFIX):
        return None
    name = relative[len(SAVE_PREFIX) :]
    if not name.endswith(".json"):
        return None
    head, _, sheet = name[: -len(".json")].partition(".")
    if head not in HEADS or "." in sheet:
        return None
    return head, sheet


class SaveEndpoint:
    """`PUT /labels/<head>.<sheet>.json` writes one sheet's drop. Mixed into a file
    handler.

    Separate from the file serving because the two rigs root their servers at
    different directories and only one of them serves the packaged page — the
    write is the same write in both, and a second copy of it would be a second
    answer to what happens when a payload is short.
    """

    def answer(self, code: int, body: str, kind: str = "text/plain") -> None:
        """Reply with a body rather than a status line.

        The refusals here are sentences, and a status line is latin-1 and one
        line long — an em dash in one raises inside the handler and the labeler
        sees a dropped connection instead of the reason their save was refused.
        """
        encoded = body.encode("utf-8")
        self.send_response(code, "ok" if code < 400 else "refused")
        self.send_header("content-type", f"{kind}; charset=utf-8")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_PUT(self) -> None:  # noqa: N802 — the name http.server dispatches on
        from fractal_wallpapers.labeling import intake

        try:
            length = int(self.headers.get("content-length") or 0)
        except ValueError:
            self.answer(400, "content-length is not a number")
            return
        if not 0 < length <= intake.MAX_EXPORT_BYTES:
            # Answered without reading it, so the connection closes rather than
            # this process holding a body it already decided not to take.
            self.close_connection = True
            self.answer(413, "an export of that size is not a labeling session")
            return
        # Drained before anything is decided: a refusal that leaves the request
        # body in the socket looks like a dropped connection at the browser, and
        # a labeler reads that as "my save vanished".
        raw = self.rfile.read(length)
        target = target_of_save(self.path)
        if target is None:
            self.answer(404, "this server saves labels/<head>.<sheet>.json and nothing else")
            return
        try:
            payload = json.loads(raw.decode("utf-8"))
            path = intake.write_export(target[0], payload, target[1])
        except intake.IntakeError as refusal:
            # 409, not 400: the payload is well formed and the file is the reason.
            self.answer(409, str(refusal))
            return
        except (ValueError, UnicodeDecodeError) as broken:
            self.answer(400, f"that is not an export: {broken}")
            return
        self.answer(200, json.dumps({"path": str(path), "units": len(payload)}), "application/json")


class SheetHandler(SaveEndpoint, http.server.SimpleHTTPRequestHandler):
    """The sheet directory, with `/` answered by the packaged page."""

    def translate_path(self, path: str) -> str:
        relative = urlsplit(path).path
        if relative in ("/", "/index.html", "/page.html"):
            return str(PAGE)
        if relative == f"/{CONTROL.name}":
            return str(CONTROL)
        return super().translate_path(path)

    def log_message(self, fmt: str, *args) -> None:
        del fmt, args  # a static file server narrating every PNG is noise


class ExclusiveServer(socketserver.TCPServer):
    """A server that refuses to share its port rather than co-hosting one."""

    allow_reuse_address = False

    def server_bind(self) -> None:
        if sys.platform == "win32" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def bind(
    directory: Path, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, scan: int = PORT_SCAN
):
    """Bind the first free port at or above `port`. Returns the bound server."""
    handler = functools.partial(SheetHandler, directory=str(directory))
    last = None
    for candidate in range(port, port + max(scan, 0) + 1):
        try:
            return ExclusiveServer((host, candidate), handler)
        except OSError as refusal:
            last = refusal
    raise OSError(f"no free port in [{port}, {port + scan}]: {last}")


def serve(
    directory: Path, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, scan: int = PORT_SCAN
) -> int:
    """Serve `directory` until interrupted."""
    server = bind(Path(directory), host, port, scan)
    bound = server.server_address[1]
    print(f"serving {directory}")
    print(f"  -> http://{host}:{bound}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
    finally:
        server.server_close()
    return 0


__all__ = [
    "CONTROL",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "PAGE",
    "PORT_SCAN",
    "SAVE_PREFIX",
    "ExclusiveServer",
    "SaveEndpoint",
    "SheetHandler",
    "bind",
    "target_of_save",
    "serve",
]
