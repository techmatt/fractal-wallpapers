# examples

The four thumbnails the root `README.md` shows at the top. Nothing reads them but that
page.

Each is a seat of the general n=1000 gallery record, rendered through the engine and
scaled to 480x270. They are the only binary files this repository tracks, and
`tests/test_history_purity.py`'s `ALLOWLIST` carries the reason and the bound.

| file | seat | family | mode | colormap |
| --- | --- | --- | --- | --- |
| `mandelbrot_stripe.jpg` | `460117ee` | mandelbrot | `stripe` | cmr.jungle |
| `phoenix_threads.jpg` | `0275fee1` | phoenix | `threads` | Sapphire Against Rose |
| `julia_smooth.jpg` | `2fd9890d` | julia (mandelbrot) | `smooth` | glowdon |
| `julia_multibrot3_threads.jpg` | `5ff0ad6b` | julia (multibrot3) | `threads` | Cobalt Furnace Ultra |

To draw any of them at full size, which is what these were scaled down from:

```
fractal-wallpapers curate solve recipes --write --stamp 20260922T012627Z
fractal-wallpapers render \
  --recipe artifacts/curation/tentative/20260922T012627Z/recipes.jsonl \
  --key <seat> --out artifacts/example.jpg
```

⚠ **Both lines, and the first is not optional on a clone.** These four seats were cut
from `20260914T171846Z`, whose `recipes.jsonl` was the one tracked file of its kind and
which went with every other saved record on 2026-09-21. All four keys are also seats of
`final139_general` above, which is kept and **not** published — so the recipe file is
built out of the candidate ledger on the machine that holds it, and a clone with no
ledger cannot draw these at all. The keys are unchanged; only the stamp that resolves
them is.

Replacing one is two steps and neither is optional: redraw and rescale the picture here,
and repoint the `<img>` in the root README. A file added or renamed also moves the
`ALLOWLIST` entry, which is what makes a fifth picture a decision rather than a copy.
