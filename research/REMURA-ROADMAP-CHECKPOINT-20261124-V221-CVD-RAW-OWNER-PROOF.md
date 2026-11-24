# REMURA A V22.1 LAB — prova aggregata di ripresa CVD RAW

Checkpoint di osservazione: 24 novembre 2026, ore 09:14–09:15 CET (Europe/Rome, UTC+01:00). PR #112 Draft. HEAD precedente: 64cb01c2ec97e8ea2febdcf7c057e6fde1cb3a4c.

## Provenienza e perimetro

Due interrogazioni SELECT mirate sono state eseguite manualmente dal proprietario nella console D1 esistente da iPhone; risultati osservati da ChatGPT nelle due schermate fornite dal proprietario. Non si tratta di accesso diretto di ChatGPT a D1, di attestation crittografica o di verifica indipendente dei byte. Nessun screenshot, identificativo privato, payload, credenziale, valore CVD o prezzo viene pubblicato. Entrambe le interrogazioni autorizzate sono state utilizzate; nessun retry.

Filtro: versione 0.9.1-cvd-lab; timestamp di ricezione nel giorno civile 2026-11-24 CET (intervallo UTC [2026-11-23 23:00, 2026-11-24 23:00)). Prima query: conteggio eventi, RAW non nulli/non vuoti dopo trim, chiusure distinte, minimo e massimo ricezione. Seconda query: LAG delle chiusure partizionato per simbolo/timeframe, distanza esatta 300000 ms, json_valid(raw_json), ricezione meno chiusura inclusa fra 0 e 120000 ms.

| Misura | Risultato osservato |
| --- | ---: |
| Eventi (entrambe le query) | 13 |
| RAW non vuoti | 13 |
| Chiusure distinte | 13 |
| JSON sintatticamente validi | 13 |
| Coppie di chiusure M5 consecutive | 12 |
| Ricezioni entro 0–120 secondi dalla chiusura | 13 |

Prima ricezione 2026-11-24 08:10:02 CET (07:10:02 UTC); ultima ricezione 09:10:03 CET (08:10:03 UTC; data coerente con filtro e schermata). Le 12 coppie consecutive condividono barre e non sono 12 decisioni o osservazioni economiche indipendenti. Le query non attestano il valore del simbolo/timeframe, la conformità semantica della busta, la qualità del CVD, la provenienza autenticata o il flag di ammissione scientifica.

Stato: RAW_PRESENCE_SYNTAX_CONTINUITY_TRANSPORT_CONFIRMED_OWNER_SCREENSHOTS; PROSPECTIVE_DIRECTION_NOT_ATTESTED.

## Interruzione della raccolta

Il proprietario riferisce di avere disattivato accidentalmente l'alert TradingView il 23 novembre intorno alle ore 22 CET e di averlo ripristinato la mattina del 24 novembre. Il grafico delle interrogazioni D1 delle ultime 24 ore mostrato dal proprietario è coerente con una pausa e una ripresa, ma non attesta autonomamente la causa o gli orari esatti. Non imputare automaticamente il buco a un malfunzionamento REMURA; non imputare/riempire dati mancanti. La continuità del feed prezzi cTrader resta un controllo distinto. La prima ricezione odierna osservata non è una prova dell'ora esatta di riattivazione dell'alert.

## Conseguenze scientifiche e prossime operazioni

- Le precedenti 12 ricevute TEST del 23 novembre rimangono OBSERVATION_ONLY. Nessuna retrodatazione o reinterpretazione.
- I nuovi eventi restano candidati di ricerca: sintassi e puntualità di trasporto non equivalgono a is_timely o ad ammissione prospettica. CVD proxy di volume classificato, non volume CME eseguito o ordini istituzionali.
- Zero decisioni prospettiche autentiche ammesse; alpha e P&L N/D. Non dedurre una direzione dalle statistiche aggregate.
- Prossimo passo, previa autorizzazione distinta: acquisizione privata dei nuovi RAW con timestamp verificabile, validazione del contratto nativo e riuso di V21.4 / V21.1 / V21.2 e del freezer esistente. Congelare decisioni prima degli esiti e con attestazione temporale indipendente, solo per eventi futuri idonei. Nessun trasferimento di RAW su GitHub pubblico.
- Copertura prezzi 60m/4h già verificata sulle quattro coorti ipotetiche precedenti; 24h da verificare su copia SQLite aggiornata e coerente, senza ripetere la precedente prova.
- Soglia esplorativa invariata: 30 confronti completi e 10 finestre non sovrapposte per orizzonte, non prova definitiva.
- Filoni B, C, D invariati.

## Budget e sicurezza

Il pannello D1 mostrato alle 08:38 CET indica 4 database, 6 righe lette, 24 scritte e 7,72 MB di storage totale; margine Free ampio secondo la schermata e la conferma del proprietario. Le successive schermate si riferiscono a finestre temporali diverse. Nessuna nuova interrogazione D1 per questo commit; nessuna modifica a gateway, alert, Oracle, collector, broker, Cloudflare, main o produzione; nessun merge/deploy. Solo prova aggregata Markdown, nessuna modifica del codice o avvio manuale CI.
