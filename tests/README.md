# tests

The test suite, including the guard that keeps this history text-only and small.

```
python -m pytest                                    # the fast lane, ~2m45s
python -m pytest --slow                             # every test, ~6m30s
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
`shipped_render_cache`, `shipped_label_pool`, `distillation_rows`, and
`tracked_ledger`. Each is a
second or more to derive and the same every time it is asked, and more than one
file asks. They are fixtures rather than module caches so the sharing is opt-in:
a test that redirects a store to `tmp_path` does not ask for them and cannot be
handed a reading of the tracked corpus by accident. Nothing writes to them.

`shipped_label_pool` is the second one to reach for by reflex, and it is a factory
rather than a value on purpose. `render_deploy.sides_for` assigns `picture.side`
**in place**, so one shared list would carry whichever file ran last into
whichever ran next; the fixture hands back fresh `Picture`s on every call — a
`dataclasses.replace` a row, about ten milliseconds against four seconds — which
is exactly the independence a second `pool()` call used to buy. Its `assignment`
is the real `render_folds.assignment` with the shared pool patched under it, for
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
| 52.4s | 6.3s | eight derivations of `render_folds.pool` collapsed to one — `conftest.shipped_label_pool` |
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

### The lane's readings, in order

Every reading this lane has taken, in the order they were written, moved here
from `CLAUDE.md` on 2026-09-04 — that file is loaded into every session in this
repository and a chronological log is not a rule. The rules the log produced
stayed there; this is the evidence under them. The order is the one they were
appended in, because several entries say "the reading below" and mean the one
that was below them.

Both are measured, not estimated. The fast lane is **142.06 s over the 3,307 it
holds**, of 3,423 there are — on this machine, idle, 2026-09-02, at the commit
that gave the depth record its autolevel stamp. It read **140.12 s over 3,302**
two commits earlier, and **139.0 s over 3,276** at the commit that added the
viewport sampler. The slow lane has **not** been re-run since that last one and
its reading stands: **6:27** over 3,388 tests. So the fast lane is flat across 31
more tests — 3.1 s and 2.2% apart — and this entry is re-measured rather than
moved.

It read **156.01 s over 3,336** immediately after the phoenix band sitting landed
200 rows across both finished-render stores, idle, 2026-09-02 — 9.8% over the
figure above across 29 more tests, which is the per-test cost holding flat and is
recorded here because it is a reading taken right after a store grew.

It read **157.21 s over 3,345** at the end of the `MINE_diverse_0903` leg, idle,
2026-09-03 — four more tests than the reading below and 2.2% *under* it, taken right after a
session that put **18,940 candidates into the ledger (182,235 -> 201,174 recipes)** and grew
the score sidecar past half a million rows. Two store growths in one day and the lane has not
moved for either.

It read **170.45 s over 3,362** at the texture-route tidy, idle, 2026-09-03 — 4.0%
over the reading below across **one** more test. The new guard is 1.49 s of that and
the rest is data: the same session put 13 revision rows and 13 crops into
`smooth_render` and 23 entries into the texture register. Worth having because the
guard was **13.88 s** before one stub — `candidate_ledger.prune` reaches
`intake.read_scores`, which the ledger's isolation fixture does not redirect, so a
three-row store in `tmp_path` still swept this machine's real 428,000-row location
score store, twice. That is `tests/README.md`'s rule about a guard taking a budget
rather than a store, hiding one call deep inside production code rather than in the
test — every merge test in `tests/test_ledger_tracking.py` pays 4.5-10 s of the same
read today.

It read **165.17 s over 3,420** at the reframe defaults, idle, 2026-09-03 —
fifteen more tests than the reading below and **1.4% under** it. The thirteen new
guards cost 1.4 s between them: they decide two defaults off ledgers that are two
rows each in `tmp_path`, and neither reads a store. Nothing grew this session.

It read **165.85 s over 3,437** at the spiral share cap, idle, 2026-09-04 — 0.6%
over the reading below across **23 more tests**, which is thirty-one new guards over a
new location store, a new solve rule and the seconds-share conversion costing this lane
nothing.

It read **164.85 s over 3,414** at the `render_cv` delete, idle, 2026-09-04 — 0.2%
under the reading below across **six fewer** tests, which is `test_render_cv.py`'s six
fast guards going with the harness. Worth having only for what it says about the two
guards that changed underneath it: `test_render_dose` and `test_render_grade` now
*derive* the lineage deal instead of reading the written one, and that cost the lane
nothing because both are slow-lane and the derivation is the session's one pool read
either way.

**The reading before it, 173.35 s over the same 3,414, was taken beside a second
copy of itself** — a backgrounded lane that had not finished when a foreground one
started — and is 5.2% over this one. That is the "measure it on an idle machine"
paragraph below priced at its cheapest: the other process does not have to be a
render leg, and two pytest lanes are enough to move the digit.

It read **167.53 s over 3,405** at the spiral probe, idle, 2026-09-03 — nine more
tests than the reading below and **1.8% under** it, taken right after the spiral
store's first sitting landed: 500 verdicts, 472 KB of rows, and the store went
from four tracked files to five. The nine new guards are 3.0 s of it. A label
store's *first drop* is the growth this lane has historically noticed, and it did
not notice this one — five hundred rows is three orders off the ledger the seven
ledger guards sweep, which is the thing that actually prices this lane.

It read **170.58 s over 3,396** at the spiral attribute store, idle, 2026-09-03 —
4.1% over the reading below across thirty-five more tests, of which thirty-one are
new guards over a store that did not exist that morning. A fourth label store,
a fourth `--head`, and the lane did not notice: an attribute store is four tracked
files and a hundred pinned rows, which is nothing beside the corpora the seven
ledger guards already sweep.

It read **163.85 s over 3,361** at the `--draw-cells` build, idle, 2026-09-03 —
1.9% over the reading below across twenty more tests, taken right after a
ten-minute near-band leg merged 4,204 candidates and the prune took the ledger
194,037 -> 198,241 -> 194,114. Another merge, another flat lane.

It read **160.75 s over 3,341** at the weights-v6 flip, idle, 2026-09-03 — 3.0%
over that across five more tests. This one is worth having because of what had just
happened to the stores it reads: the two label corpora had grown to 11,272 pictures,
the render cache to 11,272 crops, and **the candidate ledger's score sidecar had
gone from 306,431 rows and 150 MB to 486,666 rows and 239 MB** in the same session,
because a judge flip writes a second full set of readings beside the first and
retires nothing. That is the largest single-session growth this store has seen since
the 2026-08-29 episode above, and the lane did not move for it. So a judge adoption
is **not** one of the things that prices this lane, and the seven guards that sweep
the ledger read it through `conftest.tracked_ledger` once whatever it holds.

**A reading taken beside a leg is a reading of the leg.** The same lane read
**404.6 s over 3,281** earlier that day with a mining leg holding the render pool,
which is 2.9x the idle figure over the same tests. That is the paragraph below
about an idle machine, priced: before believing a lane has slowed, check what else
is on the box, and re-run it alone.

It read **3,371 tests in 6:41** with the fast lane at **136.2 s over 3,260**,
idle, 2026-09-02, at the commit that swept `artifacts/`. That reading was taken
**right after** 41.5 GiB
and 31,426 paths came off the hot tier and 7.4 GiB moved to the archive — the
conditions the paragraphs below say to suspect — and it did not move: it is 16%
over the 5:45 below across 219 more tests, which is the per-test cost holding
flat. So the 2026-08-30 doubling stays attributed to the disk settling and not to
anything a sweep does on its own.

The reading it replaces was **3,152 tests in 5:45** with the fast lane at **98.3 s
over 3,039**, idle, 2026-08-31, at the commit that cut the lane — which is still
the entry to read first, because that prompt found the lane was never a broad
tax: the **top eighty tests were 490.6 s of the 563.5 s** it started at, and the
other three thousand were 72.9 s between them. It came down by collapsing
derivations paid many times over and by taking one pixel-exactness pin off
production's raster, and **no guard was deleted or moved lanes**.
`tests/README.md` carries the table and the reasoning; the one worth knowing
here is that `served_locations.build` was asking `current_pass`
once per row instead of once, which was ~10.5 s on every merge, seating and
gallery build in **production** and not only under test.

The figures below are the history that got it here, and they are kept because
each is a way this lane has moved without code moving.

It read **3,121 tests in 8:23** at the commit that added `renders deploy`, idle,
2026-08-30, with the fast lane at 116.8 s.
**It read 3,126 in 14:26 on 2026-08-31**, idle,
at the commit that closed the pool re-score — twice in a row (12:45 then 14:26) and
over five *more* tests than the 8:23. That is the third time this lane has moved
without code moving; the store that grew in between is the release pool's, whose
16,029 rows were rewritten and whose 3,484 candidate pictures were put back on
disk that morning. The entry here read 64.3 s and 7:20 at
`0b53e15`, then **3,101 in 16:25 with the fast lane at 290-320 s** at `9560862`
later the same day; what happened in between and what undid it are the next two
paragraphs, and they are why a stale figure here is worth correcting rather than
living with.

**A third move on 2026-08-30 went the other way and is recorded unsolved.** The
fast lane went 163.6 s to 289.8 s and the slow lane 8:22 to 16:25, over the same
tests on an idle machine, right after 194,058 levelled colormap directories and
14 GiB came off `artifacts/` — so the stores got *smaller*. It is not a test: the
ten slowest sum to 99 s on both sides of the sweep, and the extra ~130 s is a
~45 ms constant spread across all 2,998. It is not that day's code either, which
was checked by measuring 317.5 s at `7383b63` with the working tree stashed.
Suspected: NTFS metadata after a bulk small-directory delete. So also re-measure
after anything that moves hundreds of thousands of paths, and suspect the **disk**
as well as the stores.

**And it came back on its own, later the same day, with nobody doing anything to
it.** The slow lane read 8:23 and the fast lane 116.8 s over twenty *more* tests
than the 16:25 and 289.8 s above — the slow lane is back to its pre-sweep 8:22 to
within a second and the fast lane is well under its pre-sweep 163.6 s. No code
was reverted and no store moved between the two readings; the only thing that
happened in between is that hours passed. That is the strongest evidence the
doubling was the disk settling after the delete rather than anything in this
repository, and it is the reason to re-run a slow lane before believing one. It
is still not *proven*, so the paragraph above stays.

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
