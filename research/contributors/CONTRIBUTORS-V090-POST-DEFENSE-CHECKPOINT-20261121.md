# REMURA Contributors v0.90 LAB — CENTRAL POST DEFENSE CHECKPOINT

**21 novembre 2026 · checkpoint circa 19:33 CET (Europe/Rome).**
**Versione codice v0.90 LAB. Nessuna pagina UI è stata modificata; per ogni futura pagina mantenere banner versione/data/ora al vertice.**

## Repository e test reali, senza ripetizione di suite storiche

- Repository pubblico: `mirkoworz/remura`.
- Branch isolato: `research/contributors-post-defense-v090-20261121`.
- Base: Contributors v0.89 LAB, commit `bbf6af8b7ce417dfbc826367b4bee44a3d04a6cb`.
- Commit del codice nuovo: `d6a28b51f4be55806b0dec4c46c7456d68b321e8` (file wrapper/test/workflow).
- Commit **effettivamente testato verde**: `bf1141119bae43d7ba2b88e1f7c117d8c0c46ed1` (solo correzione fixture di test).
- GitHub Actions one-shot **SUCCESS**, run https://github.com/mirkoworz/remura/actions/runs/44936036342 . Log letto direttamente: `1..34`, `# tests 34`, `# pass 34`, `# fail 0`, `REMURA_CONTRIBUTORS_V090_POST_GUARD=34_34_PASS`.
- Due run precedenti, `44935922448` e `44936000362`, erano **FAILED**: nel test la funzione `req()` costruiva correttamente gli header ma passava l'oggetto vuoto `headers` invece di `h`. Il wrapper rifiutava correttamente le richieste senza Origin/CSRF; corretto **solo il test**, nessun allentamento della protezione.

## Miglioramento sostanziale

- Nuovo modulo `research/contributors/private_post_guard_v090_lab.mjs`: funzione `createPostGuardedPrivateWorkerV090` avvolge il router v0.78 **senza modificare il sorgente congelato**, né toccare i 14 asset sensibili.
- Per ogni POST, PRIMA di inoltrare ai gestori, richiede HTTPS stesso origin configurato, esatto URL canonico senza query, `Origin` esatto, `Sec-Fetch-Site=same-origin`, `X-Remura-CSRF=1`, JSON, nessun Content-Encoding compresso, assenza header ruolo/subject/actor falsificati, corpo valido JSON oggetto e dimensione massima di 4096 byte. `Request.clone()` consente una lettura limitata di verifica prima della gestione downstream.
- `authenticate(ctx,env)` e `profileRead(ctx,env,actor)` vengono chiamati lato server sul POST. L'identità del subject/email_tag deve essere un digest 64 hex; `CONTRIBUTOR` può usare la propria area soltanto con `can_read`, `can_write` per `submit`/`intent`. `OWNER` può accedere alle sue code e audit con `can_recover`. La richiesta stessa non può affermare il proprio ruolo.
- Le chiamate GET continuano a essere gestite esattamente dal router v0.78; nessun diverso percorso statico e nessuna concessione extra.
- Questi sono **controlli additivi**: non sostituiscono la verifica downstream di ownership D1, limiti rate, intent, journal OWNER, RESERVED, autenticità del JWT Access o protezione CSRF nel gestore. I test sono sintetici Node, non equivalgono a un test su Cloudflare. La compatibilità header `Sec-Fetch-Site` da Safari iPhone fisico è da verificare **prima** del deploy; se non supportato va progettata e testata una soluzione alternativa con garanzie equivalenti, senza aprire la porta a cross-site.
- Sorgente `test_private_post_guard_v090_lab.mjs`: 34 NUOVI casi, inclusi richieste valide, autorizzazioni incrociate, spoofing, origine, CSRF, JSON invalidi, oversized, prototype pollution, Content-Length incongruente e conservazione GET originari.
- Workflow `.github/workflows/remura-contributors-v090-one-shot-ci.yml`: branch/path isolati, checkout senza credenziali persistenti, nessun Secret/Cloudflare API, nessun deploy.

## Stato effettivo Cloudflare Free e accesso collaboratori

- Tra le ultime 100 GitHub Actions lette al 21/11/2026, il monitor account Free più recente risulta run **44919682812 FAILED** del 21/11. `REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA` e `REAL_ACCOUNT_DAILY_USAGE=NOT_MEASURED`: questo non è zero e non autorizza spese né staging.
- Monitor del 20/11 `44772218921` SUCCESS storico: non sostituisce la misurazione attuale D1 rows read/write. Workers ~199 richieste stimate, D1 4 DB e ~6.56MB osservati nel monitor precedente; non sono prove di consumo attuale/billing. Posti Cloudflare Access Free effettivi **UNKNOWN**.
- Disponibile utility locale iPhone v0.88 (no provider calls, 22/22), anteprima v0.87 e demo interattiva v0.89 (30/30). Nessuna delle tre è un collaudo di autenticazione reale. UI private v0.78 LAB con banner versioni, non distribuite.
- Pilot 1–2 collaboratori con visualizzazione REMURA e scrittura limitata ai **propri** livelli, OWNER approva, audit append-only, correzioni separate, RESERVED non auto-release/retry, Telegram post-approvazione **solo dopo** autorizzazione, Free gate e test Safari.

## Roadmap conservata e prossima decisione utile

1. **Non produrre un'altra successione di test sintetici per i medesimi controlli.** Chiedere esplicita autorizzazione per la misura Cloudflare **in sola lettura**, minime richieste con margine Free e non pubblicazione di token/account ID/PII; usare il piano v0.86 (massimo 2 GraphQL POST giorno corrente/precedente, no retry), controllare prima se il monitor giornaliero ha già ottenuto dati. Seats Access verificati in dashboard privata.
2. Solo quando consumi Free e disponibilità Access sono effettivamente noti: staging isolato autorizzato, deny-default, rate limit, login/logout/revoca Safari fisico, separazione ruoli con verifica dei veri backend e rollback, poi pilot controllato 1–2 utenti.
3. TradingView v0.8.186 LAB continua con protocollo V2 byte-pinned (Git blob `4b0f5d5defacfdbf8e902af5a8eea32947cabeca`), holdout1 `2026-11-23T00:00Z` — `2026-11-30T00:00Z` escluso, holdout2 `2026-11-30T00:00Z` — `2026-12-07T00:00Z` escluso. Dossier pre-holdout `research/tradingview-preholdout-decision-20261121`: nessuna nuova cattura autentica o anchor indipendente attestati nei commit controllati, niente retro-imputazione e nessun edge/PNL provato.
4. Shark Science v0.4 LAB COT, sentiment Myfxbook, delta/CVD proxy, ER, as-of; attendere crosswalk feed/contratto e prove temporali per confronti per singola decisione. Non duplicare moduli esistenti.
5. Experience v0.30 LAB splash toro/orso 3D collisione/esplosione, REMURA pinna/SMF e rimozione foto; test Safari in futuro.
6. Oracle collector operativo, autoupdater persistentemente fermo, v1.65 firmata root-owned staged **NON installare**. Ampere Radar v0.36 Milano/Telegram operativo. Private Capture v0.15 LAB solo sintetico. Backup, Squalincome e Telegram livelli approvati preservati.
7. Nessuna nuova spesa, nessun merge `main`, nessun deploy, nessun Mac richiesto per questa CI. Mantenere roadmap e passaggio di consegne in nuova chat quando la conversazione diventa pesante.

**Esito: v0.90 LAB 34/34 PASS sui controlli nuovi. Inviti reali e Cloudflare staging ancora NO-GO.**