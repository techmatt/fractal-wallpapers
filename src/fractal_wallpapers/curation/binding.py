"""Which ledgers a curation is bound to, decided once and never guessed.

Curation reads walk ledgers. Which ones is a *decision*, and it used to be a
default: an invocation that named no ledger read every `walk.jsonl` under
`artifacts/`. That is the wrong default in the one way a default can be wrong —
it is silent, it is plausible, and it is expensive. A run started to release
`harvest_run3`'s supply would have pulled an earlier harvest's 17,251 unscored
rows into the same intake, ranked them together, and reported one funnel over two
populations. Nothing would have looked broken.

So there is no default. A binding is **declared** — by naming ledgers, or by
naming the harvest run that fed this one — and everything downstream (`score`,
the intake inside a run, and therefore the selection over it) reads that binding
rather than asking the filesystem again. `curate run` writes it into its own plan
at the run's entry, alongside `n` and the seed, because it is the same kind of
fact: it decides *what the run makes*, and a resume that re-derived it could
continue a run against a different supply.

The one thing resolution will do without being told is take the only ledger there
is. Choosing between one candidate and nothing is not a guess. Choosing between
eight is, and [`resolve`] refuses and lists them instead — an unbound invocation
in a repository with two harvests in it stops, with the names of both on screen,
before it has read a row.
"""

from __future__ import annotations

from pathlib import Path

from fractal_wallpapers.paths import rehome, repo_root, tracked_name
from fractal_wallpapers.supply import ledgers


class Unbound(RuntimeError):
    """No ledger binding, and more than one ledger the invocation could mean."""


def label(path: Path) -> str:
    """A ledger's name as a record carries it: repository-relative where it can be.

    [`fractal_wallpapers.paths.tracked_name`], not a private copy of it. The same
    spelling [`fractal_wallpapers.supply.ledgers.admitted_union`] stamps onto
    every row it returns, so a binding and the rows it produced name their
    ledgers identically and the join is a string comparison — and that promise
    only survives while there is one function making the spelling. A ledger under
    the artifacts tree is therefore named `artifacts/<rest>` on whichever disk the
    tree lives on, which is what lets a run planned before the tree moved be
    resumed after it.
    """
    return tracked_name(path)


def anchored(path) -> Path:
    """A declared path resolved against the repository, never against the shell's cwd.

    The same rule the command line's `--out` follows, and the reason a binding can
    be *recorded* as a repository-relative label and read back by a resume that
    started in another directory — including one recorded as `artifacts/...`,
    which resolves against the artifacts root rather than the checkout.
    """
    path = Path(path)
    if path.is_absolute():
        return path
    return rehome(path) or repo_root() / path


def of_harvest(directory) -> Path:
    """The ledger a harvest run wrote — the inheritance the run name implies.

    A curation is nearly always releasing the supply of one harvest, and the
    harvest's output directory is the thing the operator already has in hand.
    Naming it beats copying a path to a `walk.jsonl` out of it.
    """
    directory = anchored(directory)
    path = directory / ledgers.LEDGER_NAME
    if not path.is_file():
        raise Unbound(
            f"{directory} holds no {ledgers.LEDGER_NAME}, so it is not a harvest run this "
            f"curation could inherit a ledger from. Point --harvest at the harvest's own "
            f"--out-dir, or name the ledger with --ledger."
        )
    return path


def resolve(declared=None, harvests=None, root: Path | None = None) -> list[Path]:
    """The bound ledgers, as an explicit list. Refuses rather than guessing.

    `declared` names ledger files, `harvests` names harvest run directories; both
    are repeatable and they compose. With neither, the binding is the only ledger
    under `root` if there is exactly one, and a refusal listing every candidate if
    there is more than one.
    """
    chosen = [anchored(p) for p in (declared or [])] + [of_harvest(d) for d in (harvests or [])]
    if chosen:
        return _checked(_deduplicated(chosen))

    found = ledgers.ledger_paths(root)
    if not found:
        where = ledgers.ledger_root() if root is None else Path(root)
        raise Unbound(
            f"no walk ledger under {where}, so there is no supply to curate. Run "
            f"`fractal-wallpapers harvest` first."
        )
    if len(found) == 1:
        return found
    listing = "\n".join(f"  --ledger {label(path)}" for path in found)
    raise Unbound(
        f"{len(found)} walk ledgers are present and this invocation is bound to none of "
        f"them. Reading all of them would rank one harvest's supply against another's and "
        f"report one funnel over both, so nothing is assumed:\n{listing}\n"
        f"Name the ones this curation is for, or name the harvest that fed it with "
        f"--harvest <its out-dir>."
    )


def _deduplicated(paths) -> list[Path]:
    """The same list, with a ledger named twice kept once and in the order given.

    Two spellings of one file is how a union double-counts a population, and
    `--harvest x --ledger x/walk.jsonl` is an easy way to write two.
    """
    out: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        try:
            identity = path.resolve()
        except OSError:  # a path that cannot be resolved is refused a line later
            identity = path
        if identity in seen:
            continue
        seen.add(identity)
        out.append(path)
    return out


def _checked(paths: list[Path]) -> list[Path]:
    """Every declared ledger, or a refusal naming the first one that is not there."""
    for path in paths:
        if not path.is_file():
            raise Unbound(
                f"{path} is not a walk ledger this curation can read. A binding names files "
                f"that exist: a typo here would silently narrow the supply a run releases."
            )
    return paths


__all__ = ["Unbound", "anchored", "label", "of_harvest", "resolve"]
