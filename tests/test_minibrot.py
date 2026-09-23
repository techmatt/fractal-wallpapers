"""The minibrot census instrument, against frames whose answer is known.

Five claims, and each is a thing this instrument got wrong before it was
written this way.

**The period ceiling.** [`discovery.operators.MAX_PERIOD`] is 64 and the atom in
the census's own named frame has period **1026**, so the operator path — the
right instrument for a walk deciding where to go — answers
`nucleus_outside_frame` on a frame squarely on top of a minibrot. That refusal is
pinned here beside the census's answer, because the two disagreeing is the whole
reason this module exists.

**The `f64` screen changes no verdict.** It is an approximation loose by decades
and it is allowed to cut the candidate list only because the slack covers that;
a screen that dropped a real atom would be a criterion of its own wearing a
speedup's clothes. Held on the named frame, where 71 periods rank, the screen
keeps 7, and the one it must not drop is the 60th of the 71.

**A dynamical partition is refused rather than answered.** A julia or phoenix
view has no embedded copy of a parameter-plane set, so a zero there would be a
measurement where there is none to make.

**Criterion (c) answers the enclosing copy and not the ancestor.** The named
frame is decoration of a **period-27** satellite at a ratio of **754**, and the
period-2 bulb qualifies on distance at every frame in seahorse valley while being
eight decades too big to be what the frame decorates — and being a bulb on the
main body, which never counts. The generation rule is what separates them, so
both halves of it are pinned: the chain's split into `[1, 2]` and `[27, 54]`,
and the bulb law it splits on, against bulbs solved for on all five planes.

**(a) and (c) are different questions.** On the one frame both were written
around they return different periods, different scales and opposite senses of the
ratio — the frame holds a period-1026 atom 11.8 frame widths across *and* sits
inside a period-27 copy 754 times its own width. A refactor that let one read
answer the other would pass every claim above and fail this one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fractal_wallpapers.discovery import minibrot
from fractal_wallpapers.discovery import operators as ops

#: The row `minibrot_descent_census_ckpt140` was written around: a `threads`
#: wallpaper at width 1.29e-9 inside a period-27 seahorse satellite, found by
#: `tuned129x_af6c2eb9xS4` and coloured by `mn132_u2`.
NAMED = ("-0.782601984654748", "0.15006989511782523", "0.0000000012860948266974178")

#: Its atom: period, and the frame's width in atom sizes.
NAMED_PERIOD = 1026
NAMED_SIZES = 11.777

#: The copy it is decoration OF: the satellite the tuned descent aimed at, the
#: frame's width in that copy's atom sizes, and the whole record-minimum chain.
NAMED_ENCLOSING = 27
NAMED_RATIO = 754.229
NAMED_CHAIN = [2, 27, 54, 1026]

#: `window_scale` of the bulb at internal angle `1/m` on each plane's main body,
#: solved for at the cardioid-boundary point that angle names. Measured once,
#: here, because the constant [`minibrot.bulb_scale`] carries is what tells a
#: bulb from a copy and nothing else in this repository would notice it moving.
MEASURED_BULBS = {
    2: [(2, 5.000000e-01), (3, 1.889138e-01), (5, 4.736452e-02), (11, 4.817856e-03)],
    3: [(2, 2.886751e-01), (3, 1.047435e-01), (5, 2.511480e-02), (11, 2.452357e-03)],
    4: [(2, 2.099868e-01), (3, 7.342907e-02), (5, 1.704641e-02), (11, 1.633505e-03)],
    5: [(2, 1.671851e-01), (3, 5.660520e-02), (5, 1.283202e-02), (11, 1.216393e-03)],
    6: [(2, 1.397654e-01), (3, 4.600542e-02), (5, 1.024038e-02), (11, 9.636893e-04)],
}


def _qualifying(held, width, degree):
    """The chain a frame's [`minibrot.enclosing`] read is decided on, main body first."""
    import mpmath as mp

    from fractal_wallpapers.discovery import nucleus as nuc

    width = float(width)
    nuc.set_precision()
    center = mp.mpc(mp.mpf(NAMED[0]), mp.mpf(NAMED[1]))
    rows = [minibrot.main_body(degree)]
    for period in minibrot.screened_chain(held, width, degree):
        solve = nuc.newton_nucleus(center, period, degree=degree)
        record = nuc.make_atom(solve.c, period, degree) if solve.converged else None
        if record is None or record["window_scale"] < width:
            continue
        distance = float(abs(solve.c - center))
        if distance > minibrot.ENCLOSE_K * record["window_scale"]:
            continue
        record["seed_distance_atoms"] = distance / record["window_scale"]
        record["size_over_width"] = record["window_scale"] / width
        rows.append(record)
    return rows


