# tests

The test suite, including the guard that keeps this history text-only and small.

```
python -m pytest                                    # ~70s, 1647 tests
cargo test --manifest-path engine/Cargo.toml        # ~7s warm, ~28s cold
```

The walk tests need a **release** engine and skip themselves without one:
`cargo build --release --manifest-path engine/Cargo.toml`. The checks that read
the read-only source project skip where that checkout is absent, which is
everywhere but Matt's machine — CI included.

`cargo test` builds the crate at `opt-level = 2` (`[profile.test]` in
`engine/Cargo.toml`). The tests render, and unoptimized they take eight times as
long to run as the optimization costs to compile.

## Shared readings of the tracked records

`conftest.py` holds session-scoped fixtures over the records this repository
tracks — `shipped_labels`, `shipped_scored`, `shipped_tile_plan`,
`shipped_render_cache`, `distillation_rows`. Each is a second or more to derive
and the same every time it is asked, and more than one file asks. They are
fixtures rather than module caches so the sharing is opt-in: a test that
redirects a store to `tmp_path` does not ask for them and cannot be handed a
reading of the tracked corpus by accident. Nothing writes to them.

## Where the time goes

Almost all of it is in a handful of tests that do real work — building tiles
through the engine, laying out a head's render plan, regenerating judged
pictures and comparing them. Everything else is milliseconds. Two things that
used to dominate and no longer do, in case they come back:

* **A bootstrap is linear in its draws.** A read that asserts a point statistic
  or a verdict does not need the shipped five thousand resamples; tests that
  reduce it say so at the constant and pin the shipped number against the
  document that declares it.
* **A sweep over every tracked file is a sweep over tens of megabytes.** The
  palette corpus is most of this tree by bytes. Reject cheaply first.

Running the files in four concurrent processes takes about **113s against 180s
serial** — 1.6×, not the 4× the core count suggests, because per-process imports
are paid again and the slowest single tests cannot be split. That was not judged
worth a parallel-runner dependency, and the case has got weaker rather than
stronger: the suite has roughly tripled in wall time since these were last
measured at 22s/50s, and the speedup fell from 2.2× to 1.6× because one
round-robin group now runs 111s while the other three finish inside 45s. A split
that balanced by measured duration rather than by file would recover most of
that, which is a second reason a runner dependency is not the missing piece.

The twelve slowest are `--durations=12`, and they are the real work rather than a
long tail: `test_render_head`'s ablation at 14.7s, then a training checkpoint, a
regenerated picture compared against the one that was judged, and four
`curation_colors` stage tests, each 3–7.5s. Everything after those is under 3s.
