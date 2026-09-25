"""Your answers, assembled into the document indianahamradio.com will use.

The site does not compute FCC numbers itself. It reads them from the
fcc-ham-counts service on meshserver, which loads the FCC file every week and
serves county counts and trends to the site. When every question in
analytics_pandas.py is answered, that service can import your module, run
`build` on its own copy of the FCC data, and serve the result -- so your code
ends up behind a page on the real site. docs/SERVICE.md says how.

This file is finished; you do not need to change it. It fixes the questions
the site asks (Indiana, its four neighbors, the top 25 towns ...) and the shape
of the answer, which is the contract between your code and the service.

    uv run python hamstats.py export          # writes output/fccInsights.json

Only numbers and club stations go in. No individual licensee ever appears in
the document, because it will be published.
"""
from datetime import date

import pandas as pd

STATE = "IN"
NEIGHBORS = ["IN", "IL", "OH", "MI", "KY"]
TOP_CITIES = 25
MIN_OPERATORS = 50      # towns smaller than this make the Extra share meaningless
RENEWAL_MONTHS = 12

# section name in the document: (question, arguments after df, wrapper)
# The wrapper, when there is one, turns the rows into the section's object.
SECTIONS = {
    "neighbors": ("compare_states", lambda today: (NEIGHBORS,), None),
    "classMix": ("class_mix", lambda today: (STATE,), None),
    "topCities": ("top_cities", lambda today: (STATE, TOP_CITIES), None),
    "zipRegions": ("zip_regions", lambda today: (STATE,), None),
    "extraShare": ("extra_share", lambda today: (STATE, MIN_OPERATORS),
                   lambda rows, today: {"minOperators": MIN_OPERATORS, "towns": rows}),
    "renewalsDue": ("renewals_due", lambda today: (STATE, RENEWAL_MONTHS, today),
                    lambda rows, today: {"from": str(today)[:10], "months": RENEWAL_MONTHS, "byMonth": rows}),
    "callFormats": ("call_formats", lambda today: (STATE,), None),
    "clubStations": ("clubs", lambda today: (STATE, None), None),
}


def camel(name):
    """call_sign -> callSign, the style of the site's other data files."""
    head, *rest = name.split("_")
    return head + "".join(word.capitalize() for word in rest)


def plain(value):
    """A value JSON can hold: no numpy numbers, no NaN, dates as YYYY-MM-DD."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    if hasattr(value, "year"):
        return str(value)[:10]
    if hasattr(value, "item"):
        return value.item()
    return value


def records(answer):
    """A pandas or polars table as a list of {camelCaseColumn: value} rows."""
    frame = answer.to_pandas() if hasattr(answer, "to_pandas") and not isinstance(answer, pd.DataFrame) else answer
    frame = frame.reset_index(drop=True)
    columns = [camel(c) for c in frame.columns]
    return [{c: plain(v) for c, v in zip(columns, row)} for row in frame.itertuples(index=False)]


def build(df, analytics, today=None, release=None, sample=False):
    """The whole document, from `df` (the license table) and `analytics` (your
    analytics_pandas or analytics_polars module). `today` is a date for pandas
    code as a pandas Timestamp; defaults to the real today."""
    today = today if today is not None else date.today()
    arg_today = pd.Timestamp(today) if analytics.__name__.endswith("pandas") else today
    doc = {
        "_generated": str(date.today()),
        "release": release,
        "source": "FCC Universal Licensing System, amateur license file (l_amat.zip)",
        "state": STATE,
    }
    if sample:
        doc["sample"] = "Built from the Indiana-only snapshot, not the full FCC file: neighbors and national figures are wrong."
    for section, (question, argfn, wrap) in SECTIONS.items():
        try:
            rows = records(getattr(analytics, question)(df, *argfn(arg_today)))
        except NotImplementedError:
            raise NotImplementedError(f"{analytics.__name__}.{question}") from None
        doc[section] = wrap(rows, today) if wrap else rows
    return doc
