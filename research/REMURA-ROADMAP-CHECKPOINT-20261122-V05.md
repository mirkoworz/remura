# REMURA — roadmap operativa V05, 22 novembre 2026 (Europe/Rome)
**NO nuovi deploy, merge, Secret, utenti, chiamate Oracle/Cloudflare o spese.**
Precedenti checkpoint: `research/REMURA-ROADMAP-CHECKPOINT-20261122-V04.md`
sul branch COT LAB v0.4, oltre ai checkpoint V03/V02 già salvati.
Questo documento integra senza riscrivere la storia.

## Situazione aggiornata
**Produzione:** il `main` è avanzato di **un commit automatico Myfxbook**
dal vecchio `7c70bb9fd0e774d45c493217382c430b448af0e2` a
`bd19918f457809f0568aee5c674b1b36a254971e` (commit UTC
`2026-11-22T08:50:44Z`). GitHub Pages per quest'ultimo commit ha una
esecuzione già esistente `45004698324`, `created_at 08:50:46 UTC`,
success. **Questo non è un merge LAB**. Rilevazione read-only tramite GitHub.

| Filone | Stato aggiornato / prova | Prossimo gate reale |
| --- | --- | --- |
| A — COT Shark Science | v0.1 20/20, v0.2 16/16, v0.3 WAL 15/15, v0.4 global integrity 12/12 (tutti LAB) | Mac: migrazione additiva/backup/rollback/first-seen, **NO-GO Oracle** |
| B — TradingView | Nuovo v0.8.188 offline **18/18 GREEN**, [Actions 45018607314](https://github.com/mirkoworz/remura/actions/runs/45018607314), branch `research/tv-no-signal-without-proof-v0188-20261122`, docs HEAD `8b2880e4b2c4c4e69a7c66f404f301a10a6ec783` | Prove CVD autentiche con timestamp indipendente, comparatori price-only, copertura M5 e no lookahead |
| C — Contributors | v0.92 DRAFT PR #105, Access+ownership lab precedenti OK, pilot reale **NO-GO** | Quote reali Workers/D1/Access + prova Safari fisica e consenso |
| D — Retail | Nuovo **GitHub Pages event association 12/12 GREEN**, [Actions 45018604348](https://github.com/mirkoworz/remura/actions/runs/45018604348), branch `research/retail-gh-pages-receipt-v04-20261122`, docs HEAD `b03856c9d96f85449e85a9ff563faa78079c5462` | Separare orologio del collector, Git commit, evento server GitHub e first-seen provider |
| E — Codex Mac | Custodia Oracle v1.65 predisposta non installata; Experience v0.30 e Private Capture v0.15 filoni Mac | Nessuna sovrapposizione da iPhone |
| F — Ampere Radar | Monitor Oracle Milano + Telegram già operativo in altro repository | Non ripetere attivazioni; verifiche solo se un nuovo evento |
| G — Free budget | Esiste già il monitor giornaliero Cloudflare read-only su `main` | Riparare l'incompletezza di dati soltanto dopo analisi e autorizzazione; **niente doppio monitor** |

## Prova server GitHub già disponibile (non equivale a timestamp di mercato)
Run Pages associati a commit Myfxbook reali:
- Commit `32188ca...`: snapshot EURUSD 20 Nov `11:18:32Z`;
  Pages run `44726531678` creato dal server GitHub a `11:18:34Z`.
- Commit `7c70bb9...`: snapshot EURUSD 22 Nov `01:36:15Z`;
  Pages run `44972231080` creato a `01:36:18Z`.
- Nuovo main `bd19918...`: commit metadata `08:50:44Z`;
  Pages run `45004698324` creato a `08:50:46Z`.
- Il comparatore offline v0.4 pinna i **primi due** esempi a commit/blob
  e confronta i metadati Actions letti separatamente da GitHub. Il terzo
  è una verifica separata di versione main, non incluso nella fixture.
- L'orario Pages `created_at` è **riportato dal server GitHub**,
  che è una piattaforma distinta dal collector. Non è un timestamp notarizzato
  o una prova che Myfxbook pubblicò i valori o che un trader li vide
  all'ora della decisione. Il modulo offline non autentica nuovamente
  la risposta REST: `EXTERNAL_PLATFORM_RUN_ASSOCIATION_UNATTESTED_OFFLINE`.
- `scripts/update_myfxbook.py` campiona l'ora locale UTC dopo API fetch;
  l'ora `committer` Git è modificabile dal processo che crea il commit.
  Non promuovere queste date in `EXTERNALLY_TIME_ATTESTED`.

## Nuovo firewall TradingView (niente falsa sicurezza)
`tradingview/delta-peaks/scientific_admission_firewall_v0188_lab.py`
usa calendario V2 immutabile e per ogni decisione controlla il collegamento
con l'evento M5, close/receipt non successivi alla decisione, provenienza retail
e COT, mapping spot/futures, e denominator corretto delle barre di mercato.
Dati reali non attestati -> `ABSTAIN_NO_PROSPECTIVE_SCIENTIFIC_ADMISSION`.
Una stringa witness, una firma/hash locale e claim di copertura non provano
l'indipendenza dell'ora o un edge. Il guard non calcola PnL né produce
segnali; V2 congelato da 16/11 fino al 07/12, H1 apre il 23/11 00UTC.

## Audit già esistente Cloudflare Free: attenzione
Lettura **solo di GitHub Actions preesistenti**, senza nuove chiamate CF.
- Workflow `.github/workflows/remura-cloudflare-budget-daily.yml` esiste
  già su `main`; non duplicare o avviare.
- Run del **21 novembre 2026**: [44919682812](https://github.com/mirkoworz/remura/actions/runs/44919682812)
  **FAILURE**; log riporta
  `REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA`,
  `REMURA_CF_WORKERS_USAGE=OK`,
  `REMURA_D1_TEST_STORAGE=OK`,
  `REMURA_D1_ACCOUNT_STORAGE=OK`,
  `REMURA_DAILY_BUDGET=INCOMPLETE_OR_CRITICAL`.
- **Interpretazione:** un solo sub-controllo UNKNOWN rende incompleto il
  check aggregato: NON è dimostrato uno sforamento Free. Le tre sezioni
  OK riguardano il momento del log; non autorizzano un pilot, non sono
  dati precisi di fatturazione e non attestano consumo aggiornato al 22.
  Non ripetere la diagnosi GraphQL del 21 senza nuova autorizzazione.

## Limiti e prossime mosse
1. Progettare un ricevitore witness **prospettico e indipendente**, con
   identità run/commit/file, tempo di osservazione del server e attestazione
   effettiva della risposta di terzi. Solo preparazione in LAB: la spesa,
   nuovi workflow, la schedulazione e l'uso di Secret richiedono consenso.
2. Per ogni decisione V2, ammettere solo prove CVD reali ed esplicitamente
   attestabili, con missingness misurata. Una finestra calendario iniziata
   non certifica la presenza dei campioni.
3. Coordinare COT v0.4 con Codex Mac prima di qualunque migrazione;
   nessuna alterazione dei dati Oracle legacy.
4. Contributors resta NO-GO in assenza di quota Free **completa** e test
   Safari reale login/logout/revoca + accesso per ruolo.
5. L'eventuale UI REMURA aggiornata deve esporre sempre numero versione
   e data/ora Europe/Rome in cima a ogni pagina; nessuna UI modificata ora.
6. Non riavviare suite già concluse, salvo nuova modifica ai file rilevanti
   o difetto dimostrato. **30 test nuovi** eseguiti in questa prosecuzione.

**Conclusione: nuovi LAB GREEN, qualità della provenienza migliorata,
produzione invariata, capacità di anticipare gli istituzionali NON dimostrata.**
