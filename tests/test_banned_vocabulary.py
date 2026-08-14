"""Guard: names from earlier private versions of this project stay out.

The naming rule in `CLAUDE.md` says nothing ships under a name the article would
not teach. Code arrives here from an older codebase with its own vocabulary, and
renaming on the way in is the kind of discipline that holds right up until the
day it quietly does not. This test is the day-after check.

A term is banned as a *word*, not as a substring — the shortest one on the list
is jargon on its own and the opening of several ordinary English words — so every
pattern is anchored at word boundaries.

The allowlist is empty and each entry added to it would be a permanent exception
to the rule above. Note what does *not* need one: reports live in `scratch/`,
which is untracked, so writing about the old vocabulary is exempt by
construction rather than by exception.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

# Each term's last character is written as a character class, so this file is not
# itself a match for the pattern it compiles. The compiled regex is unaffected.
BANNED_TERMS = (
    "emissio[n]",
    "minin[g]",
    "sittin[g]",
    "deploy_tai[l]",
    "fractal-generato[r]",
    "fractal_generato[r]",
    "pre[f]",
)

BANNED = [re.compile(rf"\b{term}\b", re.IGNORECASE) for term in BANNED_TERMS]

# Deliberately empty. Every entry here is a permanent exception to the rule above.
ALLOWLIST: frozenset[str] = frozenset()

REPO_ROOT = Path(__file__).resolve().parents[1]


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [name for name in result.stdout.split("\0") if name]


def test_no_tracked_file_uses_the_old_vocabulary() -> None:
    offenders = []
    for name in tracked_files():
        if name in ALLOWLIST:
            continue
        path = REPO_ROOT / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:  # not text; test_history_purity owns that complaint
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern in BANNED:
                if pattern.search(line):
                    offenders.append(f"{name}:{line_number}: {pattern.pattern}")
    assert not offenders, "old-repository vocabulary in tracked files: " + "; ".join(offenders)


def spelled_out(term: str) -> str:
    """The term as it would appear in prose, with the escaping brackets removed."""
    return term.replace("[", "").replace("]", "")


def test_the_guard_would_actually_catch_something() -> None:
    """A guard that cannot fire is not a guard."""
    for term, pattern in zip(BANNED_TERMS, BANNED, strict=True):
        line = f"the {spelled_out(term)} stage"
        assert pattern.search(line), f"{pattern.pattern} missed '{line}'"


def test_the_guard_does_not_fire_on_ordinary_english() -> None:
    """Banning a word must not ban every word that starts with it."""
    for line in ("a preference for a prefix", "premature deployment", "the emissary left"):
        assert not any(pattern.search(line) for pattern in BANNED), line
