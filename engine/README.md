The Rust renderer: it makes every pixel this project ever shows.

One binary, nine subcommands, one JSON object in and one file out:

```
cargo build --release --manifest-path engine/Cargo.toml
echo '{"schema":1,"family":{"kind":"phoenix"},"resolution":[1920,1080],
       "supersample":2,"mode":"smooth_stripe","colormap":"twilight_shifted",
       "output":"artifacts/phoenix.png"}' \
  | engine/target/release/fractal-engine render
```

```
render      a location and a coloring → a PNG
dump-field  the same, stopping at the raw scalar field (+ a record of it)
recolor     a dumped field → a PNG, without iterating anything
expand      walk nodes → one rung each, gated, with a thumbnail per survivor
screen      frames you name → what each structural gate read, and its verdict
home-view   a family → where it is framed by default, and how that was derived
modes       the named colorings, as JSON
tiles       a plan of locations → training tiles, and a record of what was written
maxiter     widths → the iteration cap the depth policy gives each one
```

`expand` and `screen` are the same filter behind two doors. `src/screen.rs` owns
one `Battery` — the interior cap on a 128-pixel probe, the cap again on the node
render, the escape band, the occupancy floor, in that order — and both
subcommands spend it. `expand` *proposes* the frames it screens; `screen` is
handed them. A crate test screens an expansion's own candidates by name and
asserts every fate comes back the same, so the two cannot drift into being two
filters wearing one name.

Both readings a rung takes of its parent frame — the scale-space focus set and
the detail-weighted centroid — are pure functions of that frame, so `foci::Frame`
takes each on the first draw that wants it and every later draw off the same node
reads it. The randomness is untouched, because none of the cached work ever
consumed the node's stream. What that is worth is measured on the Python side:
see [the discovery package](../src/fractal_wallpapers/discovery/README.md).

`expand` will also report each node's kept focus set, behind `report_foci`. Off
by default and byte-identical off: the set is a reading of the parent frame that
every rung takes anyway and it consumes nothing from the node's random stream, so
the switch decides what is *reported*, never what is drawn.

The pipeline runs `spec → family → iterate → field → coloring → resample`, one
module per stage; `src/lib.rs` says what each does and why the seam between the
field and its coloring is the one that matters. `src/spec.rs` documents the JSON
and `src/mode.rs` the named colorings — nineteen of them, in four shapes: one
field, two fields blended, a base whose palette position a second field shifts,
or no field at all.

## The escape loop is written out per family and per channel set

`iterate::run` is one loop with eleven per-iteration channel checks and a `match`
over the families inside it, and it collapses to the bare recurrence only when
the compiler can see **both** the family and the channel set at the *call site*.
Then the checks fold away, `cpow`'s loop unrolls at a known degree, and the parts
of the `Orbit` nobody reads stop being built. Hand either one in as a runtime
value and none of it happens.

So the call site is written out rather than parameterized. `field::sweep_row`
matches its `Family` and its `Wants` into a table and **constructs** both fresh —
construction is what makes them constants — over the twelve channel sets of
`field::Channels` (the empty set, and each channel alone) times the nine families
of `family::over_written_out!`. Every catalogued mode lands in that table: a
composite lays its texture over the smooth base, and the smooth base asks the
loop for nothing, so a composite's channel set is its texture's single channel.
Two channels at once is reachable only from a hand-written coloring or a
multi-field dump, and falls through to the generic loop — same source, same
numbers, slower.

Measured on this repository's own machine, interleaved before-and-after at
640x360 ss2 over the home view of each family, best of three:

| family | smooth | tia | stripe | gaussian_int | threads | itinerary | de | all modes |
|---|---|---|---|---|---|---|---|---|
| mandelbrot | **2.45x** | 1.42 | 1.16 | 1.19 | 1.41 | 1.88 | 1.68 | 1.34 |
| multibrot d=3 | 1.90 | 1.51 | 1.14 | 1.22 | 1.39 | 1.65 | 1.61 | 1.34 |
| multibrot d=4 | 1.49 | 1.43 | 1.18 | 1.22 | 1.29 | 1.31 | 1.44 | 1.28 |
| multibrot d=5 | 1.24 | 1.33 | 1.15 | 1.25 | 1.27 | 1.21 | 1.42 | 1.25 |
| julia d=2 | 2.11 | 1.41 | 1.20 | 1.18 | 1.37 | 1.31 | 1.56 | 1.31 |
| julia d=3 | 2.05 | 1.52 | 1.18 | 1.18 | 1.41 | 1.80 | 1.68 | 1.35 |
| julia d=5 | 1.29 | 1.33 | 1.18 | 1.19 | 1.23 | 1.20 | 1.40 | 1.24 |
| phoenix | 1.21 | 1.07 | 1.04 | 1.11 | 1.10 | 1.13 | 1.48 | 1.12 |
| fractional d=2.5 | 1.09 | 1.06 | 1.07 | 1.14 | 1.06 | 1.07 | 1.06 | 1.08 |

**The two halves separate cleanly, and the bottom two rows are how.** Phoenix's
step is `z² + c + p·z₋₁` with no `cpow` to unroll, and `fractional_multibrot` is
not in the table at all — so both of them measure the *channel* half alone, and
both land near 1.1x. The gap between that and mandelbrot's 2.45x is the *family*
half. A direct trap, which paints in its own loop and never reaches this one, is
the control: 0.96x to 1.05x throughout.

