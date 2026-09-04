"""The `fractal-wallpapers` command line.

Everything runnable in this project is a subcommand here. There is no
`scripts/` directory: if a step is worth running twice it gets a subcommand,
a name, and `--help` text.

One module per command group, each holding its handlers and its parser
together, and [`build_parser`] is the list of them in the order they ship in.
Module names carry a `_commands` suffix and that is load-bearing rather than
decorative: eight top-level commands — `render`, `screen`, `walk`, `reframe`,
`recolor`, `census`, `harvest`, `modes` — are also the names of the handler
functions callers resolve through this package, and the import system sets a
submodule as an attribute of its package, which is one `__getattr__` never
sees. A `cli/render.py` would shadow `cli.render` for good. The suffix makes
that collision impossible for every group at once instead of by exception.

Handler names resolve through [`__getattr__`] rather than being re-exported,
which is the rule the candidate-ledger split arrived at the hard way: written
eagerly, `from .draw_commands import render as render` makes two independent
bindings of one function and a monkeypatch of either stops moving the other.
Resolving keeps one binding per name, which is what
`parse([...]).handler is cli.<name>` asserts.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from importlib import import_module

from fractal_wallpapers.paths import StorageRefusal, repo_root

__all__ = ["build_parser", "main", "repo_root"]

#: The command groups, in the order they register. The order is surface: it is
#: what `--help` lists and what the metavar prints, so a group moves here only
#: as a deliberate change to the command line.
GROUPS: tuple[str, ...] = (
    "weights_commands",
    "draw_commands",
    "walk_commands",
    "supply_commands",
    "modes_commands",
    "label_commands",
    "tiles_commands",
    "renders_commands",
    "head_commands",
    "spiral_commands",
    "regime_commands",
    "palette_commands",
    "palettes_commands",
    "figures_commands",
    "coloring_commands",
    "curate_commands",
    "deep_commands",
    "storage_commands",
    "import_commands",
)

#: Where [`__getattr__`] looks, in order. The groups first, then the shared
#: helpers, then `paths` — whose five names this module carried while the CLI
#: was one file, and which callers still reach for through it.
_LOOKUP: tuple[str, ...] = GROUPS + ("common",)
_LAST_RESORT = "fractal_wallpapers.paths"


def __getattr__(name: str):
    """Resolve a handler, a helper or a constant to the ONE module that defines it.

    Dunders answer immediately and never import anything: the import machinery
    asks a package for `__path__`, `__all__` and their relatives while the
    package is still initialising, and a scan started there would recurse.
    """
    if name.startswith("__") and name.endswith("__"):
        raise AttributeError(name)
    for module in _LOOKUP:
        try:
            return getattr(import_module(f"{__name__}.{module}"), name)
        except AttributeError:
            continue
    try:
        return getattr(import_module(_LAST_RESORT), name)
    except AttributeError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fractal-wallpapers",
        description="ML-steered fractal wallpaper generator.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    for group in GROUPS:
        import_module(f"{__name__}.{group}").add_commands(subcommands)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    from fractal_wallpapers.discovery.identity import IdentityBroken

    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except IdentityBroken as refusal:
        # Also here rather than in one command: both `walk` and `harvest` build
        # the walk that raises it, the message names the flag to change, and a
        # traceback would bury an instruction under a stack.
        print(refusal)
        return 1
    except StorageRefusal as refusal:
        # Handled here and nowhere else. Every other refusal in this package is
        # about one command's arguments and is caught by that command; these are
        # about the machine — an unplugged disk, a subtree on the wrong tier, one
        # name in both tiers — and any subcommand that touches the regenerable
        # tree can raise one. Caught rather than left to a traceback because each
        # message is an instruction, and an operator reading a stack trace to
        # find it would be reading it past the part that says nothing fell back.
        print(refusal)
        return 1
