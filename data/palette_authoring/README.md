How a palette gets authored: the brief a generator run is given, and the checker
its output is held to. Nothing here is a colormap and nothing here is read at
render time.

```
generator_prompt.md               the brief
generator_prompt_focus_color.md   the same brief, aimed at one colour region
validate_palettes.py              the mechanical checker both briefs name
```

```
python data/palette_authoring/validate_palettes.py batch.json
python data/palette_authoring/validate_palettes.py --dir data/palettes/batches/<drop>
```

This is a **kit, not a stage**. It is deliberately not a subcommand and not a
module of the package: the brief is text handed to a model, and the checker is one
standalone file that imports nothing from this repository so a reader can copy it
next to a batch of their own and run it. `--dir` takes a whole directory of
batches, which is the shape a drop arrives in.

A drop that has already shipped can still fail the checker, and that is not a
regression. Batch files are committed exactly as the generator emitted them, so a
run that emitted a name another run in the same drop also emitted still reports it
as a duplicate here; `../palettes/batches/<drop>/renames.json` is where that was
settled, and it is the file `--dir` names as skipped.

`validate_palettes.py` is **authoritative for the mechanical rules**. Both briefs
restate its numbers in prose for the model's benefit; if a threshold moves it moves
in that file's CONFIG block and the briefs are edited to match. Its exit code is 0
exactly when there are no ERRORs — warnings never change it, because the failure
mode of this generator has always been *samey* palettes rather than malformed ones,
and a checker that talks somebody out of a good weird palette is worse than one
that lets a dull one through.

## Why the focus-colour brief exists

`generator_prompt.md` conditions a run on a **mood family** — "autumn-ember",
"fire-ice", "oceanic". That is the right handle for filling out a library and the
wrong one for filling a *hole* in it: the colour census counts in swatches, and no
mood family maps onto a swatch. `generator_prompt_focus_color.md` conditions on the
colour region instead, which is what the `rare-colors-2026-08` drop was written
against after the census named the green→cyan band and the dark tail as thin.

Its results are worth knowing before reusing it. Aimed at a region the sRGB gamut
holds, it lands: the runs conditioned on green, sage and dark yellow roughly doubled
the maps carrying those swatches. Aimed at a region the gamut does not hold, it
lands somewhere else without saying so — the run conditioned on dark teal, lime and
green put all twenty of its palettes on the **light** tier instead, and reached 10%
on none of its dark targets. A focus colour is a request, not a guarantee, and the
library-footprint census is the only thing that says which one you got.

## Where the output goes

A generator run's own file is not kept here. It is committed under
`../palettes/batches/<drop>/` beside the library it densifies into, because a batch
file and `../palettes/provenance.jsonl` are one record split in two — the row a
shipped map carries and the run that emitted it — and they are read together.
`fractal-wallpapers palettes ingest --drop <drop>` is what turns one into the other.
