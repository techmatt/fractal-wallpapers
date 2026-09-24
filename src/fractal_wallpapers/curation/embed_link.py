"""A finished picture with its explorer link written into its metadata, pixels untouched.

The bytes half of `embedded_links_ckpt145`; [`curation.explorer_link`] is the link.
Every field is the one `explorer/stamp.js` in the `fractal-website` checkout writes into
a picture downloaded from the explorer, in the same place and the same bytes, so a
release wallpaper and a download are one kind of file — and one dropped on the
explorer's canvas reopens its view the same way.

## What goes in

* **The tag** — `fractal-explorer <query>`: a PNG `iTXt` chunk under the keyword
  `fractal-explorer`, a JPEG `COM` segment. The explorer's own reader; no host.
* **An XMP packet** whose `dc:source` is the absolute URL — Dublin Core's "a related
  resource from which the described resource is derived", which is what a link that
  draws the picture again is. A PNG `iTXt` under `XML:com.adobe.xmp`, a JPEG `APP1`.
  This is what `exiftool` and an asset manager show.
* **In a JPEG, EXIF** — IFD0's `ImageDescription`, the URL again. It is the field the
  Windows file-properties dialog shows as a picture's Title and Subject.

## What does not move

The compressed image data: every chunk or segment a decoder turns into pixels is the
same bytes in the same order, so the decoded picture is identical, which
`tests/test_embed_link.py` holds by decoding both. Nothing here re-encodes, and nothing
here computes image data, so the rule that Python never renders is untouched.

A file of somebody else's XMP or EXIF keeps it and goes without that half of ours — a
file carries one of each — and a stamp of ours is replaced rather than joined, so
stamping twice leaves one.
"""

from __future__ import annotations

import re
import zlib
from pathlib import Path

from fractal_wallpapers.curation.explorer_link import EXPLORER_URL, url_of

#: What a file of ours says in front of its link, and the PNG keyword it travels under.
TAG = "fractal-explorer"
KEYWORD = "fractal-explorer"

#: The PNG keyword an XMP packet travels under, and what opens a JPEG's XMP and EXIF.
XMP_KEYWORD = "XML:com.adobe.xmp"
XMP_SIGNATURE = b"http://ns.adobe.com/xap/1.0/\x00"
EXIF_SIGNATURE = b"Exif\x00\x00"

#: The TIFF tag `ImageDescription` is.
IMAGE_DESCRIPTION = 0x010E

#: The most a JPEG comment may hold.
COMMENT_LIMIT = 0xFFFF - 2

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

#: An explorer URL, whatever its host: `stamp.js`'s `queryOfUrl`.
EXPLORER_PATH = re.compile(
    r"^[a-z][a-z0-9+.-]*://[^?#\s]*/explorer/(?:index\.html)?\?([^#\s]+)$", re.IGNORECASE
)


class EmbedRefused(ValueError):
    """These bytes cannot carry a link: not a PNG or a JPEG, or a link too long for one."""


def payload_of(query: str) -> str:
    return f"{TAG} {query.strip().removeprefix('?')}"


def link_of(payload: str | None) -> str | None:
    """The query a tag carries, or `None` for a text that is not ours."""
    if not isinstance(payload, str):
        return None
    text = payload.strip()
    if not text.startswith(f"{TAG} "):
        return None
    query = text[len(TAG) + 1 :].strip().removeprefix("?")
    return query or None


def query_of_url(url: str | None) -> str | None:
    if not isinstance(url, str):
        return None
    found = EXPLORER_PATH.match(url.strip())
    return None if found is None else found.group(1)


# --------------------------------------------------------------------------- XMP
def xmp_of(url: str) -> str:
    """The packet `stamp.js`'s `xmpOf` writes, character for character."""
    text = (
        url.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )
    return (
        '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f"<dc:source>{text}</dc:source>"
        "</rdf:Description></rdf:RDF></x:xmpmeta>"
        '<?xpacket end="r"?>'
    )


_ENTITIES = {"amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'"}


