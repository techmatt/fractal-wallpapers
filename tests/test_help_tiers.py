"""`--help` in two tiers: the contract on screen, the reasoning behind an env var.

Every `help=` in `cli/` is written contract-first and reasoning-after, and the
reasoning is the best explanation of those flags anywhere — so it is kept and
[`common.TieredHelp`] prints only the first sentence unless
`FRACTAL_WALLPAPERS_HELP=full` says otherwise. That puts the whole arrangement on
one regex, and a regex is exactly the thing that goes subtly wrong on the next
help string somebody writes: it cuts `0.65` in half, or it finds no sentence at
all in a paragraph and prints the paragraph. Both are what this file is for.

All arithmetic and one parser build, so all of it is in the fast lane.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

import pytest

from fractal_wallpapers import cli
from fractal_wallpapers.cli import common

#: A summary this long is not a sentence, it is a paragraph with one period in
#: it. Three terminal lines at the width argparse wraps a help column to, which
#: is what the eight longest here genuinely are: single sentences that name a
#: rule and its exception in one breath. Anything past it is a help string whose
#: FIRST sentence needs breaking up, and the assertion names the site.
SUMMARY_CEILING = 320


def help_strings() -> list[tuple[str, int, str]]:
    """Every literal `help=` in the command line, as `(file, line, text)`.

    Read out of the source rather than off the built parser, because the failure
    this file guards against is a string somebody WRITES, and the assertion has
    to be able to say which line to go and look at. A built parser knows the
    text and not where it came from.
    """
    package = Path(cli.__file__).parent
    found = []
    for module in sorted(package.glob("*.py")):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.keyword) and node.arg == "help"):
                continue
            try:
                text = ast.literal_eval(node.value)
            except ValueError:
                continue  # an f-string or a name: formatted at build time
            if isinstance(text, str):
                found.append((module.name, node.value.lineno, text))
    return found


HELP = help_strings()


def test_the_command_line_still_carries_the_prose_this_arrangement_exists_for() -> None:
    """The premise, pinned. If the help strings were ever trimmed in place this
    whole mechanism would be machinery over nothing, and the honest fix would be
    to delete it rather than to leave it summarising one-liners."""
    assert len(HELP) > 700, "the count moved a long way; re-read the arrangement"
    assert sum(len(text) for _, _, text in HELP) > 60_000


def test_every_help_string_summarises_to_a_sentence_that_fits_a_screen() -> None:
    """The guard that catches a new help string whose contract is a paragraph."""
    long = [
        f"{name}:{line} summarises to {len(common.help_summary(text))} chars"
        for name, line, text in HELP
        if len(common.help_summary(text)) > SUMMARY_CEILING
    ]
    assert not long, (
        "these help strings have no short first sentence, so `--help` prints a "
        f"paragraph where it means to print a contract: {long}"
    )


def test_a_summary_is_never_empty_and_never_ends_mid_token() -> None:
    for name, line, text in HELP:
        summary = common.help_summary(text)
        assert summary, f"{name}:{line} summarised to nothing"
        whole = " ".join(text.split())
        assert summary == whole or summary.endswith("."), (
            f"{name}:{line} was cut somewhere that is not a sentence end: {summary[-40:]!r}"
        )
        assert whole.startswith(summary), f"{name}:{line} summary is not a prefix"


@pytest.mark.parametrize(
    "text,expected",
    [
        # A decimal, a version, an exponent and a flag: four things a
        # `split(". ")` cuts in half, and all four are in real help strings here.
        (
            "cap the share at 0.65 of the seats filled. The rest is reasoning.",
            "cap the share at 0.65 of the seats filled.",
        ),
        (
            "the floor, 1e-9 by default. Lowered on 2026-09-04 to reach the band.",
            "the floor, 1e-9 by default.",
        ),
        (
            "read the pool through --n. It was --count until 2026-09-01.",
            "read the pool through --n.",
        ),
        # An upper-case word the project means literally ends a sentence too: a
        # lowercase-only class ran past this one into the next.
        (
            "cells the palettes must be expected to DELIVER. The twin of --draw-maps.",
            "cells the palettes must be expected to DELIVER.",
        ),
        # The default is the other half of the contract, so it comes along.
        (
            "an earlier run to continue. DEFAULT: every leg the ledgers know. Because a "
            "chain continues itself.",
            "an earlier run to continue. DEFAULT: every leg the ledgers know.",
        ),
        # One sentence and no reasoning: unchanged, and the caller must be able to
        # tell, because that is what suppresses the footer.
        ("score only this many locations", "score only this many locations"),
    ],
)
def test_the_sentence_rule_on_the_shapes_that_have_broken_it(text, expected) -> None:
    assert common.help_summary(text) == expected


def test_the_formatter_reaches_every_nested_verb_and_not_only_the_root() -> None:
    """The whole point of [`common.Parser`] being a class and not a keyword.

    `add_subparsers` defaults `parser_class` to `type(self)`, so one class named
    at the root reaches all forty-eight `curate` steps and every verb under them.
    A `formatter_class=` at the root alone would summarise `fractal-wallpapers
    --help`, which is the one screen that was never the problem.
    """
    parser = cli.build_parser()
    assert parser.formatter_class is common.TieredHelp

    top = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    curating = top.choices["curate"]
    assert isinstance(curating, common.Parser)

    steps = next(a for a in curating._actions if isinstance(a, argparse._SubParsersAction))
    solving = steps.choices["solve"]
    assert isinstance(solving, common.Parser)

    verbs = next(a for a in solving._actions if isinstance(a, argparse._SubParsersAction))
    assert isinstance(verbs.choices["record"], common.Parser)
    assert verbs.choices["record"].formatter_class is common.TieredHelp


def test_the_env_var_prints_the_reasoning_and_the_footer_says_when_it_is_hidden(
    monkeypatch,
) -> None:
    """Both tiers out of one string, and a reader who can tell which they got."""
    parser = cli.build_parser()
    top = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    steps = next(
        a for a in top.choices["curate"]._actions if isinstance(a, argparse._SubParsersAction)
    )
    verbs = next(
        a for a in steps.choices["solve"]._actions if isinstance(a, argparse._SubParsersAction)
    )
    recording = verbs.choices["record"]

    monkeypatch.delenv(common.HELP_ENV, raising=False)
    trimmed = recording.format_help()
    monkeypatch.setenv(common.HELP_ENV, "full")
    whole = recording.format_help()

    assert len(whole) > len(trimmed) * 1.5, "the reasoning is most of what is written"
    assert common.TRIMMED_NOTE in trimmed
    assert common.TRIMMED_NOTE not in whole
    assert "…" in trimmed

    # The ruling behind `--themed-cap` is in the full screen and not in the
    # trimmed one. It is the flag the four-`--help` session was looking for.
    assert "2026-09-05" in whole
    assert "2026-09-05" not in trimmed


def test_a_screen_with_nothing_trimmed_on_it_carries_no_footer() -> None:
    """A note on a screen that hid nothing is a note that teaches a reader to
    ignore the note."""
    parser = common.Parser(prog="p", description="one line, nothing hidden")
    parser.add_argument("--limit", type=int, help="score only this many locations")
    assert common.TRIMMED_NOTE not in parser.format_help()


def test_an_argparse_percent_escape_survives_the_summary() -> None:
    """Summarised in `_expand_help` and not in `_get_help_string`, so the `%`
    substitution has already run. Taken the other way round, a summary cutting
    between the two characters of a `%%` leaves argparse a lone `%` to expand
    and it raises while printing help."""
    parser = common.Parser(prog="p")
    parser.add_argument(
        "--spent",
        help="a chain is spent when its latest leg held 90%% or more. The rest is reasoning.",
    )
    assert "held 90% or more." in parser.format_help()
