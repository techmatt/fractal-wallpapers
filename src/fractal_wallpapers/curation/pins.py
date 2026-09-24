"""Pinned seats: a standing list of pool rows every solve seats first.

A **pin** is one row of the candidate pool that Matt wants guaranteed a seat. The
list is two tracked files under `data/curation/`, and the split is the whole design:

* [`LINKS_NAME`] is what a person writes — one explorer link per line, `#` comments
  allowed. A link is the thing a person has in hand after finding a picture they
  want kept, and it names a **view**, not a row.
* [`RESOLVED_NAME`] is what `curate pins resolve` makes of it — each link turned
  into one ledger row key, with a short note of where the row is and how it was
  chosen. **The solver reads this and nothing else**, so a solve never streams the
  ledger to find its pins, and what it pinned is a key a reader can look up.

Both are edited only through prompts. The list is not a flag: every solve honours it
(`--no-pins` is the way out, for a comparison), and it survives a change of `n` and a
re-solve without anybody saying anything.

## A link resolves by PLACE and MODE

The explorer writes everything it knows into a link, and most of it is not about which
row is meant. What identifies the row is the **plane** (`f` and its constants `cx`,
`cy`, `px`, `py`, `zx`, `zy`), the **mode** (`m`) and the **place** (`x`, `y`, `w`),
and a place matches within [`PLACE_TOLERANCE`] of the link's own width — a tolerance
relative to `w`, because an absolute one would be a pan of a thousand frames at a deep
zoom and nothing at all at a shallow one.

What is ignored is what the explorer adds on top of a row: `level` (the tone curve the
autolevel recorded, which is the same row either way), `mirror`, and the palette and
its `phase` — **unless several rows share the place**. Then the palette and phase are
the only thing that tells them apart, and the choice is written down on the pin:
[`BY_PALETTE_AND_PHASE`] where one matches both, [`BY_PALETTE`] where one matches the
map alone, and [`BY_P_FINE`] — the highest fine-head reading at the place — where none
does. `chosen_by` on each pin says which, and `sharing_the_place` how many it chose
among.

A link whose place holds no seatable row is left **unresolved** in the file with the
reason. It is never rendered and never invented: a pin is a row that already exists.

## What a pin is exempt from, and what it is not

A pin is seated FIRST and counts toward `n`. It is exempt from the fine bar, the
per-mode clearing bar and the neutral pre-selection, and from the near-duplicate gate
**against other pins** — each pin is seated without asking. Everything else is
deduplicated against the pins as usual: a pin is held in the diversity rule and in
the one-seat-per-cluster rule like any seat, so a near-copy of a pin is refused
rather than seated beside it. The swap loop and the augmenting chains never take a
pin out: [`rules.State.pinned`] is the set, and no removal set contains one.

**Membership is by the row, never forced**: the general gallery always takes it, a
mode collection only when the row's mode is that mode, and a hue family only when the
family pass would admit the row on its own (it is dominant in the family). A pin that
is not in a pass's pool is simply not in that gallery, and the record's `pins` block
says why.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlsplit

from fractal_wallpapers.paths import repo_root

#: The schema [`RESOLVED_NAME`] carries.
SCHEMA = 1

#: The prose this module's record carries on its `*_is` fields, in one place and
#: read at write time — `fractal_wallpapers/README.md`'s *A record's prose has one
#: copy in the source and a whole copy on every row*.
SCHEMA_NOTES: dict[str, str] = {
    "place_tolerance_is": "a share of the link's own w, on x, y and w alike",
}

#: What a person writes: one explorer link per line.
LINKS_NAME = "pins.txt"

#: What `curate pins resolve` writes, and the only file the solver reads.
RESOLVED_NAME = "pins.json"

#: How far a row's centre and width may sit from the link's, as a share of the link's
#: own `w`. A thousandth of the frame is a pan no eye can see at wallpaper size, and it
#: is loose enough that the decimal strings a link and a ledger row spell need not be
#: character-identical — only the same view.
PLACE_TOLERANCE = 1e-3

#: How far a family constant (`c`, `p`, `z₋₁`) may sit from the link's. Absolute: a
#: constant is not a frame and has no width to be relative to, and a link built from a
#: row carries the row's own decimal string.
CONSTANT_TOLERANCE = 1e-9

#: How far a palette phase may sit from the link's. The explorer writes six places.
PHASE_TOLERANCE = 1e-5

#: The three ways a pin is chosen among several rows at one place, best first.
BY_PALETTE_AND_PHASE = "palette_and_phase"
BY_PALETTE = "palette"
BY_P_FINE = "highest_p_fine"
#: One row at the place: nothing to choose.
ONLY_ROW = "only_row"

#: What the solver is told to read when a caller names nothing: the tracked list.
SHIPPED = "shipped"

#: The explorer's own defaults for the two keys a link leaves out when they are the
#: default — `explorer/permalink.js`'s `FAMILIES[0]` and `MODES[0]`.
DEFAULT_FAMILY = "mandelbrot"
DEFAULT_MODE = "smooth"

#: Which constants each plane carries, by the name a link spells it with.
CONSTANTS = {
    "julia": ("cx", "cy"),
    "phoenix": ("cx", "cy", "px", "py", "zx", "zy"),
}

#: What a link is, up to its query: the local explorer, at the schema version the
#: keys below belong to. A writer that emits many links carries this **once** and
#: a query per row — [`parse`] reads the query and ignores everything left of it,
#: so the two halves join by concatenation.
EXPLORER_BASE = "http://localhost:8000/explorer/?v=4&"

#: The key a link carries an iteration cap in, from the explorer's permalink v4 on —
#: `explorer/permalink.js`'s `CAP_KEY`. Written only where a recipe's cap is not what
#: the engine's width policy gives, so every link to a view at the policy's cap is the
#: string it always was.
CAP_KEY = "n"


class PinsRefused(ValueError):
    """A link that cannot be read as a view."""


def links_path() -> Path:
    """The list a person writes. Tracked."""
    return repo_root() / "data" / "curation" / LINKS_NAME


def resolved_path() -> Path:
    """The resolution the solver reads. Tracked."""
    return repo_root() / "data" / "curation" / RESOLVED_NAME


# --------------------------------------------------------------------------- #
# Reading the list.
# --------------------------------------------------------------------------- #
def read_links(path: Path | None = None) -> list[str]:
    """Every link in the list, in order, blank lines and `#` comments dropped.

    **A link written twice is kept once**, at its first line: the list is a set of
    rows a person wants shipped, and the same link twice is the same row asked for
    twice, not two seats.
    """
    source = links_path() if path is None else Path(path)
    if not source.is_file():
        return []
    out: list[str] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        # A comment is a whole line. A link carries no `#` of its own — the explorer
        # writes no fragment — but trimming at one mid-line would be a guess about it.
        text = line.strip()
        if text.startswith("#"):
            continue
        if text and text not in out:
            out.append(text)
    return out


def links_digest(path: Path | None = None) -> str:
    """sha256 over the list's links, so a stale resolution can be told from a fresh one.

    Over the parsed links and not the file's bytes, so a comment added or a line
    reordered does not call a resolution stale that still names the same rows.
    """
    return hashlib.sha256("\n".join(sorted(read_links(path))).encode("utf-8")).hexdigest()


def family_of(kind: str, degree: int) -> str:
    """A plane's name the way a link spells it: the recurrence with its exponent."""
    if kind in ("mandelbrot", "multibrot"):
        return "mandelbrot" if int(degree) == 2 else f"multibrot{int(degree)}"
    if kind == "julia":
        return "julia" if int(degree) == 2 else f"julia{int(degree)}"
    return str(kind)


