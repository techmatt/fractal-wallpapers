"""Why a walk may score the picture it already made, checked before it makes one.

A walk's `expand` draws every gate survivor at 384×216, one field sample per
pixel, through the run's colormap — and that frame is **byte-identical** to the
same location's cached tile at [`tiles.NODE_REGIME`], which is one of the three
regimes the shipped location head was trained over. Measured, not argued: 0 of
82,944 pixels differ and the JPEGs compare equal. So the head can be asked about
the gate render, and a second picture of the same place at the deploy geometry
buys nothing — it was 58.7% of a production run's clean wall.

The identity is not free, though, and it is not one setting. It rests on four,
each of which can be moved independently and none of which announces itself:

* the walk's `--colormap` is the tile pool's **floor palette**, which is the map
  every canonical tile is drawn through;
* that map is **cyclic**, because the tile and view paths bake `mirror` into the
  palette for a map that does not wrap and the node path never mirrors — so a
  non-cyclic walk is a different picture, refused rather than folded;
* the node frame is the node regime's frame, which `--node-width` can move;
* the iteration cap the engine gives a width is still the one the tile corpus
  was **recorded** at. The cap decides what counts as interior, so a corpus built
  under one policy and a walk drawn under another are two different pictures of
  every location, and nothing about either one looks wrong.

This module turns all four into a refusal taken *before* a run writes its first
row. It is a run-start check on purpose: a harvest is an unattended program of
several hours, and an identity that failed silently would produce a full ledger
of scores read off pictures the head was never trained on — a ledger nobody can
tell from a good one afterwards.

**The cap is asked, never restated.** `maxiter::for_width` lives in the engine
and this side holds no copy of it; the check reads the caps the tile build
recorded against the caps the engine gives those same widths today. That is the
same arrangement `home-view` has, for the same reason.

## And once a run, the claim is measured rather than only checked

The four settings say the two pictures *are* the same file. What they cannot say
is whether the head's two reads would decide the same thing if they were not —
and that is the question a regression would show up in. So every run draws a
small seeded sample of its own survivors, scores them a second time at the deploy
geometry, and counts the decisions that moved at the three acting gates.

It is a **report and never a gate**: nothing in the run reads the number, no row
changes because of it, and a bad one is a thing for a person to look at. The
pre-registered cross-regime bars ([`fractal_wallpapers.models.regime_flips`]) are
where a decision about this head gets made; this is standing insurance on the
live candidate population, at about a minute of a multi-hour leg.
"""

from __future__ import annotations

import random
from pathlib import Path

#: How many of a build's locations the cap check reads. The tile plan is
#: shuffled, so a prefix is a fair sample of the whole corpus rather than of
#: whichever family sorts first — and twenty locations span enough octaves of zoom
#: that a policy which moved anywhere would have to move outside all of them to
#: pass.
CAP_SAMPLE = 20


class IdentityBroken(RuntimeError):
    """The gate render is not the picture the head was trained on.

    Raised before a walk writes anything. Every message names the setting that
    moved and what it has to be, because the failure it prevents — a ledger of
    scores read off the wrong distribution — is invisible in the ledger itself.
    """


