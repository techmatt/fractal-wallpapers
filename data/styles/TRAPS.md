# The trap channels: bubble, lines and stroke

Three channels of a stack (`STACK.md` beside this has the rest) read the orbit against a
shape of its own plane, each in its own loop: the **bubble** reads a disc or a strip at
the step the orbit enters it, **lines** the angle at which it crosses a circle, and the
**stroke** how far the sample is, in the frame, from the nearest pullback of a line or a
circle.

## The bubble

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
leaving finer detail to the layers beneath. **`fade`** (a share in (0, 1]) thins the
`height` to 0 towards either bound, from `(1 − fade)·largest` and `(1 + fade)·smallest`,
as a stroke thins: unfaded, a neighbour reading the next entry where `largest` passed over
one meets it at a seam; faded, shapes come and go softly, and several `hit`s laid
additively draw each shape whole (107 deleted `gilded_leaves`, which did; `bokeh_bloom` lays
one). A loop is shared only by reads with
one `fade`: a `step` read beside a faded height runs a loop of its own unless it takes the
same `fade`. Fade suits a height read laid additively: an inverted `height` (a rim glow)
reads 1 where the height faded, so it lights the faded part of each shape as a hard-edged
shard (074's dials take no fade); a lower rim `power` widens those shards too, while a higher one with a smaller `largest` reads continuous (108). With `spacing`, nearly every escaping sample enters some shape, so a
layer on `height` paints the whole frame unless its `power` is high (8 lights a blade's
spine alone).

## Field lines

`{"lines": {radius, arrive, settle, twist, divide, read, side}}` is the **field-lines**
channel: where the orbit crossed a circle of its own. An
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

## The stroke

`{"stroke": {shape, center, on_c, radius, tilt, width, taper, node, largest, smallest,
steps, read, side}}` is the **stroke trap**: a `line` (through `center` at `tilt`
degrees) or a `circle` (`radius` about `center`) drawn as a pen stroke along every
pullback of it, each stroke one weight along its length. The other traps measure in the
orbit's plane, so their shapes swell and pinch with `1/|dz|` (a strip's blades); a
stroke's distance is taken **in the frame**, `t / |dz|` with `t` the orbit's distance to
the curve at that step, and the read is the nearest stroke over the steps, `d`, in
half-widths. A step's curve has a size in the frame, `S = radius / (|dz|·w)` frame
widths (`w` the frame's width in the plane), and its stroke is `width · S^taper` frame
widths to each side: `taper` 0 draws every pullback as a hairline of one width, 1 is the
plane trap again, and between them a frame-wide curve is a thick tube whose small copies
thin to hairlines. `largest` and `smallest` pass over the steps whose curve is larger or
smaller than that many frame widths, so the strokes start and stop at a size at any
depth instead of filling the field with lace; `steps` is the most steps read (a slow
seat holds hundreds of curves of one size; a dozen keeps the field calm). A stroke thins
to nothing over the last quarter towards either bound, and the last step read thins as
the first fills out, so no stroke ends at a cut.

`on_c` measures `center` from the orbit's `c`. A line through the critical value pulls
back through the critical point as a cross, so on a Julia set every preimage of `0` is a
**star** of strokes joined to its neighbours by long curves, where a line that misses it
pulls back as hyperbolas that never meet; a circle pulls back as closed loops, round only
while small beside the distortion round them: at the galleries' seats an `on_c` circle
reads as long arcs, so concentric rings come from a bubble's `height` (`filigree_dials`). `node` (0
is off) counts every step as stretching the plane at least that much: at a crossing,
where `dz` is 0 and `S` has no bound, the strokes then swell into a round node instead
of leaving a hole under `largest`.

**Cost.** Each distinct curve is its own read, but every stroke of a sample shares one run
of its orbit (`style::strokes`), which ends when every curve's `steps` are read or the
orbit escapes; a curve's two reads (a glow at two powers) cost nothing extra. A mesh of
tilts costs the orbit once plus a few operations per curve a step: `hairline_rays`' six
tilts drew 2.3 times faster than one loop per curve, byte for byte the same (068).

`read` is `height` (`1 − d` on the stroke, its gradient towards the curve, so a `light`
at `period` 2 lights each stroke as a tube), `across` (0 at one edge, 1 at the other; no
`light` reads it), `step` (the nearest stroke's), or `glow` (`exp(−d)` wherever a step
was read: a halo as wide as its stroke, which a `glow` layer's `power` sharpens). Every
read but `step` is a position already: a glow, a light, an unranked sheet and a mask take
it as it is, where a palette layer and a ranked sheet spend it over the frame as they do
any channel. `side` is the `lines` channel's. Its own loop with `dz`, ending once `steps`
steps were read, else at the escape, or at `maxiter` for a bounded orbit whose curves
stay out of the bounds (`side` `outside` leaves those out).

## Defaults

| where | defaults |
| --- | --- |
| `bubble` | `center` [0, 0] (on the critical point: always set it), `radius` 1, `hit` 1, `read` `height`, `shape` `disc`, `tilt` 0, `escaped` false; `spacing`, `largest`, `smallest`, `fade`, `shift` absent |
| `lines` | `radius` 4, `arrive` 0.05, `settle` 1000, `twist` 0, `divide` 1, `read` `angle`, `side` `both` |
| `stroke` | `shape` `line`, `center` [0, 0], `on_c` false, `radius` 1, `tilt` 0, `width` 0.004, `taper` 0.5, `node` 0, `steps` 256, `read` `height`, `side` `both`; `largest`, `smallest` absent |
