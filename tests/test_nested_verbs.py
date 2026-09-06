"""Every `curate` group whose second word is a verb, and what that verb parses to.

Two guards over one subject, and they are not the same guard.

[`LINES`] is the PIN. One representative invocation per nested verb, with the
namespace keys that verb's handler actually reads, and it was written against the
parser as it stood when every group spelled its verb as a positional `choices=`
argument inside one parser. It passed then and it passes now that each verb is a
real subparser, which is the whole claim: the split moved where argparse enforces
the verb and changed no typed line's meaning.

Only the keys the handler reads, because the rest of the namespace is exactly
what the split was for. Before it, `curate candidate-ledger prune` carried
`--recolour`, `--apply`, `--out` and eight more that `prune` has never looked at;
after it, it carries `--keep` and `--dry-run`. Comparing whole namespaces would
be comparing the defect to the fix.

[`SURFACE`] is the other direction: which flags each verb reaches at all. It is
what stops a flag added to `curate solve run` from quietly becoming a flag
`curate solve record` accepts — a record that took a flag it does not read would
not be reproducible from the `run` it claims to be, and the failure would be
silent. `curate_commands.RUN_ONLY_SOLVE_FLAGS` was a runtime check for exactly
that on one group; the parser enforces it on all eighteen now, and this says so.
"""

from __future__ import annotations

import argparse
import shlex

import pytest

from fractal_wallpapers import cli

