The four judges as code: their architectures, training loops, and inference paths.

One vertical per head. Each stage writes a record the next reads rather than calling
it, so a run can be re-scored and a score re-judged without redoing what came before.

- **location** judges a place before any colour: `tiles` builds pictures, `head` and
  `dataset` define an example, `train` runs the loop, `scoring` reads a checkpoint,
  `acceptance` judges against a pre-registered bar. `location_scoring` reads the
  shipped head over a named list of places (`score-locations`).
- **render** judges one colouring of a place: `renders` regenerates every judged
  picture from its row's recipe, `finished_train` / `render_train` train,
  `finished_scoring` reads, `finished_acceptance` / `render_acceptance` judge. Kinds,
  floors and bands: `models/render/README.md`.
- **palette** is distilled from a teacher: `palette_sets` vendors real candidate sets,
  `palette_corpus` asks `palette_teacher` about rendered candidates, mostly near-tie
  sets (a map and its neighbours in `palettes/space`); then `palette_train`,
  `palette_scoring`, `palette_acceptance`, with its model and loss in `palette_head`.
- **gallery_grade** orders the render judge's flat top: `gallery_grade_train`;
  `models/gallery_grade/README.md`.

Shared: `head` (ordinal model, CORN loss), `metrics`, `ship` (fp16 cast, re-read,
agreement, hash). `adoption` restates the cuts a new location head moves, then flips.
Not judges: `embedding` (frozen DINOv2 ViT-S/14 via timm, one 384-d unit vector per
location for `curation.embeddings`, from `curation.neutral`'s 448x252 picture: 14-pixel
patches, so the frame goes in whole) and `spiral_probe` (the location-attribute store,
for `curation.spiral_scores`; see
[the labeling rig](../labeling/README.md#the-third-kind-of-sheet-a-location-attribute)).
Around a render retrain: `render_folds`, `render_grade` (adopted nothing),
`render_dose`, `render_deploy`, `render_glance`, `release_floor`; for location,
`regime_acceptance` and `regime_flips`. ⚠ `render_dose` imports its fitting machinery
from `render_grade`, so retiring the grade band takes it along.

```
fractal-wallpapers tiles build                         # or `renders build`, per head
fractal-wallpapers head preregister                    # the bar, first
fractal-wallpapers head train --run seed0_all_regimes --seed 0
fractal-wallpapers head score --run seed0_all_regimes
fractal-wallpapers head accept                         # the band, against the bar
fractal-wallpapers head ship
fractal-wallpapers score-locations --manifest rows.jsonl --out scores.jsonl
```

## Rules every head here follows

- **A score row says what produced it**: `location_scoring` rows carry the shipped
  artifact's sha256 and the regime, the two facts a `cuts.Restatement` pins.
- **Score files hold UNCONDITIONAL `P(≥k)`**: `head.probabilities` takes the running
  product of CORN's conditional sigmoids (raw sigmoids cost seven AUC points).
- **The declared backbone is checked at both ends**:
  `render_train.check_declared_backbone` at launch (a contradicting `--backbone` is
  refused), `render_train.check_written_backbone` in `render_acceptance.read`.
- **A bar is appended to, never edited**: `prereg.json`'s `amendments`, folded by
  `finished_acceptance.amended`; the **ordering** arm never moves.
  `finished_acceptance.cutpoints_of` reads `K-1` off `finished_train.RECIPES`.
- **The render cache is answered off the store**: `renders.missing` (may a trainer
  start) reads the store, not the `renders plan`. `renders verify` re-derives a seeded
  sample; `renders ship` needs a `renders accept` verdict, and a `FAIL` needs `--force`.
- **Build a render cache with ONE engine** (`renders.DEFAULT_WORKERS = 1`; about 2.25 s
  a picture, five hours from nothing). The engine already uses every core.
- **`renders decode`** stores each crop's exact pixels (~2.7 MB) for
  `renders.open_picture`; the loop is decode-bound. A truncated array reads as a miss.
- **A JPEG re-encode floor through PIL needs `subsampling=0`**: the engine writes q90
  at 4:4:4 (`engine/src/resample.rs`) and PIL's 4:2:0 reads ~27x too high.
- **A whole-store derivation reached from every builder is memoized with an un-memo**
  (`palette_sets.forget_cyclic`, `hunt.forget_recorded_prices`); a guard that
  redirects a store calls it.

## Both picture caches are addressed by their recipe

`renders` and `location_view` name a file by `renders.job_name`, a sha256 of the whole
engine spec (resolution and supersample included). The spec copies the engine's
`catalog()[mode]`, so a catalog field added renames that mode's views by design. Each
view directory's `drawn_by.jsonl` (`{schema, view, engine}`, last row wins, from
`engine_fingerprint`) is evidence after a render: an `unknown` build re-renders on read.

A tile is `<out_root>/<location_id>/t<NN>_<palette>_s<scale>_sh<shift>_<level>_q<q><regime>.jpg`,
`<regime>` being `_<w>x<h>ss<n>`, empty for canonical 640x360 ss2, with its own
`manifest<regime>.jsonl`, `build<regime>.json` and `.log`; the plan is shared.

```
fractal-wallpapers tiles build                                # canonical, 640x360 ss2
fractal-wallpapers tiles build --supersample 1                # 640x360 ss1
fractal-wallpapers tiles build --tile 384x216 --supersample 1 # 384x216 ss1
```

**384x216 ss1 is the node regime** (`tiles.NODE_REGIME`), the frame a walk's `expand`
scores directly; `discovery.identity` refuses settings that would make them differ.
Keep its manifest hot. A regime is complete when every row joins with 32 tiles, no
manifest row lacks its file, and nothing is stamped `partial`.

## Training and reading a head across regimes

```
fractal-wallpapers head train --run seed0_all_regimes --seed 0 --regime 640x360ss2 --regime 640x360ss1 --regime 384x216ss1 --selection cutpoint_cross_entropy
fractal-wallpapers head score --run seed0_all_regimes --regime 640x360ss1   # scores_640x360ss1.jsonl
fractal-wallpapers regime preregister      # bar on the evaluation split
fractal-wallpapers regime accept
fractal-wallpapers regime flip-preregister # second bar, on production stock
fractal-wallpapers regime flip-score --limit 90
fractal-wallpapers regime flip-score
fractal-wallpapers regime flip-read
fractal-wallpapers regime stage --read stock
```

An example is a `(location, regime)` pair. The canonical regime comes first; a row's
regimes share one slot draw; `dataset.join` refuses a regime short of a row; the head
gets no regime input. `--selection` is `ap_ge2` or `cutpoint_cross_entropy`.
`flip-score` draws 4,000 stratified, unlabelled sidecar locations, renders all three
regimes and writes `artifacts/regime_flips/{draw,reads}.jsonl`; `--limit` prices only
the smallest stratum. One worker is the default. `regime stage` writes
`location.candidate.fp16.pt` and `candidate.json`, never `weights.json`.

- A score file's `group` belongs to the manifest of its day; resample against one.
- A consistency figure needs a contested population (most evaluation rows read zero
  everywhere); say which rows it was measured on.
- `seed0_all_regimes` ships; its stock flip rate is 3.06% / 4.56% at 640x360ss1 /
  384x216ss1. A retrained location head moves every floor's pass rate, so adoption
  restates them from a measurement.

## The read a band cannot give: `renders glance`

[`render_glance`](render_glance.py) lays one batch's rows out in the incumbent's and
the candidate's orders, scores under each, from `artifacts/renders/<kind>/crops/`, into
one HTML file in `scratch/`. It decides nothing.

```
fractal-wallpapers renders glance --batch <name> --run <run>
```

## The deal a held-out read is drawn on: `render_folds`

[`render_folds`](render_folds.py) owns the **pool** (every fittable row of both
finished-render stores) and the **deal** (lineages in five parts) at
`artifacts/render_folds/assignment.json`, read by `renders grade`, `dose` and `deploy`.

## Grading a retrain: `renders grade`

[`render_grade`](render_grade.py) compares recipe arms unbanded on strange-holdout
`AUC(≥4)` and fits crossovers; it adopts nothing and writes `artifacts/render_grade/`.

```
fractal-wallpapers renders grade split  --fold 0
fractal-wallpapers renders grade fit    --arm A --fold 0 --seed 0
fractal-wallpapers renders grade read   --arm A --fold 0 --seed 0
fractal-wallpapers renders grade readout --seeds 0,1
fractal-wallpapers renders grade crossovers --arm A --rule <rule> --seed 0
fractal-wallpapers renders grade autopsy --candidate B@<rule> --reference A@<rule> --output <path>
```

Nothing cleared a bar, and a partial band is read for nothing. Standing results:
`input_detail` (768x448) is a judge adoption, not a config change; no `P(≥4)` crossover
exists, and the `P(≥3)` one reproduces `curation.floors.STRANGE_RELEASE_BAR`.

## Ordering the flat top: `renders top-slice`

[`top_slice_probe`](top_slice_probe.py) ridge-probes the judge's 1,280-wide pre-logit
vector (`train.activations`, pinned by `tests/test_activations.py`) at `P(≥4) ≥ 0.9`.
It found the scalar already carries what the layer has, the shipped rank key loses to
the raw judge inside the slice, and label geometry orders better than deployment.

```
fractal-wallpapers renders top-slice run     # score, cut, render, fit, draw
fractal-wallpapers renders top-slice sheet   # redraw the page from a run that landed
```

## Training the head that ships: `renders deploy`

Three seeds on the whole corpus under the incumbent recipe; the best chosen-epoch
AP(≥3) ships. `--band` keeps passes apart and `render_deploy.BANDS` names them.

```
fractal-wallpapers renders deploy split --seed 0    # what one seed's holdout holds
fractal-wallpapers renders deploy fit --seed 0      # one seed, ~13 min on this box
fractal-wallpapers renders deploy fit --seed 1
fractal-wallpapers renders deploy fit --seed 2
fractal-wallpapers renders deploy choose            # the three curves, and the winner
```

- A seed-looping driver needs an `if __name__ == "__main__":` guard (spawned workers
  re-import it and die on `training.lock`).
- The split is a seeded 80/20 over lineages; the 20 only stops the run, pinned rows
  stay unspent. Epoch by AP(≥3), patience 6, cap 20.
- Checkpoints go to `models/render/<run>/`; staging and flip are
  `ship.stage_candidate` and `ship.promote`.

⚠ **A render flip is not free, and `models/adoption.py` does not cover it.**
`STRANGE_RELEASE_BAR` refuses after a flip until refitted; `SMOOTH_RELEASE_FLOOR` acts
nowhere but is restated too. `tests/test_curation_cuts.py` holds both. Refit with `head
floor --head <kind>` and re-declare each height in `curation.floors`. **Retire the
outgoing bytes first**: `torch.save` is not byte-reproducible.

## Adopting a head: `regime restate`, then `regime adopt`

`restate` finds where each acting cut lands on the candidate by **volume** (the score
passing the same fraction of the curation sidecar as the retired cut did), and refuses
when any cut is stamped against something other than the live head. `adopt` copies the
judged bytes under the shipped name, checks the hash, and writes `adoption.json`. A
restatement holds volume, not rows. A retired artifact survives only as its release
asset (a `torch` archive embeds its file name), so deleting a release loses it.

## Running a band that takes hours

- **One trainer per directory**: `train.claim` takes an exclusive `training.lock`.
- **Wall-clock arithmetic proves little** after a resume; `models.audit.serial_time`
  reads each record's per-launch `segments`.
- **Audit a doubtful run**: `fractal-wallpapers head audit --run <run>` re-scores the
  selection slice and writes `audit.json`; ~1e-8 agreement proves one trajectory.
- **Snapshots load onto the CPU** (the RNG state cannot live on the GPU);
  `tests/test_training_resume.py` pins it.
- **A stalled run looks alive**: a Windows loader that respawns workers per epoch can
  deadlock. Watch the log's mtime and `nvidia-smi`; relaunch on silence. Persistent
  workers are safe only where the epoch counter is shared (`gallery_grade_train`).

## Budgeting a tile build

Cost tracks the population, not the row count, and class 1 carries the tail: price a
build from a stratified pilot of ~25 locations per class. Disk per 379,616-tile regime:
640x360 ss2 24.95 GiB, 640x360 ss1 26.89 GiB, 384x216 ss1 11.04 GiB.

## Installing the `models` extra

⚠ **`models` is CPU torch; GPU training is `uv sync --extra cuda` in its place, not
pip.** Only `uv` reads `[tool.uv.sources]`; pip pools indexes and takes PyPI's newer
wheel. `device_of("auto")` falls back to CPU silently: check
`python -c "import torch; print(torch.cuda.is_available())"`.

```
uv sync --extra dev --extra cuda --extra solve     # torch 2.6.0+cu124, Windows and Linux x86_64
```

Every shipped head was trained on that build; `models` and `cuda` conflict. With pip,
name the CUDA index's exact versions:

```
.venv/Scripts/pip install --extra-index-url https://download.pytorch.org/whl/cu124 \
  -e ".[dev,cuda,solve]" torch==2.6.0+cu124 torchvision==0.21.0+cu124
```

`roster` is the one stdlib-only module (`fetch-weights --check` runs on the base
install): `HEADS`, `TAG`, `manifest_path()`. **`weights.json` lists shipped heads
only**; the gallery-grade fp32 `best.pt` files `rotation.score_fine` needs travel in
`storage export`.

## What a score becomes, and the figure of it

`decisions` spells a location reading's outcome: **refused** (below the junk floor),
**expandable** (below the keeper floor), **find**, **exceptional** (`P(≥4)` over the
great cut), composing `curation.floors` and `supply.currency` rather than restating.

```
fractal-wallpapers figures judges-score-to-decision --coverage
fractal-wallpapers figures judges-score-to-decision --family julia:multibrot3
```

Four frames from held-out labelled rows of one family, each the median by `P(≥3)`,
with `frames.jsonl`. `--coverage` prints each partition's spread and draws nothing.

## Scoring a picture by hand, and checking an install

`fractal-wallpapers judges score <picture>…` reads pictures through the render, gallery
and palette judges; `--location FILE` reads location records (`models/judges.py`).
`judges check` renders `data/judges/check.jsonl`'s eight recipes and compares picture
prints (within 4/255) and all four judges' scores (within 1e-4) with tracked
references. `--write-expected` is for a deliberate judge or engine change, on the
`REFERENCE_BOX`.
