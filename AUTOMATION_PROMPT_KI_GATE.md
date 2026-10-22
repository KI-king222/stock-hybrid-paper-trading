# Kurz-Prompt: nur KI-Gate für Hybrid (Variante A)

Du darfst **keine Käufe im Hybrid-Depot** ausführen.  
Du pflegst nur die Datei `signals/ki_gate.json` im Repo **stock-hybrid-paper-trading**.

## Aufgabe

1. Lies die neuesten Algo-Signale (Repo stock-algo-paper-trading, `state/decisions_log.json` letzter Lauf).
2. Lies KI-Kontext (stock-paper-trading: last_run_status, portfolio, Gehirn/Watchlist wenn vorhanden).
3. Entscheide **nur**:
   - `blocks`: Ticker, die der Hybrid **nicht** kaufen/verkaufen soll
   - `half`: Ticker, bei denen die Stückzahl **halbiert** wird
4. Schreibe / pushe:

```json
{
  "updated_at": "YYYY-MM-DDTHH:MM:SS",
  "source": "Grok Automation",
  "blocks": [],
  "half": [],
  "notes": "kurze Begründung"
}
```

## Regeln

- Weniger blocken als erlauben (Algo führt).
- Blocken nur bei klarem Risiko / widersprüchlicher These.
- Half z. B. bei unsicherer Lage oder wenn KI dieselbe Position schon stark im Minus hält.
- Keine Fantasie-Ticker. Nur Ticker aus den Algo-Signalen oder Universum.

Danach: Hybrid-Workflow `run_hybrid_daily` (Actions) ausführen bzw. warten auf Cron.