def enforce(colormap: str, node_width: int, regime, log=print) -> dict:
    """Refuse unless the gate render is this regime's tile, and record what held.

    Returns the record a run header carries: the four settings, the values they
    were checked at, and the caps the check was taken against. A run that scores
    its own gate renders is answerable for that claim, so the claim travels with
    the ledger rather than only with the code that made it.
    """
    from fractal_wallpapers.models import location_view

    try:
        floor_palette = location_view.canonical_map()
    except location_view.ViewError as refusal:
        raise IdentityBroken(str(refusal)) from refusal

    if colormap != floor_palette:
        raise IdentityBroken(
            f"this walk draws through {colormap!r}, but the tile pool's floor palette is "
            f"{floor_palette!r}. The head reads the gate render as a tile, and a tile is "
            f"drawn through the floor palette — so scoring these frames would be asking it "
            f"about a distribution nobody trained it on. Run with "
            f"--colormap {floor_palette}, or --no-scoring to walk on the structural gates."
        )

    if colormap not in location_view.cyclic_maps():
        raise IdentityBroken(
            f"{colormap!r} is not a cyclic map. The tile and view paths mirror the palette of "
            f"a map that does not wrap, and the node path never mirrors, so the gate render "
            f"and the tile would be two different pictures of one place. A non-cyclic walk "
            f"that scores its own gate renders is Matt's ruling to make, not a fallback."
        )

    if int(node_width) != int(regime.tile[0]):
        raise IdentityBroken(
            f"--node-width {int(node_width)} draws a frame this head has no tiles of: the node "
            f"regime is {regime.spelled}, so the gate render has to be {regime.tile[0]} wide. "
            f"Either walk at {regime.tile[0]}, or pass --no-scoring."
        )

    caps = _caps(regime)
    log(
        f"[identity] gate render = {regime.spelled} tile through {colormap} (cyclic); "
        f"cap policy matched on {len(caps)} recorded location(s)"
    )
    return {
        "regime": regime.spelled,
        "colormap": colormap,
        "cyclic": True,
        "node_width": int(node_width),
        "caps": caps,
        "holds": (
            "the walk's gate render is byte-identical to this location's tile at this regime, "
            "so the head is asked about the picture it was trained on"
        ),
    }


def _caps(regime) -> dict:
    """The cap check: what the build recorded against what the engine gives now."""
    from fractal_wallpapers import engine
    from fractal_wallpapers.models import tiles as tile_module

    manifest = tile_module.manifest_path(regime)
    try:
        recorded = tile_module.recorded_caps(regime, CAP_SAMPLE)
    except FileNotFoundError as absent:
        raise IdentityBroken(
            f"{manifest} is not on this machine, so the cap the head's own pictures were "
            f"drawn at cannot be checked — and the gate render is only that picture if the "
            f"cap policy has not moved since the corpus was built. Restore the tile records "
            f"(`fractal-wallpapers storage restore tiles`), build the {regime.spelled} regime "
            f"(`fractal-wallpapers tiles build --tile 384x216 --supersample 1`), or pass "
            f"--no-scoring."
        ) from absent
    if not recorded:
        raise IdentityBroken(
            f"{manifest} holds no rows, so there is no recorded cap to check the engine's "
            f"policy against."
        )

    widths = [row["width"] for row in recorded]
    now = engine.maxiter_for(widths)
    moved = [
        {"width": row["width"], "recorded": row["maxiter"], "engine": cap}
        for row, cap in zip(recorded, now, strict=True)
        if row["maxiter"] != cap
    ]
    if moved:
        first = moved[0]
        raise IdentityBroken(
            f"the engine's iteration cap has moved since the {regime.spelled} tiles were "
            f"built: {len(moved)} of {len(recorded)} sampled locations disagree, the first at "
            f"width {first['width']} — recorded {first['recorded']}, engine now "
            f"{first['engine']}. The cap decides what counts as interior, so every gate render "
            f"is a different picture from the tile the head learned this location on. Rebuild "
            f"the corpus at the current policy, or pass --no-scoring."
        )
    return {
        "manifest": _named(manifest),
        "locations": len(recorded),
        "widths": [widths[0], widths[-1]],
        "matched": len(recorded),
    }


def _named(path: Path) -> str:
    """A manifest as a record may carry it, or as it was if it is outside the tree."""
    from fractal_wallpapers.paths import tracked_name

    return tracked_name(path)


# --------------------------------------------------------------------------- #
# The per-run sanity line.
# --------------------------------------------------------------------------- #
#: Survivors a run dual-scores. Small on purpose: the line is insurance, not a
#: measurement, and the bars that measure this live in `models.regime_flips` over
#: a stratified draw of four thousand.
SAMPLE = 100

#: What the sample keeps of a scored row. Everything a deploy-geometry view is
#: made from, and the verdict the run already recorded — so the second read is
#: compared against the number that actually landed on the ledger rather than
#: against a re-derivation of it.
KEPT = ("family", "viewport", "maxiter", "score", "score_great", "score_regime")


