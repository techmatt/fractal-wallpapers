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
leaves on disk in full precision; `smooth_render.fp16.pt` is the halved artifact
`fractal-wallpapers fetch-weights` downloads and hash-checks.

## The adoption

**Shipped on Matt's call**, alongside the palette head and in the same shape: a
recorded policy call over a FAIL arm, with the bar record untouched. The
ordering arm this sheet was bought to read PASSes at **0.6306** against a target
of 0.5671 and a floor of 0.5121, and the interface arm PASSes. What fails is
**calibration**, on an arm this repository's own bar made unsatisfiable: sheet
D's `≥4` base rate is 0.4873 against the training distribution's 0.1233, an
enrichment of 3.95×, and clearing the arm would require the head to be
systematically over-confident about everything it trained on. All three seeds
agree — 0.415 / 0.448 / 0.333 — so it is a fact about the bar, not about the
seed.

The bar is not rewritten after the fact and the arm still reads FAIL. Withholding
the head instead would have shipped a release that cannot judge a smooth render
at all, which is the larger of the two wrongs; the arm stays on the record so
that a later reader sees the trade rather than a PASS.
