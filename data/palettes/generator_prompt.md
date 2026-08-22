# Dramatic Fractal Palette Generator — v3.1

## Run conditioning (edit these four lines each run)

```
BATCH SIZE:      20              # ignored for 6-ultra — that band emits ~6 by design
MOOD FAMILY:     span        # one name from the roster below, or "span" to vary across the batch
COMPLEXITY BAND: 6-ultra             # one of: 1-2 / 3-4 / 5 / 6-ultra
VALUE KEY:       span            # one of: low / mid / high / span
```

The output json you emit should follow the following naming convention:
fire-ice_c3-4_v3_1.json
atmospheric-deep_c5_v3_1.json
etc.

Run across a grid of (mood × complexity × value) to accumulate a large set. **Skeletons and architectures
are distributed automatically within each batch — they are not run knobs.**

---

## Your task

You are a color designer generating **dramatic palettes** for a fractal wallpaper renderer. Output the
requested number as a single JSON array following the schema at the end.

A palette is a short, ordered list of **color stops** (sparse — you mark structural events, not a dense
gradient). Downstream code densifies your stops into a smooth lookup table and applies it to fractal
renders. Palettes must be **standalone and image-independent**: concrete colors at concrete positions.

## The three attached images are calibration only

They exist **solely to calibrate your sense of target quality** — the color drama that reads on fractal
geometry. **Do not extract, reproduce, or describe their specific palettes.** Generate new palettes from
the principles below.

## What the renderer does with your palette (why the rules exist)

The renderer treats the palette as a **1-D color ramp indexed by a smooth per-pixel "escape" value.**
Densification makes a fine gradient; the fractal reads into it.

1. **Texture is the fractal's job, not yours.** Fine filigree comes from many pixels reading nearby
   positions of a *smooth* palette at high spatial frequency. Never bake noise/texture into a palette —
   palette-noise × field-noise = mud. Provide clean gradient; the geometry supplies frequency.
2. **A cliff is crisp on busy detail, soft on smooth field.** A `cliff` is a narrow soft ramp: spatially
   thin (crisp) where the field is busy, feathered where it's smooth. It's a *small detail accent*, not a
   drama driver — see the cliff rules below.
3. **Big hue jumps route through black or white, never across a cliff.** A saturated jump between distant
   hues (especially complementary — teal↔red) renders as a dirty grey/brown seam wherever it lands. The
   references avoid this by jumping *through black or white* (orange→black→gold). Do the same.

## How to read the rules — mechanical vs aesthetic

- **Mechanical** (firm): cyclic endpoints match; glow feathers (no cliff at the peak); cliffs stay within
  the value cap **and carry only small hue/value steps**; big hue jumps go through black/white (never a
  cliff); no baked texture; each distinct hue on its own stop. These come from how the renderer consumes
  the palette — keep them.
- **Aesthetic** (spread for variety): the color architecture, the skeleton, the chroma level, the mood
  register. Spread these across the batch; variety matters more than any single default.

## What "dramatic" means

Drama has **several independent sources, and different palettes use different ones** — that's the whole
point of the architecture axis. Universal: a **wide value range**. Beyond that, every palette must draw
drama from **at least one** of:

- **hue purity / high contrast** — pure saturated hues with true black and/or true white at the extremes;
- **temperature tension** — a *big, saturated* warm↔cool swing (not a limp drift through grey);
- **a rich multi-hue path** — three or more hues held in balance.

The flat failure is a palette with **none** of these: one desaturated hue drifting across a narrow value
range (the scientific-colormap ramp). If a palette could be described as "a smooth gradient from X to Y,"
redo it.

**Value structure**
- **Wide value range, always.** How far it goes to the extremes depends on register: **vivid /
  high-contrast palettes should hit true black AND true white at full strength** (this is where the
  references get their punch — don't soften it to navy-grey and cream). Muted palettes may bottom out in a
  hued dark and top out in cream.
- **Non-monotone lightness.** Don't march monotone dark→light. For complexity ≥3, ≥2 interior lightness
  extrema (the skeleton sets where). *Exception:* a `mono-temperature ramp` architecture is allowed to run
  a single sweep black→hue→white — its drama is the pure ramp, not an arc.

**Chroma & register**
- **Pure hues for the vivid register — not their mineral cousins.** Vivid fire wants pure orange and pure
  cobalt, **not** petrol/ochre/olive. The jewel-earth / mineral tones are the *muted* end of the range,
  not the vivid end.
- **Vary saturation across the batch, and lean into it.** Don't let a batch trend uniformly muted (the old
  failure) *or* uniformly vivid. A good share should be genuinely **vivid/pure**; a few genuinely
  **muted** (muted is not the problem — muted-*and-samey* is). Push the vivid ones to the gamut edge.
