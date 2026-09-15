The decision log for [`README.md`](README.md): the argument behind each rule that
file states, kept where it cannot be mistaken for the rule itself.

Every section below was moved here **verbatim on 2026-09-12**, out of the reference
file, in the order it stood there. Each one argues a change — a renamed column, a
repaired renderer, a rule replayed and refused, a pile of pictures deleted — and
carries the date, the measurement or the ruling that produced today's answer. Nothing
was rewritten, re-dated, merged or reordered on the way across, and the reference file
keeps at most one present-tense line in each one's place, citing the heading it went
to.

**Entries are APPENDED and never inserted.** A new decision goes at the end under its
own heading, so the file reads in the order things were settled, and a citation to a
heading here keeps pointing at the same argument for as long as nothing renames it.

#### The prune ranks on `rank_key` and a gallery seats on the cascade, and below the bar those are one order

**This is why the seating flip of 2026-09-07 left retention alone, and it is an
argument rather than an omission.** `_prune_ranks` reads
[`curation.rank_key`](rank_key.py); `solve.DEFAULT_KEY` has been
`solve.CASCADE_KEY` since that day. Read cold, that looks like two keys deciding
the same pool's fate by different lights. It is not, and there are four reasons in
a row.

**The cascade *contains* the rank key.** Above `solve.Q4_BAR` it orders on the
fine-tier head (`models/gallery_grade/`, fitted on human verdicts about pictures
that had already cleared the gate); below the bar it hands back each row's
`rank_key` value unchanged. So **below the bar the two keys are one order**, and
retention ranking on `rank_key` is already ranking on the cascade's own lower
half. There is no third key anywhere.

**The prune's population sits mostly below the bar, so the two mostly cannot
disagree.** A pair whose rows straddle the bar, or sit wholly beneath it, is
ordered identically by both. The disagreement can only bite where a prune's whole
decision is made among rows that are *all* above the bar — and that case had never
been counted until 2026-09-07. It is **877 of the 3,729 pairs at or over
`RETAIN_PER_PAIR`, 23.5%** and 23.6% weighted by rows; on those the two orders
name a different top row 70.6% of the time, and a different survivor *set* in 23.
Restricted to the pairs that actually delete something, the survivor set differs
in **23 of 30**. So it is rare that the question arises and near-certain that the
keys differ once it does. [`MEASUREMENTS.md`](MEASUREMENTS.md)'s *How much of the
prune is settled above the bar* carries the reading, including why real prune
decisions are not recoverable from any record.

**Seating-only was a ruling and the reason is containment.** A gallery's ceiling
holds a bad ordering *at a seat*: the row is still in the pool, `curate seat-sheet`
shows what the two keys disagree about, and the next solve reseats. `_prune_ranks`
has no such containment — it deletes the row and its picture permanently, and
[`MEASUREMENTS.md`](MEASUREMENTS.md) says why the deleted side of that decision
cannot afterwards be read back. A key adopted on one seating's worth of evidence
belongs on the reversible decision first.

**And `rank_key` cannot be retired while the cascade runs.** `solve.cascade_order`
builds the cascade out of `solve.ranking_for`'s `rank-key` mapping and lays the
fine head over its top; retiring `rank_key` would retire the cascade's below-bar
half with it. The two are one order, and that cuts both ways. **Deprecating
`rank-key` on 2026-09-08 is not that retirement**: what it took away is the
*offer* — `--key rank-key` is off `solve.OFFERED_KEYS` and a new gallery cannot be
seated on it by name — and it took away nothing else. `solve.KEYS` still holds all
three, `solve.ranking_for` still resolves it for a record that names it,
`_prune_ranks` still ranks on it, and the cascade still is it below the bar.

`curation/GALLERY.md`'s *`cascade` is the default since 2026-09-07* is the seating
half of this, and `tests/test_seat_sheet.py` pins that `_prune_ranks` reaches
`curation.rank_key` directly and names neither `DEFAULT_KEY` nor the cascade.

