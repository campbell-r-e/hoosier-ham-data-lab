"""With nothing configured -- no FCCHAM_STATE_PROFILE, no profile anywhere --
the program says exactly what it said before it could be about another state:
Indiana, compared with IL, OH, MI and KY in that order. conftest makes sure nothing is
configured. These pass from the first day."""
import json

import analytics_pandas
import fcc_data
import hamstats
import stand_ins


def test_count_prints_what_it_always_has(made_up_path, monkeypatch, capsys):
    monkeypatch.setitem(hamstats.LOADERS, "pandas", lambda: fcc_data.load_pandas(made_up_path))
    monkeypatch.setitem(hamstats.LOADERS, "polars", lambda: fcc_data.load_polars(made_up_path))
    assert hamstats.main(["count", "--state", "IN", "--engine", "both"]) == 0
    assert capsys.readouterr().out == (
        "--- pandas ---\n11\n--- polars ---\n11\npandas and polars agree.\n")


def test_an_unwritten_question_says_what_it_always_has(made_up_path, monkeypatch, capsys):
    def not_yet(*args):
        raise NotImplementedError
    monkeypatch.setitem(hamstats.LOADERS, "pandas", lambda: fcc_data.load_pandas(made_up_path))
    monkeypatch.setattr(analytics_pandas, "top_cities", not_yet)    # however far she has got
    assert hamstats.main(["cities"]) == 1
    assert capsys.readouterr().out == (
        "[pandas] analytics_pandas.top_cities is not written yet -- "
        "open analytics_pandas.py and fill it in.\n")


def test_export_is_about_indiana_and_its_neighbors(made_up_path, monkeypatch, tmp_path, capsys):
    asked = {}
    written = stand_ins.export_with_stand_ins(monkeypatch, made_up_path, tmp_path / "output", asked)
    assert hamstats.main(["export", "--today", "2026-09-25"]) == 0
    assert capsys.readouterr().out == (
        "pandas and polars agree on all 8 sections; wrote output/fccInsights.json\n")
    doc = json.loads(written.read_text())
    assert doc["state"] == "IN"
    # The same states in the same order main asks for (insights.NEIGHBORS on
    # main was ["IN", "IL", "OH", "MI", "KY"]), so her output cannot change.
    assert asked[("compare_states", "pandas")] == (["IN", "IL", "OH", "MI", "KY"],)
    assert asked[("top_cities", "polars")] == ("IN", 25)
    # The same rows the old hard-coded [IN, IL, OH, MI, KY] gave: sorted, not asked order.
    assert doc["neighbors"] == [
        {"state": "IN", "operators": 9, "clubs": 2}, {"state": "OH", "operators": 2, "clubs": 0},
        {"state": "IL", "operators": 1, "clubs": 0}, {"state": "KY", "operators": 0, "clubs": 0},
        {"state": "MI", "operators": 0, "clubs": 0}]


def test_fcc_data_reports_indiana(made_up_path, monkeypatch, tmp_path, capsys):
    out = stand_ins.run_fcc_data_main(monkeypatch, capsys, tmp_path, made_up_path.parent / "l_amat.zip")
    assert out == ("data/licenses.parquet is up to date.\n"
                   "15 licenses in the file, 14 active, 11 of those in Indiana.\n")
