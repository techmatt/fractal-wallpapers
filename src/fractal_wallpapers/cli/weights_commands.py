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
    # **One package, one tag**, which is the failure the single-release scheme
    # introduced and the per-head numbering could not have. A row left behind on
    # an old tag 404s while the other three come down fine, so a clone gets three
    # working judges and one that does not exist — and the only symptom is an exit
    # code somebody has to read. Checked here rather than at fetch time because
    # this is the dry run a release is cut after, and the repair is a manifest
    # edit rather than a download.
    tags = sorted({str(entry.get("tag") or "") for entry in heads.values()})
    if len(tags) > 1:
        complaints.append(
            f"the {len(heads)} heads name {len(tags)} different tags ({', '.join(tags)}). "
            f"Since 2026-09-14 every head ships in ONE dated release — roster.TAG is "
            f"{roster.TAG!r} — and a row left on an older tag is a head that 404s while "
            f"the rest come down."
        )
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


#: Where a release check clones from when nobody says otherwise. The public HTTPS
#: URL and not the `git@` remote this checkout pushes over: what is being verified
#: is what a stranger gets, and a stranger has no deploy key.
PUBLIC_REPO = "https://github.com/techmatt/fractal-wallpapers.git"


def verify_release(args: argparse.Namespace) -> int:
    """Clone fresh, fetch, and check — **because this tree passes either way**.

    `fetch-weights` on this machine reports `already present` for every head: the
    files are on disk and they hash true, so it never asks GitHub anything. That
    makes the one question a release has to answer — *can somebody who does not
    have these files get them* — the one question this checkout cannot answer
    about itself. So this clones the public repository into a temporary directory,
    where `models/` holds no weights at all, and runs the clone's own command
    against the clone's own manifest.

    **It borrows this interpreter rather than building a venv**, and that is a
    stated limit rather than a shortcut: `fetch-weights` and `--check` are
    stdlib-only by construction (`tests/test_base_install.py` proves it in a
    subprocess with the optional imports refused), so `PYTHONPATH=<clone>/src` is
    the whole install they need. What this verifies is **the release and the
    manifest**; it does not verify that `pip install -e .` works, which is a
    different claim with a different failure.

    The clone is `--depth 1` of one ref, so it costs the pack and not the history.
    """
    import os
    import shutil
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    into = Path(args.into).resolve() if args.into else Path(tempfile.mkdtemp(prefix="weights-"))
    clone = into / "clone"
    print(f"[verify] cloning {args.repo} @ {args.ref} into {clone}")
    cloned = subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", args.ref, args.repo, str(clone)],
        capture_output=True,
        text=True,
    )
    if cloned.returncode != 0:
        print(cloned.stderr.strip()[-2000:])
        print(
            f"\nFAIL — the clone did not come down. If this says 'Remote branch {args.ref} not "
            f"found', the branch has not been pushed; the release cannot be verified against "
            f"code GitHub does not have."
        )
        return 1

    # A clean environment: this machine's roots must not reach into the clone, and
    # a `local.toml` here is not something a stranger has.
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("FRACTAL_WALLPAPERS_")
    }
    environment["PYTHONPATH"] = str(clone / "src")

    def inside(*arguments) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "fractal_wallpapers.cli", *arguments],
            cwd=clone,
            env=environment,
            capture_output=True,
            text=True,
        )

    held = sorted(str(one) for one in (clone / "models").rglob("*.pt"))
    print(f"[verify] weights in the clone before fetching: {len(held)}")

    # **Which manifest GitHub is actually serving**, said before anything is
    # fetched. A release can be cut perfectly and this still fail, because the
    # rows that name it live in a commit that has to be pushed too — and the two
    # failures look identical from inside the fetch. This separates them.
    from fractal_wallpapers.models import roster

    served = json.loads((clone / "models" / "weights.json").read_text(encoding="utf-8"))
    tags = sorted({str(row.get("tag") or "") for row in served.get("heads", {}).values()})
    print(
        f"[verify] the clone's manifest names {len(served.get('heads', {}))} head(s) "
        f"on tag(s) {', '.join(tags)}"
    )
    stale = tags != [roster.TAG]
    if stale:
        print(
            f"[verify] ⚠ this checkout names {roster.TAG!r}, so the manifest on GitHub is NOT "
            f"the one being staged here — `git push` is outstanding, and a release cut at "
            f"{roster.TAG!r} cannot be reached by the code a clone gets."
        )

    def say(done) -> None:
        for stream in (done.stdout, done.stderr):
            if stream and stream.strip():
                print(stream.strip()[-2000:])

    print("\n$ fractal-wallpapers fetch-weights")
    fetched = inside("fetch-weights")
    say(fetched)

    print("\n$ fractal-wallpapers fetch-weights --check")
    checked = inside("fetch-weights", "--check")
    say(checked)

    ok = fetched.returncode == 0 and checked.returncode == 0 and not stale
    if ok:
        print(
            f"\nPASS — {len(roster.HEADS)} of {len(roster.HEADS)} heads downloaded from "
            f"{roster.TAG} and hashed true against the manifest. The release is complete and "
            f"a stranger can use it."
        )
    else:
        print("\nFAIL — one or both of these:")
        print(
            f"  * the manifest on GitHub is stale (push `main`) — "
            f"{'THIS ONE' if stale else 'not this one, the tags agree'}"
        )
        print(
            "  * the release is missing or an asset is misnamed — every 404 above names its "
            "tag, its asset and its URL, and a hash that did not match says so. The assets "
            "must be attached under exactly the names `models/weights.json` gives."
        )
    if args.into:
        print(f"\nthe clone is at {clone} — delete it when you are done")
    else:
        shutil.rmtree(into, ignore_errors=True)
    return 0 if ok else 1


