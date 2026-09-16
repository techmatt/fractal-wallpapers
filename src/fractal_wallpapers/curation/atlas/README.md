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

`refused` lists what a link cannot carry, in the short forms the website's contract test
checks: `colormap <name>`, `mirror on a cyclic map`, `curve <name>`, and
`autolevel band_autolevel/v1` for a `lost` tone.

## Adding a plane

`PLANES` in `__init__.py` is the table: a family for the plate and the ledger partitions
whose places land on it. The multibrot and phoenix planes are a row each, with the engine's
own home view for the plate; they join when the search has kept places on them.
