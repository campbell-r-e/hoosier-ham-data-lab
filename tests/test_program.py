"""The parts that are already built: the loader and the hamstats shell.
These should pass from the first day; if one fails, something is broken in the
setup, not in your answers."""
import pandas as pd

import hamstats


def test_loader_joins_the_three_files(made_up):
    df = made_up["pandas"]
    assert len(df) == 15
    w9aa = df[df["call_sign"] == "W9AA"].iloc[0]
    assert (w9aa["city"], w9aa["state"], w9aa["operator_class"], w9aa["applicant_type"]) == \
        ("MUNCIE", "IN", "E", "I")


def test_loader_cleans_values(made_up):
    df = made_up["pandas"].set_index("call_sign")
    assert df.loc["KD9AAA", "city"] == "MUNCIE"          # "Muncie " trimmed and uppercased
    assert df.loc["KD9AAA", "zip_code"] == "47304"       # ZIP+4 cut to five digits
    assert pd.isna(df.loc["KD9AAC", "city"])             # blank becomes missing
    assert df.loc["KD9AAD", "city"] == "INDIANAPOLIS"    # the licensee, not the contact
    assert str(df.loc["W9AA", "expired_date"])[:10] == "2026-10-15"


def test_a_record_split_over_two_lines_still_loads(made_up):
    assert "KD9AAD" in set(made_up["polars"]["call_sign"])


def test_both_engines_load_the_same_table(made_up):
    a = made_up["pandas"].sort_values("usi").reset_index(drop=True)
    b = made_up["polars"].to_pandas().sort_values("usi").reset_index(drop=True)
    assert list(a.columns) == list(b.columns)
    assert hamstats.same_answer(a.astype(str), b.astype(str))


def test_same_answer_compares_values_not_names():
    a = pd.DataFrame({"x": ["IN"], "n": [3], "p": [33.3]})
    b = pd.DataFrame({"state": ["IN"], "count": [3], "pct": [33.34]})
    assert hamstats.same_answer(a, b)
    assert not hamstats.same_answer(a, b.assign(count=4))


def test_unwritten_question_is_reported_not_crashed(capsys, monkeypatch, made_up_path):
    import analytics_pandas
    import fcc_data
    monkeypatch.setitem(hamstats.LOADERS, "pandas", lambda: fcc_data.load_pandas(made_up_path))

    def not_yet(*args):
        raise NotImplementedError
    monkeypatch.setattr(analytics_pandas, "top_cities", not_yet)
    assert hamstats.main(["cities"]) == 1
    assert "not written yet" in capsys.readouterr().out


def test_example_command_runs(capsys, monkeypatch, made_up_path):
    import fcc_data
    monkeypatch.setitem(hamstats.LOADERS, "pandas", lambda: fcc_data.load_pandas(made_up_path))
    monkeypatch.setitem(hamstats.LOADERS, "polars", lambda: fcc_data.load_polars(made_up_path))
    assert hamstats.main(["count", "--state", "IN", "--engine", "both"]) == 0
    out = capsys.readouterr().out
    assert "11" in out and "agree" in out


def test_indiana_snapshot_loads(indiana):
    df = indiana["polars"]
    assert df.height == 33_619
    assert set(df["state"].unique()) == {"IN"}
