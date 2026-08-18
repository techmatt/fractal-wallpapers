The head that judges a finished render in one of the strange colourings.

Fifteen colourings beside `smooth` — engraved banding, orbit traps, stripe and
curvature averages, and the composites that screen one over the other — and they
fail differently from a smooth render. A trap mode that catches nothing is a
black frame; one that catches everything is white lace on white. So this is its
own judge over its own corpus, on the mode-and-palette axis rather than the
location one.

An ordinal head over a **four**-tier scale: 1 does not work, 2 has structure but
is unremarkable, 3 is a rendering worth keeping, 4 is exceptional. It trained on
three for its first generation, because the corpus had been collected on three
and there was no fourth to read; the store carried the wider scale throughout and
the head widened to meet it once the labels held 4s.

Tracked here: `prereg.json`, the bar, written and committed before the head
existed; `yardstick.json`, the source project's own committed reading of the same
blind sheet, copied in so the bar stays re-readable without that repository;
`config.json` and `metrics.json`, the recipe and the run; `scores.jsonl`, the
head's read of the blind sheet with each row carrying its whole join;
`acceptance.json`, what the bar says about those scores.

Its evaluation side is one sheet of 150 pictures over 110 places —
`blind_modes`, the only labels in this corpus that no head suggested — read at
`≥2`, the boundary that sheet was drawn to inform. Six of its rows sit at `≥3`,
so `≥3` is reported on it and decides nothing; four of those six were revised up
to 4 on an anchored pass, which leaves `≥4` with four positives and no claim
worth making at all.

Two generations live here side by side. The **3-class baseline** is the head's own
run at the root, with `seed1` and `seed2` as its band; the **4-class candidate**
is `four_class_seed0`, `four_class_seed1` and `four_class_seed2`, and the staged
artifact is the median of that band by its own overall score. A superseded run's
records are left exactly as they were — a config says what *that* run trained
under and is never re-read against a later recipe.

The weights themselves are not tracked. `best.pt` and `last.pt` are what training
leaves on disk in full precision; `strange_render.fp16.pt` is the halved artifact
`fractal-wallpapers fetch-weights` downloads and hash-checks.
