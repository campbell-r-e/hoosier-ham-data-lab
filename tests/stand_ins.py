"""Stand-in answers for exercising `hamstats export` before the real ones exist.

compare_states is really answered (in pandas and in polars), so the neighbors
section shows which states the export asked about and what the data says of
them. Every other question answers one fixed row and writes down the
arguments it was asked with.
"""
import types

import pandas as pd
import polars as pl

import fcc_data
import hamstats

FIXED = {
    "class_mix": {"license_class": ["Extra"], "state_pct": [100.0], "us_pct": [100.0]},
    "top_cities": {"city": ["TOWN"], "operators": [1]},
    "zip_regions": {"zip3": ["473"], "operators": [1]},
    "extra_share": {"city": ["TOWN"], "operators": [1], "extras": [1], "extra_pct": [100.0]},
    "renewals_due": {"month": ["2026-10"], "licenses": [1]},
    "call_formats": {"format": ["1x2"], "licenses": [1], "vanity_pct": [0.0]},
    "clubs": {"call_sign": ["W0CLB"], "club": ["Club"], "city": ["TOWN"], "trustee_call_sign": ["W0AA"]},
}


def compare_states_pandas(df, states):
    active = df[(df["status"] == "A") & df["state"].isin(states)]
    counts = pd.DataFrame({
        "state": states,
        "operators": [int(((active["state"] == s) & (active["applicant_type"] == "I")).sum()) for s in states],
        "clubs": [int(((active["state"] == s) & (active["applicant_type"] == "B")).sum()) for s in states],
    })
    return counts.sort_values(["operators", "state"], ascending=[False, True])


def compare_states_polars(df, states):
    return pl.from_pandas(compare_states_pandas(df.to_pandas(), states))


def modules(asked):
    """(pandas module, polars module) of stand-in answers; each question's
    arguments after `df` are recorded in `asked`, by question and engine."""
    answers = {}
    for engine, frame, compare in (("pandas", pd.DataFrame, compare_states_pandas),
                                   ("polars", pl.DataFrame, compare_states_polars)):
        module = types.SimpleNamespace(__name__=f"analytics_{engine}")
        for question, columns in {**FIXED, "compare_states": None}.items():
            answer = compare if columns is None else (lambda df, *a, c=columns, f=frame: f(c))

            def record(df, *args, question=question, engine=engine, answer=answer):
                asked[(question, engine)] = args
                return answer(df, *args)
            setattr(module, question, record)
        answers[engine] = module
    return answers["pandas"], answers["polars"]


def export_with_stand_ins(monkeypatch, table, output, asked):
    """Point hamstats at `table` (a built licenses.parquet), stand-in answers
    and the folder `output`, as if the whole-country file were downloaded.
    Returns the path export writes."""
    pandas_module, polars_module = modules(asked)
    monkeypatch.setitem(hamstats.MODULES, "pandas", pandas_module)
    monkeypatch.setitem(hamstats.MODULES, "polars", polars_module)
    monkeypatch.setitem(hamstats.LOADERS, "pandas", lambda: fcc_data.load_pandas(table))
    monkeypatch.setitem(hamstats.LOADERS, "polars", lambda: fcc_data.load_polars(table))
    monkeypatch.setattr(hamstats, "OUTPUT", output)
    monkeypatch.setattr(fcc_data, "have_full_download", lambda: True)
    monkeypatch.setattr(fcc_data, "release", lambda: "Sun, 20 Sep 2026 13:32:08 GMT")
    return output / "fccInsights.json"


def run_fcc_data_main(monkeypatch, capsys, tmp_path, zip_path):
    """What `uv run python fcc_data.py` prints, with the download already in
    tmp_path/data (built from `zip_path`) instead of fetched."""
    table = tmp_path / "data" / "licenses.parquet"
    fcc_data.build(zip_path, table)
    monkeypatch.setattr(fcc_data, "HERE", tmp_path)
    monkeypatch.setattr(fcc_data, "TABLE_PATH", table)
    monkeypatch.setattr(fcc_data, "download", lambda refresh: zip_path)
    load_polars = fcc_data.load_polars
    monkeypatch.setattr(fcc_data, "load_polars", lambda: load_polars(table))
    capsys.readouterr()
    fcc_data.main([])
    return capsys.readouterr().out
