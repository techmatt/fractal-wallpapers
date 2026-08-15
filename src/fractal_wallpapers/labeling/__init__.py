"""Collecting human taste: the label store, the split it ships, and the rig.

The store is four records and one rule each:

```text
data/labels/batches.jsonl     what generated a batch, registered before its rows exist
data/labels/rows/<batch>.jsonl  the labels themselves, append-only, one row per unit
data/labels/eval_split.jsonl  the locations pinned to the evaluation side, forever
data/labels/split.json        the recipe that drew that pin, and what it realized
```

Nothing outside [`fractal_wallpapers.labeling.store`] opens any of them.
"""
