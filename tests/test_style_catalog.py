"""The custom-mode catalog, the published modes' public knobs, and the page built from them."""

from __future__ import annotations

import json

import pytest
from tests.test_styles import tunnel

from fractal_wallpapers import cli, style_catalog, styles


def published():
    """The catalog's published rows."""
    return [row for row in style_catalog.load()["modes"] if row.get("status") == "publish"]


def test_the_catalog_holds_its_rows_and_agrees_with_the_styles():
    catalog = style_catalog.load()
    assert style_catalog.check(catalog) == []
    names = [row["style"] for row in catalog["modes"]]
    assert len(names) == len(set(names)) >= 14
    # A row with no status is one Matt has not ruled on yet.
    statuses = {row["status"] for row in catalog["modes"] if "status" in row}
    assert statuses <= set(style_catalog.STATUSES)


def test_a_round_one_row_has_neither_score_nor_status():
    """A style is catalogued as soon as its first picker exists, so its references stop
    reading as untried; a row with a status still needs its score."""
    catalog = style_catalog.load()
    row = next(row for row in catalog["modes"] if row.get("status") == "discarded")
    unscored = {key: value for key, value in row.items() if key not in ("score", "status")}
    others = [other for other in catalog["modes"] if other is not row]
    assert style_catalog.check({**catalog, "modes": [*others, unscored]}) == []
    assert row["reference"] in style_catalog.named_references({"modes": [unscored]})
    assert style_catalog.stars(None) == "unscored"
    ruled = {**unscored, "status": "discarded"}
    problems = style_catalog.check({**catalog, "modes": [*others, ruled]})
    assert problems == [f"{row['style']}: score None is not 1 to 5"]


#: Shown keeps whose record carries a projection member a knob writes, at a value outside
#: the knob's range, by (style, keep): a picture the page shows that no setting of its
#: own slider draws. `docs/qa-findings.md` has each; what to do is Matt's call.
#: Empty since 107 deleted `teal_tunnel`, the one mode that had one.
OUT_OF_RANGE_SHOWN: set[tuple[str, str]] = set()


@pytest.mark.parametrize("row", published(), ids=lambda row: row["style"])
def test_a_shown_keep_is_one_its_own_knobs_can_draw(row):
    document = styles.load(row["style"])
    for shown in style_catalog.shown_of(row):
        outside = outside_its_knobs(document, shown["location"])
        named = (row["style"], shown.get("keep"))
        assert bool(outside) == (named in OUT_OF_RANGE_SHOWN), outside


def outside_its_knobs(document: dict, location: dict) -> list[tuple[str, float]]:
    """Each knob whose projection member the location carries outside the knob's range."""
    place = location.get("projection") or {}
    outside = []
    for knob in (document.get("public") or {}).get("knobs") or []:
        for pointer in knob["set"]:
            if not isinstance(pointer, str):
                continue  # a scaled write's member is not on the knob's own scale
            steps = pointer.strip("/").split("/")
            if steps[0] != "projection" or len(steps) != 3:
                continue
            value = (place.get(steps[1]) or {}).get(steps[2])
            low, high = knob["range"]
            if value is not None and not low <= value <= high:
                outside.append((knob["name"], value))
    return outside


def test_a_record_past_its_knob_s_range_is_caught():
    """No published mode's knob writes a projection member since 107 (the guard above reads
    none), so its rule is held here on a log-polar stand-in: `turns` is 3 to 6."""
    document = tunnel()
    assert outside_its_knobs(document, {"projection": {"log_polar": {"turns": 8}}}) == [
        ("turns", 8)
    ]
    assert outside_its_knobs(document, {"projection": {"log_polar": {"turns": 4}}}) == []
    assert outside_its_knobs(document, {}) == []


