# The stack: channels, layers and their members

A style file's `style` member is the stack, handed to the engine untouched as the render
spec's `style` key (`engine/src/style.rs` parses it; `engine/src/projection.rs` holds the
projection). This is its reference; `README.md` beside it is the procedure that makes a
style, and each style file's `notes` say what that style used and taught.

## The stack and its tone

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

## Projection

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

## Channels

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

## Layers

Each **layer** is `{kind, blend, opacity, mask, …}`; `blend` is one of `normal`,
`multiply`, `screen`, `overlay`, `min`, `add` (applied per channel in linear light),
`opacity` is in [0, 1], and `mask` (`{channel, invert, power}`) multiplies the opacity by
a channel's position. A layer only touches samples where its channel has a value.

| kind | members | what it does |
| --- | --- | --- |
| `palette` | `channel`, `palette`, `warp` | the channel through the leveled spend to the map; `palette` is the engine's palette recipe less `mirror`, `reverse` and `rolloff` (`cycles`, `gamma`, `phase`, `transfer` — `value` by default, `edge`, or `rank`, which spends the map evenly over the frame's samples). `warp` (`{channel, amount}`) adds a second channel's rank in the frame, centred on 0, times `amount` to the position before the map is read: a radial palette warped by the smooth count follows the arms instead of drawing a target when the map is not in lightness order |
| `light` | `channel`, `light` | relights the stack: the channel's position is a height, cut into `bands` rings whose cross-section is a tube (`rings` of the normal; the rest is a `slope` up the field), lit Blinn–Phong from `azimuth`/`elevation` with `ambient`, `diffuse`, `specular`, `shininess`, a `rim` (sharpened by `rim_power`, default 3) and an optional `highlight` paint. The normal's direction is read off the orbit, never off neighbouring samples: on any `field` channel it is the smooth count's gradient (the way the count climbs), on `inside` and a bubble read its own (a bubble's `step` and `angle` borrow the height's) |
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