- **Avoid** muddy grey-brown midpoints — the one genuine failure to design out.

**Temperature** — no longer a universal rule. Some architectures use tension, some deliberately don't
(see below). **When you do use it, make it big:** deep saturated warm against deep saturated cool, chroma
held across the swing — never a desaturated teal drifting to brownish rust through grey (that limp
reversal is what made every prior batch feel the same).

**Roles**
- Assign each stop a role: `ground/field` (recessive mass), `anchor` (a defining hue), `accent` (a narrow
  pop), `glow` (a light band reading as illumination). Not every architecture needs all roles.

**Glow / light band** *(mechanical: feathering)*
- Most palettes have a glow; **it feathers — `smooth` on both sides, never a cliff at the glow.** In
  vivid/duotone palettes the "glow" is often **true white**, and it doubles as the safe waypoint for a big
  hue jump. Vary glow temperature across the batch (warm cream/gold vs cool bone/ice/white).

**Cliffs** *(mechanical: small-step only)*
- A `cliff` carries **only a small hue step or a value step** — never a big or complementary hue jump
  (those route through black/white). Keep the value gap **|ΔL| ≤ ~⅓ of the palette's L range**, and never
  between the palette's brightest and darkest stops. Cliffs are a minor filigree accent, not a drama
  source. Many palettes have none.

**Cycling** *(mechanical)*
- **Cyclic:** first and last stop share the **same `oklch`**.

## Color architectures — distribute the batch across all six

An architecture is the palette's **color idea** — distinct from the skeleton (which is only the lightness
arc). This axis is the fix for flavor-sameness: without it the rules collapse onto one attractor
(architecture 3 below — good, but not the only good palette). Tag each palette's `architecture` and spread
the batch across all six (~3 each), paired freely with skeletons and with the mood's hue vocabulary.

1. **duotone-plus** — exactly **2 saturated hues + true black and/or true white**, minimal mid-tones. The
   two hues may be complementary (cobalt+orange) or not (magenta+gold). Drama = purity + high contrast +
   the black/white extremes. The big jump between the two hues **routes through black or white**, never a
   blend. *(The most vivid, poster-like register.)*
2. **mono-temperature ramp** — a **single temperature, no reversal**: a heat ramp (black→red→orange→
   gold→white) or an ice ramp (black→navy→cobalt→ice→white). Drama = a pure value+chroma sweep. May run a
   single monotone lightness sweep.
3. **complementary-tension** — a warm mass against a cool mass, **bridged by a glow or a muted intermediate
   (never a cliff)**. Drama = temperature tension, done for real: deep cobalt vs deep rust, *or* a
   deliberately muted copper vs steel-blue. This is the prior attractor — kept, as **one of six**.
4. **analogous-drift** — **3–4 neighboring hues**, no complement (red→orange→gold→cream; navy→teal→
   green→foam). Drama = value + the hue walk. No temperature reversal.
5. **triad** — **3 well-separated hues** in balance (red/gold/blue; teal/magenta/gold). Drama =
   polychromatic breadth a single pair can't give.
6. **near-monochrome + spark** — **one hue family** across the full value range plus **one small
   contrasting accent** (the spark). Drama = tonal depth + the single spark.

**Pair freely with skeletons.** Not every combination is natural (a mono-temperature ramp suits
peak-early/late; a duotone suits inverted-arc or cliff-in-mids), but across the batch cover both
dimensions roughly evenly. Architectures use the mood's hue vocabulary — a fire-ice duotone is
orange+cobalt; a fire-ice mono-ramp is a pure fire (or pure ice) sweep; a fire-ice near-monochrome is one
temperature with a single opposite spark.

## Structural templates (skeletons) — distribute across all six

The **lightness-arc** axis (orthogonal to architecture). Spread ~3–4 each; tag `skeleton`.

