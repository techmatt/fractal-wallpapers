"""The judges: what they are trained on, how they are trained, and what ships.

One vertical per head. The location head — the only one built so far — reads a
picture of a viewport and says how good the place is, on the same one-to-four
scale a human labels on.

```text
roster      which heads exist, in the one module a base install can import
tiles       the label store → a plan → the pictures the head is trained on
head        the ordinal head itself: backbone, loss, and the deploy transform
dataset     locations → tensors: which tile a training example draws, and how
            often each location is drawn at all
train       the loop, what it selects on, and the record it writes
scoring     a trained head over a population → one row of probabilities each
acceptance  the bar, pre-registered, and the read against it
ship        fp16, a hash, and the manifest entry a fresh clone fetches from
```

Below `roster`, which is a list of names rather than a stage, the order is the
order they run in — and each stage writes a record the next one reads rather
than being called from inside it, so a training run can be re-scored, and a
score can be re-judged, without any of it happening again.
"""
