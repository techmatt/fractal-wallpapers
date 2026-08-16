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
and `src/mode.rs` the named colorings — sixteen of them, in three shapes: one
field, two fields blended, or no field at all.

The catalog is also the production roster, so anything meant to be *looked at*
rather than shipped stays out of it and is asked for by writing the coloring out
in full. There is one such field: `discrete`, the integer escape count, which is
what the smooth count replaced and is in the crate so the article can show the
two side by side. `fractal-wallpapers render --discrete [CYCLE]` draws it.

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
