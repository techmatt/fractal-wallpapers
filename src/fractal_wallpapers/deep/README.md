The deep run mode: sourcing, scoring and release below the shallow walk's floor.

The ordinary walk stops at width `1e-9`. Everything under this directory is one
answer to *what is down there*, built as a **separate mode** rather than as a
lower floor on the existing one — its own roots, its own floor, its own clock —
so that nothing about the shallow pipeline moves while the question is open.

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

**A production leg is launched with `--wall-budget`, not with `--seats`.** The
flag takes seconds and covers the whole piece of work — this command *and* the
evaluation gallery that reads it. Eight hours buys about **184 seats** where
`deep_run1` took 32 by hand and spent a quarter of its clock. `--seats` and
`--batches` still exist and still win when they are passed; left alone, they are
what the budget fills.

What follows is what to read before changing anything here.

**Pure `f64`, end to end.** There is no perturbation kernel in this repository
and this mode does not add one: the walk, the score and the release all run the
same arithmetic the shallow path does. The arbitrary precision in `centers.py`
exists only to say *where* a nucleus is — a center travels as decimal strings and
is re-parsed to `f64` at every render, which is exactly what the shallow path
already does with a shallower string.

**The shelf that kernel sits on now has two ways off it, not one.** The first is
the door below the coordinate wall, where two neighbouring sample centres are
the same `f64` and no arithmetic in this repository can draw anything at all. The second is *correctness at
depths already being drawn* — the escape counts up here are measurably wrong
(below), and a low-precision delta against a high-precision reference orbit is
the fix for that as much as it is the key to the next four decades. So a future
run that wants deep frames to be **right** rather than merely reproducible is a
reason to build it, on its own, without wanting a single extra decade of depth.

**Depth comes from which atom, not from how far a walk descended.** A seat is a
nucleus whose own framing band already lands below the shallow floor, so the
first frame this mode draws is one the shallow walk cannot reach. The alternative
— lifting the walk's floor and descending — spends the whole budget on the space
*between* atoms, which is the finding the maker's deep spec parked on: deep
beauty is depth-band-local.

**The `f64` wall is relative, and it was being enforced as a constant.** The
engine refused any view whose *output pixel* was under `1e-13`. That is a spacing
compared against a number that is only right when the coordinates are of order
one, and it ignored supersampling — so it refused width `2.56e-10` at release
geometry while adjacent sample centres first collide between `1.4e-13` and
`2.3e-12`, two to three decades lower. `engine/src/viewport.rs` now asks the
question the arithmetic actually poses: *how many representable numbers does one
sample step span?*, refusing below four. Nothing that used to be drawn is refused
now; a great deal that was refused for the wrong reason is drawn.

**The floor is a policy and the wall is a measurement, and they are close here.**
`depth.MIN_WIDTH` is `1e-11`. At release geometry the wall sits between `2e-12`
and `9e-12` depending on `|c|`, so the margin at the large-`|c|` end is a factor
of a few rather than decades. That is why `depth.releasable` is a check every
seat passes before anything is rendered, rather than a sentence in a comment: a
seat whose money shot fails it would produce finds that are refused at the last
step of the run that made them.

**And the floor is an *aesthetic* floor, because there is a third wall above
both of those and this mode does not clear it.** A sample coordinate can be
perfectly distinct from its neighbour and the orbit run from it still be decided
by rounding: `f64` carries about `1e-16`, a few thousand iterations of a
stretching map spend it, and what comes back is not the value at that point.
`julia_deep_eyetest`'s second addendum re-ran orbits at 50 digits against the
engine's own `f64` and found the three planes `deep_run1` walked wrong on
**8.0%, 14.5% and 22.0%** of sampled points at their deepest kept frames, by up
to 669 iterations — and the onset is case-dependent, from `1e-4` on a
period-198 mandelbrot node to `1e-10` on a benign degree-2 julia.

**The contract this mode ships under is therefore about pictures and not about
escape counts.** Deep smooth output below the fidelity wall is
deterministic — the same spec renders the same image every time — and partly
*fictional* in its finest texture, and it is judged as art, by the same heads on
the same pictures as everything else. Escape-count correctness is not claimed
and is not the thing being sold. What is *not* acceptable is a picture that
looks like arithmetic, which is what the degree-5 cap below is for.

