The head that ranks palette choices for a given location.

```
prereg.json            the bar, written before the head existed
acceptance.json        the read against it, per seed
seed*_listwise/        the seed band that was judged: config, metrics, scores
seed0_regression/      the losing arm of the loss, kept because it was an arm
palette.fp16.pt        what would ship. Fetched, not tracked
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
nothing beyond it. It is read on 377 real candidate sets that two production
colorize runs recorded — both student and teacher scored on the same pictures, so
what is compared is two functions rather than two rendering pipelines — and the
bar it must clear is calibrated on how far the teacher already disagrees with its
own recorded choices when the picture is made by this engine instead of that one.
A PASS would say the student chooses what the teacher would choose. It would say
nothing at all about whether either of them chooses what a person would: if the
teacher has a taste nobody shares, this head has inherited it exactly.

## What the read said, and why nothing is in the manifest

**FAIL, on one arm of four, and the head is not shipped.** It reproduces the
teacher's *ordering* of a real candidate set at a rank correlation of **0.907**
against a bar of 0.70, and the utility its choices give up is **5.5%** of a set's
own spread against a ceiling of 10%. It picks the teacher's exact top map on
**53.3%** of the 377 real sets — which clears the absolute floor of 50% that the
last two attempts did not — but the renderer control is **59.2%**, and the control
is the bar that binds.

Two passes of corpus work moved that number and neither moved the bar: 600 sets of
8 read 0.383, 800 sets of 20 read 0.461, and 2,000 sets of 32 — 70% of them
palette-space neighbourhoods, built to be the near-ties a production flavour is —
read 0.533. The remaining gap is **0.06**, against a seed band 0.056 wide.

Split by how decidable a set is, the shape of what is left is legible: where the
teacher's own win is *narrow* the control is 0.468 and this head reads 0.457, so
on the half that resembles a real colorize decision it now tracks the control.
Where the win is *clear* the control is 0.714 and it reads 0.608. The head has
stopped losing the hard half and is losing the easy one.

The half-precision artifact is built and verified — 10.15 MB to 5.13,
bit-identical on re-read, 2 of 377 sets changing their top pick and at most three
discordant candidate pairs in any set — so the shipping path is proven. What is
withheld is the manifest entry, because a head that failed its own pre-registered
bar does not go into a release.
