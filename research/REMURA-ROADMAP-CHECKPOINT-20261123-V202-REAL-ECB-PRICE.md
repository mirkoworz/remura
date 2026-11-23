# REMURA V20.2 — CHECKPOINT REALE: PREZZO BCE E HOLDOUT CVD
Aggiornamento: **23 novembre 2026, ore 06:49 CET — Europe/Rome**.
Stato: **research isolato, NON in main, NON distribuito**.

## Continuita'
Eredita integralmente V01–V20 e V20.1, compresa la ricerca research/remura-v20-incremental-observations-20261123 (HEAD 3b4e836bf206e70b302b52acee10ae67b3c07dd4). Nessun test precedente va rifatto, nessuna sovrapposizione con Mac/Codex, Oracle, v1.65, Splash, collector privato. Non modificati PR #105 e #106, entrambe DRAFT.

## Raccolta reale gia' confermata prima del V20.2
Myfxbook RETAIL: main a1188f8af77951b9c59b7bb1facbfa6fe2f820e7, ultimo t 2026-11-23T02:55:17Z; 30 serie attive con nuovi snapshot, 18 percentuali long cambiate (15 discese / 3 salite), 12 invariate. Quattro indici storici rimasti stale. Totale serie Myfxbook conservate 34, record 3924, le 30 serie attive usano finestra rolling 126 e perdono il record piu' vecchio.

Capital.com DEMO PRIVATO: main a4fd286439007fc9620904f7f20c3c018425f29c, ultimo t 2026-11-23T02:53:02Z; 31 nuovi record; 30 variazioni long% e 1 invarianza (aggregati 19 aumento, 11 diminuzione). Totale Capital conservato 3822; Firestore run 45102719693 SUCCESS, 32 documenti sincronizzati (NON 32 trade o outcomes). Le osservazioni complessive attualmente trattenute sono **7746** su 65 serie, non 7746 esempi indipendenti o previsioni.
Prove non ridondanti V20.1: GitHub Actions 45119080090 (9/9 nuovi test SUCCESS) e 45119190899 (prova dei 34 JSON PUBBLICI reali SUCCESS).

## V20.2: fonte PREZZI indipendente GRATUITA, primo dato ufficiale acquisito
Fonte ufficiale BCE: https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml e documentazione https://data.ecb.europa.eu/help/api/data-examples .
Report di riferimento BCE: giornaliero, pubblicato normalmente verso le 16 CET, non OHLC, tick, volume eseguito o prezzo contrattabile.

Ramo: **research/remura-v202-ecb-independent-price-witness-20261123**.

Nuovo codice:
- research/ecb_daily_reference_witness_v202.py: UNA GET pubblica verso BCE, zero API key, zero Secret, zero provider privati, zero retry; legge USD, JPY, GBP, CHF, CAD, AUD, NZD e deriva 28 cambi incrociati usando EUR come base. Valida XML, tassi, duplicati, data futura, massimo 7 giorni di ritardo e scrive nel risultato il solo tempo di osservazione POST-fetch, non un first-seen inventato.
- research/test_ecb_daily_reference_witness_v202.py: **11 test NUOVI** isolati, non ripetono suite passate.
- .github/workflows/remura-v202-ecb-real-price-witness.yml: one-shot push sul solo ramo V20.2, senza cron, deploy, push automatico o Secret.
- CI reale: https://github.com/mirkoworz/remura/actions/runs/45119825672 — **SUCCESS**: 11 test nuovi GREEN e GET BCE PUBBLICA davvero riuscita, 28/28 coppie FX.

