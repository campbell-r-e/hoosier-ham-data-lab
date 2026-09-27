"""The site export is about whichever state the profile names: nothing about
Indiana is built in. Northmark (NQ), bordered by NR and NS, is made up, and so
are its licenses."""
import json

import pytest

import fcc_data
import hamstats
import stand_ins
import state_profile
from conftest import write_made_up_zip
from profiles import NORTHMARK, write_profile

# usi, call, status, service, expires, applicant, name, city, state, zip, class, trustee
NORTHMARK_LICENSES = [
    (1, "W0AA", "A", "HV", "10/15/2026", "I", "", "NORTHTOWN", "NQ", "99001", "E", ""),
    (2, "KD0AAA", "A", "HA", "01/10/2027", "I", "", "NORTHTOWN", "NQ", "99002", "T", ""),
    (3, "KD0AAB", "E", "HA", "01/01/2024", "I", "", "NORTHTOWN", "NQ", "99002", "G", ""),
    (4, "W0CLB", "A", "HA", "12/01/2026", "B", "Northtown Test Club", "NORTHTOWN", "NQ", "99001", "", "W0AA"),
    (5, "K0RR", "A", "HA", "03/03/2029", "I", "", "RIVERTON", "NR", "98001", "G", ""),
    (6, "W9AA", "A", "HV", "10/15/2026", "I", "", "MUNCIE", "IN", "47302", "E", ""),
    (7, "KD9AAA", "A", "HA", "01/10/2027", "I", "", "MUNCIE", "IN", "47304", "T", ""),
]


@pytest.fixture
def northmark(tmp_path, monkeypatch):
    """The made-up Northmark licenses as a table, with FCCHAM_STATE_PROFILE
    pointing at Northmark's profile. Returns (table, zip)."""
    monkeypatch.setenv(state_profile.ENV_VAR, str(write_profile(tmp_path)))
    zip_path = tmp_path / "l_amat.zip"
    write_made_up_zip(zip_path, NORTHMARK_LICENSES)
    table = tmp_path / "licenses.parquet"
    fcc_data.build(zip_path, table)
    return table, zip_path


def test_export_is_about_the_profiles_state(northmark, monkeypatch, tmp_path):
    asked = {}
    written = stand_ins.export_with_stand_ins(monkeypatch, northmark[0], tmp_path / "output", asked)
    assert hamstats.main(["export", "--today", "2026-09-25"]) == 0
    doc = json.loads(written.read_text())
    assert doc["state"] == "NQ"
    assert doc["neighbors"] == [
        {"state": "NQ", "operators": 2, "clubs": 1}, {"state": "NR", "operators": 1, "clubs": 0},
        {"state": "NS", "operators": 0, "clubs": 0}]
    for (question, _), args in asked.items():
        wanted = ["NQ", "NR", "NS"] if question == "compare_states" else "NQ"
        assert args[0] == wanted, question
    assert "IN" not in repr(asked)


def test_fcc_data_reports_the_profiles_state(northmark, monkeypatch, tmp_path, capsys):
    out = stand_ins.run_fcc_data_main(monkeypatch, capsys, tmp_path, northmark[1])
    assert out.endswith("7 licenses in the file, 6 active, 3 of those in Northmark.\n")


def test_export_refuses_a_profile_without_neighbors(northmark, monkeypatch, tmp_path, capsys):
    state = {k: v for k, v in NORTHMARK.items() if k != "neighborPostalCodes"}
    monkeypatch.setenv(state_profile.ENV_VAR, str(write_profile(tmp_path / "bare", state)))
    written = stand_ins.export_with_stand_ins(monkeypatch, northmark[0], tmp_path / "output", {})
    assert hamstats.main(["export"]) == 1
    assert "Not exported: the state profile for Northmark has no state.neighborPostalCodes" \
        in capsys.readouterr().out
    assert not written.exists()


def test_a_broken_profile_stops_fcc_data_before_it_downloads(tmp_path, monkeypatch):
    monkeypatch.setenv(state_profile.ENV_VAR, str(tmp_path / "nowhere"))
    monkeypatch.setattr(fcc_data, "download", lambda refresh: pytest.fail("downloaded anyway"))
    with pytest.raises(SystemExit, match="no state profile at"):
        fcc_data.main([])
