# QA findings

What bug hunts found and left open, one line each: **deferred** (to Matt, with a
recommendation) or **won't fix** (with the reason); a fix lives in its commit, not here.
A hunt reads this first and never re-reports a line on it. The checker that found most
of the style ones is `fractal-wallpapers style sweep` (`data/styles/CHECKS.md`'s
*Checking the library*).

## The style system

### Deferred to Matt

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
  **Moot since 107**: `teal_tunnel` had no showcase pick and was deleted.
- **Field-lines interior needs the orbit within 1e-9 of its cycle after `settle`
  steps**, so the outer part of a bulb whose multiplier is near 1 (|λ| over about 0.98 at
  period 1, 0.85 at period 8) gets no lines, where `TRAPS.md` says only a parabolic or
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
- **The website must rebake its module** for the knob-order fix (`style-wasm` lays the
  record's projection before turning knobs, as `styles.spec_of`) to reach the page
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

- **Ten entries tune a knob's members apart** (087): a knob writing several members
  reads back to more than one setting on the entry (veil-drift's Brightness on nine
  soft_veils entries, glass-beads' bead_strands Strand fade 1.33 and 1.5). The page holds
  the entry's picture at rest (a setting at the entry's `rests` is no setting), but any
  slider setting, and native `--knob` at the rest value, writes every member alike, so
  no setting *off* rest draws the entry's spread. Every reading lies in range
  (`check_row`). Options: leave it (the page's rest covers the return); or split such a
  knob per member. Recommend leaving it. *(Matt's call)*
- **A recolour to an entry that switches a layer off is refused** though the kept frame
  holds every lane it needs (`drawn` drops a layer at opacity 0, so its reads shrink).
  No shipped entry does it; recommend accepting a subset of the gathered reads when one
  does.
- **An entry draws a reading no kept tile shows**: feather_plumes' starlight_plumes took
  its dim-barbs lever's barbs but not the long masks that lever was drawn on (the row
  records the choice). Recommend leaving it as recorded. *(Matt's call;* chrome_whorl's
  twin of this took its kept soft reading as its default, 087.)

### Won't fix

- `style sweep` raises `slow` on `bronze_packing`, and on a phoenix seat of
  `flame_wisp_frost`, which read 10–50x the library's median time per sample: those are
  the stacks' and seats' own cost (README's render times), so the flag compares each
  picture with its own style's median instead.
- The module's `measure` accepts a preview of another aspect, and `tile` a size past
  2^32 (wrapped by the u32 call): each needs a page breaking the documented contract
  (`style-wasm/README.md`'s *The style module: a custom mode in a page*: a preview of the
  same aspect), and the answer names the size measured.
- `style cost` leaves a lab mode's shown example out of its seats once the mode has a keep
  record (chrome_orbs since 082): the bar is the deepest *kept* seat by definition
  (`data/styles/CHECKS.md`).
