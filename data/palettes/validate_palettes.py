#!/usr/bin/env python3
"""Mechanical checker for a batch of authored palettes, as the generator emits them.

Run it on your own output; it is not part of the package and imports nothing from
it, so a reader can copy this one file next to a batch and run it:

```text
python validate_palettes.py batch.json      # one emitted batch (a JSON array)
python validate_palettes.py --dir results   # every batch in a directory
```

The exit code is 0 exactly when there are no ERRORs. Warnings never change it.

**This file is authoritative for the mechanical rules.** `generator_prompt.md`
restates the same numbers in prose for the model's benefit; if a threshold moves,
it moves in the CONFIG block below and the prompt is edited to match.

Two severities, and the split is deliberately permissive:

* **ERROR** — a rule that comes from how the renderer consumes a palette. A
  violation is render-breaking or spec-breaking.
* **warn** — a heuristic that is usually right about a dull palette and is
  sometimes wrong about a good strange one. Advisory, always.

The failure mode of this generator has been *samey* palettes rather than
malformed ones, so only genuinely broken things are errors: an unusual-but-valid
palette — a deep hued dark, a narrow range, an off value key — warns at most, and
the checker never talks anybody out of a good weird palette.

## The batch shape it reads

```text
palette : {name, mood, architecture, skeleton, value_key, complexity, stops}
stop    : {pos, oklch: [L, C, H], role, [segment], [keypoint]}
```

`segment` defaults to `smooth` when absent. The last stop repeats the first: a
palette is a closed loop, which is what lets the densifier bake it seam-free.
`value_key` and `complexity` are also accepted nested under `axes`, which is where
an older generator put them.

## Two invariants hold over a whole set, not one palette

1. **Closure.** Every palette closes: its first stop equals its last in OKLCH
   within tolerance, and `pos` runs 0→1. Tolerance rather than byte equality —
   a near-closed loop is still seam-free, an open one is not.
2. **Unique names.** No name repeats inside a batch or across a directory of
   them. The name is the join key between the palette, its dense colormap and its
   provenance row, so a collision silently collapses records.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

# ============================ CONFIG (authoritative) ==========================

#: complexity → station-count band, inclusive, counting the closing loop stop.
BAND = {1: (4, 5), 2: (5, 6), 3: (6, 7), 4: (7, 9), 5: (8, 10), 6: (11, 15)}

#: A cliff carries only a SMALL step: this much hue, and this fraction of the
#: palette's own lightness range. Past either, it is a value jump wearing a
#: cliff's name.
CLIFF_HUE_MAX = 30
CLIFF_DL_FRAC = 1 / 3

#: Closure: how far the first and last stop may sit apart and still close. Hue is
#: ignored when both endpoints are near-achromatic, because hue is meaningless
#: there and comparing it would fail palettes that open and close on black.
CLOSURE_DL_MAX = 0.01
CLOSURE_DC_MAX = 0.01
CLOSURE_DH_MAX = 1.0
CLOSURE_HUE_IGNORE_C = 0.02

#: A big saturated hue jump on a smooth segment renders as a dirty seam unless it
#: routes through black or white. "Big" and "saturated" are these; "through black
#: or white" is an endpoint past one of the two lightness gates.
JUMP_HUE_MIN = 55
JUMP_CHROMA_MIN = 0.04
NEAR_BLACK = 0.20
NEAR_WHITE = 0.88

#: Skeletons whose canonical shape has fewer than two interior lightness extrema
#: by design. The "≥2 extrema" heuristic is a guaranteed false positive on them —
#: an inverted arc has one trough, and a cliff replaces a smooth extremum with a
#: step — so they are exempt from it rather than warned about forever.
FEW_EXTREMA_SKELETONS = {"inverted-arc", "cliff-in-mids"}

#: The advisory heuristics: a wide value range always; a high key that does not
#: bottom out in black; a low key that never reaches it; chroma held at an
#: extreme lightness, where near-black and near-white are meant to be achromatic.
MIN_VALUE_RANGE = 0.55
HIGH_KEY_MIN_L = 0.14
LOW_KEY_MAX_DARK = 0.12
EXTREME_L_LO = 0.08
EXTREME_L_HI = 0.94
EXTREME_C_MAX = 0.10

#: What the batch-spread report calls vivid and muted, by peak chroma.
VIVID_PEAK_C = 0.15
MUTED_PEAK_C = 0.13

# =============================================================================


def hue_distance(one: float, other: float) -> float:
    """Degrees between two hues, the short way round."""
    gap = abs(one - other) % 360
    return min(gap, 360 - gap)


def interior_extrema(lightness: list[float]) -> int:
    """How many times the lightness turns around, ends excluded."""
    return sum(
        1
        for index in range(1, len(lightness) - 1)
        if (lightness[index] - lightness[index - 1]) * (lightness[index + 1] - lightness[index])
        < -1e-9
    )


def axis(palette: dict, key: str):
    """One axis value, from `axes` where an older generator nested it."""
    axes = palette.get("axes")
    if isinstance(axes, dict) and key in axes:
        return axes[key]
    return palette.get(key)


def segment_of(stop: dict) -> str:
    """How the ramp leaves this stop. Absent means smooth."""
    return stop.get("segment", "smooth")


def is_glow(stop: dict) -> bool:
    """Whether this stop is the palette's glow, by role or by keypoint."""
    keypoint = stop.get("keypoint")
    return stop.get("role") == "glow" or (
        isinstance(keypoint, dict) and keypoint.get("type") == "glow_band"
    )


