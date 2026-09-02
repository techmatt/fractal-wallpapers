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

**Two places still build a tree path without asking**, found by
`AUDIT_artifacts_inventory` and left alone by it: `palettes/carriers.py`'s
`RECOLOUR_DIR` and `models/decisions.py`'s `FIGURE` are both a bare
`Path("artifacts") / …`, joined directly rather than passed through `under()` or
`cli.resolve_output`. They are relative to the *shell's* working directory, so on
a machine that has moved its hot root they write to a fourth place that is
neither tier. Everything else that looks hard-coded is an argparse **default
string** — `resolve_output` puts those through `rehome`, which is what makes the
literal `"artifacts"` in them load-bearing rather than a leak.

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


## One shape for a place, and one reader for it

Every record here writes a location the same way — `family` with all its
constants, `viewport` as three decimal strings, `render` saying at what size and
through which coloring. A label row, a walk ledger's candidate and a release
decision are all that shape. **`locations.py` is the only thing that reads it**,
and everything that takes a manifest goes through it: `render --location` and
`render --manifest`, `screen`, `score-locations`, and the boundary draw's own
output.

It takes all three spellings, because all three are already on disk:

```text
{"family": ..., "viewport": ..., "render": {...}}    a label row
{"family": ..., "viewport": ..., "maxiter": 13140}   a walk ledger's candidate
{"location": {"family": ..., "viewport": ...}, ...}  a release decision row
```

A ledger row keeps its cap at the top level because it records a *frame the gates
measured*, not a picture, and has no render block to put one in. Family and
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

`engine.py` is the only door to the renderer. `engine_fingerprint.py` is the
answer to a question that door could not be asked: *which build*.

A cached picture outlives the run that made it. A view is addressed by a digest
of its own recipe — the family, the viewport, the geometry, the coloring — and
the program that carried that recipe out is not in the recipe, so a file at the
right name has never been evidence that today's engine made it. Every judge in
this project reads cached pictures.

The build is named by **what it draws**: six pinned probes over four family
kinds and six modes at the node regime, rendered through `renders.spec_of` — the
production path, not a second way to ask for pixels — and digested to sixteen hex
characters. Byte-identity of output is already this engine's contract (native
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
