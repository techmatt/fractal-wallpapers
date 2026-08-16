The tone band the autolevel operator projects a render onto.

```
levels_band.json    three tone statistics, banded across a reference set
```

`levels_band.json` is a **measurement, not a taste**. Three statistics — a black
point, a white point and a midtone, all in Oklab lightness — are read off a folder
of finished wallpapers that are already good, and each one's band is `[P10, P90]`
across that set. A render whose three statistics all sit inside these bands is
left exactly untouched: that is what makes the operator safe to ship switched on,
and it is why the identity is structural rather than a strength of zero.

The two alternatives are in the record beside the band, and neither was taken.
The inter-quartile range calls one reference image in four out of range; the full
min–max is one image's opinion at each edge. The choice is stated rather than
derived, and the sensitivity is in the file.

**The reference set lives outside this repository and is only ever read.** What
ships is the measurement, the per-image rows it was taken from, and a digest over
the set's names and bytes — never a path, because a tracked record that named
somebody's home directory would be a record about one machine. Every stamp the
operator writes names this file by its sha256, so a re-derivation that moved an
edge is visible from the stamp alone.

A re-derivation that moves an edge is a **new band**, which is a new decision
about what the operator does to every render. That is why it takes an explicit
write and why the record carries the date and the image count that produced it.

```
fractal-wallpapers coloring show
fractal-wallpapers coloring derive-band --from <folder of finished wallpapers> --write
```
