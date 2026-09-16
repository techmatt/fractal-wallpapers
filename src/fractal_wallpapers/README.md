The package that steers the renderer: find locations, color them, judge the results.

## Two roots, and the second one has two tiers

`paths.py` defines every place this package addresses files in, and nothing else
builds one for itself.

* **`repo_root()`** — the checkout. Records, labels, weights, code: everything
  that matters and everything git keeps.
* **`hot_root()`** and **`archive_root()`** — the regenerable tree, across two
  disks. Tile caches, location views, render caches, a study's pictures: around a
  hundred gigabytes, and therefore a *setting*. `hot_root` and `archive_root` in
  an untracked `local.toml` at the repository root, or
  `FRACTAL_WALLPAPERS_HOT_ROOT` / `FRACTAL_WALLPAPERS_ARCHIVE_ROOT` in the
  environment. Hot defaults to `artifacts/` inside the checkout, which is what CI
  and a fresh clone get; archive defaults to nothing at all. The single key this
  pair replaced — `artifacts_root`, and `FRACTAL_WALLPAPERS_ARTIFACTS_ROOT` — is
  **refused rather than ignored**: a machine still spelling it meant to put the
  tree somewhere, and reading nothing would send its next build to the checkout,
  which is the silent fallback `ArtifactsRootMissing` exists to prevent arriving
  through the settings file instead of through an unplugged disk.

A top-level name of the tree is in exactly one tier, and its tier is where its
files are — no registry, so nothing to drift. Everything asks through one funnel:

* **`under(*parts)`** — a path inside the tree, on whichever tier holds its
  subtree. Hot first, archive fallback, and a name in neither resolves hot
  because that is where a thing that does not exist yet gets made. `tile_dir()`,
  `view_dir()`, `cache_dir()` and the rest are all one line of this.
* **`Tiers`** — a snapshot, for a caller resolving a million rows at once: it
  reads the settings and each subtree's tier once instead of once per row.

