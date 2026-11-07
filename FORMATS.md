# File formats

Every file a reader inspects, field by field (`tests/test_formats.py` guards the names).
JSONL is UTF-8, one object per line, `schema` on every row. A *location key* is
`supply/location.py`'s `location_key`: `[partition, degree, constants, center_re,
center_im, width]`, canonical decimal strings. A *recipe key* is 16 hex of the sha256 of
everything a picture is a function of (`curation/recipes.py`'s `key_of`). Neither holds a
path. `p_geK` is a judge's `P(rating >= K)` on the 1–5 scale.

## locations.jsonl

`artifacts/harvest/locations.jsonl` (`harvest export`, `supply/places.py`'s `rows`): per
location key, the first `survived` candidate (refinement applied) joined to the location
judge, its columns null until `curate score`.

`schema` 1; `key` (location key; joins `supply_scores.jsonl` `key` and a ledger row's
`location.key`); `partition` (`mandelbrot`, `multibrot3`–`6`, `julia:<plane>`,
`phoenix`, `phoenix:classic`); `family` ([the render spec](#the-render-spec)'s);
`viewport` `{center_re, center_im, width}`; `maxiter`; `depth`; `root_id`;
`root_channel` (the root's `provenance.channel`: a seed pool, `twin:<source>`, `proven`,
`viewport_sampler`; else its `source`); `slot_channel` (`share` or `contest`); `origin`
(`walk`, a reframing operator, `refined`); `refined` (bool); `view`
(`views/node<parent>_c<child>.jpg` or null); `walk_p_ge3`, `walk_p_ge4` (null on
`--no-scoring`); `p_ge2`, `p_ge3`, `p_ge4`, `score_regime` (e.g. `384x216ss1`),
`score_view`.

`harvest stats` writes `<run>/stats/stats.json`: `{schema, run, found, places, repeats,
scored, families}`; `families` by partition, each `{found, places, scored, p_ge3, p_ge4, best, worst}`, the
`p_ge*` as `{min, q1, median, q3, max, over_half}`, `best`/`worst` location keys.

## walk.jsonl

A run directory's append-only ledger (`harvest`, `walk`; `discovery/ledger.py`'s
`Ledger.write`), rows `{schema, kind, ...}`:

- `run` (header): `seed`, `scorer`, `scoring`, `identity`, `colormap`, `limits`, `policy`,
  `gates`, `report_foci`, `reframings`, `invocation`, `ledgers_read`.
- `root` (a lineage): `root_id`, `node_id`, `source`, `family`, `viewport`, `provenance`
  (with `channel`), `plane_root`.
- `candidate`: below. `refined` (close-time framing scan, applied by
  `supply/ledgers.py`'s `refined_of`): `viewport`, `refined_viewport`, `refined_maxiter`,
  `score`, `score_great`, `gain`, `framing`, `gate_render`.
- `foci`: `node_id`, `depth`, `tile`, `found`, `spread_radius`, `kept`. `node_dead`:
  `node_id`, `depth`, `cause` (`width_floor`, `interior_cap`, `instant_escape`, `flat`,
  `occupancy_floor`, `no_candidate`). `probe` (refused): `node_id`, `degree`,
  `fired: false`, `reason`.
- `reframing`: `operator`, `available`, `reason`, `framing`, `atom_key`, `period`,
  `viewport`, `used`. `lineage_capped`: `root_id`, `admissions`, `cap`, `evicted`.
- `sampler_draw`: `scheme`, `seed_id`, `rung`, `cell`, `family`, `viewport`, `fate`,
  `passed`. `viewport_sampler`: `partition` and the sample's record.
- `twin_seed`, `twin_skip` (inside the spacing floor): `twin`, `plane`, `seed_id` or
  `distance`/`blocked_by`. `twin_channel`: counts per partition. `summary` (last row):
  `<run>/summary.json`.
- A reframing leg adds `reframing_fire`, `reframing_summary` and a `reframing` block on
  its candidates; `deep run` writes a `deep_run` header and `seat`, `sourcing_round`,
  `batch_killed`.

A `candidate` (`discovery/walk.py`'s `_candidate`): `node_id` (null if unexpanded);
`run_seed`, `batch`, `parent_node_id`, `root_id`, `depth`, `child_index`; `family`,
`viewport`, `maxiter`; `branch`, `placement`, `focus_score`; `interior_fraction`,
`escape`, `occupancy` (the gates); `image` (survivors' `views/node<parent>_c<child>.jpg`);
`origin`; `atom_key`; `channel`; `fate` (`survived`, `expandable`, `not_admitted`, or the
refusing gate); `scorer`, `score_regime`, `score_view`, `score_error`; `score`,
`score_great` (P(>=3), P(>=4)); `plane_rung`, `cleared_junk`, `grace`; `lineage_capped`
(only when the cap refused it).

## supply_scores.jsonl

`artifacts/curation/supply_scores.jsonl`, one row per location key, upserted by `curate
score` (`curation/intake.py`'s `score`): `schema` 1, `head` (`location`), `head_sha256`,
`key`, `ledger` (tracked path), `node_id`, `partition`, `family`, `viewport`, `maxiter`,
`view`, `regime` (e.g. `640x360ss2`), `p_ge2`, `p_ge3`, `p_ge4`.

## Candidate ledger rows

`artifacts/curation/candidate_ledger/rows.jsonl`, one row per candidate picture,
upserted by `curate hunt|mine merge` (`curation/candidate_ledger/rows.py`'s `row`): `schema` 1; `key`; `partition`;
`location` `{key, agrees}` (`agrees`: the frame computes to that key); `recipe`;
`at_candidate_regime` (640x360ss2; a solve seats only these); `texture_flat` (routes to
the smooth slot); `colour` `{cells, families}` or null; `engine` (build fingerprint);
`provenance` `{run, candidate, also_rendered, also_recorded}`; `picture` (JPEG under
`artifacts/curation/<leg>/pictures/`); `rejected` (never seated, or null); `hunt` (leg
rows) `{seconds, k, drawn_for, drawn_cells}`.

`recipe` (`Recipe.record`): `schema`, `family`, `viewport`, `maxiter`, `regime`, `mode`,
`mode_params` (`{}` is the catalog's), `curve` (`linear`, `sqrt`, `log`, `scurve`),
`colormap`, `palette_group` (not keyed), `palette` (the spec palette's first seven) and
`autolevel` (`{operator, switch, band_sha256}` or null).

## Candidate ledger scores

`scores.jsonl` (merges, `candidate-ledger score`), one row per (recipe, judge, regime),
never rewritten (`rows.py`'s `score_row`): `schema` 1, `key`
(`<recipe_key>|<judge_artifact>|<regime>`), `recipe_key`, `judge_artifact`, `regime`,
`head` (`smooth_render` or `strange_render`), `p_ge2`, `p_ge3`, `p_ge4`, `rank_score`
(their sum), `block` (`scores` or `scores_current`), `read_by` `{run, candidate}`.

## Candidate ledger flatness

`flatness.jsonl` (merges, `curate flatness sweep`), per recipe (`curation/flatness.py`'s
`row`): `schema`, `recipe_key`, `column` (`flat16_1.0`), `cell` (16 px), `threshold`
(1.0), and under the column's name the share of blocks with luminance spread under it.

## pool_scores.jsonl

`artifacts/gallery_grade_head/pool_scores.jsonl`, the gallery judge on the pool's
above-bar rows, rewritten by `gallery-grade score-pool` (`models/gallery_grade_train.py`'s
`score_pool`; re-run after every merge): `schema`, `head` (`gallery_grade`), `run`,
`weights` (checkpoint digest), `key`, `p_ge2`, `p_ge3`, `p_ge4` (three-seed mean),
`rank_score`.

## solve.json

`artifacts/curation/solve/<name>/solve.json` (`curate solve run|record`;
`curation/solve.py`'s `solve`): `schema`, `taken_at` (UTC), `seconds`, `config`;
`objective` `{of, tiers, rank_quantity, seed, after_the_swap_loop, after_the_augment,
final, read_as, above_q4_bar, q4_bar, q4_basis, q4_bar_is}`; `pool` `{refused,
reachable_clusters, truncated_to, truncation, truncation_is}`; `fine_bar` `{bar, offered,
kept, dropped, unscored, locations, ...}` or `{bar: null}`; `forced` `{asked, lifted,
unread, keys, ...}`; `pins`; `theme_pool`; `order` `{key, of, ranked, unranked,
unranked_are, unranked_allowed, coverage}`; `preselection`; `view`, `seed`, `swaps`,
`augment`, `swaps_after_the_augment`, `expand`; `population` `{candidates, clearing,
after_the_preselection, in_the_view, locations, ...}`; `filled`, `unfilled`;
`short_fill` (null unless under a quarter of `n` filled); `seated`; `attribution`,
`shortfalls`, `rules`, `spiral`, `diversity`, `diversity_refusals`; `rejection` (each
unseated row's last refusal, counted; `explained` for asked keys); `samples`.

`seated` (`_seated`): `key`, `seated_for`, `rank`, `location`, `partition`, `mode`,
`mode_params`, `kind` (`smooth_render`/`strange_render`), `palette_group`, `cells`,
`families`, `p_ge4`, `p_ge3`, `above_bar` (`p_ge4 >= 0.5`), `spiral`, `p_spiral`,
`picture`, `pinned`; `solve run` adds `release_picture`, `release_autolevel`,
`release_geometry` (1280x720ss2).

`config` (`_config`): `n`; `force_fill`; `fine_bar`, `fine_bar_default` (null unbarred);
`fine_head`, `fine_weights`; `theme_bar`; `forced`, `forced_default`; `fold`,
`fold_default`; `spiral_cap`, `spiral_cap_default`; `mode_ceilings`,
`mode_ceilings_default` (`{mode: share}`); `augment`, `augment_default`,
`augment_depth`, `augment_seconds`; `theme`; `method`, `objective`, `order` (prose);
`bars` (`{mode: rule}`); `ceiling` `{k, k_default, kf, kf_default, cell_share,
family_share, allowance, floor, floor_rule, floor_is, group_cap, group_cap_rule,
group_cap_from, targets, target_rule}`; `sort_key`, `sort_key_named`; `mode_floor`,
`mode_floors`, `mode_floor_rule`, `mode_floor_natural`, `mode_floor_artificial`;
`modes`; `mode_policy`. Each `*_is` and `bars_are` (`fold_is`, `fine_bar_is`,
`fine_head_is`, `fine_weights_is`, `forced_is`, `theme_bar_is`, `mode_ceilings_is`,
`augment_is`) is a sentence saying what its sibling means.

## gallery.jsonl

`artifacts/curation/tentative/<stamp>/gallery.jsonl` (`curate solve record`), a row per
seat in order (`curation/tentative.py`'s `rows_of`): `schema` 1, `seat`, `key` (**the
picture's ID**), `alias` (shortest unambiguous prefix, ≥8), `mode`, `mode_params`,
`partition`, `cell`, `hue_family` (the leading ones), `cells`, `families`, `seated_for`,
`pinned`, `floor`, `floor_cells` (`mandated`, `holding`, `no`), `centered`, `spiral`,
`p_spiral`, `rank`, `p_ge4`, `location`, `picture`. `recipes.jsonl` beside it (published
records only) is `{schema, key, recipe}` per seat; `render --recipe <file> --key <alias>`
draws one.

## manifest.json

Beside it (`manifest_of`): `schema`, `stamp`, `taken_at`, `source_commit`; `solve`
`{name, record, taken_at, seconds, config, diversity, diversity_is, pins}` (`config`
whole, so `solve.config.force_fill` says it ran forced); `pool` `{stamp, stamp_is,
candidates, locations, reachable_clusters, refused, ledger_rows, ledger_path}` (`stamp`
a sha256 of the sorted keys); `seats` `{asked, filled, shortfall, recorded}`;
`shortfalls`; `counts` `{mode, hue_family, cell, partition, centered, spiral}`, each
`{value: seats}`.

## keep.jsonl

`artifacts/curation/tentative/keep.jsonl`, append-only (`tentative.py`'s `keep`,
`release`): `{schema, stamp, kept, at, reason}`, a stamp's last row deciding; kept seats
survive merge prunes. `curate solve record` appends `kept: true` unless `--no-keep`,
`curate solve release <stamp>` `kept: false`. `tentative.PUBLISHED` keeps the rest.

## page.json

The source of every inspection page's `index.html` beside it (`judges check`, `harvest
stats`, `curate candidate-ledger browse`, `curate solve trace`; `grid_page.py`'s
`document`). `--bundle DIR` copies the pair, pictures under `DIR/pictures/`.

`schema` `1`, `title`, `command` (cwd paths relative), `intro`, `sections` `[{heading,
note, table, tiles, legend, records}]`: `table` null or rows, header first; `tiles`
`[{picture, title, mark, band, caption}]` (`band` `best`, `worst` or empty; `caption`
`[[label, value]]`); `legend` `[[column, meaning]]`; `records` `[{file, joined_on, key,
note, row}]` (a `row` copied whole from `file`).

## Gallery page.json

A recorded gallery's page (`curate solve browse`, `record`; `tentative.py`'s `page`):
`schema`, `command`, `stamp`, `name`, `forced`, `seats`, `asked`, `missing` (no picture
here), `at_full` (release pictures), `full_regime`, `ordered_by`, `legend` `[[label,
meaning]]`, `rows` ([gallery.jsonl](#galleryjsonl)'s, plus `src`, `full`, `order`).

## counts.json

`artifacts/curation/trace/<stamp>/counts.json` (`curate solve trace`;
`curation/trace.py`'s `build`), beside a [page.json](#pagejson) and `files/`: verbatim
slices of each chain file (`gallery.jsonl` through `walk.jsonl`), the walk slice adding
one row of each unreached kind. `schema` `1`, `stamp`, `seats`, `broken_chains`
`[{seat, key, stopped_at}]`, `files` `{name: {source, rows, sliced}}`.

## walkthrough.json

`artifacts/walkthrough/walkthrough.json` (`walkthrough.py`'s `build`); each folder is a
bundle. `schema` `1`, `command`, `stamp`; `pages` `[{folder, title, made_by, command,
files, bytes}]` (`missing: true` if not run); `files` `[{name, source}]`; `renders`
`[{name, picture, seconds}]`; `help` (`help/`'s `--help` texts, `walkthrough.py`'s
`HELP`, e.g. `curate-solve-trace.txt`).

## check.json

`judges check` (`cli/judges_commands.py`'s `judges_check`) renders `data/judges/check.jsonl`
cases `{schema, name, key, from, recipe, expected, picture, reference_seconds}`
(`from` `<stamp>|<key>`; `picture` `{grid, cells}`, `[32, 18]` cells of mean `[r, g, b]`
0–255; seconds on `REFERENCE_BOX`) into `artifacts/judges/check/check.json`: `schema`
`2`, `cases`, `tolerance`, `picture_tolerance` (of 255), `picture_grid`,
`reference_box`, `missed`, `largest_gap`, `largest_picture_gap`, `load_seconds`
`{judge: seconds}`, `results` `[{name, key, picture_matches, picture_gap, scores_match,
seconds, reference_seconds, actual, missed}]`.

## render.json

`artifacts/walkthrough/render/render.json` (`walkthrough.py`'s `write_renders`): the
README's two render examples as JPEGs `RENDER_WIDTH` wide. `{schema, renders}`, each
`name` (`render`, `render-link`), `picture`, `command`, `rendered_at`, `shown_at`,
`seconds`.

## parameters.json

`artifacts/walkthrough/parameters.json` (`parameters.py`'s `describe`): `schema` `1`,
`settable_by`; `families` `{kind: {flag, degree, takes, note}}`; `walked_families`;
`frame` `{center_re, center_im, width, resolution, supersample, maxiter}`, each `{flag,
default, range, unsaid}`; `modes`, `default_mode` (`[{name, tier, production, identity,
params}]`, `params` `{name: {default, min, max, range}}`); `palette` `{knob: {flag,
default, range, says}}`; `colormaps` `[{name, kind}]`; `spec_only` `{key: meaning}`;
`flags` `[{flag, dest, group, default, choices, help}]`.

## The render spec

What `fractal-engine render <spec.json>` reads (`engine/src/spec.rs`'s `RenderSpec`);
unknown keys are refused. Required: `schema` (1), `family`, `resolution` (`[w, h]`),
`colormap` (a `palettes list` name), `output` (`.png`/`.jpg`). Optional: `viewport`
`{center_re, center_im, width}` (decimal strings; home view), `supersample` (1),
`maxiter`, `colormap_dir` (`data/palettes`), `palette`, `allow_unresolvable_in_f64`
(false), and one coloring: `mode` (`smooth`) with `params` `{name: number}`, or
`coloring`, or `style` `{name, interior, tone, projection, layers}`
([`data/styles/STACK.md`](data/styles/STACK.md)), whose `palette` holds only `mirror`,
`reverse`, `rolloff`.

`family.kind`: `mandelbrot`; `multibrot` (`degree` 3–6); `julia` (`degree` 2–6, `c`
`[re, im]`); `phoenix` (`c` `["0.5667","0.0"]`, `p` `["-0.5","0.0"]`, `z_prev` 0);
`phoenix_m` (`p`; pixel is `c`); `fractional_multibrot` (`degree` a **string** in [1.8,
5.0]; no home view, so `viewport` is required whole).

`palette` (`engine/src/coloring.rs`'s `Palette`): `gamma`, `cycles` (1, > 0); `phase`
(0, turns); `reverse`, `mirror` (false; `mirror` refused on cyclic); `transfer`
(`{"kind":"value"}`, `edge` with `weight` >= 0, `rank`; `value` only under itinerary);
`rolloff` (`none`, `soft_knee` with `knee` in [0, 1), `reinhard`, `aces`); `scale`
(`leveled` or `absolute`, which ignores `gamma`, `cycles`, `transfer`); `lambda` (1,
[0, 1]); `period` (1) and `knee` (null), absolute only.

`params`: `density` (stripe 6, smooth_stripe), `radius` (trap_circle 1.0,
smooth_trap_circle, direct_trap_ring), `sigma` (threads 0.15), `weight` (the five smooth_*
composites 0.85, threads 0.5; [0, 1]), `shift` (itinerary, tail_itinerary 0.5),
`threshold`, `opacity` (direct_trap_*). The curve is a coloring's `transform`; only a spec
reaches it, `phoenix_m` and `fractional_multibrot`.

## The explorer link

The website's `explorer/README.md` owns these keys; `engine/src/link.rs` parses them
against `engine/fixtures/link-cases.json`. `render-link` reads `v` (1–4), `dv` (deep,
1–3, needs `scale`; `engine/README.md`'s *`render-link`*), `f` (`mandelbrot`,
`multibrot3`–`6`, `julia`, `julia3`–`6`, `phoenix`, `phoenix_plane`), `cx`, `cy`, `px`,
`py`, `zx`, `zy`, `m` (17 modes: not `exp_smoothing`, `tail_itinerary`, `de`),
`density`, `radius`, `sigma`, `threshold`, `weight`, `opacity`, `shift`, `curve`, `x`,
`y`, `w`, `n` (50–2,000,000), `a` (`W:H`, 16:9), `p` (`twilight_shifted`), `level`
(`band_autolevel/v1:black,white,exponent,out0,out1`), the palette keys `gamma`,
`cycles`, `phase`, `reverse`, `mirror`, `transfer` (`edge:w`), `rolloff`
(`soft_knee:k`), `scale`, `lambda`, `period`, `knee` (booleans 0/1), and page state the
picture ignores: `panel`, `every`, `collection`, `modes`, `hue`.
