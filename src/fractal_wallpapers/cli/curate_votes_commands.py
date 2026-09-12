"""`curate votes`: the pairwise vote store, and the sheets that fill it.

One verb family and its own module for `modes_commands`' reason — it is a store
with a build/serve/ingest cycle of its own, and it sits between the gallery half
and the legs without belonging to either. A vote is a human comparison of two
finished wallpapers, which makes this the only `curate` group whose input is a
person rather than the engine.

Cut out of `curate_commands` on 2026-09-12 with four sibling families; that
module's docstring carries the reversal and what it cost.
"""

from __future__ import annotations

import argparse
import json


def curate_votes(args: argparse.Namespace) -> int:
    """Build the folder Matt's friends open, out of a recorded gallery."""
    from fractal_wallpapers.curation import tentative, votes

    try:
        # Parsed before anything is rendered, and last-one-wins on a repeated
        # mode: `--ss-for` is the flag a twenty-hour leg would otherwise discover
        # was misspelt at the end of it.
        overrides = dict(votes.parse_supersample_for(text) for text in (args.ss_for or ()))
        manifest = votes.build(
            stamp=args.stamp,
            out=args.out,
            limit=args.limit,
            quality=args.quality,
            chroma=args.chroma,
            supersample=args.ss,
            supersample_for=overrides,
            friends=tuple(args.friend or ()),
            per_page=args.page,
            seed=args.seed,
        )
    except (votes.VotesRefused, tentative.TentativeRefused) as refusal:
        print(refusal)
        return 1
    print(json.dumps(manifest, indent=2))
    return 0


def add_steps(steps) -> None:
    """The pairwise vote store, and the sheets that fill it."""
    from fractal_wallpapers.curation import votes as votes_module

    voting = steps.add_parser(
        "votes",
        help="build the folder friends open to vote on a recorded gallery",
        description=(
            "A recorded gallery as something a person who is not here can rate. Every "
            "seat is rendered again at "
            f"{votes_module.FRAME[0]}x{votes_module.FRAME[1]} through the release path — "
            "the stored candidate is 640x360 and far too small to vote on — the thumbnail "
            "is a downscale of that render and never of the candidate, and the folder is "
            "zipped with a self-contained page that opens by double-clicking. A filename "
            "carries the seat's position and nothing else: no rank, no key, no mode. One zip "
            "goes to everybody and each named friend gets the same master permutation rotated "
            "to a different start, so a partial pass is a uniform sample of the record. What "
            "comes back is one small JSON file per person, keyed by recipe key, in the "
            f"shape {votes_module.VIEWER} fixes."
        ),
    )
    voting.set_defaults(handler=curate_votes)
    votes_verbs = voting.add_subparsers(dest="what", required=True)
    building_votes = votes_verbs.add_parser(
        "build",
        help="render, encode and zip a voting kit for one record",
        description=(
            "Resumable at the seat: one whose two JPEGs are already there is not rendered "
            "again, so a killed leg picks up where it stopped. --ss is the flag worth "
            "thinking about and it is the only one anybody can see: measured at 76.2 s a "
            "picture on three workers, 1,000 seats is 21 h at ss4 against about 5 at ss2, "
            "and the whole quality axis moves the picture less than that choice does. "
            "--ss 1 is neither of those: it is the debugging cell, minutes rather than "
            "hours, for exercising the viewer end to end on a kit nobody is sent. "
            "GALLERY.md's `curate votes build` has the sheet those came off."
        ),
    )
    building_votes.add_argument(
        "stamp",
        nargs="?",
        help="the recorded gallery to build a kit from (default the newest published)",
    )
    building_votes.add_argument(
        "--out",
        required=True,
        metavar="DIR",
        help="the directory to build the kit in. It is zipped to <DIR>.zip beside itself",
    )
    building_votes.add_argument(
        "--limit",
        type=int,
        help="build the first N seats only, in seat order. A kit to try before a long leg",
    )
    building_votes.add_argument(
        "--quality",
        type=int,
        default=votes_module.QUALITY,
        help=f"JPEG quality for both the fulls and the thumbnails (default {votes_module.QUALITY})",
    )
    building_votes.add_argument(
        "--chroma",
        choices=sorted(votes_module.SUBSAMPLING),
        default=votes_module.CHROMA,
        help=f"chroma subsampling, passed rather than left to Pillow "
        f"(default {votes_module.CHROMA})",
    )
    building_votes.add_argument(
        "--ss",
        type=int,
        choices=votes_module.SUPERSAMPLES,
        default=votes_module.SUPERSAMPLE,
        help=f"the field supersample under the frame (default {votes_module.SUPERSAMPLE})",
    )
    building_votes.add_argument(
        "--friend",
        action="append",
        metavar="NAME",
        help="a friend the kit is built for, repeatable and in the order they are spaced. "
        "Each gets the SAME master permutation rotated by round(i*N/F), so a partial pass "
        "is a uniform sample rather than a prefix and two friends who stop early have voted "
        "on disjoint pictures. One zip for everybody: the first screen asks who they are and "
        "that picks the deck. With no names the deck is rotated by a hash of a typed name",
    )
    building_votes.add_argument(
        "--page",
        type=int,
        default=votes_module.PAGE,
        help=f"how many pictures a page holds (default {votes_module.PAGE}). Finishing a page "
        "is the unit the friends are asked for, so this is a size somebody commits to",
    )
    building_votes.add_argument(
        "--seed",
        type=int,
        help="the master permutation's seed. Drawn and recorded if not given, and a rebuild "
        "into a kit that already exists reads its own back — a re-drawn seed would move every "
        "page a friend had not reached yet",
    )
    building_votes.add_argument(
        "--ss-for",
        action="append",
        metavar="MODE=N",
        help="render one mode at another supersample, repeatable — `--ss 2 --ss-for "
        "smooth_mean_angle=4` is a cheap kit with one mode kept fine. The leg becomes one "
        "render pass per distinct supersample, cheapest first, and each seat's own "
        "supersample rides in the page's seat list rather than in its filename",
    )
