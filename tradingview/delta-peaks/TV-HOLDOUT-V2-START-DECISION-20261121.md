# REMURA TradingView v0.8.186 LAB — DECISIONE PRE-HOLDOUT 21 NOVEMBRE 2026

**21 novembre 2026 · Europe/Rome · Documento di custodia scientifica pre-avvio, nessun protocollo o codice modificato.**

## Evidenze già verificate — NON rieseguire
- Branch base di questo dossier `research/tradingview-anchor-request-v0186-20261121`, HEAD `c1a35edfeb914fc5f24564b5ca2f11994bc9ee0d`. Protocollo prospettico `tradingview/delta-peaks/CVD-PROSPECTIVE-PROTOCOL-V2.md` blob Git `4b0f5d5defacfdbf8e902af5a8eea32947cabeca`, letto e confermato **immutato**.
- Il protocollo V2 ha come obiettivo primario il confronto CVD vs price-only a **60 minuti**; secondari 4h/24h e filtri preregistrati, round-trip ipotetici 0/1/2 pip, FIFO/strati e osservazioni tempestive entro **close+120 secondi** e prima del successivo M5. Costi ipotetici non sono costi d'esecuzione. Mancanti non rimpiazzabili. Niente ricalcolo decisioni da storia successiva, leakage fra fold o tuning durante l'holdout.
- Development **16/11/2026 00:00 UTC — 23/11/2026 00:00 UTC**, holdout 1 **23/11/2026 00:00 UTC — 30/11/2026 00:00 UTC**, holdout 2 **30/11/2026 00:00 UTC — 07/12/2026 00:00 UTC**. Estremi iniziali inclusi, finali esclusi; inizio weekend diagnostico, non aspettarsi barre di mercato quando il mercato è chiuso.
- `tradingview/delta-peaks/gateway-lab/cvd_staged_runtime_preflight_v1.py` (blob `5152e11a9eba657a76579dff4bcfd2feefdab6ed`) richiede flag `explicit=True`, budget genuine recente, host metrics genuine e uso di snapshot; non è uno scheduler attivo né una prova di ingest reale.
- `tradingview/delta-peaks/gateway-lab/cvd_receipt_window_audit_v1.py` (blob `3d2fa8482479dc215fcd19951aa6925b22bec22d`) legge ricevute di finestre **richieste**, non prova copertura del calendario FX, e mantiene `independent_provenance=false`, `outcomes_computed=false`.
- v0.8.186 LAB aggiunge `anchor_request_v0186_lab.py`, sha testato `a0706612f912b72582a99682063c093d1d015c0f`; CI `44929640322` verde **16/16 nuovi test**. Produce solo digest SHA-256 **non inviato**, `trusted_anchor_established=false`. Digest e catena locali non provano che una decisione esistesse prima dei risultati.
- `Private Capture v0.15 LAB` era sintetico/non attivato al checkpoint noto. Non è stata trovata in questi nuovi commit evidenza di attivazione di acquisizione LIVE o di un sistema di attestazione indipendente. Non sostituire un'assenza di osservazioni effettive con un report di test.

## Semaforo operativo per il 23 novembre — esplicito
| Verifica | Stato documentabile al 21 novembre |
|---|---|
| Preregistrazione degli orizzonti, fold, costi, matching | **PINNED / VERIFICATO** |
| Candidate M5 originali con clock di ricezione durante il fold | **NON ATTESTATE** |
| Ricevute indipendenti contenenti data/ora autentiche e immodificabili | **NON ATTESTATE** |
| Inventario continuo dei fold e osservazioni mancanti | **NON ATTESTATO** |
| Budget provider/free per acquisizioni nuove | **NON ATTESTATO** |
| Risultato OOS e superiorità CVD sul prezzo-only | **NON MISURATO** |
| Avvio LIVE, letture segrete o modifiche Oracle autorizzate da questo dossier | **NO-GO** |

**Conseguenza metodologica:** il calendario del protocollo resta congelato, ma se non avvengono acquisizioni originali registrate tempestivamente durante l'intervallo, il fold NON acquisisce validità retrospettiva. Non si può rinominare lo storico come nuovo holdout. Si annoterà copertura mancante/UNKNOWN e si manterrà il test non valutabile, anziché inventare risultati o prorogare arbitrariamente le date.

## Per il prossimo passaggio realmente utile
1. Prima di qualsiasi attivazione, verificare capacità Free, security budget e modalità di custodia di un vero feed di acquisizione; richiede autorizzazione specifica del proprietario, nessuna attivazione implicita da `Ok andiamo avanti` per risorse reali.
2. Se il proprietario decide di abilitare una futura raccolta, mantenere segnali e ricevute su un canale privato non pubblicabile e un clock esterno verificabile nel momento originale; avvio e fallback solo con rollback e tetto di consumo approvati.
3. Non spostare holdout1/holdout2 in automatico: un eventuale nuovo esperimento necessita *nuova preregistrazione separata*, prima di raccogliere dati futuri, mai dopo averne visto gli esiti.
4. Riprendere Shark Science solo come fonti ausiliarie per identità strumento/contratto, COT pubblicazione/first-seen, sentiment predecisione, CVD proxy e ricezione. Non applicare indicatori aggregati a una singola decisione senza prove causali.
5. Contributors v0.89 demo iPhone separata con 30/30 test; D1 daily & Access seats reali non misurati, staging NO-GO. Experience v0.30, Private Capture, Oracle collector protetto, Ampere Radar, Squalincome e backup preservati. Nessun Mac, nuovo costo o deploy introdotto.

**Esito: protocollo pronto a livello documentale, acquisizione OOS prospettica NON attestata. Non dichiarare trading edge.**