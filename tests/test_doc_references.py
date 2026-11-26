"""Guard: a docstring's [`module.name`] reference names a thing that exists.

The package's docstrings and comments point at code the way they point at docs,
in the bracketed form [`head.build`], [`roster.HEADS`], [`manifest_path`]. A
function renamed or deleted leaves every such reference pointing at nothing, and
nothing on screen says so: the sentence still reads. This is the code half of
`test_doc_citations.py`, and like it the check is structural only: does the named
module exist, and does it define the named thing. It never reads the words around
the reference.

Resolved statically, from the source, never by importing: the suite's install has
no `torch`, and half the modules that cite one another are torch's. The text
answers most references (a `def`, `class` or assignment it shows outright); `ast`
answers the rest.

How a reference resolves, from the module that writes it:

* A leading `fractal_wallpapers.` is dropped; the rest is a module path followed
  by names, the longest module prefix tried first.
* A module path is looked up beside the citing module, then in each package above
  it, then as the unique module whose dotted path ends with it.
* With no module prefix, the names are the citing module's own, or its package's.
* A name is a module-level `def`, `class`, assignment or import; an import (at any
  depth, since commands import lazily) is followed into the module it came from,
  and a package whose `__getattr__` asks a tuple of submodules is followed into
  them. A name after a class is that class's own: a method, a class attribute, a
  field, or a `self.<name>` assignment.
* A bare name also resolves to anything its own module binds by name at any depth:
  a method, a nested function, a parameter. A class docstring citing a sibling
  method is the common case.
* A trailing `()` is ignored; a name past a module-level constant or function (a
  dict's key, a nested helper) is not checked; a name ending in a file suffix is a
  file and not this guard's.
"""

from __future__ import annotations

import ast
import re
from functools import cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "fractal_wallpapers"

REFERENCE = re.compile(r"\[`([A-Za-z_][A-Za-z0-9_.]*?)(?:\(\))?`\](?!\()")

#: A bracketed name ending in one of these is a file (`LEGS.md`, bracketed), not
#: code: `test_doc_citations.py`'s territory, or nobody's.
FILE_SUFFIXES = frozenset({"md", "py", "rs", "js", "json", "jsonl", "toml", "html", "css"})

#: How many references resolved when this guard was written (3,810, after 38
#: dangling ones were repointed or unbracketed on 2026-11-25). A floor, as in
#: `test_doc_citations.py`: a sweep that silently stopped finding references
#: would pass the check above. Raise it as references are added.
RESOLVED_FLOOR = 3810


