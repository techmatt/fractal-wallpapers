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
import hashlib
import itertools
import re
import subprocess
from types import SimpleNamespace

import pytest

from fractal_wallpapers.labeling import registry as registry_module
from fractal_wallpapers.labeling import store
from fractal_wallpapers.paths import repo_root

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


#: Every module that skipped WHOLE at collection, `{nodeid: the import it wanted}`.
#:
#: A module-level `pytest.importorskip` does not skip its tests — it stops the
#: module being collected at all, so its tests are absent from the collected total
#: rather than counted and skipped. Eight modules gate on `torch` that way and five
#: more on `PIL`, all of them extras `pip install -e .[dev]` does not buy, and the
#: whole block leaves a single "skipped" apiece behind it.
#:
#: **That is how a lane reading gets written down that nothing can reproduce.** The
#: 3,383 in `tests/README.md`'s log was this: an interpreter with no `torch`, 65
#: fast tests and 5 slow ones short of the same tree on a full install, and nothing
#: on screen said so. Same argument as the deselect line below — a guard that goes
#: quiet is a guard nobody notices going missing.
SKIPPED_WHOLE: dict[str, str] = {}

#: What `importorskip` says when the module is not there, as pytest spells it.
WANTED = re.compile(r"could not import [\x27\"]([^\x27\"]+)[\x27\"]")


def pytest_collectreport(report) -> None:
    """Remember a module that skipped before it could be collected."""
    if report.outcome != "skipped" or not report.nodeid.endswith(".py"):
        return
    reason = str(report.longrepr[2] if isinstance(report.longrepr, tuple) else report.longrepr)
    found = WANTED.search(reason)
    SKIPPED_WHOLE[report.nodeid] = found.group(1) if found else reason


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    held = config.stash.get(HELD_BACK, 0)
    if held:
        tests = "test" if held == 1 else "tests"
        terminalreporter.write_sep(
            "=",
            f"{held} slow {tests} not run - `python -m pytest --slow` runs everything",
            yellow=True,
            bold=True,
        )
    if not SKIPPED_WHOLE:
        return
    modules = "module" if len(SKIPPED_WHOLE) == 1 else "modules"
    missing = ", ".join(sorted(set(SKIPPED_WHOLE.values())))
    terminalreporter.write_sep(
        "=",
        f"{len(SKIPPED_WHOLE)} test {modules} NOT COLLECTED - no {missing}. The count "
        f"above is short and is not comparable to a `.[dev,models]` install",
        red=True,
        bold=True,
    )


# --------------------------------------------------------------------------- #
# The tracked manifests, held still for the length of a session.
# --------------------------------------------------------------------------- #
#: The suffix every tracked manifest's name ends in. `durability.save` writes one
#: on every save, and *which* one it writes is decided by a `Durable` the caller
#: assembled out of accessors — so a fixture that redirects a durable's live file
#: and its copy but not its manifest writes `tmp_path` counts into the history,
#: and nothing says so.
#:
#: **That is not hypothetical.** During the candidate-ledger split an intermediate
#: `__init__` re-exported `manifest_dir` eagerly, which made two bindings of one
#: function; the redirect moved the store's and left `flatness.durable()` on the
#: real tree, and `data/curation/candidate_ledger/{flatness,signatures}` were
#: overwritten with one-row counts off a temporary ledger. A person noticed.
#:
#: Discovered through `git ls-files` rather than listed, because a hand list goes
#: stale the first time a durable is added. **20 files, 104 KB** as of 2026-09-04;
#: hashing them twice a session does not show up against a three-minute lane.
MANIFEST_SUFFIX = "manifest.json"

MANIFESTS_AT_START = pytest.StashKey[dict]()


