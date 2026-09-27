"""hamstats -- answers questions about amateur radio licenses from FCC data.

    uv run python hamstats.py count --state IN
    uv run python hamstats.py lookup W9ABC
    uv run python hamstats.py states IN IL OH MI KY
    uv run python hamstats.py classes --state IN
    uv run python hamstats.py cities --state IN --top 20
    uv run python hamstats.py renewals --state IN --months 12
    uv run python hamstats.py formats --state IN
    uv run python hamstats.py clubs --state IN --city Muncie
    uv run python hamstats.py extras --state IN --min 50
    uv run python hamstats.py zips --state IN
    uv run python hamstats.py export       # everything, as the site will use it

Every command takes:
    --engine pandas|polars|both   whose code answers (default pandas); "both"
                                  runs the two and says whether they agree
    --csv                         also save the answer to output/<command>.csv

This file is the shell of the program: it reads the command line, loads the
data, calls the function that answers the question, and prints the answer.
The answers themselves are yours to write, in analytics_pandas.py and
analytics_polars.py. `count` and `lookup` already work -- they are the
examples.

No download yet? It runs on the Indiana snapshot in tests/data/ until you
run `uv run python fcc_data.py`.

When you have written them all, add a command of your own: write the function
in both analytics files, then add it to COMMANDS below (see the BONUS note).
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import polars as pl

import analytics_pandas
import analytics_polars
import fcc_data
import insights
import state_profile

OUTPUT = Path(__file__).resolve().parent / "output"


def _today(args, engine):
    day = date.fromisoformat(args.today) if args.today else date.today()
    return pd.Timestamp(day) if engine == "pandas" else day


# Each command: (function name, help text, how to add its options, how to call it).
# The call gets the parsed options and the engine name, and returns the
# arguments after `df` for that engine's function.
COMMANDS = {
    "count": ("count_active", "how many active licenses",
              lambda p: p.add_argument("--state", help="two-letter state, e.g. IN (default: all)"),
              lambda a, e: (a.state,)),
    "lookup": ("lookup", "the license for one call sign",
               lambda p: p.add_argument("call_sign"),
               lambda a, e: (a.call_sign,)),
    "states": ("compare_states", "compare states: operators and clubs",
               lambda p: p.add_argument("states", nargs="+", metavar="STATE"),
               lambda a, e: ([s.upper() for s in a.states],)),
    "classes": ("class_mix", "a state's license classes next to the whole country's",
                lambda p: p.add_argument("--state", default="IN"),
                lambda a, e: (a.state,)),
    "cities": ("top_cities", "the towns with the most operators",
               lambda p: (p.add_argument("--state", default="IN"),
                          p.add_argument("--top", type=int, default=20)),
               lambda a, e: (a.state, a.top)),
    "renewals": ("renewals_due", "licenses expiring in each coming month",
                 lambda p: (p.add_argument("--state", default="IN"),
                            p.add_argument("--months", type=int, default=12),
                            p.add_argument("--today", help="pretend today is YYYY-MM-DD")),
                 lambda a, e: (a.state, a.months, _today(a, e))),
    "formats": ("call_formats", "call sign shapes (1x2, 2x3 ...) and how many are vanity",
                lambda p: p.add_argument("--state", default="IN"),
                lambda a, e: (a.state,)),
    "clubs": ("clubs", "the FCC's club stations in a state or town",
              lambda p: (p.add_argument("--state", default="IN"),
                         p.add_argument("--city")),
              lambda a, e: (a.state, a.city)),
    "extras": ("extra_share", "the share of Extra class operators by town",
               lambda p: (p.add_argument("--state", default="IN"),
                          p.add_argument("--min", type=int, default=50, dest="min_operators")),
               lambda a, e: (a.state, a.min_operators)),
    "zips": ("zip_regions", "operators by ZIP region (first 3 digits)",
             lambda p: p.add_argument("--state", default="IN"),
             lambda a, e: (a.state,)),
    # BONUS: your own command goes here, e.g.
    # "upgrades": ("upgrades", "who moved up a class", lambda p: p.add_argument("--state", default="IN"),
    #              lambda a, e: (a.state,)),
}

MODULES = {"pandas": analytics_pandas, "polars": analytics_polars}
LOADERS = {"pandas": fcc_data.load_pandas, "polars": fcc_data.load_polars}


def to_pandas(answer):
    """Any answer as a pandas DataFrame, for printing, saving and comparing."""
    if isinstance(answer, pl.DataFrame):
        return answer.to_pandas()
    if isinstance(answer, pd.Series):
        return answer.reset_index()
    if isinstance(answer, pd.DataFrame):
        return answer.reset_index(drop=True)
    return pd.DataFrame({"answer": [answer]})


def same_answer(a, b):
    """True when two answers hold the same rows in the same order (column names
    ignored, numbers within 0.05, dates and text compared as text)."""
    a, b = to_pandas(a), to_pandas(b)
    if a.shape != b.shape:
        return False
    for row_a, row_b in zip(a.itertuples(index=False), b.itertuples(index=False)):
        for x, y in zip(row_a, row_b):
            if pd.isna(x) and pd.isna(y):
                continue
            if pd.api.types.is_number(x) and pd.api.types.is_number(y):
                if abs(float(x) - float(y)) > 0.05:
                    return False
            elif hasattr(x, "year") or hasattr(y, "year"):
                if str(x)[:10] != str(y)[:10]:      # a date, whatever type holds it
                    return False
            elif str(x) != str(y):
                return False
    return True


def show(answer):
    frame = to_pandas(answer)
    if list(frame.columns) == ["answer"]:
        value = frame["answer"][0]
        print(f"{value:,}" if pd.api.types.is_integer(value) else value)
    elif frame.empty:
        print("(no rows)")
    else:
        with pd.option_context("display.max_rows", 200, "display.width", 160):
            print(frame.to_string(index=False))


def answer_with(engine, name, args, argfn):
    function = getattr(MODULES[engine], name)
    try:
        return True, function(LOADERS[engine](), *argfn(args, engine))
    except NotImplementedError:
        print(f"[{engine}] {MODULES[engine].__name__}.{name} is not written yet -- "
              f"open {MODULES[engine].__name__}.py and fill it in.")
        return False, None


def _export_state():
    """The site's state profile, resolved to (postal_code, neighbors) -- or,
    when the profile can't be used, the reason printed and None returned."""
    try:
        state = state_profile.load()
        return state.postal_code, list(state.require_neighbors())
    except state_profile.ProfileError as e:
        print(f"Not exported: {e}")
        return None


