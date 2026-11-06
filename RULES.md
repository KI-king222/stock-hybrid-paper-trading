# Hybrid-Regeln (Variante A)

## Rollen

1. **Algo** liefert Kandidaten: `neukauf`, `nachkauf`, `reinvestition`, `teilverkauf`, `halten`.
2. **KI-Gate**:
   - `block`: Trade findet nicht statt
   - `half`: Stückzahl × 0,5
3. Ohne Gate-Eintrag: Algo-Vorschlag ausführen (sofern Limits ok).

## Harte Grenzen

- Kein automatischer Verkauf im Minus.
- Teilverkauf nur bei Plus und Algo-Signal.
- Max. Positionsanteil laut config.
- Gebühr 1 €.

## Cash-Regel (Stand 06.11.2026)

- Puffer: ca. 500–800 € dürfen liegen.
- Darüber: aktive Suche ist erwünscht.
- **Kauf nur erlaubt, wenn beides gilt:**
  1. These / Finanzbericht intakt oder positiv
  2. Die Aktie liegt in einem durchschnittlichen Tief / spürbaren Rücksetzer (nicht am Hoch)
- Wenn keine Aktie beide Bedingungen erfüllt → Cash halten und begründen.
- Kein Kauf nur deshalb, weil gerade Cash aus einem Verkauf da ist.

## Dateien

- `signals/algo_signals.json`
- `signals/ki_gate.json`
- `state/portfolio_state.json`
- `state/hybrid_log.json`