1. **peak-early** — lightness peak in the first third (~0.20–0.40), long descent after.
2. **peak-late** — peak in the last third (~0.70–0.88), long rise before.
3. **double-peak** — two lightness maxima with a darker trough between.
4. **cliff-in-mids** — a single crisp **small-step** cliff at a mid-tone boundary (~0.25–0.55); glow
   elsewhere, feathered.
5. **no-cliff** — no sharp edge; all `smooth`. Drama from value + the architecture.
6. **inverted-arc** — a pale/bright field with the **dark as the event**: a hued-dark trough is the focal
   moment. Pairs with high value_key. **The focal dark must be genuinely deep** (deep navy, oxblood, deep
   teal — not a mid-value petrol/teal that washes out).

## Axes

- **complexity** (`1`–`6`): structural-event count → fractal busyness suited.

  | complexity | stations | structure |
  |---|---|---|
  | 1 | 4–5 | 1 anchor, 1 glow, hued dark, smooth washes |
  | 2 | 5–6 | + 1 accent or 1 cliff |
  | 3 | 6–7 | anchor + support + glow, ≥2 lightness extrema |
  | 4 | 7–9 | fuller hue path, ≥2 extrema |
  | 5 | 8–10 | full hue path, ≥2 extrema |
  | 6 (**ultra, probe**) | 11–15 | push past the useful ceiling; every stop a real event. **Emit ~6 palettes regardless of BATCH SIZE.** |

- **value_key** (`low` / `mid` / `high`):
  - `low` — deep dark (true black at the set body for vivid palettes); full sweep to bright.
  - `mid` — mid-toned field, darks and lights both present.
  - `high` — **no blacks.** A pale field carries the image; a **single genuinely-deep jewel tone** anchors
    in place of black. (Natural home for `inverted-arc`.)

- **mood family** — the **hue vocabulary** (orthogonal to architecture/skeleton). Pick per the run knob.

## Mood roster

- **fire-ice** — pure orange/amber/rust against cobalt/ice-blue/white; the vivid heat-vs-cold register.
- **jewel-earth** — oxblood, petrol, ochre, olive, deep teal; mineral tones, the muted end.
- **atmospheric-deep** — deep navy/teal, vast dark field, a small luminous warm core.
- **antique-faded** — wine, slate-blue, bone, dusty rose; candlelit, muted.
- **high-key-luminous** — pale field, no blacks; one saturated jewel tone anchors.
- **pastel-iridescent** — opalescent lilac, sky, peach, mint, silver filigree.
- **autumn-ember** — rust, burnt gold, umber, smoke, cream glow.
- **oceanic** — petrol, teal, foam, deep indigo, a warm coral/amber accent.
- **orchid-twilight** — magenta, violet, plum, indigo, a gold/chartreuse glint.
- **verdigris-copper** — oxide teal-green vs warm copper and cream.
- **ember-in-ash** — smoke and charcoal with one fierce warm event.
- **tonal-restrained** — one hue family, wide value, one temperature-shifted accent.
- **sapphire-rose** — inky navy, sapphire, indigo against dusky rose, magenta, deep fuchsia; a few blush or periwinkle glints allowed, but weighted dark — jewel blues and pinks with the lights turned low.


## How to reason before you emit

Reason **and emit in OKLCH** — the densifier converts. Per palette:

1. **Pick architecture + skeleton** (spread both across the batch) — architecture sets the color idea and
   the hue count; skeleton sets the lightness arc.
2. **Lightness (L):** darks, peak(s) per the skeleton, extrema. For vivid palettes take L to true black/
   white.
3. **Chroma (C):** vivid → push toward gamut edge (pure hues); muted → pull back. Hold chroma across any
   temperature swing.
4. **Hue (H):** the hue stations for this architecture. Big jumps go through black/white, never a cliff.
5. **Roles / glow / cliff:** glow feathers; any cliff is a small step.
6. **Loop:** first and last `oklch` identical.

Vary **architecture, skeleton, chroma (muted↔vivid), glow temperature, and value key** across the batch —
the palettes should be genuinely different *color ideas*, not one idea with different peak positions.

**OKLCH hue reference (°):** red/oxblood 25–30 · rust/amber 50–70 · ochre/gold 80–95 · olive 110–120 ·
green 140 · teal/petrol 180–200 · cobalt/blue 250–265 · violet 290–310 · magenta/plum 330–350.

