# Options Surface Lab -- UUUU

MENG FinTech, Algorithmic Trading II -- Assignment 1.1.

**Live site (GitHub Pages):** `https://chuyuqin.github.io/Adv-Algorithmic-Trading/`

## Note to the instructor -- data status on submission

The pipeline, parsing, stats, and app below are all complete and running
end to end. The one piece missing is a real LSEG pull: I did not have
access to LSEG Workspace over the weekend to authenticate a session and
pull real expired-contract history, so `option_pipeline_data.pkl` in this
submission is a **synthesized stand-in**, not real LSEG data.

The synthetic panel is built to match the real thing's shape and behavior
on purpose -- correct RIC scheme, the same sparsity pattern (MID_PRICE far
more common than TRDPRC_1, density falling off with moneyness/DTE), same
column structure a real `get_history()` batch pull would return -- so that
everything downstream (the parser, the tidy table, the two required stats,
the 3D surface, the app itself) is real code doing real work on realistic
data, just not on data that actually traded. That's flagged explicitly
everywhere: `payload["synthetic"] = True` in the cache, and the page itself
prints "synthetic demo panel" in its header rather than claiming otherwise.

**Plan:** I'll be on campus Tuesday when class resumes and will get LSEG
Workspace access sorted with the help desk / in office hours, then re-run
`fetch_data.py` against a real session and push the update. I wanted to
turn in a working, complete app on time rather than hold up the whole
submission for the data pull specifically.

## What this is

`index.html` is a self-contained, static page (Plotly.js embedded inline --
no CDN, no server) that:

1. Loads the cached options data (`option_pipeline_data.pkl`).
2. Parses every RIC into `{underlying, expiry, put/call, strike}` and melts
   it into a tidy long table, one row per contract per date
   (`parse_option_ric()` in `option_surface_utils.py`).
3. Shows a 3D surface of calls or puts for a selected as-of date.
4. Plots both `MID_PRICE` and `TRDPRC_1` side by side so it's obvious they
   are not the same series.
5. Prints, per as-of date: the percent of listed series with a mid and no
   trade, and the median `|MID_PRICE - TRDPRC_1|` on series that have both.
6. Uses its own graphical identity (dark ink background, amber = mark,
   teal = print) instead of the generic starter palette, plus an as-of-date
   dropdown and a Calls/Puts toggle as the interactive widget switches.

Three required sentences of commentary are under the plots on the page
itself.

## Field note: MID_PRICE, not SETTLE

The starter kit this repo was scaffolded from used `SETTLE` as the "mark"
field. The Canvas assignment text supersedes that: LSEG does not expose a
real exchange settlement price for expired US equity options here (`SETTLE`
returns "universe does not support" on this RIC space), so this build uses
`MID_PRICE` (closing NBBO midpoint) as the mark throughout -- every file,
plot, and label was updated accordingly.

## Files

| File | What it is |
|---|---|
| `index.html` | The GitHub Pages deliverable. Self-contained, static, no backend. |
| `options_surface_app.py` | The live Reflex app (same logic, interactive widgets) for local dev and the in-class checkpoint demo: `reflex run`. |
| `option_surface_utils.py` | RIC parsing, tidy-table building, the two required stats, and the synthetic-data fallback. |
| `option_surface_plots.py` | All Plotly figure builders (candlestick, 3D surface, mid-vs-trade, occupancy heatmaps). |
| `fetch_data.py` | Standalone data pull/cache step. |
| `build_preview.py` | Regenerates `index.html` from whatever's in `option_pipeline_data.pkl`. |
| `option_pipeline_data.pkl` | The cache -- currently the synthetic UUUU-like panel described above. |
| `STARTER_README.md` | The original course starter's README, kept for reference. |

## Why UUUU

Energy Fuels (UUUU) is a small-cap name that trades on a coarse ($0.50-ish)
strike grid with mostly-sparse, largely monthly expired listings -- exactly
the "see the holes" case this assignment is about, unlike a liquid name
where every strike prints every day.

## Local dev / swapping in the real pull

```bash
pip install -r requirements.txt
rm option_pipeline_data.pkl   # only if re-pulling
python fetch_data.py          # requires LSEG Workspace open + logged in,
                               # and `lseg-data` (or legacy `eikon`) installed
python build_preview.py       # regenerates index.html from the cache
open index.html                # or just double-click it
# or, for the interactive Reflex version:
reflex run
```

If `lseg.data` isn't importable or the session can't open, `fetch_data.py`
prints that and falls back to the synthetic panel again -- it will never
silently claim synthetic data is real.