def export(args):
    """Every answer, from both engines, into output/fccInsights.json -- but only
    when both engines are written and agree. This file is what the site gets."""
    if not fcc_data.have_full_download() and not args.allow_sample:
        print("export needs the whole-country file (the neighbors and national figures come from it).\n"
              "Run `uv run python fcc_data.py` first, or add --allow-sample to try it on the Indiana snapshot.")
        return 1
    resolved = _export_state()
    if resolved is None:
        return 1
    state_postal, neighbors = resolved
    today = date.fromisoformat(args.today) if args.today else date.today()
    frames = {engine: LOADERS[engine]() for engine in ("pandas", "polars")}
    docs = {}
    for engine in ("pandas", "polars"):
        try:
            docs[engine] = insights.build(frames[engine], MODULES[engine], today,
                                          fcc_data.release(), sample=not fcc_data.have_full_download(),
                                          state=state_postal, neighbors=neighbors)
        except NotImplementedError as e:
            print(f"Not exported: {e} is not written yet.")
            return 1
    wrong = [name for name in insights.SECTIONS
             if not same_answer(pd.json_normalize(_rows(docs["pandas"][name])),
                                pd.json_normalize(_rows(docs["polars"][name])))]
    if wrong:
        print("Not exported: pandas and polars disagree on " + ", ".join(wrong) + ".")
        return 1
    OUTPUT.mkdir(exist_ok=True)
    path = OUTPUT / "fccInsights.json"
    path.write_text(json.dumps(docs["pandas"], indent=1) + "\n")
    print(f"pandas and polars agree on all {len(insights.SECTIONS)} sections; wrote {path.relative_to(OUTPUT.parent)}")
    return 0


def _rows(section):
    """A section's rows, whether it is a list or an object holding one."""
    if isinstance(section, dict):
        return next(v for v in section.values() if isinstance(v, list))
    return section


def main(argv=None):
    parser = argparse.ArgumentParser(prog="hamstats", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    ex = sub.add_parser("export", help="every answer, as the site will use it (output/fccInsights.json)")
    ex.add_argument("--today", help="pretend today is YYYY-MM-DD")
    ex.add_argument("--allow-sample", action="store_true", help="export from the Indiana snapshot (for trying it out)")
    for command, (name, help_text, add_options, _) in COMMANDS.items():
        p = sub.add_parser(command, help=help_text)
        add_options(p)
        p.add_argument("--engine", choices=["pandas", "polars", "both"], default="pandas")
        p.add_argument("--csv", action="store_true", help="also save to output/<command>.csv")
    args = parser.parse_args(argv)
    if args.command == "export":
        return export(args)
    if not hasattr(args, "today"):
        args.today = None

    name, _, _, argfn = COMMANDS[args.command]
    engines = ["pandas", "polars"] if args.engine == "both" else [args.engine]
    answers = {}
    for engine in engines:
        ok, answer = answer_with(engine, name, args, argfn)
        if not ok:
            continue
        answers[engine] = answer
        if len(engines) > 1:
            print(f"--- {engine} ---")
        show(answer)
        if args.csv:
            OUTPUT.mkdir(exist_ok=True)
            path = OUTPUT / f"{args.command}{'' if len(engines) == 1 else '-' + engine}.csv"
            to_pandas(answer).to_csv(path, index=False)
            print(f"saved {path.relative_to(OUTPUT.parent)}")
    if len(answers) == 2:
        agree = same_answer(answers["pandas"], answers["polars"])
        print("pandas and polars agree." if agree else "pandas and polars DISAGREE -- compare the two tables above.")
        return 0 if agree else 1
    return 0 if answers else 1


if __name__ == "__main__":
    sys.exit(main())
