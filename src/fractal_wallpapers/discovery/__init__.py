"""Finding places worth rendering.

A walk descends from a seed, one rung at a time, keeping what survives the
structural gates and reframing onto the nuclei it passes. Nothing here judges a
picture: the gates are geometry, and the judgement is a seam ([`scoring`]):
`LocationScorer` reads each survivor through the shipped location head, and
`NullScorer` stands in under `--no-scoring`.

The module map is the package's `README.md`.
"""

from __future__ import annotations

from fractal_wallpapers.discovery.walk import Gates, Limits, Policy, Reframings, Walk

__all__ = ["Gates", "Limits", "Policy", "Reframings", "Walk"]
