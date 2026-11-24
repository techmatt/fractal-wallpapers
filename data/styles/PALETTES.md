# Palette sets

**A custom render mode is a stack plus a palette set.** Each entry of a row's `palettes`
is a map with its tuned values, keeps and score: `{colormap, was,
reference, values, keeps, score}` (`style_palettes.py` has the shape). The first entry
is the default: the mode's own map, no values; the mode's score is its
best entry's. A value is a knob-style pointer and what is written there; it must name a
member the stack writes (an entry drops at most one layer, `MOST_DROPPED`, as its `opacity` at 0, a `light` without
one set neutral: `ambient` 1, the rest 0). An entry's map is read at fixed slots of the
stack, and screen-blended layers wash towards the map's top, so its albedo goes well
past the reference's saturation. `style render <mode> --colormap <map>` applies them.

**Only picked palettes are saved**: `palettes add --mode` puts a map in a set for a
round, unkept, and `style keep` lays each kept tile's map in; an entry no tile kept
leaves the set, and its map the library by `fractal-wallpapers palettes remove <map>`
(refused while a kept palette or a live style draws in it). A kept map is renamed by
**`palettes rename <old> <new>`**, never by hand. A style merged into a mode still resolves under its old
name (`styles.alias_of`), to its entry or the mode's default.

**Merging a style into a mode** (its kept stack is the mode's up to values): rename its
map to the entry's name, write the entry with `was` the old style name and `values` from
`style_palettes.values_between(mode stack, kept stack)`, add the old name to the row's
`aliases` and its references to the row's; move its keeps (records, stacks and pictures)
into the mode's, then delete its style file, keeps file and catalog row.

`style gallery` rebuilds `fractal-drive-sync/custom-modes/`, one card per mode; `style
bundle` (the website's `custom-modes.json`) carries each published mode's kept entries.
**Re-drawing a shown keep** under a changed default is a one-row picker
(`style_keeps.py`'s docstring has the steps).
