The head that judges candidate viewport locations, before any color is applied.

An ordinal head over the same one-to-four scale a human labels on, emitting a
probability at each of the three cutpoints: `P(≥2)` not bad, `P(≥3)` a wallpaper,
`P(≥4)` worth releasing. The supply engine reads the last of those directly.

Tracked here: `prereg.json`, the bar, written before the head existed;
`config.json` and `metrics.json`, the recipe and the run; `scores.jsonl`, the
head's read of every location on the evaluation side, each row carrying its own
join; `acceptance.json`, what the bar says about those scores.

Tracked here as well, for the study that asks whether that read means the same
thing at another rendering regime: `regime_prereg.json`, a second bar written
before its candidate existed, and `regime_acceptance.json`, what it says about a
three-seed band trained over all three cached regimes at once. Those runs keep
their own directories — `seed<N>_all_regimes` — each holding a `scores.jsonl` at
the canonical regime and a `scores_<w>x<h>ss<n>.jsonl` for every other one. The
incumbent's three runs carry the same per-regime files, because a paired
comparison needs both heads read on the same rows at the same geometries.

`candidate.json` describes `location.candidate.fp16.pt`: a staged candidate,
verified exactly the way a shipment is and **absent from `models/weights.json`**
on purpose. Nothing resolves it. Adopting a location head moves the score scale
every floor in the supply engine is calibrated against, so the file sits beside
the shipped head until that is decided and priced.

The weights themselves are not tracked. `head_best.pt` and `head_last.pt` are
what training leaves on disk in full precision; `location.fp16.pt` is the halved
artifact `fractal-wallpapers fetch-weights` downloads and hash-checks.
