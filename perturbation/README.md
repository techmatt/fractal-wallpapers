# perturbation — `z^d + c` below the `f64` floor

The picture core of the explorer's Deep tab: the smooth field of `z^d + c` (Multibrot at integer
degrees two to six, and the Julia set of any `c` at each) by **perturbation with rebasing**, at
widths the `f64` engine cannot draw, one `f64` lane a sample. No UI and no exports of its own.
Taken by path, never copied, by `fractal-engine` (its default `deep` feature, how `render-link`
draws a `dv=` link), by the website's `explorer/perturb-wasm` (the `extern "C"` exports `plan`,
`compute_band`, `probe_band`, `reference_orbit`, `newton_step`; built to `perturb.wasm`, SIMD,
and `perturb-scalar.wasm`) and by its `explorer/deep-gpu-model`. The website pins its modules by
one commit of this repository, `engine.manifest.json`'s `wallpapers_commit`.

**The fractal-website repo cites this file's numbered headings by number and text: do not rename
or renumber them.** §9–§12 are in `fractal-website/explorer/perturb-wasm/README.md` (*9. The
minibrots in and around a view*, *10. Degrees three to six*, *11. The dive*, *12. Copy or bulb,
by the root*), beside the minibrot search, the Dive, the GPU path and the JavaScript. A
`fractal-website/` path is that checkout; a `scratch/` path is untracked.

**The two sets are one kernel and one reference orbit**: `Z₀ = 0, Z₁ = c, …` is the critical
orbit of `c`, and also the Julia orbit of `z = 0` and, shifted by one, of `z = c`. The loops
differ only in the entry index and whether `dc` is spent every step or once. The crate has **no
dependencies**, not even dev-dependencies.

```text
src/fx.rs              fixed-point reals, n × u64 limbs, written for wasm32
src/reference.rs       one high-precision orbit per frame, projected to f64
src/kernel.rs          the per-sample f64 delta loop, with rebasing
src/lanes.rs           the same loop two samples a vector, wasm SIMD builds only
src/policy.rs          the cap a frame asks for (§8)
src/json.rs            a reader for one flat JSON object (the spec)
src/progress.rs        a wasm build's one import, env.progress
src/lib.rs             the spec, anchors, the width's cap, compute_rows, compute_rows_counted
                       (a Band with its own counters, the engine's entry point), compute_listed,
                       pack_reference, unpack_reference, band_ran, band_saved
smooth-cases.json      the engine's own samples, as the pin
tests/oracle.rs        the kernel against a brute-force oracle (ignored by default)
tests/parity.rs        every bit out, pinned per spec: parity-specs.jsonl → parity-pins.txt
tests/orbit_parity.rs  every byte of the packed reference orbit, pinned
tests/interior.rs      the interior switch never paints an escaping sample black (§3)
tests/common/          the seven deep frames (§6), six controls, and the shared sample walk
                       (matching policy::probe_rows); the website's harnesses #[path] it
tests/frames.rs        the frames are still spellable and at the cap they claim
```

## The design, in one page

- **The reference orbit is fixed point; everything per-sample is `f64`.** One orbit a frame.
- **Limbs come from the view**: `ceil(log2(samples across / width)) + 64` guard bits (three limbs
  at 2e-11, four at 1e-28); a Julia frame anchored at `z = 0` multiplies the view's bits by `d`
  (`reference::limbs_pow`, §2b). The bailout check precedes the precision: fixed point overflows
  silently.
- **`δ' = (2·Z[m] + δ)·δ + dc`, rebasing Zhuoran's**: when `|z| < |δ|` or the orbit runs out,
  `δ := z`, `m := 0` — the whole glitch handling. It needs `Z₀ = 0`, which is why there is no
  second reference. Julia spends `dc` once, as the opening delta; `JULIA` is a const generic
  because `x + 0.0` is not `x` at `-0.0`.
- **Two anchors, both orbit points**: `z = c` (index 1) and `z = 0` (index 0). `delta_ulps`
  refuses a frame too far from its anchor (`DELTA_ULPS = 4.0`, the engine's rule asked of the
  delta). `dc` is a fixed-point centre difference, never `f64(centre) − f64(reference)`.
- **A named period makes the reference periodic**: the index wraps and nothing rebases.
- **The cap is the frame's own (§8)**, starting at `cap::for_width` (the engine's shape, ceiling
  `cap::AUTOMATIC_CEILING`). **There is no skip table (§6).**

### What it does not do

Integer degrees two to six, `smooth`, both planes, nothing else (§10). Closed, not pending: a
fractional degree (`(Z+δ)^α − Z^α` fails on that family's branch-cut seam) and Phoenix (a second
delta lane and a two-point reference).

## What the engine needed

**Nothing**; the engine depends on this crate, never the reverse. The engine's private
`iterate::smooth_count` is restated in `src/kernel.rs`, and two pins hold the copy to it:
`smooth-cases.json` (field samples plus `(escape step, |z|², smooth)` triples, which hold
exactly, recorded on one machine) runs from this crate alone, and the engine's
`the_deep_kernels_smooth_count_is_this_one` (under its `deep` feature) runs the two side by side,
bit for bit, at degrees two to six on any platform.