The win shrinks as the recurrence gets more expensive, in both directions: down
the modes, because a `sin` or a `hypot` per iteration is work no folding removes,
and down the degrees, because `cpow` at `d = 5` is four multiplies whether or not
it unrolls. Two written-out families are cheap enough that the loop around them
is most of the cost, and those are the two that move.

It costs **175 KB of binary** (1.75 MB to 1.92 MB) and about **8 s** of the
crate's release compile (15 s to 23 s). Nothing else about the render changed: 347
renders spanning every family and every catalogued mode at all three live
geometries — 640x360 ss2, 384x216 ss1 and 2560x1440 ss4 — are byte-identical
before and after, and `field::tests::the_specialized_loop_is_the_generic_one_bit_for_bit`
holds the two paths together on every run of the suite.

**Three guards keep production out of the generic loop**, because a silent
fallback costs a multiple of the render time and shows up as nothing at all.
`every_production_mode_takes_the_specialized_loop` walks the mode catalog over
every family and asserts `field::takes_the_specialized_loop`;
`every_field_has_a_call_site_of_its_own` catches a twelfth channel added without
one; and the fallthrough arms carry `debug_assert`s that fire if something the
table claims to cover reaches them. The `match` over `Channels` is exhaustive, so
an arm cannot simply be deleted.

**Those three tests are the whole standing guard, because there is no benchmark
in this crate.** No `benches/` directory, no bench target in `Cargo.toml`, no
criterion dependency — the table above was measured by hand, interleaved
before-and-after, and is a record of one reading on one machine rather than
something CI re-takes. So a regression in the *numbers* would not be caught here;
what is caught, on every run of the suite, is the thing that actually costs a
multiple of the render time — production silently falling into the generic loop.
Re-taking the measurement means re-running it by hand. Do not go looking for a
`cargo bench`.

**`field::sweep_row` and `field::Channels` are `pub` under a carve-out, and the
consumer is the browser.** The site's wasm module draws a *band* of rows at a
time, one band per worker, so it cannot reach the specialized table through
[`sample`] — which takes a whole frame. While `sweep_row` was private the wasm
build carried a hand-written copy of the escape loop instead, and a second copy of
the recurrence that nothing holds to this one is how a page comes to quietly
disagree with a render. Visibility is the whole of what that consumer needs:
coordinates are formed from the **whole** viewport with a global row index, which
is exactly what a band wants, and a row appends to `lanes` rather than filling
them, so a caller may sweep any range of rows into one buffer.

Which is also the precise reading of where the specialization lives: **the table
is `sweep_row`'s**, and `field::sample` is not a second specialized entry point —
it reaches the same table through `gather`, one row at a time. So **production is
specialized**: every native render is `sample` (or `sample_exact`) → `gather` →
`sweep_row` a row at a time, and `gather` carries a `debug_assert` that its own
dispatch and `takes_the_specialized_loop` agree — which is what makes the three
guards above claims about the path production really takes rather than about a
table nothing reaches. Anything that calls
`sweep_row` directly gets the specialization; anything that hands the family or
the channel set in as a runtime value gets the generic loop, same source and same
numbers, slower.

**The direct trap's own loop is not specialized and is the obvious next piece.**
`direct_trap::trace` carries the same runtime `match` over the families, plus
three more of its own — the trap shape, the transform and the merge — inside the
same iteration. Four production modes draw through it. `family::over_written_out!`
is written where it is so that loop can use the same table when somebody takes
that on.

**And at `ss = 1` the resample is skipped.** The Lanczos kernel at a reduction of
one normalizes to exactly 1.0 on the centre tap, so both passes are a long way to
copy a buffer; `resample::downsample` encodes straight from the source instead.
Byte-identical over 171 renders at the node regime, which is the geometry that
matters here — 384x216 `ss = 1` is the walk's own frame, drawn tens of thousands
of times a run — and worth about **0.9 ms** of a node frame whose paint, after
the specialization above, is 16 ms.

That skip has a trap in it, and it is written down at `encode_only` because it
reverses the sign of the change: the two passes it removes were **rayon-parallel**
and the encode replacing them was not. The expensive half of a resample is one
`powf` per output channel, and both paths do exactly the same number of those —
so a serial skip *lost* to the filter, 0.85x, by trading fifty cheap operations
for the parallelism on the one costly one. Chunked across the same cores it is
1.03x to 1.20x.

Every catalog entry carries a **tier**. Nineteen are `production` — a run may draw
them, and the finished-render judges were trained on them. One is `niche`: `de`,
renderable on demand by name and excluded from every production draw. `threads`
and `itinerary` were niche too, until a round of labels over both of them said
they were worth drawing. The exclusion is enforced in one place on each side of
the boundary — `mode::production_names` here, `engine.production_modes()` in Python —
so it is a property of a function rather than a rule every draw site remembers.
`fractal-wallpapers modes` prints the tier beside each name.

One catalog entry is not the same coloring on both planes. `itinerary`'s address
can open on `z₀`, which on a dynamical plane *is* the pixel — so its leading symbol
is the pixel's own angular sector and the modulate draws it as a hard wedge along
the axes. `{"kind": "itinerary", "start": "z1"}` opens the address at the first
iterate instead, so every symbol is one the recurrence produced. **The named mode
asks for `z1` wherever the pixel is `z₀`** and for `z0` on the parameter planes,
where `z₀ = 0` leaves no wedge to remove and the engine refuses the other. The
choice is in the record either way, so the picture and its coloring say the same
thing. `fractal-engine modes` has no family to answer for, so it prints the
parameter-plane form.

