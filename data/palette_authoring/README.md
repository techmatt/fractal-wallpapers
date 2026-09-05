How a palette gets authored: the brief a generator run is given, and the checker
its output is held to. Nothing here is a colormap and nothing here is read at
render time.

```
generator_prompt.md                     the brief
generator_prompt_focus_color.md         the same brief, aimed at one colour region
generator_prompt_specific_palettes.md   the same brief, aimed at one named colour pairing
classic_palettes.json                   the pairings that third brief is conditioned on
generator_prompt_opener.txt             what to hand a run BEFORE either brief
validate_palettes.py                    the mechanical checker every brief names
```

`generator_prompt_opener.txt` is the order of work rather than a second brief, and
it is what a run is given first: convert the focal hexes to OKLCH and write a small
colour module before authoring anything, because a large share of plausible chroma
values are outside sRGB and teals and greens at mid lightness top out near
`C = 0.075`; lay the whole batch out as a table and confirm the spread before the
first stop, since retrofitting spread is what costs the most time; author inside a
build script that clamps to the gamut edge and reports what it clamped; and check
the aesthetics numerically — ramp coverage densified per focal band, mud detected as
`C / max_chroma(L, H)` rather than as an absolute chroma. It is `.txt` and not `.md`
because it is one paragraph pasted ahead of a brief, with no structure to read.

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

## Why the specific-palettes brief exists

The third brief conditions on neither a mood nor a colour region but on a **named
pairing** — `classic_palettes.json`'s sixty entries, each two or three hexes with a
name people already use for the combination: Teal Orange, Navy Gold, Magenta Cyan.
Two palettes per entry, and its one hard rule is that the **hue inventory is
closed**: the entry's own hues within ±15° in OKLCH and nothing else chromatic, so
the stop budget is spent on lightness and chroma inside those hues rather than on a
third hue as a bridge. It is the handle for filling out a library along axes a
person can name, where the focus-colour brief is the handle for filling a hole a
census found.

Its first drop is `classic-pairs-2026-09`, six runs of twenty. What it produced,
worth knowing before reusing it:

* **It is clean by construction.** 120 palettes, zero validator errors and zero
  warnings, zero name collisions against a 901-map library, and all 120 measured
  cyclic — no `renames.json` was needed at all, which no drop before it managed.
* **It is not a hole-filler and the census says so.** 445 carrier rows over the 120
  maps, 3.71 cells a map against the library's 3.57, but the thin cells gained
  least in relative terms: `light_vivid_teal` +1 on 39, `light_vivid_azure` +2 on
  52, `light_vivid_cyan` +2 on 47. What it did move is `dark_vivid_yellow` (+11 on
  26) and `dark_muted_green` (+14 on 44). A named pairing is a request for a
  *look*, and where that look lands in the codebook is not something the brief
  controls.
* **A closed hue inventory does not crowd the library.** Each new map's nearest
  shipped neighbour runs a median M1 of 0.0575 against the library's own
  nearest-neighbour median of 0.0554 — the drop sits marginally *further* apart
  than the library does from itself, and only ten of its 120 have a shipped
  neighbour at or under `groups.CUT`.

## Where the output goes

A generator run's own file is not kept here. It is committed under
`../palettes/batches/<drop>/` beside the library it densifies into, because a batch
file and `../palettes/provenance.jsonl` are one record split in two — the row a
shipped map carries and the run that emitted it — and they are read together.
`fractal-wallpapers palettes ingest --drop <drop>` is what turns one into the other.
