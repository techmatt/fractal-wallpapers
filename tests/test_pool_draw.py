"""What the uniform pool draw writes down about itself.

The draw is a pool-holding leg — the ledger, the score sidecar and the rank key's
two stores — so the three collaborators that touch a store are stood in for here
and what is under test is the record `draw` assembles from them. The store-facing
halves have their own tests: [`test_headroom`] for the population and the bars,
and [`test_solve`] for the order.
"""

from __future__ import annotations

import json

from tests.test_headroom import candidate

from fractal_wallpapers.curation import pool_draw, solve


def quiet(*_args, **_rest) -> None:
    return None


def staged(monkeypatch, coverage: dict | None, *, count: int = 6):
    """A draw over `count` synthetic places whose order resolved to `coverage`."""
    clearing = [candidate(f"c{at}") for at in range(count)]
    table = {"on_default": count, "on_fallback": 0, "default": 0.5, "fallback": 0.5}
    order = {row.key: 0.5 for row in clearing}
    monkeypatch.setattr(pool_draw, "clearing_population", lambda log=print: (clearing, table, {}))
    monkeypatch.setattr(
        pool_draw,
        "seat_ranked",
        lambda rows, log=print: ({r.location: r for r in rows}, order, coverage),
    )
    # The one remaining store: `units_for` joins each drawn key to its ledger row.
    monkeypatch.setattr(
        pool_draw,
        "units_for",
        lambda drawn, best, held: [{"key": best[place].key} for place in drawn],
    )


def test_the_draw_records_the_key_it_drew_under(monkeypatch, tmp_path):
    """A cascade draw and a rank-key draw disagree about which picture represents
    a place for most of this pool, so "the row a seating pass would reach first"
    is not one row — it is one row *per key*. A sheet whose record does not name
    the order is a sheet nobody can attribute later, and the record's own field is
    called `rank_key` for the 2026-08 reason that it was the only fitted key
    there was.

    Both spellings land: `key` plainly at the root, and the coverage block whole
    beneath the older name.
    """
    coverage = {"key": solve.CASCADE_KEY, "ranked": 6, "unranked": 0, "cascade": {"lifted": 4}}
    staged(monkeypatch, coverage)
    record = pool_draw.draw(3, seed=1, directory=tmp_path, log=quiet)
    assert record["key"] == solve.CASCADE_KEY
    assert record["rank_key"] == coverage, "the coverage block whole, and not just its name"

    written = json.loads((tmp_path / pool_draw.RECORD_NAME).read_text(encoding="utf-8"))
    assert written["key"] == solve.CASCADE_KEY, "on disk and not only in the return value"


def test_a_draw_under_the_incumbent_key_says_so_and_one_with_no_coverage_falls_back(
    monkeypatch, tmp_path
):
    """The field is read off the coverage the resolver wrote, so it moves with the
    key rather than restating a constant. With no coverage at all the leg's own
    default is all there is to say, which is the honest answer and not a guess."""
    staged(monkeypatch, {"key": "rank_key", "ranked": 6, "unranked": 0})
    assert pool_draw.draw(3, seed=1, directory=tmp_path, log=quiet)["key"] == "rank_key"

    staged(monkeypatch, None)
    bare = pool_draw.draw(3, seed=1, directory=tmp_path / "bare", log=quiet)
    assert bare["key"] == solve.DEFAULT_KEY == solve.CASCADE_KEY
    assert bare["rank_key"] is None
