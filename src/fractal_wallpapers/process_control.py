"""Platform-specific process handling, isolated to this one module.

Long render sweeps spawn many engine processes, and on Windows that needs job
objects (so children die with the parent) and priority classes (so a sweep
does not make the desktop unusable). Those calls live here and nowhere else,
so the rest of the package stays plain cross-platform Python.
"""

from __future__ import annotations

import sys

IS_WINDOWS = sys.platform == "win32"


def set_background_priority() -> None:
    """Drop the current process to a below-normal priority class."""
    raise NotImplementedError("priority control is not implemented yet")


def bind_children_to_parent() -> None:
    """Ensure spawned engine processes exit when this process exits."""
    raise NotImplementedError("child process binding is not implemented yet")
