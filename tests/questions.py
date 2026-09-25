"""The questions the tests ask of the Indiana snapshot, and the day they pretend it is."""
from datetime import date

TODAY = date(2026, 9, 25)

# test name: (question, arguments after df)
QUESTIONS = {
    "count_active": ("count_active", ("IN",)),
    "lookup": ("lookup", ("wb9hxg",)),
    "compare_states": ("compare_states", (["IN", "OH"],)),
    "class_mix": ("class_mix", ("IN",)),
    "top_cities": ("top_cities", ("IN", 20)),
    "renewals_due": ("renewals_due", ("IN", 12, "TODAY")),
    "call_formats": ("call_formats", ("IN",)),
    "clubs": ("clubs", ("IN", None)),
    "clubs_in_muncie": ("clubs", ("IN", "Muncie")),
    "extra_share": ("extra_share", ("IN", 100)),
    "zip_regions": ("zip_regions", ("IN",)),
}

