Judging finished renders: what to colour, how to colour it, what to keep, and
what to make at full size.

This is the last stage. Everything upstream produces *supply* — places a walk
found, judges trained on human verdicts, a palette head that ranks colour choices.
Curation spends it: it turns the union of every walk into a small set of finished
wallpapers and a durable account of why those and not the others.

```
floors     every number that removes a picture, in one file
intake     the ranked offer, best first per partition
budget     how many pictures to make, and for which judge
colorize   a candidate set of maps, the head's pick, a render, a verdict
selection  top-N per judge, under the slot, supply and look caps
release    the selected rows again at full size, workers rendering
pacing     the wall clock: what may still start, and what is killed
records    what the run decided, and out of what population
sheet      the same thing laid out for a person to disagree with
checks     the two claims only a re-render can settle
run        the wiring, and nothing else
```

```
fractal-wallpapers curate score           # read the ledgers through the location head
fractal-wallpapers curate plan -n 6       # the offer and the budget, making nothing
fractal-wallpapers curate run --run v1 -n 6
fractal-wallpapers curate run --run v1 -n 60 --wall-budget 28800   # eight hours, or less
fractal-wallpapers curate run --resume v1                          # carry on where it stopped
```

Six things here are worth reading before changing anything.

**One cut acts, and everything else annotates.** `floors` owns every threshold,
and only the junk floor removes a row — at intake, on the location head's scale,
saying no more than *do not spend colorize compute on this*. The finished-render
judges' cuts are advisories: computed, written onto every record, never allowed to
drop a candidate. That is not caution, it is a measurement gap being honest — this
project has never measured a release gate for either render judge, so a bar here
would be a number nobody could defend. The advisories keep the question
answerable off the accumulating record instead of only off runs made while a bar
was enforcing.

**Nothing is frozen into a row.** Scores are read at the moment they are used, out
of a sidecar this stage owns; the walk ledgers themselves are never rewritten. A
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
partition that had plenty: that is the thin-supply rule undone one level up.

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
