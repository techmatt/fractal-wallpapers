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
the pool's own 640x360 candidate pictures.

Nothing here chooses anything. [`curation.solve`] does the choosing and this
records it, so a change in this module can never move a seat.

## Three properties, and each one is the reason for a piece of this

**The ID has to survive every later merge.** A ledger key names a recipe forever,
but [`candidate_ledger.prune`] runs inside every merge and drops the rows the
retention rank let go — with their pictures. A seat in a tentative gallery is
exactly the kind of row that rank can drop: it won its seat on the *gallery's*
objective, over a view, against the colour rules, and none of that is being in the
top three of its own (location, mode) pair. So a recorded gallery is a
**protection class** in the prune, [`candidate_ledger.RETAINED_TENTATIVE`], the
way a live release row is. Without it a figure prompt could name an alias whose
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
`partition` (text, off the seat); `cell` and `hue_family` (text, the *leading*
dominant colour cell and hue family, which is what a person means by "the green
one"); `cells` and `families` (lists, every name the picture is dominant in,
because dominance is thresholded and one picture carries more than one);
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

from fractal_wallpapers.paths import rehome, tracked_name, under

#: The schema every row and every manifest here carries.
SCHEMA = 1

#: The subtree a recorded gallery's stamped folder lands in.
UNIT = "tentative"

#: The three files one stamp holds.
ROWS_NAME = "gallery.jsonl"
MANIFEST_NAME = "manifest.json"
PAGE_NAME = "index.html"

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


def gallery_dir(stamp: str) -> Path:
    return store_root() / str(stamp)


def rows_path(stamp: str) -> Path:
    return gallery_dir(stamp) / ROWS_NAME


def manifest_path(stamp: str) -> Path:
    return gallery_dir(stamp) / MANIFEST_NAME


def page_path(stamp: str) -> Path:
    return gallery_dir(stamp) / PAGE_NAME


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


