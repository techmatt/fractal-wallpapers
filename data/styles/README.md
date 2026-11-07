Styles: named layer stacks that capture the *feel* of a reference picture, one JSON
file per style, rendered with any colormap.

```
fractal-wallpapers style list | show <name> | knobs <mode> | palettes <mode>
fractal-wallpapers style render <name|draft.json> --location <record.json> [--colormap <map>] [--knob K=V]
fractal-wallpapers style render <name> --manifest <records.jsonl> --out-dir <dir> [--draft]
fractal-wallpapers style sheet <sheet.png> <folder|picture|list.txt…>   # a labelled contact sheet
fractal-wallpapers style scout --out <scout.jsonl> [filters]             # seats (step 4)
fractal-wallpapers style tones <name> <pictures…>                        # tone check (step 5)
fractal-wallpapers style picker <plan.json>                              # a picker (step 6)
fractal-wallpapers style keep <name> <picker>.choices.json               # save a picker's keeps
fractal-wallpapers style gallery | bundle                                # custom-modes/; the page's modes
fractal-wallpapers style wasm-parity | wasm-speed                        # WebAssembly vs native; frame time
fractal-wallpapers style sweep --out <dir> [names…]                      # the checker (below)
```

A style is a stack of layers over the channels of one escape loop, composited by
`engine/src/style.rs` from the spec `styles.py` writes; **`STACK.md` here is the stack's
reference**. `style-wasm/` runs the published modes in a browser (`engine/README.md`'s
*The style module*). `<name>.keeps.json` is what Matt kept from a style's pickers
(pictures in `fractal-drive-sync/style-keeps/<name>/`); `catalog.json` is the catalog.

`--location` takes a record as `render --location` reads it (`{family, viewport,
maxiter}`); `--colormap` defaults to the suggested map. Full size is 2560x1600 ss2,
`--draft` 1280x800 ss2. A render takes every core (`RAYON_NUM_THREADS=6` caps it); a
full-size frame takes 10 to 110 s at six, each `view` about one render more, and a
six-view stack commits 2 to 3 GiB, so its round one is drawn at `--draft`.

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
published variant is always the style file's default stack. Public names are proposals
Matt may rename. `style_catalog.check` holds the rows to the style files.

## Palette sets

**A custom render mode is a stack plus a palette set.** Styles with the same layers and
channels, differing only in palette or numbers, are one mode; a different structure is
another mode. Each entry of a row's `palettes` is a map with the few values tuned for
it, its keeps and its score (`style_palettes.py` has the shape):

```
{"colormap": "<map>", "was": "<old style name>", "reference": "<image>",
 "values": {"/layers/3/color": {"palette": 0.72}, "/tone/median": 0.238, ...},
 "keeps": ["<keep id>", ...], "score": 3}
```

The first entry is the default, the stack's own (no values); the mode's score is its
best entry's. A value is a knob-style pointer and what is written there (a layer an
entry drops is its `opacity` at 0); `style render <mode> --colormap <map>` applies them.

