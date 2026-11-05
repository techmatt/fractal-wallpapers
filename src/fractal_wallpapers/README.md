The package that steers the renderer: find places, color them, judge the results.

## Two roots, and the second one has two tiers

`paths.py` defines every place this package addresses files in; nothing else builds one.

* **`repo_root()`**: the checkout, everything git keeps.
* **`hot_root()`** and **`archive_root()`**: the regenerable tree (caches, views, a
  study's pictures; ~100 GB) across two disks, set in an untracked `local.toml` at the
  repository root or by `FRACTAL_WALLPAPERS_HOT_ROOT` / `FRACTAL_WALLPAPERS_ARCHIVE_ROOT`
  (which override the file; the empty string asserts no such root). Hot defaults to
  `artifacts/` in the checkout; archive to nothing. The retired `artifacts_root` /
  `FRACTAL_WALLPAPERS_ARTIFACTS_ROOT` is **refused, not ignored**. Keep hot on an SSD.

```toml
# local.toml, untracked, at the repository root
hot_root = "<ssd>:/fractal-wallpapers/artifacts"          # omit for artifacts/ in the checkout
archive_root = "<bulk disk>:/fractal-wallpapers/artifacts"  # omit if this machine has one disk
```

A top-level name is in exactly one tier, and its tier is where its files are (no
registry). Writes land hot; reads resolve hot, then archive.

* **`under(*parts)`**: a path on whichever tier holds its subtree (neither: hot).
* **`Tiers`**: a snapshot that reads settings and tiers once, for loops.
* **A pool picture is the one name answered per file.** `curation` never leaves hot, but
  its unkept candidate JPEGs live in an archive mirror,
  `pool_pictures/<group>/<leg>/pictures/<file>` (`storage pictures archive`, then
  `storage pictures prune-hot --apply`). Records still name `artifacts/curation/...`;
  `Tiers.resolve` answers hot or mirror, `Tiers.in_place` the hot spelling for a writer.
  With the archive unplugged kept seats still resolve and any other missing picture raises
  `ArchiveUnreachable`, so a pool read never silently shrinks. `paths.py`'s *The one name
  finer than a top-level name* and `picture_mirror.py` have the rest.

Three `StorageRefusal`s, caught once by `cli.main`: `ArtifactsRootMissing` (a configured
root absent; never a fallback to the checkout), `ArchiveUnreachable`, `TierCollision` (one
name in both tiers). Trainers (`head train`, `renders train`, `palette train`) refuse a
cache on the archive (`storage.require_hot`) and name the restore command.

```
fractal-wallpapers storage status              # every subtree, its tier, its size
fractal-wallpapers storage archive tiles       # hot -> archive
fractal-wallpapers storage restore tiles       # archive -> hot
```

`storage.py` alone moves tiers (copy, verify, delete). Records name tree files through **`tracked_name(path)`** (checkout-relative, or
`artifacts/<rest>` on either tier, so a ledger's name, which keys curation's sidecar rows,
survives archiving) and read them back through **`rehome(stored, tiers=None)`** (takes
`artifacts/<rest>` or an absolute path; `None` for one outside any artifacts tree).
Guard: `tests/test_storage_tiers.py`.

- **Hand `tiers` in on any loop over a store**: ~1.8 ms a row bare, <10 µs with
  `Tiers.current()` taken once above the loop.
- **Never build a tree path as a bare `Path("artifacts") / …`**: it follows the shell's
  working directory, not the hot root. Use `under()` or `cli.resolve_output`; a
  module-level location is an accessor *function* (`carriers.recolour_dir()`,
  `decisions.figure_dir()`), since a constant would fix the tier at import time. An
  argparse default `"artifacts/..."` is fine: `resolve_output` rehomes it.
- **No tracked record carries a drive letter**:
  `tests/test_history_purity.py::test_no_absolute_paths_in_tracked_records`, one exemption
  (`acceptance.json`'s `prereg`). The read-only extraction source is
  `models.acceptance.beside(relative)`, `repo_root().parent / relative`, absent when not
  there; that is why its numbers are vendored.

## The standing keep roster

CLAUDE.md's *hot* / *archive* / *delete* rule says where a name lives; this lists what is
**kept** on any tier. The only sweep that deletes a candidate, `curate candidate-ledger
orphans`, reaches only `<tier>/curation/<subtree>/<leg>/pictures`
([`candidate_ledger.sweep.picture_dirs`](curation/candidate_ledger/sweep.py)); everything
here but `.leveled/` is outside that shape, and kept by this list, not a mechanism.

| what | why it is kept |
|---|---|
| `artifacts/curation/candidate_ledger/` | the pool: rows, scores, flatness and reduced-signature sidecars |
| the ten `durability.Durable`s | below |
| `artifacts/curation/neutral_embeddings.jsonl` | the gallery pass's distance |
| the hot copies under `artifacts/curation/` | it never leaves hot ([`curation/README.md`](curation/README.md)'s *The archive tier*); kept seats' pictures stay hot |
| `data/curation/{release,gate}/` | the live decisions, half of `orphans`' reference set |
| `artifacts/reframe_g1` … `g12` | the reframing ledgers (no `g3`), read by `discovered_priors` |
| `artifacts/curation/tentative/<stamp>/` | the records `tentative.kept()` names (`PUBLISHED` plus the keep file), the whole input to `tentative.protected_keys()`. All twenty-one saved records are published |
| `artifacts/curation/tentative/20260922T012627Z/` | `final139_general`: `tentative.DEFAULT`, `curation.backfill.DEFAULT_RECORD`, `fractal-website`'s general collection |
| `artifacts/curation/tentative/20260922T220551Z/` | `final140_general2000`; re-seat: `curate solve record --n 2000 --solve-name final140_general2000` |
| `artifacts/curation/viewer/` | **the page a person opens**, `tentative.viewer_dir()`: `curate solve browse <stamp> --viewer`, per collection `curate solve viewers`. No stamp in its name, so bookmarks survive; unstamped it shows `final139_general`. A derivation reaching pictures by relative path |
| `artifacts/curation/tentative/keep.jsonl` | the keep list's unpublished half (`solve record` / `solve release`; last row per stamp wins) |
| `artifacts/votes/` | vote kits |
| `artifacts/curation/growth/20260902T150756Z/` | a fixed series' rung |
| `data/coloring/texture_flat.jsonl` | old rows' flat-texture register |
| `data/spiral/`, `models/spiral/` | spiral probe |
| `models/render/` | `weights-v6`, `render.v5.fp16.pt`, the runs bars were read on |
| `models/gallery_grade/` | the fine head, k=3 members |
| `artifacts/gallery_grade_head/pool_scores.jsonl` | the cascade **refuses** without it |
| `artifacts/render_folds/` | render arms' folds; below |
| `artifacts/top_slice_probe/` | probe |
| `artifacts/gallery_grade/n1000_0906/*/plan.jsonl` | rebuilds those levelled pictures |
| `data/curation/candidate_ledger/ratchet.jsonl` | append-only; the census asserts on it |
| `artifacts/curation/gallery/` | retired gate attempt rows; [`curation/README.md`](curation/README.md)'s *The 53 MB of attempt rows under `artifacts/curation/gallery/` is KEPT* |

Reader pages (`artifacts/judges/`, `candidate_page/`, `trace/<stamp>/`,
`artifacts/walkthrough/`, a harvest's `stats/`) are derivations, rebuilt by one command.

- **The ten unmerged `runs/` legs are not garbage.** `orphans` lists them under
  `unmerged`, but every picture is named by a live store (`store_named` ≥ `pictures`,
  `would_delete: 0`), through `rescore.origin_of`'s chain. Deleting them is Matt's call.
- **The ten Durables**, under `artifacts/curation/`: `supply_scores.jsonl`,
  `score_amendments.jsonl`, `hunt/frames.jsonl` (these three are `durables.guarded()`;
  `curate run` refuses without them, and `frames.jsonl` has no rebuild), the ledger's rows
  and scores, the flatness and reduced-signature sidecars, the neutral embeddings, the
  spiral scores and the palette colour-mass sweep log.
- **`.leveled/` is the exception**: inside `pictures/`, so `orphans` takes the unnamed
  ones; [`curation/LEGS.md`](curation/LEGS.md)'s *A `.leveled/` directory is swept only
  with its own picture, and a prune is still structurally safe*.
- ⚠ **`artifacts/render_folds/` is on neither tier**: `render_folds.read_assignment`
  refuses, so `renders dose`, `grade`, `deploy` refuse until it is re-derived.

## Continuing on a fresh box: `storage export` and `storage import`

[`portable.ROSTER`](portable.py) is what a fresh clone needs to **continue every stage**
(the Durables, every walk ledger, each leg's `sequence.jsonl` and `depth.json`, the kept
records' text, pool scores, the colour census, label sheets' text, the `labels/` inbox, the
gallery-grade arm's three `best.pt`; ~4 GiB). Its manifest is `portable.json`.

**An export is Matt's backup, taken only at his direction**; the local instance is deleted
at once, and no tracked text names an export.

```
fractal-wallpapers storage export --to <an empty directory>
fractal-wallpapers storage import --from <path to the backup> --root <hot root> [--archive-root <archive>]
fractal-wallpapers curate candidate-ledger re-render --keys <a gallery.jsonl>   # one known solve, minutes
fractal-wallpapers curate candidate-ledger re-render --seatable   # then any solve can run
fractal-wallpapers curate candidate-ledger re-render --rest        # whenever; no seating needs it
```

- **Pictures do not travel; the fresh box re-renders** (`--seatable` is ~3 days at three
  workers). `solve.pool` refuses an absent JPEG (`picture_absent`). The export writes
  `pictures.jsonl` (sha256 per seatable candidate, `same_build`/`unknown_build`) to check
  the re-render; `--no-pictures` skips it, and nothing else reads it.
- **`--keys <gallery.jsonl>` first**, then compare `curate solve run … --no-render` with
  the record. Each export's `reference/README.md` names the two checks:
  `portable.REFERENCE` (`final139_green`, `--collection green`, n=300) and
  `portable.GENERAL_CHECK` (`final139_general`, `--n 1000`); export refuses without them.
- **Import** checks size and sha256 per file, refuses unlisted files and existing
  destinations, writes through a temporary. `--from A --from B` merges a split export.
  Without `--archive-root` all lands under `--root`. To test a restore on the same box,
  point `portable.repo_root` at scratch first (`tests/test_portable.py`'s `box` fixture).
- **A leg mined there returns** by `curate mine package` / `unpack`.
- **`fractal_wallpapers` is a namespace package**: in a `git worktree`, drop the live
  `src` from `sys.path` (a `sitecustomize.py` on `PYTHONPATH`) or both checkouts merge.

**Before the import**: `uv sync --extra dev --extra models --extra solve` (`cuda` for
`models` to train), `fetch-weights`, `cargo build --release`, a `local.toml`. On Windows,
if `rustup show` is not MSVC, `cargo +stable-x86_64-pc-windows-msvc build --release
--manifest-path engine/Cargo.toml`; write paths `<drive>:/...`, not `/c/...`. **Read the
engine fingerprint in the import's output**: `amend.read` keeps only rows drawn by the
running build, so a differing build must re-derive amendments with `curate redraw`.

Of the untracked weights beside the heads, only the gallery-grade arm's three `best.pt`
are opened by a production verb (`rotation.score_fine`), so only they travel.

## One shape for a place, and one reader for it

**`locations.py` is the only reader of a location** (`family`, `viewport` as decimal
strings, `render`), behind `render --location`, `render --manifest`, `screen` and
`score-locations`. Four spellings:

```text
{"family": ..., "viewport": ..., "render": {...}}    a label row
{"family": ..., "viewport": ..., "maxiter": 13140}   a walk ledger's candidate
{"location": {"family": ..., "viewport": ...}, ...}  a release decision row
{"family": ..., "viewport": ..., "mode": ..., ...}   a scoring corpus row
```

Family and viewport are required; an absent `maxiter` means the depth policy decides; a
member given two values is refused. Reading accepts any row; the refusal of what this shape
cannot carry (a curve, fold, palette pass, trap settings, levelling band) is at the
**render door**, which sends you to `render --recipe FILE --key <seat>`.

**Batch forms take a manifest file, never a list of paths** ([`CLAUDE.md`](../../CLAUDE.md)).
Batch pictures are `<row>_<digest>.png` (a digest of everything the engine was told, so a
batch resumes); `renders.jsonl` joins them back.

## Which engine build drew a picture

`engine.py` is the one door; `engine_spec.spec_of` builds the spec;
`engine_fingerprint.py` names the build by **what it draws** (six pinned probes through
`spec_of`, sixteen hex characters, ~0.35 s cached per process), which catches a rebuild of
unchanged source and a moved mode catalog. Each view directory's `drawn_by.jsonl`
(`{schema, view, engine}`, last row wins) claims its pictures; an unclaimed view is
`unknown`, so `location_view.render_view` redraws it, and `curate redraw` re-reads them.

### Two things never to do to `renders.job_name`, and both have bitten

⚠ **Never pin a `job_name` digest in a test.** `spec_of` writes `paths.colormap_dir()`
into the spec as an absolute path, so the digest differs per machine (why
`candidate_ledger` drops `colormap_dir` from the recipe key). Assert two rows agree or
differ. A re-clone renames every cached picture; moving the hot root renames nothing; a
catalog edit re-keys nothing (`renders.SPEC_MEMBERS` carries `mode` and `mode_params`), and
only the fingerprint catches it.

⚠ **Never patch `renders.colormap_dir`.** `spec_of` reads `engine_spec.colormap_dir`;
patching the re-export silently tests the real checkout.

## A record's prose has one copy in the source and a whole copy on every row

Beside `reachable` is `reachable_is`: a sentence saying what the number and `null` mean.
**A row read years later off the archive still says what it ran under, with no
checkout.** The prose is a module-level **`SCHEMA_NOTES: dict[str, str]` beside the
module's `SCHEMA`**, read at write time; the finished sentence goes on the row.

- *Not a pointer*: a row never carries a note key for a checkout to resolve. Do not
  re-propose it.
- *Not versioned*: a note true when written is correct about its row. A note *wrong when
  written* gets a line below.
- *Not a rewrite*: two spellings of one field stay as `<field>.<which>` (`solve.py`'s
  `group_cap_is.shipped` / `.named`) until someone reconciles them.

A note naming a runtime number is a `str.format` template formatted at the site.
`tests/test_schema_notes.py` refuses prose `*_is` at a record site, a lookup naming no
note, and an unread note.

### Notes corrected after they shipped

The whole list: rows before the date carry a **wrong** sentence.

* **2026-09-12, `depth.SCHEMA_NOTES["not_admitted_is"]`**: rows under `4e2533c` say band
  2's lost places were *all* `julia:mandelbrot`; 14 of 168 were, across ten partitions,
  166 with no supply-sidecar row.
* **2026-09-12, `gallery_grade_train.SCHEMA_NOTES["held_out_is"]`** and
  `bar_<band>.json`'s `population.is`: *optimistic by one early stop* should be three
  choices (epoch, arm, seed), so `models/gallery_grade/`'s `metrics.json` files and three
  bars understate optimism by two; the numbers stand.