def parse(link: str) -> dict:
    """One explorer link as the view it names. Raises [`PinsRefused`] on a link
    with no place in it.

    Only the keys resolution reads are kept: the plane, its constants, the mode, the
    place, and the palette and phase for the case where several rows share a place.
    """
    query = dict(parse_qsl(urlsplit(str(link)).query, keep_blank_values=True))
    missing = [key for key in ("x", "y", "w") if key not in query]
    if missing:
        raise PinsRefused(
            f"the link names no {', '.join(missing)}, so it names no place — the explorer "
            "leaves the home view's frame out of a link, and a home view is not a pin"
        )
    family = query.get("f", DEFAULT_FAMILY)
    plane = "julia" if family.startswith("julia") else family
    constants = {key: float(query.get(key, "0")) for key in CONSTANTS.get(plane, ())}
    return {
        "family": family,
        "constants": constants,
        "mode": query.get("m", DEFAULT_MODE),
        "x": float(query["x"]),
        "y": float(query["y"]),
        "w": float(query["w"]),
        "palette": query.get("p"),
        "phase": float(query.get("phase", "0")),
    }


def query_of(view: dict) -> str:
    """[`parse`]'s inverse: the query a link spells this view with.

    Only the keys [`parse`] reads, in the order the explorer writes them, and the
    two defaults are **left out** rather than spelled — a link to a `mandelbrot`
    `smooth` view carries no `f` and no `m`, which is what
    `explorer/permalink.js` does and what every link in `pins.txt` looks like.

    **And the cap, where the recipe's is not the width's** *(permalink v4,
    find_minibrots_cap2_ckpt145)*. A view may carry `maxiter`, the cap its recipe
    was drawn at; the link says `n=` it only where that differs from what the
    engine's width policy gives at `w`, because an absent `n` already means exactly
    that. A link that left out a cap somebody chose would open the place at a
    different picture under the same name. The policy is the engine's, asked through
    [`engine.maxiter_for`] and remembered per width — [`warm_width_caps`] asks for a
    whole batch in one call, which a writer of thousands of links should.

    The coordinates go in as **given**. A caller holding the decimal strings a
    ledger wrote hands those over and the link redraws that row exactly; a caller
    holding floats gets `repr`, which is the shortest string that round-trips.
    """
    family = str(view.get("family") or DEFAULT_FAMILY)
    parts = [] if family == DEFAULT_FAMILY else [f"f={family}"]
    held = view.get("constants") or {}
    plane = "julia" if family.startswith("julia") else family
    parts += [f"{key}={_spelled(held[key])}" for key in CONSTANTS.get(plane, ()) if key in held]
    mode = view.get("mode")
    if mode and str(mode) != DEFAULT_MODE:
        parts.append(f"m={mode}")
    parts += [f"{key}={_spelled(view[key])}" for key in ("x", "y", "w")]
    cap = view.get("maxiter")
    if cap is not None and int(cap) != _width_cap(_spelled(view["w"])):
        parts.append(f"{CAP_KEY}={int(cap)}")
    if view.get("palette"):
        parts.append(f"p={quote(str(view['palette']))}")
    phase = float(view.get("phase") or 0.0)
    if phase:
        parts.append(f"phase={phase:g}")
    return "&".join(parts)