### Prima prova prezzi effettiva e verificabile
- Data di riferimento BCE: **20 novembre 2026**; NON 23 novembre, perche' alle 06:46 CET del 23 il nuovo valore quotidiano non era ancora pubblicato.
- Data e ora in cui GitHub Actions ha osservato il dato: **2026-11-23T05:46:14Z = 06:46:14 Europe/Rome**.
- SHA256 del documento XML ricevuto: **a234540a78d0bccccc3642bfe604b138310a03741361434907aa4cf3e7622e8a**.
- Cambio BCE EURUSD **1.09900000**; USDJPY **158.64422202** (cross JPY per EUR diviso USD per EUR); CADJPY **110.88850728** (cross JPY per EUR diviso CAD per EUR).
- Sono 28 riferimenti giornalieri, non prezzi eseguibili. Primo witness pubblico conservato in forma JSON in research/price-witness/REMURA-ECB-20261120-OBSERVED-20261123T054614Z-V202.json, estratto dalla run GitHub SUCCESS. Solo dati istituzionali PUBBLICI, nessun simbolo/valore privato.
- Il raw XML integrale NON e' stato archiviato; SHA256 e risultati riportati non costituiscono attestazione indipendente dell'istante di pubblicazione storica o della presenza del tasso nelle decisioni precedenti. Politica conservativa: eleggibilita' solo **dopo 05:46:14Z del 23 novembre**, e marcatura stale se usato nel contesto del mercato del lunedi'.
- Nessun rendimento futuro o alpha deriva da un solo anchor di venerdi'. La prima variazione giornaliera realistica richiede un successivo riferimento pubblicato e osservato dopo il checkpoint. Il feed BCE e' troppo lento per valutare CVD M5/H1/H4.

## CVD — conferma di BLOCCO OPERATIVO, non di perdite
Dalla lettura GitHub Actions delle 400 run pubbliche piu' recenti: **nessuna nuova verifica manuale delle ricevute CVD TEST dopo l'inizio dell'holdout (23/11/2026 ore 00:00 UTC)**. L'ultima run con titolo REMURA CVD TEST Batch Reader visibile nella storia esaminata e' 44362438343 del **18/11/2026 17:46 UTC**, SUCCESS (prima della finestra). Il run v0192 successivo del 22/11 e' una CI LAB di codice, non una prova runtime.

Conclusione rigorosa: Worker TEST operativo? **UNKNOWN**. Alert di mercato inviati dopo 23/11 00:00Z? **NON ATTESTATI**. Ricevute forward-only/first_seen e CVD con prezzi M5 indipendenti? **NON ATTESTATI**. Non equivalgono a zero eventi, zero guadagni o assenza di alpha.

PROSSIMO PASSO NECESSARIO: previa autorizzazione separata specifica e verifica quota Free, UNA diagnosi soltanto read-only di Worker TEST e ricevute TEST successive al 23/11 00:00Z con credenziali preesistenti a sola lettura e senza GraphQL nuova non autorizzata, SQL write, deploy, Secret da pubblicare, retry automatici o mutazioni. Riportare solo numero eventi e metadata temporali anonimi.

## Contributors: pilot 1–2 amici
Rimane **NO-GO**. Frontend iPhone v0.95 e contratto server v0.96 LAB gia' collaudati; v0.97 Free gate 21/21 gia' GREEN, non ripetere. Mancano letture verificate nell'account personale Cloudflare: posti Access, righe giornaliere D1 lette/scritte, richiesta Worker, Billing; e poi collaudo reale JWT server/ruoli/ownership/approvazione OWNER/receipt/revoca completa. La vecchia autorizzazione a due richieste GraphQL e' esaurita; non riutilizzarla.

