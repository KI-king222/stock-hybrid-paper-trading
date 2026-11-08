"""Währung → EUR für Hybrid-Preisabruf."""
from __future__ import annotations

import math
from typing import Dict

import yfinance as yf

_EUR_SUFFIXES = (".DE", ".PA", ".AS", ".MI", ".BR", ".MC", ".HE", ".LS", ".VI", ".AT")
_GBP_SUFFIXES = (".L", ".IL")
_CHF_SUFFIXES = (".SW", ".VX")
_fx_cache: Dict[str, float] = {}


def _valid(p) -> bool:
    try:
        v = float(p)
        return math.isfinite(v) and v > 0
    except (TypeError, ValueError):
        return False


def native_currency(ticker: str) -> str:
    t = (ticker or "").upper()
    if any(t.endswith(s) for s in _EUR_SUFFIXES):
        return "EUR"
    if any(t.endswith(s) for s in _GBP_SUFFIXES):
        return "GBP"
    if any(t.endswith(s) for s in _CHF_SUFFIXES):
        return "CHF"
    return "USD"


def _fx_to_eur(ccy: str) -> float:
    ccy = (ccy or "EUR").upper()
    if ccy == "EUR":
        return 1.0
    if ccy in _fx_cache:
        return _fx_cache[ccy]
    pair = {"USD": "EURUSD=X", "GBP": "EURGBP=X", "CHF": "EURCHF=X"}.get(ccy)
    if not pair:
        _fx_cache[ccy] = 1.0
        return 1.0
    try:
        h = yf.Ticker(pair).history(period="5d")
        quote = float(h["Close"].dropna().iloc[-1]) if h is not None and not h.empty else 0.0
        rate = (1.0 / quote) if quote > 0 else 1.0
    except Exception as e:
        print(f"FX {pair}: {e}")
        rate = 1.0
    _fx_cache[ccy] = rate
    return rate


def to_eur(price_native: float, ticker: str) -> float:
    if not _valid(price_native):
        return price_native
    ccy = native_currency(ticker)
    if ccy == "EUR":
        return float(price_native)
    return float(price_native) * _fx_to_eur(ccy)
