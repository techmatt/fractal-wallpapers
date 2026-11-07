# QA findings

What bug hunts found, one line each: **fixed**, **deferred** (to Matt, with a
recommendation) or **won't fix** (with the reason). A hunt reads this first and never
re-reports a line on it. The checker that found most of the style ones is
`fractal-wallpapers style sweep` (`data/styles/README.md`'s *Checking the library*).

## The style system (item 039)

### Fixed

- `style show`, `style render`, `style knobs` and `style tones` on a draft `.json` that
  does not parse, or is not an object, raised a JSON traceback; a missing draft was
  reported as "no style … under data/styles". Now one refusal line each.
- `style render --location` (and plain `render --location`) on a missing or garbled
  file raised a traceback, and **refused an indented record** (one object over many
  lines, as a keeps file prints it) as "holds N rows". `locations.read_one` reads the
  whole file first.
- `style render <mode> --knob NAME=VALUE` was silently overridden by a location record
  carrying the same member: `teal_tunnel`'s keeps carry `projection.log_polar.turns`
  (8, outside the knob's 3..6), so `--knob turns=…` drew turns 8 whatever was asked.
  Knobs are now turned after the record's projection is laid on (`styles.spec_of`).
- `style tones <merged name>` (`crisis_smooth`, `golden_petals`, `copper_arms`, …) held
  renders to the mode's reference picture, not the entry's own, so a render tuned to
  `crisis-25.jpg` read as missing `council.jpg` by 0.21 of median. `styles.at_palette`
  now carries the entry's `reference`.
- `style scout --n -3` drew 887 seats (a negative slice); `--n 0` and
  `--probe-limit 0` drew nothing. Each is refused.
- `style keep` on a garbled choices file raised a traceback; a choices file with no
  `name` was reported as "choices 'None'".
- `style sheet <missing>.txt` raised a traceback.
- `style render --manifest` with a record named `a/b` wrote into a subfolder; a name with
  `:` would fail on Windows. Separators and Windows-reserved characters become `_`.
- `style palettes <discarded mode>` printed "score None"; it prints "no score
  (discarded)".
- `style palettes <mode> --sync` on a new catalog row (README step 10) read the
  default entry's values off its first keep, often a round-one formulation, and wrote a
  catalog that `style gallery`, `bundle` and `wasm-parity` then refused. The default
  (the suggested map) is now written with no values.
- A catalog row showing a named-mode baseline keep passed `style_catalog.check` and then
  raised `KeyError` in `style bundle` and `wasm-parity`; the check now refuses it.
- The engine accepted a layer palette's `lambda`, `scale: absolute`, `knee` and `period`
  and then misread them (a lambda measured the compressed field and placed the raw one;
  absolute clamped every smooth count to the map's end). `Style::validate` refuses them;
  `STACK.md` says so. No shipped style used one.
- **The WebAssembly module turned knobs before laying the record's projection**, so on
  the page `arch-tunnel`'s `turns` knob did nothing at a keep whose record carries
  `turns`, and once the CLI was fixed the page and native drew different pictures.
  `style-wasm`'s `Session::open` now lays the record first, as `styles.spec_of`; the fold
  is decided on the stack as turned on both sides. `wasm-parity` built its native knob
  reference in the old order (so it could not see this) and ran knobs only at each
  mode's first keep; it now turns them as `style render --knob` does, also at every
  shown keep whose record carries a projection. `engine/README.md` gives the new order
  and the bundle's `palettes`.
- `wasm-parity` printed "None pixels differ, by at most None" on a size mismatch; it
  names the sizes.
- `style tones` raised a traceback on an unreadable reference, and read a 16-bit grey
  PNG as white.
- `style picker` gave a picture offered under two keys two JPEGs, so `style keep`
  recorded and copied it twice; it is now one image, one keep picked twice. A key with
  `/` (two keys then saved to one file) and a baseline `render` lacking a member (a
  traceback at keep time, after the picking) are refused when the picker is built.
- `style scout --points`: a line that is not an object raised `TypeError`; a hand
  point's name was used as the probe's file path (`a/b` left folders, `../x` wrote
  beside `--out`); an empty draw truncated an earlier manifest at `--out`.
- `style render --manifest` silently replaced a picture drawn by another stack at the
  same seat and map (README step 6's formulations row, drawn into one folder); it now
  prints `REPLACED`, and the README says one folder per stack.
- `style sweep --gallery` (added for the hunt's long runs) draws every style at seeded
  gallery seats instead of its keeps.
- `STACK.md` now says that every `inside` channel in a stack shares one loop at the
  largest `iterations`, and that a `light` at `rings` 0 ignores `bands` and `period`.

- **`lit_petals`' public knob `petal_depth` was dead** (published `soft-petals`): it
  wrote `/layers/1/light/period`, but that light has `rings` 0, where the normal is the
  slope alone, so both ends drew byte-identical pictures (the sweep's `dead_knob`).
  Dropped from the style file's `public` and the catalog row (Matt's ruling, option a);
  the README lesson on a light's period no longer cites `lit_petals`, and
  `tests/test_styles.py` holds every knob to moving something. The website's
  custom-modes bundle needs a rebake to lose the slider.
- `renders.jsonl` was rewritten in place after every picture, so a run killed mid-write
  left every picture in the folder unrecorded; it is now written beside and swapped in.
- `style sweep --tones` holds each seat and palette entry to its reference's band at a
  checked width; a backgrounded sweep's progress lines now flush.
- Docs against the code: `STACK.md` claimed `glow_filaments` offers `log_density` 30 as a
  variant (never kept), that `center [0.5, 0.5]` at spacing 1 keeps `0` off the discs
  (only under radius 0.7; the default is 1), and listed six blends for every layer (a
  `light` takes `normal` only). The README's relief lesson cited `cauliflower_scales` for
  rings 0 (its scales need rings 0.8), called the lace-and-holes styles one stack in five
  maps (`bead_strands` has two layers more), and said a map joins a set only through a
  kept tile (`palettes add --mode` puts one in for a round). All corrected.
- Style notes against their own stacks, corrected in prose only (no stack, knob or name
  touched): `leaf_veins` (de palette not inverted; a rings-0 light domes nothing),
  `flame_veil_blue` (sheet fill 0.22), `flame_wisp_spark` (one view, not three), four
  lace styles' `inside` reuse and shared notes, `bead_strands` (periwinkle highlight),
  `flame_wisp_waves` (one literal rose, no orange), `bronze_packing` (five height glows),
  `seahorse_halo` (the fringe lands on blue at 1.5 cycles), `shaded_blades` (crescent
  reads; one darkened edge), `glow_filaments` (`log_density` tried, not kept).

- `palettes add --mode <merged name>` refused with "no mode"; it now names the mode to
  pass. A discarded mode is refused a palette round.
- `style sheet` cut a long `<folder>/<name>` label at a narrow tile's edge, losing the
  name's end; it elides the middle.
- A typo in `catalog.json`, which the README sends a person into by hand, raised a JSON
  traceback from `style gallery`, `bundle`, `wasm-parity`, `style palettes`,
  `palettes add --mode`, `style keep` and every lookup of an old merged name. Each now
  refuses with the parse error. `palettes remove` read it only after deleting the map's
  file and rows, breaking its own "every refusal before the first write"; it reads first.
- The catalog check passed a score of `4.0`, which then crashed `style gallery`'s stars,
  and a wrong-case colormap (a Windows path test), which `entry_for` then never matched.
  Scores are whole numbers 1 to 5 and maps are matched by exact name.
- `--sync` on a new row with no tile kept in the suggested map left a tuned map heading
  the set; the suggested map is put first, unkept, the stack's own.
- The gallery page's Copy choices exported marks for modes no longer on the page (the
  saved-state key hashes only statuses); it drops them. `style gallery --out` on another
  drive raised on a relative link; such links are `file://` URLs.

- A knob's write was rounded wherever the file spelled the member as an integer (`1`),
  natively but not in the module, so a draft's opacity knob was an on/off switch on the
  CLI and a slider on the page; both now round by the same named members.
- `style render` read `--location`/`--manifest` through the output resolver (an
  archived input was refused as if being written) and a missing manifest raised; a
  draft's malformed knob, a truncated renders sidecar line, a choices file without rows
  and a picker plan that is not an object each raised. All refuse in one line.

### Deferred to Matt

- **Two `stripe` densities on one escape loop collapse to the first** (the loop's
  `Wants` keeps one density; validation never asks). Measured: in `cream_lace` moving
  the second strand layer's density from 4 to 9 changes no pixel, moving the first
  changes 7.6%. So the "density 4" strands of `bead_strands`, `copper_mail`,
  `cream_lace`, `ember_plume` and `gold_arcs` draw at 2, and `flame_wisp_amber`'s 10 at
  3; the README's "crests at density 2 to 4" lesson was read off pictures drawn this way.
  Options: one running sum per density in a loop (the right fix: every shipped stack
  then draws what it says, and those six change), or refuse a second density per loop
  (refuses the six). Recommend the first, with an identity run and a re-look of the
  six, none of them published. *(Matt's call: their kept look moves)*

- **The tone sweep reads 28 of 129 kept seats and palette entries outside their
  reference's band at draft size** under today's engine, every one on p90 (the number
  the tone pass does not pin): `yas` (published) +0.10 to +0.25 at both seats and five of
  its seven maps, `glow_filaments` +0.30 (README's known heat), `flame_wisp_frost`, the
  four lace-and-holes styles +0.14 to +0.22, `molten_flow` p10 +0.11 with p90 −0.15,
  `chrome_blades` and `leaf_veins` low. They are kept pictures, so nothing is broken;
  recommend no re-tune unless a published mode's card reads hot to you (`yas` is the
  one), and re-reading this with `style sweep --tones` after any tone-pass change.
  Rows: item 039's working papers, `tone_sweep.md` (untracked). *(Matt's call)*
- **A published mode's full frame is slow on the page**: `style wasm-speed` reads 15 to
  91 s per 1280x800 ss2 frame on one thread (`gilded_orbs` 91, `glossy_lobes` 74, the
  bubble traps 54 to 55, `yas` 47). The module already has the progressive route
  (`measure` on a preview, tiles after). Options: tiles on several workers (the tile API
  allows it), a lower page `maxiter` for the deep seats (18,000 to 32,000 here), or
  shown keeps at shallower seats. Recommend workers first: no picture changes.
  *(the website's item; Matt's call on maxiter)*
- **Multi-view flame stacks commit 2 to 3 GiB per full-size frame** (`flame_veil_violet`
  3.0, `flame_wisp_spark` 2.0, at 22 to 61 s on six threads, inside the README's times).
  Noted in `data/styles/README.md`; no change recommended.
- **`arch-tunnel` (`teal_tunnel`) shows a keep its own `turns` knob cannot reach**: the
  shown keep `shortlist/01_j_dendrite_beta` (and the `palettes/yas` keep) carry
  `projection.log_polar.turns` 8 in their location, the knob's range is 3..6, and the
  bundle hands the page that location. A knob now wins over the record on both sides,
  so a page that sends the knob's setting draws that keep at 5 turns, not the 8 it was
  kept at, and no setting returns it to 8. Options: widen the range to 8 (if eight turns still holds the look), drop `turns` from
  those records (the picture was drawn at 8, so its caption would lie), or show another
  keep. Recommend widening the range to 3..8, read off a sweep at 8. *(Matt's call)*
- **Field-lines interior needs the orbit within 1e-9 of its cycle after `settle`
  steps**, so the outer part of a bulb whose multiplier is near 1 (|λ| over about 0.98 at
  period 1, 0.85 at period 8) gets no lines, where `STACK.md` says only a parabolic or
  Siegel interior lacks them. A looser cycle test (the arrival read only needs a cycle
  point to within `arrive`) changes `field_lines`, `star_eye` and `clockwork_rings`
  pixels, so it wants an identity run and a look. Recommend the fix with a re-look.
- **A bubble lattice's `hit` ≥ 2 misses a hop from one disc straight into another**
  (one `was_inside` for every lattice cell), so `bronze_packing`'s hit-2 discs are cut
  where an orbit hops. Tracking the cell index fixes it and changes `bronze_packing`'s
  pixels (published). Recommend the fix with a parity rebake and a look.
- **A light on an inverted channel lights tubes as grooves from the far side**: the
  height is inverted but the gradient is not. No shipped style does it. Recommend
  negating the gradient (pixels move only for a stack that inverts a light's channel).
- **Under `log_polar`, a bubble's `largest`/`smallest` use the plane width**, not the
  projection's local scale, and the f64 resolution refusal reads only the straight grid,
  so a deep log-polar view rounds round its vanishing point. No shipped style combines a
  bubble with a projection, and the only projected style is shallow. Recommend leaving
  both until a style needs them.
- **A strip lattice with `radius` ≥ `spacing`/2** (or a disc lattice that covers the
  plane) is accepted and draws hit 1 at step 1 everywhere. Recommend a refusal in
  `Style::validate` when a knob range can reach it.
- **The render log records the projected stack**, so a keep from a projection style
  carries a seat's `turns`/`twist` in its stack and a new palette entry read off it gets
  `{}`. Recommend logging the pre-projection stack, with the bundle and parity paths
  projecting a keep's stack over its location.

- **`style tones` drops an RGBA picture's alpha**, measuring transparent areas as their
  hidden colour. Style references are finished pictures; recommend leaving it.
- **The website must rebake its module** for the knob-order fix to reach the page
  (`style-wasm` is built here, served there): the website's item.

- **The tone pass does not re-aim at supersample 1**: a lift that pushes a saturated
  channel past 1 clips, so the picture lands short of its median target, and the
  measure-and-re-aim loop runs only above ss1. Drafts and full renders are ss2, so it
  touches the scout's probes and ss1 previews. Recommend carrying a lift with `lifted`
  (no channel past 1) and running the loop at ss1 too; moves ss1 pixels, wants an
  identity run.
- **A stretched `light` draws its top-clipped 0.5% as the start of a new tube**: at
  height exactly 1 the band phase wraps to 0, flipping the shading along the plateau;
  `Sheet::alpha` already guards the same wrap. Moves pixels of published stacks with a
  banded light (`floating_on_dreams`); recommend the guard with an identity run and a
  parity rebake.
- **Validation refuses a `threads` field on the frame beside one through a view at
  another `sigma`**, though each is its own loop. Refusal only; recommend checking per
  loop when a style wants it.
- **A palette entry's value is checked only for its pointer**, not for writing the same
  kind of node (a number over a colour passes, then fails at the engine or on the page).
  Recommend comparing kinds in `check_row`.

### Won't fix

- `style sweep` raises `slow` on `bronze_packing`, and on a phoenix seat of
  `flame_wisp_frost`, which read 10–50x the library's median time per sample: those are
  the stacks' and seats' own cost (README's render times), so the flag compares each
  picture with its own style's median instead.
