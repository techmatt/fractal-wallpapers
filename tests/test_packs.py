"""Wallpaper packs: the plan, the names, the refusal and the zip, over a toy full set."""

from __future__ import annotations

import hashlib
import json
import zipfile

import pytest

from fractal_wallpapers.curation import packs, targets, tentative

HUES = ("rose", "red")


@pytest.fixture
def full(tmp_path, monkeypatch):
    """A full set of 10 general seats and two 4-seat colour collections, half rendered."""
    monkeypatch.setattr(targets, "families", lambda: HUES)
    directory = tmp_path / "full"
    directory.mkdir()
    rows, recipes = [], {}
    for collection, count in (("general", 10), ("general_n2000", 3), *((h, 4) for h in HUES)):
        for order in range(count):
            key = f"{collection[:3]}{order:013d}"
            rows.append({"collection": collection, "stamp": collection, "order": order, "key": key})
            recipes[key] = {"colormap": f"map-{order % 2}", "family": {"kind": "mandelbrot"}}
    (directory / "membership.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    monkeypatch.setattr(tentative, "read_recipes", lambda stamp: recipes)
    names = tmp_path / "names.json"
    names.write_text(json.dumps({"map-0": {"name": "Violet Bluebell"}}), encoding="utf-8")
    return directory, names


def render(directory, keys):
    for key in keys:
        (directory / f"{key}.jpg").write_bytes(f"jpeg {key}".encode())


@pytest.mark.parametrize(
    ("family", "name"),
    [
        ({"kind": "mandelbrot"}, "Mandelbrot"),
        ({"kind": "multibrot", "degree": 3}, "Cubic Multibrot"),
        ({"kind": "julia", "degree": 2}, "Julia"),
        ({"kind": "julia", "degree": 4}, "Quartic Julia"),
        ({"kind": "julia", "degree": 6}, "Sextic Julia"),
        ({"kind": "phoenix", "c": ["0.5667", "0.0"]}, "Phoenix"),
    ],
)
def test_plane_names(family, name):
    assert packs.plane_name(family) == name


def test_plan_cuts_nests_and_is_seeded(full):
    directory, _ = full
    plan = {pack.name: pack for pack in packs.plan(directory)}
    parts = [plan[f"general-{n}-of-3"] for n in (1, 2, 3)]
    assert [len(part.keys) for part in parts] == [4, 3, 3]
    assert [part.first_rank for part in parts] == [1, 5, 8]
    assert {part.width for part in parts} == {2}
    ranked = [key for part in parts for key in part.keys]
    assert sorted(ranked) == sorted(f"gen{n:013d}" for n in range(10))
    assert ranked == packs.seeded(sorted(ranked), packs.SEED)
    # Best-K is the head of the same order (the toy set is smaller than every K).
    assert plan["best-30"].keys == ranked
    assert plan["best-30"].width == 2
    assert plan["rose"].seed == f"{packs.SEED}/rose"
    assert "general_n2000" not in {pack.collection for pack in plan.values()}
    assert [pack.keys for pack in packs.plan(directory)] == [pack.keys for pack in plan.values()]


def test_order_file_replaces_the_draw_and_must_be_whole(full, tmp_path):
    directory, _ = full
    keys = [f"gen{n:013d}" for n in reversed(range(10))]
    order = tmp_path / "order.txt"
    order.write_text("\n".join(keys) + "\n", encoding="utf-8")
    plan = {pack.name: pack for pack in packs.plan(directory, order)}
    assert plan["general-1-of-3"].keys == keys[:4]
    assert plan["general-1-of-3"].order_from == "order.txt"
    order.write_text("\n".join(keys[:9]) + "\n", encoding="utf-8")
    with pytest.raises(packs.PacksRefused, match="1 absent"):
        packs.plan(directory, order)


def test_incomplete_refuses_unless_partial(full, tmp_path):
    directory, names = full
    render(directory, [f"ros{n:013d}" for n in range(2)])
    out = tmp_path / "packs"
    with pytest.raises(packs.PacksRefused, match="rose lacks 2"):
        packs.build(directory, out, only=["rose"], names_path=names, log=lambda _: None)
    assert not out.exists()
    done = packs.build(
        directory, out, only=["rose"], names_path=names, allow_partial=True, log=lambda _: None
    )
    assert done["built"] == ["fractal-wallpapers-rose-trial-partial.zip"]
    entry = json.loads((out / packs.MANIFEST_NAME).read_text("utf-8"))["packs"][0]
    assert (entry["pack"], entry["pictures"], entry["of"], entry["complete"]) == (
        "rose-trial-partial",
        2,
        4,
        False,
    )


def test_zip_stores_pictures_byte_for_byte(full, tmp_path):
    directory, names = full
    render(directory, [f"gen{n:013d}" for n in range(10)])
    out = tmp_path / "packs"
    done = packs.build(
        directory, out, only=["general-2-of-3"], names_path=names, log=lambda _: None
    )
    assert done["unnamed_palettes"] == ["map-1"]
    path = out / "fractal-wallpapers-general-2-of-3.zip"
    entry = json.loads((out / packs.MANIFEST_NAME).read_text("utf-8"))["packs"][0]
    assert entry["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    with zipfile.ZipFile(path) as bundle:
        infos = bundle.infolist()
        pictures = [info for info in infos if info.filename.endswith(".jpg")]
        assert [info.filename.split("/")[1][:3] for info in pictures] == ["05 ", "06 ", "07 "]
        assert all(info.compress_type == zipfile.ZIP_STORED for info in pictures)
        for info, key in zip(pictures, entry["seats"], strict=True):
            assert bundle.read(info) == (directory / f"{key}.jpg").read_bytes()
            assert info.filename.endswith(
                (" Violet Bluebell Mandelbrot.jpg", " map-1 Mandelbrot.jpg")
            )
        readme = bundle.read("fractal-wallpapers-general-2-of-3/README.txt").decode("utf-8")
    assert packs.SITE in readme and "CC BY 4.0" in readme and "ranks 5 to 7 of 10" in readme