#: One representative invocation per nested verb, in registration order, with the
#: handler it resolves to and the namespace keys that verb's handler reads. A line
#: names every flag its verb reads wherever it can, so the expected value is what
#: was typed rather than a constant this test would then be pinning; the two bare
#: lines that do carry a default — `curate flatness` and `curate signatures`, whose
#: verb is optional — have it pinned to its own module in `tests/test_cli.py`.
LINES: tuple[tuple[str, str, dict], ...] = (
    # The five durable stores, one shape each: save it, check it, restore it.
    ("curate sidecar check", "curate_sidecar", {"what": "check"}),
    ("curate sidecar save", "curate_sidecar", {"what": "save"}),
    ("curate sidecar restore --force", "curate_sidecar", {"what": "restore", "force": True}),
    ("curate amendments check", "curate_amendments", {"what": "check"}),
    ("curate amendments save", "curate_amendments", {"what": "save"}),
    ("curate amendments restore --force", "curate_amendments", {"what": "restore", "force": True}),
    ("curate frames check", "curate_frames", {"what": "check"}),
    ("curate frames save", "curate_frames", {"what": "save"}),
    ("curate frames restore --force", "curate_frames", {"what": "restore", "force": True}),
    ("curate mass-sweep check", "curate_mass_sweep", {"what": "check"}),
    ("curate mass-sweep save", "curate_mass_sweep", {"what": "save"}),
    ("curate mass-sweep restore --force", "curate_mass_sweep", {"what": "restore", "force": True}),
    # The one durable store with a fifth verb: it is the only one this project can
    # add to. `extend` renders the panel for the maps the colour-mass map holds no
    # row for and appends them, which is what a colormap drop needs.
    (
        "curate mass-sweep extend --modes smooth --maps meloni --workers 2 --budget 60 "
        "--workdir w --dry-run --partial",
        "curate_mass_sweep_extend",
        {
            "what": "extend",
            "modes": ["smooth"],
            "maps": ["meloni"],
            "workers": 2,
            "budget": 60.0,
            "workdir": "w",
            "dry_run": True,
            "partial": True,
        },
    ),
    ("curate embeddings check", "curate_embeddings", {"what": "check"}),
    ("curate embeddings save", "curate_embeddings", {"what": "save"}),
    ("curate embeddings restore --force", "curate_embeddings", {"what": "restore", "force": True}),
    # The spiral store builds as well as keeping itself, so it has a fourth verb.
    (
        "curate spiral-scores build --limit 40",
        "curate_spiral_scores",
        {"what": "build", "limit": 40},
    ),
    ("curate spiral-scores check", "curate_spiral_scores", {"what": "check"}),
    ("curate spiral-scores save", "curate_spiral_scores", {"what": "save"}),
    (
        "curate spiral-scores restore --force",
        "curate_spiral_scores",
        {"what": "restore", "force": True},
    ),
    # A gallery pass's store is named by --pass on all three of its verbs.
    (
        "curate gallery-store check --pass p9",
        "curate_gallery_store",
        {"what": "check", "pass_id": "p9"},
    ),
    (
        "curate gallery-store save --pass p9",
        "curate_gallery_store",
        {"what": "save", "pass_id": "p9"},
    ),
    (
        "curate gallery-store restore --pass p9 --force",
        "curate_gallery_store",
        {"what": "restore", "pass_id": "p9", "force": True},
    ),
    # The candidate ledger: ten verbs, and the group that carried the most flags
    # none of its verbs shared.
    (
        "curate candidate-ledger backfill --recolour",
        "curate_candidate_ledger",
        {"what": "backfill", "recolour": True},
    ),
    (
        "curate candidate-ledger census --n 150 --out scratch/census.json",
        "curate_candidate_ledger",
        {"what": "census", "n": 150, "out": "scratch/census.json"},
    ),
    ("curate candidate-ledger check", "curate_candidate_ledger", {"what": "check"}),
    (
        "curate candidate-ledger orphans --apply --leg d7 --include-unmerged",
        "curate_candidate_ledger",
        {"what": "orphans", "apply": True, "leg": ["d7"], "include_unmerged": True},
    ),
    ("curate candidate-ledger pictures", "curate_candidate_ledger", {"what": "pictures"}),
    (
        "curate candidate-ledger prune --keep 12 --dry-run",
        "curate_candidate_ledger",
        {"what": "prune", "keep": 12, "dry_run": True},
    ),
    (
        "curate candidate-ledger re-render --limit 500 --workers 3",
        "curate_candidate_ledger",
        {"what": "re-render", "limit": 500, "workers": 3},
    ),
    ("curate candidate-ledger save", "curate_candidate_ledger", {"what": "save"}),
    (
        "curate candidate-ledger score --limit 500",
        "curate_candidate_ledger",
        {"what": "score", "limit": 500},
    ),
    (
        "curate candidate-ledger restore --force",
        "curate_candidate_ledger",
        {"what": "restore", "force": True},
    ),
    # The gallery leg. `run` names all twenty-six of its own flags here, because a
    # flag this line does not name is a default this test would be pinning.
    (
        "curate solve run --n 150 --key p_ge4 --group-cap identity --themed dark_vivid_lime "
        "--themed-cap 4 --themed-radius 0.3 --target dark_vivid_lime=1.0 --mode-floor 3 "
        "--locations 900 --rows-per-seat 5 --draw-seed 11 --allow-unranked --spiral-cap 0.25 "
        "--neutral-radius 0.2 --no-preselection --no-diversity --no-swap --swap-seconds 60 "
        "--explain-seats-of n150 --no-render --release-regime 1920x1080ss2 --workers 3 "
        "--no-sheet --sheet-out scratch/sheet.jpg --name n150",
        "curate_solve",
        {
            "what": "run",
            "n": 150,
            "key": "p_ge4",
            "group_cap": "identity",
            "themed": "dark_vivid_lime",
            "themed_cap": 4,
            "themed_radius": 0.3,
            "target": ["dark_vivid_lime=1.0"],
            "mode_floor": 3,
            "flat_floor": False,
            "locations": 900,
            "rows_per_seat": 5,
            "draw_seed": 11,
            "allow_unranked": True,
            "spiral_cap": 0.25,
            "neutral_radius": 0.2,
            "no_preselection": True,
            "no_diversity": True,
            "no_swap": True,
            "swap_seconds": 60.0,
            "explain_seats_of": "n150",
            "no_render": True,
            "release_regime": "1920x1080ss2",
            "workers": 3,
            "no_sheet": True,
            "sheet_out": "scratch/sheet.jpg",
            "name": "n150",
        },
    ),
    (
        "curate solve run --flat-floor",
        "curate_solve",
        {"what": "run", "flat_floor": True, "n": None},
    ),
    (
        "curate solve record --n 1000 --solve-name tentative_n1000 --key rank-key --no-swap "
        "--swap-seconds 900 --spiral-cap 0.25",
        "curate_solve",
        {
            "what": "record",
            "n": 1000,
            "solve_name": "tentative_n1000",
            "key": "rank-key",
            "no_swap": True,
            "swap_seconds": 900.0,
            "spiral_cap": 0.25,
            "themed": None,
        },
    ),
    (
        "curate solve record --n 200 --themed dark_vivid_green --themed-cap 4 --themed-radius 0.3",
        "curate_solve",
        {
            "what": "record",
            "n": 200,
            "themed": "dark_vivid_green",
            "themed_cap": 4,
            "themed_radius": 0.3,
        },
    ),
    # `--k` repeats, because the rungs of a counterfactual are a list and the
    # shipped one is meant to be named among them as the control.
    (
        "curate solve k-sweep --k 2 --k 2.5 --n 200 --control 20260901T000000Z",
        "curate_solve",
        {"what": "k-sweep", "k": [2.0, 2.5], "n": 200, "control": "20260901T000000Z"},
    ),
    # Both spellings of the stamp, because a reader who has just seen one printed
    # will type it either way and the cost of losing one is a page written for a
    # different record.
    (
        "curate solve browse 20260901T000000Z",
        "curate_solve",
        {"what": "browse", "id": ["20260901T000000Z"], "stamp": None},
    ),
    (
        "curate solve browse --stamp 20260901T000000Z",
        "curate_solve",
        {"what": "browse", "id": [], "stamp": "20260901T000000Z"},
    ),
    (
        "curate solve resolve k0,not-an-id",
        "curate_solve",
        {"what": "resolve", "id": ["k0,not-an-id"], "stamp": None},
    ),
    ("curate solve list", "curate_solve", {"what": "list"}),
    (
        "curate votes build 20260101T000000Z --out kit --limit 40 --quality 92 --chroma 444 --ss 4",
        "curate_votes",
        {
            "what": "build",
            "stamp": "20260101T000000Z",
            "out": "kit",
            "limit": 40,
            "quality": 92,
            "chroma": "444",
            "ss": 4,
        },
    ),
    # The stamp is optional and means the newest published record, which is the
    # spelling a reader who has just recorded one will type.
    (
        "curate votes build --out kit",
        "curate_votes",
        {"what": "build", "stamp": None, "out": "kit", "limit": None},
    ),
    (
        "curate growth run --name g1 --fraction 8 --n 150 --seed 7 --swap-seconds 60",
        "curate_growth",
        {
            "what": "run",
            "name": "g1",
            "fraction": [8],
            "n": [150],
            "seed": [7],
            "swap_seconds": 60.0,
        },
    ),
    (
        "curate growth plot 20260901T000000Z",
        "curate_growth",
        {"what": "plot", "stamp": "20260901T000000Z"},
    ),
    # `plot` with no stamp prints the stamps this machine holds, so the positional
    # stays optional at the verb.
    ("curate growth plot", "curate_growth", {"what": "plot", "stamp": None}),
    # The three groups whose verb is optional, and whose default verb is the one
    # that does the work. The bare line is the one that has to keep resolving.
    (
        "curate flatness",
        "curate_flatness",
        {"what": "sweep", "workers": 3, "all": False, "recompute": False},
    ),
    (
        "curate flatness sweep --workers 2 --all --recompute",
        "curate_flatness",
        {"what": "sweep", "workers": 2, "all": True, "recompute": True},
    ),
    ("curate flatness coverage --all", "curate_flatness", {"what": "coverage", "all": True}),
    ("curate flatness save", "curate_flatness", {"what": "save"}),
    ("curate flatness check", "curate_flatness", {"what": "check"}),
    ("curate flatness restore --force", "curate_flatness", {"what": "restore", "force": True}),
    (
        "curate signatures",
        "curate_signatures",
        {"what": "sweep", "workers": 3, "recompute": False},
    ),
    (
        "curate signatures sweep --workers 2 --recompute",
        "curate_signatures",
        {"what": "sweep", "workers": 2, "recompute": True},
    ),
    ("curate signatures coverage", "curate_signatures", {"what": "coverage"}),
    ("curate signatures save", "curate_signatures", {"what": "save"}),
    ("curate signatures check", "curate_signatures", {"what": "check"}),
    ("curate signatures restore --force", "curate_signatures", {"what": "restore", "force": True}),
    ("curate rank-key", "curate_rank_key", {"what": "fit"}),
    ("curate rank-key fit", "curate_rank_key", {"what": "fit"}),
    ("curate rank-key show", "curate_rank_key", {"what": "show"}),
    # The three legs that drive the engine. Each names its leg on every verb,
    # including the ones that do not read it: --name was required group-wide
    # before the split and dropping it from a verb would break a line that works.
    (
        "curate hunt plan --name h1 --unconditional 400 --conditioned 200 --cell "
        "dark_vivid_lime --work-order julia:mandelbrot=19 --per-location 4 --seed 5 "
        "--rebuild-frames",
        "curate_hunt",
        {
            "what": "plan",
            "name": "h1",
            "unconditional": 400,
            "conditioned": 200,
            "cell": "dark_vivid_lime",
            "work_order": ["julia:mandelbrot=19"],
            "per_location": 4,
            "seed": 5,
            "rebuild_frames": True,
        },
    ),
    (
        "curate hunt run --name h1 --budget 1200 --unconditional 400 --conditioned 200 "
        "--cell dark_vivid_lime --work-order julia:mandelbrot=19 --per-location 4 --seed 5 "
        "--rebuild-frames --device cpu",
        "curate_hunt",
        {
            "what": "run",
            "name": "h1",
            "budget": 1200.0,
            "unconditional": 400,
            "conditioned": 200,
            "cell": "dark_vivid_lime",
            "work_order": ["julia:mandelbrot=19"],
            "per_location": 4,
            "seed": 5,
            "rebuild_frames": True,
            "device": "cpu",
        },
    ),
    ("curate hunt merge --name h1", "curate_hunt", {"what": "merge", "name": "h1"}),
    ("curate hunt sheet --name h1", "curate_hunt", {"what": "sheet", "name": "h1"}),
    ("curate hunt frames --name h1", "curate_hunt", {"what": "frames", "name": "h1"}),
    (
        "curate mine plan --name m1 --budget 7200 --rate 0.35 --k 12 --per-location 3 --seed 5",
        "curate_mine",
        {
            "what": "plan",
            "name": "m1",
            "budget": 7200.0,
            "rate": 0.35,
            "k": 12,
            "per_location": 3,
            "seed": 5,
        },
    ),
    (
        "curate mine run --name m1 --budget 7200 --rate 0.35 --k 12 --per-location 3 "
        "--seed 5 --device cpu",
        "curate_mine",
        {
            "what": "run",
            "name": "m1",
            "budget": 7200.0,
            "rate": 0.35,
            "k": 12,
            "per_location": 3,
            "seed": 5,
            "device": "cpu",
        },
    ),
    ("curate mine merge --name m1", "curate_mine", {"what": "merge", "name": "m1"}),
    (
        "curate mine bench --name m1 --seed 5",
        "curate_mine",
        {"what": "bench", "name": "m1", "seed": 5},
    ),
    ("curate mine sheet --name m1", "curate_mine", {"what": "sheet", "name": "m1"}),
    (
        "curate depth plan --name d1 --budget 5400 --rate 0.35 --workers 3 --seed 5 "
        "--shares {} --band-weights {} --partition-weights {} --bands 4 --top-bands 2 "
        "--centered exclude --width 40 --near-width 20 --floor-width 8 --modes field "
        "--cell dark_vivid_lime --breadth-demoted 0.5 --floor-modes phoenix "
        "--floor-untried phoenix --floor-places places.txt --near-places places.txt "
        "--floor-seats 4 --draw-maps maps.txt --draw-cells 6 --draw-cutoff 0.2",
        "curate_depth",
        {
            "what": "plan",
            "name": "d1",
            "budget": 5400.0,
            "rate": 0.35,
            "workers": 3,
            "seed": 5,
            "shares": "{}",
            "band_weights": "{}",
            "partition_weights": "{}",
            "bands": 4,
            "top_bands": 2,
            "centered": "exclude",
            "width": 40,
            "near_width": 20,
            "floor_width": 8,
            "modes": ["field"],
            "cell": ["dark_vivid_lime"],
            "breadth_demoted": ["0.5"],
            "floor_modes": ["phoenix"],
            "floor_untried": ["phoenix"],
            "floor_places": "places.txt",
            "near_places": "places.txt",
            "floor_seats": 4,
            "draw_maps": "maps.txt",
            "draw_cells": ["6"],
            "draw_cutoff": 0.2,
        },
    ),
    (
        "curate depth run --name d1 --budget 5400 --rate 0.35 --workers 3 --seed 5 "
        "--shares {} --band-weights {} --partition-weights {} --bands 4 --top-bands 2 "
        "--centered exclude --width 40 --near-width 20 --floor-width 8 --modes field "
        "--cell dark_vivid_lime --breadth-demoted 0.5 --floor-modes phoenix "
        "--floor-untried phoenix --floor-places places.txt --near-places places.txt "
        "--floor-seats 4 --draw-maps maps.txt --draw-cells 6 --draw-cutoff 0.2 --device cpu",
        "curate_depth",
        {
            "what": "run",
            "name": "d1",
            "budget": 5400.0,
            "rate": 0.35,
            "workers": 3,
            "seed": 5,
            "shares": "{}",
            "band_weights": "{}",
            "partition_weights": "{}",
            "bands": 4,
            "top_bands": 2,
            "centered": "exclude",
            "width": 40,
            "near_width": 20,
            "floor_width": 8,
            "modes": ["field"],
            "cell": ["dark_vivid_lime"],
            "breadth_demoted": ["0.5"],
            "floor_modes": ["phoenix"],
            "floor_untried": ["phoenix"],
            "floor_places": "places.txt",
            "near_places": "places.txt",
            "floor_seats": 4,
            "draw_maps": "maps.txt",
            "draw_cells": ["6"],
            "draw_cutoff": 0.2,
            "device": "cpu",
        },
    ),
    ("curate depth merge --name d1", "curate_depth", {"what": "merge", "name": "d1"}),
    ("curate depth sheet --name d1", "curate_depth", {"what": "sheet", "name": "d1"}),
    # The re-mode leg. `plan` and `run` name the mode pair; the other two do not,
    # so a merge cannot be told a mode its own rows disagree with.
    (
        "curate remode plan --name r1 --from-mode exp_smoothing --to-mode smooth",
        "curate_remode",
        {"what": "plan", "name": "r1", "from_mode": "exp_smoothing", "to_mode": "smooth"},
    ),
    (
        "curate remode run --name r1 --from-mode exp_smoothing --to-mode smooth "
        "--budget 1800 --workers 3 --device cuda",
        "curate_remode",
        {
            "what": "run",
            "name": "r1",
            "from_mode": "exp_smoothing",
            "to_mode": "smooth",
            "budget": 1800.0,
            "workers": 3,
            "device": "cuda",
        },
    ),
    ("curate remode merge --name r1", "curate_remode", {"what": "merge", "name": "r1"}),
    ("curate remode read --name r1", "curate_remode", {"what": "read", "name": "r1"}),
)

