Styles: named layer stacks that capture the *feel* of a reference picture, one JSON
file per style, rendered with any colormap.

```
fractal-wallpapers style list
fractal-wallpapers style show floating_on_dreams
fractal-wallpapers style render floating_on_dreams --location <record.json> --colormap <any map>
fractal-wallpapers style render floating_on_dreams --manifest <records.jsonl> --out-dir <dir>
fractal-wallpapers style render <draft.json> --location <record.json>      # a draft, before it joins
fractal-wallpapers style keep floating_on_dreams <picker>.choices.json     # save a picker's keeps
fractal-wallpapers style knobs lit_petals                                  # its public knobs
fractal-wallpapers style render lit_petals --location <record.json> --knob light_angle=200
fractal-wallpapers style gallery                                           # rebuild custom-modes/
fractal-wallpapers style bundle                                            # the published modes, for a page
fractal-wallpapers style wasm-parity                                       # the WebAssembly module vs native
```

The published modes run in a browser through `style-wasm/`, the compositor as
WebAssembly; `engine/README.md`'s *The style module* has its API and the bundle's shape.

`<name>.keeps.json` beside a style is not a style: it is the renders Matt kept from its
pickers, each with what redraws it, and its pictures live in
`fractal-drive-sync/style-keeps/<name>/` beside the reference. Nor is **`catalog.json`**:
the custom-mode catalog, one row per style that has been through a round (*The catalog*).

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
| `public` | a published mode's knobs, `{"knobs": [...]}` (*Public knobs*); absent on the rest |
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

A `field` channel also takes **`view`** (`{turn, zoom, shift, c}`): the field read off
its own escape loop at a moved point, `p' = m + zoom·e^(i·turn)·(p − m) + shift·w` (`m`
the frame's centre, `w` its width in the plane, `turn` in degrees, `shift` `[x, y]` in
frame widths with `y` up), with `c` (`[re, im]`, plane units) added to the orbit's `c`:
a dynamical plane's parameter, so a neighbouring Julia set, and on a parameter plane the
pixel itself. One escape loop's fields share their level lines, so their bands nest and
never cross; a field read through a turned, scaled, off-centre view has level lines of
its own, and sheets of several views laid additively cross as a flame's veils do. Each
view is one more loop per sample beside the frame's own, so a stack of four views costs
about five renders. A `de` read
through a view is divided by `zoom`, so a falloff glow keeps its width; a `light` cannot
read a viewed channel (its gradient is the frame's own). `turn`, `zoom` and `shift` are
frame-relative and hold at any depth; `c` is in plane units, so it is for shallow,
hand-placed seats (deep in a zoom any `c` worth seeing moves the view off the structure).

`{"bubble": {center, radius, hit, read, spacing, escaped}}` is the **bubble trap**: the
disc `|z − center| < radius` (`center` a plane point `[re, im]`) read at the step the
orbit enters it for the `hit`-th time (default 1). The samples that first land in the disc
at step `n` are a conformal preimage of it, so each is a round disc, and the discs of
later steps fill the gaps the earlier leave: a circle packing, the tiniest crowding into
the cusps where two meet. `read` is `height` (`1 − |z − center|/radius`, 1 at a disc's
middle and 0 at its rim, its gradient pointing inwards, so a `light` at `period` 2 domes
every disc and a `glow` on it inverted is a bright rim), `step` (the entry's step, one
number per disc) or `angle` (of `z − center`, a fraction of a turn: rays from each disc's
middle, which a six-band `sheet` cuts into a star). `hit` 2 is the same disc entered
again after the orbit left it: smaller discs packed inside each disc of hit 1.
`spacing` repeats the disc on a square lattice through `center`: one disc is a target
most orbits miss for good, a lattice is one almost every orbit lands in, so the discs
fill the frame. Keep the critical point (`0`) off every disc — `center` `[0.5, 0.5]` at
spacing 1 does — or the discs it falls in pull back as peanuts, not circles. `escaped`
reads only orbits that escape: inside the set the orbit settles on its cycle, and a
cycle sitting in a disc draws the whole component as one smeared bubble, which the
`inside` channel paints better. `largest` (a fraction of the frame width) passes over
an entry whose disc pulls back larger than that (`radius / |dz| > largest · width`):
deep in a zoom every early step's disc is far larger than the frame and draws a straight
edge across it, and with the bound the packing starts at the same frame-relative size at
any depth. Its own loop, stopping at the entry, with `dz` kept.

`shift` (`[x, y]` in radii, length in (0, 1)) gives each disc a **face**: a smaller disc
inside it, internally tangent to its rim, centred `shift·radius` from its middle, of
radius `(1 − |shift|)·radius`. The read `crescent` is the lune between rim and face,
`a / (a + b)` with `a` the distance outside the face and `b` the distance inside the rim
(0 at the face, 1 at the rim, nothing on the face), widest opposite the shift and
vanishing where the face touches the rim. Its gradient is its own (the lune's, pulled
back through `dz`), so a `light` at one band lights each lune as a glossy curved band.
The shift lives in the disc's plane, so every disc's pullback turns its crescent its own
way. On a trap with a large `largest` the early discs are frame-sized, and their
crescents are ribbons sweeping the frame and curling round the discs they hug.

`shape` `strip` swaps the disc for the **line trap** read at an entry: the strip
`|Im((z − center)·e^(−i·tilt))| < radius` about the line through `center` at `tilt`
degrees (default 0, the real axis), repeated as parallel lines `spacing` apart. A disc
pulls back round; a strip pulls back through each critical point of the iterate as a
cross of arms tapering to points, so its entries are pointed, curved **blades**, and the
lattice's blades overlap in fans. `height` is `1 − |v|/radius` (1 on the line, 0 at
either edge, `v` the offset across it), `step` is one number per blade, and a strip has
no `angle` and no face. The read **`across`**, on either shape, is `(v/radius + 1)/2`
across the `tilt`: 0 at one edge, 1 at the other, its gradient the across axis pulled
back through `dz`, so a `light` at one band and `rings` 1 shades each blade from edge to
edge as a lit cylinder. `smallest` (a fraction of the frame width) is `largest`'s
partner: the read ends, `NaN`, at the first counted entry whose shape pulls back smaller
than that, and since entries only shrink along an orbit it is where the trap's detail
stops; what lies finer is left to the layers beneath.

