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
A PASS would say the student chooses what the teacher would choose. It would say
nothing at all about whether either of them chooses what a person would: if the
teacher has a taste nobody shares, this head has inherited it exactly.

## What the read said, and why nothing is in the manifest

**FAIL, on one arm of three, and the head is not shipped.** It reproduces the
teacher's *ordering* of a real candidate set at a rank correlation of **0.894**
against a bar of 0.70, and the utility its choices give up is **6.6%** of a set's
own spread against a ceiling of 10%. But it picks the teacher's exact top map on
**46.1%** of the 180 real sets, against an absolute floor of 50% and a renderer
control of 58.3% — and the top pick is what a colorize actually does with it.

Both numbers were improved by enlarging the corpus rather than by moving the bar:
a first corpus of 600 sets of 8 read 0.383, and 800 sets of 20 read 0.461. The
gap that remains is not obviously one more corpus wide. A production candidate set
is up to 32 maps of one palette flavour whose top two sit a twentieth of the set's
spread apart, and this head's median disagreement is with the teacher's
second-favourite.

The half-precision artifact is built and verified — 10.15 MB to 5.13, bit-identical
on re-read, one of 180 sets changing its top pick and at most four discordant
candidate pairs in any set — so the shipping path is proven for this head. What is
withheld is the manifest entry, because a head that failed its own pre-registered
bar does not go into a release.
