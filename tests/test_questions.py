"""Is your answer right? Checked against real Indiana data.

    uv run pytest                         # everything
    uv run pytest -k cities               # one question, both engines
    uv run pytest -k "cities and polars"  # one question, one engine

Each question is asked of tests/data/l_amat_indiana.zip -- every Indiana
license in the FCC release of 2026-09-25 -- and your answer must match the
correct one, row for row, stored in tests/expected_indiana.json. The snapshot
holds only Indiana, so in these tests "the whole country" is Indiana too, and
Ohio has no hams.

A question you have not written yet fails with "not written yet".
"""
import json
from pathlib import Path

import pandas as pd
import pytest

import analytics_pandas
import analytics_polars
import hamstats

from questions import QUESTIONS, TODAY

MODULES = {"pandas": analytics_pandas, "polars": analytics_polars}
EXPECTED = json.loads((Path(__file__).parent / "expected_indiana.json").read_text())


def ask(engine, question, data, args):
    today = pd.Timestamp(TODAY) if engine == "pandas" else TODAY
    args = tuple(today if a == "TODAY" else a for a in args)
    try:
        return getattr(MODULES[engine], question)(data[engine], *args)
    except NotImplementedError:
        pytest.fail(f"{MODULES[engine].__name__}.{question} is not written yet", pytrace=False)


@pytest.mark.parametrize("engine", ["pandas", "polars"])
@pytest.mark.parametrize("name", list(QUESTIONS))
def test_answer(name, engine, indiana):
    question, args = QUESTIONS[name]
    want = EXPECTED[name]
    answer = hamstats.to_pandas(ask(engine, question, indiana, args))
    assert list(answer.columns) == want["columns"], \
        f"columns should be {want['columns']}, not {list(answer.columns)}"
    expected = pd.DataFrame(want["rows"], columns=want["columns"])
    if not hamstats.same_answer(answer, expected):
        pytest.fail(
            f"\nexpected {len(expected)} rows, first few:\n{expected.head(8).to_string(index=False)}"
            f"\n\ngot {len(answer)} rows, first few:\n{answer.head(8).to_string(index=False)}",
            pytrace=False)
