What is measured about a finished coloring: the tone band the autolevel operator
projects onto, and which renders' texture layer said nothing.

```
levels_band.json    three tone statistics, banded across a reference set
texture_flat.jsonl  the renders whose modulate texture carried no information
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

## `texture_flat.jsonl`

One row per **field identity** — a digest of the place, the frame, the sample
grid, the iteration cap and the coloring, and nothing the recolour half spends —
saying whether that render's modulate texture had a span to normalize against. A
`true` means the picture is its base spent by rank *bit for bit*, so the render
routes as `smooth` everywhere a mode or a kind is decided; `curation`'s ledger
rows carry the same flag as a bare boolean and the label stores take it from
here, because a stored verdict is an original and is never rewritten.

The key deliberately excludes the colormap and every palette knob, so one probe
answers for all thirty-two maps at a location. It deliberately **includes** the
geometry: a candidate is drawn at 640x360ss2 and a labelled picture at
1280x720ss2, and the second may resolve a texture the first flattened.

Tracked, because routing that differed between two checkouts of one commit would
be two corpora wearing one name. Each entry costs a render to establish — there is
no proxy, and the two obvious ones are both wrong — so the file grows only when
somebody runs the measurement.

```
fractal-wallpapers coloring texture-flat measure     # render what is unmeasured
fractal-wallpapers coloring texture-flat stamp       # carry it onto the ledger rows
fractal-wallpapers coloring texture-flat show
```
