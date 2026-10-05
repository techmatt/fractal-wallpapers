# File formats

Every file a reader opens to inspect a result, field by field. Each list is derived
from the code that writes the file, and `tests/test_formats.py` reads those writers and
fails when one of them gains a field that this file does not name. Owning READMEs point
here and don't restate these lists.

**Conventions for every JSONL file.** UTF-8, one JSON object per line, and an integer
`schema` on every row from the first. A *location key* is the JSON-list spelling of
`supply/location.py`'s `location_key(family, viewport)`:
`[partition, degree, constants, center_re, center_im, width]`, with every number as a
canonical decimal string. A *recipe key* is 16 hex characters of the sha256 of
everything a picture is a function of (`curation/recipes.py`'s `key_of`). Neither key
contains a path, so both are the same in every clone. A *view* or picture name may
carry the checkout path in its digest, because it is a cache file name and not an
identity. Probabilities `p_geK` are a judge's `P(rating >= K)` on the 1–5 human scale,
each in [0, 1] and non-increasing in K.

| file | written by | section |
| --- | --- | --- |
| `artifacts/harvest/locations.jsonl` | `harvest export` | [locations.jsonl](#locationsjsonl) |
| `artifacts/harvest/walk.jsonl` | `harvest`, `walk` | [walk.jsonl](#walkjsonl) |
| `artifacts/curation/supply_scores.jsonl` | `curate score` | [supply_scores.jsonl](#supply_scoresjsonl) |
| `artifacts/curation/candidate_ledger/rows.jsonl` | `curate hunt merge`, `curate mine merge` | [Candidate ledger rows](#candidate-ledger-rows) |
| `artifacts/curation/candidate_ledger/scores.jsonl` | the same merges, `candidate-ledger score` | [Candidate ledger scores](#candidate-ledger-scores) |
| `artifacts/curation/candidate_ledger/flatness.jsonl` | the merges, `curate flatness sweep` | [Candidate ledger flatness](#candidate-ledger-flatness) |
| `artifacts/gallery_grade_head/pool_scores.jsonl` | `gallery-grade score-pool` | [pool_scores.jsonl](#pool_scoresjsonl) |
| `artifacts/curation/solve/<name>/solve.json` | `curate solve run`, `curate solve record` | [solve.json](#solvejson) |
| `artifacts/curation/tentative/<stamp>/gallery.jsonl` | `curate solve record` | [gallery.jsonl](#galleryjsonl) |
| `artifacts/curation/tentative/<stamp>/manifest.json` | `curate solve record` | [manifest.json](#manifestjson) |
| `artifacts/curation/tentative/keep.jsonl` | `solve record`, `solve release` | [keep.jsonl](#keepjsonl) |
| `page.json` beside each inspection page | every page and `--bundle` | [page.json](#pagejson) |
| `page.json` beside a gallery's page | `curate solve browse`, `record` | [Gallery page.json](#gallery-pagejson) |
| `artifacts/curation/trace/<stamp>/counts.json` and `files/` | `curate solve trace` | [counts.json](#countsjson) |
| `artifacts/walkthrough/walkthrough.json` | `walkthrough` | [walkthrough.json](#walkthroughjson) |
| a render spec JSON | you; `fractal-engine render <spec>` | [The render spec](#the-render-spec) |
| an explorer link | the website; `render-link` | [The explorer link](#the-explorer-link) |

## locations.jsonl

One row per **admitted** place of one harvest, written whole by `harvest export`
(`supply/places.py`'s `rows`). It joins the walk ledger's `candidate` rows (with an
adopted refinement applied) to the location judge's sidecar on the location key.
"Admitted" means what the run's summary counts: fate `survived`. A place `curate
score` hasn't read yet is present, with nulls in every judge column.

| field | type | meaning |
| --- | --- | --- |
| `schema` | int | 1 |
| `key` | str | the location key; joins `supply_scores.jsonl` `key` and a ledger row's `location.key` |
| `partition` | str | fractal family partition: `mandelbrot`, `multibrot3`–`6`, `julia:<plane>`, `phoenix`, `phoenix:classic` |
| `family` | object | the recurrence, as in [the render spec](#the-render-spec)'s `family` |
| `viewport` | object | `{center_re, center_im, width}`, decimal strings |
| `maxiter` | int | the iteration cap the walk read the frame at |
| `depth` | int | rungs below the lineage's root |
| `root_id` | int | the lineage the place was found in |
| `root_channel` | str/null | where the lineage's root came from: the root row's `provenance.channel` (a seed pool, `twin:<source>`, `proven`, `viewport_sampler`) or its `source` |
| `slot_channel` | str/null | which half of the harvest's clock found it: `share` (the protected exploration share) or `contest` (the deficit-priced contest) |
| `origin` | str | `walk`, a reframing operator's name, or `refined` |
| `refined` | bool | the close-time framing scan moved this frame |
| `view` | str/null | the walk's own gate render, a JPEG under `<run>/views/` |
| `walk_p_ge3`, `walk_p_ge4` | float/null | what the walk's scorer read off the gate render; null on a `--no-scoring` run |
| `p_ge2`, `p_ge3`, `p_ge4` | float/null | the location judge's probabilities off `supply_scores.jsonl` |
| `score_regime` | str/null | the geometry the judge read, e.g. `384x216ss1` |
| `score_view` | str/null | the picture file the judge read |

`harvest stats` writes `<run>/stats/stats.json`: `{schema, run, found, admitted,
scored, families}`, with `families` keyed by partition. Each family is
`{found, admitted, scored, p_ge3, p_ge4, best, worst}`; `p_ge3` and `p_ge4` are
`{min, q1, median, q3, max, over_half}`, and `best` and `worst` are lists of location
keys.

## walk.jsonl

The walk's append-only ledger, one per run directory (`discovery/ledger.py`'s
`Ledger.write`). Every row is `{schema, kind, ...}`. The kinds:

| `kind` | one row per | carries |
| --- | --- | --- |
| `run` | run (the header, first row) | `seed`, `scorer`, `scoring`, `identity`, `colormap`, `limits`, `policy`, `gates`, `report_foci`, `reframings`, `invocation`, `ledgers_read` |
| `root` | lineage started | `root_id`, `node_id`, `source`, `family`, `viewport`, `provenance` (its `channel` is where the root came from), `plane_root` |
| `candidate` | frame proposed | the fields below |
| `refined` | close-time framing scan of a place | the original `viewport`, the adopted `refined_viewport`, `refined_maxiter`, `score`, `score_great`, `gain`, `framing`, `gate_render`; readers apply it through `supply/ledgers.py`'s `refined_of` |
| `foci` | node whose children were placed by foci | `node_id`, `depth`, `tile`, `found`, `spread_radius`, `kept` |
| `node_dead` | node that could not be expanded | `node_id`, `depth`, `cause` (`width_floor`, `interior_cap`, `instant_escape`, `flat`, `occupancy_floor`, `no_candidate`) |
| `probe` | refused period probe | `node_id`, `degree`, `fired: false`, `reason` |
| `reframing` | reframing operator considered | `operator`, `available`, `reason`, `framing`, `atom_key`, `period`, `viewport`, `used` |
| `lineage_capped` | lineage over its admission cap | `root_id`, `admissions`, `cap`, `evicted` |
| `sampler_draw` | viewport-sampler attempt | `scheme`, `seed_id`, `rung`, `cell`, `family`, `viewport`, `fate`, `passed` |
| `viewport_sampler` | pinned plane's sampled ladder | `partition` and the sample's record |
| `twin_seed`, `twin_skip` | Julia parameter taken, or refused inside the spacing floor | `twin`, `plane`, `seed_id` or `distance`/`blocked_by` |
| `twin_channel` | run (at close) | the twin channel's counts per partition |
| `summary` | run (last row) | the same object as `<run>/summary.json` |

The reframing leg's own run directory adds `reframing_fire` and `reframing_summary` rows
and reframing `candidate` rows with a `reframing` block. A deep walk (`deep run`) writes
`deep_run` as its header and adds `seat`, `sourcing_round` and `batch_killed` (a batch
the clock cut short).

A `candidate` row (`discovery/walk.py`'s `_candidate`):

| field | type | meaning |
| --- | --- | --- |
| `node_id` | int/null | the node this frame became; null if it was not expanded |
| `run_seed`, `batch` | int | the run's seed and the batch it was drawn in |
| `parent_node_id`, `root_id`, `depth`, `child_index` | int | where in the lineage it sits |
| `family`, `viewport`, `maxiter` | | the frame (see [the render spec](#the-render-spec)) |
| `branch`, `placement`, `focus_score` | | how the engine placed the child frame |
| `interior_fraction`, `escape`, `occupancy` | | what the three structural gates measured |
| `image` | str/null | the gate render `node<parent>_c<child>.jpg` under `<run>/views/`; only survivors have one |
| `origin` | str | `walk` or a reframing operator |
| `atom_key` | str/null | the nucleus a reframing framed |
| `channel` | str/null | `share` or `contest` on a harvest |
| `fate` | str | `survived` (admitted), `expandable`, `not_admitted`, or the gate that refused it: `interior_cap`, `instant_escape`, `flat`, `occupancy_floor` |
| `scorer`, `score_regime`, `score_view`, `score_error` | | which judge read the frame, at what geometry, off which picture, or why it could not |
| `score`, `score_great` | float/null | the walk scorer's P(>=3) and P(>=4) |
| `plane_rung`, `cleared_junk`, `grace` | | the plane-rung and junk-floor verdicts |
| `lineage_capped` | bool | present only when the lineage cap refused the row |

## supply_scores.jsonl

The location judge's reading of every place it has scored, one row per location key,
upserted by `curate score` (`curation/intake.py`'s `score`).

| field | type | meaning |
| --- | --- | --- |
| `schema` | int | 1 |
| `head` | str | `location` |
| `head_sha256` | str | the shipped head's stamp |
| `key` | str | the location key |
| `ledger` | str | the walk ledger the place came from, as a tracked path |
| `node_id` | int/null | its candidate row's node |
| `partition`, `family`, `viewport`, `maxiter` | | the place |
| `view` | str | the picture file the judge read |
| `regime` | str | its geometry, e.g. `384x216ss1` or `640x360ss2` |
| `p_ge2`, `p_ge3`, `p_ge4` | float | the judge's probabilities |

## Candidate ledger rows

`rows.jsonl`: one row per rendered candidate picture (a *recipe*), upserted by every
merge (`curation/candidate_ledger/rows.py`'s `row`).

| field | type | meaning |
| --- | --- | --- |
| `schema` | int | 1 |
| `key` | str | the recipe key |
| `partition` | str | the place's partition |
| `location` | object | `{key, agrees}`: the location key, and whether the recipe's frame computes to it |
| `recipe` | object | everything the picture is a function of; the fields are below |
| `at_candidate_regime` | bool | rendered at the pool's 640x360ss2; a solve seats only these |
| `texture_flat` | bool | the picture's texture read as flat, which routes it to the smooth slot |
| `colour` | object/null | `{cells, families}`: the colour cells and hue families the picture is dominant in |
| `engine` | str | the engine build fingerprint that drew it |
| `provenance` | object | `{run, candidate, also_rendered, also_recorded}`: which leg made it |
| `picture` | str/null | the 640x360 JPEG, a tracked path under `artifacts/curation/<leg>/pictures/` |
| `rejected` | object/null | a person's rejection; a rejected row is never seated |
| `hunt` | object | present on leg rows: `{seconds, k, drawn_for, drawn_cells}` |

`recipe` (`curation/recipes.py`'s `Recipe.record`): `schema`, `family`, `viewport`,
`maxiter`, `regime` (e.g. `640x360ss2`), `mode`, `mode_params` (the mode's settings;
`{}` is the catalog's), `curve` (`linear`, `sqrt`, `log` or `scurve`), `colormap`,
`palette_group` (carried, not keyed), `palette` (the seven knobs of
[the render spec's palette](#the-render-spec)) and `autolevel` (`{operator, switch,
band_sha256}` or null).

## Candidate ledger scores

`scores.jsonl`: one row per (recipe, judge artifact, regime)
(`curation/candidate_ledger/rows.py`'s `score_row`). A judge adoption adds rows; it
never rewrites old ones.

| field | type | meaning |
| --- | --- | --- |
| `schema` | int | 1 |
| `key` | str | `<recipe_key>|<judge_artifact>|<regime>` |
| `recipe_key` | str | joins `rows.jsonl` `key` |
| `judge_artifact` | str | which shipped render judge read it |
| `regime` | str | the picture's geometry |
| `head` | str | `smooth_render` or `strange_render`: which slot and bar the row is judged under |
| `p_ge2`, `p_ge3`, `p_ge4` | float | the render judge's probabilities |
| `rank_score` | float | their sum |
| `block` | str | `scores` or `scores_current` |
| `read_by` | object | `{run, candidate}`: the leg that read it |

## Candidate ledger flatness

`flatness.jsonl`: one row per recipe (`curation/flatness.py`'s `row`): `schema`,
`recipe_key`, `column` (`flat16_1.0`), `cell` (16, the block size in pixels),
`threshold` (1.0), and the reading itself under the column's name, `flat16_1.0`: the
share of 16-pixel blocks whose luminance spread is under the threshold, in [0, 1].

## pool_scores.jsonl

The gallery judge's reading of the pool's above-bar rows, rewritten whole by
`gallery-grade score-pool` (`models/gallery_grade_train.py`'s `score_pool`); the cascade
order and the fine bar read it. Fields: `schema`, `head` (`gallery_grade`), `run` (the
column's name), `weights` (the checkpoint digest), `key` (the recipe key), `p_ge2`,
`p_ge3`, `p_ge4` (the three-seed mean), and `rank_score`. A merge adds rows it hasn't
read, so run it again after every merge.

## solve.json

One solve's whole record (`curation/solve.py`'s `solve`, written by `write_record`).

| field | meaning |
| --- | --- |
| `schema`, `taken_at`, `seconds` | the record's version, UTC time, and wall seconds |
| `config` | every setting the pass ran under; fields below |
| `objective` | `{of, tiers, rank_quantity, seed, after_the_swap_loop, after_the_augment, final, read_as, above_q4_bar, q4_bar, q4_basis, q4_bar_is}`: the objective at each stage and how many seats clear `P(>=4) >= 0.5` |
| `pool` | `{refused, reachable_clusters, truncated_to, truncation, truncation_is}`: what pool construction refused, by reason |
| `fine_bar` | the fine bar's cost: `{bar, offered, kept, dropped, unscored, locations, ...}`, or `{bar: null}` unbarred |
| `forced` | the `--forced` key manifest's lift: `{asked, lifted, unread, keys, ...}` |
| `pins` | which tracked pins were seated and why the rest were not |
| `theme_pool` | a themed pass's cell and its pool, or null |
| `order` | `{key, of, ranked, unranked, unranked_are, unranked_allowed, coverage}`: the seating order |
| `preselection` | the near-duplicate fold before the seed |
| `view`, `seed`, `swaps`, `augment`, `swaps_after_the_augment`, `expand` | each stage's own record |
| `population` | `{candidates, clearing, after_the_preselection, in_the_view, locations, ...}` |
| `filled`, `unfilled` | seats filled, and the asked `n` less that |
| `short_fill` | null, or the SHORT FILL notice's numbers when under a quarter of `n` filled |
| `seated` | one row per seat; fields below |
| `attribution`, `shortfalls`, `rules`, `spiral`, `diversity`, `diversity_refusals` | why each seat is there and what each rule refused |
| `rejection` | every unseated row's last refusal, counted, plus `explained` for asked keys |
| `samples` | a few refused rows per reason |

A `seated` row (`_seated`): `key` (the recipe key), `seated_for` (the demand or leg that
placed it), `rank` (the value the order sorted on), `location` (location key),
`partition`, `mode`, `mode_params`, `kind` (`smooth_render`/`strange_render`),
`palette_group`, `cells`, `families`, `p_ge4`, `p_ge3` (the render judge's), `above_bar`
(`p_ge4 >= 0.5`), `spiral`, `p_spiral`, `picture`, and `pinned`. `solve run` adds
`release_picture`, `release_autolevel` and `release_geometry` once it has rendered the
seat at 1280x720ss2.

`config` (`_config`): `n` (seats asked); `force_fill` (true: `--force-fill` seated past
both quality bars); `fine_bar` and `fine_bar_default` (null is unbarred); `fine_head`
and `fine_weights` (whose column the bar read); `theme_bar`; `forced` and
`forced_default` (keys lifted); `fold` and `fold_default`; `spiral_cap` and
`spiral_cap_default`; `mode_ceilings` and `mode_ceilings_default` (`{mode: share}`);
`augment`, `augment_default`, `augment_depth`, `augment_seconds`; `theme`; `method`,
`objective` and `order` (prose); `bars` (`{mode: the rule its bar was taken on}`);
`ceiling` (`{k, k_default, kf, kf_default, cell_share, family_share, allowance, floor,
floor_rule, floor_is, group_cap, group_cap_rule, group_cap_from, targets,
target_rule}`, the colour ceiling and floor); `sort_key` and `sort_key_named`;
`mode_floor`, `mode_floors`, `mode_floor_rule`, `mode_floor_natural`,
`mode_floor_artificial`; `modes` (the accepted roster); and `mode_policy`. Every
`*_is` and `bars_are` field (`fold_is`, `fine_bar_is`, `fine_head_is`,
`fine_weights_is`, `forced_is`, `theme_bar_is`, `mode_ceilings_is`, `augment_is`) is the
sentence saying what its sibling means, carried whole.

## gallery.jsonl

One row per seat of a recorded gallery, in seat order (`curation/tentative.py`'s
`rows_of`).

| field | type | meaning |
| --- | --- | --- |
| `schema` | int | 1 |
| `seat` | int | the seat's place in the solve's walk |
| `key` | str | the recipe key: **the picture's ID** |
| `alias` | str | the shortest unambiguous prefix of `key`, 8 characters or more |
| `mode`, `mode_params`, `partition` | | the seat's coloring and family |
| `cell`, `hue_family` | str | the leading dominant colour cell and hue family |
| `cells`, `families` | list | every cell and family it is dominant in |
| `seated_for` | str | the demand or leg that placed it |
| `pinned` | bool | a tracked pin, seated before anything else |
| `floor`, `floor_cells` | | `mandated`, `holding` or `no`: what the colour floor had to do with this seat |
| `centered` | bool | its place is a centred nucleus |
| `spiral`, `p_spiral` | | the spiral probe's verdict and probability for its place |
| `rank` | float | the value the solve's order sorted on |
| `p_ge4` | float | the render judge's P(>=4) |
| `location` | str | the location key |
| `picture` | str | the 640x360 candidate picture |

`recipes.jsonl` beside it (published records only) is one `{schema, key, recipe}` row
per seat, with `recipe` as in [Candidate ledger rows](#candidate-ledger-rows);
`render --recipe <file> --key <alias>` draws one.

## manifest.json

What a recorded gallery was taken over, and how it did (`manifest_of`).

| field | meaning |
| --- | --- |
| `schema`, `stamp`, `taken_at`, `source_commit` | the record's identity and when and from which commit it was taken |
| `solve` | `{name, record, taken_at, seconds, config, diversity, diversity_is, pins}`: `config` is [solve.json](#solvejson)'s `config` whole, so `solve.config.force_fill` says whether it ran forced |
| `pool` | `{stamp, stamp_is, candidates, locations, reachable_clusters, refused, ledger_rows, ledger_path}`; `stamp` is a sha256 over the pool's sorted keys |
| `seats` | `{asked, filled, shortfall, recorded}` |
| `shortfalls` | the solve's unmet demands |
| `counts` | `{mode, hue_family, cell, partition, centered, spiral}`, each `{value: seats}` |

## keep.jsonl

The keep list's unpublished half (`tentative.py`'s `keep` and `release`), append-only:
`{schema, stamp, kept, at, reason}`. The last row for a stamp decides. A kept record's
seats are spared by every merge's prune. `curate solve record` appends `kept: true`
unless given `--no-keep`, and `curate solve release <stamp>` appends `kept: false`. The
published records are kept by `tentative.PUBLISHED` and never appear here.

## page.json

The parseable twin of every inspection page: `judges check`, `harvest stats`, `curate
candidate-ledger browse`, and `curate solve trace`. It sits beside `index.html`, holds
exactly what the page shows, and the page is drawn from it (`grid_page.py`'s `document`
and `render`). Pass `--bundle DIR` to any of those commands and the same pair is also
written into `DIR`, with each picture the page shows re-encoded under `DIR/pictures/`
(`bundle.py`'s `WIDTH` and `QUALITY`). Nothing in a bundle refers outside the folder.

| field | meaning |
| --- | --- |
| `schema`, `title` | `1`, and the page's heading |
| `command` | the command line that wrote it; an absolute path under the working directory is spelled relative |
| `intro` | the lines under the heading |
| `sections` | `[{heading, note, table, tiles, records}]` in page order |
| `table` | `null`, or a list of rows whose first row is the header |
| `tiles` | `[{picture, title, mark, caption}]`; `picture` is the path the page uses, relative to it, or `null`; `caption` is `[[label, value]]` |
| `records` | `[{file, joined_on, key, note, row}]`: one row copied out of `file` whole, the field the chain was `joined_on` and its `key` (marked on the page), and a `note` saying why a chain stopped here |

## Gallery page.json

The twin of a recorded gallery's page (`curate solve browse`, `curate solve record`),
written by `tentative.py`'s `page`. The page is a filtering browser that embeds `rows`
as they are here.

| field | meaning |
| --- | --- |
| `schema`, `command`, `stamp` | as above, and the record's stamp |
| `name`, `forced` | the solve's name, and whether it ran `--force-fill` |
| `seats`, `asked` | seats filled, and seats asked for |
| `missing`, `at_full` | seats with no picture on this disk, and seats with a release-geometry picture |
| `full_regime`, `ordered_by` | the release regime's spelling, and the basis of the presentation order |
| `rows` | [gallery.jsonl](#galleryjsonl)'s rows, each with `src` (the picture the tile shows), `full` (its release-geometry picture, or empty; always empty in a bundle) and `order` |

## counts.json

Beside a trace's page (`curate solve trace <stamp>`, `curation/trace.py`'s `build`),
default `artifacts/curation/trace/<stamp>/`. The trace's `files/` folder holds a sliced
copy of each file a seat's chain runs through: `gallery.jsonl`, `manifest.json`,
`rows.jsonl`, `scores.jsonl`, `flatness.jsonl`, `pool_scores.jsonl`,
`supply_scores.jsonl`, `locations.jsonl` and `walk.jsonl`. Each slice holds only the rows
on the chains, copied byte for byte, so each is read by its own section above. The walk
slice also holds one row of every kind no chain reached. The page is a
[page.json](#pagejson).

| field | meaning |
| --- | --- |
| `schema`, `stamp`, `seats` | `1`, the record traced, and its seat count |
| `broken_chains` | `[{seat, key, stopped_at}]`: seats whose chain could not be followed, and the file it stopped at |
| `files` | `{name: {source, rows, sliced}}`: the full file's tracked path, how many rows it held, and how many the slice kept |

## walkthrough.json

The listing at the top of `fractal-wallpapers walkthrough`'s folder (default
`artifacts/walkthrough/`, `walkthrough.py`'s `build`), which its `index.html` is drawn
beside. Each listed folder is a bundle holding a [page.json](#pagejson), or a
[Gallery page.json](#gallery-pagejson) for `gallery/`.

| field | meaning |
| --- | --- |
| `schema`, `command`, `stamp` | `1`, the command line, and the record shown and traced |
| `pages` | `[{folder, title, made_by, command, files, bytes}]`; a page whose step was not run has `missing: true` and `made_by` is the command that makes it |
| `files` | `[{name, source}]`: the whole files copied in (`summary.json`, `stats.json`, `keep.jsonl`) and where each came from; `missing: true` where there was none |

## The render spec

The JSON object `fractal-engine render <spec.json>` reads (`engine/src/spec.rs`'s
`RenderSpec`), and the one door to the two families and the knobs no
`fractal-wallpapers render` flag reaches. Unknown keys are refused at every level, not
ignored.

| key | type | default | rule |
| --- | --- | --- | --- |
| `schema` | int | required | 1 |
| `family` | object | required | `{kind, ...}`; kinds below |
| `viewport` | object | the family's home view | `{center_re, center_im, width}`, each an optional decimal string; width > 0 |
| `resolution` | [w, h] | required | both > 0 |
| `supersample` | int | 1 | samples per pixel per axis, >= 1 |
| `mode` | str | `smooth` | a name `fractal-wallpapers modes` prints; not with `coloring` |
| `coloring` | object | none | a full coloring (field, transform, ...); not with `mode` |
| `params` | {name: number} | `{}` | the mode's settings, beside `mode` only |
| `palette` | object | identity | how the colormap is spent; fields below |
| `colormap` | str | required | a name `fractal-wallpapers palettes list` prints |
| `colormap_dir` | path | `data/palettes` | where the colormap files are |
| `maxiter` | int | the depth policy's | iteration cap |
| `output` | path | required | `.png` or `.jpg` |
| `allow_unresolvable_in_f64` | bool | false | allow a frame too deep for f64 to resolve |

`family.kind`:

| kind | keys | notes |
| --- | --- | --- |
| `mandelbrot` | none | |
| `multibrot` | `degree` | an integer, 3–6 |
| `julia` | `degree` (2), `c` | `c` is `[re, im]` decimal strings; degree 2–6 |
| `phoenix` | `c`, `p`, `z_prev` | defaults `["0.5667","0.0"]`, `["-0.5","0.0"]`, `["0.0","0.0"]` |
| `phoenix_m` | `p` | the Phoenix parameter plane: the pixel is `c`; home centre −0.69, width 2.8 |
| `fractional_multibrot` | `degree` | a decimal **string** in [1.8, 5.0], not a whole number; render only, with **no home view**, so `center_re`, `center_im` and `width` are all required |

`palette` (`engine/src/coloring.rs`'s `Palette`; a curation recipe's `palette` is its
first seven):

| key | type | default | range |
| --- | --- | --- | --- |
| `gamma` | number | 1 | > 0 |
| `cycles` | number | 1 | > 0 |
| `phase` | number, turns | 0 | finite |
| `reverse` | bool | false | |
| `mirror` | bool | false | refused on a cyclic colormap (`palettes list --kind cyclic`) |
| `transfer` | object | `{"kind":"value"}` | `value`, `{"kind":"edge","weight":w}` with w >= 0, or `rank`; only `value` under an itinerary mode |
| `rolloff` | object | `{"kind":"none"}` | `none`, `{"kind":"soft_knee","knee":k}` with k in [0, 1), `reinhard`, `aces` |
| `scale` | str | `leveled` | `leveled` or `absolute`; under `absolute`, `gamma`, `cycles` and `transfer` do not apply |
| `lambda` | number | 1 | Box–Cox, [0, 1] |
| `period` | number | 1 | > 0, absolute only |
| `knee` | number/null | null | > 0, absolute only |

`params` by mode: `density` (stripe 6, smooth_stripe), `radius` (trap_circle 1.0,
smooth_trap_circle, direct_trap_ring), `sigma` (threads 0.15), `weight` (the
smooth_mean_angle, smooth_angle_min, smooth_curvature, smooth_trap_circle and
smooth_stripe composites 0.85, threads 0.5; [0, 1]), `shift` (itinerary,
tail_itinerary 0.5), `threshold` and `opacity` (the four direct_trap_* modes). The
curve is not a palette key: it is an explicit coloring's `transform` (`linear`, `sqrt`,
`log`, `scurve`). `fractal-wallpapers render` reaches every palette key and `params`
through flags (`--gamma` … `--knee`, `--param NAME=VALUE`); the curve and the
`phoenix_m` and `fractional_multibrot` families are this file's alone. A minimal
fractional multibrot:

```json
{"schema": 1, "family": {"kind": "fractional_multibrot", "degree": "2.5"},
 "viewport": {"center_re": "-0.4", "center_im": "0", "width": "3"},
 "resolution": [1280, 720], "supersample": 2, "mode": "smooth",
 "colormap": "twilight_shifted", "output": "artifacts/fractional.png"}
```

## The explorer link

The website's `explorer/README.md` (in the `techmatt/fractals` checkout) owns this
vocabulary; `engine/src/link.rs` parses the same keys, and
`engine/fixtures/link-cases.json` holds the website's own cases against it. The keys
`render-link` reads:

| key | meaning |
| --- | --- |
| `v` | link version, 1–4 (a shallow link) |
| `dv` | deep-link version, 1–3; parsed, not yet drawn |
| `f` | family: `mandelbrot` (default), `multibrot3`–`multibrot6`, `julia`, `julia3`–`julia6`, `phoenix`, `phoenix_plane` (the `phoenix_m` plane) |
| `cx`, `cy` | the Julia or Phoenix constant `c` |
| `px`, `py` | the Phoenix `p` |
| `zx`, `zy` | the Phoenix `z_prev` |
| `m` | coloring mode (default `smooth`); 17 of the 20, not `exp_smoothing`, `tail_itinerary` or `de` |
| `density`, `radius`, `sigma`, `threshold`, `weight`, `opacity`, `shift` | the mode's params |
| `curve` | `linear`, `sqrt`, `log`, `scurve`, when it differs from the mode's own |
| `x`, `y`, `w` | centre and width; the family's home view when absent |
| `n` | iteration cap, 50–2,000,000 (v4) |
| `a` | aspect `W:H` (default 16:9) |
| `p` | colormap name (default `twilight_shifted`) |
| `level` | `band_autolevel/v1:black,white,exponent,out0,out1`, the autolevel curve |
| `gamma`, `cycles`, `phase`, `reverse`, `mirror`, `transfer`, `rolloff`, `scale`, `lambda`, `period`, `knee` | the palette keys above (`transfer` as `edge:w`, `rolloff` as `soft_knee:k`, booleans as 0/1) |
| `panel`, `every`, `collection`, `modes`, `hue` | the page's own state; the picture ignores them |
