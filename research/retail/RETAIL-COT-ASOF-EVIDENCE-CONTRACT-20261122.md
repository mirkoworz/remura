# REMURA Shark Science — retail × COT as-of evidence contract v0.1
**22 Nov 2026 (Europe/Rome). Research only, no fetch, no deploy, no merge.**

## Facts that must remain distinct
- Myfxbook community outlook: **retail** account positioning proxy. It is not
  an institutional holding, futures exchange volume or aggressor CVD.
- CFTC TFF/disaggregated: public **futures** positioning by report category,
  reporting period and publication schedule; not a live order tape or exact
  realtime institutional entry/exit.
- A newer retail snapshot or revised COT number must **never** be applied to
  a decision made before it was locally received and demonstrably available.
- FX spot symbols and futures contracts are NOT automatically interchangeable;
  mapping, currency orientation, contract identity and coverage need explicit
  evidence. Otherwise NON_COMPARABLE, even if names look similar.

## Required evidence tuple per source and per decision
`{decision_id, decision_utc, provider, instrument_id, dataset, report_date,
provider_publication_utc_or_unknown, provider_observation_utc_or_unknown,
local_receipt_utc_or_unknown, independent_first_seen_utc_or_unknown,
immutable_content_sha256_or_unknown, exact_archived_payload_or_unknown,
revision_version_or_unknown, symbol_mapping_id_or_unknown,
mapping_status, evidence_tier}`.

Treat time labels separately: publication time, reported market reference time,
local receipt claim and independent first-seen witness are not synonyms.
If a field is unavailable, store UNKNOWN, not zero or the current time.
Original payload or prior immutable revision must be available to replay as-of;
a hash by itself is insufficient to recover earlier values.

## As-of admission algorithm (no new runtime in this document)
1. Select only recorded versions with receipt no later than decision UTC;
   independently witnessed time, when available, is an *additional* evidence
   quality field, never silently manufactured.
2. Require archived source values for that historical version and validate its
   content identity; if legacy data has only `cot_first_seen` while values may
   have been overwritten, return UNKNOWN for historical claims.
3. Check explicit mapping **before** any comparison. Unverified mapping =>
   NON_COMPARABLE, never infer correlation from a similar instrument label.
4. Report separate evidence classes: LOCAL_OBSERVED_UNATTESTED,
   EXTERNALLY_TIME_ATTESTED (only with real external witness),
   UNKNOWN_NOT_AVAILABLE, NON_COMPARABLE. A local digest/Ed25519 signature
   cannot upgrade the class without independent timing evidence.
5. Avoid ecological fallacy: aggregate retail/COT series cannot be attached
   to a specific TradingView decision without its own valid decision link.
6. Count availability, gaps, mapping failures and unknowns explicitly.
   Missing or non-comparable observations cannot be treated as flat markets.

## Current empirical boundary
Previous Myfxbook historical audit inspected **34 files and 3,984 observations**
for an earlier snapshot. Its 30 aligned series and 4 legacy US-index series
describe that checkpoint only. The 3,908 intervals >2 h do not prove missing
mandatory trading hours. The 22 Nov latest.json had 89 symbols, timestamp
2026-11-22T01:36:15Z; this document is NOT a repeat audit of that newer file.

No authenticated cross-source per-decision causal comparison, validated
futures/spot mapping, independent first-seen or statistical edge is established.
Aim: first make historical availability auditable, THEN test predictive value.