Three refusals, all subclasses of `StorageRefusal`, which `cli.main` catches once
for every subcommand because each is about the machine rather than about a
command's flags: `ArtifactsRootMissing` for a configured root that is not there,
`ArchiveUnreachable` for a name only the unplugged archive could have answered
for, `TierCollision` for one name in both tiers. See the
[top-level README](../../README.md#putting-the-regenerable-tree-on-another-disk)
for why each refuses rather than falls back.

`storage.py` is the only thing that changes any of those answers: `move` copies a
subtree to the other tier, verifies it three ways and only then deletes the
source, `status` says where everything is, and `require_hot` is the refusal the
trainers make when their cache is on slow storage. A move copies *files*, and a
directory holding none is copied by `mirror_empty_directories` rather than by the
copy — the structural check counts directories, so a run that never released
would otherwise fail a verification in which every file was present, after paying
for the whole copy.

Because the tree moves and subtrees change tier, a record that names a file under
it is written and read through one pair of functions:

* **`tracked_name(path)`** on the way out — a file in the checkout is named
  relative to it, and a file under either tier is named `artifacts/<rest>`. This
  is not cosmetic, and the tier-independence is the point. A walk ledger's name
  is the key curation's sidecar stores each scored row under, so a name that
  changed when the subtree was archived would leave every stored row unmatchable
  and a re-score would pile duplicates beside the rows it meant to replace.
* **`rehome(stored, tiers=None)`** on the way in — a stored name re-addressed
  against wherever that subtree is now. It takes both spellings a record can
  carry, the relative `artifacts/<rest>` and one machine's absolute path, and
  returns `None` for a path that names nothing under an artifacts tree, so the
  caller keeps its own bytes rather than having them re-spelled.

The one hot user is `models/tiles.read_manifest`, which re-homes the path on
every row of a manifest the engine wrote — a million of them — taking one `Tiers`
snapshot for the whole file so the tier of `artifacts/tiles` is decided once
rather than stat-ed on two disks a million times.
`tests/test_storage_tiers.py` is the guard over all of it.

**Hand `tiers` in on any loop over a store, and it is not a micro-optimization.**
Measured on this machine 2026-09-06 through `flatness.missing` over 20,000 ledger
rows: **1,777 µs a row bare against 8.6 µs with the tiers handed in**, which over
the candidate ledger's 308,419 rows is **548 s against 2.7 s**. The loop is correct
either way and simply sits there — it cost one killed pass during the ckpt-112
promotion sweep before anybody looked. Resolve `Tiers.current()` **once above the
loop**. The passes that do are `candidate_ledger.delete_pictures`,
`candidate_ledger.rerender`'s job build and its rescore chunking,
`flatness.missing`, `signatures.missing`, `curation.rules.clouds_for`,
`curation.pool_draw.units_for`, `curation.tentative.page`, `curation.intake`'s
scoring pass, and `curate distinct`'s two `picture_of` closures. What is
deliberately left per-call is a **single** resolution — `cli.common.anchored`,
`curation.binding.anchored` — and the per-card resolutions in the HTML sheets
(`hunt._card`, `mine._card`, `solve`'s release frame), where the call already opens
a JPEG to make a thumbnail and the resolution is not what the card costs.

**Two places used to build a tree path without asking**, found by
`AUDIT_artifacts_inventory` and closed on 2026-09-02: `palettes/carriers.py`'s
`RECOLOUR_DIR` and `models/decisions.py`'s `FIGURE` were both a bare
`Path("artifacts") / …`, joined directly rather than passed through `under()` or
`cli.resolve_output`. They were relative to the *shell's* working directory, so on
a machine that has moved its hot root they wrote to a fourth place that was
neither tier — and that failure is silent, because a regenerable subtree in the
wrong place looks exactly like one nothing has built yet. Both are now accessor
functions, `carriers.recolour_dir()` and `decisions.figure_dir()`, resolving
through `under()`; they are **functions and not constants** because `under()`
reads which tier the subtree is on and a constant would have to answer that at
import time. `tests/test_storage_tiers.py` pins both in the consumer list and
asserts a `chdir` cannot move either answer. Everything else that looks
hard-coded is an argparse **default string** — `resolve_output` puts those
through `rehome`, which is what makes the literal `"artifacts"` in them
load-bearing rather than a leak.

**Censusing the tree is cheap and worth doing.** A metadata-only walk of the hot
tier — 403,088 files, 102 GiB on 2026-09-02 — takes under thirty seconds on this
machine with `os.scandir` and no `stat` beyond size and mtime. `git status` over
the same tree is 90–108 ms, and `-uno` is no faster, so the tracked hole in
`.gitignore` is not making git descend expensively. The tool that this tree *is*
expensive for is anything walking the checkout without honouring `.gitignore`.

**Every tracked record goes out through `tracked_name`, including the ones that
name a file the tree does not hold.** A summary's `run_dir`, a metrics record's
checkpoints, a price table's source runs: all of them are read back on a machine
that is not the one that wrote them, so none of them may carry a drive letter.
`tests/test_history_purity.py::test_no_absolute_paths_in_tracked_records` walks
every tracked `.json` and `.jsonl` and fails on one, with a single exemption —
the `prereg` key of a head's `acceptance.json`, which names a pre-registration by
absolute path and is left alone deliberately. A path that leaves the checkout
entirely, like the extraction source's colormap pool, is named by *what* it is
rather than where it sat: `the source project's data/palettes/pool_colormaps.json`.

The read-only extraction source is the one thing outside the checkout that code
still has to *open*, and it is addressed **relative to this checkout** rather
than by an absolute path: `models.acceptance.beside(relative)` is
`repo_root().parent / relative`, so a sibling clone is found wherever the pair
was put and is simply absent afterwards. That absence is the reason the numbers
it reads are vendored — a bar has to stay re-readable without that repository.

## The standing keep roster

CLAUDE.md's three-way rule — *hot*, *archive*, *delete* — decides where a subtree
lives, once per subtree. This is the other list: the paths that are **kept**
whichever tier they are on, each with the one-line reason. It lives here rather
than in [`curation/README.md`](curation/README.md) because it names top-level tree
names, tracked stores and `models/` alike, and the unit of the three-way rule is a
top-level name, which is this section's subject.

**Almost none of it is protected by a mechanism, and that is the thing to
understand before reading the list.** The only sweep that deletes a candidate is
`curate candidate-ledger orphans`, and
[`candidate_ledger.sweep.picture_dirs`](curation/candidate_ledger/sweep.py)
enumerates `<tier>/curation/<subtree>/<leg>/pictures` — `store.POOL_SUBTREES`,
`store.PICTURES_NAME`, a fixed shape at a fixed depth — and nothing else.
Everything on this list bar the last two entries is outside that shape entirely,
so it is not *exempted* from the sweep, it is **unreachable** by it. What keeps it
is a ruling, and a ruling is only as good as the place it is written down.

| what | why it is kept |
|---|---|
| `artifacts/curation/candidate_ledger/` | the pool itself: `rows.jsonl`, `scores.jsonl`, and the flatness and reduced-signature sidecars |
| the ten `durability.Durable`s | see below — every one of them is under `artifacts/curation/`, and three are what a run refuses to start without |
| `artifacts/curation/neutral_embeddings.jsonl` | one neutral-render vector per admitted location; the gallery pass needs a distance |
| the hot copies under `artifacts/curation/` | `artifacts/curation/` never leaves the hot tier — see [`curation/README.md`](curation/README.md)'s *The archive tier* |
| the tracked release and gate stores, `data/curation/{release,gate}/` | the live decisions, and half of `orphans`' reference set |
| `artifacts/reframe_g1` … `g10` | the reframing chain's ledgers — nine legs, there is no `g3`. `discovered_priors` reads every one as a prior, so losing a leg is re-finding its atoms |
| `artifacts/curation/tentative/<stamp>/` | **the records `tentative.kept()` names**, published or not — `PUBLISHED` plus `KEPT_UNPUBLISHED`. Since 2026-09-13 that list is the whole input to `tentative.protected_keys()`; before it the sweep was store-wide, so a record merely existing pinned its seats and deleting it was the only release. An off-list record is still readable by naming its stamp and pins nothing. The next two rows are inside this one and named anyway: neither is in `tentative.PUBLISHED`, both are in `KEPT_UNPUBLISHED`, and each is a hard dependency cited by name somewhere a reader of this store would not look. **`20260914T171846Z` is the published n=1000 record** since 2026-09-14 and is in `PUBLISHED`, so it is the one stamp here a clone arrives holding |
| `artifacts/curation/tentative/20260906T133559Z/` | cited from the **other** repository: the site's `modes-gallery` figure stands its curvature panel on seat `0cb93bec2bec2baf`, and `fractal-website`'s `builder/picks.py` resolves `<stamp>\|<key>` out of this checkout and keeps no copy of its own, so deleting it breaks a figure and `builder check`'s `seats` |
| `artifacts/curation/tentative/20260906T133236Z/` | cited from **this** one: `data/gallery_grade/batches.jsonl` names it as the draw behind all three `n1000_0906_*` batches of the shipped label corpus, and [`curation.k_sweep`] reproduces its seating as the `K = 2` control arm |
| `artifacts/curation/viewer/` | **the page a person opens**, `tentative.viewer_dir()`, written by `curate solve browse --viewer`. One directory with no stamp in its name, always the newest PUBLISHED record, so a bookmark survives the official record moving. Regenerable in a second and a **derivation, not a copy** — the candidates and the `1280x720ss2` fulls stay where they are and the page reaches them by relative path |
| `artifacts/votes/` | the exported voting kits, which are a sitting's whole population |
| `artifacts/curation/growth/20260902T150756Z/` | one rung of a chronological series that is never rewritten; the pool it was solved over does not exist any more |
| `data/coloring/texture_flat.jsonl` | the register of which renders' modulate texture carried no information, for rows written before the engine reported it |
| `data/spiral/`, `models/spiral/` | the spiral probe's corpus and its shipped weights |
| `models/render/` | `weights-v6` with `render.v5.fp16.pt` beside it, and the run directories every bar was read against |
| `models/gallery_grade/` | the fine head's weights and its recipe. On `roster.HEADS` since 2026-09-14 and shipped as ONE asset holding k=3 members — `gallery-grade ship` |
| `artifacts/gallery_grade_head/pool_scores.jsonl` | the cascade **refuses** without it. Every row carries the `weights` sha256 since 2026-09-14 — a run NAME is what a retrain keeps |
| `artifacts/render_folds/` | the fold assignment every render arm is fitted against — see the note below |
| `artifacts/top_slice_probe/` | the probe's features, scores and held-out split |
| `artifacts/gallery_grade/n1000_0906/*/plan.jsonl` | the only thing that can rebuild those levelled pictures as they were judged |
| `data/curation/candidate_ledger/ratchet.jsonl` | tracked and append-only: the census asserts against it, and a lost row is a lost deletion |
| `artifacts/curation/{depth,rotation,repetition}/*/fields` | Matt's ruling. All three **are** pool subtrees, so these are the entries the sweep walks past — `fields` is not `pictures`, so they are unreachable by name at that depth rather than by subtree. Each is bounded while its leg runs by `colorize.FIELDS_KEPT`, which is 64 dumps or about 226 MB, and none is swept after it |
| `artifacts/curation/gallery/` | 14,438 gate attempt rows over four retired passes, and `orphans` is their only reader — see [`curation/README.md`](curation/README.md)'s *The 53 MB of attempt rows under `artifacts/curation/gallery/` is KEPT* |

**The Durables are ten and not five**, all of them under `artifacts/curation/`:
the supply sidecar (`supply_scores.jsonl`), the score amendment
(`score_amendments.jsonl`), the hunt frame index (`hunt/frames.jsonl`) — those
three are [`curation.durables.guarded`], the ones a `curate run` refuses to start
without — plus the candidate ledger's rows and scores, the flatness sidecar, the
reduced-signature sidecar, the neutral-render embedding store, the spiral score
store and the palette colour-mass sweep log. `hunt/frames.jsonl` is the one with
**no rebuild**: `Durable.rebuild_command` is a sentence rather than a command,
because the scan it came from is gone.

**`.leveled/` directories are the exception to *unreachable*, and the question has
two answers.** They sit beside a candidate's own picture inside a `pictures/`
directory, so `orphans` addresses them — by the name the JPEG would have — and
takes the ones no store names. That is the sweep working, not a leak: the
provably-unreachable share is 1.6% of the directories and 1.3% of the bytes, and a
*bounded* sweep of the rest cannot be written at all. Both halves are
[`curation/LEGS.md`](curation/LEGS.md)'s *A `.leveled/` directory is swept only
with its own picture, and a prune is still structurally safe*.

⚠ **`artifacts/render_folds/` is on neither tier as of 2026-09-07.** The roster
kept it and it is not there; `render_folds.read_assignment` refuses, so
`renders dose`, `renders grade`, `renders deploy` and the fits behind them all
refuse until the deal is re-derived. It would have to be re-derived anyway — the
corpus has grown since, and `sides_for` refuses an assignment that does not cover
the store — so what was lost is the record of which fold each row was in, not a
working input.

## Continuing on a fresh box: `storage export` and `storage import`

The keep roster above says what is *kept*. [`portable.ROSTER`](portable.py) says
what a fresh Windows box with a GPU and a fresh clone needs to **continue every
stage**, and it is a different list: it was measured on 2026-09-16 by an audit
hook over every file the production verbs opened (`curate run`/`plan`, `hunt`,
`depth`, `mine`, `rotate`, `score`, `solve`, `atlas`, the census, the re-render,
`label sheets`/`show`, a hunt merge and a reframe), live and then from an imported
throwaway root in a `git worktree`. 501 files, **3.28 GiB**: the ten Durables, all
55 walk ledgers on both tiers, every leg's `sequence.jsonl`, the depth legs'
`depth.json`, the kept tentative records' text, the gallery-grade pool scores, the
colour census, the built label sheets' text, the `labels/` inbox, and the three
fp32 seeds of the shipped gallery-grade ensemble.

```
fractal-wallpapers storage export --to <archive disk>/portable/<stamp>
fractal-wallpapers storage import --from <that directory> --root <hot root> [--archive-root <archive>]
```

**Pictures do not travel; the fresh box re-renders**, Matt's ruling of 2026-09-16.
A solve is not picture-free — `solve.pool` refuses a row whose JPEG is absent as
`picture_absent` — so the first leg after an import is `curate candidate-ledger
re-render`, and only then a solve. The export writes `pictures.jsonl` instead: one
row per candidate the solve can seat (418,339, 59.3 GiB on 2026-09-16) with its
sha256 and whether the build that drew it is the exporting build (`same_build`) or
unrecorded (`unknown_build`, the rows before 2026-09-02). Two seeded samples
re-rendered from an imported root came back **byte-identical, 125 of 125** — 48 at
one picture a (location, mode) pair, 24 of each class, and 77 as 30 whole pairs. The
pool is 178,569 pairs at 2.34 pictures a pair, and the whole-pair sample's
**0.66 s a picture of wall at three workers** prices the full re-render at about
**76 hours** on this machine.

**What the export proves before a byte lands.** Import checks every file's size and
sha256 against the manifest, refuses a file the manifest does not name and a
destination that already exists, writes through a temporary, and touches nothing
else. Without `--archive-root` every file lands under `--root`, which is what a
single-root box is. From a throwaway root in a worktree it wrote nothing under the
live checkout or archive, `durables.guard()` passed, `depth plan` resolved the same
34,160 units as live, `reframe` read all 55 ledgers, a 12-candidate hunt merged, a
prune dropped 5,296 rows whose pictures were all absent without a failure, and a
lime solve seated the **same 150 seats in the same order** as the live solve run
before it, with the live stores' sha256 identical before and after the pair (the
worktree's pool pictures were stand-in copies for that one comparison, deleted
after).

**What a fresh box needs before the import**: `uv sync --extra dev --extra models
--extra solve`, `fetch-weights`, `cargo build --release`, and a `local.toml` naming
the root it imports to. **The engine fingerprint is the thing to read in the import's
output.** `amend.read` keeps only amendment rows drawn by the running build, so a build
that fingerprints differently silently reads every amended location at its old
sidecar score; the amendment then has to be *re-derived* with `curate redraw` and
cannot be re-keyed, because a row is a reading of a view that build drew. A fresh
`cargo build --release` of the same source fingerprinted identically on 2026-09-16
(`5d97e76bb16be71d`) although the binary's bytes differed.

**Why weights outside `models/weights.json` exist here, and which one travels.**
The manifest names one asset per head in `roster.HEADS`. Untracked beside them sit
every run's `best.pt`/`last.pt` (training output no release carries), the retired
`smooth_render`/`strange_render` artifacts (replaced by `render` on 2026-08-23),
`render.v5.fp16.pt` (the previous render artifact) and `render.candidate.fp16.pt`
(`ship`'s staging output). No production verb opens any of those **except** the
shipped gallery-grade arm's three `best.pt`: `rotation.score_fine` loads them with no
fallback to the halved ensemble, so they are on the roster.

## One shape for a place, and one reader for it

Every record here writes a location the same way — `family` with all its
constants, `viewport` as three decimal strings, `render` saying at what size and
through which coloring. A label row, a walk ledger's candidate and a release
decision are all that shape. **`locations.py` is the only thing that reads it**,
and everything that takes a manifest goes through it: `render --location` and
`render --manifest`, `screen`, `score-locations`, and the boundary draw's own
output.

It takes all four spellings, because all four are already on disk:

```text
{"family": ..., "viewport": ..., "render": {...}}    a label row
{"family": ..., "viewport": ..., "maxiter": 13140}   a walk ledger's candidate
{"location": {"family": ..., "viewport": ...}, ...}  a release decision row
{"family": ..., "viewport": ..., "mode": ..., ...}   a scoring corpus row
```

A ledger row keeps its cap at the top level because it records a *frame the gates
measured*, not a picture, and has no render block to put one in. The fourth writes
its coloring flat beside `family`, which is what `labeling/finished.py`'s row
builder emits and what the palette-choice, render-head and gallery-grade corpora
are full of. **Until 2026-09-14 that one was read and its coloring silently
dropped**: `render --manifest` over such a file drew every row at `smooth` /
`twilight_shifted` and exited 0. It is read now, and a member answered twice with
two different values is refused rather than resolved — there is no defensible way
to pick, which is the argument `refuse_two_descriptions` already makes for a record
that a flag contradicts.

**Reading a row and drawing it are two different questions, and only one door asks
the second.** `record` takes anything that names a place and a geometry, because
two of its three callers do not draw: `screen` keeps the frame and the cap and
throws the rest away, and `score-locations` discards the coloring entirely. A
corpus row carrying a curve and a palette pass is a perfectly good input to both.
So the refusal for a picture this shape cannot carry — a curve, a fold, a palette
pass, a trap's settings, a levelling band — lives at the **render door** and
nowhere else, and it sends you to `render --recipe FILE`, which takes the whole
picture. Asking it in `record` would refuse tens of thousands of tracked rows to
protect a door those rows never go through. Family and
viewport are the identity and are required; everything else defaults to what the
flag nobody passed would have meant, so a two-key record is a legal record.
`maxiter` is the one field with a third answer — absent means "the depth-aware
policy decides", which is not any particular number, so it stays absent.

**Batch forms take a manifest file, never a list of paths** — the repository-wide
rule, stated in [`CLAUDE.md`](../../CLAUDE.md); here the manifest is also the
record of what the batch was over. Pictures in a batch are named `<row>_<digest>.png`, the digest
being of everything the engine was told — so a batch is resumable and two records
that would draw one picture name one file. `renders.jsonl` beside them is the join
back to the records.


## Which engine build drew a picture

`engine.py` is the only door to the renderer. `engine_spec.py` is what the door
is handed — the one derivation of the JSON spec from a row, plus the palette
recipe that goes in it. `engine_fingerprint.py` is the answer to a question the
door could not be asked: *which build*.

A cached picture outlives the run that made it. A view is addressed by a digest
of its own recipe — the family, the viewport, the geometry, the coloring — and
the program that carried that recipe out is not in the recipe, so a file at the
right name has never been evidence that today's engine made it. Every judge in
this project reads cached pictures.

The build is named by **what it draws**: six pinned probes over four family
kinds and six modes at the node regime, rendered through `engine_spec.spec_of` —
the production path, not a second way to ask for pixels — and digested to sixteen
hex characters. That derivation is at the floor rather than in `models/renders.py`,
where it lived until 2026-09-04, for exactly this reason: a fingerprint that has
to reach *up* into the render cache and the label store to name the production
path is a fingerprint whose module sits inside their import cycle, and it did —
`engine_fingerprint` was one of five modules the layering fixes took out of a
49-module one. `renders.spec_of`, `renders.coloring_of`, `renders.catalog` and
`finished.recipe` all still resolve; they are imported from here.

Byte-identity of output is already this engine's contract (native
&equiv; wasm), so a digest of output *is* the build identity, and it needs no
build system. It is preferred over a source revision because it also catches a
rebuild from unchanged source and a moved mode catalog. About 0.35 s, cached per
process.

Every view directory carries a `drawn_by.jsonl` beside its pictures —
`{schema, view, engine}` a row, appended, last row winning. A view no row claims
is `unknown`, which is not a fingerprint and is therefore stale: `location_view.
render_view` draws it again rather than handing it to a head. That is every
picture drawn before this existed, and re-reading them is
`fractal-wallpapers curate redraw`.

### Two things never to do to `renders.job_name`, and both have bitten

Neither is enforced by a test, which is why they are here rather than only in
`engine_spec.py`'s module docstring: the person about to do either is writing a
test, and a test author does not read the module the derivation moved to.

⚠ **Never pin a `job_name` digest in a test.** `job_name` is a sha256 of the whole
engine spec, and `engine_spec.spec_of` writes `paths.colormap_dir()` into that spec
as an **absolute path into the checkout**. So the digest is different on every
machine, and different again after a clone moves — a pinned literal passes for the
author and fails for everybody else and for CI. That the path is in there is
deliberate and it is why `candidate_ledger` drops `colormap_dir` from the recipe
key: harmless in a cache file name, which means nothing off the machine that wrote
it, and not harmless in anything keyed forever. Assert what a name *is a function
of* — two rows agreeing or differing — never the sixteen characters.

**Which move breaks a cache and which does not follows from that one path.**
`paths.colormap_dir()` is `<repo_root>/data/palettes`, so a **re-clone** renames
every cached picture and misses the render cache entirely, while moving the
**hot root** — where `artifacts/` lives — renames nothing, because no tier root
is in the spec. And `renders.SPEC_MEMBERS` carries `mode` and `mode_params`, the
name and its settings, never the catalog those resolve through: **adding a catalog
entry renames nothing**. Editing an existing entry's arithmetic is the other case
and re-keys nothing either, which is why it is invisible and why the engine
fingerprint rather than the job name is what catches it.

⚠ **Never patch `renders.colormap_dir`.** `spec_of` moved down to `engine_spec.py`
on 2026-09-04, so it reads `engine_spec.colormap_dir` and nothing else. A fixture
that patches the name still re-exported from `models/renders.py` is holding a name
`spec_of` no longer reads: the patch takes, the test goes green, and the digest it
is checking is silently over the real checkout instead of over the field the
fixture set up. `tests/test_curation_colorize.py`'s field-name digests are the
ones that depend on this, and they name `engine_spec`.


## A record's prose has one copy in the source and a whole copy on every row

Every record this package writes explains itself in place. Beside `reachable` is
`reachable_is`, beside `theme_bar` is `theme_bar_is`: a sentence saying what the
number means, what `null` means, and what a record that does not carry the field
at all was taken before. There are 104 of them across 25 modules, 22 in
`curation/solve.py` alone, and **a row read years from now off the archive tier
still says what it ran under with no checkout present.** That is the property the
whole arrangement exists for.

Until 2026-09-12 each sentence was written at the record site, so the source
carried one copy per *write* and a module's own two records could disagree about
the same field — `models/gallery_grade_train.py` had two spellings of
`held_out_is` differing in three words. Standing them beside each other is what got
them read, and reading them found both wrong: see the dated entry below. The prose
now lives in a module-level **`SCHEMA_NOTES: dict[str, str]` beside that module's
`SCHEMA`**, and the builder reads it at write time.

**Three things this is deliberately not.**

*Not a pointer.* Nothing on a row became a key, a reference, or a note the reader
needs this repository to resolve. `SCHEMA_NOTES` is read at **write** time and the
finished sentence goes on the row. A scheme where the row carries `reachable_is:
"solve.reachable_is"` and a reader resolves it against a checkout is the one thing
this must never become — it trades the isolated-readability property for source
tidiness, and the tidiness was never the point. Do not re-propose it.

*Not versioned.* There is no `schema: 2`, no note version, no bump rule when a
sentence is edited. A record carrying the note that was true **when it was
written** is correct about itself; that is the property working, not drifting, and
two records whose notes differ are two records taken under two readings — which is
what a reader wants to see. The one genuine defect is a note that was *wrong when
written* and later corrected, which leaves earlier rows asserting something false.
That is rare enough to want a dated line here when it happens rather than an
integer nobody maintains, and the list below is that line.

### Notes corrected after they shipped

Rows written before the date carry a sentence that was **wrong**, not merely
older. This is the whole of the list; anything not on it, a reader may take at
face value.

* **2026-09-12 — `depth.SCHEMA_NOTES["not_admitted_is"]`.** Landed in `727733d`
  saying the places `general_leg_0909`'s band 2 lost were *all*
  `julia:mandelbrot`. Measured the same day: the same 168 places cost all three of
  that night's arms, they span **ten** partitions, only **14** are
  `julia:mandelbrot`, and **166 of them have no supply-sidecar row at all** — so
  they were never an embedding backlog either. A `curate depth near-places` census
  written under `727733d` carries the wrong sentence.
* **2026-09-12 — `gallery_grade_train.SCHEMA_NOTES["held_out_is"]`**, both
  spellings of it, and `bar_<band>.json`'s `population.is` with them. They said
  every number in a run record is *optimistic by one early stop* (or *by one
  choice*). Read against the trainer: **three** choices land on the stopping
  slice, not one — the epoch inside every run, and then in `band` the arm, by the
  mean of the band's statistic over its seeds, and the seed, by the median of the
  winning arm, both off the records' own `held_out` numbers. So every
  `metrics.json` in `models/gallery_grade/` (21) and all three tracked bars
  understate their own optimism by two choices. Nothing on those rows is
  re-measured by this: the numbers stand, the caveat over them was too small.

*Not a rewrite.* The lift moved 104 sentences and edited none of them. Where two
of a module's records write one field two ways, both notes are kept under
`<field>.<which>` — `solve.py`'s `group_cap_is.shipped` against
`group_cap_is.named` is one — so the near-duplicates are visible to whoever wants
to reconcile them, and reconciling them is a separate decision. The lift's own
near-duplicate, `gallery_grade_train`'s two spellings of `held_out_is`, was
reconciled on 2026-09-12 into a **single** note: once read side by side, neither
was true.

**A sentence that names a runtime number is a `str.format` template**, formatted
at the site: `SCHEMA_NOTES["reachable_is"].format(wanted=wanted)`. A field written
one of two ways picks between two notes at the site the same way. Either way the
row carries the finished sentence and the prose still has one copy.

`tests/test_schema_notes.py` is the guard. It refuses a `*_is` / `*_are` value
written as prose at a record site, a `SCHEMA_NOTES` lookup that names no note, and
a note nothing reads.
