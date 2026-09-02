# tests

The test suite, including the guard that keeps this history text-only and small.

```
python -m pytest                                    # the fast lane, ~1m40s
python -m pytest --slow                             # every test, ~5m45s
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
`shipped_render_cache`, `shipped_cv_pool`, `distillation_rows`, and
`tracked_ledger`. Each is a
second or more to derive and the same every time it is asked, and more than one
file asks. They are fixtures rather than module caches so the sharing is opt-in:
a test that redirects a store to `tmp_path` does not ask for them and cannot be
handed a reading of the tracked corpus by accident. Nothing writes to them.

`shipped_cv_pool` is the second one to reach for by reflex, and it is a factory
rather than a value on purpose. `render_deploy.sides_for` assigns `picture.side`
**in place**, so one shared list would carry whichever file ran last into
whichever ran next; the fixture hands back fresh `Picture`s on every call — a
`dataclasses.replace` a row, about ten milliseconds against four seconds — which
is exactly the independence a second `pool()` call used to buy. Its `assignment`
is the real `render_cv.assignment` with the shared pool patched under it, for
`shipped_render_cache`'s reason: a fixture that dealt the folds itself would be a
second opinion about the deal.

`tracked_ledger` is the dear one and the one to reach for by reflex. It carries
`.rows`, `.scores`, `.pool`, `.costs` and `.refused` — one reading, about 40s and
about 6 GB resident, serving `test_solve`, `test_headroom`, `test_distinct`,
`test_retention`, `test_hunt` and `test_candidate_ledger`. It
unsets the hot root while it lays the pool out, so a module that has redirected
the root at its own `tmp_path` cannot have this read an empty tree and report
every picture missing. It skips where the ledger has not been backfilled, which
is every machine but Matt's — CI included, so none of this costs CI anything.

## Where the time goes

The lane is a handful of tests and never a broad tax, and that is measurable
rather than a figure of speech: at 2026-08-31 the **top eighty tests were 490.6s
of a 563.5s lane**, and the other three thousand and sixty-eight were 72.9s
between them. So the question to ask of a slow lane that has grown is never
"what got slower"; it is **which store grew**, or **which derivation is being
paid twice**, and never a broad hunt.

That 563.5s is now **345.8s**, over the same 3,152 tests on the same machine the
same day, and no guard was deleted or moved lanes to get there. Four things came
out of the durations list, in the order they were worth:

| was | is | what |
| --- | --- | --- |
| 116.6s | 5.7s | `test_curation_colorize`'s byte-identity leg, on [`EXACTNESS_GEOMETRY`] |
| 29.5s | — | its fallback leg, the same |
| 52.4s | 6.3s | eight derivations of `render_cv.pool` collapsed to one — `conftest.shipped_cv_pool` |
| ~10.5s a call | 9ms | `served_locations.build` asking `current_pass` once instead of once a row |

And what is left, which is the list to read before touching this again:

| s | what |
| --- | --- |
| 31 | `test_autolevel_identity`'s 28 pinned probes — **pinned to production geometry**, so it is not the colorize leg's trade |
| 12 | **the one reading of the candidate ledger**, wherever it lands first |
| ~10 each | `test_render_head`, `test_distinct`, `test_candidate_ledger`, `test_hunt` |
| ~7 each | `test_train`'s two epochs, `test_renders`' regeneration, `test_ledger_tracking`'s merges |

`test_ledger_tracking`'s merges are the honest kind: a merge reads the tracked
release sidecar through `intake.read_scores` once, and a test that merges twice
pays for two. That is what the door does in production and it is not a bug.

### A derivation paid twice is the thing to look for

`served_locations.build` is the one to remember, because it was not a test
problem at all. `current_pass(rows)` sat **inside the list comprehension that
filters `rows`**, so it re-ranked the whole store once per row: 1,186 calls to
`records.score_rank` where one was meant, on every merge, every seating and every
gallery build. It is a pure function of `rows` and `rows` does not move under the
filter, so hoisting it is the same answer for a thousandth of the work. Nothing
about the test suite made that visible — a profile of one 10s test did.

### The candidate ledger is the thing that grows

It went from 15,362 rows and 41 MB on 2026-08-26 to **366,236 rows and 1.11 GB on
2026-08-29** — 24x in three days, and it grew with every mine, hunt and depth leg.
One `candidate_ledger.read()` of that file was 21.9s, `read_scores()` 4.2s,
`present_pictures()` 13.0s and laying the pool out over them 13.4s, so a cold
`headroom.population()` was about 46 seconds.

**Those figures are the wide store's, and it was deleted on 2026-08-29.** What
stands in its place is 122,516 rows and 150.8 MiB — the top three per (location,
mode) under five protections, each row cut to what the readers consume.
Re-measured on this machine: `read()` **3.9s**, `read_scores()` **0.8s**,
`solve.pool()` end to end **7.1s** against **29.3s** over the wide file. Reading
is no longer what this lane pays for.

**And it now has a ceiling, which is new.** `candidate_ledger.prune` runs inside
`candidate_ledger.merge`, so rows per (location, mode) are bounded by
`RETAIN_PER_PAIR` plus whatever the five protections carry, and are no longer a
function of the attempts made. A leg that opens new locations still grows the
file; a leg that deepens old ones no longer does. The two rules below stand as
written — a bound is not a licence to read the store in a fast test — but the
digit is no longer expected to move on its own.

Two rules follow, and they are why this lane is 7 minutes instead of 18:

* **The ledger is read once a session.** `conftest.tracked_ledger` holds the
  rows, the sidecar and the pool laid out over them. Seven guards used to derive
  that independently — four module fixtures at ~46s each and three more that read
  the rows again to census them. Ask the fixture; never call `read()` in a test.
* **A guard that sweeps the ledger takes a budget, not the store.** Two did not,
  and both had lost their own docstring's estimate by an order of magnitude:
  `test_solve`'s cutting plane was super-linear (1.3s at 2,000 candidates, 1.9s at
  20,000, 18.8s at 100,000, **185.6s at 275,822**) — that guard went with the exact
  solve it measured, on 2026-08-31 — and `test_hunt` rebuilt a recipe key for all
  344,923 levelled rows at half a millisecond each. `test_hunt` states a constant,
  `SAMPLE`, with the measurement that set it and an assertion that the budget was
  actually filled. This is the one place the
  suite trades coverage for time, and it is written down at each site rather than
  implied.

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

`pytest-xdist` was measured rather than argued about, and the answer is still
**no** — but the reasons have changed, so here is both the old measurement and
what is left of it.

| 2026-08-26 | serial | `-n 4` | `-n 8` |
| --- | --- | --- | --- |
| fast lane | 44.7s | 37.3s | 39.7s |
| full lane | 160.3s | 79.4s | 76.4s |

The fast lane gains seven seconds at four workers and gets *slower* at eight,
because per-process imports are paid again and torch is most of them. That has
not changed and it is the lane that gets run all day.

The deciding fact was never the clock. Under xdist the held-back count **does not
print**, and neither does the deselection: `pytest_collection_modifyitems` and
the stash live in the workers, so the controller reports `4 passed` where the
serial run reports `4 passed, 2 deselected` and names the number. A runner that
makes the lane go quiet is buying seven seconds with the one property the lane
exists for.

That objection does not reach `--slow`, which deselects nothing and so has
nothing to go quiet about — which is why it was worth asking again at 18 minutes.
The answer is still no, for a new reason: **what is left of the lane does not
parallelise.** 160s of the 440s is `colorize` and `autolevel_identity` driving the
engine, and the engine is rayon across all twelve cores already — three concurrent
`fractal-engine.exe` were measured at 126s against 105s, a fifth and not a third,
because they contend rather than spread. Another 40s is one ledger read that every
worker would simply pay again, and 6 GB apiece with it. A dependency that bought a
fifth of a third of the lane, at four copies of a six-gigabyte read, is not a
trade.
