"""`curate veto`: what a human `1` at the fine level takes out, and the pass that collects more.

Four verbs over one idea. `reach` says how far the veto goes over the whole
store; `seats` says what it takes out of one recorded gallery, with a page of the
pictures; `palettes` is the concentration reading taken off the same join; and
`sheet` cuts the rejection pass that collects the next round of them.

The veto itself has no verb here and that is deliberate. It is not a thing to
run — [`curation.veto`] derives it from the gallery-grade store every time
[`curation.solve.pool`] builds a pool, so it is already in force everywhere and
there is nothing to apply. What is here is only ways of looking at it.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fractal_wallpapers.cli.common import display_path, resolve_output


def curate_veto(args: argparse.Namespace) -> int:
    """Read the veto: its reach, its cost to one record, and the sheet that grows it."""
    from fractal_wallpapers.curation import veto

    doing = {
        "reach": _reach,
        "seats": _seats,
        "palettes": _palettes,
        "sheet": _sheet,
    }[args.what]
    try:
        return doing(args)
    except (veto.VetoRefused, OSError) as refusal:
        print(refusal)
        return 1


def _reach(args: argparse.Namespace) -> int:
    from fractal_wallpapers.curation import veto

    print(json.dumps(veto.reach(), indent=2))
    return 0


def _seats(args: argparse.Namespace) -> int:
    from fractal_wallpapers.curation import veto

    readout = veto.seats(args.stamp)
    where = Path(args.out) if args.out else veto.root() / args.stamp
    veto.write_record(readout, resolve_output(str(where / "vetoed_seats.json")))
    if not readout["vetoed"]:
        print(json.dumps({key: value for key, value in readout.items() if key != "rows"}, indent=2))
        print(f"no seat in {args.stamp} carries a human 1; no page was built")
        return 0
    if args.page:
        page = veto.page(readout, resolve_output(str(where / "vetoed_seats.html")))
        print(display_path(page))
        if args.open:
            import webbrowser

            webbrowser.open(page.resolve().as_uri())
    print(json.dumps({key: value for key, value in readout.items() if key != "rows"}, indent=2))
    return 0


def _palettes(args: argparse.Namespace) -> int:
    from fractal_wallpapers.curation import veto

    print(json.dumps(veto.palette_concentration(args.stamp, top=args.top), indent=2))
    return 0


def _sheet(args: argparse.Namespace) -> int:
    from fractal_wallpapers.curation import veto

    units, record = veto.plan(args.stamp)
    record["batch"] = args.batch
    where = resolve_output(args.out) if args.out else veto.plan_home(args.stamp, args.batch)
    plan_path, record_path = veto.write_plan(where, units, record)
    print(json.dumps(record, indent=2))
    print(display_path(plan_path))
    print(display_path(record_path))
    print(
        "next, register the batch, render the sheet and serve it:\n"
        f"  fractal-wallpapers label register --head gallery_grade --batch {args.batch} "
        f"--method '...' --anchored --why '...'\n"
        f"  fractal-wallpapers label build --head gallery_grade --rejection --workers 3 "
        f"--from-plan {display_path(plan_path)} --batch {args.batch} "
        f"--out-dir artifacts/sheet/{args.batch}\n"
        f"  fractal-wallpapers label serve --sheet artifacts/sheet/{args.batch}"
    )
    return 0


def add_steps(steps) -> None:
    """The veto's readouts, and the rejection pass that collects the next of them."""
    from fractal_wallpapers.curation import veto as veto_module

    vetoing = steps.add_parser(
        "veto",
        help="what a human fine-level 1 takes out, and the rejection pass that collects more",
        description=(
            "A picture a person grades 1 at the fine level is excluded from seating, from the "
            "pool and from every future solve, permanently. The veto is ROW-LEVEL — the exact "
            "candidate by its recipe key, never the place, the pair, the mode or the map — it "
            "is derived from the gallery-grade store rather than written anywhere, so it is "
            "retroactive and latest-wins, and only a HUMAN label vetoes: a model score of 1 or "
            "a low p_fine is not one. There is no verb here that applies it, because "
            "`solve.pool` already does on every leg that seats anything. These four verbs only "
            "look at it."
        ),
    )
    vetoing.set_defaults(handler=curate_veto)
    verbs = vetoing.add_subparsers(dest="what", required=True)

    reaching = verbs.add_parser(
        "reach",
        help="how many pictures the veto names store-wide, and how many ledger rows that is",
        description=(
            "One streaming pass over the ledger. A vetoed render key with no ledger row is a "
            "picture a person judged that the pool has since stopped holding, which is neither "
            "an error nor a leak: a row not in the ledger is not in the pool either."
        ),
    )
    reaching.set_defaults(what="reach")

    seating = verbs.add_parser(
        "seats",
        help="which seats of one recorded gallery the veto takes out, with a page of them",
        description=(
            "The record is NOT rewritten: a stamp seated before a label was cast still holds "
            "that seat, and this is what a re-solve drops. Broken out by mode, family, colour "
            "cell, hue family and map, so a systematic pocket of bad pictures shows as one. The "
            "page is the ledger's stored 640x360 candidates — nothing is re-rendered — and it "
            "ingests nowhere: its captions are open, which is what keeps it from being mistaken "
            "for a label instrument."
        ),
    )
    seating.set_defaults(what="seats")
    seating.add_argument("stamp", help="the recorded gallery to read")
    seating.add_argument(
        "--page",
        action="store_true",
        help="write the page of vetoed seats beside the readout",
    )
    seating.add_argument(
        "--open",
        action="store_true",
        help="open the page in the default browser once it is written",
    )
    seating.add_argument(
        "--out",
        help=(
            f"where the readout and the page land (default artifacts/curation/"
            f"{veto_module.UNIT}/<stamp>)"
        ),
    )

    palettes = verbs.add_parser(
        "palettes",
        help="how many distinct maps hold a record's seats, and what the top of them holds",
        description=(
            "A direct check on whether the collection is converging toward one palette. The "
            "colormap is on the ledger row and not on the recorded seat, so this takes the same "
            "join `seats` does. Read it against `ceiling.GROUP_CAP_RATE`, which caps a palette "
            "GROUP rather than a map: a top map under that cap is a cap that is not binding."
        ),
    )
    palettes.set_defaults(what="palettes")
    palettes.add_argument("stamp", help="the recorded gallery to read")
    palettes.add_argument(
        "--top", type=int, default=10, help="how many of the leading maps to report (default 10)"
    )

    sheeting = verbs.add_parser(
        "sheet",
        help="cut the rejection plan over every seat of a recorded gallery",
        description=(
            "One gallery-grade unit per seat, the whole record and nothing sampled — a "
            "rejection pass looks at every seat once and marks only the bad ones. The seats "
            "that already carry a verdict are kept, because the store is latest-wins and a "
            "plan that dropped them could not change its own mind. Each unit carries the fine "
            "head's decode as its prefill and that head's expected grade as what the page is "
            "ordered good->bad by. This writes the PLAN; `label build --head gallery_grade "
            "--rejection --from-plan` renders the sheet, and `--rejection` is what turns the "
            "page's sweep off."
        ),
    )
    sheeting.set_defaults(what="sheet")
    sheeting.add_argument("stamp", help="the recorded gallery to cut the pass over")
    sheeting.add_argument(
        "--batch",
        required=True,
        help="the gallery-grade batch this pass's marks will land in. Named here and not only "
        "at `label build`, because the plan's home on disk is `<draw>/<batch>/` and "
        "`gallery_grade.plan_paths()` is what finds it: a row carries `leveled` as a boolean "
        "and never the directory, so the plan is the only thing that can say which colormap a "
        "picture was judged through, and a plan written anywhere else is one this store's own "
        "accessor cannot see and `tests/test_gallery_grade_retention.py` fails on",
    )
    sheeting.add_argument(
        "--out",
        help=(
            f"where the plan and its record land (default "
            f"{veto_module.PLAN_DRAW_PREFIX}<stamp>/<batch> under the gallery-grade plans "
            f"tree, which is where `gallery_grade.plan_paths()` looks)"
        ),
    )
