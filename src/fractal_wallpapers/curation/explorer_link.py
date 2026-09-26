"""The explorer link a released picture carries: the site's permalink, spelled here.

Every full-size wallpaper this project writes carries, in its metadata, the link that
opens the same picture in the website's explorer (`embedded_links_ckpt145`). The bytes
are [`curation.embed_link`]'s; this module is the *link* — a render row, its mode and
its palette pass, and the tone curve the autolevel operator drew it through, spelled as
`explorer/permalink.js` in the `fractal-website` checkout spells a view.

## A second author of one contract, held to the first

That contract is JavaScript and belongs to the site, whose `builder/emit.mjs` says in
so many words that a Python spelling of it would be a contract with two authors. This is
that second author, and it exists because the release writer is here and cannot ask
node. What keeps it honest is on the other side: the site's `builder check` runs
[`query_of`] next door over the seats of the published-candidate gallery and holds every
string it spells to the one `emit.mjs` spells for the same recipe, byte for byte — the
`stamps` check. So a change to the contract lands as a failing check there, and the
tables below are the ones that check reads.

What is *not* restated is what the engine already owns: a family's home view, the
iteration cap its width policy gives, a mode's catalog curve and its settled constants
are all asked of [`engine`] and [`engine_spec`], the same sources the site bakes its own
copies from.

## A link that is nearly the picture is not written

The site's rule: a link that opens something close to the picture is worse than none.
So [`query_of`] returns a query or a reason, never an approximation. A family the
explorer does not draw, a mode it does not offer, a mode read through a curve its
catalog does not give it, a parameter the contract cannot spell, a cap outside what a
link may name — each is a refusal with the sentence that says which, and the file goes
out with no link in it. A release render is always a shallow (`f64`) picture, so the
link is always the shallow contract's; the Deep tab's links are written only by that tab.

## The base is one constant

[`EXPLORER_URL`] is the site's own address, `pages.SITE_URL` there with `explorer/`
after it. The hosting choice is not final; when it moves, it moves on both sides and the
site's `stamps` check fails until it has. `pins.EXPLORER_BASE` is a different thing — the
local server a person authors pins against — and is deliberately not this.
"""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
from urllib.parse import quote

from fractal_wallpapers import engine, engine_spec

#: Where a link written into a file points. The site's `SITE_URL` plus `explorer/`.
EXPLORER_URL = "https://techmatt.github.io/fractals/explorer/"

#: The shallow contract's version, `permalink.js`'s `VERSION`.
VERSION = 4

#: The family a link leaves out, `FAMILIES[0]`, and the mode, `MODES[0]`.
DEFAULT_FAMILY = "mandelbrot"
DEFAULT_MODE = "smooth"

#: The constants each family's link carries, in emit order — `permalink.js`'s `CONSTANTS`.
#: A family absent here is one the explorer does not draw.
CONSTANTS = {
    "mandelbrot": (),
    "multibrot3": (),
    "multibrot4": (),
    "multibrot5": (),
    "multibrot6": (),
    "julia": ("cx", "cy"),
    "julia3": ("cx", "cy"),
    "julia4": ("cx", "cy"),
    "julia5": ("cx", "cy"),
    "julia6": ("cx", "cy"),
    "phoenix": ("cx", "cy", "px", "py", "zx", "zy"),
    "phoenix_plane": ("px", "py"),
}

#: The modes the explorer offers, `permalink.js`'s `MODES` — the site's own roster.
MODES = frozenset(
    {
        "smooth",
        "tia",
        "stripe",
        "gaussian_int",
        "trap_circle",
        "curvature",
        "smooth_mean_angle",
        "smooth_angle_min",
        "smooth_trap_circle",
        "smooth_stripe",
        "smooth_curvature",
        "direct_trap_ring",
        "direct_trap_screen",
        "direct_trap_multiply",
        "direct_trap_lines",
        "threads",
        "itinerary",
    }
)

#: Each mode's parameters in emit order, `permalink.js`'s `MODE_PARAMETERS`.
MODE_PARAMETERS = {
    "stripe": ("density",),
    "trap_circle": ("radius",),
    "smooth_mean_angle": ("weight",),
    "smooth_angle_min": ("weight",),
    "smooth_trap_circle": ("radius", "weight"),
    "smooth_stripe": ("density", "weight"),
    "smooth_curvature": ("weight",),
    "direct_trap_ring": ("radius", "threshold", "opacity"),
    "direct_trap_screen": ("threshold", "opacity"),
    "direct_trap_multiply": ("threshold", "opacity"),
    "direct_trap_lines": ("threshold", "opacity"),
    "threads": ("sigma", "weight"),
    "itinerary": ("shift",),
}

