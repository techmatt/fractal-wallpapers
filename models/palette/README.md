The head that ranks palette choices for a given location.

```
prereg.json       the bar, written before the head existed
acceptance.json   the read against it, per seed
seed*/            one training run each: config, metrics, scores
palette.fp16.pt   what ships. Fetched, not tracked
```

## What it is

A single tower that reads one finished picture and emits one scalar utility. Its
answer is never that number on its own: a location arrives with a list of
candidate maps, every candidate is rendered and scored, and the highest one is
what the picture is coloured with. Only the *differences* inside a set mean
anything, which is why the loss that trains it removes each set's own mean before
comparing.

## Where it came from, and what that does and does not establish

**It is distilled, not trained on human labels.** There is no palette-preference
corpus in this repository — the verdicts that taught this ability live in the
source project and did not come across — so the teacher is that project's own
pretrained head, resolved through its single-source pointer, and the student is
trained to reproduce the teacher's whole score vector on pictures made *here*.
The corpus of the teacher's answers is committed under `data/palette_choice/`, so
this head is regenerable from this repository forever: a checkpoint is a fact
about one run, and the corpus is what the run can be done again from.

The claim this head makes is **approximate equivalence with its teacher**, and
nothing beyond it. It is read on 180 real candidate sets a production colorize
run recorded — both student and teacher scored on the same pictures, so what is
compared is two functions rather than two rendering pipelines — and the bar it
must clear is calibrated on how far the teacher already disagrees with its own
recorded choices when the picture is made by this engine instead of that one.
A PASS says the student chooses what the teacher would choose. It says nothing at
all about whether either of them chooses what a person would: if the teacher has
a taste nobody shares, this head has inherited it exactly.
