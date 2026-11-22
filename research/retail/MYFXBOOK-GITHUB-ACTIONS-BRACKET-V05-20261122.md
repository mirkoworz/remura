# REMURA Retail — Myfxbook v0.5, intervalli temporali GitHub
**22 novembre 2026 — Europe/Rome. Solo LAB.**

## Nuovo risultato verificato
- Branch `research/retail-gh-actions-time-bracket-v05-20261122`;
  nuovo codice `research/retail/github_actions_time_bracket_v05_lab.py`
  e 16 nuovi casi `test_github_actions_time_bracket_v05_lab.py`.
- GitHub Actions [run 45022967620](https://github.com/mirkoworz/remura/actions/runs/45022967620)
  **SUCCESS, 16/16 PASS**, log letto:
  `REMURA_RETAIL_GH_TIME_BRACKET_V05=16_16_PASS`.
- La prova non riesegue suite v0.2, v0.3, v0.4 né audit multi-symbol
  preesistenti. Nessun Secret né lettura Myfxbook API nei test.
- Ciascun esempio collega (a) run schedulata Myfxbook con `head_sha`
  che risulta **genitore del commit successivo**, (b) blob Git del
  `data/myfxbook/latest.json` della versione confermata, (c) ora UTC
  dello snapshot Myfxbook, (d) run Pages `head_sha` uguale al nuovo commit
  e `created_at` riportato dal servizio GitHub.

| Data UTC | Avvio run collector GitHub | Snapshot UTC | Avvio run Pages GitHub | Ampiezza intervallo |
|---|---|---|---|---|
| 20/11/2026 | 11:18:27 (ID 44726515105) | 11:18:32 | 11:18:34 (ID 44726531678) | 7 secondi |
| 22/11/2026 | 01:36:08 (ID 44972218268) | 01:36:15 | 01:36:18 (ID 44972231080) | 10 secondi |
| 22/11/2026 | 08:50:31 (ID 45004678062) | 08:50:44 | 08:50:46 (ID 45004698324) | 15 secondi |

Le tre run Pages risultavano SUCCESS nei metadati GitHub; il comparatore
offline però blocca solo **orari e identità preventivamente letti** dalla
connessione GitHub. Non autentica nuovamente quelle risposte né produce
una marca temporale notarizzata. I tre avvii Pages si verificano **prima**
dell'orario `updated_at` di completamento della run collector:
non usare la conclusione della run per ricostruire arbitrariamente il
momento della push o del primo accesso pubblico al contenuto.

## Cosa si può affermare
- Il `latest.json` realmente contenuto in ciascun commit ha il blob
  Git SHA-1 esattamente previsto e lo stesso `updatedAt` del campione.
- Il commit successivo ha realmente come genitore l'HEAD della
  run Myfxbook precedente, per ciascuno dei tre campioni.
- Nei metadati GitHub precedentemente consultati, l'inizio della run
  collector precede il campione e l'inizio della run Pages è successivo.

## Cosa NON si può ancora affermare
- I due eventi server GitHub non sono prove firmate dal provider Myfxbook.
- Il clock dello snapshot deriva dal collector REMURA, non dalla
  pubblicazione originale del mercato e può differire dal vero first-seen.
- Una run Pages iniziata non dimostra disponibilità pubblica già avvenuta.
- L'intervallo non rende scientificamente ammissibile un CVD, un dato COT
  o un backtest per decisioni già passate.
- Non sono stati raccolti i payload Myfxbook dal provider durante
  questa procedura, né fatte nuove chiamate Cloudflare/Oracle.

## Prossimo gate
Separare in uno schema futuro `collector_run_created_at`,
`local_sampling_at`, `content_commit_id`, `pages_run_created_at`,
`page_deployment_completed_at_or_UNKNOWN`,
`provider_publication_at_or_UNKNOWN`,
`independent_received_at_or_UNKNOWN`.
Ricostruire in maniera verificabile solo quando esiste una prova autentica;
non retrodatare o promuovere automaticamente gli snapshot storici.
Nessuna nuova automazione senza consenso e verifica del budget Free.

**Esito:** 16/16 GREEN su tre commit reali, first-seen indipendente e
vantaggio istituzionale ancora NON dimostrati.
