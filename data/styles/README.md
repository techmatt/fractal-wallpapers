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
fractal-wallpapers style knobs lit_petals                                  # its public knobs
fractal-wallpapers style render lit_petals --location <record.json> --knob light_angle=200
fractal-wallpapers style gallery                                           # rebuild custom-modes/
fractal-wallpapers style bundle                                            # the published modes, for a page
fractal-wallpapers style wasm-parity                                       # the WebAssembly module vs native
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
six threads a full-size frame takes 10 to 110 s, each `view` about one render more.

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
keeps the page shows (`{keep, caption}`), the card's text, and for a published mode
`public` (`{name, palette, knobs}`). The published variant is always the style file's
default stack: a formulation Matt kept over it became the default. Public names are
proposals Matt may rename. `style_catalog.check` holds the rows to the style files.

`style gallery` rebuilds `fractal-drive-sync/custom-modes/` (its `index.html` and the
downscaled `img/`, traced in `img/sources.json` so a rebuild redraws only what moved);
a style with no row is listed under *not yet catalogued*. **Re-drawing a shown keep**
under a changed default is a one-row picker: `style render` at the keep's location and
public palette, `style picker`, a choices file keeping it, `style keep`; then point the
catalog's `show` at the new id and rebuild `style bundle` and `style gallery`.

## A new style from a reference image

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
   `spiral: false` seat that still reads as a whirl.

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

   Render with `style render` (`--manifest` into one folder per row; each render logged
   to `renders.jsonl` beside it), then `fractal-wallpapers style picker <plan.json>`
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
10. **Catalogue it**: its `catalog.json` row (score and status as Matt gave them, keeps
    with captions, the card's text; a published mode its `public` name, palette and
    knobs), then `style gallery`. A later score or status change is the same two steps.

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
- A light's `period` sets what one dome is: 1 corrugates, 2 domes a disc, 3 a petal
  (`glossy_lobes`, `lit_petals`). On lace, decoration colour comes from a cyclic map
  (`lit_petals`).
- A dark reference's black share is held in the gaps, not the ground (`shaded_blades`); a
  rank fog spends the map's top on the nearest tenth (`star_eye`).
- A structure the galleries lack comes from a trap, a family chosen for it, or hand
  seats, measured first: basins (`field_lines`), parabolic flowers (`ember_rose`),
  quasicircles (`star_eye`, `clockwork_rings`), far field (`flame_veil_blue`).
- One loop's level lines never cross; views at turned, scaled, shifted points cross as a
  flame's veils (`flame_veil_blue`). The same route gives density: five views of a
  dendrite's `de` filled a frame with crossing veins where one left gaps (a scratch run
  after `leaf_veins`, item 029; not yet a style).
