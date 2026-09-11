"""The groups table: what it says, and that the metric still says it.

Regenerating the whole table is three and a half minutes of sliced Wasserstein
over nine hundred maps, which is not a unit test. So the file is pinned here by
its *result* — the numbers Matt ruled on, and the merges he named — and the
metric behind it is checked on one pair at a time, where a two-map distance is
exactly the number the record already carries.

The ruling being pinned: **65 groups over 143 of 901 maps, largest 6**, at cut
0.039735. Anything that moves those numbers has changed what a group means, and
the change belongs in front of a person rather than in a diff.
"""

from __future__ import annotations

import pytest
from tests.test_headroom import candidate

from fractal_wallpapers.palettes import groups, variants
from fractal_wallpapers.paths import colormap_dir

#: The three maps a pass over gallery3's seats found sharing twelve of them, and
#: which this metric holds apart. Named because "the trio does not group" is the
#: single most surprising thing the table says.
APART = ("wallhaven_wallhaven-1joljg", "Furnace Rose", "Gilt and Rose")


def header() -> dict:
    rows = groups.read()
    assert rows, f"{groups.record_path()} is missing"
    return rows[0]


def test_the_ruling_the_table_is_pinned_to() -> None:
    """The four numbers Matt approved on a sheet, by eye, merge by merge."""
    head = header()
    assert head["kind"] == groups.METHOD_ROW
    assert head["cut"] == groups.CUT == 0.039735
    assert head["maps"] == 901
    assert head["groups"] == 65
    assert head["grouped"] == 143
    assert head["largest"] == 6
    assert head["singletons"] == 901 - 143


def test_the_table_holds_together_as_a_partition_of_what_it_names() -> None:
    """No map in two groups, every group at least a pair, every member a map the
    library actually holds. A group naming a map that is not there would collapse
    a pool slot onto nothing."""
    head = header()
    rows = groups.groups()
    assert len(rows) == head["groups"]
    assert [row["group"] for row in rows] == [f"m{n:02d}" for n in range(1, len(rows) + 1)]

    library = set(groups.library())
    seen: list[str] = []
    for row in rows:
        assert row["size"] == len(row["members"]) >= 2
        assert set(row["members"]) <= library
        assert row["canonical"] in row["members"]
        assert row["mean_m1"] <= row["max_m1"] <= head["cut"] or row["size"] > 2
        seen.extend(row["members"])
    assert len(seen) == len(set(seen)) == head["grouped"]


def test_the_merges_the_sheet_was_marked_on() -> None:
    """Two pairs Matt marked SAME, and they have to land in one group each."""
    home = {name: row["group"] for row in groups.groups() for name in row["members"]}
    assert home["cet_linear_kry_0_97_c73"] == home["cet_linear_kryw_0_100_c71"]
    assert home["cet_linear_bmw_5_95_c86"] == home["cet_linear_bmw_5_95_c89"]


def test_the_trio_that_does_not_group() -> None:
    """Three maps an earlier pass had sharing twelve gallery3 seats. Under this
    metric and this cut they are three singletons — the nearest pair of them is at
    0.0539, well above the cut — and a table that quietly merged them would be
    reinstating a grouping the marks reject."""
    grouped = {name for row in groups.groups() for name in row["members"]}
    assert grouped.isdisjoint(APART)


def test_the_record_never_lands_where_a_colormap_would_be_read() -> None:
    """Every reader of the library globs `*.json` here and takes the stem as a map
    name. The table written as `.json` would be read as a map with no stops."""
    assert groups.record_path().suffix != ".json"
    assert groups.record_path().name not in [path.name for path in colormap_dir().glob("*.json")]
    assert groups.record_path().stem not in groups.library()


