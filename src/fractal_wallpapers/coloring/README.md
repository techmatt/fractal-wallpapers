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

**The direct-trap family is excluded by kind**, at the site that decides rather
than by a test buried in the measurement. A direct trap is a thin bright figure
over a flat ground, so its tone statistics describe the ground; a new direct mode
must not be able to acquire a tone curve by being added.
