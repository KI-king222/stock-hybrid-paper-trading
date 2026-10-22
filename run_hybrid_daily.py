#!/usr/bin/env python3
"""Täglicher Hybrid-Lauf Variante A."""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import yfinance as yf  # noqa: E402

from portfolio import Portfolio  # noqa: E402
from hybrid.fetch_remote import load_algo_signals, load_ki_artifacts  # noqa: E402
from hybrid.orchestrator import apply_hybrid  # noqa: E402

STATE = ROOT / "state"
PORTFOLIO = STATE / "portfolio_state.json"
LOG = STATE / "hybrid_log.json"
STATUS = STATE / "last_run_status.json"
SIGNALS_OUT = ROOT / "signals" / "algo_signals.json"
GATE = ROOT / "signals" / "ki_gate.json"
CFG = ROOT / "config.json"


def load_cfg() -> dict:
    return json.loads(CFG.read_text(encoding="utf-8"))


def get_prices(tickers) -> dict:
    out = {}
    for t in tickers:
        try:
            h = yf.Ticker(t).history(period="5d")
            if h is None or h.empty:
                continue
            p = float(h["Close"].dropna().iloc[-1])
            if math.isfinite(p) and p > 0:
                out[t] = p
        except Exception as e:
            print(f"Preis {t}: {e}")
    return out


def main():
    cfg = load_cfg()
    STATE.mkdir(parents=True, exist_ok=True)
    (ROOT / "signals").mkdir(parents=True, exist_ok=True)

    signals = load_algo_signals(cfg)
    ki = load_ki_artifacts(cfg)

    SIGNALS_OUT.write_text(
        json.dumps(
            {"date": datetime.now().isoformat(timespec="seconds"), "signals": signals},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"Algo-Signale: {len(signals)}")

    pf = Portfolio.load(PORTFOLIO)
    if pf is None:
        pf = Portfolio(
            starting_cash=float(cfg.get("starting_cash", 10_000)),
            fee_per_trade=float(cfg.get("fee_per_trade", 1.0)),
        )

    tickers = set(cfg.get("universe") or [])
    for s in signals:
        if s.get("ticker"):
            tickers.add(s["ticker"])
    tickers |= set(pf.positions.keys())
    prices = get_prices(list(tickers))

    now = datetime.now()
    log_entries = apply_hybrid(pf, signals, prices, cfg, GATE, ki, now)
    pf.update_prices(prices)
    pf.save(PORTFOLIO)

    history = []
    if LOG.exists():
        history = json.loads(LOG.read_text(encoding="utf-8")).get("runs", [])
    run = {
        "date": now.isoformat(timespec="seconds"),
        "source": "Hybrid A: Algo + KI-Gate",
        "n_signals": len(signals),
        "decisions": log_entries,
        "cash": round(pf.cash, 2),
        "equity": round(pf.total_equity(), 2),
        "external_profit": round(pf.external_profit, 2),
        "wealth": round(pf.total_wealth(), 2),
    }
    history.append(run)
    LOG.write_text(
        json.dumps({"runs": history[-200:]}, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    status = {
        "last_run": now.isoformat(timespec="seconds"),
        "headline": (
            f"Hybrid A {now.strftime('%d.%m.%Y %H:%M')} | "
            f"Vermögen {pf.total_wealth():,.0f} € | Cash {pf.cash:,.0f} €"
        ),
        "wealth": round(pf.total_wealth(), 2),
        "cash": round(pf.cash, 2),
        "n_decisions": len(log_entries),
        "actions": [
            f"{e.get('final')} {e.get('ticker')}" for e in log_entries if e.get("final") != "halten"
        ][:15],
    }
    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")

    print(status["headline"])
    for e in log_entries:
        print(f"  {e}")


if __name__ == "__main__":
    main()
