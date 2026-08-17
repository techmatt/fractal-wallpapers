"""Human labels are never lost and never lose their meaning. Everything else is regenerable.

That sentence is the whole standard, and each test here is one way it could stop
being true without anybody noticing. A second module that opens the records is a
second answer to what the corpus says. A writer that opens a row file for
anything but appending is an edit that leaves no trace of what it replaced. A
stored row that cannot express its own identity is a verdict about a picture
nobody can rebuild — and it fails silently, because a corpus with holes in it
still trains a head.

`tests/test_label_store.py` holds the same choke-point guard for the location
records. This file holds the finished-render half of it, the append-only rule for
both, and the on-disk audit of what is actually shipped.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

from fractal_wallpapers.labeling import finished, store
from fractal_wallpapers.labeling import registry as registry_module

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The one module allowed to know where the finished-render records live.
FINISHED_MODULE = "src/fractal_wallpapers/labeling/finished.py"


def tracked_sources() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "src"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [name for name in result.stdout.split("\0") if name.endswith(".py")]


# --------------------------------------------------------------------------- #
# One reader, per corpus.
# --------------------------------------------------------------------------- #
def addresses_a_finished_store(source: str) -> bool:
    """Whether this source builds a path through a finished-render store's own name.

    Path *building* rather than the word, for the same reason the location guard
    reads it that way: half a dozen module docstrings name these corpora, a
    report key is spelled the same, and neither is a second reader. What a second
    reader has to write is a join — `something / "smooth_render"` — or a path
    with the directory inside it.
    """

    def named(node) -> bool:
        return isinstance(node, ast.Constant) and node.value in finished.HEADS

    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.BinOp)
            and isinstance(node.op, ast.Div)
            and (named(node.left) or named(node.right))
        ):
            return True
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "Path":
            for argument in node.args:
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    spelled = argument.value.replace("\\", "/")
                    if any(spelled.endswith(f"/{head}") for head in finished.HEADS):
                        return True
    return False


def test_only_the_finished_store_addresses_the_finished_records() -> None:
    offenders = [
        name
        for name in tracked_sources()
        if name.replace("\\", "/") != FINISHED_MODULE
        and addresses_a_finished_store((REPO_ROOT / name).read_text(encoding="utf-8"))
    ]
    assert not offenders, (
        "these modules address a finished-render store themselves instead of going through "
        f"{FINISHED_MODULE}: {offenders}. Nearly eight thousand verdicts are in there and a "
        "second reader is a second answer about every one of them."
    )


def test_that_guard_would_actually_catch_something() -> None:
    """A guard that cannot fire is not a guard."""
    assert addresses_a_finished_store('path = repo_root() / "data" / "smooth_render"')
    assert addresses_a_finished_store('path = Path("data/strange_render")')
    assert not addresses_a_finished_store('"""Prose about smooth_render is not a reader."""')
    assert not addresses_a_finished_store('BARS = {"strange_render": 0.5}')


# --------------------------------------------------------------------------- #
# Append, or nothing.
# --------------------------------------------------------------------------- #
def opens_in(source: str) -> set[tuple[str, str]]:
    """`{(function, mode)}` for every `.open(...)` in a module."""
    tree = ast.parse(source)
    out: set[tuple[str, str]] = set()
    for parent in ast.walk(tree):
        if not isinstance(parent, ast.FunctionDef):
            continue
        for node in ast.walk(parent):
            if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "open":
                mode = "r"
                if node.args and isinstance(node.args[0], ast.Constant):
                    mode = str(node.args[0].value)
                out.add((parent.name, mode))
    return out


#: Every way a store module is allowed to open a file, and each one is a decision.
#: A row file is opened `a` to write and read-only to read, and that is the whole
#: list — an edit in place is an edit that leaves no trace of what it replaced.
#: `write_pin` is the one `w`, and what it rewrites is not a row: the pinned side
#: is a view over rows that already exist and is regenerated from them.
EXPECTED_OPENS = {
    "src/fractal_wallpapers/labeling/store.py": {("register", "a"), ("append", "a"), ("read", "r")},
    FINISHED_MODULE: {
        ("register", "a"),
        ("append", "a"),
        ("read", "r"),
        ("write_pin", "w"),
        ("pinned", "r"),
    },
}

#: Verbs that end a row rather than adding one.
DESTRUCTIVE = ("unlink", "rmdir", "rename", "replace", "truncate", "write_text", "write_bytes")

#: The one place a store module may write a whole file. `write_pin` ships the
#: pinned evaluation side, which is a view over rows that already exist.
ALLOWED_WHOLE_FILE_WRITES = {(FINISHED_MODULE, "write_pin", "write_text")}


def whole_file_writes(source: str) -> set[tuple[str, str]]:
    """`{(function, verb)}` for every call that could end or replace a file."""
    out: set[tuple[str, str]] = set()
    for parent in ast.walk(ast.parse(source)):
        if not isinstance(parent, ast.FunctionDef):
            continue
        for node in ast.walk(parent):
            if isinstance(node, ast.Call) and getattr(node.func, "attr", None) in DESTRUCTIVE:
                out.add((parent.name, node.func.attr))
    return out


@pytest.mark.parametrize("module", sorted(EXPECTED_OPENS))
def test_a_store_module_opens_a_row_file_to_append_and_nothing_else(module: str) -> None:
    source = (REPO_ROOT / module).read_text(encoding="utf-8")
    assert opens_in(source) == EXPECTED_OPENS[module], (
        f"{module} opens a file in a way this test did not know about. Adding it here is a "
        "decision about whether a stored verdict can be replaced in place."
    )


@pytest.mark.parametrize("module", sorted(EXPECTED_OPENS))
def test_a_store_module_never_deletes_or_rewrites(module: str) -> None:
    source = (REPO_ROOT / module).read_text(encoding="utf-8")
    found = sorted(
        (function, verb)
        for function, verb in whole_file_writes(source)
        if (module, function, verb) not in ALLOWED_WHOLE_FILE_WRITES
    )
    assert not found, (
        f"{module} calls {found}. A verdict that changes is a new row; nothing here removes "
        "one, and the earlier one stays readable underneath the later one forever."
    )


def test_a_revision_leaves_the_original_byte_for_byte(tmp_path, monkeypatch) -> None:
    """The rule the append-only guards exist to protect, exercised rather than read."""
    monkeypatch.setattr(store, "label_dir", lambda: tmp_path / "labels")
    store.register(registry_module.Registration(batch="b", method="a draw, for a test"))
    first = store.label_row(
        batch="b",
        score=2,
        family={"kind": "mandelbrot"},
        viewport={"center_re": "0", "center_im": "0", "width": "3"},
        recorded_at="2026-08-17T00:00:00Z",
    )
    path = store.append([first])
    original = path.read_bytes()
    store.append([{**first, "score": 4, "recorded_at": "2026-08-18T00:00:00Z"}])
    assert path.read_bytes().startswith(original)
    resolution = store.resolved()
    assert resolution.n_rows == 2 and resolution.n_superseded == 1
    assert [row["score"] for row in resolution.scored()] == [4]


# --------------------------------------------------------------------------- #
# What is actually on disk.
# --------------------------------------------------------------------------- #
def test_every_stored_location_row_carries_its_whole_join() -> None:
    if not store.registry_path().is_file():
        pytest.skip("the location store has not been imported on this machine")
    resolution = store.resolved()
    assert resolution.n_rows > 0
    assert resolution.n_unkeyed == 0, "rows with no location identity"
    known = store.registry()
    unregistered = sorted({row["batch"] for row in resolution.scored()} - set(known))
    assert not unregistered, f"batches with rows and no registration: {unregistered}"


@pytest.mark.parametrize("head", sorted(finished.HEADS))
def test_every_stored_render_row_carries_its_whole_join(head: str) -> None:
    if not finished.registry_path(head).is_file():
        pytest.skip(f"the {head} store has not been imported on this machine")
    resolution = finished.resolved(head)
    assert resolution.n_rows > 0
    assert resolution.n_unkeyed == 0, f"{head}: rows with no render identity"
    known = finished.registry(head)
    scored = resolution.scored()
    unregistered = sorted({row["batch"] for row in scored} - set(known))
    assert not unregistered, f"{head}: batches with rows and no registration: {unregistered}"
    for row in scored:
        assert row.get("origin") == store.HUMAN or str(row.get("origin", "")).startswith(
            store.RULE_PREFIX
        )
    train = [row for row in scored if not registry_module.lookup(known, row["batch"]).eval_only]
    assert finished.assert_pin_holds(head, train)["ok"]


# --------------------------------------------------------------------------- #
# The drop.
# --------------------------------------------------------------------------- #
def test_the_drop_is_intake_and_no_tracked_file_lives_in_it() -> None:
    """`labels/` is where a page saves. Nothing tracked may live there: a verdict
    that only exists in the drop is a verdict the store never resolved."""
    tracked = subprocess.run(
        ["git", "ls-files", "-z", "labels"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert not [name for name in tracked.split("\0") if name], (
        "something under labels/ is tracked. That directory is a drop: what a page saves "
        "there is intake, and `label ingest` is what makes it durable."
    )


def test_the_drop_is_ignored_rather_than_merely_untracked() -> None:
    """It was untracked by decision and enforced by nothing, which is the state a
    rule rots from. The one line in `.gitignore` is what makes it a rule."""
    ignored = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "labels/" in [line.strip() for line in ignored]
