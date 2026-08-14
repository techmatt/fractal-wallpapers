"""Guard: this repository's history stays text-only and small, forever.

Binary blobs and large files are a one-way door — once committed they live in
every clone of the history. This test refuses them at the door. The allowlist
starts empty and adding to it should feel like a decision, not a fix.
"""

from __future__ import annotations

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

# Deliberately empty. Every entry here is a permanent exception to the rule above.
ALLOWLIST: frozenset[str] = frozenset()

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
        if name in ALLOWLIST:
            continue
        path = REPO_ROOT / name
        if path.is_file() and path.stat().st_size > MAX_TRACKED_BYTES:
            offenders.append(f"{name} ({path.stat().st_size} bytes)")
    assert not offenders, f"tracked files exceed {MAX_TRACKED_BYTES} bytes: {offenders}"


def test_no_absolute_paths_in_source() -> None:
    offenders = []
    for name in tracked_files():
        if not name.startswith(SOURCE_PREFIXES):
            continue
        path = REPO_ROOT / name
        if path.is_file() and ABSOLUTE_PATH_PATTERN.search(path.read_text(encoding="utf-8")):
            offenders.append(name)
    assert not offenders, f"absolute paths in source: {offenders}"