**Degree 5 stops a decade early: `depth.DEGREE_MIN_WIDTH` puts its floor at
`1e-10`.** It is the one plane where being wrong is visible. Its neighbouring
orbits do not scatter, they collapse onto one value, and at `1e-11` two thirds
of horizontally adjacent samples come back bit-identical — a mosaic of flat
cells rather than fine texture. **Supersampling makes it worse**: 66.6% identical
at ss1, 95.6% at ss8, because a finer grid puts the coordinates closer together
and closeness is exactly what the orbit cannot keep apart. The other three
planes keep `1e-11`; their errors are larger and invisible. The floor is wired
per degree in `depth.min_width`, so it reaches the seat window
(`depth.seat_sizes`), the bands a plane is offered (`depth.open_bands` — degree
5 loses the `floor` band outright) and the walk's own rung gate, which is how a
seat admitted above the floor is stopped from descending through it.

**Standing check on any future deep release.** Render the winner at *eval* and at
*release* geometry and eyeball the pair before shipping it. In the amplified
regime the texture is grid-dependent — supersampling makes the degree-5 collapse
worse rather than better, and the same is true in principle of any case near its
own onset — so a frame that passed at 1920×1080 ss2 is not evidence about the
same frame at 2560×1440 ss4. This is a two-picture eye check, not a metric.

**Judging is the shipped head, at its existing floors, on record-and-rank.** No
deep-specific gate, no deep-specific calibration, no deep labels. The location
head has seen nothing below `1.8e-10` and exactly one held-out row below `1e-9`,
so its scale down here is an extrapolation with a single point behind it — and
the answer to that is to record what it said about every candidate at every fate
and let a later reading decide, not to invent a second unmeasured opinion.

**The reframing operators are off, and the reason is a number.** `discovery/
operators.py` refuses a framing whose node-width spacing is within half a decade
of the old `1e-13` wall, which puts its floor at `1.21e-10` — an order of
magnitude above this mode's. Left on, every find below that comes back
`f64_spacing_wall`. Nothing is lost: the operators are Newton on a nucleus
followed by a framing in atom sizes, and that is precisely what `roots.py` does —
at the precision the atom asks for, and as a source of seats rather than as a
triggered move.

**Seats are the budget lever.** A leg is priced by how many nuclei it stands on,
not by batches or rungs, because the cost of this mode is dominated by producing
a place to stand. `--seats` is the flag; everything else divides the work at one
of them.

**And a lever nobody can read is a lever set wrong.** `deep_run1` was given eight
hours, was seated at 32 by hand from conservative estimates, and spent **2h10m**
— the frontier emptied at 470 of 2000 node slots with three quarters of the
budget untouched. So `deep/budget.py` prices a seat off that run's own record
and `--wall-budget` divides:

```text
sourcing   379 s / 32 seats             11.8 s a seat
walk       290 s / 470 nodes x 14.7      9.1 s a seat
gallery    254 / 741 x 12.8 s x 23.2   102   s a seat
                                       -----
                                       123   s a seat
```

At eight hours, less a 15% margin for the estimate being `n = 1` and a flat 30
minutes for the staging and the checks that do not scale, that is **22,680 s of
usable budget and 184 seats** — 5.75x what was seated by hand. The gallery is two
thirds of it and is reserved rather than assumed: this command draws no finished
frame, and a walk that spends to the last second is a walk nobody has time to
look at. `--no-gallery-reserve` is the walk-only run, and it is a different piece
of work rather than a saving.

**The frontier emptying is not the end of the run.** With budget left beyond the
margin the run **sources again into itself** — same ledger, same artifacts root,
same `roots.Standing`, filling the family x band cells the earlier rounds left
least full. That is within-run continuation and not a follow-up run: the
no-back-to-back rule governs launching runs, and a run topping up its own seats
mid-flight is simply a correctly sized one. Every round is still gated on
don't-start-what-cannot-finish, against the same clock the batches are.

