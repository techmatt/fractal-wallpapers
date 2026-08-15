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

Each stage writes a record the next one reads rather than being called from
inside it, so a training run can be re-scored and a score can be re-judged
without any of it happening again. Three heads exist so far; the palette head
does not.

Everything here needs `pip install -e ".[models]"` — torch and timm are not in
the base install, because rendering fractals, walking the plane, running the
supply engine and collecting labels all work without them.
