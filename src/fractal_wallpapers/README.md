The package that steers the renderer: find locations, color them, judge the results.

## Two roots

`paths.py` defines both places this package addresses files in, and nothing else
builds one for itself.

* **`repo_root()`** — the checkout. Records, labels, weights, code: everything
  that matters and everything git keeps.
* **`artifacts_root()`** — the regenerable tree. Tile caches, location views,
  render caches, a study's pictures. Around a hundred gigabytes, and therefore a
  *setting*: `artifacts_root` in an untracked `local.toml` at the repository
  root, or `FRACTAL_WALLPAPERS_ARTIFACTS_ROOT` in the environment, defaulting to
  `artifacts/` inside the checkout when neither says otherwise. A configured root
  that is not present raises `ArtifactsRootMissing` rather than falling back —
  see the [top-level README](../../README.md#putting-the-regenerable-tree-on-another-disk)
  for why a fallback would be worse than a refusal.

Because the second root moves, a record that names a file under it is written and
read through one pair of functions:

* **`tracked_name(path)`** on the way out — a file in the checkout is named
  relative to it, and a file under the artifacts tree is named `artifacts/<rest>`
  wherever that tree lives. This is not cosmetic. A walk ledger's name is
  the key curation's sidecar stores each scored row under, so a name that changed
  when the tree moved would leave every stored row unmatchable and a re-score
  would pile duplicates beside the rows it meant to replace.
* **`rehome(stored, root=None)`** on the way in — a stored name re-addressed
  against the root as it is now. It takes both spellings a record can carry, the
  relative `artifacts/<rest>` and one machine's absolute path, and returns `None`
  for a path that names nothing under an artifacts tree, so the caller keeps its
  own bytes rather than having them re-spelled.

The one hot user is `models/tiles.read_manifest`, which re-homes the path on
every row of a manifest the engine wrote — a million of them — resolving the root
once for the file rather than once per row. `tests/test_artifacts_root.py` is the
guard over all of it.
