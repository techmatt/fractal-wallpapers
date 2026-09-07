"""THE finished-render label stores: one per judge, one writer, one reader.

The location store answers *is this a place worth rendering*. These two answer
the question after it — **is this finished picture worth keeping** — and they are
separate stores because the unit is different. A location is judged once; a
finished render is judged per picture, and one location carries a dozen of them
that differ only in how they were colored. Keying those on the location would
collapse a dozen verdicts into one and throw away the entire axis the judges
exist to read.

Two heads, two stores, same shape:

```text
smooth_render    the smooth coloring, judged as a wallpaper.   Tiers 1..4.
strange_render   the strange colorings, judged as renderings.  Tiers 1..4.
```

## A row carries its whole join, and the join is bigger here

The location *and* the recipe: which mode with which of its own settings,
through which curve, which map, and every knob of the palette pass — gamma, how
many times the gradient is traversed and from where, whether the map is read
backwards or folded, how its arc is spent, what happens to the highlights. Two
rows of one location under one map can be a 1 and a 4, and the only thing
separating them is on that list. A row missing any of it is a verdict about a
picture nobody can rebuild — and one sheet here sweeps a trap's opacity and
threshold across nine settings of one place, so "which mode" alone is not enough
to tell its rows apart.

The **curve** sits beside the mode rather than inside the recipe because it
replaces the mode's own: a mode names a field and a curve to read it through, and
these corpora set that curve per render. Naming the mode and the curve separately
is what lets a row say "this mode, read straight" without inventing a mode name
for every combination.

## One scale, every head — and it is not the shipped model's class count

Every judge in this project is cast on **1..4**, the same scale the location
corpus uses, `strange_render` included. Its corpus was *collected* on three
tiers, and that is a fact about the rows already in it rather than a ceiling on
the rows to come: a labeler looking at a page of strange renders can see the
difference between "worth keeping" and "the best of those", and a store that
refused to write it down would be throwing away the only tier the release path
actually cuts on.

**The store's scale and a model's class count are two different numbers**, and
conflating them is what this section exists to stop. Whatever a checkpoint can
emit is in that checkpoint's own config, read by whoever loads it — see
[`fractal_wallpapers.models.finished_train`] — and it is never read off the
corpus. `strange_render` is the case that proves it: it was trained on three
classes and could not suggest a 4 while its store was already collecting them,
and the retrain that widened it to four could only happen because the store had
been free to grow the tier first. A capped store could never have collected it.

## Which store a row belongs in is decided by its mode, at the writer

`smooth` is the smooth judge's whole roster and every other mode is the strange
judge's, and [`curation.hunt.kind_of`] is what says so — it is the router the
pipeline already offers candidates through. [`routed_to`] asks that same function
rather than restating the answer, and [`check`] refuses a row whose mode routes to
the other store. A second spelling of a routing rule agrees with the first until
one of them is edited.

It is a guard and not a repair. Forty resolved `smooth` rows reached
`strange_render` through the `rare_palette` batch before this existed, and they
stay there: an original is never modified. What a store should not be holding is
excluded where it is **read** — [`fractal_wallpapers.models.finished_train`]
derives it at the training read, the same way eval-eligibility is derived and
never stored.

A **pooled** read has the same question one turn harder: 117 renders are labelled
in *both* stores, which is one picture with two verdicts rather than a row in the
wrong place, and a reader that unions the corpora counts each twice.
[`crossovers`] is that decided once, off the same router, for every caller that
pools.

## Eligibility, and why it is not the location store's rule

Over there, a batch may be an instrument if its draw carried no model score and
its page served no suggestion. **Not one finished-render batch passes that**, and
not because the corpus is careless: every one of them draws locations the
location head already admitted, so on the location axis every batch is biased,
and every batch but the two blind sheets served a head's own tier prefilled.

So the eval side here is not drawn, it is **pinned**: a batch registered
`eval_only` is on the evaluation side and may never train, for this generation of
heads or any later one. That flag outranks everything, it is a property of the
batch rather than of a row, and the pin is asserted at the **location** — a
future batch re-rendering a pinned place under a fresh identifier cannot spend
the instrument by not naming it.

Everything else trains. A head that needs a slice to pick an epoch on takes one
from its own training side: an instrument is spent the moment it trains, and
choosing an epoch on it is a partial spend that leaves nothing red.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from fractal_wallpapers.engine_spec import recipe
from fractal_wallpapers.labeling import registry as registry_module
from fractal_wallpapers.labeling import store
from fractal_wallpapers.paths import repo_root
from fractal_wallpapers.supply.location import location_key

#: The schema every finished-render row carries, from the first row.
SCHEMA = 1

#: Every finished-render judge, and therefore every store this module owns.
HEADS: tuple[str, ...] = ("smooth_render", "strange_render")

#: The scale a person casts on, for every one of them. One number, not a per-head
#: ceiling: what a model can emit is the model's own config and is read off its
#: checkpoint, never off the corpus it was trained from.
SCALE: tuple[int, ...] = (1, 2, 3, 4)


class FinishedError(ValueError):
    """A row that may not enter a store, or one already in it that cannot be read."""


def head_of(name: str) -> str:
    """Return `name`, having proved it names a judge."""
    if name not in HEADS:
        raise FinishedError(f"unknown head {name!r} — known: {sorted(HEADS)}")
    return name


def tiers(head: str) -> tuple[int, ...]:
    """The scores a labeler may cast for this judge: [`SCALE`], for every one."""
    head_of(head)
    return SCALE


def store_dir(head: str) -> Path:
    """Where one judge's tracked label records live."""
    return repo_root() / "data" / head_of(head)


