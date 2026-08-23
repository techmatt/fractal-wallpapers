The Rust renderer: it makes every pixel this project ever shows.

One binary, nine subcommands, one JSON object in and one file out:

```
cargo build --release --manifest-path engine/Cargo.toml
echo '{"schema":1,"family":{"kind":"phoenix"},"resolution":[1920,1080],
       "supersample":2,"mode":"smooth_stripe","colormap":"twilight_shifted",
       "output":"artifacts/phoenix.png"}' \
  | engine/target/release/fractal-engine render
```

```
render      a location and a coloring → a PNG
dump-field  the same, stopping at the raw scalar field (+ a record of it)
recolor     a dumped field → a PNG, without iterating anything
expand      walk nodes → one rung each, gated, with a thumbnail per survivor
screen      frames you name → what each structural gate read, and its verdict
home-view   a family → where it is framed by default, and how that was derived
modes       the named colorings, as JSON
tiles       a plan of locations → training tiles, and a record of what was written
maxiter     widths → the iteration cap the depth policy gives each one
```

`expand` and `screen` are the same filter behind two doors. `src/screen.rs` owns
one `Battery` — the interior cap on a 128-pixel probe, the cap again on the node
render, the escape band, the occupancy floor, in that order — and both
subcommands spend it. `expand` *proposes* the frames it screens; `screen` is
handed them. A crate test screens an expansion's own candidates by name and
asserts every fate comes back the same, so the two cannot drift into being two
filters wearing one name.

Both readings a rung takes of its parent frame — the scale-space focus set and
the detail-weighted centroid — are pure functions of that frame, so `foci::Frame`
takes each on the first draw that wants it and every later draw off the same node
reads it. The randomness is untouched, because none of the cached work ever
consumed the node's stream. What that is worth is measured on the Python side:
see [the discovery package](../src/fractal_wallpapers/discovery/README.md).

`expand` will also report each node's kept focus set, behind `report_foci`. Off
by default and byte-identical off: the set is a reading of the parent frame that
every rung takes anyway and it consumes nothing from the node's random stream, so
the switch decides what is *reported*, never what is drawn.

The pipeline runs `spec → family → iterate → field → coloring → resample`, one
module per stage; `src/lib.rs` says what each does and why the seam between the
field and its coloring is the one that matters. `src/spec.rs` documents the JSON
and `src/mode.rs` the named colorings — nineteen of them, in four shapes: one
field, two fields blended, a base whose palette position a second field shifts,
or no field at all.

## The escape loop is written out per family and per channel set

`iterate::run` is one loop with eleven per-iteration channel checks and a `match`
over the families inside it, and it collapses to the bare recurrence only when
the compiler can see **both** the family and the channel set at the *call site*.
Then the checks fold away, `cpow`'s loop unrolls at a known degree, and the parts
of the `Orbit` nobody reads stop being built. Hand either one in as a runtime
value and none of it happens.

So the call site is written out rather than parameterized. `field::sweep_row`
matches its `Family` and its `Wants` into a table and **constructs** both fresh —
construction is what makes them constants — over the twelve channel sets of
`field::Channels` (the empty set, and each channel alone) times the nine families
of `family::over_written_out!`. Every catalogued mode lands in that table: a
composite lays its texture over the smooth base, and the smooth base asks the
loop for nothing, so a composite's channel set is its texture's single channel.
Two channels at once is reachable only from a hand-written coloring or a
multi-field dump, and falls through to the generic loop — same source, same
numbers, slower.

Measured on this repository's own machine, interleaved before-and-after at
640x360 ss2 over the home view of each family, best of three:

