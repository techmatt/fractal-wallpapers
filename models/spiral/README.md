A linear probe over frozen features: is this location a spiral?

```
manifest.json        which probe reads what picture, at which regime, cut where
neutral_dinov2.json  the shipped probe: standardization, coefficients, intercept
```

Both are tracked text and both are small — a probe is 384 coefficients and the
three vectors that centre them, about 28 KB. `src/fractal_wallpapers/models/spiral_probe.py`
is the only module that opens either.

## This is not a fourth judge, and it is not a fifth head

Nothing here is trained. A probe is one logistic regression fitted on features a
frozen network already produces, asking whether the answer is already in there.
The label side is `data/spiral/` — an **attribute** store, named classes rather
than a 1–4 tier — and the answer exists to be counted into a gallery share cap
rather than maximized.

```
fractal-wallpapers spiral fit --write
fractal-wallpapers spiral read --locations <records.jsonl> --out <probabilities.jsonl>
```

`fit` cuts the store on its own pin, asserts the pin on the training side, chooses
the ridge by 5-fold cross-validation over the 400 and writes the probe and the
manifest. `read` renders each location at the probe's regime, encodes it and
reports the share called `spiral` at 0.3, the probe's own threshold, and 0.7 —
because a cap acts on a share. Both take `--pictures` to draw somewhere other
than the neutral render store.

## A spiral is a property of the PLACE, and the numbers say so

Four frozen readings were fitted on the same 400 verdicts and read once on the
same pinned 100, on 2026-09-03. Only the picture changed:

```text
set                    accuracy  balanced  AUC     what it reads
neutral_dinov2           0.94      0.919   0.987   DINOv2 on the location's neutral render
render_head_pooled       0.88      0.845   0.918   render judge pooled, seated picture
seated_dinov2            0.88      0.831   0.965   DINOv2 on the seated picture
render_head              0.85      0.829   0.892   render judge pre-logits, seated picture
location_head            0.87      0.816   0.899   location head pre-logits, canonical view
location_head_pooled     0.86      0.808   0.876   location head pooled, canonical view
```

The place-side reading beats the picture-side one by **8.8 points of balanced
accuracy** and 17.6 points of recall at 0.5, which is the colour Matt reported
being confused by, priced. It is the only set that clears the ~90% bar, and it is
what ships.

**The location head is not the best reader of its own view**, which is worth
knowing before reaching for it again: it has seen far more spirals than DINOv2
has, and it is ten points of balanced accuracy worse here. It was trained to rank
places by quality, and a spiral is not a quality.

## The regime is half of what a coefficient means

`neutral_dinov2` reads the **neutral render** — `curation/neutral.py`'s frozen
recipe, 448×252 at one sample per pixel, `smooth`/`linear` through
`twilight_shifted` with every palette knob at its default — encoded by DINOv2
ViT-S/14 into 384 unit-norm dimensions. That map is the same one the location
head's canonical view is drawn through, so **"neutral" here does not mean
colour-free**: it means one fixed colouring, held still, that says nothing about
a colouring nobody has chosen yet. The manifest carries the whole recipe and
`neutral.stamp()`'s digest of it; a probe read off a picture drawn any other way
is arithmetic between unrelated numbers.

## What another sitting would buy: nothing

Fitted on 100 / 200 / 300 / 400 of the training side with the ridge re-chosen
inside each subsample and read on the same pinned 100, the probe reads 0.919 /
0.919 / 0.904 / 0.919 balanced accuracy. It is saturated at a hundred labels.
More verdicts is not what moves this number; the five pinned misses are all
places a person calls a spiral at a glance, so what is left is the encoder's
notion of one rather than the corpus's size.
