Styles: named layer stacks that capture the *feel* of a reference picture, one JSON
file per style, rendered with any colormap.

```
fractal-wallpapers style list
fractal-wallpapers style show floating_on_dreams
fractal-wallpapers style render floating_on_dreams --location <record.json> --colormap <any map>
fractal-wallpapers style render floating_on_dreams --manifest <records.jsonl> --out-dir <dir>
fractal-wallpapers style render <draft.json> --location <record.json>      # a draft, before it joins
fractal-wallpapers style sheet <sheet.png> <folder|picture|list.txt…>     # a labelled contact sheet
fractal-wallpapers style scout --out <scout.jsonl> [filters]               # seats (step 4)
fractal-wallpapers style tones <name> <pictures…>                          # tone check (step 5)
fractal-wallpapers style picker <plan.json>                                # a picker (step 6)
fractal-wallpapers style keep floating_on_dreams <picker>.choices.json     # save a picker's keeps
fractal-wallpapers style palettes glossy_spirals                          # a mode's palette set
fractal-wallpapers style knobs lit_petals                                  # its public knobs
fractal-wallpapers style render lit_petals --location <record.json> --knob light_angle=200
fractal-wallpapers style gallery                                           # rebuild custom-modes/
fractal-wallpapers style bundle                                            # the published modes, for a page
fractal-wallpapers style wasm-parity                                       # the WebAssembly module vs native
fractal-wallpapers style wasm-speed                                        # its frame time, one thread
fractal-wallpapers style sweep --out <dir> [names…]                        # the checker (below)
```

A style is several channels of **one** escape loop per sample (more through a channel's
`view`), each layer turning one into colour or light, stacked by blend and opacity. The
engine composites it (`engine/src/style.rs`); Python reads the file and writes the spec
(`src/fractal_wallpapers/styles.py`). **`STACK.md` here is the stack's reference**: every
channel, layer kind, blend, projection and member. `style-wasm/` runs the published
modes in a browser (`engine/README.md`'s *The style module*). `<name>.keeps.json` is the
renders Matt kept from a style's pickers (pictures in
`fractal-drive-sync/style-keeps/<name>/`), and `catalog.json` the custom-mode catalog.

`--location` takes a record as `render --location` reads it (`{family, viewport,
maxiter}`); `--colormap` defaults to the suggested map. Full size is 2560x1600 ss2,
`--draft` 1280x800 ss2. A render takes every core; `RAYON_NUM_THREADS=6` caps it, and at
six threads a full-size frame takes 10 to 110 s, each `view` about one render more: a
six-view stack ran about two minutes a full-size frame and over four on a parabolic or
phoenix seat, so its round one is drawn at `--draft`. Each view also holds its own
channel lanes for the whole frame: a full-size frame of the flame stacks (six to seven
loops) committed 2 to 3 GiB in one engine (item 039: `flame_veil_violet` 3.0,
`flame_wisp_spark` 2.0), which counts against the commit charge a test lane beside it
needs: beside a render run the lane is killed on commit charge (CLAUDE.md).

## The file

| key | what |
| --- | --- |
| `schema` | 1 |
| `name` | the file's name, and the stack's |
| `description` | one line: what the style looks like |
| `reference` | `{image, folder, made_with}`; images live in `fractal-drive-sync/style-refs/`, never in git |
| `suggested_colormap` | the map the stack was fitted with; any map renders |
| `reuses`, `adds` | the existing pieces it is built from; the engine primitives it added (often none) |
| `notes` | what it added and what its rounds taught (optional) |
| `public` | a published mode's knobs, `{"knobs": [...]}` (*Public knobs*) |
| `style` | the stack (`STACK.md`), handed to the engine untouched as the spec's `style` key |

## Public knobs

A published mode exposes three to five knobs in its file's `public` block:

