# REMURA Retail — 4 snapshot Git provenance v0.3 LAB
**22 novembre 2026 — Europe/Rome. Lettura real data via Git, NO-GO first-seen indipendente.**

## Evidence newly established (not repeated audits)
- Branch `research/retail-git-commit-witness-boundary-v03-20261122`.
- Nuovo `research/retail/myfxbook_git_commit_boundary_v03_lab.py`:
  **4 oggetti commit reali** di `mirkoworz/remura`, ispezionati con `git
  show` offline e blob SHA-1 vincolati a commit precisi; confronta il
  campione EURUSD di ogni `latest.json` con lo stesso record nello storico
  `data/myfxbook/history/EURUSD.json` del commit congelato 7c70bb9.
- Nuovi 12 test in `test_myfxbook_git_commit_boundary_v03_lab.py`.
  Workflow read-only, checkout Git limitato a 60 commit, nessuna chiamata
  provider, nessun Secret: [GitHub Actions 45002589685](https://github.com/mirkoworz/remura/actions/runs/45002589685).
  **12/12 PASS**, conclusione SUCCESS e marker
  `REMURA_RETAIL_GIT_BOUNDARY_V03=12_12_PASS`, log verificato.
- Snapshot EURUSD verificati:
  | Ora scritta nel record (UTC) | Commit | Blob `latest.json` |
  | --- | --- | --- |
  | 2026-11-20T11:18:32Z | `32188ca6304b86190d993159260f3baf4a801e89` | `05351844eed9e2575e8651fe4a701d50b518dfbf` |
  | 2026-11-21T08:12:01Z | `f1c05654c380035aaa7ffd52103b17c293f6f03d` | `9e5450715882e61abf2d46482c8ec444c649efa7` |
  | 2026-11-21T21:43:42Z | `06ebde2ce740f92fd8b44d5eb3c9d6faa57c7a07` | `89a5b483a6131edd926ff7ffaf8526262f9cefe3` |
  | 2026-11-22T01:36:15Z | `7c70bb9fd0e774d45c493217382c430b448af0e2` | `c2c4dfc6546fa26e315400995132fc60170cede1` |

## Discovery: why these are NOT timestamp witnesses
Il metadata Git *committer date* coincide, in questi quattro casi,
con l'ora dichiarata nei record. Tuttavia quel campo appartiene al commit e
può essere assegnato dal processo che lo crea: **non è un timestamp firmato
dal server GitHub al ricevimento della push**. L'orario degli snapshot è
creato da `scripts/update_myfxbook.py` con `datetime.now(timezone.utc)`
**dopo** il recupero API dei simboli, non da un campo documentato di
pubblicazione del provider. Il workflow `.github/workflows/myfxbook.yml`
esegue il collector, commit e push. La coincidenza delle date non aggiunge
un testimone indipendente.

Quello che è verificato: contenuti immutabilmente identificati dagli hash
*dei commit selezionati* e coerenti con lo storico del repository.
Quello che NON è verificato: disponibilità pubblica all'ora scritta nel
record, primo arrivo esterno, identità di un witness temporale esterno,
equivalenza futures/spot o COT istituzionale, alpha, profitti.

## Next gate (without deploying)
Per produrre un audit prospettico rigoroso, usare un witness di ricezione
indipendente e salvare commit/ref/hash payload con data accettazione attestata
dal server o altro sistema separato; mantenere i due orologi distinti.
Registrare esplicitamente `recorded_at` e
`independently_observed_at_or_UNKNOWN`; non retrodatare le osservazioni
legacy. Il vecchio audit 34 file / 3.984 osservazioni non è stato ripetuto.

**Decision:** contenuti Git confermati, primo-seen/causal admission NO-GO.