**The first cascade record is `20260908T144844Z`**, taken at n=1000 under
`--fine-bar 0.50`. Before it, all **62** records in the tentative store carried
`solve.config.sort_key_named` = `rank-key` — every one, published and unpublished,
counted 2026-09-07 — so anything read off a *tracked* stamp is still a rank-key
seating: the new record is unpublished, `tentative.latest()` resolves over
published stamps only, and every figure the site draws is on the old side of the
flip. What the record does close is the missing side of a comparison: a
cascade-versus-rank-key read at n=1000 no longer has to be derived against a fresh
in-memory solve, which is how `GALLERY.md`'s *The desire list is aimable at
cell × mode and nowhere else* had to take its reading.

### `mine.make` dropped `mode_params`, so every varied candidate in the pool is the bare mode's picture

**Fixed 2026-09-08 in `FIX_ckpt116_mine_mode_params_0908`; the 10,664 rows already in
the pool were left as they are, deliberately.** What follows is what the defect was
and what it cost, because the rows are still there.

**It was one missing keyword.** `hunt.Maker.make` passes
`mode_params=dict(plan.mode_params or {})` into `colorize.render`; `mine.make` — the
call every `curate mine` and every `curate depth` leg actually renders through —
does not, so the parameter defaults to `{}`. A leg that names
`direct_trap_multiply@opacity=0.6,threshold=0.2` on its roster therefore *records*
the variant on its row, takes the variant's own recipe key (`mode_params` is in
`recipes.KEYED` and reaches the digest through `engine.coloring`, so the key is not
the problem), and **renders the bare mode**. `mine.make`'s own docstring claims it
is `hunt.Maker.make` "with the single `seconds` split eight ways and nothing else
altered … at the same recipe", which is what kept this invisible.

Measured 2026-09-08 over the pool: **10,664 rows carry a non-empty `mode_params`,
across thirteen legs, and every leg sampled has its stored picture reproduce
byte-for-byte as the bare-mode render.** Four probed rows a leg, own-params render
against bare-mode render against the stored file: bare matched 4/4 in every leg.
`dtm_lc_smoke`'s pictures are dated 2026-09-07, five days after the roster feature
landed, so this is not the pre-`52d6d80` era being rediscovered.

`direct_trap_multiply` is the only mode that has ever carried settings, so the
damage is bounded to it — and it is not only the pictures: each row's judge score
is a reading of the bare picture under the variant's key, so the whole
`dtm_variants` programme compared a mode with itself. The clean proof came from the
other direction, in `curation.label_migration`'s byte-identity sweep: 123 of 123
varied-dtm rows whose staged redraw differed from the ledger's file have a
**bare-mode** redraw that is byte-identical to it.

**A second renderer had the same hole and it would have undone the fix.**
`candidate_ledger.rerender.render_pair` — what puts a picture back — built its engine
spec by naming four members of `recipes.KEYED`, so a restored varied row was the bare
mode's picture; and `re_render`'s key guard rebuilt each row's key with `mode_params`
pinned to `{}`, so every varied row failed it and was refused. Protective by accident,
and it would have gone on refusing them after the pictures were correct. Both fixed
with the keyword, and the guard now rebuilds with the row's own settings — the row is
the only place a leg's chosen settings exist.

**The guard is one test over every renderer, and it had to be widened once already.**
It began as `tests/test_mine.py::test_the_two_makers_draw_the_same_picture_for_one_recipe`
over three renderers. The tree has **eight**, four more were found dropping `curve` and
`palette` the same week, and a registry somebody has to remember to add to is a registry
that goes stale — so it is now `tests/test_renderer_agreement.py`, which renders one
recipe through every renderer, compares the **bytes**, requires the bare arm to differ so
a guard on settings that move no pixels cannot pass, and **sweeps the tree for
`colorize.render` call sites** so a renderer added later is either covered or declared
exempt with its reason. An assertion that each site passes `mode_params` would have
caught this one argument and nothing else — and it did exactly that.

**What it cost, measured on the seats.** Twelve of the 1,000 seats of
`20260908T201911Z` carry a non-empty `mode_params`; seven of their stored pictures
were the bare mode's and were re-rendered. **Six of the seven collapse once the file
matches its key** — `P(≥4)` 0.94→0.002, 0.97→0.018, 0.95→0.011, 0.83→0.000 — so six
seats were held on a picture the pool would not have chosen. The record was
deliberately **not** re-solved: thousands of varied rows in the pool are still bare
under their own keys, so a fresh solve would be differently wrong rather than more
right.

