"""Fixtures shared across the suite: a disposable store, and the tracked ones.

The label store addresses one directory under the repository, deliberately: a
store whose location is a parameter is a store that gets written to twice. Tests
redirect that one function and get a whole empty store, which is also the
cheapest proof that everything really does address the records through it.

The session-scoped fixtures below are the other half of that. Several files ask
the same question of the *tracked* records — resolve the label store, lay out the
tile plan, walk the render cache for what is missing — and each answer costs a
second or more to derive and is the same every time it is asked. They are
fixtures rather than module-level caches so that the sharing is opt-in: a test
that redirects a store to `tmp_path` simply does not ask for them, and cannot be
handed a reading of the tracked corpus by accident.

Nothing here is written to. A test that needs to mutate one of these readings
should take its own copy.

The other thing this file owns is the **slow lane** — the `slow` marker, the
`--slow` flag that runs it, and the line the fast lane prints to say how many
guards it just held back. A guard that goes quiet is a guard nobody notices
going missing, so the count is printed on every run that deselects anything.
"""

from __future__ import annotations

import functools
from types import SimpleNamespace

import pytest

from fractal_wallpapers.labeling import registry as registry_module
from fractal_wallpapers.labeling import store

# --------------------------------------------------------------------------- #
# The slow lane.
# --------------------------------------------------------------------------- #
HELD_BACK = pytest.StashKey[int]()

SLOW = (
    "slow: real work rather than arithmetic about it — a render through the engine, a "
    "training loop, or a sweep of a store (the render cache, the tracked pool, the "
    "distillation corpus). Held back unless --slow is given, which CI and the "
    "pre-checkpoint run give."
)


def pytest_addoption(parser) -> None:
    parser.addoption(
        "--slow",
        action="store_true",
        default=False,
        help="run the slow lane as well, which is every test there is. What CI runs.",
    )


def pytest_configure(config) -> None:
    config.addinivalue_line("markers", SLOW)


def pytest_collection_modifyitems(config, items) -> None:
    """Hold the slow lane back, and remember how much was held.

    Deselected rather than skipped: a skip is a test that ran and decided not to,
    and these did not run at all. The count is printed below, which is the half
    of this that matters — the lane exists to be cheap, not to be quiet.
    """
    if config.getoption("--slow"):
        return
    held = [item for item in items if item.get_closest_marker("slow") is not None]
    if not held:
        return
    items[:] = [item for item in items if item.get_closest_marker("slow") is None]
    config.hook.pytest_deselected(items=held)
    config.stash[HELD_BACK] = len(held)


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    held = config.stash.get(HELD_BACK, 0)
    if not held:
        return
    tests = "test" if held == 1 else "tests"
    terminalreporter.write_sep(
        "=",
        f"{held} slow {tests} not run - `python -m pytest --slow` runs everything",
        yellow=True,
        bold=True,
    )


@pytest.fixture
def store_dir(tmp_path, monkeypatch):
    """An empty label store, and everything in the package pointed at it."""
    directory = tmp_path / "labels"
    monkeypatch.setattr(store, "label_dir", lambda: directory)
    return directory


@pytest.fixture
def registered(store_dir):
    """Register a batch and hand back the registry, for tests that need a writer."""

    def register(batch: str, **flags) -> dict:
        store.register(
            registry_module.Registration(
                batch=batch,
                method=flags.pop("method", "a draw, for a test"),
                **flags,
            )
        )
        return store.registry()

    return register


# --------------------------------------------------------------------------- #
# The tracked records, read once.
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def shipped_labels():
    """The tracked label store, resolved once."""
    return store.resolved()


@pytest.fixture(scope="session")
def shipped_scored(shipped_labels):
    """Every scored row of the tracked store, in the order the store hands them."""
    return shipped_labels.scored()


@pytest.fixture(scope="session")
def shipped_tile_plan(shipped_scored):
    """The training population laid out over the tracked store, at the shipped seed.

    Laying it out walks every row and re-derives every id, which is a second's
    work repeated by every test that wants to look at the population.
    """
    from fractal_wallpapers.models import tiles as tile_module

    return tile_module.plan(shipped_scored, seed=0)


@pytest.fixture(scope="session")
def shipped_render_cache():
    """The finished-render cache as it stands on this machine.

    Laying out a head's plan digests every row of its store, and `missing` is
    that plan filtered by what is on disk — so asking both questions of both
    heads, as tests in two files do, lays the same plan out four times.

    `missing` is still the real one. It is called with the cached plan bound
    under it for the length of the call, rather than reimplemented here: a
    fixture that filtered the plan itself would be a second answer to *is the
    cache complete*, which is the question that function exists to own.
    """
    from unittest import mock

    from fractal_wallpapers.models import renders

    plan = functools.cache(renders.plan)

    @functools.cache
    def missing(head: str) -> list[dict]:
        with mock.patch.object(renders, "plan", plan):
            return renders.missing(head)

    return SimpleNamespace(plan=plan, missing=missing)


@pytest.fixture(scope="session")
def distillation_rows():
    """The tracked palette-distillation corpus, or a skip where it is not built."""
    from fractal_wallpapers.models import palette_corpus

    if not palette_corpus.row_dir().is_dir():
        pytest.skip("the distillation corpus has not been built")
    return palette_corpus.read()


@pytest.fixture(scope="session")
def tracked_ledger():
    """The candidate ledger and its score sidecar, read **once** for the session.

    The dearest reading in this repository by a wide margin, and until this
    existed the slow lane paid for it eight times: four module fixtures derived
    the same pool independently, and three more guards read the rows again to
    census them. On this machine, 2026-08-29, one reading is 21.9 s for the rows,
    4.2 s for the sidecar and 13.4 s to lay the pool out over them — so the four
    duplicated derivations alone were 138 s of a 1,088 s lane.

    Why the whole file rather than the six fields the censuses read: a projection
    is a second opinion about which fields a row has, and a guard handed a
    thinned row would go on passing after the field it stopped being given
    started mattering. The cost is that the session holds about 6 GB while it
    runs. That is a reading of *this machine's* tree and nowhere else's — the
    ledger lives under `artifacts/`, so every machine without it, CI included,
    skips these guards rather than paying anything.

    The hot root is unset while the pool is laid out, deliberately. `solve.pool`
    asks whether each row's picture is still on disk, and a module that has
    redirected the root at its own `tmp_path` would otherwise have this read the
    empty tree and report every picture missing. Higher-scoped fixtures are built
    before lower-scoped ones, so this is belt and braces — but the belt is what
    makes the reading independent of which file happened to ask for it first.
    """
    from fractal_wallpapers import paths
    from fractal_wallpapers.curation import candidate_ledger, headroom

    if not candidate_ledger.rows_path().is_file():
        pytest.skip("the candidate ledger has not been backfilled on this machine")

    def quiet(*_args, **_flags) -> None:
        """The census logs a line a mode; a fixture is not a place for it."""

    with pytest.MonkeyPatch.context() as patched:
        patched.delenv(paths.HOT_ROOT_VARIABLE, raising=False)
        rows = candidate_ledger.read()
        scores = candidate_ledger.read_scores()
        pool, costs, refused = headroom.population(rows=rows, scores=scores, log=quiet)
    return SimpleNamespace(rows=rows, scores=scores, pool=pool, costs=costs, refused=refused)