#: The engine's width policy, per width as a link spells it. A cache rather than a
#: mirror: Python holds no copy of the policy (`engine.maxiter_for` says why), so each
#: distinct width is one question to the engine, asked once.
_WIDTH_CAPS: dict[str, int] = {}


def warm_width_caps(widths) -> None:
    """Ask the engine for every width not yet known, in one call.

    [`query_of`] asks one width at a time, which is one subprocess each; a writer about
    to emit a link per row calls this first with every width it holds.
    """
    from fractal_wallpapers import engine

    wanted = sorted({_spelled(width) for width in widths} - set(_WIDTH_CAPS))
    if wanted:
        _WIDTH_CAPS.update(zip(wanted, engine.maxiter_for(wanted), strict=True))


def _width_cap(width: str) -> int:
    """The cap the engine's width policy gives at `width`, asked once."""
    if width not in _WIDTH_CAPS:
        warm_width_caps([width])
    return int(_WIDTH_CAPS[width])


def _spelled(value) -> str:
    """A coordinate as a link spells it: the string it arrived as, or `repr`."""
    return value if isinstance(value, str) else repr(float(value))


def _row_view(row: dict) -> dict | None:
    """A ledger row's plane, constants, mode and place, in [`parse`]'s shape."""
    recipe = row.get("recipe") or {}
    held = recipe.get("family") or {}
    viewport = recipe.get("viewport") or {}
    try:
        family = family_of(held.get("kind"), held.get("degree", 2))
        c = held.get("c") or ("0", "0")
        p = held.get("p") or ("0", "0")
        z = held.get("z_prev") or ("0", "0")
        every = {
            "cx": float(c[0]),
            "cy": float(c[1]),
            "px": float(p[0]),
            "py": float(p[1]),
            "zx": float(z[0]),
            "zy": float(z[1]),
        }
        plane = "julia" if family.startswith("julia") else family
        return {
            "family": family,
            "constants": {key: every[key] for key in CONSTANTS.get(plane, ())},
            "mode": str(recipe.get("mode")),
            "x": float(viewport["center_re"]),
            "y": float(viewport["center_im"]),
            "w": float(viewport["width"]),
            "palette": recipe.get("colormap"),
            "phase": float((recipe.get("palette") or {}).get("phase", 0.0)),
        }
    except (KeyError, TypeError, ValueError):
        return None


