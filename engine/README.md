The Rust renderer: it makes every pixel this project ever shows.

One binary, six subcommands, one JSON object in and one file out:

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
home-view   a family → where it is framed by default, and how that was derived
modes       the named colorings, as JSON
```

The pipeline runs `spec → family → iterate → field → coloring → resample`, one
module per stage; `src/lib.rs` says what each does and why the seam between the
field and its coloring is the one that matters. `src/spec.rs` documents the JSON
and `src/mode.rs` the named colorings — nineteen of them, in four shapes: one
field, two fields blended, a base whose palette position a second field shifts,
or no field at all.

Every catalog entry carries a **tier**. Sixteen are `production` — a run may draw
them, and the finished-render judges were trained on them. Three are `niche`:
`threads`, `itinerary`, and `de`, renderable on demand by name and excluded from
every production draw. The exclusion is enforced in one place on each side of the
boundary — `mode::production_names` here, `engine.production_modes()` in Python —
so it is a property of a function rather than a rule every draw site remembers.
`fractal-wallpapers modes` prints the tier beside each name.

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
carries the TODO).

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
