# Hybrid-Regeln (Variante A)

Stand: 07.11.2026 – Loop-Stand (wie Algo).

## Rollen

1. **Algo** liefert Kandidaten + Score (inkl. Finanzbericht).
2. **KI-Gate**: block / half / oder voll ausführen.

## Harte Grenzen

- **Take-Profit ab +7 % → komplette Position** (Lohn, kein Teilverkauf).
- Kein automatischer Verkauf im Minus.
- Max. Positionsanteil laut config (~25 %).
- Gebühr 1 €.
- Universe: **DE + EU + US** (config).

## Cash-Regel

- Ziel ≤ **700 €** freies Cash; darüber reinvestieren.
- Pro Neukauf ca. **40 %** des investierbaren Cash (Algo-Config).
- Kauf: These/Score + Kurslage (Tief oder starke These).

## Dateien

- `config.json` – TP7, Universe, Cash
- `signals/algo_signals.json`
- `signals/ki_gate.json`
- `state/portfolio_state.json`
