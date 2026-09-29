"""Wallpaper packs: the full set's JPEGs, zipped into the downloads the site offers.

[`curation.full_set`] renders every kept seat into one directory as `<key>.jpg` and
writes `membership.jsonl` beside them, one row per (collection, seat). This module
reads that directory and nothing else of the render path: it never renders, never
re-encodes, and copies each picture into its zip byte for byte, so the explorer link
the full set stamped into every JPEG travels with it.

## What ships

Eighteen zips (Matt, 2026-09-26):

- **The general n=1000 in three parts**, [`PARTS`] of them in rank order — 334, 333
  and 333. A part keeps the general rank in its file names, so part 2 opens at
  `0335`, and every part pads to the width of the whole thousand.
- **Best 30, 100 and 200** ([`BEST`]): the first K of that same order, so each is
  nested in part 1. A best-K pack pads to the width of K.
- **The twelve colour collections**, the hue families of [`targets.families`], one
  zip each in an order of their own.

The n=2000 general pass and the seven mode collections are not shipped.

## Rank order

Until the friends' votes on the n=1000 set are in, the general rank is a **seeded
permutation** of its seats ([`SEED`]). The order is an input — `--order FILE`, one
recipe key a line, the id a returned vote carries — and the draw is only its
default, so the day the votes land is a file and not a change here. A colour pack
draws its own permutation from `<SEED>/<collection>`. Every seed is written into
[`MANIFEST_NAME`] beside the order it produced.

## Inside a zip

One folder named after the zip, holding `<rank> <palette> <fractal>.jpg` per picture
and a `README.txt`. **The palette is the explorer's display name**, read from
`explorer/palette-names.json` in the `fractal-website` checkout, keyed by the
recipe's colormap id; an id with no entry falls back to the raw id and is reported.
**The fractal is the site's family name** ([`plane_name`]) with the degree said as
a word. Pictures are STORED, since JPEGs do not compress; only the README deflates.

## Incomplete packs refuse

The full set renders for days, so a pack is often not whole yet. [`missing`] names
the members not on disk, and [`build`] refuses a pack with any unless it is told to
allow a partial one — which is then named `-trial-partial` in both its pack name and
its file, so it can never be mistaken for the release asset.
"""

from __future__ import annotations

import hashlib
import json
import random
import zipfile
from dataclasses import dataclass
from pathlib import Path

from fractal_wallpapers.paths import repo_root

#: The schema of [`MANIFEST_NAME`].
SCHEMA = 1

#: The seed of the general rank until the votes define one. A colour pack's is
#: `f"{SEED}/{collection}"`.
SEED = 20260926

#: How many zips the general n=1000 is cut into, in rank order.
PARTS = 3

#: The best-K packs, each the first K of the general rank.
BEST = (30, 100, 200)

#: The collection names in `membership.jsonl` the general packs are cut from.
GENERAL = "general"

#: Every zip's file name opens with this.
PREFIX = "fractal-wallpapers"

#: The manifest the site's packs page reads counts and sizes from.
MANIFEST_NAME = "packs.json"

#: What a partial pack's name and file carry, so it is never the release asset.
PARTIAL = "trial-partial"

#: A zip should stay under this (Matt): comfortably inside GitHub Releases' 2 GiB
#: per-asset limit, and a download that does not feel like a commitment.
SIZE_BUDGET = 1_100_000_000

SITE = "https://techmatt.github.io/fractals/"
LICENCE = (
    "Wallpapers © 2026 Matt Fisher, licensed under CC BY 4.0 "
    "(https://creativecommons.org/licenses/by/4.0/)."
)

#: A degree said as a word, as the site's own prose says it ("a degree-three Julia
#: set") and as a person would say the family.
DEGREE_WORD = {3: "Cubic", 4: "Quartic", 5: "Quintic", 6: "Sextic"}


class PacksRefused(RuntimeError):
    """A pack cannot be built as asked."""


def palette_names_path() -> Path:
    """The explorer's palette display names, in the `fractal-website` checkout next door."""
    return repo_root().parent / "fractal-website" / "explorer" / "palette-names.json"


