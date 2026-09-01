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

        from fractal_wallpapers.palettes import groups

        self.values = {
            key: numpy.full(groups.QUANTILES * groups.DIRECTIONS, value, dtype="float32")
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
    state = state_of(20)
    assert state.rule.allowed("dark_vivid_blue", 20) == 1
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