`{"lines": {radius, arrive, settle, twist, divide, read, side}}` is the **field-lines**
channel: where the orbit crossed a circle of its own, outside the set and inside it. An
escaping orbit is read at the step it first leaves `|z| < radius` (default 4; a radius
near the set's own size, 1.2 for a quadratic Julia set, puts several bands in the
frame); an orbit that stays bounded is run `settle` steps (default 1000) onto its
attracting cycle, the cycle found as the first repeat within 64 steps, and read at the
first step it comes within `arrive` (default 0.05) of a cycle point `w`. `read` is
`angle` (of `z`, or of `z − w` inside, a fraction of a turn) or `step` (the crossing's
step, one number per band or arrival ring). The escape angle `decomposition` is the
same angle read at the engine's `2¹⁶` bailout, where it has turned so often round each
band that its level lines are straight rays crowding into moiré; read at a circle of a
few units they are curves fanning out of the points that map to `0`, cut into sectors
at the band seams, and inside, each cell of an attracting basin holds a pinwheel of
lines into its centre. `twist` turns the angle by `twist·ln(|z| / radius)` radians
(`ln(|z − w| / arrive)` inside), bending each band's lines into arcs; `divide` (outside
only) divides the angle by `divide^step`, so the lines stop doubling with every band
inwards (at the degree, each band holds as many as the one outside it). `side`
(`both`, `outside`, `inside`) keeps one half of the frame, so the set and its outside
take their own layers. Lines are cut by a sheet's `period` on the raw angle; a palette's
stretch on a divided angle is spent on the outermost band. No gradient, so no `light`;
a parabolic or Siegel interior, whose orbit never repeats, has no lines.

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

## Public knobs

A published mode exposes three to five knobs, the parameters most worth handing a user,
in its file's `public` block:

```
{"name": "light_angle", "label": "Light direction", "what": "<one line a user reads>",
 "default": 135.0, "range": [45.0, 225.0],
 "set": ["/layers/*/light/azimuth", {"path": "/layers/14/opacity", "scale": 0.6, "offset": 0}]}
```

