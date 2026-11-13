The Rust renderer: it makes every pixel this project shows. Python reaches it through
`src/fractal_wallpapers/engine.py` and nothing else.

```
cargo build --release --manifest-path engine/Cargo.toml
echo '{"schema":1,"family":{"kind":"phoenix"},"resolution":[1920,1080],
       "supersample":2,"mode":"smooth_stripe","colormap":"twilight_shifted",
       "output":"artifacts/phoenix.png"}' \
  | engine/target/release/fractal-engine render
```

Ten subcommands. All but `render-link` and `modes` read one JSON spec and print a JSON
report; `render`, `dump-field`, `recolor` and `render-link` write the picture, and
`expand`, `screen` and `tiles` write thumbnails or tiles:

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

The search (`rng`, `screen`, `foci`, `expand`) decides *where*, never *how*.
`expand` and `screen` share one `screen::Battery` of gates, so a candidate meets the same fate
in both. `expand`'s `report_foci` (off by default, byte-identical off) reports a parent's
focus set (`foci::Frame`, consuming no random stream).

## `render-link`: an explorer link, drawn without Python

```
fractal-engine render-link --link <URL|query> --size WxH [--ss N] [--out FILE.png|.jpg] [--data DIR]
```

`--ss` is **3** by default, `--out` `render-link.png`. The link is **embedded**
(PNG `iTXt`/XMP; JPEG comment/XMP/EXIF) as `curation/embed_link.py` and the site's
`stamp.js` write it (`src/embed.rs`). stdout is `render`'s report plus `link`
(canonical query), `url`, `levelled`, `data`. Python: `engine.render_link`; keys:
`FORMATS.md`'s *The explorer link*.

**A link replays; nothing re-derives.** `src/link.rs` parses by `permalink.js` (`v=1`–`4`)
and `deep-link.js` (`dv=1`–`3`); `mode::tune` applies mode parameters;
`autolevel::curved_stops` replays `level=`. So a v3+ link omitting a derived parameter
(`weight`, `opacity`) is refused with the fix, `--size` must match the link's aspect (`a=`,
default 16:9), and a `curve` under a direct trap is refused.

**Data is found**: `--data DIR`, else `$FRACTAL_ENGINE_DATA`, else the first `data/` with
`palettes/` and `anchors.jsonl` up from the working directory, then the executable.
The levelling band is compiled in from `data/coloring/levels_band.json`.

**The parse is the site's**: `link::tests::the_parsers_are_the_sites` holds its answers in
`fixtures/link-cases.json` (`tests/test_render_link.py`, a tolerance, the pipeline).

**Deep links are drawn by the explorer's own kernel.** A `dv=` link goes to
`deep::Perturbation`, over `../perturbation`, behind the default `deep` feature (off in the
website's `engine-wasm`; without it `link::NotBuilt` refuses), coloured by
`link::shade_lanes`. A link without `scale` is refused; the
reference orbit is the view's centre; the cap is `n`, else the width's. `deep::tests` holds
native draws to the website's answers in `fixtures/deep-cases.json`.

`src/autolevel.rs`, `src/derive.rs` and `mode::tune`/`set`/`params_of` copy the site's
`explorer/engine-wasm`.

## The cap is a policy, and one door still cannot name another

`maxiter::for_width` is the policy; an explicit `maxiter` wins and travels with the picture:
the ledger recipe and the links' `n` (`curation/pins.py`'s `query_of` writes it only
off-policy). **Except `expand.rs`'s `Node`**, a centre and a width drawn at `for_width`.

## The escape loop is written out per family and per channel set

`iterate::run` collapses to the bare recurrence only when the call site sees **both** family
and channel set as constants, so `field::sweep_row` writes out the twelve `field::Channels`
sets times `family::over_written_out!`'s families; two channels at once fall to the generic
loop (same, slower). **There is no benchmark**: the guards are
`every_production_mode_takes_the_specialized_loop`, `every_field_has_a_call_site_of_its_own`,
`debug_assert`s on the fallthrough and in `gather`, and
`the_specialized_loop_is_the_generic_one_bit_for_bit`. A render is `sample` → `gather` →
`sweep_row` a row at a time; `sweep_row` is `pub` for the site's wasm workers (a band each).

**Interior samples skip the cap** where every field reads an escape (`smooth`, `discrete`,
`stripe`, `tia`, `curvature`, `threads`, `exp_smoothing`, `decomposition`, `de`): before the
loop, the cardioid, period-2 bulb and a disk inside the degree-3–6 main component (`1e-3`
margin); in the loop (`iterate::Interior`, every sixteenth step), a disk about a Julia cycle
proven to map into itself and, on every family, an exact bit repeat (Brent). Orbit-reading
modes stop only at a repeat that makes the reading final (`FieldSpec::is_final_at_a_repeat`);
means and direct traps iterate on. All held byte-identical by `fractal-wallpapers identity`
(and `--edges`) and `the_interior_tests_move_no_sample`. At `ss = 1` the resample is skipped,
chunked across cores (`resample::encode_only` says why).

