The style compositor as WebAssembly: a custom mode drawn in a page by the engine's own
`style::measure`/`tile` split (`engine/README.md`'s *Styles: a layer stack over one orbit*).

## The style module: a custom mode in a page

`style-wasm/` is that split as a raw `wasm32-unknown-unknown` module (no wasm-bindgen,
JSON in, length-prefixed JSON or bare RGBA out), and `js/style-wasm.mjs` is its whole
glue, for a browser or Node:

```
cargo build --release --target wasm32-unknown-unknown --manifest-path style-wasm/Cargo.toml
   -> style-wasm/target/wasm32-unknown-unknown/release/style_wasm.wasm

open(request)               -> {ok, handle, maxiter, resolution, supersample, samples,
                                mirror, post (drawn whole: `frame`, never `tile`),
                                style (the stack as drawn)} | {ok: false, why}
measure(h, w, hgt, ss)      -> {ok, measured, supersample, tone: {b, g} | null,
                                interior_fraction}         zeros: the picture's own frame
tile(h, x, y, w, hgt)       -> RGBA, w·hgt·4 bytes, against the last measure; null: last_error()
frame(h)                    -> RGBA of the whole picture in one pass (the native path)
export_measure(h)           -> length-prefixed bytes: the measure report; null: last_error()
import_measure(h, ptr, len) -> measure's answer: the report taken as h's measures, unmeasured
recolour(h, ptr, len)       -> measure's answer + {recoloured, style, mirror}: h re-measured
                                under a new request from its kept frame | {ok: false, why}
close(h)
```

`last_error()` is a plain sentence, length-prefixed like the rest, never JSON. The glue's
`Picture` has them as `exportMeasure()` (a `Uint8Array`), `importMeasure(report)` and
`recolour(request)`.

**The shared measure**: one worker measures the picture and posts `exportMeasure()`'s bytes
(transferable); every other worker opens the same request, `importMeasure`s them, and only
tiles, its tiles the bytes a session measuring itself draws. A report names its picture (the
place, the stack as drawn, the map; not the size, so a preview's report shares too) and is
refused by a session of another. Its size is a few hundred bytes plus eight per valid sample
for each rank-spent layer (about 8 MB per such layer at 1280x800, supersample 1).

**The recolour**: `measure` keeps the frame's escape loop (every channel the stack reads,
per sample, about what the measure allocated; the next `measure`, an `importMeasure` or
`close` frees it). `recolour(request)` with another palette entry (its map and its `values`
over the stack) at the same place, size and knobs re-takes the measures from that frame
without iterating, the same bits as a fresh `measure`, and the session becomes the new
request's; `exportMeasure` then shares them. It refuses, leaving the session as it was, when
the request moves the place or size, or when its stack reads channels the kept frame did not
gather (an entry moving a trap's `largest` or a stroke's members, or turning off the only
layer reading a channel): measure afresh.
Colours, opacities above 0, a palette's settings, a light's, the tone and the post stage's
settings all recolour.

A **request** is the CLI's inputs, not the engine's spec: `{schema: 1, location, style,
knobs, settings, colormap, resolution, supersample}`. `location` is a record as
`style render --location` reads it (`family`, `viewport`, `maxiter`, a place's own
`projection` members); `style` is a stack; `knobs` its style file's `public.knobs` and
`settings` `{name: value}` inside their ranges; `colormap` a `data/palettes/<name>.json` file
whole. The module applies `style render`'s three rules (`src/lib.rs`'s docstring has them
and why) and hands the engine the spec as JSON text. Plain `f64` only: no `deep`.

**Progressive drawing**: `measure` a small frame of the same aspect, tile at full size against
it, then `measure()` at the picture's own size and tile again. `frame` costs one pass,
`measure()` plus tiles about two; a full frame takes seconds to over a minute on one thread.

## The bundle a page draws from

`fractal-wallpapers style bundle` writes it (default `artifacts/style-wasm/bundle.json`):
`{schema, modes: [{name, style, tier, palette, palettes, aliases, variant, what, knobs, stack,
shown: [{keep, caption, location, colormap, stack}]}], colormaps: {name: file}}`, one mode
per published row of `data/styles/catalog.json` (`style_wasm.bundle`'s docstring). `tier` is
`curated` (the *Custom* list) or `lab` (*Custom (lab)*); a lab mode's `knobs` may be empty,
and a shown example has no `keep` (a draft's place, drawn with the mode's own stack).
`palettes` is `[{colormap, was, values, rests, score}]`, the mode's own map first (values `{}`,
there whether or not a keep was drawn in it) and then each kept entry; the page writes `values` over `stack` at their
pointers (`style_palettes.apply`) before opening a session, and switches entries with
`recolour`. `rests` is `{knob: value}` where a knob rests off its `default` on that entry:
the entry's tuned first member read back through the knob (`style_palettes.knob_rest`, the
website's `knobRest`), always inside the knob's range, so a slider moved off the entry can
come back to its picture. `aliases` are old style names merged into the mode (`styles.alias_of`): a link
naming one opens the entry whose `was` it is, else the mode's default. A shown keep carries the stack it
was drawn with.

## Parity: which run is owed

`style wasm-parity` and `style wasm-speed` hold the module to the native engine under Node
(`style_wasm.py`). The whole run is about 71 minutes at its default three workers, the
render pool's count and its cap (six threads with the native side; 357 jobs, 107's reading,
the module's side the bound: 223 jobs read 38 to 48 minutes before the showcase's Examples): a detached run of its own, so owe it only where
nothing cheaper covers the change. What a change owes, after its last code edit:

| The change | Owed |
|---|---|
| Docs, tests, catalog metadata (`score`, `tier`, captions), a palette entry's values | nothing beyond the fast lane: no job reads them (below) |
| A name list both engines read on a knob's write (`styles.INTEGER_MEMBERS` and `src/lib.rs`'s twin) | `tests/test_style_wasm.py` plus `style wasm-parity --member <name>` per name added or removed: the modes whose knobs write it (none: nothing owed) |
| One style's stack, knobs or a new `show` | `style wasm-parity <name>` |
| An engine member no other stack sets | `identity` (0 differ) plus `style wasm-parity <name>` for the style setting it |
| Any other engine or module code | the whole run |

The native side draws beside the workers (`style_wasm.PARITY_WORKERS` and
`PARITY_NATIVE_THREADS` have the counts and what bounds the run; never shorter than its
longest job, one keep's tiled draw). A clean whole run is all identical but five, all
multi-view flame stacks: `flame_veil_chalk__1` reads one pixel one step off (on main since
063's reading); the showcase's Examples add `flame_veil_blue__2` (13 pixels, worst step 2)
and `flame_veil_chalk__3`, `__4`, `__5` (11, 455 and 7 pixels; worst 1, 12, 1), 107's
reading, the same divergence at deeper seats (a module item, not a catalog one).
`flame_veil_teal__0__knobs`, a sixth, left with its mode in 107. Any other miss is the change. A mode's jobs are its shown keeps (`style_catalog.shown_of`), not its
palette entries: an entry's new values or a new entry moves no job, a new `show` does. A
draft not yet in `data/styles/` is checked with its job list (`style_wasm.request`, `run_node`, `native_rgb`,
`compare`).
