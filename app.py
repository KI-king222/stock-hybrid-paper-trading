"""Streamlit Hybrid Paper Trading – Charts, Change-Katalog, Regelwerk."""
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
st.title("🔗 Hybrid Paper Trading")
st.caption("Variante A · Algo schlägt vor · KI blockt oder halbiert · eigenes Depot")


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
cfg = load(ROOT / "config.json") or {}
rules_md = ""
rules_path = ROOT / "RULES.md"
if rules_path.exists():
    rules_md = rules_path.read_text(encoding="utf-8")

if status:
    st.info(status.get("headline") or status.get("last_run") or "")
else:
    st.warning("Noch kein Hybrid-Lauf – Actions **Run Hybrid Daily** starten.")

# --- Kennzahlen ---
if pf:
    cash = float(pf.get("cash") or 0)
    ext = float(pf.get("external_profit") or 0)
    start = float(pf.get("starting_cash") or 10_000)
    positions = pf.get("positions") or {}
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

    st.divider()
    st.subheader("Offene Positionen")
    if positions:
        rows = []
        for t, p in positions.items():
            sh = float(p["shares"])
            avg = float(p["avg_cost"])
            px = float(p.get("current_price") or avg)
            pct = (px / avg - 1) * 100 if avg else 0
            rows.append(
                {
                    "Ticker": t,
                    "Stück": sh,
                    "Einstand": round(avg, 2),
                    "Kurs": round(px, 2),
                    "Wert": round(sh * px, 2),
                    "P&L %": round(pct, 2),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.write("Keine Positionen.")

    st.divider()
    render_position_charts(positions)
else:
    st.write("Kein portfolio_state.json – noch kein Lauf.")

# --- KI-Gate ---
st.divider()
st.subheader("KI-Gate (aktuell)")
if gate:
    st.write(f"**Blocks:** {gate.get('blocks') or '–'}")
    st.write(f"**Half:** {gate.get('half') or '–'}")
    st.caption(gate.get("notes") or "")
else:
    st.write("Keine ki_gate.json")

# --- Change-Katalog ---
st.divider()
st.subheader("Change-Katalog")
st.caption("Hybrid-Läufe und ausgeführte Trades")

if log and log.get("runs"):
    for run in reversed(log["runs"][-30:]):
        date = str(run.get("date") or "")[:19].replace("T", " ")
        title = f"Hybrid: {date} – Vermögen {run.get('wealth', '–')} €"
        with st.expander(title, expanded=False):
            st.write(run.get("source") or "")
            dec = run.get("decisions") or []
            if dec:
                st.dataframe(pd.DataFrame(dec), use_container_width=True, hide_index=True)
            st.caption(
                f"Cash {run.get('cash')} · Equity {run.get('equity')} · "
                f"Positionen: {', '.join(run.get('positions') or []) or '–'}"
            )
else:
    st.info("Noch keine Hybrid-Läufe im Log.")

if pf and pf.get("trades"):
    st.markdown("**Alle Trades (Kauf/Verkauf)**")
    trade_rows = []
    for t in pf["trades"]:
        trade_rows.append(
            {
                "Datum": str(t.get("date") or "")[:19].replace("T", " "),
                "Aktion": str(t.get("action") or "").upper(),
                "Ticker": t.get("ticker"),
                "Stück": t.get("shares"),
                "Kurs": round(float(t.get("price") or 0), 2),
                "Begründung": t.get("reason") or "",
            }
        )
    st.dataframe(pd.DataFrame(trade_rows), use_container_width=True, hide_index=True)

# --- Regelwerk ---
st.divider()
st.subheader("Regelwerk")

with st.expander("Hybrid-Regeln (Variante A) – ausführlich", expanded=True):
    st.markdown(
        """
### Rollen
1. **Algo** (`stock-algo-paper-trading`) liefert Signale: kaufen, nachkaufen, reinvestieren, teilverkauf, halten.  
2. **KI-Gate** darf nur:
   - **block** – Trade findet nicht statt  
   - **half** – Stückzahl wird halbiert  
3. Ohne Gate-Eintrag wird der **Algo-Vorschlag** (bei leerem Depot: Startkauf) ausgeführt.

### Startkauf
- Wenn das Hybrid-Depot **leer** ist: score-gewichteter Kauf aus dem Universum (wie Algo-Start).  
- KI-Gate kann einzelne Ticker blocken oder halbieren.

### Nach dem Start
- Nur Signale aus dem letzten Algo-`decisions_log`  
- **Kein automatischer Verkauf im Minus**  
- Teilverkauf nur bei Algo-`teilverkauf` und Position im Plus  
- Max. Positionsanteil laut Config  
- Gebühr **1 €** pro Trade (Paper)

### Dateien
| Datei | Bedeutung |
|-------|-----------|
| `signals/ki_gate.json` | blocks / half von der KI-Automation |
| `signals/algo_signals.json` | letzter gelesener Algo-Stand |
| `state/portfolio_state.json` | Hybrid-Depot |
| `state/hybrid_log.json` | Change-Katalog der Läufe |
"""
    )

with st.expander("Config (aktuell)", expanded=False):
    if cfg:
        st.json(cfg)
    else:
        st.write("Keine config.json")

with st.expander("RULES.md (Repo)", expanded=False):
    if rules_md:
        st.markdown(rules_md)
    else:
        st.write("RULES.md fehlt")

st.caption("Paper-Trading · Keine Anlageberatung · Repo: KI-king222/stock-hybrid-paper-trading")