#: Every nested group, its verbs in registration order, and the flags each verb
#: reaches. The order is the `--help` surface and the flag list is the promise:
#: a flag here is one that verb's handler reads, and a flag missing from a verb
#: is refused at the verb rather than accepted and dropped on the floor.
SURFACE: dict[str, dict[str, tuple[str, ...]]] = {
    "sidecar": {"check": (), "save": (), "restore": ("--force",)},
    "amendments": {"check": (), "save": (), "restore": ("--force",)},
    "frames": {"check": (), "save": (), "restore": ("--force",)},
    "mass-sweep": {
        "check": (),
        "save": (),
        "restore": ("--force",),
        "extend": (
            "--modes",
            "--maps",
            "--workers",
            "--budget",
            "--workdir",
            "--dry-run",
            "--partial",
        ),
    },
    "embeddings": {"check": (), "save": (), "restore": ("--force",)},
    "spiral-scores": {
        "build": ("--limit",),
        "check": (),
        "save": (),
        "restore": ("--force",),
    },
    "gallery-store": {
        "check": ("--pass",),
        "save": ("--pass",),
        "restore": ("--pass", "--force"),
    },
    "candidate-ledger": {
        "backfill": ("--recolour",),
        "census": ("--n", "--out"),
        "check": (),
        "orphans": ("--apply", "--leg", "--include-unmerged"),
        "pictures": (),
        "prune": ("--keep", "--dry-run"),
        "re-render": ("--workers", "--limit"),
        "save": (),
        "score": ("--limit",),
        "restore": ("--force",),
    },
    "solve": {
        "run": (
            "--name",
            "--n",
            "--locations",
            "--rows-per-seat",
            "--draw-seed",
            "--allow-unranked",
            "--target",
            "--mode-floor",
            "--flat-floor",
            "--group-cap",
            "--spiral-cap",
            "--mode-ceiling",
            "--themed",
            "--themed-cap",
            "--themed-radius",
            "--neutral-radius",
            "--no-preselection",
            "--no-diversity",
            "--key",
            "--no-swap",
            "--swap-seconds",
            "--augment",
            "--augment-depth",
            "--augment-seconds",
            "--explain-seats-of",
            "--no-render",
            "--release-regime",
            "--workers",
            "--no-sheet",
            "--sheet-out",
        ),
        "record": (
            "--solve-name",
            "--n",
            "--spiral-cap",
            "--mode-ceiling",
            "--key",
            "--no-swap",
            "--swap-seconds",
            "--augment",
            "--augment-depth",
            "--augment-seconds",
            "--themed",
            "--themed-cap",
            "--themed-radius",
        ),
        "k-sweep": ("--k", "--n", "--control"),
        "browse": ("--stamp",),
        "resolve": ("--stamp",),
        "list": (),
    },
    "votes": {"build": ("--out", "--limit", "--quality", "--chroma", "--ss", "--ss-for")},
    "growth": {
        "run": ("--name", "--fraction", "--n", "--seed", "--swap-seconds"),
        "plot": (),
    },
    "flatness": {
        "sweep": ("--workers", "--all", "--recompute"),
        "coverage": ("--all",),
        "save": (),
        "check": (),
        "restore": ("--force",),
    },
    "signatures": {
        "sweep": ("--workers", "--recompute"),
        "coverage": (),
        "save": (),
        "check": (),
        "restore": ("--force",),
    },
    "rank-key": {"fit": (), "show": ()},
    "hunt": {
        "plan": (
            "--name",
            "--unconditional",
            "--conditioned",
            "--cell",
            "--work-order",
            "--per-location",
            "--seed",
            "--rebuild-frames",
        ),
        "run": (
            "--name",
            "--budget",
            "--unconditional",
            "--conditioned",
            "--cell",
            "--work-order",
            "--per-location",
            "--seed",
            "--rebuild-frames",
            "--device",
        ),
        "merge": ("--name",),
        "sheet": ("--name",),
        "frames": ("--name",),
    },
    "mine": {
        "plan": ("--name", "--budget", "--rate", "--k", "--per-location", "--seed"),
        "run": ("--name", "--budget", "--rate", "--k", "--per-location", "--seed", "--device"),
        "merge": ("--name",),
        "bench": ("--name", "--seed"),
        "sheet": ("--name",),
    },
    "depth": {
        "plan": (
            "--name",
            "--budget",
            "--rate",
            "--workers",
            "--seed",
            "--shares",
            "--band-weights",
            "--partition-weights",
            "--bands",
            "--top-bands",
            "--centered",
            "--width",
            "--near-width",
            "--floor-width",
            "--modes",
            "--cell",
            "--breadth-demoted",
            "--floor-modes",
            "--floor-untried",
            "--floor-places",
            "--near-places",
            "--floor-seats",
            "--draw-maps",
            "--draw-cells",
            "--draw-cutoff",
        ),
        # `--device` sits inside "the leg and its clock" rather than at the end,
        # which is where it printed before the split too: `device_flag` was
        # called on that group and never on the parser.
        "run": (
            "--name",
            "--budget",
            "--rate",
            "--workers",
            "--device",
            "--seed",
            "--shares",
            "--band-weights",
            "--partition-weights",
            "--bands",
            "--top-bands",
            "--centered",
            "--width",
            "--near-width",
            "--floor-width",
            "--modes",
            "--cell",
            "--breadth-demoted",
            "--floor-modes",
            "--floor-untried",
            "--floor-places",
            "--near-places",
            "--floor-seats",
            "--draw-maps",
            "--draw-cells",
            "--draw-cutoff",
        ),
        "merge": ("--name",),
        "sheet": ("--name",),
    },
    # The mode pair is on `plan` and `run` and on neither of the other two: a
    # merge reads the rows the run already wrote and a read reads its record, so
    # a mode named there would be a flag that could disagree with the leg.
    "remode": {
        "plan": ("--name", "--from-mode", "--to-mode"),
        "run": ("--name", "--from-mode", "--to-mode", "--budget", "--workers", "--device"),
        "merge": ("--name",),
        "read": ("--name",),
    },
}


