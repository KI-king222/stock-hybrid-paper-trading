"""Streamlit Hybrid – Live-Kurse EUR, Charts v5 Einstand am Kauftag."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict

import pandas as pd
import streamlit as st

from charts import render_position_charts, CHART_VERSION
from fx import to_eur, native_currency, raw_live_price

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state"

st.set_page_config(page_title="Hybrid Paper Trading", page_icon="🔗", layout="wide")
st.markdown(
    """
<style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    div[data-testid="stPlotlyChart"] { margin-bottom: 0.8rem; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("🔗 Hybrid Paper Trading")
st.caption(f"Live-Kurse EUR · Charts **{CHART_VERSION}** · Einstand am Kauftag")


def load(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def fmt_dt(s) -> str:
    if not s:
        return "–"
    return str(s).replace("T", " ")[:19]


def first_buy_date(trades, ticker) -> str:
    for tr in trades or []:
        if tr.get("ticker") == ticker and str(tr.get("action")).lower() == "buy":
            return fmt_dt(tr.get("date"))
    return "–"


def fetch_live_prices(tickers) -> Dict[str, float]:
    out = {}
    for t in tickers:
        try:
            raw = raw_live_price(t)
            if raw is not None and math.isfinite(raw) and raw > 0:
                out[t] = round(to_eur(raw, t), 4)
        except Exception:
            pass
    return out


pf = load(STATE / "portfolio_state.json")
status = load(STATE / "last_run_status.json")
trades = (pf or {}).get("trades") or []
positions = (pf or {}).get("positions") or {}

live_ok = False
if positions:
    live = fetch_live_prices(list(positions.keys()))
    if live:
        live_ok = True
        for t, p in live.items():
            if t in positions:
                positions[t]["current_price"] = p

if live_ok:
    st.success("Live-Kurse geladen")
elif positions:
    st.warning("Live-Kurse nicht geladen – gespeicherter Stand")

if pf:
    cash = float(pf.get("cash") or 0)
    ext = float(pf.get("external_profit") or 0)
    start = float(pf.get("starting_cash") or 10_000)
    positions_mv = positions_cost = 0.0
    for p in positions.values():
        sh = float(p.get("shares", 0))
        avg = float(p.get("avg_cost") or 0)
        px = float(p.get("current_price") or avg)
        positions_mv += sh * px
        positions_cost += sh * avg
    laufendes_depot = cash + positions_mv
    gesamtvermoegen = laufendes_depot + ext
    unrealisiert = positions_mv - positions_cost

    r1 = st.columns(4)
    r1[0].metric("Gesamtvermögen", f"{gesamtvermoegen:,.2f} €", f"{gesamtvermoegen-start:+.2f} €")
    r1[1].metric("Laufendes Depot", f"{laufendes_depot:,.2f} €")
    r1[2].metric("Offene Aktien", f"{positions_mv:,.2f} €", f"{unrealisiert:+.2f} €")
    r1[3].metric("Cash / Lohn", f"{cash:,.0f} / {ext:,.0f} €")

st.divider()
st.subheader("Offene Positionen")
if positions:
    rows = []
    for t, p in positions.items():
        sh = float(p["shares"])
        avg = float(p["avg_cost"])
        px = float(p.get("current_price") or avg)
        pnl = sh * px - sh * avg
        pct = (px / avg - 1) * 100 if avg else 0
        rows.append({
            "Ticker": t,
            "Kaufdatum": fmt_dt(p.get("opened_at")) if p.get("opened_at") else first_buy_date(trades, t),
            "Stück": sh,
            "Einstand €": round(avg, 2),
            "Kurs €": round(px, 2),
            "Wert €": round(sh * px, 2),
            "P&L €": round(pnl, 2),
            "P&L %": round(pct, 2),
            "Notiz": "US→EUR" if native_currency(t) != "EUR" else "",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.divider()
if status:
    st.info(status.get("headline") or status.get("last_run") or "")

st.divider()
render_position_charts(positions, trades=trades)

st.divider()
st.subheader("Trade-Historie")
if trades:
    st.dataframe(pd.DataFrame([{
        "Datum": fmt_dt(t.get("date")),
        "Aktion": str(t.get("action") or "").upper(),
        "Ticker": t.get("ticker"),
        "Stück": t.get("shares"),
        "Kurs €": round(float(t.get("price") or 0), 2),
        "Begründung": t.get("reason") or "",
    } for t in trades]), use_container_width=True, hide_index=True)

st.caption("Paper-Trading · Basiswährung EUR")