#: The parameter a v3+ link asks the page to derive when it is absent, by mode —
#: `permalink.js`'s `DERIVED`. A recorded picture was drawn at the catalog's constant,
#: so its link writes that constant down rather than leaving the key out.
DERIVED = {
    "smooth_mean_angle": "weight",
    "smooth_angle_min": "weight",
    "smooth_curvature": "weight",
    "direct_trap_screen": "opacity",
    "direct_trap_multiply": "opacity",
    "direct_trap_lines": "opacity",
}

#: What a row's `mode_params` calls a composite's drawn weight, where a link says `weight`.
LEDGER_TEXTURE_WEIGHT = "texture_weight"

#: The palette pass's keys in emit order, each with its default and how it is written —
#: `permalink.js`'s `SHADE_KEYS`. A key at its default is left out.
SHADE_KEYS = (
    ("gamma", 1.0, "number"),
    ("cycles", 1.0, "number"),
    ("phase", 0.0, "number"),
    ("reverse", False, "flag"),
    ("mirror", False, "flag"),
    ("transfer", {"kind": "value"}, "tagged"),
    ("rolloff", {"kind": "none"}, "tagged"),
    ("scale", "leveled", "word"),
    ("lambda", 1.0, "number"),
    ("period", 1.0, "number"),
)

#: The tone operators a link can replay, `permalink.js`'s `OPERATORS`.
OPERATORS = frozenset({"band_autolevel/v1"})

#: The aspect a link means when it says nothing, and the largest side one may name.
DEFAULT_ASPECT = (16, 9)
ASPECT_LIMIT = 10000

#: The iteration caps a link may name, `CAP_FLOOR` and `CAP_LIMIT`. The limit is the
#: explorer's explicit ceiling, two million since the website's cap_split_ckpt145.
CAP_FLOOR = 50
CAP_LIMIT = 2_000_000

#: The longest a coordinate string may be, `COORDINATE_LIMIT`.
COORDINATE_LIMIT = 64


def js_number(value: float) -> str:
    """A number as JavaScript's `String(number)` writes it.

    The contract's `shortest`. Python's `repr` finds the same shortest round-tripping
    digits and then formats them differently — `1e-07` for `1e-7`, `100.0` for `100` —
    so the digits are taken from `repr` and laid out by ECMAScript's own rule.
    """
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError(f"{value} is not a number a link can carry")
    if value == 0:
        return "0"
    sign = "-" if value < 0 else ""
    held = Decimal(repr(abs(value))).as_tuple()
    # int(digits) × 10^exponent; every trailing zero dropped moves the exponent up one.
    digits = "".join(str(one) for one in held.digits).lstrip("0")
    exponent = held.exponent + len(digits) - len(digits.rstrip("0"))
    digits = digits.rstrip("0")
    # digits × 10^(n − k), in ECMAScript's names.
    k = len(digits)
    n = exponent + k
    if k <= n <= 21:
        return sign + digits + "0" * (n - k)
    if 0 < n <= 21:
        return sign + digits[:n] + "." + digits[n:]
    if -6 < n <= 0:
        return sign + "0." + "0" * (-n) + digits
    e = n - 1
    mantissa = digits if k == 1 else f"{digits[0]}.{digits[1:]}"
    return f"{sign}{mantissa}e{'+' if e >= 0 else '-'}{abs(e)}"


def encode(text: str) -> str:
    """`encodeURIComponent`, with the colon left alone — `permalink.js`'s `encode`."""
    return quote(str(text), safe="-_.!~*'()").replace("%3A", ":")


def encode_curve(text: str) -> str:
    """The same, leaving the slash and the comma alone too — `encodeCurve`."""
    return encode(text).replace("%2F", "/").replace("%2C", ",")


def url_of(query: str) -> str:
    """The absolute link: the explorer, then the query."""
    return f"{EXPLORER_URL}?{query}"