def nested_groups(parser):
    """Every `curate` step that spells a second verb, as (name, its subparsers)."""
    steps = curate_steps(parser)
    found = {}
    for name, child in steps.choices.items():
        verbs = [
            action for action in child._actions if isinstance(action, argparse._SubParsersAction)
        ]
        if verbs:
            found[name] = verbs[0]
    return found


def curate_steps(parser):
    """The `curate` group's own subparsers action."""
    top = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    curating = top.choices["curate"]
    return next(a for a in curating._actions if isinstance(a, argparse._SubParsersAction))


@pytest.fixture(scope="module")
def parser():
    """One parser for the whole pinned set below.

    `build_parser` imports nineteen modules and assembles every subparser, which
    is **34.8 ms** on this machine — measured in-process, a hundred builds after
    a warm one. The guard below is seventy-nine cases and built one apiece, so the
    pin cost 2.5 s to answer a question about spelling.

    Shared rather than rebuilt because `parse_args` does not touch the parser: it
    walks the actions and fills a fresh `Namespace`. Any guard here that wants a
    parser it can mutate, or one built after a patch, calls `build_parser` itself
    — and three below do.
    """
    return cli.build_parser()


@pytest.mark.parametrize("line,handler,expected", LINES, ids=[line for line, _, _ in LINES])
def test_a_nested_verb_resolves_to_the_namespace_it_always_did(line, handler, expected, parser):
    """The pin. Written against the parser that spelled every second verb as a
    positional inside one parser, and unchanged since: same spelling, same flags,
    same values, same handler."""
    parsed = parser.parse_args(shlex.split(line))

    assert parsed.handler is getattr(cli, handler), f"`{line}` resolved to another handler"
    held = vars(parsed)
    missing = sorted(key for key in expected if key not in held)
    assert not missing, f"`{line}` no longer carries {missing}"
    assert {key: held[key] for key in expected} == expected


