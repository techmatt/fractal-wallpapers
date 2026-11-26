"""`python -m fractal_wallpapers.cli`: the package's entry under `-m`.

A module answers that invocation with its own `__main__` guard; a package
answers it with this file and nothing else, so the split needed it to keep the
documented spelling working.
"""

from __future__ import annotations

from fractal_wallpapers.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
