# The stack: channels, layers and their members

A style file's `style` member is the stack, handed to the engine untouched as the render
spec's `style` key (`engine/src/style.rs` parses it; `engine/src/projection.rs` holds the
projection). This is its reference; `README.md` beside it is the procedure that makes a
style, and each style file's `notes` say what that style used and taught.

## The stack and its tone

The stack is `{name, interior, tone, projection, layers}`. `interior` is a paint for a
sample whose orbit never escaped and that no layer coloured (black when absent). `tone`
(`{median, p10}`, optional) holds the frame's tonal balance: once the stack is
composited, the frame's median lightness (CIE L\* over 100) is carried to `median`, and
its 10th percentile to `p10` when given, through one curve `L ↦ b + (1 − b)·L^g` that
keeps hue and pins white. It keeps a stack fitted at one location in the reference's key
at another, where more far field would otherwise draw it paler. `tone` also takes
`log_density` (`k`): a flame fractal's log-density curve `Y ↦ ln(1 + k·Y) / ln(1 + k)`
on each sample's luminance, hue kept, laid before the median and p10 are measured, so
faint structure beside a bright core is lifted (the flame styles use `k` 8 to 10).

A **paint** is `{"rgb": "#rrggbb"}` or `{"palette": t}`, a position on whatever map the
render was given; the second keeps a style in key with every palette.

## Projection

`projection` (optional) is where each sample looks: a per-sample pre-map of the frame
before anything is iterated. The one kind is the **log-polar** (exponential-map) view,
`{"log_polar": {center, turns, power, twist, angle, ring}}`: about a vanishing point at
`center` (fractions of the frame from its top-left; the location's viewport `center` is
the plane point it shows), a sample at frame radius `r` and angle `θ` reads
`c = center + (width/2)·exp(u + i·v)` with `u = power·ln(r / half the frame width)` and
`v = turns·θ + twist·u + angle°`. Every octave round the point is one ring of the
picture, so a location whose structure repeats per octave (a Misiurewicz point, a Julia
set's repelling fixed point) tiles the disc in rings of self-similar cells. `turns` (a
whole number) copies the plane's full turn that many times round the disc; `power`
defaults to `turns`, the conformal map; `twist` (radians per e-fold of the plane radius)
shears the strip, and at a point whose structure turns by `arg λ` as it shrinks by `|λ|`
a twist of `arg λ / ln|λ|` (less whole turns) stacks every ring's copy straight above
the last; `ring` is how many escape steps make one ring (below). At one turn and power
one about the middle it is the straight view. The distance estimate and the light's
gradient go through its Jacobian, so `de` is a distance in samples and a light's
`azimuth` is the frame's.

**What only a place knows rides on its location record**: a record may carry
`"projection": {"log_polar": {"twist": …, "ring": …}}`, and `style render` lays it over
the style's projection member by member (`styles.projected`); a style with no
projection ignores it. Both come from the point's multiplier `λ` (the derivative of its
cycle) and the steps `p` per repeat: the smooth count climbs by `p` each time the
structure shrinks by `|λ|`, so `ring = k·p` with `k` the repeats nearest the ring size
the style wants. For a quadratic Julia set at its fixed point `(1 ∓ √(1 − 4c))/2`,
`λ = 2z`; a Misiurewicz point is found by Newton on `f^{k+p}(0) = f^k(0)`.

## Channels

A **channel** is `{"field": <a field spec>, "transform": <curve>}`,
`{"inside": {"iterations": N}, "transform": ...}` or `{"radial": {"center": [x, y]}}`,
and any of them takes `"invert": true` to read the position from the other end. A field
spec is anything the mode catalog's fields are made of (`smooth`, `decomposition`, `de`,
`threads` with its `sigma`, `trap_cross`, `stripe`, `tia`, …; not `itinerary`); the curve
is `linear`, `sqrt`, `log` or `scurve`, applied after the frame's stretch (and the
invert). `inside` is the one channel defined only inside the set: a smooth convergence
count, highest at each bulb's nucleus, so banding it draws rings into every bulb. Every
`inside` channel in a stack reads one loop, run at the largest `iterations` any asks
for. Each loop (the frame's, and each view's) keeps one running sum per `stripe`
density, up to four; a fifth is refused. `radial` is the one channel not read off the
orbit: nearness to a frame point
(`center` in fractions from the top-left), 1 at the core and 0 at the farthest corner.
It has no gradient, so a `light` cannot read it, and the location has to put its core
where `center` says.

