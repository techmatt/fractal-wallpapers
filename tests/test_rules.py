"""One spelling per rule: the set-level predicate, and what a 1-swap may ask it.

The whole point of this module is that a greedy seed and a swap loop consult the
**same** statement of every rule. So the pins here are pairs: `admits` and
`removals` have to agree about the same candidate against the same seated set, and
a rule that refuses outright has to be a rule whose requirement set no single
departure can satisfy.

The other pin is cost. The retired exact solve's seed asked its pairwise rule for
every pair of `[candidate, *seated]` at every candidate it considered — cubic — and
828 s of an 1800 s budget went there. Nothing here may reuse that shape, so
`test_a_candidate_the_counts_refuse_never_opens_a_picture` is a guard about the
clock as much as about the rules.
"""

from __future__ import annotations

import pytest
from tests.test_headroom import candidate

from fractal_wallpapers.curation import ceiling, rules


class Signatures:
    """A [`pixel_clouds.Clouds`] whose signatures are a lookup, so a test needs no
    pictures. Every signature is flat, so the distance between two of them is
    exactly the difference between the two values a test asked for."""

    def __init__(self, values):
        import numpy

        from fractal_wallpapers.palettes import groups, pixel_clouds

        self.values = {
            key: numpy.full(groups.QUANTILES * pixel_clouds.DIRECTIONS, value, dtype="float32")
            for key, value in values.items()
        }
        self.made = 0
        self.hits = 0
        self._seen: set = set()

    def of(self, name):
        held = self.values.get(str(name))
        if held is None:
            return None
        if str(name) in self._seen:
            self.hits += 1
        else:
            self._seen.add(str(name))
            self.made += 1
        return held

    def hold(self, name) -> None:
        pass

    def let_go(self, name) -> None:
        pass


def state_of(n, values=None, group_cap=100, targets=None):
    rule = ceiling.Rule(targets=dict(targets or {}))
    rule.group_cap = group_cap
    diversity = None if values is None else rules.Twins(Signatures(values))
    return rules.State(rule, n, diversity=diversity)


# --------------------------------------------------------------------------- #
# The two questions, and that they are one rule.
# --------------------------------------------------------------------------- #
def test_a_candidate_nothing_refuses_is_admitted_and_any_seat_could_leave_for_it():
    state = state_of(5)
    state.seat(candidate("a"), "general_pool")
    other = candidate("b")
    assert state.admits(other)
    assert state.requirements(other) == []
    assert state.removals(other) == {"a"}, "nothing in the way reads as every seat"


def test_a_place_already_taken_names_the_one_seat_that_would_have_to_leave():
    state = state_of(5)
    state.seat(candidate("a", location="one"), "general_pool")
    state.seat(candidate("b", location="two"), "general_pool")
    arriving = candidate("c", location="one")
    assert state.refuses(arriving) == "location"
    assert state.removals(arriving) == {"a"}


def test_two_rules_at_once_intersect_and_an_empty_intersection_is_no_swap_at_all():
    """The 1-swap's whole shape: at least one member of EVERY requirement has to
    leave, so a candidate whose requirements do not share a member cannot be
    admitted by removing one seat and is dropped without further arithmetic."""
    state = state_of(20, group_cap=1)
    state.seat(candidate("a", location="one", group="g"), "general_pool")
    state.seat(candidate("b", location="two", group="h"), "general_pool")
    arriving = candidate("c", location="two", group="g")
    assert state.refuses(arriving) == "location"
    assert state.requirements(arriving) == [{"b"}, {"a"}]
    assert state.removals(arriving) == set(), "no single departure admits it"


def test_the_cell_allowance_names_the_seats_carrying_that_cell_and_not_the_gallery():
    # The gallery is sized so the allowance is exactly one seat, off the rule
    # rather than off a number: `floor(K * t * n) + 1` is 1 up to n = 48/K, which
    # is n < 24 at K=2 and n < 16 at K=3, so a literal here would have to move
    # with the ceiling and this does not.
    seats = 48 // (ceiling.K + 1)
    state = state_of(seats)
    assert state.rule.allowed("dark_vivid_blue", seats) == 1
    state.seat(candidate("blue", cells=("dark_vivid_blue",)), "general_pool")
    state.seat(candidate("plain", cells=()), "general_pool")
    arriving = candidate("more_blue", cells=("dark_vivid_blue",))
    assert state.refuses(arriving) == "cell_allowance"
    assert state.removals(arriving) == {"blue"}