## Proof

The anchor is a **period-2838 minibrot nucleus in the seahorse valley** (atom 6.478e-12),
`-0.74501772828532335842941892835857434 + 0.14993443275456819177805709088257971i`, width
**2e-11**: cap 48,551, 38.9% interior.

### 1. Against `f64`, where `f64` still draws

At the anchor the kernel and `iterate::run` disagree (median 61 iterations, none bit-equal):
fidelity fails above the coordinate wall. Against a 384-bit oracle on 311 escaping samples, the
kernel is nearer the truth on 307.

### 2. Against a brute-force oracle, below the wall

`tests/oracle.rs` iterates each sample directly in fixed point. The ladder is **`c = i`**
(Misiurewicz: exact, on the boundary, self-similar), since below its atom the anchor is all
interior. From 1e-4 to 1e-28 every sample agrees on escaping and the **median difference is
exactly zero**. On the anchor ladder the interior masks never disagree; the median relative error
is 3.5e-11 (the suite holds the median; the worst is boundary chaos). A named period removes
rebasing.

### 2b. The Julia case, against the same oracle

`c = i`'s Julia set, both anchors, 1e-4 to 1e-28: median Δ 0. At `z = 0` neighbours differ by the
*square* of the spacing, so the oracle doubles its limbs and the kernel's orbit uses
`reference::limbs_pow`; `the_origin_anchor_holds_a_non_dyadic_c_to_the_squared_step` is the test
that sees it. `plan` refuses a frame sixteen limbs cannot hold. The Douady rabbit is held to
`engine.wasm`'s own Julia render by `fractal-website/explorer/deep.test.mjs`.

### 2c. A reference somewhere else in the frame

Off its own centre or a parent's, a frame matches the oracle equally well but not byte for byte,
so the page keeps an orbit only where a fresh load would compute it (`sameOrbit`,
`fractal-website/explorer/deep-render.js`): determinism, not accuracy.

### 3. The interior switch

`dz_n = ∏ 2·z_k` is carried as a mantissa in `[1, 2^64)` and a power-of-two exponent.
`|dz|² < 2^INTERIOR_EXPONENT` (−64) is a **gate, not a proof**: `Kernel::prove` continues the
loop and stops a sample only when **a disc about its orbit maps into itself** (radius carried
exactly by `(|z| + ρ)^d − |z|^d`, four radii, small margins). Beside a parabolic point it never
closes, where a bare threshold painted exterior black. Ships **on** (`SHIPS_INTERIOR`). The
anchor's floor sweep, 96×54:

| floor | −120 | −64 | −32 | −16 | −8 | −4 |
|---|--:|--:|--:|--:|--:|--:|
| caught of 2,019 interior | 4 | 66 | 272 | 616 | 988 | 1,293 |
| wrongly painted | 0 | 0 | 0 | 0 | 0 | 0 |

No escaping sample on any frame tried (parabolic, Siegel, the GPU model's corpus) is painted
interior, and escaping counts are bit-identical to the switch off.

### 4. Price

Native at the anchor: the engine's loop 4.68 ns a sample-iteration, this one **4.80** (5.24
with the switch); wasm 5.04 and 6.59. Julia is ~20% cheaper. The orbit is 6.3 ms native, 11.2 ms
wasm. Speed comes from one interleaved `[re, im]` orbit array with `Z[m]` carried across the
step, and `Fx::mul` specialized per limb count (bit-identical by its own test). Module sizes are
the website README's *Committed: `perturb.wasm`*.

### 5. Pictures

`scratch/perturb-ladder.png` (the anchor and the `c = i` ladder), untracked, for Matt's eye.

### 6. The skip table, and why it is not here

Bivariate linear approximation (`δ ← A·δ + B·dc` over `2^k` steps) was built and taken out: its
59× held only on all-interior frames; on the seven deep frames it is a 21% loss to 2.6×, and **it
moves escape counts at every tolerance down to `2⁻⁵³`** (and the mask on `body`). A periodic
orbit cannot take one. The bar would have to change, not the code; the GPU model's own table is
its own ruling.

The seven frames, from `fractal-website/explorer/perturb-wasm/tests/descend.rs`:

| frame | escaped | `dv` link, after `explorer/?` |
|---|--:|:--|
| tangle 1e-22 | 69.5% | `dv=2&x=-0.745017728290198619298817365858&y=0.149934432756897045833502403382&w=1e-22&n=93600` |
| tangle 1e-28 | 80.9% | `dv=2&x=-0.74501772829019861929877929889763684&y=0.14993443275689704583350282968726721&w=1e-28&n=117518` |
| pinch 1e-28 | 82.5% | `dv=2&x=-0.74501772828897655304632685480388684&y=0.14993443275858764694789167606226721&w=1e-28&n=117518` |
| tangle 1e-40 | 74.9% | `dv=2&x=-0.7450177282901986192987792989188510315333046875&y=0.1499344327568970458335028296517884911675546875&w=1e-40&n=165354` |
| tangle 1e-54 | 71.3% | `dv=2&x=-0.745017728290198619298779298918851031533262270733325571484375&y=0.149934432756897045833502829651788491167588360989048041953125&w=1e-54&n=221162` |
| body 1e-22 | 55.7% | `dv=2&x=-0.745017728288852579046129865858&y=0.149934432757626550615361778382&w=1e-22&n=374400` |
| body 1e-28 | 78.9% | `dv=2&x=-0.74501772828885257904614927236638684&y=0.14993443275762655061538134007789221&w=1e-28&n=470072` |