**The rest of the pool was repaired on 2026-09-08 in
`PRECLOSEOUT_ckpt116_renderer_holes_and_repair_0908`.** All 10,664 were re-rendered
through the fixed path and re-scored, because every standing reading on them was about
another picture. `curate candidate-ledger bare-varied` is what names them: a row carrying
settings whose picture's path is under neither `hunt` nor `label_migration` went through
`mine.make` and was drawn bare, which is `label_fate.drawn_bare`'s rule reached rather
than restated. What that repair did **not** do is re-solve — see the next section.

### `release.Task` had the same hole twice more, and `curve`/`palette` was the second

`mode_params` was added to `release.Task` on 2026-09-04 after twelve release renders
of varied seats came out bare. **The same argument applies to `curve` and `palette`
and they were not there**: both are `recipes.KEYED` members, so a row whose recipe
names a `log` field or a sampled `gamma` renders — through the release path — as the
*plain* picture under that row's name. It went unnoticed while the pool held only
plain-recipe rows; `label_migration merge` ended that on 2026-09-08 by putting 3,015
rows derived from the two label corpora into the pool, a third of which carry knobs
the candidate path never spends. Both are on the task since `curate label-fate`,
default `None`, so every candidate leg renders exactly as it did.

### The fix was one builder, not four more keywords

**Closed 2026-09-08, and the closure is structural.** Five legs turn a stored row into
a release render — `solve.render_seats`, `checks.tasks_of`, `run`'s release leg,
`votes.render_fulls` and `label_fate.render` — and every one of them spelled the task
out inline. Four passed `mode_params` and dropped `curve` and `palette`. Two guards in
`tests/test_curation_release.py` counted `mode_params=` and `autolevel=` per builder and
were **green through all four**, which is the argument against fixing this by adding
keywords: the next member is the one nobody counted.

So there is now **one** builder, `release.task_for`, whose picture-deciding parameters
have no defaults. Forgetting one is a `TypeError`; a member added to `recipes.KEYED` is
added to one signature and every leg fails until it says what it passes. The guard is
correspondingly structural — `release.Task(` is constructed in exactly one place in the
tree, and the five legs are named as still going through it so a leg that quietly
stopped releasing is not read as compliance.

Two more renderers were fixed with them. `shrinkage._render_one` dropped all three
members **and** re-measured its levelling at label geometry rather than inheriting the
candidate's decision — pre-`87ad3eb` behaviour, and a second uncontrolled difference
inside the one quantity that module exists to measure, since a shrinkage read is defined
as *the geometry and nothing else moves*. It now reads the recipe through
`recipes.of_record` and takes its borrowed curve from `stamps.for_release`, batched in
the parent. `manufacture`'s render arm passes the row's settings; its recolour arm needs
none, settings being legal only on a direct trap, which has no field to dump.

### The fourth appearance was a spec with no row behind it, and `trap_circle` is where it shows

**Closed 2026-09-15.** The three sweeps above look for a caller of a **builder**:
`colorize.render`, `locations.spec_of`, `release.Task`. A site that writes its engine
spec out as a dict literal calls none of them and is invisible to all three. Nineteen do,
seventeen of them not a builder, and `tests/test_renderer_agreement.py`'s `HAND_BUILT`
is now the table that holds them — keyed by **function**, because a table keyed by module
is what let `render --manifest` hide behind `cli.draw_commands`' other door.

**What such a site drops is the curve, and it does not look like dropping anything.** A
spec says `mode` or `coloring` and never both. `mode` alone resolves through the engine's
catalog, which puts `Transform::Log` on `trap_circle` and on the niche `de` and
`Transform::Linear` on the other eighteen, while every production render has
`engine_spec.coloring_of` write `colorize.CURVE` over it. So a bare mode draws
`trap_circle` through a transform nothing in this project renders at.