def closure_error(palette: dict) -> str | None:
    """The palette's closure failure, with its deltas, or `None` if it closes."""
    first, last = palette["stops"][0]["oklch"], palette["stops"][-1]["oklch"]
    lightness_gap, chroma_gap = abs(first[0] - last[0]), abs(first[1] - last[1])
    hue_gap = hue_distance(first[2], last[2])
    hue_matters = min(first[1], last[1]) >= CLOSURE_HUE_IGNORE_C
    open_loop = (
        lightness_gap > CLOSURE_DL_MAX
        or chroma_gap > CLOSURE_DC_MAX
        or (hue_matters and hue_gap > CLOSURE_DH_MAX)
    )
    if not open_loop:
        return None
    ignored = "" if hue_matters else ", hue ignored"
    return (
        f"open loop: first {first} != last {last} (dL={lightness_gap:.3f}, "
        f"dC={chroma_gap:.3f}, dH={hue_gap:.1f}deg{ignored})"
    )


def find_duplicate_names(pairs) -> dict[str, list[str]]:
    """`{name: [files]}` for every name that appears more than once."""
    by_name: dict[str, list[str]] = {}
    for name, source in pairs:
        by_name.setdefault(name, []).append(source)
    return {name: sources for name, sources in by_name.items() if len(sources) > 1}


