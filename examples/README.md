# examples

The four thumbnails the root `README.md` shows at the top. Nothing reads them but that
page, and each one there links to its view in the live explorer.

Each is rendered through the engine at 1920x1080, supersample 2, and scaled to 480x270
(Lanczos; JPEG quality 82, progressive, 4:2:0). They are the only binary files this
repository tracks, and `tests/test_history_purity.py`'s `ALLOWLIST` carries the reason
and the bound.

| file | seat | family | mode | colormap |
| --- | --- | --- | --- | --- |
| `mandelbrot_stripe.jpg` | `460117ee` | mandelbrot | `stripe` | cmr.jungle |
| `phoenix_threads.jpg` | `0275fee1` | phoenix | `threads` | Sapphire Against Rose |
| `julia_multibrot4_smooth.jpg` | — (a link) | julia (multibrot4) | `smooth` | glowdon, phase 0.053 |
| `julia_multibrot3_threads.jpg` | `5ff0ad6b` | julia (multibrot3) | `threads` | Cobalt Furnace Ultra |

## The one that is a link

`julia_multibrot4_smooth.jpg` is not a gallery seat. It is this explorer view, and it is
here so a reader can open the same picture there:

```
https://techmatt.github.io/fractals/explorer/index.html?v=4&f=julia4&cx=0.44637678855595264&cy=0.6581861161102234&x=-0.0006944498037232774&y=-0.007170259608518661&w=0.644829668143998&p=glowdon&phase=0.053
```

The link leaves out `m`, `level` and every shade key but `phase`, so it takes the
explorer's defaults (`permalink.js`): mode `smooth`, no autolevel curve, and the engine's
default palette recipe with only the phase moved — which is `engine_spec.recipe(phase=…)`
exactly. The cap is the engine's depth policy in both places. The render spec is
`curation.pins.parse` of the link with those defaults and no autolevel; `render` has no
flag for a palette phase, so it goes to `engine.render_report` as a spec rather than
through the command line. It was written as `v=3`, and is spelled `v=4` now because that
is what the explorer rewrites it to on arrival: nothing a smooth-mode view says changed
between the two, and `render-link` draws both to the same pixels.

## The three that are seats

To draw any of them at full size, which is what these were scaled down from:

```
fractal-wallpapers curate solve recipes --write --stamp 20260922T012627Z
fractal-wallpapers render \
  --recipe artifacts/curation/tentative/20260922T012627Z/recipes.jsonl \
  --key <seat> --out artifacts/example.jpg
```

**On a clone the second line is enough.** These three seats were cut from
`20260914T171846Z`, which went with every other saved record on 2026-09-21. All three
keys are also seats of `final139_general` above, which was **published on 2026-09-29**
with its `recipes.jsonl` tracked, so a clone with no ledger draws them from the tracked
file. The first line rebuilds that file out of the candidate ledger, and only the machine
that holds the ledger can run it. The keys are unchanged; only the stamp that resolves
them is.

Each seat's link in the root README is `curation.explorer_link.query_of` of the seat's
recipe, with the tone curve its run or `autolevel_backfill.jsonl` recorded: the link the
embedded stamps carry and the site's gallery row for the seat carries, byte for byte.
**Never `pins.query_of`**, which is a writer for authoring pins and drops `mirror`, the
`level` curve and a mode's parameters. The strip carried its spelling until 2026-09-28, and
`mandelbrot_stripe.jpg`, whose palette has `mirror: true`, opened in the un-mirrored map.
The site's `builder check` runs a `readmes` check that holds every link in this README to
parsing as its own canonical spelling, and each seat's to the contract's link for its
recipe, reading the `seat` column above.

Replacing one is two steps and neither is optional: redraw and rescale the picture here,
and repoint the `<img>` and its link in the root README. A file added or renamed also moves the
`ALLOWLIST` entry, which is what makes a fifth picture a decision rather than a copy.

A fourth seat, `julia_smooth.jpg` (`2fd9890d`, julia (mandelbrot), `smooth`, glowdon),
left the strip on 2026-09-23 on Matt's call. Its pin in `data/curation/pins.txt` stays,
because a pin is a seating decision and not a README one.