def tracked_manifests() -> dict:
    """`{repo-relative name: sha256}` for every tracked manifest, right now.

    `git ls-files` and not a walk, for the reason `CLAUDE.md` gives: this checkout
    carries a hundred gigabytes of untracked `artifacts/` and a recursive walk of
    it takes minutes. The index answers in milliseconds.
    """
    listing = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    if listing.returncode != 0:
        return {}
    found = {}
    # `chr(0)` rather than an escape: this is the separator `-z` writes, and a
    # literal one in the source is a null byte in a tracked text file.
    for name in listing.stdout.split(chr(0)):
        if not name.endswith(MANIFEST_SUFFIX):
            continue
        path = repo_root() / name
        if path.is_file():
            found[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


def pytest_sessionstart(session) -> None:
    session.config.stash[MANIFESTS_AT_START] = tracked_manifests()


def pytest_sessionfinish(session, exitstatus) -> None:
    """Fail the session over a tracked manifest this run rewrote, and name it.

    A **backstop**, not a substitute for redirecting properly. The fixtures that
    exercise a durable redirect at the tier roots, which is where the live file
    and the copy resolve from; a manifest resolves off `repo_root()` instead and
    there is no root to redirect it at, because `repo_root` is imported by value
    into three dozen modules. So the manifest is the one path a fixture can miss
    while looking complete, and this catches the one it missed.

    It names the file and the command that puts it back, because a manifest
    written out of a `tmp_path` store is a wrong count in the history and the next
    `durability.check` believes it.

    A hook rather than a session-scoped fixture, so that it brackets collection
    too; and reported straight to the terminal reporter rather than through
    `pytest_terminal_summary`, so it does not depend on which of the two pytest
    runs first.
    """
    before = session.config.stash.get(MANIFESTS_AT_START, None)
    if not before:
        return
    after = tracked_manifests()
    moved = sorted(name for name in set(before) | set(after) if before.get(name) != after.get(name))
    if not moved:
        return
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_sep("=", "TRACKED MANIFESTS REWRITTEN BY THIS RUN", red=True, bold=True)
        for name in moved:
            reporter.write_line(f"  {name}")
        reporter.write_line("")
        reporter.write_line(
            "A test wrote a tracked manifest instead of a redirected one, so the history now "
            "records a count that came out of a temporary store. Put them back with "
            f"`git checkout -- {' '.join(moved)}`, then find the fixture: it is redirecting a "
            "durable's live file and its copy without redirecting its manifest."
        )
    session.exitstatus = pytest.ExitCode.TESTS_FAILED


# --------------------------------------------------------------------------- #
# Temporary directories, numbered by a counter rather than by a listing.
# --------------------------------------------------------------------------- #
#: The serial every temporary name in this file is numbered off.
#:
#: `tmp_path_factory.mktemp` is `numbered=True`, and pytest numbers a new
#: directory by **iterating the whole basetemp** for the highest suffix already
#: there. One call per test is therefore quadratic in the test count: basetemp
#: grows an entry per test and every later call reads all of them. It is the one
#: cost in this suite that scales with the number of tests rather than with a
#: store, which is why every reading in [`tests/README.md`]'s log was blind to it
#: — it grew with the lane instead of stepping when something landed.
#:
#: Measured on this machine over a synthetic 3,500-test run, every test also
#: taking `tmp_path`, fresh basetemp each time: **43.27 s** with `mktemp` per
#: test, **15.12 s** with the sidecar's path taken off a session directory, and
#: **5.38 s** with that plus the `tmp_path` override below. The scaling is the
#: proof it is the scan: 2,000 trivial tests cost 5.4 s of it and 4,000 cost
#: 19.7 s — twice the tests, 3.6x the price.
#:
#: No coverage is traded for any of this. The directories are the same
#: directories; they are counted rather than searched for.
_TMP_SERIAL = itertools.count()


@pytest.fixture
def tmp_path(request, tmp_path_factory):
    """`tmp_path`, with pytest's directory listing replaced by [`_TMP_SERIAL`].

    An override of pytest's own fixture, which is supported and is the only
    place this is fixable once — the alternative is rewriting the sixteen
    hundred sites that ask for it. The directory is still named after the test
    that asked, so a temporary kept after a failure is still readable; what goes
    is the `iterdir()` of a basetemp that ends a run holding thousands of
    entries.
    """
    stem = re.sub(r"[^A-Za-z0-9_-]", "_", request.node.name)[:30]
    directory = tmp_path_factory.getbasetemp() / f"{stem}_{next(_TMP_SERIAL)}"
    directory.mkdir()
    return directory


@pytest.fixture(scope="session")
def _absent_sidecar_root(tmp_path_factory):
    """One directory to hang every test's absent sidecar off. See [`_TMP_SERIAL`]."""
    return tmp_path_factory.mktemp("no_signature_sidecar")


@pytest.fixture(autouse=True)
def no_signature_sidecar(monkeypatch, _absent_sidecar_root):
    """No test reads the **real** bound-signature sidecar. Every test, always.

    [`curation.signatures`]' store is ~247 MB and [`solve.solve`] consults it on
    every pass, so a unit test seating three synthetic candidates would otherwise
    read a quarter of a gibibyte off disk to answer for keys it has never heard of.
    Measured when this was missing: `test_view.py` plus `test_solve.py` went from
    5.9 s to 35.8 s, which is a store being priced by the lane rather than code.

    Autouse and in `conftest` rather than per file, because the hazard is not a
    property of the tests that happen to call the gallery leg today. Pointing it at
    a path that does not exist is the whole fixture: an absent sidecar reads empty
    by design, which is the ordinary state of a fresh checkout.

    `test_signatures.py` overrides this with its own tmp store — a file's fixture
    runs after this one, so its `monkeypatch.setattr` is the one that stands.

    **A serial name in one session directory, not a directory apiece.** What this
    owes each test is a private path that does not exist, and a directory was
    never part of that — it was only how `mktemp` spelled *unique*, at the price
    [`_TMP_SERIAL`] measures. The parent here exists, so a `signatures.write`
    through the patch still lands somewhere private and still succeeds, which is
    exactly what happened before. Nothing in the suite does: the three files that
    write a sidecar — `test_signatures`, [`test_ledger_tracking`] and
    [`test_candidate_ledger`] — each replace this patch with their own store
    first. The uniqueness stays anyway, because it costs a counter.
    """
    from fractal_wallpapers.curation import signatures

    nowhere = _absent_sidecar_root / f"{next(_TMP_SERIAL)}_{signatures.SIDECAR_NAME}"
    monkeypatch.setattr(signatures, "sidecar_path", lambda: nowhere)


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
def shipped_label_pool():
    """`render_folds.pool()` and the deal over it, derived **once** for the session.

    The same argument as [`shipped_render_cache`] one module up. Laying this out
    sweeps every scored row of both finished stores, digests a recipe per row and
    asks the render cache for its picture, and until this existed the slow lane
    paid for it eight times: the deleted `test_render_cv` twice — once directly
    and once inside `assignment`, which calls `pool` itself — `test_render_deploy`
    four times, once in its module fixture and once per seed in the three-seed
    guard, and `test_render_dose` and `test_render_grade` once each. On this
    machine, 2026-08-31, that was 52.4 s of a 563 s lane.

    **The pictures are handed out fresh on every call, and that is the whole
    reason this is a factory rather than a value.** `render_deploy.sides_for`
    assigns `picture.side` **in place**, so one shared list would carry whichever
    file ran last into whichever ran next — a cross-file coupling that reads as a
    split rule breaking. A `dataclasses.replace` per row restores exactly the
    independence a second `pool()` call used to buy, at about ten milliseconds
    against four seconds.

    The rows and the record are shared as they are: nothing here writes to them,
    and `groups.assign` only reads. A test that needs to move one takes a copy,
    which is this file's standing rule.
    """
    import dataclasses
    from unittest import mock

    from fractal_wallpapers.models import render_folds

    derived: list = []

    def pool():
        if not derived:
            derived.append(render_folds.pool())
        rows, pictures, record = derived[0]
        return rows, [dataclasses.replace(picture) for picture in pictures], record

    @functools.cache
    def assignment(*args, **flags):
        """The real `assignment`, with the shared pool bound under it.

        Patched rather than reimplemented, for [`shipped_render_cache`]'s reason:
        a fixture that dealt the folds itself would be a second opinion about the
        deal, which is the question that function exists to own.
        """
        with mock.patch.object(render_folds, "pool", pool):
            return render_folds.assignment(*args, **flags)

    return SimpleNamespace(pool=pool, assignment=assignment)


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
