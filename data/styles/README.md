Styles: named layer stacks that capture the *feel* of a reference picture, one JSON
file per style, rendered with any colormap.

```
fractal-wallpapers style list
fractal-wallpapers style show floating_on_dreams
fractal-wallpapers style render floating_on_dreams --location <record.json> --colormap <any map>
fractal-wallpapers style render floating_on_dreams --manifest <records.jsonl> --out-dir <dir>
fractal-wallpapers style render <draft.json> --location <record.json>      # a draft, before it joins
fractal-wallpapers style keep floating_on_dreams <picker>.choices.json     # save a picker's keeps
```

`<name>.keeps.json` beside a style is not a style: it is the renders Matt kept from its
pickers, each with what redraws it, and its pictures live in
`fractal-drive-sync/style-keeps/<name>/` beside the reference.

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
     from the scout's forty, in the current formulation with the matched map.

   Render with `style render` (`--manifest` into one folder per row): each render is
   logged to `renders.jsonl` beside it. Then write a plan and build the picker:

   ```
   fractal-wallpapers style picker <plan.json>
   ```

   (`style_picker.py`'s docstring has the plan's shape; a named-mode baseline carries its
   own `render`). It writes the JPEGs, a manifest whose every row is `"kind": "many"`,
   `"default": []`, and the renders sidecar `style keep` needs.
7. **Round two, once Matt's keeps are back: twelve tiles or fewer.** His kept
   formulations at his kept locations, and three or four library maps on them, each map
   drafted at `--draft` first and dropped on a bullseye (concentric bands the map turns
   into rings), a wash, or a tone miss.
8. Write `reference`, `reuses`, `adds` and `suggested_colormap` into the style file.
9. **Save Matt's keeps** after each round: `fractal-wallpapers style keep <name>
   <picker>.choices.json` writes `<name>.keeps.json` here and copies the pictures, with
   the reference, to `fractal-drive-sync/style-keeps/<name>/`; a later round merges in.

### The per-image prompt

```
Goal: a new style from <image>, in fractal-drive-sync/style-refs/.
Name: <style_name>. The look, in a line: <what makes the picture>.
Structure it needs (optional): <e.g. thin sets: --max-ink 0.10; Julia sets only: --kind julia>.
  Lacking in the galleries? <yes: hand or atlas points via --points, per step 4's exception>.
Keep / avoid (optional): <what must survive, what must not appear>.
Round: 1 | 2 with <picker>.choices.json (round 2: the kept formulations and locations).
Follow data/styles/README.md's *A new style from a reference image*. Commit when done.
```

The procedure covers the rest by itself: the layer reading, any engine primitive and
its identity check, the matched map and `palettes add`, the gallery scout with no
spirals, the tone targets and the draft-size check, the picker with nothing
pre-selected and its sidecar, and `style keep`.

## The styles

| style | reference | suggested map | added |
| --- | --- | --- | --- |
| `floating_on_dreams` | `floating-on-dreams-25.jpg` | `floating_on_dreams` | the compositor, `gradient`, `inside`, `light`, `glow`, `pattern`, `mask` |
| `yas` | `yas-25.jpg` | `yas` | `radial`, `sheet`, `invert`, `warp`, `tone` (and `tone` back onto `floating_on_dreams`) |
| `teal_tunnel` | `795548-3840x2160-desktop-4k-fractal-background.jpg` | `teal_tunnel` | `projection` (`log_polar`), `period` on `light` and `sheet`, a location's own `projection` |
| `glow_filaments` | `Black-and-Green-Abstract-Wallpaper.jpg` | `glow_filaments` | `falloff` on `glow`, `log_density` on `tone` |
| `bronze_packing` | `795549-3840x2160-desktop-4k-fractal-background.jpg` | `bronze_packing` | the `bubble` channel (`height`, `step`, `angle`; `hit`, `spacing`, `escaped`) |
| `ribbon_packing` | `795565-3840x2160-desktop-4k-fractal-wallpaper-image.jpg` | `ribbon_packing` | the bubble's `shift` (a face in each disc) and its `crescent` read |

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
