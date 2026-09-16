"""The three pictures a dot carries, and what a link to each can and cannot say.

Left to right on the page, and in that order in the record:

| slot | a `mandelbrot` place | a `julia` place |
| --- | --- | --- |
| `mandelbrot` | the place's own frame | a neighbourhood plate `plate_width` wide around `c` |
| `julia` | the Julia set at the centre of that frame | the place's own Julia frame |
| `gallery` | the seat if it has one, else its best row by `p_fine` | the same |

The first two are drawn **plain** — the location head's own mode and canonical map,
unlevelled — because they are a view of a place rather than a picture of one. The gallery
slot is the row's own recipe.

## The tone curve, in the permalink's own spelling

Every candidate is drawn with `band_autolevel/v1` switched on, and where the operator
acted the picture is the map's stops pushed through a curve. The permalink contract carries
that curve in its `level` key as `band_autolevel/v1:<black_pt>,<white_pt>,<exponent>,
<out_ends[0]>,<out_ends[1]>`, each number spelled the way JavaScript spells it, so the
gallery slot carries exactly that string where the curve was recorded. [`tone_of`] reads
it through [`curation.stamps.for_rows`], the one door onto a run's stamps, and answers in
the website's own three words:

* `curved` — the run recorded the curve; `level` carries it.
* `clean` — the operator did not act (or cannot act on this mode), so the picture is the
  map's own and a link needs no `level`.
* `lost` — the operator acted, or may have, and no record holds the numbers. `level` is
  `null`, `gap` says what is missing, and the refusal list names the operator. **The
  atlas re-derives nothing to fill the gap**: a curve re-measured off the picture is a
  different curve, and `curate autolevel backfill` — which re-renders the base at
  candidate geometry and says `rederived` on the stamp — is the one place a missing
  curve is made. `rotation` runs were the standing case until 2026-09-16, when they
  started writing `sequence.jsonl` and their seats were backfilled.

## What the refusal list says

`refused` names what the recipe holds that a link cannot carry, in the short forms the
website's contract test holds the record to: `colormap <name>` for a map the library does
not hold (the explorer bakes every map it does), `mirror on a cyclic map`, `curve <name>`
for a field curve other than the linear one, and `autolevel band_autolevel/v1` where the
tone is `lost`. What the explorer's contract accepts beyond that is the contract's to say,
in JavaScript, and is deliberately not re-read here.
"""

from __future__ import annotations

import json
from decimal import Decimal

#: The one tone operator a link may name. Its version is part of the name.
OPERATOR = "band_autolevel/v1"

#: The three answers [`tone_of`] gives, spelled as the website's seat gallery spells them.
CLEAN, CURVED, LOST = "clean", "curved", "lost"

SLOTS = ("mandelbrot", "julia", "gallery")


def js_number(value: float) -> str:
    """A double as JavaScript's `Number.prototype.toString` writes it.

    The digits are Python's shortest round-trip digits, which are the same digits
    JavaScript picks; only where the decimal point goes and when an exponent is used
    differ, and this is ECMA-262's `Number::toString` rule for placing them.
    """
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError(f"{value!r} has no spelling a link can carry")
    if value == 0:
        return "0"
    sign, digits, exponent = Decimal(repr(value)).as_tuple()
    text = "".join(str(d) for d in digits).rstrip("0") or "0"
    k = len(text)
    n = len(digits) + exponent
    head = "-" if sign else ""
    if k <= n <= 21:
        return head + text + "0" * (n - k)
    if 0 < n <= 21:
        return head + text[:n] + "." + text[n:]
    if -6 < n <= 0:
        return head + "0." + "0" * (-n) + text
    power = n - 1
    mark = "+" if power >= 0 else "-"
    mantissa = text if k == 1 else text[0] + "." + text[1:]
    return f"{head}{mantissa}e{mark}{abs(power)}"


def level_text(curve: dict) -> str:
    """A recorded curve as the permalink's `level` value."""
    numbers = [curve["black_pt"], curve["white_pt"], curve["exponent"], *curve["out_ends"]]
    return f"{OPERATOR}:{','.join(js_number(number) for number in numbers)}"


def run_of(ledger_row: dict) -> str:
    """`<store>/<run>` for the run a ledger row's picture was made by, or `unknown`."""
    parts = [part for part in str(ledger_row.get("picture") or "").split("/") if part]
    if len(parts) >= 4 and parts[1] == "curation":
        return f"{parts[2]}/{parts[3]}"
    run = (ledger_row.get("provenance") or {}).get("run")
    return f"unknown/{run}" if run else "unknown"


