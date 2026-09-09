"""Every candidate this project has rendered, one row per recipe, kept.

A gallery pass makes candidates and then throws away everything about them
except a decision. The pictures stay on disk under `artifacts/`, and the rows in
the two decision stores say what was decided — but nothing anywhere answers the
question a solver has to ask first: **have we already made this picture?** 126
of the 15,488 candidate renders on record are the same recipe drawn twice by two
different passes, byte for byte, because nothing could tell either pass that the
other had already spent the seconds.

This is the store that answers it. One row per [`recipes.Recipe`], carrying the
location it stands on, the colour it turned out to be, where its picture is if
the picture is still there, and which pass paid for it.

## The modules

```
store      the two files, the tiers, the manifests, and reading rows out of them
rows       one row and the blocks it carries, as shape with no store behind it
ratchet    the high-water mark, and the deletions that account for a smaller store
rerender   putting back a picture the row names, and reading a score onto it
sweep      the retention rule, the orphan backstop, and the one delete verb
door       THE door: `merge` — upsert, record, prune, and every leg comes through it
rebuild    `backfill`: the ledger built out of the two decision stores that predate it
inventory  `census` and `feasibility`: what the pool holds, and what a solve can get
```

**Three of those are not named for the function they hold, and the reason is
mechanical.** A package cannot hold a module and a function of the same name: the
import system sets the submodule as an attribute of the package, and an attribute
that is already there is one `__getattr__` is never asked about — so
`candidate_ledger.merge` would answer with the *module*, silently, the first time
anything imported it. `door`, `rebuild` and `inventory` are what those modules
do; `merge`, `backfill` and `census` remain what the functions are called and what
`fractal-wallpapers curate candidate-ledger …` still spells.

`store`, `rows` and `ratchet` import nothing above them — no judge, no palette, no
label store, no leg — which is the whole point of the split: a reader that only
needs to know what is in the pool pays for none of the machinery that fills it.
`ratchet` goes further and imports nothing of this package either, so the census
that reads it does not drag the store in to ask what the mark is.

**Within the package, a sibling's *functions* are reached through its module
(`store.read()`) and its constants are imported by name.** The first half is not
a style preference: a test that redirects the store with
`monkeypatch.setattr(candidate_ledger.store, "rows_path", ...)` only reaches a
caller that looked the name up on the module.

Every name the single module exposed is reachable here, private ones included: a
call site that reached `candidate_ledger._framing` before the split still reaches
it, and nothing outside this package had to move.

**It resolves rather than re-exports, and that is a correctness rule and not a
style.** A `from .store import rows_path` here would bind a SECOND name to the
same function, and the two drift the moment anybody redirects one:
`curation.flatness` reads `candidate_ledger.manifest_dir` while
[`store.durable_rows`] reads `store.manifest_dir`, so a test that redirected the
store would move one of them and leave the other pointed at this machine's real
history. That is not hypothetical -- it is what six guards in
`tests/test_ledger_tracking.py` caught when this file was written the other way.
Going through `__getattr__` means there is one binding per name, exactly as there
was when this was one module.
"""

import importlib

#: The modules this package resolves a name through, in the order it asks them.
#: Order settles a tie between two modules holding the same name, and every tie
#: there is is a shared import of one object (`SCHEMA` in `rows` is `store`'s),
#: so it decides nothing. `store` leads because it owns the most.
#:
#: **That property is maintained rather than observed**, and `ratchet` is what
#: made the difference visible: its log carries a schema and is read row by row,
#: so the obvious names for those were `SCHEMA` and `read` — two ties that would
#: have been *different objects* wearing one name, resolved silently by this
#: tuple's order. They are `LOG_SCHEMA` and `entries` for that reason and no
#: other. A tie here has to be one object or it is a bug waiting on a reordering.
_MODULES = ("store", "rows", "ratchet", "rerender", "sweep", "door", "rebuild", "inventory")


def _held(module: str):
    return importlib.import_module(f"{__name__}.{module}")


def __getattr__(name: str):
    """Whatever module of this package holds `name`, asked at the moment it is read.

    The lookup, not a copy of the value: that is what keeps
    `monkeypatch.setattr(candidate_ledger.store, ...)` visible to a caller that
    spells it `candidate_ledger.<name>`.
    """
    if name in _MODULES:
        return _held(name)
    if not name.startswith("__"):
        for module in _MODULES:
            held = _held(module)
            if name in vars(held):
                return getattr(held, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """The whole surface, so `dir()` and a tab-complete still answer."""
    names = set(_MODULES)
    for module in _MODULES:
        names.update(n for n in vars(_held(module)) if not n.startswith("__"))
    return sorted(names)


__all__ = [
    "FIRST_SOLVE",
    "FROM_GALLERY",
    "FROM_RELEASE",
    "LedgerError",
    "MADE_IT",
    "ROWS_NAME",
    "ALL_UNMERGED",
    "PICTURES_NAME",
    "POOL_SUBTREES",
    "SCHEMA",
    "SCORES_NAME",
    "UNIT",
    "ENGINE_FIELD",
    "UNKNOWN_ENGINE",
    "LOG_SCHEMA",
    "LOG_NAME",
    "COUNTERS",
    "COUNTER_OF",
    "RECIPE_KEY",
    "RUN_INDEX",
    "MARK",
    "DELETED",
    "advance",
    "append",
    "counts_of",
    "entries",
    "log_path",
    "reading",
    "record_loss",
    "shape_of",
    "backfill",
    "bare_varied",
    "canonical_artifacts",
    "census",
    "check",
    "colour_block",
    "colour_kept",
    "delete_pictures",
    "engine_of",
    "hunt_block",
    "durable_rows",
    "durable_scores",
    "feasibility",
    "k_of",
    "live_artifact",
    "live_engine",
    "manifest_dir",
    "missing_pictures",
    "read_keys",
    "recolour",
    "merge",
    "read",
    "read_scores",
    "stream",
    "stream_scores",
    "re_render",
    "render_pair",
    "renders_of",
    "prune",
    "restore",
    "row",
    "rows_path",
    "save",
    "score_row",
    "scores_by_recipe",
    "rescore",
    "scores_path",
    "sources",
    "stale_scores",
    "store_root",
    "write",
    "write_scores",
]
