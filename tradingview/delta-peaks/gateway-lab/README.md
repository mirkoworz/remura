# REMURA — GATEWAY ISOLATO Cloudflare Worker + D1 (audit LAB v0.8.4)
**Versione/aggiornamento: 0.8.4 — 11/11/2026, ore 18:05 CET**
**Codice gateway invariato v0.8.2, NO DEPLOY.**

## Bilancio Free aggiornato 11/11/2026 (simulazione, non quota account)
Il modello [quota_budget_v1.py](../quota_budget_v1.py) esegue un
controllo **offline** sul piano Free Cloudflare senza accedere ad account.
Le 7 prove sono in [test_quota_budget_v1.py](../test_quota_budget_v1.py).
Per un singolo `FXCM:EURUSD` M5, heartbeat di tutte le barre,
30 giorni, al massimo 20 KB/record, 10% ritentativi e 40% overhead,
il modello resta entro il **65% di 500 MB** per singolo DB e 10% delle
quote giornaliere. Con due simboli e 30 giorni **non** supera il limite
assoluto stimato soltanto, ma **supera il margine prudenziale**: usare
retention più corta (es. 14 giorni) oppure progetto/DB separato dopo
verifica del piano. Nessun risultato del modello conferma che l'account
dell'utente sia libero o che il CPU reale resti sotto 10ms.
Per eseguire senza deploy:

```sh
python3 tradingview/delta-peaks/quota_budget_v1.py --symbols 1 --retention-days 30
python3 tradingview/delta-peaks/quota_budget_v1.py --symbols 2 --retention-days 14
```

### Riutilizzo risorse REMURA
Nel repository `main` esistono già una configurazione **Firebase Web**
e una procedura Firestore riservata a Capital.com. Sono dedicate
a una funzione differente, con quote, regole e autorizzazioni da
verificare. **Non scrivere nella stessa raccolta e non toccare filone C**.
Cloudflare come gateway D1 indipendente evita di richiedere credenziali
Firebase amministrative al webhook e separa il rischio sperimentale;
un export eventuale verso l'interfaccia C richiederà coordinamento.



**Stato: SOLO CODICE E TEST OFFLINE. Non è stato creato un account, Worker, D1, endpoint pubblico o webhook. PR #102 DRAFT.**

## Quale problema risolve
Trasforma i messaggi `alert()` v0.8.1 in un registro append-only
con identificazione di ogni barra e di ogni livello, evitando doppie
registrazioni; **non** interpreta il segnale e **non** negozia.
L'archivio è totalmente separato da REMURA Filoni A/B/C.

Pipeline *potenziale, NON attivata*:

`TradingView alert JSON` → `HTTPS Worker con filtri` → `D1 LAB privato`
→ esportazione/analisi offline, solo dopo nuove autorizzazioni.

File: [worker.mjs](worker.mjs), [schema.sql](schema.sql),
[worker.test.mjs](worker.test.mjs). Nessun pacchetto npm richiesto.

## Perché Worker Free, non Oracle adesso
- Oracle Free Trial ha una scadenza prevista per il 15/11/2026 e segue
  un filone separato. Nessuna nuova dipendenza dalla VPS.
- Cloudflare Workers Free: **100.000 HTTP request/giorno per account** e
  **10ms CPU/request**; gli altri Worker dell'account condividono le quote.
- Cloudflare D1 Free: **5 milioni di righe lette/giorno**, **100.000
  righe scritte/giorno**, **5 GB account**, con limiti ulteriori per singolo
  database da verificare prima di crearlo. Se si supera una quota Free,
  le chiamate vengono bloccate. Non si passa automaticamente a un piano
  a pagamento senza un'azione di upgrade.
- A 1 heartbeat/M5 su un mercato continuo: fino a **288 eventi/giorno**
  per simbolo, più eventuali ritentativi (giorni di mercato FX spesso
  meno di 24 ore per sessione). 288 × 30 = 8.640 righe in 30 giorni
  per simbolo se consegnate tutte e nessun duplicato; ignora overhead DB.
- Richiede un account Cloudflare e un eventuale progetto D1 Free,
  **non ancora creati**. Verificare quota effettiva e utilizzo preesistente.

Fonti ufficiali:
- https://developers.cloudflare.com/workers/platform/limits/
- https://developers.cloudflare.com/workers/platform/pricing/
- https://developers.cloudflare.com/d1/platform/limits/
- https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/
- https://developers.cloudflare.com/fundamentals/reference/http-headers/

## Policy di ingresso implementata
1. In modalità predefinita `INGEST_ENABLED` assente/non `true`:
   risponde **503 disabled**, anche se un utente scopre l'URL.
2. Per funzionare occorrono binding D1 `TELEMETRY_DB` e
   `WEBHOOK_TOKEN_SHA256` (64 caratteri esadecimali SHA256 di un
   token casuale forte, segreto, non riutilizzato); nessuna chiave
   privilegiata nel codice, nel Pine o nel body JSON.