**`start` has a third value, and it is a window rather than a start.**
`{"kind": "itinerary", "start": "tail"}` reads the **last** `depth` symbols the
orbit spelled before it stopped, instead of the first — `Address::roll`, a rolling
window whose whole rule is `frac(value·base) + sector·base^-depth`. It is exact
where `base >= sectors`, which is the only way the catalog asks for it (four
sectors in base four); under a smaller `weight_base` the retained window can reach
past 1 and `fract` takes a bite out of a symbol that was meant to stay, which is
stated at the function rather than refused. An orbit shorter than `depth` fills
the window from the bottom and so reads with leading zeros, which puts the
address's structure where the orbits run long — the boundary — and leaves the
fast-escaping exterior at the smooth base spent by rank.

`z₀` is never in a tail address, so there is no wedge for a plane to make and
nothing to renumber: **`tail_itinerary` is one coloring on both planes**, and
`Coloring::agrees_with_family` says so as a three-way match over `AddressStart`
rather than by not naming the variant. `tail_itinerary` is the catalog mode — the
same sectors, base, depth and half-turn shift as `itinerary`, with only the window
moved, so the two render as a comparison of the window and nothing else.

**A modulate can degenerate into an exact spelling of another mode, and it says
so.** `Coloring::Modulate` spends its base by rank and shifts where in the
gradient each rank lands by the normalized texture — `position = frac(rank(base)
+ shift · normalize(texture))`. Normalizing needs a span, and `Stretch::over` has
an `else` branch for when there is none: every sample at one value, or none of
them at a value at all. Then `spread.position` is `0.0` everywhere, the
per-sample phase is the recipe's own phase everywhere, and the picture is
`frac(rank(base)·cycles + phase)` through the map. The shift is still applied; it
is applied to zero. **That is not a picture resembling the base spent by rank, it
is that render bit for bit** — and since every catalogued composite and the
modulate are all built on `smooth_base()`, which
`smooth_is_the_default_and_the_base_of_every_composite` asserts over the whole
catalog, a degenerate `itinerary` or `tail_itinerary` render is the `smooth` mode
at `transfer: {"kind": "rank"}` and nothing else. Confirmed by sha256 at the
candidate regime, not only in the arithmetic.

So the `else` branch is reported rather than discarded. `Stretch::is_flat` keeps
it, `modulate` returns it beside the colour, `Painted::texture_flat` carries it up
and `RenderReport.texture_flat` prints it — `Option<bool>`, absent for every
coloring with no texture layer to be flat, which is all of them but the two
modulates.
It is absent by `skip_serializing_if` for the same recorded-name reason
`Composite::texture_gamma` is. The rule is about the modulate *shape* and names no
mode, which is why `tail_itinerary` needed nothing added to it. Python reads it in
`fractal_wallpapers.curation.mode_policy.routed_mode`, which is where the
consequence lives: such a render routes as `smooth` wherever a mode or a kind is
decided. **A flat texture is a no-op recolour and not a weak one** — this is the
difference between the modulate and a composite, where a flat texture blends
toward a constant and makes a *worse* picture rather than a different mode's.

Width does not predict it and a dumped field cannot measure it. Over the 1,962
`itinerary` rows in the candidate ledger the widest degenerate frame is wider
than the narrowest varying one in every one of the nine partitions; and counting
distinct values in the `f32` dump reads 1,280 degenerate against a truth of
1,085, wrong 15.2% of the time, because `Address` spends its `f32` after eleven
base-4 symbols against the catalogued depth of 26 and whole subtrees of the
lamination collapse on the way in. That is the same fact `why_not_a_field` states:
the texture is carried at `f64` precisely to keep it out of the dump.

A field meant to be *looked at* rather than named stays out of the catalog
entirely. There is one: `discrete`, the integer escape count, which is what the
smooth count replaced and is in the crate so the article can show the two side by
side. `fractal-wallpapers render --discrete [CYCLE]` draws it. A **teaching field
has no business having a name**, so the guard is not "no mode is called
discrete": `no_catalogued_mode_reads_a_teaching_field` walks every field every
catalogued mode reads, both halves of a composite included, because the second
way in is the one nobody would look for. The two readings really are one escape,
and the smooth one refines the other — `the_smooth_count_lands_inside_the_step_the_orbit_left_on`
pins `floor(smooth) == iteration` over five families and 3,600 pixels each, which
is what makes the discrete render the *floor* of the smooth one rather than
something merely similar to it.

**A new field of a coloring must `skip_serializing_if` its default.** The render
cache and the location head's deploy view both name a file by
`renders.job_name`, a **truncated sha256 of the whole spec that goes over the
wire** — every key the engine is told, and nothing else — so a key that appeared
unconditionally would rename every picture the corpora were built from.
`Composite::texture_gamma`, `Direct::merge_order` and the itinerary field's
`start` are all written that way, and each says so where it is declared.

**The same digest names a dumped field, and there the rule runs the other way.**
`curation.colorize.field_of` keys the field cache with `renders.job_name` over a
spec it *builds* rather than one it was handed, so a field-side axis added to the
engine and left out of that spec would leave two different fields sharing one
name — and every candidate recoloured off whichever was dumped first. The
identity is therefore derived from the field-side members themselves
(`renders.FIELD_IDENTITY`) rather than hand-listed at the call site, and
`tests/test_curation_colorize.py` pins both halves: an added member moves the
digest, and the digests of the specs already on disk do not move.