`--no-reseat` turns the continuation off; both it and `--reseat` default to
saying nothing, so the shipped default lives on `Limits` and not on a flag.

**A lineage is capped at 24 admissions, because monotony is a supply problem.**
`deep_run1` put 741 admissions on 15 of its 48 roots and 85 on one, and the 162
frames of its floor gallery were largely one composition in 162 palettes. A
gallery can spread itself over lineages after the fact — that one had to, mid-leg
— but it cannot get back the walk time that went into the lineage it then
thinned. So the cap acts at supply time: past it the lineage stops expanding and
its standing frontier nodes are evicted at the crossing, which is recorded as its
own `lineage_capped` row. Twenty-four is half again the equal share of that run's
own admissions over its own roots. **Record-and-rank still governs**: capped is
not deleted, every row keeps the fate it earned, and nothing is retro-refused —
which is also why a lineage can finish a run slightly over its cap, from nodes
already in flight when it closed. The overshoot is in the count; the batch slots
stop at the crossing. `--lineage-cap 0` turns it off.

**Seats spread over family x band, because rank hides this mode's own subject.**
The window is read in three equal-log **depth bands** — `depth.BAND_NAMES`, from
`floor` at `1e-11` to `upper` at the shallow floor — and the seats fill the cells
of family x band round-robin, least full first. The reason is a measurement, not
a taste: a global rank does not reproduce the window. `deep_v0`'s release ranked
by render score and its deepest picture landed at `4.4x` this mode's floor, and
seats taken in anchor order fill from whichever family the plane-seed grid
solved most of — so seats, quotas and galleries are all written per cell, and
the floor decade, which is the decade this mode exists for, is a cell rather
than a tail. A Newton descent is *aimed* at its cell by the size ceiling it
hands the ladder, and aim is not arrival — a ladder that lands deeper than it was
asked to is credited to the band it landed in rather than thrown away. The
continuation channel cannot aim, since the band a row sits in is a fact about the
ledger that admitted it, so it spreads over the four planes and keeps its own
depth-first rank inside one.

**What a leg of this mode costs, measured.** `deep_run1` (32 seats, 60 batches, an
idle machine): **sourcing ~12 s a seat** — and a ladder that stalls costs what one
that arrives does, so the price is per *descent*, not per seat — **a walk batch of
eight nodes 4.3 s median and 16.5 s worst** against the 900 s ceiling, and a
finished 1920x1080 ss2 frame **5.8-12.5 s** of render plus about four seconds of
colorize. That medium geometry is a seventh of a release frame's samples and is
what an evaluation gallery is drawn at; the release figures below are still the
only ones the release ceiling may be read against.

**A deep release is a different cost class and gets its own ceilings.**
Curation's hung-unit backstop only ever raises itself off units a run has
*finished*, so a class whose first row dies at the ceiling never teaches the run
that the class is slow. `curate run --deep` swaps in `run.HUNG_CEILING`, which is
sized off a measured deep release frame rather than off the shallow
distribution. A run's own measurements may still only raise it.

**`required_dps` is enforced here, and at these depths it never binds.**
`discovery/nucleus.Atom.required_dps` has always been computed, recorded and
ignored. `centers.solve` acts on it: it re-solves and re-measures at the demanded
precision until the answer stops asking. It first exceeds the shallow 60 digits
at `log₁₀|A| > 45`, about thirty decades below anything this mode frames, so what
the enforcement buys today is that the rule is in the code rather than in a
comment — and every center records the precision it settled at, so that claim is
checkable rather than assertable.

## What v0 does not do

Phoenix is out of scope entirely and fractional degrees are excluded. **Julia is
in scope and has no deep supply on either channel**: a Julia viewport is a point
of the *z*-plane and has no nucleus for Newton to solve, and no ledger in this
project holds a Julia admission anywhere near the shallow floor for the
continuation channel to carry. In practice v0 is the four parameter planes.