def test_the_census_finds_the_atom_the_operator_path_cannot_reach():
    record, cost = minibrot.probe(*NAMED, 2)
    assert record is not None
    assert record["period"] == NAMED_PERIOD
    assert record["frame_sizes"] == pytest.approx(NAMED_SIZES, abs=1e-3)
    assert record["in_frame"]
    # Under one frame width of centre, which is the same bound a snap holds to.
    assert record["seed_distance_frames"] < minibrot.NEAR_MULTIPLE
    assert cost["solves"] >= 1

    view = {"center_re": NAMED[0], "center_im": NAMED[1], "width": NAMED[2]}
    refused, _solves, why = ops._solve_at_center(view, 2)
    assert refused is None and why == "nucleus_outside_frame", (
        "the operator path found something at this frame, so the ceiling it sweeps to is no "
        "longer the reason this module exists"
    )


def test_the_f64_screen_keeps_the_period_the_solve_needs():
    """It may cut the list; it may not cut the answer."""
    held = minibrot.scan(NAMED[0], NAMED[1], 2)
    kept = minibrot.screened(held, float(NAMED[2]), 2)
    assert NAMED_PERIOD in held.periods
    assert NAMED_PERIOD in kept
    assert len(kept) < len(held.periods), "a screen that cuts nothing is not a screen"


def test_a_frame_centred_on_its_own_nucleus_reads_the_framing_it_was_built_at():
    """`snap_to_nucleus` frames an atom at 4 and at 16 sizes; the census reads them back.

    The one end-to-end check that the atom instrument and the framing agree: a
    view the operators built at `4 * window_scale` has to come back as four atom
    sizes wide, or the size this census reports is not the size anything else in
    this project frames by.
    """
    elephant = {"center_re": "0.2925", "center_im": "0.0149", "width": "0.01"}
    built = [row for row in ops.snap_to_nucleus(elephant) if row.available]
    assert built, "the snap found no atom in the elephant valley, where it always has"
    for row in built:
        if row.framing is None:
            continue
        record, _cost = minibrot.probe(row.center_re, row.center_im, row.width, 2)
        assert record is not None
        assert record["frame_sizes"] == pytest.approx(float(row.framing), rel=1e-6)
        assert record["in_frame"] is (float(row.framing) <= minibrot.FRAME_MAX)


@pytest.mark.parametrize("partition", ["julia:mandelbrot", "phoenix", "phoenix:classic"])
def test_a_dynamical_partition_is_refused_and_not_answered(partition):
    assert minibrot.degree_of(partition) is None


@pytest.mark.parametrize(
    ("partition", "degree"),
    [("mandelbrot", 2), ("multibrot3", 3), ("multibrot4", 4), ("multibrot6", 6)],
)
def test_every_parameter_plane_names_its_degree(partition, degree):
    assert minibrot.degree_of(partition) == degree


def test_the_band_reporting_covers_every_reading_including_both_open_ends():
    assert minibrot.band_of(0.5) == "<1"
    assert minibrot.band_of(1.0) == "1-2"
    assert minibrot.band_of(11.78) == "8-16"
    assert minibrot.band_of(1e9) == ">=1024"


def test_the_named_frame_is_decoration_of_the_satellite_its_descent_aimed_at():
    """Criterion (c)'s acceptance test: period 27, ratio ~750, and the chain."""
    record, cost = minibrot.enclosing(*NAMED, 2)
    assert record is not None
    assert record["period"] == NAMED_ENCLOSING
    assert record["size_over_width"] == pytest.approx(NAMED_RATIO, rel=1e-5)
    assert record["seed_distance_atoms"] < minibrot.TIGHT_ENCLOSE_K
    # The main body and its period-2 bulb qualify on distance and are one
    # generation; the copy and its own period doubling are the next, and the
    # answer is that generation's head — not the doubling, not the ancestor.
    assert record["chain_periods"] == [1, 2, NAMED_ENCLOSING, 2 * NAMED_ENCLOSING]
    assert record["generation"] == [NAMED_ENCLOSING, 2 * NAMED_ENCLOSING]
    assert record["innermost_period"] == 2 * NAMED_ENCLOSING
    assert cost["enclose_solves"] == len(NAMED_CHAIN)


