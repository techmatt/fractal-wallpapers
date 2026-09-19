"""A gallery recorded under a name, so its pictures can be referred to by ID.

`curate solve` chooses a gallery and writes a record of the choosing. That record
is a *decision*, and it is rewritten every time the same name is solved again. It
is not something a person can point at: to say "use this wallpaper, and that one"
a reader needs a stable handle per picture, a page showing the pictures beside
their handles, and a guarantee the picture is still on disk next week.

A **tentative gallery** is that. One stamped folder holds `gallery.jsonl` — one
row per seat, carrying the ledger recipe key that IS the ID, a short alias for
typing, and the few columns a person filters on — `manifest.json` saying what pool
it was taken over and how it did, and `index.html`, a self-contained browser over
the pool's own 640x360 candidate pictures — filterable on seven facets, groupable
on five, sortable on four, and opening any picture at the size the screen gives.
It opens in [`page_order`]'s **presentation order**, which is derived from the rows
at build time and moves none of them.

**The record is the rows and the manifest; the page is a derivation of them.**
Matt's ruling of 2026-09-05, and it is what publication tracks: `gallery.jsonl`
and `manifest.json` come through the hole in `.gitignore` and `index.html` does
not. [`page`] rebuilds it from the rows alone — `fractal-wallpapers curate solve
browse <stamp>` — so a clone that wants the browser runs one command rather than
carrying 4.07 MB of derived HTML in the history for the seven published stamps.

Nothing here chooses anything. [`curation.solve`] does the choosing and this
records it, so a change in this module can never move a seat.

## Three properties, and each one is the reason for a piece of this

**The ID has to survive every later merge.** A ledger key names a recipe forever,
but [`candidate_ledger.prune`] runs inside every merge and drops the rows the
retention rank let go — with their pictures. A seat in a tentative gallery is
exactly the kind of row that rank can drop: it won its seat on the *gallery's*
objective, over a view, against the colour rules, and none of that is being in
the top [`candidate_ledger.RETAIN_PER_PAIR`] of its own (location, mode) pair. So
a recorded gallery is a **protection class** in the prune,
[`candidate_ledger.RETAINED_TENTATIVE`], the way a live release row is. Without
it a figure prompt could name an alias whose
picture had already been swept, which is the one failure this store exists to
prevent.

**The alias has to be short and it has to be unambiguous.** Eight hex characters
of a sixteen-character key, and a group of keys sharing those eight gets the
shortest prefix at which the group is distinct. Aliases stay unique across the
whole record because a lengthened alias begins with a prefix no other group holds.

**The page has to work from the file system.** No server, no build step, no CDN:
one HTML file whose only external references are relative paths to JPEGs already
on this disk. That is what makes it openable by double-clicking, and it is why the
rows are embedded in the page as JSON rather than fetched — a `fetch` of a sibling
file is refused under `file://`.

## What a row carries, and why it is these columns

`schema` (int, [`SCHEMA`]); `seat` (int, the seat's place in the solve's own walk);
`key` (text, the ledger recipe key — **the ID**); `alias` (text); `mode` and
`partition` (text, off the seat); `mode_params` (dict, the seat's own colouring
settings off `recipe.mode_params`, so a `direct_trap_multiply` at `opacity=0.6` and
a bare one are two rows here — `{}` is a bare seat, and it is also what a record
written before this field existed means, so an absent one needs no rewrite;
[`colorize.spelled`] turns the pair into the one string a roster names it by, and
[`colorize.roster_entry`] reads that back); `cell` and `hue_family` (text, the *leading*
dominant colour cell and hue family, which is what a person means by "the green
one"); `cells` and `families` (lists, every name the picture is dominant in,
because dominance is thresholded and one picture carries more than one);
`seated_for` (text, the demand or leg that placed the seat, as `solve` stamped it)
and `pinned` (bool, a row of the pinned list, seated before the seed — forward-only
and absent before 2026-09-19, which reads as `false`) and `floor` (text,
[`FLOOR_MANDATED`] / [`FLOOR_HOLDING`] / [`FLOOR_FREE`] — what
the **colour floor** had to do with this seat being here, with `floor_cells`
naming the cells that make it so; both are forward-only and absent on a record
taken before 2026-09-09, which carried no colour floor);
`centered` (bool, joined off the walk ledgers through
[`depth.centered_locations`], since nothing downstream of a walk carries the flag);
`rank` (the leg's own fitted rank key, which is what the seats were ordered on) and
`p_ge4` (the judge's raw probability, kept beside it because the two are different
numbers and a reader comparing galleries needs both); `location` (text, so the
one-wallpaper-per-location rule is checkable off the record alone); `picture`
(text, the stored 640x360 candidate, named as the record that chose it named it).
"""

from __future__ import annotations

import html
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.curation import fulls, page_order
from fractal_wallpapers.curation import page as page_module
from fractal_wallpapers.paths import Tiers, rehome, tracked_name, under

#: The schema every row and every manifest here carries.
SCHEMA = 1

#: The prose this module's records carry on their `*_is` / `*_are` fields, in
#: one place. The builder reads it at write time and the row still carries the
#: sentence WHOLE — nothing here is a pointer, and a record read years later off
#: the archive tier needs no checkout to resolve. Not versioned either. The
#: argument for both, and the reason not to re-propose the pointer, is at
#: `fractal_wallpapers/README.md`'s *A record's prose has one copy in the source
#: and a whole copy on every row*.
SCHEMA_NOTES: dict[str, str] = {
    "diversity_is": "which rule decided two seats were different enough, as "
    "`rules.State.record` spells it. A gallery chosen under a different rule is "
    "not comparable with this one. A manifest with no `diversity` key at all was "
    "written before 2026-09-11; an explicit `null` is a pass that ran without the "
    "rule",
    "stamp_is": "sha256 over the sorted candidate keys, as `growth.pool_stamp` takes "
    "it. Two records carrying the same stamp were chosen over the same pool — over "
    "the same POOL and not necessarily the same seatable rows, because a quality "
    "bar narrows what a pass may seat and is on `solve.config.fine_bar` instead",
}


#: The subtree a recorded gallery's stamped folder lands in.
UNIT = "tentative"

#: The subtree holding **the page a person opens**, as against the pages the
#: records hold. One directory, no stamp in its name, and [`viewer_dir`] is the
#: only spelling of it.
#:
#: A record's own `index.html` is beside its rows and names its stamp, which is
#: right for a record and wrong for a bookmark: the official record moves every
#: checkpoint and a bookmark that names a stamp is a bookmark onto a superseded
#: gallery the day after it is made. `curate solve browse --viewer` writes the
#: newest PUBLISHED record's page here, so the same path answers *show me the
#: gallery* for as long as the project runs and the stamp in its title bar is how
#: a reader tells which one they are looking at.
#:
#: **It is a derivation and it is not a copy.** The thumbnails and the
#: release-geometry fulls stay where they are and the page reaches them by
#: relative path, [`page`]'s rule, which is why moving this directory means
#: writing it again rather than dragging it — the same reason `--out` exists at
#: all. Under `curation` because the pictures it points at are the live pool's
#: and a viewer on the archive tier would be a page of dead links.
VIEWER_UNIT = "viewer"

#: The two files one stamp's RECORD is, and the one derived from them.
#:
#: Matt's ruling of 2026-09-05 draws the line here: the rows and the manifest are
#: the record and are what publication tracks, and [`PAGE_NAME`] is a browse view
#: [`page`] writes from `gallery.jsonl` whenever somebody asks. Before it, all
#: three were tracked per published stamp, which put a derivation in the history
#: — 4.07 MB of it against the rows' 3.60 MB.
ROWS_NAME = "gallery.jsonl"
MANIFEST_NAME = "manifest.json"
PAGE_NAME = "index.html"

#: The third file of a published record, and the one that makes it **redrawable**.
#:
#: A seat row says which picture was seated and carries the key that names it; it
#: does not say what the picture is made of. The key is a one-way digest, the
#: recipe behind it lives in the untracked candidate ledger, and 529 of a
#: thousand seats carry a continuous `palette.phase` — so recovery by search is
#: out and a clone could draw the *place* a seat stands on and nothing else. That
#: was measured on 2026-09-14: 994 of 1,000 published seats could not be redrawn
#: from tracked data, the six that could being the ones a tracked decision store
#: happens to overlap.
#:
#: One `{key, recipe}` row per seat closes it, at 0.68 MiB for a thousand — under
#: `tests/test_history_purity.py`'s 1 MiB ceiling and smaller than the
#: `gallery.jsonl` beside it. The `recipe` block is [`recipes.Recipe.record`]
#: verbatim, so `recipes.of_record` reads it back and `recipes.key_of` of that is
#: the row's own key; `render --recipe` is the door that draws one.
#:
#: ⚠ **Tracked for `20260914T171846Z` alone**, and `.gitignore` names that one
#: path rather than a pattern. The other seven published stamps predate the
#: decision and their rows are on this machine; writing theirs is a decision about
#: history's size, not a fix. [`recipes_path`] resolves for any stamp and
#: [`write_recipes`] writes for any stamp — what is per-stamp is only whether git
#: carries it.
RECIPES_NAME = "recipes.jsonl"

