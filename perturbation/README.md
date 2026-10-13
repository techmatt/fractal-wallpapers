# perturbation — `z^d + c` below the `f64` floor

The picture core of the explorer's Deep tab, as a crate of its own beside `engine/`. It
renders the smooth field of `z^d + c` — the Multibrot set of every integer degree from two
to six, and the Julia set of any `c` at each — by **perturbation with rebasing**, at widths
the `f64` engine cannot draw, and hands it out as one `f64` lane a sample. It has no UI, no
page, no link contract and no exports of its own. Two crates ship it, and neither keeps a
copy (the website's `explorer/deep-gpu-model` also takes it by path, as the kernel its GPU
model is measured against):

- **`fractal-engine`**, natively, behind its `deep` feature, which is on by default: it is
  how `render-link` draws a `dv=` link from the same arithmetic the page uses. The
  website's `engine-wasm` turns the feature off, so `engine.wasm` links none of this.
- **The website's `explorer/perturb-wasm`**, which wraps this crate in the `extern "C"`
  exports the page calls and compiles it twice, to `perturb.wasm` (wasm SIMD) and
  `perturb-scalar.wasm`. The website pins all three of its modules by one commit of this
  repository, `engine.manifest.json`'s `wallpapers_commit`.

**What stays in the website** is what only the explorer asks for: the minibrot search
(`fractal-website/explorer/perturb-wasm/src/nuclei.rs`), the Dive
(`fractal-website/explorer/perturb-wasm/src/dive.rs`),
the exports, the GPU path and all of the JavaScript. Their measurements are §9 to §12 of
that crate's `README.md`, and the eight sections this file took kept their numbers, so a
citation of §3 or §8 from either repository still names the same thing.

**Reading the sections below.** They were measured and written in the website's checkout
and moved here whole *(deep_seam_move_ckpt163)*: a path the move changed was repointed,
and nothing else was rewritten. So:

- a path under `src/` or `tests/` is this crate's own, unless it starts
  `fractal-website/`, which is the website's checkout beside this one;
- an export named in passing — `plan`, `compute_band`, `probe_band`, `reference_orbit`,
  `newton_step` — is the wrapper's, in `fractal-website/explorer/perturb-wasm/src/lib.rs`,
  over the functions here;
- a `scratch/` path is the website checkout's untracked scratch, where that measurement
  was taken, and neither repository carries it.

A moved section that points at one of the four that stayed means the website README's
(`fractal-website/explorer/perturb-wasm/README.md`) section of that number:

| § | heading there |
| --- | --- |
| 9 | *9. The minibrots in and around a view* |
| 10 | *10. Degrees three to six* |
| 11 | *11. The dive* |
| 12 | *12. Copy or bulb, by the root* |

**The two sets are one kernel and one reference orbit**, which is the shape the
whole Julia case takes and is worth reading before anything below. The stored
orbit is `Z₀ = 0, Z₁ = c, Z₂ = c² + c, …` — the critical orbit of `c` — and it is
*simultaneously* the Julia orbit of `z = 0` and, shifted by one index, the Julia
orbit of `z = c`. So a Julia frame is drawn from the orbit a Mandelbrot frame
centred at that `c` already computed, and the only differences in the loop are
where it enters and whether `dc` is spent every step or once.

It also has **no dependencies at all** — not `serde`, not the engine, not even as
a dev-dependency. It is a dependency of the engine, of the website's wasm module, and of its
GPU model, so everything it took, all three would take. `src/json.rs` reads the fifteen-member spec
and `smooth-cases.json` pins the one formula that had to come from the engine.

```text
src/fx.rs              fixed-point reals, n × u64 limbs, written for wasm32
src/reference.rs       one high-precision orbit per frame, projected to f64
src/kernel.rs          the per-sample f64 delta loop, with rebasing
src/lanes.rs           the same loop two samples a vector, in a wasm SIMD build
                       and nowhere else
src/policy.rs          the cap a frame asks for: what died at a cap, and whether
                       raising it would change the picture
src/json.rs            a reader for one flat JSON object
src/progress.rs        a wasm build's one import, env.progress: how far a long
                       call has got, told while it runs; nothing, natively
src/lib.rs             the spec, its anchors, the width's cap, and the calls both
                       builders make: compute_rows, compute_listed, pack_reference,
                       band_ran, band_saved
smooth-cases.json      400 of the engine's own samples, as the pin
tests/oracle.rs        the kernel against a brute-force oracle (ignored by default)
tests/parity.rs        every bit the kernel hands out, pinned a spec at a time:
                       parity-specs.jsonl in, parity-pins.txt the record
tests/orbit_parity.rs  every byte of the packed reference orbit, pinned
tests/interior.rs      the interior switch never paints an escaping sample
                       black (§3)
tests/common/          the seven deep frames the website's descend.rs settled on,
                       as cases, with their links — and the six controls a cap
                       policy has to leave alone; plus the one walk of a sample
                       grid the harnesses share, written to match
                       policy::probe_rows
tests/frames.rs        the two cheap pins on that record: still spellable, still
                       at the cap it claims
```

The harnesses that read `tests/common` and stayed in the website — `descend.rs`,
`measure.rs` and `classify_speed.rs` — reach it by `#[path]` across the two checkouts.

## The design, in one page

- **The reference orbit is fixed point; everything per-sample is `f64`.** The
  orbit runs once per frame: 11.2 ms in wasm at the anchor's 48,552 points and
  three limbs (§4), growing with the cap and the limb count to seconds at a cap of
  a million. The frame costs seconds to minutes.
