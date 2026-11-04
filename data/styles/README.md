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
One render takes every core the box has; `RAYON_NUM_THREADS=6` caps it when a picker's
worth of renders has to leave the desktop room. At six threads a 2560x1600 `yas` frame
took 10 to 110 s, most of it the `de` and `trap_cross` loops at caps of 4,000 to 10,000.

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

The stack is `{name, interior, tone, layers}`. `interior` is a paint for a sample whose
orbit never escaped and that no layer coloured (black when absent). `tone`
(`{median, p10}`, optional) holds the frame's tonal balance: once the stack is
composited, the frame's median lightness (CIE L\* over 100) is carried to `median`, and
its 10th percentile to `p10` when given, through one curve `L ↦ b + (1 − b)·L^g` that
keeps hue and pins white. It is how a stack fitted at one location keeps the
reference's key at another, where more far field would otherwise draw it paler. A
**paint** is
`{"rgb": "#rrggbb"}` or `{"palette": t}`, a position on whatever map the render was given
— the second is what keeps a style in key with every palette.

A **channel** is `{"field": <a field spec>, "transform": <curve>}`,
`{"inside": {"iterations": N}, "transform": ...}` or `{"radial": {"center": [x, y]}}`,
and any of them takes `"invert": true` to read the position from the other end. A field
spec is anything the mode catalog's fields are made of (`smooth`, `decomposition`, `de`,
`threads` with its `sigma`, `trap_cross`, `stripe`, `tia`, …; not `itinerary`); the curve
is `linear`, `sqrt`, `log` or `scurve`, applied after the frame's stretch (and the
invert). `inside` is the one channel defined only inside the set: a smooth convergence
count, highest at each bulb's nucleus, so banding it draws rings into every bulb.
`radial` is the one channel not read off the orbit: how near a sample is to a point of
the frame (`center` in fractions from the top-left, default the middle), 1 at the core
and 0 at the farthest corner, for a picture whose hue and brightness fall away from a
centre. It has no gradient, so a `light` cannot read it, and the location has to put its
core where `center` says.

Each **layer** is `{kind, blend, opacity, mask, …}`; `blend` is one of `normal`,
`multiply`, `screen`, `overlay`, `min`, `add` (applied per channel in linear light),
`opacity` is in [0, 1], and `mask` (`{channel, invert, power}`) multiplies the opacity by
a channel's position. A layer only touches samples where its channel has a value.

| kind | members | what it does |
| --- | --- | --- |
| `palette` | `channel`, `palette`, `warp` | the channel through the leveled spend to the map; `palette` is the engine's palette recipe less `mirror`, `reverse` and `rolloff` (`cycles`, `gamma`, `phase`, `transfer` — `rank` spends the map evenly over the frame's samples). `warp` (`{channel, amount}`) adds a second channel's rank in the frame, centred on 0, times `amount` to the position before the map is read: a radial palette warped by the smooth count follows the arms instead of drawing a target when the map is not in lightness order |
| `light` | `channel`, `light` | relights the stack: the channel's position is a height, cut into `bands` rings whose cross-section is a tube (`rings` of the normal; the rest is a `slope` up the field), lit Blinn–Phong from `azimuth`/`elevation` with `ambient`, `diffuse`, `specular`, `shininess`, a `rim` and an optional `highlight` paint. The normal's direction is the channel's own gradient, read off the orbit, never off neighbouring samples |
| `glow` | `channel`, `color`, `power` | the channel's position to `power` is an alpha for `color` under the blend |
| `pattern` | `checker`, `color` | a checker of escape bands (`per_iteration`) by escape-angle sectors (`sectors`, 2 is binary decomposition) |
| `sheet` | `channel`, `sheet`, `color` | translucent sheets: the channel cut into `bands` steps (offset by `phase`), by the sample's rank in the frame (`rank`, the default) or by the stretch; across each step the alpha rises from 0 to `fill` (the scoop) and then to 1 within `edge` of its far end (the rim). Without a `color` it paints the stack beneath, so `add` or `screen` brightens in whatever hue is there. One band of an inverted channel is a glow falling off exponentially from the channel's low end — a strand along a trap, light along the filaments |

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
5. **Hold the tonal balance.** Set the stack's `tone` to the reference's median and
   p10 (`style tones <name>` prints them), then check every render against the
   reference before it goes to a picker:

   ```
   fractal-wallpapers style tones <name> <rendered pictures…>
   ```

   A picture **misses** when its median is more than 0.03 or its p10 more than 0.05
   from the reference's, or its near-white or near-black share is more than 0.05 above
   the reference's (`styles.TONE_BAND`, fitted on `floating_on_dreams`'s round one, where
   the three Matt kept are exactly the three that hold). Re-tune a stack whose renders
   miss, or drop the location, and say which.
6. **Render for the picker**: every shortlisted location in the style with its map; the
   best few with four to six contrasting library maps; the best two in the closest named
   mode or style with the matched map, as the baseline the style is judged against.
7. Write `reference`, `reuses`, `adds` and `suggested_colormap`, and check the existing
   modes still draw the same bytes (`fractal-wallpapers identity` before and after, when
   the engine changed).

## The styles

| style | reference | suggested map | added |
| --- | --- | --- | --- |
| `floating_on_dreams` | `floating-on-dreams-25.jpg` | `floating_on_dreams` | the compositor, `gradient`, `inside`, `light`, `glow`, `pattern`, `mask` |
| `yas` | `yas-25.jpg` | `yas` | `radial`, `sheet`, `invert`, `warp`, `tone` (and `tone` back onto `floating_on_dreams`) |

The second style was the test of whether the framework takes a very different picture
by additions or needs reshaping. **By additions**: a picture lit from within, its
structure inside the depth rather than on a lit surface, needed one channel that is not
read off the orbit (`radial`), one layer kind (`sheet`), a member every channel has
(`invert`), a member of the palette layer (`warp`) and one frame-wide pass after
compositing (`tone`). No existing layer, blend or file changed shape; `floating_on_dreams`
gained a `tone` and draws its old stack. The one lesson that is about the framework
rather than this picture: **a channel that is not structure, laid through the map
whole, turns every map not in lightness order into a target** — a style that colours
by position has to bend that position by the fractal (`warp`), or it only holds its
look with its own map.
