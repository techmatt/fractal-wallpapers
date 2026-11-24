# Checking the library

`style sweep --out <dir>` is the checker after an engine or stack change: every style
small at its keeps, each public knob at both ends and each palette entry, flagged per
`style_sweep.FLAGS`, a contact sheet per style; it exits 1 on any flag. Read the sheets
too: the flag is a symptom. What hunts found is
`docs/qa-findings.md`. A `slow` flag is a timing: re-run it on an idle box. To tell a new
flag from an old one, sweep also through the engine built from the commit before (a
worktree's `cargo build`, `engine.engine_path` pointed at its binary) and compare bytes.

**Explorer cost** is the module's time for one frame: `style wasm-parity <name>` writes
each job's `wasm_seconds` (one thread, 640x400 ss2) to `parity.jsonl` and `seconds.json`
in its folder; 1280x800 is about four times that. Read it on an idle box. A round-one style
(no keep) draws at `style_wasm.POST_SEAT` (a Mandelbrot frame at maxiter 2000); its own
deeper seats cost more. To
scale from a native render there, `native_seconds` is the engine on
`style_wasm.PARITY_NATIVE_THREADS` (three), not one thread: compare thread-seconds.
