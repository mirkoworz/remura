# REMURA TradingView v0.8.184 LAB — EXPLICIT M5 CAPTURE COVERAGE

**Checkpoint: 21 novembre 2026 · ore 18:14 CET (Europe/Rome)**

## Risultato GitHub verificato
- Repository pubblico `mirkoworz/remura`; branch LAB isolato `research/tradingview-m5-coverage-v0184-20261121`.
- Base v0.8.183 `b1c65e59334300c7920756b866329e1dd58540f0`; non modificato `main`.
- Commit di CODICE testato `a63da52415be469062a7dc259efc3403da8d23e0`.
- Run one-shot https://github.com/mirkoworz/remura/actions/runs/44928854306: **SUCCESS**; log `Ran 25 tests`, `OK`, `REMURA_TV_V0184_M5_COVERAGE=25_25_PASS`.
- 25/25 test **NUOVI** PASS; nessun test storico ripetuto, nessun deploy, Secret, cattura dati reali, Oracle o spesa.

## Nuovo modulo
- `explicit_m5_coverage_v0184_lab.py`: usa esclusivamente **slot M5 sintetici ed esplicitamente richiesti** dall'operatore, con fold HOLDOUT_1 o HOLDOUT_2, insieme a osservazioni sintetiche. Reimpiega i boundary v0.8.182 (protocollo V2 pin Git) e v0.8.183 (lateness <= close+120 sec e prima del next close); NON modifica sorgenti precedenti.
- Contatori `planned_slots`, `timely_captures`, `late_captures`, `uncaptured_requested_slots`. Un evento mancante **non** viene sostituito, un tardivo **non** diventa puntuale. Non seleziona segnali, pesi o esiti, non forma coppie e non calcola PnL.
- Blocca slot duplicati o disordinati, timestamp non UTC/non M5, eventi fuori piano o fold errato, più eventi che slot, fingerprint duplicati, eventi incoerenti, protocollo drift, piani fuori dai limiti.
- Un intervallo non pianificato **NON** viene automaticamente considerato barra mancante. Non esiste attestazione di calendario FX, disponibilità feed o storia completa; nessuna imputazione di weekend/chiusure mercato.
- Output conserva `exchange_calendar_attested=false`, `capture_provenance_attested=false`, `market_coverage_attested=false`, `zero_captures_prove_no_market_activity=false`, `future_outcomes_used=false`, `edge_claim_allowed=false`, `decision=NO_GO_LIVE`.
- Nuovi `test_explicit_m5_coverage_v0184_lab.py` con 25 casi e workflow `.github/workflows/remura-tv-m5-coverage-v0184-one-shot-ci.yml`. Solo Python stdlib e runner pubblico read-only.

## Roadmap scientifica invariata
1. Il protocollo `CVD-PROSPECTIVE-PROTOCOL-V2.md` resta **pinned byte-for-byte** (Git blob `4b0f5d5defacfdbf8e902af5a8eea32947cabeca`), calendario UTC immutato: development 16–22/11, HOLDOUT_1 23–29/11, HOLDOUT_2 30/11–06/12/2026, fine esclusiva 00:00 UTC giorno successivo.
2. Primario CVD vs price-only a 60 minuti; secondari, costi di 0/1/2 pip ipotetici e criteri FIFO preregistrati non cambiati. Nessun risultato OOS ancora misurato, nessun edge istituzionale dimostrato, nessun sistema live attivato.
3. Prossimo passo utile: qualità dell'inventario delle acquisizioni e coerenza dei timestamp di disponibilità; se mancano feed privati verificati, lasciare UNKNOWN e NON tentare ricostruzioni retrospettive.
4. Shark Science v0.4 LAB resta separato per evidenze COT, sentiment retail, delta/CVD, assorbimento ed Effort/Result; non collegare aggregati anonimi a decisioni individuali senza chiavi e orologi verificati.
5. Contributors v0.84 laboratorio Free/Access D1 ancora NO_GO reale, quattro pagine v0.78 LAB; Experience v0.30 LAB toro/orso splash + SMF; Private Capture NON attivato, Oracle collector e Ampere Radar invariati, backup e Squalincome preservati.
6. Nessun Mac richiesto per test LAB GitHub; non ripetere suite GREEN, niente credenziali, dati privati, deploy/merge/costi senza autorizzazione. Salva SHA e CI nel passaggio di consegne.

**Risultato: v0.8.184 GREEN 25/25 sintetico; edge trading e copertura reale NON verificati.**