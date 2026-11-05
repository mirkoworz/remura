# REMURA v1.64 — Cinematic Splash Option B (CANDIDATO, NON LIVE)

**Proposta approvata:** 05/11/2026, estensione animazione ~4,3 secondi complessivi. La LIVE attualmente attestata dall'utente è **v1.63**, installazione e riconciliazione completate con backup SQLite e manifest rollback, commit installato `16fb7c84a130a2e54f849fa7eadddba4f62455bf`.

## Modifica grafica
- Prima apertura PWA Home: sei micro-fasi animate **550+600+650+650+600+250 = 3.300 ms**, poi **700 ms** remura agganciata e **320–340 ms** dissolvenza: durata visuale complessiva attesa **~4.32–4.34 s**, escluso l'avvio nativo di iOS. Le animazioni sono di presentazione; il server è verificato tramite **una sola** GET interna `/private-api/health` con timeout 1.100 ms e senza provider di trading.
- Barra e remura procedono insieme, con transizioni CSS di 720 ms; 100% solo dopo conclusione della verifica interna (successo o timeout); se il server non risponde, avviso di connessione senza dichiarazioni ingannevoli di dati finanziari freschi.
- `prefers-reduced-motion` mantiene entrata veloce (< 1 s) per accessibilità; chiusura di emergenza massimo 6,2 secondi. Navigazione interna non ripete lo splash.
- Stessa grafica scelta dall'utente: niente nuove immagini, nuovi servizi o download esterni.

## Regole del rilascio v1.64
- `nav.js` con banner v1.64 e **timestamp preparatorio** `05/11/2026 18:03 (Italia, preparazione)`; il guarded installer lo sostituisce con la **vera data/ora italiana al momento dell'applicazione**.
- Tutte e **nove** le pagine importano `nav.js?v=164`; `index.html` importa `splash.js?v=164` e `splash.css?v=164`. SW cambia cache a `remura-shell-v78-v1.64-shark-cinematic`; le API private non vengono mai cache-ate.
- Nessuna modifica ai collector, agli endpoint del server, alle soglie H1, ai segnali, alle API e a SQLite. I vecchi test di v1.58–v1.63 verificano ancora i loro installer storici usando fixture versionate.
- Installer `deploy/oracle/release_v164.py`: origine immutabile **v1.63** con 15 Git blob pinnati, update soli 15 file autorizzati (di cui modifica effettiva soltanto lato UI), compare whitelist stretta, SHA main/CI Price+Insights, backup SQLite con restore-test, registro rollback e riavvio verificato; non cambia autoupdater state.
- Riconciliazione separata `deploy/oracle/reconcile_v164.py`: pin di SHA/blob dello script installer, verifica hash 15 file e unico timestamp release, manifest rollback e backup SQLite, verifica CI, backup dello stato e modifica **esclusiva** di `autoupdate-state.json`.

## Correzione preflight STOP_SPLASH_SAFETY_GUARD — 05/11/2026
- Diagnosi: l'installer v1.64 cercava `setTimeout(close,4500)`, residuo dello splash v1.63; il caricamento cinematico approvato utilizza `failSafeTimer=setTimeout(close,6200)`, per consentire ~4,3 secondi di scena e sempre chiudere in caso di errore.
- Correzione limitata al **guard di verifica dell'installer**, non al client: conferma una sola GET health locale, il timer di emergenza 6200 ms, la pausa di aggancio e la gestione del fallimento. Regressioni negative bloccano un timer errato o la rimozione dei controlli.
- Nuovo installer immutabile: commit `883336a4e956a9e50c94dcfebf8d7ba78910fb65`, blob `5cad0abdff8a30f9e7dc583c872c213807863dc4`. Il riconciliatore v1.64 contiene entrambi i pin aggiornati. La PR deve passare la CI e poi essere unita a main prima di ritentare il preflight con **nuovo SHA target**.
- Il precedente `STOP_SPLASH_SAFETY_GUARD` è avvenuto in `--check`: nessuna installazione o backup nuovo v1.64 eseguiti; v1.63 ancora LIVE, riconciliata.
  
## Gate obbligatori
1. Lavorare in PR isolata; prima di merge/rilascio ricontrollare main e PR dei Track A/B. Non unire la PR hotfix #93 del vecchio riconciliatore prima del rilascio v1.64.
2. CI PR Price, Insights e splash tutte verdi; dopo merge richiedere specificamente CI **push/main** verdi sul commit target.
3. Visto che cambia `deploy/oracle/`, l'autoupdater deve classificare `manual_required` e non tentare di aggiornare automaticamente. **Il merge GitHub non installa l'app sulla VPS.**
4. Solo con accesso Tailscale funzionante, eseguire `release_v164.py --check --commit TARGET` come script scaricato da SHA immutabile e verificato con Git blob hash. Qualunque differenza dalla v1.63 attestata causa STOP; nessun `--force`.
5. Con preflight riuscito, eseguire `--apply --commit TARGET`: backup SQLite + restore-test e rollback, health test server. In caso di fallimento non ripetere alla cieca.
6. Quindi `reconcile_v164.py --check --target TARGET` e `--apply --target TARGET` con controllo SHA/hashes; solo dopo dichiarare v1.64 LIVE.
7. Collaudo reale iPhone: nuova durata, remura agganciata visibile, 9/9 pagine con banner v1.64 + ora italiana installata, ritorno Home senza nuova animazione, connessione assente, accessibilità riduzione movimento. Report quote Oracle/Firestore/GitHub Actions a parte, senza asserire spesa zero non verificata.

**Nessun nuovo provider o chiamata broker.** Si riusa la GET health esistente, senza incremento di frequenza rispetto al precedente splash v1.63.

**Stato:** preparazione, NON LIVE fino a prove operative VPS e riconciliazione.
