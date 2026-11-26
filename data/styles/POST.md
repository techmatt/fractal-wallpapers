# The stir and the post stage

The two members of a stack that are not layers (`STACK.md` beside this has the rest): the
**stir** moves where each sample looks before anything is iterated, and the **post
stage** works over the finished frame, where a pass may read neighbouring samples.

## The stir

`stir` (optional) is a list of up to four **passes** that move where each sample looks by
what the fractal itself reads there, after the projection and before anything is
iterated (`engine/src/stir.rs`): the whole stack is then drawn at the moved point, so
every layer is stirred alike. A pass is `{view, strength, angle, period, phase, largest,
steps}`. It reads the smooth count `ν` of a **copy** of the fractal (the frame's own, or
one seen through a `view` as a channel's is), the unit direction `ĝ` that count climbs
in, and the copy's distance estimate `L` (capped at `largest` frame widths), and pushes
the point

`p ← p + (strength / steps) · L · sin(2π·(ν / period + phase)) · e^(i·angle°) · ĝ`

`steps` times, each from where the last landed. At `angle` 90 the push runs along the
copy's level lines, so the point is carried round whatever the line encloses, about
`strength` radians in all; the sine reverses it every half `period` of the copy's count
(`period` 0: no swing), so neighbouring bands shear against each other and the stack's
own bands, which cross the copy's, are combed into S-curls and hooks. The push is as
long as the copy's set is far, so curls are large in open field, tighten without end
towards the set, and a point on or inside the copy's set never moves.

**The copy must differ from the frame** for a look that bands the smooth count: a push
along the frame's own level lines slides each band along itself and shows nothing, and
at other angles it scratches. A turned, scaled and shifted view is what stirs.
`strength` 3 over 4 `steps` is a poured liquid; 6 over 8 winds the curls further;
`zoom` under 1 with a larger `largest` makes a few frame-wide swirls (keep a second,
finer pass under them). More `steps` at one `strength` follow the flow more closely:
one large jump folds the picture over itself.

A light and a distance go through the stirred map's Jacobian as through a projection's,
so a relief is lit as the curled surface it draws and a falloff glow keeps its width.
Each step is one escape loop per sample, three when a light, a distance or an `inside`
channel needs the Jacobian (two passes of 4 and 3 steps: 21 loops). A point inside the
copy's set ends its pass at the first loop, stopped once the orbit is proven interior;
the cost is the samples close outside it, whose every loop runs most of the way to the
seat's `maxiter`, so a stirred stack is drawn at seats of low `maxiter` first. A
bubble's `largest` and `smallest` stay plane lengths, as under a projection. It is a
pure function of the sample: tiles and `style-wasm` draw the same picture, **because the
stir makes its own logarithm and sine** from `+ − × ÷ √`: several steps near the copy's
set magnify a last-bit difference between two maths libraries into visibly different
samples (`engine/src/stir.rs`; a fractional-degree family, whose every step is the
library's `powf`, is the exception, as is a point that came through a projection). The
module on one thread takes about 100 to 140 s for a
640x400 ss2 frame of two passes with a light, 28 s for one gentle pass without.

## The post stage

`post` (optional) is a list of **passes** over the whole composited frame, run in order
after the layers and before the tone is measured, so `tone` holds on the picture the
passes made. A layer never reads a neighbouring sample; a pass is the part of a style
that may. Each is a pure function of the frame's buffers (its linear samples, whether
each orbit escaped, the distance to the set, a height), so `style-wasm` draws the same
picture (`style wasm-parity`), and **a style with a post stage is drawn whole, never in
tiles** (the module's `open` reports `"post": true`; `tile` refuses). Every length is a
fraction of the frame's width, so `--draft` and full size are one picture.

There are three kinds, `mosaic`, `paper` and `rays` (below). A kind is wired in three places:
`engine/src/post.rs`'s `Pass` (its variant, `height` and `validate`), and
`engine/src/style.rs`'s `Style::fields` (the lanes the frame's loop carries for it) and
`posted` (the height it is handed and the pass it runs). Python never validates the
`post` list: the engine's `validate` is the only check.

**`mosaic`** is a recursive tiling whose cells split where the set is, each cell a facet
of the picture under it.

| member | what |
| --- | --- |
| `largest`, `smallest` | the edge of the largest cell (at least 1/256) and the floor no cell's edge goes under (at least 1e-5), in frame widths |
| `levels` | the most times a cell of the largest size splits (at most 10) |
| `reach` | a cell splits in four while the set is within `reach` of its edges of it (the least `de` under it), or the set's edge crosses it; 0 keeps only the second rule |
| `detail` | a cell also splits while the picture inside varies by more than this (the standard deviation of its root luminance); 0 is off |
| `spiral` | `{center, arms, twist}`: the lattice is quads of a log-polar grid about `center` (fractions of the frame), `arms` to a ring, each ring turned `twist` quads past the one outside it; absent, equilateral triangles split by their edges' midpoints |
| `rhombi` | `true`: the cells are the triangle lattice's rhombi (two triangles each), split in four as slanted quads, so two families of seams run where the triangles have three |
| `tilt` | triangles and rhombi: the lattice turned by this many degrees |
| `fill` | `flat`, the mean of the picture under the facet; `turned`, the picture itself, turned about the facet's middle and slipped by `shift` |
| `shift` | `turned`: how far each facet's view is slipped (0 to 4 facet edges), each facet its own way, so neighbours show the picture broken along their seam |
| `turn` | `turned`: degrees, times a number per facet: a triangle's or rhombus's one of −1, 0, 1; a spiral quad's column round its ring, counted at its middle (360 over `arms` turns each view with the ring) |
| `relief`, `height` | each facet tilted to the plane fitted through `height` under it, `relief` the tilt per unit of height across one facet edge; `height` is a plain field channel (no view) stretched over the frame, or the picture's own root luminance when absent |
| `fold` | each facet a low pyramid of this slope, one face per edge |
| `azimuth`, `elevation` | where the light on `relief` and `fold` comes from; a facet never tilts past a slope of 0.6, so at elevation 45 a face turned away dims to about a third |
| `inlay` | `{levels, amount}`: the cells the facet would split into, `levels` deep (at most 6, never under `smallest`), each lightened or darkened by up to `amount` of its colour: nested detail inside a calm facet, without splitting it |
| `seam` | `{width, color, opacity}`: a line along every facet's rim, `width` in frame widths and never over 0.08 of the facet's edge |
| `faces` | triangles only, three gains in [0, 4]: each facet's colour times the gain of the cube face it is (the six triangles round every third lattice vertex pair into three rhombi), so the tiling reads as stacked cubes at every size; an `inlay` then draws cubes too, gain `g` as `1 + amount·(g − 1)` |

`opacity` (in [0, 1]) lays that much of the mosaic over the picture it was made from:
under 1 the facets are translucent plates and the stack's own detail shows through.

A mosaic costs no escape loop: it reads the lanes the frame already has, plus one `de`
lane. It holds about 150 bytes a cell, and refuses a tiling of over six million cells.

**`paper`** is the frame as stacked sheets of cut paper: a height cut into a few flat
sheets, each one colour with a hard edge that is the fractal's own level line. No
lattice: the shapes are the set's bands.

| member | what |
| --- | --- |
| `height` | the channel the sheets are cut from: a plain field channel (no view), the smooth count when absent. It is cut on its **rank** over the frame, so `invert` (which end is the top sheet) changes the picture and `transform` does not |
| `levels` | how many sheets (2 to 64) |
| `taper` | each sheet's share of the frame as a multiple of the one under it, in (0, 1]: 1 is equal areas, under 1 the sheets thin towards the top (towards the set, on the smooth count) |
| `fill` | `map`: each sheet reads the map once; `picture`: the mean of the picture under the sheet |
| `hop`, `phase` | `map`: sheet `i` reads the map at `phase + i·hop`, wrapped, so neighbouring sheets can be far apart on it (a map of eight flat inks at `hop` 0.125, `phase` 0.0625 reads each ink's middle in turn); `hop` absent, the sheets walk the map once end to end. Each is within 1000 turns |
| `shadow` | `{width, offset, azimuth, opacity, color}`: each sheet's shadow on the sheets under it, fading over `width` and thrown `offset` from the edge (frame widths, each at most 0.25), away from a light at `azimuth`; `opacity` in [0, 1]; `color` black when absent |
| `ragged` | `{reach, length, width, azimuth, accent}`: a dry brush's edge. Each sample takes the sheet of a sample up to `reach` away along the stroke (`azimuth`), every bristle (`width` across) its own distance, the wobble running `length` along; an `accent` (`{color, share}`) paints that share of the strokes (in [0, 1]) its own colour where they moved an edge. `reach` is 0 to 0.5 frame widths, and 1e-5 ≤ `width` ≤ `length` ≤ 4 |
| `opacity` | how much of the paper is laid over the picture beneath, in [0, 1] |

Under a stir the height is the stirred count, so the sheets are combed with everything
else: flat inks marbled into folds (`marbled_pour`).
A sample whose orbit never escaped keeps the picture beneath (the stack's `interior`),
lies over every sheet (under them all when the height is inverted), and is never
dragged by the brush, so the set's own edge stays whole. The pass costs no escape loop
beyond its height's field, one sort of the frame's heights, and for a shadow four box
blurs.

**`rays`** casts straight beams of light from the frame's brightest samples: a star
filter's spokes, or shafts through haze. One escape loop draws only arcs (a beam is a
line thin along its whole pullback), so the beam is a pass: each sample brighter than
all but `share` of the frame casts the part of its light above that cut, and the beams
are added over the picture. What casts is whatever the stack lit, so a beam's root is
the fractal's own: a spark, a rim, the set's hair.

| member | what |
| --- | --- |
| `share` | the brightest share of the frame's samples that cast, by luminance, in (0, 0.5]: about 0.002 for stars off sparks, 0.03 for shafts off the lace. A sample casts only what it has above the cut, so a frame whose brightest share is one flat value casts nothing |
| `spokes`, `angle` | each source's beams, evenly round the circle from `angle` (degrees anticlockwise from the right): 2 a streak, 4 a cross, 6 or 8 a star (at most 16). Each spoke is one sweep over the frame, each sample its own light plus `fade` of the beam one step behind, so a beam at a multiple of 45 degrees stays one sample wide its whole length (one upright reads as rain) and any other spreads as it runs, the step's interpolation repeated: about 6 samples across after 200 steps at 15 degrees |
| `length` | how far a beam runs before it fades to 1/e, in frame widths (1e-4 to 2) |
| `center` | shafts instead of spokes: each sample gathers the light between it and this point (fractions of the frame), so shafts run outwards from it. A shaft is the **mean** of the light behind it (a spoke is the sum), summed by doubling, 2^k samples in `k` one-tap passes, out to three `length`s. `spokes` and `angle` are not read |
| `strength` | the beams' gain, 0 to 100. A spoke sums the samples behind it, so its gain is read at the draft's 2560 samples across and scaled by that over the frame's: a draft, the full frame and the explorer draw one picture |
| `color` | every beam this paint times the luminance of the light its source casts (a dark paint dims the beams); absent, each beam that light's colour |

A pass costs no escape loop: a select over the frame's luminance, then a sweep per spoke
(two transposes for a spoke nearer level than upright), or about a dozen one-tap passes
for shafts.

## Defaults

| where | defaults |
| --- | --- |
| `stir` pass | `view` straight (the frame's own), `strength` 1, `angle` 90, `period` 4, `phase` 0, `largest` 0.05, `steps` 1 (at most 16) |
| `mosaic` | `largest` 0.25, `smallest` 0.004, `levels` 6, `reach` 1, `detail` 0, `rhombi` false, `tilt` 0, `fill` `flat`, `turn` 0, `shift` 0, `relief` 0, `fold` 0, `azimuth` 135, `elevation` 45, `opacity` 1; `spiral`, `height`, `inlay`, `seam`, `faces` absent |
| `spiral`, `inlay`, `seam` | `center` [0.5, 0.5], `arms` 12, `twist` 0; `levels` 2; `color` black, `opacity` 1 |
| `paper` | `height` the smooth count, `levels` 9, `taper` 1, `fill` `map`, `phase` 0, `opacity` 1; `hop`, `shadow`, `ragged` absent |
| `rays` | `share` 0.02, `spokes` 4, `angle` 45, `length` 0.05, `strength` 1; `center`, `color` absent |
| `shadow`, `ragged` | `offset` 0, `azimuth` 135, `opacity` 1, `color` black; `azimuth` 0, `accent` absent (`reach`, `length`, `width` and a shadow's `width` are always given) |
