"""Chart helpers – Stil wie KI-Paper-Trading."""
from __future__ import annotations

import streamlit as st
import pandas as pd

try:
    import plotly.graph_objects as go

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def get_price_history(ticker: str, period: str = "1mo", interval: str = "1d"):
    import yfinance as yf

    h = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
    if h is None or h.empty:
        return None
    df = h.reset_index()
    # Date / Datetime column
    date_col = "Datetime" if "Datetime" in df.columns else "Date"
    df = df.rename(columns={date_col: "Date", "Close": "Kurs"})
    df["Date"] = pd.to_datetime(df["Date"], utc=True).dt.tz_convert(None)
    return df[["Date", "Kurs"]].dropna()


def render_position_charts(positions: dict):
    st.subheader("Kursverlauf der aktuellen Positionen")
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
        key="hybrid_chart_period",
    )
    cfg = period_config[selected_label]
    CHART_CONFIG = {
        "displayModeBar": True,
        "displaylogo": False,
        "scrollZoom": True,
        "responsive": True,
        "doubleClick": "reset",
        "modeBarButtonsToRemove": [
            "zoom2d",
            "select2d",
            "lasso2d",
            "autoScale2d",
            "toggleSpikelines",
            "hoverClosestCartesian",
            "hoverCompareCartesian",
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
            avg = float(pos.get("avg_cost") or 0)
            hist = get_price_history(ticker, period=cfg["period"], interval=cfg["interval"])
            if hist is None or hist.empty:
                st.info(f"Kein Kursverlauf für {ticker}.")
                continue
            hist = hist.copy().reset_index(drop=True)
            hist["i"] = hist.index.astype(int)
            y_min = min(float(hist["Kurs"].min()), avg if avg else float(hist["Kurs"].min()))
            y_max = max(float(hist["Kurs"].max()), avg if avg else float(hist["Kurs"].max()))
            pad = max((y_max - y_min) * 0.03, 0.5)
            n = len(hist)
            n_ticks = min(6, n)
            tick_idx = (
                [int(i * (n - 1) / max(n_ticks - 1, 1)) for i in range(n_ticks)] if n > 1 else [0]
            )
            tick_idx = sorted(set(tick_idx))
            ticktext = [hist.loc[i, "Date"].strftime("%d.%m") for i in tick_idx]

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=hist["i"],
                    y=hist["Kurs"],
                    mode="lines",
                    name=ticker,
                    line=dict(width=2.0, color="#30D158"),
                    fill="tozeroy",
                    fillcolor="rgba(48, 209, 88, 0.13)",
                    customdata=hist["Date"],
                    hovertemplate="<b>%{y:.2f} €</b><br>%{customdata|%d.%m.%Y %H:%M}<extra></extra>",
                )
            )
            if avg > 0:
                fig.add_hline(
                    y=avg,
                    line_dash="dot",
                    line_color="#FF9F0A",
                    line_width=1.4,
                    annotation_text=f"Einstand {avg:.2f} €",
                    annotation_position="top left",
                    annotation_font=dict(size=11, color="#FF9F0A"),
                )
            fig.update_layout(
                title=dict(
                    text=f"{ticker}  ·  {selected_label}",
                    font=dict(size=17, color="#F5F5F7"),
                    x=0.0,
                    xanchor="left",
                ),
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
                    showspikes=True,
                    spikemode="across+toaxis",
                    spikesnap="cursor",
                    spikethickness=1.5,
                    spikecolor="#0A84FF",
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor="rgba(255,255,255,0.07)",
                    side="right",
                    tickformat=".2f",
                    ticksuffix=" €",
                    range=[y_min - pad, y_max + pad],
                    fixedrange=False,
                    showspikes=True,
                ),
                showlegend=False,
                hoverlabel=dict(
                    bgcolor="rgba(28,28,30,0.95)",
                    font_size=15,
                    font_color="#FFFFFF",
                    bordercolor="#30D158",
                ),
            )
            st.plotly_chart(
                fig,
                use_container_width=True,
                config=CHART_CONFIG,
                key=f"hy_chart_{ticker}_{selected_label}",
            )
        except Exception as e:
            st.info(f"Chart {ticker}: {e}")