def source_of(packet: str | None) -> str | None:
    """The `dc:source` a packet names, unescaped, element or attribute form."""
    if not isinstance(packet, str):
        return None
    found = re.search(r"<dc:source>([^<]*)</dc:source>", packet) or re.search(
        r'\bdc:source="([^"]*)"', packet
    )
    if found is None:
        return None
    return re.sub(r"&(amp|lt|gt|quot|apos);", lambda one: _ENTITIES[one.group(1)], found.group(1))


def _our_xmp(packet: str) -> bool:
    return query_of_url(source_of(packet)) is not None


# -------------------------------------------------------------------------- EXIF
def exif_of(url: str) -> bytes | None:
    """IFD0 with one entry, `ImageDescription`, big-endian; `None` for a non-ASCII URL."""
    if not re.fullmatch(r"[\x20-\x7e]*", url):
        return None
    text = url.encode("ascii") + b"\x00"
    tiff = (
        b"MM"
        + (42).to_bytes(2, "big")
        + (8).to_bytes(4, "big")
        + (1).to_bytes(2, "big")
        + IMAGE_DESCRIPTION.to_bytes(2, "big")
        + (2).to_bytes(2, "big")
        + len(text).to_bytes(4, "big")
        + (26).to_bytes(4, "big")
        + (0).to_bytes(4, "big")
    )
    return EXIF_SIGNATURE + tiff + text


def description_of(block: bytes | None) -> str | None:
    """IFD0's `ImageDescription`, either byte order, or `None`."""
    if not block or not block.startswith(EXIF_SIGNATURE):
        return None
    tiff = block[len(EXIF_SIGNATURE) :]
    if len(tiff) < 8 or tiff[:2] not in (b"MM", b"II"):
        return None
    order = "big" if tiff[:2] == b"MM" else "little"

    def number(at: int, size: int) -> int:
        return int.from_bytes(tiff[at : at + size], order)

    ifd = number(4, 4)
    if ifd + 2 > len(tiff):
        return None
    for index in range(number(ifd, 2)):
        at = ifd + 2 + index * 12
        if at + 12 > len(tiff):
            return None
        if number(at, 2) != IMAGE_DESCRIPTION or number(at + 2, 2) != 2:
            continue
        count = number(at + 4, 4)
        start = at + 8 if count <= 4 else number(at + 8, 4)
        text = tiff[start : start + count]
        return text.split(b"\x00", 1)[0].decode("latin-1")
    return None


def _our_exif(block: bytes) -> bool:
    return query_of_url(description_of(block)) is not None


# --------------------------------------------------------------------------- PNG
def _png_chunks(data: bytes):
    """Each chunk as `(type, start, end, body)`; stops at one that runs past the end."""
    at = 8
    while at + 12 <= len(data):
        length = int.from_bytes(data[at : at + 4], "big")
        end = at + 12 + length
        if length > 0x7FFFFFFF or end > len(data):
            return
        yield data[at + 4 : at + 8].decode("latin-1"), at, end, data[at + 8 : at + 8 + length]
        at = end


def _chunk(kind: str, body: bytes) -> bytes:
    name = kind.encode("latin-1")
    return len(body).to_bytes(4, "big") + name + body + zlib.crc32(name + body).to_bytes(4, "big")


def _itxt(keyword: str, text: str) -> bytes:
    return _chunk("iTXt", keyword.encode("latin-1") + b"\x00\x00\x00\x00\x00" + text.encode())


def _text_of(kind: str, body: bytes) -> tuple[str, str] | None:
    """A `tEXt` or uncompressed `iTXt` chunk's keyword and text."""
    first = body.find(b"\x00")
    if first < 0:
        return None
    keyword = body[:first].decode("latin-1")
    if kind == "tEXt":
        return keyword, body[first + 1 :].decode("latin-1")
    if kind != "iTXt" or body[first + 1 : first + 2] != b"\x00":
        return None
    language = body.find(b"\x00", first + 3)
    translated = body.find(b"\x00", language + 1) if language >= 0 else -1
    if translated < 0:
        return None
    return keyword, body[translated + 1 :].decode("utf-8")


