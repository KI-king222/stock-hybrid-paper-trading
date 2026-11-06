# Hybrid-Regeln (Variante A)

## Rollen

1. **Algo** liefert Kandidaten.
2. **KI-Gate**: block / half / oder voll ausführen.

## Harte Grenzen

- **Take-Profit ab +8 % → komplette Position verkaufen** (kein Teilverkauf mehr).
- Kein automatischer Verkauf im Minus.
- Max. Positionsanteil laut config.
- Gebühr 1 €.

## Cash-Regel

- Puffer 500–800 €.
- Kauf nur bei: These intakt **und** Aktie im durchschnittlichen Tief.
- Sonst Cash halten.

## Dateien

- `signals/algo_signals.json`
- `signals/ki_gate.json`
- `state/portfolio_state.json`
- `state/hybrid_log.json`
