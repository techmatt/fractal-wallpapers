Human verdicts on rendered locations: the currency everything downstream is
denominated in.

No labels exist yet. The labelling tools arrive in a later slice and will write
here; this file states the one property a label record has to have, because the
standing deficit already reads whatever lands in it.

```
*.jsonl    one label per line, UTF-8, an integer `schema` from the first row
```

**A row carries its whole join.** The class *and* the complete render parameters,
on the same line — the family with every constant, and the viewport — so a
labelled example is never split across two files that have to be reconciled
later. The supply census needs exactly two things from a row, and it needs them
together:

```json
{"schema": 1, "score": 4, "family": {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]},
 "viewport": {"center_re": "0.1", "center_im": "0.2", "width": "0.5"}}
```

`score` is 1 to 4. A 4 is a picture worth releasing and is the unit of currency; a
3 is worth a tenth of one; 1 and 2 are recorded and are worth nothing.

**The family and the viewport are what make a row a location**, and the census
keys on both. Two Julia views at the same coordinates with different `c` are
different fractals, so a record that carried only the viewport would silently
merge them — and the deficit's precedence rule, where a human verdict suppresses
the scorer's opinion about the same place, dies the moment the two sides key a
location differently. Coordinates stay decimal strings, verbatim, and are
normalized at the reader.

A row with a `score` of `null` is a location somebody has looked at and not
judged. It is read past rather than counted.
