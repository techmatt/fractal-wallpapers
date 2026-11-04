Styles: named layer stacks that capture the *feel* of a reference picture, one JSON
file per style, rendered with any colormap.

```
fractal-wallpapers style list
fractal-wallpapers style show floating_on_dreams
fractal-wallpapers style render floating_on_dreams --location <record.json> --colormap <any map>
fractal-wallpapers style render floating_on_dreams --manifest <records.jsonl> --out-dir <dir>
fractal-wallpapers style render <draft.json> --location <record.json>      # a draft, before it joins
```

`--location` takes the same record `render --location` reads — `{family, viewport,
maxiter}` is enough — and `--colormap` defaults to the style's suggested map. The
default size is 2560x1600 at supersample 2; `--resolution` and `--supersample` move it.

A named mode (`fractal-wallpapers modes`) is one field through the colormap, or two
blended. A style is the next shape up: several channels of **one** escape loop per
sample, each layer turning one of them into colour or into light, stacked by a blend and
an opacity. The engine composites it (`engine/src/style.rs`); Python only reads the file
and writes the spec (`src/fractal_wallpapers/styles.py`). The compositor is a pure
per-sample function of the channels, the layer parameters and the map once each channel's
frame-wide stretch is measured — the measure-then-samples split the explorer already
makes — so the explorer can port it without anything here.

## The file

| key | what |
| --- | --- |
| `schema` | 1 |
| `name` | the file's name, and the stack's |
| `description` | one line: what the style looks like |
| `reference` | `{image, folder, made_with}`: the picture it was made from. Reference images live in `fractal-drive-sync/style-refs/`, never in git |
| `suggested_colormap` | the map the stack was fitted with; any map renders |
| `reuses` | the existing pieces the stack is built from |
| `adds` | the primitives this style added to the engine, empty when it added none |
| `style` | the stack, handed to the engine untouched as the render spec's `style` key |

The stack is `{name, interior, layers}`. `interior` is a paint for a sample whose orbit
never escaped and that no layer coloured (black when absent). A **paint** is
`{"rgb": "#rrggbb"}` or `{"palette": t}`, a position on whatever map the render was given
— the second is what keeps a style in key with every palette.

A **channel** is `{"field": <a field spec>, "transform": <curve>}` or
`{"inside": {"iterations": N}, "transform": ...}`. A field spec is anything the mode
catalog's fields are made of (`smooth`, `decomposition`, `de`, `threads` with its
`sigma`, `trap_cross`, `stripe`, `tia`, …; not `itinerary`); the curve is `linear`,
`sqrt`, `log` or `scurve`, applied after the frame's stretch. `inside` is the one channel
defined only inside the set: a smooth convergence count, highest at each bulb's nucleus,
so banding it draws rings into every bulb.

Each **layer** is `{kind, blend, opacity, mask, …}`; `blend` is one of `normal`,
`multiply`, `screen`, `overlay`, `min`, `add` (applied per channel in linear light),
`opacity` is in [0, 1], and `mask` (`{channel, invert, power}`) multiplies the opacity by
a channel's position. A layer only touches samples where its channel has a value.

| kind | members | what it does |
| --- | --- | --- |
| `palette` | `channel`, `palette` | the channel through the leveled spend to the map; `palette` is the engine's palette recipe less `mirror`, `reverse` and `rolloff` (`cycles`, `gamma`, `phase`, `transfer` — `rank` spends the map evenly over the frame's samples) |
| `light` | `channel`, `light` | relights the stack: the channel's position is a height, cut into `bands` rings whose cross-section is a tube (`rings` of the normal; the rest is a `slope` up the field), lit Blinn–Phong from `azimuth`/`elevation` with `ambient`, `diffuse`, `specular`, `shininess`, a `rim` and an optional `highlight` paint. The normal's direction is the channel's own gradient, read off the orbit, never off neighbouring samples |
| `glow` | `channel`, `color`, `power` | the channel's position to `power` is an alpha for `color` under the blend |
| `pattern` | `checker`, `color` | a checker of escape bands (`per_iteration`) by escape-angle sectors (`sectors`, 2 is binary decomposition) |

Under a style the render spec's own `palette` carries the bake and the rolloff only. The
CLI folds a sequential map (`mirror`) only when a palette layer repeats it (`cycles` > 1):
at one traversal the fold would run the near-set end back to the far field's colour.

## A new style from a reference image

The item that brings a picture says "new style from <image>". The procedure:

1. **Read the picture into layers.** Name its structure (where to look), what carries the
   vibe (lighting, banding, overlays), the background, and the palette. Write each as a
   layer of the table above, and for each say whether a channel, a layer kind and a blend
   that draw it already exist. Most will.
2. **Add a primitive only where one is missing**, in `engine/src/style.rs`, with a test, and
   list it under `adds`. A new channel is a `FieldSpec` already in the catalog wherever one
   will do; a new field means a new `FieldSpec`, which every named mode can then use too.
   Keep every primitive a function of one sample's channels — no neighbour reads.
3. **Fit the palette with the lighting, not off the pixels.** The lighting supplies the
   near-whites, so a palette sampled naively is too pale. Author the map as albedo
   (`data/palettes/README.md`, `data/palette_authoring/`), name it after the style, and
   tune the stack and the map together on drafts: `style render <draft.json>` takes a
   style file from anywhere, so a draft never has to enter `data/styles/` to be tried.
4. **Shortlist locations** with the structure the picture has (the atlas,
   `artifacts/atlas/<plane>/dots.json`, is the library), framed for 16:10.
5. **Render for the picker**: every shortlisted location in the style with its map; the
   best few with four to six contrasting library maps; the best two in the closest named
   mode with the matched map, as the baseline the style is judged against.
6. Write `reference`, `reuses`, `adds` and `suggested_colormap`, and check the existing
   modes still draw the same bytes (`fractal-wallpapers identity` before and after, when
   the engine changed).

## The styles

| style | reference | suggested map | added |
| --- | --- | --- | --- |
| `floating_on_dreams` | `floating-on-dreams-25.jpg` | `floating_on_dreams` | the compositor, `gradient`, `inside`, `light`, `glow`, `pattern`, `mask` |