def test_a_catalog_garbled_by_hand_is_refused_not_raised(tmp_path, monkeypatch):
    """The README sends a person into catalog.json to tune an entry's values; a typo
    there once raised a JSON traceback from the gallery, the bundle and every alias."""
    garbled = tmp_path / styles.CATALOG_FILE
    garbled.write_text('{"schema": 1, "modes": [', encoding="utf-8")
    with pytest.raises(style_catalog.CatalogError, match="not JSON"):
        style_catalog.load(garbled)
    monkeypatch.setattr(styles, "styles_dir", lambda: tmp_path)
    with pytest.raises(styles.StyleError, match="not JSON"):
        styles.catalog_rows()


def test_a_row_names_its_references_its_own_first_and_its_entries_among_them():
    row = {
        "reference": "a-25.jpg",
        "references": ["a-25.jpg", "b.jpg"],
        "palettes": [{"colormap": "m", "reference": "b.jpg"}],
    }
    assert style_catalog.check_references(row) == []
    assert style_catalog.check_references({**row, "references": "a-25.jpg"})
    assert style_catalog.check_references({**row, "references": ["b.jpg", "a-25.jpg"]})
    assert style_catalog.check_references({**row, "references": ["a-25.jpg", "a-25.jpg"]})
    assert style_catalog.check_references({**row, "references": ["a-25.jpg", "x/b.jpg"]})
    lost = {**row, "palettes": [{"colormap": "m", "reference": "c.jpg"}]}
    assert style_catalog.check_references(lost) == [
        "palette m's reference c.jpg is not in references"
    ]


def test_unused_references_are_the_triage_yes_rows_no_row_names(tmp_path):
    assert style_catalog.triage_id("commons_Chaos_Clock_-_The_Spell-Shaper.jpg") == (
        "commons_chaos_clock___the_spell_shaper"
    )
    assert style_catalog.triage_id("forest_00024_1.17e222.jpg") == "forest_00024_1_17e222"
    choices = tmp_path / "triage.choices.json"
    rows = [
        {"id": "fish_head_25", "key": "yes"},
        {"id": "gyre_25", "key": "yes"},
        {"id": "lethe_25", "key": "no"},
    ]
    choices.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    catalog = {"modes": [{"style": "soft_veils", "references": ["fish-head-25.jpg"]}]}
    assert style_catalog.unused_references(choices, catalog) == [
        {"id": "gyre_25", "file": "", "picture": ""}
    ]
    with pytest.raises(style_catalog.CatalogError):
        style_catalog.unused_references(tmp_path / "gone.json", catalog)


