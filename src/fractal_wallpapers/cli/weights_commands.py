"""`fetch-weights`: the release download, and the manifest check that stays torch-free."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

from fractal_wallpapers.models.roster import manifest_path
from fractal_wallpapers.paths import repo_root, tracked_name

RELEASE_URL = "https://github.com/techmatt/fractal-wallpapers/releases/download/{tag}/{asset}"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


#: What a manifest row has to say before a release can be cut from it. An asset
#: nobody can hash is a download nobody checked, and one that cannot name its
#: commit is a file nobody can rebuild.
REQUIRED_FIELDS = ("tag", "asset", "sha256", "source_commit", "provenance")


def check_weights(manifest: dict) -> int:
    """Read the manifest against the local tree: no network, no downloads.

    The dry run a release is cut after. It answers three questions the release
    itself cannot be un-cut to fix — is every head this project trains actually
    in here, does every row say the things a row has to say, and does the file
    each row names exist and hash to what the row claims.

    All of it is stdlib, and stays that way: the roster comes from the light
    module that owns it rather than from `ship`, which would drag the training
    stack into a check that reads JSON and hashes a file. A fresh clone runs
    this on `pip install -e .`, before it has any reason to own torch.
    """
    from fractal_wallpapers.models import roster

    heads = manifest.get("heads", {})
    complaints = []
    for head in roster.HEADS:
        if head not in heads:
            complaints.append(f"{head}: no manifest entry; a release cut now would omit it")
    for head, entry in sorted(heads.items()):
        missing = [field for field in REQUIRED_FIELDS if field not in entry]
        if missing:
            complaints.append(f"{head}: entry names no {', '.join(missing)}")
        asset = entry.get("asset")
        if not asset:
            continue
        path = repo_root() / "models" / head / asset
        if not path.is_file():
            complaints.append(f"{head}: {asset} is not on disk, so nothing was hashed")
            continue
        digest = sha256_of(path)
        size = path.stat().st_size
        if digest != entry.get("sha256"):
            complaints.append(f"{head}: {asset} hashes to {digest}, not {entry.get('sha256')}")
        elif "bytes" in entry and size != entry["bytes"]:
            complaints.append(f"{head}: {asset} is {size} bytes, not {entry['bytes']}")
        else:
            commit = str(entry.get("source_commit", ""))[:12] or "?"
            print(f"{head}: {asset} {size:>9} bytes  verified  from {commit}")
    for complaint in complaints:
        print(complaint)
    print(
        f"{len(heads)} of {len(roster.HEADS)} heads present; "
        f"{'release-complete' if not complaints else f'{len(complaints)} gap(s)'}"
    )
    return 1 if complaints else 0


def fetch_weights(args: argparse.Namespace) -> int:
    """Download each head's weights from GitHub Releases and verify its sha256."""
    manifest = json.loads(manifest_path().read_text(encoding="utf-8"))
    if args.check:
        return check_weights(manifest)
    heads = manifest.get("heads", {})
    if not heads:
        print(f"no weights listed in {tracked_name(manifest_path())}; nothing to fetch")
        return 0

    for head, entry in sorted(heads.items()):
        if args.head and head != args.head:
            continue
        destination = repo_root() / "models" / head / entry["asset"]
        if destination.is_file() and sha256_of(destination) == entry["sha256"]:
            print(f"{head}: already present")
            continue
        url = RELEASE_URL.format(tag=entry["tag"], asset=entry["asset"])
        print(f"{head}: fetching {url}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, destination)  # noqa: S310
        actual = sha256_of(destination)
        if actual != entry["sha256"]:
            destination.unlink()
            print(f"{head}: sha256 mismatch (expected {entry['sha256']}, got {actual})")
            return 1
        print(f"{head}: verified")
    return 0


def add_commands(subcommands) -> None:
    """Register this group's commands, in the order they ship in."""
    fetch = subcommands.add_parser(
        "fetch-weights",
        help="download model weights from GitHub Releases into models/<head>/",
    )
    fetch.add_argument("--head", help="fetch only this head instead of all of them")
    fetch.add_argument(
        "--check",
        action="store_true",
        help=(
            "verify the manifest against the local tree and download nothing: every head "
            "present, every entry complete, every named artifact on disk and hashing true"
        ),
    )
    fetch.set_defaults(handler=fetch_weights)
