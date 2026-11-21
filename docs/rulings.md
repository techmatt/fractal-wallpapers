# Standing rulings

Matt's rulings for this repository that outlive the item they were made in. An executor
reads this beside `CLAUDE.md`; changing one is his call. Each keeps the wording it was
given in, with its date and the item it came from.

## Styles and custom modes

- **The fractal feel is the goal of every style** (2026-11-05/06): a render should promise
  more detail if you zoomed in, and read as the fractal's own structure. Large shapes
  never occlude the finer scales into a finite set of objects (018's blades); a few
  frame-filling lines with no tie to the set fail even when they match the reference
  (032's wisps).
- **A custom mode is a stack plus a palette set** (2026-11-07, 038): styles whose stacks
  match up to palette and numeric values are one mode, each palette carrying its tuned
  values; only palettes with a kept tile are saved; a new reference whose stack fits an
  existing mode becomes a palette entry (`palettes add --mode`).
- **Styles may post-process** (Matt, 2026-11-19): image-space passes with neighbour reads
  are allowed as a separate post stage (layers stay per-sample); post-processed modes go
  to Mandelnaut too, with explorer extensions as needed, never wallpaper-only.
- Lighting is a style layer only, never a catalog mode; the mode catalog and `de` stay
  unlit (Matt, 2026-11-04).
- Custom modes never use deep zoom (Matt, 2026-11-05).
- Custom modes reach the browser as this pipeline's own style compositor compiled to
  WebAssembly, checked for parity against the keeps; a GPU shader is a later speed-up only
  (2026-11-05).
- **The stroke trap keeps its `steps` cap** (Matt, 2026-11-20; 061-063's audit).
- **The post stage's explorer side waits** until a post-stage look leaves lab (Matt,
  2026-11-20; 061-063's audit).
- New modes enter the lab tier; Matt promotes modes out of lab himself (2026-11-19).
- **A round-one style gets a catalog row at once** (Matt, 2026-11-19; 059's audit):
  `style_catalog.check` accepts an unscored row with no status, so its references stop
  reading as untried in `style refs --unused`.
- **A round-one picker holds about twenty tiles** (Matt, 2026-11-19; 059's audit):
  formulations at one seat and the best four at a second, plus locations.

## Palettes and tone

- The tone pass measures the block-averaged picture, not the samples (Matt, 2026-11-04;
  012). `style tones` reads pictures at 640 wide in sRGB.
- `groups.jsonl` admits new maps incrementally (nearest group within the cut, else a new
  group; no existing id moves), never a full re-cut (2026-11-04; 012).

## Checks and docs

- **No wording or prose checks** (Matt, 2026-11-13; removed by 051): checks cover
  structure and data only, and none is to be added back. A prose pass runs only when a
  prompt asks for one.
- **15 KB (15,000 bytes) is the standing bar for the style docs** (Matt, 2026-11-19;
  059's audit): the post stage and the stir leave `STACK.md` for `data/styles/POST.md`;
  `style sweep` leaves `README.md` for `data/styles/CHECKS.md` (064). `FORMATS.md` is
  exempt (Matt, 2026-11-19; 060): the bar is for the style docs, and it stays whole at
  about 16.5 KB, its bytes being field names `tests/test_formats.py` requires. No split.
  `CLAUDE.md` is exempt as `FORMATS.md` is (Matt, 2026-11-20; 064's audit): the bar is
  15,000 bytes for the style docs alone.
- `CLAUDE.md` cleanup picks standing (2026-11-04): the build-era section stays until
  publication, and the lane rules stay in `CLAUDE.md`.
- The memory note `final-statement-ends-with-report-filename` (Matt, 2026-11-19; 059's
  audit): keep the drive copy of the report, drop its last-line rule (conductor's "Report
  written to <path>" stands).

## The website and zoom videos

- A website item never commits into this repo; an engine change the website needs is its
  own item here.
- Zoom videos use non-flowing colouring (fixed escape-count → colour); `knee` mapping is
  the default; final zoom renders raise the iteration cap.
