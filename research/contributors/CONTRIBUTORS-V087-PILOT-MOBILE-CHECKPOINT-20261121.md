# REMURA Contributors v0.87 LAB — PILOT MOBILE PREVIEW / CHECKPOINT

**Checkpoint: 21 novembre 2026, ore 18:29 CET (Europe/Rome)**

## Stato GitHub concretamente verificato
- Repository pubblico: `mirkoworz/remura`.
- Branch nuovo e isolato: `research/contributors-pilot-mobile-v087-20261121`, base v0.86 LAB `514eec786efa2b1ae2a3473ed0d0774104a9cae4`.
- Commit effettivamente testato: `a8a4d5a6a7ef0360fa90cb50345de15b26bdf2ce`.
- Workflow nuovo one-shot: `.github/workflows/remura-contributors-v087-one-shot-ci.yml`, run https://github.com/mirkoworz/remura/actions/runs/44930226185 — **SUCCESS** verificato direttamente nei job log: `Ran 22 tests`, `OK`, `REMURA_V087_IPHONE_PREVIEW=22_22_PASS`.
- 22/22 **test nuovi** PASS; **primo tentativo** SHA `47d62206d033c97644f5727e7443dbd6cd9a4664`, run 44930191814, **FAILED** per una verifica testuale troppo rigida `soltanto i propri livelli` rispetto alla dicitura realmente esposta `esclusivamente i propri livelli`. Corretto il solo test testuale, lasciando l'interfaccia intatta, e verificata la nuova esecuzione verde. Nessuna suite storica ripetuta.

## Valore concreto per iPhone
- `research/contributors/contributors_pilot_preview_v087_lab.html`: nuovo mockup **visuale autonomo HTML** per un iPhone, dark ocean/teal, logo pinna REMURA, cards responsive, sezione CONTRIBUTOR e OWNER, sezioni pieghevoli FAQ e percorso futuro di attivazione. Versione e data/ora visibili **in altissimo**, come richiesto.
- Scritto in italiano, senza JavaScript, form, input, chiamate API, accesso a Cloudflare/Oracle, cookie, localStorage, CDN, fetch, link a servizi esterni o risorse che producano costi.
- CONTRIBUTOR: visualizza REMURA, propone **solo propri livelli**, conserva ricevute personali e invia amendment separati. Niente scrittura su contributi altrui e niente approvazione, che richiede OWNER.
- OWNER: coda original-level, coda amendment, review manuale, audit persistente e stati RESERVED non sbloccabili automaticamente.
- I messaggi spiegano cosa resta **NO-GO**: D1 rows read/write quotidiane UNKNOWN, Cloudflare Access Free seats UNKNOWN, nessun collaudo Safari fisico di login/logout/revoca, nessun staging. I controlli visuali non impongono autorizzazioni: quelle richiederanno token Access verificato e ruolo D1 server-side.
- `test_contributors_pilot_preview_v087_lab.py`: 22 test nuovi su banner, ruoli, responsive, no network / JS / forms, CSP e FAQ. Niente credenziali; workflow GitHub read-only.
- `CONTRIBUTORS-V087-PILOT-MOBILE-RUNBOOK-20261121.md`: obiettivi e step futuri.
- **Importante**: anteprima offline NON integrata nel router v0.78 e NON pubblicata su Cloudflare. La base di 14 file private pinned, le quattro pagine v0.78 e i diritti esistenti NON sono stati modificati. Nessun merge `main`.

## Cloudflare Free — decisione scientificamente corretta
- Dal controllo del codice del workflow corrente `.github/workflows/remura-cloudflare-budget-daily.yml` risulta che è già attivo un monitor schedulato isolato sul commit storico `08ee9d8f5ba0b4655f4b0b84245afc7cb7a360c8`.
- Monitor 21 novembre run https://github.com/mirkoworz/remura/actions/runs/44919682812: `REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA`, `REAL_ACCOUNT_DAILY_USAGE=NOT_MEASURED`, conclusione FAIL. Nessun dato di rows read/written quotidiane attendibile; non usare zero e non inferire margine Free. Posti Access ancora UNKNOWN.
- Documentazione ufficiale Cloudflare aggiornata 06/11/2026 https://developers.cloudflare.com/d1/observability/metrics-analytics/ : `d1AnalyticsAdaptiveGroups` registra dati solo se la richiesta raggiunge l'esecuzione SQL; l'assenza di gruppi NON certifica il consumo zero né l'assenza di problemi. La query esistente è coerente sintatticamente con gli esempi ufficiali; non fare correzioni arbitrarie o cambiare il monitor real senza autorizzazione.
- Il piano di diagnosi v0.86 già pronto è SOLO OFFLINE e prevede, dopo autorizzazione separata, un massimo di due richieste read-only giorno UTC corrente e precedente, senza retry né output identificativo. Non eseguito in questa sessione.
- Nessuna nuova spesa o nuovo servizio provider. Il report v0.80 resta storico, Workers ~199 richieste stimate, D1 4 DB e storage aggregato ~6,56MB provengono da osservazioni precedenti non da questo codice.

## Roadmap completa e priorità
1. **Contributors**: usare questa vista UI per accettare la struttura del pilot. Priorità tecnica reale: prova Access seats/Free plan e daily D1 read/write da provider **solo dopo consenso specifico**, staging/fixture D1 separato, deny-default, verifica server JWT/ruoli, Safari iPhone login/logout/revoca, rollback. Pilot 1–2 utenti, SOLO propri livelli e consultazione del resto, OWNER approva/audita. Originali e correzioni distinti, RESERVED senza auto retry/unlock, Telegram soltanto post approvazione e autorizzazione.
2. **TradingView**: ultimo v0.8.186 LAB branch `research/tradingview-anchor-request-v0186-20261121` HEAD `c1a35edfeb914fc5f24564b5ca2f11994bc9ee0d`, 16/16 test verdi. Protocollo prospettico V2 frozen, sviluppo 16–22/11, holdout 1 23–29/11 UTC, holdout 2 30/11–06/12 UTC. Nessuna cattura attiva, anchor indipendente non verificato, nessun edge istituzionale dimostrato. Non rivalutare risultati prima della fine fold.
3. **Shark Science**: v0.4 LAB branch `research/track-b-shark-science-20261104` SHA `05e731b26bccb167ba7e0859797de01136a5c933`. Sono già presenti moduli complessi per COT as-of, Myfxbook first-seen, CVD-ness, legami causali con Squalincome. Evitare di duplicare nuove sonde sintetiche equivalenti; dati reali e identità decisione/capture trust rimangono il vero collo di bottiglia.
4. **Experience** v0.30 LAB, splash toro/orso 3D, scontro/esplosione, REMURA pinna, logo/ringraziamenti SMF e foto da rimuovere, verifica Safari reale in futuro.
5. **Private Capture** v0.15 LAB sintetico NON attivo; collector Oracle in funzione, autoupdater bloccato, release v1.65 firmata root-owned staged NON installare/toccare. Ampere Radar v0.36 per capienza Oracle Milano e Telegram operativo. Backup reale, Squalincome, future notifiche livelli approvati in roadmap.
6. Controllare periodicamente l'uso Free, senza promettere zero; nessun Mac richiesto per GitHub LAB e non rifare test già verdi. Per chat lunga passaggio completo SHA, branch, run CI e roadmap.

**Stato finale: UI anteprima v0.87 LAB realizzata, 22/22 test PASS, nessun deploy/merge/Cloudflare live/Oracle/utente reale/costo; staging NO-GO.**