def test_unseating_gives_the_candidate_back_and_the_counts_with_it():
    state = state_of(20)
    held = candidate("blue", cells=("dark_vivid_blue",), families=("blue",), group="g")
    state.seat(held, "general_pool")
    assert state.counts(state.cells) == {"dark_vivid_blue": 1}
    back = state.unseat("blue")
    assert back is held
    assert state.cells == {} and state.families == {} and state.groups == {}
    assert state.places == {} and state.modes == {}
    assert state.admits(candidate("more_blue", cells=("dark_vivid_blue",)))


def test_the_group_cap_is_a_count_of_seats_and_the_record_says_so():
    state = state_of(20, group_cap=2)
    state.seat(candidate("a", group="g"), "general_pool")
    assert state.admits(candidate("b", group="g"))
    state.seat(candidate("b", group="g"), "general_pool")
    assert state.refuses(candidate("c", group="g")) == "group_cap"
    record = state.record()
    assert record["group_cap"] == 2
    assert "COUNT" in record["group_cap_is"]
    assert "tau_group" not in record


# --------------------------------------------------------------------------- #
# The cost, which is a rule about this machine as much as about the gallery.
# --------------------------------------------------------------------------- #
def test_a_candidate_the_counts_refuse_never_opens_a_picture():
    """Every candidate the four counted rules refuse is a signature not made, and
    that is why the diversity rule is last of [`rules.RULES`]."""
    clouds = Signatures({"a": 0.0, "b": 0.0})
    state = rules.State(ceiling.Rule(), 5, diversity=rules.Twins(clouds))
    state.rule.group_cap = 100
    state.seat(candidate("a", location="one"), "general_pool")
    assert state.refuses(candidate("b", location="one")) == "location"
    assert clouds.made == 1, "one for the seat held, none for the one `location` took"


def test_removals_short_circuits_the_counted_rules_before_it_opens_anything():
    """The same guard for the swap loop, which asks this once per view row: a
    candidate whose counted requirements already intersect to nothing must not pay
    a tenth of a second to learn what it already knows."""
    clouds = Signatures({"a": 0.0, "b": 0.0, "c": 0.0})
    state = rules.State(ceiling.Rule(), 20, diversity=rules.Twins(clouds))
    state.rule.group_cap = 1
    state.seat(candidate("a", location="one", group="g"), "general_pool")
    state.seat(candidate("b", location="two", group="h"), "general_pool")
    before = clouds.made
    assert state.removals(candidate("c", location="two", group="g")) == set()
    assert clouds.made == before, "an empty intersection is settled by arithmetic alone"


def test_a_counted_refusal_is_free_and_answers_for_a_candidate_nothing_reached():
    """The rejection ledger asks this of every clearing candidate after the fact,
    which it can only afford because it opens nothing."""
    clouds = Signatures({"a": 0.0})
    state = rules.State(ceiling.Rule(), 20, diversity=rules.Twins(clouds))
    state.rule.group_cap = 100
    state.seat(candidate("a", location="one"), "general_pool")
    before = clouds.made
    assert state.counted_refusal(candidate("z", location="one")) == "location"
    assert state.counted_refusal(candidate("y", location="free")) is None
    assert clouds.made == before


# --------------------------------------------------------------------------- #
# The diversity rule, and the seam it sits behind.
# --------------------------------------------------------------------------- #
def test_a_twin_of_two_seats_can_never_be_admitted_by_removing_one_of_them():
    """At one neighbour every seated picture inside the threshold is its own
    single-member requirement, so two of them intersect to nothing. That is a fact
    about the cost as well as the gallery — it is what lets the loop drop such a
    candidate immediately."""
    state = state_of(20, values={"a": 0.0, "b": ceiling.TAU / 4, "c": ceiling.TAU / 2})
    state.seat(candidate("a"), "general_pool")
    state.seat(candidate("b"), "general_pool")
    arriving = candidate("c")
    assert state.refuses(arriving) == "twin"
    assert state.removals(arriving) == set()


