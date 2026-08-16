The Rust renderer: it makes every pixel this project ever shows.

One binary, five subcommands, one JSON object in and one file out:

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
`src/family.rs`. Only Phoenix's row is derived rather than inherited: its set is
taller than it is wide and a three-unit frame at 16:9 cuts both lobes off.

Beside the pipeline sits the search — `rng`, `screen`, `foci`, `expand` — which
uses it and does not extend it. It decides *where* to render and never *how*:
`expand` reads fields the pipeline produced and returns coordinates with the
structural gate that refused each one. What makes a picture good is not its
business; that judgement lives in Python.

Python drives this through `src/fractal_wallpapers/engine.py` and nothing else.