def embed_png(data: bytes, query: str) -> bytes:
    """`stamp.js`'s `embedPng`: the tag's chunk then the packet, straight after `IHDR`."""
    if not data.startswith(PNG_MAGIC):
        raise EmbedRefused("not a PNG")
    chunks = list(_png_chunks(data))
    if not chunks or chunks[0][0] != "IHDR":
        raise EmbedRefused("a PNG opens with IHDR")
    header_end = chunks[0][2]
    kept = [data[:header_end]]
    foreign = False
    for kind, start, end, body in chunks[1:]:
        said = _text_of(kind, body) if kind in ("tEXt", "iTXt") else None
        if said is not None and said[0] == KEYWORD:
            continue
        if said is not None and kind == "iTXt" and said[0] == XMP_KEYWORD:
            if _our_xmp(said[1]):
                continue
            foreign = True
        kept.append(data[start:end])
    last = chunks[-1][2]
    ours = [_itxt(KEYWORD, payload_of(query))]
    if not foreign:
        ours.append(_itxt(XMP_KEYWORD, xmp_of(url_of(query))))
    return kept[0] + b"".join(ours) + b"".join(kept[1:]) + data[last:]


def png_fields(data: bytes) -> dict:
    """What a PNG carries: `{"tag", "xmp"}`, each `None` where absent."""
    found = {"tag": None, "xmp": None}
    for kind, _, _, body in _png_chunks(data):
        said = _text_of(kind, body) if kind in ("tEXt", "iTXt") else None
        if said is None:
            continue
        if said[0] == KEYWORD and found["tag"] is None:
            found["tag"] = said[1]
        elif said[0] == XMP_KEYWORD and kind == "iTXt" and found["xmp"] is None:
            found["xmp"] = said[1]
    return found


# -------------------------------------------------------------------------- JPEG
def _jpeg_segments(data: bytes) -> tuple[list[tuple[int, int, int, bytes]], int]:
    """Every marker segment before the scan as `(marker, start, end, body)`, and where
    the scan starts. Standalone markers carry an empty body."""
    out = []
    at = 2
    while at + 4 <= len(data) and data[at] == 0xFF:
        marker = data[at + 1]
        if marker in (0xD9, 0xDA):
            break
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:
            out.append((marker, at, at + 2, b""))
            at += 2
            continue
        length = int.from_bytes(data[at + 2 : at + 4], "big")
        if length < 2 or at + 2 + length > len(data):
            break
        out.append((marker, at, at + 2 + length, data[at + 4 : at + 2 + length]))
        at += 2 + length
    return out, at


def _segment(marker: int, body: bytes) -> bytes:
    if len(body) + 2 > 0xFFFF:
        raise EmbedRefused(f"a JPEG segment holds {0xFFFF - 2} bytes and this one is longer")
    return bytes([0xFF, marker]) + (len(body) + 2).to_bytes(2, "big") + body


def _app1_kind(body: bytes) -> str | None:
    if body.startswith(EXIF_SIGNATURE):
        return "exif"
    if body.startswith(XMP_SIGNATURE):
        return "xmp"
    return None


def _is_app(marker: int) -> bool:
    return 0xE0 <= marker <= 0xEF


def embed_jpeg(data: bytes, query: str) -> bytes:
    """`stamp.js`'s `embedJpeg`: EXIF and XMP at the end of the leading `APPn` run, then
    the tag's comment, and every other segment and the scan exactly as they were."""
    if not data.startswith(b"\xff\xd8"):
        raise EmbedRefused("not a JPEG")
    payload = payload_of(query).encode()
    if len(payload) > COMMENT_LIMIT:
        raise EmbedRefused(f"a JPEG comment holds {COMMENT_LIMIT} bytes and this link is longer")
    segments, scan = _jpeg_segments(data)
    kept = []
    foreign = set()
    for marker, start, end, body in segments:
        if marker == 0xFE and link_of(body.decode("utf-8", "replace")) is not None:
            continue
        kind = _app1_kind(body) if marker == 0xE1 else None
        if kind == "exif" and _our_exif(body):
            continue
        if kind == "xmp" and _our_xmp(body[len(XMP_SIGNATURE) :].decode("utf-8", "replace")):
            continue
        if kind is not None:
            foreign.add(kind)
        kept.append((marker, data[start:end]))
    insert = 0
    while insert < len(kept) and _is_app(kept[insert][0]):
        insert += 1

    url = url_of(query)
    added = []
    exif = None if "exif" in foreign else exif_of(url)
    if exif is not None:
        added.append(_segment(0xE1, exif))
    if "xmp" not in foreign:
        added.append(_segment(0xE1, XMP_SIGNATURE + xmp_of(url).encode()))
    added.append(_segment(0xFE, payload))
    ordered = [raw for _, raw in kept[:insert]] + added + [raw for _, raw in kept[insert:]]
    return data[:2] + b"".join(ordered) + data[scan:]


