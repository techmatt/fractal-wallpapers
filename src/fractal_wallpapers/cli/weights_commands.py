"""`fetch-weights`: the release download, and the manifest check that stays torch-free."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
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


def unreachable(head: str, entry: dict, url: str, why: Exception) -> str:
    """What a head that could not be downloaded says. **Naming all four things.**

    The tag, the asset, the URL and what the server said, because each of them is
    a different repair by a different person. A missing tag is a release nobody
    cut; a 404 under a tag that exists is an asset that was never uploaded or was
    renamed; a timeout is this machine's network. A bare `HTTPError: 404` says
    which of those is the case to nobody, and this is the first command
    `README.md` tells a fresh clone to run.
    """
    if isinstance(why, urllib.error.HTTPError):
        said = f"HTTP {why.code} {why.reason}"
        if why.code == 404:
            said += (
                f" — either the release {entry['tag']!r} has not been cut, or it carries no "
                f"asset named {entry['asset']!r}"
            )
    elif isinstance(why, urllib.error.URLError):
        said = f"{why.reason} — this machine could not reach GitHub"
    else:
        said = str(why)
    return f"{head}: {said}\n  tag {entry['tag']}  asset {entry['asset']}\n  {url}"


def fetch_weights(args: argparse.Namespace) -> int:
    """Download each head's weights from GitHub Releases and verify its sha256.

    **Every head is tried, and a failure is reported rather than raised.** This
    used to let `urlretrieve` throw, so a clone whose first head 404s learned
    nothing about the other two and read a stack trace instead of an instruction
    — and the releases this manifest names are cut by hand, so one head missing
    while the rest are there is the ordinary state rather than a rare one.
    """
    manifest = json.loads(manifest_path().read_text(encoding="utf-8"))
    if args.check:
        return check_weights(manifest)
    heads = manifest.get("heads", {})
    if not heads:
        print(f"no weights listed in {tracked_name(manifest_path())}; nothing to fetch")
        return 0

    asked, got, complaints = 0, 0, []
    for head, entry in sorted(heads.items()):
        if args.head and head != args.head:
            continue
        asked += 1
        destination = repo_root() / "models" / head / entry["asset"]
        if destination.is_file() and sha256_of(destination) == entry["sha256"]:
            print(f"{head}: already present")
            got += 1
            continue
        url = RELEASE_URL.format(tag=entry["tag"], asset=entry["asset"])
        print(f"{head}: fetching {url}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            urllib.request.urlretrieve(url, destination)  # noqa: S310
        except (urllib.error.URLError, OSError) as why:
            destination.unlink(missing_ok=True)
            complaints.append(unreachable(head, entry, url, why))
            continue
        actual = sha256_of(destination)
        if actual != entry["sha256"]:
            destination.unlink()
            complaints.append(
                f"{head}: {entry['asset']} hashes to {actual}, not {entry['sha256']} — the "
                f"download was not the file the manifest describes, and has been removed\n"
                f"  {url}"
            )
            continue
        print(f"{head}: verified")
        got += 1
    if args.head and not asked:
        print(f"{args.head!r} is not a head in {tracked_name(manifest_path())}")
        return 1
    for complaint in complaints:
        print(complaint)
    print(f"{got} of {asked} head(s) present")
    return 1 if complaints else 0


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