At the width's cap a sixth to a third of each (all of `body`) is exterior painted as set: §8.

### 7. The interior switch's rule, and why it cannot be a width rule

On the anchor the switch loses above about 3e-12 and wins more the deeper (−97% at 1e-22); on
the seven deep frames it costs 9%–12%. `anchor 1e-22` and `tangle 1e-22` take opposite verdicts
at one width: what it pays on is what the frame contains.

#### In wasm the switch is dearer, and the page now chooses it per frame

It costs about half the loop's speed where it does not fire, so the frame decides:
`band_ran()` and `band_saved()` price the full pass both ways from the quarter pass, and
`deep.js`'s `switchFor` turns it off where `ran + saved < 1.4 × ran`. No pixel moves either way.

### 8. The cap a frame asks for

`src/policy.rs`, driven by the page through `probe_band`: **start at the width's cap, double
while the frame is still dying for want of iterations, stop at the ceiling.** The probe is 64×36
of the frame's own cells (under 0.25% of the fine pass), so the full pass runs once.

A `NaN` sample is proven interior, on its way, or **the cap's fault**: `|dz|` past the escape
radius (`Outcome::dz_log2`). `FAULT_EXPONENT` is `log₂|dz|² > 16`, `FAULT_SHARE` a tenth; at the
width's cap the tangle frames read 87 and up, `body` 25–27, the anchor −59 to 162 (median −3).
The five tangle/pinch frames settle at 2× and `body` at 8×; none of the six controls moves, and
22 of 25 bar/share pairs give the same answers (`the_bar_and_the_share_sit_on_a_plateau`). A
pinned cap (typed, or a link's `n`) is drawn as pinned; `Settled::at_ceiling` says a frame ran
out.

**Two ceilings**, each spelled once:

- **`cap::AUTOMATIC_CEILING`, 1,000,000**: caps the explorer chooses (`cap::for_width`,
  `policy::next_cap`, `policy::settle`, `nuclei::tile_cap`); `plan`'s `ceiling`.
- **`cap::EXPLICIT_CEILING`, 2,000,000**: caps asked for (`nuclei::open_cap`, `permalink.js`'s
  `CAP_LIMIT`, held by `deep.test.mjs`, Halve/Double, a typed cap, builder-pinned caps);
  `plan`'s `explicit_ceiling`. Bounded by orbit memory, sixteen bytes a point per worker (the
  page's side is the "Two cap ceilings" bullet of `fractal-website/explorer/README.md`).

`next_cap` past the automatic ceiling returns its input.

## Running it

From this directory:

```text
cargo fmt   --check                                  # rustfmt-clean, and held there
cargo clippy --all-targets -- -D warnings
cargo test  --release                                # unit tests, frames, interior,
                                                     #   orbit_parity, parity (1.95 G
                                                     #   sample-iterations: --release)
cargo test  --release --test oracle -- --ignored --nocapture   # the ladders, ~30 s
cargo check --target wasm32-unknown-unknown          # the scalar build
RUSTFLAGS="-C target-feature=+simd128" cargo check --target wasm32-unknown-unknown
                                                     # the SIMD build (src/lanes.rs)
PARITY_RECORD=1 cargo test --release --test parity   # re-record the pins (rarely right)
```

**The pins are native Windows bytes.** On another OS, whose `ln` may differ, `tests/parity-pins.txt`
holds only what no `ln` reaches (label, counters, `shape`); in-run comparisons are exact
everywhere. Wasm modules are held to their predecessors by the website's
`explorer/bench/perturb-parity.mjs` over `tests/parity-specs.jsonl`.

**What an edit here owes the website.** It commits `perturb.wasm` and `perturb-scalar.wasm`
built from this directory, and its builder refuses a kernel that is not the pinned tree:

0. In the website, build candidates from the uncommitted kernel —
   `python -c "from builder import explorer; explorer.build_perturb(pinned=False)"`, the one way
   past the pin check, writing no manifest — and hold them to the committed modules (saved first
   with `git show HEAD:explorer/perturb.wasm`) with `explorer/bench/perturb-parity.mjs`. Fix a
   red before committing anything.
1. Commit it in this repository.
2. In the website, `python -m builder explorer`: rebuilds `engine.wasm` and writes this commit
   into `engine.manifest.json` as `wallpapers_commit`, the one pin for all three modules.
3. Then `python -m builder explorer --perturb` (both perturbation modules and
   `perturb.manifest.json`), held to the modules it replaces with
   `node explorer/bench/perturb-parity.mjs <old.wasm> <new.wasm>`: every orbit, band, band cut,
   listed sample and counter, byte for byte. This second run is the gate that counts.
