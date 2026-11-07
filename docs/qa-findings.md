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
- `STACK.md` now says that every `inside` channel in a stack shares one loop at the
  largest `iterations`, and that a `light` at `rings` 0 ignores `bands` and `period`.

### Deferred to Matt

- **`lit_petals`' public knob `petal_depth` is dead** (published mode): it writes
  `/layers/1/light/period`, but that light has `rings` 0, where the normal is the slope
  alone and the same in every ring, so both ends draw byte-identical pictures (the sweep's
  `dead_knob`). The style's notes ("every three escape steps one smooth rise, the
  petal") describe a ramp the engine does not draw. Options: drop the knob (style file,
  catalog `public`, bundle); re-point it at something live; or give the light a small
  `rings` so period draws (changes the kept look). Recommend dropping it: the kept look
  stays and the page stops offering a slider that does nothing. *(Matt's call)*
  `tests/test_styles.py`'s `DEAD_KNOBS` names it until ruled.
- **`arch-tunnel` (`teal_tunnel`) shows a keep its own `turns` knob cannot reach**: the
  shown keep `shortlist/01_j_dendrite_beta` (and the `palettes/yas` keep) carry
  `projection.log_polar.turns` 8 in their location, the knob's range is 3..6, and the
  bundle hands the page that location. Here `style render --knob turns=…` now wins over
  the record; whether the page lays the record over the knob is the website's code.
  Options: widen the range to 8 (if eight turns still holds the look), drop `turns` from
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

### Won't fix

- `style sweep` raises `slow` on `bronze_packing`, and on a phoenix seat of
  `flame_wisp_frost`, which read 10–50x the library's median time per sample: those are
  the stacks' and seats' own cost (README's render times), so the flag compares each
  picture with its own style's median instead.