def row_dir(head: str) -> Path:
    return store_dir(head) / "rows"


def batch_path(head: str, batch: str) -> Path:
    return row_dir(head) / f"{batch}.jsonl"


def registry_path(head: str) -> Path:
    return store_dir(head) / "batches.jsonl"


def eval_split_path(head: str) -> Path:
    """The pinned evaluation side: one row per pinned location."""
    return store_dir(head) / "eval_split.jsonl"


def split_recipe_path(head: str) -> Path:
    """How the side was decided, and what it realized."""
    return store_dir(head) / "split.json"


def registry(head: str) -> dict[str, registry_module.Registration]:
    """Every batch registration for one judge, fail-closed on anything absent."""
    return registry_module.read(registry_path(head))


def register(head: str, registration: registry_module.Registration) -> dict:
    """Register a batch. Appended, and refused when it contradicts what stands.

    An identical re-registration is written and reads as a no-op; one that
    disagrees is refused here rather than at the next read, so the file never
    holds two answers about one population.
    """
    if not registration.batch:
        raise registry_module.RegistrationError("a registration must name its batch")
    if not registration.method:
        raise registry_module.RegistrationError(
            f"{registration.batch}: a registration must say how the population was drawn"
        )
    registry_module.refuse_contradiction(registry(head), registration)
    row = registration.row()
    if row["registered_at"] is None:
        row["registered_at"] = store.now()
    path = registry_path(head)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


#: Every knob of the palette pass a row must carry. Absent means the picture
#: cannot be rebuilt, so it is refused rather than defaulted: a default here would
#: be a guess about what somebody was looking at when they judged it.
RECIPE_KEYS = ("gamma", "cycles", "phase", "reverse", "mirror", "transfer", "rolloff")


