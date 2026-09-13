"""Guard: a record's prose has one copy in the source and a whole copy on the row.

Every record this package writes carries `*_is` / `*_are` fields — a sentence
saying what the number beside it means, what `null` means, and what a record
missing the field was taken before. The row carries that sentence **whole**, so a
record read years from now off the archive tier needs no checkout to resolve; the
*source* carries it once, in the module-level `SCHEMA_NOTES` beside that module's
`SCHEMA`, so one module's two records cannot disagree about the same field.

`src/fractal_wallpapers/README.md`'s *A record's prose has one copy in the source
and a whole copy on every row* is the argument, including the three things this
is deliberately not. What is enforced here is the mechanism:

* no `*_is` / `*_are` value is written as prose at a record site,
* every `SCHEMA_NOTES[...]` lookup names a note its own module holds,
* every note is read by something.

The sweep is over the source text and not over a run, because the defect is a
second spelling appearing in a module nothing in the fast lane exercises.
"""

from __future__ import annotations

import ast
import functools
import re
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "fractal_wallpapers"

#: The field names this is about. `_is` for one thing, `_are` for a collection.
FIELD = re.compile(r"^[a-z0-9_]+_(is|are)$")

#: What a note may be filed under: the field, or the field and which of a module's
#: records writes it where one module writes the field two ways. `held_out_is.fit`
#: against `held_out_is.drop_high_asymmetric` is the case, and the two notes differ
#: by three words — which is the disagreement this arrangement makes visible.
NOTE = re.compile(r"^[a-z0-9_]+_(is|are)(\.[a-z0-9_]+)?$")

#: Fields whose value is a NUMBER and not prose, so nothing about them belongs in
#: `SCHEMA_NOTES`. Earned one at a time: `one_swap_is` is milliseconds of one swap
#: on the fp16 bound, and reads `"one_swap_is": swap` for that reason.
NOT_PROSE = frozenset({"one_swap_is"})

#: What the sweep saw on 2026-09-12, the day the prose was lifted: **121** record
#: sites over 221 modules — 104 of them reading a note and 17 reading a roster
#: their module already keeps, like `gallery_grade_train.CORPORA` — and **110**
#: notes over 25 modules.
#:
#: They are asserted as FLOORS because every guard above passes on an empty list.
#: A sweep that silently stopped finding record sites — a moved package root, a
#: parse that started throwing, a rename of the field convention — would go green
#: and say so exactly as loudly as one that checked all 121. Raise them as records
#: are added; a reading that comes in UNDER one is a deletion to look at rather
#: than a number to repoint.
SWEPT_AT_LEAST = 121
NOTES_AT_LEAST = 110


@functools.cache
def modules() -> tuple[tuple[str, ast.Module], ...]:
    """Every module of the package, parsed once and shared by all three guards."""
    out = []
    for path in sorted(PACKAGE.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        out.append((str(path.relative_to(PACKAGE)).replace("\\", "/"), ast.parse(text)))
    return tuple(out)


def block_of(tree: ast.Module) -> ast.Dict | None:
    """One module's `SCHEMA_NOTES` literal, or `None` where it writes no records."""
    for node in tree.body:
        targets = getattr(node, "targets", None) or (
            [node.target] if isinstance(node, ast.AnnAssign) else []
        )
        if not any(isinstance(one, ast.Name) and one.id == "SCHEMA_NOTES" for one in targets):
            continue
        assert isinstance(node.value, ast.Dict), "SCHEMA_NOTES is a dict literal"
        return node.value
    return None


def notes_of(tree: ast.Module) -> dict[str, ast.expr] | None:
    """`{note: the value expression}`, or `None` where the module holds no block."""
    block = block_of(tree)
    if block is None:
        return None
    return {
        key.value: value
        for key, value in zip(block.keys, block.values, strict=True)
        if isinstance(key, ast.Constant)
    }


def prose(value: ast.expr) -> bool:
    """Is this value expression a sentence written here, rather than one read?"""
    if isinstance(value, ast.Constant):
        return isinstance(value.value, str) and value.value != ""
    if isinstance(value, ast.JoinedStr):
        return True
    if isinstance(value, ast.IfExp):
        return prose(value.body) or prose(value.orelse)
    if isinstance(value, ast.BinOp):
        return prose(value.left) or prose(value.right)
    return False


def record_sites(tree: ast.Module):
    """`(field, lineno, value)` for every `*_is` / `*_are` key a dict writes.

    The module's own `SCHEMA_NOTES` is skipped: its keys match the same pattern
    and its values are exactly the prose this is checking has a home.
    """
    block = block_of(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict) or node is block:
            continue
        for key, value in zip(node.keys, node.values, strict=True):
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                continue
            if FIELD.match(key.value) and key.value not in NOT_PROSE:
                yield key.value, key.lineno, value


def lookups(tree: ast.Module):
    """`(note, lineno)` for every `SCHEMA_NOTES[...]` in a module."""
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "SCHEMA_NOTES"
        ):
            for piece in ast.walk(node.slice):
                if isinstance(piece, ast.Constant) and isinstance(piece.value, str):
                    yield piece.value, node.lineno


