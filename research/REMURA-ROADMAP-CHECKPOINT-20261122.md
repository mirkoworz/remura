# REMURA — roadmap checkpoint multi-filone LAB
**Data:** 22 novembre 2026, Europe/Rome. **Nessun merge o deploy.**
Repository `mirkoworz/remura`. Ultimo `main` verificato prima di questi
commit LAB: `7c70bb9fd0e774d45c493217382c430b448af0e2` (Myfxbook automatico).
Nessuna modifica applicata qui a `main`, Oracle o Cloudflare.

## Avanzamento di questo checkpoint (nuovo, non ripetizione)
| Track | Nuovo artefatto / branch isolato | Stato |
| --- | --- | --- |
| A — COT Revision Science | `research/cot-revision-lineage-lab-20261121`; `research/cot/cot_atomic_ingest_v02_lab.py`; `COT-ATOMIC-V02-HANDOFF-20261122.md` | 16/16 GREEN GitHub Actions run 44998195582; LAB synthetic, real NO-GO |
| B — TradingView | `research/tv-decision-evidence-contract-v0186-20261121`; `TV-HOLDOUT-ADMISSION-PREFLIGHT-20261122.md` | Preflight prospettico pronto; real evidence NO-GO |
| C — Contributors | `research/contributors-access-free-hardcap-v092-20261121`; `CONTRIBUTORS-PILOT-NOGO-20261122.md` | Piano 1–2 amici pronto, Access/D1/Safari veri NO-GO |
| D — Retail × COT | `research/retail-history-readonly-real-data-20261121`; `RETAIL-COT-ASOF-EVIDENCE-CONTRACT-20261122.md` | Classi evidenza/as-of documentate; confronto reale NO-GO |
| E — Mac | Experience v0.30, Private Capture v0.15, custody v1.65 | Nessun file toccato, coordinare con Codex Mac |
| F — Free / governance | Nessuna chiamata Cloudflare, nuovi utenti, deploy o costi | Margini reali Cloudflare UNKNOWN; verificare solo previa autorizzazione |

## Confini scientifici invarianti
- COT `cot_reports` può sovrascrivere una riga con `ON CONFLICT DO UPDATE`;
  `cot_first_seen` non identifica la versione originale dopo una correzione.
  Il LAB v0.2 mostra il comportamento desiderato con fixture in-memory;
  **non** attesta revisioni avvenute davvero su Oracle.
- I 20/20 COT v0.1 non sono stati rilanciati; v0.2 ha 16 nuovi test.
- TradingView V2 non modificato: Development fino al 23/11 00:00 UTC;
  Holdout 1 23–30 novembre UTC; Holdout 2 30 novembre–7 dicembre UTC.
  Avvio finestra NON equivale ad avere CVD autentico, anchor indipendente o edge.
- Myfxbook = RETAIL, CFTC = futures per classi; niente equivalenza con
  istituzionali live, tick volume aggressore o CVD TradingView.
  Audit passato 34 file / 3.984 osservazioni su snapshot precedente; ultimo
  snapshot noto 22/11 01:36:15Z 89 simboli; non è stato rifatto l'audit.
- Contributors v0.92: precedente 15/15 composizione, 12/12 revoche, 18/18
  ownership, 18/18 preflight e 22/22 hardcap free fixture non ripetuti.
  Non rappresentano prova di disponibilità reale di quote o iPhone Safari.
- Oracle v1.65 firmato/preparato in area protetta, NON installato; collector
  preservato, autoupdater inibito come da checkpoint Mac. Nessuna sovrapposizione.
- Ampere Radar monitor gratuito Oracle Milano/Telegram già attivato in passato;
  non riattivarlo e non confondere l'assenza di capienza con capienza zero futura.

## Prossimi gate (ordine dipendente dalle evidenze, non solo dal calendario)
1. **COT:** esaminare il passaggio append-only + proiezione atomica persistente
   con Codex Mac; niente migrazione e niente historic backfill senza backup,
   clock, CI, concordanza branch e autorizzazione.
2. **TV:** il 23/11 classificare per-decisione ammissibile / late / conflict /
   UNKNOWN solo dopo verifica degli artifact reali; non sbloccare holdout
   per il solo arrivo della data. Nessun tuning.
3. **Contributors:** ottenere il margine **reale** Access/Workers/D1 e consenso
   esplicito prima del pilot; testare login/logout/revoca su iPhone reale.
4. **Retail:** implementare in futuro join temporale versionato solo quando
   identificativi e mapping spot/futures siano certificati; non far passare
   uno storico corrente per un vero snapshot decisionale.
5. **Mac:** raccogliere stato Codex senza eseguire comandi concorrenti.
6. **Spesa:** gratis per quanto verificato nelle nuove attività GitHub;
   API Free Cloudflare/space/seats/requests/stoccaggio attuali sconosciuti
   finché non viene letta fonte autorizzata. UNKNOWN non significa zero.

## Release e sicurezza
PR #105 Contributors e #106 TradingView restano research DRAFT / no merge
secondo l'ultimo checkpoint; da rivalidare in caso di nuove decisioni.
Nessun Secret, utente reale, provisioning, modifica Oracle o integrazione
Telegram è stato attivato. Le future pagine REMURA devono riportare
versione e timestamp Europe/Rome in alto; qui sono cambiati solo LAB e docs.
