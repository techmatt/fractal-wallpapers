"""Guard: this repository's history stays text-only and small, forever.

Binary blobs and large files are a one-way door — once committed they live in
every clone of the history. This test refuses them at the door. The allowlist
starts empty and adding to it should feel like a decision, not a fix.
"""

from __future__ import annotations

import functools
import json
import re
import subprocess
from pathlib import Path

MAX_TRACKED_BYTES = 1024 * 1024

# A machine-specific path in source is the other kind of one-way door: it works
# for exactly one developer. Source directories are held to pathlib and relatives.
SOURCE_PREFIXES = ("src/", "engine/src/")
# The lookbehind keeps URL schemes ("https://...") from reading as drive letters.
ABSOLUTE_PATH_PATTERN = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/]|/(?:home|Users|mnt)/")

BINARY_SUFFIXES = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".tif",
        ".tiff",
        ".webp",
        ".mp4",
        ".mov",
        ".zip",
        ".gz",
        ".tar",
        ".7z",
        ".pt",
        ".pth",
        ".ckpt",
        ".safetensors",
        ".npy",
        ".npz",
        ".bin",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".pdf",
        ".ico",
    }
)

# The tracked *records* are held to the same rule as source, for a sharper
# reason: a record is data a later machine reads back. `artifacts/tiles/...` is a
# name every clone can resolve through `paths.rehome`, on whichever tier the
# subtree sits; one machine's drive letter is a name only that machine could ever
# have used. `paths.tracked_name` is the one function that writes the spelling.
RECORD_SUFFIXES = (".json", ".jsonl")

# Exempt by KEY, not by file, so the exception cannot widen without being seen: a
# head's acceptance record names the pre-registration it was read against with an
# absolute path. A known wart, deliberately left — every other path in the same
# file is still held to the rule.
RECORD_EXEMPT_KEYS = frozenset({"prereg"})

# Deliberately empty. Every entry here is a permanent exception to the rule above.
ALLOWLIST: frozenset[str] = frozenset()

# Exempt from the SIZE rule only, and still held to being text. The two rules are
# separated here because they protect different things: a binary blob is a
# one-way door whatever its size, and a megabyte of JSONL is a file `git` packs,
# `diff` reads and a person can open.
#
# The palette head's distillation corpus is the one thing that needs it. It is
# 16,000 machine-labeled rows — the entire input to a training run, which is what
# makes that head regenerable rather than merely reproducible — and it is written
# one file per partition because that is the axis its draw is apportioned on.
# Splitting a partition into numbered parts to sit under a limit would be
# arranging the data around the guard instead of around what it is. Matt's call,
# recorded here rather than in a commit message nobody will find again.
LARGE_TEXT_ALLOWLIST = ("data/palette_choice/rows/",)

REPO_ROOT = Path(__file__).resolve().parents[1]


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [name for name in result.stdout.split("\0") if name]


def test_no_binary_files_are_tracked() -> None:
    offenders = [
        name
        for name in tracked_files()
        if name not in ALLOWLIST and Path(name).suffix.lower() in BINARY_SUFFIXES
    ]
    assert not offenders, f"binary-by-nature files are tracked: {offenders}"


def test_no_tracked_file_exceeds_one_mebibyte() -> None:
    offenders = []
    for name in tracked_files():
        if name in ALLOWLIST or name.startswith(LARGE_TEXT_ALLOWLIST):
            continue
        path = REPO_ROOT / name
        if path.is_file() and path.stat().st_size > MAX_TRACKED_BYTES:
            offenders.append(f"{name} ({path.stat().st_size} bytes)")
    assert not offenders, f"tracked files exceed {MAX_TRACKED_BYTES} bytes: {offenders}"


def test_the_size_exemption_does_not_exempt_a_blob() -> None:
    """A file allowed to be large is still not allowed to be binary.

    The whole reason the two rules are separated: `LARGE_TEXT_ALLOWLIST` widens
    one of them and must not quietly widen the other.
    """
    for prefix in LARGE_TEXT_ALLOWLIST:
        exempt = [name for name in tracked_files() if name.startswith(prefix)]
        assert exempt, f"{prefix} exempts nothing — a dead exception is a rule nobody reads"
        assert not [name for name in exempt if Path(name).suffix.lower() in BINARY_SUFFIXES], (
            f"{prefix} holds a binary-by-nature file"
        )


def _named_strings(document, key: str | None = None):
    """Every string in a parsed record, paired with the key it hangs off.

    A list carries its parent's key down, so `ledgers[0]` is reported as
    `ledgers` — the exemption is about what a field *means*, and an element of a
    list means what the list does.
    """
    if isinstance(document, dict):
        for name, value in document.items():
            yield from _named_strings(value, name)
    elif isinstance(document, list):
        for value in document:
            yield from _named_strings(value, key)
    elif isinstance(document, str):
        yield key, document


@functools.cache
def absolute_paths_in_records() -> tuple[tuple[str, str | None, str], ...]:
    """`(file, key, value)` for every absolute path a tracked record carries.

    The tracked records run to ninety-odd megabytes, nearly all of it the palette
    corpus and the colormap library, so the pattern screens the raw text and only
    a file it hits is parsed.
    """
    found = []
    for name in tracked_files():
        if not name.endswith(RECORD_SUFFIXES):
            continue
        path = REPO_ROOT / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if not ABSOLUTE_PATH_PATTERN.search(text):
            continue
        lines = text.splitlines() if name.endswith(".jsonl") else [text]
        for line in lines:
            if not line.strip():
                continue
            for key, value in _named_strings(json.loads(line)):
                if ABSOLUTE_PATH_PATTERN.search(value):
                    found.append((name, key, value))
    return tuple(found)


def test_no_absolute_paths_in_tracked_records() -> None:
    offenders = [
        f"{name}: {key} = {value}"
        for name, key, value in absolute_paths_in_records()
        if key not in RECORD_EXEMPT_KEYS
    ]
    assert not offenders, f"absolute paths in tracked records: {offenders}"


def test_the_record_exemption_is_not_dead() -> None:
    """An exception nobody needs any more is a rule nobody reads.

    The same reasoning as the size exemption above: the moment the acceptance
    records name their pre-registration the way everything else names a file,
    this fails and `RECORD_EXEMPT_KEYS` goes away with it.
    """
    exempted = {key for _, key, _ in absolute_paths_in_records() if key in RECORD_EXEMPT_KEYS}
    assert exempted == RECORD_EXEMPT_KEYS, (
        f"RECORD_EXEMPT_KEYS exempts {sorted(RECORD_EXEMPT_KEYS - exempted)}, which no tracked "
        "record needs any more"
    )


def test_no_absolute_paths_in_source() -> None:
    offenders = []
    for name in tracked_files():
        if not name.startswith(SOURCE_PREFIXES):
            continue
        path = REPO_ROOT / name
        if path.is_file() and ABSOLUTE_PATH_PATTERN.search(path.read_text(encoding="utf-8")):
            offenders.append(name)
    assert not offenders, f"absolute paths in source: {offenders}"