## Mode catalog rules

- **`itinerary`** opens at `z1` on dynamical planes and `z0` on parameter planes;
  `start: "tail"` reads the last `depth` symbols (`Address::roll`).
- **A flat modulate texture is reported** (`RenderReport.texture_flat`): it is then `smooth`
  at `transfer: rank` bit for bit, and `curation.mode_policy.routed_mode` routes it so.
- **A teaching field has no name**: `discrete` is drawn by `fractal-wallpapers render
  --discrete [CYCLE]` (`no_catalogued_mode_reads_a_teaching_field`).
- **A new coloring field must `skip_serializing_if` its default**: `renders.job_name` hashes
  the whole wire spec and names every cached picture.
- **A dumped field is named by `renders.field_job_name`** over `FIELD_IDENTITY`;
  `RECOLOR_MEMBERS` is spent after; an unclassified `SPEC_MEMBERS` entry raises
  (`tests/test_curation_colorize.py`).
- **A recolor is the render through every stage**: `coloring::toned` owns `Rolloff` for both
  `paint` and `recolor`.

## The direct traps: a blend from white is not a screen upside down

Four production modes make no field: `direct_trap::Painter::trace` composites a gradient
sample at every near miss. `direct_trap_multiply` (from white) and `_screen` (from black) are
symmetric in linear light only, so in Oklab the multiply is pale by construction.
⚠ **Never gate on clip share; the measure is in-mask chroma**: every compressive operator
drives clip share to zero on a white surface.

**A fix is a mode-param variant** (`opacity`, `threshold`, written by
`engine_spec.coloring_of`), a new key voiding nothing; editing `mode.rs`'s constants re-keys
the mode and voids its verdicts. `engine_fingerprint.TRAP_PROBES` guards trap pixels.

## The colormap: stops on disk, a folded table in the engine

A `data/palettes` file is **control points**. `Colormap::from_stops_baked` interpolates them in
**OKLab** into a 4096-entry (`TABLE_SIZE`) linear-light table on every load; a lookup clamps,
never wraps; compare maps by sampling through it (`palettes.groups.cloud`). **Folding is at
bake time** from `mirror` (`colormap::mirror`, `n` stops to `2n − 1`, closing on the opening
colour). Production folds exactly the non-cyclic maps (`models.palette_sets.recipe_for`); the
engine refuses to fold a cyclic one. A fold puts the ramp's far end at `t = 0.5`, so
`curation.palette_coverage` measures on pixels.

## The whole lib compiles to wasm32, and draws the same bytes

No `cfg(target_arch)`: rayon falls back to one thread, and a wasm consumer calls
`from_stops_baked` instead of `Colormap::load`. The site's `plan`, `compute_band` and `shade`
take the render spec plus the colormap by value, so a new family is not a new export.

**A coloring splits into a measure and a colouring, so a caller may band it**:
`Spend::measure(field, transfer)` is the frame-wide normalization, once; `shade_samples`,
`composite_samples` and `modulate_samples` run samples through it. `shade`/`composite`/
`modulate` are a measure plus one whole-field band; `Spend` serializes across workers. The
colouring stages:

```
compression   g = (ν^λ − 1)/λ, ln ν at λ = 0; with a knee, ν − 1 at and above it
scale         leveled: measure over g, then curve, gamma, cycles, phase
              absolute: frac(g/period + phase), nothing measured
bake          the map folded and/or reversed
lookup        the 4096-entry table, lerped
rolloff       on luminance
```

`Palette`'s `scale`, `lambda`, `period` and `knee` are omitted at defaults and never emitted
by the pipeline. Under absolute, gamma, cycles, transfer and curve do not apply; `knee` acts
only there. The lane is `f32`, so a short absolute `period` bands at large `ν`: compress first.

**Consumers pin by path** (the crate is `0.1.0`, never bumped); a build is identified by
`engine_fingerprint.py`.

## Styles: a layer stack over one orbit

The spec's `style` key draws through `src/style.rs`: one generic escape loop a sample, lanes
per field plus the style's channels (`data/styles/STACK.md` owns kinds, channels and blends,
`data/styles/README.md` how to make a style). A field read through a **view** (`style::View`)
runs one more escape loop per sample at the moved point. Each statistic is measured once, then
composited per sample, so a band matches the whole frame; **tone**
is a second measure, of the composite. A `log_polar` **projection** (`src/projection.rs`)
carries its Jacobian to `de` and the light. **Lighting exists only in a style's `light`
layer**; named modes carry no normal-map shading.

