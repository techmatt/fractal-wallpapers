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
# The tracked records, held still for the length of a session.
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

#: The tracked files a **runtime writer** appends to that are not manifests, named
#: one by one because there is no suffix to sweep for. `ratchet.jsonl` is written
#: by `sweep.prune` at the end of every merge and resolves off `repo_root()`, so
#: it is in exactly the class this guard was built for: a path a fixture that
#: redirects at the tier roots looks complete without having moved.
HELD_STILL = ("data/curation/candidate_ledger/ratchet.jsonl",)

#: The **regenerable** tree's half of the same question, and the reason this guard
#: is not about tracked files any more. Every path above resolves off
#: `repo_root()`; these resolve off a tier, so a fixture *can* move them — and the
#: class of miss is a fixture that moves one tier and not the other. That is what
#: `records.use(tmp_path)` does: the decision rows go to a temporary store and the
#: run's release sheet, written through `run_layout.run_dir()`, does not. Two test
#: files leaked whole run directories onto this machine's live tree that way,
#: `runs/r` and `runs/earlier`, until 2026-09-07; a leg that nothing ran is then a
#: leg every inventory and the orphan sweep have to have an answer for.
#:
#: A **name at a fixed depth**, never a walk: this is the tree `CLAUDE.md` says a
#: recursive grep takes tens of minutes over. One `scandir` of about fifteen
#: entries, twice a session.
LIVE_LEG_DIRS = (("curation", "runs"),)

RECORDS_AT_START = pytest.StashKey[dict]()
LEGS_AT_START = pytest.StashKey[dict]()


def tracked_records() -> dict:
    """`{repo-relative name: sha256}` for every tracked record this run must not move.

    Every `*.manifest.json`, discovered rather than listed so that a durable added
    tomorrow is covered without anybody remembering, plus [`HELD_STILL`].

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
        if not name.endswith(MANIFEST_SUFFIX) and name not in HELD_STILL:
            continue
        path = repo_root() / name
        if path.is_file():
            found[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


def live_legs() -> dict:
    """`{tracked name: [entry names]}` for each of [`LIVE_LEG_DIRS`] on the live tree.

    Off `hot_root()` rather than `paths.under`, and asked only in the two session
    hooks — where no test is running, so no `monkeypatch` is standing and the root
    is this machine's own. `under` would resolve the subtree's tier, which is a
    question about where the bulk lives; this one is about where a write lands.
    """
    from fractal_wallpapers import paths

    try:
        root = paths.hot_root()
    except paths.StorageRefusal:
        return {}
    found = {}
    for parts in LIVE_LEG_DIRS:
        where = root.joinpath(*parts)
        if where.is_dir():
            found["/".join((paths.ARTIFACTS_NAME, *parts))] = sorted(
                entry.name for entry in where.iterdir()
            )
    return found


def pytest_sessionstart(session) -> None:
    session.config.stash[RECORDS_AT_START] = tracked_records()
    session.config.stash[LEGS_AT_START] = live_legs()


def pytest_sessionfinish(session, exitstatus) -> None:
    """Fail the session over a live record or a live leg this run wrote, and name it.

    A **backstop**, not a substitute for redirecting properly. It answers one
    question — *did a test write to this machine's real tree* — and it asks it on
    both tiers, because the class of miss is the same on each: a fixture that
    redirects one store's live files and leaves a second path resolving somewhere
    it never looked.

    On the **tracked** tier that path resolves off `repo_root()`, so there is no
    root to redirect it at — `repo_root` is imported by value into three dozen
    modules. A durable's manifest is the shape, and [`HELD_STILL`]'s ratchet log
    joined it on 2026-09-07 when `prune` gained a tracked writer.

    On the **regenerable** tier the path does follow a root; what goes wrong is
    that a fixture moves the other one. `records.use(tmp_path)` sends the decision
    rows to a temporary store and leaves the run's release sheet going through
    `run_layout.run_dir()` to the live artifacts tree — which is how
    `artifacts/curation/runs/{r,earlier}` came to be two whole legs nothing ever
    ran, found on 2026-09-07 by an audit of what the orphan sweep was looking at.
    [`LIVE_LEG_DIRS`] is that half.

    **One mechanism and two snapshots**, deliberately: a second hook reporting the
    same class of fault through a second writer is the thing that goes quiet when
    somebody moves one of them.

    It names what moved and how to put it back, because a manifest written out of
    a `tmp_path` store is a wrong count in the history that the next
    `durability.check` believes, a ratchet row written out of one is a census of
    three synthetic rows in a guard's high-water mark, and a leg written out of
    one is work the sweeps then have to have an answer for.

    A hook rather than a session-scoped fixture, so that it brackets collection
    too; and reported straight to the terminal reporter rather than through
    `pytest_terminal_summary`, so it does not depend on which of the two pytest
    runs first.
    """
    before = session.config.stash.get(RECORDS_AT_START, None)
    if not before:
        return
    after = tracked_records()
    moved = sorted(name for name in set(before) | set(after) if before.get(name) != after.get(name))
    grew = _legs_that_appeared(session.config.stash.get(LEGS_AT_START, None) or {})
    if not moved and not grew:
        return
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_sep("=", "THIS RUN WROTE TO THE LIVE TREE", red=True, bold=True)
        for name in moved:
            reporter.write_line(f"  {name}")
        for name in grew:
            reporter.write_line(f"  {name}  (a leg that did not exist when the run started)")
        reporter.write_line("")
        if moved:
            reporter.write_line(
                "A test wrote a tracked record instead of a redirected one, so the history now "
                "records a count that came out of a temporary store. Put them back with "
                f"`git checkout -- {' '.join(moved)}`, then find the fixture: it is redirecting "
                "a store's live files without redirecting the one path that resolves off "
                "`repo_root()` rather than off a tier — a durable's manifest, or the ratchet log."
            )
        if grew:
            reporter.write_line(
                "A test wrote a run directory onto the regenerable tree. Delete it, then find "
                "the fixture: it redirected the tracked tier — `records.use(tmp_path)` — and "
                "left something writing through `run_layout.run_dir()` to the artifacts tier. "
                "Redirect both, at the roots, the way `tests/test_release_bar.py` does."
            )
    session.exitstatus = pytest.ExitCode.TESTS_FAILED


def _legs_that_appeared(before: dict) -> list[str]:
    """`<tracked name>/<entry>` for every leg the live tree gained during this run."""
    after = live_legs()
    return sorted(
        f"{where}/{name}"
        for where, names in after.items()
        for name in set(names) - set(before.get(where, ()))
    )


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


@pytest.fixture(scope="session")
def tracked_ratchet_log():
    """Where the **real** ratchet log is, resolved before anything redirects it.

    Session-scoped and depended on by the autouse redirect below, which is what
    guarantees the order: pytest builds this before the first function-scoped
    fixture body runs, so it reads `log_path` while it is still the shipped one.
    The two guards that mean to read the tracked log take this and pass it in,
    rather than un-patching — an explicit path is one binding, and un-patching is
    two.
    """
    from fractal_wallpapers.curation.candidate_ledger import ratchet

    return ratchet.log_path()


@pytest.fixture(scope="session")
def _absent_ratchet_root(tmp_path_factory):
    """One directory to hang every test's redirected ratchet log off."""
    return tmp_path_factory.mktemp("no_tracked_ratchet")


