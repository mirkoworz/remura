# REMURA Shark Science — COT v0.3 WAL reopen LAB handoff
**22 novembre 2026 — Europe/Rome.** SOLO RICERCA. **NO-GO Oracle.**

## Nuove evidenze verificate
- Branch: `research/cot-wal-reopen-v03-lab-20261122`.
- `research/cot/cot_wal_reopen_v03_lab.py`: crea un `TemporaryDirectory`,
  copia lo schema in-memory v0.2 in un database SQLite di prova creato
  automaticamente, abilita WAL, chiude e riapre il collegamento.
  Non accetta nomi di database Oracle o percorsi operativi.
- `research/cot/test_cot_wal_reopen_v03_lab.py`: **15 test NUOVI**.
- GitHub Actions **44999165979**:
  https://github.com/mirkoworz/remura/actions/runs/44999165979
  — esito completato SUCCESS, log del job letto, marker
  `REMURA_COT_WAL_V03=15_15_PASS`.
- Controllati commit persistenti dopo riapertura, separazione versioni prima/dopo
  revisione, rollback per errore introdotto tra righe, nessuna promozione di
  revisioni future, replay idempotente, trigger immutabili, collisione tra
  scrittori, `PRAGMA integrity_check`, chiusura e pulizia fixture temporaneo.
- Non eseguiti nuovamente i 20/20 del COT v0.1, i 16/16 del v0.2,
  né suite preesistenti di Oracle, TradingView, Contributors o Mac.

## Distinzioni indispensabili
1. La prova riguarda **chiusura/riapertura del DB** e rollback su eccezione
   sintetica, NON simula un vero guasto elettrico, kernel crash o storage failure.
2. WAL + checksum locale + first-seen dichiarato non provano un'ora indipendente
   di ricezione o l'autenticità della risposta CFTC.
3. Non è stata misurata la performance dei consumer reali né fatta una migrazione,
   né sono stati osservati dati COT Oracle reali. UNKNOWN resta UNKNOWN.
4. La v0.3 è uno *harness* che usa il codice v0.2 in fixture, non un sostituto
   del collector. Il codice operativo `scripts/cot_monitor.py` resta immutato.

## Prossimo gate riservato a coordinamento Codex Mac
- Confrontare il Mac branch aggiornato prima di disegnare la migrazione.
- Predisporre nuova tabella append-only solo additiva, con finestra transazionale
  contenente evento sorgente, valori per versione e proiezione dei dati consumer.
- Separare prova di ricezione locale, fonte attestata e tempo attestato da terzi.
- Verificare recovery da crash realmente persistente / fsync / WAL checkpoint,
  lock e conflitti, compatibilità delle letture legacy, backup & restore.
- Vietato retrodatare dati legacy o copiare le versioni attuali
  spacciandole per prima versione storica.
- Cloudflare e Oracle richiedono autorizzazione separata; nessun costo o deploy.
- Non interrompere né sostituire il collector live o la custodia v1.65.

**Decisione:** v0.3 fixture PASS (15/15); possibile integrazione Oracle ancora NO-GO.
