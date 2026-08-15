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
After that the shape is the same: `palette_train` runs the loop over sets rather
than pictures, `palette_scoring` reads a checkpoint, `palette_acceptance` judges
it against its own pre-registered bar. Its model, transform and loss are in
`palette_head`, separately from `head`, because its answer is a choice inside a
set and not a tier on an ordinal scale — but it ships through the same `ship`,
supplying only its own agreement statistic.

Each stage writes a record the next one reads rather than being called from
inside it, so a training run can be re-scored and a score can be re-judged
without any of it happening again.

Everything here needs `pip install -e ".[models]"` — torch and timm are not in
the base install, because rendering fractals, walking the plane, running the
supply engine and collecting labels all work without them.
