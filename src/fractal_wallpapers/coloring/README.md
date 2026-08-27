Applying colour to a field: the tone band a finished render is held to, and the
operator that pulls it there.

A colormap is a ramp somebody drew, and it was drawn without knowing what field it
would be spent on. Sweep it across a location whose escape times all bunch at one
end and the picture comes out muddy, or blown out, or flat — not because the map
is bad but because this location spends it badly.

```
band       the tone band, measured off finished wallpapers that are already good
autolevel  the operator that projects a render onto it, or leaves it exactly alone
```

```
fractal-wallpapers coloring show
fractal-wallpapers coloring derive-band --from <folder> --write
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

**What the operator costs, measured.** The measurement is linear in the picture:
0.27 s per megapixel, which is 0.063 s on a candidate and 1.01 s on a release
render. Most of that is still the sRGB→Oklab conversion; the linearisation inside it
used to be a third of the measurement and is now a 256-entry table, which is exact
because the input is `uint8` (`palettes.space._srgb_to_linear`). Before the table the
same three release pictures measured 1.42–1.48 s, so the rate was 0.39–0.43 s/Mpx.
The application is size-independent, because it works on the stops rather than on
pixels.

**The second pass is a colormap swap over the same field**, which is why
`curation.colorize.render` routes it through the shared field wherever the mode
has one: the spec is identical but for `colormap_dir`, so on a `field` coloring
the operator's second pass costs a `recolor` (0.04 s at candidate size) rather
than a second iteration pass. On a composite, the modulate and the direct traps
there is no field to dump and it is still a full second render. On the release
rows profiled so far the curve acted on 42% of them, and on curation candidates
on 47.7%.

**Which leaves the measurement as the operator's own cost, and on a shareable
mode it is now the larger half.** A candidate whose colouring is a 0.04 s lookup
pays about 0.15 s to be *read* — a JPEG decode and an Oklab pass in Python, over
a picture the engine had in memory as linear light a moment earlier and threw
away. That is the shape of the next optimization here and it is written down
rather than taken: the engine would have to report the three statistics
`tone_stats` derives, at which point the operator would read a number instead of
a picture.

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