| family | smooth | tia | stripe | gaussian_int | threads | itinerary | de | all modes |
|---|---|---|---|---|---|---|---|---|
| mandelbrot | **2.45x** | 1.42 | 1.16 | 1.19 | 1.41 | 1.88 | 1.68 | 1.34 |
| multibrot d=3 | 1.90 | 1.51 | 1.14 | 1.22 | 1.39 | 1.65 | 1.61 | 1.34 |
| multibrot d=4 | 1.49 | 1.43 | 1.18 | 1.22 | 1.29 | 1.31 | 1.44 | 1.28 |
| multibrot d=5 | 1.24 | 1.33 | 1.15 | 1.25 | 1.27 | 1.21 | 1.42 | 1.25 |
| julia d=2 | 2.11 | 1.41 | 1.20 | 1.18 | 1.37 | 1.31 | 1.56 | 1.31 |
| julia d=3 | 2.05 | 1.52 | 1.18 | 1.18 | 1.41 | 1.80 | 1.68 | 1.35 |
| julia d=5 | 1.29 | 1.33 | 1.18 | 1.19 | 1.23 | 1.20 | 1.40 | 1.24 |
| phoenix | 1.21 | 1.07 | 1.04 | 1.11 | 1.10 | 1.13 | 1.48 | 1.12 |
| fractional d=2.5 | 1.09 | 1.06 | 1.07 | 1.14 | 1.06 | 1.07 | 1.06 | 1.08 |

**The two halves separate cleanly, and the bottom two rows are how.** Phoenix's
step is `z² + c + p·z₋₁` with no `cpow` to unroll, and `fractional_multibrot` is
not in the table at all — so both of them measure the *channel* half alone, and
both land near 1.1x. The gap between that and mandelbrot's 2.45x is the *family*
half. A direct trap, which paints in its own loop and never reaches this one, is
the control: 0.96x to 1.05x throughout.

The win shrinks as the recurrence gets more expensive, in both directions: down
the modes, because a `sin` or a `hypot` per iteration is work no folding removes,
and down the degrees, because `cpow` at `d = 5` is four multiplies whether or not
it unrolls. Two written-out families are cheap enough that the loop around them
is most of the cost, and those are the two that move.

It costs **175 KB of binary** (1.75 MB to 1.92 MB) and about **8 s** of the
crate's release compile (15 s to 23 s). Nothing else about the render changed: 347
renders spanning every family and every catalogued mode at all three live
geometries — 640x360 ss2, 384x216 ss1 and 2560x1440 ss4 — are byte-identical
before and after, and `field::tests::the_specialized_loop_is_the_generic_one_bit_for_bit`
holds the two paths together on every run of the suite.

**Three guards keep production out of the generic loop**, because a silent
fallback costs a multiple of the render time and shows up as nothing at all.
`every_production_mode_takes_the_specialized_loop` walks the mode catalog over
every family and asserts `field::takes_the_specialized_loop`;
`every_field_has_a_call_site_of_its_own` catches a twelfth channel added without
one; and the fallthrough arms carry `debug_assert`s that fire if something the
table claims to cover reaches them. The `match` over `Channels` is exhaustive, so
an arm cannot simply be deleted.

**The direct trap's own loop is not specialized and is the obvious next piece.**
`direct_trap::trace` carries the same runtime `match` over the families, plus
three more of its own — the trap shape, the transform and the merge — inside the
same iteration. Four production modes draw through it. `family::over_written_out!`
is written where it is so that loop can use the same table when somebody takes
that on.

**And at `ss = 1` the resample is skipped.** The Lanczos kernel at a reduction of
one normalizes to exactly 1.0 on the centre tap, so both passes are a long way to
copy a buffer; `resample::downsample` encodes straight from the source instead.
Byte-identical over 171 renders at the node regime, which is the geometry that
matters here — 384x216 `ss = 1` is the walk's own frame, drawn tens of thousands
of times a run — and worth about **0.9 ms** of a node frame whose paint, after
the specialization above, is 16 ms.

That skip has a trap in it, and it is written down at `encode_only` because it
reverses the sign of the change: the two passes it removes were **rayon-parallel**
and the encode replacing them was not. The expensive half of a resample is one
`powf` per output channel, and both paths do exactly the same number of those —
so a serial skip *lost* to the filter, 0.85x, by trading fifty cheap operations
for the parallelism on the one costly one. Chunked across the same cores it is
1.03x to 1.20x.

