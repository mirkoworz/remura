# REMURA — TRACK A: Qualità H1 e raccolta prezzi

**Ultimo stato attestato:** 03/11/2026 ore 20:54 Italia. **Roadmap coordinatrice:** [ROADMAP.md](ROADMAP.md). **Track parallelo:** [B — Shark Science](ROADMAP-B-SHARK-SCIENCE.md).

## Scopo
Assicurare che REMURA ragioni su prezzi **realmente verificati** e non su H1 vecchie, incomplete o con orologi incoerenti. Priorità alla causa dei problemi, non a rendere artificialmente verdi gli indicatori. Questo track NON introduce nuovi segnali né modifica il modello trading.

## Baseline attendibile
- Applicazione **LIVE v1.62** installata il 03/11/2026 ore **20:31 Italia**, nove pagine e banner verificati, SQLite backup+restore-test, rollback e SHA autoupdater riconciliati su `1568edefabc7bbdb7d06485d2b863b196a4e6155`. GitHub `main` può avere nuovi commit di **soli dati Myfxbook**: SHA main NON è prova di nuovo codice LIVE.
- Collector ON, Squalincome 34 mercati, monitor post-ingest ON, COT sync ON, batch timing ON e rotazione prioritaria ON. A 20:46 8/8 ultimi batch salvati, 8/8 post-scan riusciti e nessun errore.
- Diagnostica 20:39: **26/34 H1 pronte**, **8/34 stale oltre 120 minuti**, almeno 55 barre, 0 insufficienti/anomale. Otto simboli osservati a 20:46: `NAS100`, `NZDCAD`, `NZDCHF`, `NZDJPY`, `NZDUSD`, `US30`, `US500`, `USDCAD`.
- `REMURA_H1_PAIRED_ENABLED=1` attivato reversibilmente alle 20:50 Italia, riavvio e health OK. Primo campione reale letto alle 20:54: `samples=1`, `comparableSamples=1`, `unverifiableSamples=0`; 5 mercati, H1 ready **5→5**, **0 stale→ready**, **0 barre avanzate**, 5 invariate. Questo NON dimostra nulla sugli altri 29 mercati né un trading edge.
- L'algoritmo H1 paired esegue il confronto **alla stessa UTC**: 1–5 mercati del batch vs full-scan di 34; campione N/D se non confrontabile. Soglia H1 120 min, almeno 55 barre, snapshot full-scan entro 30 min. Registro solo aggregati, max 256 campioni, senza nomi/prezzi/token. Un avanzamento NON prova causalità del batch.
- Diagnostica privata sul repository `mirkoworz/remura-collector`: PR **#22** aggiunge campioni/validi/N/D/recuperi usando la **GET già esistente**; PR **#23** aggiunge **una** schedulazione lun–ven 06:37 UTC, condizionata a `REMURA_VPS_DIAG_ENABLED=1`. Le PR erano integrate al 03/11; l'esito del primo run schedulato **non era attestato**.

## Passi e criteri di completamento (A)
- [ ] **A1 — audit aggiornato:** leggere lo stato LIVE **prima** di qualsiasi modifica (health, SHA installato, auto-update, flag nel processo, snapshot e campioni). Non confondere raccolte pre-attivazione con record `remura_h1_paired`; confrontare timestamp/slot. Preferire diagnostica privata read-only già presente, altrimenti un solo comando Termius quando davvero necessario. Verificare se il workflow schedulato è stato eseguito, non assumerlo.
- [ ] **A2 — campione sufficiente:** raccogliere **almeno 8 record paired nuovi, reali**, successivi all'attivazione; distinguere `samples`, `comparableSamples`, `unverifiableSamples`, `lastState`, `readyBefore`, `readyAfter`, `staleToReady`, `h1Advanced`, `h1Unchanged`. Se 8 totali ma troppi N/D, prolungare la misura anziché inventare conclusioni.
- [ ] **A3 — indagine per causa:** correlare gli 8 mercati stale con sessioni/chiusure H1 UTC, momento del full-scan, slot effettivi, finestra M15→H1 (4 barre), sorgente primaria/backup, età all'istante della decisione e weekend. Testare localmente le ipotesi UTC/DST prima di intervenire. Non confondere 26/34 osservati a 20:39 con stato attuale.
- [ ] **A4 — proposte senza costi:** simulare offline alternative sulla **stessa quantità di chiamate**: prioritaria 8×5=40 acquisizioni programmate/2h (EURUSD e XAUUSD ripetuti) contro 38 standard. Confrontare disponibilità realmente valida e N/D, non soltanto conteggi cosmetici. Rivedere [PR collector #19](https://github.com/mirkoworz/remura-collector/pull/19) (replay sintetico, non effetto LIVE certificato).
- [ ] **A5 — eventuale fix:** solo se supportato da campioni e test, preparare PR focalizzata su raccolta/telemetria; CI verdi e review diff. Un solo track per volta può effettuare merge, version bump e deploy VPS. Ogni rilascio applicativo richiede **v nuova + data/ora italiana effettiva in alto sulle nove pagine**, backup SQLite, restore-test, rollback e riconciliazione autoupdater.
- [ ] **A6 — conclusione:** report con prima/dopo su campioni reali, impatto M15/H1/H4, differenza sulle esclusioni Squalincome, latenza e uso API/disco. Se non c'è miglioramento dimostrabile, dichiararlo.

## Limiti, costi e coordinamento
- **Gratis prima di tutto**: zero nuove richieste a cTrader/Capital/Myfxbook per questo audit; non aggiungere polling o cron senza stimare quota/costi e consenso. Oracle Always Free, GitHub Actions e Firestore devono restare nei limiti: le fatture vere non sono verificabili dai soli dati RAM/disco.
- Lavorare su ramo dedicato `research/track-a-h1-20261104`, nato da SHA attuale di `main`, e PR separata. **Non modificare** file del track B, modello segnali/CVD, notifiche o `ROADMAP-B-SHARK-SCIENCE.md`.
- **Durante le due chat:** aggiornare principalmente questo file per il progresso del track A; sincronizzare `ROADMAP.md` soltanto quando si integra la PR, dopo aver ricontrollato il nuovo `main`. Non fare merge o deploy sulla fiducia: fermarsi e riconciliare se l'altra chat ha aggiornato `main`.
- Nessun trade automatico o pretesa di anticipare con certezza gli istituzionali; l'idoneità delle H1 è prerequisito per test statistici, non una strategia profittevole.