def at_place(view: dict, row: dict | None) -> bool:
    """Whether a row's view is the link's plane, mode and place. Palette ignored."""
    if row is None or row["family"] != view["family"] or row["mode"] != view["mode"]:
        return False
    for key, value in view["constants"].items():
        if abs(row["constants"].get(key, 0.0) - value) > CONSTANT_TOLERANCE:
            return False
    reach = PLACE_TOLERANCE * view["w"]
    return (
        abs(row["x"] - view["x"]) <= reach
        and abs(row["y"] - view["y"]) <= reach
        and abs(row["w"] - view["w"]) <= reach
    )


def note_of(view: dict) -> str:
    """The short note a pin carries: plane, mode, place."""
    plane = view["family"]
    held = view["constants"]
    if "cx" in held:
        plane += f" c={held['cx']:.6g}{held['cy']:+.6g}i"
    if "px" in held:
        plane += f" p={held['px']:.6g}{held['py']:+.6g}i z={held['zx']:.6g}{held['zy']:+.6g}i"
    return f"{plane} · {view['mode']} · ({view['x']:.9g}, {view['y']:.9g}) w {view['w']:.3g}"


# --------------------------------------------------------------------------- #
# Resolving it.
# --------------------------------------------------------------------------- #
def choose(view: dict, rows: list[dict], fine: dict) -> tuple[dict, str]:
    """`(the row a link means among the seatable rows at its place, how it was chosen)`.

    `rows` are ledger rows, each already known to be at the place. See the module
    docstring for the order: palette and phase, palette alone, then the highest fine
    reading. Ties inside a tier break on the fine reading and then the key, so the
    answer never depends on the ledger's order.
    """

    def strength(row: dict) -> tuple:
        read = fine.get(str(row["key"]))
        return (read is not None, -math.inf if read is None else float(read), str(row["key"]))

    if len(rows) == 1:
        return rows[0], ONLY_ROW
    views = [(row, _row_view(row)) for row in rows]
    same_map = [row for row, held in views if held and held["palette"] == view["palette"]]
    same_phase = [
        row for row in same_map if abs(_row_view(row)["phase"] - view["phase"]) <= PHASE_TOLERANCE
    ]
    for tier, name in ((same_phase, BY_PALETTE_AND_PHASE), (same_map, BY_PALETTE)):
        if tier:
            return max(tier, key=strength), name
    return max(rows, key=strength), BY_P_FINE