def family_name(family: dict) -> str | None:
    """A family as a link names it, or `None` for one the explorer does not draw."""
    kind = family.get("kind")
    degree = family.get("degree", 2)
    if isinstance(degree, float) and not degree.is_integer():
        return None
    degree = int(degree)
    if kind == "mandelbrot" or (kind == "multibrot" and degree == 2):
        name = "mandelbrot"
    elif kind == "multibrot":
        name = f"multibrot{degree}"
    elif kind == "julia":
        name = "julia" if degree == 2 else f"julia{degree}"
    elif kind == "phoenix":
        name = "phoenix"
    elif kind == "phoenix_m":
        name = "phoenix_plane"
    else:
        return None
    return name if name in CONSTANTS else None


def constants_of(name: str, family: dict) -> dict[str, str]:
    """A family's constants as the decimal strings the row holds. Absent is the origin."""
    c = family.get("c") or ("0", "0")
    p = family.get("p") or ("0", "0")
    z = family.get("z_prev") or ("0", "0")
    every = {"cx": c[0], "cy": c[1], "px": p[0], "py": p[1], "zx": z[0], "zy": z[1]}
    return {key: str(every[key]) for key in CONSTANTS[name]}


def level_of(stamp: dict | None) -> dict | None:
    """The tone curve a link replays, out of an autolevel stamp — or `None` where the
    operator did not move the picture: no stamp, a curve that does not apply, or one
    that is the identity. Replaying an identity curve is not free, which is why the site
    carries none."""
    if not stamp:
        return None
    curve = stamp.get("curve") or {}
    if not curve.get("applies") or curve.get("identity"):
        return None
    return {
        "operator": str(stamp["operator"]),
        "black_pt": float(curve["black_pt"]),
        "white_pt": float(curve["white_pt"]),
        "exponent": float(curve["exponent"]),
        "out_ends": [float(curve["out_ends"][0]), float(curve["out_ends"][1])],
    }


def _settled(mode: str) -> dict[str, float]:
    """The constant a derived parameter was drawn at, out of the engine's catalog — the
    same reading the site's `builder/explorer.py` bakes `SETTLED` with."""
    coloring = engine_spec.catalog().get(mode) or {}
    if coloring.get("kind") == "composite" and "texture_weight" in coloring:
        return {"weight": float(coloring["texture_weight"])}
    if coloring.get("kind") == "direct" and "opacity" in coloring:
        return {"opacity": float(coloring["opacity"])}
    return {}


def _catalog_curve(mode: str) -> str:
    """The curve a mode's catalog reads its field through; `linear` where it names none."""
    return str((engine_spec.catalog().get(mode) or {}).get("transform", "linear"))


def _tagged(value: dict) -> str:
    """A tagged shade value — `edge:0.3`, `none` — as `writeTagged` spells it."""
    for name, held in value.items():
        if name != "kind":
            return f"{value['kind']}:{js_number(held)}"
    return str(value["kind"])


def _aspect(resolution) -> tuple[int, int]:
    width, height = (int(side) for side in resolution)
    ratio = Fraction(width, height)
    return ratio.numerator, ratio.denominator


