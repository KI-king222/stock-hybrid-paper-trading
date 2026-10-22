#!/usr/bin/env python3
"""Täglicher Hybrid-Lauf Variante A – inkl. Startkauf bei leerem Depot."""
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
from hybrid.fetch_remote import load_algo_last_run, load_ki_artifacts  # noqa: E402
from hybrid.orchestrator import apply_hybrid  # noqa: E402
from hybrid.ki_gate import resolve_gate  # noqa: E402

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


def bootstrap_portfolio(
    pf: Portfolio,
    universe: list,
    scores: dict,
    prices: dict,
    cfg: dict,
    ki: dict,
    now: datetime,
) -> list:
    """
    Wenn Hybrid noch keine Positionen hat: wie Algo starten –
    score-gewichtet kaufen (KI-Gate kann block/half).
    """
    log = []
    if pf.positions:
        return log
    if not prices:
        log.append({"final": "bootstrap_fail", "grund": "keine Preise"})
        return log

    tickers = [t for t in universe if t in prices]
    if not tickers:
        tickers = list(prices.keys())

    weights = {}
    for t in tickers:
        sc = float(scores.get(t) or 20.0)
        weights[t] = max(sc, 5.0)

    # Gate anwenden
    allowed = []
    for t in tickers:
        mode, reason = resolve_gate(GATE, ki, "neukauf", t)
        if mode == "block":
            log.append(
                {
                    "ticker": t,
                    "algo_action": "startkauf",
                    "final": "blockiert",
                    "gate": reason,
                    "score": scores.get(t),
                }
            )
            continue
        allowed.append((t, mode, reason))

    if not allowed:
        log.append({"final": "bootstrap_fail", "grund": "alles geblockt"})
        return log

    # Gewichte nur für erlaubte
    wsum = sum(weights.get(t, 5.0) for t, _, _ in allowed) or 1.0
    investable = pf.cash * 0.98  # kleine Reserve

    for t, mode, reason in allowed:
        w = weights.get(t, 5.0) / wsum
        budget = investable * w
        if mode == "half":
            budget *= 0.5
        px = prices[t]
        n = int((budget - pf.fee_per_trade) // px)
        if n <= 0:
            log.append(
                {
                    "ticker": t,
                    "algo_action": "startkauf",
                    "final": "keine_stueck",
                    "gate": reason,
                    "score": scores.get(t),
                }
            )
            continue
        ok = pf.buy(
            t,
            float(n),
            px,
            now,
            reason=f"Hybrid Startkauf Score {weights.get(t, 0):.0f} | {reason}",
        )
        log.append(
            {
                "ticker": t,
                "algo_action": "startkauf",
                "final": "kauf" if ok else "kauf_fail",
                "shares": n,
                "gate": reason,
                "score": scores.get(t),
            }
        )

    return log


def main():
    cfg = load_cfg()
    STATE.mkdir(parents=True, exist_ok=True)
    (ROOT / "signals").mkdir(parents=True, exist_ok=True)

    signals, scores = load_algo_last_run(cfg)
    ki = load_ki_artifacts(cfg)

    SIGNALS_OUT.write_text(
        json.dumps(
            {
                "date": datetime.now().isoformat(timespec="seconds"),
                "signals": signals,
                "scores": scores,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"Algo-Signale: {len(signals)} | Scores: {list(scores.keys())}")

    pf = Portfolio.load(PORTFOLIO)
    if pf is None:
        pf = Portfolio(
            starting_cash=float(cfg.get("starting_cash", 10_000)),
            fee_per_trade=float(cfg.get("fee_per_trade", 1.0)),
        )

    universe = list(cfg.get("universe") or [])
    tickers = set(universe)
    for s in signals:
        if s.get("ticker"):
            tickers.add(s["ticker"])
    tickers |= set(pf.positions.keys())
    tickers |= set(scores.keys())
    prices = get_prices(list(tickers))

    now = datetime.now()
    log_entries = []

    # --- Startkauf, wenn Depot leer ---
    if not pf.positions:
        print("Depot leer → Bootstrap-Startkauf")
        log_entries.extend(
            bootstrap_portfolio(pf, universe or list(prices.keys()), scores, prices, cfg, ki, now)
        )
    else:
        # Normale Hybrid-Logik nur wenn schon investiert
        log_entries.extend(apply_hybrid(pf, signals, prices, cfg, GATE, ki, now))

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
        "positions": list(pf.positions.keys()),
    }
    history.append(run)
    LOG.write_text(
        json.dumps({"runs": history[-200:]}, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    status = {
        "last_run": now.isoformat(timespec="seconds"),
        "headline": (
            f"Hybrid A {now.strftime('%d.%m.%Y %H:%M')} | "
            f"Vermögen {pf.total_wealth():,.0f} € | Cash {pf.cash:,.0f} € | "
            f"Pos {len(pf.positions)}"
        ),
        "wealth": round(pf.total_wealth(), 2),
        "cash": round(pf.cash, 2),
        "n_positions": len(pf.positions),
        "n_decisions": len(log_entries),
        "actions": [
            f"{e.get('final')} {e.get('ticker', '')}"
            for e in log_entries
            if e.get("final") not in ("halten",)
        ][:15],
    }
    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")

    print(status["headline"])
    for e in log_entries:
        print(f"  {e}")


if __name__ == "__main__":
    main()
