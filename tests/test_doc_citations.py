"""Guard: a citation of a doc's heading names a heading that doc has.

`CLAUDE.md`'s naming rule says to cite a heading and a file, never a line number,
and the form the tree uses is `` `<doc>.md`'s *Heading* ``. A heading renamed or
trimmed away leaves every such citation pointing at nothing, and nothing on screen
says so: the sentence still reads. This sweeps every tracked `.md`, `.py` and `.rs`
file for that form and resolves each one against the cited doc's headings.

What counts as a match is deliberately loose: the cited words and the heading are
compared case-folded with markdown and comment markers stripped, and either may be
a prefix of the other, so a citation may shorten a long heading or drop a dated
suffix. What it does not see: the link form (`` [`x.md`](...)'s *Heading* ``), a
citation of a bold phrase rather than a heading, and citations into `.py`
docstrings. A doc is found by its path from the citing file's directory, then from
the repository root, then as the unique tracked doc whose path ends with it.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]

CITE = re.compile(r"`([\w./-]+\.md)`(?:'s|’s)\s+\*([^*]+?)\*", re.S)
HEADING = re.compile(r"^#{1,6}\s+(.*)$", re.M)

#: How many citations resolved when this guard was written (127, with none
#: dangling). A floor, because a sweep that silently stopped finding citations — a
#: changed form, a parse that matches nothing — would pass the check above. Raise
#: it as citations are added; a reading under it is a deletion to look at.
RESOLVED_FLOOR = 127


def _norm(text: str) -> str:
    text = re.sub(r"\n\s*(#:|#|///|//!|//|\*)?", " ", text)
    text = re.sub(r"[`*_]", "", text)
    text = text.replace("’", "'").replace("—", "-").replace("–", "-")
    return re.sub(r"\s+", " ", text).strip().strip(".:,;").lower()


def _matches(heading: str, words: str) -> bool:
    """Either may shorten the other: a citation drops a suffix, a heading gains one."""
    return bool(heading) and (heading.startswith(words) or words.startswith(heading))


def _tracked() -> list[str]:
    listing = subprocess.run(
        ["git", "ls-files", "-z", "*.md", "*.py", "*.rs"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [name for name in listing.stdout.split(chr(0)) if name and (ROOT / name).is_file()]


def _candidates(doc: str, citing: str, docs: set[str]) -> list[str]:
    """The docs a citation may mean: beside the citing file, from the root, by suffix."""
    found = []
    for candidate in ((PurePosixPath(citing).parent / doc).as_posix(), doc):
        parts: list[str] = []
        for part in PurePosixPath(candidate).parts:
            if part == "..":
                if parts:
                    parts.pop()
            elif part != ".":
                parts.append(part)
        found.append("/".join(parts))
    found += sorted(name for name in docs if name.endswith("/" + doc))
    return [name for name in dict.fromkeys(found) if name in docs]


def _sweep() -> tuple[set[tuple[str, str]], int]:
    files = _tracked()
    docs = {name for name in files if name.endswith(".md")}
    headings: dict[str, list[str]] = {}
    dangling: set[tuple[str, str]] = set()
    resolved = 0
    for citing in files:
        text = (ROOT / citing).read_text(encoding="utf-8", errors="replace")
        for match in CITE.finditer(text):
            doc, words = match.group(1), _norm(match.group(2))
            hit = False
            for target in _candidates(doc, citing, docs):
                if target not in headings:
                    body = (ROOT / target).read_text(encoding="utf-8", errors="replace")
                    headings[target] = [_norm(h) for h in HEADING.findall(body)]
                if any(_matches(h, words) for h in headings[target]):
                    hit = True
                    break
            if hit:
                resolved += 1
            else:
                dangling.add((citing, words))
    return dangling, resolved


def test_every_heading_citation_names_a_heading_its_doc_has():
    dangling, resolved = _sweep()
    assert not dangling, "citations of a heading the cited doc does not have:\n" + "\n".join(
        f"  {citing}: *{words}*" for citing, words in sorted(dangling)
    )
    assert resolved >= RESOLVED_FLOOR, f"only {resolved} citations resolved"