## Roadmap da eseguire, non altri simulatori
1. Avviare audit read-only del CVD TEST SOLO dopo consenso puntuale del proprietario. Se non risultano eventi, restituire NO CONFIRMED EVENTS e distinguere errori di delivery dal non generare alert.
2. Agganciare prezzi intraday REALI e autonomi, con timeframe M5/M15 e osservazioni prospettiche prima di decisione; il motore privato cTrader gia' esistente e' di competenza Mac/Codex, non sovrapporsi.
3. Dopo una futura pubblicazione BCE giornaliera, raccogliere con nuovo consenso/piano un secondo witness e confrontare soltanto prezzi daily; nessuna schedulazione automatica e' stata accesa.
4. Proteggere retention retail Myfxbook evitando perdita della finestra rolling, su branch/ambiente autorizzato e con budget verificato.
5. Owner da Safari Cloudflare read-only dashboard Access, D1, Workers, Billing per chiudere Free gate; poi autorizzazione distinta staging e 1–2 utenti veri.
6. Integrazione controllata Cockpit v1.68, Contributors e Splash Mac in release dopo revisione e consenso; ogni pagina HTML modificata dovra' avere numero versione e timestamp Europe/Rome in alto.

## Sicurezza e costi
ZERO modifiche main, Oracle, Mac, Cloudflare, Access, D1, Firestore, Secrets, utenti; ZERO nuove sottoscrizioni. Una GET ufficiale BCE senza chiavi ha prodotto dati reali; una run CI breve su ramo pubblico GitHub. Non dedurre residuo delle quote personali da quello che e' stato usato.

**Conclusione: raccolta sentiment funzionante; un primo anchor prezzo BCE indipendente e vero e' ora documentato; misurazione intraday CVD e alpha rimangono NON DIMOSTRATE; Contributors live ancora NO-GO.**


## 23/11/2026 06:52 CET — RISPARMIO D1: workflow ESISTENTE per holdout V2
Prima di qualsiasi chiamata Cloudflare, verificato in GitHub il codice gia' esistente, evitando di sviluppare un doppione o interrogare per errore le ricevute del 14 novembre:
- Il vecchio workflow REMURA TEST First Webhook Receipt legge le **prime 100** ricevute dal **14/11** (ordinamento crescente), quindi potrebbe restituire solo storia vecchia. NON utilizzarlo per attestare l'holdout iniziato il 23/11.
- Workflow piu' adatto, **gia' presente su main**, senza deploy: REMURA CVD TEST Batch Reader, file .github/workflows/remura-tv-cvd-batch-readonly-manual.yml. Accetta start_utc/end_utc e modalita' receipt-only per **massimo 12 chiusure M5** e verifica maturazione >=120 secondi. Codice immutabilmente pinnato al commit 08f5cdb48d430739ce3688480d95ac78aea3640b.
- Sul caso receipt-only fa **esattamente 1 GET REST inventario D1 TEST + 1 POST REST che esegue esclusivamente SELECT parametrizzato** sul DB TEST isolato, non GraphQL; NO D1 write. Il reader legge alcuni raw_json delle righe nell'ambiente GitHub runner per validare formato ma **non pubblica i raw payload nel summary**, riporta soli aggregati. Questo dettaglio di accesso a righe reali richiede **consenso esplicito separato**, non va occultato.
- Finestra di prova conservativa gia' maturata: start_utc=**2026-11-23T04:30Z**, end_utc=**2026-11-23T05:25Z**, mode=**receipt-only**, confirmation=**READ_CVD_TEST_BATCH_ONLY**. Sono 12 slot M5, all'interno dell'holdout V2, adatti alla diagnosi del trasporto senza PnL o pretesa di copertura dell'intera giornata.
- URL: https://github.com/mirkoworz/remura/actions/workflows/remura-tv-cvd-batch-readonly-manual.yml .
- Prima di eseguire: autorizzazione dell'OWNER per esattamente queste 2 richieste REST TEST in sola lettura, token di sola lettura preesistente, previa verifica del margine gratuito. Senza autorizzazione **NON eseguire**.
- Risultato NO_MATCHING_RECEIPTS = **assenza di ricevute nella finestra scelta**, non prova che nessun alert sia partito o che il Worker sia inattivo. Risultati missing/invalid vanno distinti da zero eventi. Se risultati parziali, nessun retry automatico.

**Nessuna chiamata Cloudflare o nuovo workflow e' stata eseguita in V20.2 durante questa ricognizione codice.**
