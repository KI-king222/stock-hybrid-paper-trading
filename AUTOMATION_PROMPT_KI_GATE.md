# Kurz-Prompt: nur KI-Gate für Hybrid (Variante A)

Du darfst **keine Käufe/Verkäufe** im Hybrid-Depot ausführen.  
Du pflegst nur:

1. `signals/ki_gate.json`
2. optional `signals/watchlist.json`

## Aufgabe

1. Lies Algo-Signale: `stock-algo-paper-trading` → `state/decisions_log.json` (letzter Lauf).
2. Lies KI-Kontext: `stock-paper-trading` (Status, Portfolio, Watchlist/Gehirn).
3. **Nur Ticker mit Aktion kaufen/nachkauf/reinvestition/teilverkauf** dürfen in `blocks` oder `half`.
4. Bei reinem **halten**: **weder block noch half** für diesen Ticker (sinnlos, wird ignoriert).
5. Schreibe `signals/ki_gate.json`:

```json
{
  "updated_at": "YYYY-MM-DDTHH:MM:SS",
  "source": "Grok Automation",
  "blocks": [],
  "half": [],
  "notes": "kurze Begründung"
}
```

6. Optional Watchlist `signals/watchlist.json`:

```json
{
  "updated_at": "YYYY-MM-DDTHH:MM:SS",
  "scale": "1 = hoch, 2 = mittel, 3 = niedrig",
  "items": [
    {"ticker": "…", "title": "…", "priority": 1, "status": "active", "reason": "…", "added_at": "YYYY-MM-DD"}
  ]
}
```

## Regeln

- Algo führt – wenig eingreifen.
- **half** = halbe Stückzahl nur wenn wirklich ein Trade ansteht.
- **block** nur bei klarem Risiko.
- Keine Fantasie-Ticker.
