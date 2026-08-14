The Rust renderer: it makes every pixel this project ever shows.

One binary, one subcommand, one JSON object in and one PNG out:

```
cargo build --release --manifest-path engine/Cargo.toml
echo '{"schema":1,"family":{"kind":"phoenix"},"resolution":[1920,1080],
       "supersample":2,"colormap":"twilight_shifted","output":"artifacts/phoenix.png"}' \
  | engine/target/release/fractal-engine render
```

The pipeline runs `spec → family → iterate → field → coloring → resample`, one
module per stage; `src/lib.rs` says what each does and why the seam between the
field and its coloring is the one that matters. `src/spec.rs` documents the JSON.

Python drives this through `src/fractal_wallpapers/engine.py` and nothing else.