**Only picked palettes are saved** (Matt's rule): a map stays in a set only through a
kept tile (`palettes add --mode` puts it in for a round, unkept). `style keep` lays each
kept tile's map into the mode's set; a map no tile kept leaves the library by
`fractal-wallpapers palettes remove <map>` (its file, produced, carrier and groups rows;
refused while a kept palette or a live style draws in it). A style merged into a mode
keeps resolving under its old name (`styles.alias_of`): to its entry, or to the mode's
default when it kept nothing, so `style render`, `style keep` and a picker's scoped rows
still work.

`style gallery` rebuilds `fractal-drive-sync/custom-modes/` (`index.html` and `img/`,
traced in `img/sources.json` so a rebuild redraws only what moved), one card per mode.
`style bundle` (the website's `custom-modes.json`) carries each published mode's kept
entries. **Re-drawing a shown keep**
under a changed default is a one-row picker: `style render` at the keep's location and
public palette, `style picker`, a choices file keeping it, `style keep`; then point the
catalog's `show` at the new id and rebuild `style bundle` and `style gallery`.

## Checking the library

`style sweep --out <dir>` is the checker after an engine or stack change: every style
(or those named) at `--resolution` (320x200 default) at its first `--seats` keeps
(seeded gallery seats if none; `--gallery` for those always, vary `--seed`), each public
knob at both ends and each palette entry. It flags per `style_sweep.FLAGS` (`tone_miss`
only with `--tones` at 1280 wide or more), writes a folder and a contact sheet
(`sheets/`) per style and `sweep.jsonl`, and exits 1 on any flag. Read the sheets too: a
flag is a symptom, the sheet is the look. What hunts found is `docs/qa-findings.md`.

## A new style from a reference image

**The goal of every style is the fractal feel** (Matt's rule). A render should promise
more detail if you zoomed in, and its structure should read as the fractal's own.
Frame-filling strokes with no tie to the set fail even when they match the reference.

The item that brings a picture says "new style from <image>". Cap the engine with
`RAYON_NUM_THREADS=6` and background `style render --manifest` and `style scout
--max-ink`/`--thinnest` (minutes each).

1. **Read the picture into layers**: its structure, what carries the vibe (lighting,
   banding, overlays), the background and the palette, each as a layer (`STACK.md`), and
   whether a channel, kind and blend that draw it exist. **Ask whether one escape loop
   reaches its density**: accumulated density (a flame's veils, leaves edge to edge)
   needs several `view`s or a new primitive, and round one says so. Drafts may use
   atlas points (`artifacts/atlas/<plane>/dots.json`), a picker only by step 4's
   exception. **First ask whether an existing mode's stack already fits**
   (`style list`, the gallery's cards). If one does, the result is **a new palette
   entry, not a new style**: author the map (step 3), admit it with `palettes add
   <map.json> --mode <mode>`, tune its values (*Palette sets*) on `style render <mode>
   --colormap <map>` drafts, and run steps 4 to 9 for the mode; the entry stays only if
   a tile in it is kept.
2. **Add a primitive only where one is missing**, in `engine/src/style.rs`, with a test,
   listed under `adds`; a function of one sample's channels, no neighbour reads. When the
   engine changed, `fractal-wallpapers identity <tag> --against <last tag>` must read 0
   differ (about seven minutes), and the style path's checks run (CLAUDE.md).
3. **Fit the palette with the lighting, not off the pixels**: the lights supply the
   near-whites, so a sampled map is too pale. Author the map as albedo
   (`data/palettes/README.md`), named after the style, and tune stack and map together on
   drafts. Admit it with **`fractal-wallpapers palettes add <map.json>`** (`--replace`
   after a re-tune) before any `--manifest` run (it writes the map, its share and carrier
   rows, and names the nearest library maps); never move a map a running render reads. It can move `tests/test_curation_ceiling.py`'s
   pinned carrier-table reading: re-pin it, naming the map in its docstring (Matt's ruling).
4. **Scout the locations from the published galleries, never a spiral** (Matt's ruling):
   `style scout --out <dir>/scout.jsonl --n 40 [filters]` draws seeded and stratified
   from `tentative.DEFAULT` (`--record` names others), passing over seats flagged
   `spiral` or too deep; filters are `--kind julia|plane`, `--degree`, `--partition`,
   `--mode` and `--max-p-spiral`. **Ink** is the share of the frame a half-pixel distance
   glow paints (`style_scout.PROBE`): dendrites read 0.003 to 0.025, lace 0.1 to 0.5, and
   a glow floods white above about 0.11. The galleries are lace-heavy (median 0.23, none
   under 0.03), so `--max-ink 0.10` keeps what a glow can draw and `--thinnest
   --probe-limit 200` the thinnest of a seeded 200. Drop by eye a `spiral: false` seat
   that still reads as a whirl. **`--spiral`** keeps spiral-flagged seats alone, only
   when the reference itself is a spiral (Matt's ruling).

   **The one exception** (Matt's ruling): a style needing a structure the galleries
   measurably lack may use hand-placed or atlas points that have it, measured the same
   way (`style scout --points <records.jsonl>` with `--max-ink`, or `--measure` for
   every row's ink) and checked by eye to be non-spiral.
5. **Hold the tonal balance.** Set the stack's `tone` to the reference's median and p10
   (`style tones <name>` prints them) and check renders with `style tones <name>
   <pictures…>`. A picture **misses** when its median is over 0.03, p10 over 0.05 or p90
   over 0.10 off, or its near-white or near-black share over 0.05 above the reference's
   (`styles.TONE_BAND`). A stack whose every render misses p90 is re-tuned (narrower
   glows, less fog), not its locations dropped. Check at `--draft`; `style tones` marks
   anything under 1280 wide `DRAFT`.
6. **Round one: formulations and locations, about twenty tiles**, asking both:
   **formulations**, four to
   six readings (the stack, its strongest variants, the stack without its headline
   addition) at the same two seats plus the closest named mode as baseline; and
   **locations**, ten to twelve seats kept by eye from the scout's forty `--draft`s (a
   10–15 minute run at four threads; give it a kill limit well past that).

   **Judge the look at `--draft` or larger** (at 640 wide a hair glow reads as blur).
   **A render must always look as if zooming in would show more
   detail** (Matt's rule): large shapes (a trap's big early entries, wide blades or
   discs) must never occlude the finer scales; drop or re-bound (`largest`) a stack that
   fails it. **A seam reads as ugly on an organic look**: a `lines` overlay, a period
   sheet on the `lines` angle or a `light` at `period` 1 on the smooth count cut along
   band seams; keep one only where the reference has hard edges.

   Render with `style render --manifest` into one folder per row and per stack (a
   picture is named by seat and map, so a second stack in one folder replaces the first,
   printed `REPLACED`; renders are logged to `renders.jsonl` beside them), then `style
   picker <plan.json>` (`style_picker.py`'s docstring has the plan's shape). **The
   report header carries one `pick: <manifest path>` line per picker** (from the repo
   root); that line, not `carry:` or the body, makes conductor offer the Pick button.
7. **Round two, once Matt's keeps are back: twelve tiles or fewer.** His kept
   formulations at his kept locations, and three or four library maps on them, each
   drafted first and dropped on a bullseye, a wash, or a tone miss.
8. Write `reference`, `reuses`, `adds`, `suggested_colormap` and `notes` into the file.
9. **Save Matt's keeps** after each round: `style keep <name> <picker>.choices.json`
   writes `<name>.keeps.json` and copies the pictures and reference to
   `fractal-drive-sync/style-keeps/<name>/`; a later round merges in. **One picker for a
   group of styles** scopes its row ids `<style>/<row>`, and `style keep <name>` runs
   once per style on the one choices file, taking its rows and unscoped ones. Maps go
   as *Palette sets* says.
10. **Catalogue it**: its `catalog.json` row (*The catalog*; score and status as Matt
    gave them) with `"palettes": []`, then `style palettes <name> --sync` to lay its
    keeps' maps in (the suggested map first; each entry Matt's score) and `style
    gallery`. A new style whose stack is an existing mode's is merged into it.

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

Each style's `notes` hold what its rounds taught. The general lessons:

- A glow wants thin sets: it paints anything finer than a pixel solid. Under a tone
  target dimming does nothing; balance comes from glow widths, fog and trap coverage.
- A gallery seat is a deep zoom: bound an entry trap by frame fraction (`largest`).
- A minibrot or hyperbolic Julia seat is Newton on `f^p(0) = 0` (`crescent_lines`).