def resolve(links=None, rows=None, fine=None, seatable=None, log=print) -> dict:
    """The document [`RESOLVED_NAME`] holds, for every link in the list.

    One streamed pass over the ledger collects every row at any link's place; the
    pool's own exclusions are then asked of those few rows alone — `seatable` is
    `{key}` of the ones [`solve.pool`] would admit — so the resolution is a row the
    solver can actually seat. Every argument is a parameter so a guard can hand in a
    three-row ledger; unsaid, each reads its store.
    """
    from fractal_wallpapers.curation import candidate_ledger, distinct

    held_links = read_links() if links is None else list(links)
    views: list = []
    for link in held_links:
        try:
            views.append(parse(link))
        except (PinsRefused, ValueError) as refusal:
            views.append(refusal)
    found: dict = {at: [] for at in range(len(held_links))}
    seen = 0
    wanted_modes = {view["mode"] for view in views if isinstance(view, dict)}
    for row in candidate_ledger.stream() if rows is None else rows:
        seen += 1
        recipe = row.get("recipe") or {}
        if str(recipe.get("mode")) not in wanted_modes:
            continue
        held = _row_view(row)
        for at, view in enumerate(views):
            if isinstance(view, dict) and at_place(view, held):
                found[at].append(row)
    matched = [row for rows_at in found.values() for row in rows_at]
    if seatable is None:
        seatable = seatable_keys(matched, log=log)
    fine_read = distinct.fine_scores() if fine is None else dict(fine)

    pins = []
    for at, link in enumerate(held_links):
        view = views[at]
        entry: dict = {"schema": SCHEMA, "link": link}
        if not isinstance(view, dict):
            pins.append({**entry, "key": None, "status": "unresolved", "why": str(view)})
            continue
        entry["note"] = note_of(view)
        at_the_place = found[at]
        usable = [row for row in at_the_place if str(row["key"]) in seatable]
        if not usable:
            why = (
                "no ledger row stands at this plane, mode and place"
                if not at_the_place
                else f"{len(at_the_place)} ledger row(s) stand here and none is in the "
                "seatable pool — rejected, vetoed, off the regime, pictureless or unscored"
            )
            pins.append({**entry, "key": None, "status": "unresolved", "why": why})
            continue
        chosen, how = choose(view, usable, fine_read)
        chosen_view = _row_view(chosen) or {}
        read = fine_read.get(str(chosen["key"]))
        pins.append(
            {
                **entry,
                "key": str(chosen["key"]),
                "status": "resolved",
                "chosen_by": how,
                "sharing_the_place": len(usable),
                "at_the_place_in_the_ledger": len(at_the_place),
                "partition": chosen.get("partition"),
                "palette": chosen_view.get("palette"),
                "phase": chosen_view.get("phase"),
                "p_fine": None if read is None else round(float(read), 6),
            }
        )
    resolved = [pin for pin in pins if pin["key"]]
    log(
        f"[pins] {len(resolved)} of {len(pins)} link(s) resolved over {seen:,} ledger row(s); "
        f"{len(pins) - len(resolved)} unresolved"
    )
    return {
        "schema": SCHEMA,
        "of": "the pinned seats: each link in data/curation/pins.txt resolved to the ledger "
        "row it means, by plane, mode and place. Every solve seats these first; see "
        "curation/pins.py",
        "resolved_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "links_sha256": links_digest() if links is None else _digest_of(held_links),
        "place_tolerance": PLACE_TOLERANCE,
        "place_tolerance_is": SCHEMA_NOTES["place_tolerance_is"],
        "pins": pins,
    }


def _digest_of(links) -> str:
    return hashlib.sha256("\n".join(sorted(links)).encode("utf-8")).hexdigest()


