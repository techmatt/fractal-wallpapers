The four judges as code: their architectures, training loops, and inference paths.

One vertical per head, in the order it runs. For the **location** head, which
judges a place before any colour is applied: `tiles` builds the pictures,
`head` and `dataset` say what a training example is, `train` runs the loop,
`scoring` reads a checkpoint over a population, `acceptance` judges the result
against a bar written down beforehand.

For the two **finished-render** judges, which answer the question after it —
does this particular colouring of a place work — the same five stages exist
under their own names: `renders` regenerates every judged picture from the recipe
its row carries, `finished_train` runs the loop over pictures rather than places,
`finished_scoring` reads a checkpoint, `finished_acceptance` judges it against its
own pre-registered bar. They share `head` (the ordinal model, the CORN loss and
the reading of its cutpoints as unconditional probabilities), `metrics`, and
`ship` — the fp16 cast, the re-read, the agreement check and the hash are the
same for every head, so they are written once and a four-field record says where
each head's pieces are.

The fourth, the **palette** head, is the one that is not trained from human
labels — there are none here to train it on — so it has two stages the others do
not. `palette_sets` vendors the real candidate sets a production colorize run put
in front of the head it is distilled from; `palette_corpus` generates a corpus by
rendering candidates here and asking that teacher (`palette_teacher`) about each.
Most of that corpus is made *hard on purpose* — a set is a map and its nearest
neighbours in `palettes/space`, so it asks the near-tie question a production
flavour asks instead of waiting for a uniform draw to ask it by accident.
After that the shape is the same: `palette_train` runs the loop over sets rather
than pictures, `palette_scoring` reads a checkpoint, `palette_acceptance` judges
it against its own pre-registered bar. Its model, transform and loss are in
`palette_head`, separately from `head`, because its answer is a choice inside a
set and not a tier on an ordinal scale — but it ships through the same `ship`,
supplying only its own agreement statistic.

## Two picture caches, and only one of them is addressed by its recipe

The **finished-render** cache (`renders`) and the location head's **deploy view**
(`location_view`) both name a file by `renders.job_name` — a sha256 of the whole
engine spec. Resolution and supersample are fields of that spec, so a view
rendered at another geometry gets its own file and three regimes can share one
directory without colliding.

The **tile** cache does not work that way. A tile is
`<out_root>/<location_id>/t<NN>_<palette>_s<scale>_sh<shift>_<level>_q<q>.jpg`,
and neither `recipe.tile` nor `recipe.field_supersample` appears anywhere in it.
Two builds that differ only in geometry write **the same names**, and because the
build skips a location whose tiles are all present, the second one renders
nothing, reports success, and records the geometry it did not use. The manifest
row does carry `field.supersample` and `tile_size` — the regime is *recorded*,
it is simply not *addressed*.

So a tile corpus at a second geometry is not a build step. It needs the identity
to carry the geometry, or an `out_root`, `manifest` and build record per regime —
a decision, not a flag.

## Budgeting a tile build

Cost tracks what the pixels do, not how many rows there are. Measured on the
2026-08-19 top-up, per location, all 32 tiles, one field pass:

| label | s/location |
|---|---|
| 1 | 23.4 |
| 2 | 2.2 |
| 3 | 1.8 |
| 4 | 0.6 |

Nearly all of it is the field, not the tiles: a location labelled 1 is usually
interior-heavy and every interior sample iterates to the cap. Estimate a build
from a **stratified** pilot — the corpus-wide mean rate under-projected this
top-up by 4.2×.

Each stage writes a record the next one reads rather than being called from
inside it, so a training run can be re-scored and a score can be re-judged
without any of it happening again.

Everything here needs `pip install -e ".[models]"` — torch and timm are not in
the base install, because rendering fractals, walking the plane, running the
supply engine and collecting labels all work without them.

One exception, and it is the reason the exception is written down: `roster` is
the tuple of head names and nothing else, stdlib-only on purpose, because
`fetch-weights --check` runs on the base install and has to know which heads a
complete release carries. `ship` imports the roster from there. Any other module
here that a base install can import is an accident, not a second exception.
