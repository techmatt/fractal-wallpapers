# Checking the library

`style sweep --out <dir>` is the checker after an engine or stack change: every style
small at its keeps, each public knob at both ends and each palette entry, flagged per
`style_sweep.FLAGS`, a contact sheet per style; it exits 1 on any flag. Read the sheets
too: the flag is a symptom. What hunts found is
`docs/qa-findings.md`. A `slow` flag is a timing: re-run it on an idle box. To tell a new
flag from an old one, sweep also through the engine built from the commit before (a
worktree's `cargo build`, `FRACTAL_ENGINE=<worktree>/engine/target/release/fractal-engine`
set for the run: `engine.ENGINE_ENV`) and compare bytes.

A sweep's seats are distinct places: a keep at a place an earlier keep took (a later
round's lever at its seat) is passed over for the next.

**The page's palette switch**: `style wasm-parity --recolour [names]` measures each published
mode's default entry at its first shown place, recolours it to every other kept entry and
tiles it, against a plain module frame of that entry (96x60 ss2, module only: 67 switches
in 32 s on three workers, quiet box, 085). Each switch reads `identical`, or
`refused` where the entry moves what the frame gathered (a stir's `steps`, a trap's
`largest`, a layer switched on from opacity 0), which the page meets by measuring afresh;
anything else exits 1. A mode with a post stage is drawn whole and never recoloured.

**Explorer cost** is the module's time for one frame. **`style cost <name>...`** reads it
as the bar is set: the published stack and map at each style's deepest kept seat (highest
`maxiter`, ties to the keep record's first; `--seat <name>` for another kept seat), one 1280x800 ss2 frame as WebAssembly on one thread,
printed against Matt's 5-minute bar (`style_wasm.COST_BAR_SECONDS`), rows in `cost.jsonl`.
`--workers 3` reads three styles at once (the render pool's count, never more); read it
idle, as every time here. A round-one mode has no kept seat and no shown one: give it
one with `--location <record>`. A mode already known to be over (a whole frame held a
worker 20+ minutes in 080) reads with `--shrink 4`: a quarter of each side, the time
scaled by 16, the row's `read_seconds` what it took; so does one clearly over (a seat at
`maxiter` 10k or more): never a whole frame first, and Node reads count against the
three-worker pool as engines do. What drives cost is interior share times `maxiter`
(096: ~100 s native at a 28%-interior seat at 11,946, 7-40 s elsewhere), so wasm ranks
do not predict a native plan. Deepest is not always dearest: dew_bloom
takes 21 s at its own deepest seat and about 260 s at `POST_SEAT`, whose interior runs
every sample to the cap. Before it, `style wasm-parity <name>` writes
each job's `wasm_seconds` (one thread, 640x400 ss2) to `parity.jsonl` and `seconds.json`
in its folder; 1280x800 is about four times that. Read it on an idle box. A round-one style
(no keep) draws at `style_wasm.POST_SEAT` (a Mandelbrot frame at maxiter 2000); its own
deeper seats cost more. To
scale from a native render there, `native_seconds` is the engine on
`style_wasm.PARITY_NATIVE_THREADS` (three), not one thread: compare thread-seconds.

**Pickers** (manifest, pictures, renders sidecar) live in `artifacts/pickers/<name>/`,
never under `experiments/` (excluded here) or `out/`: `style keep` reads them there.
`style render --location` reads a file: a bash `<(...)` substitution is no path on
Windows, so write the record under `out/<item>/` first. A Python printing repo text
(`·`, `λ`, curly quotes) on this box sets `PYTHONIOENCODING=utf-8` (cp1252 console).
