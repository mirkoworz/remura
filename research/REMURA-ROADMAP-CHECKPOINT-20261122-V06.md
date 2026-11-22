# REMURA — checkpoint V06, 22 novembre 2026 (Europe/Rome)
**Solo LAB, nessun nuovo servizio o costo autorizzato.**

Questo è il sesto checkpoint incrementale del 22 novembre. Quelli precedenti
rimangono nelle rispettive branch di ricerca, ultimo V05:
`research/tv-no-signal-without-proof-v0188-20261122/research/REMURA-ROADMAP-CHECKPOINT-20261122-V05.md`.

## Lavoro realmente completato in questa prosecuzione
| Area | Risultato nuovo (non test storici) | Esecuzione CI |
| --- | --- | --- |
| D — Retail Myfxbook | 3 intervalli tra avvio Actions e avvio Pages collegati a 3 commit Git reali e relativi blob `latest.json`, con parent `head_sha` verificati; nessuna attestazione provider | [45022967620](https://github.com/mirkoworz/remura/actions/runs/45022967620), **16/16 PASS**, branch `research/retail-gh-actions-time-bracket-v05-20261122`, HEAD docs `b11ea67e23da05f4465ccd3f89d43d1e086b4b0b` |
| C — Contributors | Nuovo schema dati sanificati per valutare il rapporto budget esistente, proibire fake-green e rendere esplicita quota D1 GraphQL UNKNOWN, piano e seats da verificare | [45022970415](https://github.com/mirkoworz/remura/actions/runs/45022970415), **16/16 PASS**, branch `research/contributors-free-evidence-gate-v093-20261122`, HEAD docs `2aac149c635a169655c87a6b579e53cf6786cb0a` |

I log CI dei due job mostrano `Ran 16 tests`, `OK` e marcatori
`REMURA_RETAIL_GH_TIME_BRACKET_V05=16_16_PASS` e
`REMURA_CONTRIBUTORS_FREE_V093=16_16_PASS`. Sono **32 test nuovi**;
non sono state rieseguite le suite precedenti.

## Elementi scientifici ormai ben distinti
1. Il clock UTC nello snapshot è impostato dal collector dopo fetch API;
   il `committer` Git può essere impostato dal processo. Non è una ricevuta
   indipendente, nemmeno se gli orari coincidono.
2. Il provider GitHub registra separatamente i run collector e Pages.
   I precedenti tre eventi hanno bracket di **7, 10 e 15 secondi**
   *dai metadati server riferiti e congelati offline*, NON certificati
   crittograficamente nel fixture e non attestazione first-seen Myfxbook.
   Nei tre casi Pages ha iniziato prima della conclusione riportata
   della run collector: `Pages started` NON significa `content public`.
3. Nessun campione di questa ricerca è promosso ad ammissione scientifica
   delle decisioni TradingView. Il protocollo V2 resta intatto; la prima
   finestra holdout si apre **23/11/2026 ore 00:00 UTC (01:00 CET)**,
   senza implicare acquisizioni reali, CVD o edge dimostrati.
4. Myfxbook è retail; CFTC (TFF/disaggregated) è futures per categorie;
   il collegamento spot/futures e il timing delle revisioni richiedono
   controllo indipendente prima di poter calcolare qualcosa di predittivo.
5. COT versioning v0.1/v0.2/v0.3/v0.4 in LAB: append-only atomico,
   WAL reopen, global integrity; ancora NO-GO sul collector Oracle reale.

## Free budget — evidenza reale e blocchi
- Monitor di budget `.github/workflows/remura-cloudflare-budget-daily.yml`
  **già attivo/esistente**, non duplicato.
- Log GitHub Actions [44919682812](https://github.com/mirkoworz/remura/actions/runs/44919682812)
  21 novembre: Workers OK, D1 TEST storage OK, D1 account storage OK,
  **D1 account quota UNKNOWN_NO_GRAPHQL_DATA**, risultato globale incompleto.
- Non significa consumo oltre limite. Non consente però di verificare
  margine gratuito per pilot; Cloudflare Access seats, piano e GitHub Actions
  Free corrente rimangono da verificare.
- In questa prosecuzione ZERO chiamate Cloudflare, nessun Secret letto,
  né modifica monitor, Worker, D1 o Access. Il nuovo v0.93
  restituisce sempre `NO_GO_REAL_CONTRIBUTOR_PILOT` su evidenza non attestata,
  anche se vengono presentate fixture artificialmente tutte OK.

## Altri filoni preservati
- Contributors PR #105 v0.92 DRAFT non merge; permessi personali con ownership
  server-side, revoca, prova Safari iPhone e onboarding 1–2 amici solo
  dopo consenso e headroom reale.
- TradingView PR #106 v0.8.186 DRAFT non merge, successivo v0.8.187 e v0.8.188
  su LAB separati, emissione segnali inibita senza dati autentici.
- Mac Codex: custodia Oracle v1.65 non installata, Experience v0.30
  cinematica toro/orso 3D e SMF, Private Capture v0.15 e anti-rollback
  riservati al Mac; non toccati.
- Ampere Radar Oracle Milano + Telegram già operante; non riattivare.
- Squalincome e integrazione Telegram Contributors sono roadmap, nessuna
  attivazione o promessa di rendimento.
- L'ultimo `main` verificato in questa fase era
  `bd19918f457809f0568aee5c674b1b36a254971e` (solo aggiornamento
  automatico Myfxbook). Nessun merge dei branch LAB. Controllare SHA solo
  quando nuove modifiche reali lo richiedono.

## Prossimi gate, senza costi
A. **Primo passo:** predisporre, senza attivarla, la struttura per archiviare
   attestazioni reali di terzi (GitHub run API e timestamp server, provider,
   indipendente first-seen quando disponibile) e la disponibilità al
   momento di *ogni* decisione.
B. **Contributors:** ottenere con consenso separato una lettura reale e
   completa delle quote, compresi Access seats e consumo D1, solo dopo
   verifica preventiva di costi e richieste consentite; poi pilot fisico
   su iPhone, 1–2 amici, senza write ad altre sezioni.
C. **COT/Oracle:** coordinare Mac, backup, cutover additivo solo su consenso,
   garantire preservazione/versioning delle revisioni senza lookahead.
D. **TradingView:** valutazione prospettica dei soli campioni realmente
   ricevuti, cover M5 e FIFO, primary 60min vs price-only con V2 congelato.
E. **UI vera:** qualsiasi aggiornamento deve riportare in alto in **ogni**
   pagina numero versione e data/ora Europe/Rome; nessuna pagina toccata ora.

**Decisione generale: LAB GREEN, real-world alpha e pilot Contributors
ancora NO-GO. Produzione e Mac preservati.**