def read_palette_names(path: Path | None = None) -> dict[str, str]:
    """`{colormap id: display name}` off the explorer's table."""
    path = palette_names_path() if path is None else Path(path)
    if not path.is_file():
        raise PacksRefused(f"no palette names at {path}; pass --names FILE")
    return {cid: entry["name"] for cid, entry in json.loads(path.read_text("utf-8")).items()}


def plane_name(family: dict) -> str:
    """A recipe's family as a reader names it.

    `builder/picks.py`'s `family_name` in the `fractal-website` checkout, with the
    degree spoken rather than written `d = n`, which is a label and not a file name:
    Mandelbrot, Julia, Cubic Multibrot, Quartic Julia, Phoenix. The classic Phoenix
    slice and any other Phoenix are both Phoenix, as they are on the site.
    """
    kind = family.get("kind")
    if kind in ("multibrot", "julia"):
        degree = int(family.get("degree", 2))
        noun = "Multibrot" if kind == "multibrot" else "Julia"
        if degree == 2:
            return "Mandelbrot" if kind == "multibrot" else "Julia"
        if degree not in DEGREE_WORD:
            raise PacksRefused(f"no name for a degree-{degree} {kind}; add it to DEGREE_WORD")
        return f"{DEGREE_WORD[degree]} {noun}"
    names = {"mandelbrot": "Mandelbrot", "phoenix": "Phoenix"}
    if kind not in names:
        raise PacksRefused(f"no reader name for family kind {kind!r}")
    return names[kind]


def picture_name(rank: int, width: int, palette: str, plane: str) -> str:
    """`<rank> <palette> <fractal>.jpg`, the rank zero-padded to `width`."""
    return f"{rank:0{width}d} {palette} {plane}.jpg"


# --------------------------------------------------------------------------- #
# The plan.
# --------------------------------------------------------------------------- #
@dataclass
class Pack:
    """One zip: its members in order, and the rank its first member carries."""

    name: str
    collection: str
    stamp: str
    about: str
    keys: list[str]
    first_rank: int = 1
    width: int = 0
    seed: str | None = None
    order_from: str = "seed"

    def file_name(self, partial: bool = False) -> str:
        return f"{PREFIX}-{self.name}{'-' + PARTIAL if partial else ''}.zip"

    def ranks(self) -> list[int]:
        return list(range(self.first_rank, self.first_rank + len(self.keys)))


def read_membership(full: Path) -> list[dict]:
    from fractal_wallpapers.curation import full_set

    rows = full_set.read_jsonl(Path(full) / full_set.MEMBERSHIP_NAME)
    if not rows:
        raise PacksRefused(f"no {full_set.MEMBERSHIP_NAME} in {full}; is this the full set?")
    return rows


def seeded(keys: list[str], seed) -> list[str]:
    """`keys` in a permutation drawn from `seed`, the same on every run."""
    shuffled = list(keys)
    random.Random(seed).shuffle(shuffled)
    return shuffled


def read_order(path: Path, keys: list[str]) -> list[str]:
    """An order file: one recipe key a line, naming exactly the record's seats once each."""
    wanted = [line.strip() for line in Path(path).read_text("utf-8").splitlines()]
    wanted = [key for key in wanted if key and not key.startswith("#")]
    extra = sorted(set(wanted) - set(keys))
    lost = sorted(set(keys) - set(wanted))
    twice = sorted({key for key in wanted if wanted.count(key) > 1})
    if extra or lost or twice:
        raise PacksRefused(
            f"{path} is not an order of the {len(keys)} general seats: "
            f"{len(extra)} unknown, {len(lost)} absent, {len(twice)} repeated"
        )
    return wanted


