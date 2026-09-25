# Hoosier Ham Data Lab

Build **hamstats**, a command-line program that answers questions about Indiana's
amateur radio operators from the FCC's own license database. It works in two
Python data libraries, **pandas** and **polars**.

The shell of the program is already built. It downloads the data, reads the
command line, prints answers and saves CSVs. **The answers are yours to write.**
Each question is one function, written twice: once in `analytics_pandas.py`
and once in `analytics_polars.py`.

```
$ uv run python hamstats.py cities --state IN --top 5
        city  operators
INDIANAPOLIS       1409
  FORT WAYNE        760
 BLOOMINGTON        393
  EVANSVILLE        355
 TERRE HAUTE        322
```

## Setup

You need [uv](https://docs.astral.sh/uv/). It installs Python and the libraries for you.

```sh
git clone <this repo>
cd hoosier-ham-data-lab
uv sync                          # installs pandas, polars, pyarrow, pytest
uv run pytest                    # most tests fail at first; that's the to-do list
```

That's enough to start. Until you download the full database, the program
uses `tests/data/l_amat_indiana.zip`. That file is every Indiana license from
the FCC release of September 25, 2026: 33,619 real licenses.

When you want the whole country, current as of this week (a ~200 MB download):

```sh
uv run python fcc_data.py
```

## The program

| Command | Question it answers | Function you write |
|---|---|---|
| `count --state IN` | How many active licenses? | `count_active` *(example, done)* |
| `lookup W9ABC` | Whose license is this? | `lookup` *(example, done)* |
| `cities --state IN --top 20` | Which towns have the most operators? | `top_cities` |
| `zips --state IN` | Operators by ZIP region (first 3 digits) | `zip_regions` |
| `states IN IL OH MI KY` | How do states compare? | `compare_states` |
| `clubs --state IN --city Muncie` | The FCC's club stations | `clubs` |
| `extras --state IN --min 50` | Share of Extra class operators by town | `extra_share` |
| `renewals --state IN --months 12` | Licenses coming up for renewal each month | `renewals_due` |
| `classes --state IN` | License classes, the state vs. the country | `class_mix` |
| `formats --state IN` | Call sign shapes (1x2, 2x3 ...) and vanity share | `call_formats` |

They're listed roughly easiest to hardest. Do them in that order.

Every command also takes:

- `--engine pandas` (the default), `--engine polars`, or `--engine both`. With
  `both`, the program runs both versions and tells you whether they agree.
- `--csv` saves the answer to `output/<command>.csv`, ready for a spreadsheet.

## How to work

1. Read `count_active` and `lookup` in both analytics files. They're the worked
   examples.
2. Pick the next question. Its docstring in `analytics_pandas.py` says
   exactly what to return: which columns, in what order, sorted how.
3. Write the pandas version. Try it:
   `uv run python hamstats.py cities --state IN`
4. Check it: `uv run pytest -k "top_cities and pandas"`
5. Write the polars version, then run `--engine both` until they agree.
6. Repeat until `uv run pytest` is all green.

The tests check your answers against real Indiana data. When one fails, it
prints the first rows it expected next to the first rows you returned.

**Bonus:** add a command of your own. Write the function in both analytics
files, then add it to `COMMANDS` in `hamstats.py`. The BONUS comment there
shows how. Some ideas: who upgraded their license class, how many licenses
were granted each year, or the most common first letter after the 9.

## What's in the data

`fcc_data.py` describes every column at the top of the file. The short version:
one row per license, with its call sign, status (`A` = active), license class,
town, state, ZIP, whether it belongs to a person (`I`) or a club (`B`), and its
grant and expiration dates.

The data is the FCC's Universal Licensing System amateur file,
<https://data.fcc.gov/download/pub/uls/complete/l_amat.zip>, published weekly.

## Be decent with it

This is public data, and it names real people and their home addresses.
Share counts and charts freely. Don't publish lists of individuals.
