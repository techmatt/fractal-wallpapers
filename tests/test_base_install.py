"""The one command a fresh clone runs first, held to the install it runs on.

`pip install -e .` buys the engine, the walk, the supply engine and the labeling
rig. It does not buy torch, deliberately — the `models` extra is two gigabytes
of CUDA wheels that a clone which only wants to render fractals should never pay
for. `fetch-weights` is what that clone runs before anything else, and `--check`
is how it finds out whether the release it is about to pull is complete.

Everything `--check` does is stdlib: read the manifest, stat a file, hash it.
But "this path is stdlib-only" is a property of an entire import graph, and one
constant imported from the wrong module is enough to lose it. It was lost
exactly that way: the roster of heads lived in `ship`, `ship` imports the model
code, and `--check` exited 1 with `ModuleNotFoundError: numpy` on the one
environment it exists to serve.

The property is only observable in a process that does not have the extra, so
the check is a subprocess with those imports refused at the meta path. Asserting
it in this interpreter would prove nothing: every machine that runs this suite
has torch installed, which is exactly how the defect survived to be shipped.
"""

from __future__ import annotations

import os
import subprocess
import sys

from fractal_wallpapers.paths import repo_root

#: What `pip install -e ".[models]"` adds, and therefore what a base install
#: does without. Refusing the top-level names refuses their submodules too.
BLOCKED = ("numpy", "torch", "torchvision", "timm", "PIL")

GUARD = '''"""Import as a base install would, then do what the argument says."""

import sys

BLOCKED = {blocked!r}


class BaseInstall:
    """Refuse the models extra, the way an interpreter without it would."""

    def find_spec(self, name, path=None, target=None):
        top = name.partition(".")[0]
        if top in BLOCKED:
            raise ModuleNotFoundError(f"No module named {{top!r}}")
        return None


sys.meta_path.insert(0, BaseInstall())

if sys.argv[1] == "check":
    from fractal_wallpapers import cli

    raise SystemExit(cli.main(["fetch-weights", "--check"]))

__import__(sys.argv[1])
'''


def run_without_the_extra(tmp_path, argument: str) -> subprocess.CompletedProcess:
    """Run one thing in a fresh interpreter that cannot import the models extra."""
    script = tmp_path / "base_install.py"
    script.write_text(GUARD.format(blocked=frozenset(BLOCKED)), encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-B", str(script), argument],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(repo_root() / "src")},
    )


def test_the_refusal_is_real(tmp_path) -> None:
    """Otherwise the guard below passes on a machine where nothing is refused,
    which is every machine this suite runs on."""
    result = run_without_the_extra(tmp_path, "numpy")
    assert result.returncode != 0
    assert "ModuleNotFoundError" in result.stderr


def test_the_check_runs_without_the_models_extra(tmp_path) -> None:
    """The whole `--check` path — roster, row completeness, files, sha256, bytes.

    It may well report gaps: a working tree that has not fetched its weights has
    no artifact to hash, and saying so is the command doing its job. What it may
    not do is fail to *run*, which is the only thing asserted here.
    """
    result = run_without_the_extra(tmp_path, "check")
    assert "Traceback" not in result.stderr, result.stderr
    assert result.returncode in (0, 1), result.stderr
    # Printed only after every row has been read, so reaching it is the proof
    # that the path ran to the end rather than dying somewhere quiet.
    assert "heads present" in result.stdout, result.stdout