def plan(full: Path, order: Path | None = None, seed: int = SEED) -> list[Pack]:
    """Every shipped pack, members in rank order, off the full set's membership."""
    from fractal_wallpapers.curation import targets

    rows = read_membership(full)
    by_collection: dict[str, list[dict]] = {}
    for row in rows:
        by_collection.setdefault(row["collection"], []).append(row)
    general = sorted(by_collection.get(GENERAL, []), key=lambda row: row["order"])
    if not general:
        raise PacksRefused(f"membership has no {GENERAL!r} collection")
    stamp = general[0]["stamp"]
    seats = [str(row["key"]) for row in general]
    if order is not None:
        ranked, order_from, drawn = read_order(order, seats), Path(order).name, None
    else:
        ranked, order_from, drawn = seeded(seats, seed), "seed", str(seed)

    total = len(ranked)
    width = len(str(total))
    packs = []
    # 1000 over three is 334/333/333: the remainder goes to the first part.
    cut = [0] + [total - (total * (PARTS - part)) // PARTS for part in range(1, PARTS + 1)]
    for part in range(PARTS):
        lo, hi = cut[part], cut[part + 1]
        packs.append(
            Pack(
                name=f"general-{part + 1}-of-{PARTS}",
                collection=GENERAL,
                stamp=stamp,
                about=(
                    f"Fractal wallpapers, the general collection, part {part + 1} of {PARTS}: "
                    f"ranks {lo + 1} to {hi} of {total:,}."
                ),
                keys=ranked[lo:hi],
                first_rank=lo + 1,
                width=width,
                seed=drawn,
                order_from=order_from,
            )
        )
    for k in BEST:
        packs.append(
            Pack(
                name=f"best-{k}",
                collection=GENERAL,
                stamp=stamp,
                about=(
                    f"Fractal wallpapers, the best {k} of the {total:,} in the general collection."
                ),
                keys=ranked[:k],
                width=len(str(k)),
                seed=drawn,
                order_from=order_from,
            )
        )
    for hue in targets.families():
        members = sorted(by_collection.get(hue, []), key=lambda row: row["order"])
        if not members:
            raise PacksRefused(f"membership has no {hue!r} collection")
        hue_seed = f"{seed}/{hue}"
        keys = seeded([str(row["key"]) for row in members], hue_seed)
        packs.append(
            Pack(
                name=hue,
                collection=hue,
                stamp=members[0]["stamp"],
                about=f"Fractal wallpapers, the {hue} collection: {len(keys)} pictures.",
                keys=keys,
                width=len(str(len(keys))),
                seed=hue_seed,
            )
        )
    return packs


def missing(full: Path, pack: Pack) -> list[str]:
    """The members of `pack` whose picture is not in the full set yet."""
    from fractal_wallpapers.curation import full_set

    done = full_set.done(full)
    return [key for key in pack.keys if key not in done]


def status(full: Path, order: Path | None = None) -> list[dict]:
    """Per pack: members, on disk, missing, bytes so far and projected at the mean."""
    packs = plan(full, order)
    sizes = {held.stem: held.stat().st_size for held in Path(full).glob("*.jpg")}
    mean = sum(sizes.values()) / len(sizes) if sizes else 0.0
    out = []
    for pack in packs:
        have = [sizes[key] for key in pack.keys if key in sizes]
        own = sum(have) / len(have) if have else mean
        out.append(
            {
                "pack": pack.name,
                "pictures": len(pack.keys),
                "on_disk": len(have),
                "missing": len(pack.keys) - len(have),
                "bytes_so_far": sum(have),
                "projected_at_set_mean": round(len(pack.keys) * mean),
                "projected_at_own_mean": round(len(pack.keys) * own),
            }
        )
    return out


# --------------------------------------------------------------------------- #
# Writing a zip.
# --------------------------------------------------------------------------- #
def readme_text(pack: Pack, partial: bool) -> str:
    lines = [pack.about]
    if partial:
        lines.append("TRIAL: this pack is incomplete and is not a release.")
    lines += [
        "",
        f"More, and the explorer every picture came from: {SITE}",
        "Each picture's metadata carries a link that reopens it in the explorer.",
        "",
        LICENCE,
        "",
    ]
    return "\n".join(lines)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_zip(
    full: Path, out: Path, pack: Pack, names: dict[str, str], partial: bool = False
) -> dict:
    """Zip one pack into `out`. The manifest entry, plus the palette ids with no name."""
    from fractal_wallpapers.curation import tentative

    recipes = tentative.read_recipes(pack.stamp)
    done = {held.stem for held in Path(full).glob("*.jpg")}
    target = Path(out) / pack.file_name(partial)
    folder = target.stem
    writing = target.with_name(target.name + ".writing")
    unnamed: set[str] = set()
    seats = []
    Path(out).mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(writing, "w") as bundle:
        for rank, key in zip(pack.ranks(), pack.keys, strict=True):
            if key not in done:
                continue
            recipe = recipes[key]
            colormap = recipe["colormap"]
            if colormap not in names:
                unnamed.add(colormap)
            inside = picture_name(
                rank, pack.width, names.get(colormap, colormap), plane_name(recipe["family"])
            )
            bundle.write(
                Path(full) / f"{key}.jpg", f"{folder}/{inside}", compress_type=zipfile.ZIP_STORED
            )
            seats.append({"rank": rank, "key": key, "file": inside})
        bundle.writestr(
            f"{folder}/README.txt",
            readme_text(pack, partial),
            compress_type=zipfile.ZIP_DEFLATED,
        )
    writing.replace(target)
    entry = {
        "pack": pack.name + (f"-{PARTIAL}" if partial else ""),
        "file": target.name,
        "collection": pack.collection,
        "stamp": pack.stamp,
        "pictures": len(seats),
        "of": len(pack.keys),
        "complete": len(seats) == len(pack.keys),
        "bytes": target.stat().st_size,
        "sha256": sha256_of(target),
        "order_from": pack.order_from,
        "seed": pack.seed,
        "seats": [seat["key"] for seat in seats],
        "first_rank": pack.first_rank,
    }
    return {"entry": entry, "unnamed": sorted(unnamed)}


def write_manifest(out: Path, entries: list[dict]) -> Path:
    """Merge `entries` into [`MANIFEST_NAME`] by pack, dropping entries whose zip is gone."""
    path = Path(out) / MANIFEST_NAME
    held = json.loads(path.read_text("utf-8")) if path.is_file() else {"packs": []}
    by_pack = {entry["pack"]: entry for entry in held.get("packs", [])}
    by_pack.update({entry["pack"]: entry for entry in entries})
    kept = [entry for entry in by_pack.values() if (Path(out) / entry["file"]).is_file()]
    writing = path.with_name(path.name + ".writing")
    with writing.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump({"schema": SCHEMA, "packs": kept}, handle, indent=1)
        handle.write("\n")
    writing.replace(path)
    return path


def build(
    full: Path,
    out: Path,
    only: list[str] | None = None,
    order: Path | None = None,
    names_path: Path | None = None,
    allow_partial: bool = False,
    log=print,
) -> dict:
    """Build the named packs (every pack if `only` is empty) and update the manifest.

    Refuses, before writing anything, if a pack asked for has members not on disk
    and `allow_partial` is not set.
    """
    packs = plan(full, order)
    if only:
        unknown = sorted(set(only) - {pack.name for pack in packs})
        if unknown:
            raise PacksRefused(f"no pack named {', '.join(unknown)}")
        packs = [pack for pack in packs if pack.name in only]
    short = {pack.name: missing(full, pack) for pack in packs}
    short = {name: keys for name, keys in short.items() if keys}
    if short and not allow_partial:
        said = "; ".join(f"{name} lacks {len(keys)}" for name, keys in short.items())
        raise PacksRefused(f"incomplete: {said}. --allow-partial builds a trial")
    names = read_palette_names(names_path)
    entries, unnamed = [], set()
    for pack in packs:
        done = write_zip(full, out, pack, names, partial=pack.name in short)
        entry = done["entry"]
        unnamed.update(done["unnamed"])
        over = " OVER BUDGET" if entry["bytes"] > SIZE_BUDGET else ""
        log(
            f"[packs] {entry['file']}: {entry['pictures']}/{entry['of']} pictures, "
            f"{entry['bytes'] / 1e6:.1f} MB{over}"
        )
        entries.append(entry)
    manifest = write_manifest(out, entries)
    return {
        "built": [entry["file"] for entry in entries],
        "missing": {name: len(keys) for name, keys in short.items()},
        "unnamed_palettes": sorted(unnamed),
        "manifest": str(manifest),
    }
