"""Fixtures shared across the labeling tests.

The label store addresses one directory under the repository, deliberately: a
store whose location is a parameter is a store that gets written to twice. Tests
redirect that one function and get a whole empty store, which is also the
cheapest proof that everything really does address the records through it.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.labeling import registry as registry_module
from fractal_wallpapers.labeling import store


@pytest.fixture
def store_dir(tmp_path, monkeypatch):
    """An empty label store, and everything in the package pointed at it."""
    directory = tmp_path / "labels"
    monkeypatch.setattr(store, "label_dir", lambda: directory)
    return directory


@pytest.fixture
def registered(store_dir):
    """Register a batch and hand back the registry, for tests that need a writer."""

    def register(batch: str, **flags) -> dict:
        store.register(
            registry_module.Registration(
                batch=batch,
                method=flags.pop("method", "a draw, for a test"),
                **flags,
            )
        )
        return store.registry()

    return register
