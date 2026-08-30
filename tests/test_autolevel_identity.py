"""The autolevel operator's output is pinned, byte for byte, through the real path.

`autolevel` re-renders a candidate through a colormap it re-bakes from the tone
band, and the band's own sha256 is part of the recipe key — so the picture a
recipe key names is only well-defined while the operator's arithmetic is fixed.
A change that moved a levelled stop in its last digit would rename nothing and
silently make the candidate ledger's byte-identity property false.

So this is the guard an optimisation of that stage is allowed to run against:
**every mode [`autolevel.applies_to`] says yes to**, drawn at a real candidate
geometry, and pinned twice over — the levelled colormap the operator wrote, and
the picture that came back through it. The colormap is the intermediate; the
picture is the contract, and both are here because a route can reproduce one
without the other.

**What is measured is what the encoder wrote, not what the renderer held.**
Supersampling and JPEG both average colour *after* the colormap lookup, so the
pixels this stage reads have been through the resample filter and a lossy
encoder. Measured on twenty-four real candidates recoloured to both formats, the
JPEG round trip moves all three statistics on every one of them and moves the
levelled stop list itself on seventeen — so a route that reads the engine's
pre-encode buffer is measuring a different picture, and this test is what says
so out loud.

The set is the *tracked* half of the evidence. The optimisation that made it necessary
was also run as a differential against its own predecessor over 2,500 real candidates
from a production depth run, 1,320 of them firing, with every statistic, curve and
levelled stop list identical — but a sweep of an artifact directory is not a guard, and
this is.

Slow lane, and it needs a **release** engine: it is thirty-odd renders.
"""

from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor

import pytest

from fractal_wallpapers import engine
from fractal_wallpapers.coloring import autolevel
from fractal_wallpapers.coloring import band as band_module
from fractal_wallpapers.curation import colorize, release
from fractal_wallpapers.models import renders

try:
    ENGINE = engine.engine_path()
except FileNotFoundError:
    ENGINE = None

needs_engine = pytest.mark.skipif(ENGINE is None, reason="the engine is not built")

#: The band these digests were taken under. A re-derived band is a new decision
#: about what the operator does to every render — `coloring.band` says so — and
#: it is therefore a new set of expected digests rather than a test to relax.
BAND_SHA256 = "49d4f43b200904c5967df788308834be163698081d85802df978554261aa63a1"

#: The geometry every probe is drawn at. Supersampled, because the resample
#: filter is half of what makes the measured pixels not the rendered ones.
RESOLUTION = (480, 270)
SUPERSAMPLE = 2

