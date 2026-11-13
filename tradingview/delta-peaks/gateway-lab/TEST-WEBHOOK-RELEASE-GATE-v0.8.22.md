# REMURA — TEST WEBHOOK RELEASE GATE v0.8.24 (NESSUN DEPLOY)
**Aggiornamento: 13/11/2026, ore 15:55 CET**  
**Sola documentazione e prove offline, PR #102 OPEN/DRAFT. Worker Production v0.8.5 non modificato.**

## Checkpoint piano Workers Free — 13/11/2026, ore 15:55 CET
- Screenshot reale dell'utente Cloudflare → **Workers plans**: `Free $0` indicato come **Current plan**, Paid `$5/month + usage` disponibile ma non selezionato. **Verificato l'effettivo piano Workers Free** per l'account alla data del controllo; non richiedere di nuovo uno screenshot del piano.
- Per i soli Workers Free: 100.000 richieste/giorno/account, 10 ms CPU per richiesta, massimo 100 Worker (documentazione ufficiale 2026). La conferma Workers Free **non prova l'assenza di altri prodotti a pagamento né una fattura a zero**. Restano non accertati CPU reale, consumo aggregato di tutti i Worker, eventuali fatture e binding limiter del Worker TEST.
- Modificare solo il piano Workers è operazione da non fare: **NO upgrade** senza nuova richiesta e consenso utente. Nessuna necessità attuale di passare a Paid per una compilazione TEST o piccoli volumi teorici.
- Il rate limiter per Workers è approssimativo, attivo solo dopo l'arrivo della richiesta al codice, e non protegge da abuso anonimo sul conteggio account; la documentazione non dimostra né quota né disponibilità reale del binding per questo nuovo Worker. Serve preflight prima di abilitarne l'ingestione.
- **Prossimo gate indipendente**: preparare credenziali minime Workers *per il solo Worker TEST* e binding confermati senza sostituire quelli già configurati del Worker Production. Il primo deploy è autorizzabile **solo OFF**, separatamente dal consenso a eventuali webhook TradingView reali.

