The Rust renderer: it makes every pixel this project shows. Python reaches it through
`src/fractal_wallpapers/engine.py` and nothing else.

```
cargo build --release --manifest-path engine/Cargo.toml
echo '{"schema":1,"family":{"kind":"phoenix"},"resolution":[1920,1080],
       "supersample":2,"mode":"smooth_stripe","colormap":"twilight_shifted",
       "output":"artifacts/phoenix.png"}' \
  | engine/target/release/fractal-engine render
```

Ten subcommands; all but `render-link` take one JSON object and write one file:

```
render      a location and a coloring → a PNG
dump-field  the same, stopping at the raw scalar field (+ a record of it)
recolor     a dumped field → a PNG, without iterating anything
expand      walk nodes → one rung each, gated, with a thumbnail per survivor
screen      frames you name → what each structural gate read, and its verdict
home-view   a family → where it is framed by default, and how that was derived
modes       the named colorings, as JSON
tiles       a plan of locations → training tiles, and a record of what was written
maxiter     widths → the iteration cap the depth policy gives each one
render-link an explorer link and a size → the wallpaper, its link embedded
```

The pipeline is `spec → family → iterate → field → coloring → resample`, one module a stage
(`src/lib.rs`). `src/spec.rs` documents the JSON; `FORMATS.md`'s *The render spec* lists
every key. `src/mode.rs` holds **twenty** named colorings (eight field, six composite, two
modulate, four direct); nineteen are tier `production` and `de` is `niche`, excluded from every
production draw by `mode::production_names` and `engine.production_modes()`.

The search — `rng`, `screen`, `foci`, `expand` — decides *where* to render, never *how*.
`expand` and `screen` share one `screen::Battery` (interior cap on a 128-pixel probe, the cap
on the node render, the escape band, the occupancy floor); a crate test asserts both give a
candidate the same fate. `foci::Frame` caches a parent's focus set and centroid, consuming no
random stream; `expand`'s `report_foci` (off, byte-identical off) reports the set.

## `render-link`: an explorer link, drawn without Python

```
fractal-engine render-link --link <URL|query> --size WxH [--ss N] [--out FILE.png|.jpg] [--data DIR]
```

`--ss` defaults to **3**, `--out` to `render-link.png`. The link is **embedded in the file**
(PNG `iTXt` and XMP; JPEG comment, XMP and EXIF), byte for byte what `curation/embed_link.py`
and the site's `stamp.js` write (`src/embed.rs`). stdout is `render`'s report plus `link`
(canonical query), `url`, `levelled`, `data`. Python: `engine.render_link`. Link keys:
`FORMATS.md`'s *The explorer link*.

**A link replays; nothing re-derives.** `src/link.rs` parses by `permalink.js` (`v=1`–`4`)
and `deep-link.js` (`dv=1`–`3`); `mode::tune` applies mode parameters;
`autolevel::curved_stops` replays `level=`. So a v3+ link omitting a derived parameter
(`weight`, `opacity`) is refused with the fix, `--size` must match the link's aspect (`a=`,
default 16:9), and a `curve` under a direct trap is refused.

**Data is found**: `--data DIR`, else `$FRACTAL_ENGINE_DATA`, else the first `data/` holding
`palettes/` and `anchors.jsonl` walking up from the working directory, then the executable.
The levelling band is compiled in from `data/coloring/levels_band.json`.

**The parse is the site's**: `fixtures/link-cases.json` carries the site's own answers (and
its generator); `link::tests::the_parsers_are_the_sites` holds every row. Against the pipeline
it is a tolerance (`tests/test_render_link.py`).