def validate_palette(palette: dict) -> tuple[list[str], list[str]]:
    """`(errors, warnings)` for one palette."""
    errors: list[str] = []
    warnings: list[str] = []
    stops = palette["stops"]
    lightness = [stop["oklch"][0] for stop in stops]
    chroma = [stop["oklch"][1] for stop in stops]
    hue = [stop["oklch"][2] for stop in stops]
    positions = [stop["pos"] for stop in stops]
    architecture = palette.get("architecture", "?")
    complexity = axis(palette, "complexity")
    complexity = int(complexity) if complexity is not None else None
    value_key = axis(palette, "value_key")
    value_range = max(lightness) - min(lightness)
    brightest = lightness.index(max(lightness))
    darkest = lightness.index(min(lightness))

    # --- the loop and its ordering ------------------------------------------
    failure = closure_error(palette)
    if failure:
        errors.append(failure)
    if abs(positions[0]) > 1e-9 or abs(positions[-1] - 1.0) > 1e-9:
        errors.append(f"pos does not run 0->1 ({positions[0]}..{positions[-1]})")
    if any(positions[i + 1] <= positions[i] for i in range(len(positions) - 1)):
        errors.append("pos not strictly increasing")

    # --- station count against the complexity band --------------------------
    if complexity in BAND:
        low, high = BAND[complexity]
        if not low <= len(stops) <= high:
            errors.append(f"{len(stops)} stops outside cx{complexity} band {low}-{high}")

    # --- a glow is feathered: smooth on both sides --------------------------
    for index, stop in enumerate(stops):
        if not is_glow(stop):
            continue
        leaving = segment_of(stop)
        arriving = segment_of(stops[index - 1]) if index > 0 else "smooth"
        if leaving != "smooth" or arriving != "smooth":
            errors.append(f"glow at pos {stop['pos']} not feathered (in={arriving}, out={leaving})")

    # --- a cliff carries a small step, and never spans the extremes ---------
    for index in range(len(stops) - 1):
        if segment_of(stops[index]) != "cliff":
            continue
        step = abs(lightness[index + 1] - lightness[index])
        turn = hue_distance(hue[index], hue[index + 1])
        cap = value_range * CLIFF_DL_FRAC
        if step > cap + 1e-9:
            errors.append(
                f"cliff |dL| {step:.2f} > {CLIFF_DL_FRAC:.2f}*range ({cap:.2f}) "
                f"at pos {positions[index]}"
            )
        if turn > CLIFF_HUE_MAX:
            errors.append(
                f"cliff hue step {turn:.0f}deg > {CLIFF_HUE_MAX} at pos {positions[index]}"
            )
        if {index, index + 1} == {brightest, darkest}:
            errors.append(f"cliff spans brightest<->darkest at pos {positions[index]}")

    # --- a big saturated hue jump routes through black or white -------------
    for index in range(len(stops) - 1):
        if segment_of(stops[index]) not in ("smooth", "ease"):
            continue
        turn = hue_distance(hue[index], hue[index + 1])
        saturated = chroma[index] > JUMP_CHROMA_MIN and chroma[index + 1] > JUMP_CHROMA_MIN
        if turn <= JUMP_HUE_MIN or not saturated:
            continue
        pair = (lightness[index], lightness[index + 1])
        if min(pair) < NEAR_BLACK or max(pair) > NEAR_WHITE:
            continue
        errors.append(
            f"unrouted hue jump {turn:.0f}deg between mid-value stops "
            f"pos {positions[index]}->{positions[index + 1]} "
            f"(L {pair[0]:.2f}->{pair[1]:.2f}); route it through black or white"
        )

    # --- advisory heuristics ------------------------------------------------
    extrema = interior_extrema(lightness)
    skeleton = palette.get("skeleton", "?")
    if (
        architecture != "mono-temperature-ramp"
        and skeleton not in FEW_EXTREMA_SKELETONS
        and complexity is not None
        and complexity >= 3
        and extrema < 2
    ):
        warnings.append(f"only {extrema} interior L extrema (want >=2 for cx>=3)")
    if value_range < MIN_VALUE_RANGE:
        warnings.append(f"narrow value range {value_range:.2f} (< {MIN_VALUE_RANGE})")
    if value_key == "high" and min(lightness) < HIGH_KEY_MIN_L:
        warnings.append(f"value_key high but darkest L={min(lightness):.2f} (< {HIGH_KEY_MIN_L})")
    if value_key == "low" and min(lightness) > LOW_KEY_MAX_DARK:
        warnings.append(f"value_key low but no true black (darkest L={min(lightness):.2f})")
    for one_l, one_c in zip(lightness, chroma, strict=True):
        if (one_l < EXTREME_L_LO or one_l > EXTREME_L_HI) and one_c > EXTREME_C_MAX:
            warnings.append(f"chroma C={one_c} high at extreme L={one_l}")

    return errors, warnings