#: The record's own directory of full-resolution pictures — see [`fulls_dir`].
FULLS_NAME = "fulls"

#: How many characters of the recipe key an alias is, before a collision makes it
#: longer. Eight of sixteen: short enough to read out loud, and over a gallery of
#: a thousand seats a birthday collision on those 32 bits is about one in ten
#: thousand — rare enough to be worth the short name, common enough that the
#: lengthening in [`aliases`] is a rule rather than a decoration.
ALIAS_LENGTH = 8

#: How many seats a recorded gallery asks for unless a caller says otherwise. **A
#: thousand**, which is well above what today's pool can fill — the shortfall is
#: the reading, and a record cut to what fills is a record that hides it.
RECORDED_SEATS = 1000

#: **The stamps Matt has published**, oldest first. A published record is tracked
#: — its two text files come through the hole in `.gitignore` — and it is the
#: only kind an unstamped read can land on. [`PAGE_NAME`] is not one of them: a
#: record is its rows and its manifest, and [`page`] regenerates the browser from
#: those on demand.
#:
#: Recording a gallery and publishing one used to be a single act: the hole was
#: spelled per FILE across every stamp, so every record ever made was committed,
#: and a record too large to track was a record that could not be made without
#: breaking `tests/test_history_purity.py` — an n=2000 record's `gallery.jsonl` is
#: over `MAX_TRACKED_BYTES`. **`LARGE_TEXT_ALLOWLIST` was not the answer and was
#: not touched**: widening the size rule would have tracked every record ever made
#: rather than the ones worth pointing at, which is the wrong question. Matt's
#: ruling of 2026-09-04 split
#: them. A record is published when he names it; every other record is read **by
#: naming its stamp**, and what it does not get is a Durable-class save, check or
#: restore and a place in an archive copy.
#:
#: **An unpublished record is DISCARDED by default**, Matt's ruling of 2026-09-13,
#: which reversed a default that had read the other way. **Keeping needs a reason
#: and discarding does not**: a leg that recorded a gallery to measure something
#: against deletes it once the measurement is taken and says so in its report,
#: because a solve is cheap to run again and what a leftover record costs is
#: misreading hazard and prune protection rather than bytes. The keep list is the
#: stamps below, any record a published or upcoming figure cites, and the current
#: official n=1000 record — which is `20260914T171846Z`, and which since
#: 2026-09-14 is a stamp in **this** tuple rather than in [`KEPT_UNPUBLISHED`].
#: **The role moves and the entry does not follow it**: a stamp that held it keeps
#: its line for as long as something still resolves it, so this sentence names the
#: rule and the tuples name the stamps. That list is [`kept`], and
#: [`KEPT_UNPUBLISHED`] is the half of it this tuple does not already carry.
#:
#: **`20260914T171846Z` is the project's first publication since the split**, and
#: the eighth stamp here. It is the first solve taken with the full rejection pass
#: ingested — 1,000 of 1,000, shortfall 0, 728 vetoed rows out of the pool — and it
#: is what an unqualified "the record" and an unstamped [`latest`] both mean from
#: here. It was in [`KEPT_UNPUBLISHED`] until it was published and is not in both:
#: [`kept`] de-duplicates, so a stamp named twice would read as two decisions where
#: there is one, and publication is the stronger of the two to state.
#:
#: **Retention is a third question after publication and durability**, and until
#: 2026-09-13 the protection answered it by itself: [`protected_keys`] swept the
#: whole store whatever any list said, so a record that merely existed pinned its
#: seats and deleting it was the only thing that released them. That is the policy
#: backwards — an ephemeral artifact conferring preservation — and it is why
#: sweeping the store kept arriving on Matt's desk as a recurring approval. **The
#: pin now reads [`kept`] and nothing else.** A record off the keep list is still
#: perfectly readable by naming its stamp; what it no longer does is hold candidate
#: rows against the prune on nobody's decision.
#:
#: **This list and `.gitignore`'s negation lines are one list written twice**, and
#: `tests/test_tentative.py` fails if they disagree. Two spellings because git
#: cannot read a Python tuple and this module must not shell out to git to answer
#: what an unstamped read means.
PUBLISHED: tuple[str, ...] = (
    "20260902T161757Z",
    "20260902T164622Z",
    "20260903T234205Z",
    "20260904T023748Z",
    "20260904T080248Z",
    "20260904T134242Z",
    "20260904T233233Z",
    "20260914T171846Z",
)

#: **The unpublished stamps the keep list names**, which is the whole of the keep
#: list that [`PUBLISHED`] does not already carry. Discarding is the default for an
#: unpublished record, so an entry here is a stated reason and not an oversight,
#: and it is what makes [`protected_keys`] a decision rather than a side effect of
#: what happens to be on a disk.
#:
#: **The test for an entry is that something RESOLVES the record**, not that
#: something mentions it. Every batch in `data/gallery_grade/batches.jsonl` names
#: the record it was cut from in its `method` prose, and none of those is a reason
#: to be here — the corpus rows carry their own join, so the record is provenance
#: and provenance does not need the folder. What earns a line is code or a figure
#: that reads the rows.
#:
#: * `20260906T133236Z` — `data/gallery_grade/batches.jsonl` names it as the draw
#:   behind all three `n1000_0906_*` batches of the shipped label corpus, and
#:   [`k_sweep`] reproduces its seating as the `K = 2` control arm.
#: * `20260906T133559Z` — the site's `modes-gallery` figure stands its curvature
#:   panel on seat `0cb93bec2bec2baf`; `fractal-website`'s `builder/picks.py`
#:   resolves `<stamp>|<key>` out of this checkout and keeps no copy of its own.
#: * `20260908T144844Z` — `backfill.DEFAULT_RECORD`, the record a backfill sweeps
#:   when nobody names one, and the n=1000 gallery the site's figures resolve.
#: * `20260908T211552Z` — two more seats `fractal-website`'s `article/figures.jsonl`
#:   names as `<stamp>|<key>`.
#: * `20260911T022330Z` — the record `curation/page_order.py`'s constants were
#:   measured on. Re-measuring those against a record pruned out from under them
#:   would read as drift in the page order rather than as a missing record.
#: * `20260914T152502Z` — **Matt's instruction in `veto_model_ckpt124`**, and the
#:   one entry here he named rather than something in the tree earning: it is the
#:   first n=1000 solve taken with the veto in force, and it is the counterfactual
#:   the veto's cost to the gallery is read off — `curation/GALLERY.md`'s *The veto
#:   and the seat floors can disagree* quotes its shortfall, its pool counts and
#:   its worst seat. ⚠ **Nothing resolves its rows**, which is the ordinary test
#:   for a line here, so this one goes when the veto's cost stops being a live
#:   question rather than waiting for a figure to stop naming it.
#: * `20260913T172903Z` and `20260914T144946Z` — the **before and after of the
#:   `mine_night2_ckpt124` run**, added 2026-09-14, and they are one entry in two
#:   lines: `curate seat-sheet --before … --after …` names both by stamp, and a
#:   diff with one half missing is not a smaller diff, it is no diff. ⚠ The before
#:   half was **moved out of the store by that same night's sweep and moved back**
#:   — it was off the keep list for the hours between, which is exactly right under
#:   discard-by-default and exactly why the sweep moves records rather than
#:   deleting them. When the pair stops being interesting, both go.
#:   `20260914T144946Z` **earns a second line of its own**: the rejection pass was
#:   cut over its thousand seats — `data/gallery_grade/batches.jsonl` names it as
#:   the population `gallery_rejection_20260914` was drawn from — so it is the
#:   before half of `rejection_ingest_ckpt124`'s diff as well, and it stays until
#:   that batch stops being the newest thing the store learned.
#: * `20260919T171003Z` … `20260919T173838Z` — **the twenty-one pinned records**,
#:   Matt's instruction in `site_rebase_ckpt132`, and one entry in twenty-one lines:
#:   the first solves with `data/curation/pins.json` seated first, one per
#:   collection in `targets.TARGETS` plus the general n=1000 and an n=2000. Twenty of
#:   them are the collection stamps `fractal-website` lists — its galleries, seat
#:   tiles and atlases resolve their rows — and each has a live page under `curate
#:   solve viewers`. `20260919T171350Z`, the n=2000, is **not** listed by the site and
#:   is kept as the comparison beside the n=1000; it goes when that stops being asked.
#:
#: ⚠ **`20260914T171846Z` was here and is now in [`PUBLISHED`]**, from 2026-09-14.
#: It is kept by that tuple and must not be named by this one as well: [`kept`]
#: de-duplicates either way, so a second line would change nothing on disk and
#: would leave two answers to *why is this record kept* where publication is the
#: only one that still applies.
#:
#: ⚠ The first four were named in `fractal_wallpapers/README.md`'s store table as
#: hard dependencies **while the store-wide sweep made the distinction cost
#: nothing**. Now it costs everything, so they are here: the day this list became
#: the whole input to [`protected_keys`] is the day a dependency not on it is a
#: figure that breaks.
#:
#: ⚠ **Unlike [`PUBLISHED`], nothing in `.gitignore` corresponds to this**, and that
#: is deliberate: a kept record is kept, not tracked. Publication, durability and
#: retention are three questions, and this tuple answers only the third.
KEPT_UNPUBLISHED: tuple[str, ...] = (
    "20260906T133236Z",
    "20260906T133559Z",
    "20260908T144844Z",
    "20260908T211552Z",
    "20260911T022330Z",
    "20260913T172903Z",
    "20260914T144946Z",
    "20260914T152502Z",
    # The pinned records: general n1000, general n2000, twelve families, seven modes.
    "20260919T171003Z",
    "20260919T171350Z",
    "20260919T171517Z",
    "20260919T171636Z",
    "20260919T171754Z",
    "20260919T171915Z",
    "20260919T172029Z",
    "20260919T172144Z",
    "20260919T172300Z",
    "20260919T172420Z",
    "20260919T172535Z",
    "20260919T172651Z",
    "20260919T172806Z",
    "20260919T172927Z",
    "20260919T173059Z",
    "20260919T173230Z",
    "20260919T173402Z",
    "20260919T173514Z",
    "20260919T173625Z",
    "20260919T173732Z",
    "20260919T173838Z",
)


