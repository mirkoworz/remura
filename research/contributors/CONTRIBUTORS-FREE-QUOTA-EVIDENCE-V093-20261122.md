# REMURA Contributors v0.93 LAB — Free quota proof gate
**22 novembre 2026 — Europe/Rome. Nessuna modifica Cloudflare.**

## Nuova funzionalità
- Branch: `research/contributors-free-evidence-gate-v093-20261122`
  derivato da Contributors v0.92 LAB, senza alterare PR #105.
- `research/contributors/contributors_free_proof_gate_v093_lab.py`
  legge SOLO uno schema di stati testuali già sanificati, non i log
  completi o le credenziali, e restituisce motivi di blocco specifici.
  Non accetta chiavi sconosciute, righe arbitrarie o campi segreti.
- Nuovi **16 test** dedicati, run
  [45022970415](https://github.com/mirkoworz/remura/actions/runs/45022970415),
  esito **SUCCESS**, log verificato:
  `REMURA_CONTRIBUTORS_FREE_V093=16_16_PASS`.
  Non ripetuti 22/22 hardcap, 18/18 routing, 12/12 revoca né
  test storici Workers/Access.

## Diagnosi esistente, SOLO fonte GitHub Actions
La run già eseguita il 21 novembre
[44919682812](https://github.com/mirkoworz/remura/actions/runs/44919682812)
riporta:
- `REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA`.
- `REMURA_CF_WORKERS_USAGE=OK`.
- `REMURA_D1_TEST_STORAGE=OK`.
- `REMURA_D1_ACCOUNT_STORAGE=OK`.
- `REMURA_DAILY_BUDGET=INCOMPLETE_OR_CRITICAL`.

Il motivo non prova uno sforamento ma **impedisce di garantire headroom
Free globale**. Un log storico OK non attesta il piano attivo, posti
Access ancora liberi o quote GitHub Actions residue. La run del 21
novembre non è una misura in tempo reale del 22 novembre.

Il nuovo gate restituisce `NO_GO_REAL_CONTRIBUTOR_PILOT` e liste di
blocker; esegue *zero* richieste Cloudflare e non consente onboarding,
deploy né acquisti. Perfino una fixture tutta OK rimane NO-GO perché
flag forniti localmente non sono certificazioni dell'account provider.
La revisione Manuale G0–G5 rimane obbligatoria.

## Next actionable step — richiede separata autorizzazione
Con uno specifico consenso futuro, consultare soltanto le quote reali
minime attraverso gli strumenti provider già disponibili e verificare
costo/budget prima di qualsiasi richiesta, senza duplicare le sonde del
monitor giornaliero. Stabilire Access seats effettivamente occupati
(con OWNER e altre eventuali utenze), spazio/righe D1, Workers e
minuti GitHub Actions; poi testare login/logout/revoca da Safari iPhone
fisico in staging privato, senza toccare Oracle.

**Esito:** v0.93 16/16 GREEN in LAB, pilot amici ancora NO-GO.