`colorize.field_row`'s docstring has said so since it was written — *"a field dumped by
mode name would carry the catalogued curve into its record and recolour every
`trap_circle` through a curve nobody rendered"* — and three sites dumped by mode name
anyway. A field's **binary** is unaffected (`dump-field` writes the raw scalars before
any normalization); its **record** is not, and `engine recolor` takes
`spec.transform.unwrap_or(record.transform)`.

`manufacture` and `palette_coverage` both state the curve on their recolour, so
`manufacture` never drew a wrong picture. `palette_coverage` has **three** other readers
of its own dump that did not: `field_shape`, which is what the panel is *chosen* on, and
`_make_tile` and `contact_sheet`, which draw the pictures a person sets the swatch bar by
eye against. Three of the shipped panel's sixteen cells are `trap_circle`, and
**3,171 of its 16,912 measured rows** came off them. Re-reading this machine's 56 dumps
under the curve production spends moves **three of the sixteen seats** — two of the three
dropped are `trap_circle` cells. The rows themselves were measured right; the panel they
were measured on is not the one the rule specifies.

The fix is at the **dump** and not at the three readers: `palette_coverage.dump` and
`manufacture.field_for` build through `colorize.field_row` + `renders.spec_of` now, so
the record is the builder's and inheriting it is inheriting the builder's answer. A
cached field whose record disagrees is re-dumped rather than trusted — a cache must not
be able to make a fixed command go on reporting the old number.

### The `curve`/`palette` refusal was one rule doing two jobs, and a NEW MAP is neither

`render` refused a `fields=` directory beside **either** override. Read from the split
that decides it, the two halves fail differently and only one of them was ever about the
cache — so **since 2026-09-11 the refusal is the curve's alone**, and a palette override
rides the cache. `recolored` takes the whole pass; `test_a_recolour_is_the_render_byte_for_byte`
sweeps three of them and a second guard holds each path to the pass actually *moving* the
picture, because two paths agreeing is also what you get when both of them ignore it.
The split below is why, and it is unchanged apart from the verdict.

**The map is not in a field's identity at all.** `renders.RECOLOR_MEMBERS` is `colormap`
and `recipe`, and `field_job_name` pins both to constants — `FIELD_COLORMAP` and
`finished.recipe(mirror=False)` — so what a dump is a function of is the place, the
geometry, the mode and the curve, and nothing else. That is the whole of why one
iteration pass serves thirty-two candidates, and it means **a map this repository has
never rendered before is served by the field cache exactly as a shipped one is**.
`mirror` rides along with it: `recolored` takes it as a parameter and it is the one knob
of the seven a recolour does not pin, which is why a map's `kind` can vary over one
dumped field.

* **`curve` is field-side** (`renders.FIELD_IDENTITY`) and the hole is a call site rather
  than the cache: `_shared_field` never passes a curve down to `field_of`, and
  `engine recolor` reads the transform out of the dump's own record when the spec leaves
  it unsaid — so an overridden render served from the cache would paint the `linear`
  field wearing the override's name. `field_job_name` already digests a curve, so each
  distinct one would simply get its own field.
* **`palette` was recolour-side** and the hole was a dropped argument: `recolored` wrote
  `_plain_recipe(mirror)` and threw the other six knobs away. The Rust `RecolorSpec`
  already carried a full `Palette` and `fn recolor` spends it through `coloring::shade`
  and `coloring::toned` exactly as `fn render` does, so nothing about the cache ever
  stopped this. **Closed in `palette_variant_mine_ckpt120`**: `recolored` takes a
  `palette`, defaulting to the plain pass of its `mirror` so every call that predates it
  reads as it did, and `render` hands it the pass it keyed the row under.

**What that bought and what it cost.** A varied palette is now a **recolour**, so
`curate depth --vary-palette` prices its varied rows the way an unvaried leg prices its
plain ones on the three shareable modes — which is the only thing that makes *varied
against unvaried inside one leg* a comparison rather than two legs at two prices. The
phase sweep of 2026-09-11 is the demonstration: 100 points over 5 seats, twenty phases
each at candidate geometry, **50 s of wall on three workers** — five dumps and ninety-five
recolours where the old refusal would have made it a hundred renders.

