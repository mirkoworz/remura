# REMURA Contributors v0.80 LAB — READINESS, D1 TRIAGE, ACCESS E SNAPSHOT IPHONE

**Checkpoint: 21 novembre 2026, ore 17:26 CET (Europe/Rome)**

## Risultato concreto e identificatori
- Repository GitHub: `mirkoworz/remura` (**pubblico**); branch isolato `research/contributors-readiness-v080-20261121`.
- Base confermata v0.79: `eaa6805b3db8fce29a736d0ab47211c925cda055`; `main` NON modificato.
- **60/60 nuovi test di readiness PASS**, GitHub Actions: https://github.com/mirkoworz/remura/actions/runs/44924395473 (SHA testato `c5144d5f4e6e14c437d16b1a45847e9eafff1dda`).
- **20/20 nuovi test statici pagina iPhone PASS**, GitHub Actions: https://github.com/mirkoworz/remura/actions/runs/44924515260 (SHA testato `143fd6143f6bc2a35c5f4d114fa6e28182ec031e`).
- Totale **80/80 nuovi test PASS** in due suite indipendenti, senza ripetere v0.79 (89/89), v0.78 (50/50), v0.77 (56/56), v0.76 (64/64), v0.75 (50/50), v0.74 (55/55), v0.70 (24/24).
- Nessuna chiamata Cloudflare, nuovo Secret, credenziale, deploy, modifica database, merge, modifica Oracle o nuova spesa.
- `v0.80` è solo **LAB readiness**; le quattro pagine reali candidate Contributors/OWNER restano **v0.78 LAB**, senza cambi di asset/router e con i banner v0.78 già in cima. La nuova pagina **v0.80 LAB** è un report statico separato.

## Nuovo codice v0.80
1. `research/contributors/readiness_dossier_v080_lab.py`: produce un dossier JSON di evidenza **offline e non attestata**. Controlla quattro log quota v0.79 (D1 righe oggi, Workers richieste oggi, D1 TEST storage, D1 account storage), provenienza di una run GitHub, snapshot manuale Access Free seats, GraphQL D1 oggi/ieri e lock byte esatto dei 14 sorgenti v0.78.
2. `triage(today,yesterday,day,inventory)`: valida un singolo account GraphQL, data UTC esatta, massimo 10 gruppi/DB, UUID in inventario, contatori interi finiti non negativi, nessun DB duplicato. Se i gruppi oggi sono vuoti, espone `TODAY_EMPTY_PRIOR_PRESENT` o `BOTH_DAYS_EMPTY` ma **NON inventa 0 righe** e non trasferisce ieri a oggi. La presenza di gruppi forniti come input sintetico NON prova fatturazione o attività reale.
3. `access_snapshot`: considera un'osservazione manuale Zero Trust Free solo se struttura completa, posti coerenti (1..50), giorno UTC corrente, non più vecchia di 4h e senza data futura >2 minuti. Anche se valida, lo stato è `MANUAL_ONLY`, **non provider-attested**. Il numero reale di seats Access oggi è UNKNOWN.
4. `monitor_provenance`: accetta solo un riferimento a una run GitHub `main` con ID numerico, timestamp UTC recente e conclusione nota; una run fallita è `INCOMPLETE`. Anche una run GitHub SUCCESS è solo metadato pubblico e NON attesta l'accuratezza dei dati Cloudflare.
5. `staging_source_lock_v079_lab.py` è riutilizzato (non modificato) per verificare **14/14 blob Git** della baseline v0.78; SHA-1 Git non è una firma di release o una prova di runtime Cloudflare.
6. Output sempre `decision: NO_GO`, `input_trust: OFFLINE_SUPPLIED_UNVERIFIED`, `real_cloudflare_quotas_attested: false`, `automatic_deploy_allowed: false`, `requires_explicit_staging_authorization: true`. **Nessun input offline può trasformarsi in autorizzazione reale**.
7. `test_readiness_dossier_v080_lab.py`: **60 nuovi test** (no retest storico) su errori, revoche/limiti Access, quote D1, GraphQL vuoto/duplicato/inventario falso, monitor fallito/scaduto, source lock drift, output senza identificativi e divieto deploy.
8. `contributors_readiness_v080_lab.html`: **nuova pagina iPhone statica**, con versione e data/ora **v0.80 LAB · 21/11/2026 17:24 CET** in cima, responsive, nessun JavaScript, nessuna API, nessun modulo, nessuna immagine remota, nessuna chiave. Mostra NO-GO e quattro metriche con le rispettive fonti/limiti. I valori sono esplicitamente **snapshot del 21/11, non live**.
9. `test_readiness_snapshot_v080_lab.py`: **20 nuovi test** su banner, data, responsività, assenza script/credenziali, Access/D1 unknown, link GitHub e assenza attivazioni.
10. Due GitHub Actions one-shot isolati: `.github/workflows/remura-contributors-v080-one-shot-ci.yml` e `.github/workflows/remura-contributors-v080-snapshot-one-shot-ci.yml`, `contents:read`, `persist-credentials:false`, nessun Cloudflare Secret e senza deploy.

