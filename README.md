# stock-hybrid-paper-trading

**Variante A:** Der **Algo** schlägt Käufe/Verkäufe vor. Die **KI** darf nur:

- **blocken** (kein Trade), oder  
- **Positionsgröße halbieren**

Kein paralleles „KI kauft frei“ in diesem Depot – nur Gate + gemeinsames Hybrid-Portfolio.

## Repos

| Repo | Rolle |
|------|--------|
| `stock-algo-paper-trading` | Signale (Scores, decisions_log) |
| `stock-paper-trading` | KI-Status, Watchlist, optionales `ki_gate.json` |
| **dieses** | Orchestrator + eigenes Hybrid-Depot |

## Täglicher Ablauf

1. Algo-Repo läuft (ca. 23 Uhr) → `state/decisions_log.json`  
2. Optional: Grok/Automation schreibt `signals/ki_gate.json` (blocks / half)  
3. Dieses Repo: `run_hybrid_daily.py`  
   - holt Algo-Signale + KI-Gate  
   - wendet Regeln an  
   - speichert Hybrid-Portfolio unter `state/`

## Lokal / Actions

```bash
pip install -r requirements.txt
python run_hybrid_daily.py
```

Streamlit: Main file `app.py`.

## Regeln

Siehe `RULES.md` und `config.json`.