def test_a_twin_of_exactly_one_seat_can_be_admitted_by_removing_that_seat():
    state = state_of(20, values={"a": 0.0, "c": ceiling.TAU / 2})
    state.seat(candidate("a"), "general_pool")
    assert state.removals(candidate("c")) == {"a"}


def test_a_candidate_whose_picture_cannot_be_read_can_never_be_admitted():
    """PLANTED: the rule fails closed. Admitting means the diversity rule silently
    stops applying to exactly the candidates nothing can check — which put three
    untested rows in a shipped gallery — and no seat leaving changes that, so the
    swap loop's answer is `None` rather than an empty set."""
    state = state_of(20, values={"a": 0.0})
    state.seat(candidate("a"), "general_pool")
    assert state.refuses(candidate("gone")) == "picture_unreadable"
    assert state.requirements(candidate("gone")) is None
    assert state.removals(candidate("gone")) is None


def test_the_rule_is_reached_only_through_its_own_small_protocol():
    """A themed leg supplies geometry-only distinctness and changes nothing else, so
    what [`rules.State`] may call has to stay this short."""

    class Themed:
        NAME = "geometry"
        neighbours = 1
        tau = 0.5

        def __init__(self):
            self.held: list = []

        def within(self, key):
            return [(0.0, self.held[0])] if self.held and str(key) == "twinned" else []

        def hold(self, key):
            self.held.append(str(key))
            return True

        def drop(self, key):
            self.held.remove(str(key))
            return True

        def record(self):
            return {"rule": self.NAME}

    state = rules.State(ceiling.Rule(), 20, diversity=Themed())
    state.rule.group_cap = 100
    state.seat(candidate("a"), "general_pool")
    assert state.refuses(candidate("twinned")) == "geometry"
    assert state.record()["diversity"]["rule"] == "geometry"
    assert state.unseat("a").key == "a"


@pytest.mark.parametrize("gap", [0.0, ceiling.TAU / 2, ceiling.TAU * 0.99])
def test_everything_inside_the_threshold_refuses_and_the_threshold_has_one_name(gap):
    state = state_of(20, values={"a": 0.0, "b": gap})
    state.seat(candidate("a"), "general_pool")
    assert state.refuses(candidate("b")) == "twin"
    assert state.diversity.tau == ceiling.TAU
    assert state.record()["diversity"]["threshold"] == ceiling.TAU


# --------------------------------------------------------------------------- #
# What a pass costs, which is a rule about this machine as much as the gallery.
# --------------------------------------------------------------------------- #
def test_a_reduced_signature_is_made_once_and_kept_for_the_whole_pass():
    """THE COST OF A PASS. Deriving the reduced form from the full one through a
    bounded cache means a view larger than that cache re-decodes the same pictures
    on every pass — measured at 24,969 signatures for an 8,704-row view, 2.9 a
    row, and it made a pass that found nothing cost what a pass that found
    everything cost."""
    clouds = Signatures({"a": 0.0, "b": 0.5})
    held = rules.Twins(clouds)
    for _ in range(20):
        held.within("b")
    assert clouds.made == 1, "one decode, however many times it is asked"
    assert held.reduced_made == 1
    assert held.reduced_hits == 19
    assert len(held._mine) == 1


def test_the_full_signature_is_fetched_only_when_the_bound_cannot_settle():
    """99.9% of seat comparisons are settled by the bound, and a candidate whose
    bound settles every one of them never needs its own half-mebibyte cloud."""
    far = rules.Twins(Signatures({"seated": 0.0, "far": ceiling.TAU * 4}))
    far.hold("seated")
    assert far.within("far") == []
    assert far.full_signatures_fetched == 0, "settled, so nothing was read back"

    near = rules.Twins(Signatures({"seated": 0.0, "near": ceiling.TAU / 2}))
    near.hold("seated")
    assert [key for _gap, key in near.within("near")] == ["seated"]
    assert near.full_signatures_fetched == 1


