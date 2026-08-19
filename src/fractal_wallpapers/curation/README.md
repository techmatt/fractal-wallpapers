Judging finished renders: what to colour, how to colour it, what to keep, and
what to make at full size.

This is the last stage. Everything upstream produces *supply* — places a walk
found, judges trained on human verdicts, a palette head that ranks colour choices.
Curation spends it: it turns the union of every walk into a small set of finished
wallpapers and a durable account of why those and not the others.

```
binding    which ledgers this curation reads, declared once and never guessed
floors     every number that removes a picture, in one file
intake     the ranked offer, best first per partition
budget     how many pictures to make, and for which judge
colorize   a candidate set of maps, the head's pick, a render, a verdict
selection  top-N per judge, under the slot, supply and look caps — and the bar
release    the selected rows again at full size, workers rendering
pacing     the wall clock: what may still start, and what is killed
records    what the run decided, and out of what population
rejection  taking a released row back afterwards, without losing what the run did
sheet      the same thing laid out for a person to disagree with
checks     the two claims only a re-render can settle
run        the wiring, and nothing else
```

```
fractal-wallpapers curate score --harvest artifacts/harvest_run3   # through the location head
fractal-wallpapers curate plan --harvest artifacts/harvest_run3 -n 6   # making nothing
fractal-wallpapers curate run --run v1 --harvest artifacts/harvest_run3 -n 6
fractal-wallpapers curate run --run v1 --ledger artifacts/harvest_run3/walk.jsonl -n 60 \
    --wall-budget 28800                                            # eight hours, or less
fractal-wallpapers curate run --resume v1                          # carry on where it stopped
fractal-wallpapers curate reject --run v1 --rejector matt_review --date 2026-08-17
```

Eight things here are worth reading before changing anything.

**A run is bound to its ledgers, and nothing defaults to all of them.** `--ledger`
names them; `--harvest` names the run that wrote them and takes its `walk.jsonl`.
`curate run` resolves the binding at its entry, writes it into `run_plan.json`
beside `n` and the seed, and every stage downstream reads it from there — a resume
names no ledger and is bound by its own plan. An invocation that names none with
more than one ledger present **refuses and lists them**. The old default was to
read every `walk.jsonl` under `artifacts/`, which would have ranked one harvest's
17,251 unscored rows into another harvest's intake and printed one funnel over
both populations, with nothing raising and nothing looking wrong.

**Two cuts act; everything else annotates.** `floors` owns every threshold. The
junk floor removes a row at intake, on the location head's scale, saying no more
than *do not spend colorize compute on this*. The **strange head's release bar**
removes one at selection: a strange row below 0.685 is not seated, and a strange
slot with nothing above it goes unfilled.

Both render judges shipped as advisories — computed, written onto every record,
never allowed to drop a candidate — because neither had a measured release gate
and a bar without one is a number nobody can defend. The strange bar is an
exception taken deliberately, by review rather than by measurement: Matt read
`run2` on 2026-08-17, and all eleven released strange rows below the advisory were
bad, the head had been right about every one, and the release path had been
padding strange slots out of thin passing supply. Its *height* is no longer that
verdict: the 4-class retrain moved the head's whole probability scale, so the bar
was restated off the labels — the crossover where the head's own P(>=3) stops
disagreeing with the people who judged 3,085 pictures — and it landed at 0.685
rather than at the advisory it was promoted from. **The smooth head stays
advisory** — its below-advisory rows belong to a mix-ratio decision that has not
been taken. An `Advisory` and a `Bar` are two classes rather than one class with
a flag, so which kind a head has is visible at every call site.

**Nothing is frozen into a row.** Scores are read at the moment they are used, out
of a sidecar this stage owns — upserted per ledger, so scoring one binding
replaces that binding's rows and leaves every other ledger's alone; the walk
ledgers themselves are never rewritten. A
verdict stamped into a ledger on the day it was minted is a verdict the pipeline
must later either believe or delete, and deleting is how a head flip once took an
intake from about fourteen hundred locations to sixteen. Here a flip is a
re-score, and a stale score costs *rank quality* rather than a row.

