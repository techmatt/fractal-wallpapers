"""`FORMATS.md` names every field its writers write.

`FORMATS.md` is the one home for the format of every file a reader inspects, and it
goes stale the way any second spelling does: a writer gains a field and nothing
says so. So each writer is read here — the dict literal it builds its rows from,
parsed out of the source, or the engine's own key lists — and every key in it must
appear, backticked, in the section of `FORMATS.md` that owns that file. The check is
name-level: it catches a field nobody documented, and a person still owns whether
the sentence beside it is right.

Reading source rather than running the writers keeps this arithmetic: no store, no
engine, no fixture, a few hundredths of a second.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "src" / "fractal_wallpapers"


def section(heading: str) -> str:
    """The text of one `## heading` section of FORMATS.md."""
    text = (ROOT / "FORMATS.md").read_text(encoding="utf-8")
    parts = re.split(r"^## ", text, flags=re.M)
    for part in parts:
        if part.splitlines()[0].strip() == heading:
            return part
    raise AssertionError(f"FORMATS.md has no `## {heading}` section")


def named(heading: str) -> set[str]:
    """Every backticked token in a section, split on the separators tables use."""
    tokens = set()
    for span in re.findall(r"`([^`]+)`", section(heading)):
        tokens |= {piece.strip() for piece in re.split(r"[\s,{}|:()\[\]]+", span) if piece}
    return tokens


def literal_keys(path: str, function: str, marker: set[str]) -> set[str]:
    """The string keys of the dict literal in `function` that holds every `marker` key.

    The marker picks the row literal out of a function that builds several (a
    report beside the rows, a nested block); a function whose row literal lost a
    marker key fails here rather than silently reading another dict.
    """
    tree = ast.parse((SOURCE / path).read_text(encoding="utf-8"))
    found = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == function
    ]
    assert found, f"{path} has no function {function}"
    for node in ast.walk(found[0]):
        if isinstance(node, ast.Dict):
            keys = {k.value for k in node.keys if isinstance(k, ast.Constant)}
            if marker <= keys:
                return {key for key in keys if isinstance(key, str)}
    raise AssertionError(f"{path}:{function} builds no dict holding {sorted(marker)}")


#: (FORMATS.md section, writer module, writer function, keys that pick the row literal)
WRITERS = [
    ("locations.jsonl", "supply/places.py", "rows", {"root_channel", "slot_channel"}),
    ("walk.jsonl", "discovery/walk.py", "_candidate", {"fate", "child_index"}),
    ("supply_scores.jsonl", "curation/intake.py", "score", {"head_sha256", "node_id"}),
    ("Candidate ledger rows", "curation/candidate_ledger/rows.py", "row", {"at_candidate_regime"}),
    ("Candidate ledger rows", "curation/recipes.py", "record", {"palette_group", "autolevel"}),
    ("Candidate ledger scores", "curation/candidate_ledger/rows.py", "score_row", {"read_by"}),
    ("Candidate ledger flatness", "curation/flatness.py", "row", {"recipe_key", "threshold"}),
    ("pool_scores.jsonl", "models/gallery_grade_train.py", "score_pool", {"weights", "key"}),
    ("solve.json", "curation/solve.py", "solve", {"seated", "rejection"}),
    ("solve.json", "curation/solve.py", "_seated", {"seated_for", "above_bar"}),
    ("solve.json", "curation/solve.py", "_config", {"force_fill", "mode_policy"}),
    ("solve.json", "curation/solve.py", "_config", {"k", "kf", "target_rule"}),
    ("solve.json", "curation/solve.py", "solve", {"rank_quantity", "q4_bar"}),
    ("solve.json", "curation/solve.py", "solve", {"reachable_clusters", "truncation_is"}),
    ("gallery.jsonl", "curation/tentative.py", "rows_of", {"alias", "floor_cells"}),
    ("manifest.json", "curation/tentative.py", "manifest_of", {"source_commit", "counts"}),
    ("manifest.json", "curation/tentative.py", "manifest_of", {"diversity_is", "pins"}),
    ("manifest.json", "curation/tentative.py", "manifest_of", {"stamp_is", "ledger_rows"}),
    ("manifest.json", "curation/tentative.py", "manifest_of", {"asked", "recorded"}),
    ("keep.jsonl", "curation/tentative.py", "_keep_row", {"stamp", "kept"}),
    ("page.json", "grid_page.py", "document", {"intro", "sections"}),
    ("page.json", "grid_page.py", "document", {"heading", "tiles"}),
    ("page.json", "grid_page.py", "document", {"picture", "caption"}),
    ("page.json", "grid_page.py", "document", {"joined_on", "row"}),
    ("Gallery page.json", "curation/tentative.py", "page", {"stamp", "ordered_by"}),
    ("counts.json", "curation/trace.py", "build", {"broken_chains", "files"}),
    ("counts.json", "curation/trace.py", "counted", {"source", "sliced"}),
    ("walkthrough.json", "walkthrough.py", "build", {"pages", "files"}),
]


@pytest.mark.parametrize(("heading", "path", "function", "marker"), WRITERS)
def test_every_field_a_writer_writes_is_named_in_its_section(heading, path, function, marker):
    missing = literal_keys(path, function, marker) - named(heading)
    assert not missing, (
        f"{path}:{function} writes {sorted(missing)} and FORMATS.md's `## {heading}` does not "
        f"name them. Add each with its type and meaning."
    )


def test_every_walk_row_kind_is_named():
    """Every literal kind a ledger writer in the walk's packages writes, and the
    constants they write through."""
    from fractal_wallpapers.discovery import ledger, reframing

    kinds = {"run", ledger.REFINED, reframing.FIRE_KIND, reframing.SUMMARY_KIND}
    kinds |= {"twin_seed", "twin_skip"}
    pattern = re.compile(r'ledger\.write\(\s*"([a-z_]+)"', re.S)
    for package in ("discovery", "supply", "deep"):
        for path in (SOURCE / package).glob("*.py"):
            kinds |= set(pattern.findall(path.read_text(encoding="utf-8")))
    missing = kinds - named("walk.jsonl")
    assert not missing, f"walk.jsonl row kinds FORMATS.md does not name: {sorted(missing)}"


def rust_struct_fields(path: str, struct: str) -> set[str]:
    text = (ROOT / "engine" / "src" / path).read_text(encoding="utf-8")
    body = re.search(rf"pub struct {struct} \{{(.*?)\n\}}", text, re.S)
    assert body, f"engine/src/{path} has no struct {struct}"
    return set(re.findall(r"^\s*pub (\w+):", body.group(1), re.M))


def test_every_render_spec_and_palette_key_is_named():
    spec = rust_struct_fields("spec.rs", "RenderSpec")
    palette = rust_struct_fields("coloring.rs", "Palette") - {"bake"}
    palette |= rust_struct_fields("colormap.rs", "Bake")
    missing = (spec | palette) - named("The render spec")
    assert not missing, f"render spec keys FORMATS.md does not name: {sorted(missing)}"
    kinds = set(re.findall(r'"kind":\s*"(\w+)"', section("The render spec")))
    variants = (ROOT / "engine" / "src" / "spec.rs").read_text(encoding="utf-8")
    enum = re.search(r"pub enum FamilySpec \{(.*?)\n\}", variants, re.S)
    assert enum
    declared = {
        re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
        for name in re.findall(r"^\s{4}([A-Z]\w*)", enum.group(1), re.M)
    }
    assert declared <= named("The render spec") | kinds, (
        f"family kinds FORMATS.md does not name: {sorted(declared - named('The render spec'))}"
    )


def test_every_link_key_the_website_s_cases_use_is_named():
    """The website owns the vocabulary; its own cases are the population."""
    cases = json.loads((ROOT / "engine" / "fixtures" / "link-cases.json").read_text("utf-8"))
    keys = set()
    for case in cases["cases"]:
        if case.get("ok") is False:
            continue
        query = str(case.get("query") or "").lstrip("?")
        keys |= {pair.split("=", 1)[0] for pair in query.split("&") if pair}
    missing = keys - named("The explorer link")
    assert not missing, f"explorer-link keys FORMATS.md does not name: {sorted(missing)}"
