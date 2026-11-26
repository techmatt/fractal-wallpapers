Styles: named layer stacks that capture the *feel* of a reference picture, one JSON
file per style, rendered with any colormap.

```
fractal-wallpapers style list | show <name> | knobs <mode> | palettes <mode>
fractal-wallpapers style render <name|draft.json> --location <record.json> [--colormap <map>] [--knob K=V]
fractal-wallpapers style render <name> --manifest <records.jsonl> --out-dir <dir> [--draft]
fractal-wallpapers style sheet <sheet.png> <folder|picture|list.txt…>  # a contact sheet (--tile-width 320: forty at once)
fractal-wallpapers style scout --out <scout.jsonl> [filters]  # seats (step 4)
fractal-wallpapers style tones <name> <pictures…> [--reference <entry|image>]  # tone check (step 5)
fractal-wallpapers style picker <plan.json>  # a picker (step 6)
fractal-wallpapers style keep <name> <picker>.choices.json  # save a picker's keeps
fractal-wallpapers style refs [--unused <triage>.choices.json [--sheet <dir>]]  # references named; triage `yes` rows no row names
fractal-wallpapers style gallery | bundle  # custom-modes/; the page's modes
fractal-wallpapers style wasm-parity [names…] | wasm-speed  # vs native: what is owed is style-wasm/README.md's table; frame time
fractal-wallpapers style cost <name…> [--seat <seat>]  # explorer cost, against the 5-minute bar (CHECKS.md)
fractal-wallpapers style sweep --out <dir> [names…]  # the checker (CHECKS.md)
```

