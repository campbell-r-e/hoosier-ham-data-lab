r"""YOUR WORK GOES HERE, part two -- the same questions, answered with polars.

Every function answers exactly the question of the same name in
analytics_pandas.py (read the full description there) and must return the same
columns in the same order. Do the pandas one first, then this one, then run
both and see whether they agree:

    uv run python hamstats.py cities --state IN --engine polars
    uv run python hamstats.py cities --state IN --engine both
    uv run python hamstats.py check cities --engine polars

polars thinks in expressions instead of indexing:
    df.filter(pl.col("status") == "A")
    df.group_by("state").agg(pl.len().alias("operators"))
    df.with_columns((pl.col("a") / pl.col("b") * 100).round(1).alias("pct"))
    df.sort(["operators", "city"], descending=[True, False]).head(n)
    pl.col("call_sign").str.extract(r"^([A-Z]+)\d", 1).str.len_chars()
    pl.col("expired_date").dt.strftime("%Y-%m")
    pl.lit(today).dt.offset_by(f"{months}mo")          # today plus N months
"""
import polars as pl

from analytics_pandas import CLASS_NAMES  # noqa: F401  (same names in both)


# ---------------------------------------------------------------- examples
def count_active(df, state=None):
    """EXAMPLE. How many active licenses are there (in one state, if given)?"""
    active = df.filter(pl.col("status") == "A")
    if state:
        active = active.filter(pl.col("state") == state)
    return active.height


def lookup(df, call_sign):
    """EXAMPLE. The license for one call sign, newest first."""
    return (
        df.filter(pl.col("call_sign") == call_sign.upper())
        .select(["call_sign", "status", "operator_class", "service", "city", "state",
                 "grant_date", "expired_date"])
        .sort("grant_date", descending=True)
    )


# ---------------------------------------------------------------- your turn
def compare_states(df, states):
    """See analytics_pandas.compare_states. Columns: state, operators, clubs"""
    raise NotImplementedError


def class_mix(df, state):
    """See analytics_pandas.class_mix. Columns: license_class, state_pct, us_pct"""
    raise NotImplementedError


def top_cities(df, state, top=20):
    """See analytics_pandas.top_cities. Columns: city, operators"""
    raise NotImplementedError


def renewals_due(df, state, months, today):
    """See analytics_pandas.renewals_due. Columns: month, licenses
    Here `today` is a datetime.date."""
    raise NotImplementedError


def call_formats(df, state):
    """See analytics_pandas.call_formats. Columns: format, licenses, vanity_pct"""
    raise NotImplementedError


def clubs(df, state, city=None):
    """See analytics_pandas.clubs. Columns: call_sign, club, city, trustee_call_sign"""
    raise NotImplementedError


def extra_share(df, state, min_operators=50):
    """See analytics_pandas.extra_share. Columns: city, operators, extras, extra_pct"""
    raise NotImplementedError


def zip_regions(df, state):
    """See analytics_pandas.zip_regions. Columns: zip3, operators"""
    raise NotImplementedError
