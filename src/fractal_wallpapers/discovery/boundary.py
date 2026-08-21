"""The boundary draw: random frames, kept only by the structural gates.

Deep inside a set nothing escapes and the frame is black; far outside everything
escapes at once and the frame is a bland wash; the structure crowds the boundary
between them. So "a random view worth looking at" and "a random view near the
boundary" are the same request, and this module makes it by the only honest
route: **draw uniformly, and let the gates decide.**

That is not a shortcut around a boundary-finder. It is what a boundary-finder
would be. A frame that clears the interior cap is not mostly set; a frame that
clears the escape band is not far exterior; a frame that clears the occupancy
floor has detail spread across it rather than one filament in a void. A frame
that clears all three is straddling the boundary — there is no other way to be.

## Why this exists as a subcommand

The claim it supports is a claim about *rarity*: draw at random near the
boundary, keep only what passes a crude complexity check, and the survivors are
still mostly mediocre. Until now the only evidence for it was a batch of labels
recording a draw made once, in another project, by a generator nobody here has.
A record of a draw is not a draw. This is the generator: seeded, so the same
number reproduces the same frames; recording every attempt and not only the
keepers, because the yield *is* the measurement; and screening through
[`fractal_wallpapers.engine.screen`], so the filter in the picture is the filter
in the walk rather than a second one written to look like it.

## The two files, and why they are two

`draws.jsonl` is the record: a run header, one row per attempt with the fate it
earned, and a summary. `kept.jsonl` is a plain location manifest of the
survivors — nothing else, so it feeds straight into anything that reads
locations. One file could not be both: a manifest with a header row in it is a
manifest whose first line is not a location.

## Cost

Every attempt pays a 128-pixel probe, and only a frame that clears the interior
cap pays the 384-pixel render the other two gates read. That ordering is the
engine's and is why an unscreened draw is affordable at all: the cap refuses
most of what a uniform draw produces, and it refuses it on the cheap picture.
Attempts are screened in batches of [`BATCH`] so the per-call cost of starting
the engine is spread over many frames rather than paid per draw.
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

from fractal_wallpapers import engine, locations

#: The schema every row of a draw record carries.
SCHEMA = 1

#: Attempts screened per engine call. The engine costs a few milliseconds to
#: start and a probe costs a few more, so a batch of one would spend a third of
#: the clock on process spawn; a batch of this size spends under a percent.
BATCH = 64

#: The band a frame's width is drawn from, log-uniformly.
#:
#: Wide enough that the draw is not a survey of one scale, and bounded below well
#: above anywhere `f64` runs short. The lower end is where the source project's
#: own flat draw sat (2.06e-3); the upper end is a frame that still has to find
#: its structure rather than containing the whole set.
WIDTH_LOW, WIDTH_HIGH = 1e-3, 1e-1

#: How much of the home frame a center may be drawn from, per axis, as a fraction
#: of it. The home framing carries a margin of empty plane around the set on
#: purpose, and a draw that spent attempts out there would be measuring the
#: margin rather than the set.
HOME_SHARE = 0.9


class BoundaryError(RuntimeError):
    """The draw cannot be made as asked."""


def home_box(family: dict) -> tuple[float, float, float, float]:
    """`(re, im, half_width, half_height)` — the box centers are drawn from.

    The family's own home framing, read through the engine because the home table
    lives there and this side keeps no copy of it, shrunk to [`HOME_SHARE`] of
    each axis.
    """
    view = engine.home_view(family)
    width = float(view["width"]) * HOME_SHARE
    height = width * 9.0 / 16.0
    return float(view["center_re"]), float(view["center_im"]), width / 2.0, height / 2.0


def draws(
    rng: random.Random,
    count: int,
    box: tuple[float, float, float, float],
    band: tuple[float, float],
    start: int,
) -> list[dict]:
    """`count` uniform frames inside `box`, at widths log-uniform in `band`.

    Both draws are seeded and both are recorded: the center, so the frame can be
    re-rendered, and the width, so the scale the attempt was made at is part of
    the record rather than a property of the flag it was run under.
    """
    centre_re, centre_im, half_width, half_height = box
    low, high = band
    rows = []
    for offset in range(count):
        width = low * (high / low) ** rng.random()
        rows.append(
            {
                "index": start + offset,
                "center_re": repr(centre_re + rng.uniform(-half_width, half_width)),
                "center_im": repr(centre_im + rng.uniform(-half_height, half_height)),
                "width": repr(width),
            }
        )
    return rows


def sample(
    family: dict,
    *,
    seed: int = 0,
    keep: int = 12,
    attempts: int = 4000,
    band: tuple[float, float] = (WIDTH_LOW, WIDTH_HIGH),
    out_dir: Path,
    colormap: str = "twilight_shifted",
    images: bool = True,
    log=print,
) -> dict:
    """Draw frames at random and keep the ones every structural gate passed.

    Stops at `keep` survivors or `attempts` attempts, whichever comes first, and
    says which — a draw that ran out of attempts measured a *rarity* and must not
    be read as one that found what it was looking for.
    """
    if keep < 1:
        raise BoundaryError("a draw that keeps nothing is not a draw")
    if attempts < 1:
        raise BoundaryError("a draw needs at least one attempt")
    low, high = float(band[0]), float(band[1])
    if not 0 < low <= high:
        raise BoundaryError(f"the width band {low}..{high} is not a band")

    out_dir = Path(out_dir)
    frames_dir = out_dir / "frames"
    if images:
        frames_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)
    box = home_box(family)
    started = time.monotonic()

    record_path = out_dir / "draws.jsonl"
    manifest: list[dict] = []
    fates: dict[str, int] = {}
    made = 0
    header = {
        "schema": SCHEMA,
        "kind": "run",
        "seed": seed,
        "family": family,
        "home_box": {
            "center_re": repr(box[0]),
            "center_im": repr(box[1]),
            "half_width": repr(box[2]),
            "half_height": repr(box[3]),
            "share_of_home": HOME_SHARE,
        },
        "width_band": [low, high],
        "keep": keep,
        "attempt_cap": attempts,
        "colormap": colormap,
    }

    with record_path.open("w", encoding="utf-8", newline="\n") as handle:
        stated = False
        while made < attempts and len(manifest) < keep:
            wanted = min(BATCH, attempts - made)
            batch = draws(rng, wanted, box, (low, high), made)
            report = engine.screen(
                {
                    "schema": 1,
                    "frames": [
                        {
                            "family": family,
                            **{k: row[k] for k in ("center_re", "center_im", "width")},
                        }
                        for row in batch
                    ],
                    "colormap": colormap,
                    "colormap_dir": str(engine.colormap_dir()),
                    **({"out_dir": str(frames_dir)} if images else {}),
                }
            )
            if not stated:
                # The geometry every verdict was read at, taken from the engine
                # that read them rather than restated on this side.
                header.update(
                    {
                        "tile": report["tile"],
                        "field_supersample": report["field_supersample"],
                        "probe_width": report["probe_width"],
                        "battery": report["battery"],
                    }
                )
                handle.write(json.dumps(header, ensure_ascii=False) + "\n")
                stated = True

            for row, screened in zip(batch, report["frames"], strict=True):
                made += 1
                fates[screened["fate"]] = fates.get(screened["fate"], 0) + 1
                picture = None
                if screened.get("image"):
                    picture = f"draw{row['index']:05d}.jpg"
                    (frames_dir / screened["image"]).replace(frames_dir / picture)
                location = {
                    "family": family,
                    "viewport": {
                        "center_re": screened["center_re"],
                        "center_im": screened["center_im"],
                        "width": screened["width"],
                    },
                    "render": {"maxiter": screened["maxiter"]},
                }
                handle.write(
                    json.dumps(
                        {
                            "schema": SCHEMA,
                            "kind": "draw",
                            "index": row["index"],
                            **location,
                            "fate": screened["fate"],
                            "kept": screened["passed"],
                            "probe_interior_fraction": screened["probe_interior_fraction"],
                            "interior_fraction": screened["interior_fraction"],
                            "escape": screened.get("escape"),
                            "occupancy": screened.get("occupancy"),
                            "verdicts": screened["verdicts"],
                            "image": picture,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                if screened["passed"] and len(manifest) < keep:
                    manifest.append(location)

            log(
                f"[boundary] {made} drawn, {len(manifest)}/{keep} kept "
                f"({fates.get('survived', 0) / max(1, made):.2%} passed every gate)"
            )

        summary = {
            "schema": SCHEMA,
            "kind": "summary",
            "attempts": made,
            "kept": len(manifest),
            # The measurement, and it is not `kept / attempts`: the last batch is
            # screened whole, so it can turn up a survivor past the number asked
            # for. What the rarity claim rests on is how often a uniform draw
            # cleared every gate, which is this.
            "survived": fates.get("survived", 0),
            "pass_rate": fates.get("survived", 0) / max(1, made),
            "fates": dict(sorted(fates.items())),
            "stopped": "kept" if len(manifest) >= keep else "attempts",
            "seconds": round(time.monotonic() - started, 1),
        }
        handle.write(json.dumps(summary, ensure_ascii=False) + "\n")

    manifest_path = locations.write(manifest, out_dir / "kept.jsonl")
    return {
        **{k: v for k, v in header.items() if k not in ("schema", "kind")},
        **{k: v for k, v in summary.items() if k not in ("schema", "kind")},
        "record": str(record_path),
        "manifest": str(manifest_path),
        "frames": str(frames_dir) if images else None,
    }


__all__ = [
    "BATCH",
    "HOME_SHARE",
    "SCHEMA",
    "WIDTH_HIGH",
    "WIDTH_LOW",
    "BoundaryError",
    "draws",
    "home_box",
    "sample",
]
