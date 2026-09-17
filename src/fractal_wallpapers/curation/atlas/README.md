# The atlas record

`fractal-wallpapers curate atlas` puts every place the search kept on a plate of the plane
it sits in, thinned to one dot per neighbourhood, and gives each dot three pictures. It
writes a working directory, and **the website is its only consumer**: `fractal-website`'s
`python -m builder atlas --ingest <dir>/dots.json` turns it into the committed
`atlas/atlas.jsonl`, `atlas/<plane>.jsonl` and the re-encoded pictures the atlas page
ships. That module (`builder/atlas.py`) is the contract; this directory writes to it.

```
fractal-wallpapers curate atlas                     # the mandelbrot plane, the newest published record
fractal-wallpapers curate atlas --record <stamp> --radius 12 --out artifacts/atlas/mandelbrot
fractal-wallpapers curate atlas --no-pictures       # dots.json only, for checking a thinning
```

About two minutes: ~30 s reading the stores, ~7 s for the plate, ~85 s for the thumbnails
at three workers. **It holds the candidate pool while it reads**, so it never runs beside a
solve, a growth pass or the slow lane.

## What lands in `artifacts/atlas/<plane>/`

Untracked, like the rest of `artifacts/`, and regenerable from the stores and the named
record.

| file | what it is |
| --- | --- |
| `dots.json` | the record: method fields, the tally, and one entry per dot |
| `dots_summary.json` | the tally again, with the tone counts and what the pictures cost |
| `base.jpg`, `base.json` | the plate, 4096x2304 `smooth` through `atlas_grey`, and the engine's report of it |
| `thumbs/<id>_<slot>.jpg` | 400x225 at supersample 2, three per dot |
| `thumbs.json` | how the thumbnail leg went |

The names are the ones the ingest reads, which is why the plate is still called `base`.

## What a dot is

**The population is one bar**: a place is on the plate if at least one of its rows reads at
or above `solve.DEFAULT_FINE_BAR`. **The priority is the record's**: seated places are
queued first, then everything else by best `p_fine`. **The thinning is greedy**: a place
inside `--radius` plate pixels of a dot already standing is dropped and counted against it,
whichever kind either is. A `julia:mandelbrot` place is its `c`, which is a point of the
same plane, so both kinds share one plate and a dot is one place of one kind.
`population.py` carries the argument.

Every dot carries its plane coordinates (`place.x`, `place.y`) beside its plate pixels, so
the website can re-crop a plate and re-project the dots without re-thinning anything. Every
slot carries its own `viewport` and `family`, so nothing downstream derives a frame.

## The three slots, and the gallery's tone

`mandelbrot` and `julia` are views of the place, drawn plain through the location head's
canonical map. `gallery` is the seat if the place holds one, else its best row by
`p_fine`. `slots.py` has the table.

The gallery slot also carries what the tone operator did to that row, read through
`curation.stamps.for_rows`: `tone` is `curved`, `clean` or `lost` (the website's own
words); `level` is the permalink's `level` value where the run recorded the curve —
`band_autolevel/v1:<black>,<white>,<exponent>,<out0>,<out1>`, numbers as JavaScript spells
them — and `null` otherwise; `gap` says what is missing when the tone is `lost`, and `from`
names the `<store>/<run>` that was asked, and a backfilled curve is found through the same
door (`curate autolevel backfill`'s sidecar is the overlay `for_rows` prefers). **The atlas
never re-measures a curve itself**: a seat with none on any record is `lost` and says so,
and the fix is a backfill followed by a re-run, not a change here. `rotation` runs recorded
no curve until 2026-09-16 and were most of the `lost` seats before their backfill.

**An unseated dot is not a record's seat**, so `--record` cannot reach the best row it
stands behind. `curate autolevel backfill --atlas <plane>` sweeps every gallery slot this
directory's `dots.json` names — `survey --atlas <plane>` counts them first, no renders — and
a re-run of `curate atlas` then reads the curves. Run the atlas first: the population is the
record it wrote, not a re-thinning. The mandelbrot plane read 0 `lost` after it on
2026-09-16.

`refused` lists what a link cannot carry, in the short forms the website's contract test
checks: `colormap <name>`, `mirror on a cyclic map`, `curve <name>`, and
`autolevel band_autolevel/v1` for a `lost` tone.

## The five planes

`PLANES` in `__init__.py` is the table: a family for the plate and the ledger partitions
whose places land on it, named as the website's `builder/atlas.py` names its partitions.

| `--plane` | plate family | partitions | a dot's `kind` |
| --- | --- | --- | --- |
| `mandelbrot` | `mandelbrot`, degree 2 | `mandelbrot`, `julia:mandelbrot` | `mandelbrot` / `julia` |
| `multibrot3`, `4`, `5` | `multibrot` at that degree | `multibrotN`, `julia:multibrotN` | `mandelbrot` / `julia` |
| `phoenix` | the classic slice, `partitions.CLASSIC_PHOENIX_POINT` | `phoenix:classic` | `julia` |

A multibrot plane is the Mandelbrot plane at another degree, and its Julia slots are drawn
at that degree. **`phoenix` is the classic slice only**: its parameters are pinned, so a
place is a frame on the slice itself — the whole location key, as a parameter-plane place
is — and its `kind` is `julia` because the frame is on a `z` plane, which is how the
website's `PLANE_OF_FAMILY` reads a phoenix family. Its first slot is a neighbourhood plate
of the slice around the frame, as a Julia place's is of its parameter plane. **Varied
phoenix is on no plate**: every place is a different point of a six-dimensional space, so
there is no one plane to draw it on, and `population.position` answers `None` for it.

Every plane uses the same `--radius 12` and the same `PLATE_FRACTION`, so a plate pixel is
the plane's home-view width over 4096 and the neighbourhood plate is 0.05 of that width.

```
fractal-wallpapers curate atlas --plane multibrot3
fractal-wallpapers curate autolevel survey --atlas multibrot3
fractal-wallpapers curate autolevel backfill --atlas multibrot3
fractal-wallpapers curate atlas --plane multibrot3   # the re-run that reads the curves
```
