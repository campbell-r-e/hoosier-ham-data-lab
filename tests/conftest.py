"""Test data, two kinds.

indiana   the real thing: every Indiana license in the FCC release of
          2026-09-25 (tests/data/l_amat_indiana.zip), loaded by fcc_data.build
          exactly as the full download is. The question tests use this.

made_up   15 invented licenses written out below, one for each odd case the
          loader has to handle (a town with a trailing space, a 9-digit ZIP, a
          contact row, a record split over two lines). test_program uses this.
"""
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fcc_data  # noqa: E402

INDIANA_ZIP = Path(__file__).parent / "data" / "l_amat_indiana.zip"

# usi, call, status, service, expires, applicant, name, city, state, zip, class, trustee
LICENSES = [
    (1, "W9AA", "A", "HV", "10/15/2026", "I", "", "MUNCIE", "IN", "47302", "E", ""),
    (2, "KD9AAA", "A", "HA", "01/10/2027", "I", "", "Muncie ", "IN", "473041234", "T", ""),
    (3, "KD9AAB", "A", "HA", "01/01/2030", "I", "", "MUNCIE", "IN", "47305", "G", ""),
    (4, "N9ZZ", "A", "HV", "11/02/2026", "I", "", "INDIANAPOLIS", "IN", "46201", "E", ""),
    (5, "KC9ABC", "A", "HA", "09/20/2026", "I", "", "INDIANAPOLIS", "IN", "46202", "T", ""),
    (6, "AB9XY", "A", "HV", "06/30/2028", "I", "", "FORT WAYNE", "IN", "46802", "A", ""),
    (7, "KD9CLB", "A", "HA", "12/01/2026", "B", "Muncie Test Radio Club", "MUNCIE", "IN", "47303", "", "KD9AAA"),
    (8, "W9ZZZ", "A", "HA", "05/05/2031", "B", "Fort Wayne Test Club", "FORT WAYNE", "IN", "46803", "", "AB9XY"),
    (9, "K9OLD", "E", "HA", "01/01/2024", "I", "", "MUNCIE", "IN", "47302", "G", ""),
    (10, "W8ABC", "A", "HA", "03/03/2029", "I", "", "COLUMBUS", "OH", "43201", "G", ""),
    (11, "KD8XYZ", "A", "HA", "04/04/2029", "I", "", "COLUMBUS", "OH", "43202", "T", ""),
    (12, "K9IL", "A", "HV", "02/02/2030", "I", "", "CHICAGO", "IL", "60601", "E", ""),
    (13, "N9NOV", "A", "HA", "03/01/2027", "I", "", "KOKOMO", "IN", "46901", "N", ""),
    (14, "KD9AAC", "A", "HA", "08/08/2031", "I", "", "", "IN", "", "T", ""),
    (15, "KD9AAD", "A", "HA", "07/07/2031", "I", "", "INDIANAPOLIS", "IN", "46203", "T", ""),
]


def _row(record_type, width, values):
    fields = [""] * width
    fields[0] = record_type
    for position, value in values.items():
        fields[position] = value
    return "|".join(fields)


def write_made_up_zip(path):
    hd, en, am = [], [], []
    for usi, call, status, service, expires, applicant, name, city, state, zip_code, cls, trustee in LICENSES:
        values = {1: str(usi), 4: call, 5: status, 6: service, 7: "01/01/2020", 8: expires}
        if usi == 15:
            # A value with a line break in it splits a record over two lines,
            # as happens a handful of times in the real file.
            values[34] = "Line one\nline two"
        hd.append(_row("HD", 59, values))
        en.append(_row("EN", 30, {1: str(usi), 4: call, 5: "L", 7: name, 16: city, 17: state,
                                  18: zip_code, 23: applicant}))
        am.append(_row("AM", 18, {1: str(usi), 4: call, 5: cls, 8: trustee}))
    # A contact row for license 15 in another town: only the licensee row counts.
    en.append(_row("EN", 30, {1: "15", 4: "KD9AAD", 5: "CL", 16: "GARY", 17: "IN", 23: "I"}))
    with zipfile.ZipFile(path, "w") as zf:
        for name, rows in (("HD.dat", hd), ("EN.dat", en), ("AM.dat", am)):
            zf.writestr(name, "\r\n".join(rows) + "\r\n")


def _load(zip_path, folder):
    table = folder / "licenses.parquet"
    fcc_data.build(zip_path, table)
    return table, {"pandas": fcc_data.load_pandas(table), "polars": fcc_data.load_polars(table)}


@pytest.fixture(scope="session")
def made_up_table(tmp_path_factory):
    folder = tmp_path_factory.mktemp("made_up")
    write_made_up_zip(folder / "l_amat.zip")
    return _load(folder / "l_amat.zip", folder)


@pytest.fixture(scope="session")
def made_up(made_up_table):
    """{"pandas": DataFrame, "polars": DataFrame} of the 15 invented licenses."""
    return made_up_table[1]


@pytest.fixture(scope="session")
def made_up_path(made_up_table):
    return made_up_table[0]


@pytest.fixture(scope="session")
def indiana(tmp_path_factory):
    """{"pandas": DataFrame, "polars": DataFrame} of every Indiana license, 2026-09-25."""
    return _load(INDIANA_ZIP, tmp_path_factory.mktemp("indiana"))[1]
