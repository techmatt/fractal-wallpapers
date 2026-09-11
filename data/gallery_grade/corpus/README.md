# A frozen corpus, and why one is tracked at all

Every other corpus this head fits on is **regenerable**: `gallery-grade population`
re-joins the store to the ledger and `gallery-grade split` re-draws the sides, both
under the regenerable tree at `artifacts/gallery_grade_head/`. Nothing there needs
keeping, because the command that made it will make it again.

**A corpus stops being regenerable the moment the store grows past it.** The join is
*every graded row the store holds*, so the day another sheet is graded the same
command gives a different, larger population and a different split over it — and the
run fitted on the old one becomes a run nobody can rebuild, with nothing looking
broken. That is a one-way door, and the files below are what holds it open.

They are kept **byte for byte**, not re-serialised, so `checksums.json` still checks:
a copy that pretty-printed itself on the way in would verify nothing.

## `twelve_sheets/`

The 2,829 rows over twelve labelling sheets that `best_head_20260910` built and
`deterministic_refit_20260910` fitted the adopted column on. `models/gallery_grade`'s
`CORPORA` names it and the trainer reads it from here rather than from the
regenerable tree — the one corpus that does.

```text
population.jsonl     2,829 rows, one per render, the join to the ledger's 640x360 picture
split.json           the sides, drawn over lineages at SPLIT SEED 20260910 — 2,263 / 566
targets.json         the de-drifted target fit; the RAW column is what the band trains on
render_key_of.json   candidate key -> render key, which is how a row finds its target
environment.json     the box the deterministic promise is about
checksums.json       every sha256 above, the row and sheet counts, and the split seed
```

⚠ **`population.jsonl` carries absolute paths and that is deliberate.** It is a frozen
record rather than source, it is re-homed through `paths.rehome` on the way in, and
rewriting the field would break the checksum that makes the file worth keeping. The
pictures it names are ignored candidate JPEGs and were never going to resolve in a
fresh clone regardless.

**The target is not the row's own grade.** `population.jsonl`'s `score` is the verdict
as cast; the band trains on `targets.json`'s per-render **`raw`**, which is the same
scale de-duplicated across a render's repeat gradings. `models/gallery_grade/README.md`'s
*What the de-drifted target is for* has why the `normalized` column beside it is a
yardstick and not a training target.

**Adding another frozen corpus is a decision.** These two files are over
`tests/test_history_purity.py`'s `MAX_TRACKED_BYTES` and are excused by a
`LARGE_TEXT_ALLOWLIST` prefix whose reason is written at that site. A corpus that is
still regenerable does not come here.
