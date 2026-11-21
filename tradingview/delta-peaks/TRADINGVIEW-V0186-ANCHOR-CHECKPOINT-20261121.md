# REMURA TradingView v0.8.186 LAB — ANCHOR REQUEST SHA256

**Checkpoint 21 novembre 2026 · ore 18:24 CET (Europe/Rome)**

## GitHub
- Repository pubblico `mirkoworz/remura`, branch di ricerca `research/tradingview-anchor-request-v0186-20261121`.
- Base v0.8.185 LAB `26a44db318d53d3964f407bb3f364fde24a5debc`.
- Commit CODICE testato `a0706612f912b72582a99682063c093d1d015c0f`.
- Run https://github.com/mirkoworz/remura/actions/runs/44929640322 **SUCCESS**. Log `Ran 16 tests`, `OK`, `REMURA_TV_V0186_ANCHOR_REQUEST=16_16_PASS`, controllato direttamente.
- **16 nuovi test PASS**, nessuna suite storica rieseguita. Workflow `.github/workflows/remura-tv-v0186-anchor-one-shot-ci.yml`, runner pubblico di sola lettura e `persist-credentials:false`, senza Secret, fetch mercati, deploy, Cloudflare/Oracle live, merge o costo.

## Nuova capacità
- `anchor_request_v0186_lab.py`: dopo verifica del ledger M5 sintetico v0.8.185 e protocollo V2 pinned, costruisce un digest SHA-256 deterministico con separazione di dominio. Non pubblica record, timestamp individuali o identità nel riepilogo. Digest pronto per **futura** domanda di timestamp indipendente; **nessuna domanda inviata**.
- `receipt_review`: controlla solo forma e corrispondenza digest di un placeholder; **NON verifica firma RFC 3161 né provenienza di servizi di terze parti**. `signature_verified=false` anche se la forma è coerente.
- `test_anchor_request_v0186_lab.py`: 16 nuovi test su determinismo, input alterati, cross-fold, receipts fasulle, soglie, non disclosure e nessuna acquisizione.
- `TRADINGVIEW-V0186-ANCHOR-REQUEST-RUNBOOK-20261121.md` spiega prerequisiti per un vero anchor. Un autore può cambiare tutta una catena non attestata e ricalcolarne l'hash; non dichiarare che la semplice consistenza equivalga a prova di registrazione prospettica.
- Output `network_calls_performed=0`, `request_submitted_to_tsa=false`, `independent_timestamp_token_verified=false`, `trusted_anchor_established=false`, `capture_clock_proven=false`, `trade_edge_proven=false`, `decision=NO_GO_LIVE`.

## Roadmap scientifica
- V2 invariato byte-for-byte (protocollo `CVD-PROSPECTIVE-PROTOCOL-V2.md`); development 16–22/11 UTC, holdout 1 23–29/11, holdout 2 30/11–06/12/2026. Nessun risultato valutato prima dei fold.
- Primario CVD vs price-only 60 min, FIFO per strato, orizzonti e costi ipotetici preregistrati. Nessun edge dimostrato; no imputation di missing bar e nessuna retrodatazione di eventi. Prima di utilizzare un anchor realmente indipendente servono ricevuta firmata, fiducia, chain di certificati, timestamp certificato, dati reali con clock/provenienza, e consenso/costi.
- Shark Science v0.4 LAB COT/sentiment/delta-CVD/assorbimento, senza fusione ecologica di metriche anonime e decisioni individuali.
- Contributors v0.86 prepara solo piano Cloudflare/Access, senza app reali; Experience v0.30 LAB toro/orso + SMF; Private Capture non attivo, Oracle collector non modificare, Ampere Radar e backup/Squalincome/TG roadmap mantenute.
- Non ripetere test storici; iPhone sufficiente per GitHub LAB, nessuna spesa o merge. Preservare tutti i riferimenti in passaggio chat.

**Conclusione: v0.8.186 LAB 16/16 PASS, digest non ancorato, nessun risultato trading e nessuna attestazione reale.**
