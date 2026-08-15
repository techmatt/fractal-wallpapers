The head that judges a finished render in one of the strange colourings.

Fifteen colourings beside `smooth` — engraved banding, orbit traps, stripe and
curvature averages, and the composites that screen one over the other — and they
fail differently from a smooth render. A trap mode that catches nothing is a
black frame; one that catches everything is white lace on white. So this is its
own judge over its own corpus, on the mode-and-palette axis rather than the
location one.

An ordinal head over a **three**-tier scale: 1 does not work, 2 has structure but
is unremarkable, 3 is a rendering worth keeping. Three, not four, because the
corpus was collected on three and there is no fourth to read — the ceiling is a
fact about the labels and lives on the store.

Tracked here: `prereg.json`, the bar, written and committed before the head
existed; `yardstick.json`, the source project's own committed reading of the same
blind sheet, copied in so the bar stays re-readable without that repository;
`config.json` and `metrics.json`, the recipe and the run; `scores.jsonl`, the
head's read of the blind sheet with each row carrying its whole join;
`acceptance.json`, what the bar says about those scores.

Its evaluation side is one sheet of 150 pictures over 110 places —
`blind_modes`, the only labels in this corpus that no head suggested — read at
`≥2`, the boundary that sheet was drawn to inform. It holds six rows at tier 3,
so `≥3` is reported on it and decides nothing.

The weights themselves are not tracked. `best.pt` and `last.pt` are what training
leaves on disk in full precision; `head.fp16.pt` is the halved artifact
`fractal-wallpapers fetch-weights` downloads and hash-checks.
