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

**A round-two lever or map that becomes the default** is a hand edit: `style keep` only
appends keeps, and writes `values` only for an entry new to the set, never re-reads an
existing entry's. Write the new default into the style file *before* `style keep`, so new
entries' values are read against it; a new default map is the stack taking that entry's
values, the entry moved first with none, the old map an entry with the old values, and
`suggested_colormap` and the row's `public.palette` renamed (`style_catalog.check` holds
`public.palette` to the set's first entry; only `tests/test_style_catalog.py` holds
`suggested_colormap`, for a published row). An existing entry taking a lever's values is
written by hand. **Moving the stack's own constants** moves every entry that leaves those
members to the stack: write each other entry the old value of every member moved, so it
draws what it drew (`style_palettes.apply` before and after proves it). **A round-one
re-tune of the default is an entry, not a moved default**: draw it as a copy of the map
carrying the re-tune as values, and move the default only once Matt keeps it over the old
reading (106 moved teal's early and pinned eleven entries; 108 kept both and moved it back
as `soft_veils_teal_echoes`).

**The lever rule: a shown keep is one the published stack draws.** The site opens an
Example as the keep's entry plus the knob settings read off it; a keep showing a member
no entry or knob reaches opens at the defaults instead (089's marbled_pour, 090's
veil_shards). The fast lane's `style_catalog.check_reached` refuses one the moment `show`
names it: move the stack to the kept reading (as above) or show another keep;
`style_catalog.UNREACHED_SHOWN` (the website's `UNREACHED`) lists the accepted ones.

**Merging a style into a mode** (its kept stack is the mode's up to values): rename its
map to the entry's name, write the entry with `was` the old style name and `values` from
`style_palettes.values_between(mode stack, kept stack)`, add the old name to the row's
`aliases` and its references to the row's; move its keeps (records, stacks and pictures)
into the mode's, then delete its style file, keeps file and catalog row.

**Deleting a mode** (092, 107): its style file, keeps file and catalog row; each map in its
set that nothing else uses (another row's entry or `public.palette`, a style file's
`suggested_colormap`, a remaining keep's render) goes with its `data/palettes/<map>.json`
and its rows in `carriers.jsonl` (the method header's `maps`, `carriers` and `uncarried`
recounted), `groups.jsonl` (its `admitted` row; no group id moves) and
`palette_family_shares.csv`: `palettes remove <map>` does this map half once the mode's
files are gone, refusing a map the grouping's cut placed or another map joined.
Its kept pictures stay in `fractal-drive-sync/style-keeps/<mode>/`; a test or doc naming
the mode is repointed. The deleted mode's shown keeps leave the parity run with it.

`style gallery` rebuilds `fractal-drive-sync/custom-modes/`, one card per mode; `style
bundle` (the website's `custom-modes.json`) carries each published mode's kept entries.
**Re-drawing a shown keep** under a changed default is a one-row picker
(`style_keeps.py`'s docstring has the steps).
