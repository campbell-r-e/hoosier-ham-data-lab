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

`insights.build(df, analytics_pandas, today, release)` returns the document.
`hamstats export` writes it to `output/fccInsights.json`. The service will
serve the same document, and the site will publish it as
`public/data/fccInsights.json`.

```jsonc
{
  "_generated": "2026-09-25",            // the day it was built
  "release": "Sun, 20 Sep 2026 ...",     // the FCC's Last-Modified for the file used
  "source": "FCC Universal Licensing System, amateur license file (l_amat.zip)",
  "state": "IN",
  "neighbors":   [{"state", "operators", "clubs"}],                 // IN, IL, OH, MI, KY
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

## Why the service runs the pandas version

meshserver is 32-bit (i686) Alpine Linux. Alpine packages pandas 3, numpy and
pyarrow for it (`py3-pandas`, `py3-numpy`, `py3-pyarrow`), but polars publishes
no build for that platform. So the service imports `analytics_pandas.py`.
The lab pins pandas 3, the same major version as the server, so code that
passes here runs there.

The polars version is not wasted: `hamstats export` only writes the file when
both versions give the same answer to every question. That agreement is the
evidence the pandas code is right.

## Dropping it in (once every question is answered)

1. `uv run pytest` is all green and `uv run python hamstats.py export` writes
   the file from the full download.
2. In fcc-ham-counts: copy in `analytics_pandas.py` and `insights.py`, and add
   a step to the weekly refresh. That step builds the same table this lab's
   `fcc_data.build` makes, but from the bronze tables that already hold the
   full national file, calls `insights.build`, and stores the document with
   the run.
3. Serve it at `GET /insights`, like `/counties` and `/trends`.
4. The weekly site job writes it to `public/data/fccInsights.json` and adds it
   to the site's open-data catalog. Then a page on the site shows it.

Memory is the constraint to respect: the box has 2 GB. Load only the columns
the table needs, as `fcc_data.build` does.