def jpeg_fields(data: bytes) -> dict:
    """What a JPEG carries: `{"tag", "xmp", "exif"}`, each `None` where absent."""
    found = {"tag": None, "xmp": None, "exif": None}
    for marker, _, _, body in _jpeg_segments(data)[0]:
        if marker == 0xFE and found["tag"] is None:
            text = body.decode("utf-8", "replace")
            if link_of(text) is not None:
                found["tag"] = text
        elif marker == 0xE1:
            kind = _app1_kind(body)
            if kind == "xmp" and found["xmp"] is None:
                found["xmp"] = body[len(XMP_SIGNATURE) :].decode("utf-8", "replace")
            elif kind == "exif" and found["exif"] is None:
                found["exif"] = description_of(body)
    return found


# ------------------------------------------------------------------------- both
def embed(data: bytes, query: str) -> bytes:
    """Whichever of the two these bytes are, with the link in it."""
    if data.startswith(PNG_MAGIC):
        return embed_png(data, query)
    if data.startswith(b"\xff\xd8"):
        return embed_jpeg(data, query)
    raise EmbedRefused("neither a PNG nor a JPEG")


def strip(data: bytes) -> bytes:
    """These bytes with every field of ours taken back out — the file as its encoder
    wrote it, which is what a comparison of two renders compares."""
    if data.startswith(PNG_MAGIC):
        out = [data[:8]]
        for kind, start, end, body in _png_chunks(data):
            said = _text_of(kind, body) if kind in ("tEXt", "iTXt") else None
            if said is not None and (
                said[0] == KEYWORD or (said[0] == XMP_KEYWORD and _our_xmp(said[1]))
            ):
                continue
            out.append(data[start:end])
        return b"".join(out)
    if data.startswith(b"\xff\xd8"):
        segments, scan = _jpeg_segments(data)
        out = [data[:2]]
        for marker, start, end, body in segments:
            if marker == 0xFE and link_of(body.decode("utf-8", "replace")) is not None:
                continue
            kind = _app1_kind(body) if marker == 0xE1 else None
            if kind == "exif" and _our_exif(body):
                continue
            if kind == "xmp" and _our_xmp(body[len(XMP_SIGNATURE) :].decode("utf-8", "replace")):
                continue
            out.append(data[start:end])
        return b"".join(out) + data[scan:]
    return data


def link_in(data: bytes) -> str | None:
    """The query a file carries: the tag first, the XMP packet's source where there is
    no tag — `stamp.js`'s `linkIn`."""
    fields = png_fields(data) if data.startswith(PNG_MAGIC) else jpeg_fields(data)
    return link_of(fields.get("tag")) or query_of_url(source_of(fields.get("xmp")))


def embed_file(path: Path, query: str) -> None:
    """Write the link into a finished picture in place, through a temporary and a rename,
    so a reader never meets half a file."""
    path = Path(path)
    stamped = embed(path.read_bytes(), query)
    scratch = path.with_name(f"{path.stem}.embedding{path.suffix}")
    scratch.write_bytes(stamped)
    scratch.replace(path)


__all__ = [
    "EXPLORER_URL",
    "EmbedRefused",
    "description_of",
    "embed",
    "embed_file",
    "embed_jpeg",
    "embed_png",
    "exif_of",
    "jpeg_fields",
    "link_in",
    "link_of",
    "png_fields",
    "source_of",
    "strip",
    "xmp_of",
]