def test_a_pair_distance_is_the_number_the_record_carries() -> None:
    """The metric itself, on the two-map groups where a pair distance IS the
    group's widest. Regenerating the whole triangle takes minutes; this asks the
    same question about the same function on four maps."""
    pytest.importorskip("numpy")
    pairs = [row for row in groups.groups() if row["size"] == 2]
    for row in (pairs[0], pairs[len(pairs) // 2], pairs[-1]):
        matrix = groups.m1(row["members"])
        assert round(float(matrix[0, 1]), 6) == row["max_m1"] == row["mean_m1"]


def test_the_cloud_is_the_bake_and_not_a_second_densifier() -> None:
    """Interpolated in Oklab, ends held, unfolded — `colormap.rs` with
    `mirror = false`. Interpolating the same stops in sRGB and converting after is
    a different curve, and a cloud built that way would answer a slightly different
    question than the picture does."""
    numpy = pytest.importorskip("numpy")
    from fractal_wallpapers.palettes import space

    name = "cet_linear_bmw_5_95_c86"
    positions, colours, _kind = space.ramp(name)
    read = groups.cloud(name)
    assert read.shape == (groups.SAMPLES, 3)

    lab = space.oklab(colours)
    # The ends are held rather than extrapolated, and they are the map's own stops.
    assert numpy.allclose(read[0], lab[numpy.argmin(positions)], atol=1e-9)
    assert numpy.allclose(read[-1], lab[numpy.argmax(positions)], atol=1e-9)

    # Halfway between two adjacent stops: the Oklab midpoint, which is not the
    # colour an sRGB midpoint converts to.
    order = numpy.argsort(positions)
    low, high = positions[order][0], positions[order][1]
    middle = groups.cloud(name)[int(round(0.5 * (low + high) * (groups.SAMPLES - 1)))]
    in_oklab = 0.5 * (lab[order][0] + lab[order][1])
    in_srgb = space.oklab(0.5 * (colours[order][0] + colours[order][1]))
    assert numpy.allclose(middle, in_oklab, atol=2e-4)
    assert not numpy.allclose(in_oklab, in_srgb, atol=2e-4)


def test_the_directions_are_a_half_sphere_of_unit_vectors() -> None:
    """Unit length, no pole sampled, and every one of them in the same half — a
    direction and its opposite give the same 1-D distance, so a lattice holding
    both would be half the coverage it claims."""
    numpy = pytest.importorskip("numpy")
    lattice = groups.directions()
    assert lattice.shape == (groups.DIRECTIONS, 3)
    assert numpy.allclose(numpy.linalg.norm(lattice, axis=1), 1.0)
    assert (lattice[:, 2] > 0.0).all()
    assert lattice[:, 2].max() < 1.0


def test_average_linkage_merges_by_the_group_and_not_by_its_nearest_member() -> None:
    """The chaining case, in four points: `a` and `b` are a pair, `c` is near `b`
    alone and far from `a`. Single linkage would weld all three; average asks about
    the group and holds `c` out."""
    numpy = pytest.importorskip("numpy")
    distance = numpy.array(
        [
            [0.0, 0.01, 0.09, 1.0],
            [0.01, 0.0, 0.03, 1.0],
            [0.09, 0.03, 0.0, 1.0],
            [1.0, 1.0, 1.0, 0.0],
        ]
    )
    merges = groups.average_linkage(distance, 0.05)
    found = {frozenset(group) for group in groups.cut_at(merges, 4, 0.05)}
    assert found == {frozenset({0, 1}), frozenset({2}), frozenset({3})}


# --------------------------------------------------------------------------- #
# The read-time collapse.
# --------------------------------------------------------------------------- #
def test_the_collapse_stands_one_member_of_each_group_up() -> None:
    """One member per group survives, every other member of that group is gone,
    and nothing that was not in a group is touched."""
    names = groups.library()
    pool, record = groups.collapse(names, seed=0)
    table = groups.groups()

    assert record["collapsed"] is True
    assert record["library"] == len(names)
    assert record["pool"] == len(pool) == len(names) - record["maps_stood_down"]
    assert record["groups_collapsed"] == len(table) == len(record["drawn"])

    kept = set(pool)
    for row in table:
        inside = kept & set(row["members"])
        assert len(inside) == 1
        assert record["drawn"][row["group"]] in inside
    grouped = {name for row in table for name in row["members"]}
    assert kept >= set(names) - grouped


def test_the_collapse_is_a_draw_and_the_seed_is_the_whole_of_it() -> None:
    """Same seed, same pool — a run has to be reproducible from its record. And
    two seeds have to stand different members up somewhere, or the draw is a
    canonical pick wearing a seed and every other member is retired for good."""
    names = groups.library()
    first, _ = groups.collapse(names, seed=0)
    again, _ = groups.collapse(names, seed=0)
    other, _ = groups.collapse(names, seed=17)
    assert first == again
    assert first != other


def test_the_collapse_deletes_nothing_from_the_library() -> None:
    """A stood-down map is still a map: still on disk, still nameable by a record,
    still readable by every other consumer. The collapse is a read, not an edit."""
    names = groups.library()
    pool, record = groups.collapse(names, seed=3)
    stood_down = set(names) - set(pool)
    assert len(stood_down) == record["maps_stood_down"] > 0
    for name in stood_down:
        assert (colormap_dir() / f"{name}.json").is_file()


def test_a_group_with_one_member_present_is_not_a_group() -> None:
    """A pool that holds only part of a group has no choice to collapse, and taking
    its one member away would leave the group unrepresented."""
    row = next(row for row in groups.groups() if row["size"] == 2)
    names = sorted({row["members"][0], "twilight_shifted"})
    pool, record = groups.collapse(names, seed=0)
    assert pool == names
    assert record["groups_collapsed"] == 0


def test_the_switch_is_on_and_an_unreadable_value_does_not_move_it(monkeypatch) -> None:
    """Shipping on. A typo must read as the default rather than as its own state:
    silently widening a production pool is the failure this guards."""
    monkeypatch.delenv(groups.COLLAPSE_ENV, raising=False)
    assert groups.enabled() is groups.COLLAPSE_DEFAULT is True
    monkeypatch.setenv(groups.COLLAPSE_ENV, "off")
    assert groups.enabled() is False
    monkeypatch.setenv(groups.COLLAPSE_ENV, "  ON  ")
    assert groups.enabled() is True
    monkeypatch.setenv(groups.COLLAPSE_ENV, "maybe")
    assert groups.enabled() is groups.COLLAPSE_DEFAULT


def test_the_pool_collapses_and_says_so(monkeypatch) -> None:
    """The one consumer. With the switch on the drawable pool is smaller than the
    shipped one and its record names the group behind every absence; with it off
    the pool is what it always was."""
    from fractal_wallpapers.curation import colorize

    shipped = colorize._shipped_pool()

    monkeypatch.delenv(groups.COLLAPSE_ENV, raising=False)
    collapsed = colorize.pool(seed=0)
    record = colorize.pool_record(seed=0)
    assert len(collapsed) < len(shipped)
    assert record["collapsed"] is True
    assert record["switch"] == groups.COLLAPSE_ENV
    assert set(record["drawn"].values()) <= set(collapsed)

    monkeypatch.setenv(groups.COLLAPSE_ENV, "off")
    assert colorize.pool(seed=0) == shipped
    assert colorize.pool_record(seed=0)["collapsed"] is False


# --------------------------------------------------------------------------- #
# A variant belongs to its base map's group.
# --------------------------------------------------------------------------- #
#: Three maps the table leaves alone, so a variant test reads a singleton
#: base — `twilight_shifted` looks like one and is in `m06`.
SINGLETON = "viridis"
OTHER_SINGLETONS = ["jet", "magma"]


def a_grouped_map() -> str:
    """One member of a real group, so the base's answer is an id and not `map:`."""
    return groups.groups()[0]["members"][0]


def test_the_mark_a_variant_is_split_on_is_absent_from_every_tracked_map() -> None:
    """`group_of` recovers a variant's base by splitting its name on
    `variants.MARK`, so a tracked map carrying one would be split into a base that
    is not itself and would answer with somebody else's group. The mark was chosen
    because no map here carries it; this is what holds that true."""
    carrying = [name for name in groups.library() if variants.MARK in name]
    assert carrying == [], f"{len(carrying)} tracked map(s) carry {variants.MARK!r}"


def test_a_variant_and_its_base_are_one_group() -> None:
    """Both halves: a base inside a real group, and a base that is a singleton.
    A variant is the same map one axis round, so it names the same group whatever
    the base's own group turns out to be."""
    table = groups.member_groups()
    for base in (a_grouped_map(), SINGLETON):
        wanted = groups.group_of(base, table)
        for axis, dose in variants.DOSES:
            name = variants.name_of(base, axis, dose)
            assert groups.group_of(name, table) == wanted
            assert groups.group_of(name) == wanted
    # And a variant OF a variant, which is how the sheet's two axes compose.
    twice = variants.name_of(variants.name_of(SINGLETON, "phase", 250), "repeat", 2)
    assert groups.group_of(twice, table) == groups.group_of(SINGLETON, table)


def test_the_palette_group_cap_counts_a_base_map_and_its_variants_together() -> None:
    """The cap is a count of seats one palette group may take, keyed on the
    `palette_group` a recipe carries — which is `group_of`'s answer. At a cap of
    one, a base map's variant is refused for `group_cap` exactly as a second seat
    on the base map would be."""
    from fractal_wallpapers.curation import ceiling, rules

    base = a_grouped_map()
    variant = variants.name_of(base, "phase", 250)
    rule = ceiling.Rule(targets={})
    rule.group_cap = 1
    state = rules.State(rule, 8)
    state.seat(candidate("seated", group=groups.group_of(base)), "general_pool")
    arriving = candidate("arriving", group=groups.group_of(variant))
    assert state.refuses(arriving) == "group_cap"
    assert set(state.groups[groups.group_of(base)]) == {"seated"}


def test_the_collapse_does_not_stand_a_variant_up_as_a_separate_look() -> None:
    """A pool holding a map and variants of it spends ONE slot on them, whether
    the base is in a group or a singleton — and every map that is not one of them
    is untouched. A variant standing up in the base's place is fine: the members
    of a group are near enough that no one of them deserves the slot."""
    table = groups.member_groups()
    assert not set([SINGLETON, *OTHER_SINGLETONS]) & set(table), "these three are not singletons"
    base = SINGLETON
    family = [base, *[variants.name_of(base, axis, dose) for axis, dose in variants.DOSES]]
    others = OTHER_SINGLETONS
    pool, record = groups.collapse([*others, *family], seed=0)
    inside = [name for name in pool if name in family]
    assert len(inside) == 1
    assert record["maps_stood_down"] == len(family) - 1
    assert [name for name in pool if name not in family] == others
    assert record["drawn"][f"map:{base}"] == inside[0]


def test_the_collapse_is_what_it_was_for_a_pool_of_library_maps() -> None:
    """Resolving variants changed no draw the library itself takes. The table's own
    group ids sort ahead of every `map:` id and a singleton consumes no draw, so a
    pool with no variant in it collapses exactly as it did — which is what makes
    this a fix rather than a re-seeding of every run record in the store."""
    names = groups.library()
    pool, record = groups.collapse(names, seed=0)
    table = {row["group"]: sorted(row["members"]) for row in groups.groups()}
    assert record["groups_collapsed"] == len(table)
    assert set(record["drawn"]) == set(table)
    for group, members in table.items():
        assert record["drawn"][group] in members
        assert [name for name in members if name in set(pool)] == [record["drawn"][group]]