Every catalog entry carries a **tier**. Eighteen are `production` — a run may draw
them, and the finished-render judges were trained on them. One is `niche`: `de`,
renderable on demand by name and excluded from every production draw. `threads`
and `itinerary` were niche too, until a round of labels over both of them said
they were worth drawing. The exclusion is enforced in one place on each side of
the boundary — `mode::production_names` here, `engine.production_modes()` in Python —
so it is a property of a function rather than a rule every draw site remembers.
`fractal-wallpapers modes` prints the tier beside each name.

One catalog entry is not the same coloring on both planes. `itinerary`'s address
can open on `z₀`, which on a dynamical plane *is* the pixel — so its leading symbol
is the pixel's own angular sector and the modulate draws it as a hard wedge along
the axes. `{"kind": "itinerary", "start": "z1"}` opens the address at the first
iterate instead, so every symbol is one the recurrence produced. **The named mode
asks for `z1` wherever the pixel is `z₀`** and for `z0` on the parameter planes,
where `z₀ = 0` leaves no wedge to remove and the engine refuses the other. The
choice is in the record either way, so the picture and its coloring say the same
thing. `fractal-engine modes` has no family to answer for, so it prints the
parameter-plane form.

A field meant to be *looked at* rather than named stays out of the catalog
entirely. There is one: `discrete`, the integer escape count, which is what the
smooth count replaced and is in the crate so the article can show the two side by
side. `fractal-wallpapers render --discrete [CYCLE]` draws it. A **teaching field
has no business having a name**, so the guard is not "no mode is called
discrete": `no_catalogued_mode_reads_a_teaching_field` walks every field every
catalogued mode reads, both halves of a composite included, because the second
way in is the one nobody would look for. The two readings really are one escape,
and the smooth one refines the other — `the_smooth_count_lands_inside_the_step_the_orbit_left_on`
pins `floor(smooth) == iteration` over five families and 3,600 pixels each, which
is what makes the discrete render the *floor* of the smooth one rather than
something merely similar to it.

**A new field of a coloring must `skip_serializing_if` its default.** The render
cache and the location head's deploy view both name a file by
`renders.job_name`, a sha256 of the whole spec that goes over the wire, so a key
that appeared unconditionally would rename every picture the corpora were built
from. `Composite::texture_gamma`, `Direct::merge_order` and the itinerary field's
`start` are all written that way, and each says so where it is declared.

## The one family that only draws pictures

`fractional_multibrot` is `z ← z^d + c` at a **non-integer** `d`, on the
principal branch — `exp(d · Log z)` with `Arg z ∈ (−π, π]`, written out in
`cpowf` rather than delegated so the branch cut is a line somebody can point at.
The cut is on the negative real axis, so the picture carries a **seam** along
every ray where an iterate crosses it. That seam is not an artifact to be
smoothed away: it is what a fractional degree *is* on a single-valued branch, and
it is the subject of the figure this family exists to draw. A different branch
moves it and does not remove it.

It is **render-only**, and that is a guarantee about what cannot happen rather
than a gap. A written `render` or `dump-field` spec reaches it; seven other doors
turn it away by name — the supply engine's partition registry, the render cache's
plane question, every `--family` choice on the command line, the home-view table,
`expand`, `screen` and `tiles`. `Family::is_render_only` is the single question
all of them ask, so adding a door cannot quietly add a way in, and
`spec::render_only_refusal` is the one message they share.
`location.key_of_row` is the one that answers `None` instead of raising, and its
caller counts unjoinable rows, which is the loudest failure short of an
exception. `tests/test_fractional_degree.py` is the whole guarantee in one file.

Three consequences fall out of render-only:

* **`Family::home_view()` returns an `Option`, and this is the `None`.** A row in
  the framing table is a claim that a family is worth looking at unprompted,
  which is the one thing this family is not — so a spec for one says where it is
  framed or is refused.
