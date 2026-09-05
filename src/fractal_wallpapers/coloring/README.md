Applying colour to a field: the tone band a finished render is held to, and the
operator that pulls it there.

A colormap is a ramp somebody drew, and it was drawn without knowing what field it
would be spent on. Sweep it across a location whose escape times all bunch at one
end and the picture comes out muddy, or blown out, or flat — not because the map
is bad but because this location spends it badly.

```
band          the tone band, measured off finished wallpapers that are already good
autolevel     the operator that projects a render onto it, or leaves it exactly alone
texture_flat  which renders' modulate texture carried no information at all
```

```
fractal-wallpapers coloring show
fractal-wallpapers coloring derive-band --from <folder> --write
fractal-wallpapers coloring texture-flat measure     # render what is unmeasured
fractal-wallpapers coloring texture-flat stamp       # carry it onto the ledger rows
fractal-wallpapers coloring texture-flat show
```

**The correction is measured on the picture and applied on the palette.** Every
pixel of a palette-mapped render is a lookup into the map, so a monotone tone
curve pushed through the map's own stops moves every pixel's lightness by exactly
that curve. The measurement reads a rendered image; the application writes a
colour ramp and hands it back to the engine. Python here never makes a pixel.

**In band is the exact identity.** Three statistics, each projected onto its band —
inside, itself; outside, the nearest edge — and when all three are already inside
the operator returns the render's own file rather than making a second one. That
is what makes it safe to ship switched on: the curve is *skipped*, not applied at
strength zero. On this repository's first release run it was the identity on
thirteen of twenty palette-mapped candidates and on four of six release renders.

**The stamp replays.** Everything the curve is a function of is recorded — the band
with its own sha256, the statistics it was derived from, the curve's coefficients
— so the leveled stop list rebuilds from the stamp alone, with no image and no
re-measurement. Without that, a release record could say which row shipped and not
which *image* that row was, which after the operator ships on is no longer a
record of the decision.

**What the operator costs, measured.** The measurement is linear in the picture.
On a 640x360 candidate it is 30 ms and it used to be 67 ms, of which the
sRGB→Oklab conversion was 52 ms and three `numpy.cbrt` calls were 31 ms of
*that* — numpy runs a cube root one element at a time. It is now read through
[`palettes.space.lightness_and_chroma`], which is the same arithmetic split over
threads: every step between a pixel's three bytes and its two numbers is
elementwise, so a chunk read on its own thread reaches the bytes one pass would.
The linearisation inside it is a 256-entry table, exact because the input is
`uint8` (`palettes.space._srgb_to_linear`). The application is size-independent,
because it works on the stops rather than on pixels.

**The second pass is a colormap swap over the same field**, which is why
`curation.colorize.render` routes it through the shared field wherever the mode
has one: the spec is identical but for `colormap_dir`, so on a `field` coloring
the operator's second pass costs a `recolor` (0.04 s at candidate size) rather
than a second iteration pass. On a composite, the modulate and the direct traps
there is no field to dump and it is still a full second render. On the release
rows profiled so far the curve acted on 42% of them, and on curation candidates
on 47.7%.

**The picture the operator reads is not the buffer the engine held, and that
closes the obvious optimization.** Supersampling and JPEG both average colour
*after* the colormap lookup, so what `tone_stats` measures has been through the
resample filter and a lossy encoder. Recoloured to both formats on twenty-four
real candidates, the JPEG round trip moves all three statistics on **24 of 24**
and moves the levelled stop list itself on **17 of 24** — white point by 2.0e-3
at the median. So having the engine report the three numbers off its own
pre-encode buffer would draw a different picture on about seven firing
candidates in ten, and the band's sha is in the recipe key, so those pictures
would keep the names of the old ones. The route is closed unless a decoder in
the engine reproduces libjpeg-turbo bit for bit, which is a bigger claim than the
saving: the **decode is 4.5 ms, 6.7% of the measurement.** `tests/test_autolevel_identity.py`
is the pin that keeps this honest — every mode the operator applies to, drawn
through `colorize.render`, with both the levelled colormap and the picture
digested.

**What is left of the stage is the curve, not the measurement.** Over 200 real
firing candidates `curved_stops` is 15 ms at the median and 100 ms at P90; the
top decile is 47% of its total. That tail is `cap_lightness`, whose chroma
bisection calls the gamut bisection inside it — up to 540 sRGB↔Oklab round trips
over 257 densified stops, each about ninety numpy calls on an array too small
for any of them to be work rather than dispatch. `densify` and its position
rounding are cached per map (`_densified`, 1024 slots — the drawable pool is 942 maps
and a run draws from all of it, so a cache sized for a handful hits 0.072 where
one sized for the library hits 0.983), which took two fifths off a levelled
candidate; the bisections are untouched, because the only way to make ninety
dispatches cheap is to stop dispatching, and a reimplementation would have to
agree with numpy's `pow` and `cbrt` to the last bit on every platform this
builds on.

**Which colorings a run may draw is a function, not a rule each site remembers.**
The engine's catalog tiers every named mode, and this side reads that tiering at
call time through `engine.production_modes()` — so a mode cannot be production on
one side of the boundary and niche on the other. `curation.colorize.modes_for`
is the **only** place a mode is drawn: the niche exclusion lives there rather
than at each of its callers, and the paying head decides the roster (the smooth
judge owns the one smooth coloring, the strange judge owns every other production
mode). What the tiers are and which mode sits in each is
[the engine's](../../../engine/README.md).

**The direct-trap family is excluded by kind**, at the site that decides rather
than by a test buried in the measurement. A direct trap is a thin bright figure
over a flat ground, so its tone statistics describe the ground; a new direct mode
must not be able to acquire a tone curve by being added.

**A modulate whose texture said nothing is another mode's render, exactly.** The
one modulate coloring shifts its base's palette position by a normalized texture,
and normalizing needs a span. Where there is none the shift is zero everywhere and
the picture is the base spent by rank — bit for bit the `smooth` mode at
`transfer: {"kind": "rank"}`, since every catalogued composite and the modulate
are built on the same smooth base. The engine reports that per render as
`RenderReport.texture_flat`; `curation.mode_policy.routed_mode` is where the
consequence is spelled, and such a render routes as `smooth` wherever a mode or a
kind is decided — the seating pool, the census, the per-mode bars, the mode floors
and both label stores.

**"Bit for bit" is measured, not asserted.** All 17 `texture_flat` seats of the
914 in tentative gallery `20260904T023748Z` were re-rendered two ways on
2026-09-04 and came back **sha256-identical to the shipped picture on 17 of 17
both ways** — at the recipe's own mode, `itinerary`, and at `smooth` with
`transfer: {"kind": "rank"}`. Rendered at `smooth` *without* the rank transfer
they agree with nothing: median mean absolute channel difference 71.43. The
recipes themselves carry `transfer: {"kind": "value"}`, which is not a
contradiction — `coloring.rs`'s `agrees_with` **requires** the transfer left
unset alongside a modulate, because spending the base by rank is part of what
the modulate is.

`texture_flat` here is the register for the rows written before the engine
reported it. It is **tracked**, because the label corpus is tracked and routing
that differed between two checkouts of one commit would be two corpora wearing one
name; and it is keyed on the field side of the render — place, frame, sample grid,
iteration cap, coloring — so one probe answers for all thirty-two maps at a
location. Establishing a single entry costs a render: frame width does not
separate the two populations in any partition, and counting distinct values in a
dumped `f32` field is wrong 15.2% of the time in the direction that matters.