- **The limb count comes from the view, and at one anchor from the degree as
  well** — `ceil(log2(samples across / width)) + 64` guard bits, the archive's
  rule, with no term for the orbit length, the supersample, or the period. Three
  limbs at 2e-11, four at 1e-28. The exception is a Julia frame anchored at
  `z = 0`, whose first step raises the pixel offset to the degree: there the
  view's bits are multiplied by `d` before the guard bits are added
  (`reference::limbs_pow`, §2b, and the website README's *10. Degrees three to six*).
- **The bailout check comes before the precision.** Fixed point overflows its
  integer limb silently, so a reference that escapes has to be stopped rather
  than wrapped. (The audit priced the alternatives: astro-float degrades to
  inf/NaN on an escaping orbit and dashu-float panics outright.)
- **`δ' = (2·Z[m] + δ)·δ + dc`, and rebasing is Zhuoran's**: when `|z| < |δ|`, or
  the reference runs out, `δ := z` and `m := 0`. That is the whole of the glitch
  handling — no Pauldelbrot test, no secondary reference, no correction pass.
- **The Julia case is that recurrence with `dc` spent once instead of every
  step.** Holding `c` and varying `z₀`, the delta obeys `δ' = (2·Z[m] + δ)·δ` with
  no `dc` term at all: the offset that was added every iteration becomes the delta
  the loop opens with, and the entry index moves from `Z₀` to the point the view is
  anchored at. `JULIA` is a const generic and not a field, because `x + 0.0` is not
  `x` when `x` is `-0.0` — a zero `dc` carried as data would cost the Julia loop two
  additions an iteration that no optimizer is permitted to remove.
- **And rebasing is untouched, which is the reason there is no second reference
  here.** `δ := z` is only a rebase because `Z₀ = 0`: the delta becomes the iterate
  itself, with no subtraction and so no cancellation. Under `z ↦ z² + c` the stored
  orbit from index 0 is the orbit of the critical point, a valid reference for any
  `z`, so the same two lines say the same true thing. Rebasing onto an orbit that
  started anywhere else would need `δ := z − Z₀` in `f64`, and that subtraction is
  exactly the precision a deep frame has none of to spare.
- **Two anchors, and both are points of the orbit**: `z = c` at index 1, where the
  filigree is, and `z = 0` at index 0, the critical point, where the picture has
  exact two-fold symmetry. Both offsets are exact fixed-point subtractions, so
  which one a frame uses changes nothing about the mathematics — only how much of
  the pixel step survives into the `f64` delta.
- **`delta_ulps` is the engine's `resolution_ulps` asked of the delta**, and it is
  what refuses a frame too far from its anchor. There the question is whether two
  neighbouring sample *centres* are the same `f64`; here the centres are exact
  decimals and it is the delta that is a double, so a view a long way from its
  anchor at a width far below it starts every pixel from the same number and would
  draw one flat colour with total confidence. The floor is `DELTA_ULPS = 4.0`, the
  engine's own, restated the way `cap::for_width` is. The wall is further out than
  it sounds: an offset of 0.76 at 480 samples across still leaves 375 numbers to a
  pixel at 2e-11, and only bites below about 3e-13 — which is why the second anchor
  matters at depth and nowhere else.
- **`dc` is geometry plus a fixed-point centre difference**, never `f64(centre) −
  f64(reference)`. At 1e-28 those two are the same `f64` and the difference is
  exactly zero, which would draw the reference's neighbourhood wherever the view
  actually is and look entirely plausible.
- **A named period makes the reference periodic.** The orbit is stored for one
  period and the index wraps instead of rebasing: 45 KB instead of 777 KB at the
  anchor, and — measured below — no rebasing at all.
- **The cap a frame draws at is the frame's own, and §8 is the rule.** The
  width's answer is where the walk *starts*: below about 1e-22 it lands inside the
  frame's own escape-count distribution and a sixth to a third of a busy frame is
  painted as set when it was exterior the count never reached. So a frame is
  probed at that cap, and the cap doubles while samples are still dying with
  `|dz|` past the escape radius. It moves five of the seven deep frames by one
  doubling and repaints a sixth to a third of each; it moves none of the six
  controls at all.
- **The width's own cap is the engine's shape without the engine's ceiling.**
  `maxiter::for_width` saturates at 67,000 by a width of about 4.7e-16, which
  would flatten every perturbation-depth view to one cap. The shape is restated
  here and only the ceiling moves, to 1,000,000 — `cap::AUTOMATIC_CEILING`, one of
  the crate's two ceilings since cap_split_ckpt145 (§8). Touching
  `maxiter::for_width` itself was never an option: six callers read it and a
  wider ceiling there moves the cap of every shallow picture the project has.
- **There is no skip table, and §6 is why.** Bivariate linear approximation was
  built, priced over two rounds and taken back out: on the anchor's own ladder it
  looked like a 59×, but every frame it was measured deep enough to pay on was
  100% interior, and on seven deep frames that have something in them it is
  between a 21% loss and 2.6× **and moves the picture at every tolerance,
  including the tightest one the approximation admits**. Every picture the page
  draws is the plain loop's, which is the whole of what §1 through §3 argue.

### What it does not do

`z^d + c` at integer degrees two to six, `smooth`, and nothing else *(degrees three to six
since `deep_degrees_ckpt140`; §10, the website README's "10. Degrees three to six")*. It
draws the two sets each degree has — the parameter
plane and the dynamical one — because they are one recurrence read two ways and one
reference orbit to draw either from, and **not** because it is growing into a wider engine.
No fractional degree, no other family, no other mode. It is one kernel with the degree as a
const parameter, which is the shape `fractal-website/explorer/README.md` always said a deep renderer would
have to take. Two families are closed rather than pending: a fractional degree, because
`(Z+δ)^α − Z^α` fails exactly on the branch-cut seam that is that family's subject, and
Phoenix, because its recurrence needs a second delta lane and a two-point reference.

## What the engine needed

**Nothing.** No change was made or is needed in `fractal-wallpapers`, and
`engine.manifest.json` is unmoved. The one thing that had to come from next door
is `iterate::smooth_count`, which is private — and the audit's ruling was to
restate it here with a test pinning it to the engine's output rather than open a
function over there. `smooth-cases.json` is that test's data: 400 samples of the
engine's own field, plus the 311 `(escape step, |z|² at it, smooth)` triples read
straight off `Orbit`, written by `scratch/perturb_validate cases`.

The triples are the real pin, and they hold **exactly** — the closed form is
compared with no iteration in front of it, so there is nowhere for a difference
in arithmetic to hide.

*(deep_seam_move_ckpt163.)* The paragraphs above describe the kernel's first home, in
the website, where nothing in this repository had to change for it. The ruling they record
holds here too: the engine now depends on this crate and nothing runs the other way, so
`iterate::smooth_count` is still restated in `src/kernel.rs` rather than shared, and
`smooth-cases.json` still pins the restatement to the engine's output.

## Proof

Measured on 2026-09-19, one idle box, `rustc 1.96.0`, Node v24.19.0. The anchor
throughout is the audit's: a **period-2838 minibrot nucleus in the seahorse
valley**, atom size 6.478e-12, centre
`-0.74501772828532335842941892835857434 + 0.14993443275456819177805709088257971i`,
framed at width **2e-11** — cap 48,551, **38.9% interior**.

### 1. Against `f64`, where `f64` still draws

The anchor frame at 480×270 ss1, this kernel against `iterate::run`:

| | |
|---|---|
| interior, both | 48,161 (37.2%) |
| interior, only perturbation | 2,241 |
| interior, only the engine | 2,324 |
| smooth on the 76,874 both escape | median **61.4**, p90 7,790, p99 20,160, worst 34,250 |
| bit-equal | **0** |

**They do not agree, and the disagreement is not small.** A median difference of
61 iterations on escape counts whose median is 20,236 is 0.3%, and the tail runs
to 34,250 — half the cap. This is the audit's own surprise 3 seen from the other
side: fidelity fails far above the coordinate wall, and 2e-11 is four decades
below where it starts failing.

**Which of the two is wrong is settled separately**, by the brute-force oracle,
and the answer is unambiguous. On the 311 escaping samples of the pinned cases'
view (`smooth-cases.json`: the seahorse-valley point −0.7436438870371587 +
0.1318259042053120i at width 0.02, cap 12,674, 20×20 — not the 2e-11 anchor, where no
oracle is run), run three ways — this kernel, the plain `f64` loop, and a 384-bit
fixed-point oracle — **the kernel is nearer the truth on 307 and the plain loop
on 4**. On a shallow grid at `c = -0.5` where `f64` is still honest, 1,874 of
2,776 escaping samples are bit-equal to the oracle and 2,770 are within 1e-6; the
worst sample there is one within an ulp of the boundary, where the kernel reads
3,832, the plain loop 1,730, and the truth is 3,025.

### 2. Against a brute-force oracle, below the wall

`tests/oracle.rs`. Every sample iterated directly in the same fixed-point
arithmetic, no reference and no delta, so the comparison measures the
perturbation and nothing else. Tiles are 16×9 because the oracle is the expensive
half.

**A finding first: the anchor cannot supply a ladder.** The atom is 6.478e-12
across, so every frame narrower than that is inside the minibrot's body and
100% interior — a nucleus is the wrong place to look for structure below its own
atom size. Those rungs still say something (the two agree about *which* samples
are interior, at every depth) but the escaping half of the question needs a view
with structure at every scale. That is `c = i`: a Misiurewicz point, exactly
representable as `0 + 1i` with no solve and no stored digits, on the boundary,
and asymptotically self-similar about itself.

**The Misiurewicz ladder** — and this is the one that proves the arithmetic:

| width | cap | limbs | escaping | interior disagreements | median Δ | worst Δ | rebases mean / max |
|---|--:|--:|--:|--:|--:|--:|--:|
| 1e-4 | 21,847 | 3 | 144 | 0 | **0** | 1.7e-13 | 2.0 / 7 |
| 1e-8 | 37,792 | 3 | 144 | 0 | **0** | 1.5e-12 | 2.5 / 8 |
| 1e-13 | 57,724 | 3 | 144 | 0 | **0** | 2.9e-13 | 2.1 / 9 |
| 1e-16 | 69,682 | 3 | 144 | 0 | **0** | 8.5e-14 | 2.1 / 7 |
| 1e-19 | 81,641 | 4 | 144 | 0 | **0** | 8.4e-13 | 2.1 / 7 |
| 1e-22 | 93,600 | 4 | 144 | 0 | **0** | 2.4e-12 | 2.1 / 8 |
| 1e-25 | 105,559 | 4 | 144 | 0 | **0** | 2.5e-12 | 2.1 / 9 |
| 1e-28 | 117,518 | 4 | 144 | 0 | **0** | 5.5e-13 | 2.2 / 9 |

Every sample of every rung escapes, every sample agrees with the oracle about
whether it escaped, the **median difference is exactly zero at every depth**, and
the worst is a part in 1e13. At the bottom rung the sample spacing is 6e-30 and
every sample in the tile is the same `f64`, so there is no reading of this table
in which the coordinate machinery is working by accident.

**The anchor ladder**, both references:

| reference | width | cap | limbs | escaping | interior disagreements | median Δ | median Δ/ν | worst Δ | rebases mean / max |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| view centre | 2e-11 | 48,551 | 3 | 88 | **0** | 1.0e-6 | 3.5e-11 | 7.6e3 | 10.3 / 44 |
| view centre | 1e-13 | 57,724 | 3 | 0 | **0** | — | — | — | 0.0 / 0 |
| view centre | 1e-19 | 81,641 | 4 | 0 | **0** | — | — | — | 12.6 / 28 |
| view centre | 1e-28 | 117,518 | 4 | 0 | **0** | — | — | — | 20.5 / 41 |
| nucleus, period 2838 | 2e-11 | 48,551 | 3 | 100 | **0** | 9.7e-7 | 5.6e-11 | 7.5e3 | 12.0 / 44 |
| nucleus, period 2838 | 1e-13 | 57,724 | 3 | 0 | **0** | — | — | — | 0.0 / 0 |
| nucleus, period 2838 | 1e-19 | 81,641 | 4 | 0 | **0** | — | — | — | **0.0 / 0** |
| nucleus, period 2838 | 1e-28 | 117,518 | 4 | 0 | **0** | — | — | — | **0.0 / 0** |

(1e-16, 1e-22 and 1e-25 are in the suite too and say the same thing.) The
periodic run has the view nudged a quarter of a frame off the nucleus, so its
centre offset is not zero and has to be taken in fixed point.

Three things worth reading off it. **The interior masks never disagree**, at any
depth or either reference. **On the one rung with exterior in it the median
relative error is 3.5e-11** — ten digits — while the worst is 7,600, which is the
chaos the three-way probe pins on the boundary rather than on the kernel; the
suite is held to the median for that reason, and the share within a relative
1e-6 is 84%. And **naming the period removes rebasing entirely**: 20.5 rebases a
sample at 1e-28 against the view centre, and none at all against the wrapped
nucleus, because the wrap is what the rebase was standing in for.

### 2b. The Julia case, against the same oracle

Measured 2026-09-20, same box. Three ladders, all in `tests/oracle.rs`, and the
oracle for a Julia sample is the same fixed-point loop with `z₀` the pixel and `c`
held.

**`c = i` is the ladder for the same reason it is the Mandelbrot one**: its Julia
set is a dendrite — no interior at all, structure at every scale, and the critical
point on the set, so both anchors sit on real structure — and `0 + 1i` is exactly
representable with no stored digits to be wrong about. Every rung, both anchors,
1e-4 down to 1e-28, 144 samples a tile:

| | escaping | interior disagreements | median Δ | worst Δ | within 1e-6 | rebases mean / max |
|---|--:|--:|--:|--:|--:|--:|
| anchored at `z = c` | 144 of 144, every rung | **0** | **0** at every rung | 1.8e-12 | 100% | 2.0–2.3 / 6–9 |
| anchored at `z = 0` | 144 of 144, every rung | **0** | **0** at every rung | 1.3e-12 | 100% | 2.1–2.7 / 5–7 |

At the bottom rung the sample spacing is 6e-30 and every `z₀` in the tile is the
same `f64`, so there is no reading of this in which the delta machinery is working
by accident.

**A finding the first run of that ladder produced, and it is about the oracle.**
At the origin anchor the ladder failed below 1e-16 — 20 interior disagreements at
1e-28 and a median Δ of 0.3 — and the kernel was not the one that was wrong. A
Julia sample anchored at `z = 0` has `z₁ = z₀² + c`, so what tells two neighbouring
pixels apart is the *square* of a spacing: 4e-59 at the bottom rung. Fixed point is
absolute precision, and at the frame's own four limbs 4e-59 is below the last bit —
every pixel of the oracle's tile became the same number and the oracle drew a flat
tile. The kernel carries that delta in `f64`, which is *relative* precision and
holds it to sixteen digits. The oracle runs at twice the limbs at that anchor now,
and the walk says so where it does it.

⚠ **And the kernel's own orbit was short of the same bits, which the ladder could not
see** *(found by `audit_deep_families_ckpt140`, fixed in `deep_degrees_ckpt140`,
2026-09-22)*. The delta rides in `f64` and is fine; the *reference* is fixed point, and
it held `c` to the view's bits when the pixels at `z₁` are `step²` apart. The `c = i`
ladder is blind to it because `i` is dyadic — its orbit is exact at any limb count. So
the origin anchor now computes its orbit at `reference::limbs_pow`'s count — twice the
view's sample bits plus the 64 guard bits — and `tests/oracle.rs`'s
`the_origin_anchor_holds_a_non_dyadic_c_to_the_squared_step` is the ladder that can see
it: `M(3,1)` to 130 digits, a real boundary `c` whose orbit uses all of them, 16×9 at a
cap of 20,000.

| width | limbs before → after | median Δ before | median Δ after | interior disagreements |
|---|--:|--:|--:|--:|
| 1e-20 | 4 → 5 | 2.8e-14 | 2.8e-14 | 0 |
| 1e-30 | 4 → 6 | **6.6** | 5.7e-14 | 0 |
| 1e-36 | 4 → 6 | **34** | 5.7e-14 | 0 |
| 1e-40 | 5 → 7 | **11** | 5.7e-14 | 0 |

The "before" column is the audit's run of the committed kernel on the same tile. On the
page's own grid of about 2,272 samples across, the limb rule puts the threshold near
3e-26 — derived, not measured on the page. It costs a longer reference orbit and nothing
per sample. The page's orbit key reads the count off `plan` rather than off
`limbs_for_width`, since a held orbit at the width's count would otherwise pass the key
test for a frame it is too shallow for; and where even sixteen limbs cannot hold the
square — below about 3e-132 at `z = 0` on that grid — `plan` refuses the frame in a sentence.

**The audit's own deep `c`, drawn as a Julia set at `z = c`** — the view the tab's
button opens — is held to its median and not its worst sample, which is the anchor
ladder's ruling and is here for the anchor ladder's reason:

| width | cap | escaping | interior disagreements | median Δ/ν | worst Δ | within 1e-6 |
|---|--:|--:|--:|--:|--:|--:|
| 2e-6 | 28,619 | 142 | 0 | 3.9e-14 | 1.5e-1 | 99.3% |
| 2e-8 | 36,592 | 141 | 0 | 7.0e-12 | 1.7e2 | 89.4% |
| 2e-9 | 40,578 | 136 | **2** | 5.5e-12 | 5.9e2 | 86.0% |
| 2e-10 | 44,565 | 15 | 0 | 1.2e-11 | 6.2e1 | 86.7% |
| 2e-11 | 48,551 | 0 | 0 | — | — | — |

The bottom rungs are entirely interior, and that is the picture rather than the
kernel: inside a superattracting basin every point converges to the cycle, so a
frame narrower than the structure around `z = c` is filled.

**The two interior disagreements at 2e-9 are chaos, and that is settled rather
than asserted.** The oracle escapes at 32,897 and 36,223 where the kernel runs to a
cap of 40,578 — not cap-straddling, a difference of thousands, which is the same
signature as the Mandelbrot anchor's worst Δ of 7.6e3 one section up. So
`fractal-website/explorer/perturb-wasm/tests/probe.rs` asks the third opinion at a width where `f64` is still honest
(2e-9 across sixteen samples is a million representable numbers to a pixel), and
the answer is unambiguous: **the kernel is nearer the oracle on 250 of 256 samples
and the plain `f64` loop on 1**, with the plain loop reading 20,283 where the
oracle reads 29,223. A kernel carrying the wrong recurrence could not produce that
table.

And the shallow end, where a completely different program can be asked:
`fractal-website/explorer/deep.test.mjs` draws the Douady rabbit's Julia set through this module
and through **`engine.wasm`'s own `f=julia` render** of the same `c` — no reference
orbit, no delta, no rebasing — and holds the two to agreeing about the interior
mask sample for sample and about the smooth count to a median relative 1e-6. Two
kernels sharing no code and agreeing about a picture is the strongest statement
available about the recurrence, the entry index and the geometry at once.

### 2c. A reference somewhere else in the frame *(deep_orbit_history_ckpt150, 2026-09-25)*

The page's pool used to keep an orbit whose point was anywhere inside the next frame, so the
same frame could be drawn off its own centre on a fresh load and off a parent's centre after
a zoom. Which of the two is right was asked of this oracle, with a scratch crate on the
crate's public API (nothing here moved). Each frame is a child at half its parent's width,
centred 0.2 of the parent's width across and −0.1 down, so the parent's centre is inside
it. The tile is 64×36 and the interior switch is on, as the page draws.

| child of | width | cap | orbit points, own / kept | vs oracle: median Δ own / kept | Δ > 0.1, own / kept | mask | rebases a sample, own / kept |
|---|--:|--:|--:|--:|--:|--:|--:|
| the video's final frame | 1.74e-15 | 63,534 | 27,258 / 26,246 | 1.7e-10 / 2.1e-10 | 37 / 36 | 0 / 0 | 11.6 / 11.9 |
| the glowdon gallery frame | 5e-20 | 200,416 | 30,727 / 200,417 | 4.4e-11 / 5.5e-11 | 25 / 30 | 0 / 0 | 11.0 / 11.3 |

**Neither reference is wrong, and neither is better.** Both agree with the oracle to the
same median, both keep the mask, and both have the same chaotic tail, a percent or two of
the samples, where a boundary sample amplifies the last bit of whatever path it took. Kept
against own, only 101 and 440 of 2,304 samples are bit-equal, and 43 and 31 differ past 0.1:
the two are the same picture to the eye, and not the same bytes. The home frame
`-0.77 + 0i` at width 4.4, drawn off the deep centre above, says the same against `f64`: both
at median 1.4e-7 and p99 1.0e-6, with 49 samples past 0.1 off its own centre and 52 off
the deep one. So the page now keeps an
orbit only where it is the one a fresh load would compute (`sameOrbit` in
`fractal-website/explorer/deep-render.js`), which is a rule for determinism rather than for accuracy.

### 3. The interior switch

`dz_n = ∏ 2·z_k` is the derivative of the `n`-fold map along the orbit: it decays
geometrically inside a hyperbolic component and grows outside one. (The usual
derivative, with respect to `z₀`, is useless here — Mandelbrot fixes `z₀ = 0` and
the product is identically zero from its first factor.) It is carried as a
mantissa in `[1, 2^64)` and a power-of-two exponent, and the test `|dz|² < 2^floor`
is exact, gated by an integer compare that is false on all but the last handful
of iterations.

**Swept on the anchor at 96×54** — 2,019 of 5,184 samples interior:

| floor | `\|dz\|²` below | caught of 2,019 | wrongly painted | iterations saved |
|--:|--:|--:|--:|--:|
| −300 | 2^-300 | 0 | 0 | 0.0% |
| −160 | 2^-160 | 0 | 0 | 0.0% |
| −120 | 2^-120 | 4 | 0 | 0.0% |
| −100 | 2^-100 | 14 | 0 | 0.1% |
| −80 | 2^-80 | 30 | 0 | 0.2% |
| **−64** | 2^-64 | 66 | **0** | 0.4% |
| −48 | 2^-48 | 129 | 0 | 0.9% |
| −32 | 2^-32 | 272 | 0 | 2.5% |
| −16 | 2^-16 | 616 | 0 | 7.7% |
| −8 | 2^-8 | 988 | 0 | 16.0% |
| −4 | 2^-4 | 1,293 | 0 | 26.4% |

And ON against OFF across both ladders at −64, with the same assertion on every
sample:

| view | width | interior | caught | wrongly painted | iterations saved |
|---|---|--:|--:|--:|--:|
| anchor | 2e-11 | 56 | 2 | 0 | 0.4% |
| anchor | 1e-13 | 144 | 144 | 0 | 75.1% |
| anchor | 1e-16 | 144 | 144 | 0 | 91.9% |
| anchor | 1e-22 | 144 | 144 | 0 | 97.0% |
| anchor | 1e-28 | 144 | 144 | 0 | 97.6% |
| c = i | any rung | 0 | 0 | 0 | 0.0% |

**Nothing was ever wrongly painted, at any threshold from 2^-300 to 2^-4**, on
either ladder. The condition for shipping it on was that it never paint interior
a sample the plain run escapes from, and it never did; it ships **on**, at
**−64**, the safe end of the sweep's useful range.

**It is worth saying plainly that at the anchor this is a small net loss.** The
switch costs 9% per iteration (4.80 ns to 5.24) and at −64 recovers 0.4% of the
frame, because only about seventeen periods of a period-2838 minibrot fit inside a cap
of 48,551 and `|dz|` has not had room to fall. It pays where the frames are
deeper and interior-dominated, which is most of what a perturbation renderer is
for. The sweep is here so that the tab prompt can move the number against its own
views rather than re-deriving it; −4 catches 64% of the interior and takes 26% off
the frame, and on this evidence is safe, but on one frame's evidence only.

#### The threshold was never a proof *(interior_switch_fix_ckpt162, 2026-10-10)*

The ladders above were the wrong frames to find this on. `fractal-website/explorer/deep-gpu-model` built
long-orbit frames beside parabolic points, and the switch painted their exterior black:
**52 of 144** samples of the degree-2 main cusp (`c = 1/4 + (π/10⁷)²`, 4e-19 across) and
**140 of 144** of the imploded Julia set at `c = 1/4 + 10⁻¹²`, every one of them proven
at about 2.2e5 iterations by a sample the plain loop escapes from at 1e7 and 3.1e6.

**Why.** There the orbit creeps up on a fixed point where `|f'| = 1`, from the side
where `|f'|` is just under one, so `∏|f'(z_k)|²` decays like a power of `n` instead of
geometrically. On the cusp it crosses `2^-64` at 219,631 iterations, bottoms out at
`2^-79.4` half way through, climbs back as the orbit leaves, and the sample escapes at
9,999,855. A small product says the map has contracted so far, and not that it always
will. **It is not one frame's accident**: built the same way at every degree, the cusp
and its imploded Julia set at both anchors (`scratch/interior-fix/parabolic.py`), the
rule was wrong on every cusp and every origin-anchored implosion from degree two to six,
84 of 84 samples on each cusp.

**The fix makes it a proof.** The product is now a gate: a sample under it is handed to
`Kernel::prove`, which carries on the same loop step for step and stops the sample only
when **a disc about its orbit maps into itself**. A disc `B` with `f^k(B) ⊂ B` traps
the orbit, so it is bounded. The image of a disc of radius `ρ` about `z` lies within
`(|z| + ρ)^d − |z|^d` of `f(z)`, so the radius is carried forward exactly, with no
linearization, and the test is `|z_{s+k} − z_s| + ρ_k ≤ ρ₀`. The disc sits at the
smallest `|z|` reached since the gate (an attracting cycle contracts hardest nearest the
critical point, and `z` is known to the finest absolute error there). Four radii, a
factor of 256 apart, are tried at once, with a relative margin of `2^-40` a step and
an absolute one of about thirty ulps on the test. Beside a parabolic point the proof cannot
close, since a disc mapped into itself holds a fixed point that an escaping orbit does not
have, so those samples run to their escape or their cap. A disc is carried for as many
steps past its anchor as the gate took (at least 4,096), and then the sample runs plain
until a new low re-arms it: on the corpus no proof needed more than 2.0× the gate's own
`n`, and a parabolic gate is millions of steps.

**What it moved, measured against the rule it replaces sample for sample**
(`scratch/interior-fix/harness`, the old kernel linked beside the new):

- **No escaping sample is painted interior on any frame tried**: the parabolic set above,
  the model's nine long-orbit frames, eighteen Siegel and one-third boundary frames at
  degrees two to four, the 2,333-frame corpus the GPU model was measured on (64×36), and
  the 157 of those behind a tracked picture or the deep pack (256×144). Every escaping
  count is bit-identical to the switch off. §10's floor sweep (the website README's *The
  constants, re-swept at each degree*) is now 0 wrongly painted at every floor and degree, the degree-six −4 case included.
- **No site frame had a wrong pixel**: across the corpus not one sample goes from interior
  to escaped, and the same at 256×144. The rule's failure needs a gate millions of steps
  long, and no frame the site draws has one.
- **What it costs is proofs that land later.** Proven interior falls 0.4% (36,899 to
  36,746 on the corpus, which now run to the cap and are black either way), and the
  iterations rise 0.47%. **In wasm**, §7's frames at 240×135, the committed module against
  this one alternated, best of three, lanes byte for byte the same on all five:
  `tangle 1e-22` 1.04×, `body 1e-22` 1.04×, `anchor 2e-11` 1.03× and `anchor 3e-12` 1.14×,
  all inside the box's drift, and **`anchor 1e-12`, 100% interior, 1.37×**, the one result
  clearly beyond it. That frame's samples run 13% more steps before a disc closes, about a
  period past the gate, and those steps carry the discs. Where the gate fires on an escaping
  sample the frame is slower than with the switch off (the d2 cusp at 16×9 took 1.6× as
  long, the imploded Julia set 2.0×), and the page's `switchFor` turns the switch off for
  such a frame after its quarter pass, since nothing was saved.
- **The module grew 20,869 bytes raw and 3,570 gzipped** (377,477 and 136,453, on 1.96.0,
  which rebuilds the module before this one byte for byte): the proof's loop, once per
  degree and set, and the refusal's second sentence.

### 4. Price

**Native**, one idle box, best of three, all three measured the same way in the
same binary on the same frame — the anchor at 480×270 ss1, 4.22e9
sample-iterations:

| | seconds | ns / sample-iteration |
|---|--:|--:|
| the engine's own `iterate::run` | 19.78 | **4.68** |
| perturbation, interior off | 20.27 | **4.80** |
| perturbation, interior on | 22.01 | 5.24 |

**Perturbation costs 2.6% more per sample-iteration than the plain `f64` loop**,
and the interior switch costs a further 9%. The audit's expectation was "the same
order", and it is nearer than that — which is not obvious, because the delta
recurrence is about 1.7× the arithmetic of the plain one and reads a 777 KB array
the plain one does not. Where that goes is not accounted for here.

Two caveats on the 4.68. It is *this harness's* figure for the engine, calling
`iterate::escape` per sample; the audit measured 3.83 ns for the same loop
through `field::sweep_row`'s specialized table and the engine's own report. The
ratio above is the fair comparison because both sides of it were taken the same
way; against the audit's own figure the kernel is 25% slower.

**The first version of this loop was about 2.5× slower**, and the fix was how the
reference orbit is laid out and read: two parallel `f64` arrays, four indexed
loads per iteration, and the loop's invariants re-read through `&Reference` every
pass. Interleaving the orbit into one array of `[re, im]` pairs, carrying `Z[m]`
across the step instead of loading it twice, and hoisting the invariants took it
to 4.80. A 48,552-point orbit is 777 KB and does not sit in L2, so how it is read
is most of what the loop is doing. ⚠ *The two changes were made together and are
not separated, and the before figure is an estimate: the harness that produced it
had the engine's loop inside its own timer, worth about 4.7 ns an iteration,
which is a measurement bug found and fixed afterwards. The 4.80 and the 4.68 above
are clean.*

**The reference orbit**: 48,552 points at three limbs in **6.3 ms** native and
**11.2 ms** in wasm, once per frame. Against a frame of 20 s that is
0.03%, and it is the number that would have been paid fifty times over had it
been computed inside a band's `resolve` instead of handed across as a buffer.

⚠ **It was 14.7 ms and 25.4 ms** until `deep_refactor_ckpt138`, and what moved is
`Fx::mul`: the limb count is a compile-time constant inside it now, through a
dispatch to a specialization per `n`, where it used to be a field read off the
operand. The scratch array is the frame's own width rather than the widest this
module carries — twelve `u32`s zeroed at three limbs instead of sixty-four — and,
which is most of the win, every trip count in the loop is known.

| | before | after | |
|---|--:|--:|--:|
| `Fx::mul`, 3 limbs | 97.5 ns | **37.6 ns** | 2.6× |
| `Fx::mul`, 4 limbs | 131.5 ns | **57.8 ns** | 2.3× |
| `Fx::mul`, 6 limbs | 231.8 ns | **99.9 ns** | 2.3× |
| `Fx::mul`, 16 limbs | 1,373 ns | 1,372 ns | 1.0× |
| reference orbit, native | 13.9 ms | **6.3 ms** | 2.2× |
| reference orbit, wasm | 21.6 ms | **11.2 ms** | 1.9× |
| `newton_step`, period 2,838 | 0.82 ms | **0.38 ms** | 2.2× |
| `newton_step`, period 94,776 | 28.1 ms | **12.8 ms** | 2.2× |

Native figures are `scratch/fx_bench`, best of five, the two versions run
alternately because the box drifts about 30%; the wasm pair is the same orbit
through both committed modules. **`ns / sample-iteration` is not in that table
because there is no mechanism for it to move**: nothing per-sample is fixed
point. It was measured anyway — 4.73 against the 4.80 above, interior off, and
5.42 against 5.24 with the switch on — and those are the box on the day, not the
multiply.

**Sixteen limbs buys nothing** and is the fallback arm, still the unspecialized
loop: 256 half-limb products, where the zeroing was never what it was spending.
**The cost is 19.8 KB of module**, 4.0 KB gzipped — fifteen specializations of
one function, and the only reason the gzip figure is the smaller half is
`#[inline(never)]` on it, which is worth 1.1 KB compressed and nothing
measurable in time. The whole of it is paid by a reader who opens the Deep tab,
and what it buys them is a nucleus search at twice the speed: a solve at 1e-54
was 1.96 s.

**Bit-identical, and checked rather than argued.** `Fx::mul` has a test of its
own against the unspecialized version — 3,000 products at every limb count from
2 to 16, both signs, zero limbs among them — and across the two committed
modules the reference orbits at 3, 4, 5 and 6 limbs and the fields drawn from
them are byte for byte the same (`scratch/orbit-parity.mjs`).

**In wasm**, Node v24.19.0, single instance, single thread, same frame:

| | seconds | ns / sample-iteration |
|---|--:|--:|
| perturbation, interior off | 21.28 | **5.04** |
| perturbation, interior on | 27.70 | 6.59 |

Wasm is **5% slower than native** here, and the interior switch costs 31% in wasm
against 9% native. Both are worth flagging rather than explaining: the audit
found the *engine's* loop 12% **faster** in wasm than native on this same frame
and excluded build flags, engine version and thread count as causes. Whatever V8
is doing for that loop it is not doing for this one, and a deep tab should price
its own frames rather than scale a native figure.

**What a Julia frame costs against the Mandelbrot frame at the same `c`, width and
cap** — `fractal-website/explorer/bench/julia.mjs`, 221×124 on one thread, 2026-09-20:

| width | cap | mandelbrot | julia | ratio |
|---|--:|--:|--:|--:|
| 2e-9 | 40,578 | 2,025 ms · 14% interior | 2,038 ms · 4% interior | **1.01×** |
| 2e-10 | 44,565 | 1,957 ms · 1% interior | 3,275 ms · 89% interior | **1.67×** |
| 2e-11 | 48,551 | 5,751 ms · 39% interior | 1,858 ms · 100% interior | **0.32×** |

**A frame time cannot answer whether the Julia loop is the same price**, and that
table is why: the two frames do different amounts of work because their interior
shares are different, and an interior sample either stops early under the switch or
pays the whole cap. The ratio swings from 0.32 to 1.67 with the picture and says
nothing about the recurrence.

So the loop is priced with the work held equal — a cap of 1,200, low enough that
**no sample of either frame escapes**, and the interior switch off, so every sample
of both runs exactly `cap` iterations:

| | ms | ns / sample-iteration |
|---|--:|--:|
| mandelbrot | 167 | **5.08** |
| julia | 134 | **4.07** |

**The Julia loop is 20% cheaper per sample-iteration**, which is the two additions
it does not do and, on frames that rebase differently, some part of that too — the
two are not separated here. It is the first thing in this crate that is *faster*
than the Mandelbrot path, and it wants no explanation beyond the recurrence being
shorter.

**The orbit the jump needs is 18 to 25 ms**, and every point of it is a point the
Mandelbrot frame's orbit already had: the Julia orbit is asked for one step longer,
because a view entered at `Z₁` has one step less of reference in front of it, so it
is recomputed rather than reused. Against a frame of seconds that is 1%, and it is
the whole price of pressing the button.

**`perturb.wasm` is 199,293 bytes raw and 78,382 gzipped** at level 9
(`fractal-website/explorer/perturb.manifest.json` carried both) — 112,675 / 52,784 when
this paragraph was first written, grown by the cap policy (§8), the nucleus search (§9,
the website README's *9. The minibrots in and around a view*), whose Newton solve, decimal
writer and second walk of the loop are most of it, the multiply's fifteen specializations
above, and the degrees of §10 (the website README's *10. Degrees three to six*), whose
monomorphizations are about thirty kilobytes of it.
Beside `engine.wasm`'s 785,424 / 231,149 that is 25% more raw and 34% more gzipped, and it
buys a renderer for everything below 1e-10, on both of the sets `z^d + c` has at each degree
from two to six. It is large for a dependency-free crate of
1,500 lines, and the reason is `core::fmt`: `plan` formats a JSON report and every
refusal is a sentence. That is an attribution from what the module contains rather
than a measurement by subtraction, and if the tab wants the bytes back that is
where to look. There is no `serde`, no `serde_json` and no engine in it.

*(deep_seam_move_ckpt163.)* The sizes above are the module's when this section was
written, and a manifest no longer carries them: today's two modules, `perturb.wasm` and
`perturb-scalar.wasm`, and what each weighs are the website README's *Committed:
`perturb.wasm`*.

**9,423 of those bytes were the skip table**, and they came back when it did —
the module was 122,098 raw and 56,147 gzipped while the table was in it, for a
code path that was off by default and that no page could set. §6 is the ruling.

### 5. Pictures

`scratch/perturb-ladder.png` — the anchor, then a `c = i` ladder from 1e-2 to
1e-28, coloured by a percentile stretch and a plain gradient. Not committed;
`scratch/` is ignored, and the sheet is for Matt's eye rather than for a page.

### 6. The skip table, and why it is not here

Bivariate linear approximation — one entry standing for a run of `2^k` steps as
`δ ← A·δ + B·dc`, read out of a table built off the reference orbit — was built,
priced twice, and taken back out. What follows is what it cost to find out, kept
because the seam comment in `kernel.rs` will give somebody the same idea and this
is the only thing that should talk them out of it.

**The ruling stands for this crate, and one other path reopens the question for itself
alone.** `fractal-website/explorer/deep-gpu-model` models the WebGPU kernel the Deep tab draws its full
passes with, in `f32` and in double-single, where the picture already moves by its own
rounding, so it carries a skip table behind a switch that is off by default and holds it to
agreeing with this crate's `f64` kernel no worse than the model does without it. Its
`README.md` has that argument and the measurements; the shipped kernel is double-single
with no skip table (`fractal-website/explorer/README.md`, "The GPU draws the full pass where it has earned
it"). Nothing here changes: `perturb.wasm` draws the plain loop, and everything below still
stands for it.

**Measured 2026-09-20**, tiles of 64×36, the plain loop and the skipping loop the
same spec and the same orbit, alternated. `ε` is the share of a linear step the
dropped quadratic term is allowed to be; `2⁻⁵³` is the tightest tolerance the
approximation admits, since below it the dropped term is asked to be under the
last bit of the term beside it.

**On the anchor's own ladder it looked like an order of magnitude and more.** The
headline rows, single thread, interior switch off:

| frame | cap | interior | ε = 2⁻⁵³ | 1e-12 | 1e-9 | 1e-6 |
|---|--:|--:|--:|--:|--:|--:|
| mandelbrot 2e-11 | 48,551 | 38.9% | 0.59× | 0.59× | 0.60× | 0.88× |
| julia 2e-10 | 44,565 | 89.3% | 2.32× | 2.52× | 2.93× | 4.69× |
| mandelbrot 1e-22 | 93,600 | 100% | 1.08× | **59.08×** | 59.11× | 59.51× |
| mandelbrot 1e-28 | 117,518 | 100% | **59.19×** | 58.93× | 58.78× | 60.08× |

⚠ **And every Mandelbrot rung of that ladder below the minibrot's own 6.5e-12
atom is inside its body and 100% interior** — the deepest frame either ladder
carries with exterior in it is `julia 2e-10` — so the depth at which the skip paid
and the depth at which its accuracy had been checked did not overlap. The second round closed that
gap the only way it could be closed — by going and finding deep frames that have
something in them. They are the seven in `tests/common`, and on them the 59× is
**between a 21% loss and 2.6×**:

| frame | plain wait | ε = 2⁻⁵³ | 1e-12 | 1e-9 | counts moved @1e-12 | @2⁻⁵³ | mask moved @2⁻⁵³ |
|---|--:|--:|--:|--:|--:|--:|--:|
| tangle 1e-22 | 197 s | 0.64× | **1.00×** | 1.38× | 76 | 24 | 0 |
| tangle 1e-28 | 244 s | 0.98× | **1.38×** | 2.19× | 161 | 56 | 0 |
| pinch 1e-28 | 241 s | 0.96× | **1.21×** | 1.49× | 213 | 78 | 1 |
| tangle 1e-40 | 363 s | 1.38× | **1.72×** | 2.45× | 127 | 45 | 0 |
| tangle 1e-54 | 480 s | 1.92× | **2.58×** | 3.49× | 113 | 39 | 0 |
| body 1e-22 | 786 s | 0.58× | **0.79×** | 1.22× | 372 | 190 | **15** |
| body 1e-28 | 1,049 s | 0.87× | **1.15×** | 1.84× | 371 | 174 | **20** |

At each frame's own cap, the interior switch **on** because that is what ships.
The wait is the tab's own fine pass, derived as `1,859,584 lanes × mean iterations
× ns × 1.05 / 4.7` — the canvas `fractal-website/explorer/README.md` measures on, wasm's 5% over
native from §4, and the pool's effective parallelism.

Three findings, and together they are the ruling.

**The 59× was a property of having no exterior in the frame.** An interior sample
sits by the reference and never rebases, so a run of 2,048 is available to it at
every index; an escaping sample wanders off and rebases, and the runs the table
can offer it are short. The plain loop's own rebase is also the hard ceiling on a
run — no entry may be built whose run reaches the index the loop rebases at — and
a **periodic reference is refused a table outright**, because the kernel's wrap
assigns `m = 0` rather than `m % length` and a table indexed on an absolute orbit
index has nothing to say about an index that wraps. Put structure in a frame and
the speedup falls by a factor of twenty to sixty. The `body` pair was expected to
be the skip's best case and is its worst: 44% of `body 1e-22` runs 374,400
iterations without escaping, which is exactly the shape a skip table wants, and
the table can still only skip 12.7% of the frame's iterations at `2⁻⁵³` against
22% to 73% on the tangle frames. Those long samples do not stay by the reference;
they rebase.

**And there is no tolerance at which nothing moves.** Walked from 1e-12 down
through nine tolerances to `2⁻⁵³`, every frame moved escape counts at every one of
them — 24 to 190 at the floor, while still skipping 13% to 73% of the iterations.
On the `body` pair the **interior mask itself moves at the floor**: 8 escaping
samples painted interior and 7 let escape on `body 1e-22`, 8 and 12 on `body
1e-28`, with a worst error of 35,000 and 11,700 smooth counts. That is the one
thing this crate has never let an approximation touch, and there is nothing below
`2⁻⁵³` to try. The differentials are the same kernel against itself on the same
orbit, differing only by the skip, so a moved count is the skip's and not the
frame's own chaos.

**The seam costs 70% on every iteration it does not skip.** The `2⁻⁵³` rows at
2e-11 and 1e-16 are 0% skipped and run at 0.59×, which is the lookup alone — an
alignment mask, a bounds-checked index into the table and a radius compare,
against a loop body of about ten flops.

So the skip buys 1.0× to 2.6× on the frames a reader opens, rising with depth, in
exchange for a picture that is no longer the one the plain loop draws — and this
crate's whole argument, from §1 through §3, is that it draws what the engine
draws. What would have to change for it to come back is not code but the bar.
Taking it out returned **9,423 bytes raw and 3,363 gzipped** — 8.4% and 6.4% of
what the module weighs without it, paid until then by every reader who opened the
Deep tab, for a path nothing on the page could reach.

**The frames stay**, because they are the only deep frames this project has that
are not one flat colour. `fractal-website/explorer/perturb-wasm/tests/descend.rs` is how
they were got: from the
anchor's minibrot at 1e-11, render a 64×64 tile at the policy cap, recentre on the
busiest boundary neighbourhood it offers, shrink the width tenfold, repeat. **The
centre is an exact decimal the whole way**, which the square tile is what makes
possible — the sample step is `width/64` on both axes, so a recentre is
`(2·col − 63)·78125·10^−(7+p)`, integer addition rather than a double that ran out
of bits twenty rungs up. Three routes, because the first two agreed too well:
`tangle` takes the most boundary crossings in a 5×5, `pinch` the deepest escaping
sample beside a bounded one, and `body` walks every rung at four times the policy
cap, which is what it takes to see a frame with genuine interior in it. Neither of
the first two backtracked once.

| frame | cap | escaped | `dv` link, after `explorer/?` |
|---|--:|--:|:--|
| tangle 1e-22 | 93,600 | 69.5% | `dv=2&x=-0.745017728290198619298817365858&y=0.149934432756897045833502403382&w=1e-22&n=93600` |
| tangle 1e-28 | 117,518 | 80.9% | `dv=2&x=-0.74501772829019861929877929889763684&y=0.14993443275689704583350282968726721&w=1e-28&n=117518` |
| pinch 1e-28 | 117,518 | 82.5% | `dv=2&x=-0.74501772828897655304632685480388684&y=0.14993443275858764694789167606226721&w=1e-28&n=117518` |
| tangle 1e-40 | 165,354 | 74.9% | `dv=2&x=-0.7450177282901986192987792989188510315333046875&y=0.1499344327568970458335028296517884911675546875&w=1e-40&n=165354` |
| tangle 1e-54 | 221,162 | 71.3% | `dv=2&x=-0.745017728290198619298779298918851031533262270733325571484375&y=0.149934432756897045833502829651788491167588360989048041953125&w=1e-54&n=221162` |
| body 1e-22 | **374,400** | 55.7% | `dv=2&x=-0.745017728288852579046129865858&y=0.149934432757626550615361778382&w=1e-22&n=374400` |
| body 1e-28 | **470,072** | 78.9% | `dv=2&x=-0.74501772828885257904614927236638684&y=0.14993443275762655061538134007789221&w=1e-28&n=470072` |

All seven parse and round-trip byte for byte through `fractal-website/explorer/deep-link.js`, and
a cheap test in `tests/frames.rs` holds every centre to the characters a
coordinate is capped at and every cap to the policy's or the stated multiple of it
— the two ways a committed frame goes quietly wrong without rendering anything.
**The deepest is 1e-54 because of the link and not the renderer**: a rung costs
about five seconds a tile there and the descent was still going down, but a centre
is 63 characters at that width and `COORDINATE_LIMIT` was 64 when it was chosen.
Since gpu_deep_ship_ckpt162 the deep cap is its own, 128 characters (`deep-fx.js`'s
120-digit `MAX_SCALE` and eight), so a link spells a frame down to about 1e-112; the
seven frames stay as they were chosen.

⚠ **And they found something that is not about the skip at all: at these depths
the policy cap paints exterior as interior.** This is the open problem the section
leaves behind, and it is the most consequential thing in it.
`fractal-website/explorer/perturb-wasm/tests/measure.rs`'s `what_a_deeper_cap_resolves` is the evidence, at 32×18, each
rung a multiple of the width's own **policy** cap:

| frame | at the policy cap | 2× | 4× | 8× |
|---|--:|--:|--:|--:|
| tangle 1e-22 | 29.3% unresolved | 0.2% | 0.0% | 0.0% |
| tangle 1e-28 | 21.0% | 0.0% | 0.0% | 0.0% |
| pinch 1e-28 | 16.5% | 0.0% | 0.0% | 0.0% |
| tangle 1e-40 | 22.7% | 0.0% | 0.0% | 0.0% |
| tangle 1e-54 | 27.4% | 0.0% | 0.0% | 0.0% |
| body 1e-22 | **100%** | 100% | 43.6% | 1.7% |
| body 1e-28 | **100%** | 100% | 21.5% | 0.2% |

On the five tangle and pinch frames a sixth to a third of the picture is
unresolved at the cap the tab would use, and **at twice that cap every one of them
is 100% escaping** for about 2% more mean iterations: those samples were never
interior, they were exterior the cap stopped a few thousand short. The `body` pair
is the same fault four times over — at the policy cap they are a **flat interior
fill**, over escape counts that run from about 100,000 to 400,000. The policy's cap
lands inside the frame's own escape-count distribution, and what a reader sees is
the shortfall painted as set. **The policy moved, and §8 is where** — these seven
frames and six controls beside them are what it was argued on.

**Not one sample of any of the seven is *proven* interior.** The switch needs
`|dz|²` under `2⁻⁶⁴`, which takes many periods of whatever component a sample is
in, and at this depth the nearby periods are of the order of the cap itself.

### 7. The interior switch's rule, and why it cannot be a width rule

| frame | proven interior | plain: off → on |
|---|--:|--:|
| anchor 2e-11 | 1.3% | +11% |
| anchor 1e-11 | 4.8% | +13% |
| anchor 8e-12 | 7.4% | +14% |
| anchor 6.5e-12 | 11.5% | +13% |
| anchor 5e-12 | 19.1% | +9% |
| **anchor 3e-12** | 56.7% | **−3%** |
| anchor 2e-12 | 89.8% | **−17%** |
| anchor 1e-12 | 100% | −43% |
| anchor 1e-13 | 100% | −72% |
| anchor 1e-16 | 100% | −91% |
| anchor 1e-22 | 100% | −97% |
| anchor 1e-28 | 100% | −97% |
| the seven deep frames | 0% | +9% to +12% |

**The crossing is at 3e-12**, where two runs of this table gave +4% and −3% — so
that rung is the crossing to within what the measurement can say, at about **half
to two thirds proven interior**. The minibrot's own atom, 6.5e-12, is *not* the
crossing: a frame is still 13% slower there. Below it the return deepens with the
frame, because what the switch waits for is `|dz|` to fall and a sample further
inside the body falls faster.

⚠ **But `anchor 1e-22` is −97% and `tangle 1e-22` is +12%.** Same width, opposite
verdicts, and the same again at 1e-28. **There is no width at which to turn the
switch on or off**: what it pays on is what the frame contains, which is not
something a link, a policy or a worker knows before the frame has been drawn. It
ships on, at −64, and on the frames a reader actually opens it costs 9% to 12%. A
width rule was the thing this section set out to write, and the table is the
reason there is not one.

#### In wasm the switch is dearer, and the page now chooses it per frame *(profiling_pass_ckpt146, 2026-09-24)*

The 9% above is native. **In the committed module the same switch costs the loop about
half its speed where it does not fire**: at 240×135, alternated, lanes identical both
ways, off ran in 0.50 to 0.73 of the time on did — `tangle 1e-22` 55.1 s against 28.3,
`body 1e-22` 56.6 against 31.4, the anchor at 2e-11 15.6 against 8.9, and even
`anchor 3e-12`, 100% interior, 28.7 against 19.4. Only `anchor 1e-12` came out even
(18.8 against 19.6), and the table above says the return deepens below it. Making the
flag a const parameter, one monomorphized loop per setting, bought nothing measurable,
so the price is the tracking itself and not the branch.

The table's conclusion still holds — no width says which way to set it — but the frame
itself does, once a sixteenth of it has been drawn. `compute_band` now leaves two
numbers behind, read by `band_ran()` and `band_saved()`: the iterations the band ran,
and the iterations the switch spared it (the cap less the step it stopped at, over the
samples it stopped). `ran + saved` is exactly what the plain loop would have run, so
the quarter pass, drawn with the switch on, prices the full pass both ways, and
`deep.js`'s `switchFor` turns it off where `ran + saved < 1.4 × ran`. **No pixel moves
either way** — a stopped sample is one the plain loop runs to the cap, and both write
`NaN` — and 1.4 is the cheap end of the measured price, so a frame near the crossing
keeps the setting the kernel ships. A download uses the screen's quarter pass of the
same frame when it is still held.

### 8. The cap a frame asks for *(deep_cap_policy_ckpt138, 2026-09-20)*

§6's open problem, closed. **The cap is no longer the width's answer alone: a frame
is asked what it needs, and the answer is the frame's.** `src/policy.rs` is the
rule, `fractal-website/explorer/perturb-wasm/tests/measure.rs` is the evidence, and the page drives it a rung at a time
through `probe_band`.

**A width rule was never available**, and §7 had already said why about the
interior switch: `anchor 1e-22` is 100% *proven* interior at the policy cap and
`tangle 1e-22` is 29% cap-starved at the same width and the same cap. What a frame
needs depends on what it contains. So the policy is **self-escalation** — start at
the width's cap, look at what died there, double while the frame is still dying for
want of iterations, stop at the ceiling.

#### The three ways a sample ends `NaN`, and the one that is a fault

The hard half is not the escalation, it is knowing when to stop. **The share of a
frame that dies unproven says nothing on its own.** It is 100% on `body 1e-22` at
both the policy cap and twice it, where the frame is exterior the cap has not
reached; and it is 38% on `anchor 2e-11`, where the frame is the minibrot's own
body — interior the switch cannot prove, because the period is 2,838 and only
seventeen of them fit inside the cap. One number, opposite pictures, and a rule
that read it would multiply the anchor's wait by twenty for nothing.

What separates them is **`|dz|` where the sample stopped**. `Outcome` now hands out
the switch's own mantissa and exponent rather than only comparing them — two field
stores at a sample's exit, nothing added to the loop — and
`Outcome::dz_log2` is what the policy reads. So a `NaN` sample is one of:

- **proven interior** — the switch fired, `|dz|²` fell under `2^-64`. A deeper cap
  confirms it and changes nothing.
- **on its way there** — no proof, but `|dz|` is small and collapsing. Black is
  already the right colour.
- **the cap's fault** — `|dz|` has grown past the escape radius. The map is
  expanding hard here, nothing is settling into anything, and the only reason the
  sample is black is that the loop ran out.

`FAULT_EXPONENT` is that bar: **`log₂|dz|² > 16`, which is `|dz|² > 65,536`, the
escape radius.** Measured at the policy cap, 32×18, over the frames that have to be
told apart — and it is two orders of magnitude of daylight:

| frame | unproven at the policy cap | `log₂\|dz\|²` of those: min / median / max |
|---|--:|--:|
| tangle 1e-22 | 29.3% | 87 / 123 / 157 |
| tangle 1e-28 | 21.0% | 128 / 175 / 211 |
| tangle 1e-40 | 22.7% | 225 / 261 / 364 |
| pinch 1e-28 | 16.5% | 141 / 179 / 233 |
| tangle 1e-54 | 27.4% | 317 / 356 / 404 |
| body 1e-22 | 100% | 27 / 27 / 27 |
| body 1e-28 | 100% | 25 / 25 / 25 |
| **anchor 2e-11** | **37.8%** | **−59 / −3 / 162** |

The `body` pair is the reason the bar is 16 and not 32: at the policy cap their
whole frame sits at 27, which is above the escape radius and below `2^32`. The
anchor is the reason it is not 0.

#### Where it settles, and what it costs

`FAULT_SHARE` is **a tenth**: the smallest share that has to escalate is
`pinch 1e-28` at 17% and the largest that must not is the anchor at 5%.
`where_the_policy_settles`, on the 1136×636 canvas at the fine pass's supersample,
probing 64×36 of that grid — so these are the numbers the page takes:

| frame | policy cap | settled | × | the cap's fault, rung by rung | mean iterations | repainted | deciding |
|---|--:|--:|--:|:--|--:|--:|--:|
| tangle 1e-22 | 93,600 | **187,200** | 2× | 29.4% → 0.2% | 89,230 → 92,524 | **29.2%** | 0.16% |
| tangle 1e-28 | 117,518 | **235,036** | 2× | 19.7% → 0.3% | 109,808 → 112,855 | **19.5%** | 0.16% |
| tangle 1e-40 | 165,354 | **330,708** | 2× | 24.8% → 0.0% | 159,892 → 162,529 | **24.8%** | 0.16% |
| pinch 1e-28 | 117,518 | **235,036** | 2× | 17.2% → 0.1% | 108,488 → 110,471 | **17.1%** | 0.16% |
| tangle 1e-54 | 221,162 | **442,324** | 2× | 28.1% → 0.0% | 215,594 → 219,587 | **28.0%** | 0.16% |
| body 1e-22 | 93,600 | **748,800** | 8× | 100% → 100% → 44.1% → 2.2% | 93,600 → 398,834 | **97.8%** | 0.21% |
| body 1e-28 | 117,518 | **940,144** | 8× | 100% → 100% → 20.9% → 0.1% | 117,518 → 470,687 | **99.9%** | 0.22% |
| anchor 2e-11 | 48,551 | 48,551 | 1× | 5.3% | 32,383 | 0.0% | 0.08% |
| anchor 1e-22 | 93,600 | 93,600 | 1× | 0.0% | 2,838 | 0.0% | 0.08% |
| misiurewicz 1e-22 | 93,600 | 93,600 | 1× | 0.0% | 68 | 0.0% | 0.08% |
| home 3 | 4,000 | 4,000 | 1× | 0.0% | 107 | 0.0% | 0.08% |
| seahorse 1e-6 | 29,819 | 29,819 | 1× | 0.0% | 169 | 0.0% | 0.08% |
| julia anchor 2e-9 | 40,578 | 40,578 | 1× | 1.9% | 12,677 | 0.0% | 0.08% |

**`repainted` is the whole point**: the share of the frame that was painted as set
at the width's cap and escapes at the settled one. A sixth to a third of each
tangle, effectively the whole of each `body` — they were flat black fills over
escape counts running to 400,000 — and **nothing at all on any of the six
controls**, which is the other half of the requirement and was the harder half to
meet.

**Five of the seven settle at twice the cap for 2% to 3.7% more mean iterations**,
which is §6's own finding turned into a policy. The `body` pair costs four times
the work, and that is what it costs to draw a frame the old cap could not see into
at all.

**Deciding costs 0.08% to 0.22% of the fine pass it decides for**, because the
probe is 2,304 of the frame's own sample cells — about a thousandth of one pass —
at the frame's own limb count, through the frame's own geometry. So the
supersampled pass runs **once**, at the settled cap. Nothing about the decision is
an approximation of the thing decided; only the number of samples is smaller.

#### The bar and the share are on a plateau

`the_bar_and_the_share_sit_on_a_plateau` walks every rung of all thirteen frames
and reads it twenty-five ways: five bars from 8 to 24, five shares from 5% to 15%.
**Twenty-two of the twenty-five give the same thirteen answers.** The three that
differ are all share = 5%, at bars 8, 12 and 16, and all move one frame —
`anchor 2e-11` — by one doubling. Neither number is quoted to a second digit
because neither deserves one.

#### What is not decided here

**A pinned cap is drawn as pinned.** Escalation is the *policy*, so it runs where
the width's answer is in force and nowhere else: a cap a reader typed, and a cap a
link carries, are drawn exactly as asked. That distinction already existed on the
page as `pinnedCap` and needed no new control.

**And a frame can run out of ceiling.** The walk stops at `cap::AUTOMATIC_CEILING`,
a million, and `Settled::at_ceiling` says the frame is still the cap's fault there.
None of the thirteen reaches it. What a page does with that is a sentence, not a
retry.

#### Two ceilings *(Matt, cap_split_ckpt145, 2026-09-23)*

There was one ceiling, `cap::CEILING`, and there are two now, each spelled once:

- **`cap::AUTOMATIC_CEILING`, 1,000,000**: every cap the explorer chooses by itself.
  That is `cap::for_width`'s clamp, `policy::next_cap` and `policy::settle` (this walk),
  and the wrapper's `nuclei::tile_cap`, since a preview tile is drawn unasked. It is the old ruling
  unchanged, and `plan` reports it as `ceiling`.
- **`cap::EXPLICIT_CEILING`, 2,000,000**: every cap somebody asks for on purpose. That is
  the wrapper's `nuclei::open_cap`, the link contracts' `n` (`CAP_LIMIT` in `permalink.js`), Halve and
  Double and a typed cap on the page, and the builder's pinned `period × periods`
  (`deep_gallery.py`, `descent.py`). `plan` reports it as `explicit_ceiling`, and
  `deep.test.mjs` holds `CAP_LIMIT` to it.

`next_cap` of a cap already past the automatic ceiling returns that cap: the probe never
lowers a cap somebody asked for, and never raises one either.

What bounds the explicit one is the reference orbit's memory. It is sixteen bytes a point,
**one copy per worker**, and a wasm heap never gives memory back. Measured on the
committed module: 15.3 MiB at 1e6 and 30.5 MiB at 2e6 per worker it is fed to, twice
that in the worker that computes it, about 550 MiB for the whole pool at sixteen workers
and 2e6. `fractal-website/explorer/README.md` *Two ceilings* has the table and where a browser tab would
start to be at risk.

## Running it

From this directory:

```text
cargo fmt   --check                                  # rustfmt-clean, and held there
cargo clippy --all-targets -- -D warnings
cargo test  --release                                # the unit tests, frames, interior,
                                                     #   orbit_parity and parity; parity.rs
                                                     #   runs 1.95 G sample-iterations,
                                                     #   which is why this is --release
cargo test  --release --test oracle -- --ignored --nocapture   # the ladders, ~30 s
cargo check --target wasm32-unknown-unknown          # the scalar build
RUSTFLAGS="-C target-feature=+simd128" cargo check --target wasm32-unknown-unknown
                                                     # the SIMD build: the one that
                                                     #   compiles src/lanes.rs at all
PARITY_RECORD=1 cargo test --release --test parity   # re-record the pins (rarely right)
```

**The pins are native bytes.** `tests/parity-pins.txt` was recorded natively, on Windows,
and holds every lane, counter and `Outcome` a spec produces. So a pin holds whole on
Windows, and on another operating system, whose C runtime may take `ln` from another
library, only in what no `ln` reaches: the label, the two counters, which are iteration
counts, and `shape`, every sample's count, rebases and flags. The comparisons made inside one run — a band cut in two, a list against a band —
are exact everywhere. Wasm takes `ln` from another library than native does too, so the
modules are held to their predecessors instead, by the website's
`explorer/bench/perturb-parity.mjs` over this crate's `tests/parity-specs.jsonl`.

**What an edit here owes the website.** `perturb.wasm` and `perturb-scalar.wasm` are
committed there and built from this directory, and the website's builder refuses to build
them from a kernel that is not the tree its engine manifest pins. So a change here is
gated before it is committed and finished in three steps after:

0. In the website, build candidate modules from the uncommitted kernel —
   `python -c "from builder import explorer; explorer.build_perturb(pinned=False)"`, the
   one way past the pin check, which writes no manifest — and hold them to the committed
   modules (saved first with `git show HEAD:explorer/perturb.wasm`) with
   `explorer/bench/perturb-parity.mjs`. A red here is fixed before anything is committed.
1. Commit it in this repository.
2. In the website, `python -m builder explorer`: it rebuilds `engine.wasm` and writes this
   commit into `engine.manifest.json` as `wallpapers_commit`, the one pin for all three
   modules.
3. Then `python -m builder explorer --perturb`, which rebuilds both perturbation modules
   and `perturb.manifest.json`, and hold the result to the modules it replaces with
   `node explorer/bench/perturb-parity.mjs <old.wasm> <new.wasm>`: every spec's orbit,
   bands, band cuts, listed samples and counters, byte for byte. These are the modules the
   website commits, so this second run is the gate that counts.
