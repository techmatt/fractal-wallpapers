# tests

The test suite, including the guard that keeps this history text-only and small.

```
python -m pytest                                    # the fast lane, ~45s
python -m pytest --slow                             # every test, ~160s
cargo test --manifest-path engine/Cargo.toml        # ~7s warm, ~28s cold
```

The walk tests need a **release** engine and skip themselves without one:
`cargo build --release --manifest-path engine/Cargo.toml`. The checks that read
the read-only source project skip where that checkout is absent, which is
everywhere but Matt's machine — CI included.

`cargo test` builds the crate at `opt-level = 2` (`[profile.test]` in
`engine/Cargo.toml`). The tests render, and unoptimized they take eight times as
long to run as the optimization costs to compile.

## The two lanes

`--slow` is the whole suite; the default run holds back the eighty-odd tests
that do real work. A test earns `@pytest.mark.slow` by costing about a second or
more of a render through the engine, a training loop, or a sweep of a store —
the render cache, the tracked pool, the distillation corpus. Arithmetic stays
in the fast lane however much of it there is, and a slow guard **moves lanes rather than
being deleted or weakened**. The marker, the flag and the line the fast lane
prints all live in `conftest.py`; `CLAUDE.md` states the rule.

The line is the part that matters. Every run that holds anything back says how
much, because a lane that went quiet would be a set of guards nobody would
notice had stopped running.

Marking is not free of surprises: several of these guards share a cached
derivation — `absolute_paths_in_records`, `shipped_render_cache`, the engine
fingerprint's probe set — so moving one to the slow lane can simply hand its
cost to whichever sibling reads the cache next. Three of the first round's marks
bought nothing until their partner was marked too. Measure the fast lane after
marking, not before.

## Shared readings of the tracked records

`conftest.py` holds session-scoped fixtures over the records this repository
tracks — `shipped_labels`, `shipped_scored`, `shipped_tile_plan`,
`shipped_render_cache`, `distillation_rows`. Each is a second or more to derive
and the same every time it is asked, and more than one file asks. They are
fixtures rather than module caches so the sharing is opt-in: a test that
redirects a store to `tmp_path` does not ask for them and cannot be handed a
reading of the tracked corpus by accident. Nothing writes to them.

## Where the time goes

Measured over the whole suite by wrapping the calls, so these are shares of real
wall clock rather than a guess:

| cause | share |
| --- | --- |
| `is_file` / `stat` / `glob` sweeps | 33% |
| in-process compute — JSON, digests, numpy, torch | 50% |
| process launches (22.6s of 23.0s is the engine) | 12% |
| bulk file reads and writes | 5% |
| image codec, checkpoint load | under 1% each |

**The stat sweeps are the surprise and they are a Windows tax.** Laying out a
head's training population calls `Path.is_file` once per judged picture — twenty
thousand of them — and that one loop was 21s of a 195s suite. Nothing about it
is wasted work; it is just far dearer here than on Linux.

Four things that used to dominate and no longer do, in case they come back:

* **A bootstrap is linear in its draws.** A read that asserts a point statistic
  or a verdict does not need the shipped five thousand resamples; tests that
  reduce it say so at the constant and pin the shipped number against the
  document that declares it.
* **A sweep over every tracked file is a sweep over tens of megabytes.** The
  palette corpus is most of this tree by bytes. Reject cheaply first.
* **A stage that is a pure read of tracked data can be read once.** The colour
  census's `library` stage folds six hundred colormaps onto the codebook, and
  five tests ran it eight times between them for 21s. It is a module fixture now
  and every number they assert is still the real stage's.
* **A fixture that redirects a store must redirect all of it.** The neutral
  embeddings fixture redirected the store, the copy and the manifest but not the
  picture directory, so every `save` counted and sized this machine's thirty
  thousand neutral renders — 5.3s to measure something no test asserts.

## On a parallel runner

`pytest-xdist` was measured rather than argued about, and the answer is **no**:

| | serial | `-n 4` | `-n 8` |
| --- | --- | --- | --- |
| fast lane | 44.7s | 37.3s | 39.7s |
| full lane | 160.3s | 79.4s | 76.4s |

The fast lane — the one that gets run all day — gains seven seconds at four
workers and gets *slower* at eight, because per-process imports are paid again
and torch is most of them. The full lane genuinely halves, but it is the lane
that runs in CI and before a checkpoint, where 80s against 160s buys nobody's
attention back.

The deciding fact is not the clock. Under xdist the held-back count **does not
print**, and neither does the deselection: `pytest_collection_modifyitems` and
the stash live in the workers, so the controller reports `4 passed` where the
serial run reports `4 passed, 2 deselected` and names the number. A runner that
makes the lane go quiet is buying seven seconds with the one property the lane
exists for, and getting it back would mean a worker-to-controller channel —
complexity a new dependency ought to be removing.