#: The pinned set: real locations off a production draw, two per mode, each
#: through a map the same draw spent. `acted` says whether the operator fired —
#: both answers are worth pinning, because an identity row and a levelled row
#: leave by different doors, and `leveled` is the map it re-baked where it did.
PROBES: tuple[dict, ...] = (
    {
        "family": {
            "c": ["0.2995601657228102", "-0.024825619193795445"],
            "degree": 2,
            "kind": "julia",
        },
        "viewport": {
            "center_re": "-0.436866950370211",
            "center_im": "0.23054661143294045",
            "width": "0.12305352558744842",
        },
        "maxiter": 9529,
        "mode": "smooth",
        "colormap": "Faded Salon",
        "acted": True,
        "picture": "8eb77f2820c09d21513f77ebba26752f0a483a27737711b2068727e3ac58f596",
        "leveled": "a6d196ea20f22032dd636b38c1408997f36e541d842cf88049e9154dc2eb8013",
    },
    {
        "family": {
            "c": ["-0.7486548983277147", "0.045059269407464055"],
            "degree": 2,
            "kind": "julia",
        },
        "viewport": {
            "center_re": "-0.30936643768751393",
            "center_im": "-0.17443292954695358",
            "width": "0.13117225095173557",
        },
        "maxiter": 9418,
        "mode": "smooth",
        "colormap": "wallhaven_wallhaven-d6yv9m",
        "acted": True,
        "picture": "0a401719e7cbd9541072fedcee854f7dc479e994d5a2a50db1298b19523d8c3c",
        "leveled": "2074593a4da7d4d46985fdfb2a3b2928ca8de3b4c8c32ea7ef1545b4646624e9",
    },
    {
        "family": {
            "c": ["0.2995601657228102", "-0.024825619193795445"],
            "degree": 2,
            "kind": "julia",
        },
        "viewport": {
            "center_re": "-0.436866950370211",
            "center_im": "0.23054661143294045",
            "width": "0.12305352558744842",
        },
        "maxiter": 9529,
        "mode": "tia",
        "colormap": "Foam Over Indigo",
        "acted": False,
        "picture": "1311da2afd0acd7c2b174d5add051e6a682fd511578c73958b5cc2145b745eb3",
    },
    {
        "family": {
            "c": ["-0.4748679270492898650099865018", "0.05403771977037510058618831149"],
            "degree": 3,
            "kind": "julia",
        },
        "viewport": {
            "center_re": "0.5501634702635906",
            "center_im": "0.32795735114373326",
            "width": "0.23634193343617468",
        },
        "maxiter": 8399,
        "mode": "tia",
        "colormap": "mossy-25",
        "acted": False,
        "picture": "8f9727f27eaaeeceb5b3a8f57a3878d5b72404f6b85144fbd018882b930bb6e6",
    },
    {
        "family": {
            "c": ["0.15672426598054978", "0.8134251857082828"],
            "degree": 3,
            "kind": "julia",
        },
        "viewport": {
            "center_re": "-0.5780337160750894",
            "center_im": "-0.28873775442209737",
            "width": "0.40260614509906184",
        },
        "maxiter": 7477,
        "mode": "stripe",
        "colormap": "metal-emblem-25",
        "acted": False,
        "picture": "c56f2990a4c7b107fd0294db27c6204bf3d63a06183d74e9911b038f255ba247",
    },
    {
        "family": {
            "c": ["-0.4748679270492898650099865018", "0.05403771977037510058618831149"],
            "degree": 3,
            "kind": "julia",
        },
        "viewport": {
            "center_re": "0.4891714915603066",
            "center_im": "0.3014885911864699",
            "width": "0.03668435720134815",
        },
        "maxiter": 11624,
        "mode": "stripe",
        "colormap": "Ember Standard",
        "acted": False,
        "picture": "1a30f14625636edf81e75c79dacffe89a24b08f515bdeaa637af2b4efc41262b",
    },
    {
        "family": {
            "c": ["-0.818454065630246", "-0.11468747249463887"],
            "degree": 4,
            "kind": "julia",
        },
        "viewport": {
            "center_re": "0.4068494938362181",
            "center_im": "-0.24881606866309142",
            "width": "0.0037220135512530963",
        },
        "maxiter": 15585,
        "mode": "exp_smoothing",
        "colormap": "embrace-25",
        "acted": True,
        "picture": "4e68cb228c24829ab20b2fe5c467925135df99633bfb415512fffadc23ddd0fa",
        "leveled": "0970c52f89ae37f2566f0b29f138edd0ca15b6b42071dfb8f310179a1ee6046a",
    },
    {
        "family": {
            "c": ["-0.818454065630246", "-0.11468747249463887"],
            "degree": 4,
            "kind": "julia",
        },
        "viewport": {
            "center_re": "0.4068494938362181",
            "center_im": "-0.24881606866309142",
            "width": "0.0037220135512530963",
        },
        "maxiter": 15585,
        "mode": "exp_smoothing",
        "colormap": "technology-25",
        "acted": True,
        "picture": "abf599ff8cacf4e66be5c8778778da03bae560d7230cd207b0bf2555248c9c33",
        "leveled": "37ef643940f99a5f46d7e030ed24ef68cf224197eaa051e60644983d8b6f708e",
    },
    {
        "family": {
            "c": ["0.31091863418755555", "0.7724735098244783"],
            "degree": 4,
            "kind": "julia",
        },
        "viewport": {
            "center_re": "-0.05991504488791758",
            "center_im": "0.6229703186357396",
            "width": "0.025757646202994346",
        },
        "maxiter": 12236,
        "mode": "gaussian_int",
        "colormap": "Faded Salon",
        "acted": False,
        "picture": "259474bf114dbd30842c7b6e02914a6176743500d74bdb866e1e4cf2cf4edd7c",
    },
    {
        "family": {
            "c": ["0.15883729018125314", "0.6965037043819076"],
            "degree": 5,
            "kind": "julia",
        },
        "viewport": {
            "center_re": "-0.10519119652290315",
            "center_im": "0.02217615955456713",
            "width": "1.818774366946878",
        },
        "maxiter": 4866,
        "mode": "gaussian_int",
        "colormap": "wallhaven_wallhaven-d6yv9m",
        "acted": True,
        "picture": "5b3f9456fbf00a8cacff2d01ebd8f11fcc9a9aabee2bcafe0bb34db32ec91f03",
        "leveled": "a448f426fc19627ac1fdfa4fdae43c0ca741114aa53fa87f5ffe1b0eb1a3e030",
    },
    {
        "family": {"c": ["0.5127583652571049", "0.616143424236027"], "degree": 5, "kind": "julia"},
        "viewport": {
            "center_re": "-0.07086541776839363",
            "center_im": "0.5753202740873946",
            "width": "0.784552629976848",
        },
        "maxiter": 6322,
        "mode": "trap_circle",
        "colormap": "Foam Over Indigo",
        "acted": True,
        "picture": "331256e8437d5a8b368ef3edeab84708d857d7f83347c400fae83f27bd30ef23",
        "leveled": "2e014af7ae6fd740c33c6104aeb55c6c024f392e4a4419d017d6295b527ee065",
    },
    {
        "family": {"c": ["0.5129098720104551", "0.6160557674891126"], "degree": 5, "kind": "julia"},
        "viewport": {
            "center_re": "-0.1691379470959805",
            "center_im": "0.6575736185236963",
            "width": "0.6742730016507726",
        },
        "maxiter": 6584,
        "mode": "trap_circle",
        "colormap": "mossy-25",
        "acted": True,
        "picture": "cf8fdd11ea034221bd6a98f1c93ad153009eba97c490def1596bbc8dd1ff55a4",
        "leveled": "76fac313e7e0294f3969abab97dee81ea6638a27c0031fb67da567114c6c262e",
    },
    {
        "family": {"kind": "mandelbrot"},
        "viewport": {
            "center_re": "-0.7494228684735113",
            "center_im": "0.04144910645662158",
            "width": "0.000004328425856381971",
        },
        "maxiter": 27283,
        "mode": "curvature",
        "colormap": "metal-emblem-25",
        "acted": True,
        "picture": "1251ff99107b497e52e3921c8a0c6b9447f1b4724774d155886d5b44c34c6be7",
        "leveled": "411ad8107d952467c2b1e36c0ce863df978b596b944b11ba407b23688d0cf7a4",
    },
    {
        "family": {"kind": "mandelbrot"},
        "viewport": {
            "center_re": "-0.07810706326940536",
            "center_im": "-0.6514612049278983",
            "width": "0.000006487347737687225",
        },
        "maxiter": 26582,
        "mode": "curvature",
        "colormap": "Ember Standard",
        "acted": False,
        "picture": "c9815d7fb5142217803c5b9ba906f6ba9463511fb842ccb1fbca5debc697d549",
    },
    {
        "family": {"kind": "mandelbrot"},
        "viewport": {
            "center_re": "-1.1068697608234854",
            "center_im": "0.2310644465804754",
            "width": "0.000008349755989145383",
        },
        "maxiter": 26145,
        "mode": "de",
        "colormap": "embrace-25",
        "acted": True,
        "picture": "48b8d5648d86ca02f335887db5bb03df21b2691c3717c67c789a87e36bac4c42",
        "leveled": "eac8ca7cca4551f3066bf5008db9576e5e8b6a0307fc9379ea016b1404b5cda1",
    },
    {
        "family": {"degree": 3, "kind": "multibrot"},
        "viewport": {
            "center_re": "0.1734626796466219",
            "center_im": "0.7456723109163306",
            "width": "0.000000826641717773875",
        },
        "maxiter": 30149,
        "mode": "de",
        "colormap": "technology-25",
        "acted": True,
        "picture": "4e2f6388b39738757ff560f6f1fe3459fbfb82b750a7a85827b649aac8393861",
        "leveled": "668af99ba497237d70fa19a11d8da71180b69b1ab4a40429a7cdba38710a0edb",
    },
    {
        "family": {"degree": 3, "kind": "multibrot"},
        "viewport": {
            "center_re": "-0.0594926227428737",
            "center_im": "0.7687990088222284",
            "width": "0.0000016497229872342448",
        },
        "maxiter": 28953,
        "mode": "smooth_mean_angle",
        "colormap": "Faded Salon",
        "acted": True,
        "picture": "e1cc3a9ab4369afc5e28f353b0db90f56a3fbda56c54ab4383131b0315f8bbce",
        "leveled": "1a1efce47c97a6bff7b7e10e30027e7d1360a9ee354fd549b3cfbe9c1115f71c",
    },
    {
        "family": {"degree": 3, "kind": "multibrot"},
        "viewport": {
            "center_re": "-0.059493077804906036",
            "center_im": "0.7687991542168716",
            "width": "0.00000023714273848572532",
        },
        "maxiter": 32311,
        "mode": "smooth_mean_angle",
        "colormap": "wallhaven_wallhaven-d6yv9m",
        "acted": True,
        "picture": "ae7535cf13624451e0dc29493623c1f4acebf24291287a1d42f8d6789fe6af35",
        "leveled": "9b504e13754291ab5c99bb5ba0cc23b25f88659155d6e2015ac8cf950e6da3ec",
    },
    {
        "family": {"degree": 4, "kind": "multibrot"},
        "viewport": {
            "center_re": "0.046461800984962214",
            "center_im": "0.7413319682297884",
            "width": "0.000043833267918172875",
        },
        "maxiter": 23275,
        "mode": "smooth_angle_min",
        "colormap": "Foam Over Indigo",
        "acted": False,
        "picture": "243eb809571ce55734c46b8d4782c529334586d8667a56acc2be56a6af8f762b",
    },
    {
        "family": {"degree": 4, "kind": "multibrot"},
        "viewport": {
            "center_re": "0.04841171009369742",
            "center_im": "0.7412659930753782",
            "width": "0.000000023151215225214605",
        },
        "maxiter": 36339,
        "mode": "smooth_angle_min",
        "colormap": "mossy-25",
        "acted": True,
        "picture": "259847aad91738a45175d672b1a8f2606f619df968bf544193b823f46b5fac76",
        "leveled": "2b2c77bf90b79a87b9bdcebba639918620d2da61b26c0cd841be9707a0ef671b",
    },
    {
        "family": {"degree": 4, "kind": "multibrot"},
        "viewport": {
            "center_re": "0.16294676798820665",
            "center_im": "0.7509857653033828",
            "width": "0.00047143152535962486",
        },
        "maxiter": 19162,
        "mode": "smooth_trap_circle",
        "colormap": "metal-emblem-25",
        "acted": True,
        "picture": "c2d1a30aa2147bc6bd558d5bd9476e329d99d6f534ed91a155045bee1570c9d1",
        "leveled": "5770cc52e574248f10102720b2f3dfcbbe5228bf8aba00df525603a9d76ff169",
    },
    {
        "family": {"degree": 5, "kind": "multibrot"},
        "viewport": {
            "center_re": "0.23324607839064926",
            "center_im": "0.70411768085275",
            "width": "0.0000000000922730228782122",
        },
        "maxiter": 45904,
        "mode": "smooth_trap_circle",
        "colormap": "Ember Standard",
        "acted": True,
        "picture": "5be07d2505be5cfdc37d1e2508933c1855b6d461c1405efdd23cb9b27fbce0e3",
        "leveled": "938cedcde8d656f227804651c91bfadae8f6464afb3148a7e3db20a562bdb30c",
    },
    {
        "family": {"degree": 5, "kind": "multibrot"},
        "viewport": {
            "center_re": "0.2332460790925228",
            "center_im": "0.7041176816257577",
            "width": "0.0000000024694777502676774",
        },
        "maxiter": 40213,
        "mode": "smooth_stripe",
        "colormap": "embrace-25",
        "acted": True,
        "picture": "dad0b163249a9185a9065994c915db51dc569bfb8fb3ee6ff4de39443cf82d52",
        "leveled": "e8b8de4a3db516240d05649be8395b5844daf77b295ec1daea80e8e1b1637126",
    },
    {
        "family": {"degree": 5, "kind": "multibrot"},
        "viewport": {
            "center_re": "0.6680099407757032",
            "center_im": "0.5127901368169132",
            "width": "0.00615359321761275",
        },
        "maxiter": 14715,
        "mode": "smooth_stripe",
        "colormap": "technology-25",
        "acted": True,
        "picture": "8a40c031b83e58de0f979867990226eb1a5ae2ae042b3006469c57039e8bb06b",
        "leveled": "4fe104bf983dd9ef90ce62550d3f41a31fc6d79eb1d0873dc8ffd296f1db4b1a",
    },
    {
        "family": {
            "c": ["-0.27738015918203646", "-0.05834793381449761"],
            "kind": "phoenix",
            "p": ["0.3901718144336561", "-0.13182322668745225"],
            "z_prev": ["0.01686063935750582", "0.011320035842502742"],
        },
        "viewport": {
            "center_re": "-0.1533943673048909",
            "center_im": "-0.04329706920396079",
            "width": "0.01680074400561011",
        },
        "maxiter": 12976,
        "mode": "smooth_curvature",
        "colormap": "Faded Salon",
        "acted": True,
        "picture": "77a2e3f5261f25ab8adbc751f757f7c5253e666c5e54307c4f87f76aa93b69cd",
        "leveled": "5c7edf40a0de788e65ad3a87e3e3b895b50ef77219de26a45391afcd916160ce",
    },
    {
        "family": {
            "c": ["-0.27738015918203646", "-0.05834793381449761"],
            "kind": "phoenix",
            "p": ["0.3901718144336561", "-0.13182322668745225"],
            "z_prev": ["0.01686063935750582", "0.011320035842502742"],
        },
        "viewport": {
            "center_re": "0.5053325337532999",
            "center_im": "-0.29867451325784067",
            "width": "0.7726617066568294",
        },
        "maxiter": 6348,
        "mode": "smooth_curvature",
        "colormap": "wallhaven_wallhaven-d6yv9m",
        "acted": True,
        "picture": "7f83586bf0bd78b7f6e3ecf41bb1ad53c550458d313113412a551c5b0ff2d8fe",
        "leveled": "f2d1fa8c9e6902d5cb325f5278712323b75bec7caafe5f583e7886f31957001a",
    },
    {
        "family": {
            "c": ["0.5383514808287658", "0.3480859582688848"],
            "kind": "phoenix",
            "p": ["0.6099239902151401", "0.46174366575103293"],
            "z_prev": ["0.0", "0.0"],
        },
        "viewport": {
            "center_re": "-0.05513247500252275",
            "center_im": "0.9098724842113037",
            "width": "0.015569224679909763",
        },
        "maxiter": 13108,
        "mode": "threads",
        "colormap": "Foam Over Indigo",
        "acted": False,
        "picture": "17552b2fac4f9c0c2dcdbb94579c2906bd6686751720221280c4e2b187823794",
    },
    {
        "family": {
            "c": ["0.2995601657228102", "-0.024825619193795445"],
            "degree": 2,
            "kind": "julia",
        },
        "viewport": {
            "center_re": "-0.436866950370211",
            "center_im": "0.23054661143294045",
            "width": "0.12305352558744842",
        },
        "maxiter": 9529,
        "mode": "threads",
        "colormap": "mossy-25",
        "acted": True,
        "picture": "0bcdeceadab6a464d0ef1dd5e4b099053012d4c3adf6f22225fdc7adf8965076",
        "leveled": "acebf7a067c72385d43af60cf578787ace65607d059ddfa37f179503cb4dbf71",
    },
)