def test_unused_sheets_draw_each_thumbnail_and_list_every_row(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    rows = []
    for index in range(31):
        thumb = tmp_path / "thumbs" / f"r{index}.jpg"
        thumb.parent.mkdir(exist_ok=True)
        Image.new("RGB", (32, 20), (index * 8, 40, 40)).save(thumb)
        rows.append({"id": f"r{index}", "file": f"r-{index}.jpg", "picture": str(thumb)})
    rows.append({"id": "lost", "file": "lost.png", "picture": ""})
    out = tmp_path / "sheets"
    out.mkdir()
    (out / "unused-03.jpg").write_bytes(b"from a longer run")
    done = style_catalog.unused_sheets(rows, out)
    # Thirty-one drawn split evenly over two sheets; the stale third is gone.
    assert [path.name for path in done["sheets"]] == ["unused-01.jpg", "unused-02.jpg"]
    assert not (out / "unused-03.jpg").exists()
    assert (done["drawn"], done["missing"]) == (31, 1)
    with Image.open(done["sheets"][0]) as sheet:
        assert sheet.width == style_catalog.UNUSED_COLUMNS * style_catalog.UNUSED_TILE_WIDTH
    lines = (out / "unused.txt").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 32 and lines[0] == "r0\tr-0.jpg"
    assert lines[-1] == "lost\tlost.png\t(no thumbnail)"


def test_the_catalog_is_not_a_style():
    assert styles.CATALOG_FILE.removesuffix(".json") not in styles.names()


@pytest.mark.parametrize("row", published(), ids=lambda row: row["style"])
def test_a_published_mode_exposes_knobs_whose_defaults_are_its_stack(row):
    document = styles.load(row["style"])
    knobs = (document.get("public") or {}).get("knobs") or []
    low, high = style_catalog.KNOBS[row["tier"]]
    assert low <= len(knobs) <= high
    if knobs:
        assert styles.check_public(document) == []
    assert row["public"]["palette"] == document["suggested_colormap"]


def test_the_two_tiers_are_matt_s_ruling():
    """Custom: the nine first published and the seven item 050 added, less the three 107
    deleted (no showcase pick); Custom (lab): every
    other mode Matt did not drop or discard. A round-one row has no status yet, and so
    no tier."""
    rows = style_catalog.load()["modes"]
    curated = {row["style"] for row in rows if row.get("tier") == "curated"}
    assert curated == CURATED
    for row in rows:
        if "status" not in row:
            assert "tier" not in row and "score" not in row, row["style"]
            continue
        ruled_out = row.get("status") in ("drop", "discarded")
        assert (row.get("status") == "publish") != ruled_out, row["style"]
        if not ruled_out:
            assert row["tier"] == ("curated" if row["style"] in CURATED else "lab")


CURATED = {
    *("bronze_packing", "glossy_lobes", "floating_on_dreams", "yas"),
    *("ribbon_packing", "lit_petals"),
    *("soft_veils", "clockwork_rings", "molten_flow", "flame_wisp_frost", "crescent_lines"),
    *("glossy_spirals", "lace_holes"),
}


def test_a_showcase_reading_is_a_published_mode_s_passes_out_of_ten():
    row = {"status": "publish", "showcase": {"passes": 3, "item": "107"}}
    assert style_catalog.check_showcase(row) == []
    assert style_catalog.check_showcase({"status": "publish"}) == []
    held = {"passes": 0, "item": "107", "held": "a later pass", "note": "too dark"}
    assert style_catalog.check_showcase({**row, "showcase": held}) == []
    for bad in (
        {"passes": 0, "item": "107"},
        {"passes": 11, "item": "107"},
        {"passes": 2.0, "item": "107"},
        {"passes": 2},
        {"passes": 2, "item": "107", "rank": 1},
    ):
        assert style_catalog.check_showcase({**row, "showcase": bad}), bad
    assert style_catalog.check_showcase({**row, "status": "drop"})


def test_an_example_is_a_lab_mode_s_and_names_a_place_and_a_map():
    maps = {"m"}
    place = {"family": {"kind": "mandelbrot"}, "viewport": {}, "maxiter": 100}
    lab = {"tier": "lab"}
    good = {"location": place, "colormap": "m", "caption": "c", "picture": "artifacts/p.png"}
    assert style_catalog.check_example(lab, good, maps) == []
    assert style_catalog.check_example({"tier": "curated"}, good, maps)
    assert style_catalog.check_example(lab, {**good, "colormap": "x"}, maps)
    assert style_catalog.check_example(lab, {**good, "caption": ""}, maps)
    assert style_catalog.check_example(lab, {**good, "picture": "C:\\p.png"}, maps)
    assert style_catalog.check_example(lab, {**good, "location": {}}, maps)


@pytest.mark.parametrize("row", published(), ids=lambda row: row["style"])
def test_every_knob_moves_its_stack_at_either_end(row):
    document = styles.load(row["style"])
    for knob in (document.get("public") or {}).get("knobs") or []:
        for end in knob["range"]:
            if end == knob["default"]:
                continue
            turned = styles.with_knobs(document, {knob["name"]: end})
            assert turned["style"] != document["style"], (knob["name"], end)
    assert styles.with_knobs(document, {})["style"] == document["style"]


def test_a_knob_writes_every_target_and_refuses_what_it_does_not_offer():
    # A wildcard write and a scaled one: `disc_size` sets every disc's radius, and its
    # `largest` at 0.24 x - 0.008.
    document = styles.load("clockwork_rings")
    turned = styles.with_knobs(document, {"disc_size": 0.6})
    layers = turned["style"]["layers"]
    discs = [i for i, layer in enumerate(layers) if "bubble" in layer["channel"]]
    assert discs and {layers[i]["channel"]["bubble"]["radius"] for i in discs} == {0.6}
    assert {round(layers[i]["channel"]["bubble"]["largest"], 9) for i in discs} == {0.136}
    assert document["style"]["layers"][discs[0]]["channel"]["bubble"]["radius"] == 0.45
    with pytest.raises(styles.StyleError, match="outside"):
        styles.with_knobs(document, {"disc_size": 0.2})
    with pytest.raises(styles.StyleError, match="no knob"):
        styles.with_knobs(document, {"swirl": 0.2})
    # A wildcard over layers: every light turns, whatever its index.
    lit = styles.with_knobs(styles.load("glossy_lobes"), {"light_angle": 200})
    lights = [layer["light"]["azimuth"] for layer in lit["style"]["layers"] if "light" in layer]
    assert lights and set(lights) == {200}


def test_a_whole_number_member_stays_whole():
    turned = styles.with_knobs(tunnel(), {"turns": 3})
    assert turned["style"]["projection"]["log_polar"]["turns"] == 3
    assert isinstance(turned["style"]["projection"]["log_polar"]["turns"], int)
    # A member a file happens to spell as `1` is still a number, not an on/off switch.
    document = styles.load("lit_petals")
    spelled = json.loads(json.dumps(document))
    spelled["style"]["layers"][2]["opacity"] = 1
    spelled["public"]["knobs"] = [
        {**knob, "default": 1.0, "range": [0.4, 1.0]}
        for knob in spelled["public"]["knobs"]
        if knob["name"] == "jewels"
    ]
    assert styles.with_knobs(spelled, {"jewels": 0.6})["style"]["layers"][2]["opacity"] == 0.6


def test_knob_arguments_parse_and_refuse_a_bad_pair():
    assert styles.parse_knobs(["a=1", "b = 0.5"]) == {"a": 1.0, "b": 0.5}
    for bad in ("a", "a=x", "=1"):
        with pytest.raises(styles.StyleError):
            styles.parse_knobs([bad])


def test_the_cli_parses_a_knob_and_the_gallery():
    parser = cli.build_parser()
    args = parser.parse_args(
        ["style", "render", "yas", "--location", "x.json", "--knob", "swirl=0.4"]
    )
    assert args.knob == ["swirl=0.4"]
    assert parser.parse_args(["style", "gallery", "--out", "x"]).out == "x"


def test_the_gallery_starts_each_toggle_from_the_status(tmp_path, monkeypatch):
    from PIL import Image

    reference = tmp_path / "ref.png"
    Image.new("RGB", (2000, 1250), (40, 60, 90)).save(reference)
    monkeypatch.setattr(styles, "reference_path", lambda document: reference)
    rows = [
        {**row, "show": []}
        for row in style_catalog.load()["modes"]
        if row["style"] in ("yas", "field_lines", "leaf_veins")
    ]
    folder = tmp_path / "page"
    (folder / "img").mkdir(parents=True)
    (folder / "img" / "stale.jpg").write_bytes(b"")
    done = style_catalog.gallery(folder, {"schema": 1, "modes": rows})
    assert (done["shown"], done["discarded"], done["written"]) == (2, 1, 3)
    page = (folder / "index.html").read_text(encoding="utf-8")
    assert json.dumps({"yas": "publish", "field_lines": "drop"}) in page
    assert 'data-id="yas"' in page and "glass-whorl" in page and "Discarded" in page
    assert 'id="lb"' in page and "Escape" in page and 'target="_blank"' not in page
    assert page.count('class="zoom"') == 3 and 'data-cap="leaf_veins · reference · ' in page
    assert not (folder / "img" / "stale.jpg").exists()
    with Image.open(folder / "img" / "yas__ref.jpg") as small:
        assert small.width == style_catalog.REFERENCE_WIDTH
    again = style_catalog.gallery(folder, {"schema": 1, "modes": rows})
    assert again["written"] == 0