The two halves are public, so a frame can be drawn in pieces: `style::measure` (every
frame-wide statistic and the tone curve, as `Measures`), `style::tile` (output pixels of a
crop, with its Lanczos apron, against them) and `style::paint` (both at once, the native
`render`). Tiles against `measure` of the frame itself stitch to `paint`'s picture byte for
byte (`tiles_stitch_to_the_whole_picture`).

### The style module: a custom mode in a page

`../style-wasm/` is that split as a raw `wasm32-unknown-unknown` module (no wasm-bindgen,
JSON in, length-prefixed JSON or bare RGBA out), and `style-wasm/js/style-wasm.mjs` is its
whole glue, for a browser or Node:

```
cargo build --release --target wasm32-unknown-unknown --manifest-path style-wasm/Cargo.toml
   -> style-wasm/target/wasm32-unknown-unknown/release/style_wasm.wasm

open(request)               -> {ok, handle, maxiter, resolution, supersample, samples,
                                mirror, style (the stack as drawn)} | {ok: false, why}
measure(h, w, hgt, ss)      -> {ok, measured, supersample, tone: {b, g} | null,
                                interior_fraction}         zeros: the picture's own frame
tile(h, x, y, w, hgt)       -> RGBA, w·hgt·4 bytes, against the last measure; null: last_error()
frame(h)                    -> RGBA of the whole picture in one pass (the native path)
close(h)
```

A **request** is the CLI's inputs, not the engine's spec: `{schema: 1, location, style,
knobs, settings, colormap, resolution, supersample}`. `location` is a record as
`style render --location` reads it (`family`, `viewport`, `maxiter`, a place's own
`projection` members); `style` is a stack; `knobs` its style file's `public.knobs` and
`settings` `{name: value}` inside their ranges; `colormap` a `data/palettes/<name>.json` file
whole. The module applies `style render`'s three rules (`style-wasm/src/lib.rs`'s docstring
has them and why) and hands the engine the spec as JSON text. Plain `f64` only: no `deep`.

**Progressive drawing**: `measure` a small frame of the same aspect, tile at full size against
it, then `measure()` at the picture's own size and tile again. `frame` costs one pass,
`measure()` plus tiles about two; a full frame takes seconds to over a minute on one thread.

`fractal-wallpapers style bundle` writes what a page draws from (default
`artifacts/style-wasm/bundle.json`): `{schema, modes: [{name, style, tier, palette,
palettes, variant, what, knobs, stack, shown: [{keep, caption, location, colormap,
stack}]}], colormaps: {name: file}}`, one mode per published row of
`data/styles/catalog.json` (`style_wasm.bundle`'s docstring). `tier` is `curated` (the
*Custom* list) or `lab` (*Custom (lab)*); a lab mode's `knobs` may be empty, and a shown
example has no `keep` (a draft's place, drawn with the mode's own stack). `palettes` is
`[{colormap, values, score}]`; the page
writes `values` over `stack` at their pointers (`style_palettes.apply`) before opening a
session. A shown keep carries the stack it was drawn with. `style wasm-parity` and `style
wasm-speed` hold the module to the native engine under Node (`style_wasm.py`).

## What each family's picture is symmetric under

No code folds a render. Multibrot (pixel `c`): `(d − 1)`-fold rotation (as
`discovery.nucleus` folds). Julia (pixel `z₀`): `d`-fold. Real constants: reflection in the real axis (for
phoenix, only when `c`, `p`, `z₋₁` are all real; at `p = 0` it is a quadratic Julia set).

## The one family that only draws pictures

`fractional_multibrot`, `z^d + c` at non-integer `d` on the principal branch (`cpowf`), the
seam at the cut its subject. `d` runs 1.8 (`LOWEST_FRACTIONAL_DEGREE`) to 5.0; a whole number
is refused. **Render-only**: only `render` and `dump-field` reach it (`Family::is_render_only`,
`spec::render_only_refusal`), and `home_view()` is `None`.

## How deep `f64` goes

`Viewport::is_resolvable_in_f64` refuses where neighbouring sample centres tie
(`RESOLUTION_ULPS`, 4, of the frame's reach); `"allow_unresolvable_in_f64": true` opts past it
for `render`/`dump-field` only. It guards **coordinates only**: above a case-dependent
*fidelity wall* (about `1e-4` to `1e-10`) rounding decides counts, undetected. `cpow`'s order
is the canonical identity. Perturbation serves only `dv=` links
(`src/fractal_wallpapers/deep/README.md`).

## Home views

A render with no viewport, and a walk root, come home to `src/family.rs`'s table: **framing has
one owner**, a measured rule a row (Julia gets the whole plane). A row is added by re-running
`RAYON_NUM_THREADS=3 cargo test --release --manifest-path engine/Cargo.toml -- --ignored
the_measured_boxes_are_the_measurement --nocapture` (~100 s).