* **The degree range is a statement about what has been eyeballed, not about
  where the arithmetic breaks.** `LOWEST_FRACTIONAL_DEGREE` is `1.8` and the
  ceiling is `5.0`, the same kind of claim `check_degree` makes about the
  integers. `iterate::BAILOUT` is `2^16` and a multibrot's escape radius
  `2^(1/(d−1))` stays inside it all the way down to `d = 1 + 1/16`;
  `the_bailout_covers_the_lowest_degree` pins that gap, so the floor can be
  lowered by looking at pictures rather than by touching the loop. The range
  reaches below 2 deliberately — `z^1.8 + c` is a set of its own and not an
  interpolation between two named ones.
* **A whole number is refused.** `degree: "3.0"` is the multibrot family's, read
  the same way `multibrot` refuses degree 2 because that set is the Mandelbrot
  set: one picture gets one name, and one cache identity.

No integer-degree render pays for any of this. `cpow` is repeated multiplication
over degrees 2 through 5 — faster than a polar round trip and exact where one is
not — and `cpowf` is reached only by this family.

**One capability is deliberately absent and is not debt: normal-map shading** —
lighting a render by the surface normal of a distance estimate, with an azimuth
and a lamp height. It makes a fractal read as an embossed metal plaque rather than
as a field, replacing the picture's own structure with a lighting model's. The
`de` field ships without it, as a scalar coloring like any other. Two further
gaps *are* open decisions rather than omissions: `biomorph`, which would change
what `n` means and so what every cached render means, and perturbation-based deep
zoom, which is the one genuinely large thing this engine lacks (`iterate.rs`
carries the TODO). **Deep zoom has two revival conditions, not one.** The obvious
one is the door below the coordinate wall. The second is *correctness above it*:
the escape counts this engine returns are already measurably wrong at depths it
draws today (below), and a low-precision delta against a high-precision reference
orbit is the fix for that as much as it is the key to the next four decades.

Until it arrives, `Viewport::is_resolvable_in_f64` is what says how deep `f64`
goes — and it asks the question the arithmetic actually poses. A sample coordinate
is formed as `center + across * width`, so two neighbouring sample centres tie
when the step between them falls under one `f64` unit of last place *at the
magnitude of that sum*. The refusal reads exactly that: `sample_spacing()`
against `RESOLUTION_ULPS` (4) ulps of the frame's own reach.

**It used to be `pixel_size() > 1e-13`, which was wrong twice.** A relative limit
enforced as an absolute constant, and read off the *output* pixel, so a
supersampled render was judged on a grid four times coarser than the one it
samples. Bisected at 2560x1440 ss4, the first tie is at width 2.84e-13 for a
centre near 0.23, 1.42e-13 near 0.081, 2.27e-12 at |c| = 1 — against a refusal at
2.56e-10, so **2.0 to 3.3 decades of headroom nothing was using**. Nothing that
used to be drawn is refused now; a great deal that was refused for the wrong
reason is drawn, which is what
[the deep run mode](../src/fractal_wallpapers/deep/README.md) descends into. The
new rule is held to the measurement by `viewport.rs`'s own tests, which bisect for
the tie and require the refusal to sit a *constant* multiple above it at four
magnitudes — a rule that were secretly absolute shows a headroom that moves.

Measured alongside, before any of that changed: the deepest location any ledger
holds (1.0165e-9) renders at release geometry with **zero** tied sample centres
per row, and the tie rate in its dumped field scales exactly x4 with a 4x finer
grid — which is the `f32` dump's own storage granularity, the same law the
shallow control four decades above the wall obeys. See
`scratch/measure_deep_probe_report.md`.

**The refusal guards COORDINATE REPRESENTABILITY and nothing else.** That is the
whole of its contract: it says two neighbouring sample centres are still two
numbers, and it says nothing whatever about the escape count computed from
either. There is a second wall above it — call it the *fidelity* wall — and the
engine does not guard it, cannot cheaply detect it, and does not claim to. A
sample coordinate can be perfectly distinct from its neighbour and the *orbit*
run from it still be decided by rounding: `f64` carries about 1e-16, the dynamics
stretch that by the Lyapunov growth of a few thousand iterations, and what comes
back is not the value at that point.
`julia_deep_eyetest`'s second addendum measured it — same starting `f64`
coordinate, orbit re-run at 50 digits, and the share of sampled points whose
escape count disagrees:

```text
case                 deg   wrong >=1% from   engine refuses   at 1e-11
julia (off-set)        2             1e-11            1e-13       6.3%
multibrot3 walk node   3              1e-9            1e-13       8.0%
mandelbrot walk node   2              1e-5            1e-13      22.0%
multibrot4 walk node   4              1e-5            1e-13      14.5%
julia (off-set)        5              1e-5            1e-13      26.8%
```

**The fidelity wall is case-dependent and sits between about `1e-4` and `1e-10`,
two to eight decades above the refusal.** Where a case lands on that spread is
decided by how long its orbits linger near the boundary, not by its degree: the
degree-2 mandelbrot node above sits on a **period-198** nucleus and is already
**2.3% wrong at `1e-5`**, crossing at the same rung as the degree-5 julia.

**It is almost never visible.** Only the degree-5 julia shows anything, as a
mosaic of bit-identical neighbours, and *supersampling makes that one worse* —
66.6% of adjacent samples identical at ss1 rising to 95.6% at ss8, because a
finer grid brings coordinates closer together and closeness is what the orbit
cannot keep. The other four are wrong by more and read as ordinary deep
pictures.

**This engine's `z^d` is the canonical identity of this project's output.**
`cpow` builds it by repeated multiplication; Python's repeated squaring is the
same arithmetic in a different order, and at degrees 4 and 5 the two `f64`
implementations differ by a whole iteration or more on **12.2%** and **20.4%** of
samples, worst 411 and 205. At degrees 2 and 3 the orders coincide and they
agree to `1e-5`, which is what that test looks like when rounding is not deciding
the answer. So **cross-implementation agreement is not expected at degree ≥ 4**
and is not a bug report: below the fidelity wall the evaluation order *is* the
definition, and a render is reproducible against this engine rather than against
the mathematics.

Nothing in the engine changed on the strength of this — the refusal is unmoved
and no fidelity check was added, because detecting one costs a second orbit at
higher precision per sample. What changed is downstream: the deep run mode reads
its floor as an **aesthetic** one and caps degree 5 a decade early, where wrong
turns into visibly flat. See
`scratch/julia_deep_eyetest_addendum2_report.md` for the per-case evidence and
`../src/fractal_wallpapers/deep/README.md` for the contract.

What deep zoom would cost, observed on the maker's perturbation backend at the S1
anchor with this repo's own cap policy: a walk node (384×216 ss1) is 0.31 s at
fw 1e-12, 2.75 s at 1e-15, 1.02 s at 1e-18 — cost tracks how much of the frame is
deep-iterating material, not depth, so budget ~3 s worst case. A *release* frame
(2560×1440 ss4) at fw 1e-15 is **~1 800 s** with no series approximation, which is
`curation.pacing.HUNG_CEILING[RELEASE]` exactly. Descending is cheap; presenting
what is found is not.

A render given no viewport comes home to its family's own frame, a table in
`src/family.rs` — and so does a walk root, which reads that table through
`home-view` rather than keeping a literal of its own. **Framing has one owner.**

Every row is one rule evaluated on that family's own measured set: the filled
set found on a 4001² grid at a cap of 4000, centred on itself, contained at 16:9
with a tenth of its deciding extent in margin. Nothing in the table was chosen —
the textbook Mandelbrot view `(−0.5, 3.0)` does not survive it, because three
units at 16:9 is 1.69 tall and the set is 2.2. Julia is the one exception, and a
stated one: its set is a different shape for every `c`, so there is nothing to
measure and it comes home to the whole plane.

Beside the pipeline sits the search — `rng`, `screen`, `foci`, `expand` — which
uses it and does not extend it. It decides *where* to render and never *how*:
`expand` reads fields the pipeline produced and returns coordinates with the
structural gate that refused each one. What makes a picture good is not its
business; that judgement lives in Python.

Python drives this through `src/fractal_wallpapers/engine.py` and nothing else.