def seatable_keys(rows, log=print) -> set:
    """`{key}` of the rows [`solve.pool`] would admit, asked of these rows alone.

    The veto is read from its store, because a pool over handed-in rows reads none
    unless it is handed one — and a vetoed row pinned would be a person's no
    overridden by a list.
    """
    from fractal_wallpapers.curation import solve, veto

    held = list(rows)
    if not held:
        return set()
    candidates, _refused = solve.pool(
        rows=held, vetoed=set(veto.render_keys()), spirals={}, log=lambda _line: None
    )
    return {str(candidate.key) for candidate in candidates}


def write(document: dict, path: Path | None = None) -> Path:
    """Write the resolution. LF, UTF-8, one pin per line inside the list."""
    target = resolved_path() if path is None else Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    head = {key: value for key, value in document.items() if key != "pins"}
    lines = json.dumps(head, indent=2, ensure_ascii=False)[:-2]
    body = ",\n".join(
        "    " + json.dumps(pin, ensure_ascii=False) for pin in document.get("pins") or ()
    )
    text = lines + ',\n  "pins": [\n' + body + ("\n" if body else "") + "  ]\n}\n"
    target.write_text(text, encoding="utf-8", newline="\n")
    return target


# --------------------------------------------------------------------------- #
# What a solve reads.
# --------------------------------------------------------------------------- #
def read(path: Path | None = None) -> dict | None:
    """The resolution on disk, or `None` where there is none."""
    source = resolved_path() if path is None else Path(path)
    if not source.is_file():
        return None
    return json.loads(source.read_text(encoding="utf-8"))


def pinned(log=print) -> tuple[str, ...]:
    """The keys every solve seats first, in the list's order. **The solver's one read.**

    A missing or stale resolution is a loud line and never a crash: a solve that
    stopped because somebody edited a text file would be a list that could take the
    gallery down with it. Stale means the list's links no longer match the ones the
    resolution was taken over, and the old keys are used until `curate pins resolve`
    runs again.
    """
    links = read_links()
    document = read()
    if document is None:
        if links:
            log(
                f"[pins] ⚠ {len(links)} link(s) are listed in {LINKS_NAME} and there is no "
                f"{RESOLVED_NAME}, so NOTHING is pinned. Run `fractal-wallpapers curate pins "
                "resolve`"
            )
        return ()
    if document.get("links_sha256") != links_digest():
        log(
            f"[pins] ⚠ {LINKS_NAME} has changed since {RESOLVED_NAME} was resolved "
            f"({document.get('resolved_at')}), so the pins in force are the OLD list's. Run "
            "`fractal-wallpapers curate pins resolve`"
        )
    keys: list[str] = []
    for pin in document.get("pins") or ():
        if pin.get("key") and str(pin["key"]) not in keys:
            keys.append(str(pin["key"]))
    unresolved = sum(1 for pin in document.get("pins") or () if not pin.get("key"))
    if unresolved:
        log(f"[pins] ⚠ {unresolved} listed link(s) are unresolved and pin nothing")
    return tuple(keys)


def keys_for(asked, log=print) -> tuple[str, ...]:
    """What one solve pins: [`SHIPPED`] reads the list, anything else is the keys named."""
    if isinstance(asked, str) and asked == SHIPPED:
        return pinned(log=log)
    return tuple(dict.fromkeys(str(key) for key in (asked or ())))


__all__ = [
    "BY_PALETTE",
    "BY_PALETTE_AND_PHASE",
    "BY_P_FINE",
    "CONSTANT_TOLERANCE",
    "LINKS_NAME",
    "ONLY_ROW",
    "PHASE_TOLERANCE",
    "PLACE_TOLERANCE",
    "RESOLVED_NAME",
    "SCHEMA",
    "SHIPPED",
    "PinsRefused",
    "at_place",
    "choose",
    "family_of",
    "keys_for",
    "links_digest",
    "links_path",
    "note_of",
    "parse",
    "pinned",
    "read",
    "read_links",
    "resolve",
    "resolved_path",
    "seatable_keys",
    "write",
]