def tone_of(ledger_row: dict, stamp: dict | None) -> dict:
    """`{tone, level, gap, from}` for one gallery row and the stamp its run recorded."""
    recipe = ledger_row.get("recipe") or {}
    source = run_of(ledger_row)
    switch = (recipe.get("autolevel") or {}).get("switch")
    if switch != "on":
        # The operator's own ruling that it has nothing to say about this kind of mode —
        # a direct trap paints over a flat ground — so there was never a curve.
        return {"tone": CLEAN, "level": None, "gap": None, "from": source}
    if stamp is None:
        store = source.split("/", 1)[0]
        return {
            "tone": LOST,
            "level": None,
            "gap": f"the tone curve, which a {store} run does not record",
            "from": source,
        }
    if not stamp.get("acted"):
        return {"tone": CLEAN, "level": None, "gap": None, "from": source}
    curve = stamp.get("curve") or {}
    wanted = ("black_pt", "white_pt", "exponent", "out_ends")
    if (
        not curve.get("applies")
        or curve.get("identity")
        or any(curve.get(k) is None for k in wanted)
    ):
        return {
            "tone": LOST,
            "level": None,
            "gap": f"the tone curve, which {source} recorded as a fact and not as coefficients",
            "from": source,
        }
    return {"tone": CURVED, "level": level_text(curve), "gap": None, "from": source}


def refusals(recipe: dict, library: set[str], cyclic: set[str], tone: str | None) -> list[str]:
    """What of this recipe a link cannot carry, in the record's short forms."""
    refused: list[str] = []
    colormap = str(recipe.get("colormap") or "")
    if colormap not in library:
        refused.append(f"colormap {colormap}")
    if (recipe.get("palette") or {}).get("mirror") and colormap in cyclic:
        refused.append("mirror on a cyclic map")
    curve = str(recipe.get("curve") or "linear")
    if curve != "linear":
        refused.append(f"curve {curve}")
    if tone == LOST:
        refused.append(f"autolevel {OPERATOR}")
    return refused


def julia_family(c) -> dict:
    return {"kind": "julia", "degree": 2, "c": [str(c[0]), str(c[1])]}


def viewport_of(key_text: str) -> dict:
    """The frame a location key names, as the three decimal strings it holds."""
    key = json.loads(key_text)
    return {"center_re": str(key[3]), "center_im": str(key[4]), "width": str(key[5])}


def views_of(place, plane_family: dict, julia_home: dict, plate_width: str, canonical: str):
    """The dot's two location views, as recipes with `maxiter` still to be asked for."""
    from fractal_wallpapers.models import location_view

    from .population import JULIA

    def plain(family: dict, viewport: dict, what: str) -> dict:
        return {
            "family": family,
            "viewport": viewport,
            "maxiter": None,
            "mode": location_view.MODE,
            "mode_params": {},
            "curve": location_view.CURVE,
            "colormap": canonical,
            "palette": None,
            "what": what,
        }

    if place.partition == JULIA:
        key = json.loads(place.location)
        c = [str(key[2][0][0]), str(key[2][0][1])]
        return {
            "mandelbrot": plain(
                dict(plane_family),
                {"center_re": str(place.x), "center_im": str(place.y), "width": plate_width},
                f"a neighborhood plate {plate_width} wide",
            ),
            "julia": plain(
                julia_family(c), viewport_of(place.location), "the place's own Julia frame"
            ),
        }
    key = json.loads(place.location)
    return {
        "mandelbrot": plain(
            dict(plane_family), viewport_of(place.location), "the place's own frame"
        ),
        "julia": plain(
            julia_family([str(key[3]), str(key[4])]),
            dict(julia_home),
            "the Julia set at the center of that frame",
        ),
    }


def gallery_of(place, ledger: dict) -> tuple[str, dict] | None:
    """`(key, recipe)` for the wallpaper a place stands behind: its seat, or its best row.

    Two sources and no third. A seated place shows the picture the record seats; every
    other place shows its best row by `p_fine`, which clears the bar because clearing the
    bar is what put the place on the plate. So this slot never falls back to a location
    view, and a reader hovering a dot is always looking at a wallpaper.
    """
    tried = []
    if place.seat is not None:
        tried.append((str(place.seat["key"]), "seated"))
    tried += [(key, "best row by the fine score") for _value, key in place.fine_rows]
    for key, source in tried:
        stored = ledger.get(key)
        if stored is None:
            continue
        recipe = dict(stored["recipe"])
        recipe["source"] = source
        recipe["seated"] = source == "seated"
        recipe["key"] = key
        recipe["what"] = None
        recipe["p_fine"] = next((value for value, other in place.fine_rows if other == key), None)
        return key, recipe
    return None
