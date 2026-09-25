"""Download the FCC amateur license database and load it as a DataFrame.

You do not need to change anything in this file. Run it once:

    uv run python fcc_data.py            # download (~200 MB) and build the table
    uv run python fcc_data.py --refresh  # download again even if you have a copy

Then, from any script:

    from fcc_data import load_pandas, load_polars
    df = load_pandas()     # a pandas DataFrame, one row per license
    lf = load_polars()     # the same data as a polars DataFrame

WHERE THE DATA COMES FROM. The FCC's Universal Licensing System (ULS) publishes
every amateur license in one zip file, refreshed weekly:
https://data.fcc.gov/download/pub/uls/complete/l_amat.zip

Inside are pipe-separated text files with no header row. This project reads
three of them and joins them on the license's unique id:

    HD.dat  the license header: call sign, status, grant and expiry dates
    EN.dat  the licensee: name, city, state, ZIP, individual or club
    AM.dat  amateur details: operator class, trustee, previous call sign

The column positions come from the FCC's published layout, as checked against
the live file by the fcc-ham-counts project (EN 30 fields, HD 59, AM 18).

THE TABLE YOU GET (one row per license, every status, the whole country):

    usi                the FCC's unique id for the license
    call_sign          e.g. W9ABC
    status             A = active, E = expired, C = canceled, T = terminated
    service            HA = regular (systematic) call sign, HV = vanity call sign
    grant_date         date the license was last granted or renewed
    expired_date       date the license expires
    cancellation_date  date it was canceled, if it was
    applicant_type     I = individual person, B = club or other organization
    entity_name        licensee name -- for clubs this is the club's name
    city, state, zip_code
    operator_class     E Extra, A Advanced, G General, P Tech Plus,
                       T Technician, N Novice; blank for club stations
    trustee_call_sign  a club station's trustee
    previous_call_sign, previous_class
                       what the license had before its last change

PRIVACY. This is public FCC data, but it names real people and their home
addresses. Share counts and charts, never lists of individuals.

NO DOWNLOAD YET? tests/data/l_amat_indiana.zip is a real snapshot of every
Indiana license from the FCC release of 2026-09-25 -- the same files, cut down
to Indiana. Until you download the full file, load_pandas() and load_polars()
build and use that instead, and say so.
"""
import argparse
import io
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

import polars as pl

URL = "https://data.fcc.gov/download/pub/uls/complete/l_amat.zip"
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
ZIP_PATH = DATA / "l_amat.zip"
TABLE_PATH = DATA / "licenses.parquet"
SAMPLE_ZIP = HERE / "tests" / "data" / "l_amat_indiana.zip"
SAMPLE_TABLE = DATA / "licenses-indiana-sample.parquet"
USER_AGENT = "hoosier-ham-data-lab/0.1 (+https://github.com/campbell-r-e)"
MAX_AGE_DAYS = 7          # the FCC publishes weekly; a newer copy does not exist yet

# The columns we keep from each file: {position in the file (0-based): name}.
HD_COLUMNS = {1: "usi", 4: "call_sign", 5: "status", 6: "service", 7: "grant_date",
              8: "expired_date", 9: "cancellation_date"}
EN_COLUMNS = {1: "usi", 5: "entity_type", 7: "entity_name", 16: "city", 17: "state",
              18: "zip_code", 23: "applicant_type"}
AM_COLUMNS = {1: "usi", 5: "operator_class", 8: "trustee_call_sign",
              15: "previous_call_sign", 16: "previous_class"}
FIELD_COUNTS = {"HD": 59, "EN": 30, "AM": 18}
DATE_COLUMNS = ["grant_date", "expired_date", "cancellation_date"]


