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
the sheet directory; `/` is the rig page, read out of the package. A server
rooted at the repository would work just as well and would also serve every file
in the checkout to anything that can reach the port.
"""

from __future__ import annotations

import functools
import http.server
import socket
import socketserver
import sys
from pathlib import Path
from urllib.parse import urlsplit

PAGE = Path(__file__).with_name("page.html")

#: Where the rig lands by default. Nothing is bound outside the loopback address:
#: a labeling page is a local tool and has no business on a network interface.
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8010
PORT_SCAN = 20


class SheetHandler(http.server.SimpleHTTPRequestHandler):
    """The sheet directory, with `/` answered by the packaged page."""

    def translate_path(self, path: str) -> str:
        relative = urlsplit(path).path
        if relative in ("/", "/index.html", "/page.html"):
            return str(PAGE)
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
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "PAGE",
    "PORT_SCAN",
    "ExclusiveServer",
    "SheetHandler",
    "bind",
    "serve",
]
