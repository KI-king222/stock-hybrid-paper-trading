"""Streamlit: Hybrid Paper Trading."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state"

st.set_page_config(page_title="Hybrid Paper Trading", page_icon="🔗", layout="wide")
st.title("Hybrid Paper Trading (Variante A)")
st.caption("Algo schlägt vor · KI darf blocken oder halbieren · eigenes Depot")


def load(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


pf = load(STATE / "portfolio_state.json")
status = load(STATE / "last_run_status.json")
log = load(STATE / "hybrid_log.json")
gate = load(ROOT / "signals" / "ki_gate.json")

if status:
    st.info(status.get("headline", status.get("last_run", "")))
else:
    st.warning("Noch kein Hybrid-Lauf – Actions **Run Hybrid Daily** starten.")

if pf:
    cash = float(pf.get("cash") or 0)
    ext = float(pf.get("external_profit") or 0)
    positions = pf.get("positions") or {}
    equity = cash + sum(
        float(p.get("shares", 0)) * float(p.get("current_price") or p.get("avg_cost") or 0)
        for p in positions.values()
    )
    wealth = equity + ext
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gesamtvermögen", f"{wealth:,.2f} €")
    c2.metric("Equity", f"{equity:,.2f} €")
    c3.metric("Cash", f"{cash:,.2f} €")
    c4.metric("Realisierter Gewinn", f"{ext:,.2f} €")

    st.subheader("Positionen")
    if positions:
        rows = []
        for t, p in positions.items():
            sh = float(p["shares"])
            avg = float(p["avg_cost"])
            px = float(p.get("current_price") or avg)
            rows.append(
                {
                    "Ticker": t,
                    "Stück": sh,
                    "Ø": round(avg, 2),
                    "Kurs": round(px, 2),
                    "P&L %": round((px / avg - 1) * 100, 2) if avg else 0,
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.write("Keine Positionen.")

st.subheader("KI-Gate")
if gate:
    st.write(f"**Blocks:** {gate.get('blocks') or '–'}")
    st.write(f"**Half:** {gate.get('half') or '–'}")
    st.caption(gate.get("notes") or "")
else:
    st.write("Keine ki_gate.json")

st.subheader("Letzte Hybrid-Entscheidungen")
if log and log.get("runs"):
    last = log["runs"][-1]
    st.write(last.get("source"), last.get("date"))
    st.dataframe(pd.DataFrame(last.get("decisions") or []), use_container_width=True, hide_index=True)
else:
    st.write("Noch kein Log.")

st.caption("Repos: KI-king222/stock-hybrid-paper-trading")