def test_a_norm_written_per_row_is_the_norm_of_the_whole_stack():
    """The one arithmetic claim `Twins.hold` rests on, asserted rather than argued.

    The norm screen's store used to be `abs(stack).sum(axis=1)` over a stack
    gathered on every hold; it is now written a row at a time as the row arrives.
    Both reduce one contiguous run of the same length in float64, so the two agree
    **to the bit** — and if a numpy release ever made them differ, the screen would
    silently start settling a different set of seat comparisons.
    """
    import numpy

    made = numpy.random.default_rng(20260907).random((257, rules.bound_width()))
    for dtype in ("float32", "float64"):
        stack = made.astype(dtype)
        whole = numpy.abs(stack).sum(axis=1, dtype=numpy.float64)
        per_row = numpy.array([numpy.abs(row).sum(dtype=numpy.float64) for row in stack])
        assert (whole == per_row).all(), f"the two norms differ in {dtype}"


def test_a_seat_held_again_takes_its_own_row_back_rather_than_a_second_one():
    """What bounds the reduced store at the distinct pictures ever seated.

    The augmenting stage ejects and re-inserts thousands of times, and every one of
    those used to append a row that was never reclaimed — so the store grew with
    the CHURN rather than with the gallery, and the walk that gathered it grew
    with it. The row is the key's for the life of the pass, which is a stronger
    index guarantee than the one this replaced, not a weaker one.
    """
    held = rules.Twins(Signatures({"a": 0.0, "b": 0.5, "c": 0.9}))
    assert held.hold("a") is True
    assert held.hold("b") is True
    rows = dict(held._at)
    for _ in range(50):
        assert held.drop("a") is True
        assert held.hold("a") is True
    assert held._at == rows, "fifty ejections and re-inserts, and no row moved"
    assert len(held.keys) == 2
    assert held.held == ["a", "b"]
    assert held.drop("a") is True
    assert held.drop("a") is False, "a key already out is still not held"
    assert held.held == ["b"]


def test_the_counted_removals_open_nothing_and_are_a_superset_of_the_real_ones():
    """The whole basis of the swap loop's second prune: the diversity rule can only
    ever narrow the counted set, so a decision taken on the counted set alone is
    sound for the real one."""
    clouds = Signatures({"a": 0.0, "b": ceiling.TAU / 2, "c": 0.9})
    state = rules.State(ceiling.Rule(), 20, diversity=rules.Twins(clouds))
    state.rule.group_cap = 100
    state.seat(candidate("a"), "general_pool")
    before = clouds.made
    counted = state.counted_removals(candidate("b"))
    assert counted == {"a"}
    assert clouds.made == before, "no picture was opened"
    assert state.narrowed(candidate("b"), counted) <= counted
    assert state.narrowed(candidate("c"), state.counted_removals(candidate("c"))) == {"a"}


# --------------------------------------------------------------------------- #
# The themed diversity rule: geometry-only distinctness.
# --------------------------------------------------------------------------- #
def place_rule(vectors, tau=None, locations=None):
    """A [`rules.Places`] over two-dimensional unit vectors, by angle.

    Two dimensions because the cosine between two unit vectors is the whole of
    what the rule reads, and an angle is a distance a test can state — the same
    stand-in `test_solve`'s pre-selection tests use.
    """
    import math

    import numpy

    places = {
        key: numpy.array([math.cos(angle), math.sin(angle)], dtype=numpy.float32)
        for key, angle in vectors.items()
    }
    where = {key: key for key in vectors} if locations is None else locations
    return rules.Places(places, where, tau=tau)


def test_the_geometry_rule_refuses_a_place_inside_the_radius_and_names_the_seat():
    # cos(0.4) is 0.921, so a and b sit 0.079 apart — outside 0.07; a and c sit
    # 0.002 apart, well inside it.
    rule = place_rule({"a": 0.0, "b": 0.4, "c": 0.06})
    rule.hold("a")
    assert rule.within("b") == []
    assert [key for _gap, key in rule.within("c")] == ["a"]
    assert rule.tau == rules.GEOMETRY_RADIUS


def test_the_geometry_rule_is_over_the_PLACE_and_not_over_the_picture():
    """Two candidates at one location share one descriptor, which is the whole
    reason a themed leg can use this: colour is the theme, so the rule that keeps
    the collection varied must not be a rule about colour."""
    rule = place_rule({"here": 0.0, "far": 1.0}, locations={"one": "here", "two": "here"})
    rule.hold("one")
    assert [key for _gap, key in rule.within("two")] == ["one"]
    assert rule.record()["pictures_opened"] == 0