def render_key(row: dict) -> tuple | None:
    """THE identity of one finished render: the place, the mode, and the recipe.

    `None` when the row cannot express one, which the reader counts and the
    writer refuses. The location half goes through the same adapter the location
    store uses, so a place is one place across both corpora.
    """
    place = location_key(row.get("family") or {}, row.get("viewport") or {})
    if place is None:
        return None
    recipe = row.get("recipe")
    if not isinstance(recipe, dict) or any(key not in recipe for key in RECIPE_KEYS):
        return None
    mode = row.get("mode")
    curve = row.get("curve")
    colormap = row.get("colormap")
    settings = row.get("mode_params")
    if not all(isinstance(value, str) for value in (mode, curve, colormap)):
        return None
    if not isinstance(settings, dict):
        return None
    return (
        place,
        mode,
        json.dumps(settings, sort_keys=True),
        curve,
        colormap,
        json.dumps(recipe, sort_keys=True),
    )


def place_of(row: dict) -> tuple | None:
    """The location half of a row's identity — what the eval pin is asserted on."""
    return location_key(row.get("family") or {}, row.get("viewport") or {})


def routed_to(mode: str, texture_flat: bool = False) -> str:
    """Which store a mode's rows belong in, asked of the thing that does the routing.

    [`curation.hunt.kind_of`] is the router: everything the pipeline draws is
    offered to one of these two judges by mode, and this is that same call rather
    than a second copy of the answer. A second copy is precisely how a store ends
    up holding a mode it does not own — the two spellings agree until one of them
    is edited.

    `texture_flat` says the render's modulate texture carried no information, so
    the picture is the smooth field spent by rank and the row is the smooth
    judge's. Callers with a row rather than a mode want [`routes_to`], which takes
    the render's own identity to the register and needs no argument.

    Imported at the call rather than at the top: this module is on the base
    install's labeling path and the router sits in `curation`, which imports back
    here.
    """
    from fractal_wallpapers.curation import hunt

    return hunt.kind_of(mode, texture_flat)


def routes_to(row: dict, extend: bool = False) -> str:
    """Which store one **row** belongs in, its texture's degeneracy included.

    THE call a reader of a stored corpus makes. A finished-render row carries
    everything the flag is a function of — the place, the geometry, the mode and
    its curve — so the answer is a lookup in
    [`fractal_wallpapers.coloring.texture_flat`] and never a re-render here.

    A row this repository has never measured reads as not flat, which is what
    every reader concluded before the flag existed. That is why the register is
    tracked: routing that differed between two checkouts of one commit would be
    two corpora wearing one name.

    ## `extend` is for the WRITE path and is off everywhere else

    `extend=True` measures a register MISS instead of defaulting it — one render
    at the row's own geometry through
    [`coloring.texture_flat.extend_with`], appended to the tracked register, and
    the row then routed on the measurement. It is what [`append`] passes, because
    ingest is the one moment a row's identity is new and the one moment somebody
    is waiting on a handful of rows rather than sweeping a corpus.

    **It must stay off by default and the reason is arithmetic.** This is called
    per row by `finished_train.population` over both stores — 4,235 rows today —
    and by every reader of a stored corpus. A default that rendered on a miss
    would turn a corpus read into a render leg, silently, on a machine that may
    already be running one.
    """
    from fractal_wallpapers.coloring import texture_flat

    flat = texture_flat.extend_with(row) if extend else texture_flat.flat_for(row)
    return routed_to(row.get("mode"), flat)