class TentativeRefused(RuntimeError):
    """A tentative gallery cannot be recorded, read or browsed."""


# --------------------------------------------------------------------------- #
# Where a stamp lives.
# --------------------------------------------------------------------------- #
def stamp_now() -> str:
    """The name a record's folder takes: UTC, to the second, sortable."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def store_root() -> Path:
    """Where every recorded gallery lives. **The one accessor**, because a test
    redirecting the store redirects this and a second spelling would be a path
    that reads past the redirect into this machine's real records."""
    return under("curation", UNIT)


def viewer_dir() -> Path:
    """Where `--viewer` writes the page. **The one accessor**, [`store_root`]'s reason."""
    return under("curation", VIEWER_UNIT)


def gallery_dir(stamp: str) -> Path:
    return store_root() / str(stamp)


def rows_path(stamp: str) -> Path:
    return gallery_dir(stamp) / ROWS_NAME


def manifest_path(stamp: str) -> Path:
    return gallery_dir(stamp) / MANIFEST_NAME


def page_path(stamp: str) -> Path:
    return gallery_dir(stamp) / PAGE_NAME


def recipes_path(stamp: str) -> Path:
    return gallery_dir(stamp) / RECIPES_NAME


def fulls_dir(stamp: str) -> Path:
    """Where this record's own full-resolution pictures live. **Untracked, and pinned.**

    A gather resolves most of a record's fulls to somebody else's labelling
    sheet — 923 of the published record's 1,000 on 2026-09-14, and 895 of those
    to one sheet — so the sheet's ordinary cleanup would take nine tenths of the
    published gallery's full-resolution pictures with it. [`fulls.pin`] gives each
    one a second name in here, which is a hard link and costs no disk, and the
    record then owns a set of pictures nothing else's retention decides.

    **Ignored, like every other picture.** `.gitignore` excludes a stamp's
    contents and un-ignores the text files one path at a time, so a directory
    appearing inside a published stamp is ignored without a rule being written —
    which is the shape that decision was given on 2026-09-04.
    """
    return gallery_dir(stamp) / FULLS_NAME


def stamps() -> list[str]:
    """Every recorded gallery on this machine, oldest first.

    A folder counts only once it holds its rows: a stamp claimed by a record that
    died before writing is not a gallery, and a resolver defaulting to it would
    answer nothing for every ID that exists.
    """
    root = store_root()
    if not root.is_dir():
        return []
    return sorted(held.name for held in root.iterdir() if (held / ROWS_NAME).is_file())


def published() -> list[str]:
    """The [`PUBLISHED`] stamps this machine actually holds, oldest first.

    Intersected with the store rather than returned whole, because a clone has
    every published stamp's three text files but a machine that has never solved
    holds no pictures for them — and a caller of this wants a record it can read.
    """
    held = set(stamps())
    return [stamp for stamp in PUBLISHED if stamp in held]


def kept() -> list[str]:
    """**The keep list**: every stamp this project has decided to hold on to.

    [`PUBLISHED`] plus [`KEPT_UNPUBLISHED`], intersected with the store the same
    way and for the same reason [`published`] is — a caller wants records it can
    read. This is the whole input to [`protected_keys`], so a record is preserved
    because a list names it and never because a folder exists.
    """
    held = set(stamps())
    named = list(PUBLISHED) + [stamp for stamp in KEPT_UNPUBLISHED if stamp not in set(PUBLISHED)]
    return sorted(stamp for stamp in named if stamp in held)


def latest() -> str:
    """The newest PUBLISHED gallery, which is what an unstamped read means.

    **Published and not merely newest**, Matt's ruling of 2026-09-04. An
    unstamped read is a reader who has not said which gallery they mean, and the
    honest default is the newest one a clone could also resolve — otherwise the
    next experimental record silently becomes the answer for every figure prompt,
    naming IDs that exist on one machine. An unpublished record is read by naming
    its stamp, which is the whole way it is reached.
    """
    held = published()
    if not held:
        unpublished = [stamp for stamp in stamps() if stamp not in set(PUBLISHED)]
        if unpublished:
            raise TentativeRefused(
                f"no PUBLISHED tentative gallery on this machine, though "
                f"{len(unpublished)} unpublished record(s) are in the store "
                f"({tracked_name(store_root())}): {', '.join(unpublished)}. Name one by "
                f"its stamp, or publish it — `curation.tentative.PUBLISHED` and the "
                f"negation lines in `.gitignore` are the list, and adding to it is "
                f"Matt's decision."
            )
        raise TentativeRefused(
            f"no tentative gallery has been recorded on this machine "
            f"({tracked_name(store_root())}). `curate solve record` writes one."
        )
    return held[-1]


