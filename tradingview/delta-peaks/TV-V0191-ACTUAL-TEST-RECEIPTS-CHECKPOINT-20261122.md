# REMURA TradingView v0.8.191 — audit reale delle prove TEST già presenti
22 novembre 2026 · Europe/Rome · SOLO LAB in sola lettura, nessuna acquisizione.

## Nuova prova rispetto alle simulazioni precedenti
Nel branch di ricerca sono disponibili quattro file JSON sanitizzati delle letture TEST CVD EURUSD, già presenti nel repository:
- evidence/fx_first_receipt_20261116.json — run 43839770016, 4/4 barre;
- evidence/fx_second_receipt_20261116.json — run 43851249699, 12/12 barre;
- evidence/fx_third_receipt_20261118.json — run 44294693651, 12/12 barre;
- evidence/fx_fourth_receipt_20261118.json — run 44362438343, 12/12 barre.

Totale: 40 barre nelle finestre TEST esplicitamente richieste, NON nel mercato intero e NON nel futuro holdout. Le quattro ricevute dichiarano: target EU_D1_TEST_ONLY; independent_provenance=false; scientific_admission=false; conflict_ledger_available=false; account_quota_utilization=null. Il conteggio 40/40 NON dimostra indipendenza, pubblicazione originaria, assenza di altre barre, copertura di mercato o profitto.

Il repository main al checkpoint espone 16 file workflow remura-tv-*.yml preesistenti. Ispezione REST GitHub READ-ONLY: tutti con workflow_dispatch, nessuno schedule; uno include push. **Questo NON prova che un Worker Cloudflare, una TradingView alert o un altro collector siano spenti**, ne' certifica l'assenza di dati prospettici esterni. Non e' stato interrogato alcun provider live.

## Codice nuovo
- tradingview/delta-peaks/checked_in_receipt_reality_v0191_lab.py
- tradingview/delta-peaks/test_checked_in_receipt_reality_v0191_lab.py (14 casi mirati)
- .github/workflows/remura-tv-reality-v0191-only.yml

Verifica realmente i byte dei quattro metadata JSON tramite blob SHA del Git checkout e controllo di forma, run ID unici, ordine/numero di slot M5, periodo pre-holdout e fonti dichiarate. Ispeziona soltanto i 16 nomi workflow preesistenti nella propria copia di checkout; quarantena ogni variazione, file mancante o schedule aggiunto. Non sostituisce una lettura delle API del provider e non verifica firme o timestamp indipendenti. L'unita' di misura della prova e' **file JSON TEST versionato**, NON market bar originale o autenticata.

## Per il 23 novembre
Il protocollo immutabile V2 prevede il primo holdout alle 00:00 UTC / 01:00 CET. Da questo inventario non si puo' dichiarare CVD disponibile nel holdout; occorre registrare davvero future barre/prove prospettiche e validare autenticamente clock, identita' per decisione, origine, comparatore e market coverage. Nessun invio di segnali, attivazione automatica, tuning o claim di vantaggio.
