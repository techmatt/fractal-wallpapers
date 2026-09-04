"""`modes`: the list of named colorings."""

from __future__ import annotations

import argparse

from fractal_wallpapers import engine


def modes(args: argparse.Namespace) -> int:
    """List the named colorings, what each one is for, and whether it ships.

    The tier is shown because it is the difference between a mode a run will draw
    and one only a person will ask for by name, and a list that hid it would read
    as sixteen interchangeable choices plus three.

    Takes the parsed arguments and reads none of them, because every handler
    has the same shape and one exception is worse than one unused parameter.
    """
    del args
    for mode in engine.modes():
        tier = "" if mode["tier"] == engine.PRODUCTION else f"[{mode['tier']}] "
        print(f"{mode['name']:<22} {tier}{mode['identity']}")
    return 0


def add_commands(subcommands) -> None:
    """Register this group's commands, in the order they ship in."""
    listing = subcommands.add_parser("modes", help="list the named colorings")
    listing.set_defaults(handler=modes)