def crossovers(pairs) -> tuple[set, dict]:
    """`(the (kind, render) pairs a pooled read must leave out, the record)`.

    A finished render is judged per picture and the two stores are keyed apart,
    so nothing stops one render being labelled in **both**. **117 are**, on
    2026-09-06 — every one of them an `itinerary` whose texture said nothing, so
    it is the smooth field spent by rank bit for bit and the two stores hold two
    verdicts about literally the same pixels. A reader that pools the stores
    counts each of those twice, which is what
    [`fractal_wallpapers.curation.rank_key.fit`] was doing to 52 of them.

    **Nothing is written, moved or re-keyed.** The stores are append-only, an
    original is never modified, and the row this leaves out is a real verdict a
    person cast. This is the same read-side arrangement [`routes_to`] already
    serves for the forty `rare_palette` rows, asked of the same router: the
    render is counted once, in the store its **routed mode** names — which is
    [`curation.hunt.kind_of`], which is
    [`curation.mode_policy.routed_mode`]'s KIND half.

    `pairs` is `[(kind, row)]` over both stores; what comes back is the set of
    `(kind, render_key)` a caller must skip. Only a render **both** stores hold
    is considered — a row in the wrong store on its own is a different question
    with a different answer, and this one is not it.

    **A crossover the router cannot settle is left whole and reported.** Two rows
    of one render can only route differently if the flatness register answers
    differently at their two geometries — [`render_key`] carries no resolution
    and [`coloring.texture_flat.KEYED`] does — and inventing a tiebreak there
    would be deciding which store owns a mode on no evidence. None disagree
    today; the record says so rather than a caller assuming it.
    """
    held: dict = {}
    for kind, row in pairs:
        identity = render_key(row)
        if identity is None:
            continue
        held.setdefault(identity, {}).setdefault(kind, []).append(row)

    leave_out: set = set()
    kept_in: dict[str, int] = {}
    ambiguous: list[dict] = []
    crossings = 0
    for identity, by_kind in held.items():
        if len(by_kind) < 2:
            continue
        crossings += 1
        routed = {routes_to(row) for rows in by_kind.values() for row in rows}
        owner = next(iter(routed)) if len(routed) == 1 else None
        if owner is None or owner not in by_kind:
            ambiguous.append(
                {
                    "place": str(identity[0]),
                    "mode": str(identity[1]),
                    "held_by": sorted(by_kind),
                    "routes_to": sorted(routed),
                }
            )
            continue
        kept_in[owner] = kept_in.get(owner, 0) + 1
        leave_out.update((kind, identity) for kind in by_kind if kind != owner)

    record = {
        "renders_in_both_stores": crossings,
        "rows_left_out": sum(len(held[identity][kind]) for kind, identity in leave_out),
        "kept_in": dict(sorted(kept_in.items())),
        "routed_by": "labeling.finished.routes_to -> hunt.kind_of -> mode_policy.routed_mode",
        "ambiguous": ambiguous,
    }
    return leave_out, record


def check(head: str, row: dict, extend: bool = False) -> dict:
    """Return `row`, having proved it is a finished-render row for this judge.

    `extend` is [`routes_to`]'s and carries its warning: on the write path it is
    `True` and a register MISS costs one render, everywhere else it is `False` and
    a miss routes on the unmeasured default.
    """
    if row.get("schema") != SCHEMA:
        raise FinishedError(f"schema {row.get('schema')!r}, expected {SCHEMA}")
    batch = row.get("batch")
    if not isinstance(batch, str) or not batch:
        raise FinishedError("a row must name the batch it was drawn from")
    score = row.get("score")
    if score is not None and score not in tiers(head):
        raise FinishedError(
            f"score {score!r} is not one of {tiers(head)} or null. Every judge in this project "
            f"is cast on one scale, and a verdict outside it is not a tier anybody could have "
            f"meant."
        )
    origin = row.get("origin")
    if origin != store.HUMAN and not (
        isinstance(origin, str) and origin.startswith(store.RULE_PREFIX)
    ):
        raise FinishedError(f"origin {origin!r}: a verdict is a human's or a stated rule's")
    if not isinstance(row.get("recorded_at"), str):
        raise FinishedError("a row must carry the time it was recorded; it is how latest wins")
    if render_key(row) is None:
        raise FinishedError(
            "this row carries no render identity — a finished-render verdict needs the place, "
            "the mode with its own settings and its curve, the map, and every knob of the "
            "palette pass on the same line, or it is a verdict about a picture nobody can "
            "rebuild"
        )
    routed = routes_to(row, extend=extend)
    if routed != head:
        # Which of the two reasons, because they read very differently to whoever
        # has to act on this. The mode being in the wrong store is a mistake at
        # the sheet; a flat texture is not — the mode is the mode that rendered,
        # and the picture it produced is another mode's exactly.
        why = (
            f"mode {row['mode']!r} is routed to the {routed} store"
            if routed_to(row["mode"]) == routed
            else f"mode {row['mode']!r} is this store's, but this render's texture carried no "
            f"information, so the picture is the smooth field spent by rank bit for bit and "
            f"the row is the {routed} store's"
        )
        raise FinishedError(
            f"{why} and this row is being written to {head}. A store that holds a mode it "
            f"does not own inflates its own per-mode tables, double-weights the places that "
            f"carry the mode in both, and reads as evidence about a population it is not "
            f"from. Write it to {routed}."
        )
    return row


