"""One colour vocabulary across the instrument pages, and a guard against a tenth copy.

Ten modules in this tree write a dark HTML instrument and each of them carried its
own copy of the same palette, which is how the copies came to disagree: three
grounds within four of 255 of each other and three inks within seven. Nobody chose
those differences. [`curation.page.PALETTE`] is the one vocabulary now.

What this file actually catches is the eleventh page: a module that pastes
`#14161a` in rather than naming `var(--ground)`, and a page that names a token
without carrying the `:root` block that declares it — the second being the silent
failure, because an undeclared custom property is not an error in CSS. It renders
as nothing at all, and a fate table with no background is a page somebody reads
for a while before noticing.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from fractal_wallpapers import curation
from fractal_wallpapers.curation import page

#: Dark pages that build their rules in a module-level constant, so the
#: vocabulary is concatenated in where it can be read off the source.
#: `sheet.STYLE` is deliberately absent: it is the second family,
#: `color-scheme: light dark`, and it inherits the reader's theme.
CONCATENATED: dict[str, str] = {
    "curation/color_sheets.py": "STYLE",
    "curation/label_fate.py": "STYLE",
    "curation/sheet.py": "SCORE_STYLE",
    "curation/swatch_frequency.py": "_STYLE",
    "curation/tentative.py": "_PAGE",
    "models/top_slice_probe.py": "STYLE",
    "supply/autopsy.py": "_STYLE",
}

#: Dark pages whose whole document is a `str.format` template, so the vocabulary
#: travels as a `{style}` field and NOT as a concatenation: `page.STYLE` is CSS,
#: CSS is full of braces, and a brace inside a format template is a field. This
#: is the shape that silently produces a page with no colours on it if the field
#: is ever dropped from the format call, which is what the second assertion is.
TEMPLATED: dict[str, str] = {
    "curation/label_migration.py": "PAGE",
    "curation/seat_sheet.py": "PAGE",
}

#: A page making a point with colour spells that colour itself, so a literal is
#: not banned outright — what is banned is a literal the vocabulary already has a
#: token for. `votes.py` is the one page exempt whole, below.
TOKENISED = {
    "#14161a",
    "#12141a",
    "#101216",  # ground
    "#1c1f26",
    "#191c22",  # panel
    "#0e1013",  # well
    "#1b1e24",
    "#22262e",  # raised
    "#e6e8eb",
    "#dfe3e8",
    "#e8e8ea",  # ink
    "#9aa4b1",
    "#9aa0aa",
    "#8a939f",
    "#8f98a4",  # muted
    "#6b7480",
    "#6f7681",  # faint
    "#2c313a",  # rule
    "#3a4150",  # rule_strong
    "#c8b98a",  # accent
    "#8fc7a0",  # good
    "#d8b45a",  # warn
    "#7fa6d8",  # link
}

#: `votes.py` and nothing else. It is the vote UI, the one page a person DRIVES
#: rather than reads, and its colour vocabulary is its own: two vote colours a
#: person learns on the first screen, and an `--ink` meaning dark-text-on-bright
#: -button rather than body text. Folding it in would put two meanings on one
#: token name, which is the defect the shared vocabulary exists to prevent.
EXEMPT = (
    "curation/page.py",  # the definition: this is where the literals live
    "curation/votes.py",
)

ROOT = Path(curation.__file__).parent.parent


def source(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def constant(rel: str, name: str) -> str:
    """One module-level string constant, evaluated. Concatenation is folded."""
    tree = ast.parse(source(rel))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return _fold(node.value)
    raise AssertionError(f"{rel} has no module-level {name}")


def _fold(node) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _fold(node.left) + _fold(node.right)
    if isinstance(node, ast.Attribute):  # `page.STYLE` / `page_module.STYLE`
        return page.STYLE
    raise AssertionError(f"unexpected node in a style constant: {ast.dump(node)[:80]}")


def test_the_vocabulary_names_one_colour_per_job_and_declares_every_one() -> None:
    """The tokens and the `:root` block agree, which is what makes a token safe
    to name: an undeclared custom property renders as nothing and raises no error."""
    for token in page.PALETTE:
        assert f"--{token}:" in page.STYLE, f"--{token} is in PALETTE and not declared"
    declared = set(re.findall(r"--([a-z_]+):", page.STYLE))
    assert declared == set(page.PALETTE), (
        f"declared but not in PALETTE: {declared - set(page.PALETTE)}"
    )
    assert all(re.fullmatch(r"#[0-9a-f]{6}", v) for v in page.PALETTE.values())


@pytest.mark.parametrize("rel,name", sorted(CONCATENATED.items()))
def test_a_dark_page_names_the_vocabulary_and_carries_the_block_that_declares_it(rel, name) -> None:
    style = constant(rel, name)
    assert "var(--ground)" in style, f"{rel}'s {name} does not use the shared vocabulary"
    assert ":root {" in style and "--ground:" in style, (
        f"{rel}'s {name} names custom properties without the `:root` block that "
        f"declares them, so every colour on that page renders as nothing. Prepend "
        f"`page.STYLE`, or pass it through the template as `style=`"
    )


@pytest.mark.parametrize("rel,name", sorted(TEMPLATED.items()))
def test_a_templated_page_takes_the_vocabulary_as_a_field_and_is_handed_it(rel, name) -> None:
    """Both halves, because either alone is a page with no colours on it."""
    template = constant(rel, name)
    assert "<style>{style}" in template, (
        f"{rel}'s {name} has no `{{style}}` field, so the vocabulary has nowhere "
        f"to go. It cannot be concatenated in: CSS braces are format fields"
    )
    assert "style=page" in source(rel), (
        f"{rel} never hands `page.STYLE` to {name}.format, so `{{style}}` fills "
        f"with nothing and every colour on that page renders as nothing"
    )


def test_no_module_pastes_a_colour_the_vocabulary_already_names() -> None:
    """The guard against an eleventh copy. What went wrong before was not one
    module getting a shade wrong — it was ten modules each holding the whole
    palette, so a re-tune was a sweep and a missed file was a page that drifted."""
    offenders = []
    for path in sorted(ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if rel in EXEMPT:
            continue
        text = path.read_text(encoding="utf-8")
        for literal in sorted(TOKENISED):
            if literal in text.lower():
                offenders.append(f"{rel} pastes {literal}")
    assert not offenders, (
        "these name a colour `curation.page.PALETTE` already has a token for; use "
        f"`var(--<token>)`: {offenders}"
    )


def test_the_shell_escapes_its_title_and_puts_the_vocabulary_before_the_caller() -> None:
    """Two things the fourteen hand-rolled skeletons each had to get right, and
    two of them interpolated a title unescaped."""
    built = page.shell("a <script> & a stamp", "<h1>hi</h1>", style=".x { color: red; }")
    assert "<title>a &lt;script&gt; &amp; a stamp</title>" in built
    assert built.startswith("<!doctype html>\n")
    assert built.endswith("\n")
    # The caller's rules come last, so a page's own selector wins on a tie.
    assert built.index("--ground:") < built.index(".x { color: red; }")
