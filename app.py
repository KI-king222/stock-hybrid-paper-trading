"""Streamlit Hybrid – Live-Kurse und Charts immer in EUR."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict

import pandas as pd
import streamlit as st
import yfinance as yf

from charts import render_position_charts
from fx import to_eur, native_currency

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
st.caption(
    "Variante A · **Kurse in EUR** (US via FX) · Charts live · Trades nach Hybrid-Workflow"
)


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


def last_action_date(trades, ticker) -> str:
    for tr in reversed(trades or []):
        if tr.get("ticker") == ticker:
            return fmt_dt(tr.get("date"))
    return "–"


def fetch_live_prices(tickers) -> Dict[str, float]:
    """Immer EUR."""
    out = {}
    for t in tickers:
        try:
            h = yf.Ticker(t).history(period="5d")
            if h is None or h.empty:
                continue
            p = float(h["Close"].dropna().iloc[-1])
            if math.isfinite(p) and p > 0:
                out[t] = round(to_eur(p, t), 4)
        except Exception:
            pass
    return out


pf = load(STATE / "portfolio_state.json")
status = load(STATE / "last_run_status.json")
log = load(STATE / "hybrid_log.json")
gate = load(ROOT / "signals" / "ki_gate.json")
wl = load(ROOT / "signals" / "watchlist.json")
cfg = load(ROOT / "config.json") or {}
rules_md = ""
if (ROOT / "RULES.md").exists():
    rules_md = (ROOT / "RULES.md").read_text(encoding="utf-8")

positions = (pf or {}).get("positions") or {}
trades = (pf or {}).get("trades") or []

live_ok = False
if positions:
    live = fetch_live_prices(list(positions.keys()))
    if live:
        live_ok = True
        for t, p in live.items():
            if t in positions:
                positions[t]["current_price"] = p

if live_ok:
    st.caption("Kurse: **live in EUR** (US umgerechnet) · Bestand: letzter Hybrid-Lauf")
elif positions:
    st.caption("Kurse: gespeicherter Stand (Live-Abruf fehlgeschlagen)")

if pf:
    cash = float(pf.get("cash") or 0)
    ext = float(pf.get("external_profit") or 0)
    start = float(pf.get("starting_cash") or 10_000)
    positions_mv = 0.0
    positions_cost = 0.0
    for p in positions.values():
        sh = float(p.get("shares", 0))
        avg = float(p.get("avg_cost") or 0)
        px = float(p.get("current_price") or avg)
        positions_mv += sh * px
        positions_cost += sh * avg
    laufendes_depot = cash + positions_mv
    gesamtvermoegen = laufendes_depot + ext
    unrealisiert = positions_mv - positions_cost
    vs_start_ohne_lohn = laufendes_depot - start
    vs_start_gesamt = gesamtvermoegen - start

    st.markdown("#### Kennzahlen")
    st.caption("Alle Kurse/Einstände in **EUR**.")

    r1 = st.columns(4)
    r1[0].metric("Gesamtvermögen", f"{gesamtvermoegen:,.2f} €", f"{vs_start_gesamt:+.2f} € vs. Start")
    r1[1].metric("Laufendes Depot", f"{laufendes_depot:,.2f} €", f"{vs_start_ohne_lohn:+.2f} € vs. Start")
    r1[2].metric("Offene Aktien (Kurswert)", f"{positions_mv:,.2f} €", f"{unrealisiert:+.2f} € P&L")
    r1[3].metric(
        "Offene Aktien P&L",
        f"{unrealisiert:+.2f} €",
        f"{(unrealisiert/positions_cost*100) if positions_cost else 0:+.1f}%",
    )

    r2 = st.columns(3)
    r2[0].metric("Investierbares Cash", f"{cash:,.2f} €")
    r2[1].metric("Gesperrter Lohn", f"{ext:,.2f} €")
    r2[2].metric("Startkapital", f"{start:,.0f} €")
else:
    st.write("Kein portfolio_state.json – noch kein Lauf.")

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
        opened = fmt_dt(p.get("opened_at")) if p.get("opened_at") else first_buy_date(trades, t)
        last_a = fmt_dt(p.get("last_action_at")) if p.get("last_action_at") else last_action_date(trades, t)
        rows.append({
            "Ticker": t,
            "Kaufdatum": opened,
            "Letzte Aktion": last_a,
            "Stück": sh,
            "Einstand €": round(avg, 2),
            "Kurs €": round(px, 2),
            "Wert €": round(sh * px, 2),
            "P&L €": round(pnl, 2),
            "P&L %": round(pct, 2),
            "Notiz": "US→EUR" if native_currency(t) != "EUR" else "",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.write("Keine Positionen.")

st.divider()
st.subheader("Watchlist")
if wl and wl.get("items"):
    items = [i for i in wl["items"] if i.get("status", "active") == "active"]
    if items:
        st.dataframe(
            pd.DataFrame([{
                "Ticker": i.get("ticker"), "Name": i.get("title"),
                "Priorität": i.get("priority"), "Seit": i.get("added_at"),
                "Grund": i.get("reason"),
            } for i in sorted(items, key=lambda x: x.get("priority") or 99)]),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("Keine aktiven Einträge")
else:
    st.info("Noch leer.")

st.divider()
st.subheader("Letzter Lauf")
if status:
    st.info(status.get("headline") or status.get("last_run") or "")
else:
    st.warning("Noch kein Hybrid-Lauf.")

st.divider()
render_position_charts(positions)

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
else:
    st.write("Noch keine Trades.")

if log and log.get("runs"):
    st.markdown("**Hybrid-Läufe**")
    for run in reversed(log["runs"][-20:]):
        date = fmt_dt(run.get("date"))
        with st.expander(f"Hybrid: {date} – Vermögen {run.get('wealth', '–')} €", expanded=False):
            if run.get("decisions"):
                st.dataframe(pd.DataFrame(run["decisions"]), use_container_width=True, hide_index=True)

st.divider()
st.subheader("Letzte Entscheidungen")
if log and log.get("runs"):
    last = log["runs"][-1]
    st.write(f"**{fmt_dt(last.get('date'))}** · {last.get('source', '')}")
    if last.get("decisions"):
        st.dataframe(pd.DataFrame(last["decisions"]), use_container_width=True, hide_index=True)

st.subheader("KI-Gate")
if gate:
    st.write(f"**Blocks:** {gate.get('blocks') or '–'}")
    st.write(f"**Half:** {gate.get('half') or '–'}")
    st.caption(gate.get("notes") or "")
else:
    st.write("Keine ki_gate.json")

st.caption("Paper-Trading · Keine Anlageberatung · Basiswährung EUR")
