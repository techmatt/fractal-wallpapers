"""Finding places worth rendering.

A walk descends from a seed, one rung at a time, keeping what survives the
structural gates and reframing onto the nuclei it passes. Nothing here judges a
picture: the gates are geometry and the scorer that will judge is a seam
([`scoring`]) with a null implementation behind it today.

```text
pools      the tracked seed pools, and the spacing the Julia one has to keep
walk       the frontier, the batch, the reserved floors, the run loop
nucleus    Newton on a nucleus, the atom instrument, the canonical key
operators  reframing a found view onto the atoms around it
ledger     one JSONL record, one schema, a fate on every row
scoring    the seam a trained head arrives through
```
"""

from __future__ import annotations

from fractal_wallpapers.discovery.walk import Gates, Limits, Policy, Reframings, Walk

__all__ = ["Gates", "Limits", "Policy", "Reframings", "Walk"]
