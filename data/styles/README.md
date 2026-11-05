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

The stack is `{name, interior, tone, projection, layers}`. `interior` is a paint for a sample whose
orbit never escaped and that no layer coloured (black when absent). `tone`
(`{median, p10}`, optional) holds the frame's tonal balance: once the stack is
composited, the frame's median lightness (CIE L\* over 100) is carried to `median`, and
its 10th percentile to `p10` when given, through one curve `L ↦ b + (1 − b)·L^g` that
keeps hue and pins white. It is how a stack fitted at one location keeps the
reference's key at another, where more far field would otherwise draw it paler.
`tone` also takes `log_density` (`k`): a flame fractal's log-density curve
`Y ↦ ln(1 + k·Y) / ln(1 + k)` on each sample's luminance, hue kept, laid before the
median and p10 are measured, so faint structure beside a bright core is lifted
(`glow_filaments` offers it at `k` = 30 as a variant). A
**paint** is
`{"rgb": "#rrggbb"}` or `{"palette": t}`, a position on whatever map the render was given
— the second is what keeps a style in key with every palette.

`projection` (optional) is where each sample looks: a per-sample pre-map of the frame
before anything is iterated (`engine/src/projection.rs`). The one kind is the
**log-polar** (exponential-map) view, `{"log_polar": {center, turns, power, twist,
angle, ring}}`: about a vanishing point at `center` (fractions of the frame from its
top-left, default the middle; the location's viewport `center` is the plane point it
shows), a sample at frame radius `r` and angle `θ` reads
`c = center + (width/2)·exp(u + i·v)` with `u = power·ln(r / half the frame width)`
and `v = turns·θ + twist·u + angle°`. Every octave round the point is then one ring of
the picture, so a location whose structure repeats per octave — a Misiurewicz point, a
Julia set's repelling fixed point — tiles the disc in rings of self-similar cells
shrinking towards the point. `turns` (a whole number, default 1) copies the plane's
full turn that many times round the disc; `power` defaults to `turns`, the conformal
map where a cell keeps its shape; `twist` (radians per e-fold of the plane radius)
shears the strip, and at a point whose structure turns by `arg λ` each time it shrinks
by `|λ|` a twist of `arg λ / ln|λ|` (less whole turns) stacks every ring's copy straight
above the last; `ring` is how many escape steps make one ring (below). At one turn and
power one about the middle it is the straight view. The distance estimate and the
light's gradient go through its Jacobian, so `de` is a distance in samples and a light's
`azimuth` is the frame's.

**What only a place knows rides on its location record**: a record may carry
`"projection": {"log_polar": {"twist": …, "ring": …}}`, and `style render` lays it over
the style's projection member by member (`styles.projected`); a style with no
projection ignores it. `twist` and `ring` come from the point's multiplier `λ` (the
derivative of its cycle) and the steps `p` per repeat: the smooth count climbs by `p`
each time the structure shrinks by `|λ|`, so `ring = k·p` with `k` the repeats nearest
the ring size the style wants. `teal_tunnel`'s shortlist was found that way: Misiurewicz
points by Newton on `f^{k+p}(0) = f^k(0)` from a rough seed, and quadratic Julia sets
at their fixed points `(1 ∓ √(1 − 4c))/2`, where `λ = 2z`.

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
| `glow` | `channel`, `color`, `power`, `falloff` | the channel's position to `power` is an alpha for `color` under the blend. With `falloff` (on the `de` channel only) the position is not the frame's stretch but `exp(−d / falloff)`, `d` the distance to the set in frame widths: a thread of light the same width at every location, resolution and supersample. A hair's falloff (2e-4, half a pixel at 2560) is a hot core; 1e-3 a halo; 1e-2 a bloom |
| `pattern` | `checker`, `color` | a checker of escape bands (`per_iteration`) by escape-angle sectors (`sectors`, 2 is binary decomposition) |
| `sheet` | `channel`, `sheet`, `color` | translucent sheets: the channel cut into `bands` steps (offset by `phase`), by the sample's rank in the frame (`rank`, the default) or by the stretch; across each step the alpha rises from 0 to `fill` (the scoop) and then to 1 within `edge` of its far end (the rim). Without a `color` it paints the stack beneath, so `add` or `screen` brightens in whatever hue is there. One band of an inverted channel is a glow falling off exponentially from the channel's low end — a strand along a trap, light along the filaments |

`light` and `sheet` also take **`period`**: cut a ring every `period` of the channel's
*raw* value instead of `bands` across the frame's rank or stretch, counted in the
projection's `ring`s (escape steps without one). A frame-wide cut spends its steps over
whatever range the frame holds, and a log-polar view's smooth count climbs without end
towards the vanishing point, so the steps smear into the deep end; a periodic cut is
the same at every depth. On the smooth count it draws one equipotential tube per ring.

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

   **Draft the contrasting-palette row (step 6) at low resolution first.** A library map
   the stack was not tuned for is where the failures hide: render each pairing small
   (`style render <name> --manifest <best>.jsonl --colormap <map> --resolution 640 400
   --supersample 1`), and look at every frame for bullseyes (concentric bands the map
   turns into rings) and washed-out frames (the lighting's near-whites swallowing a pale
   map; `style tones` flags these too). Drop or swap a failing map before any
   full-resolution render is paid for.
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
| `teal_tunnel` | `795548-3840x2160-desktop-4k-fractal-background.jpg` | `teal_tunnel` | `projection` (`log_polar`), `period` on `light` and `sheet`, a location's own `projection` |
| `glow_filaments` | `Black-and-Green-Abstract-Wallpaper.jpg` | `glow_filaments` | `falloff` on `glow`, `log_density` on `tone` |

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

The third style changed *where* samples look, not how they are coloured, and went in
by additions too: a projection in front of the iteration, and a `period` member on the
two banding layers. Two lessons. **Under a view without a bottom, every frame-wide
statistic is spent on the deep end**: rank and stretch cuts smear, and the distance
estimate must be read in samples (the Jacobian), or the whole outer frame is "far".
**Equipotentials run along the arms, not round the point**: the rings that make the
tunnel are the smooth count cut once per self-similar repeat (`ring`), and the cells
between the arms are the distance estimate's dark far side; at one cut per escape step
the arches crowd into stripes.

The fourth style came from a flame fractal, whose look is accumulated density, not a
statistic of one orbit: luminous threads, a hot core, a soft halo. The distance
estimate is the escape-time stand-in, and it went in as one member (`falloff`) that
reads it as a length, so the threads keep their width wherever they are; the halo and
bloom are the same layer at wider falloffs, and faint equipotential threads (a
`period` sheet on the smooth count) supply the strands crossing the dark. Two lessons.
**A distance glow paints whatever is finer than a pixel solid**: lace (seahorse
valley, spiral arms, parabolic Julia sets) reads as a lit stencil, not as threads, at
any falloff, so the style's locations are the ones whose set is thin — dendrites,
Misiurewicz points, higher-degree Julia sets at Misiurewicz `c` (`c^(d−1) = ω − 1`, `ω`
a `d`-th root of unity). **Under a tone target, dimming a layer does nothing**: the
tone pass lifts it straight back, so a stack whose frame is half void meets the
reference's key through the width of its glows and the fog in the void, never through
their opacity.