def _digest(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_pinned_set_spans_every_mode_the_operator_applies_to() -> None:
    """A new field or composite mode cannot arrive without a pin behind it.

    The coverage is the whole value of the set: an optimisation checked against
    `smooth` alone would say nothing about a composite, whose two layers reach
    the colormap by a different route and whose tone is the blend's.
    """
    catalog = renders.catalog()
    applies = {name for name, entry in catalog.items() if autolevel.applies_to(entry["kind"])}
    assert applies, "the catalog offered no mode the operator applies to"
    assert {probe["mode"] for probe in PROBES} == applies
    # And the levelled half is exercised, not just the identity half.
    assert sum(probe["acted"] for probe in PROBES) >= 10


def test_the_band_the_digests_were_taken_under_is_the_band_that_ships() -> None:
    """The digests are a function of the band, so the band is pinned beside them."""
    assert band_module.load()["_sha256"] == BAND_SHA256


@needs_engine
@pytest.mark.slow
def test_every_pinned_candidate_comes_back_byte_for_byte(tmp_path) -> None:
    """The whole contract, through `colorize.render` rather than around it.

    Not `maybe_level` on a picture from disk: the stage being guarded sits inside
    the candidate path, and a check that skipped the path could pass while the
    picture the path writes moved.
    """
    record = band_module.load()
    cyclic = colorize.cyclic()

    def check(index: int, probe: dict) -> None:
        name = f"{index:03d}_{probe['mode']}"
        row = {
            "family": probe["family"],
            "viewport": probe["viewport"],
            "maxiter": probe["maxiter"],
        }
        geometry = {
            "resolution": list(RESOLUTION),
            "supersample": SUPERSAMPLE,
            "maxiter": probe["maxiter"],
        }
        picture, stamp = colorize.render(
            row,
            probe["mode"],
            probe["colormap"],
            cyclic,
            tmp_path / f"{name}.jpg",
            render_geometry=geometry,
            level=True,
            band=record,
            fields=None,
        )
        acted = bool(stamp and stamp.get("acted"))
        assert acted == probe["acted"], f"{name}: the operator changed its mind about firing"
        assert _digest(picture) == probe["picture"], f"{name}: the picture moved"
        if acted:
            leveled = tmp_path / f"{name}.leveled" / f"{probe['colormap']}.json"
            assert _digest(leveled) == probe["leveled"], f"{name}: the levelled colormap moved"

    # One probe a worker, at the pool's own width. Every probe writes under its
    # own indexed name and `fields=None` means no cache is shared, so the only
    # thing the workers contend for is the engine — which is what the count is
    # about. Twenty-eight serial renders were 38.9 s on 2026-08-29.
    with ThreadPoolExecutor(max_workers=release.DEFAULT_WORKERS) as pool:
        list(pool.map(lambda pair: check(*pair), enumerate(PROBES)))
