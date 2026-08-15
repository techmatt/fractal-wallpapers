Colormaps, one JSON file per map, named for the map it holds.

Each file carries a `schema`, the map's `name` (which must match the filename),
its `kind` — `cyclic` if the last color returns to the first, `sequential`
otherwise — a one-line `source`, and the `stops`: `[position, [r, g, b]]` pairs
in sRGB8, in order, spanning `0.0` to `1.0`. The engine interpolates them in
OKLab, so the stops are control points rather than samples of a final gradient;
a dozen well-placed ones make a better map than a hundred evenly spaced ones.

`tests/test_colormaps.py` holds these files to that shape.

Most of them were not curated: they arrived by mechanical conversion because a
labeled corpus row or a vendored candidate set names them, and their `source`
line says exactly that.
