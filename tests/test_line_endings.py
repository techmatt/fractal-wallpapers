r"""Guard: every tracked text file is LF in the *working tree*, not just in git.

`.gitattributes` is `* text=auto eol=lf`, so git normalizes on the way in and a
CRLF working-tree file still commits as LF. That is what makes the drift
dangerous rather than merely untidy: `git status` never reports it, `git diff`
shows nothing, and the file sits there until something reads it and rewrites it
`newline="\n"` — changing every line at once, which is the hazard CLAUDE.md
names for code that writes tracked text.

Twenty files had drifted before this guard existed, scattered across `engine/`,
`src/` and `tests/`, and none of them had ever been reported by anything.

`git ls-files --eol` is the detector, and on this platform it is the only one
that works: Git Bash's `grep` reports a CR on every line of a pure-LF file, so a
grep-based check passes and fails for reasons unrelated to the tree.

Checkout is not the cause and there is nothing to fix in `.gitattributes` — a
fresh clone of this repository comes out 1901 files LF, zero CRLF, even with
`core.autocrlf=true` in the system git config. The drift comes from tools that
write a file and choose their own line endings.
"""

from __future__ import annotations

import functools
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

DRIFTED = frozenset({"w/crlf", "w/mixed"})


@functools.cache
def worktree_line_endings() -> tuple[tuple[str, str], ...]:
    """`(eol, path)` for every tracked file, as git sees the working tree.

    One sweep of the tree, shared by both guards below — it reads every tracked
    file to classify it, which is what makes this a slow-lane cost rather than
    arithmetic.
    """
    result = subprocess.run(
        ["git", "ls-files", "--eol"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    rows = []
    for line in result.stdout.splitlines():
        flags, _, name = line.partition("\t")
        eol = next((field for field in flags.split() if field.startswith("w/")), "")
        rows.append((eol, name.strip()))
    return tuple(rows)


@pytest.mark.slow
def test_no_tracked_file_carries_crlf_in_the_worktree() -> None:
    offenders = [f"{name} ({eol})" for eol, name in worktree_line_endings() if eol in DRIFTED]
    assert not offenders, (
        "tracked files carry CRLF in the working tree. git will not report them as "
        "modified, so the next tool that rewrites one silently changes every line. "
        f"Normalize them back to LF: {offenders}"
    )


@pytest.mark.slow
def test_the_line_ending_sweep_actually_reads_the_tree() -> None:
    """A parse that quietly yielded nothing would make the guard above vacuous.

    The same reasoning as `test_history_purity.py`'s checks on its own
    exemptions: a rule that cannot fail is a rule nobody is following.
    """
    rows = worktree_line_endings()
    assert len(rows) > 1000, f"git ls-files --eol returned {len(rows)} rows, expected the tree"
    unparsed = [name for eol, name in rows if not eol.startswith("w/")]
    assert not unparsed, (
        f"rows git ls-files --eol reported in a shape this parse missed: {unparsed}"
    )