def render_row(
    head: str,
    batch: str,
    score: int | None,
    family: dict,
    viewport: dict,
    mode: str,
    mode_params: dict,
    curve: str,
    colormap: str,
    recipe_: dict,
    render: dict,
    origin: str = store.HUMAN,
    labeler: str | None = None,
    recorded_at: str | None = None,
    **extra,
) -> dict:
    """Build one finished-render row. The only shape the writer accepts."""
    row = {
        "schema": SCHEMA,
        "batch": batch,
        "recorded_at": recorded_at or store.now(),
        "labeler": labeler,
        "origin": origin,
        "score": score,
        "family": family,
        "viewport": viewport,
        "mode": mode,
        "mode_params": mode_params,
        "curve": curve,
        "colormap": colormap,
        "recipe": recipe_,
        "render": render,
        **extra,
    }
    return check(head, row)


def append(head: str, rows: list[dict], known: dict | None = None, extend: bool = True) -> Path:
    """THE writer. Append checked rows to their batch's file and return its path.

    **`extend` is on here and off everywhere else**, which is what makes the
    texture register self-extending: a sheet ingest is where a render identity is
    new, so a MISS is measured now rather than left for a backfill that has to
    find it again later. See [`routes_to`] for the cost and for why no reader gets
    this default.
    """
    if not rows:
        raise FinishedError("nothing to append")
    batches = {row.get("batch") for row in rows}
    if len(batches) != 1:
        raise FinishedError(f"one call writes one batch's rows, not {sorted(batches)}")
    name = batches.pop()
    known = registry(head) if known is None else known
    if name not in known:
        raise FinishedError(
            f"batch {name!r} has no registration in the {head} store. Register it before its "
            "first row exists — afterwards, how it was drawn is answered from memory."
        )
    checked = [check(head, row, extend=extend) for row in rows]
    path = batch_path(head, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for row in checked:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def row_paths(head: str) -> list[Path]:
    directory = row_dir(head)
    return sorted(directory.glob("*.jsonl")) if directory.is_dir() else []


def read(head: str, paths=None) -> list[dict]:
    """Every row of one store, schema-checked and stamped with where it came from."""
    paths = row_paths(head) if paths is None else [Path(p) for p in paths]
    out: list[dict] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if row.get("schema") != SCHEMA:
                    raise FinishedError(
                        f"{path}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}"
                    )
                out.append({**row, "_file": path.name, "_line": number})
    return out


@dataclass
class Resolution:
    """What one store currently says, and what it could not say it about."""

    current: dict = field(default_factory=dict)
    n_rows: int = 0
    n_superseded: int = 0
    n_unkeyed: int = 0
    unkeyed: list = field(default_factory=list)

    def scored(self) -> list[dict]:
        """The resolved rows carrying a verdict, in render-key order.

        Ordered on the key's text rather than on the key: an absent family
        constant is recorded as absent, so two keys can hold a tuple and a
        `None` in the same position and refuse to compare. The text of a key is
        as stable an order as the key and is total.
        """
        return [
            row
            for _key, row in sorted(self.current.items(), key=lambda item: repr(item[0]))
            if row.get("score") is not None
        ]

    def summary(self) -> dict:
        scored = self.scored()
        return {
            "rows": self.n_rows,
            "renders": len(self.current),
            "scored": len(scored),
            "locations": len({place_of(row) for row in scored}),
            "superseded": self.n_superseded,
            "unkeyed": self.n_unkeyed,
        }


def resolve(rows: list[dict], known: dict | None = None) -> Resolution:
    """THE resolution rule: per render, an evaluation row wins, then the latest.

    `known` is this head's batch registry, which is where a row's side is read
    from — see [`fractal_wallpapers.labeling.store.resolution_order`] for why the
    pin has to outrank the clock here. Without it the rule degrades to the clock
    alone; [`resolved`] always hands the store's own registrations over.
    """
    eval_only = store.eval_side_batches(known)
    resolution = Resolution(n_rows=len(rows))
    for row in sorted(rows, key=lambda row: store.resolution_order(row, eval_only)):
        key = render_key(row)
        if key is None:
            resolution.n_unkeyed += 1
            resolution.unkeyed.append(row)
            continue
        if key in resolution.current:
            resolution.n_superseded += 1
        resolution.current[key] = row
    return resolution


def resolved(head: str, paths=None) -> Resolution:
    """THE reader every consumer of a finished-render store routes through."""
    return resolve(read(head, paths), known=registry(head))


def write_pin(head: str, rows: list[dict], recipe_document: dict) -> tuple[Path, Path]:
    """Ship the pinned evaluation side and the record of how it was decided."""
    members = eval_split_path(head)
    members.parent.mkdir(parents=True, exist_ok=True)
    with members.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    document = split_recipe_path(head)
    document.write_text(
        json.dumps(recipe_document, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return members, document


def pinned(head: str) -> dict[tuple, str]:
    """`{location: batch}` for every place the evaluation side holds.

    Keyed on the location rather than on the render, because that is what the pin
    has to survive: a later batch that re-renders a pinned place under a fresh
    identifier would otherwise train on the instrument without ever naming it.
    """
    path = eval_split_path(head)
    if not path.is_file():
        return {}
    out: dict[tuple, str] = {}
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            place = place_of(row)
            if place is None:
                raise FinishedError(f"{path}:{number}: a pinned row carries no location")
            out[place] = row.get("batch", "")
    return out


def assert_pin_holds(head: str, train_rows: list[dict]) -> dict:
    """Raise unless no training row touches a pinned location.

    The check a trainer runs on the split it *built*, not a claim the pin makes
    about itself: a pass that never consulted the pin still dies here rather than
    passing silently.
    """
    keys = pinned(head)
    if not keys:
        return {"pinned_locations": 0, "checked_rows": len(train_rows), "ok": True}
    caught = [row for row in train_rows if place_of(row) in keys]
    if caught:
        raise FinishedError(
            f"{len(caught)} training row(s) sit on a location pinned to the {head} evaluation "
            f"side, e.g. batch {caught[0].get('batch')!r}. A blind slice is spent the moment it "
            f"trains — fix the split, never the pin."
        )
    return {"pinned_locations": len(keys), "checked_rows": len(train_rows), "ok": True}


__all__ = [
    "HEADS",
    "RECIPE_KEYS",
    "SCALE",
    "SCHEMA",
    "FinishedError",
    "Resolution",
    "append",
    "assert_pin_holds",
    "batch_path",
    "check",
    "crossovers",
    "eval_split_path",
    "head_of",
    "pinned",
    "place_of",
    "read",
    "recipe",
    "register",
    "registry",
    "registry_path",
    "render_key",
    "render_row",
    "resolve",
    "resolved",
    "routed_to",
    "routes_to",
    "row_dir",
    "row_paths",
    "split_recipe_path",
    "store_dir",
    "tiers",
    "write_pin",
]