def fetch_weights(args: argparse.Namespace) -> int:
    """Download each head's weights from GitHub Releases and verify its sha256.

    **Every head is tried, and a failure is reported rather than raised.** This
    used to let `urlretrieve` throw, so a clone whose first head 404s learned
    nothing about the other two and read a stack trace instead of an instruction
    — and the releases this manifest names are cut by hand, so one head missing
    while the rest are there is the ordinary state rather than a rare one.
    """
    if args.verify_release:
        return verify_release(args)
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
            "present, every entry complete, every named artifact on disk and hashing true, "
            "and all four naming ONE tag — since 2026-09-14 every head ships in one dated "
            "release, and a row left on an older tag is a head that 404s while the rest "
            "come down"
        ),
    )
    fetch.add_argument(
        "--verify-release",
        action="store_true",
        help="clone the public repository into a temporary directory and run `fetch-weights` "
        "and `--check` THERE. The one thing this checkout cannot answer about itself: here "
        "every head reports `already present` and GitHub is never asked, so a release that "
        "was never uploaded passes. Borrows this interpreter through PYTHONPATH rather than "
        "building a venv — both commands are stdlib-only by construction — so it verifies "
        "the release and the manifest, not that `pip install` works",
    )
    fetch.add_argument(
        "--repo",
        default=PUBLIC_REPO,
        help=f"which repository --verify-release clones (default {PUBLIC_REPO}). The public "
        f"HTTPS URL rather than the push remote, because what is being verified is what a "
        f"stranger gets and a stranger has no deploy key",
    )
    fetch.add_argument(
        "--ref",
        default="main",
        help="which branch --verify-release clones (default main). A release is verified "
        "against the manifest GitHub actually serves, which is the pushed one and not this "
        "working tree",
    )
    fetch.add_argument(
        "--into",
        metavar="DIR",
        help="keep the --verify-release clone here instead of a temporary directory that is "
        "deleted afterwards. For reading what came down when something failed",
    )
    fetch.set_defaults(handler=fetch_weights)