@pytest.fixture(autouse=True)
def no_tracked_ratchet(monkeypatch, tracked_ratchet_log, _absent_ratchet_root):
    """No test appends to the **tracked** ratchet log. Every test, always.

    [`candidate_ledger.ratchet`]'s log resolves off `repo_root()` and not off a
    tier, so it is in the class of path a fixture that redirects the store at the
    tier roots does not move — the same class as `manifest_dir`, and the same
    class as the defect that put a temporary ledger's counts into two tracked
    manifests. Any test that prunes writes a mark and a deletion, and a store of
    three synthetic rows would otherwise append *its* census to the history.

    Autouse rather than per file for the reason the sidecar above is: the hazard
    belongs to `prune`, not to the tests that happen to call it today, and a
    redirect written per call site is complete only against the call graph on the
    day somebody wrote it. Pointing it at a path that does not exist is the whole
    fixture — an absent log reads as no mark, which is a state [`ratchet.reading`]
    is defined on.

    The failure it leaves behind if a guard forgets to opt out is **loud**: the
    census asserts every counter is marked, and an empty log marks none of them.
    `pytest_sessionfinish` is the backstop under that, and it is a backstop and
    not the mechanism.
    """
    from fractal_wallpapers.curation.candidate_ledger import ratchet

    nowhere = _absent_ratchet_root / f"{next(_TMP_SERIAL)}_{ratchet.LOG_NAME}"
    assert nowhere != tracked_ratchet_log
    monkeypatch.setattr(ratchet, "log_path", lambda: nowhere)


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
def _pool_scores_once() -> dict:
    """The fine-tier head's read of the seating pool, read **once** for the session.

    9.2 MiB and 42,300 rows on this machine, 0.21 s to parse. That was paid once a
    pass and nobody noticed until `distinct.preselect` started resolving the column
    itself on 2026-09-09 — the fold picks its survivor on `p_fine` now, and it runs
    on passes where nothing upstream has read it, so it has to. Every synthetic
    `headroom.census` and `solve.solve` in this suite then paid the read again, and
    the fast lane went 124.06 s to 129.13 s over six added guards.
    """
    from fractal_wallpapers.models import gallery_grade_train

    return gallery_grade_train.read_pool_scores()


@pytest.fixture(autouse=True)
def the_pool_scores_are_read_once(monkeypatch, _pool_scores_once):
    """`read_pool_scores()` hands back that one reading rather than re-parsing it.

    **The real store's contents and not a stub**, so a guard sees what the machine
    holds exactly as it did before — this is the `tracked_ledger` arrangement at a
    smaller scale, and for the same reason. A call that names a `path` is left
    alone and reads that file, because a test writing its own column is asking
    about that file and not about this machine's.

    A module or a test that patches the same name later wins, which is what
    `test_solve.py`'s own column and `test_distinct.py`'s fine-key guards rely on:
    an autouse fixture in `conftest` is built before either.
    """
    from fractal_wallpapers.models import gallery_grade_train

    real = gallery_grade_train.read_pool_scores

    def read(path=None):
        return _pool_scores_once if path is None else real(path)

    monkeypatch.setattr(gallery_grade_train, "read_pool_scores", read)


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
