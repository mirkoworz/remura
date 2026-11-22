# REMURA Retail — GitHub Pages server-event receipt v0.4 LAB
**22 novembre 2026 — Europe/Rome.** No new provider calls, runs, Secret, scheduling, merge, deployment.

## Evidence newly compared
- Branch: `research/retail-gh-pages-receipt-v04-20261122`.
- `research/retail/github_pages_receipt_association_v04_lab.py`: read-only
  comparator for two previously created GitHub Pages runs with **real Git
  commits and exact blob SHA-1** containing historic Myfxbook EURUSD samples.
- `research/retail/test_github_pages_receipt_association_v04_lab.py`: 12
  **new** tests only. GitHub Actions
  [45018604348](https://github.com/mirkoworz/remura/actions/runs/45018604348)
  **SUCCESS, 12/12**, verified job log and marker
  `REMURA_RETAIL_GH_PAGES_V04=12_12_PASS`.

| Snapshot record UTC | Repository commit | Existing Pages run ID | Run created_at reported by GitHub UTC | Difference |
| --- | --- | --- | --- | --- |
| 2026-11-20 11:18:32 | `32188ca6304b86190d993159260f3baf4a801e89` | `44726531678` | 2026-11-20 11:18:34 | 2 seconds |
| 2026-11-22 01:36:15 | `7c70bb9fd0e774d45c493217382c430b448af0e2` | `44972231080` | 2026-11-22 01:36:18 | 3 seconds |

The pairs were obtained from the existing GitHub REST Actions run metadata,
where `head_sha` matched the corresponding repository content commit, and
the pages workflow finished successfully. The offline test freezes these
already-read fields and checks timing/order and actual Git object contents.
The **offline fixture does not re-authenticate** the GitHub REST server
response. The GitHub `created_at` value is server-*reported* and can
provide a separately operated platform's timeline reference once retrieved
from GitHub through a trusted channel. It is **not** a cryptographically
notarized timestamp, a publication timestamp from Myfxbook, proof a trader
saw the same sample at that instant, or attested original market first-seen.

The source snapshot uses `datetime.now(timezone.utc)` after API fetch,
and its Git committer date is controlled by the commit producer. This
new GitHub-platform timeline is a distinct *upper-bound candidate* on
the commit's existence at server run creation, not a certification that
the provider supplied each underlying value at the same time.

## Scientific decision remains NO-GO
- **GitHub Pages runs are not COT or institutional order flow.**
- No first-seen from the market provider, no independently notarized source
  arrival or mapping between retail spot / CFTC futures.
- Never backdate a receipt based on a later workflow run, and never treat
  an on-time Pages build as admission of TradingView CVD or evidence of alpha.
- Future optional improvement: independently read Actions API run metadata
  via a separate, read-only observer, bind full run identity, payload/commit
  content and response timestamp, and preserve raw response provenance.
  Do NOT activate new workflows or external services without a new budget
  and permissions approval.

**Status: 12/12 synthetic contract tests GREEN; two actual Git blobs and
existing server-run metadata compared; independent provider timing UNKNOWN.**
