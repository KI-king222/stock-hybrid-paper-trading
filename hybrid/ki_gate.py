"""
KI-Gate Variante A: nur block oder half.
1) Lokale signals/ki_gate.json (Automation/Grok)
2) Heuristik aus KI-Repo (Verkaufs-Historie, Status-Text)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


def load_local_gate(path: Path) -> dict:
    if not path.exists():
        return {"blocks": [], "half": [], "notes": ""}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"blocks": [], "half": [], "notes": ""}


def derive_gate_from_ki(ki: Dict[str, Any]) -> Tuple[Set[str], Set[str], str]:
    """Leichte Heuristik ohne LLM-Aufruf."""
    blocks: Set[str] = set()
    half: Set[str] = set()
    notes: List[str] = []

    status = ki.get("last_run_status") or {}
    summary = (status.get("summary") or "") + " " + (status.get("notes") or "")
    summary_l = summary.lower()

    # Wenn KI klar sagt: keine Qualitätskäufe → aggressive Neukäufe halbieren (nicht blocken)
    if "keine qualitäts" in summary_l or "keine qualitaets" in summary_l:
        notes.append("KI-Status: keine Qualitätskäufe → Neukäufe tendenz half")

    pf = ki.get("portfolio") or {}
    for t, p in (pf.get("positions") or {}).items():
        try:
            avg = float(p.get("avg_cost") or 0)
            px = float(p.get("current_price") or avg)
            if avg > 0 and (px / avg - 1) * 100 <= -8:
                half.add(t)
                notes.append(f"KI hält {t} stark im Minus → Hybrid-Nachkauf half")
        except (TypeError, ValueError):
            pass

    # Kürzlich verkauft (nicht TP) → block Neukauf kurz
    for tr in (pf.get("trades") or [])[-15:]:
        if tr.get("action") != "sell":
            continue
        reason = str(tr.get("reason") or "").lower()
        t = tr.get("ticker")
        if t and "take-profit" not in reason and "take_profit" not in reason and "+4" not in reason:
            # nur wenn negativer Kontext
            if "schwach" in reason or "risiko" in reason or "ablehn" in reason:
                blocks.add(t)
                notes.append(f"KI verkaufte {t} nicht als TP → block")

    return blocks, half, "; ".join(notes)


def resolve_gate(
    local_path: Path,
    ki_artifacts: Dict[str, Any],
    action: str,
    ticker: str,
) -> Tuple[str, str]:
    """
    Returns (mode, reason) mode in: allow | half | block
    """
    local = load_local_gate(local_path)
    blocks = {str(x).upper() for x in (local.get("blocks") or [])}
    halfs = {str(x).upper() for x in (local.get("half") or [])}
    # Ticker normalisieren
    t_key = ticker.upper()
    t_alt = ticker

    if t_key in blocks or t_alt in (local.get("blocks") or []):
        return "block", f"ki_gate.json block: {ticker}"
    if t_key in halfs or t_alt in (local.get("half") or []):
        return "half", f"ki_gate.json half: {ticker}"

    d_blocks, d_half, note = derive_gate_from_ki(ki_artifacts)
    if ticker in d_blocks:
        return "block", note or f"KI-Heuristik block {ticker}"

    # Heuristik half nur bei Kauf-Aktionen
    if action in ("neukauf", "nachkauf", "reinvestition", "new_buy", "dip_buy", "reinvest"):
        if ticker in d_half:
            return "half", note or f"KI-Heuristik half {ticker}"
        if note and "keine qualitäts" in note.lower() and action in ("neukauf", "new_buy"):
            return "half", note

    return "allow", "kein KI-Veto"