`curve` keeps its refusal and `curation.candidate_ledger.rerender` keeps a refusal that
now names the curve alone. The one thing still unmeasured is whether a **levelled**
repaint composes with a non-identity `gamma` or `transfer`; the passes compared are
`phase` and `cycles` over the plain defaults, which is what the varied draw spends.

### The subtraction on a card is not a margin, and the card now says which leg placed the seat

**The `gap` column was renamed `p_fine Δ` on 2026-09-09 and the old name was
wrong**, measured rather than suspected — `forced_seating_20260909`, Part A. It
reads as *how close this row came to a seat* and there is no such quantity on this
page: the rule that took the row compared no scores at all. `cell_allowance` is a
**count** against an allowance, `location` is a seat standing in a cluster, and
the competitor beside either is picked **after the fact** as the marginal seat —
the two rows never met. 127 of `20260909T173957Z`'s 173 paired cards carried a
negative value, which reads as *I scored higher and still lost* and is simply what
a rule that never read a score does.

**So the fact that explains a negative one goes on the card ahead of it: the leg
that placed the competitor.** Of those 105 negative `cell_allowance` competitors,
**zero** came from the ranked walk — 47 from `swap`, 47 from `augment`, 11 from a
mode floor's mandate. `general_pool` is the only leg the seating key orders; the
swap and the chain accept on the lexicographic objective and a mandate walks one
demand's subpool scarcest-first, so a seat from any of the other three says
nothing about how the two rows would have compared. A card whose competitor came
from the ranked walk gets no disclaimer, because there the two orders did meet.

The column itself stays — a competitor reading 0.01 above a refused row and one
reading 0.4 above it are different findings — under a label that cannot be read as
closeness, with the disclaimer beside the number and once at the top of every
refused slice.

**Under the colour floor the leg column is MORE load-bearing, not less.** Re-read on
the `K = 3` + floor record, the competitor was placed by a **mandate** on 103 of 144
cards — 50 `cell_floor` and 53 `mode_floor` — by `swap` on 14, and by the ranked walk
on only **27**. So 66 of the 81 negative-delta cards are now against a seat that no
seating key ordered at all, where before the floor existed the mandate accounted for
11 of 105. Adding a soft demand adds a leg that does not read the column the card
subtracts, so the disclaimer is doing more work on every record taken since
2026-09-09.

⚠ **The 0 / 0 / 64 / 175 / 73 above is a `K = 2`, no-floor, `p_fine ≥ 0.50` reading
and does not survive either ruling.** Rebuilt on the `K = 3` + floor record the same
312 rows read **0 / 0 / 64 / 168 / 80** — seven more of the graded 4s ship, with 25
refused → seated against 18 the other way and 269 unchanged. And the fine head's
adoption moved rung 2 itself: `label_fate`'s second rung **is**
`solve.DEFAULT_FINE_BAR`, so a fate readout taken after 2026-09-09 sits on a
different rung boundary *and* a different column, and no two of these three readings
are comparable. Read the rungs off the record's own `config.fine_bar` and
`config.fine_head`.

**Every count in this section is one record's**, `20260908T211552Z`, which is what
made the shape visible. The same population re-solved against the repaired pool as
`20260909T061451Z` reads 350 / 99 / 72 / 3 by rule against 348 / 102 / 71 / 3, 452
paired over 114 distinct rows, 218 where no single departure would have been enough,
and a rebuild reproducing 449 of 449. **The proportions are the finding and the
integers are not** — a greedy seed plus swaps plus augment lands somewhere else under
any perturbation, and only 892 of 1,000 seats survived this one.

**Those three are three-store readings.** The gallery-grade population alone, over
`20260909T173957Z` — the pooled fold, the fine bar at 0.50 — is **312 rows: 0 / 0 /
64 / 175 / 73** across the five rungs, and the 175 refusals split **120
`cell_allowance`, 51 `location`, 3 `twin`, 1 `spiral`** with **zero**
`another_place_is_the_same_place`. 173 paired over 77 distinct rows, 87 where one
departure would have been enough, 2 unpairable. The shape the narrower page makes
visible is that `cell_allowance` is more than twice `location` here: what stops a
wallpaper a person wanted is far more often the colour ceiling than another picture
at its own place.

