"""Signale aus Algo- und KI-Repo (GitHub raw) laden."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import requests

RAW = "https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"


def fetch_json(owner: str, repo: str, path: str, branch: str = "main") -> Optional[dict]:
    url = RAW.format(owner=owner, repo=repo, branch=branch, path=path)
    try:
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            print(f"fetch {url}: HTTP {r.status_code}")
            return None
        return r.json()
    except Exception as e:
        print(f"fetch {url}: {e}")
        return None


def load_algo_last_run(cfg: dict) -> Tuple[List[dict], Dict[str, float]]:
    """Letzter Algo-Lauf: decisions + scores."""
    owner = cfg["algo_owner"]
    repo = cfg["algo_repo"]
    branch = cfg.get("algo_branch", "main")
    log = fetch_json(owner, repo, "state/decisions_log.json", branch)
    if not log or not log.get("runs"):
        log = fetch_json(owner, repo, "decisions_log.json", branch)
    if not log or not log.get("runs"):
        return [], {}

    last = log["runs"][-1]
    scores = {k: float(v) for k, v in (last.get("scores") or {}).items()}
    out = []
    map_en = {
        "hold": "halten",
        "buy": "neukauf",
        "reinvest": "reinvestition",
        "dip_buy": "nachkauf",
        "new_buy": "neukauf",
        "take_profit": "teilverkauf",
        "sell": "teilverkauf",
    }
    for d in last.get("decisions") or []:
        akt = d.get("aktion") or d.get("action") or "halten"
        akt = map_en.get(str(akt), str(akt))
        sh = d.get("stück") if d.get("stück") is not None else d.get("shares")
        out.append(
            {
                "ticker": d.get("ticker"),
                "action": akt,
                "shares": sh,
                "score": d.get("score") if d.get("score") is not None else scores.get(d.get("ticker")),
                "reason": d.get("grund") or d.get("reason") or "",
                "source_date": last.get("date"),
            }
        )
    return out, scores


def load_algo_signals(cfg: dict) -> List[dict]:
    signals, _ = load_algo_last_run(cfg)
    return signals


def load_ki_artifacts(cfg: dict) -> Dict[str, Any]:
    owner = cfg["ki_owner"]
    repo = cfg["ki_repo"]
    branch = cfg.get("ki_branch", "main")
    return {
        "last_run_status": fetch_json(owner, repo, "last_run_status.json", branch),
        "portfolio": fetch_json(owner, repo, "portfolio_state.json", branch),
        "watchlist": fetch_json(owner, repo, "watchlist.json", branch),
    }