def latest() -> str:
    """The newest recorded gallery, which is what an unstamped read means."""
    held = stamps()
    if not held:
        raise TentativeRefused(
            f"no tentative gallery has been recorded on this machine "
            f"({tracked_name(store_root())}). `curate gallery record` writes one."
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
    out = []
    for seat, held in enumerate(seated):
        cells = [str(name) for name in (held.get("cells") or ())]
        families = [str(name) for name in (held.get("families") or ())]
        key = str(held["key"])
        out.append(
            {
                "schema": SCHEMA,
                "seat": seat,
                "key": key,
                "alias": named[key],
                "mode": held.get("mode"),
                "partition": held.get("partition"),
                "cell": cells[0] if cells else None,
                "hue_family": families[0] if families else None,
                "cells": cells,
                "families": families,
                "centered": str(held.get("location")) in centered,
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
        },
        "pool": {
            "stamp": None if candidates is None else growth.pool_stamp(candidates),
            "stamp_is": "sha256 over the sorted candidate keys, as `growth.pool_stamp` takes "
            "it. Two records carrying the same stamp were chosen over the same pool",
            "candidates": None if candidates is None else len(candidates),
            "locations": places,
            "reachable_locations": pool.get("reachable_locations"),
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
    """Every recipe key any recorded gallery seats. **What retention must keep.**

    Over every stamp and not only the newest, because the point of recording a
    gallery is that its IDs stay resolvable — an older record whose keys the rank
    let go would be a page of broken thumbnails and a resolver answering nothing.

    Cheap by construction: a stamp is a few hundred to a few thousand short lines,
    and there are as many stamps as there are galleries somebody decided to name.
    Tolerant of a folder it cannot parse, because [`candidate_ledger.prune`] calls
    this and a prune must not be stopped by a browser's store.
    """
    out: set = set()
    for stamp in stamps():
        try:
            out |= {str(row["key"]) for row in read_rows(stamp)}
        except (TentativeRefused, ValueError, KeyError):
            continue
    return out


# --------------------------------------------------------------------------- #
# The resolver.
# --------------------------------------------------------------------------- #
def resolve(names, stamp: str | None = None) -> list[dict]:
    """`[{name, found, row, recipe, ...}]` for each ID or alias asked for, in order.

    An unknown name is a row saying so rather than a refusal: a comma list of ten
    aliases with one typo in it should still answer for the nine, and what a miss
    is worth is the caller's decision.

    The recipe comes from the candidate ledger and not from the record, because a
    seat row is what a *rule* reads and a figure prompt needs what a *render*
    reads. One streamed pass of the ledger for the whole list.
    """
    from fractal_wallpapers.curation import candidate_ledger

    stamp = latest() if stamp is None else str(stamp)
    rows = read_rows(stamp)
    by_alias = {str(row["alias"]): row for row in rows}
    by_key = {str(row["key"]): row for row in rows}
    wanted = [str(name).strip() for name in names if str(name).strip()]
    found = {name: by_key.get(name) or by_alias.get(name) for name in wanted}
    recipes = candidate_ledger.by_key({row["key"] for row in found.values() if row})
    return [
        {
            "name": name,
            "stamp": stamp,
            "found": found[name] is not None,
            "row": found[name],
            "recipe": (recipes.get(str(found[name]["key"])) or {}).get("recipe")
            if found[name]
            else None,
            "picture": (found[name] or {}).get("picture"),
            "picture_on_disk": _on_disk(found[name]),
        }
        for name in wanted
    ]


def _on_disk(row: dict | None) -> bool | None:
    """Whether one row's stored picture is on this machine; `None` for no picture."""
    if not row or not row.get("picture"):
        return None
    resolved = rehome(row["picture"])
    return bool(resolved is not None and resolved.is_file())


# --------------------------------------------------------------------------- #
# The page.
# --------------------------------------------------------------------------- #
def thumbnail_href(picture, directory: Path) -> str:
    """One stored picture as the page refers to it: relative, forward slashes.

    Relative rather than absolute so the folder can be copied or synced elsewhere
    and still open. A picture the relative spelling cannot reach — another drive
    letter, which Windows has no relative form for — falls back to a `file://`
    URL, which still opens here and says plainly that it is machine-local.
    """
    resolved = rehome(picture)
    if resolved is None:
        resolved = Path(str(picture))
    try:
        return Path(os.path.relpath(resolved, directory)).as_posix()
    except ValueError:
        return resolved.absolute().as_uri()


def page(stamp: str | None = None, log=print) -> Path:
    """Write `index.html` beside a record's rows. Returns the page.

    Self-contained: the rows are embedded, the styling is inline, and the only
    external references are the relative thumbnails. Nothing is fetched and no
    script is loaded from anywhere, because the page is opened over `file://`
    where both fail.
    """
    stamp = latest() if stamp is None else str(stamp)
    directory = gallery_dir(stamp)
    rows = read_rows(stamp)
    manifest = read_manifest(stamp)
    shown = [{**row, "src": thumbnail_href(row.get("picture"), directory)} for row in rows]
    missing = sum(1 for row in rows if _on_disk(row) is not True)
    path = page_path(stamp)
    writing = Path(str(path) + ".writing")
    writing.write_text(
        _PAGE.replace("__STAMP__", html.escape(str(stamp)))
        .replace("__SEATS__", str(len(rows)))
        .replace("__ASKED__", str(manifest["seats"]["asked"]))
        .replace("__MISSING__", str(missing))
        .replace("__ROWS__", json.dumps(shown, ensure_ascii=False)),
        encoding="utf-8",
        newline="\n",
    )
    writing.replace(path)
    log(f"[tentative] {tracked_name(path)}: {len(rows):,} tile(s), {missing} without a picture")
    return path


#: The browser, as one string with four substitutions. Kept here rather than in a
#: tracked asset file because it is the only page this project writes for a person
#: to drive, and a second file would be a second thing to find. The substitutions
#: are `__ROWS__`, `__STAMP__`, `__SEATS__`, `__ASKED__` and `__MISSING__`, all
#: filled by [`page`] and none of them by the reader.
_PAGE = """<!doctype html>
<meta charset="utf-8">
<title>tentative gallery __STAMP__</title>
<style>
  :root { color-scheme: dark; }
  body { margin: 0; background: #14161a; color: #e6e8eb;
         font: 13px/1.45 ui-sans-serif, system-ui, "Segoe UI", sans-serif; }
  header { position: sticky; top: 0; z-index: 2; background: #1b1e24;
           border-bottom: 1px solid #2c313a; padding: 10px 14px; }
  h1 { font-size: 14px; margin: 0 0 8px; font-weight: 600; letter-spacing: .02em; }
  h1 span { color: #8a939f; font-weight: 400; }
  .controls { display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-start; }
  fieldset { border: 1px solid #2c313a; border-radius: 5px; margin: 0; padding: 5px 8px 7px;
             max-height: 132px; overflow-y: auto; }
  legend { color: #8a939f; font-size: 11px; text-transform: uppercase;
           letter-spacing: .06em; padding: 0 4px; }
  label { display: block; white-space: nowrap; cursor: pointer; }
  label input { vertical-align: -1px; margin-right: 4px; }
  label b { color: #8a939f; font-weight: 400; }
  input[type=search], select { background: #14161a; color: #e6e8eb; border: 1px solid #2c313a;
                               border-radius: 4px; padding: 5px 7px; font: inherit; }
  button { background: #2b313b; color: #e6e8eb; border: 1px solid #3a414d; border-radius: 4px;
           padding: 5px 9px; font: inherit; cursor: pointer; }
  button:hover { background: #3a414d; }
  #tray { margin-top: 8px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
          color: #8a939f; }
  #tray code { color: #cfd4db; }
  main { display: grid; gap: 10px; padding: 12px 14px 60px;
         grid-template-columns: repeat(auto-fill, minmax(224px, 1fr)); }
  .tile { border: 1px solid #2c313a; border-radius: 6px; overflow: hidden; background: #1b1e24; }
  .tile.picked { border-color: #6f9ef8; box-shadow: 0 0 0 1px #6f9ef8; }
  .tile img { display: block; width: 100%; aspect-ratio: 16/9; object-fit: cover;
              background: #0e1013; cursor: pointer; }
  .tile .gone { display: grid; place-items: center; width: 100%; aspect-ratio: 16/9;
                background: #0e1013; color: #6b7280; cursor: pointer; }
  .meta { padding: 6px 8px 8px; }
  .meta .line { display: flex; justify-content: space-between; gap: 8px; }
  .alias { font-family: ui-monospace, "Cascadia Mono", Consolas, monospace; color: #9fc2ff;
           cursor: pointer; border-bottom: 1px dotted #47536b; }
  .alias.flash { color: #7ee08a; border-bottom-color: #7ee08a; }
  .dim { color: #8a939f; }
  .num { font-family: ui-monospace, "Cascadia Mono", Consolas, monospace; }
  #empty { padding: 24px 14px; color: #8a939f; }
</style>
<header>
  <h1>tentative gallery __STAMP__ <span>&middot; __SEATS__ of __ASKED__ seat(s) filled
      &middot; __MISSING__ without a picture on this disk</span></h1>
  <div class="controls">
    <fieldset id="f-mode"><legend>mode</legend></fieldset>
    <fieldset id="f-hue_family"><legend>hue family</legend></fieldset>
    <fieldset id="f-cell"><legend>colour cell</legend></fieldset>
    <fieldset id="f-partition"><legend>partition</legend></fieldset>
    <fieldset id="f-centered"><legend>centered</legend></fieldset>
    <fieldset><legend>find &amp; sort</legend>
      <input type="search" id="q" placeholder="ID or alias" size="18">
      <select id="sort">
        <option value="rank">rank, best first</option>
        <option value="seat">seat order</option>
        <option value="p_ge4">P(&ge;4), best first</option>
      </select>
      <button id="clear">clear filters</button>
    </fieldset>
  </div>
  <div id="tray">
    <b id="count"></b>
    <span>selected <code id="picked">0</code></span>
    <button id="copy">copy selected IDs</button>
    <button id="drop">clear selection</button>
    <span id="says"></span>
  </div>
</header>
<main id="grid"></main>
<div id="empty" hidden>Nothing matches these filters.</div>
<script>
const ROWS = __ROWS__;
const FACETS = ["mode", "hue_family", "cell", "partition", "centered"];
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

function tile(row) {
  const card = document.createElement("div");
  card.className = "tile" + (picked.has(row.key) ? " picked" : "");
  const pick = () => {
    if (picked.has(row.key)) { picked.delete(row.key); } else { picked.add(row.key); }
    card.classList.toggle("picked", picked.has(row.key));
    document.getElementById("picked").textContent = picked.size;
  };
  if (row.src) {
    const img = document.createElement("img");
    img.src = row.src;
    img.loading = "lazy";
    img.title = "click to select";
    img.addEventListener("error", () => {
      const gone = document.createElement("div");
      gone.className = "gone";
      gone.textContent = "no picture on this disk";
      img.replaceWith(gone);
      gone.addEventListener("click", pick);
    });
    img.addEventListener("click", pick);
    card.append(img);
  }
  const meta = document.createElement("div");
  meta.className = "meta";
  const top = document.createElement("div");
  top.className = "line";
  const alias = document.createElement("span");
  alias.className = "alias";
  alias.textContent = row.alias;
  alias.title = row.key + " \\u2014 click to copy the full ID";
  alias.addEventListener("click", () => { copy(row.key); flash(alias, "copied"); });
  const score = document.createElement("span");
  score.className = "num dim";
  score.title = "rank key / P(\\u22654)";
  score.textContent = (row.rank === null ? NONE : Number(row.rank).toFixed(3)) + " / " +
    (row.p_ge4 === null ? NONE : Number(row.p_ge4).toFixed(3));
  top.append(alias, score);
  const one = document.createElement("div");
  one.className = "dim";
  one.textContent = row.mode + " \\u00b7 " + (row.hue_family || NONE) +
    " \\u00b7 " + (row.cell || NONE);
  const two = document.createElement("div");
  two.className = "dim";
  two.textContent = row.partition + (row.centered ? " \\u00b7 centered" : "") +
    " \\u00b7 seat " + row.seat;
  meta.append(top, one, two);
  card.append(meta);
  return card;
}

function draw() {
  const held = ROWS.filter(matches);
  const key = document.getElementById("sort").value;
  held.sort((a, b) => key === "seat" ? a.seat - b.seat : (b[key] ?? -1) - (a[key] ?? -1));
  document.getElementById("grid").replaceChildren(...held.map(tile));
  document.getElementById("empty").hidden = held.length > 0;
  document.getElementById("count").textContent = held.length + " of " + ROWS.length + " shown";
  document.getElementById("picked").textContent = picked.size;
}

document.getElementById("q").addEventListener("input", draw);
document.getElementById("sort").addEventListener("change", draw);
document.getElementById("clear").addEventListener("click", () => {
  for (const facet of FACETS) chosen[facet].clear();
  for (const box of document.querySelectorAll("header input[type=checkbox]")) {
    box.checked = false;
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


__all__ = [
    "ALIAS_LENGTH",
    "MANIFEST_NAME",
    "PAGE_NAME",
    "RECORDED_SEATS",
    "ROWS_NAME",
    "SCHEMA",
    "UNIT",
    "TentativeRefused",
    "aliases",
    "counts_of",
    "gallery_dir",
    "latest",
    "ledger_rows",
    "manifest_of",
    "manifest_path",
    "page",
    "page_path",
    "protected_keys",
    "read_manifest",
    "read_rows",
    "resolve",
    "rows_of",
    "rows_path",
    "stamp_now",
    "stamps",
    "store_root",
    "thumbnail_href",
    "write",
]