A style is a stack of layers over the channels of one escape loop, composited by
`engine/src/style.rs` from the spec `styles.py` writes: **`STACK.md` here is the stack's
reference**, `TRAPS.md` its trap channels', `POST.md` that of its **stir** (where each sample looks) and **post stage**
(passes over the finished frame). `style-wasm/` runs the published modes in a browser
(`style-wasm/README.md`'s *The style module*). `<name>.keeps.json` is what Matt kept from a
style's pickers (pictures in `fractal-drive-sync/style-keeps/<name>/`); `catalog.json`
is the catalog; `docs/rulings.md` holds Matt's standing rulings.

`--location` takes a record as `render --location` reads it (`{family, viewport,
maxiter}`); `--colormap` defaults to the suggested map. Full size is 2560x1600 ss2,
`--draft` 1280x800 ss2. A render takes every core (`RAYON_NUM_THREADS=6` caps it); a
full-size frame takes 10 to 110 s at six, and a six-view stack commits 2 to 3 GiB.

## The file

| key | what |
| --- | --- |
| `schema`, `name` | 1; the file's name, and the stack's |
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

Every value a knob writes at its `default` is the stack's own (`styles.check_public`).
`range` spans what Matt kept without breaking the look, read off a sweep of each knob's
ends at a kept location, and **never past the size where a large shape starts hiding
the finer scales** (step 6), except that it **covers every value a palette entry tunes**
(Matt, 2026-11-25): each tuned member read back through the knob lies in it
(`style_palettes.check_row`), so a slider moved off an entry can return to it, at the
entry's `rests` in the bundle. `set` is pointers into the stack
(list indices as numbers, `*` for every member), each written as `scale·value + offset`.

## The catalog

`catalog.json` is one row per mode: Matt's score (1–5) and status, **`references`**
(every reference file the mode was fitted or tried against, kept or not), and a
published mode's **tier**, `curated` (four or five knobs, kept pictures only) or `lab`,
where every new mode starts. `style_catalog.py`'s docstring has the row's shape and the
tiers; `style_catalog.check` holds the rows to the style files. `style refs --unused`
reads the planner's triage, `picks/wallpaper_triage.choices.json`; `--sheet <dir>`
shows its unused references as captioned sheets plus `unused.txt`.

**A custom render mode is a stack plus a palette set** (each entry a map with its tuned
values, keeps and score): `PALETTES.md` beside this has the sets, saving only picked
palettes, renaming a map, and merging a style into a mode.

`style sweep`, the checker after an engine or stack change, is `CHECKS.md` beside this.

## A new style from a reference image

**The goal of every style is the fractal feel**: a render promises more detail if you
zoomed in, and its structure reads as the fractal's own (`docs/rulings.md`). Background
`style render --manifest` and `style scout --max-ink`/`--thinnest` (minutes each).

1. **Read the picture into layers**: its structure, what carries the vibe (lighting,
   banding, overlays), the background and the palette, each as a layer (`STACK.md`), and
   whether a channel, kind and blend draw it. **Ask whether one escape loop reaches its
   density**: accumulated density (a flame's veils) needs several `view`s or a new
   primitive, and round one says so. Drafts may use atlas points
   (`artifacts/atlas/<plane>/dots.json`), a picker only by step 4's exception. **First
   ask whether an existing mode's stack fits** (the gallery's cards); a plain escape-time
   reference always does (`smooth_bands`, `teal_filaments`, `lit_petals`). If one fits,
   the result is **a palette entry, not a style**: author the map (step 3), admit it with
   `palettes add <map.json> --mode <mode>`, tune its values on `style render <mode>
   --colormap <map>` drafts, and run steps 4 to 9 for the mode. A mode's layers with
   members removed or resized are its entry or formulation, not a new mode: grep the
   catalog's `what` lines for the look's nouns and name the nearest mode before drafting.
2. **Add a primitive only where one is missing**, in `engine/src/style.rs`, with a test,
   listed under `adds`. A layer is a function of one sample's channels, no neighbour
   reads; **what must read neighbours is a post pass** (`POST.md`'s *The post stage*).
   When the engine changed, `fractal-wallpapers identity <tag> --against <last tag>`
   (the newest file in `artifacts/identity/`) must read 0 differ (about seven minutes;
   once, on the final binary), and the style path's checks run (CLAUDE.md).
3. **Fit the palette with the lighting, not off the pixels**: the lights supply the
   near-whites, so a sampled map is too pale. Author the map as albedo
   (`data/palettes/README.md`), named after the style, and tune stack and map together.
   Admit it with **`fractal-wallpapers palettes add <map.json>`** (`--replace` after a
   re-tune) before any `--manifest` run; never move a map a running render reads. It can
   move `tests/test_curation_ceiling.py`'s pinned carrier-table reading: re-pin it,
   naming the map in its docstring.
4. **Scout the locations from the published galleries, never a spiral**: `style scout
   --out <dir>/scout.jsonl --n 40 [filters]` draws seeded and stratified from
   `tentative.DEFAULT` (`--record` names others), passing over seats flagged `spiral` or
   too deep (`style scout --help`). **Ink** is the share of the frame a half-pixel
   distance glow paints (`style_scout.PROBE`): dendrites read 0.003 to 0.025, lace 0.1
   to 0.5, and a glow floods white above about 0.11. The galleries are lace-heavy (median
   0.23), so `--max-ink 0.10` keeps what a glow can draw and `--thinnest --probe-limit
   200` the thinnest of a seeded 200. Drop by eye a `spiral: false` seat that whirls. **`--spiral`** keeps spiral seats alone, only when
   the reference is a spiral; some are too deep for a multi-loop stack.

   **The one exception**: a style needing a structure the galleries measurably lack may
   use hand-placed or atlas points that have it, measured the same way (`style scout
   --points <records.jsonl>` with `--max-ink`, or `--measure`) and checked by eye to be
   non-spiral.
5. **Hold the tonal balance.** Set the stack's `tone` to the reference's median and p10
   (`style tones <name>` prints them) and check renders with `style tones <name>
   <pictures…>`. A picture **misses** when its median is over 0.03, p10 over 0.05 or p90
   over 0.10 off, or its near-white or near-black share (lightness over 0.9, under 0.1: a
   dark navy ground is black) over 0.05 above the reference's (`styles.TONE_BAND`, `WHITE_ALLOWANCE`,
   `BLACK_ALLOWANCE`). Picker
   JPGs read directly; check three guide renders before a forty-seat location run. A stack whose every render misses p90 is re-tuned (narrower
   glows, less fog), not its locations dropped; on a dark reference keep the ground in
   the map's dark end, since a layer sinking it to black makes the pass lift the rest.
   The pass holds the median, so dimming one glow or light can leave p90 where the seat
   puts it; lowering the ground's `cycles` (keeping it off the map's bright end) moves it.
   Check at `--draft`, on the stack as shipped. A palette entry is held to **its own**
   reference: `style tones <mode> <pictures…> --reference <entry map>`.