def test_every_nested_verb_is_a_real_subparser() -> None:
    """Eighteen groups and seventy-two verbs, and no group left spelling its verb as
    a positional `choices=` argument. The two are not interchangeable: a positional
    takes the whole group's flags, so `--help` at the group is every verb's flags at
    once and a flag on the wrong verb is accepted and silently ignored."""
    groups = nested_groups(cli.build_parser())

    assert set(groups) == set(SURFACE), (
        f"nested groups the surface table does not name: {sorted(set(groups) - set(SURFACE))}; "
        f"named but not nested: {sorted(set(SURFACE) - set(groups))}"
    )
    assert sum(len(verbs) for verbs in SURFACE.values()) == 72
    for name, action in groups.items():
        assert list(action.choices) == list(SURFACE[name]), (
            f"`curate {name}` registers its verbs in another order, and the order is the "
            f"`--help` surface"
        )
        assert action.dest == "what", (
            f"`curate {name}` names its verb something other than `what`, which is what its "
            f"handler dispatches on"
        )


def test_a_themed_record_and_a_themed_run_ask_for_the_same_two_demands() -> None:
    """`--themed` sets a cell target and a flat floor, and `record` has neither
    flag to set them with — so the two verbs reach them through one helper or they
    reach two different galleries. A record's whole claim is that it is a `run`
    taken once and kept, and a themed record that floored differently would be a
    stamp nobody could reproduce from the command it names."""
    from fractal_wallpapers.cli import curate_commands
    from fractal_wallpapers.curation import ceiling, solve

    targets, floor = curate_commands.themed_demands("dark_vivid_green", 200)
    assert targets == {"dark_vivid_green": 1.0}
    assert floor == solve.mode_floor(200)

    # The target is what keeps the cell allowance off the theme: at t=1.0 the
    # allowance is 2n + 1, and at the cell default of 1/48 it refuses at nine.
    rule = ceiling.Rule(targets=targets)
    assert rule.allowed("dark_vivid_green", 200) == 401 > 200
    assert ceiling.Rule().allowed("dark_vivid_green", 200) == 9


