# Codebase review — what was not resolved

Written 2026-09-12 against [`codebase_review.md`](codebase_review.md), off the session
that implemented it. §1, §2, §3, §5, §6, §8 and §9 landed. What is here is the three
items that did **not**, each with the finding that stopped it — and in two cases the
finding is that the proposal as written collides with a locked convention, so the item is
a decision for Matt rather than a fix somebody can pick up.

---

## §4 — the record format's own documentation, unresolved

**The proposal.** 118 `*_is` / `*_are` prose keys are written into JSON records across
`src/`, 27 in `solve.py` alone; a tentative `manifest.json` is roughly half explanation by
bytes. Keep the values, move the explanations to one tracked `curation/record_schema.json`
(or a `SCHEMA_NOTES` dict beside `SCHEMA`), and have records carry `"schema": 2` plus a
pointer. Same information, one copy, and it gains a version number.

**What stopped it: the proposal as written contradicts the records convention.** CLAUDE.md
locks *a label row carries its full join — the label and the complete render parameters in
the same row — so a labeled example is never split across files*. The `*_is` keys are that
rule applied to a record's own **fields**, and the property they buy is the one a pointer
cannot: a record read in isolation — out of the archive tier, years later, by somebody with
no checkout at that revision — still says what it ran under. A pointer to a file in the
repository is only as good as the reader having the repository, at the right commit. Two of
these keys exist *because* a record could not say which rule chose it (`theme_bar_is`,
`truncation_is`), which is the defect being reintroduced.

**The half of §4 that is right and is not addressed.** The diagnosis is sound: the prose is
identical in every row of every record and is versioned by nothing, so editing it in the
builder silently makes old and new records disagree about their own fields. There is no
detector for that today.

**The design that gets that without splitting the record.** A module-level `SCHEMA_NOTES:
dict[str, str]` beside each `SCHEMA`, read by the builder at write time, so the prose has
one copy **in the source** and the record still carries it whole. Then `SCHEMA_NOTES` is a
thing a guard can pin: a test asserting that every `*_is` key a record writes comes out of
`SCHEMA_NOTES` and that no note changed without `SCHEMA` moving. That is the version number
§4 asks for, on the source rather than on the reader.

**Why it was not done in this session.** 118 keys across the tree, and the interesting part
is not the mechanical move — it is deciding whether a *changed* note is a schema bump. A
note corrected for a typo is not; a note that now describes a different rule is. That rule
has to be written before the guard can hold anything to it, and it is a call about what a
record's schema number means, which is Matt's.

---

## §7 — `curation/` as 64 flat modules, unresolved

**The proposal.** Group into `curation/pool/`, `curation/select/`, `curation/legs/` and
`curation/pages/`, with *"re-exports from `curation/__init__.py` keep every import working,
so this can land in one commit with no call-site churn."*

**What stopped it: the re-export shortcut is the thing `2dc6a8b` was about.** CLAUDE.md
records it under the CLI conventions — *handler names resolve through `__getattr__`, never
re-exported*, because written eagerly, `from .draw_commands import render as render` makes
**two independent bindings of one function and a monkeypatch of either stops moving the
other**. That is not a CLI-specific hazard; it is what an eager re-export is. And this
suite monkeypatches `curation` modules heavily — `solve`, `tentative`, `headroom`,
`ceiling`, `flatness` and `candidate_ledger` all get patched by name — so a
`curation/__init__.py` full of re-exports would give every one of those two addresses, with
the tests patching whichever one they happened to import. The failure mode is a guard that
goes green while patching nothing, which is the worst kind this tree has.

**So §7 is a real move, not a re-export.** Move the 64 modules and repoint every import —
about 1,500 call sites across `src/`, `tests/` and the six `cli/curate_*_commands.py`
modules that §1 just created. `git grep` makes it mechanical and `ruff` catches what it
misses, but it is a whole prompt's work and it wants the tree to itself: every import line
in the package moves at once.

**One ordering note for whoever takes it.** §1 landed first and helps: `cli/` now names the
five `curate` families, and those names (`ledger`, `solve`, `votes`, `mine`, `colors`) are a
better-tested cut of the same nouns than the four §7 proposes. `curation/pages/` in
particular should be read against what §5 found — the page writers share a colour
vocabulary and almost no layout, so they are a family by palette rather than by structure.

---

## §8 — `tentative.read_rows`, declined on the evidence

**The proposal.** *"`read_rows` is the odd one out against the `read_*` family elsewhere;
`rows()` or `seats()` would read better. Cosmetic."*

**The finding: it is not the odd one out, it is the family name.** Three other modules
spell the same accessor the same way — `discovery/pools.read_rows`,
`curation/palette_coverage.read_rows` and `curation/manufacture`'s call to
`coverage.read_rows`. Renaming `tentative`'s would make it the one exception rather than
stop it being one, and `read_rows` / `read_manifest` is already a parallel pair. Left as
it is, deliberately.

---

## §6 landed as a split, not as a distillation — and the target it missed is the wrong target

**What landed.** All four docs are `X.md` + `X_decisions.md`, every moved section
**verbatim under its own heading in its original order**, zero headings renamed, zero
prose lost — checked mechanically, twice, by the splitter and then by an independent
adversarial pass over each file. 2,277 lines of argument moved out.

**What did not.** §6 asks the reference file to be *"what is true now, present tense, no
dates — target a quarter of the current length"*. The result is GALLERY 4,200 → 3,596,
LEGS 3,404 → 3,150, README 3,130 → 2,799, MEASUREMENTS 1,563 → 902. Date density barely
moved: GALLERY kept 148 of 170.

**Why, and it is not conservatism.** A rule in this repository is routinely *stated* with
its date, because a record is read against it: *`cascade` is THE DEFAULT since
2026-09-07*, *a record carrying `reachable_locations` was taken under the old placement*,
*the share was 0.05 until 2026-09-12, so a record taken before THAT ran at two thirds of
this cap*. That date is not the log — it is the reference information a reader needs to
interpret a record they are holding, and a store full of records taken under seven
successive rules cannot have a dateless reference. So *no dates* is the wrong test for
whether a section is reference; *is this the argument, or the answer* is the right one,
and that is what the split was actually done on.

**The quarter-length version is a different job and a riskier one.** Getting there means
**authoring new distilled prose** over 12,297 lines — not moving text — and the failure
mode is a reference doc that misstates a live rule while looking authoritative. This
session deliberately did not do it: the mechanical split is lossless and reversible, and
a distillation is neither. Whoever takes it should distil **one** file first and have it
read before doing the other three.

## Two things the numbers in the review do not support

Recorded because both were measured while implementing, and both would send the next
reader the wrong way.

**§5's saving is not 1,500–2,000 lines.** The ten dark style blocks hold **341 lines**
between them and share **three identical rules in one pair** — measured over the parsed
constants, not estimated. A fate table's absolute-positioned captions, a score sheet's
sticky band headers and the vote page's two-up keyboard UI are three different instruments
and a shared layout would be overridden by every caller. What *was* duplicated is the
colour vocabulary: 107 hex literals across 13 modules, in three grounds within four of 255
of each other and three inks within seven. That is what `curation/page.py` now holds, and
what went is 107 literals rather than 2,000 lines.

**§8's `shortfalls.groups.counts` already had its comment.** The review offers *"add the
comment, or rename to `counts_top20`"*, and the comment had landed in `cb66b30` — the same
session's last commit. So the rename was the part left, and it is done: naming the
truncation is worth more than commenting it, because the defect happened at a **read** site
and a writer's comment is not in front of the reader.
