The four judges as code: their architectures, training loops, and inference paths.

One vertical per head, in the order it runs: `tiles` builds the pictures, `head`
and `dataset` say what a training example is, `train` runs the loop, `scoring`
reads a checkpoint over a population, `acceptance` judges the result against a
bar written down beforehand, and `ship` stages the artifact a fresh clone fetches.

Each stage writes a record the next one reads rather than being called from
inside it, so a training run can be re-scored and a score can be re-judged
without any of it happening again. Only the location head exists so far.

Everything here needs `pip install -e ".[models]"` — torch and timm are not in
the base install, because rendering fractals, walking the plane, running the
supply engine and collecting labels all work without them.