def _module_name(path: Path) -> str:
    parts = list(path.relative_to(PACKAGE.parent).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


@cache
def _modules() -> dict[str, Path]:
    return {_module_name(path): path for path in sorted(PACKAGE.rglob("*.py"))}


class _Symbols:
    """What one module defines at top level, and what each of its classes does."""

    def __init__(self, tree: ast.Module, name: str, is_package: bool) -> None:
        self.names: set[str] = set()
        self.imports: dict[str, tuple[str, str | None]] = {}
        self.classes: dict[str, set[str]] = {}
        self.delegates: list[str] = []
        self.inner: set[str] = set()
        package = name if is_package else name.rpartition(".")[0]
        for node in _statements(tree.body):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    local = alias.asname or alias.name.partition(".")[0]
                    self.imports[local] = (alias.name if alias.asname else local, None)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    anchor = package.split(".")
                    anchor = anchor[: len(anchor) - (node.level - 1)]
                    base = ".".join(anchor + ([base] if base else []))
                for alias in node.names:
                    self.imports[alias.asname or alias.name] = (base, alias.name)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.inner.add(node.name)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                arguments = node.args
                self.inner.update(
                    argument.arg
                    for argument in (
                        *arguments.posonlyargs,
                        *arguments.args,
                        *arguments.kwonlyargs,
                        *filter(None, (arguments.vararg, arguments.kwarg)),
                    )
                )
            if isinstance(node, ast.FunctionDef) and node.name == "__getattr__":
                asked = {leaf.id for leaf in ast.walk(node) if isinstance(leaf, ast.Name)}
                for top in tree.body:
                    if (
                        isinstance(top, ast.Assign)
                        and isinstance(top.value, (ast.Tuple, ast.List))
                        and any(isinstance(t, ast.Name) and t.id in asked for t in top.targets)
                    ):
                        self.delegates += [
                            f"{name}.{item.value}"
                            for item in top.value.elts
                            if isinstance(item, ast.Constant) and isinstance(item.value, str)
                        ]
        for node in self._top(tree.body):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.names.add(node.name)
            elif isinstance(node, ast.ClassDef):
                self.names.add(node.name)
                self.classes[node.name] = self._members(node)
            elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    for leaf in ast.walk(target):
                        if isinstance(leaf, ast.Name):
                            self.names.add(leaf.id)

    @staticmethod
    def _top(body: list[ast.stmt]):
        """Module-level statements, through the `if`/`try`/`with` that guard them."""
        for node in body:
            yield node
            if isinstance(node, (ast.If, ast.Try, ast.With)):
                yield from _Symbols._top(_blocks(node))

    @staticmethod
    def _members(node: ast.ClassDef) -> set[str]:
        members: set[str] = set()
        for item in _Symbols._top(node.body):
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                members.add(item.name)
            elif isinstance(item, (ast.Assign, ast.AnnAssign)):
                targets = item.targets if isinstance(item, ast.Assign) else [item.target]
                members |= {t.id for t in targets if isinstance(t, ast.Name)}
        for item in _statements(node.body):
            if isinstance(item, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = item.targets if isinstance(item, ast.Assign) else [item.target]
                members |= {
                    t.attr
                    for t in targets
                    if isinstance(t, ast.Attribute)
                    and isinstance(t.value, ast.Name)
                    and t.value.id in ("self", "cls")
                }
        return members


def _blocks(node: ast.stmt) -> list[ast.stmt]:
    """The statements nested directly in one statement: its bodies and handlers."""
    nested = [*getattr(node, "body", ()), *getattr(node, "orelse", ())]
    nested += getattr(node, "finalbody", ())
    for inner in (*getattr(node, "handlers", ()), *getattr(node, "cases", ())):
        nested += inner.body
    return [child for child in nested if isinstance(child, ast.stmt)]


def _statements(body: list[ast.stmt]):
    """Every statement at any depth, without walking the expressions: everything this
    guard reads is a statement, and `ast.walk` spent seconds in the expressions."""
    for node in body:
        yield node
        yield from _statements(_blocks(node))


@cache
def _text(module: str) -> str:
    return _modules()[module].read_text(encoding="utf-8")


@cache
def _symbols(module: str) -> _Symbols | None:
    path = _modules().get(module)
    if path is None:
        return None
    return _Symbols(ast.parse(_text(module)), module, path.name == "__init__.py")


TOP_LEVEL = re.compile(r"^(?:(?:async\s+)?def\s+|class\s+)?([A-Za-z_]\w*)\s*[:=(]", re.M)
ANY_DEF = re.compile(r"^[ \t]*(?:async\s+)?(?:def|class)\s+([A-Za-z_]\w*)", re.M)


@cache
def _plain(module: str) -> tuple[frozenset[str], frozenset[str]]:
    """`(column-0 names, def/class names at any depth)` as the text shows them."""
    text = _text(module)
    return frozenset(TOP_LEVEL.findall(text)), frozenset(ANY_DEF.findall(text))


def _plainly_defined(module: str, name: str, anywhere: bool = False) -> bool:
    """A definition the text shows outright: the shortcut past parsing most modules.

    Column 0 for a module-level name; any indent for a `def` or `class` when
    `anywhere`. Parsing is what the rest of this file falls back to, and it is
    most of this guard's cost (about 1.5 s over the whole package)."""
    if module not in _modules():
        return False
    top, nested = _plain(module)
    return name in (nested if anywhere else top)


MEMBER = re.compile(
    r"^    (?:(?:async\s+)?def\s+|class\s+)?([A-Za-z_]\w*)\s*[:=(]|self\.([A-Za-z_]\w*)\s*[:=]",
    re.M,
)


def _plain_member(module: str, owner: str, name: str) -> bool:
    """`owner.name` where the text shows a module-level class `owner` defining `name`:
    a method, an attribute or field at the class body's indent, or a `self.` store."""
    if module not in _modules():
        return False
    text = _text(module)
    start = re.search(rf"^class\s+{owner}\b.*$", text, re.M)
    if start is None:
        return False
    end = re.search(r"^[^\s#)\]]", text[start.end() :], re.M)
    block = text[start.end() : start.end() + end.start()] if end else text[start.end() :]
    return any(name in pair for pair in MEMBER.findall(block))


def _find_module(dotted: str, citing: str) -> list[str]:
    """The modules `dotted` may mean, from the module that wrote it."""
    modules = _modules()
    found = []
    anchor = citing.split(".")
    while anchor:
        candidate = ".".join([*anchor, dotted])
        if candidate in modules:
            found.append(candidate)
        anchor.pop()
    if dotted in modules:
        found.append(dotted)
    if not found:
        found = _by_suffix().get(dotted, [])
        if len(found) > 1:
            found = []
    return found


@cache
def _by_suffix() -> dict[str, list[str]]:
    """Every module under each dotted tail of its name: `head` and `models.head`."""
    index: dict[str, list[str]] = {}
    for name in _modules():
        parts = name.split(".")
        for start in range(1, len(parts)):
            index.setdefault(".".join(parts[start:]), []).append(name)
    return index


def _defines(module: str, names: list[str], depth: int = 0) -> bool:
    if not names:
        return module in _modules()
    if len(names) == 1 and _plainly_defined(module, names[0]):
        return True
    if len(names) == 2 and _plain_member(module, *names):
        return True
    symbols = _symbols(module)
    if symbols is None or depth > 8:
        return False
    first, rest = names[0], names[1:]
    if first in symbols.imports:
        source, name = symbols.imports[first]
        if source == "fractal_wallpapers" or source.startswith("fractal_wallpapers."):
            if name is None:
                return _defines(source, rest, depth + 1)
            if f"{source}.{name}" in _modules():
                return _defines(f"{source}.{name}", rest, depth + 1)
            return _defines(source, [name, *rest], depth + 1)
        return True  # a name from outside the package: not this guard's to check
    if first not in symbols.names:
        return any(_defines(module, names, depth + 1) for module in symbols.delegates)
    if not rest:
        return True
    if first in symbols.classes:
        return rest[0] in symbols.classes[first]
    return True


def _resolves(reference: str, citing: str) -> bool:
    parts = reference.split(".")
    if parts[0] == "fractal_wallpapers":
        parts = parts[1:]
        if not parts:
            return True
    for split in range(len(parts), 0, -1):
        for module in _find_module(".".join(parts[:split]), citing):
            if _defines(module, parts[split:]):
                return True
    if len(parts) == 1 and _plainly_defined(citing, parts[0], anywhere=True):
        return True
    package = citing if _modules()[citing].name == "__init__.py" else citing.rpartition(".")[0]
    if _defines(citing, parts) or _defines(package, parts):
        return True
    own = _symbols(citing)
    members = set().union(own.inner, *own.classes.values())
    return len(parts) == 1 and parts[0] in members


def _sweep() -> tuple[list[tuple[str, str]], int]:
    dangling: list[tuple[str, str]] = []
    resolved = 0
    for module, path in _modules().items():
        text = path.read_text(encoding="utf-8")
        for match in REFERENCE.finditer(text):
            if match.group(1).rpartition(".")[2] in FILE_SUFFIXES:
                continue
            if _resolves(match.group(1), module):
                resolved += 1
            else:
                dangling.append((path.relative_to(ROOT).as_posix(), match.group(1)))
    return dangling, resolved


#: Slow: about 1.1 s on this desktop, most of it parsing the three dozen modules
#: whose references the text cannot settle (`solve`, `depth`, `rules` among them).
#: The fast lane stops covering reference rot; `--slow` and CI's run still do.
@pytest.mark.slow
def test_every_code_reference_in_a_docstring_names_something_defined():
    dangling, resolved = _sweep()
    assert not dangling, "references to something the named module does not define:\n" + (
        "\n".join(f"  {path}: [`{reference}`]" for path, reference in sorted(set(dangling)))
    )
    assert resolved >= RESOLVED_FLOOR, f"only {resolved} references resolved"
