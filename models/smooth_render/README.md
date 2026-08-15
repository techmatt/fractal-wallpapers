The head that judges a finished smooth-mode render — the picture, not the place.

The location head answers *is this worth rendering*. This one answers the
question after it: **does this particular colouring of it work as a wallpaper**.
One place appears in its corpus a dozen times at a dozen recipes and the verdicts
genuinely differ, so its training unit is a picture rather than a place.

An ordinal head over the same one-to-four scale a human labels on, emitting a
probability at each of the three cutpoints: `P(≥2)` not bad, `P(≥3)` a genuine
wallpaper and the floor a picture ships at, `P(≥4)` the best of those.

Tracked here: `prereg.json`, the bar, written and committed before the head
existed; `yardstick.json`, the source project's own committed reading of the same
blind sheet, copied in so the bar stays re-readable without that repository;
`config.json` and `metrics.json`, the recipe and the run; `scores.jsonl`, the
head's read of the blind sheet with each row carrying its whole join;
`acceptance.json`, what the bar says about those scores.

Its evaluation side is one sheet of 197 pictures — `blind_minibrot`, the only
labels in this corpus that no head suggested — read at `≥4`, which is the one
boundary that sheet was drawn to inform and the one production turns on. It holds
six rows below tier 3, so nothing else on it is measurable.

The weights themselves are not tracked. `best.pt` and `last.pt` are what training
leaves on disk in full precision; `head.fp16.pt` is the halved artifact
`fractal-wallpapers fetch-weights` downloads and hash-checks.