A `field` channel also takes **`view`** (`{turn, zoom, shift, c}`): the field read off
its own escape loop at a moved point, `p' = m + zoom·e^(i·turn)·(p − m) + shift·w` (`m`
the frame's centre, `w` its width in the plane, `turn` in degrees, `shift` `[x, y]` in
frame widths with `y` up), with `c` (`[re, im]`, plane units) added to the orbit's `c`.
One loop's fields share their level lines, so their bands nest and never cross; a viewed
field has level lines of its own, so sheets of several views laid additively cross as a
flame's veils do. Each view is one more loop per sample. A `de` read through a view is
divided by `zoom`, so a falloff glow keeps its width; a `light` cannot read a viewed
channel. `turn`, `zoom` and `shift` are frame-relative and hold at any depth; `c` is in
plane units, so it is for shallow, hand-placed seats.

`{"bubble": {center, radius, hit, read, spacing, escaped}}` is the **bubble trap**: the
disc `|z − center| < radius` (`center` a plane point `[re, im]`) read at the step the
orbit enters it for the `hit`-th time. The samples first landing in the disc at step `n`
are a conformal preimage of it, so each is a round disc, and later steps' discs fill the
gaps: a circle packing. `read` is `height` (`1 − |z − center|/radius`, 1 at a disc's
middle and 0 at its rim, its gradient pointing inwards, so a `light` at `period` 2 domes
every disc and an inverted `glow` is a bright rim), `step` (the entry's step, one number
per disc) or `angle` (of `z − center`, a fraction of a turn: rays from each disc's
middle). `hit` 2 packs smaller discs inside each disc of hit 1. `spacing` repeats the
disc on a square lattice through `center`, so almost every orbit lands in one and the
discs fill the frame. Keep the critical point (`0`) off every disc (`center`
`[0.5, 0.5]` at spacing 1 does while `radius` is under 0.7; the default 1 does not), or
the discs it falls in pull back as peanuts. `escaped` reads only orbits that escape: an
interior cycle sitting in a disc smears its whole component into one bubble.
`largest` (a fraction of the frame width) passes over an entry whose disc pulls back
larger than that (`radius / |dz| > largest · width`), so the packing starts at the same
frame-relative size at any depth instead of drawing early discs as straight edges. Its
own loop, stopping at the entry, with `dz` kept.

`shift` (`[x, y]` in radii, length in (0, 1)) gives each disc a **face**: a smaller disc
internally tangent to its rim, centred `shift·radius` from its middle, of radius
`(1 − |shift|)·radius`. The read `crescent` is the lune between rim and face,
`a / (a + b)` with `a` the distance outside the face and `b` the distance inside the rim
(0 at the face, 1 at the rim, nothing on the face). Its gradient is the lune's, pulled
back through `dz`, so a `light` at one band lights each lune as a glossy curved band;
every disc's pullback turns its crescent its own way.

`shape` `strip` swaps the disc for the **line trap**: the strip
`|Im((z − center)·e^(−i·tilt))| < radius` about the line through `center` at `tilt`
degrees, repeated as parallel lines `spacing` apart. A strip pulls back through each
critical point of the iterate as a cross of tapering arms, so its entries are pointed,
curved **blades**. `height` is `1 − |v|/radius` (`v` the offset across the line), `step`
is one number per blade, and a strip has no `angle` and no face. The read **`across`**,
on either shape, is `(v/radius + 1)/2`, 0 at one edge and 1 at the other, its gradient
pulled back through `dz`, so a `light` at one band and `rings` 1 shades each blade as a
lit cylinder. `smallest` (a fraction of the frame width) is `largest`'s partner: the
read ends, `NaN`, at the first counted entry whose shape pulls back smaller than that,
leaving finer detail to the layers beneath.