def test_a_themed_record_reaches_the_same_three_flags_the_run_carries() -> None:
    """One helper builds them, so `--help` cannot describe one flag two ways."""
    groups = nested_groups(cli.build_parser())
    verbs = groups["solve"].choices
    themed = ("--themed", "--themed-cap", "--themed-radius")
    for verb in ("run", "record"):
        held = {
            option.option_strings[0]: option
            for group in verbs[verb]._action_groups
            for option in group._group_actions
            if option.option_strings
        }
        assert set(themed) <= set(held), f"curate solve {verb} is missing {themed}"
    for name in themed:
        run_flag = next(
            option
            for group in verbs["run"]._action_groups
            for option in group._group_actions
            if option.option_strings and option.option_strings[0] == name
        )
        record_flag = next(
            option
            for group in verbs["record"]._action_groups
            for option in group._group_actions
            if option.option_strings and option.option_strings[0] == name
        )
        assert run_flag.help == record_flag.help, f"{name} is described two ways"
        assert run_flag.default == record_flag.default, f"{name} defaults two ways"


def test_a_nested_verb_carries_only_the_flags_its_handler_reads() -> None:
    """A flag added to `curate solve run` must not quietly become a flag `curate
    solve record` accepts: a record is a `run` with nothing changed, so a record
    handed a flag it does not read would not be reproducible from the run it claims
    to be, and the failure would be silent — the flag dropped on the floor and the
    stamp written anyway. `curate_commands.RUN_ONLY_SOLVE_FLAGS` was a runtime
    check for that on one group. The parser enforces it on all eighteen now."""
    groups = nested_groups(cli.build_parser())

    wrong = {}
    for name, action in groups.items():
        for verb, child in action.choices.items():
            # Read in the order argparse PRINTS them — group by group — rather
            # than the order they were registered in. The two differ on a
            # command whose help is grouped, and it is the printed one the table
            # is a claim about.
            held = tuple(
                option.option_strings[0]
                for group in child._action_groups
                for option in group._group_actions
                if option.option_strings and option.option_strings[0] != "-h"
            )
            if held != SURFACE[name][verb]:
                wrong[f"curate {name} {verb}"] = {"parser": held, "table": SURFACE[name][verb]}
    assert not wrong, f"the flags a verb reaches are not the ones the table promises: {wrong}"


def test_a_flag_the_verb_does_not_read_is_refused_at_the_verb() -> None:
    """The point of the split, stated as the four spellings that used to parse and
    now do not. Each was accepted by the group, ignored by the handler, and left no
    trace: `curate sidecar check --force` restored nothing, `curate depth plan
    --device cpu` planned on no device, `curate solve list k0` listed everything."""
    parse = cli.build_parser().parse_args

    for line in (
        "curate sidecar check --force",
        "curate depth plan --name d1 --rate 0.35 --device cpu",
        "curate solve list k0",
        "curate candidate-ledger prune --recolour",
    ):
        with pytest.raises(SystemExit):
            parse(shlex.split(line))
