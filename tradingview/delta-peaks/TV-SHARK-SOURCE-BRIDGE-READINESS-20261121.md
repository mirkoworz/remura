# REMURA — TradingView / Shark Science: confini di integrazione delle evidenze

**Checkpoint di coordinamento scientifico · 21/11/2026 18:31 CET (Europe/Rome)**

## Versioni realmente ispezionate
- TradingView v0.8.186 LAB, branch `research/tradingview-anchor-request-v0186-20261121`, base HEAD `c1a35edfeb914fc5f24564b5ca2f11994bc9ee0d`; CI nuovi 16/16 PASS su GitHub run https://github.com/mirkoworz/remura/actions/runs/44929640322. L'ultima esecuzione attesta solo un digest non inviato a una TSA, non un clock indipendente.
- Shark Science v0.4 LAB, branch `research/track-b-shark-science-20261104`, HEAD `05e731b26bccb167ba7e0859797de01136a5c933`. Ispezionati i moduli reali: `scripts/shark_cot_asof_witness.py` (blob `babcfe4784f9cf6f75d5d83bf629588f4128c6d9`); `scripts/shark_retail_prospective_validation.py` (`f02b9e3109d587eaea405c2f9ea673ca3898fdc4`); `scripts/shark_cvd_cot_price_triage.py` (`b4d2c3baca3de2aa03c8426f69888069bf206a54`); `scripts/shark_signal_ingest_decision_link.py` (`393b7954b8278dd66a1cab3f62e4cca103b8d362`).
- Il codice Shark è **già articolato**: osserva as-of COT, receipt retail, link con decisione originale, proof HMAC fonte CVD privata. NON duplicare questi moduli con una nuova implementazione semplificata: rischio falsa prova di causalità.

## Informazioni obbligatorie prima di fondere i filoni

| Campo e prova | TradingView | Shark Science | Conclusione |
|---|---|---|---|
| Identità originale della stessa decisione | ledger M5 sintetico con digest anonimo; non attesta identità esterna | Squalincome history e link ingressi decisione | **NON DIMOSTRATO** che siano la stessa decisione |
| Strumento, feed, prodotto/contratto | nomenclatura TV e futuro mapping specifico | market FX / futures e provider cTrader | **MAPPING NON VERIFICATO** |
| Clock first-seen, close M5, ordine di ingest | solo timestamp di fixture; soglia <=120 s e prossima chiusura | clocks witness locali e receipt HMAC | **NESSUN CLOCK INDIPENDENTE COMUNE** |
| COT data, pubblicazione e first-seen reali | non usati come input v0.8.186 | witness locale del valore COT attualmente presente | **NESSUNA FIRMA CFTC** |
| Sentiment originario e disponibilità prima della decisione | non presente nel ledger M5 | receipt Myfxbook con vincoli first-seen | **NON COLLEGABILE** al singolo segnale TV senza verifica |
| Delta CVD e prezzo | TV CVD/price-only prospettico V2 | CLV x tick-volume cTrader proxy, NON flusso aggressore diretto | **NON EQUIVALENTI** per definizione |
| Fold, costi e risultati | preregistrazione 60m e 0/1/2 pip ipotetici, holdout futuri | studio incrementale separato, Squalincome storico | **NESSUN PNL O ALPHA INFERIBILE** |

## Requisiti per un futuro bridge verificabile
1. Identificatore di decisione stabile su originale (mai generato retroattivamente); crosswalk feed e strumento **esplicito** con famiglia prodotto, ticker e contratto.
2. Timestamp UTC della fonte originale, first-seen interno e ora di ricezione, con conferma che tutte le evidenze ausiliarie esistessero **entro** la decisione (as-of; evitare look-ahead).
3. Proof della stessa fonte/bytes prezzo/CVD, HMAC o digest con secret custodito privatamente; firma/testimone indipendente del clock per affermare reale esistenza temporale.
4. Denominatore completo delle decisioni eleggibili, anche quelle senza CVD/retail/COT; tutte le mancanze UNKNOWN e non etichette negative. Nessun rebinding delle osservazioni posteriori o sostituzione delle coppie FIFO assegnate.
5. Esito primario frozen CVD vs price-only a 60 min, secondari preregistrati, finestra di fold e scelte fissate prima dell'esame degli esiti; niente scegliere a posteriori il mercato o giorno che funziona meglio.
6. Materiale privato custodito in archivi separati. Nessuna chiave HMAC, identità collaboratore, report grezzo, prova originale o token nel repository pubblico.

## Stato di oggi e road map in ordine di priorità
- **Fino al 22/11 23:59:59 UTC** sviluppo congelato, non leggere gli esiti dell'holdout prima che maturino.
- **Holdout 1** `2026-11-23T00:00:00Z` incluso fino al `2026-11-30T00:00:00Z` escluso, con weekend iniziale soltanto diagnostico.
- **Holdout 2** `2026-11-30T00:00:00Z` incluso fino al `2026-12-07T00:00:00Z` escluso.
- Non attivare Private Capture, non importare dati dal collector Oracle, non modificare i protocolli V1/V2 o il pinned flow. L'assenza di un registro live affidabile rimane un **limite scientifico**, non qualcosa da risolvere generando un hash sintetico aggiuntivo.
- Contributors v0.87 LAB: nuova anteprima mobile offline (branch `research/contributors-pilot-mobile-v087-20261121`, codice testato `a8a4d5a6a7ef0360fa90cb50345de15b26bdf2ce`, 22/22 nuovi test PASS), staging NO-GO perché daily D1 e Access seats non attestati.
- Experience v0.30 LAB splash toro/orso 3D + REMURA pinna/SMF, Private Capture v0.15 LAB non attivato; Oracle collector autoupdater bloccato e v1.65 staged NON installare; radar Ampere, backup reale, Squalincome e futuro Telegram post approvazione preservati.
- Continuità: **questa è soltanto una verifica documentale di sorgenti preesistenti** e NON una nuova suite CI, un nuovo modello statistico, una connessione ai feed o una prova di redditività. Nessuna modifica a main, Cloudflare, Oracle, policy o costo.

**Semaforo bridge istituzionale live: NO-GO; il passo utile è acquisizione affidabile, coerente e prospettica, non nuove simulazioni sostitutive.**
