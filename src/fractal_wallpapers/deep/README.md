The deep run mode: sourcing, scoring and release below the shallow walk's floor.

The ordinary walk stops at width `1e-9`. Everything under this directory is one
answer to *what is down there*, built as a **separate mode** rather than as a
lower floor on the existing one — its own roots, its own floor, its own clock —
so that nothing about the shallow pipeline moves.

```
depth      how deep this mode goes, the band a nucleus is framed in, the f64 wall
centers    Newton on a nucleus at the precision that nucleus asks for
roots      the two channels a seat comes from: newton, and continuation
budget     what a seat costs, and how many of them a wall budget buys
run        one deep run: seats in, a ledger out, and the ceilings it is held to
```

```
fractal-wallpapers deep roots --seats 8 --out scratch/seats.jsonl
fractal-wallpapers deep walk  --seats 8 --batches 12 --out-dir artifacts/deep
fractal-wallpapers deep walk  --wall-budget 28800 --out-dir artifacts/deep2
fractal-wallpapers curate run --deep --harvest artifacts/deep --run deep1 -n 2
```

**A production leg is launched with `--wall-budget`, not with `--seats`.** The flag
takes seconds and covers the whole piece of work — this command *and* the
evaluation frames that read it; eight hours buys about **184 seats**. `--seats` and
`--batches` still win when passed; left alone, they are what the budget fills.

## What the mode is

**Pure `f64`, end to end.** There is no perturbation kernel in this repository and
this mode adds none: walk, score and release run the shallow path's arithmetic. The
arbitrary precision in `centers.py` only says *where* a nucleus is — a center travels
as decimal strings re-parsed to `f64` at every render. A kernel would be the way past
the coordinate wall **and** the way to make deep frames *right* rather than merely
reproducible; either is a reason to build one.

**Depth comes from which atom, not from how far a walk descended.** A seat is a
nucleus whose own framing band already lands below the shallow floor, so the first
frame drawn is one the shallow walk cannot reach. Lifting the walk's floor instead
spends the budget on the space *between* atoms: deep beauty is depth-band-local.

**The `f64` wall is relative.** `engine/src/viewport.rs` refuses a view when one
sample step spans fewer than four representable numbers, rather than comparing an
output pixel's spacing to a constant.

**The floor is a policy and the wall is a measurement, and they are close here.**
`depth.MIN_WIDTH` is `1e-11`; at release geometry the wall sits between `2e-12` and
`9e-12` depending on `|c|`. So `depth.releasable` is a check every seat passes before
anything is rendered: a seat whose money shot fails it would produce finds refused at
the last step.

### The aesthetic contract

**The floor is an *aesthetic* floor**, because there is a third wall above both and
this mode does not clear it: a sample can be distinct from its neighbour and its orbit
still be decided by rounding. At the deepest kept frames the escape counts are wrong
on a measurable share of points (8–22% on three planes, by up to hundreds of
iterations), with an onset that varies by case from `1e-4` to `1e-10`.

**The contract is about pictures and not about escape counts.** Deep smooth output
below the fidelity wall is deterministic — the same spec renders the same image every
time — and partly *fictional* in its finest texture, and it is judged as art, by the
same heads on the same pictures as everything else. Escape-count correctness is not
claimed. What is *not* acceptable is a picture that looks like arithmetic.

**Degree 5 stops a decade early: `depth.DEGREE_MIN_WIDTH` puts its floor at
`1e-10`.** Its neighbouring orbits collapse onto one value, and at `1e-11` two thirds
of adjacent samples come back bit-identical — a mosaic of flat cells. Supersampling
makes it worse (a finer grid puts coordinates closer). **Degree 6 takes degree 5's
`1e-10` by the pattern**, not by a measurement of its own: `z^(d−1)` pulls orbits
together harder as `d` rises. The other planes keep `1e-11`. The floor is wired per
degree in `depth.min_width`, reaching the seat window (`depth.seat_sizes`), the bands
offered (`depth.open_bands` — degree 5 loses `floor`), and the walk's rung gate
(`walk.Gates.for_family`).

