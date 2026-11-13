# REMURA — Bootstrap Worker TEST & accesso minimo v0.8.25
**Aggiornato: 13/11/2026, ore 16:32 CET**  
**SOLO PIANO: NESSUNA CREAZIONE, DEPLOY, WEBHOOK, NUOVO TOKEN O MODIFICA CLOUDFLARE AUTORIZZATI.**

## Nuova scoperta sui ruoli Cloudflare (verifica documentale 13/11/2026)
- Cloudflare Workers adotta ruoli granulari **Metadata Read-Only**, **Content Read-Only**, **Editor** e **Admin**; i ruoli possono essere assegnati a **un singolo Worker esistente** oppure a tutti i Workers.
- **Un Worker inesistente non può essere selezionato come risorsa di un token per-Worker**. Per creare un Worker nuovo con API/Wrangler è necessario **Workers product-level Admin**, con potere potenzialmente anche sugli altri Worker dell'account. Per aggiornare/deployare un Worker **già esistente** basta **Editor soltanto su quel Worker**. Per i binding D1, deploy Editor del Worker non richiede accesso diretto in scrittura a D1.
- Soluzione di minimo privilegio preferita: l'**utente proprietario**, una sola volta e **solo dopo consenso esplicito**, crea mediante dashboard il Worker `remura-tv-webhook-test`; successivamente un eventuale token CI viene limitato **Editor al solo `remura-tv-webhook-test` già esistente**. **MAI** assegnare Editor/Admin a `remura-tv-ingest-lab`, né al prodotto Workers intero per automatizzare semplicemente il TEST.
- Nessun token nuovo serve adesso. Se la UI non permette di assegnare il ruolo singolo desiderato o crea un nuovo Worker non verificabile, **STOP** senza allargare gli scope.
- Fonte: https://developers.cloudflare.com/workers/authorization/workers/ (Workers roles and permissions, updated Sep 15 2026); https://developers.cloudflare.com/changelog/post/2026-09-21-invite-members-to-workers/ .

## Codice bootstrap totalmente inerte, nuovo rispetto al gateway
- `gateway-lab/bootstrap_test_worker.mjs` **v0.8.25** NON è `worker.mjs` v0.8.6. È un codice indipendente con solo `GET /health` JSON `{"status":"bootstrap_only","accepting":false}`, altri metodi/route: **HTTP 503 disabled**. Non usa variabili, Secrets, D1, limiter, client HTTP esterni, token, code di trading o webhook.
- Test Node `gateway-lab/bootstrap_test_worker.test.mjs` (solo offline) verificano: anche con `INGEST_ENABLED=true` passato a runtime, chiamate POST o /ingest/token mai accettate, nessuna lettura env, nessuna scrittura DB, nessuna eco di token/body e risposte no-store/nosniff.
- **Questo bootstrap è progettato per stare isolato e spento**. Non è il receiver TradingView. `worker.mjs` completo andrà distribuito eventualmente **in una seconda fase**, con tutte le protezioni precedentemente validate.
- **Verifica reale di toolchain, ma NON di Cloudflare runtime:** [GitHub Actions #43453466241](https://github.com/mirkoworz/remura/actions/runs/43453466241) SUCCESS — 6 test Node e `wrangler@4.157.0 deploy --dry-run` sul solo bootstrap con configurazione temporanea `workers_dev:false` e senza alcun binding, namespace, account ID o credential. Nessun deploy e nessun Worker creato.
- Il bootstrap non contiene binding, D1 UUID, credenziali, namespace rate limiter. Per il futuro passaggio al gateway reale resta indispensabile il preflight: D1 TEST `TELEMETRY_DB → remura-tv-lab-test`, limiter `INGEST_RATE_LIMITER`, Secret separato, `INGEST_ENABLED=false`.

## Procedura owner-only (NON ESEGUIRE SENZA NUOVO CONSENSO)
1. Dalla dashboard Cloudflare nel piano Workers Free già confermato, creare un **Worker nuovo** dal nome **esatto** `remura-tv-webhook-test`, senza collegarlo al DB principale e senza creare route personalizzate. Il contenuto da deployare *inizialmente* è quello di `bootstrap_test_worker.mjs` (oppure, se il prodotto forza un template iniziale, verificare che nessun webhook venga esposto e sostituire subito con bootstrap inerte; in caso di dubbi STOP).
2. Confermare dalla Dashboard che si tratti **esclusivamente** del Worker `remura-tv-webhook-test`, e che **NON** compaia alcun `TELEMETRY_DB` collegato al database principale; nessun Secret del Production deve essere copiato.
3. Valutare **disattivazione della route pubblica workers.dev** durante il bootstrap, se supportata dalla UI senza cambiare altri Worker; non dare per scontato che 503 blocchi il consumo delle richieste Workers: ogni richiesta al codice può comunque consumare la quota Free account-wide.
4. Solo dopo creazione verificata, potrà essere proposto un token con ruolo **Workers: Editor** assegnato **solo** al nuovo Worker esistente, conservato in GitHub Secret dedicato e **mai trasmesso in chat**. Verificare con interfaccia Cloudflare l'effettiva restrizione, non presumere che il nome del token ne limiti lo scope.
5. Con nuovo consenso distinto, futuro deploy di `worker.mjs` con flag ingest OFF, D1 solo TEST, rate limiter e Secret Test differente; nessun webhook prima di verificare output health ed eventuale blocco edge.
6. Terzo momento, con consenso ulteriore e costi/quote verificati: singolo alert TradingView verso TEST; al termine kill-switch OFF e audit read-only D1 TEST. Preservare record sintetico esistente e non toccare Production.

## Stato oggettivo
| Elemento | Stato |
| --- | --- |
| Piano Workers Free $0 | VERIFICATO screenshot proprietario |
| D1 TEST distinto dal MAIN | VERIFICATO GET API read-only |
| Gateway v0.8.6 + mock end-to-end | TEST OFFLINE |
| Bootstrap inerte v0.8.25 | TEST OFFLINE CI; **non distribuito** |
| Editor per-Worker disponibile nella documentazione | CONFERMATO DOCUMENTALMENTE |
| Worker `remura-tv-webhook-test` esistente su Cloudflare | **NON CREATO/DA CONFERMARE** |
| Token Editor limitato a questo Worker | **NON CREATO** |
| Binding rate limiter realmente disponibile/account Free | NON VERIFICATO |
| CPU, fatture Cloudflare aggregate e quota CPU per POST | NON VERIFICATE |
| Worker Production `remura-tv-ingest-lab` | INVARIATO, D1 MAIN |
| PR #102 | OPEN / DRAFT; NO MERGE |
| Deploy/alert/order | NO |

**Non richiedere di ripetere prove già concluse. Non autorizzare alcun token product-level Admin per il semplice deploy TEST.**