`default` is the kept version: every value the knob writes at its default is the stack's
own (`styles.check_public`, which `style knobs` and the catalog's check run). `range`
spans what Matt kept without breaking the look, read off a sweep of each knob's ends at a
kept location, and **never past the size where a large shape starts hiding the finer
scales** (see step 6's rule). `set` is where the value goes: a pointer into the stack,
list indices as numbers and `*` for every member under which the rest exists, written as
`scale·value + offset` (default 1 and 0), so one knob can move linked members together
(`gilded_orbs`' `orb_size` moves each orb trap's `largest` with its `radius`, through its
`many_orbs` keep). `style render --knob NAME=VALUE` turns one, refusing a name the style
does not expose and a value outside its range; the render log keeps the stack as drawn.

## The catalog

`catalog.json` is the single record per mode: style, reference image, Matt's score
(1–5), status (`publish`, `drop`, `discarded`; absent on a row Matt has not ruled on, whose
page toggles start unmarked), the published variant, the keeps the page
shows (`{keep, caption}`, ids from `<name>.keeps.json`), the card's text, and for a
published mode `public` (`{name, palette, knobs}`). The published variant is always the
style file's default stack: where Matt kept a formulation over the stack (`lit_petals`'
`soft`, `shaded_blades`' `lune_blades`), it became the default. Public names are
proposals Matt may rename; they are data. `style_catalog.check` holds the rows to the
style files (reference, knob names, colormap, keep ids).

`fractal-wallpapers style gallery` rebuilds `fractal-drive-sync/custom-modes/index.html`
and its downscaled pictures (`img/`, each traced in `img/sources.json` so a rebuild
redraws only what moved) from the catalog, the keeps and the references. Its Publish /
Maybe / Drop toggles start from each row's status, and a style in the library with no
row is listed under *not yet catalogued*.

## A new style from a reference image

The item that brings a picture says "new style from <image>". Run every engine-driving
step at below-normal priority with `RAYON_NUM_THREADS=6`; `style render --manifest` and
`style scout --max-ink`/`--thinnest` take minutes and are not on conductor's background
globs, so background them yourself.

1. **Read the picture into layers.** Name its structure (where to look), what carries the
   vibe (lighting, banding, overlays), the background, and the palette. Write each as a
   layer of the table above, and for each say whether a channel, a layer kind and a blend
   that draw it already exist. Most will. Draft and tune on hand-placed points or the
   atlas (`artifacts/atlas/<plane>/dots.json`); those reach a picker only through step
   4's exception.
2. **Add a primitive only where one is missing**, in `engine/src/style.rs`, with a test, and
   list it under `adds`. A new channel is a `FieldSpec` already in the catalog wherever one
   will do. Keep every primitive a function of one sample's channels: no neighbour reads.
   When the engine changed, `fractal-wallpapers identity <tag> --against <last tag>` must
   read 0 differ (three engines at two threads each, about seven minutes).
3. **Fit the palette with the lighting, not off the pixels.** The lighting supplies the
   near-whites, so a palette sampled naively is too pale. Author the map as albedo
   (`data/palettes/README.md`), name it after the style, and tune stack and map together
   on drafts (`style render <draft.json>` takes a style file from anywhere). Admit it with
   **`fractal-wallpapers palettes add <map.json>`** (`--replace` after a re-tune): it
   writes the map, its zero `palette_family_shares.csv` row and its carrier rows, and
   names the nearest library maps, saying so when one is a near-twin.
4. **Scout the locations from the published galleries, never a spiral** (Matt's ruling):

   ```
   fractal-wallpapers style scout --out <dir>/scout.jsonl --n 40 [filters]
   ```

   draws seeded and stratified over partitions from `final139_general` (`--record`
   names others), passing over every seat flagged `spiral` and any too deep for a double
   render; the filters are `--kind julia|plane`, `--degree`, `--partition`, `--mode` and
   `--max-p-spiral`. A style that needs a structure measures it: **ink** is the share of
   the frame a half-pixel distance glow paints (`style_scout.PROBE`). On
   `glow_filaments`'s 117 hand records thin dendrites read 0.003 to 0.025 and lace 0.1 to
   0.5; its three keeps read 0.005, 0.052 and 0.079, and every render that flooded white
   read above 0.11. The galleries are lace-heavy (median 0.23 over 120 seats, 11 at or
   under 0.10, none under 0.03), so `--max-ink 0.10` keeps what a glow can draw and
   `--thinnest --probe-limit 200` keeps the thinnest of a seeded 200 (a fifth of the
   record; raise the limit for more). A `spiral: false` seat can still read as a whirl:
   drop it by eye at step 6.

   **The one exception** (Matt's ruling): a style whose entry under *The styles* names a
   structure the galleries lack (thin dendrites for a glow) may fill its location row
   with hand-placed or atlas points that have it, measured the same way
   (`style scout --points <records.jsonl> --max-ink 0.03 --out …`) and checked by eye
   to be non-spiral, since no spiral probe has read them. `glow_filaments` is the case:
   three of its keeps were hand-placed, and a lace-leaning row shows a glow badly.
5. **Hold the tonal balance.** Set the stack's `tone` to the reference's median and p10
   (`style tones <name>` prints them), and check renders against the reference:

   ```
   fractal-wallpapers style tones <name> <rendered pictures…>
   ```

   A picture **misses** when its median is more than 0.03, its p10 more than 0.05 or its
   p90 more than 0.10 from the reference's, or its near-white or near-black share is more
   than 0.05 above it (`styles.TONE_BAND`). The tone pass pins the median and p10, so p90
   is what tells the stack's highlights from the reference's: a stack whose every render
   misses p90 is re-tuned (narrower glows, less fog), not its locations dropped.
   **Check at `style render --draft`** (1280x800 ss2), the cheap size, whose tones are the
   full size's to about 0.01. The pass measures the finished picture (each pixel its block
   of supersamples averaged), so every size's picture meets the targets at its own
   resolution; `style tones` reads a copy resized to 640 wide, which averages thin
   structure once more, so a thin-structured frame can read ~0.02–0.03 off its target at
   full size and a little less at the draft, still inside the band. A 640-wide ss1
   picture is read exactly as the pass measured it and holds by construction, so
   `style tones` marks anything under 1280 wide `DRAFT` instead of passing it.
6. **Round one: formulations and locations, about twenty tiles.** Keeps are sparse (two
   to four locations of nine to eleven), the agent's best location was never among them,
   and the variant Matt kept was each time a different formulation from the one the
   location row used. So round one asks the two independent questions first:
   - **formulations**: four to six distinct readings of the look (the stack, its strongest
     variants, the stack without its headline addition), each at the same two scouted
     locations, plus the closest named mode at one of them as the baseline;
   - **locations**: ten to twelve scouted seats, rendered at `--draft` and kept by eye
     from the scout's forty, in the current formulation with the matched map. The forty
     drafts are one `style render --manifest … --draft` run of 10–15 minutes at four
     threads, a single seat sometimes several minutes alone: give its background job a
     kill limit well past that.

   **A render must always look as if zooming in would show more detail** (Matt's rule,
   item 018). Large shapes — a trap's big early entries, wide blades or discs — must never
   occlude the finer scales, or the frame reads as a finite set of objects instead of a
   fractal. Check for it when picking locations and formulations, and drop or re-bound
   (`largest`) a stack that fails it; a public knob's range stops short of it too.

   Render with `style render` (`--manifest` into one folder per row): each render is
   logged to `renders.jsonl` beside it. Then write a plan and build the picker:

   ```
   fractal-wallpapers style picker <plan.json>
   ```

   (`style_picker.py`'s docstring has the plan's shape; a named-mode baseline carries its
   own `render`). It writes the JPEGs, a manifest whose every row is `"kind": "many"`,
   `"default": []`, and the renders sidecar `style keep` needs. **The item's report header
   carries one `pick: <manifest path>` line per picker it built** (the path from the repo
   root), which is what makes conductor offer the Pick button; naming the picker only in
   `carry:` or the body does not.
7. **Round two, once Matt's keeps are back: twelve tiles or fewer.** His kept
   formulations at his kept locations, and three or four library maps on them, each map
   drafted at `--draft` first and dropped on a bullseye (concentric bands the map turns
   into rings), a wash, or a tone miss.
8. Write `reference`, `reuses`, `adds` and `suggested_colormap` into the style file.
9. **Save Matt's keeps** after each round: `fractal-wallpapers style keep <name>
   <picker>.choices.json` writes `<name>.keeps.json` here and copies the pictures, with
   the reference, to `fractal-drive-sync/style-keeps/<name>/`; a later round merges in.
10. **Catalogue it and rebuild the page.** A new mode adds its row to `catalog.json`
    (score and status as Matt gave them, the keeps to show with captions, the card's
    text; a published mode its variant as the default stack, its `public` name and
    palette, and its knobs in the style file), then `fractal-wallpapers style gallery`
    rebuilds `fractal-drive-sync/custom-modes/`. Matt's score or status changing later is
    the same two steps.

### The per-image prompt

```
Goal: a new style from <image>, in fractal-drive-sync/style-refs/.
Name: <style_name>. The look, in a line: <what makes the picture>.
Structure it needs (optional): <e.g. thin sets: --max-ink 0.10; Julia sets only: --kind julia>.
  Lacking in the galleries? <yes: hand or atlas points via --points, per step 4's exception>.
Keep / avoid (optional): <what must survive, what must not appear>.
Round: 1 | 2 with <picker>.choices.json (round 2: the kept formulations and locations).
The report header carries one `pick: <manifest path>` line per picker.
Follow data/styles/README.md's *A new style from a reference image*. Commit when done.
```

The procedure covers the rest by itself: the layer reading, any engine primitive and
its identity check, the matched map and `palettes add`, the gallery scout with no
spirals, the tone targets and the draft-size check, the picker with nothing
pre-selected and its sidecar, `style keep`, the catalog row and `style gallery`.

## The styles

| style | reference | suggested map | added |
| --- | --- | --- | --- |
| `floating_on_dreams` | `floating-on-dreams-25.jpg` | `floating_on_dreams` | the compositor, `gradient`, `inside`, `light`, `glow`, `pattern`, `mask` |
| `yas` | `yas-25.jpg` | `yas` | `radial`, `sheet`, `invert`, `warp`, `tone` (and `tone` back onto `floating_on_dreams`) |
| `teal_tunnel` | `795548-3840x2160-desktop-4k-fractal-background.jpg` | `teal_tunnel` | `projection` (`log_polar`), `period` on `light` and `sheet`, a location's own `projection` |
| `glow_filaments` | `Black-and-Green-Abstract-Wallpaper.jpg` | `glow_filaments` | `falloff` on `glow`, `log_density` on `tone` |
| `bronze_packing` | `795549-3840x2160-desktop-4k-fractal-background.jpg` | `bronze_packing` | the `bubble` channel (`height`, `step`, `angle`; `hit`, `spacing`, `escaped`) |
| `ribbon_packing` | `795565-3840x2160-desktop-4k-fractal-wallpaper-image.jpg` | `ribbon_packing` | the bubble's `shift` (a face in each disc) and its `crescent` read |
| `gilded_orbs` | `ancient-empires-25.jpg` | `gilded_orbs` | nothing: the old layers on `de`, `smooth`, `tia`, `inside` and two bubble traps |
| `field_lines` | `blood-price-25.jpg` | `field_lines` | the `lines` channel (`angle`, `step`; `radius`, `arrive`, `settle`, `twist`, `divide`, `side`). Its structure, connected Julia sets with attracting basins, is one the galleries lack: its locations are hand-placed (step 4's exception) |
| `leaf_veins` | `commons_Fractal_Art_Series__2814465834074_29.jpg` | `leaf_veins` | nothing: old layers on `de`, `smooth` and `lines`. Its structure, dendrites, is one the galleries lack: its locations are hand-placed (step 4's exception) |
| `shaded_blades` | `chronoscope-25.jpg` | `shaded_blades` | the bubble trap's `strip` shape (`shape`, `tilt`), the `across` read and the `smallest` bound. Its default stack is the `lune_blades` formulation (crescent lunes, not strips), Matt's one keep |
| `glossy_lobes` | `blessed-by-the-night-25.jpg` | `glossy_lobes` | nothing: a disc lattice domed at `period` 2 under `shaded_blades`' strip blades, on `de`, `inside` and the sparkle lattice |
| `lit_petals` | `carnival-25.jpg` | `lit_petals` | nothing: the smooth count through a cyclic map, lit at `period` 3, and cycled three times under a `de` mask for the jewels. Its default stack is the `soft` formulation (no tube, no seam sheet), the one Matt kept |
| `seahorse_halo` | `103489.jpg` | `seahorse_halo` | nothing: the smooth count through a cyclic map by rank at 1.5 cycles, a dark `de` hair, the tone pass |
| `citadel` | `citadel.jpg` | `citadel_gold` | nothing: the same stack at 2 cycles; the map is `citadel_gold` because the library's older `citadel` is another map |
| `teal_filaments` | `alina-25.jpg` | `teal_filaments` | nothing: `glow_filaments`' falloff glows softened, two wide haze glows and a scooped period sheet on the smooth count for the mist, on a literal ground |
| `ember_rose` | `406031.jpg` | `ember_rose` | nothing: the `inside` channel cycled into petal rings, softened falloff threads, a bead lattice. Its structure, parabolic flowers, is one the galleries lack: its locations are hand-placed (step 4's exception) |
| `star_eye` | `Abstract-Desktop-Backgrounds-Pictures.jpg` | `star_eye` | nothing: a falloff ring, the `lines` channel on both sides for the strands and the pupil's star. Its structure, quasicircle Julia sets, is one the galleries lack: its locations are hand-placed (step 4's exception) |
| `clockwork_rings` | `commons_Chaos_Clock_-_The_Steampunk_Spell-Shaper.jpg` | `clockwork_rings` | nothing: period sheets on the smooth count for the rings, the `lines` angle for the hairlines, two single bubble discs whose pullbacks ride the rings, the `lines` channel inside for the lit and spoked basin. Its structure, concentric rings round a point, is one the galleries lack (measured): its locations are hand-placed (step 4's exception) |
| `flame_veil_blue` | `bluebird-25.jpg` | `flame_veil_blue` | the `view` member of a field channel: scooped period sheets on the smooth count of four turned, scaled, off-centre views crossing additively, rims from the map's yellow end, the set a crisp hair beneath. Its structure, a thin set seen shallow with wide far field, is one the galleries lack (measured): its locations are hand-placed (step 4's exception) |
| `flame_veil_teal` | `celestial-domain-25.jpg` | `flame_veil_teal` | nothing past `flame_veil_blue`'s `view`: its veils in teal, a radial magenta nebula and veil, a white falloff star masked to the centre. Hand-placed seats, as `flame_veil_blue` |
| `flame_veil_violet` | `cipher-25.jpg` | `flame_veil_violet` | nothing past `view`: the veils on a pinwheel of views, each with a fine period sheet for its strands. Hand-placed seats, as `flame_veil_blue` |
| `flame_veil_chalk` | `chalk-drawing-25.jpg` | `flame_veil_chalk` | nothing past `view`: rank sheets on the cross trap through moved views and `shaded_blades`' strip blades for the shards, a crisp hair on the frame's own Julia dust for the snowflakes. Hand-placed seats, as `flame_veil_blue` |

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

The fifth style came from a circle packing (most likely an inversion or Kleinian
render, not escape-time), and its circles went in as one channel, the bubble trap: the
existing circle trap keeps the orbit's closest pass to a circle, which draws rings that
cross, where a packing needs **discs read at an entry**. Everything else — the dome, the
bevel, the rim, the glint, the rays, the nested beads, the cusp sparkle — is the old
layers on the channel's three reads. Three lessons. **One disc is a target most orbits
miss; a lattice of discs is one every orbit hits**, and that is the difference between a
few bubbles on the set and a frame packed with them. **A disc holding a critical point
pulls back as a peanut**, so the lattice is offset off `0`, and a disc holding an
attracting cycle smears a whole component, so the trap reads escaping orbits only and
leaves the inside to the `inside` channel. **A gallery location is a deep zoom**, where
every early disc pulls back far larger than the frame and crosses it as straight bands;
bounding the disc size as a fraction of the frame (`largest`) is what makes the style
stand at every location instead of at hand-placed shallow ones. And one about the tone
check: this style's sub-pixel beads average up at supersample 2, so while the tone pass
measured the samples, the frame's p10 at full resolution sat ~0.05–0.07 above its
target, and the stack's `p10` was hand-lowered to 0.05 to land in the band. That gap is
why the pass now measures the averaged picture: the stack holds the reference's own
0.099, and its picture reads p10 0.100 at both 1280x800 and 2560x1600; `style tones`'
640-wide copy reads 0.13–0.14, in band.

The sixth style is the fifth's packing swept by glossy blue ribbons, and the ribbons went
in as one member and one read of the same trap: a face set off-centre in each disc
(`shift`) and the lune between them (`crescent`). Read off a trap whose `largest` is
frame-sized, the lunes of the early discs are broad bands across the frame, and the
packing's own trap (bounded at a tenth of the frame) packs their faces, so **the two
layers are one lattice of discs read at two scales**. A reading needed no new layer kind:
a glow at power near zero paints the lune flat, and a light on it at one band makes the
tube. Two lessons. **A ribbon trap bounded near the packing's scale shows the bound**:
where a disc pulls back just over `largest` it is passed over and its neighbour entered
later instead, so its lune is cut by a straight edge (at `largest` 0.4 the cuts are
everywhere; at 1.5 they are rare and off the frame's large discs). **A stack's paint for
the new structure is a literal colour on purpose**: the ribbons are the contrast the
picture is about, so they keep the reference's blue under every map, and the formulation
painting them from the map is a picker row, not the default.

The seventh style is gold filigree with blue jewel orbs strung along it, and it went in
with **no new primitive**: the filigree is a light on the smooth count at one band a
step, a period sheet of four fine lines a band and the `tia` field multiplied in as
engraving; the haze and the hair of light are `glow_filaments`' falloff glows; the
sparkles are a bubble lattice of tiny discs masked to the set; and each orb is one
"jewel" (a flat blue glow, a domed light, gold rings cut by a sheet, a dark rim and an
ice-white glint) laid on a channel highest at its middle. Two lessons. **A structure the
galleries lack can come from a trap instead of a location.** The first reading put the
orbs on the set's interior components, which the galleries almost never show: 25 of
`final139_general`'s 890 non-spiral seats hold a round one and 9 hold three or more, and
hand-placed hyperbolic Julia sets were no better (past degree 2 their basins are petalled
polygons). One bubble disc with no `spacing` is the fix: unlike a lattice, which every
orbit hits, a single disc is entered only by the orbits passing near it, so its
pullbacks are a few round discs strung along the arms, at any location. The interior
keeps the same jewel on the `inside` channel where a seat has one, the locations come
from an ordinary gallery scout, and step 4's exception went unused. **A stack whose bright structure is lace misses p90 through the
map, not the layers**: the lace takes the map's top end wherever the set is within a
hair, so the first fit's near-white top read p90 ~0.10 over the reference at most seats,
and holding the map's top at a warm gold where the lights do not reach brought every
render back into the band.

The eighth style is a Julia set's cyan chain of cells over fans of fine field lines, and
it went in as **one channel**, `lines`. The escape angle was already a field, but read at
the engine's `2¹⁶` bailout its level lines are straight rays crowding into moiré; read
where the orbit leaves a circle of radius 1.2 the same angle draws curved fans cut into
sectors by the band seams, and read inside at the orbit's arrival near its attracting
cycle it fills every cell with a pinwheel of lines into its centre. Everything else is
old: a palette at one cycle on the angle for the broad rose sweeps, a rank palette on
the step for a tone per band, two period sheets at incommensurate periods for the hair,
the falloff glows for the chain. Three lessons. **Lines that double with every band
average into flat tone**: each band's angle turns `dⁿ` times round the set, so a line
period that reads well in the outer band is sub-pixel three bands in; `divide` (1.6 here)
spreads them so each band keeps lines to the set. **The galleries hold no basins**: of
`final139_general`'s 355 non-spiral Julia seats one shows three cells and 5% interior
(the inside rendered white at 320x200, its components counted; the median seat's inside
share is 0), so its locations are
hand-placed (step 4's exception), `c` found by Newton on the cycle's multiplier
(`f^p(z) = z`, `(f^p)'(z) = μ`) for a spiral `μ` in a component of period 1 to 5.
**A low-contrast reference is held through the map's top again**: its p90 is 0.38 against
a median of 0.27, and the first fit's pale-rose top read p90 0.43–0.54; holding the map's
top at a mid dusty rose, narrowing the chain's glows and a gamma of 1.4 on the sweeps
brought the worst seats to ~0.42.

The ninth style is a frame-filling tile of green leaves crossed by dark branching veins,
and it went in with **no new primitive**: the veins are `glow_filaments`' falloff glows on
`de` painted near-black, the side veins are `field_lines`' `lines` angle cut by two
period sheets and multiplied dark, a rank overlay on the lines' step cuts the frame into
bands, and a light on the smooth count domes each band. Three lessons. **Lace is not
veins**: the galleries' seats draw as a dark stencil of beads and spirals under a dark
distance glow, and only 1 of 200 probed `final139_general` seats reads ink at or under
0.03, so the locations are dendrites placed by hand (step 4's exception): Julia sets at
Misiurewicz `c` centred on points of the set found by inverse iteration, and the
Mandelbrot plane at Misiurewicz points found by Newton on `f^(k+p)(0) = f^k(0)`, which
read ink 0.001 to 0.05. **A sparse structure under a dark reference's tone target reads
as smears**: the reference is a third near-black, so a frame whose veins cover a few
percent has its far field pulled dark by the tone pass; reading the distance inverted
(pale near the set, the map's dark end far from it) turns that dark into the shadow
between leaves, each dendrite wearing a pale leaf blade, and keeps the balance at 10 of
12 drafts. The reference's density, leaves everywhere, is still beyond one dendrite per
frame: wider Mandelbrot views add no density (each decoration is a copy of the last), and
a log-polar view at three turns about a Misiurewicz point fills the frame with its arms
but reads as a kaleidoscope star, a picker row rather than the default. **Judge a hair glow at `--draft` or larger**: at 640 wide a 2e-4 falloff is a
fifth of a pixel and the veins blur into the shadow they sit in.

The tenth style is broad shaded blades in copper, slate and cream on near-black, meeting at
small spiky stars, and it went in as **one new shape of the bubble trap and two members**:
the strip about a line (`shape`, `tilt`), the `across` read and the `smallest` bound.
Everything else is old: a rank palette on the entry step at three cycles gives each blade
one flat colour, a light at one band and `rings` 1 on `across` makes it a lit cylinder, an
inverted glow on the height darkens its edges, and a falloff hair glow on `de` and a dim
rank palette on the smooth count lie in the gaps beneath. Three lessons. **The shape of a
trap is the shape of what it draws**: a disc's entries pull back round, so its crescents
read as eyes, while a strip pulls back through each critical point as a cross of
tapering arms, so a strip's entries are blades and the small ones crowding a critical
point are spiky stars, the reference's ornaments, with no layer of their own. **An entry
trap needs both bounds**: `largest` alone at 3 frames gives one blade filling the frame,
at 0.3 a fan of them; with no lower bound the blades shrink into the set as hatching
(striped fans of sub-pixel blades), and `smallest` 0.006 is what leaves the near-black
gaps the reference is a fifth made of. **A dark reference's black share is held in the
gaps, not by the ground's colour**: the tone pass carries p10 to 0.029 whatever the
ground is, so a flat ground in a third of the frame reads black 0.30 against 0.22; a
dim rank palette on the smooth count at 0.35 under the blades gives the gaps a gradient
and the frame back its share. Its locations are an ordinary gallery scout
(`--max-ink 0.12`); 32 of the 40 drafts hold the reference's balance, the misses frames
flooded by one cream blade (p90) or by gap (black).

The eleventh style is soft glossy blue lobes nestled between gold star webs with orange
cores, and it went in with **no new primitive**: the lobes are `bronze_packing`'s disc
lattice (radius 0.3 every 1, bounded at 0.02 to 0.35 frames) painted a literal blue and
domed by a light on the height at `period` 2; the gold stars are `shaded_blades`' strip
trap at a tenth of its width, painted flat gold from the map, lit across, with bright
edges and the map's orange end on the late entries crowding each star's core; the veins,
halo and sparkles are `glow_filaments`' and `gilded_orbs`' layers. Three lessons. **A
light on a disc's height rings it at one band and domes it at period 2**: at `bands` 1
and `rings` 1 the tube's crest sits at half height, so every lobe drew as an eye with a
dark centre; at `period` 2 only the tube's rising half lies across the disc and its crest
is the middle, one soft dome with one highlight, which is what "glossy, not banded"
needs. **A blade trap's coverage is its width and its `largest`, never its opacity**:
at radius 0.18 and `largest` 0.3 the blades covered most of every frame, the tone pass
turned their gold olive, and every one of the forty drafts read p90 ~0.50 against 0.68;
at radius 0.1 and `largest` 0.2 the gaps open for the lobes and 24 of 40 hold. **The
galleries hold no lobes, so the lattice supplies them**: at the scout's forty seats the
set's interior fills at least 5% of the frame at 3 and none of it at 22, while the
lattice covers 38–99% (median 82%) before the blades go on; its density is also what
holds the black share, since at spacing 1.5 the navy gaps read black 0.20–0.24 against
0.118 and at spacing 1 the mid-blue domes fill them. Its locations are an ordinary
gallery scout (`--max-ink 0.30`); the misses are frames with little gold (p90 ~0.55)
or a dark gap left open (black).

The twelfth style is a rosette of smoothly lit petals, cream and gold outside and orange,
maroon and plum within, crusted at their edges with tiny jewels on a teal ground, and it
went in with **no new primitive**: the petals are the smooth count through the map by
rank, lit at `period` 3 with a dark period sheet for the seam; the jewels are the same
count cycled three times round the map and lit once a step, masked to the set by the
inverted distance estimate at power 25, with a dark falloff hair outlining them. Three
lessons. **A petal is several escape steps**: a light at `period` 1 (`gilded_orbs`'
filigree) draws every petal of a gallery seat as a stack of corrugated ridges, and at 3
each lobe between the arms lights as one soft dome. **On lace, a jewel's colour has to
come from the map, not from a glow**: every lace sample lies within a hair of the set, so
the gold halo and hair glows of the earlier styles painted the whole fringe one khaki,
and a flat teal paint under gold bead lattices read as a beaded texture rather than
jewels; cycling the petals' own map, made **cyclic** (teal ground through cream, gold,
maroon and plum back to teal) so the cycles meet no seam, gives each decoration its own
teal, gold or maroon. **The jewels hold the highlights**: the stack held the reference's
balance at all 40 scout drafts and the eleven full renders, while the same petals with
the jewels taken off read p90 0.75–0.79 against 0.65 at both formulation seats, the
cream petals unbroken by the dark crust. The galleries hold petals at almost every
non-spiral seat, so the locations are an ordinary scout with no ink filter, whirls
dropped by eye.

The thirteenth and fourteenth styles came in one item, from two crisp deep zooms that are
close to plain escape time: `seahorse_halo` (saturated blue clusters ringed by gold,
orange and magenta inside a hot yellow-orange halo) and `citadel` (gold, cream, mauve,
plum and umber). The item allowed either to land as a palette alone if a matched map
under a named mode caught it; **neither did**, and both are the same three-layer stack
with no new primitive: the smooth count through a cyclic matched map **by rank**, a dark
falloff hair on `de`, and the tone pass. Three lessons. **What a named mode lacks here is
the rank spend, not a layer**: `smooth` with the matched map read far off the reference at
every probe seat (`seahorse_halo`'s washed into one yellow, median up to 0.19 over and
p10 up to 0.43 over; `citadel_gold`'s a dark maroon, median 0.17–0.24 against 0.45),
while the same map by rank spreads the bands over the frame's samples and holds the
balance at all 40 scout drafts of each. **The cycle count is the reference's order**:
at one cycle `seahorse_halo` runs halo, magenta, navy, blue, cream once and gives the
set's whole fringe the map's lime end, which the tone pass turns olive; at one and a half
the fringe comes round to the blue and cream, the reference's heart. `citadel`'s regions
alternate warm and dark across the frame, which two cycles draws. **A cream stop held
wide floods a far field**: the first `citadel` map's cream spanned a fifth of the map and
read white 0.056–0.096 against 0.034; held to a narrow stop between pale gold and mauve
it reads 0.02–0.07 at full size. Lights did not help either: one ring a step corrugates
every band, and a slope-only gloss barely shows, so both are picker rows. The library
already held a map named `citadel` (a pooled-library conversion, a washed brown, p90
~0.63 against 0.81 in this stack), so the matched map is `citadel_gold`. Locations are
an ordinary scout of the parameter plane.

The fifteenth to seventeenth styles came in one item, from three glow references built on
`glow_filaments`: `teal_filaments` (soft teal curl clusters in a green-grey mist),
`ember_rose` (a rose of layered petals in crimson, red-orange and gold, bead-studded, on
black) and `star_eye` (a luminous blue ring round a star, strands radiating out). All
three went in with **no new primitive**, and share one stack builder: a ground, a fog,
softened falloff glows, a period sheet on the smooth count, and per style one more
channel. Four lessons. **A soft thread is a mid-tone core, not a dim one**:
`glow_filaments`' threads are hot because their innermost glow is a hair (2e-4) of the
map's near-white top, added; screened from the map's middle at 4e-4 instead, dense curls
stop at a pale aqua rather than flooding white. Dimming did nothing beyond that, as
before: under a dark rank fog every teal draft read p90 ~0.85 against 0.666 whatever the
glows' paints, because the tone pass lifts a dark ground with a curve that carries the
structure to near-white. **The softness is the ground's**: a literal mid green-grey under
a dim fog needs no such lift, and 36 of 40 teal drafts hold. **A rank fog always spends
the map's top on the frame's nearest tenth**: `star_eye`'s ring drawn by the inverted
distance by rank read p90 0.64–0.70 at most seats at any gamma or opacity, and dimming
the other layers made it worse; a falloff glow (3e-2) for the ring over a quarter of the
fog holds 27 of 40, every miss but one a view whose disc fills the frame. **A structure
the galleries lack can be a family of Julia sets chosen for it**: the rose is a
parabolic Julia set (`z^d + c` with a fixed point of multiplier `e^(2πi p/q)`, centred on
it), whose basin's `inside` count cycled round the map draws petal rings layered about
the parabolic point, and the eye is a quasicircle (`z^d + c` at small `c`) seen whole,
where the `lines` channel inside the ring draws a star round the attracting fixed point.
Narrow views of the flower read as a bullseye of polygons and views whose pupil is a flat
disc read as one object, so both were dropped: **a frame must look as if zooming in would
show more** (Matt's ruling). Parabolic seats are slow, since the whole basin iterates to
the cap: a `--draft` took ~30 s at six threads at maxiter 3000, so their records carry
maxiter 1000, which the `inside` channel's own 1000 already reads.

The eighteenth style is a flame-fractal clock: concentric glowing rings round a
green-gold core, small luminous discs riding the rings, fine radial lines, on dark olive.
It went in with **no new primitive**, on `star_eye`'s quasicircle Julia sets seen whole.
Three lessons. **Outside a quasicircle the escape-time fields are already a clock face**:
its equipotentials are near-circles round the set, so a period sheet on the smooth count
draws the rings (a second at a quarter period the graduations), and its field lines run
out radially, so the `lines` angle cut fine with no twist draws the hairlines. **A single
disc outside the set rides the rings**: its pullbacks lie on the equipotentials, `d` discs
a ring, `d` times as many and smaller each ring inwards, crowding to the set, so the
riding discs are also the frame's proof that zooming in shows more; two discs at
different angles double them without a lattice, which would pack the whole frame. **Light
a basin from its attracting point, not its convergence count**: the `inside` count peaks
at every preimage of the fixed point, so as a glow it lit a dozen equal hot spots in a
flat olive blob; the `lines` channel's arrival step inverted lights the basin outwards
from the fixed point, its angle cut into 36 spokes, while the `inside` bands ring each
preimage, smaller and smaller towards the set. Seats whose basin is a smooth disc with
few preimages still read as one object and were dropped by eye. The structure was
measured: a 320x200 rank render of the smooth count, scored by the share of its variance
a function of the radius alone explains (best of 25 centres in the frame's middle third),
reads median 0.23 over 200 `final139_general` seats (none at 0.7, five at 0.5) against
median 0.82 at `star_eye`'s twelve quasicircle seats. Seats come from the fixed point's
multiplier `λ` (`|λ| < 1`, `arg λ` near 0 or π so the basin does not spiral): `d·z^(d−1) = λ`,
`c = z − z^d`. All 40 drafts and the eleven full renders hold the reference's balance.

The nineteenth to twenty-second styles came in one item, from four flame fractals whose
look is **veils**: translucent sheets of accumulated density crossing one another, lit at
their edges (`bluebird-25.jpg`, `celestial-domain-25.jpg`, `cipher-25.jpg`,
`chalk-drawing-25.jpg`). `glow_filaments` had reached a flame's threads but not its
sheets, and the sheets went in as **one member**, `view`: a field read off its own escape
loop at a turned, scaled, off-centre point. Everything else is old: per view a scooped
period sheet on the smooth count (dim face, bright rim) and a second, edge-only sheet for
the lit rim, screened over the frame's own, the set a crisp falloff hair underneath, and
the tone pass with `log_density`. Four lessons. **One loop's level lines never cross**:
every field of one orbit is banded along the same equipotentials, so sheets cut from one
loop nest like onion skins; a second loop at a moved point has level lines of its own,
and four such views' sheets cross at every angle, brightest where they overlap. **Views
about one centre draw a tunnel**: a shallow set's equipotentials are near-circles round
it, so views only turned about the frame's middle nest their rings into a bullseye; each
view's centre shifted 0.2 to 0.4 frame widths off makes the ring systems cross instead.
Far from the set the level lines are still arcs, which is why `cipher-25.jpg`'s S-shaped
ribbons swirling through the frame were not reached: its style draws silky arcs (a fine
period sheet per veil for the strands) round the set; moving each view's set off the frame
(shifts of 0.6 to 1 frame width) sweeps the arcs across it instead, the nearest its round
one came to the ribbons. Its first fit read p90 ~0.40
against 0.51 at most drafts, and brighter strands fixed that but washed the violet grey
under `log_density`; the kept balance is bright rims and faint strands. **Veils need far field, which the
galleries lack**: a gallery seat is a deep zoom of lace, where every view's bands crowd
into texture and the veils vanish into it. The share of a 320x200 frame lying over 0.02
frame widths from the set reads median 0.285 over the scout's 40 gallery seats (5 at 0.5
or more) and 0.544 over 40 hand seats (23), so the locations are hand-placed shallow
Julia sets, Misiurewicz dendrites and whole multibrots (step 4's exception), with those
five gallery seats in the pool; whole sets whose basin is a smooth disc read as one ring
round a blob and were dropped by eye. **Straight-edged panes are not level lines**:
`chalk-drawing-25.jpg`'s shards are flat polygons, and the nearest escape-time shapes are
the cross trap's star-shaped level lines (rank sheets through two views) and
`shaded_blades`' strip blades, pointed and curved; over a Julia dust drawn crisp they give
translucent shards with snowflakes embedded, a partial reach, and stacking screened
sheets flattened the frame until the tone pass could not pull its p10 down, so the
ground went near-black and every fill thinned.

**Re-drawing a shown keep** under a style's current stack (after its default changed) is
a one-row picker: `style render <name> --location <the keep's location> --colormap <its
public palette>`, `style picker` on a plan naming the picture, a choices file keeping it,
`style keep`; then point the catalog's `show` at the new id and rebuild `style bundle`
and `style gallery`.
