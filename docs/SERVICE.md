# How the site uses this

indianahamradio.com never reads the FCC file itself. Its license numbers come
from **fcc-ham-counts**, a small service on meshserver:

```
FCC l_amat.zip ──→ fcc-ham-counts (meshserver, hourly check, weekly data)
                     bronze  every FCC record, the whole country, as filed
                     silver  Indiana licensees
                     gold    county counts, trends
                       │
                       └─→ read-only API ──→ weekly job ──→ site pull request
                                                         ──→ public/data/*.json
```

This lab adds one more product to that pipeline: **insights**, the answers to
the questions in `analytics_pandas.py`. The site has no data like this yet:
neighboring states, class mix against the country, towns, ZIP regions, Extra
share, renewals coming due, call sign formats, and the FCC's list of club
stations.

## The contract

`insights.build(df, analytics_pandas, today, release, state=..., neighbors=...)`
returns the document. `hamstats export` writes it to `output/fccInsights.json`.
The service will serve the same document, and the site will publish it as
`public/data/fccInsights.json`. Which state it is about, and which neighbors it
is compared with, the caller says (see "Which state" below).

```jsonc
{
  "_generated": "2026-09-25",            // the day it was built
  "release": "Sun, 20 Sep 2026 ...",     // the FCC's Last-Modified for the file used
  "source": "FCC Universal Licensing System, amateur license file (l_amat.zip)",
  "state": "IN",
  "neighbors":   [{"state", "operators", "clubs"}],                 // the state and its neighbors
  "classMix":    [{"licenseClass", "statePct", "usPct"}],
  "topCities":   [{"city", "operators"}],                           // top 25
  "zipRegions":  [{"zip3", "operators"}],
  "extraShare":  {"minOperators": 50, "towns": [{"city", "operators", "extras", "extraPct"}]},
  "renewalsDue": {"from": "2026-09-25", "months": 12, "byMonth": [{"month", "licenses"}]},
  "callFormats": [{"format", "licenses", "vanityPct"}],
  "clubStations":[{"callSign", "club", "city", "trusteeCallSign"}]
}
```

Keys are camelCase to match the site's other data files (`countyStats.json`,
`licenseTrends.json`). The document holds counts and club stations only, never
an individual licensee.

## Which state

The site describes its state in one file, `state/<slug>/profile.json` in the
website repository, and fcc-ham-counts reads it (`fccham/state.py`). The lab
reads the same file, in `state_profile.py`, so `hamstats export` builds the
document about the state the service would publish: `state.postalCode`, and
`state.neighborPostalCodes` for the neighbors comparison.

Where the lab looks, first match wins:

1. the `FCCHAM_STATE_PROFILE` environment variable: the site's `state/`
   folder (holding exactly one state's folder) or a `profile.json` itself;
2. `/opt/fcc-ham-counts-state/state`, the service's copy, when it exists;
3. otherwise Indiana, built in and matching the site's Indiana profile.

So a learner never configures anything: with nothing set, everything is
Indiana, exactly as before. A profile that is named but missing or unsound
stops `export` (and `fcc_data.py`) with the reason, never a quiet fallback to
Indiana.

Only the export and `fcc_data.py`'s closing summary follow the profile. The
exercises, their `--state IN` defaults, the Indiana snapshot and the tests'
expected answers are about Indiana on purpose: they are the lessons.

`insights.py` is the same contract as the service's copy in `fccham/lab/`, so
`deploy/sync-lab.sh` carries it over unchanged in behavior.

## Why the service runs the pandas version

meshserver is a 32-bit netbook (Intel Atom N270) running Alpine Linux. Alpine
packages pandas 3 for it, but polars publishes no 32-bit build, and Alpine's
pyarrow crashes on that CPU ("Illegal instruction": it needs newer
instructions than the Atom has). So the service imports `analytics_pandas.py`
and runs it on plain pandas, without pyarrow. The lab pins pandas 3, the same
major version, so code that passes here runs there.

Two consequences for your code:

- **Don't depend on pyarrow features.** No `dtype="string[pyarrow]"`, no
  `pd.ArrowDtype`, no `.pipe(pyarrow...)`. Plain pandas string methods, groupby,
  sorting and dates are all fine.
- **Keep it reasonably lean.** The box has 2 GB of memory. Filtering first and
  then grouping is kinder than copying the whole table several times over.

The polars version is not wasted: `hamstats export` only writes the file when
both versions give the same answer to every question. That agreement is the
evidence the pandas code is right.

## How it is wired (already built)

- **fcc-ham-counts** has a copy of this lab's `analytics_pandas.py` and
  `insights.py` in `fccham/lab/`. After every weekly FCC release, the refresh
  builds this same table from the national FCC data it already holds, runs
  `insights.build`, and stores the document. `GET /insights` serves it.
- **Until every question is answered**, the refresh logs
  `insights: skipped -- the lab's analytics_pandas.<question> is not written yet`
  and publishes nothing. `/insights` answers 503, and the site's weekly job
  reads that as "nothing to do".
- **The site's weekly counts job** runs `fccham insights-diff`. When there is
  a new document, `fccham insights-apply` writes it to
  `src/data/fccInsights.json` in the pull request it opens. The site's catalog
  already lists `fccInsights.json`, so it is published at `/data/fccInsights.json`
  from the first week.

## Going live (once `uv run pytest` is all green)

1. `uv run python hamstats.py export` writes the file from the full download.
2. In fcc-ham-counts, `sh deploy/sync-lab.sh` copies the finished
   `analytics_pandas.py` (and `insights.py`) into `fccham/lab/`. It refuses
   if the lab's tests fail. Commit that in a pull request and merge it.
3. meshserver pulls it within the hour. To publish right away instead of at
   the next FCC release: `python -m fccham.refresh --recompute-insights` on meshserver.
4. The next Sunday counts job opens the site pull request with
   `src/data/fccInsights.json`.