**Three lists carry that, and adding an axis means classifying it.**
`renders.SPEC_MEMBERS` is every row member `spec_of` reads — the whole of what
the digest is over. `FIELD_IDENTITY` is the half a dumped field is a function of
(the place, the geometry, the field the mode names and the curve it is read
through); `RECOLOR_MEMBERS` is the rest (`colormap`, `recipe`), spent after the
field is on disk, over and over, without iterating anything. Two candidates
differing only in the second half are one field and thirty-two pictures.

**`field_job_name` refuses rather than proceeds, in both directions**, which is
what makes the classification mandatory instead of merely conventional. A member
`spec_of` reads that is in neither list raises — "classify it" — because a field's
name would otherwise not say whether it depends on that member. And a member
declared field-side that the caller supplied no value for raises too, because a
field cached without it would be shared by every value it can take. So an axis
added to the engine cannot reach the field cache by being forgotten: one of those
two refusals fires first. The failure being bought off is not one stale file — it
is thirty-two wrong candidates, every one recoloured off whichever field was
dumped first under a shared name.

**A recolor is the render, through EVERY stage of the recipe.** `recolor` used to
call `coloring::shade` and stop, and `shade` ends at the colormap lookup — so the
recipe's last stage, `Rolloff`, which acts on the colour rather than on the index
into the map, was applied by `render` and not by `recolor`. Nothing caught it,
because every recipe this project renders through carries `rolloff: none`, which
is a fact about today's recipes and not about the two paths. `coloring::toned` is
now the single owner of that stage and `paint` and `recolor` both call it. It
matters more than it did: `curation.colorize.render` serves a candidate out of a
dumped field wherever the coloring has one, so "a recolour is the render byte for
byte" is load-bearing for the candidate ledger rather than only for exploration.
`tests/test_modes.py` pins all four curves, each held to *moving* the picture so
the test cannot pass by testing nothing.

## The direct traps: a blend from white is not a screen upside down

Four production modes make no field at all. `direct_trap::Painter::trace` watches
the orbit and composites a gradient sample into the pixel at **every** near miss,
so a pixel is the stack of every approach the orbit made, in order. That has one
consequence the module used to state backwards, and it cost this project a whole
mode's worth of pale pictures before anybody measured it.

`direct_trap_screen` starts from black and screens; `direct_trap_multiply` starts
from white and multiplies. Black absorbs a multiply, so the mode that multiplies
*has* to start from white — but the two constructions are symmetric **in linear
light and nowhere else**. For a neutral, Oklab `L = v^(1/3)`, so `dL/dv` is 0.333
at white and 8.33 at `L = 0.2`. A multiply from white can lose at most
`1 - opacity*(1 - sample)` of its ground per hit: 9.3 hits to reach `L = 0.5` at
the impossible best case of alpha 0.20 and sample 0, and about 29 at a typical
alpha 0.10 and sample 0.30. A screen from black clears `L = 0.2` in half a hit.

Measured on the two modes' clearing candidates — near-white being the share of the
frame at `L >= 0.90` and chroma `<= 0.06`:

| mode | rows | in-mask chroma p50 | near-white p50 / p90 / max |
|---|--:|--:|--:|
| `direct_trap_multiply` | 138 | 0.011 | **0.434 / 0.708 / 0.950** |
| `direct_trap_screen` | 134 | 0.046 | 0.005 / 0.061 / 0.360 |
| `direct_trap_lines` | 82 | 0.045 | 0.084 / 0.456 / 0.924 |
| `direct_trap_ring` | 29 | 0.047 | 0.053 / 0.358 / 0.555 |