**Standing check on any future deep release.** Render the winner at *eval* and at
*release* geometry and eyeball the pair before shipping. Texture is grid-dependent
here, so a frame that passed at 1920×1080 ss2 is not evidence about it at 2560×1440
ss4. A two-picture eye check, not a metric.

## How a run is judged, sourced and sized

**Judging is the shipped head, at its existing floors, on record-and-rank.** No
deep-specific gate, calibration or labels. The location head has seen almost nothing
below `1e-9`, so its scale here is an extrapolation; the answer is to record what it
said about every candidate at every fate and let a later reading decide.

**The reframing operators are off.** `discovery/operators.py`'s spacing guard puts its
floor at `1.21e-10`, an order of magnitude above this mode's, so every find below it
would come back `f64_spacing_wall`. Nothing is lost: `roots.py` does the same Newton
and framing at the precision the atom asks for, as a source of seats.

**Seats are the budget lever**: this mode's cost is dominated by producing a place to
stand. `deep/budget.py` prices a seat off a measured run and `--wall-budget` divides:

```text
sourcing      11.8 s a seat
walk           9.1 s a seat
evaluation   102   s a seat
             123   s a seat
```

The budget is reduced by `budget.MARGIN_SHARE` (15%) and `budget.FIXED_RESERVE`
(30 minutes) first. The evaluation frames are two thirds of a seat's cost and are
reserved, not assumed: a walk that spends to the last second is a walk nobody has time
to look at. `--no-evaluation-reserve` is the walk-only run, a different piece of work
rather than a saving.

**The frontier emptying is not the end of the run.** With budget left beyond the
margin the run **sources again into itself** — same ledger, same artifacts root, same
`roots.Standing` — filling the family x band cells least full. That is within-run
continuation, not a back-to-back run, and every round is gated on
don't-start-what-cannot-finish. `--no-reseat`/`--reseat` default to saying nothing; the
shipped default lives on `Limits`.

**What a later round must not re-buy is one object**, `roots.Standing`: the
per-family anchor queues (built once, *consumed*), the reflection keys the Newton
channel stands on, the place keys and `ledger|root_id` lineages the continuation
channel has taken, and the `family|band` cell fills. They are read and written
together; a round handed four of them re-seats along the fifth.

**A lineage is capped at `run.LINEAGE_ADMISSIONS` (24) admissions, because monotony is
a supply problem**: an uncapped run put most of its admissions on a few roots and its
frames were largely one composition. Past the cap the lineage stops expanding and its
frontier nodes are evicted (a `lineage_capped` row). **Record-and-rank still governs**:
nothing is deleted or retro-refused. The cap is asked per row at booking, so a lineage
never finishes over it: later rows are `not_admitted` with `lineage_capped: true` and
their score kept. `--lineage-cap 0` turns it off.

**Seats spread over family x band, because rank hides this mode's own subject.** The
window is three equal-log depth bands (`depth.BAND_NAMES`, `floor` at `1e-11` to
`upper` at the shallow floor), and seats fill family x band cells round-robin, least
full first — a global rank does not reproduce the window, and the floor decade is a
cell rather than a tail. A Newton descent is *aimed* at its cell by its size ceiling
and credited to the band it lands in. The continuation channel cannot aim, so it
spreads over the four planes and keeps a depth-first rank inside one.

**Costs.** Sourcing is about 12 s a *descent* (a stalled ladder costs what an arriving
one does); a walk batch of eight nodes about 4 s median, 16.5 s worst, against the
900 s ceiling; an evaluation frame (1920x1080 ss2) 6–13 s of render plus about 4 s of
colorize. **A deep release gets its own ceilings**: `curate run --deep` swaps in
`run.HUNG_CEILING`, sized off measured deep release frames, because curation's backstop
only raises itself off finished units. A run's measurements may still only raise it.

