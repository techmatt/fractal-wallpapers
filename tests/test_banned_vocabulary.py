"""Guard: names from earlier private versions of this project stay out.

The naming rule in `CLAUDE.md` says nothing ships under a name the article would
not teach. Code arrives here from an older codebase with its own vocabulary, and
renaming on the way in is the kind of discipline that holds right up until the
day it quietly does not. This test is the day-after check.

A term is banned as a **name**, not as a substring — the shortest one on the list
is jargon on its own and the opening of several ordinary English words. So a term
is a hit when the characters touching it are not letters. That is deliberately
*not* `\\b`: `_` is a word character, so `\\bterm\\b` does not match `term_twin_top`,
and snake_case is the one form this vocabulary actually takes in this repository —
directory names, batch names, module names. Anchored at word boundaries this guard
passed for its whole life against names that were in the tree the entire time.

Two exceptions exist, and neither is a place a rename was declined:

* `FROZEN_RECORDS` — appended rows. A row records what a run wrote down; the term
  inside one is the name a sheet *had*, not a name this repository is choosing
  now. Renaming there would rewrite recorded data, which nothing here does.
* `FOREIGN_KEYS` — an exact literal, in one named file, that identifies something
  in another system. Renaming it does not rename the thing; it breaks the read.

`ALLOWLIST` is the third kind — a tracked file simply excused — and it is empty.
Every entry added to it would be a permanent exception to the rule above. Note
what does *not* need one: reports live in `scratch/`, which is untracked, so
writing about the old vocabulary is exempt by construction rather than by
exception.
"""

from __future__ import annotations

import functools
import json
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


def spelled_out(term: str) -> str:
    """The term as it would appear in prose, with the escaping brackets removed."""
    return term.replace("[", "").replace("]", "")


#: A letter on either side means this is a longer word and not the term. Anything
#: else — `_`, `-`, `/`, `.`, a digit, a space, the end of the line — means the
#: term is there, wearing the clothes the names in this repository actually wear.
BANNED = [re.compile(rf"(?<![a-z]){term}(?![a-z])", re.IGNORECASE) for term in BANNED_TERMS]

#: Appended record files. Not exceptions to the naming rule: the rule governs what
#: this repository *names* things, and these hold what a past run wrote down. The
#: glob is kept narrow and `test_every_frozen_record_glob_matches_only_records`
#: proves each file it reaches is one JSON object per line carrying a schema — so
#: this cannot quietly grow to cover source.
FROZEN_RECORDS: tuple[tuple[str, str], ...] = (
    (
        "data/*/rows/*.jsonl",
        "stored labels: each row records the sheet a verdict was cast on, and "
        "nothing re-keys hand-labeled data",
    ),
)

#: (file, exact literal, why). The literal is removed from a line before the ban
#: is applied, so the exception covers those characters in that file and nothing
#: else — not the rest of the line, not the same string elsewhere.
FOREIGN_KEYS: tuple[tuple[str, str, str], ...] = (
    (
        "src/fractal_wallpapers/labeling/corpus_import.py",
        "2026-06-25_minin[g]_v3guided_v1",
        "names a batch directory in the read-only source project; the import reads it",
    ),
    (
        "src/fractal_wallpapers/labeling/corpus_import.py",
        "2026-08-03_v2_sittin[g]_v1",
        "names a batch directory in the read-only source project; the import reads it",
    ),
    (
        "src/fractal_wallpapers/models/palette_sets.py",
        "pre[f]_fit",
        "the source corpus's own field name for the score its deployed head gave its pick",
    ),
)

# Deliberately empty. Every entry here is a permanent exception to the rule above.
ALLOWLIST: frozenset[str] = frozenset()

REPO_ROOT = Path(__file__).resolve().parents[1]


@functools.cache
def tracked_files() -> tuple[str, ...]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(name for name in result.stdout.split("\0") if name)


def is_frozen_record(name: str) -> bool:
    path = Path(name)
    return any(path.match(pattern) for pattern, _ in FROZEN_RECORDS)


def without_foreign_keys(name: str, line: str) -> str:
    """The line with this file's declared foreign keys cut out of it."""
    for owner, literal, _ in FOREIGN_KEYS:
        if owner == name:
            line = line.replace(spelled_out(literal), "")
    return line


#: The banned terms as plain lowercase strings, for the pre-check below.
SPELLED = tuple(spelled_out(term).lower() for term in BANNED_TERMS)


def offenders_in(name: str, text: str) -> list[str]:
    """Every banned name in one file, as `file:line: pattern`.

    Two passes, and the first one is a substring search rather than a regex. Each
    pattern is a literal wearing a pair of lookarounds, so a file that does not
    contain the bare characters cannot match — the pre-check is a superset of the
    ban and is allowed to be as generous as it likes, since the second pass is
    what convicts. It is generous: every ordinary use of `preference` reaches it.

    That matters because this sweep reads every tracked file, which is twenty-odd
    megabytes of text here. Running seven lookaround patterns over all of it was
    the whole cost of this file; running one lowercase substring search over it
    and the patterns over the sixty-odd files that survive is not measurable.
    """
    text = without_foreign_keys(name, text)
    lowered = text.lower()
    if not any(spelled in lowered for spelled in SPELLED):
        return []
    return [
        f"{name}:{number}: {pattern.pattern}"
        for number, line in enumerate(text.splitlines(), start=1)
        for pattern in BANNED
        if pattern.search(line)
    ]


