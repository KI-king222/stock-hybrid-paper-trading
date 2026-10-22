"""Wendet Algo-Signale + KI-Gate auf Hybrid-Portfolio an."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Tuple

from portfolio import Portfolio
from hybrid.ki_gate import resolve_gate

BUY_ACTIONS = {"neukauf", "nachkauf", "reinvestition", "new_buy", "dip_buy", "reinvest", "buy"}
SELL_ACTIONS = {"teilverkauf", "take_profit", "sell"}


def apply_hybrid(
    pf: Portfolio,
    signals: List[dict],
    prices: Dict[str, float],
    cfg: dict,
    gate_path,
    ki_artifacts: dict,
    now: datetime | None = None,
) -> List[dict]:
    now = now or datetime.now()
    pf.update_prices(prices)
    equity = max(pf.total_equity(), 1.0)
    max_pos = float(cfg.get("max_position_pct_of_equity", 35.0)) / 100.0
    fee = pf.fee_per_trade
    log = []

    for sig in signals:
        t = sig.get("ticker")
        if not t:
            continue
        action = str(sig.get("action") or "halten").lower()
        reason = str(sig.get("reason") or "")
        score = sig.get("score")
        shares = sig.get("shares")
        try:
            shares = float(shares) if shares is not None else 0.0
        except (TypeError, ValueError):
            shares = 0.0

        mode, gate_reason = resolve_gate(gate_path, ki_artifacts, action, t)

        if action in SELL_ACTIONS and cfg.get("allow_algo_sells", True):
            if mode == "block":
                log.append(
                    {
                        "ticker": t,
                        "algo_action": action,
                        "final": "blockiert",
                        "gate": gate_reason,
                        "score": score,
                    }
                )
                continue
            if t not in pf.positions or t not in prices:
                log.append(
                    {
                        "ticker": t,
                        "algo_action": action,
                        "final": "kein_bestand",
                        "gate": gate_reason,
                        "score": score,
                    }
                )
                continue
            pos = pf.positions[t]
            if pos.unrealized_pnl_pct < 0:
                log.append(
                    {
                        "ticker": t,
                        "algo_action": action,
                        "final": "kein_verkauf_im_minus",
                        "gate": gate_reason,
                        "score": score,
                    }
                )
                continue
            n = shares if shares > 0 else max(1.0, round(pos.shares * 0.35))
            if mode == "half":
                n = max(1.0, round(n * 0.5))
            ok = pf.sell(t, n, prices[t], now, reason=f"Hybrid/Algo: {reason} | {gate_reason}")
            log.append(
                {
                    "ticker": t,
                    "algo_action": action,
                    "final": "teilverkauf" if ok else "sell_fail",
                    "shares": n,
                    "gate": gate_reason,
                    "score": score,
                }
            )
            continue

        if action in BUY_ACTIONS:
            if mode == "block":
                log.append(
                    {
                        "ticker": t,
                        "algo_action": action,
                        "final": "blockiert",
                        "gate": gate_reason,
                        "score": score,
                    }
                )
                continue
            if t not in prices:
                log.append(
                    {
                        "ticker": t,
                        "algo_action": action,
                        "final": "kein_preis",
                        "gate": gate_reason,
                        "score": score,
                    }
                )
                continue
            px = prices[t]
            n = shares
            if n <= 0:
                # Budget-Vorschlag: 20% Cash
                budget = pf.cash * 0.20
                n = int((budget - fee) // px)
            if mode == "half":
                n = max(0, int(n * 0.5))
            if n <= 0:
                log.append(
                    {
                        "ticker": t,
                        "algo_action": action,
                        "final": "keine_stueck",
                        "gate": gate_reason,
                        "score": score,
                    }
                )
                continue
            # Positions-Cap
            cur_mv = pf.positions[t].market_value if t in pf.positions else 0.0
            room = equity * max_pos - cur_mv
            max_n = int(room // px) if room > 0 else 0
            if max_n <= 0:
                log.append(
                    {
                        "ticker": t,
                        "algo_action": action,
                        "final": "positions_limit",
                        "gate": gate_reason,
                        "score": score,
                    }
                )
                continue
            n = min(n, max_n)
            is_dip = action in ("nachkauf", "dip_buy")
            ok = pf.buy(
                t,
                float(n),
                px,
                now,
                reason=f"Hybrid/Algo: {reason} | {gate_reason}",
                is_dip=is_dip,
            )
            log.append(
                {
                    "ticker": t,
                    "algo_action": action,
                    "final": ("nachkauf" if is_dip else "kauf") if ok else "kauf_fail",
                    "shares": n,
                    "gate": gate_reason,
                    "score": score,
                }
            )
            continue

        # halten / sonst
        log.append(
            {
                "ticker": t,
                "algo_action": action,
                "final": "halten",
                "gate": gate_reason,
                "score": score,
            }
        )

    return log
