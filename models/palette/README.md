The head that ranks palette choices for a given location.

```
prereg.json            the bar, written before the head existed
acceptance.json        the read against it, per seed
seed*_listwise/        the seed band that was judged: config, metrics, scores/
seed0_regression/      the losing arm of the loss, kept because it was an arm
palette.fp16.pt        what ships. Fetched, not tracked
```

Each seed's `scores/` is a tree — `<source_batch>/<partition>.jsonl` — and not one
file. A score row carries two whole score vectors and the candidate list they are
aligned to, so 377 sets read 999 KiB against the repository's 1 MiB size guard on
every seed. The batch is the axis the corpus grows on and the partition is the
axis its rows already arrive in blocks of; split on both, the largest file is
425 KiB and a new labeling batch adds a directory rather than lengthening one.
`palette_scoring.read()` is the reader over the whole tree and hands the rows back
in `set` order, which is the order the single file had.

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

## What the read said, and what shipped anyway

**FAIL, on one arm of four, and it is in the manifest on Matt's call.** It reproduces the
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
discordant candidate pairs in any set.

## The adoption

**Shipped on Matt's call, 2026-08-15**, as `seed2_listwise` — the median seed by
the top-pick arm, which is the rule this head's bar declared before it existed
and not the best of the three. The bar record is untouched: no arm was moved, no
threshold rewritten, and `acceptance.json` still reads FAIL. What changed is the
decision taken over that FAIL, which is recorded here rather than hidden in the
number.

The three operative arms all PASS — floor **0.533** against 0.50, ordering
**0.907** against 0.70, regret **0.055** against 0.10 — and the fourth is
re-read for what it is. The renderer control at **0.592** is a **ceiling
reference**, not a bar: it is the teacher's self-agreement across two rendering
pipelines, so it measures how far a change of renderer already moves the
teacher's own choice, and the remaining **0.059** gap to it is smaller than the
**0.056** seed band. A head cannot be asked to track its teacher more closely
than the teacher tracks itself, and this instrument cannot resolve whether it
does.

Two caveats travel with the adoption and are not softened by it. **The misses
are rarer but deeper**: on the original 180 sets the median rank this head gives
the teacher's pick when it misses is now **4**, mode 2, where the first pass's
median miss was the teacher's second favourite. And **the listwise-vs-regression
choice was decided inside seed noise** — listwise won its declared read by 0.0325
held-out top pick, the three listwise seeds span 0.0450, and on the real sets the
kept regression arm reads 0.5305 against the listwise band's 0.483/0.533/0.539.
The two arms are indistinguishable on the instrument; the rule was declared in
advance and stands, but it did not resolve anything.
