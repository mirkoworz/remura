# REMURA v0.8.66 LAB — 14/11/2026, checkpoint deploy 13:36 CET

## Gateway TEST CVD attivo
- Run reale [43595646049](https://github.com/mirkoworz/remura/actions/runs/43595646049) SUCCESS.
- Cloudflare versione d237bb64-aab8-4cb2-8680-d692fe73cd5a; deploy 12:36:36 UTC, postcheck SETTINGS_VERIFIED. Nome Worker TEST e D1 TEST EU già verificati; nessuna modifica produzione. Non è una prova HTTP edge o ricezione CVD.
- Pin Gateway 58dc84e0de93b48eb5a6c596664d4d338548754a. Worker già esistente, medesimi token/limiter. Nessun nuovo servizio.

## Preparazione alert FX:EURUSD
1. Grafico standard EURUSD M5, ID esatto FX:EURUSD (verificare nel pannello CVD). Non rinominare FXCM:EURUSD.
2. Indicatore compilato REMURA ALL-IN-ONE Premium v0.9.1 CVD PREVIEW, non v0.9 visual-only e non v0.8.1 BTC. Impostazioni numeriche default e DAY/previous day attivi; confrontare CONFIG in cvd_telemetry_preview_v1.py. Attivare solo l'input CVD LAB: payload preview (DO NOT CONNECT CURRENT WEBHOOK): la dicitura precedente risale a prima del deploy TEST.
3. Creare nuovo alert, condizione Any alert() function call (Qualsiasi chiamata alla funzione alert()), nome REMURA CVD FX EURUSD M5 TEST. Notifiche webhook: riusare esattamente l'URL TEST privato già salvato dell'alert BTC senza condividerlo in chat/git. Il JSON è generato da Pine, non incollarne uno manuale. Non modificare né duplicare alert BTC, non creare altri alert FX concorrenti.
4. Nel weekend può essere predisposto se TradingView lo consente; nessun evento finché non chiude una barra realtime. Se non consente l'attivazione, farlo alla riapertura effettiva; non inferire orario dal solo calendario. Dopo creazione controllare stato attivo. Non toccare input dopo creazione senza rifare snapshot alert.
5. Spegnere soltanto alert BTC domenica sera prima del cutoff 16/11 00:00 UTC (01:00 CET). Non interrompere gateway condiviso se FX attivo.
6. Dopo prima ricezione reale e maturazione 120 s, lettore CVD dedicato con primo/ultimo close UTC osservati, max 72 slot (non assumere mercato aperto). Primo close ammesso 14/11 12:40 UTC, allineato dopo deploy, non necessariamente ora apertura Forex.

## Verifiche
- Se delivery fallisce, verificare simbolo/config/condizione/URL esatto senza pubblicare token. Il gateway richiede ritardo ricezione 0–120 s e configurazione congelata.
- CVD sender effettivo non attestato dalla compilazione; CVD è proxy di volumi classificati, non esecuzioni CME.
- Non duplicare v1 legacy FXCM e nuova coorte FX. CVD is_timely=0 intenzionale nel vecchio DB; lettore dedicato valuta trasporto, nessun segnale operativo.
- STOP_CVD_TEST e ROLLBACK_LEGACY_TEST nel workflow CVD manuale solo se necessario; non usare vecchi workflow incompatibili col quinto binding. Quote effettive non ancora misurate.
