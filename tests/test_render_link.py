"""`fractal-engine render-link`: its embedded link, and its picture against a release's.

Two claims, one per test:

* **The engine's embed is the Python writer's, byte for byte.** A picture `render-link`
  writes, taken back to the bytes its encoder wrote and stamped again by
  [`curation.embed_link`], is the file the engine wrote — for a PNG and a JPEG, over a
  link whose palette name and `level=` both need escaping.
* **A link draws its release picture within a tolerance.** A release render embeds its
  own link; `render-link` over that link, at the same size, draws the same picture to
  within a fraction of a code value. Byte identity is not the claim and is not
  promised: a levelled map is baked from unrounded stops here and from nine-decimal
  ones through the pipeline, which can move a byte at a rounding boundary. That is why
  this is its own test rather than a `link` door in `test_renderer_agreement.py`'s
  `RENDERERS`, whose one assertion is a single digest.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fractal_wallpapers import engine

try:
    ENGINE = engine.engine_path()
except FileNotFoundError:
    ENGINE = None

needs_engine = pytest.mark.skipif(ENGINE is None, reason="the engine is not built")

#: A seat's link with a comma and spaces in its palette name and a replayed curve, and
#: one with neither: the two encoders and the two metadata payload shapes.
LINKS = (
    "v=4&m=smooth&x=-0.7612572175676096&y=-0.08419961869150334&w=0.0001808092935632228"
    "&n=4000&p=Oxblood%2C%20Cyan%2C%20Cream"
    "&level=band_autolevel/v1:0.03,0.91,1.2,0.02,0.95",
    "v=4&f=julia&cx=-0.07810228973371881&cy=-0.6514609012382414&m=stripe&p=viridis",
)


@needs_engine
@pytest.mark.parametrize("suffix", [".png", ".jpg"])
@pytest.mark.parametrize("link", LINKS)
def test_the_engine_embeds_what_the_python_writer_does(tmp_path: Path, link, suffix) -> None:
    from fractal_wallpapers.curation import embed_link

    picture = tmp_path / f"link{suffix}"
    report = engine.render_link(link, (64, 36), picture, supersample=1)
    written = picture.read_bytes()
    assert embed_link.link_in(written) == report["link"]
    assert report["url"] == embed_link.url_of(report["link"])
    assert embed_link.embed(embed_link.strip(written), report["link"]) == written


def _pixels(picture: Path):
    import numpy
    from PIL import Image

    with Image.open(picture) as image:
        return numpy.asarray(image.convert("RGB"), dtype=numpy.int16)


#: The release cases: a levelled field mode under a moved palette, a composite whose
#: weight the link carries as its settled value, and a varied direct trap.
RELEASE_CASES = {
    "levelled": ("smooth", {}, {"phase": 0.37, "cycles": 2.0}),
    "composite": ("smooth_mean_angle", {}, None),
    "varied": ("direct_trap_multiply", {"opacity": 0.6, "threshold": 0.2}, None),
}

#: How far apart the two may land, out of 255 per channel: the mean over every pixel
#: and channel, and the 99th percentile. Measured at 0 and 0 on 2026-09-25; the bounds
#: are what a rounding-boundary byte could cost and nothing a real disagreement fits in.
MEAN_TOLERANCE = 0.05
P99_TOLERANCE = 1


@needs_engine
@pytest.mark.slow
@pytest.mark.parametrize("case", sorted(RELEASE_CASES))
def test_a_link_draws_its_release_picture_within_a_tolerance(tmp_path: Path, case) -> None:
    import numpy

    from fractal_wallpapers.curation import colorize, embed_link, release
    from fractal_wallpapers.labeling import finished

    mode, settings, palette = RELEASE_CASES[case]
    colormap = "viridis"
    if palette is not None:
        palette = finished.recipe(mirror=colormap not in colorize.cyclic(), **palette)
    released = tmp_path / "release.png"
    task = release.task_for(
        id=case,
        row={
            "family": {"kind": "mandelbrot"},
            "viewport": {
                "center_re": "-0.7612572175676096",
                "center_im": "-0.08419961869150334",
                "width": "0.0001808092935632228",
            },
        },
        mode=mode,
        colormap=colormap,
        mode_params=settings,
        curve=None,
        palette=palette,
        autolevel=None,
        output=released,
        geometry={"resolution": [320, 180], "supersample": 2, "maxiter": 4000},
    )
    result = release.render_task(task)
    assert result.ok, result.error
    link = embed_link.link_in(released.read_bytes())
    assert link, result.info.get("link_refused")

    drawn = tmp_path / "link.png"
    report = engine.render_link(link, (320, 180), drawn, supersample=2)
    assert report["link"] == link, "the release's link is already canonical"
    apart = numpy.abs(_pixels(released) - _pixels(drawn))
    mean, p99 = float(apart.mean()), float(numpy.percentile(apart, 99))
    assert mean <= MEAN_TOLERANCE and p99 <= P99_TOLERANCE, (
        f"{case}: {link} draws {mean:.3f} mean, {p99:.0f} p99 away from its release"
    )