**The release budgets the colorize, never the other way round.** A judge's attempt
budget is a multiple of the slots it is asked to fill, and when the two cannot
both be afforded they scale down together. Volume that falls out of a spread over
render styles gives the one smooth coloring a sixteenth of the attempts however
many smooth slots the release wanted — a release starved by an allocation rule
that had no opinion about the release.

**Nothing is padded, backfilled or redistributed.** A judge that cannot fill its
quota under the caps ships fewer and says so with the three numbers that make the
shortfall attributable. A slot a thin partition could not use is not handed to a
partition that had plenty: that is the thin-supply rule undone one level up. With
the strange bar acting the same rule has an edge — the allocation is still solved
over the partitions that have a *scored* candidate, not over the ones that have a
passing one, so a partition the bar empties holds its slot and leaves it unfilled
rather than exporting it. Every run reports planned against seated against
unfilled, per head and per partition, with the reason each shortfall bound on.

**A release can be wrong, and taking a row back adds to the record.** `rejection`
stamps a released row with who rejected it, when, and against which bar and
artifact; `verdict` stays `released`, the scores are untouched, nothing is
deleted. `records.served` — released minus rejected — is what every listing,
every check and the sheet read, so a row leaves service everywhere at once. The
sheet keeps it on the page under its own heading, because a review page that
disagreed with its own records would be the one thing a review page may not be.
`curate reject` applies today's acting bars to a run released before they acted,
which is a rule rather than a list, and re-running it rewrites the same bytes.

**Serving order is score rank within the partition, on each head's own scale.**
`records.score_rank` ranks every `(partition, head)` pool separately and then
interleaves the pools by *position*, so no sort ever compares the two judges'
probabilities and every prefix of a listing covers the partitions evenly — the
property the near-miss section needs, because it takes a prefix. The served set
used to come out in candidate order, which is the attempt number, which is
arrival order: a page led with whichever partition the attempt plan interleaved
first. Floors are untouched by this. The junk floor still acts at intake and an
acting release bar still refuses a seat; rank only orders what survived them.

**Where a run's clock goes.** Profiled serially over a real run: the release pass is
the run, and painting is the release pass. A full-resolution row is ~90% engine, and
inside the engine 97% is painting — resampling is 2.6% and process start, PNG encode
and the write together are 0.3%, so encode and file I/O are not worth counting here.
An attempt is 2.49 s, half of it the thirty-two candidate recolors (36.6 ms each, one
engine process apiece, each re-reading the same 3.7 MB field). At the shipped shape
that is roughly 80% release, 17% attempts, and everything else in the noise.

**A run is sized by a clock as well as by `-n`, and the gate is prospective.** At
six pictures the size of a run is `-n`; at sixty it is the wall clock, because one
release row measured between sixteen seconds and three and a half minutes turns
"twenty rows" into an answer between six minutes and an hour. `--wall-budget` is
checked *before* each unit — `elapsed + estimate + margin > budget` and it does not
start — off an estimate formed from this run's own finished units, with a hard kill
deadline covering the first unit of a class, which by construction has no estimate.
Stopping is an outcome: the summary says `budget_stopped`, which is neither
`completed` nor `crashed`, so a short release is attributable to the clock rather
than mistaken for thin supply.

**An interrupted run is continued, not restarted.** `--resume` skips what the run
already finished, off the run's own candidate log and the pictures on disk. Its
plan comes from the sidecar it wrote at entry rather than from the command line, so
a forgotten flag cannot re-plan a run half of whose attempts are recorded; nothing
half-written is trusted; and the seam is checked arithmetically — `planned =
resumed + made + failed + not-started` on both legs, loudly and non-zero when it
does not balance.

The two claims this stage makes that a test cannot settle are settled by commands
against a real plan — `curate parity`, that a concurrently rendered release is
byte-identical to a serial one, and `curate replay`, that every released picture
re-derives from its own record.