def read_rows(stamp: str | None = None) -> list[dict]:
    """One record's seats, in seat order."""
    stamp = latest() if stamp is None else str(stamp)
    path = rows_path(stamp)
    if not path.is_file():
        raise TentativeRefused(f"no tentative gallery at {path}")
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def read_manifest(stamp: str | None = None) -> dict:
    """One record's manifest."""
    stamp = latest() if stamp is None else str(stamp)
    path = manifest_path(stamp)
    if not path.is_file():
        raise TentativeRefused(f"no manifest at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_recipes(stamp: str | None = None) -> dict:
    """`{key: recipe block}` for one record, off its own tracked [`RECIPES_NAME`].

    The **tracked** answer to what a seat is made of: no ledger, no pool, no
    store on this machine. A record that has not been written one refuses and
    names the command, because the alternative — falling through to the ledger —
    is exactly the silence this file exists to end. A clone would get an answer
    on the machine that has the pool and `null` everywhere else.
    """
    stamp = latest() if stamp is None else str(stamp)
    path = recipes_path(stamp)
    if not path.is_file():
        raise TentativeRefused(
            f"no recipe file at {tracked_name(path)}, so this record says which pictures "
            f"were seated and not what they are made of. `curate solve recipes --stamp "
            f"{stamp} --write` builds one out of the candidate ledger."
        )
    held: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        held[str(row["key"])] = row["recipe"]
    return held


def build_recipes(stamp: str | None = None) -> tuple[list[dict], dict]:
    """`(rows, readout)` — one `{schema, key, recipe}` per seat, off the ledger.

    **Every seat is checked before it is written**, twice. The stored block has to
    read back through [`recipes.of_record`] — which refuses a member that was
    defaulted rather than recorded — and the key that comes out of
    [`recipes.key_of`] has to be the seat's own. A row that fails either is not
    written and is counted with its reason: a recipe file whose keys do not
    recompute is a file that names different pictures under the record's names,
    which is worse than the record having no recipe file at all.

    A seat the ledger does not hold is the one gap this cannot close, and it is
    reported rather than skipped silently.
    """
    from fractal_wallpapers.curation import candidate_ledger
    from fractal_wallpapers.curation import recipes as recipes_module

    stamp = latest() if stamp is None else str(stamp)
    keys = [str(row["key"]) for row in read_rows(stamp)]
    held = candidate_ledger.by_key(keys)

    rows, absent, refused, autolevel_off = [], [], [], 0
    for key in keys:
        row = held.get(key)
        if row is None or not row.get("recipe"):
            absent.append(key)
            continue
        block = row["recipe"]
        try:
            recomputed = recipes_module.key_of(recipes_module.of_record(block))
        except recipes_module.RecipeError as why:
            refused.append({"key": key, "why": str(why)})
            continue
        if recomputed != key:
            refused.append({"key": key, "why": f"recomputes to {recomputed}"})
            continue
        if block.get("autolevel") is None:
            autolevel_off += 1
        rows.append({"schema": SCHEMA, "key": key, "recipe": block})
    return rows, {
        "stamp": stamp,
        "seats": len(keys),
        "written": len(rows),
        "not_in_the_ledger": absent,
        "refused": refused,
        # Not a gap. The operator acts on a mode KIND — `autolevel.applies_to` —
        # and the direct traps and the itinerary are not among them, so a seat in
        # one of those modes has no band in its identity to record. It re-renders
        # from this row exactly as it was made.
        "no_autolevel_because_the_mode_takes_none": autolevel_off,
    }


def write_recipes(stamp: str | None = None) -> tuple[Path, dict]:
    """Write one record's [`RECIPES_NAME`] out of the ledger, and say what it holds."""
    stamp = latest() if stamp is None else str(stamp)
    rows, readout = build_recipes(stamp)
    path = recipes_path(stamp)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path, {**readout, "bytes": path.stat().st_size, "wrote": tracked_name(path)}


# --------------------------------------------------------------------------- #
# The aliases.
# --------------------------------------------------------------------------- #
def aliases(keys) -> dict:
    """`{key: alias}` — [`ALIAS_LENGTH`] characters, lengthened where they collide.

    Every alias is unique within the record, and a lengthened one cannot collide
    with a short one from elsewhere: it begins with a prefix only its own
    colliding group holds, and inside that group the length was chosen to separate
    them. Deterministic and order-free — the same key set gives the same aliases
    whichever order it arrives in — so an alias printed in a report still names
    the same picture after the record is read again.
    """
    grouped: dict[str, list[str]] = {}
    for key in sorted({str(key) for key in keys}):
        grouped.setdefault(key[:ALIAS_LENGTH], []).append(key)
    out: dict[str, str] = {}
    for prefix, group in grouped.items():
        if len(group) == 1:
            out[group[0]] = prefix
            continue
        longest = max(len(key) for key in group)
        length = ALIAS_LENGTH
        while length < longest and len({key[:length] for key in group}) != len(group):
            length += 1
        for key in group:
            out[key] = key[:length]
    return out


# --------------------------------------------------------------------------- #
# The record.
# --------------------------------------------------------------------------- #
#: What a seat's `floor` column says about the colour floor. Three answers and
#: they are not the same fact.
#:
#: [`FLOOR_MANDATED`] is a seat the scarcity leg took **for** a cell floor: its
#: `seated_for` names a `cell_floor:` demand, so the floor is why this picture is
#: in the gallery at all. [`FLOOR_HOLDING`] is a seat some other leg placed that
#: the floor now **keeps**: it is dominant in a cell sitting at or below its
#: floor, so removing it would open a shortfall and the objective's tier 2
#: refuses every swap that would. [`FLOOR_FREE`] is a seat the floor has no
#: opinion about.
#:
#: The distinction is the evaluation question. *What did the floor drag in* is
#: answered by the first; *what is the floor now paying for* by the first and the
#: second together, because a mandated seat that a swap later replaced is a seat
#: the floor still bought.
FLOOR_MANDATED = "mandated"
FLOOR_HOLDING = "holding"
FLOOR_FREE = "no"


def _floor_marks(record: dict) -> dict:
    """`{cell: its floor}` for the cells at or below it. Empty where none ran."""
    block = ((record.get("shortfalls") or {}).get("cell_floors") or {}).get("per_cell") or {}
    return {
        str(cell): int(row["floor"])
        for cell, row in block.items()
        if int(row["seated"]) <= int(row["floor"])
    }


def rows_of(record: dict, centered: frozenset | None = None) -> list[dict]:
    """A solve record's seats as the rows this store keeps, in seat order.

    `centered` is the location-key set [`depth.centered_locations`] returns,
    passed in rather than read here so a caller recording more than one gallery
    pays the walk-ledger join once. `None` reads it.
    """
    from fractal_wallpapers.curation import depth

    seated = list(record.get("seated") or ())
    if centered is None:
        centered = depth.centered_locations()
    named = aliases(str(held["key"]) for held in seated)
    # The cells whose floor is unmet or exactly met, so a seat that charges one of
    # them is a seat the floor is holding. Off the record's own block and never
    # re-derived: this is a reading OF that record, not a second answer to it.
    binding = _floor_marks(record)
    out = []
    for seat, held in enumerate(seated):
        cells = [str(name) for name in (held.get("cells") or ())]
        families = [str(name) for name in (held.get("families") or ())]
        key = str(held["key"])
        why = str(held.get("seated_for") or "")
        floor_cells = sorted(cell for cell in cells if cell in binding)
        if why.startswith("cell_floor:"):
            floor = FLOOR_MANDATED
        elif floor_cells:
            floor = FLOOR_HOLDING
        else:
            floor = FLOOR_FREE
        out.append(
            {
                "schema": SCHEMA,
                "seat": seat,
                "key": key,
                "alias": named[key],
                "mode": held.get("mode"),
                # The seat's own settings, so `direct_trap_multiply@opacity=0.6`
                # and the bare mode are two rows here rather than one. FORWARD
                # ONLY: a record written before this carries no such field, and
                # `{}` is what a reader takes an absent one to mean — which is
                # also what a bare seat writes, so the two are the same row and
                # nothing tracked has to be rewritten to say so.
                "mode_params": dict(held.get("mode_params") or {}),
                "partition": held.get("partition"),
                "cell": cells[0] if cells else None,
                "hue_family": families[0] if families else None,
                "cells": cells,
                "families": families,
                # Which leg placed the seat and, off it, what the COLOUR FLOOR had
                # to do with the seat being here — see [`FLOOR_MANDATED`]. FORWARD
                # ONLY, as `mode_params` is: a record written before 2026-09-09
                # carries neither, and a reader takes an absent `floor` to mean the
                # pass carried no colour floor rather than that every seat was free
                # of it.
                "seated_for": held.get("seated_for"),
                # A row of `data/curation/pins.json`, seated before the seed without
                # asking a rule — see `curation/pins.py`. FORWARD ONLY: absent on a
                # record taken before 2026-09-19, and absent means `false`.
                "pinned": bool(held.get("pinned")),
                "floor": floor,
                "floor_cells": floor_cells,
                "centered": str(held.get("location")) in centered,
                # Joined at record time like `centered`, and off the seat rather
                # than off a second store read: `solve` already did the location
                # join, so re-reading it here would be a second answer to one
                # question. `None` is a place with no score and is not `false`.
                "spiral": held.get("spiral"),
                "p_spiral": held.get("p_spiral"),
                "rank": held.get("rank"),
                "p_ge4": held.get("p_ge4"),
                "location": held.get("location"),
                "picture": held.get("picture"),
            }
        )
    return out


def counts_of(rows: list[dict], column: str) -> dict:
    """`{value: seats}` for one column, largest first. `"null"` for a missing value."""
    tally: dict = {}
    for row in rows:
        value = row.get(column)
        name = "null" if value is None else str(value)
        tally[name] = tally.get(name, 0) + 1
    return dict(sorted(tally.items(), key=lambda item: (-item[1], item[0])))


def ledger_rows() -> int:
    """How many rows the live candidate ledger holds, counted rather than believed.

    Off the file and not off `data/curation/candidate_ledger/rows.manifest.json`:
    that manifest is what the last `save` mirrored, and a merge since then would
    make it a count of a different store than the one this gallery was solved over.
    """
    from fractal_wallpapers.curation import candidate_ledger

    path = candidate_ledger.rows_path()
    if not path.is_file():
        return 0
    with path.open("rb") as handle:
        return sum(1 for line in handle if line.strip())


def manifest_of(
    record: dict,
    rows: list[dict],
    stamp: str,
    solve_name: str | None = None,
    candidates=None,
    pool_refused: dict | None = None,
) -> dict:
    """What says whether two recorded galleries are comparable, and how this one did.

    The solve's own `config` block whole, rather than a restatement of it: every
    constant the leg read is already spelled there, and a second spelling here
    would be a second thing to keep true.

    **The diversity rule is the one thing beside it**, since 2026-09-11, and for
    the reason that sentence implies rather than against it: `config` carries no
    `rules` block, so the rule that decided two seats were different enough lived
    only on the solve record — which a published stamp does not carry. A themed
    record could not say which rule chose it. Carried whole from
    `record["rules"]["diversity"]`, so it is still one spelling; what changed is
    where it can be read.

    The **pool stamp** is taken here rather than read off the solve record, which
    does not carry one — [`growth.pool_stamp`] over the candidates the solve was
    handed, which is the same digest the growth sweep compares its runs on. A
    caller with no candidates records `null` and says so, because a stamp that was
    not measured is worse than a stamp that is missing.
    """
    from fractal_wallpapers.curation import candidate_ledger, growth

    pool = dict(record.get("pool") or {})
    asked = int((record.get("config") or {}).get("n") or 0)
    filled = int(record.get("filled") or 0)
    places = None if candidates is None else len({held.location for held in candidates})
    return {
        "schema": SCHEMA,
        "stamp": str(stamp),
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_commit": growth.source_commit(),
        "solve": {
            "name": None if solve_name is None else str(solve_name),
            "record": None if solve_name is None else tracked_name(_solve_record_path(solve_name)),
            "taken_at": record.get("taken_at"),
            "seconds": record.get("seconds"),
            "config": record.get("config"),
            # The diversity rule, beside `config` and not inside it, because it is
            # the solve record's own `rules.diversity` block carried whole — the
            # rule's name, its threshold and its neighbour count — and restating
            # any of those here would be the second spelling the docstring above
            # refuses. It is on the MANIFEST because `config` never carried a
            # `rules` block and the solve record a published stamp does not carry
            # is the only other place it lives, so a themed record could not say
            # which rule chose it. `null` is a real answer and is written rather
            # than omitted: it is a pass that ran with no diversity rule at all.
            "diversity": (record.get("rules") or {}).get("diversity"),
            "diversity_is": SCHEMA_NOTES["diversity_is"],
            # The solve record's `pins` block whole, for `diversity`'s reason: a
            # published stamp does not carry the solve record, and a gallery that
            # seated rows without asking any rule has to be able to say which. Absent
            # on a record taken before 2026-09-19, which pinned nothing.
            "pins": record.get("pins"),
        },
        "pool": {
            "stamp": None if candidates is None else growth.pool_stamp(candidates),
            "stamp_is": SCHEMA_NOTES["stamp_is"],
            "candidates": None if candidates is None else len(candidates),
            "locations": places,
            # `reachable_clusters` since 2026-09-09, when the `--locations` cut moved
            # after the fold and started cutting clusters — `solve.strongest_clusters`.
            # The old name is read as a fallback so a manifest rebuilt from a record
            # taken before that carries its number rather than a null.
            "reachable_clusters": pool.get("reachable_clusters", pool.get("reachable_locations")),
            "refused": dict(pool_refused) if pool_refused is not None else pool.get("refused"),
            "ledger_rows": ledger_rows(),
            "ledger_path": tracked_name(candidate_ledger.rows_path()),
        },
        "seats": {
            "asked": asked,
            "filled": filled,
            "shortfall": asked - filled,
            "recorded": len(rows),
        },
        "shortfalls": record.get("shortfalls"),
        "counts": {
            "mode": counts_of(rows, "mode"),
            "hue_family": counts_of(rows, "hue_family"),
            "cell": counts_of(rows, "cell"),
            "partition": counts_of(rows, "partition"),
            "centered": counts_of(rows, "centered"),
            "spiral": counts_of(rows, "spiral"),
        },
    }


def _solve_record_path(name: str) -> Path:
    from fractal_wallpapers.curation import solve

    return solve.solve_dir(str(name)) / "solve.json"


def write(
    record: dict,
    candidates=None,
    stamp: str | None = None,
    solve_name: str | None = None,
    pool_refused: dict | None = None,
    log=print,
) -> Path:
    """Record one solve as a tentative gallery. Returns the folder.

    Both files are written to `.writing` names and renamed together, the manifest
    first — so a stamp [`stamps`] can see is a stamp whose rows *and* manifest are
    both whole, and a half-written record can never reach a resolver.

    **A stamp is written once and never over.** The IDs in it are what a figure
    prompt names, so re-recording under the same stamp is refused rather than
    merged: a page whose aliases moved under a reader is worse than a second
    folder.
    """
    stamp = stamp_now() if stamp is None else str(stamp)
    directory = gallery_dir(stamp)
    if (directory / ROWS_NAME).is_file():
        raise TentativeRefused(
            f"{tracked_name(directory)} is already a recorded gallery. A stamp is written "
            "once and never over: the IDs in it are what a figure prompt names."
        )
    rows = rows_of(record)
    manifest = manifest_of(
        record,
        rows,
        stamp,
        solve_name=solve_name,
        candidates=candidates,
        pool_refused=pool_refused,
    )
    directory.mkdir(parents=True, exist_ok=True)
    rows_writing = directory / (ROWS_NAME + ".writing")
    manifest_writing = directory / (MANIFEST_NAME + ".writing")
    with rows_writing.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    manifest_writing.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    manifest_writing.replace(directory / MANIFEST_NAME)
    rows_writing.replace(directory / ROWS_NAME)
    log(
        f"[tentative] {len(rows):,} seat(s) recorded at {tracked_name(directory)}; "
        f"{manifest['seats']['shortfall']} short of {manifest['seats']['asked']}"
    )
    return directory


# --------------------------------------------------------------------------- #
# The protection.
# --------------------------------------------------------------------------- #
def protected_keys() -> set:
    """Every recipe key a **kept** gallery seats, and every pin. **What retention must keep.**

    Over every stamp on [`kept`] and not only the newest, because the point of
    recording a gallery worth keeping is that its IDs stay resolvable — an older
    record whose keys the rank let go would be a page of broken thumbnails and a
    resolver answering nothing.

    ⚠ **Over [`kept`] and not over [`stamps`], since 2026-09-13.** It swept the
    whole store before that, which made preservation a property of a folder
    existing: a leg that recorded a gallery to measure one number against left
    behind an artifact pinning thousands of candidate rows, and no prune's output
    said which record was holding a key. Discarding an unpublished record is the
    default and this is what makes that default cost nothing — an off-list record
    stays readable by naming its stamp and simply stops voting on retention.

    Cheap by construction: a stamp is a few hundred to a few thousand short lines,
    and the keep list is shorter than the store. Tolerant of a folder it cannot
    parse, because [`candidate_ledger.prune`] calls this and a prune must not be
    stopped by a browser's store.
    """
    out: set = set()
    for stamp in kept():
        try:
            out |= {str(row["key"]) for row in read_rows(stamp)}
        except (TentativeRefused, ValueError, KeyError):
            continue
    # And every PINNED row, since 2026-09-19: a pin is a row every solve seats, so a
    # prune that took one would empty a seat the list promises. Off the resolution,
    # tolerant of it being unreadable for the reason above.
    import contextlib

    from fractal_wallpapers.curation import pins

    with contextlib.suppress(ValueError, KeyError, TypeError):
        out |= {str(pin["key"]) for pin in (pins.read() or {}).get("pins") or () if pin.get("key")}
    return out


# --------------------------------------------------------------------------- #
# The resolver.
# --------------------------------------------------------------------------- #
def resolve(names, stamp: str | None = None) -> list[dict]:
    """`[{name, found, row, recipe, ...}]` for each ID or alias asked for, in order.

    An unknown name is a row saying so rather than a refusal: a comma list of ten
    aliases with one typo in it should still answer for the nine, and what a miss
    is worth is the caller's decision.

    The recipe comes from the record's own [`RECIPES_NAME`] where it has one and
    from the candidate ledger where it does not — a seat row is what a *rule*
    reads and a figure prompt needs what a *render* reads, and the tracked file is
    the only one of the two a clone has. The ledger is one streamed pass for the
    whole list.

    **It refuses rather than answering `"recipe": null`.** A record with neither
    file behind it used to return a row per name with a null recipe and exit 0,
    which reads as *this seat has no recipe* where the truth is *this machine has
    nothing to look it up in* — the first is a fact about a picture and the second
    is a missing store, and the command said the wrong one. [`_recipe_source`]
    names what is absent.
    """
    stamp = latest() if stamp is None else str(stamp)
    rows = read_rows(stamp)
    by_alias = {str(row["alias"]): row for row in rows}
    by_key = {str(row["key"]): row for row in rows}
    wanted = [str(name).strip() for name in names if str(name).strip()]
    found = {name: by_key.get(name) or by_alias.get(name) for name in wanted}
    source, recipes = _recipe_source(stamp, {row["key"] for row in found.values() if row})
    return [
        {
            "name": name,
            "stamp": stamp,
            "found": found[name] is not None,
            "row": found[name],
            "recipe": recipes.get(str(found[name]["key"])) if found[name] else None,
            "recipe_from": source,
            "picture": (found[name] or {}).get("picture"),
            "picture_on_disk": _on_disk(found[name]),
        }
        for name in wanted
    ]


def _recipe_source(stamp: str, keys) -> tuple[str, dict]:
    """`(where it came from, {key: recipe})` — the tracked file, else the ledger.

    The tracked file first, because it is what a clone has and because it is the
    record's own statement about its seats rather than a lookup in a store that
    has moved since. The ledger is the fallback for the seven published stamps
    that have no recipe file and for every unpublished record.

    Refuses when neither is there. The two absences are named separately: one is
    fixed by a command in this repository and the other by having the pool.
    """
    from fractal_wallpapers.curation import candidate_ledger

    if recipes_path(stamp).is_file():
        held = read_recipes(stamp)
        return tracked_name(recipes_path(stamp)), {
            key: held[key] for key in map(str, keys) if key in held
        }
    ledger = candidate_ledger.rows_path()
    if not ledger.is_file():
        raise TentativeRefused(
            f"a recipe was asked for and there is nothing on this machine to read one out "
            f"of. {stamp} has no {RECIPES_NAME} ({tracked_name(recipes_path(stamp))}) and "
            f"the candidate ledger is not here either ({tracked_name(ledger)}). A clone gets "
            f"the recipe file for a record that was written one — `curate solve recipes "
            f"--stamp {stamp} --write` writes it on a machine that holds the pool. It is NOT "
            f"a fact about these seats: every one of them was made from a recipe."
        )
    return tracked_name(ledger), {
        key: (row or {}).get("recipe") for key, row in candidate_ledger.by_key(keys).items()
    }


def _on_disk(row: dict | None, tiers: Tiers | None = None) -> bool | None:
    """Whether one row's stored picture is on this machine; `None` for no picture.

    `tiers` for a caller asking over a whole record — a page of an n=2000 record
    asks this and [`thumbnail_href`] once each per row, and resolving the tiers
    per call is 246x per ask (see [`fractal_wallpapers.paths.rehome`])."""
    if not row or not row.get("picture"):
        return None
    resolved = rehome(row["picture"], tiers)
    return bool(resolved is not None and resolved.is_file())


# --------------------------------------------------------------------------- #
# The page.
# --------------------------------------------------------------------------- #
def thumbnail_href(picture, directory: Path, tiers: Tiers | None = None) -> str:
    """One stored picture as the page refers to it: relative, forward slashes.

    Relative rather than absolute so the folder can be copied or synced elsewhere
    and still open. A picture the relative spelling cannot reach — another drive
    letter, which Windows has no relative form for — falls back to a `file://`
    URL, which still opens here and says plainly that it is machine-local.
    """
    resolved = rehome(picture, tiers)
    if resolved is None:
        resolved = Path(str(picture))
    try:
        return Path(os.path.relpath(resolved, directory)).as_posix()
    except ValueError:
        return resolved.absolute().as_uri()


def page(stamp: str | None = None, out: Path | None = None, log=print) -> Path:
    """Write `index.html` beside a record's rows. Returns the page.

    Self-contained: the rows are embedded, the styling is inline, and the only
    external references are the relative thumbnails. Nothing is fetched and no
    script is loaded from anywhere, because the page is opened over `file://`
    where both fail.

    **The two tracked files are all it REQUIRES**, which is what makes the page a
    derivation rather than part of the record: `curate solve browse <stamp>` writes
    it again on any clone that has them, which is why the page itself is not
    tracked. `record` calls this too, so a fresh record still lands with its page
    beside it.

    It *reads* one more thing where this machine has it — the neutral embedding
    store, for [`page_order`]'s distance term — and reads it **optionally**: with no
    store the presentation order is the attribute terms alone and the page's header
    says which basis it used. That is the one way the claim above is narrower than
    it was, and it is narrower on purpose: an order that needed an untracked store
    would make the page undroppable.

    `out` writes the same page somewhere else — a sheet under `scratch/` for one
    reading, say — with every thumbnail resolved **relative to where it lands**,
    which is the whole reason this is a parameter rather than a copy afterwards:
    an `index.html` moved by hand points at nothing. It is the same derivation
    either way and the record's own page is left where it is.
    """
    stamp = latest() if stamp is None else str(stamp)
    path = page_path(stamp) if out is None else Path(out)
    directory = path.parent
    directory.mkdir(parents=True, exist_ok=True)
    rows = read_rows(stamp)
    manifest = read_manifest(stamp)
    # Two resolutions a row over a record that reaches two thousand of them, so
    # the tiers are read once here rather than four thousand times below.
    tiers = Tiers.current()
    # The release-geometry picture where the record has one. Resolved here rather
    # than by the page, because `file://` cannot look in a directory: a seat with
    # no full picture has to arrive with an empty string and be laid out as the
    # candidate alone. `curate solve fulls <stamp>` is what fills that in.
    full = fulls.index(
        [row.get("key") for row in rows], log=lambda _line: None, pin_dir=fulls_dir(stamp)
    )
    shown = [
        {
            **row,
            "src": thumbnail_href(row.get("picture"), directory, tiers),
            "full": (
                fulls.href(full[row["key"]], directory, tiers) if row.get("key") in full else ""
            ),
        }
        for row in rows
    ]
    missing = sum(1 for row in rows if _on_disk(row, tiers) is not True)
    at_full = sum(1 for row in shown if row["full"])
    # The presentation order: derived here, from the rows, changing none of them.
    # `order` is a column on the EMBEDDED copy and never on `gallery.jsonl` — the
    # record is untouched and an existing one gets today's order on its next build.
    vectors = page_order.vectors_for(rows)
    for at, held in enumerate(page_order.order(rows, vectors)):
        shown[held]["order"] = at
    writing = Path(str(path) + ".writing")
    writing.write_text(
        _PAGE.replace("__STAMP__", html.escape(str(stamp)))
        .replace("__SEATS__", str(len(rows)))
        .replace("__ASKED__", str(manifest["seats"]["asked"]))
        .replace("__NAME__", html.escape(str(manifest.get("solve", {}).get("name") or "")))
        .replace("__MISSING__", str(missing))
        .replace("__AT_FULL__", str(at_full))
        .replace("__FULL_REGIME__", html.escape(fulls.REGIME.spelled))
        .replace("__ORDERED_BY__", html.escape(page_order.basis(vectors)))
        .replace("__ROWS__", json.dumps(shown, ensure_ascii=False)),
        encoding="utf-8",
        newline="\n",
    )
    writing.replace(path)
    log(f"[tentative] {tracked_name(path)}: {len(rows):,} tile(s), {missing} without a picture")
    return path


#: The browser, as one string with nine substitutions. Kept here rather than in a
#: tracked asset file because it is the only page this project writes for a person
#: to drive, and a second file would be a second thing to find. The substitutions
#: are `__ROWS__`, `__STAMP__`, `__NAME__`, `__SEATS__`, `__ASKED__`, `__MISSING__`,
#: `__AT_FULL__`, `__FULL_REGIME__` and `__ORDERED_BY__`, all filled by [`page`]
#: and none of them by the reader.
_PAGE = (
    """<!doctype html>
<meta charset="utf-8">
<title>tentative gallery __STAMP__</title>
<style>"""
    + page_module.STYLE
    + """
  :root { color-scheme: dark; }
  body { margin: 0; background: var(--ground); color: var(--ink);
         font: 13px/1.45 ui-sans-serif, system-ui, "Segoe UI", sans-serif; }
  header { position: sticky; top: 0; z-index: 2; background: var(--raised);
           border-bottom: 1px solid var(--rule); padding: 10px 14px; }
  h1 { font-size: 14px; margin: 0 0 8px; font-weight: 600; letter-spacing: .02em; }
  h1 span { color: var(--muted); font-weight: 400; }
  .controls { display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-start; }
  fieldset { border: 1px solid var(--rule); border-radius: 5px; margin: 0; padding: 5px 8px 7px;
             max-height: 132px; overflow-y: auto; }
  legend { color: var(--muted); font-size: 11px; text-transform: uppercase;
           letter-spacing: .06em; padding: 0 4px; }
  label { display: block; white-space: nowrap; cursor: pointer; }
  label input { vertical-align: -1px; margin-right: 4px; }
  label b { color: var(--muted); font-weight: 400; }
  input[type=search], select { background: var(--ground); color: var(--ink);
                               border: 1px solid var(--rule);
                               border-radius: 4px; padding: 5px 7px; font: inherit; }
  button { background: #2b313b; color: var(--ink); border: 1px solid #3a414d; border-radius: 4px;
           padding: 5px 9px; font: inherit; cursor: pointer; }
  button:hover { background: #3a414d; }
  #tray { margin-top: 8px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
          color: var(--muted); }
  #tray code { color: #cfd4db; }
  main { display: grid; gap: 10px; padding: 12px 14px 60px;
         grid-template-columns: repeat(auto-fill, minmax(224px, 1fr)); }
  h2 { grid-column: 1 / -1; margin: 14px 0 0; padding-bottom: 5px; font-size: 12px;
       font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: #9fc2ff;
       border-bottom: 1px solid var(--rule); }
  h2:first-child { margin-top: 0; }
  h2 b { color: var(--muted); font-weight: 400; text-transform: none; letter-spacing: 0; }
  .tile { border: 1px solid var(--rule); border-radius: 6px; overflow: hidden;
          background: var(--raised); }
  .tile.picked { border-color: #6f9ef8; box-shadow: 0 0 0 1px #6f9ef8; }
  .tile.pinned { border-color: #d4a73a; }
  .tile.pinned.picked { box-shadow: 0 0 0 1px #6f9ef8; }
  .pin { margin-top: 4px; font-size: 11px; border-radius: 3px; padding: 1px 5px;
         display: inline-block; background: #3a3114; color: #f0cf6a;
         border: 1px solid #6b5a1d; }
  .tile img { display: block; width: 100%; aspect-ratio: 16/9; object-fit: cover;
              background: var(--well); cursor: zoom-in; }
  #hires-label { margin-top: 6px; border-top: 1px solid var(--rule); padding-top: 5px;
                 color: var(--muted); }
  #hires-label b { color: var(--accent); font-weight: 400; }
  .tile .gone { display: grid; place-items: center; width: 100%; aspect-ratio: 16/9;
                background: var(--well); color: #6b7280; cursor: pointer; }
  .meta { padding: 6px 8px 8px; }
  .meta .line { display: flex; justify-content: space-between; gap: 8px; }
  .pick { vertical-align: -1px; margin-right: 5px; cursor: pointer; }
  .alias { font-family: ui-monospace, "Cascadia Mono", Consolas, monospace; color: #9fc2ff;
           cursor: pointer; border-bottom: 1px dotted #47536b; }
  .alias.flash { color: #7ee08a; border-bottom-color: #7ee08a; }
  .dim { color: var(--muted); }
  .floor { margin-top: 4px; font-size: 11px; border-radius: 3px; padding: 1px 5px;
           display: inline-block; }
  .floor.mandated { background: #3a2a14; color: #f0b45e; border: 1px solid #6b4a1d; }
  .floor.holding { background: #1d2a20; color: #7ec294; border: 1px solid #33513d; }
  .num { font-family: ui-monospace, "Cascadia Mono", Consolas, monospace; }
  #empty { padding: 24px 14px; color: var(--muted); }
  /* The full-size view. A candidate picture is 640x360, so `contain` scales it up
     to whatever the screen gives rather than pinning it at its stored pixels: the
     point of opening one is judging it larger than a 224px tile, not counting its
     pixels. Fixed and above everything, because it is opened over `file://` where
     there is no second window to put it in. */
  #lb { position: fixed; inset: 0; z-index: 9; background: #0b0d10ee; display: none;
        grid-template-rows: 1fr auto; cursor: zoom-out; }
  #lb.open { display: grid; }
  #lb img { min-width: 0; min-height: 0; width: 100%; height: 100%;
            object-fit: contain; }
  #lb .bar { padding: 8px 14px 12px; text-align: center; color: var(--muted); }
  #lb .bar b { color: #9fc2ff; font-weight: 600; }
</style>
<header>
  <h1>tentative gallery __STAMP__ <span>&middot; __NAME__
      &middot; __SEATS__ of __ASKED__ seat(s) filled
      &middot; __MISSING__ without a picture on this disk
      &middot; presented on __ORDERED_BY__</span></h1>
  <div class="controls">
    <fieldset id="f-mode"><legend>mode</legend></fieldset>
    <fieldset id="f-hue_family"><legend>hue family</legend></fieldset>
    <fieldset id="f-cell"><legend>colour cell</legend></fieldset>
    <fieldset id="f-partition"><legend>partition</legend></fieldset>
    <fieldset id="f-centered"><legend>centered</legend></fieldset>
    <fieldset id="f-spiral"><legend>spiral</legend></fieldset>
    <fieldset id="f-floor"><legend>colour floor</legend></fieldset>
    <fieldset id="f-pinned"><legend>pinned</legend></fieldset>
    <fieldset><legend>find, group &amp; sort</legend>
      <input type="search" id="q" placeholder="ID or alias" size="18">
      <select id="group">
        <option value="">no grouping</option>
        <option value="mode">group by mode</option>
        <option value="cell">group by colour cell</option>
        <option value="hue_family">group by hue family</option>
        <option value="partition">group by partition</option>
        <option value="floor">group by colour floor</option>
      </select>
      <select id="sort">
        <option value="order">presentation order</option>
        <option value="rank">rank, best first</option>
        <option value="seat">seat order</option>
        <option value="p_ge4">P(&ge;4), best first</option>
      </select>
      <button id="clear">clear filters</button>
      <label id="hires-label"><input type="checkbox" id="hires">full resolution
        <b>__FULL_REGIME__</b></label>
    </fieldset>
  </div>
  <div id="tray">
    <b id="count"></b>
    <span>selected <code id="picked">0</code></span>
    <button id="copy">copy selected IDs</button>
    <button id="drop">clear selection</button>
    <span id="says"></span>
    <span class="dim">click a picture for the full size &middot;
      <code>&larr;</code> <code>&rarr;</code> step, <code>esc</code> closes</span>
    <span class="dim" id="fulls">__AT_FULL__ of __SEATS__ seats have a __FULL_REGIME__
      picture</span>
  </div>
</header>
<main id="grid"></main>
<div id="empty" hidden>Nothing matches these filters.</div>
<div id="lb"><img alt=""><div class="bar"></div></div>
<script>
const ROWS = __ROWS__;
const FACETS = ["mode", "hue_family", "cell", "partition", "centered", "spiral", "floor",
  "pinned"];
// `cells` and `families` are lists because dominance is thresholded: a picture
// can be dominant in several, and filtering on the leading one alone would hide
// a green picture from the green filter whenever teal happened to lead it.
const PLURAL = {hue_family: "families", cell: "cells"};
const NONE = "\\u2014";
const picked = new Set();
const chosen = {};

function valuesOf(row, facet) {
  const many = PLURAL[facet];
  if (many && Array.isArray(row[many]) && row[many].length) return row[many].map(String);
  const one = row[facet];
  return [one === null || one === undefined ? NONE : String(one)];
}

for (const facet of FACETS) {
  const tally = new Map();
  for (const row of ROWS) {
    for (const value of valuesOf(row, facet)) tally.set(value, (tally.get(value) || 0) + 1);
  }
  const box = document.getElementById("f-" + facet);
  chosen[facet] = new Set();
  for (const [value, n] of [...tally].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))) {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = value;
    input.addEventListener("change", () => {
      if (input.checked) { chosen[facet].add(value); } else { chosen[facet].delete(value); }
      draw();
    });
    const count = document.createElement("b");
    count.textContent = n;
    label.append(input, document.createTextNode(value + " "), count);
    box.append(label);
  }
}

function matches(row) {
  for (const facet of FACETS) {
    const want = chosen[facet];
    if (want.size && !valuesOf(row, facet).some((value) => want.has(value))) return false;
  }
  const q = document.getElementById("q").value.trim().toLowerCase();
  if (q && !row.key.toLowerCase().includes(q) && !row.alias.toLowerCase().includes(q)) {
    return false;
  }
  return true;
}

function flash(node, text) {
  const was = node.textContent;
  node.classList.add("flash");
  node.textContent = text;
  setTimeout(() => { node.classList.remove("flash"); node.textContent = was; }, 700);
}

// `navigator.clipboard` is undefined over `file://` in some browsers, so the page
// carries its own fallback rather than silently copying nothing.
function copy(text) {
  const fallback = () => {
    const box = document.createElement("textarea");
    box.value = text;
    document.body.append(box);
    box.select();
    try { document.execCommand("copy"); } finally { box.remove(); }
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).catch(fallback);
  } else {
    fallback();
  }
}

// WHICH picture a tile loads. The candidate by default, because a thousand
// 1280x720 JPEGs is a page that does not open; `#hires` swaps the grid over to
// the release-geometry render where the record has one. A seat with no full
// picture keeps its candidate under the toggle rather than going blank — the
// toggle is an upgrade where one exists and never a filter.
let hires = false;

function pictureOf(row) {
  return (hires && row.full) ? row.full : (row.src || row.full || "");
}

function tile(row) {
  const card = document.createElement("div");
  card.className = "tile" + (row.pinned ? " pinned" : "") + (picked.has(row.key) ? " picked" : "");
  const pick = () => {
    if (picked.has(row.key)) { picked.delete(row.key); } else { picked.add(row.key); }
    card.classList.toggle("picked", picked.has(row.key));
    box.checked = picked.has(row.key);
    document.getElementById("picked").textContent = picked.size;
  };
  if (row.src || row.full) {
    const img = document.createElement("img");
    img.src = pictureOf(row);
    img.loading = "lazy";
    img.title = "click for the full size";
    img.addEventListener("error", () => {
      const gone = document.createElement("div");
      gone.className = "gone";
      gone.textContent = "no picture on this disk";
      img.replaceWith(gone);
      gone.addEventListener("click", pick);
    });
    // The picture opens; the checkbox beside the alias selects. The two were one
    // gesture while a tile was the only size there was, and a click that both
    // opened and selected would put a stray ID in the tray on every look.
    img.addEventListener("click", () => openAt(shown.indexOf(row)));
    card.append(img);
  }
  const box = document.createElement("input");
  box.type = "checkbox";
  box.className = "pick";
  box.checked = picked.has(row.key);
  box.title = "select this seat";
  box.addEventListener("change", pick);
  const meta = document.createElement("div");
  meta.className = "meta";
  const top = document.createElement("div");
  top.className = "line";
  const alias = document.createElement("span");
  alias.className = "alias";
  alias.textContent = row.alias;
  alias.title = row.key + " \\u2014 click to copy the full ID";
  alias.addEventListener("click", () => { copy(row.key); flash(alias, "copied"); });
  const left = document.createElement("span");
  left.append(box, alias);
  const score = document.createElement("span");
  score.className = "num dim";
  score.title = "rank key / P(\\u22654)";
  score.textContent = (row.rank === null ? NONE : Number(row.rank).toFixed(3)) + " / " +
    (row.p_ge4 === null ? NONE : Number(row.p_ge4).toFixed(3));
  top.append(left, score);
  const one = document.createElement("div");
  one.className = "dim";
  // EVERY cell the seat is dominant in, not the leading one: the colour floor is
  // stated per cell and a seat charges 2.1 of them on average, so a tile showing
  // one membership cannot be checked against a floor at all.
  one.textContent = row.mode + " \\u00b7 " + (row.hue_family || NONE) +
    " \\u00b7 " + ((row.cells && row.cells.length) ? row.cells.join(" + ") : NONE);
  const two = document.createElement("div");
  two.className = "dim";
  two.textContent = row.partition + (row.centered ? " \\u00b7 centered" : "") +
    " \\u00b7 seat " + row.seat;
  meta.append(top, one, two);
  // A pinned seat was placed by the list and not by any rule, so it must not look
  // like a seat the solve chose: data/curation/pins.json is where it came from.
  if (row.pinned) {
    const mark = document.createElement("div");
    mark.className = "pin";
    mark.textContent = "pinned";
    mark.title = "a row of the pinned list (data/curation/pins.json), seated before the " +
      "seed and never swapped out";
    meta.append(mark);
  }
  // The floor mark, and only where the pass carried a floor at all. A seat the
  // floor bought must not look like every other seat: that is the whole question
  // this page is being read to answer.
  if (row.floor === "mandated" || row.floor === "holding") {
    const mark = document.createElement("div");
    mark.className = "floor " + row.floor;
    mark.textContent = row.floor === "mandated"
      ? "floor seated this \\u2014 " + (row.seated_for || "").replace("cell_floor:", "")
      : "floor holds this \\u2014 " + (row.floor_cells || []).join(", ");
    mark.title = row.floor === "mandated"
      ? "the scarcity leg took this seat FOR a cell floor: the floor is why it is here"
      : "another leg placed it, and it is dominant in a cell at or below its floor \\u2014 " +
        "so the objective's shortfall tier now refuses every swap that would remove it";
    meta.append(mark);
  }
  card.append(meta);
  return card;
}

// Grouping reads the LEADING cell or family, never the dominance list the filters
// read. A row dominant in three cells would otherwise stand in three sections, the
// section counts would sum past the seat count, and stepping would visit it three
// times. Filter on a cell to see every seat that reaches it; group to cut the
// seats into sections once each.
function groupOf(row, facet) {
  const one = row[facet];
  return one === null || one === undefined ? NONE : String(one);
}

//: the drawn order, flattened across sections. `openAt` steps along this and not
//: along ROWS, so the full-size view walks exactly what the grid is showing.
let shown = [];

function draw() {
  const held = ROWS.filter(matches);
  const key = document.getElementById("sort").value;
  // `order` and `seat` are positions and read ASCENDING; `rank` and `p_ge4` are
  // scores and read best-first. A row with no position sorts to the end rather than
  // to the front, which is where a record written before this column existed goes.
  held.sort((a, b) => key === "seat" ? a.seat - b.seat
    : key === "order" ? (a.order ?? Infinity) - (b.order ?? Infinity)
    : (b[key] ?? -1) - (a[key] ?? -1));
  const facet = document.getElementById("group").value;
  const bins = new Map();
  for (const row of held) {
    const name = facet ? groupOf(row, facet) : "";
    if (!bins.has(name)) bins.set(name, []);
    bins.get(name).push(row);
  }
  const order = facet
    ? [...bins].sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]))
    : [...bins];
  const out = [];
  shown = [];
  for (const [name, rows] of order) {
    if (facet) {
      const head = document.createElement("h2");
      const n = document.createElement("b");
      n.textContent = "  " + rows.length + " seat(s)";
      head.append(document.createTextNode(name), n);
      out.push(head);
    }
    for (const row of rows) { shown.push(row); out.push(tile(row)); }
  }
  document.getElementById("grid").replaceChildren(...out);
  document.getElementById("empty").hidden = held.length > 0;
  document.getElementById("count").textContent = held.length + " of " + ROWS.length + " shown" +
    (facet ? " in " + bins.size + " group(s)" : "");
  document.getElementById("picked").textContent = picked.size;
}

//: which of [`shown`] the full-size view is on, or -1 when it is closed.
let at = -1;

function openAt(i) {
  if (i < 0 || i >= shown.length) return;
  at = i;
  const row = shown[at];
  const view = document.getElementById("lb");
  // ALWAYS the release-geometry picture where there is one, toggle or no toggle.
  // The header has said "click a picture for the full size" since this page
  // existed and could only ever show the 640x360 candidate blown up.
  view.querySelector("img").src = row.full || row.src || "";
  const where = document.createElement("span");
  where.textContent = (at + 1) + " of " + shown.length + "  \\u00b7  ";
  const who = document.createElement("b");
  who.textContent = row.alias;
  const what = document.createElement("span");
  what.textContent = "  \\u00b7  " + row.mode +
    " \\u00b7 " + ((row.cells && row.cells.length) ? row.cells.join(" + ") : NONE) +
    " \\u00b7 " + row.partition + (row.centered ? " \\u00b7 centered" : "") +
    " \\u00b7 seat " + row.seat +
    " \\u00b7 rank " + (row.rank === null ? NONE : Number(row.rank).toFixed(3)) +
    (row.pinned ? "  \\u00b7  pinned" : "") +
    (row.floor === "mandated" ? "  \\u00b7  seated BY a colour floor"
      : row.floor === "holding" ? "  \\u00b7  held by a colour floor" : "");
  view.querySelector(".bar").replaceChildren(where, who, what);
  view.classList.add("open");
}

function step(by) {
  if (at >= 0) openAt(Math.min(shown.length - 1, Math.max(0, at + by)));
}

function shut() {
  document.getElementById("lb").classList.remove("open");
  at = -1;
}

document.getElementById("lb").addEventListener("click", shut);
document.addEventListener("keydown", (event) => {
  if (at < 0) return;
  if (event.key === "Escape") { shut(); }
  else if (event.key === "ArrowRight") { step(1); }
  else if (event.key === "ArrowLeft") { step(-1); }
  else { return; }
  event.preventDefault();
});

document.getElementById("q").addEventListener("input", draw);
document.getElementById("sort").addEventListener("change", draw);
document.getElementById("group").addEventListener("change", draw);
// The resolution toggle is NOT a filter: it changes which picture a tile loads
// and never which tiles there are. So it is excluded from `clear filters` by
// name — the sweep below unchecks every box in the header, and a toggle swept by
// it would go off on screen while `hires` stayed on underneath.
document.getElementById("hires").addEventListener("change", (event) => {
  hires = event.target.checked;
  draw();
});
document.getElementById("clear").addEventListener("click", () => {
  for (const facet of FACETS) chosen[facet].clear();
  for (const box of document.querySelectorAll("header input[type=checkbox]")) {
    if (box.id !== "hires") box.checked = false;
  }
  document.getElementById("q").value = "";
  draw();
});
document.getElementById("copy").addEventListener("click", () => {
  const says = document.getElementById("says");
  if (!picked.size) { says.textContent = "nothing selected"; return; }
  const order = ROWS.filter((row) => picked.has(row.key)).map((row) => row.key);
  copy(order.join(" "));
  says.textContent = "copied " + order.length + " ID(s)";
  setTimeout(() => { says.textContent = ""; }, 1400);
});
document.getElementById("drop").addEventListener("click", () => { picked.clear(); draw(); });
draw();
</script>
"""
)


__all__ = [
    "ALIAS_LENGTH",
    "FLOOR_FREE",
    "FLOOR_HOLDING",
    "FLOOR_MANDATED",
    "FULLS_NAME",
    "MANIFEST_NAME",
    "PAGE_NAME",
    "RECIPES_NAME",
    "RECORDED_SEATS",
    "ROWS_NAME",
    "SCHEMA",
    "UNIT",
    "VIEWER_UNIT",
    "TentativeRefused",
    "aliases",
    "build_recipes",
    "counts_of",
    "fulls_dir",
    "gallery_dir",
    "latest",
    "ledger_rows",
    "manifest_of",
    "manifest_path",
    "page",
    "page_path",
    "protected_keys",
    "read_manifest",
    "read_recipes",
    "read_rows",
    "recipes_path",
    "resolve",
    "rows_of",
    "rows_path",
    "stamp_now",
    "stamps",
    "store_root",
    "thumbnail_href",
    "viewer_dir",
    "write",
    "write_recipes",
]
