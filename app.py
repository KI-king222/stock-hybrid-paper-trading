"""Streamlit Hybrid – Anordnung wie gewünscht."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from charts import render_position_charts

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

# --- 1) Titel + Caption ---
st.title("🔗 Hybrid Paper Trading")
st.caption("Variante A · Algo schlägt vor · KI blockt oder halbieren · eigenes Depot")


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


pf = load(STATE / "portfolio_state.json")
status = load(STATE / "last_run_status.json")
log = load(STATE / "hybrid_log.json")
gate = load(ROOT / "signals" / "ki_gate.json")
cfg = load(ROOT / "config.json") or {}
rules_md = ""
if (ROOT / "RULES.md").exists():
    rules_md = (ROOT / "RULES.md").read_text(encoding="utf-8")

positions = (pf or {}).get("positions") or {}
trades = (pf or {}).get("trades") or []

# --- 2) Kennzahlen ---
if pf:
    cash = float(pf.get("cash") or 0)
    ext = float(pf.get("external_profit") or 0)
    start = float(pf.get("starting_cash") or 10_000)
    equity = cash + sum(
        float(p.get("shares", 0)) * float(p.get("current_price") or p.get("avg_cost") or 0)
        for p in positions.values()
    )
    wealth = equity + ext
    pnl = wealth - start
    pnl_pct = (pnl / start * 100) if start else 0.0
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Startkapital", f"{start:,.0f} €")
    c2.metric("Gesamtvermögen", f"{wealth:,.2f} €", f"{pnl:+.2f} €")
    c3.metric("Performance", f"{pnl_pct:+.2f} %")
    c4.metric("Cash", f"{cash:,.2f} €")
    c5.metric("Realisierter Gewinn", f"{ext:,.2f} €")
else:
    st.write("Kein portfolio_state.json – noch kein Lauf.")

# --- 3) Offene Positionen ---
st.divider()
st.subheader("Offene Positionen")
if positions:
    rows = []
    for t, p in positions.items():
        sh = float(p["shares"])
        avg = float(p["avg_cost"])
        px = float(p.get("current_price") or avg)
        pct = (px / avg - 1) * 100 if avg else 0
        opened = fmt_dt(p.get("opened_at")) if p.get("opened_at") else first_buy_date(trades, t)
        last_a = fmt_dt(p.get("last_action_at")) if p.get("last_action_at") else last_action_date(trades, t)
        rows.append({
            "Ticker": t, "Kaufdatum": opened, "Letzte Aktion": last_a,
            "Stück": sh, "Einstand": round(avg, 2), "Kurs": round(px, 2),
            "Wert": round(sh * px, 2), "P&L %": round(pct, 2),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.write("Keine Positionen.")

# --- 4) Letzter Lauf ---
st.divider()
st.subheader("Letzter Lauf")
if status:
    st.info(status.get("headline") or status.get("last_run") or "")
else:
    st.warning("Noch kein Hybrid-Lauf – Actions **Run Hybrid Daily** starten.")

# --- 5) Graphen ---
st.divider()
render_position_charts(positions)

# --- 6) Trade History ---
st.divider()
st.subheader("Trade-Historie / Change-Katalog")
if trades:
    trade_rows = [{
        "Datum": fmt_dt(t.get("date")),
        "Aktion": str(t.get("action") or "").upper(),
        "Ticker": t.get("ticker"),
        "Stück": t.get("shares"),
        "Kurs": round(float(t.get("price") or 0), 2),
        "Begründung": t.get("reason") or "",
    } for t in trades]
    st.dataframe(pd.DataFrame(trade_rows), use_container_width=True, hide_index=True)
else:
    st.write("Noch keine Trades.")

if log and log.get("runs"):
    st.markdown("**Hybrid-Läufe**")
    for run in reversed(log["runs"][-20:]):
        date = fmt_dt(run.get("date"))
        with st.expander(f"Hybrid: {date} – Vermögen {run.get('wealth', '–')} €", expanded=False):
            st.write(run.get("source") or "")
            dec = run.get("decisions") or []
            if dec:
                st.dataframe(pd.DataFrame(dec), use_container_width=True, hide_index=True)

# --- 7) Letzte Entscheidungen (Gate + Decisions aus letztem Lauf) ---
st.divider()
st.subheader("Letzte Entscheidungen")
if log and log.get("runs"):
    last = log["runs"][-1]
    st.write(f"**{fmt_dt(last.get('date'))}** · {last.get('source', '')}")
    if last.get("decisions"):
        st.dataframe(pd.DataFrame(last["decisions"]), use_container_width=True, hide_index=True)
else:
    st.write("Noch keine Entscheidungen.")

st.subheader("KI-Gate (aktuell)")
if gate:
    st.write(f"**Blocks:** {gate.get('blocks') or '–'}")
    st.write(f"**Half:** {gate.get('half') or '–'}")
    st.caption(gate.get("notes") or "")
else:
    st.write("Keine ki_gate.json")

# --- 8) Rest: Regelwerk ---
st.divider()
st.subheader("Regelwerk")
with st.expander("Hybrid-Regeln (Variante A)", expanded=False):
    st.markdown(
        """
**Algo** liefert Signale. **KI-Gate** darf nur **block** oder **half**.  
Leeres Depot → Startkauf score-gewichtet. Kein Auto-Verkauf im Minus. Gebühr 1 € (Paper).
"""
    )
with st.expander("Config", expanded=False):
    st.json(cfg) if cfg else st.write("–")
with st.expander("RULES.md", expanded=False):
    st.markdown(rules_md) if rules_md else st.write("–")

st.caption("Paper-Trading · Keine Anlageberatung")