A matched test settles that it is the blend and not anything around it: same
`Shape::Cross`, same threshold, same opacity, same place and same map, so the hit
set and every per-hit alpha are identical and only `merge` and `start_color`
differ. Multiply moves the frame **further** in linear light (0.0897 against
0.0114 on one pair) and 7-25x **less** in Oklab (0.032 against 0.215). It is not
autolevel — `applies_to` answers only for `field` and `composite`, and every one
of those 138 rows carries `autolevel = null`. It is not the palette fold, which
runs the other way: forced onto one location, a plain map is *whiter* than the
same map mirrored, because folding halves how far up the ramp a key reaches. And
it is not the colormap: Spearman(near-white, the map's mean spent Oklab L) is
0.101, and restricting to the 143 darkest of the 901 maps of the day moves the median 0.434 to
about 0.418. `direct_trap_multiply` already carries twice `direct_trap_screen`'s
threshold and 1.33x its opacity, and it is still the pale one.

**The fix is a mode-param variant, not an engine change.** `renders.coloring_of`
writes a row's `opacity` and `threshold` into the coloring block, so a varied row
is a new recipe key: nothing re-keys, no cached picture changes underneath its
name, and no human label is voided. Editing the constants at `mode.rs` instead
re-keys all 4,733 `direct_trap_multiply` rows the ledger holds, voids their
sidecar scores, forces a full re-render — a direct trap cannot dump, so a recolour
is a render — and invalidates **594 of the 5,298** human verdicts in the
strange-render store (406 of 5,110 before `dtm_variants_20260902` landed), because
they were cast on pictures that would no longer exist. Only 44 of the 594 override
both knobs, so a change to either constant reaches all but those.

**The variants were drawn, served and judged, and they do fix the whitewash.**
`dtm_variants_20260902`, 188 human verdicts at label geometry, 2026-09-03. All four
cells collapse the near-white share against the shipped mode's 0.434 median:
`opacity=0.4` to 0.094, `opacity=0.6` to 0.032, `threshold=0.2` to 0.011, and both
raised to 0.000. Matt's tier-4 rate over the batch is 21.8% against 1.8% on the 55
shipped-setting rows this store already held, and the top tier is the whole of the
gain — the three single-knob cells sit at 65.9-78.8% tier-3-or-better and mean tier
2.92-2.95, while raising **both** knobs together overshoots: mean tier 1.93, 25.0%
tier-3-or-better, and no ground left to lose.

**And the bias is the judge's alone.** On the three single-knob cells
Spearman(chroma, `P(>=4)`) is **-0.291**, which reproduces the -0.269 above on a
population the audit never saw; Spearman(chroma, Matt's tier) over the same rows is
**+0.023**. The eye is indifferent to chroma and the judge is against it, so the
disagreement between them is chroma-shaped: ranking the 188 by tier against ranking
them by `P(>=4)`, Spearman(rank gap, chroma) is **-0.271** (p = 0.0002, -0.318 with
the over-inked cell dropped). On a matched page — same place, same map, only the
settings swapped — the judge's `P(>=4)` falls on 16-19 of 20 pairs per cell, by a
median 0.37 to 0.73. Nothing here changes a roster; the cells are Matt's to dictate.

**And an engine-side pixel change here used to be invisible twice over.** The
recipe key digests the catalog block, which carries `shape`, `trap_radius`,
`threshold`, `opacity`, `merge`, `start_color` and `transform` — and no
arithmetic. So a whole-frame normalization, a gamma before the multiply, or a
second clamp beside `SCREEN_CROSS_OPACITY_CAP` would change every direct-trap
picture in the project while every file name held. The engine fingerprint did not
catch it either: its probe set drew six field-and-composite modes and no direct
trap. `engine_fingerprint.TRAP_PROBES` closes that half — one probe per trap,
digested into `coverage()` rather than into the stamp, so the sample widens
without restamping the views already on disk. What is still unguarded is the
candidate pool itself, whose rows carry no engine at all.

## The colormap: stops on disk, a folded table in the engine

A file in `data/palettes` is **control points**, never a gradient, and it ships at
one of four resolutions — 33 stops for 156 maps, 34 for 36, 257 for 334, 512 for
495; 1,021 files and none at 4096. `Colormap::from_stops_baked` is the only densifier:
the stops are sorted, converted to **OKLab**, interpolated there, and baked into a
`TABLE_SIZE` (**4096**) entry table of linear-light RGB, regenerated on every load.
Perceptual interpolation because a gradient interpolated in linear RGB is evenly
spaced and visually lumpy; a table because a 2560x1440 render at ss4 is 59 million
lookups that only ever take 4096 values.

Two consequences a reader outside the crate has to carry. A lookup is **clamped and
not wrapped** — `t` outside `[0, 1]` returns the end colour, and what falling off the
end means is for the recipe's `cycles` and `phase` to say. And **anything comparing
two maps has to sample positions through this interpolation** rather than compare
stop lists, because two maps at 33 and 512 stops are two samplings of one curve and
the difference between the samplings is not a difference between the maps.
`palettes.groups.cloud` is the Python side of that: 4096 evenly spaced unfolded
positions, `numpy.interp` in OKLab, end colours held outside the outermost stops
exactly as `interpolate` holds them here.

**Folding happens at bake time, from the recipe's `mirror`.** `colormap::mirror`
runs the stops out across `[0, 0.5]` and back across `[0.5, 1]` — `n` stops become
`2n − 1`, the two ends shared between the halves rather than duplicated, and the
opening colour written again at `1.0` so the closing segment is the fold rather than
the second-to-last colour held flat. It is applied **before** the OKLab conversion,
so a folded map is a different 4096-entry table and not a different way of reading
one. Production's rule is `mirror = the map is not cyclic`, owned by
`models.palette_sets.recipe_for` and read off the gradient rather than off a row: of
the 1,020-map candidate pool **155 are sequential and are folded, 865 are cyclic and
are not**, and the engine refuses to fold a cyclic map at all.

**And a fold is why a lopsided field loses nearly all of a map.** The fold sends the
ramp's original position `g` to *two* table positions, `g / 2` and `1 − g / 2`, so
the ramp's far end lands **dead centre** — `g = 1` at `t = 0.5` — and its whole far
half lives in the middle band of the stretch. `coloring` normalizes a field against
its own 0.5th and 99.5th percentiles, and an escape-time field is nowhere near
uniform over that stretch: it piles up, often very hard, at one end. A frame with no
middle therefore never reaches the far half of a folded map, however much of the
gradient that half occupies — a swatch at gradient position 0.8 needs field values
near 0.4 and 0.6 of the stretch and is simply absent from a frame that has none. So
a map's ramp is a **necessary condition on what a picture can be and not a
prediction**, which is why `curation.palette_coverage` measures capability on pixels
instead, and why its probe panel takes by construction the two cells whose gradient
positions pile hardest at one end: those are the cells where a mirrored ramp strands
its far half, and a panel without one cannot see the failure it exists to find.

## The whole lib compiles to wasm32, and draws the same bytes

`engine/src` carries **no `cfg(target_arch)` anywhere**: the crate compiles to
`wasm32-unknown-unknown` unmodified, and the two things that could have needed a
gate do not.

* **Rayon.** `coloring` and `resample` are `par_iter` throughout. `rayon-core`
  detects that a target's threading is unsupported and configures a global
  **single-threaded fallback** rather than panicking — as if `RAYON_NUM_THREADS=1` —
  so the parallelism on a page is that page's worker pool, and the engine did not
  have to know.
* **The filesystem.** The one fs touch reachable from the coloring path is
  `Colormap::load`. A wasm consumer calls `from_stops_baked` instead, which is why a
  map crosses that boundary as stops rather than as a name.

**Whole-frame output is byte-identical to native.** Each of the eighteen production
modes, on the parameter plane and on a dynamical one, at one and at two samples per
pixel, against `fractal-engine render` of the same spec: **72 of 72 frames**. It is
the same `f64` code over the same inputs, and wasm's `f64` is IEEE-754 with no x87
excess precision to diverge through. That measurement lives with the consumer rather
than here — this crate has no wasm target of its own and no test that builds one.

**The bindings take one render spec and have no family-specific entry point.** The
site's module exports `plan`, `compute_band` and `shade`, and all three take the
engine's own render spec minus the two keys that name files, plus the colormap by
value — so a family, a degree, a constant, a mode, a mode parameter and a palette
recipe have exactly one spelling on that boundary, and **adding a family here is not
adding an export**. `plan` is what a page asks first, and it answers out of
`mode::resolve`, `maxiter::for_width` and `Family::home_view` rather than out of a
table the page keeps. No wasm-bindgen: the module is this crate plus one file.

**Consumers pin by path, because the version cannot tell them anything.** This crate
is `0.1.0` and is never bumped, so a git dependency could not distinguish two
revisions of it — and it would drag the Python package, the data and the labels into
a build that wants one Rust library. The site's `explorer/engine-wasm` therefore
depends on this directory by path, and its `build.rs` exists to say exactly that when
the sibling checkout is missing. What identifies a build is what it draws: see
[`engine_fingerprint`](../src/fractal_wallpapers/engine_fingerprint.py), a digest of
a pinned probe set rendered through the production path, which catches a binary
rebuilt from unchanged source by a different toolchain as well as a source change.

## What each family's picture is symmetric under

None of this is code — there is no symmetry pass in the crate and nothing folds a
render — but it is what the recurrences in `family.rs` imply, and it is the first
thing to check when a picture looks like it has a bug in it. Measured below on 401²
`smooth` fields, width 3.0 about the origin at a cap of 800, rotated by nearest
sample and compared where both land inside the frame.

* **Multibrot, `z ← z^d + c` with the pixel as `c`: `(d − 1)`-fold rotation about the
  origin.** `c ↦ ωc` with `ω^{d−1} = 1` conjugates the whole orbit by `ω`, and the
  escape test reads only `|z|`. At `d = 2` that is the identity, which is the honest
  reading of the Mandelbrot set having no rotational symmetry at all;
  `discovery.nucleus` folds an atom's `c` into the fundamental sector on this same
  rule. Measured: at `d = 3, 4, 5` the median `|Δsmooth|` under a `(d − 1)`-fold
  rotation is 0.0000, 0.0041 and 0.0000, against 0.10 to 0.69 at the neighbouring
  wrong orders.
* **Julia, the same recurrence with the pixel as `z₀`: `d`-fold.** Not by conjugacy —
  `f(ωz) = ω^d z^d + c = f(z)` exactly when `ω^d = 1`, so the two orbits *coincide*
  after one step rather than merely mirroring, and it holds for every `c`. Measured
  at `c = −0.4 + 0.6i`: median `|Δsmooth|` 0.0000, 0.0049, 0.0000 and 0.0031 at
  `d = 2..5`, against 0.16 to 0.28 at the wrong orders.
* **Any family whose constants are real: reflection in the real axis**, because
  `cpow` and `cpowf` both commute with conjugation and `|z̄| = |z|`. That is the one
  symmetry `fractional_multibrot` has, and it is why the negative real axis of its
  *parameter* plane is not a seam — below.
* **Phoenix, `z ← z² + c + p·z₋₁`: that conjugation and nothing else, and only when
  `c`, `p` and `z₋₁` are ALL real.** `CLASSIC_PHOENIX` is `(0.5667, 0)`, `(−0.5, 0)`
  and `z₋₁ = 0`, so the default render has it; give any one of the three an imaginary
  part and it is gone. Measured on the classic instance the largest `|Δsmooth|`
  across the axis is **0.0057** — the `f32` dump's own granularity — and with `c`
  moved to `0.5666 + 0.1i` it is **147**.
* **`p = 0` erases the memory term and leaves a quadratic Julia set**, exactly rather
  than approximately: `phoenix_with_zero_p_is_a_quadratic_julia` pins the smooth
  counts equal **bit for bit** over 1,600 samples, and a dumped 401² field at
  `c = −0.4 + 0.6i` is byte-identical to the `julia` degree-2 one. A non-zero `z₋₁`
  is a real axis and not a decoration — `a_nonzero_z_prev_gives_a_different_set`.

## The one family that only draws pictures

`fractional_multibrot` is `z ← z^d + c` at a **non-integer** `d`, on the
principal branch — `exp(d · Log z)` with `Arg z ∈ (−π, π]`, written out in
`cpowf` rather than delegated so the branch cut is a line somebody can point at.
The cut is on the negative real axis, so the picture carries a **seam** along
every ray where an iterate crosses it. That seam is not an artifact to be
smoothed away: it is what a fractional degree *is* on a single-valued branch, and
it is the subject of the figure this family exists to draw. A different branch
moves it and does not remove it.

**The cut is in `z`, so the parameter plane's own real axis is NOT a seam.** The
branch is chosen in `cpowf`, which is applied to an *iterate*; the pixel is `c`, and
`cpowf` commutes with conjugation, so the orbit from `c̄` is the conjugate of the
orbit from `c` and the escape test reads only `|z|`. The picture is therefore exactly
symmetric about the real axis: on 401² fields at `d = 1.8` and `d = 2.5` the
difference across `im = 0` is **zero everywhere**, where the typical neighbouring
difference elsewhere in the same frame is 0.009 to 0.027. What the picture does carry
is the curves where an *iterate* crosses the cut, and by the same argument those
arrive in conjugate pairs.

**Below degree 2 the seam is the picture rather than a detail of it.** At `d = 2.5`
the seams are thin rays off a set that still reads as a multibrot. At `d = 1.8` a
broad double ray runs corner to corner through a set that is small, lopsided and
pushed off-centre, and it is the first thing anyone sees — which is the figure this
family exists to draw, and the reason `LOWEST_FRACTIONAL_DEGREE` reaches below the
quadratic degree at all.

**A frame below degree 2 costs about half of one just above it, and that is the set
shrinking rather than orbits escaping sooner.** Same geometry throughout — 401²,
width 4.0 about the origin, cap 2000, `dump-field`:

| d | escapes | median smooth | seconds |
|--:|--:|--:|--:|
| 1.8 | 94.3% | 6.88 | 0.23 |
| 1.9 | 93.2% | 6.61 | 0.27 |
| 2.1 | 88.6% | 6.15 | 0.48 |
| 2.5 | 88.3% | 5.39 | 0.44 |
| 3.5 | 89.5% | 4.43 | 0.39 |

Only interior samples pay the full cap, so the cost tracks the escaping share and
not the count. **The count itself runs the other way**: over the samples that escape
at every degree in the table the median is 6.73 at `d = 1.8` against 5.32 at
`d = 2.5`, because the smooth count's base is `ln d` and `ln d < ln 2` below the
quadratic degree. That is the same fact
`the_smooth_count_does_not_terrace_below_degree_two` exists for — a smaller base
*amplifies* the overshoot correction rather than shrinking it, so a wrong
normalization shows up more loudly at 1.8 and 1.9 than at 2.

It is **render-only**, and that is a guarantee about what cannot happen rather
than a gap. A written `render` or `dump-field` spec reaches it; seven other doors
turn it away by name — the supply engine's partition registry, the render cache's
plane question, every `--family` choice on the command line, the home-view table,
`expand`, `screen` and `tiles`. `Family::is_render_only` is the single question
all of them ask, so adding a door cannot quietly add a way in, and
`spec::render_only_refusal` is the one message they share.
`location.key_of_row` is the one that answers `None` instead of raising, and its
caller counts unjoinable rows, which is the loudest failure short of an
exception. `tests/test_fractional_degree.py` is the whole guarantee in one file.

Three consequences fall out of render-only:

* **`Family::home_view()` returns an `Option`, and this is the `None`.** A row in
  the framing table is a claim that a family is worth looking at unprompted,
  which is the one thing this family is not — so a spec for one says where it is
  framed or is refused.
* **The degree range is a statement about what has been eyeballed, not about
  where the arithmetic breaks.** `LOWEST_FRACTIONAL_DEGREE` is `1.8` and the
  ceiling is `5.0`, the same kind of claim `check_degree` makes about the
  integers. `iterate::BAILOUT` is `2^16` and a multibrot's escape radius
  `2^(1/(d−1))` stays inside it all the way down to `d = 1 + 1/16`;
  `the_bailout_covers_the_lowest_degree` pins that gap, so the floor can be
  lowered by looking at pictures rather than by touching the loop. The range
  reaches below 2 deliberately — `z^1.8 + c` is a set of its own and not an
  interpolation between two named ones.
* **A whole number is refused.** `degree: "3.0"` is the multibrot family's, read
  the same way `multibrot` refuses degree 2 because that set is the Mandelbrot
  set: one picture gets one name, and one cache identity.

No integer-degree render pays for any of this. `cpow` is repeated multiplication
over degrees 2 through 5 — faster than a polar round trip and exact where one is
not — and `cpowf` is reached only by this family.

**One capability is deliberately absent and is not debt: normal-map shading** —
lighting a render by the surface normal of a distance estimate, with an azimuth
and a lamp height. It makes a fractal read as an embossed metal plaque rather than
as a field, replacing the picture's own structure with a lighting model's. The
`de` field ships without it, as a scalar coloring like any other. Two further
gaps *are* open decisions rather than omissions: `biomorph`, which would change
what `n` means and so what every cached render means, and perturbation-based deep
zoom, which is the one genuinely large thing this engine lacks (`iterate.rs`
carries the TODO). **Deep zoom has two revival conditions, not one.** The obvious
one is the door below the coordinate wall. The second is *correctness above it*:
the escape counts this engine returns are already measurably wrong at depths it
draws today (below), and a low-precision delta against a high-precision reference
orbit is the fix for that as much as it is the key to the next four decades.

Until it arrives, `Viewport::is_resolvable_in_f64` is what says how deep `f64`
goes — and it asks the question the arithmetic actually poses. A sample coordinate
is formed as `center + across * width`, so two neighbouring sample centres tie
when the step between them falls under one `f64` unit of last place *at the
magnitude of that sum*. The refusal reads exactly that: `sample_spacing()`
against `RESOLUTION_ULPS` (4) ulps of the frame's own reach.

**It used to be `pixel_size() > 1e-13`, which was wrong twice.** A relative limit
enforced as an absolute constant, and read off the *output* pixel, so a
supersampled render was judged on a grid four times coarser than the one it
samples. Bisected at 2560x1440 ss4, the first tie is at width 2.84e-13 for a
centre near 0.23, 1.42e-13 near 0.081, 2.27e-12 at |c| = 1 — against a refusal at
2.56e-10, so **2.0 to 3.3 decades of headroom nothing was using**. Nothing that
used to be drawn is refused now; a great deal that was refused for the wrong
reason is drawn, which is what
[the deep run mode](../src/fractal_wallpapers/deep/README.md) descends into. The
new rule is held to the measurement by `viewport.rs`'s own tests, which bisect for
the tie and require the refusal to sit a *constant* multiple above it at four
magnitudes — a rule that were secretly absolute shows a headroom that moves.

Measured alongside, before any of that changed: the deepest location any ledger
holds (1.0165e-9) renders at release geometry with **zero** tied sample centres
per row, and the tie rate in its dumped field scales exactly x4 with a 4x finer
grid — which is the `f32` dump's own storage granularity, the same law the
shallow control four decades above the wall obeys. See
`scratch/measure_deep_probe_report.md`.

**The refusal guards COORDINATE REPRESENTABILITY and nothing else.** That is the
whole of its contract: it says two neighbouring sample centres are still two
numbers, and it says nothing whatever about the escape count computed from
either. There is a second wall above it — call it the *fidelity* wall — and the
engine does not guard it, cannot cheaply detect it, and does not claim to. A
sample coordinate can be perfectly distinct from its neighbour and the *orbit*
run from it still be decided by rounding: `f64` carries about 1e-16, the dynamics
stretch that by the Lyapunov growth of a few thousand iterations, and what comes
back is not the value at that point.
`julia_deep_eyetest`'s second addendum measured it — same starting `f64`
coordinate, orbit re-run at 50 digits, and the share of sampled points whose
escape count disagrees:

```text
case                 deg   wrong >=1% from   engine refuses   at 1e-11
julia (off-set)        2             1e-11            1e-13       6.3%
multibrot3 walk node   3              1e-9            1e-13       8.0%
mandelbrot walk node   2              1e-5            1e-13      22.0%
multibrot4 walk node   4              1e-5            1e-13      14.5%
julia (off-set)        5              1e-5            1e-13      26.8%
```

**The fidelity wall is case-dependent and sits between about `1e-4` and `1e-10`,
two to eight decades above the refusal.** Where a case lands on that spread is
decided by how long its orbits linger near the boundary, not by its degree: the
degree-2 mandelbrot node above sits on a **period-198** nucleus and is already
**2.3% wrong at `1e-5`**, crossing at the same rung as the degree-5 julia.

**It is almost never visible.** Only the degree-5 julia shows anything, as a
mosaic of bit-identical neighbours, and *supersampling makes that one worse* —
66.6% of adjacent samples identical at ss1 rising to 95.6% at ss8, because a
finer grid brings coordinates closer together and closeness is what the orbit
cannot keep. The other four are wrong by more and read as ordinary deep
pictures.

**This engine's `z^d` is the canonical identity of this project's output.**
`cpow` builds it by repeated multiplication; Python's repeated squaring is the
same arithmetic in a different order, and at degrees 4 and 5 the two `f64`
implementations differ by a whole iteration or more on **12.2%** and **20.4%** of
samples, worst 411 and 205. At degrees 2 and 3 the orders coincide and they
agree to `1e-5`, which is what that test looks like when rounding is not deciding
the answer. So **cross-implementation agreement is not expected at degree ≥ 4**
and is not a bug report: below the fidelity wall the evaluation order *is* the
definition, and a render is reproducible against this engine rather than against
the mathematics.

Nothing in the engine changed on the strength of this — the refusal is unmoved
and no fidelity check was added, because detecting one costs a second orbit at
higher precision per sample. What changed is downstream: the deep run mode reads
its floor as an **aesthetic** one and caps degree 5 a decade early, where wrong
turns into visibly flat. See
`scratch/julia_deep_eyetest_addendum2_report.md` for the per-case evidence and
`../src/fractal_wallpapers/deep/README.md` for the contract.

What deep zoom would cost, observed on the maker's perturbation backend at the S1
anchor with this repo's own cap policy: a walk node (384×216 ss1) is 0.31 s at
fw 1e-12, 2.75 s at 1e-15, 1.02 s at 1e-18 — cost tracks how much of the frame is
deep-iterating material, not depth, so budget ~3 s worst case. A *release* frame
(2560×1440 ss4) at fw 1e-15 is **~1 800 s** with no series approximation, which is
`curation.pacing.HUNG_CEILING[RELEASE]` exactly. Descending is cheap; presenting
what is found is not.

A render given no viewport comes home to its family's own frame, a table in
`src/family.rs` — and so does a walk root, which reads that table through
`home-view` rather than keeping a literal of its own. **Framing has one owner.**

Every row is one rule evaluated on that family's own measured set: the filled
set found on a 4001² grid at a cap of 4000, centred on itself, contained at 16:9
with a tenth of its deciding extent in margin. Nothing in the table was chosen —
the textbook Mandelbrot view `(−0.5, 3.0)` does not survive it, because three
units at 16:9 is 1.69 tall and the set is 2.2. Julia is the one exception, and a
stated one: its set is a different shape for every `c`, so there is nothing to
measure and it comes home to the whole plane.

Beside the pipeline sits the search — `rng`, `screen`, `foci`, `expand` — which
uses it and does not extend it. It decides *where* to render and never *how*:
`expand` reads fields the pipeline produced and returns coordinates with the
structural gate that refused each one. What makes a picture good is not its
business; that judgement lives in Python.

Python drives this through `src/fractal_wallpapers/engine.py` and nothing else.