**A pooled pass never writes `another_place_is_the_same_place` at all.** Since the
fold merges instead of deleting (2026-09-09), a row that loses its cluster's seat to a
sibling place is refused by the ordinary **`location`** rule, and its card carries the
sibling, the cluster the two are seated under, and **both spokes of the star** — each
place's neutral distance to the survivor, never the distance between the two, which
`distinct.suppress` does not measure. `label_fate._fold` is where a `location` card
gets that decoration, and it fires only where the seat that took it is at another
place. Today's record writes **zero** of the old refusal.

The constant is still read, because a record taken before that fold explains itself:
there the whole place went at pool construction, before a seat existed, and the card
names the place that absorbed it off the record's own `preselection.refusals` with the
distance the fold was taken at. `competitors` reads `refusals` on a destructive record
and `folds` on a pooled one — the same rows either way, and the second name exists
precisely because nothing was refused.

**The rebuild is proved before it is used.** `competitors` reconstructs the pass's
final `rules.State` from `solve.pool` and the record's own ceiling, then requires
`counted_refusal` to reproduce every refusal the record wrote down — 450 of them, exactly
— and refuses outright otherwise. The two it cannot be asked about are excluded by name
rather than by silence: `twin` is the diversity rule's, kept per key in the record's
`diversity_refusals`, and `another_place_is_the_same_place` is pool construction's. The
first run of the verb reported a 71-row disagreement that was exactly those, which is
the guard working.

### The 09-02 sweep and `curate re-render` were a loop, and the union is what closed it

**Closed 2026-09-07.** The 3,610 pictures the 09-02 `--leg` sweep took out of the
ten backfilled `runs` legs came back the next morning: 3,615 of them, every one
dated 2026-09-03, the per-leg count of 09-03 files matching the per-leg unnamed
count on all ten. The writer is **`curate re-render`** — the pool's, `rescore.py`'s
`re_render`, not the ledger's — run twice inside `RETRAIN_render_v6`: a `--limit`
pilot that made **61** and stopped at 04:32:41, then the leg proper
04:32:55.8 → 04:59:55 that made **3,554**. 61 + 3,554 = 3,615 exactly, and
`artifacts/curation/pool_re_render/re_render.json` carries the leg's own half of
it (`made: 3554`, `failed: 0`, `refused: 0`, `wall_seconds: 1619.2`). The
arithmetic closes both ways: 15,485 − 3,610 + 3,615 − 495 = 14,995 pictures on
disk, the 495 being the drop in ledger-named `runs` rows over the same days, and
the orphan set measured 0.624 GiB against the sweep's own 0.624 GiB.

**Nothing in that set was garbage. All 3,615 were named by a real store, just not
by the candidate ledger** — **85** by the tracked gate store, **3,530** by
`artifacts/curation/gallery/<pass>/gate.jsonl`, matched 3,530 of 3,530 exactly. So
the sweep and the repair were pointed at the same files and the question was only
which of the two was wrong. It was the sweep, and `_named_by_a_store` is the fix:
the reference set is now the union, the loop is disarmed, and deleting the
pictures behind the kept attempt rows is available as a **named act** rather than
as a side effect of garbage collection.

The gallery half became invisible on 2026-09-07 rather than on 09-03: retiring the
gallery gate store stopped `rescore.pool_rows()` reading the attempt rows, which
is why the pool could put them back in the first place and no longer would.

**Measured after the union, 2026-09-07.** `orphans --include-unmerged`, a dry run
over all ten legs: **0 pictures would be deleted**, against the 3,615 the
ledger-only rule named. Every picture in every one of the ten is named by a store,
which is the arithmetic the audit predicted — 11,380 by the ledger, 85 by the two
tracked decision stores, 3,530 by the attempt rows, and 11,380 + 3,615 = 14,995,
the whole of what is on disk. Eight of the ten now report `store_named` *above*
their picture count (gallery4 6,866 against 6,620) because the stores also name
renders a prune has since taken; that is the reference set being wider than the
disk, which is the safe direction.