def test_the_sweep_reaches_the_records_it_is_asserting_about():
    """The budget every guard below spends, and the assertion that it was filled."""
    swept = sum(1 for _, tree in modules() for _ in record_sites(tree))
    notes = sum(len(notes_of(tree) or ()) for _, tree in modules())
    assert swept >= SWEPT_AT_LEAST, f"only {swept} record site(s) swept; the sweep is broken"
    assert notes >= NOTES_AT_LEAST, f"only {notes} note(s) found; the sweep is broken"


def test_no_record_site_writes_its_own_prose():
    """The defect this exists for: a sentence spelled at the place it is written.

    104 sites across 25 modules were exactly that until 2026-09-12, and two
    modules had gone on to write one field two ways.
    """
    wrong = [
        f"{rel}:{line} {field}"
        for rel, tree in modules()
        for field, line, value in record_sites(tree)
        if prose(value)
    ]
    assert not wrong, (
        "these record sites carry their prose inline; it belongs in the module's "
        f"SCHEMA_NOTES, read at write time: {wrong}"
    )


def test_every_lookup_names_a_note_its_module_holds():
    """A lookup that resolves to nothing is a `KeyError` in a leg, hours in."""
    wrong = []
    for rel, tree in modules():
        held = notes_of(tree)
        for note, line in lookups(tree):
            if held is None or note not in held:
                wrong.append(f"{rel}:{line} {note}")
    assert not wrong, f"SCHEMA_NOTES lookups naming no note: {wrong}"


def test_every_note_is_read_and_named_for_its_field():
    """A note nothing reads is the second spelling arriving by another door."""
    unread, misnamed = [], []
    for rel, tree in modules():
        held = notes_of(tree)
        if held is None:
            continue
        read = {note for note, _ in lookups(tree)}
        unread += [f"{rel} {note}" for note in held if note not in read]
        misnamed += [f"{rel} {note}" for note in held if not NOTE.match(note)]
    assert not unread, f"SCHEMA_NOTES entries nothing reads: {unread}"
    assert not misnamed, f"SCHEMA_NOTES entries not named for a record field: {misnamed}"


@pytest.mark.parametrize(
    "rel", [rel for rel, tree in modules() if block_of(tree) is not None], ids=str
)
def test_every_note_is_prose_and_not_an_f_string(rel: str):
    """A note is a sentence, and a slot in it is `str.format`'s, not the parser's.

    An f-string here would be a note interpolated at **import** time, which puts
    the value back out of reach of the site that knows it and makes the module's
    constants an ordering problem. A template formatted at the site is neither.
    """
    tree = dict(modules())[rel]
    for note, value in (notes_of(tree) or {}).items():
        assert not isinstance(value, ast.JoinedStr), (
            f"{rel} {note} is an f-string; a note naming a runtime value is a "
            "str.format template the record site formats"
        )
        assert prose(value), f"{rel} {note} is not prose"