## Nuova prova non distruttiva (v0.8.23)
- [Wrangler compile-only #43443677850](https://github.com/mirkoworz/remura/actions/runs/43443677850) SUCCESS: 5 test isolati più compilazione reale `wrangler@4.157.0 deploy --dry-run`; pacchetto 11,76 KiB (gzip 4,06 KiB). Non è avvenuto upload né deploy. Config TEST temporanea con D1 e rate limiter sintetici; account, Secrets, Worker Production e dati D1 non toccati.
- Un primo test di eccezione del manifest aveva fallito e viene registrato correttamente; fix `1c6a783f` ha reso la prova fail-closed. **Questo non è un preflight finale di autorizzazione al deploy**.
- Numero teorico di heartbeat EURUSD M5 = 288/24 h, pari a 0,288% delle 100k richieste giornaliere Free se fosse l'unico utilizzo. Non compresi ritrasmissioni, altri Worker e richieste anonime. **Piano Cloudflare, CPU e fatture effettive NON ancora verificati.**
- Al prossimo rilascio reale, NON caricare la configurazione sintetica del dry-run: occorre generare separatamente il file di Worker TEST da identità D1 verificata nell'account, Secret separato, limiter univoco e autorizzazione esplicita. **Nessun token dev'essere incollato in chat.**

## Evidenze accertate
- Cloudflare Worker **Production** `remura-tv-ingest-lab` è legato a D1 **PRINCIPALE**: `TELEMETRY_DB → remura-tv-lab`; confermato da screenshot dell'utente. **Mai usarlo come banco di prova**.
- Cloudflare D1 inventory GET autenticato [Actions #43441281362](https://github.com/mirkoworz/remura/actions/runs/43441281362) **SUCCESS**: D1 `remura-tv-lab` e `remura-tv-lab-test` con UUID distinti e giurisdizione UE. La lettura NON ha stampato/conservato UUID; 12 test offline PASS. La disponibilità del DB TEST non equivale a permesso di deploy Worker.
- Manifest `wrangler.webhook-test.EXAMPLE.json` intenzionalmente non distribuibile: Worker name `remura-tv-webhook-test`, solo `TELEMETRY_DB → remura-tv-lab-test`, `INGEST_ENABLED=false`, UUID e namespace limiter segnaposto. È una **bozza**, non la configurazione Cloudflare.
- Sorgente gateway GitHub v0.8.6: se flag OFF o manca limiter/D1/secret, l'endpoint ingest risponde **503 disabled**; test Node con FakeD1; non è una verifica del Worker distribuito. `test_d1_test_target_preflight_v1.py` controlla identity e no-POST; `worker.test.mjs` simula kill-switch ON → OFF, senza cancellare alcun record TEST.
- API Cloudflare Worker Settings con token D1 READ ha già restituito `403` sul control-plane: non riutilizzare per tentativi identici e non attribuire questa causa al BIC del sito pubblico. Non è attualmente disponibile un token autorizzato al deploy.
- Cloudflare Free **limiti pubblicati**: Workers **100.000 richieste/giorno/account**, **10 ms CPU/invocazione**; D1 Free **10 DB/account, 500 MB/DB, 5 GB/account**. **Workers Free confermato da screenshot del proprietario 13/11/2026**; restano non verificati fatture/account billing aggregato e CPU per invocazione sul nuovo Worker. Aggiungere un Worker non prova che il costo sarà zero, e la quota account è condivisa da altri servizi.
- Rate Limiting binding Cloudflare: `namespace_id` deve essere una stringa di intero positivo univoco per l'account; `simple.limit=20`, `simple.period=60`; quota **approssimativa per Cloudflare location**, non un tetto globale né protezione di richieste anonime che arrivano prima del codice. Namespace reale e disponibilità/costi del binding **NON confermati**.

## Gate necessari, nell'ordine
1. **GO/NO-GO costo + accessi**: prima dell'eventuale deploy verificare piano effettivo Workers, limiti disponibili e costi reali; individuare permesso Workers Scripts **Edit** limitato al Worker TEST, in sessione proprietario, senza usare mai Global API Key o condividere token in chat. Non creare token a pagamento né elevare permessi dei vecchi token D1/Analytics. Nessun automatismo deploy sul ramo DRAFT.
2. **Binding preparato fuori dal repository**: ottenere soltanto da Cloudflare il vero UUID D1 TEST, verificarne corrispondenza con il nome TEST, configurare `INGEST_RATE_LIMITER` con namespace univoco, e generare segreto webhook **separato** dal Worker Production. Non aggiungere a GitHub file con segreti, token in URL, UUID sensibili o output API integrali. L'esempio con placeholder non va caricato.
3. **Primo deploy richiede consenso ESPRESSO distinto**: nuovo Worker `remura-tv-webhook-test` con `INGEST_ENABLED=false`, nessuna route custom, binding a `remura-tv-lab-test`, MAI toccare `remura-tv-ingest-lab`. Non abilitare TradingView alert. Verificare via Cloudflare Dashboard versione, binding, limiter e l'endpoint `/health` **da un canale affidabile**: `accepting:false`. Una risposta 403 da GitHub verso `workers.dev` resta inconcludente, non ripetere uguale.
4. **Secondo consenso per invio LIVE**: solo dopo identità e limiti confermati, abilitare temporaneamente ingest sul Worker TEST e configurare alert nel Pine TradingView, assicurando token fuori dal codice (niente log/chats). Permettere 1–pochi eventi pilota da TradingView, mai esecuzioni di ordini. Accertare esito consegna alert, presenza `BAR_EVENT/HEARTBEAT` e `received_at_ms` in D1 TEST con query read-only, latenza, errori Workers/CPU e rispetto del budget. Se Cloudflare applica BIC o protezioni edge che bloccano TradingView, **STOP**; non allargare globalmente Access/WAF per aggirare.
5. **Rollback**: portare `INGEST_ENABLED=false` **sul solo Worker TEST**, confermare `/health.accepting=false` o accertare dalla Dashboard flag OFF + versione deployed; invii successivi devono tornare `503 disabled` e nuove scritture D1 TEST devono cessare. **Non** eliminare il record sintetico già presente o i nuovi eventi di prova senza autorizzazione separata. Se necessario, revocare **solo** segreto di TEST. Eliminazione del Worker TEST, se desiderata, è operazione separata. Non toccare il Worker Production.
6. **Evidenza prima della raccolta prospettica**: il solo successo di un POST non rende validi i proxy TradingView come esecuzioni CME e non produce segnali profittevoli. L'attivazione stabile e i collegamenti ai filoni B/C richiedono un checkpoint separato.

## Stati e sicurezza del rilascio
| Voce | Stato attuale |
| --- | --- |
| D1 TEST identità distinta | VERIFICATO con GET API |
| Sorgente/test di rollback | SOLO SIMULAZIONE OFFLINE |
| Manifest deployabile reale | NO — PLACEHOLDER |
| Rate limiter account | NON VERIFICATO |
| Secret per Worker TEST | NON CREATO |
| Permesso Worker EDIT/DEPLOY | NON DISPONIBILE IN QUESTA CHAT |
| Primo deploy e primo webhook live | NON AUTORIZZATI |
| Piano Workers Free | CONFERMATO con screenshot dashboard 13/11/2026 |
| Fatturazione aggregata account/CPU Worker TEST | NON VERIFICATE |
| Trading automatico | NON AUTORIZZATO |

**STOP GUARANTEE**: nessun GitHub Actions della PR #102 può effettuare deploy, variare `INGEST_ENABLED` su Cloudflare o spedire webhook con gli attuali script di questo filone.

### Fonti tecniche Cloudflare, consultate 13/11/2026
- [Workers Free limits](https://developers.cloudflare.com/workers/platform/limits/)
- [D1 Free limits](https://developers.cloudflare.com/d1/platform/limits/)
- [D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/)
- [Workers Rate Limiting binding](https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/)
- [Wrangler D1 bindings](https://developers.cloudflare.com/workers/wrangler/configuration/)