def test_the_period_2_bulb_qualifies_on_distance_and_is_still_not_the_answer():
    """The failure the generation rule exists to stop, pinned as a measurement.

    Lowest-period-wins on its own is not a criterion here. The period-2 bulb's
    nucleus sits about half its own atom size from every frame in seahorse
    valley, so it qualifies on distance while being eight decades too big to be
    what the frame decorates — and it is a bulb on the main body rather than a
    copy, so its decorations are the main body's. A census pass taken before this
    rule existed read 618 of 804 enclosed record seats as period 2.
    """
    held = minibrot.scan(NAMED[0], NAMED[1], 2)
    groups = minibrot.generations(_qualifying(held, NAMED[2], 2), 2)
    assert [[row["period"] for row in group] for group in groups] == [[1, 2], [27, 54]]
    assert groups[0][1]["seed_distance_atoms"] < minibrot.TIGHT_ENCLOSE_K
    assert groups[0][1]["size_over_width"] > 1e8


def test_a_frame_whose_every_copy_is_a_bulb_on_the_main_body_is_enclosed_by_nothing():
    """Seahorse valley at 1e-7, where the chain is the period-2 bulb and nothing else."""
    record, cost = minibrot.enclosing("-0.7499", "0.0001", "1e-7", 2)
    assert record is None
    assert cost["enclose_refused"] == minibrot.NOT_ENCLOSED
    assert 2 in minibrot.scan("-0.7499", "0.0001", 2).chain


@pytest.mark.parametrize("degree", [2, 3, 4, 5, 6])
def test_a_bulb_on_the_main_body_reads_as_one_on_every_plane(degree):
    """The law is what tells a bulb from a copy, and it carries the `1/(d-1)`.

    Without that factor a degree-6 bulb reads 0.21 of the law and is taken for a
    copy, which would make every frame in the main body's decorations on four of
    the five planes read enclosed by something.
    """
    body = minibrot.main_body(degree)
    for m, measured in MEASURED_BULBS[degree]:
        law = minibrot.bulb_scale(m, degree) * body["window_scale"]
        assert 0.9 < measured / law < 1.5
        bulb = {"period": m, "window_scale": measured}
        assert minibrot.generations([body, bulb], degree) == [[body, bulb]]
    # A primitive minibrot at the same period is not, and degree 2's period 3 —
    # the largest one there is — is the nearest case in the whole population.
    primitive = {"period": 3, "window_scale": 1.903552e-02}
    assert minibrot.generations([minibrot.main_body(2), primitive], 2) == [
        [minibrot.main_body(2)],
        [primitive],
    ]


def test_the_record_minimum_chain_is_the_nesting_and_drops_the_main_body():
    held = minibrot.scan(NAMED[0], NAMED[1], 2)
    assert held.chain == NAMED_CHAIN
    assert 1 not in held.chain, "the main body never counts, so it is not a candidate"
    # The screen leaves only the copies that could still be bigger than the
    # frame; 1026's atom is a twelfth of the frame's width and is solved and
    # then dropped by the exact test, which is what the slack is for.
    kept = minibrot.screened_chain(held, float(NAMED[2]), 2)
    assert kept == NAMED_CHAIN


def test_the_two_criteria_answer_different_questions_about_the_same_frame():
    held = minibrot.scan(NAMED[0], NAMED[1], 2)
    holds, _cost = minibrot.probe(*NAMED, 2, held=held)
    inside, _cost = minibrot.enclosing(*NAMED, 2, held=held)
    assert holds is not None and inside is not None
    assert holds["period"] != inside["period"]
    # (a)'s atom is smaller than the frame and (c)'s copy is very much bigger.
    assert holds["frame_sizes"] > 1.0
    assert inside["size_over_width"] > 1.0
    assert holds["window_scale"] < float(NAMED[2]) < inside["window_scale"]


def test_a_frame_holding_the_whole_set_is_decoration_of_nothing():
    """The home view: no copy on the plane is bigger than it, so nothing encloses it."""
    record, cost = minibrot.enclosing("-0.75", "0.0", "3.0", 2)
    assert record is None
    assert cost["enclose_refused"] == minibrot.NOT_ENCLOSED


#: The four `tuned129x_*` descents' own root frames, at 25.89 atom sizes: centre,
#: width, the satellite period the descent aimed at, and what `enclosing` answers
#: at the shipped cut. Every one of them sits at 1.2–1.3 atom sizes from its
#: satellite's nucleus, so the satellite is cut and the answer is its doubling.
TUNED_ROOTS = [
    ("-0.7625147982130057", "0.09498293802778866", "0.00000042500141555402064", 35, 70),
    ("-0.7803396116701233", "0.14964433641224018", "0.00000014104674336470383", 22, 44),
    ("-0.7450176044215268", "0.14993460843809991", "0.00000000931250846995306", 33, 66),
    ("-0.7826022764422826", "0.1500694732679044", "0.0000000374656785728769", 27, 54),
]


