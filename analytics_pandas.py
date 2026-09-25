"""YOUR WORK GOES HERE -- the pandas version of every question hamstats answers.

Each function gets the whole license table (`df`, one row per license, from
fcc_data.load_pandas) and returns the answer. The program in hamstats.py does
everything else: reading the command line, printing, saving CSVs, and checking
your answer against the reference.

The first two functions are finished examples. Read them, then fill in the
rest one at a time, replacing `raise NotImplementedError` with your code.
Try each one as you go:

    uv run python hamstats.py cities --state IN        # runs your pandas version
    uv run python hamstats.py check cities             # is it right?

Words used below:
    operators  active licenses held by a person:
               status == "A" and applicant_type == "I"
    clubs      active licenses held by a club or organization:
               status == "A" and applicant_type == "B"

Handy pandas pieces: df[df["col"] == x], .groupby(...).size(),
.value_counts(), .sort_values([...], ascending=[...]), .head(n),
.reset_index(name=...), .str.extract(...), .dt.to_period("M"), .round(1).
"""
import pandas as pd

CLASS_NAMES = {"E": "Extra", "A": "Advanced", "G": "General", "P": "Tech Plus",
               "T": "Technician", "N": "Novice"}


# ---------------------------------------------------------------- examples
def count_active(df, state=None):
    """EXAMPLE. How many active licenses are there (in one state, if given)?

    Returns a single number.
    """
    active = df[df["status"] == "A"]
    if state:
        active = active[active["state"] == state]
    return len(active)


def lookup(df, call_sign):
    """EXAMPLE. The license for one call sign.

    Returns a table with one row (or none) and these columns:
    call_sign, status, operator_class, service, city, state, grant_date, expired_date
    """
    rows = df[df["call_sign"] == call_sign.upper()]
    columns = ["call_sign", "status", "operator_class", "service", "city", "state",
               "grant_date", "expired_date"]
    # A call sign can appear on an old, expired license and a newer one;
    # show the newest first.
    return rows[columns].sort_values("grant_date", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------- your turn
def compare_states(df, states):
    """How do these states compare?

    For each state in `states`, count operators and clubs.
    Returns columns: state, operators, clubs
    Sorted by operators (most first), then state A to Z.
    A state with no clubs shows 0, not blank.
    """
    raise NotImplementedError


def class_mix(df, state):
    """What share of a state's operators hold each license class,
    next to the share for the whole country?

    Only operators whose operator_class is one of the six in CLASS_NAMES count.
    Use CLASS_NAMES to turn "E" into "Extra".
    Returns columns: license_class, state_pct, us_pct
    Percentages of 100, rounded to 1 decimal. A class the state has none of
    shows 0.0. Sorted by us_pct (largest first), then license_class A to Z.
    """
    raise NotImplementedError


def top_cities(df, state, top=20):
    """Which towns in a state have the most operators?

    Leave out licenses with no city.
    Returns columns: city, operators
    Sorted by operators (most first), then city A to Z. Only the first `top` rows.
    """
    raise NotImplementedError


def renewals_due(df, state, months, today):
    """How many licenses in a state expire in each of the next `months` months?

    Count active licenses (people and clubs) whose expired_date is on or after
    `today` and before the same day `months` months later.
    `today` is a pandas Timestamp; `today + pd.DateOffset(months=months)` is the end.
    Returns columns: month (text like "2026-11"), licenses
    Sorted by month, earliest first. Months with none can be left out.
    """
    raise NotImplementedError


def call_formats(df, state):
    """What shapes do a state's operators' call signs come in?

    A call sign is letters, one digit, letters: W9ABC is 1 letter + 9 + 3
    letters, a "1x3". KD9XYZ is a "2x3". Name each format "<letters before>x<letters after>".
    A vanity call has service == "HV".
    Leave out a call sign that does not fit letters-digit-letters.
    Returns columns: format, licenses, vanity_pct
    vanity_pct = percent of that format's licenses that are vanity, 1 decimal.
    Sorted by licenses, most first, then format A to Z.
    """
    raise NotImplementedError


def clubs(df, state, city=None):
    """The FCC's list of club stations in a state (or one town in it).

    Only clubs count. For the city, match without caring about upper/lower case.
    Returns columns: call_sign, club, city, trustee_call_sign
    (`club` is the entity_name column.) Sorted by city, then call_sign;
    a club with no city goes last.
    """
    raise NotImplementedError


def extra_share(df, state, min_operators=50):
    """In towns with at least `min_operators` operators, what share hold an
    Extra class license?

    Leave out licenses with no city.
    Returns columns: city, operators, extras, extra_pct
    extra_pct is a percent rounded to 1 decimal.
    Sorted by extra_pct (highest first), then city A to Z.
    """
    raise NotImplementedError


def zip_regions(df, state):
    """Operators by ZIP region -- the first 3 digits of the ZIP code.

    Leave out licenses with no ZIP code.
    Returns columns: zip3, operators
    Sorted by operators (most first), then zip3.
    """
    raise NotImplementedError
