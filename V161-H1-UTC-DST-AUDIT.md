# REMURA v1.61 — Verifica dell'ipotesi FUSO ORARIO per H1 (solo test offline)

**03 novembre 2026 — nessuna modifica alla VPS.**

## Ipotesi e verifiche nel codice LIVE v1.61

- `scripts/ctrader_feed.py`: cTrader `utcTimestampInMinutes` diventa un timestamp consapevole **UTC** tramite `datetime.fromtimestamp(value*60, UTC)`; `price_feed.candle` normalizza in ISO `Z` UTC. Il provider non viene interpretato come orario italiano.
- `scripts/price_feed.py`: `parse_time` converte in UTC e `rollup` raggruppa H1/H4 su ore UTC complete e intervalli M15 consecutivi. **Nessuna trasformazione Europe/Rome per H1**, neppure al cambio DST.
- `scripts/price_store.py`: `ZoneInfo("Europe/Rome")` interviene solo per identificare il weekend; l'età della barra si ottiene da `now UTC - close UTC`.
- `scripts/signals_monitor.py`: usa il tempo di chiusura UTC `opened + 3600s`, con soglia H1 di **120 minuti**, non 120 minuti dal momento di richiesta o dalla candela M15.
- `scripts/private_server.py`: UTC per scheduling quarto d'ora, con grazia di 90 secondi. Se la VPS gira in ora italiana, la logica UTC resta invariata.

## Test che devono superare la CI

1. **25/10/2026** cambio ora solare Europe/Rome: `00:00 UTC` e `01:00 UTC` sono due H1 diverse, sebbene entrambe appaiano `02:00` locali con offset rispettivamente +02 e +01.
2. **29/03/2026** ora legale: `00:00 UTC`, `01:00 UTC`, `02:00 UTC` restano tre H1 continue anche se la visualizzazione Roma salta dalle 01 alle 03.
3. cTrader `utcTimestampInMinutes` mantiene due istanti distinti durante la ripetizione dell'ora locale.
4. Un caso concreto e **puramente UTC**: osservazione alle `2026-11-03T16:01Z`; M15 chiusa alle `14:30Z` con età **91m**, ultima H1 chiusa alle `14:00Z` con età **121m**, quindi H1 fuori soglia **120m** pur con M15 entro **180m**. Testa anche il confine H1 120m valido, 121m non valido.

## Conclusione e limiti

**Il codice non mostra un errore di fuso orario come causa principale dei 12 H1 stale della diagnostica #37.** M15 e H1 possono avere età diverse perché l'H1 si forma solo con 4 M15 e il collector ruota gli strumenti in 120 minuti. Questo è una dimostrazione logica, **non un attestato di ogni candela reale**: le 12 H1 escluse non sono state ispezionate individualmente in questa PR. Casi di server/broker con clock non conforme, input manuale CSV ingenuo e gap storici vanno diagnosticati separatamente senza presumere che siano la causa.

**Prossimo gate:** riutilizzare la diagnostica privata per confrontare `lastClosedAt` UTC di M15/H1 e gruppi di raccolta (aggregati/redatti, nessun token/prezzo), poi testare offline una schedulazione che riduca il tempo massimo tra chiusura H1 e aggiornamento senza nuove chiamate broker o abbassamento della soglia. Non installare da questo ramo, non cambiare l'autoupdater e mantenere v1.61 LIVE.