@pytest.mark.parametrize(("re_", "im_", "width", "aimed", "answered"), TUNED_ROOTS)
def test_a_cut_that_drops_a_copy_answers_its_period_doubling(re_, im_, width, aimed, answered):
    """What [`minibrot.TIGHT_ENCLOSE_K`] costs at the shallow end, pinned as a number.

    These are the root frames of the four descents the tight reading is
    calibrated on, and it is calibrated on their *deep* rows. At the root
    the frame is 1.2 to 1.3 atom sizes off the satellite's nucleus, which the cut
    refuses — and the generation then starts at the satellite's own period
    doubling, which is half the size and inside the bound. The reading is not
    wrong, it is one generation too deep, and it is the shape of what a tighter
    or looser cut does to this census.
    """
    record, cost = minibrot.enclosing(re_, im_, width, 2, k=minibrot.TIGHT_ENCLOSE_K)
    assert record is not None
    table = {row[0]: row[1] for row in cost["chain_table"]}
    assert aimed in table, "the satellite is solved for; it is the cut that drops it"
    assert 1.2 < table[aimed] < 1.35
    assert record["period"] == answered == 2 * aimed
    # And it comes back the moment the cut is widened to hold the root frames.
    wider, _cost = minibrot.enclosing(re_, im_, width, 2, k=1.35)
    assert wider is not None and wider["period"] == aimed
    # The shipped bound is the geometric extent of a copy, so it holds them too.
    shipped, _cost = minibrot.enclosing(re_, im_, width, 2)
    assert shipped is not None and shipped["period"] == aimed


def test_the_solved_chain_is_reported_whatever_the_cut_says():
    """`chain_table` is what makes [`minibrot.ENCLOSE_K`] a line and not a re-run.

    The bound is calibrated on tuned descents, which all land in one part of a
    copy, so it is the cut most likely to be moved. Every row carries the whole
    solved chain with each entry's distance in its own atom sizes — including the
    rows that read *not* enclosed, which is where a wider cut would find its new
    answers.
    """
    record, cost = minibrot.enclosing(*NAMED, 2, k=0.5)
    assert record is None, "0.5 atom sizes is inside the copy's body, so nothing qualifies"
    table = cost["chain_table"]
    assert [row[0] for row in table] == [2, NAMED_ENCLOSING, 2 * NAMED_ENCLOSING]
    reswept = [row for row in table if row[1] <= minibrot.ENCLOSE_K]
    assert [row[0] for row in reswept] == [2, NAMED_ENCLOSING, 2 * NAMED_ENCLOSING]
    assert table[1][2] == pytest.approx(NAMED_RATIO, rel=1e-5)


def test_a_cut_moved_off_the_chain_table_agrees_with_probing_again():
    """[`minibrot.enclosing_at`] is what makes the example set cheap, so it is pinned.

    `minibrots examples` re-reads a census row rather than solving again, which is
    the only reason a different `--k` costs nothing. It has to give the answer a
    fresh [`minibrot.enclosing`] gives at the same cut, or the example set and the
    census would drift apart with nothing looking broken.
    """
    held = minibrot.scan(NAMED[0], NAMED[1], 2)
    _record, cost = minibrot.enclosing(*NAMED, 2)
    row = {"partition": "mandelbrot", "width": float(NAMED[2]), "chain_table": cost["chain_table"]}
    for k in (0.5, minibrot.TIGHT_ENCLOSE_K, 1.35, minibrot.ENCLOSE_K):
        fresh, _cost = minibrot.enclosing(*NAMED, 2, k=k, held=held)
        reread = minibrot.enclosing_at(row, k)
        if fresh is None:
            assert reread is None
            continue
        head, groups, solved = reread
        assert head["period"] == fresh["period"]
        assert [[one["period"] for one in group] for group in groups] == fresh["generations"]
        assert [one["period"] for one in solved] == [row[0] for row in cost["chain_table"]]


def test_the_example_set_is_read_back_or_answers_empty():
    """A writeup asking what the census found gets `({}, [])` where nobody has run it."""
    assert minibrot.examples_path().name == minibrot.EXAMPLES_NAME
    assert minibrot.read_examples(Path("no") / "such" / "file.jsonl") == ({}, [])


def test_the_ratio_decade_bins_by_the_decade_and_refuses_a_non_reading():
    assert minibrot.ratio_decade(1.0) == "1e0"
    assert minibrot.ratio_decade(754.23) == "1e2"
    assert minibrot.ratio_decade(3.9e8) == "1e8"
    assert minibrot.ratio_decade(0.0) == "n/a"
    assert minibrot.ratio_decade(float("inf")) == "n/a"
