# Hybrid-Regeln (Variante A)

## Rollen

1. **Algo** liefert Kandidaten: `neukauf`, `nachkauf`, `reinvestition`, `teilverkauf`, `halten`.
2. **KI-Gate** (Datei oder abgeleitet aus KI-Repo):
   - `block`: Trade findet nicht statt
   - `half`: Stückzahl × 0,5 (aufgerundet mind. 1 wenn ≥2 vorgeschlagen)
3. Ohne Gate-Eintrag: **Algo-Vorschlag voll ausführen** (bei Kauf, sofern Cash/Limits ok).

## Harte Grenzen (Code)

- Kein automatischer Verkauf im Minus (außer manueller Override später).
- Teilverkauf nur wenn Algo `teilverkauf` und Position im Plus.
- Max. Positionsanteil am Equity laut `config.json`.
- Gebühr 1 € pro Trade (Paper).

## Dateien

- `signals/algo_signals.json` – vom Orchestrator aus Algo-Repo gebaut  
- `signals/ki_gate.json` – optional von der KI-Automation  
- `state/portfolio_state.json` – Hybrid-Depot  
- `state/hybrid_log.json` – Entscheidungen mit Gate-Begründung  
