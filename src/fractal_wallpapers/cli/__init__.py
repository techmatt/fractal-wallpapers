"""The `fractal-wallpapers` command line.

Everything runnable in this project is a subcommand here. There is no
`scripts/` directory: if a step is worth running twice it gets a subcommand,
a name, and `--help` text.

One module per command group, each holding its handlers and its parser
together, and [`build_parser`] is the list of them in the order they ship in.
The one group too big to be one module is `curate`, which is nine command groups
wearing one hat: [`FAMILIES`] names the five modules it was cut into, and
`curate_commands` owns the `curate` parser and calls each family's `add_steps`.
Module names carry a `_commands` suffix and that is load-bearing rather than
decorative: eight top-level commands — `render`, `screen`, `walk`, `reframe`,
`recolor`, `census`, `harvest`, `modes` — are also the names of the handler
functions callers resolve through this package, and the import system sets a
submodule as an attribute of its package, which is one `__getattr__` never
sees. A `cli/render.py` would shadow `cli.render` for good. The suffix makes
that collision impossible for every group at once instead of by exception.

A command whose second word is a VERB spells it as a real `add_subparsers`, never
as a `choices=` positional inside one parser. The two look alike from the command
line and are not alike: a positional puts the whole group's flags on every verb,
so `curate sidecar check --force` was accepted and dropped on the floor, `curate
solve record` accepted twenty-two flags a record cannot pass through, and `--help`
at the group printed every verb's flags at once with nothing saying which belonged
to which. Sixteen groups and sixty-five verbs were spelled that way and none are
now; `tests/test_nested_verbs.py` holds the surface and the pin. The verb's dest is
`what` and the handler is `set_defaults` on the GROUP parser, so one handler still
serves a whole group and resolves to one binding through [`__getattr__`]. Where the
verb is optional — `curate flatness`, `curate signatures`, `curate rank-key` all
have a default verb that does the work — the group carries that verb's flags too
and the verb re-declares them with `default=argparse.SUPPRESS`, because argparse
copies a subparser's whole namespace over the parent's and a plain re-declaration
would overwrite what the parent had already taken.

**`--help` prints in two tiers and every `help=` string is written for both.**
The contract first — what the flag does and what the default is — then the
reasoning: the ruling, the date, the measurement behind the number.
[`common.TieredHelp`] prints the first sentence and marks the cut with `…`;
`FRACTAL_WALLPAPERS_HELP=full` prints the whole thing. So the reasoning stays
beside the flag it is about rather than one file away, and a person reaching for
`--help` gets the one-line contract: `curate solve record --help` was 237 lines
and is 96. `tests/test_help_tiers.py` holds the rule, and the thing it actually
catches is a new help string whose *first sentence* is a paragraph.

A command carrying twenty flags or more groups its help with
`add_argument_group`, and once one flag on a command is grouped they all are —
argparse prints an ungrouped optional above every named group, beside `-h`,
where it reads as belonging with `--help` rather than as having missed a
heading. Group titles are lowercase noun phrases naming what the flags steer,
and `walk` and `harvest` deliberately share six of them, because a harvest is a
walk with an economics layer over it. `tests/test_cli.py` holds both halves of
the rule. The shared flag helpers in [`common`] take a parser OR one of its
groups, so a grouped command hands the group and an ungrouped one hands the
parser; `common.location_arguments` is the exception and makes its own three,
because the fourteen flags it adds are themselves three questions.

Handler names resolve through [`__getattr__`] rather than being re-exported,
which is the rule the candidate-ledger split arrived at the hard way: written
eagerly, `from .draw_commands import render as render` makes two independent
bindings of one function and a monkeypatch of either stops moving the other.
Resolving keeps one binding per name, which is what
`parse([...]).handler is cli.<name>` asserts.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from importlib import import_module

from fractal_wallpapers.paths import StorageRefusal, repo_root

# The one thing here that runs at import, and it has to: cuBLAS reads this when it
# makes its handle, so a trainer that asked for determinism after torch was
# imported would be asking too late. `models/train.make_deterministic` refuses
# rather than warns when it is absent, which is how a fit says *this process
# cannot keep the promise* instead of quietly not keeping it. `setdefault`, so a
# caller who set it deliberately keeps their value.
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

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
    "gallery_grade_commands",
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

#: The modules that hold handlers but register **no top-level command**: the five
#: `curate` families cut out of `curate_commands` on 2026-09-12, when that module
#: reached 6,354 lines and forty-eight verbs. Their steps are registered by
#: [`curate_commands.add_commands`], which owns the `curate` parser and calls each
#: family's `add_steps` in the order they appear here — so this list is the
#: `curate --help` surface the way `GROUPS` is the top-level one. They are named
#: here rather than in `GROUPS` because `build_parser` iterates that list calling
#: `add_commands`, and a family has none: what they need from this package is only
#: that [`__getattr__`] can resolve their handler names.
FAMILIES: tuple[str, ...] = (
    "curate_ledger_commands",
    "curate_solve_commands",
    "curate_votes_commands",
    "curate_mine_commands",
    "curate_colors_commands",
    "curate_veto_commands",
    "curate_atlas_commands",
)

#: Where [`__getattr__`] looks, in order. The groups first, then the families,
#: then the shared helpers, then `paths` — whose five names this module carried
#: while the CLI was one file, and which callers still reach for through it.
_LOOKUP: tuple[str, ...] = GROUPS + FAMILIES + ("common",)
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
    # [`common.Parser`] and not `argparse.ArgumentParser`: it is the two-tier
    # `--help`, and it is set ONCE here because `add_subparsers` defaults
    # `parser_class` to `type(self)`, so the class reaches every step and every
    # nested verb without a `formatter_class=` at any of the 150-odd sites.
    # Imported here and not at module scope, so importing this package still
    # costs nothing: `common` reaches the labeling stores for its head lists.
    from fractal_wallpapers.cli.common import Parser

    parser = Parser(
        prog="fractal-wallpapers",
        description="ML-steered fractal wallpaper generator.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    for group in GROUPS:
        import_module(f"{__name__}.{group}").add_commands(subcommands)
    return parser


#: Which extra installs each optional dependency, and the cheapest one that does.
#:
#: The base install is deliberately torch-free — `pip install -e .` buys the
#: engine, the walk, the supply engine and the labeling rig, and the `models`
#: extra is two gigabytes of CUDA wheels a clone that only renders should never
#: pay for. The cost of that is an `ImportError` on any command that crosses the
#: line, and on a base install `curate mine plan` raised a bare
#: `ModuleNotFoundError: No module named 'numpy'` naming nothing a person could
#: act on. This turns every one of those into the install command.
#:
#: `numpy` and `pillow` are in **two** extras and the cheaper is named: choosing a
#: gallery reads scores off a store and never loads a head, so a machine that does
#: it needs neither torch nor the CUDA wheels.
EXTRA_FOR: dict[str, str] = {
    "numpy": "solve",
    "PIL": "solve",
    "torch": "models",
    "torchvision": "models",
    "timm": "models",
    "scipy": "dev",
}


def name_the_extra(missing: ModuleNotFoundError) -> str | None:
    """The install line for an optional dependency, or `None` for anything else.

    `None` where the module is not one of ours to explain: an import error inside
    this package is a bug and must keep its traceback, and a message guessing an
    extra for it would bury one.
    """
    extra = EXTRA_FOR.get(str(missing.name or "").split(".")[0])
    if extra is None:
        return None
    return (
        f"{missing.name} is not installed. It comes with the `{extra}` extra, which this "
        f"command needs and the base install deliberately leaves out:\n"
        f'    pip install -e ".[{extra}]"\n'
        f"The base install is torch-free on purpose — `models` alone is about four gigabytes "
        f"of CUDA wheels — so a clone that only renders pays for none of this."
    )


def main(argv: Sequence[str] | None = None) -> int:
    from fractal_wallpapers.cli.common import speak_utf8
    from fractal_wallpapers.discovery.identity import IdentityBroken

    # Before the parser, because `--help` is printed from inside `parse_args` and
    # two of the help screens here carry a character cp1252 cannot encode at all.
    speak_utf8()
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except IdentityBroken as refusal:
        # Also here rather than in one command: both `walk` and `harvest` build
        # the walk that raises it, the message names the flag to change, and a
        # traceback would bury an instruction under a stack.
        print(refusal)
        return 1
    except ModuleNotFoundError as missing:
        # Here for the same reason `StorageRefusal` is: the condition is about
        # the machine rather than about one command's arguments, and any command
        # that crosses into the optional half can raise it. Anything this cannot
        # name is re-raised with its traceback intact — an import error inside
        # this package is a bug and must not be dressed up as a missing extra.
        said = name_the_extra(missing)
        if said is None:
            raise
        print(said)
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
