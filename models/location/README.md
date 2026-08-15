The head that judges candidate viewport locations, before any color is applied.

An ordinal head over the same one-to-four scale a human labels on, emitting a
probability at each of the three cutpoints: `P(≥2)` not bad, `P(≥3)` a wallpaper,
`P(≥4)` worth releasing. The supply engine reads the last of those directly.

Tracked here: `prereg.json`, the bar, written before the head existed;
`config.json` and `metrics.json`, the recipe and the run; `scores.jsonl`, the
head's read of every location on the evaluation side, each row carrying its own
join; `acceptance.json`, what the bar says about those scores.

The weights themselves are not tracked. `head_best.pt` and `head_last.pt` are
what training leaves on disk in full precision; `head.fp16.pt` is the halved
artifact `fractal-wallpapers fetch-weights` downloads and hash-checks.
