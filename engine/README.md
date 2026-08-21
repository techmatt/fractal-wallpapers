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
side. `fractal-wallpapers render --discrete [CYCLE]` draws it.

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
