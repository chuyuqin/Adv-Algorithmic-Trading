"""
Generate the standalone GitHub Pages HTML for the Options Surface Lab
(no Reflex server required -- this is what actually gets pushed and rendered
on GitHub Pages; options_surface_app.py is the live Reflex version used for
local dev / the in-class checkpoint demo).

Widget switches: an as-of-date dropdown and a Calls/Puts toggle drive the
3D surface, its two occupancy heatmaps, and the mid-vs-trade comparison
panel -- all pre-rendered client-side combinations, toggled with a small
inline script, so the page stays fully static.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.io as pio

from option_surface_plots import (
    candlestick_figure,
    coverage_heatmap,
    price_surface_figure,
    mid_vs_trade_figure,
)
from option_surface_utils import (
    attach_underlying,
    flatten_lseg_options,
    load_payload,
    summarize_sparsity,
    pivot_trade_mid,
)

N_SAMPLE_DATES = 6  # evenly spaced as-of dates offered in the dropdown


def _sample_dates(all_dates: list[pd.Timestamp], n: int) -> list[pd.Timestamp]:
    if len(all_dates) <= n:
        return all_dates
    idx = [round(i * (len(all_dates) - 1) / (n - 1)) for i in range(n)]
    seen, out = set(), []
    for i in idx:
        if i not in seen:
            seen.add(i)
            out.append(all_dates[i])
    return out


def _card(label: str, value) -> str:
    return (
        "<div class='card'>"
        f"<div class='card-label'>{label}</div>"
        f"<div class='card-value'>{value}</div>"
        "</div>"
    )


def main() -> Path:
    payload = load_payload("option_pipeline_data.pkl")
    tidy = flatten_lseg_options(payload["options"])
    tidy = attach_underlying(tidy, payload["stock"])
    wide = pivot_trade_mid(tidy)
    ticker = payload.get("ticker", "UUUU")

    all_dates = sorted(wide["date"].unique()) if len(wide) else []
    sample_dates = _sample_dates(all_dates, N_SAMPLE_DATES)
    latest = sample_dates[-1] if sample_dates else None

    overall_stats = summarize_sparsity(wide)
    latest_stats = summarize_sparsity(wide[wide["date"] == latest]) if latest is not None else overall_stats

    fig_cs = candlestick_figure(payload["stock"], ticker)
    plotly_js_written = False

    def fig_html(fig) -> str:
        nonlocal plotly_js_written
        html = pio.to_html(fig, full_html=False, include_plotlyjs=(True if not plotly_js_written else False))
        plotly_js_written = True
        return html

    candlestick_html = fig_html(fig_cs)

    panels = []  # (date_str, cp) -> surface + 2 heatmaps, shown/hidden by JS
    compare_panels = []  # date_str -> compare figure
    per_date_stats = {}

    for d in sample_dates:
        d_str = str(pd.Timestamp(d).date())
        sl = wide[wide["date"] == d]
        per_date_stats[d_str] = summarize_sparsity(sl)
        compare_panels.append(
            f"<div class='snapshot compare' data-date='{d_str}'>{fig_html(mid_vs_trade_figure(wide, d, ticker=ticker))}</div>"
        )
        for cp in ("C", "P"):
            surf = fig_html(price_surface_figure(wide, d, cp=cp, ticker=ticker))
            heat_mid = fig_html(coverage_heatmap(wide, d, cp=cp, field="MID_PRICE"))
            heat_trade = fig_html(coverage_heatmap(wide, d, cp=cp, field="TRDPRC_1"))
            panels.append(
                f"<div class='snapshot surface' data-date='{d_str}' data-cp='{cp}'>{surf}</div>"
            )
            panels.append(
                f"<div class='snapshot heat' data-date='{d_str}' data-cp='{cp}'>"
                f"<div class='heat-pair'><div>{heat_mid}</div><div>{heat_trade}</div></div></div>"
            )

    date_options = "".join(
        f"<option value='{str(pd.Timestamp(d).date())}'{' selected' if d == latest else ''}>"
        f"{str(pd.Timestamp(d).date())}</option>"
        for d in sample_dates
    )

    out = Path(__file__).resolve().parent / "index.html"

    synth_note = (
        "synthetic demo panel -- delete option_pipeline_data.pkl and re-run fetch_data.py "
        "with LSEG Workspace open to replace this with a real pull"
        if payload.get("synthetic")
        else f"loaded from option_pipeline_data.pkl (fetched {payload.get('fetched_at', '?')})"
    )

    overall_pct = overall_stats["pct_mid_no_trade"]
    overall_med = overall_stats["median_abs_diff"]
    overall_med_txt = "n/a" if overall_med is None else f"${overall_med:.3f}"

    commentary = f"""
      <ol class="commentary">
        <li>The cloud is densest within roughly +/-15% of spot on the nearest one or two expiries;
            it thins fast in the wings and on far-dated contracts, where most strikes on this
            {ticker} $0.50 grid never see a trade and often never see a mid either -- that is the
            "hole" the assignment asks us to actually look at rather than assume away.</li>
        <li>Interpolating across those empty cells is dangerous here specifically because the
            $0.50 strike step on a roughly single-digit-dollar name like {ticker} is a large fraction
            of the underlying's price, so a straight line between two real quotes several strikes
            apart can imply a smooth, liquid market that never actually existed at any strike in between.</li>
        <li>Next week the mark we price off of is MID_PRICE (the closing NBBO mid -- LSEG has no true
            settlement price for expired equity options here), and TRDPRC_1 stays what it is: evidence
            that a trade actually happened, not a price we can assume is available on demand.</li>
      </ol>
    """

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{ticker} Option Surface -- Where the Quotes Run Out</title>
<style>
  :root {{
    --bg: #14110f; --panel: #1e1a17; --grid: #3a332d;
    --ink: #f2ede6; --muted: #a89a8c; --amber: #f2b84b; --teal: #4fb0a8;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--ink);
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }}
  header {{ padding: 32px 32px 12px 32px; max-width: 1100px; }}
  h1 {{ color: var(--amber); letter-spacing: 2px; font-size: 22px; margin: 0 0 4px 0; }}
  .subtitle {{ color: var(--muted); margin: 0 0 14px 0; line-height: 1.5; max-width: 820px; }}
  .cards {{ display: flex; gap: 16px; flex-wrap: wrap; margin: 12px 0 20px 0; }}
  .card {{ background: var(--panel); border: 1px solid var(--grid); border-radius: 8px;
           padding: 12px 16px; min-width: 150px; }}
  .card-label {{ color: var(--muted); font-size: 12px; }}
  .card-value {{ color: var(--amber); font-size: 22px; font-weight: 700; }}
  .controls {{ display: flex; gap: 20px; align-items: center; flex-wrap: wrap;
               padding: 4px 32px 16px 32px; max-width: 1100px; }}
  .controls label {{ color: var(--muted); font-size: 13px; margin-right: 6px; }}
  select, .toggle button {{
    background: var(--panel); color: var(--ink); border: 1px solid var(--grid);
    border-radius: 6px; padding: 6px 10px; font-family: inherit; font-size: 13px;
  }}
  .toggle {{ display: inline-flex; border: 1px solid var(--grid); border-radius: 6px; overflow: hidden; }}
  .toggle button {{ border: none; border-radius: 0; cursor: pointer; }}
  .toggle button.active {{ background: var(--amber); color: #14110f; font-weight: 700; }}
  main {{ padding: 0 32px 40px 32px; max-width: 1100px; }}
  .block {{ background: var(--panel); border: 1px solid var(--grid); border-radius: 8px;
            padding: 1rem; margin-bottom: 20px; }}
  .snapshot {{ display: none; }}
  .snapshot.active {{ display: block; }}
  .heat-pair {{ display: flex; gap: 12px; }}
  .heat-pair > div {{ width: 50%; }}
  .commentary {{ color: var(--ink); line-height: 1.6; padding-left: 20px; }}
  .commentary li {{ margin-bottom: 8px; }}
  footer {{ color: var(--muted); padding: 0 32px 32px 32px; font-size: 12px; max-width: 1100px; }}
</style>
</head>
<body>
<header>
  <h1>{ticker} -- WHERE THE QUOTES RUN OUT</h1>
  <p class="subtitle">
    Assignment 1.1, Option Surface Lab. Data source: {synth_note}.
    Amber = MID_PRICE (closing NBBO mid, the closest thing to a mark-of-close for expired
    {ticker} equity options). Teal = TRDPRC_1 (an actual last trade -- one print, not a mark).
    The translucent sheet on the 3D plot is a linear interpolation of MID_PRICE only; it is a
    convenience for the eye, not a market, and can be switched off would-be strikes were never quoted.
  </p>
  <div class="cards">
    {_card('Underlying', ticker)}
    {_card('Series parsed', overall_stats['n_series'])}
    {_card('As-of dates in window', overall_stats['n_dates'])}
    {_card('Overall: mid, no print', f"{overall_pct:.0f}%")}
    {_card('Overall median |mid - trade|', overall_med_txt)}
  </div>
</header>

<div class="controls">
  <div><label for="date-select">As-of date</label>
    <select id="date-select">{date_options}</select>
  </div>
  <div><label>Contract side</label>
    <span class="toggle">
      <button data-cp="C" class="active">Calls</button><button data-cp="P">Puts</button>
    </span>
  </div>
  <div id="live-stats" style="color: var(--muted); font-size: 13px;"></div>
</div>

<main>
  <div class="block">{candlestick_html}</div>

  <div class="block">
    <div id="surface-panels">{''.join(p for p in panels if 'surface' in p)}</div>
  </div>

  <div class="block">
    <p style="color: var(--muted); font-size: 13px; margin-top: 0;">
      MID_PRICE vs. TRDPRC_1 for the selected as-of date -- points off the dashed y=x line are
      places where the mark and the print disagree; the bar chart is the honest headcount of how
      many series that day had a mid with no print at all.
    </p>
    <div id="compare-panels">{''.join(compare_panels)}</div>
  </div>

  <div class="block">
    <p style="color: var(--muted); font-size: 13px; margin-top: 0;">
      Occupancy: lit cells had a real number that day, dark cells did not.
    </p>
    <div id="heat-panels">{''.join(p for p in panels if 'heat' in p)}</div>
  </div>

  <div class="block">
    <h3 style="margin-top:0; color: var(--amber);">Three sentences</h3>
    {commentary}
  </div>
</main>

<footer>
  Built for MENG FinTech, Algorithmic Trading II -- Assignment 1.1. See README.md for how the
  data is fetched/cached and how to regenerate this page after a real LSEG pull.
</footer>

<script>
const PER_DATE_STATS = {json.dumps(per_date_stats)};

function fmtPct(x) {{ return (x === null || x === undefined) ? 'n/a' : x.toFixed(0) + '%'; }}
function fmtUsd(x) {{ return (x === null || x === undefined) ? 'n/a' : '$' + x.toFixed(3); }}

function currentCp() {{
  return document.querySelector('.toggle button.active').dataset.cp;
}}

function render() {{
  const date = document.getElementById('date-select').value;
  const cp = currentCp();

  document.querySelectorAll('#surface-panels .snapshot, #heat-panels .snapshot').forEach(el => {{
    el.classList.toggle('active', el.dataset.date === date && el.dataset.cp === cp);
  }});
  document.querySelectorAll('#compare-panels .snapshot').forEach(el => {{
    el.classList.toggle('active', el.dataset.date === date);
  }});

  // Let Plotly resize now-visible plots (they were rendered while hidden).
  document.querySelectorAll('.snapshot.active .js-plotly-plot').forEach(gd => {{
    if (window.Plotly) window.Plotly.Plots.resize(gd);
  }});

  const s = PER_DATE_STATS[date];
  if (s) {{
    document.getElementById('live-stats').textContent =
      `On ${{date}}: ${{s.n_quotes}} listed series -- ${{fmtPct(s.pct_mid_no_trade)}} have a mid and no trade -- median |mid - trade| where both exist: ${{fmtUsd(s.median_abs_diff)}}`;
  }}
}}

document.getElementById('date-select').addEventListener('change', render);
document.querySelectorAll('.toggle button').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.toggle button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    render();
  }});
}});

render();
</script>
</body>
</html>
"""

    out.write_text(html, encoding="utf-8")
    print(
        f"Wrote {out}  dates_sampled={len(sample_dates)}  synthetic={payload.get('synthetic')}  "
        f"overall_pct_mid_no_trade={overall_pct:.1f}%  overall_median_abs_diff={overall_med_txt}"
    )
    return out


if __name__ == "__main__":
    main()