3. Solo metodo POST `/ingest/<token_segreto>` su HTTPS, dalle **quattro
   IPv4 TradingView pubblicate** (rilevate dall'header Cloudflare
   `CF-Connecting-IP` per ingresso edge diretto); confronto digest
   SHA256 senza interruzione anticipata. **Non è una firma crittografica
   per ogni messaggio**: chi conosce l'URL e arriva da IP ammesso può
   spacciarsi per la sorgente. Rivedere la sicurezza prima di attivare.
   Cloudflare documenta cautele per subrequest tra Workers/zone:
   vietare proxy non verificati verso questo endpoint.
4. `Content-Type: application/json`; body max **20.000 byte** letto
   in streaming; UTF-8 valido. Nessun log del token o del corpo JSON.
5. Schema di versione `remura.tv.flow.v1`, versione Pine `0.8.1-lab`,
   simbolo pilota `FXCM:EURUSD`, timeframe `5`, realtime e
   candela confermata, timestamp validi e campi numerici finiti.
   Footprint assente → tutti i relativi valori JSON null.
6. **Freschezza:** oltre 2 minuti dalla chiusura il record è salvato
   come `is_timely=0` ma **non** può far parte del campione prospettico.
   Messaggi dal futuro oltre 2 minuti o con oltre 24h di ritardo
   sono rifiutati.
7. Il DB conserva `raw_json`, ora ricezione e chiave unica
   `symbol|timeframe|bar_close_ms|version|event_type`. `INSERT OR IGNORE`
   rende idempotenti le ripetizioni. Risponde in JSON senza inviare nulla
   ai filoni B/C.
8. **Rate limit leggero:** max 20 eventi memorizzati negli ultimi 60s;
   è un limite best-effort, non una difesa definitiva contro burst/
   traffico abusivo. Da aggiungere protezione edge e allarmi quota
   prima di ogni attivazione.
9. Sulla quota gratuita: se D1 non risponde, restituisce 503 e non
   dichiara falsa acquisizione. Il webhook TradingView può comunque
   fallire. Controllare il log di consegna e i buchi nelle barre.

### Sicurezza del token URL
TradingView non fornisce un campo documentato per impostare header
di autenticazione personalizzati negli alert Pine `alert()`: in questo
prototipo il token è un segmento dell'URL da configurare nell'interfaccia
privata TradingView **solo dopo autorizzazione**. Gli URL possono
finire nei log dei servizi, perciò NON inserirli in screenshot,
issue, repository, chat, analytics o log. Ruotare subito il token
in caso di esposizione. L'IP allowlist riduce ma non annulla il rischio.

### Test automatizzati già previsti (offline)
Su un ambiente con Node 22:
```sh
node --test tradingview/delta-peaks/gateway-lab/worker.test.mjs
node --check tradingview/delta-peaks/gateway-lab/worker.mjs
```
Il workflow GitHub Actions `remura-tv-telemetry-lab.yml` li esegue
insieme ai 16 test Python sintetici e non avvia alcuna distribuzione.
I dati fittizi nei test non sono prove di redditività.

## Schema dati e retention (progettazione)
Il file `schema.sql` definisce la tabella `tv_flow_events`, con
`event_key` unico, timestamp e contenuto originale JSON. Nessuna
tabella o migrazione viene creata dall'esecuzione dei test.
Proposta: conservazione 30 giorni per il primo pilota, estendibile
solo dopo verifica dello spazio e di una strategia di esportazione;
**non attivare cleanup senza prima stabilire test di backup e restore**.

## Procedura futura che richiede consenso esplicito (NON eseguire ora)
1. Verificare piano Cloudflare realmente Free, consumo Workers/D1 e 2FA
   TradingView. Verificare gli IP aggiornati dalla documentazione ufficiale.
2. Creare spazio Cloudflare isolato e database D1 dedicato LAB,
   configurare `TELEMETRY_DB` e applicare `schema.sql` **solo a questo DB**.
3. Generare un token URL crittograficamente casuale forte in locale,
   salvare **solo l'hash SHA256** tramite secret Worker, non GitHub.
   Impostare esplicitamente `INGEST_ENABLED=true` soltanto per un test
   approvato, con protections/rate limit edge.
4. Provare l'endpoint con un payload sintetico e osservare 200,
   duplicati, rifiuti e quote. Testare recupero con DB non disponibile.
5. Impostare soltanto allora il webhook nel pannello TradingView,
   per una finestra di prova controllata. Per avere tutte le barre
   necessarie ai benchmark/futuri 15/30/60 min servirà abilitare
   heartbeat in `v0.8.1` (OFF di default), ricreare l'alert dopo
   variazioni del codice, monitorare latenza e fallimenti.
6. Solo in uno step successivo preparare export e analisi offline
   per il Filone B e UI C. Nessun ordine automatico autorizzato.

**Avvertenza:** ricevere ordini e volumi classificati nel feed FXCM NON
equivale a registrare operazioni di banche/CME. Risultati non validati.