```
{"name": "light_angle", "label": "Light direction", "what": "<one line a user reads>",
 "default": 135.0, "range": [45.0, 225.0],
 "set": ["/layers/*/light/azimuth", {"path": "/layers/14/opacity", "scale": 0.6, "offset": 0}]}
```

`default` is the kept version: every value a knob writes at its default is the stack's
own (`styles.check_public`). `range` spans what Matt kept without breaking the look, read
off a sweep of each knob's ends at a kept location, and **never past the size where a
large shape starts hiding the finer scales** (step 6). `set` is pointers into the stack
(list indices as numbers, `*` for every member), each written as `scale·value + offset`,
so one knob can move linked members together. `style render --knob NAME=VALUE` refuses
a name the style does not expose and a value outside its range.

## The catalog

`catalog.json` is one row per mode: style, reference, Matt's score (1–5), status
(`publish`, `drop`, `discarded`; absent until he rules), the published variant, the
keeps the page shows (`{keep, caption}`), the card's text, its **palette set**
(`palettes`, below), the old style names it answers to (`aliases`), and for a
published mode `public` (`{name, palette, knobs}`, `palette` the set's first). The
published variant is always the style file's default stack: a formulation Matt kept
over it became the default. Public names are proposals Matt may rename.
`style_catalog.check` holds the rows to the style files.

## Palette sets

**A custom render mode is a stack plus a palette set.** Styles with the same layers and
channels, differing only in palette or numbers, are one mode; a different structure is
another mode, even from the same item. Each entry of a row's `palettes` is a map with
the few values tuned for it, its keeps and its score (`style_palettes.py` has the
shape):

```
{"colormap": "copper_arms", "was": "copper_arms", "reference": "eventide-25.jpg",
 "values": {"/layers/3/color": {"palette": 0.72}, "/tone/median": 0.238, ...},
 "keeps": ["<keep id>", ...], "score": 3}
```

The first entry is the default and is the stack's own (no values); the mode's score is
its best entry's. A value is a pointer into the stack, as a knob's, and the number or
colour written there; a layer an entry does without is its `opacity` at 0.
`style render <mode> --colormap <map>` draws a map in the set with its values;
`style palettes <mode>` lists the set.

**Only picked palettes are saved** (Matt's rule): a map stays in a set only through a
kept tile (`palettes add --mode` puts it in for a round, unkept). `style keep` lays each
kept tile's map into the mode's set; a map no tile kept
leaves the library, `fractal-wallpapers palettes remove <map>` (its file, produced,
carrier and groups rows; refused while a kept palette or a live style draws in it). A
style merged into a mode keeps resolving under its old name (`styles.alias_of`): to its
entry, or to the mode's default when it kept nothing, so `style render`, `style keep`
and a picker's scoped rows (`golden_petals/locations`) still work.

The merges so far: `glossy_spirals` (item 036: violet_star_arms, golden_petals,
copper_arms, cream_tubes) and `smooth_bands` (item 031: council, crisis and dalooka;
forest_smooth and mandelbrot3_smooth kept nothing). Kept apart by structure:
`corkscrew_smooth` (a sheen layer more) and the flame families, whose members differ in
channels and layer kinds (028's `flame_veil_*`, 032's `flame_wisp_*`).

`style gallery` rebuilds `fractal-drive-sync/custom-modes/` (its `index.html` and the
downscaled `img/`, traced in `img/sources.json` so a rebuild redraws only what moved):
one card per mode with its palette swatches, a palette still in its first round dimmed;
a style with no row is listed under *not yet catalogued*. `style bundle`, which the
website writes as its `custom-modes.json`, carries each published mode's set (its kept
entries, values and all) for the page to cycle. **Re-drawing a shown keep**
under a changed default is a one-row picker: `style render` at the keep's location and
public palette, `style picker`, a choices file keeping it, `style keep`; then point the
catalog's `show` at the new id and rebuild `style bundle` and `style gallery`.

## Checking the library

`style sweep --out <dir>` is the checker a bug hunt runs, and anyone after an engine or
stack change: every style (or the names given) drawn at 320x200 at its first `--seats`
keeps (seeded gallery seats for a style with none), each public knob at both ends of its
range and each palette entry of its mode's set; `--gallery` draws every style at
`--seats` seeded gallery seats instead, places it was never tuned on (vary `--seed`). Each picture is checked as it lands and
flagged `failed` (the engine refused), `flat`, `washed`, `drowned`, `dead_knob` (both
ends byte-identical), `same_palette` (an entry drawing the default's pixels) or `slow`
(over eight times its style's median per sample); `style_sweep.FLAGS` has the
thresholds. It writes one folder of pictures per style, a contact sheet each under
`sheets/`, and `sweep.jsonl`, and exits 1 when anything is flagged. The whole library,
about 200 pictures, took under four minutes at six threads (`RAYON_NUM_THREADS=6`).
Read the sheets as well as the flags: a flag is a symptom, the sheet is the look. What
hunts found is `docs/qa-findings.md`.

## A new style from a reference image

**The goal of every style is the fractal feel** (Matt's rule). A render should promise
more detail if you zoomed in, and its structure should read as the fractal's own.
Frame-filling strokes with no tie to the set ("a few lines") fail even when they match
the reference: Matt scored 032's flame wisps 2/5 for this, and only `flame_wisp_frost`'s
phoenix seat, where the strands followed the set, scored 4.

The item that brings a picture says "new style from <image>". The engine runs itself at
below-normal priority; cap its threads with `RAYON_NUM_THREADS=6`, and background
`style render --manifest` and `style scout --max-ink`/`--thinnest` (minutes each). Items
before 030 copied `sheet.py` and `draft.sh` from one results folder to the next: use
`style sheet` and `style render --manifest … --draft` instead.

1. **Read the picture into layers.** Name its structure, what carries the vibe
   (lighting, banding, overlays), the background and the palette; write each as a layer
   (`STACK.md`) and say whether a channel, kind and blend that draw it exist. Most will.
   **Ask whether one escape loop reaches the picture's density**: a reference of
   accumulated density (a flame's veils, leaves edge to edge) needs several `view`s or a
   new primitive, and round one says so. Draft on hand-placed points or the atlas
   (`artifacts/atlas/<plane>/dots.json`); those reach a picker only by step 4's exception.
   **First ask whether an existing mode's stack already fits** (`style list`, the
   gallery's cards): the same layers and channels, only the map and a few numbers to
   tune. If one does, the result is **a new palette entry, not a new style**: author the
   map (step 3), admit it with `palettes add <map.json> --mode <mode>`, tune its values
   in the entry (*Palette sets*) on `style render <mode> --colormap <map>` drafts, and run
   steps 4 to 9 for the mode; the entry stays only if a tile in it is kept, and
   `palettes remove <map>` ends it if none is.
2. **Add a primitive only where one is missing**, in `engine/src/style.rs`, with a test,
   listed under `adds`; a function of one sample's channels, no neighbour reads. When the
   engine changed, `fractal-wallpapers identity <tag> --against <last tag>` must read 0
   differ (about seven minutes), and the style path's checks run (CLAUDE.md).
3. **Fit the palette with the lighting, not off the pixels**: the lights supply the
   near-whites, so a naively sampled map is too pale. Author the map as albedo
   (`data/palettes/README.md`), named after the style, and tune stack and map together on
   drafts (`style render <draft.json>` takes a style file from anywhere). Admit it with
   **`fractal-wallpapers palettes add <map.json>`** (`--replace` after a re-tune) before
   any `--manifest` run, and never move a map file a running render reads. It writes the
   map, its `palette_family_shares.csv` row and carrier rows, and names the nearest
   library maps. A new map can move `tests/test_curation_ceiling.py`'s pinned
   carrier-table reading: re-pin it, naming the map in its docstring (Matt's ruling).
4. **Scout the locations from the published galleries, never a spiral** (Matt's ruling):
   `fractal-wallpapers style scout --out <dir>/scout.jsonl --n 40 [filters]` draws
   seeded and stratified from `final139_general` (`--record` names others), passing over
   seats flagged `spiral` or too deep; filters are `--kind julia|plane`, `--degree`,
   `--partition`, `--mode` and `--max-p-spiral`. **Ink** is the share of the frame a
   half-pixel distance glow paints (`style_scout.PROBE`): dendrites read 0.003 to 0.025,
   lace 0.1 to 0.5, and a glow floods white above about 0.11. The galleries are
   lace-heavy (median 0.23, none under 0.03), so `--max-ink 0.10` keeps what a glow can
   draw and `--thinnest --probe-limit 200` the thinnest of a seeded 200. Drop by eye a
   `spiral: false` seat that still reads as a whirl. **`--spiral` turns the rule round,
   only when the reference itself is a spiral** (Matt's ruling, item 031): the draw keeps
   spiral-flagged seats alone. The galleries hold plenty (`final140_general2000` 201 of
   2000, most `julia:mandelbrot` and `mandelbrot`).

   **The one exception** (Matt's ruling): a style needing a structure the galleries lack,
   measured, may fill its row with hand-placed or atlas points that have it, measured the
   same way (`style scout --points <records.jsonl>` with `--max-ink`, or `--measure` for
   every row in order with its ink) and checked by eye to be non-spiral. Two rows at one
   self-similar point at two widths render alike: keep one.
5. **Hold the tonal balance.** Set the stack's `tone` to the reference's median and p10
   (`style tones <name>` prints them) and check renders with
   `fractal-wallpapers style tones <name> <pictures…>`. A picture **misses** when its
   median is over 0.03, p10 over 0.05 or p90 over 0.10 off, or its near-white or
   near-black share over 0.05 above the reference's (`styles.TONE_BAND`). The tone pass
   pins median and p10, so p90 tells the highlights: a stack whose every render misses
   p90 is re-tuned (narrower glows, less fog), not its locations dropped. Check at
   `--draft` (tones within ~0.01 of full size); `style tones` marks anything under 1280
   wide `DRAFT`.
6. **Round one: formulations and locations, about twenty tiles.** Keeps are sparse and
   Matt's kept variant was each time not the location row's formulation, so ask both:
   - **formulations**: four to six readings (the stack, its strongest variants, the
     stack without its headline addition) at the same two scouted seats, plus the
     closest named mode at one as the baseline;
   - **locations**: ten to twelve seats kept by eye from the scout's forty `--draft`s (one
     `style render --manifest … --draft` run of 10–15 minutes at four threads; give it a
     kill limit well past that).

   **Judge the look at `--draft` or larger**: at 640 wide a 2e-4 hair glow is a fifth of a
   pixel and reads as blur that is not there. `style sheet` lays drafts side by side.
   **A render must always look as if zooming in would show more detail** (Matt's rule):
   large shapes (a trap's big early entries, wide blades or discs) must never occlude the
   finer scales; drop or re-bound (`largest`) a stack that fails it. **A seam reads as
   ugly on an organic look** (`leaf_veins` was discarded for it): a `lines` overlay, a
   period sheet on the `lines` angle or a `light` at `period` 1 on the smooth count cut
   the frame along band seams. Keep one only where the reference has hard edges.

   Render with `style render` (`--manifest` into one folder per row, and per stack in the
   formulations row: a picture is named by seat and map, so a second stack drawn into the
   same folder replaces the first, which the command says as `REPLACED`; each render
   logged to `renders.jsonl` beside it), then `fractal-wallpapers style picker <plan.json>`
   (`style_picker.py`'s docstring has the plan's shape). It writes the JPEGs, a manifest
   whose rows are `"kind": "many"`, `"default": []`, and the sidecar `style keep` needs.
   **The report header carries one `pick: <manifest path>` line per picker** (from the
   repo root); that line, not `carry:` or the body, makes conductor offer the Pick button.
7. **Round two, once Matt's keeps are back: twelve tiles or fewer.** His kept
   formulations at his kept locations, and three or four library maps on them, each
   drafted first and dropped on a bullseye, a wash, or a tone miss.
8. Write `reference`, `reuses`, `adds`, `suggested_colormap` and `notes` into the file.
9. **Save Matt's keeps** after each round: `fractal-wallpapers style keep <name>
   <picker>.choices.json` writes `<name>.keeps.json` and copies the pictures, with the
   reference, to `fractal-drive-sync/style-keeps/<name>/`; a later round merges in.
   **One picker for a group of styles** scopes its row ids `<style>/<row>`
   (`council_smooth/locations`): `style keep <name>` takes only that style's rows (and any
   unscoped ones), so it runs once per style on the one choices file. A style merged into
   a mode keeps into the mode. Each kept tile's map joins the mode's palette set; a map
   no tile kept goes, `palettes remove <map>`.
10. **Catalogue it**: its `catalog.json` row (score and status as Matt gave them, keeps
    with captions, the card's text; a published mode its `public` name, palette and
    knobs), with `"palettes": []`, then `style palettes <name> --sync` to lay its keeps'
    maps in (the suggested map first; give each entry Matt's score) and `style gallery`.
    A later score or status change is an entry's score, the row's, and the gallery. When
    a new style's stack turns out to be an existing mode's, merge it (*Palette sets*).

### The per-image prompt

```
Goal: a new style from <image>, in fractal-drive-sync/style-refs/.
Name: <style_name>. The look, in a line: <what makes the picture>.
Structure it needs (optional): <e.g. thin sets: --max-ink 0.10; Julia sets only: --kind julia>.
  Lacking in the galleries? <yes: hand or atlas points via --points, per step 4's exception>.
  Reachable by one escape loop? (optional) <yes | no: density from several views or a new primitive>.
Keep / avoid (optional): <what must survive, what must not appear>.
Round: 1 | 2 with <picker>.choices.json (round 2: the kept formulations and locations).
The report header carries one `pick: <manifest path>` line per picker.
Follow data/styles/README.md's *A new style from a reference image*. Commit when done.
```

## What the styles taught

General lessons; the named style's `notes` hold the detail.

- A channel that is not structure, laid through the map whole, turns every map not in
  lightness order into a target: bend it by the fractal with `warp` (`yas`).
- Under a view without a bottom every frame-wide statistic is spent on the deep end:
  cut by `period`, read `de` in samples (`teal_tunnel`).
- A distance glow paints anything finer than a pixel solid, so a glow wants thin sets
  (`glow_filaments`).
- Under a tone target dimming does nothing: balance comes from glow widths, fog and a
  trap's coverage, never opacity (`glow_filaments`, `glossy_lobes`, `teal_filaments`).
- One disc is a target most orbits miss, a lattice one every orbit hits; one disc with no
  `spacing` strings pullbacks along the arms (`bronze_packing`, `gilded_orbs`). Keep `0`
  off every disc and read escapes only (`bronze_packing`).
- A gallery seat is a deep zoom: bound an entry trap by frame fraction, `largest` and
  `smallest` (`bronze_packing`, `shaded_blades`). A trap's shape is what it draws: discs
  pull back round, strips as blades and spiky stars (`shaded_blades`).
- p90 misses are fixed at the map's top end (`gilded_orbs`, `field_lines`); a wide
  cream stop floods a far field (`citadel`). What a named mode lacks is often the rank
  spend, and the cycle count is the reference's order (`seahorse_halo`).
- A light's `period` sets what one dome is, 1 corrugating and 2 doming a disc
  (`glossy_lobes`), but only with `rings` above 0: at `rings` 0 the normal is the slope
  alone, the same in every ring, and the period draws nothing. On lace, decoration colour
  comes from a cyclic map (`lit_petals`).
- A dark reference's black share is held in the gaps, not the ground (`shaded_blades`); a
  rank fog spends the map's top on the nearest tenth (`star_eye`).
- A structure the galleries lack comes from a trap, a family chosen for it, or hand
  seats, measured first: basins (`field_lines`), parabolic flowers (`ember_rose`),
  quasicircles (`star_eye`, `clockwork_rings`), far field (`flame_veil_blue`).
- One loop's level lines never cross; views at turned, scaled, shifted points cross as a
  flame's veils (`flame_veil_blue`). The same route gives density: five views of a
  dendrite's `de` filled a frame with crossing veins where one left gaps (a scratch run
  after `leaf_veins`, item 029; not yet a style).
- Smooth-count sheets through views are a few broad arcs, nesting as rings round the set
  however fine the period; a flame's fine strands are the `stripe` average's crests (a
  glow at power 10), which run along the field lines, across the level lines, and seven
  loops of them fill the frame (`flame_wisp_waves` and its four siblings). Far out the
  crests are near-straight rays; views narrower than the frame read nearer the set, where
  they curl. Like veils they need far field: on lace the set's own hair floods them.
- Streamlines over a whole frame are the stripe average's level lines through the map at
  a few cycles: they run along the field lines and are debanded, so they cross every
  escape band unbroken, where the `lines` channel's angle is cut at each band seam and
  draws fans (`crescent_lines`). Three cycles at density 6; at six a draft aliases, and
  at density 10 and over the average is noise near the set. A small minibrot is a seat
  the galleries lack: Newton on `f^p(0) = 0` places one (`crescent_lines`' notes).
- A smooth, heavily lit surface is a `light` on the frame's own smooth count at one band
  with no ring (`rings` 0, a `slope`): one glossy relief whose lace keeps every finer scale
  lit, so it never hides them (`molten_flow`, `chrome_orbs`). Lit scales want a ring:
  `rings` about 0.8 and a small `slope` at `period` 1 make each band a lit scale (at
  `rings` 0 the period draws nothing), and a bounded disc lattice domed at `period` 2
  over it is a cauliflower texture (`cauliflower_scales`). Fit its key in the albedo, not the tone pass: a
  pass that darkens a pale stack far casts gold olive, and a light's gain over about 1
  clips a red into gold (`molten_flow`).
- Glossy blades along a spiral's arms are one strip trap's entries lit `across` over that
  relief: one strip, not a lattice (a lattice fans shards over the whole frame), bounded
  0.015 to 0.08 frames and masked by the inverted smooth count so they live in the far
  field and the lace stays on top; unbounded they swallow it (`glossy_spirals`,
  item 036's six references; four palettes kept). On a dark reference the p90 misses are the blades'
  highlights: a saturated paint and spine glow, never a pale highlight, which reads steel
  (`violet_star_arms`).
- Holes at every scale are the set's interior, which the galleries' Julia seats lack (a
  hole probe, interior white over black, read 0 on every one; phoenix-classic seats hold
  interior but read as whirls): a Julia set at a hyperbolic centre (Newton on
  `f^p(0) = 0`) has round Fatou components at every scale, measured as hand seats. Lace
  that hugs them is the stripe average's crests at density 2 (a second density on the
  same loop draws as the first today: `docs/qa-findings.md`) masked by the inverted
  `de` over a dark ground (gamma 2 to 5); a light on `inside` at one band, `rings` 1, domes
  each hole as a glass bead, and `inside` through a palette at cycles 3 is a bullseye
  (`cream_lace`, `copper_mail`, `ember_plume` and `gold_arcs`, one stack in four maps;
  `bead_strands` adds the `inside` rim glow and the bead light).