def query_of(
    *,
    family: dict,
    viewport: dict,
    maxiter: int | None,
    mode: str,
    mode_params: dict | None,
    curve: str | None,
    colormap: str,
    palette: dict | None,
    level: dict | None,
    resolution=DEFAULT_ASPECT,
    policy_cap: int | None = None,
) -> tuple[str | None, str | None]:
    """The canonical query for one picture, or `(None, why)` where no link is exact.

    Returned without the leading `?`. `level` is [`level_of`]'s answer; `resolution` is
    the frame's width and height, of which the link keeps only the shape. `policy_cap` is
    the engine's width policy at this width where the caller has already asked it — a
    batch asks once for every width rather than once a row — and is asked here otherwise.
    """
    name = family_name(family)
    if name is None:
        kind, degree = family.get("kind"), family.get("degree", 2)
        return None, f"the {kind} family at degree {degree} is not one the explorer draws"
    if mode not in MODES:
        return None, f"the {mode} render mode is not one the explorer offers"
    held_curve = _catalog_curve(mode)
    if curve is not None and str(curve) != held_curve:
        return None, (
            f"this picture reads {mode} through a {curve} curve and the catalog's {mode} is "
            f"{held_curve}, which no key of a link can say"
        )

    params = dict(mode_params or {})
    if LEDGER_TEXTURE_WEIGHT in params:
        params["weight"] = params.pop(LEDGER_TEXTURE_WEIGHT)
    wanted = MODE_PARAMETERS.get(mode, ())
    stray = sorted(set(params) - set(wanted))
    if stray:
        return None, f"a {mode} picture carries {', '.join(stray)}, which a link cannot spell"
    derived = DERIVED.get(mode)
    if derived is not None and derived not in params:
        settled = _settled(mode).get(derived)
        if settled is None:
            return None, f"the catalog gives no settled {derived} for {mode}"
        params[derived] = settled

    frame = {
        "x": str(viewport["center_re"]),
        "y": str(viewport["center_im"]),
        "w": str(viewport["width"]),
    }
    constants = constants_of(name, family)
    for key, text in {**frame, **constants}.items():
        if len(text) > COORDINATE_LIMIT:
            return None, (
                f"{key} is {len(text)} characters and a link caps a coordinate "
                f"at {COORDINATE_LIMIT}"
            )

    parts = [f"v={VERSION}"]
    if name != DEFAULT_FAMILY:
        parts.append(f"f={encode(name)}")
    parts += [f"{key}={encode(constants[key])}" for key in CONSTANTS[name]]
    if mode != DEFAULT_MODE:
        parts.append(f"m={encode(mode)}")
    parts += [f"{key}={encode(js_number(params[key]))}" for key in wanted if key in params]

    home = engine.home_view(family)
    homes = {"x": home["center_re"], "y": home["center_im"], "w": home["width"]}
    for key in ("x", "y", "w"):
        if frame[key] != js_number(float(homes[key])):
            parts.append(f"{key}={encode(frame[key])}")

    if maxiter is not None:
        cap = int(maxiter)
        if not CAP_FLOOR <= cap <= CAP_LIMIT:
            return None, f"a cap of {cap:,} is outside what a link may name"
        if policy_cap is None:
            policy_cap = engine.maxiter_for([frame["w"]])[0]
        if cap != int(policy_cap):
            parts.append(f"n={cap}")

    across, down = _aspect(resolution)
    if (across, down) != DEFAULT_ASPECT:
        if max(across, down) > ASPECT_LIMIT:
            return None, f"a {across}:{down} frame is a shape no link can name"
        parts.append(f"a={across}:{down}")

    parts.append(f"p={encode(colormap)}")
    shade = dict(palette or {})
    for key, fallback, kind in SHADE_KEYS:
        value = shade.get(key, fallback)
        if kind == "number":
            if float(value) != float(fallback):
                parts.append(f"{key}={encode(js_number(value))}")
        elif kind == "flag":
            if bool(value) != fallback:
                parts.append(f"{key}={'1' if value else '0'}")
        elif kind == "tagged":
            if _tagged(value) != _tagged(fallback):
                parts.append(f"{key}={encode(_tagged(value))}")
        elif value != fallback:
            parts.append(f"{key}={encode(str(value))}")

    # Last, and none under the absolute scale, which does not level — `levelUnder`.
    if level is not None and shade.get("scale", "leveled") != "absolute":
        if level["operator"] not in OPERATORS:
            return None, f"the tone operator {level['operator']} is not one a link can replay"
        numbers = [level["black_pt"], level["white_pt"], level["exponent"], *level["out_ends"]]
        written = f"{level['operator']}:{','.join(js_number(one) for one in numbers)}"
        parts.append(f"level={encode_curve(written)}")
    return "&".join(parts), None


def for_task(task, stamp: dict | None) -> tuple[str | None, str | None]:
    """The query for one [`release.Task`]'s picture, drawn with this autolevel stamp.

    Read off the row [`colorize.render_row`] builds — the one the engine was handed —
    rather than off the task, because that is where an unset curve becomes the
    candidate path's and an unset palette pass becomes the plain one, `mirror` decided
    by whether the map is cyclic. A link written from the task alone would say nothing
    about a mirror the picture has.
    """
    from fractal_wallpapers.curation import colorize
    from fractal_wallpapers.models import palette_sets

    drawn = colorize.render_row(
        task.row,
        task.mode,
        task.colormap,
        palette_sets.cyclic(),
        task.geometry,
        task.mode_params,
        task.curve,
        task.palette,
    )
    return query_of(
        family=drawn["family"],
        viewport=drawn["viewport"],
        maxiter=task.row.get("maxiter"),
        mode=drawn["mode"],
        mode_params=drawn["mode_params"],
        curve=drawn["curve"],
        colormap=drawn["colormap"],
        palette=drawn["recipe"],
        level=level_of(stamp),
        resolution=task.geometry.get("resolution", DEFAULT_ASPECT),
    )
