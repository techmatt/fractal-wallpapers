"""The explorer link a release render carries: spelled as the site spells it, written into
the file's metadata, and the picture untouched.

The spelling is held to the site's own contract by `fractal-website`'s `builder check`
(`stamps`), over a thousand real seats; what is held here is what needs no second
checkout — the number and URL encodings, the refusals, and the bytes.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from fractal_wallpapers.curation import embed_link, explorer_link, release

QUERY = (
    "v=4&f=julia&cx=-1.2540170796954613&cy=-0.07161459637319667&m=tia"
    "&x=-0.336363658629224&y=-0.06271709146615745&w=0.5659066537374874"
    "&p=Oxblood%2C%20Cyan%2C%20Cream&phase=0.597858"
)
DEEP = (
    "dv=3&f=multibrot4&x=0.462137566635993966&y=0.637160777512752593&w=2.95e-16&n=67810&p=gemini-25"
)


def picture(kind: str) -> bytes:
    image = Image.new("RGB", (40, 23))
    image.putdata(
        [((x * 37) % 256, (y * 53) % 256, (x * y * 11) % 256) for y in range(23) for x in range(40)]
    )
    held = io.BytesIO()
    image.save(held, format=kind, **({"quality": 90} if kind == "JPEG" else {}))
    return held.getvalue()


def pixels(data: bytes) -> bytes:
    return Image.open(io.BytesIO(data)).convert("RGB").tobytes()


# ------------------------------------------------------------------ the spelling
@pytest.mark.parametrize(
    ("value", "written"),
    [
        (0.0, "0"),
        (100.0, "100"),
        (0.1, "0.1"),
        (-2.5, "-2.5"),
        (1e-7, "1e-7"),
        (1.5e-7, "1.5e-7"),
        (0.000001, "0.000001"),
        (1e21, "1e+21"),
        (1.2345e21, "1.2345e+21"),
        (123456789012345680000.0, "123456789012345680000"),
        (0.597858, "0.597858"),
        (0.30000000000000004, "0.30000000000000004"),
    ],
)
def test_a_number_is_written_the_way_javascript_writes_it(value, written) -> None:
    assert explorer_link.js_number(value) == written


def test_encoding_is_encode_uri_component_with_the_colon_left_alone() -> None:
    assert explorer_link.encode("Oxblood, Cyan, Cream") == "Oxblood%2C%20Cyan%2C%20Cream"
    assert explorer_link.encode("edge:0.3") == "edge:0.3"
    # The `+` of an exponent is encoded: raw, a query string reads it as a space.
    assert explorer_link.encode("1e+21") == "1e%2B21"
    assert explorer_link.encode("a-b_c.d!e~f*g'h(i)j") == "a-b_c.d!e~f*g'h(i)j"
    assert explorer_link.encode_curve("band_autolevel/v1:0.1,0.9") == "band_autolevel/v1:0.1,0.9"


def test_the_link_names_the_family_the_explorer_does() -> None:
    name = explorer_link.family_name
    assert name({"kind": "multibrot", "degree": 2}) == "mandelbrot"
    assert name({"kind": "multibrot", "degree": 4}) == "multibrot4"
    assert name({"kind": "julia", "degree": 2}) == "julia"
    assert name({"kind": "julia", "degree": 5}) == "julia5"
    assert name({"kind": "phoenix_m"}) == "phoenix_plane"
    assert name({"kind": "multibrot", "degree": 7}) is None
    assert name({"kind": "multibrot", "degree": 2.5}) is None


def test_a_curve_the_operator_did_not_move_the_picture_with_is_not_carried() -> None:
    curve = {"applies": True, "identity": False, "black_pt": 0.1, "white_pt": 0.9,
             "exponent": 1.2, "out_ends": [0.05, 0.95]}  # fmt: skip
    stamp = {"operator": "band_autolevel/v1", "curve": curve}
    assert explorer_link.level_of(stamp)["exponent"] == 1.2
    assert explorer_link.level_of(None) is None
    assert explorer_link.level_of({**stamp, "curve": {**curve, "identity": True}}) is None
    assert explorer_link.level_of({**stamp, "curve": {**curve, "applies": False}}) is None


@pytest.fixture
def engine_free(monkeypatch):
    """The three engine answers `query_of` asks, stated, so the spelling is tested alone."""
    from fractal_wallpapers import engine, engine_spec

    monkeypatch.setattr(
        engine, "home_view", lambda family: {"center_re": "-0.5", "center_im": "0", "width": "3"}
    )
    monkeypatch.setattr(engine, "maxiter_for", lambda widths: [1000 for _ in widths])
    monkeypatch.setattr(
        engine_spec,
        "catalog",
        lambda: {
            "smooth": {"kind": "field"},
            "trap_circle": {"kind": "field", "transform": "log"},
            "smooth_mean_angle": {"kind": "composite", "texture_weight": 0.85},
        },
    )


def spelled(**changes):
    view = {
        "family": {"kind": "multibrot", "degree": 3},
        "viewport": {"center_re": "0.25", "center_im": "-0.5", "width": "0.001"},
        "maxiter": 1000,
        "mode": "smooth",
        "mode_params": {},
        "curve": "linear",
        "colormap": "Gold Field, Blood Spark",
        "palette": None,
        "level": None,
    }
    view.update(changes)
    return explorer_link.query_of(**view)


def test_a_view_is_spelled_in_contract_order_and_defaults_are_left_out(engine_free) -> None:
    assert spelled() == (
        "v=4&f=multibrot3&x=0.25&y=-0.5&w=0.001&p=Gold%20Field%2C%20Blood%20Spark",
        None,
    )
    query, _ = spelled(
        maxiter=5000,
        palette={"gamma": 0.5, "mirror": True, "transfer": {"kind": "edge", "weight": 2.0}},
        level={
            "operator": "band_autolevel/v1",
            "black_pt": 0.1,
            "white_pt": 0.9,
            "exponent": 1.0,
            "out_ends": [0.0, 1.0],
        },  # fmt: skip
    )
    assert query.endswith(
        "&w=0.001&n=5000&p=Gold%20Field%2C%20Blood%20Spark&gamma=0.5&mirror=1"
        "&transfer=edge:2&level=band_autolevel/v1:0.1,0.9,1,0,1"
    )


def test_a_derived_parameter_is_written_at_the_catalogs_constant(engine_free) -> None:
    query, _ = spelled(mode="smooth_mean_angle")
    assert "&m=smooth_mean_angle&weight=0.85&" in query
    query, _ = spelled(mode="smooth_mean_angle", mode_params={"texture_weight": 0.4})
    assert "&weight=0.4&" in query


@pytest.mark.parametrize(
    ("changes", "said"),
    [
        ({"family": {"kind": "fractional_multibrot", "degree": 2.5}}, "not one the explorer draws"),
        ({"mode": "tail_itinerary"}, "not one the explorer offers"),
        ({"curve": "log"}, "no key of a link can say"),
        ({"mode": "trap_circle", "curve": "linear"}, "no key of a link can say"),
        ({"mode_params": {"density": 2.0}}, "which a link cannot spell"),
        ({"maxiter": 20}, "outside what a link may name"),
    ],
)
def test_a_picture_no_link_draws_exactly_gets_a_reason_and_no_link(engine_free, changes, said):
    query, why = spelled(**changes)
    assert query is None
    assert said in why


# -------------------------------------------------------------------- the bytes
@pytest.mark.parametrize("kind", ["PNG", "JPEG"])
def test_an_embedded_picture_is_the_same_picture_and_carries_the_link(kind) -> None:
    raw = picture(kind)
    embedded = embed_link.embed(raw, QUERY)
    assert pixels(embedded) == pixels(raw)
    assert embed_link.strip(embedded) == raw
    assert embed_link.link_in(embedded) == QUERY
    url = explorer_link.url_of(QUERY)
    held = Image.open(io.BytesIO(embedded))
    if kind == "PNG":
        assert held.text["fractal-explorer"] == f"fractal-explorer {QUERY}"
        assert embed_link.source_of(held.text["XML:com.adobe.xmp"]) == url
    else:
        assert held.getexif()[270] == url
        assert embed_link.source_of(held.info["xmp"].decode()) == url
        assert held.info["comment"] == f"fractal-explorer {QUERY}".encode()


@pytest.mark.parametrize("kind", ["PNG", "JPEG"])
def test_embedding_twice_leaves_one_link_and_the_last_one(kind) -> None:
    once = embed_link.embed(picture(kind), QUERY)
    twice = embed_link.embed(once, DEEP)
    assert embed_link.link_in(twice) == DEEP
    assert embed_link.embed(twice, DEEP) == twice
    assert embed_link.strip(twice) == picture(kind)


def test_somebody_elses_exif_is_kept_and_ours_goes_without() -> None:
    held = io.BytesIO()
    image = Image.open(io.BytesIO(picture("JPEG")))
    exif = image.getexif()
    exif[270] = "A camera wrote this"
    image.save(held, format="JPEG", quality=90, exif=exif)
    embedded = embed_link.embed(held.getvalue(), QUERY)
    assert Image.open(io.BytesIO(embedded)).getexif()[270] == "A camera wrote this"
    assert embed_link.link_in(embedded) == QUERY


def test_bytes_that_are_neither_are_refused() -> None:
    with pytest.raises(embed_link.EmbedRefused):
        embed_link.embed(b"GIF89a", QUERY)


# ------------------------------------------------------------------ the writer
def test_a_release_render_goes_out_with_its_link_in_it(monkeypatch, tmp_path) -> None:
    """The seam: `render_task` writes the link into the picture `colorize.render` made,
    and says what it wrote; a picture no link draws goes out as rendered, with the reason."""
    from fractal_wallpapers.curation import colorize

    raw = picture("PNG")

    def render(row, mode, colormap, cyclic, output, **rest):
        Path(output).write_bytes(raw)
        return Path(output), None

    monkeypatch.setattr(colorize, "render", render)
    monkeypatch.setattr(explorer_link, "for_task", lambda task, stamp: (QUERY, None))
    task = release.Task(id="a", row={}, colormap="x", mode="smooth",
                        output=str(tmp_path / "a.png"), geometry={})  # fmt: skip
    result = release.render_task(task)
    assert result.ok
    assert result.info["link"] == explorer_link.url_of(QUERY)
    written = (tmp_path / "a.png").read_bytes()
    assert embed_link.link_in(written) == QUERY
    assert pixels(written) == pixels(raw)

    monkeypatch.setattr(explorer_link, "for_task", lambda task, stamp: (None, "no such mode"))
    result = release.render_task(task)
    assert result.ok
    assert result.info["link"] is None
    assert result.info["link_refused"] == "no such mode"
    assert (tmp_path / "a.png").read_bytes() == raw