def download(refresh=False):
    """Fetch l_amat.zip into data/, unless a copy less than a week old is there."""
    DATA.mkdir(exist_ok=True)
    if ZIP_PATH.exists() and not refresh:
        age_days = (time.time() - ZIP_PATH.stat().st_mtime) / 86400
        if age_days < MAX_AGE_DAYS:
            print(f"Using the copy downloaded {age_days:.1f} days ago ({ZIP_PATH.name}).")
            return ZIP_PATH
    print(f"Downloading {URL}")
    tmp = ZIP_PATH.with_suffix(".part")
    # data.fcc.gov answers 403 unless the request carries an Accept header AND a
    # User-Agent shaped like "name/version (contact)" -- a bare name, or a
    # browser's "Mozilla/5.0", is refused too (checked 2026-09-25).
    request = urllib.request.Request(URL, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(request, timeout=60) as response, open(tmp, "wb") as out:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        while chunk := response.read(1 << 20):
            out.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r  {done / 1e6:6.0f} of {total / 1e6:.0f} MB", end="", flush=True)
    print()
    tmp.replace(ZIP_PATH)
    return ZIP_PATH


def read_member(zf, record_type, columns):
    """One .dat file from the zip as a polars DataFrame of the chosen columns.

    Every value is read as text: the files have no quoting and no header, and
    guessing types would turn ZIP codes like 04101 into numbers. Rows are kept
    only when their first field is the record type, which drops the fragments
    left when a value contains a line break and splits one record in two.
    """
    raw = zf.read(f"{record_type}.dat")
    count = FIELD_COUNTS[record_type]
    frame = pl.read_csv(
        io.BytesIO(raw), separator="|", has_header=False, quote_char=None,
        infer_schema=False, truncate_ragged_lines=True, encoding="utf8-lossy",
        new_columns=[f"f{i}" for i in range(count)],
    )
    frame = frame.filter(pl.col("f0") == record_type)
    return frame.select([pl.col(f"f{i}").alias(name) for i, name in columns.items()])


def build(zip_path=ZIP_PATH, out_path=TABLE_PATH):
    """Join HD, EN and AM into one table and save it as data/licenses.parquet."""
    print("Reading HD, EN and AM (about a minute) ...")
    with zipfile.ZipFile(zip_path) as zf:
        hd = read_member(zf, "HD", HD_COLUMNS)
        en = read_member(zf, "EN", EN_COLUMNS)
        am = read_member(zf, "AM", AM_COLUMNS)
    # EN can carry a contact as well as the licensee; keep the licensee row.
    en = en.filter(pl.col("entity_type") == "L").drop("entity_type").unique("usi", keep="first")
    am = am.unique("usi", keep="first")
    table = (
        hd.unique("usi", keep="first")
        .join(en, on="usi", how="left")
        .join(am, on="usi", how="left")
        .with_columns(
            [pl.col(c).str.strptime(pl.Date, "%m/%d/%Y", strict=False) for c in DATE_COLUMNS]
            + [pl.col(c).str.strip_chars().str.to_uppercase()
               for c in ("call_sign", "city", "state", "operator_class", "applicant_type")]
            + [pl.col("zip_code").str.slice(0, 5)]
        )
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(exist_ok=True)
    table.write_parquet(out_path)
    print(f"Saved {table.height:,} licenses to {out_path.name}")
    return table


def _need_table(path):
    """The table to read: the one asked for, or the Indiana snapshot when there
    is no download yet."""
    if Path(path).exists():
        return path
    if Path(path) == TABLE_PATH and SAMPLE_ZIP.exists():
        print("(using the Indiana snapshot from 2026-09-25 -- run `uv run python fcc_data.py`"
              " for the whole, current country)", file=sys.stderr)
        if not SAMPLE_TABLE.exists():
            build(SAMPLE_ZIP, SAMPLE_TABLE)
        return SAMPLE_TABLE
    sys.exit("No data yet. Run this first:  uv run python fcc_data.py")


def load_polars(path=TABLE_PATH):
    """The license table as a polars DataFrame."""
    return pl.read_parquet(_need_table(path))


def load_pandas(path=TABLE_PATH):
    """The license table as a pandas DataFrame."""
    import pandas as pd
    df = pd.read_parquet(_need_table(path))
    # Parquet dates arrive in pandas as plain Python objects; make them real
    # datetimes so comparisons and .dt work.
    for column in DATE_COLUMNS:
        df[column] = pd.to_datetime(df[column])
    return df


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--refresh", action="store_true", help="download again even if a recent copy exists")
    args = parser.parse_args(argv)
    zip_path = download(refresh=args.refresh)
    if args.refresh or not TABLE_PATH.exists() or TABLE_PATH.stat().st_mtime < zip_path.stat().st_mtime:
        build(zip_path)
    else:
        print(f"{TABLE_PATH.relative_to(HERE)} is up to date.")
    df = load_polars()
    active = df.filter(pl.col("status") == "A")
    print(f"{df.height:,} licenses in the file, {active.height:,} active, "
          f"{active.filter(pl.col('state') == 'IN').height:,} of those in Indiana.")


if __name__ == "__main__":
    main()
