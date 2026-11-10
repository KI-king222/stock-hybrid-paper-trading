"""Hybrid Charts v3 – Einstand = feste EUR-Linie, Kurve = reine Historie.

Kein Scale, kein Live-Punkt-Anhang (beides hat 1T verzerrt).
"""
from __future__ import annotations

import streamlit as st
import pandas as pd

try:
    import plotly.graph_objects as go

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from fx import native_currency, _fx_to_eur

CHART_VERSION = "v3-2026-11-10"


def to_berlin(series: pd.Series) -> pd.Series:
    s = pd.to_datetime(series, utc=True, errors="coerce")
    try:
        return s.dt.tz_convert("Europe/Berlin").dt.tz_localize(None)
    except Exception:
        return pd.to_datetime(series, errors="coerce")


def get_price_history(ticker: str, period: str = "5d", interval: str = "15m"):
    """Nur yfinance-Historie → EUR. Kein Nachziehen, kein Scale."""
    import yfinance as yf

    h = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
    if h is None or h.empty:
        return None
    df = h.reset_index()
    date_col = "Datetime" if "Datetime" in df.columns else "Date"
    df["Date"] = to_berlin(df[date_col])

    native = pd.to_numeric(df["Close"], errors="coerce")
    ccy = native_currency(ticker)
    if ccy == "EUR":
        df["Kurs"] = native
    else:
        rate = float(_fx_to_eur(ccy))
        df["Kurs"] = native * rate

    df = df.dropna(subset=["Kurs", "Date"])
    df = df[df["Kurs"] > 0]
    if df.empty:
        return None
    return df[["Date", "Kurs"]].reset_index(drop=True)


def render_position_charts(positions: dict):
    st.subheader("Kursverlauf (EUR)")
    st.caption(
        f"Chart **{CHART_VERSION}** · Einstand = gebuchter Kaufpreis in € · "
        "Kurve = Börsenhistorie in € · **kein** Strecken der Kurve"
    )
    period_config = {
        "1T": {"period": "1d", "interval": "5m"},
        "1W": {"period": "5d", "interval": "15m"},
        "1M": {"period": "1mo", "interval": "1h"},
        "3M": {"period": "3mo", "interval": "1d"},
        "6M": {"period": "6mo", "interval": "1d"},
        "1J": {"period": "1y", "interval": "1d"},
    }
    selected_label = st.radio(
        "Zeitraum",
        list(period_config.keys()),
        index=1,
        horizontal=True,
        label_visibility="collapsed",
        key="hybrid_chart_period_v3",
    )
    cfg = period_config[selected_label]
    CHART_CONFIG = {
        "displayModeBar": True,
        "displaylogo": False,
        "scrollZoom": True,
        "responsive": True,
        "doubleClick": "reset",
        "modeBarButtonsToRemove": [
            "zoom2d", "select2d", "lasso2d", "autoScale2d",
            "toggleSpikelines", "hoverClosestCartesian", "hoverCompareCartesian",
        ],
    }
    if not PLOTLY_AVAILABLE:
        st.warning("Plotly nicht verfügbar.")
        return
    if not positions:
        st.info("Keine Positionen für Charts.")
        return

    for ticker, pos in positions.items():
        try:
            avg = round(float(pos.get("avg_cost") or 0), 2)
            hist = get_price_history(
                ticker, period=cfg["period"], interval=cfg["interval"]
            )
            if hist is None or hist.empty:
                st.info(f"Kein Kursverlauf für {ticker}.")
                continue

            hist = hist.reset_index(drop=True)
            hist["i"] = hist.index.astype(int)

            last_dt = hist["Date"].iloc[-1]
            stand = last_dt.strftime("%d.%m. %H:%M") if pd.notna(last_dt) else "?"
            last_px = float(hist["Kurs"].iloc[-1])
            lo = float(hist["Kurs"].min())
            hi = float(hist["Kurs"].max())

            # Diagnose: liegt Einstand im sichtbaren Kursband?
            if avg > 0 and (avg < lo * 0.98 or avg > hi * 1.02):
                note = (
                    f" · Einstand außerhalb des {selected_label}-Bands "
                    f"({lo:.2f}–{hi:.2f} €) – normal, wenn Kauf älter/anderer Tag"
                )
            else:
                note = ""

            st.caption(
                f"**{ticker}** Stand **{stand}** · Chart **{last_px:.2f} €** "
                f"(Band {lo:.2f}–{hi:.2f}) · Einstand **{avg:.2f} €**{note}"
            )

            y_min = min(lo, avg if avg else lo)
            y_max = max(hi, avg if avg else hi)
            pad = max((y_max - y_min) * 0.05, 0.5)
            n = len(hist)
            n_ticks = min(6, n)
            tick_idx = (
                [int(i * (n - 1) / max(n_ticks - 1, 1)) for i in range(n_ticks)] if n > 1 else [0]
            )
            tick_idx = sorted(set(tick_idx))
            if selected_label == "1T":
                ticktext = [hist.loc[i, "Date"].strftime("%H:%M") for i in tick_idx]
            else:
                ticktext = [hist.loc[i, "Date"].strftime("%d.%m %H:%M") for i in tick_idx]

            ccy = native_currency(ticker)
            title = f"{ticker} · {selected_label} · EUR · {stand}" + (
                f" · aus {ccy}" if ccy != "EUR" else ""
            )

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=hist["i"],
                    y=hist["Kurs"],
                    mode="lines",
                    name=ticker,
                    line=dict(width=2.0, color="#30D158"),
                    # kein tozeroy – vermeidet optische Verzerrung
                    customdata=hist["Date"],
                    hovertemplate="<b>%{y:.2f} €</b><br>%{customdata|%d.%m.%Y %H:%M}<extra></extra>",
                )
            )
            if avg > 0:
                fig.add_hline(
                    y=avg,
                    line_dash="dot",
                    line_color="#FF9F0A",
                    line_width=1.6,
                    annotation_text=f"Einstand {avg:.2f} €",
                    annotation_position="top left",
                    annotation_font=dict(size=11, color="#FF9F0A"),
                )
            fig.update_layout(
                title=dict(text=title, font=dict(size=15, color="#F5F5F7"), x=0.0, xanchor="left"),
                height=380,
                margin=dict(l=8, r=8, t=50, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#AEAEB2", size=11),
                hovermode="x unified",
                dragmode="pan",
                xaxis=dict(
                    showgrid=True,
                    gridcolor="rgba(255,255,255,0.07)",
                    tickmode="array",
                    tickvals=tick_idx,
                    ticktext=ticktext,
                    rangeslider=dict(visible=False),
                    fixedrange=False,
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor="rgba(255,255,255,0.07)",
                    side="right",
                    tickformat=".2f",
                    ticksuffix=" €",
                    range=[y_min - pad, y_max + pad],
                    fixedrange=False,
                    autorange=False,
                ),
                showlegend=False,
            )
            st.plotly_chart(
                fig,
                use_container_width=True,
                config=CHART_CONFIG,
                key=f"hy_v3_{ticker}_{selected_label}",
            )
        except Exception as e:
            st.info(f"Chart {ticker}: {e}")
