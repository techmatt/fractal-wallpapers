"""The ratio table: complete in both directions, and never zero.

The table is data, so the interesting tests are about the guard around it rather
than about the numbers in it — a shipped table that disagrees with the partition
registry is the failure this layer exists to refuse.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.supply import release_mix
from fractal_wallpapers.supply.partitions import ALL_PARTITIONS, CLASSIC_PHOENIX


def test_the_shipped_table_covers_the_registry_exactly() -> None:
    assert set(release_mix.ratios()) == set(ALL_PARTITIONS)


def test_a_registered_partition_with_no_ratio_is_a_red_build() -> None:
    """A defaulted ratio would give a partition a plausible target nobody decided,
    and every read downstream would be about the default."""
    entries = release_mix.entries()
    entries.pop("phoenix")
    with pytest.raises(release_mix.ReleaseMixError, match="registered with no ratio"):
        release_mix.check_complete(entries)


def test_a_ratio_for_an_unregistered_partition_is_a_red_build() -> None:
    """A partition somebody retired without retiring its share of the release
    leaves every remaining ratio quietly meaning less than it says."""
    entries = release_mix.entries()
    entries["multibrot9"] = {"ratio": 1.0}
    with pytest.raises(release_mix.ReleaseMixError, match="unregistered partition"):
        release_mix.check_complete(entries)


def test_a_zero_ratio_is_refused_rather_than_treated_as_a_retirement() -> None:
    """Zeroing leaves a partition registered, floored, censused and permanently
    starved — the report about it afterwards describes a decision nobody made."""
    entries = release_mix.entries()
    entries["phoenix"] = {"ratio": 0.0}
    with pytest.raises(release_mix.ReleaseMixError, match="RETIRED"):
        release_mix.check_complete(entries)


def test_externally_supplied_is_a_flag_and_not_a_zero_ratio() -> None:
    """Classic phoenix is still that much of a release. What it loses is the
    clock, not its share of the intent — so the zero-ratio refusal applies to it
    exactly as to everything else."""
    assert release_mix.is_externally_supplied(CLASSIC_PHOENIX)
    assert release_mix.ratio_of(CLASSIC_PHOENIX) == pytest.approx(0.2)
    assert release_mix.externally_supplied() == {CLASSIC_PHOENIX}

    entries = release_mix.entries()
    entries[CLASSIC_PHOENIX] = {"ratio": 0.0, "externally_supplied": True}
    with pytest.raises(release_mix.ReleaseMixError):
        release_mix.check_complete(entries)


def test_the_two_degree_two_planes_carry_the_release() -> None:
    """The one policy statement the table makes, asserted as a shape rather than
    as nine literals — a test that restates the file cannot fail usefully."""
    ratios = release_mix.ratios()
    top = max(ratios.values())
    assert {p for p, v in ratios.items() if v == top} == {"mandelbrot", "julia:mandelbrot"}
    assert ratios[CLASSIC_PHOENIX] < min(v for p, v in ratios.items() if p != CLASSIC_PHOENIX)


def test_shares_are_derived_and_sum_to_one() -> None:
    """A stored share table is wrong from the moment a partition is registered or
    retired, and the arithmetic is one line."""
    shares = release_mix.shares()
    assert sum(shares.values()) == pytest.approx(1.0)
    assert shares["mandelbrot"] == pytest.approx(3.0 / sum(release_mix.ratios().values()))


def test_the_table_is_a_copy_so_a_consumer_cannot_edit_the_policy() -> None:
    """A consumer that normalizes in place must not edit the policy for everyone
    else in the process."""
    first = release_mix.ratios()
    first["mandelbrot"] = 99.0
    assert release_mix.ratios()["mandelbrot"] == 3.0


def test_an_unknown_schema_is_refused(tmp_path) -> None:
    path = tmp_path / "release_mix.json"
    path.write_text(json.dumps({"schema": 99, "partitions": {}}), encoding="utf-8")
    with pytest.raises(release_mix.ReleaseMixError, match="schema"):
        release_mix.entries(path)