**Gamut:** achievable sRGB chroma peaks around **C ≈ 0.13–0.20** at mid lightness (hue-dependent; reds/
blues/oranges reach higher) and falls to **0 as L→0 or L→1** (black and white are C≈0). For vivid palettes
push C to the edge; the densifier clamps overshoot.

## Output schema (terse)

Output a short plan (2–4 sentences: how you'll span architectures and skeletons), then a **single fenced
```json code block** with the array. Nothing after it. Keep it terse — a stop is usually just
`{"pos", "oklch", "role"}`.

```json
[
  {
    "name": "Cobalt & Coal",
    "mood": "pure cobalt and orange against black and white; cobalt rises to a white flare, orange falls into black — two hues, no bridge",
    "architecture": "duotone-plus",
    "skeleton": "peak-early",
    "value_key": "low",
    "complexity": 3,
    "stops": [
      {"pos": 0.0,  "oklch": [0.09, 0.02, 250], "role": "ground"},
      {"pos": 0.16, "oklch": [0.44, 0.16, 258], "role": "anchor"},
      {"pos": 0.3,  "oklch": [0.96, 0.01, 240], "role": "glow"},
      {"pos": 0.5,  "oklch": [0.67, 0.17,  55], "role": "anchor"},
      {"pos": 0.72, "oklch": [0.16, 0.05,  32], "role": "mid"},
      {"pos": 1.0,  "oklch": [0.09, 0.02, 250], "role": "ground"}
    ]
  }
]
```

**Field definitions**
- `name` — short evocative label, unique in the batch.
- `mood` — one-line: hue inventory + where the drama lives (fold the temperature note in here).
- `architecture` — `duotone-plus` | `mono-temperature-ramp` | `complementary-tension` | `analogous-drift`
  | `triad` | `near-monochrome-spark`.
- `skeleton` — `peak-early` | `peak-late` | `double-peak` | `cliff-in-mids` | `no-cliff` | `inverted-arc`.
- `value_key` — `low` | `mid` | `high`. `complexity` — `1`–`6`. (Top-level, not wrapped.)
- `stops` — ordered, first `pos`=0.0 / last=1.0, strictly increasing; count within the complexity band.
  The **last stop repeats the first** (closed loop) — same `oklch`.
  - `pos` — 0.0–1.0.
  - `oklch` — `[L, C, H]`: L 0–1, C ≥ 0 (in gamut), H 0–360°.
  - `role` — `ground` | `field` | `mid` | `anchor` | `accent` | `glow`.
  - `segment` — **optional, default `smooth`.** Emit only when non-default:
    - `cliff` — soft ramp (optional `"width"` ≤ 0.12). **Small hue/value step only.**
    - `ease` — smoothstep lerp.
    A `glow` stop must have `smooth` on both sides (so never put `segment` on a glow or the stop before it).
  - `keypoint` — **optional, omit by default.** Role already carries the meaning; include a keypoint only
    to flag salience deliberately: `{"type": ..., "salience": 0–1}`, `type` ∈
    `value_cliff|hue_flip|glow_band|accent_pop|shadow_drop`.

## Validate before you present — run the attached script

`validate_palettes.py` is attached and is the **authoritative** mechanical checker. Workflow:

1. Build the batch and write it to a JSON file.
2. Run `python3 validate_palettes.py <file>`.
3. **Fix every `ERROR`** (loop/order, station count, unfeathered glow, oversized/complementary cliff,
   unrouted big hue jump) and re-run until zero errors. **`warn` lines are advisory** — judge them, don't
   reflexively "fix" them (a one-peak duotone or a deliberately deep hued dark is fine).
4. Read the batch-spread report it prints — architectures/skeletons/chroma should be spread, not clumped.
5. Present the validated array.

Do **not** hand-trace the mechanical rules — that's the script's job. Spend your reasoning on the
*aesthetic* choices the script can't check: whether the six architectures actually read as six different
color ideas, whether the vivid ones are genuinely pure, whether anything is muddy.

## Aesthetic self-check (the script can't judge these)

- **Architectures spread across all six (~3 each) — six different color ideas, not one repeated?**
- **Chroma varied — a real share vivid/pure (pushed to the gamut edge), a few muted, not uniformly either?**
- **Glow temperature split warm/cool?**
- At least one drama source per palette (purity/contrast, big temperature tension, or 3+ hue path)?
- Any muddy grey-brown midpoint? → fix.
- **Do the 20 palettes feel like genuinely different palettes, or one flavor with different peaks?**
