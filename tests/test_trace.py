"""`curate solve trace`: a seat followed back to its walk row, and a broken chain said.

A store built by hand in a temporary hot root: one record of two seats, the ledger,
its sidecars, the location judge's sidecar and one harvest. One seat's chain runs to
the walk's root; the other's place was never scored, and the trace has to say where
it stopped rather than drop it. Arithmetic over a dozen rows, no engine and no judge.
"""

from __future__ import annotations

import json

from fractal_wallpapers.curation import trace

JUDGE = "481fe0582328f0de8d64d8e0ddc9a0bde1f044419e2074af6a559239b5792d46"


def _jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8", newline="\n")


def _store(root):
    place_a, place_b, place_c = '["mandelbrot", 2, "a"]', '["mandelbrot", 2, "b"]', '["c"]'
    stamp = "20261005T000000Z"
    record = root / "curation" / "tentative" / stamp
    _jsonl(
        record / "gallery.jsonl",
        [
            {"schema": 1, "key": "k1", "alias": "k1", "location": place_a, "mode": "smooth"},
            {"schema": 1, "key": "k2", "alias": "k2", "location": place_b, "mode": "tia"},
        ],
    )
    (record / "manifest.json").write_text(
        json.dumps({"schema": 1, "seats": {"asked": 2}, "solve": {"config": {"force_fill": 1}}}),
        encoding="utf-8",
    )
    ledger = root / "curation" / "candidate_ledger"
    _jsonl(
        ledger / "rows.jsonl",
        [
            {"schema": 1, "key": key, "location": {"key": place}}
            for key, place in (("k1", place_a), ("k2", place_b), ("k3", place_c))
        ],
    )
    _jsonl(
        ledger / "scores.jsonl",
        [
            {
                "schema": 1,
                "key": f"{key}|{JUDGE}|640x360ss2",
                "recipe_key": key,
                "judge_artifact": JUDGE,
                "regime": "640x360ss2",
                "head": "smooth_render",
                "p_ge2": 0.9,
                "p_ge3": 0.5,
                "p_ge4": p4,
                "rank_score": 1.0,
                "block": "scores",
                "read_by": {"run": "h1", "candidate": "0"},
            }
            for key, p4 in (("k1", 0.5), ("k2", 0.5), ("k3", 0.01))
        ],
    )
    _jsonl(
        root / "curation" / "supply_scores.jsonl",
        [
            {
                "schema": 1,
                "head": "location",
                "key": place_a,
                "ledger": "artifacts/harvest/walk.jsonl",
                "node_id": 7,
                "p_ge2": 0.9,
                "p_ge3": 0.6,
                "p_ge4": 0.2,
            },
            {
                "schema": 1,
                "head": "location",
                "key": place_c,
                "ledger": "artifacts/harvest/walk.jsonl",
                "node_id": 9,
                "p_ge2": 0.1,
                "p_ge3": 0.01,
                "p_ge4": 0.0,
            },
        ],
    )
    _jsonl(
        root / "harvest" / "walk.jsonl",
        [
            {"schema": 1, "kind": "run", "seed": 0},
            {"schema": 1, "kind": "root", "root_id": 3, "node_id": 1},
            {"schema": 1, "kind": "candidate", "node_id": 5, "parent_node_id": 1, "root_id": 3},
            {"schema": 1, "kind": "candidate", "node_id": 7, "parent_node_id": 5, "root_id": 3},
            {"schema": 1, "kind": "candidate", "node_id": 9, "parent_node_id": 1, "root_id": 3},
            {"schema": 1, "kind": "node_dead", "node_id": 11, "cause": "flat"},
        ],
    )
    _jsonl(root / "harvest" / "locations.jsonl", [{"schema": 1, "key": place_a}])
    return stamp


def test_a_seat_is_followed_to_its_root_and_a_broken_chain_is_said(tmp_path, monkeypatch):
    root = tmp_path / "artifacts"
    monkeypatch.setenv("FRACTAL_WALLPAPERS_HOT_ROOT", str(root))
    monkeypatch.setenv("FRACTAL_WALLPAPERS_ARCHIVE_ROOT", "")
    root.mkdir()
    stamp = _store(root)
    out = tmp_path / "trace"
    page, counts = trace.build(stamp, out=out, bundle=tmp_path / "bundle", log=lambda _: None)

    assert counts["broken_chains"] == [
        {"seat": 2, "key": "k2", "stopped_at": "supply_scores.jsonl"}
    ]
    assert counts["files"]["rows.jsonl"] == {
        "source": counts["files"]["rows.jsonl"]["source"],
        "rows": 3,
        "sliced": 3,
    }
    walk = (out / "files" / "walk.jsonl").read_text(encoding="utf-8").splitlines()
    kinds = [json.loads(line)["kind"] for line in walk]
    # The seat's own row, its ancestor and its root, the lowest-scored place's row,
    # and one row of each kind no chain reached.
    assert kinds == ["run", "root", "candidate", "candidate", "candidate", "node_dead"]
    source = (root / "harvest" / "walk.jsonl").read_text(encoding="utf-8").splitlines()
    assert set(walk) <= set(source), "a slice is copied byte for byte"
    text = page.read_text(encoding="utf-8")
    assert "CHAIN BROKEN" in text and "under the pool gate" in text
    assert (tmp_path / "bundle" / "files" / "walk.jsonl").is_file()
    assert (tmp_path / "bundle" / "counts.json").is_file()