**A deep julia center has to be *on the julia set*, and there is a cheap way to
put it there.** `julia_deep_eyetest` measured what happens without one. Holding a
labeled julia location's center and narrowing the frame collapses: over six
julias and four widths, **22 of 24 frames come back with the engine's field
constant to a fraction of an iteration**, two thirds of them already dead at
`1e-3` and all of them by `1e-8`. This is not the `f64` wall — at `1e-11` the
sample step still spans 70 ulps or more — it is that a julia set has measure zero
in the *z*-plane, so a center that is not on it is in the open exterior, whose
escape-time bands thin toward the set faster than the frame narrows. Two ways of
finding a center were measured and one works:

* **Bisecting escape-time level sets does not get there.** The point it converges
  on, whose orbit survives 100 iterations, still sits `~1e-7` from the set,
  because the derivative product along an orbit that lingers near the set grows
  about a decade every nine iterations rather than doubling. Its frames are a
  smooth ramp by `1e-7`.
* **Orbit-guided inverse iteration does.** `z ← (z − c)^(1/d)` contracts, so it
  reaches the set from anywhere; steering which of the `d` branches it takes by
  the forward orbit of the place you meant carries the destination as well. Sixty
  steps each way, one retry loop for the case where the orbit passes near the
  critical point and the branch choice goes ambiguous. Every frame it produced at
  `1e-11` is live and **passes `depth.releasable` at full release geometry**.

**And a dead julia frame does not look dead.** The coloring stretches whatever
range it is handed, so a field that is constant to five decimals arrives as a
full-palette ramp or a few clean bands. Anything that screens julia frames for
emptiness has to read the field's span, not the picture — and the span has to be
taken over the samples that *escaped*, because an interior sample is a NaN and a
plain min/max over a black frame says nothing at all.

**Descending at a julia's center is a shallow maneuver, and no choice of `c`
changes that.** The ceiling is about `1e-5` whatever the parameter is: at every
tested `c`, from nuclei of large atoms to parameters `1e-22` from ∂M, the frame
degenerates into one of two dead things — an interior basin (a black body, no
sample escapes) or a `RAMP`, a frame of exterior that lies wholly inside one
escape band and reads, often to the digit, as the critical point's own escape count.
**Deep julia supply is viable only off-axis, at a point that is on the julia
set**, which orbit-guided inverse iteration puts there cheaply. That is measured
knowledge and not a plan: no julia seeder is built, and this mode is still the
four parameter planes.

**Choosing `c` near ∂M does not buy the descent depth either.** The obvious
rescue for the maneuver above — pick a `c` hard against the boundary of its own
parameter set, so that `z = 0` lands in the julia set rather than in an interior
basin — was measured over fifteen parameters at four widths, descending at the
critical point. **Nothing reached `1e-8`.** Grouped by distance to ∂M, rows still
spanning more than one escape count:

```text
group                       ∂M gap          1e-3  1e-5  1e-8  1e-11
nuclei of large atoms       1.6e-2..2.8e-2   0/3   0/3   0/3   0/3
labeled julia c             2.7e-20..7.3e-4  2/6   1/6   0/6   0/6
deep walk frames on a plane 1.5e-22..7.8e-12 2/3   2/3   0/3   0/3
nuclei of the deepest atoms 1.6e-12..3.8e-10 1/3   0/3   0/3   0/3
```

Two things fall out of that table. **The critical orbit's fate beats the
distance.** A minibrot nucleus is ten decades nearer ∂M than a large atom's and
behaves like it, not like a near-boundary parameter, because a nucleus is
superattracting and `z = 0` is the middle of a black basin at every width.
**And a frame that has fallen off the set sits at the critical point's own escape
count** — often to the digit, `3139.02` across a frame whose critical orbit
escapes at 3139. That is the number to read when asking how deep an origin
descent got, and it is why proximity to ∂M measured in the *parameter* plane does
not predict how far `z = 0` is from the julia set in the *dynamical* one.

**Budget note: a black frame is the expensive one.** Every pixel of an
interior-basin frame runs to the cap, so a `1e-11` frame at eval geometry costs
60–75 s against 0.2 s for a live one. A deep julia sweep is priced by how many of
its frames are interior, not by how many it draws.