| | gallery4 | gallery3 | gallery2 | gallery1 | run10 | run3 | run9 | run2 | run8h | release_v1 |
|---|---|---|---|---|---|---|---|---|---|---|
| on disk | 6,620 | 3,843 | 2,415 | 1,089 | 311 | 234 | 234 | 114 | 111 | 24 |
| named by a store | 6,866 | 3,980 | 2,472 | 1,120 | 320 | 240 | 240 | 114 | 112 | 24 |
| **would delete** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** |

Whether the ten legs are worth keeping is still Matt's and still open. What has
changed is that it is now a question about **11.75 GiB of superseded attempts**
and not one a garbage sweep can answer by itself.

### The 11.75 GiB is not the 14,995 pictures, and only one of its subtrees is free

**Asked properly on 2026-09-07 and the two figures name different things.** The ten
legs hold 77,282 files and 11.76 GiB; `pictures/` — the 15,033 candidate renders the
census is about, 14,995 of them before the repair leg put 38 back — is **2.59 GiB of
it**. The rest is `candidates/` 6.39 GiB, `release/` 2.15 GiB, `framings/` 0.50 GiB,
and `fields/`, which is already empty on all ten.

**Nothing outside the ten names anything but `pictures/`.** Every json and jsonl
under `artifacts/`, `data/`, `labels/` and `models/` was read: **206 files mention a
leg path, 27,133 times, and every one of those mentions is a `pictures/` path.** So
the free subtree is the one whose own writer calls it a cache —
`runs/<leg>/candidates/<field stem>/<map>.jpg`, written in
[`colorize.Clouds.recolours`] and read only by a live pass, which
[`run._discard_partials`] describes as *swept after the attempt leg* and which no
index names, not even inside the leg. **48,632 files and 6.39 GiB, deleted
2026-09-07** under an isolation proved against a 330,763-path reference set built at
the moment of deletion: zero collisions, every path re-checked to be under one of
the ten legs' `candidates/`, and the six subtrees that had to stay still counted
before and after. `absent_pictures()` 0 → 0, the ledger's `missing_pictures()`
0 → 0, and the ratchet untouched at `rows` 308,419 / `recipe_key_named` 294,893 /
`run_index_named` 13,526, because no row moved.

**`framings/` is unreferenced from outside and was still kept**: its own
`framings.jsonl` names each trial by slug, so a store that survives the deletion
would be left naming nothing. That is the orphan sweep's rule applied to a subtree
rather than to a picture — delete what *nothing* names — and it is the line the
09-07 deletion was drawn on.

### A per-cell retention arm cannot prune this store, and the shape says why

Replayed 2026-08-29 over 366,236 rows at 18,424 locations: a rule keeping the top
K per (location, mode) **union** the top K per (location, dominant cell) keeps
**65.8% of the rows at K=1** and frees 15.7 of 49.2 GiB. It is not a tuning
failure, it is the store's shape.

**Rows per location are median 12, p90 40, max 332 — and the two arms together
open median 22 of them.** A location carries median 1 mode but **median 21
distinct dominant cells**, because `colour.cells` is thresholded rather than
singular: a row is dominant in 2.36 cells on average and the codebook has 48. So
at K=1 only **1,819 of 18,424 locations (9.9%)** hold more rows than arms, and
everywhere else top-K reaches every row and refuses nothing. Restricting the arm
to the largest cell buys nothing either — 66.7% kept — because 12 rows over 48
cells rarely collide whichever cell you read. **The mode arm alone at K=1 keeps
13.4% and frees 84.9%**, which is the rule shape this module already ships.

The counterpart worth knowing before any prune is that **deleting rows is not
deleting pictures**. Rows are what `hunt.run` and `mine.population` build `known`
off; a deleted row is a recipe the next leg cannot tell it has already drawn, and
at K=1 that is **10.2 engine-hours** of re-render priced through
[`headroom.render_cost`]. And the two `(location, *)` aggregates above keep every
pair under such a rule — the arms *are* their key spaces — while every count in
them silently becomes a count over winners.