def test_a_dropped_seat_stops_refusing_and_the_indices_do_not_move():
    rule = place_rule({"a": 0.0, "b": 0.06, "c": 1.0})
    rule.hold("a")
    rule.hold("c")
    assert [key for _gap, key in rule.within("b")] == ["a"]
    assert rule.drop("a") is True
    assert rule.within("b") == []
    assert rule.held == ["c"]
    assert rule.drop("a") is False


def test_a_place_with_no_descriptor_is_admitted_and_counted():
    """The OPPOSITE of [`rules.Twins`], which fails closed, and the ruling
    `distinct.preselect` already made for this store: refusing on a missing row
    would make the rule a silent function of when the embedding leg last ran. Safe
    here only because one-per-location sits above it."""
    rule = place_rule({"a": 0.0})
    rule.hold("a")
    assert rule.within("nowhere") == []
    assert rule.hold("nowhere") is True
    assert rule.drop("nowhere") is True
    assert rule.record()["admitted_without_a_descriptor"] == 1
    assert rule.record()["seated_without_a_descriptor"] == 1


def test_the_state_names_the_geometry_rule_last_and_never_the_twin_test():
    """A rejection ledger keyed on `twin` under a pass that never applied the twin
    test names a rule nothing ran, which is worse than naming none."""
    rule = place_rule({"a": 0.0, "b": 0.06})
    state = rules.State(ceiling.Rule(), 20, diversity=rule)
    state.rule.group_cap = 100
    state.seat(candidate("a"), "general_pool")
    assert state.refuses(candidate("b")) == "geometry"
    assert rules.rules_for(rule)[-1] == "geometry"
    assert state.record()["rules"][-1] == "geometry"
    assert state.record()["diversity"]["threshold"] == rules.GEOMETRY_RADIUS
    assert rules.rules_for(None) == rules.RULES


# --------------------------------------------------------------------------- #
# One seat per CLUSTER.
# --------------------------------------------------------------------------- #
def test_two_places_in_one_cluster_hold_one_seat_between_them():
    """The whole of what pooling changes in the seating. `b` is a real place with
    real rows and the pre-selection folded it into `a`, so the two compete for one
    seat where before the fold `b`'s rows simply were not in the pool."""
    state = state_of(20)
    state.seat(candidate("a1", location="a"), "general_pool")
    arriving = candidate("b1", location="b", folded_into="a")
    assert state.refuses(arriving) == "location"
    assert state.removals(arriving) == {"a1"}


def test_a_relabeled_row_takes_its_clusters_seat_and_locks_out_the_survivor():
    """The constraint is one seat per cluster and not one seat per SURVIVOR: a
    sibling can take the seat, and the place the cluster is named after is then
    the one refused. That is the trade pooling exists to make available."""
    state = state_of(20)
    state.seat(candidate("b1", location="b", folded_into="a"), "general_pool")
    assert state.places == {"a": "b1"}
    assert state.refuses(candidate("a1", location="a")) == "location"


def test_a_place_nothing_folded_is_its_own_cluster_and_the_rule_is_unchanged():
    """Every record before 2026-09-09 and every pass under `distinct.DELETE`: no
    row carries a fold, `cluster` is `location`, and this is the one-per-location
    rule it has always been."""
    state = state_of(20)
    held = candidate("a1", location="a")
    assert held.cluster == held.location and held.folded_into is None
    state.seat(held, "general_pool")
    assert state.places == {"a": "a1"}
    assert state.refuses(candidate("a2", location="a")) == "location"
    assert state.admits(candidate("z1", location="z"))


def test_unseating_a_relabeled_row_releases_the_cluster_and_not_its_own_place():
    """`unseat` has to take the same key out that `seat` put in, or the swap loop
    leaves a cluster locked by a seat that is no longer there."""
    state = state_of(20)
    held = candidate("b1", location="b", folded_into="a")
    state.seat(held, "general_pool")
    assert state.unseat("b1") is held
    assert state.places == {}
    assert state.admits(candidate("a1", location="a"))


def test_the_seat_axis_says_it_is_keyed_on_the_cluster():
    """A record naming `one wallpaper per location` under a pass that seated one
    per cluster describes a rule that did not run."""
    state = state_of(20)
    assert "one wallpaper per cluster" in state.record()["hard"]
    assert "cluster" in state.record()["location_is"]