`{"lines": {radius, arrive, settle, twist, divide, read, side}}` is the **field-lines**
channel: where the orbit crossed a circle of its own, outside the set and inside it. An
escaping orbit is read at the step it first leaves `|z| < radius` (a radius near the
set's own size, 1.2 for a quadratic Julia set, puts several bands in the frame); a
bounded orbit is run `settle` steps onto its attracting cycle (found as the first repeat
within 64 steps) and read at the first step it comes within `arrive` of a cycle point
`w`. `read` is `angle` (of `z`, or of `z − w` inside, a fraction of a turn) or `step`
(the crossing's step). Unlike `decomposition`, read at the `2¹⁶` bailout where its level
lines are straight rays crowding into moiré, these lines curve out of the points that
map to `0`, cut into sectors at the band seams, and each interior basin cell holds a
pinwheel into its centre. `twist` turns the angle by `twist·ln(|z| / radius)` radians
(`ln(|z − w| / arrive)` inside), bending lines into arcs; `divide` (outside only)
divides the angle by `divide^step`, so at the degree each band holds as many lines as
the one outside it. `side` (`both`, `outside`, `inside`) keeps one half of the frame.
Lines are cut by a sheet's `period` on the raw angle; a palette's stretch on a divided
angle is spent on the outermost band. No gradient, so no `light`; a parabolic or Siegel
interior, whose orbit never repeats, has no lines.

## Layers

Each **layer** is `{kind, blend, opacity, mask, …}`; `blend` is one of `normal`,
`multiply`, `screen`, `overlay`, `min`, `add` (applied per channel in linear light; a
`light` takes `normal` only, mixing its relit colour in by opacity),
`opacity` is in [0, 1], and `mask` (`{channel, invert, power}`) multiplies the opacity by
a channel's position. A layer only touches samples where its channel has a value.

| kind | members | what it does |
| --- | --- | --- |
| `palette` | `channel`, `palette`, `warp` | the channel through the leveled spend to the map; `palette` is the engine's palette recipe (`cycles`, `gamma`, `phase`, `transfer`: `value`, `edge`, or `rank`, which spends the map evenly over the frame's samples), refusing `mirror`, `reverse`, `rolloff` and a named mode's `scale`, `lambda`, `period` and `knee`. `warp` (`{channel, amount}`) adds a second channel's frame rank, centred on 0, times `amount` to the position before the map is read |
| `light` | `channel`, `light` | relights the stack: the channel's position is a height, cut into `bands` rings whose cross-section is a tube (`rings` of the normal; the rest is a `slope` up the field), lit Blinn–Phong from `azimuth`/`elevation` with `ambient`, `diffuse`, `specular`, `shininess`, a `rim` (sharpened by `rim_power`) and an optional `highlight` paint. At `rings` 0 the normal is the slope alone, so `bands` and `period` draw nothing. The normal is read off the orbit, never off neighbouring samples: on a `field` channel it is the smooth count's gradient, on `inside` and a bubble read its own (a bubble's `step` and `angle` borrow the height's) |
| `glow` | `channel`, `color`, `power`, `falloff` | the channel's position to `power` is an alpha for `color` under the blend. With `falloff` (on the `de` channel only) the position is `exp(−d / falloff)`, `d` the distance to the set in frame widths: the same width at every location, resolution and supersample. 2e-4 (half a pixel at 2560) is a hot core; 1e-3 a halo; 1e-2 a bloom |
| `pattern` | `checker`, `color` | a checker of escape bands (`per_iteration`) by escape-angle sectors (`sectors`, 2 is binary decomposition) |
| `sheet` | `channel`, `sheet`, `color` | translucent sheets: the channel cut into `bands` steps (offset by `phase`), by the sample's frame rank (`rank`) or by the stretch; across each step the alpha rises from 0 to `fill` (the scoop) and then to 1 within `edge` of its far end (the rim). Without a `color` it paints the stack beneath, so `add` or `screen` brightens in whatever hue is there. One band of an inverted channel is a glow falling off exponentially from the channel's low end |

`light` and `sheet` also take **`period`**: cut a ring every `period` of the channel's
*raw* value instead of `bands` across the frame's rank or stretch, counted in the
projection's `ring`s (escape steps without one). A frame-wide cut spends its steps over
whatever range the frame holds, so under a log-polar view, whose smooth count climbs
without end towards the vanishing point, they smear into the deep end; a periodic cut is
the same at every depth. On the smooth count it draws one equipotential tube per ring.

Under a style the render spec's own `palette` carries the bake and the rolloff only. The
CLI folds a sequential map (`mirror`) only when a palette layer repeats it (`cycles` > 1):
at one traversal the fold would run the near-set end back to the far field's colour.

## Defaults

What a member left out reads as (`engine/src/style.rs`'s `Default`s and serde defaults;
the stack refuses unknown members):

| where | defaults |
| --- | --- |
| stack | `interior` black; `tone` and `projection` absent |
| `log_polar` | `center` [0.5, 0.5], `turns` 1, `power` = `turns`, `twist` 0, `angle` 0, `ring` 1 |
| channel | `transform` `linear`, `invert` false |
| `inside` | `iterations` 1000 |
| `radial` | `center` [0.5, 0.5] |
| `view` | `turn` 0, `zoom` 1, `shift` [0, 0], `c` [0, 0] |
| `bubble` | `center` [0, 0] (on the critical point: always set it), `radius` 1, `hit` 1, `read` `height`, `shape` `disc`, `tilt` 0, `escaped` false; `spacing`, `largest`, `smallest`, `shift` absent |
| `lines` | `radius` 4, `arrive` 0.05, `settle` 1000, `twist` 0, `divide` 1, `read` `angle`, `side` `both` |
| layer | `blend` `normal`, `opacity` 1 |
| `mask` | `invert` false, `power` 1 |
| palette recipe | `cycles` 1, `gamma` 1, `phase` 0, `transfer` `value` |
| `light` | `bands` 8, `rings` 0.7, `slope` 0.2, `azimuth` 135, `elevation` 45, `ambient` 0.5, `diffuse` 0.6, `specular` 0.6, `shininess` 30, `rim` 0, `rim_power` 3, `highlight` white, `period` absent |
| `sheet` | `bands` 8, `phase` 0, `edge` 0.08, `fill` 0.05, `rank` true, `period` absent |
| `checker` | `per_iteration` 1, `sectors` 2 |