def validate_batch(palettes: list[dict]) -> list[dict]:
    """One result row per palette: what it is, and what it failed."""
    out = []
    for palette in palettes:
        errors, warnings = validate_palette(palette)
        out.append(
            {
                "name": palette.get("name", "?"),
                "architecture": palette.get("architecture", "?"),
                "skeleton": palette.get("skeleton", "?"),
                "errors": errors,
                "warnings": warnings,
            }
        )
    return out


def batch_spread(palettes: list[dict]) -> dict:
    """How the batch spread across its aesthetic axes — the point of a batch."""

    def column(key: str) -> dict:
        nested = key in ("value_key", "complexity")
        return dict(Counter(axis(p, key) if nested else p.get(key) for p in palettes))

    peaks = [
        (p.get("name", "?"), round(max(s["oklch"][1] for s in p["stops"]), 2)) for p in palettes
    ]
    return {
        "architecture": column("architecture"),
        "skeleton": column("skeleton"),
        "value_key": column("value_key"),
        "complexity": column("complexity"),
        "vivid": sum(1 for _, peak in peaks if peak >= VIVID_PEAK_C),
        "muted": sum(1 for _, peak in peaks if peak < MUTED_PEAK_C),
        "peak_chroma": peaks,
    }


def load(path: Path) -> list[dict]:
    """One batch file as a list of palettes, however it wrapped them."""
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(document, dict):
        return document.get("palettes", document.get("data", [document]))
    return document


def report(path: Path) -> tuple[int, list[tuple[str, str]]]:
    """Print one batch's findings. `(errors, [(name, file)])` for the set check."""
    palettes = load(path)
    results = validate_batch(palettes)
    errors = sum(len(row["errors"]) for row in results)
    warnings = sum(len(row["warnings"]) for row in results)
    print(f"=== {path}: {len(palettes)} palettes | {errors} error(s), {warnings} warning(s) ===")
    for row in results:
        if not row["errors"] and not row["warnings"]:
            continue
        print(f"\n[{row['name']}]  ({row['architecture']} / {row['skeleton']})")
        for line in row["errors"]:
            print(f"   ERROR  {line}")
        for line in row["warnings"]:
            print(f"   warn   {line}")
    spread = batch_spread(palettes)
    print("\n--- batch spread ---")
    print("  architecture:", spread["architecture"])
    print("  skeleton    :", spread["skeleton"])
    print("  value_key   :", spread["value_key"])
    print("  complexity  :", spread["complexity"])
    print(
        f"  chroma      : {spread['vivid']} vivid (peak>={VIVID_PEAK_C}), "
        f"{spread['muted']} muted (peak<{MUTED_PEAK_C})"
    )
    return errors, [(p.get("name", "?"), str(path)) for p in palettes]


def report_duplicates(pairs, scope: str) -> int:
    """Print the name-uniqueness check over `scope`, and return its error count."""
    duplicates = find_duplicate_names(pairs)
    print(f"\n--- name uniqueness ({scope}) ---")
    if not duplicates:
        print(f"  OK: {len(pairs)} palette(s), all names unique")
        return 0
    for name, sources in sorted(duplicates.items()):
        print(f"   ERROR  duplicate name {name!r} in: {', '.join(sources)}")
    return len(duplicates)


def main() -> int:
    arguments = sys.argv[1:]
    if arguments and arguments[0] == "--dir":
        directory = Path(arguments[1] if len(arguments) > 1 else "results")
        files = sorted(directory.glob("*.json"))
        total, pairs = 0, []
        for path in files:
            errors, found = report(path)
            total += errors
            pairs += found
            print()
        total += report_duplicates(pairs, f"across {len(files)} file(s) in {directory}/")
        print(f"\n>>> TOTAL ERRORS across {len(files)} file(s): {total}")
        return 0 if total == 0 else 1
    path = Path(arguments[0] if arguments else "batch.json")
    total, pairs = report(path)
    total += report_duplicates(pairs, str(path))
    print(f"\n>>> TOTAL ERRORS: {total}")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
