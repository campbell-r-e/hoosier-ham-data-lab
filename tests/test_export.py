"""hamstats export: what it refuses to do, and the shape of what it writes.
These pass from the first day -- they use stand-in answers, not yours."""
import json
from pathlib import Path

import pandas as pd
import polars as pl
import pytest

import analytics_pandas
import analytics_polars
import fcc_data
import hamstats
import insights

EXPECTED = json.loads((Path(__file__).parent / "expected_indiana.json").read_text())
STAND_IN = {question: EXPECTED[question] for question in
            ("compare_states", "class_mix", "top_cities", "zip_regions", "extra_share",
             "renewals_due", "call_formats", "clubs")}


@pytest.fixture
def lab(monkeypatch, tmp_path, made_up_path):
    """hamstats pointed at the made-up data and a scratch output folder."""
    monkeypatch.setitem(hamstats.LOADERS, "pandas", lambda: fcc_data.load_pandas(made_up_path))
    monkeypatch.setitem(hamstats.LOADERS, "polars", lambda: fcc_data.load_polars(made_up_path))
    monkeypatch.setattr(hamstats, "OUTPUT", tmp_path / "output")
    monkeypatch.setattr(fcc_data, "have_full_download", lambda: True)
    return tmp_path / "output" / "fccInsights.json"


def answer_everything(monkeypatch, polars_changes=None):
    for question, want in STAND_IN.items():
        frame = pd.DataFrame(want["rows"], columns=want["columns"])
        monkeypatch.setattr(analytics_pandas, question, lambda df, *a, f=frame: f.copy())
        other = polars_changes(question, frame) if polars_changes else frame
        monkeypatch.setattr(analytics_polars, question, lambda df, *a, f=other: pl.from_pandas(f))


def test_refuses_while_a_question_is_unwritten(lab, monkeypatch, capsys):
    answer_everything(monkeypatch)

    def not_yet(*args):
        raise NotImplementedError
    monkeypatch.setattr(analytics_pandas, "zip_regions", not_yet)
    assert hamstats.main(["export"]) == 1
    assert "analytics_pandas.zip_regions is not written yet" in capsys.readouterr().out
    assert not lab.exists()


def test_refuses_when_the_engines_disagree(lab, monkeypatch, capsys):
    answer_everything(monkeypatch, lambda q, f: f.head(1) if q == "top_cities" else f)
    assert hamstats.main(["export"]) == 1
    assert "disagree on topCities" in capsys.readouterr().out
    assert not lab.exists()


def test_refuses_the_indiana_snapshot_unless_asked(lab, monkeypatch, capsys):
    answer_everything(monkeypatch)
    monkeypatch.setattr(fcc_data, "have_full_download", lambda: False)
    assert hamstats.main(["export"]) == 1
    assert "whole-country file" in capsys.readouterr().out
    assert hamstats.main(["export", "--allow-sample"]) == 0
    assert "sample" in json.loads(lab.read_text())


def test_writes_the_document_the_service_serves(lab, monkeypatch):
    answer_everything(monkeypatch)
    assert hamstats.main(["export", "--today", "2026-09-25"]) == 0
    doc = json.loads(lab.read_text())
    assert list(doc) == ["_generated", "release", "source", "state", *insights.SECTIONS]
    assert doc["state"] == "IN" and "sample" not in doc
    assert doc["renewalsDue"]["from"] == "2026-09-25" and doc["renewalsDue"]["months"] == 12
    assert doc["extraShare"]["minOperators"] == 50
    assert set(doc["clubStations"][0]) == {"callSign", "club", "city", "trusteeCallSign"}
    assert set(doc["classMix"][0]) == {"licenseClass", "statePct", "usPct"}


def test_camel_case_and_plain_values():
    assert insights.camel("trustee_call_sign") == "trusteeCallSign"
    rows = insights.records(pd.DataFrame({"extra_pct": [33.3], "n": pd.array([3], dtype="Int64"),
                                          "when": [pd.Timestamp("2026-09-25")], "gone": [None]}))
    assert rows == [{"extraPct": 33.3, "n": 3, "when": "2026-09-25", "gone": None}]
