"""Einfaches Paper-Portfolio für Hybrid."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class Position:
    ticker: str
    shares: float
    avg_cost: float
    current_price: float = 0.0
    dip_buy_count: int = 0
    opened_at: str = ""  # ISO – erster Kauf
    last_action_at: str = ""  # ISO – letzter Kauf/Verkauf an dieser Pos.

    @property
    def market_value(self) -> float:
        return self.shares * (self.current_price or self.avg_cost)

    @property
    def unrealized_pnl_pct(self) -> float:
        if not self.avg_cost or not self.shares:
            return 0.0
        px = self.current_price or self.avg_cost
        return (px / self.avg_cost - 1.0) * 100.0

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "shares": self.shares,
            "avg_cost": self.avg_cost,
            "current_price": self.current_price,
            "dip_buy_count": self.dip_buy_count,
            "opened_at": self.opened_at,
            "last_action_at": self.last_action_at,
        }


@dataclass
class Portfolio:
    starting_cash: float = 10_000.0
    cash: float = 10_000.0
    fee_per_trade: float = 1.0
    external_profit: float = 0.0
    positions: Dict[str, Position] = field(default_factory=dict)
    trades: List[dict] = field(default_factory=list)

    def total_equity(self) -> float:
        return self.cash + sum(p.market_value for p in self.positions.values())

    def total_wealth(self) -> float:
        return self.total_equity() + self.external_profit

    def update_prices(self, prices: Dict[str, float]):
        for t, p in self.positions.items():
            if t in prices:
                p.current_price = prices[t]

    def buy(
        self,
        ticker: str,
        shares: float,
        price: float,
        when: datetime,
        reason: str = "",
        is_dip: bool = False,
    ) -> bool:
        if shares <= 0 or price <= 0:
            return False
        cost = shares * price + self.fee_per_trade
        if cost > self.cash + 1e-6:
            return False
        self.cash -= cost
        iso = when.isoformat()
        if ticker in self.positions:
            pos = self.positions[ticker]
            total_sh = pos.shares + shares
            pos.avg_cost = (pos.avg_cost * pos.shares + price * shares) / total_sh
            pos.shares = total_sh
            pos.current_price = price
            pos.last_action_at = iso
            if is_dip:
                pos.dip_buy_count += 1
        else:
            self.positions[ticker] = Position(
                ticker,
                shares,
                price,
                price,
                1 if is_dip else 0,
                opened_at=iso,
                last_action_at=iso,
            )
        self.trades.append(
            {
                "date": iso,
                "ticker": ticker,
                "action": "buy",
                "shares": shares,
                "price": price,
                "fee": self.fee_per_trade,
                "reason": reason,
                "locked_profit": 0.0,
            }
        )
        return True

    def sell(
        self,
        ticker: str,
        shares: float,
        price: float,
        when: datetime,
        reason: str = "",
    ) -> bool:
        if ticker not in self.positions or shares <= 0 or price <= 0:
            return False
        pos = self.positions[ticker]
        shares = min(shares, pos.shares)
        proceeds = shares * price - self.fee_per_trade
        pnl = (price - pos.avg_cost) * shares - self.fee_per_trade
        if pnl > 0:
            self.external_profit += pnl
        self.cash += proceeds
        iso = when.isoformat()
        pos.shares -= shares
        pos.last_action_at = iso
        if pos.shares <= 1e-9:
            del self.positions[ticker]
        else:
            pos.current_price = price
        self.trades.append(
            {
                "date": iso,
                "ticker": ticker,
                "action": "sell",
                "shares": shares,
                "price": price,
                "fee": self.fee_per_trade,
                "reason": reason,
                "locked_profit": round(max(pnl, 0.0), 2),
            }
        )
        return True

    def to_dict(self) -> dict:
        return {
            "starting_cash": self.starting_cash,
            "cash": self.cash,
            "fee_per_trade": self.fee_per_trade,
            "external_profit": self.external_profit,
            "positions": {k: v.to_dict() for k, v in self.positions.items()},
            "trades": self.trades,
        }

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Optional["Portfolio"]:
        if not path.exists():
            return None
        d = json.loads(path.read_text(encoding="utf-8"))
        pf = cls(
            starting_cash=float(d.get("starting_cash", 10_000)),
            cash=float(d.get("cash", 10_000)),
            fee_per_trade=float(d.get("fee_per_trade", 1.0)),
            external_profit=float(d.get("external_profit", 0.0)),
            trades=list(d.get("trades") or []),
        )
        for t, p in (d.get("positions") or {}).items():
            opened = p.get("opened_at") or ""
            last = p.get("last_action_at") or ""
            if not opened:
                for tr in pf.trades:
                    if tr.get("ticker") == t and tr.get("action") == "buy":
                        opened = str(tr.get("date") or "")
                        break
            if not last:
                for tr in reversed(pf.trades):
                    if tr.get("ticker") == t:
                        last = str(tr.get("date") or "")
                        break
            pf.positions[t] = Position(
                ticker=t,
                shares=float(p["shares"]),
                avg_cost=float(p["avg_cost"]),
                current_price=float(p.get("current_price") or p["avg_cost"]),
                dip_buy_count=int(p.get("dip_buy_count") or 0),
                opened_at=opened,
                last_action_at=last,
            )
        return pf
