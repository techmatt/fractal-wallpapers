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

`flip_prereg.json` and `flip_acceptance.json` are the **second** bar of that same
study, on a different population. The first is read on the evaluation split,
where 78% of rows read below `P(≥3) = 0.05` at every geometry and agree
trivially; this one re-asks the question on production stock — a seeded draw over
the curation sidecar, stratified over partition × the incumbent's own canonical
score band, with every location this store holds excluded — and counts decision
flips at the junk floor, the good floor and the great cut rather than a rank
correlation. Its draw and its reads are re-derivable and live under
`artifacts/regime_flips/`.

`candidate.json` describes what was staged as `location.candidate.fp16.pt` and
now records that it was **adopted**. A staged candidate is verified exactly the
way a shipment is and is absent from `models/weights.json` on purpose, because
adopting a location head moves the score scale every floor in the supply engine
is calibrated against — so it sits beside the shipped head until that is decided
and priced.

`restatement.json` and `adoption.json` are that decision, and they are the two
records of the 2026-08-20 flip. **What serves now is `seed0_all_regimes`**, sha
`f8f80511…`, under `weights-v2`.

`restatement.json` is a measurement and it could only be taken once, before the
artifact moved: every acting cut on this head's scale, restated as the candidate
score passing the **same fraction of a fixed reference pool** — the whole 28,072-
location curation sidecar — as the retired head's cut passed. Junk floor 0.20 →
0.100, good floor 0.50 → 0.385, great cut 0.50 → 0.105. The old heights survive
in it as the prior, and nowhere else: after the sidecar was re-scored there are
no retired-head reads left to match against. It holds **volume** and not rows —
13.5%, 14.6% and 9.9% of the pool changes side at the three cuts — and it is not
a calibration: no label was read, and where a keeper starts on the new scale is
the question it was before.

`adoption.json` records the flip itself: which sha retired, which serves, under
what tag, and each cut's restated height beside the share it holds. It also
carries both pre-registered reads *with their verdicts*, because they did not
agree — the split bar reads FAIL and the stock bar reads PASS — and a record that
listed two paths would read as "passed both".

**One validity line.** The offer-body rank validation that retired curation's
never-rank-the-mandelbrot-offer rule — ρ = 0.582 over the body, serve-top-down —
measured the **incumbent's** ranks, through `4b60deb9…`. The candidate's
rank-within-offer quality is unmeasured. Re-measure it only when a decision needs
it.

The weights themselves are not tracked. `head_best.pt` and `head_last.pt` are
what training leaves on disk in full precision; `location.fp16.pt` is the halved
artifact `fractal-wallpapers fetch-weights` downloads and hash-checks. A flip
**copies** the candidate's bytes onto that name rather than re-casting the
checkpoint: a `torch` archive carries its own file name inside itself, and
`torch.save` is not byte-reproducible run to run, so a re-cast is a file no bar
has read. The corollary is that the retired artifact's hash cannot be rebuilt
from `seed0/head_best.pt` — its bytes are the asset published under `weights-v1`,
and its manifest row lives in git history.
