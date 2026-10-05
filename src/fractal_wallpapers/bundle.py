"""A page that can leave the clone: its HTML, its JSON, and only the pictures it shows.

Every inspection page this package writes — `judges check`, `harvest stats`, `curate
candidate-ledger browse`, a recorded gallery, `curate solve trace` — links the
pictures already on disk by a path relative to the page, which opens here and
nowhere else. Each also takes `--bundle DIR`, which writes the same page into a
folder that holds everything it needs:

```text
DIR/index.html      the page, drawn from page.json
DIR/page.json       exactly what the page shows: rows, scores, which pictures
DIR/pictures/*.jpg  each picture the page shows, re-encoded small
```

No absolute path, no reference outside the folder, nothing fetched. The website
hosts these folders unchanged, so a bundle is held to about a megabyte, and the
picture settings below are what keep it there.
"""

from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path

#: The width every bundled picture is re-encoded at. A tile is drawn at 224 to
#: 260 px, so 384 is sharper than the tile and no larger.
WIDTH = 384

#: JPEG quality for a bundled picture. Fractal detail compresses badly: over thirty
#: seats of a published record, 480 px at 70 averaged 33.7 KB a picture and 384 at
#: 60 averaged 18.5 KB, which is what holds a fifty-picture page near a megabyte.
QUALITY = 60

#: The folder inside a bundle the pictures go to.
PICTURES = "pictures"

#: The parseable twin's name, beside every page.
PAGE_JSON = "page.json"

#: Schema of `page.json`.
SCHEMA = 1


def invoked() -> str:
    """The command line that is running, as a reader would retype it.

    An argument that is an absolute path inside the working directory is spelled
    relative to it, so a page written from a clone's root names no machine's paths.
    """
    here = Path.cwd().resolve()

    def spelled(argument: str) -> str:
        path = Path(argument)
        if not path.is_absolute():
            return argument
        try:
            return path.resolve().relative_to(here).as_posix()
        except ValueError:
            return argument

    return shlex.join(["fractal-wallpapers", *(spelled(a) for a in sys.argv[1:])])


def relative_href(picture, directory: Path) -> str:
    """A picture as a page in `directory` refers to it: relative, forward slashes,
    or a `file://` URL where Windows has no relative spelling (another drive)."""
    resolved = Path(picture).resolve()
    try:
        return Path(os.path.relpath(resolved, Path(directory).resolve())).as_posix()
    except ValueError:
        return resolved.as_uri()


class Pictures:
    """Re-encodes pictures into one bundle's `pictures/`, once each, and names them.

    Names are the source's stem, so a bundled picture can be matched to its
    source by eye; two sources with one stem get a counter rather than one
    overwriting the other.
    """

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self._done: dict[str, str] = {}
        self._names: set[str] = set()

    def href(self, picture) -> str | None:
        """The bundled copy's relative path, made on first ask; `None` for no picture."""
        if picture is None or not Path(picture).is_file():
            return None
        source = str(Path(picture).resolve())
        if source in self._done:
            return self._done[source]
        stem = Path(picture).stem
        name, n = f"{stem}.jpg", 1
        while name in self._names:
            n += 1
            name = f"{stem}_{n}.jpg"
        self._names.add(name)
        target = self.directory / PICTURES / name
        encode(Path(picture), target)
        self._done[source] = f"{PICTURES}/{name}"
        return self._done[source]


def encode(source: Path, target: Path) -> int:
    """One picture re-encoded at `WIDTH` and `QUALITY`. Returns the bytes written."""
    # Inside the call: Pillow is an extra, and `cli.main` names it if it is missing.
    from PIL import Image

    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image = image.convert("RGB")
        if image.width > WIDTH:
            image = image.resize((WIDTH, round(image.height * WIDTH / image.width)), Image.LANCZOS)
        image.save(target, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    return target.stat().st_size


def measure(directory: Path) -> dict:
    """`{files, bytes}` of a bundle, for the line a command prints after writing one."""
    files = [path for path in Path(directory).rglob("*") if path.is_file()]
    return {"files": len(files), "bytes": sum(path.stat().st_size for path in files)}


def said(directory: Path) -> str:
    """One line naming a bundle and its size."""
    size = measure(directory)
    return f"bundle {directory}: {size['files']} file(s), {size['bytes'] / 1e6:.2f} MB"
