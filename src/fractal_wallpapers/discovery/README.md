Finding places worth rendering: seeded walks, reframing operators, and the record
they leave.

A walk descends from a seed one rung at a time. The engine does the looking —
`fractal-engine expand` draws candidate next frames from a geometric policy and
puts each through the structural gates — and this package does the deciding:
which places to expand next, when to reframe onto a nucleus, what to write down,
and when to stop.

```
pools      the tracked seed pools, and the spacing the julia one has to keep
walk       the frontier, the batch, the two reserved floors, the run loop
nucleus    Newton on a nucleus, the atom instrument, the canonical key
operators  reframing a found view onto the atoms around it
ledger     one JSONL record, one schema, a fate on every row
scoring    the seam a trained head arrives through
```

Nothing here judges a picture. The gates are geometry — how much of the frame is
the set's interior, how much variety its escape times have, whether its detail is
spread over the frame or piled in a corner — and the judgement that decides
whether a location is beautiful is a seam (`scoring.py`) with a null
implementation behind it. A walk that runs on the null scorer is a complete walk:
it admits what survives the gates, and its ledger is what the first head gets
trained on, which is the only order the two can be built in.

Two things are worth reading before changing anything here.

**Reframing operators are triggered, never a source.** They apply to a place the
walk already found and admitted, and they inherit both its provenance and its
budget. Every source that enumerated minibrots from first principles was measured
and found dead; what a minibrot is good for is being a *marker* of a dense
neighbourhood, at a scale the search can compute before rendering anything.

**Where a root starts is not decided here.** A root given no view comes home to
its family's frame, and that frame is the engine's — `fractal-engine home-view`,
read through `engine.home_view`. This package holds no framing literal, and the
guard for that is in `tests/test_home_views.py`. It held one once, `{0, 0, 3.0}`,
which agreed with the engine until the engine's Phoenix row moved: after that a
phoenix root framed 66% of its own set with both lobes cut, and nothing in either
half could have noticed.

**Every candidate is recorded, with the gate that refused it.** A walk that
logged only its survivors could never afterwards tell "the gates were too tight"
from "there was nothing there", and both look like a low yield.

```
fractal-wallpapers walk --family julia --roots 20 --batches 8
fractal-wallpapers walk --seeds my_locations.jsonl --neighborhood
```
