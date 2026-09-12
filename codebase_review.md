# Codebase review

Written 2026-09-12, off a session that did housekeeping in `src/fractal_wallpapers/README.md`
and `models/`, then drove five themed galleries end to end through `curate solve record`,
`solve.render_seats` and the tentative store. Everything below is either something that
cost that session time or something the measurements turned up on the way. Nothing here
is a correctness complaint — the tree is green and the conventions hold. It is all about
**how much you have to read to do a small thing**.

The numbers first, because they set the scale.

| | |
|---|---|
| tracked Python | 388 files, 198,352 lines (`src/` 133,954) |
| prose inside `src/` | 32,556 docstring lines (24%) + 10,397 comment lines (8%) = **32%** |
| tracked markdown | 46 files, 26,784 lines (after this session's CLAUDE.md trim) |
| `curation/` alone | 64 modules and **12,297 lines of markdown** across four files |
| largest module | `cli/curate_commands.py`, **6,354 lines** |
| largest doc | `curation/GALLERY.md`, **4,200 lines** |

---

## 1. `cli/curate_commands.py` is the single worst file in the tree

6,354 lines, ~50 subcommands, and **28% of it (84,561 chars across 395 strings) is
argparse `help=` prose**. The `_commands` suffix rule and the one-module-per-command-group
rule are both good and neither is in question — but `curate` is not a command group, it is
nine of them wearing one hat: the ledger, the solve, votes, growth, headroom, colours,
mining, labelling migration, and the durability record/check/restore trio.

**Proposal.** Split by the noun, keeping the suffix convention exactly:
`curate_solve_commands.py`, `curate_ledger_commands.py`, `curate_votes_commands.py`,
`curate_mine_commands.py`, `curate_colors_commands.py`, and leave the long tail in
`curate_commands.py`. `cli/__init__.py` gains five names in the list it already is.

This is mechanical, has no runtime effect, and it is the change that most improves the
odds of finding the right flag — which matters because of §2.

## 2. Command help is the only documentation for the flags, and it is unskimmable

Finding that `--no-render` is on `curate solve run` and **not** on `curate solve record`
took four `--help` invocations this session, because each one prints several screens.
`curate solve record --help` spends ~40 lines on `--themed`, `--themed-cap` and
`--themed-radius` alone, each carrying its full ruling history.

The prose is *good* — it is genuinely the best explanation of those flags anywhere. It is
in the wrong channel. A person reaching for `--help` wants the one-line contract.

**Proposal.** Two tiers. `help=` gets one sentence: what it does, what the default is.
The ruling, the measurement and the date move to the module docstring or to `GALLERY.md`,
where the `[`module.symbol`]` citation convention already points. Add `--help-verbose`, or
simply let `argparse`'s `epilog` carry a pointer to the heading. Rough saving:
**~60,000 characters out of the CLI layer**, and a `--help` that fits a screen.

## 3. One key, two shapes: `theme` in the solve record

This cost the most time of anything this session and it is a real trap, not a preference:

- `solve.py:2780` — `record["theme"]` is a **dict** (`cell`, `membership`, `in_the_cell`,
  `group_cap`, `P`, …), built in `solve()`.
- `solve.py:3071` — `record["config"]["theme"]` is a **string**, built in `_config()`.

Both are named `theme`, both live in the same record, and the tracked manifest carries the
`config` one — so `config.get("theme")` looks exactly right, returns `"dark_vivid_green"`,
and every `.get()` on it raises. The gate a themed pass actually ran under is a third
place, `config["themed_bar"]`.

**Proposal.** Rename the dict to `record["theme_pool"]` (it is a description of the pool,
not of the theme) and leave `config["theme"]` as the cell name it is. Fold
`config["themed_bar"]` into it or name it `config["theme_bar"]` so the two config members
sort together. One-line migration note in `GALLERY.md`; no reader outside this repo.

## 4. The record format carries its own documentation, at runtime

**118 `*_is` / `*_are` prose keys** are written into JSON records across `src/`, 27 of them
in `solve.py` alone. A tentative `manifest.json` is roughly half explanation by bytes —
`fine_bar_is`, `augment_is`, `truncation_is`, `bars_are`, `floor_rule`, `group_cap_is`,
`reachable_is`, `cell_at_bar_is`.

The instinct is right and I would not remove it: a record that cannot say what it ran
under is the defect several of these were added to fix. But the prose is **identical in
every row of every record** and is versioned by nothing.

**Proposal.** Keep the *values*, move the *explanations* to one tracked
`curation/record_schema.json` (or a `SCHEMA_NOTES` dict beside `SCHEMA`), and have records
carry `"schema": 2` plus a pointer. Same information, one copy, and it gains a version
number — which the current arrangement cannot have, since editing the prose in the builder
silently makes old and new records disagree about their own fields.

## 5. Fourteen modules write an HTML page and twelve carry their own CSS

`below_bar`, `color_sheets`, `distinct`, `hunt`, `label_fate`, `label_migration`, `mine`,
`palette_coverage`, `seat_sheet`, `sheet`, `solve`, `swatch_frequency`, `tentative`,
`votes`, plus `render_glance`, `render_grade`, `top_slice_probe` and `supply/autopsy`.
Twelve of them define their own `grid-template-columns` block. The dark palette
(`#101216` / `#e6e8eb` / `#2c313a`) is copy-pasted throughout — I copied it again writing
this session's throwaway page, which is how I know.

**Proposal.** A `curation/page.py` with `shell(title, header, tiles, css_extra)` and one
`STYLE` constant. Each caller keeps its own tile rendering and its own captions; only the
document skeleton and the palette are shared. Conservatively **1,500–2,000 lines**, and
every page gets the same keyboard handling and responsive behaviour for free.

`labeling/page.html` already proves the pattern is acceptable here.

## 6. The `curation/` docs are four changelogs that answer as reference

| file | lines | headings | avg section | dates |
|---|---|---|---|---|
| `GALLERY.md` | 4,200 | 89 | 47 lines | 166 |
| `LEGS.md` | 3,404 | 72 | 47 lines | 109 |
| `README.md` | 3,130 | 44 | 71 lines | 120 |
| `MEASUREMENTS.md` | 1,563 | 28 | 56 lines | 48 |
| `tests/README.md` | 1,948 | 15 | **129 lines** | 116 |

**A date every 17 to 25 lines.** These are decision logs — and they are excellent ones;
the reasoning they preserve is the most valuable thing in the repository and none of it
should be thrown away. The problem is that they are also the *reference* documentation,
so answering "what does a themed pass do today" means reading an argument that reaches
today's answer through three superseded ones.

**Proposal.** Split each into `X.md` (what is true now, present tense, no dates — target
a quarter of the current length) and `X_decisions.md` (the log, dates kept, append-only).
The naming rule's heading-citation convention survives the split unchanged, and a
`git grep` repoints any citation that moves.

`tests/README.md` needs headings more than it needs splitting — 129 lines per section
means nothing is addressable, which matters because CLAUDE.md links into it five times.

## 7. `curation/` is 64 modules in one flat package

No subdirectories, so `solve.py`, `k_sweep.py`, `k_sweep_plot.py`, `votes.py`,
`seat_sheet.py`, `growth_plot.py`, `swatch_frequency.py` and `durability.py` sit at one
level with no signal about which are load-bearing and which are one-off legs.

**Proposal.** Group into `curation/pool/` (ledger, flatness, signatures, intake, prune),
`curation/select/` (solve, ceiling, rules, floors, distinct, tentative),
`curation/legs/` (hunt, mine, depth, rotation, remode, repetition, reframe),
`curation/pages/` (the §5 page writers). Re-exports from `curation/__init__.py` keep every
import working, so this can land in one commit with no call-site churn.

Lower priority than §1 — a flat package of 64 is annoying, a 6,354-line module is a wall.

## 8. Smaller things

- **`engine.engine_path()` raises where callers expect a probe.** CLAUDE.md already warns
  that a bare `not engine.engine_path().is_file()` interrupts collection for the whole
  lane. That a convention has to warn about an API is the argument for adding
  `engine.is_built() -> bool` beside it and letting the guard ask the question it means.
- **`shortfalls.groups.counts` is silently `[:20]`.** `held` carries the true count, so
  `len(counts)` is wrong and looks right — I got it wrong first pass this session. It is
  the one member of that block with no explaining comment where `realized_max` and
  `at_the_cap` both have one. Add the comment, or rename to `counts_top20`.
- **`tentative.read_rows` vs `read_manifest`.** `read_rows` is the odd one out against the
  `read_*` family elsewhere; `rows()` or `seats()` would read better. Cosmetic.
- **The build-era section in CLAUDE.md is 35 lines carrying its own deletion instruction.**
  Everything it names still exists. Worth confirming it is still wanted before publication
  rather than at it.

## 9. CLAUDE.md — done, and what is left

**Already applied this session.** `### The two lanes` was **128 lines, 31% of a file that
loads into every session**, and about 70 of those were chronology: the "nineteen over the
previous reading" narrative, the `5665ae6` three-reds story, the 2026-09-09 pair and the
two before it, and the per-crop ingest arithmetic. Every figure in it is already in
`tests/README.md` two to five times over, and the section's own closing sentence said the
log belongs there and not here. Rewritten to the current figure plus the rules the log
produced, with every rule preserved verbatim in substance — the ratchet, the forbidden
repoint, zero-skips-means-short-cache, the ingest/sheet distinction, the fixture lesson,
the parametrized-guard caveat. **412 → 377 lines; the section 128 → 94.**

Everything else in CLAUDE.md checks out. I verified the four `test_history_purity`
exemption lists against the source (all four match, including `ALLOWLIST` being empty and
`LARGE_TEXT_ALLOWLIST`'s three entries), the `.gitignore` negation lines against
`tentative.PUBLISHED` (seven each, agreeing), every named test file (ten, all present),
every named symbol (`child_priority_flags`, `shipped_cyclic_maps`, `protected_keys`,
`engine_path`, `palette_sets.cyclic`), and all three commit references (`2dc6a8b`,
`915ede6`, `5665ae6`). No stale claims.

**Left as a larger refactor.** `## Locked conventions` is 117 lines, the longest section
remaining, and it has the same problem the lanes section had: several entries argue their
history inline. The `.gitignore` entry spends 14 lines on the tentative-store hole and the
`index.html` ruling; `test_history_purity`'s entry spends 17 on four exemption lists. Both
belong where §6 would put them — the rule here, the argument in the module doc. That would
take CLAUDE.md under 300 lines. I did not do it in this session because unlike the lanes
section there is **no second copy** of that reasoning anywhere yet, so the split has to
write the destination before it trims the source.

---

## Suggested order

1. **§1** split `curate_commands.py` — biggest friction, zero risk.
2. **§3** the `theme` shape collision — the only item here that is a latent bug.
3. **§2** two-tier CLI help — large mechanical saving, pairs naturally with §1.
4. **§6** split the four `curation/` docs into reference + decisions.
5. **§5** one page shell.
6. **§9** finish CLAUDE.md once §6 gives the arguments somewhere to live.
7. **§7** subpackage `curation/`, and **§8** whenever each is passed.
