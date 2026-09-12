"""One colour vocabulary and one document skeleton for every instrument page.

Fourteen modules in this package write an HTML page and every one of them is an
**instrument**: a contact sheet, a fate table, a coverage census, a vote UI. They
are read on a screen to decide something, and the decision is usually about a
picture, which is why they are all dark.

## What is shared here and what deliberately is not

**The colours are.** Ten modules carried their own copy of the same dark palette
and the copies had drifted into three near-identical grounds — `#14161a`,
`#12141a` and `#101216`, within four of 255 of each other — and three inks,
`#e6e8eb`, `#dfe3e8` and `#e8e8ea`. Nobody chose those differences; they are what
a palette pasted into a tenth file looks like. [`PALETTE`] is the one vocabulary
now and [`STYLE`] declares it as custom properties, so a page names `var(--ink)`
and a re-tune is one edit rather than a sweep. Sixty-odd hex literals went.

**The layout is not, and that is not an oversight.** Measured before this module
was written: the ten style blocks hold 341 lines between them and share
**three** identical rules in one pair. A fate table's absolute-positioned
captions, a score sheet's sticky band headers and a vote page's two-up keyboard
UI are three different instruments, and a shell that tried to hold all three
would be a shell every caller overrode. So each page keeps its own rules and
hands them to [`shell`] as `style`; what this module owns is the vocabulary they
are written in and the four lines of boilerplate around them.

**`sheet.STYLE` is a second family and stays one.** It is `color-scheme: light
dark` and inherits the reader's theme — the release sheet, the near-pair bands,
the solve's contact sheet and the mining legs all use it, and they are pages
about a picture's *content* rather than about a table of numbers. A page belongs
to one family or the other; there is no page that wants both.
"""

from __future__ import annotations

import html

__all__ = ["PALETTE", "STYLE", "shell"]

#: The dark vocabulary, one token per job rather than one per shade. A page that
#: needs a colour this does not name is a page making a point with colour —
#: `label_fate`'s four verdict colours are the example — and it spells that one
#: itself rather than adding a token nothing else uses.
PALETTE: dict[str, str] = {
    # The three planes: the page, a panel raised off it, and the well a picture
    # sits in. The well is darker than the page so a dark photograph still has an
    # edge.
    "ground": "#14161a",
    "panel": "#1c1f26",
    "well": "#0e1013",
    "raised": "#1b1e24",
    # Type, brightest to faintest. `ink` is body text, `muted` is a lede or a
    # caption, `faint` is a label nobody reads unless they are looking for it.
    "ink": "#e6e8eb",
    "muted": "#9aa4b1",
    "faint": "#6b7480",
    # A rule between planes, and the one above a sticky header, which has to be
    # lighter or the header has no top edge when the page scrolls under it.
    "rule": "#2c313a",
    "rule_strong": "#3a4150",
    # The three things a page says with colour rather than with words: a value
    # worth reading, a number that is good, and a number that wants attention.
    "accent": "#c8b98a",
    "good": "#8fc7a0",
    "warn": "#d8b45a",
    "link": "#7fa6d8",
}

#: The custom-property block plus the rules that genuinely are every page's —
#: the body plane, the type scale, monospace, and a table. Everything else a
#: page wants it declares itself.
STYLE = (
    ":root {\n"
    + "".join(f"  --{token}: {value};\n" for token, value in PALETTE.items())
    + """}
body { background: var(--ground); color: var(--ink); margin: 0;
       font: 13px/1.45 ui-sans-serif, system-ui, "Segoe UI", sans-serif; }
a { color: var(--link); }
h1 { font-size: 16px; margin: 0 0 6px; }
h2 { font-size: 14px; margin: 1.8rem 0 .3rem; }
.lede { color: var(--muted); max-width: 78rem; margin: 0 0 6px; }
.lede b { color: var(--ink); }
code, .mono { font-family: ui-monospace, monospace; }
code { color: var(--accent); }
img { display: block; width: 100%; background: var(--well); }
table { border-collapse: collapse; font-size: 13px; }
td, th { text-align: left; padding: .15rem .8rem .15rem 0; vertical-align: top; }
"""
)


def shell(title: str, body: str, *, style: str = "") -> str:
    """One page, as a string ending in a newline.

    The four lines every one of these writers had its own copy of — the doctype,
    the charset, the title and the `<style>` — plus [`STYLE`] ahead of the
    caller's own rules so a page's own selector always wins. `title` is escaped
    here rather than at fourteen call sites, which is the other reason this is a
    function: two of those sites interpolated a stamp into a title unescaped.

    Written as a string and not to a file, because where a page lands is the
    caller's question — some write beside their record, some to `scratch/`, and
    `tentative` writes one per published stamp. Every caller opens with
    `newline="\\n"`; a page is a tracked-shaped text file even where it is not
    tracked, and a Windows run that wrote CRLF would make a diff of every line.
    """
    return (
        "<!doctype html>\n"
        '<meta charset="utf-8">\n'
        f"<title>{html.escape(title)}</title>\n"
        f"<style>{STYLE}{style}</style>\n"
        f"{body}\n"
    )