def test_no_tracked_file_uses_the_old_vocabulary() -> None:
    offenders = []
    for name in tracked_files():
        if name in ALLOWLIST or is_frozen_record(name):
            continue
        path = REPO_ROOT / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:  # not text; test_history_purity owns that complaint
            continue
        offenders.extend(offenders_in(name, text))
    assert not offenders, "old-repository vocabulary in tracked files: " + "; ".join(offenders)


def test_the_sweep_reports_the_line_a_planted_name_is_on() -> None:
    """The planted red for the sweep, as distinct from the patterns it runs.

    A pre-check that answered "clean" for a file the patterns would have
    convicted is the one way this guard can go quiet without failing, so the
    planted name is buried in a long otherwise-clean file and the sweep is asked
    to name the line it is on.
    """
    for index, term in enumerate(BANNED_TERMS):
        spelled = spelled_out(term)
        text = "a clean line\n" * 40 + f"batch = 'twin_top_{spelled}'\n" + "a clean line\n"
        assert offenders_in("src/somewhere.py", text) == [
            f"src/somewhere.py:41: {BANNED[index].pattern}"
        ], spelled
    assert not offenders_in("src/somewhere.py", "a clean line\n" * 41)


def test_the_pre_check_cannot_reject_a_file_the_patterns_would_convict() -> None:
    """The sweep's fast path is a substring search, and it is sound only because
    every pattern is a literal in lookarounds. A term written with anything the
    substring search could not find — a character class doing real work, an
    alternation — would pass this guard while never being looked for."""
    for term, spelled, pattern in zip(BANNED_TERMS, SPELLED, BANNED, strict=True):
        assert pattern.pattern == rf"(?<![a-z]){term}(?![a-z])", term
        # The term is the spelled name with one character wrapped in a class, and
        # what is left over holds nothing a regex reads as anything but itself.
        assert not set(spelled) & set(r".^$*+?{}|()[]\\"), term
        assert pattern.search(spelled) and pattern.search(spelled.upper()), term


def test_the_guard_would_actually_catch_something() -> None:
    """A guard that cannot fire is not a guard."""
    for term, pattern in zip(BANNED_TERMS, BANNED, strict=True):
        line = f"the {spelled_out(term)} stage"
        assert pattern.search(line), f"{pattern.pattern} missed '{line}'"


def test_the_guard_catches_the_snake_case_form_word_boundaries_missed() -> None:
    """The planted red: the form these names actually take.

    `\\b` is compared against, not consulted — the expectation is that every
    planted line *is* a violation, written down here, and the old pattern is
    shown missing it rather than asked what the answer should be.
    """
    word_bounded = [re.compile(rf"\b{term}\b", re.IGNORECASE) for term in BANNED_TERMS]
    for term, pattern, old in zip(BANNED_TERMS, BANNED, word_bounded, strict=True):
        spelled = spelled_out(term)
        for planted in (
            f"artifacts/{spelled}_twin_top/plan.jsonl",  # bounded by a separator and a `_`
            f"artifacts/twin_top_{spelled}",  # bounded by a `_` and the end of the line
            f'    directory = Path("{spelled}_plane_deep")',  # in source, as it would appear
        ):
            assert pattern.search(planted), f"{pattern.pattern} missed '{planted}'"
            assert not old.search(planted), (
                f"'{planted}' is not a planted red: the old word-bounded pattern caught it too"
            )


def test_the_guard_does_not_fire_on_ordinary_english() -> None:
    """Banning a word must not ban every word that starts with it."""
    for line in (
        "a preference for a prefix",
        "premature deployment",
        "the emissary left",
        "PREFIXED and Preferred and preflight",
    ):
        assert not any(pattern.search(line) for pattern in BANNED), line


def test_every_frozen_record_glob_matches_only_records() -> None:
    """The frozen-record exception cannot be pointed at source.

    Every file it reaches must be one JSON object per line carrying an integer
    `schema`, which is what this repository means by a record file.
    """
    for pattern, why in FROZEN_RECORDS:
        reached = [name for name in tracked_files() if Path(name).match(pattern)]
        assert reached, f"{pattern} matches nothing; a dead exception is a lie about coverage"
        assert why.strip(), f"{pattern} carries no reason"
        for name in reached:
            with (REPO_ROOT / name).open(encoding="utf-8") as handle:
                for number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    assert isinstance(row, dict), f"{name}:{number} is not a record"
                    assert isinstance(row.get("schema"), int), f"{name}:{number} carries no schema"
                    if number >= 5:  # the shape is the file's, not the fifth line's
                        break


def test_every_foreign_key_is_still_quoted_where_it_says_it_is() -> None:
    """An exception that outlived its line stops being an exception."""
    for name, literal, why in FOREIGN_KEYS:
        path = REPO_ROOT / name
        assert path.is_file(), f"{name} does not exist; its exception is stale"
        text = path.read_text(encoding="utf-8")
        assert spelled_out(literal) in text, f"{name} no longer quotes {spelled_out(literal)!r}"
        assert why.strip(), f"{name}:{literal} carries no reason"


def test_a_foreign_key_excuses_itself_and_not_its_line() -> None:
    """Cutting the literal out must not take the rest of the line with it."""
    name, literal, _ = FOREIGN_KEYS[0]
    spelled = spelled_out(literal)
    line = f'    "{spelled}": Imported(batch="{spelled_out("sittin[g]")}_plane_deep"),'
    assert offenders_in(name, line), "the exception swallowed a violation that shared its line"
    assert not offenders_in(name, f'    "{spelled}",'), "the declared key is not excused"