**`required_dps` is enforced.** `centers.solve` re-solves at the precision
`discovery/nucleus.Atom.required_dps` demands until it stops asking, and every center
records the precision it settled at. At this mode's depths it never exceeds the shallow
60 digits.

## What v0 does not do

Phoenix is out of scope and fractional degrees are excluded. **Julia is in scope and
has no deep supply on either channel**: a Julia viewport has no nucleus for Newton,
and no ledger holds a Julia admission near the shallow floor. In practice v0 is the
four parameter planes.

**A deep julia center has to be *on the julia set*.** A julia set has measure zero in
the *z*-plane, so narrowing on a labelled center lands in the open exterior and the
field goes constant by `1e-3` to `1e-8` — not the `f64` wall. Bisecting escape-time
level sets stalls about `1e-7` from the set. **Orbit-guided inverse iteration** works:
`z ← (z − c)^(1/d)` contracts onto the set, steered branch by branch by the forward
orbit of the intended place; its `1e-11` frames are live and pass `depth.releasable`.
No julia seeder is built.

**And a dead julia frame does not look dead.** The coloring stretches whatever range
it is handed, so a near-constant field arrives as a full-palette ramp. Screen for
emptiness by the field's span over the samples that *escaped* (interior samples are
NaN), not by the picture.

**Descending at a julia's center is a shallow maneuver**, about `1e-5` whatever `c` is,
and choosing `c` near ∂M does not change it: the critical orbit's fate beats the
distance (a nucleus is superattracting, so `z = 0` is a black basin at every width).
A frame that has fallen off the set reads, often to the digit, as the critical point's
own escape count. A black frame is the expensive one: every pixel runs to the cap.

## Tuning a good frame onto a satellite, and the width where it stops working

Douady–Hubbard tuning re-aims a main-set frame at the same position relative to a
satellite, from numbers `discovery/nucleus.py` already holds:

```text
lambda   = 1/A = atom.window_scale * e^(i * atom.rotation)
c_tuned  = c_sat + lambda * c_seed
w_tuned  = |lambda| * w_seed
```

The copy renders where the aim says, **rotated by `atom.rotation`**. **The aim misses
by a fixed fraction of `|lambda|`** (worse on larger satellites), so the miss in tuned
frame widths is `e / (|lambda| * w_seed)` and grows as the seed narrows: fine at
`w_seed >= 0.1`, gone by `0.01`. **So a gallery seat is the wrong thing to tune**;
tune the seed's neighbourhood at `w_seed = 0.1` and recover depth by descent. A nudge
cannot rescue a dead tuned frame, and `curation.flatness.fraction` is not a deadness
reading (a smooth gradient is locally planar); read `engine.screen`'s battery.

**Descending out of a tuned frame needs the relative floor**:
`Gates(min_width=depth.deepest_releasable_width(c_re, c_im))`, a parameter rather than
an override, since a tuned frame is already below `walk.Gates.min_width`. The release
floor is the **satellite's**, not the seed's.

**A tuned descent saturates.** It bottoms out against that floor after one to two
decades and the frontier dies; past about sixteen batches more buy nothing. **Size a
leg of this shape by places wanted, not by hours**: what bounds it is how many places
a copy holds above the junk floor. A copy whose root expands once and stops holds
nothing the gates admit at that scale.

### The reframing operators find nothing inside a copy

On a tuned descent they refuse with `nucleus_outside_frame`. That is half geometry
(the nucleus they would snap to is the parent's, thousands of frame widths away) and
half the period ceiling: `operators.MAX_PERIOD` is 64 and the atoms inside a
period-`q` copy sit at multiples of `q`. The operators are right not to fire — a
`4 x size` framing of such an atom is past the spacing wall at release geometry — but
their refusal does not mean *no minibrot in this frame*. `discovery/README.md`'s *Is
there a minibrot in this frame* has the instrument.
