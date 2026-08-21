The deep run mode: sourcing, scoring and release below the shallow walk's floor.

The ordinary walk stops at width `1e-9`. Everything under this directory is one
answer to *what is down there*, built as a **separate mode** rather than as a
lower floor on the existing one — its own roots, its own floor, its own clock —
so that nothing about the shallow pipeline moves while the question is open.

```
depth      how deep this mode goes, the band a nucleus is framed in, the f64 wall
centers    Newton on a nucleus at the precision that nucleus asks for
roots      the two channels a seat comes from: newton, and continuation
run        one deep run: seats in, a ledger out, and the ceilings it is held to
```

```
fractal-wallpapers deep roots --seats 8 --out scratch/seats.jsonl
fractal-wallpapers deep walk  --seats 8 --batches 12 --out-dir artifacts/deep
fractal-wallpapers curate run --deep --harvest artifacts/deep --run deep1 -n 2
```

What follows is what to read before changing anything here.

**Pure `f64`, end to end.** There is no perturbation kernel in this repository
and this mode does not add one: the walk, the score and the release all run the
same arithmetic the shallow path does. The arbitrary precision in `centers.py`
exists only to say *where* a nucleus is — a center travels as decimal strings and
is re-parsed to `f64` at every render, which is exactly what the shallow path
already does with a shallower string.

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