**Deep links are drawn by the explorer's own kernel.** A `dv=` link goes to
`deep::Perturbation`, over `../perturbation`, behind the default `deep` feature (off in the
website's `engine-wasm`; without it `link::NotBuilt` refuses), coloured by
`link::shade_lanes`. A link without `scale` is refused (the arrival fit is `fit.js`'s); the
reference orbit is at the view's centre; the cap is `n`, else the width's. `deep::tests` holds
native draws to `fixtures/deep-cases.json` (the website's `perturb-scalar.wasm`): mask and
counts exact, lanes within four ulps, pixels within one level.

`src/autolevel.rs`, `src/derive.rs` and `mode::tune`/`set`/`params_of` are copies of the
website's `explorer/engine-wasm`; each names the other.

## The cap is a policy, and one door still cannot name another

`maxiter::for_width` is the policy; an explicit `maxiter` wins
(`an_explicit_maxiter_wins_over_the_policy`) and travels with the picture: the ledger recipe
and the links' `n` (`curation/pins.py`'s `query_of` writes it only off-policy). **Except
`expand.rs`'s `Node`**, a centre and a width drawn at `for_width`.

## The escape loop is written out per family and per channel set

`iterate::run` collapses to the bare recurrence only when the call site sees **both** family
and channel set as constants. `field::sweep_row` constructs both fresh over the twelve
`field::Channels` sets times `family::over_written_out!`'s families; every catalogued mode
lands in the table, and two channels at once fall to the generic loop (same numbers, slower).
Worth 1.1x–2.45x.

**There is no benchmark**; three tests are the guard: `every_production_mode_takes_the_specialized_loop`,
`every_field_has_a_call_site_of_its_own`, and `debug_assert`s on the fallthrough and in
`gather`. `the_specialized_loop_is_the_generic_one_bit_for_bit` ties the paths. A render is
`sample` → `gather` → `sweep_row` a row at a time; `sweep_row` is `pub` for the site's wasm,
which draws a band of rows per worker.

**Interior samples skip the cap** where every field reads an escape (`smooth`, `discrete`,
`stripe`, `tia`, `curvature`, `threads`, `exp_smoothing`, `decomposition`, `de`):

- before the loop: the cardioid and period-2 bulb, and a disk inside the degree-3–6 main
  component, each with a `1e-3` margin;
- in the loop (`Wants::interior`, `iterate::Interior`, every sixteenth step): a disk about the
  Julia cycle proven to map into itself, and on every family an exact bit repeat (Brent);
- orbit-reading modes stop only at a repeat, where it makes the reading final
  (`FieldSpec::is_final_at_a_repeat`, `Interior::REPEAT`): minima/maxima, a full head address,
  an exact tail roll (`Symbols::rolls_exactly`). Means and direct traps iterate on.

All held byte-identical by `fractal-wallpapers identity` (and `--edges`) and
`the_interior_tests_move_no_sample`. At `ss = 1` the resample is skipped, chunked across
cores (`resample::encode_only` says why).

## Mode catalog rules

- **`itinerary`** opens at `z1` on dynamical planes (no pixel wedge) and `z0` on parameter
  planes; `start: "tail"` reads the last `depth` symbols (`Address::roll`), and
  `tail_itinerary` is one coloring on both planes.
- **A flat modulate texture is reported**: it is then `smooth` at `transfer: rank` bit for
  bit. `RenderReport.texture_flat` carries it; `curation.mode_policy.routed_mode` routes it as
  `smooth`. Only a render can tell (the texture is carried at `f64`).
- **A teaching field has no name**: `discrete` is drawn by `fractal-wallpapers render
  --discrete [CYCLE]`, guarded by `no_catalogued_mode_reads_a_teaching_field`.
- **A new coloring field must `skip_serializing_if` its default**: `renders.job_name` hashes
  the whole wire spec and names every cached picture.
- **A dumped field is named by `renders.field_job_name`** over `FIELD_IDENTITY`;
  `RECOLOR_MEMBERS` (`colormap`, `recipe`) is spent after. An unclassified `SPEC_MEMBERS` entry,
  or a field-side member with no value, raises (`tests/test_curation_colorize.py`).
- **A recolor is the render through every stage**: `coloring::toned` owns `Rolloff` for both
  `paint` and `recolor` (`tests/test_modes.py`).

## The direct traps: a blend from white is not a screen upside down

Four production modes make no field: `direct_trap::Painter::trace` composites a gradient
sample at every near miss. `direct_trap_multiply` multiplies from white and `_screen` screens
from black; they are symmetric in linear light only, so in Oklab the multiply is pale by
construction (in-mask chroma p50 0.011 against ~0.046 for the other three).

⚠ **Never gate on clip share; the measure is in-mask chroma.** Every compressive operator
(multiply from white, rolloff, gamma under 1, the autolevel band) drives clip share to zero on
a white surface.

**The fix is a mode-param variant, not an engine change**: `engine_spec.coloring_of` writes a
row's `opacity` and `threshold` into the coloring, so a variant is a new key and voids nothing;
editing `mode.rs`'s constants re-keys the mode and voids its verdicts. `opacity=0.4` buys
chroma at the least judge cost; the judge is biased against chroma where Matt's tiers are not.
The recipe key digests no arithmetic, so `engine_fingerprint.TRAP_PROBES` guards trap pixels.

## The colormap: stops on disk, a folded table in the engine

A `data/palettes` file is **control points**. `Colormap::from_stops_baked` interpolates them in
**OKLab** into a 4096-entry (`TABLE_SIZE`) linear-light table on every load; a lookup clamps,
never wraps. Compare maps by sampling through this, not stop lists (`palettes.groups.cloud`).
**Folding is at bake time** from `mirror` (`colormap::mirror`, `n` stops to `2n − 1`, the
opening colour repeated at `1.0`: `every_folded_map_closes_so_a_repeat_has_no_seam`).
Production folds exactly the non-cyclic maps (`models.palette_sets.recipe_for`); the engine
refuses to fold a cyclic one. A fold puts the ramp's far end at `t = 0.5`, so a lopsided field
never reaches it: `curation.palette_coverage` measures on pixels.

## The whole lib compiles to wasm32, and draws the same bytes

No `cfg(target_arch)`: rayon falls back to one thread, and a wasm consumer calls
`from_stops_baked` instead of `Colormap::load`. The site's `plan`, `compute_band` and `shade`
take the render spec plus the colormap by value, so a new family is not a new export.

### A coloring splits into a measure and a colouring, so a caller may band it

```
Spend::measure(field, transfer)       the frame-wide normalization, once
shade_samples(values, spend, …)       a run of samples through it
composite_samples(base, texture, …)   and the pair, and the modulate's
modulate_samples(base, texture, …)
```

`shade`/`composite`/`modulate` are a measure plus one whole-field band; `Spend` and its parts
serialize across workers (the website's `bands.test.mjs` holds bands to the whole frame).

### The colouring stages, and the two a palette may add before the stretch

```
compression   g = (ν^λ − 1)/λ, ln ν at λ = 0; with a knee, ν − 1 at and above it
scale         leveled: measure over g, then curve, gamma, cycles, phase
              absolute: frac(g/period + phase), nothing measured
bake          the map folded and/or reversed
lookup        the 4096-entry table, lerped
rolloff       on luminance
```

`Palette`'s `scale`, `lambda`, `period` and `knee` are omitted at defaults and never emitted
by the pipeline (`engine_spec.py`). Under absolute, gamma, cycles, transfer and curve do not
apply (`Spend::Absolute`); `knee` acts only there (`place_absolute`).

**Consumers pin by path** (the crate is `0.1.0`, never bumped); a build is identified by
`engine_fingerprint.py`.

## Styles: a layer stack over one orbit

The spec's `style` key draws through `src/style.rs`: one generic escape loop a sample, lanes
per field plus the style's channels — **gradient** (analytic from `z`, `dz`), **inside** (a
convergence count), **radial**, **bubble** (`style::bubble`, a disc read at the `hit`-th
entry). Each statistic is measured once, then composited per sample, so a band matches the
whole frame given its geometry and width. **tone** is a second measure, of the composite. A
`log_polar` **projection** (`src/projection.rs`) carries its Jacobian to `de` and the light.
`data/styles/README.md` owns kinds, channels, blends and how to make a style. **Lighting
exists only in a style's `light` layer**; named modes carry no normal-map shading.

## What each family's picture is symmetric under

No code folds a render; this is what `family.rs` implies. Multibrot (pixel `c`): `(d − 1)`-fold
rotation (`discovery.nucleus` folds on it). Julia (pixel `z₀`): `d`-fold, any `c`. Real
constants: reflection in the real axis. Phoenix: that reflection only when `c`, `p`, `z₋₁` are
all real; `p = 0` is a quadratic Julia set (`phoenix_with_zero_p_is_a_quadratic_julia`).

## The one family that only draws pictures

`fractional_multibrot`, `z^d + c` at non-integer `d` on the principal branch (`cpowf`): the
**seam** where an iterate crosses the cut is its subject. `d` runs 1.8
(`LOWEST_FRACTIONAL_DEGREE`) to 5.0; a whole number is refused. **Render-only**: `render` and
`dump-field` reach it; every other door refuses through `Family::is_render_only` and
`spec::render_only_refusal`, and `home_view()` is `None` (`tests/test_fractional_degree.py`).

## How deep `f64` goes

`Viewport::is_resolvable_in_f64` refuses where neighbouring sample centres tie
(`RESOLUTION_ULPS`, 4, of the frame's reach); `"allow_unresolvable_in_f64": true` opts past it
for `render`/`dump-field` only. It guards **coordinates only**: a case-dependent *fidelity wall*
(about `1e-4` to `1e-10`) lets rounding decide counts above it, undetected. `cpow`'s order is
the canonical identity, so other implementations disagree at degree ≥ 4. Perturbation serves
only `dv=` links; see `src/fractal_wallpapers/deep/README.md`.

## Home views

A render with no viewport, and a walk root, come home to `src/family.rs`'s table: **framing has
one owner**. Each row is one rule on the measured set (4001² grid, cap 4000, 16:9 with a
tenth of margin); Julia gets the whole plane. A row is added by re-running
`RAYON_NUM_THREADS=3 cargo test --release --manifest-path engine/Cargo.toml -- --ignored
the_measured_boxes_are_the_measurement --nocapture` (~100 s).