6. **Round one: a picker of about twenty tiles**: **formulations**, four to six readings
   (the stack, its strongest variants, the stack without its headline addition) at one
   seat, the best four again at a second, plus the closest named mode as baseline; and
   **locations**, ten to twelve seats kept by eye from the scout's forty `--draft`s (a
   10–15 minute run at four threads; give it a kill limit well past that). Each `view`
   iterates interior points to the seat's `maxiter`: draw a view-heavy stack at seats under
   about 10,000 `maxiter` and time one draft first.

   **Draw every reading you will show before you verify**: verification (identity, the
   parity row, the checks) and the diff review run once, after the last code change.

   **Judge the look at `--draft` or larger** (at 640 wide a hair glow reads as blur).
   Large shapes (a trap's big early entries, wide blades or discs) never occlude the
   finer scales: drop or re-bound (`largest`) a stack that fails it. **A seam reads as ugly on an organic look** (a `lines` overlay, a period sheet on
   the `lines` angle, a `light` at `period` 1 on the smooth count): keep one only where
   the reference has hard edges.

   Render with `style render --manifest` into one folder per row and per stack (a
   second stack in one folder replaces the first, printed `REPLACED`), then `style
   picker <plan.json>` (`style_picker.py`'s docstring
   has the plan's shape) into `artifacts/pickers/<name>/`. **Entry tiles** are drawn
   from draft `e_<map>.json` files, the mode's stack with the entry's values written in;
   `style keep` diffs each kept tile's stack against the default to write `values`.
   **The report header carries one `pick: <manifest path>` line per picker** (from the
   repo root: conductor's Pick button).

   **Round one writes the catalog row at once**, with neither `score` nor `status`
   (`item`, `reference`, `references`, `what`, `"palettes": []`), so its references stop
   reading as untried; the rest lands with Matt's keeps (step 10).
7. **Round two, once Matt's keeps are back: twelve tiles or fewer.** His kept
   formulations at his kept locations, and three or four library maps on them, each
   drafted first and dropped on a bullseye, a wash, or a tone miss.
8. Write `reference`, `reuses`, `adds`, `suggested_colormap` and `notes` into the file.
   A style's own lessons go in its `notes`, never into this README.
9. **Save Matt's keeps** after each round: `style keep <name> <picker>.choices.json`
   (a later round merges in). **One picker for a group of styles** scopes its row ids
   `<style>/<row>`, and `style keep <name>` runs once per style on one choices file,
   taking its rows and unscoped ones; a tile goes to the catalog mode that drew it (a
   baseline's keep is that mode's: run the `style keep <mode>` it prints). Maps go as
   `PALETTES.md` says.
10. **Catalogue it**: the row's score and status as Matt gave them, a published one's
    `tier` (`lab`), `variant`, `show` and `public`, and `references` naming its reference
    (an entry's round adds the entry's file to the mode's `references` and the entry's
    `reference`, kept or not); then `style palettes <name> --sync` to lay its keeps' maps
    in (each entry Matt's score) and `style gallery`. A `drop` row keeps its default
    entry: only discarded and round-one rows have `"palettes": []`. A new style whose stack is an
    existing mode's is merged into it.

### The per-image prompt

```
Goal: a new style from <image>, in fractal-drive-sync/style-refs/.
Name: <style_name>. The look, in a line: <what makes the picture>.
Nearest mode: <name>; what must differ from it: <headline>.
Structure it needs (optional): <e.g. thin sets: --max-ink 0.10; dynamical planes (Julia, phoenix) only: --kind julia>.
  Lacking in the galleries? <yes: hand or atlas points via --points, per step 4's exception>.
  Reachable by one escape loop? (optional) <yes | no: density from several views or a new primitive>.
Keep / avoid (optional): <what must survive, what must not appear>.
Round: 1 | 2 with <picker>.choices.json (round 2: the kept formulations and locations).
Spare time goes to further readings, drawn before the checks: the checks and the diff
  review run once, after the last code change.
Checks: the tone check on the stack as shipped; `style wasm-parity <name>`, never the whole run
  (an engine member only this style sets adds `identity`, 0 differ, not the whole run).
Module and explorer-cost times (CHECKS.md, **Explorer cost**) are read on a quiet box only when the item holds one
  (`locks: [quiet]`, which Matt must allow explicitly); otherwise they are marked upper bounds.
The report header carries one `pick: <manifest path>` line per picker.
Tables go in out/keep/<item>/ and the report; experiments/ is git-excluded here, never committed.
Follow data/styles/README.md's *A new style from a reference image*. Commit when done.
```
