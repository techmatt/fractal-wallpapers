"""Everything a reader can set on a single render, as one JSON document.

`walkthrough` writes it as `parameters.json`. **Nothing in it is typed here twice**:
each part is read from the place that already decides it.

* the flags, their defaults and their help: `render`'s own argument parser;
* the modes, their tier and each mode parameter's default and range: the engine
  (`fractal-engine modes`, which reads `mode::parameter_range`);
* the palette knobs' defaults and ranges: `cli.common.PALETTE_KNOBS`, which
  `render`'s flags are built from;
* the colormap names: `palettes.drawable`, as `palettes list` prints them;
* the families: [`FAMILIES`] below, the one table of what each family takes, held
  to the engine's `FamilySpec` and to `--family`'s choices by the suite;
* the fractal families the pipeline walks: `supply.partitions.ALL_PARTITIONS`.

Each parameter says whether a flag of `fractal-wallpapers render` sets it or only a
spec JSON does (`fractal-engine render <spec.json>`, FORMATS.md's *The render spec*).
"""

from __future__ import annotations

import argparse

#: Schema of `parameters.json`.
SCHEMA = 1

#: Every family the engine renders, keyed by the spec's `family.kind`: what else it
#: takes, its degree where it has one, and whether `render --family` names it.
FAMILIES: dict[str, dict] = {
    "mandelbrot": {"flag": True, "degree": "2, fixed", "takes": []},
    "multibrot": {"flag": True, "degree": "an integer, 3 to 6", "takes": ["degree"]},
    "julia": {
        "flag": True,
        "degree": "an integer, 2 to 6",
        "takes": ["degree", "c (required)"],
    },
    "phoenix": {
        "flag": True,
        "degree": "2, fixed",
        "takes": ["c (default 0.5667 0)", "p (default -0.5 0)", "z_prev (default 0 0)"],
    },
    "phoenix_m": {
        "flag": False,
        "degree": "2, fixed",
        "takes": ["p"],
        "note": "the Phoenix parameter plane: the pixel is c",
    },
    "fractional_multibrot": {
        "flag": False,
        "degree": "a decimal string in [1.8, 5.0]",
        "takes": ["degree"],
        "note": "render only, with no home view: center_re, center_im and width are required",
    },
}

#: Spec keys no flag of `render` reaches, beside the two families above.
SPEC_ONLY = {
    "curve": "linear, sqrt, log or scurve: an explicit coloring's `transform`",
    "coloring": "a full coloring object in place of a named mode",
    "colormap_dir": "where the colormap files are (default data/palettes)",
    "allow_unresolvable_in_f64": "allow a frame too deep for f64 to resolve (default false)",
}

#: The numeric frame parameters, by the flag's `dest`: the range the engine holds
#: each to (`spec.rs`'s checks), and what an unsaid one means.
FRAME = {
    "center_re": {"range": "a decimal string", "unsaid": "the family's home view"},
    "center_im": {"range": "a decimal string", "unsaid": "the family's home view"},
    "width": {"range": "a decimal string, > 0", "unsaid": "the family's home width"},
    "resolution": {"range": "two integers, each > 0", "unsaid": None},
    "supersample": {"range": "an integer, >= 1", "unsaid": None},
    "maxiter": {
        "range": "an integer, >= 1 (an explorer link holds it to 50-2,000,000)",
        "unsaid": "the depth policy's cap for the view's width",
    },
}


def render_parser() -> argparse.ArgumentParser:
    """`fractal-wallpapers render`'s own parser, as the command line builds it."""
    from fractal_wallpapers import cli

    parser = cli.build_parser()
    for action in parser._subparsers._group_actions:  # noqa: SLF001
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            return action.choices["render"]
    raise LookupError("the command line has no `render`")


def flags() -> list[dict]:
    """Every flag of `render`: its group, spelling, default, choices and help."""
    parser = render_parser()
    out = []
    for group in parser._action_groups:  # noqa: SLF001
        for action in group._group_actions:  # noqa: SLF001
            if not action.option_strings or action.dest in ("help",):
                continue
            out.append(
                {
                    "flag": max(action.option_strings, key=len),
                    "dest": action.dest,
                    "group": group.title,
                    "default": action.default,
                    "choices": list(action.choices) if action.choices else None,
                    "help": action.help,
                }
            )
    return out


def describe() -> dict:
    """The whole document `parameters.json` holds."""
    from fractal_wallpapers import engine
    from fractal_wallpapers.cli.common import DEFAULT_MODE, PALETTE_KNOBS
    from fractal_wallpapers.palettes import drawable
    from fractal_wallpapers.supply.partitions import ALL_PARTITIONS

    flagged = {item["dest"]: item for item in flags()}
    family_flag = flagged["family"]["choices"] or []
    families = {kind: {**block, "flag": kind in family_flag} for kind, block in FAMILIES.items()}
    frame = {
        dest: {
            "flag": flagged[dest]["flag"] if dest in flagged else None,
            "default": flagged[dest]["default"] if dest in flagged else None,
            **rule,
        }
        for dest, rule in FRAME.items()
    }
    palette = {
        key: {
            "flag": knob["flag"] if knob.get("dest", key) in flagged else None,
            "default": knob["default"],
            "range": knob["range"],
            "says": knob["says"],
        }
        for key, knob in PALETTE_KNOBS.items()
    }
    modes = [
        {
            "name": mode["name"],
            "tier": mode["tier"],
            "production": mode["tier"] == engine.PRODUCTION,
            "identity": mode["identity"],
            "params": mode.get("params") or {},
        }
        for mode in engine.modes()
    ]
    return {
        "schema": SCHEMA,
        "settable_by": {
            "flag": "fractal-wallpapers render --<flag>; a mode parameter is --param NAME=VALUE",
            "spec": "only through a spec JSON: fractal-engine render <spec.json>, whose keys "
            "are FORMATS.md's *The render spec*",
        },
        "families": families,
        "walked_families": list(ALL_PARTITIONS),
        "frame": frame,
        "modes": modes,
        "default_mode": DEFAULT_MODE,
        "palette": palette,
        "colormaps": [{"name": name, "kind": kind} for name, kind in drawable().items()],
        "spec_only": SPEC_ONLY,
        "flags": list(flagged.values()),
    }