## Semafori Cloudflare e Free (verificati fino al 21/11)
- Monitor account Cloudflare Free 21/11: https://github.com/mirkoworz/remura/actions/runs/44919682812 **FAIL / INCOMPLETE**, `REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA`; `REAL_ACCOUNT_DAILY_USAGE=NOT_MEASURED`.
- **D1 rows read/write giornaliere: UNKNOWN — NO_GO**. L'ultimo report verde del 20/11 NON vale per il 21/11.
- Workers: 199 richieste **stimate**, 0 errori stimati (non estratto fatturazione).
- D1 account: 4 database, 6.557.696 byte totali; D1 TEST: 6.266.880 byte. Questi sono metadati di storage, non righe D1 consumate.
- Access Free seats effettivi: **UNKNOWN — NO_GO**; non abbiamo consultato l'account.
- Cloudflare Free limiti nominali: 10 DB, 5 GB totali, 500 MB per DB, 100.000 Workers requests/day, 5M D1 rows read/day, 100K D1 rows write/day. Verificare sempre documentazione ufficiale prima dell'attivazione: https://developers.cloudflare.com/d1/platform/limits/ ; https://developers.cloudflare.com/d1/platform/pricing/ ; https://developers.cloudflare.com/workers/platform/pricing/
- `d1AnalyticsAdaptiveGroups` può restituire gruppi vuoti quando nessuna operazione raggiunge SQL o quando non è disponibile la misurazione; il vuoto **non prova zero**. Fonte: https://developers.cloudflare.com/d1/observability/metrics-analytics/
- Runbook già disponibile: `CLOUDFLARE-D1-GRAPHQL-UNKNOWN-V079-RUNBOOK-20261121.md`. Non avviare query D1 per fabbricare telemetria.

## Roadmap senza perdere gli altri filoni
1. **v0.81 LAB**: preparare (senza eseguire) un adapter read-only per due finestre GraphQL D1 oggi/ieri, con timeout, limiti, inventario UUID verificato, output sanitizzato e confronto con run GitHub. Una vera chiamata al provider con i Secret esistenti richiede **consenso specifico** e verifica dei limiti Free. Evitare riavvii ripetitivi del monitor già fallito.
2. Access Free: verificare piano, posti e policy reale; fino ad allora NON creare utenti. Preparare percorso diretto Worker same-origin e JWT `ctx.access`, senza Service Binding/Static Assets router per propagare identità; test Safari login/logout/revoca con consenso separato.
3. D1 staging: fixture dedicato e reversibile solo dopo contatori correnti, quota/Seats confermati e autorizzazione; nessuna migrazione ai DB storici o `main`. Mantenere originale-level `RESERVED` e audit OWNER append-only senza sblocchi automatici.
4. Pilot collaboratori: 1–2 invitati, accesso in lettura a REMURA generale, scrittura **solo dei propri livelli autorizzati**, OWNER audit/approvazione; Telegram formattato solo livelli approvati e con consenso.
5. TradingView v0.8.181 LAB: holdout1 23–29 novembre 2026 UTC; holdout2 30 novembre–6 dicembre UTC. Shark Science v0.4 LAB: COT, sentiment, delta/CVD e proxies, nessun edge istituzionale provato finché non validato out-of-sample.
6. Experience v0.30 LAB splash toro/orso 3D + pinna REMURA e SMF, rimozione foto; Private Capture v0.15 LAB STOP; Ampere Radar v0.36 operativo, Oracle collector attivo e autoupdater bloccato, v1.65 root-owned staged **NO-GO install**; backup, Squalincome e Telegram roadmap preservati.
7. Monitorare limiti Free; non aggiungere nuove spese o deploy senza consenso. Se chat pesante, passaggio di consegne completo con SHA, CI e roadmap, evitando test già conclusi.

## Limiti e sicurezza
- GitHub `mirkoworz/remura` è **pubblico**: niente token, e-mail/nomi reali, chiavi HMAC, ID account privati o dati di mercato riservati nei file o log.
- La nuova pagina è un report **statico**, non un pannello live; i dati sono del 21/11. I nuovi test sono **offline sintetici** e non attestano Cloudflare reale.
- Nessuna necessità del Mac. Nessun deploy, merge, modifica Oracle, nuovo D1, nuovi utenti, Secret reali, fatturazione o acquisizione dati reali.

**STAGING REALE = NO-GO fino a nuove prove e autorizzazione.**