class Sample:
    """A seeded reservoir of one run's survivors, held for a second read.

    A reservoir rather than a prefix: a walk's first batches are its shallowest,
    so the first hundred survivors are a sample of the top of every lineage and
    of nothing else. Drawn on its own stream, never the walk's — a sample that
    consumed the run's randomness would change which nodes the frontier popped,
    and an insurance line that moves the run is not insurance.

    Not checkpointed, so a resumed run samples the batches it served after the
    resume. The report says how many survivors were offered, which is what makes
    that visible rather than something a reader has to know.
    """

    def __init__(self, size: int = SAMPLE, seed: int = 0):
        self.size = max(0, int(size))
        self.rng = random.Random(f"gate-flips:{seed}")
        self.seen = 0
        self.rows: list[dict] = []

    def offer(self, candidate: dict) -> None:
        """Show the sample one scored survivor."""
        if self.size == 0 or candidate.get("score") is None:
            return
        self.seen += 1
        kept = {field: candidate.get(field) for field in KEPT}
        if len(self.rows) < self.size:
            self.rows.append(kept)
            return
        index = self.rng.randrange(self.seen)
        if index < self.size:
            self.rows[index] = kept


def dual_score(sample: Sample, scorer, directory: Path, log=print) -> dict | None:
    """Read the sample again at the deploy geometry and count the moved decisions.

    Serial, and into a directory of the run's own: `location_views` is the record
    of what production scored at the deploy geometry and stops growing when a walk
    stops rendering there, so a sanity read must not quietly start refilling it.

    `None` where there is nothing to say — an unsampled run, a scorer that already
    reads the deploy geometry and would be comparing a number with itself, or one
    that cannot be asked to read another regime at all.

    The second reader is the *same judge*, made by the scorer rather than here:
    the question is whether a verdict moves with the picture, so the artifact, the
    device and the batch size all have to be held still, and only the scorer knows
    what it is holding.
    """
    import time

    from fractal_wallpapers.models import tiles as tile_module

    regime = getattr(scorer, "regime", None)
    twin = getattr(scorer, "at", None)
    if not sample.rows or regime is None or regime == tile_module.CANONICAL_REGIME:
        return None
    if not callable(twin):
        return None

    started = time.monotonic()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    against = twin(tile_module.CANONICAL_REGIME, directory)
    readings = against.read(sample.rows)

    flips = {gate["gate"]: 0 for gate in _gates()}
    compared = 0
    failed = 0
    for row, reading in zip(sample.rows, readings, strict=True):
        if reading.score is None:
            failed += 1
            continue
        compared += 1
        here = {"p_ge3": row.get("score"), "p_ge4": row.get("score_great")}
        there = {"p_ge3": reading.score, "p_ge4": reading.great}
        for gate in _gates():
            one, two = here[gate["field"]], there[gate["field"]]
            if one is None or two is None:
                continue
            if (one >= gate["edge"]) != (two >= gate["edge"]):
                flips[gate["gate"]] += 1

    seconds = time.monotonic() - started
    return {
        "regime": (regime or tile_module.CANONICAL_REGIME).spelled,
        "against": tile_module.CANONICAL_REGIME.spelled,
        "survivors": sample.seen,
        "sampled": len(sample.rows),
        "compared": compared,
        "failed": failed,
        "flips": flips,
        "seconds": round(seconds, 1),
        "views": {
            k: v
            for k, v in (getattr(against, "summary", dict)() or {}).items()
            if k in ("rendered", "reused")
        },
        "line": line(flips, compared, tile_module.CANONICAL_REGIME.spelled, seconds),
        "acts": "no. Reported and never read: nothing in this run turns on it.",
    }


def line(flips: dict, compared: int, against: str, seconds: float) -> str:
    """The sanity read as the one line a run summary prints."""
    if not compared:
        return f"0 survivors could be re-scored at {against}, so no decision was compared"
    moved = ", ".join(f"{count} {gate}" for gate, count in flips.items())
    return (
        f"{compared} survivors re-scored at {against} in {seconds:.0f}s: {moved} "
        f"(report only, nothing acts on it)"
    )


def _gates() -> tuple[dict, ...]:
    """The three decisions a location score makes, off their own owners."""
    from fractal_wallpapers.models import regime_flips

    return regime_flips.gates()


__all__ = [
    "CAP_SAMPLE",
    "KEPT",
    "SAMPLE",
    "IdentityBroken",
    "Sample",
    "dual_score",
    "enforce",
    "line",
]
