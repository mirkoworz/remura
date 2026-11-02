# REMURA v1.57 — rilascio intraday protetto (piano, NON installato)

Preparazione: 02/11/2026, Europe/Rome. **Attualmente in produzione: v1.56.**

## Obiettivo misurabile
- Conservare tutti i **38 mercati** nella rotazione.
- Con `REMURA_PRIORITY_COLLECTOR_ENABLED=1` dopo il rilascio, raddoppiare la frequenza **di tentativi** EURUSD e XAUUSD a un massimo previsto di un tentativo ogni 60 min; gli altri 36 mercati restano una volta ogni 120 min. Le barre M15 ottenute includono quelle intermedie già chiuse.
- Otto batch da cinque: esattamente **40 posizioni-symbol ogni 2h**, contro 38 oggi (**+5,26%**). Il numero **effettivo** di richieste storiche può essere superiore per simbolo (2 giorni, finestre giornaliere ed eventuali recuperi da pagine incomplete). Il picco massimo di cinque simboli per batch resta invariato.
- Da documentazione cTrader Open API: limite pubblicato di **5 richieste storiche/sec per connessione** e 50 non storiche/sec; `ctrader_feed.py` ha intervalli di circa 0,35 s fra richieste storiche. È un controllo della **frequenza**, NON una certificazione di budget, continuità del feed, costo in euro o sfruttabilità trading.

## File nel pacchetto
- Backend: `scripts/private_server.py` (pianificatore prioritario, **spento per default**).
- UI: `nav.js` (banner in alto v1.57 + timestamp Italia al momento dell'installazione), `sw.js` (cache PWA distinta), e nove pagine HTML con riferimenti nav v157.
- `deploy/oracle/release_v157.py` (operazione manuale): verifica commit SHA e blob GitHub, cache di tutte le pagine, versione v1.56 presente, `autoupdate-state.json` riallineato al commit `d6e2cd7575e0e58a36d1512f6ccffee24fe2438a`, salute server e spazio disponibile. Backup SQLite consistente con prova di ripristino isolata; conserva 12 file precedenti per rollback, poi riavvia e ricontrolla la salute. **Non tocca `remura.env`**, non modifica autonomamente i flag.
- `tests/test_release_v157.py` e regressioni scheduler, Node UI; testano anche arresto sicuro su file/hash/versioni diverse e restart fallito.

## Gate indispensabili (in ordine)
1. **Due CI GitHub verdi sul commit finale PR #69**, compresi `test_release_v157.py`. Non usare un commit intermedio se nel frattempo la PR cambia.
2. **Preflight read-only** dal server del codice finale, scaricato da SHA immutabile + `git hash-object` verificato. Il comando `--check --commit SHA` non deve cambiare file e deve confermare `PREFLIGHT_V157=OK`.
3. Prima del deploy ripetere la diagnostica VPS: stato autoupdater `up_to_date`, SHA allineati, server sano, COT, 38 mercati e RAM/disco; controllare che il sistema resti nella configurazione OCI Always Free dal pannello OCI.
4. **Rilascio manuale protetto**, dopo autorizzazione: `release_v157.py --apply --commit SHA` con il **medesimo SHA** verificato, backup SQLite e rollback automatico file in caso di errore. Non ripetere `--apply` due volte.
5. Con v1.57 installata ma scheduler ancora **OFF**, testare banner v1.57/data reale e diagnosi post-riavvio dei 38 strumenti, volumi, COT, Squalincome e risorse. Nessun incremento API dovrebbe avvenire per il flag OFF.
6. **Attivazione separata** del flag privato `REMURA_PRIORITY_COLLECTOR_ENABLED=1` solo dopo test del piano e un backup del file `remura.env` con controllo del permesso proprietario. Riavvio supervisionato, verifica dopo due giri, ritorno a `0` se picchi/errori/polling lento.
7. Misurare per almeno due cicli completi: `lastAttempt`, `lastComplete`, errori, volume valido/gap, esclusioni `prices_stale` e qualità CVD. **Non interpretare CVD come aggressione reale di ordini né garantire miglioramento dei profitti.**
8. Solo dopo collaudo: merge PR #69 e riconciliazione stato autoupdater con nuova main SHA, senza `--init-sha` o nuovo deploy automatico.

## Rollback
Lo script conserva `predeploy-backups/rollback-v157-...` e un backup SQLite. Il rollback dei **file** è automatizzato nel caso di errore d'installazione; dopo una perdita totale di alimentazione può servire il ripristino manuale. Lo script `--rollback-dir` verifica gli hash dei 12 file e riavvia la versione precedente, senza sostituire lo storico SQLite.

## Confronto attuale
Diagnostica privata #17 del 02/11/2026 ~14:16 CET: `SHA_INSTALLATO=SHA_TARGET=d6e2cd7575e0`, stato `up_to_date`; 38/38 mercati integri e recenti; EURUSD tick volume 58/64, ritardo 47 min; XAUUSD 50/64, ritardo 107 min; Squalincome 3/34 analizzati, 12 `prices_stale`. Sono dati di confronto, **non validano ancora la v1.57**.

**Costi:** nessun servizio a pagamento aggiunto e nessuna modifica Oracle prevista; traffico e uso API potrebbero aumentare del ~5,3% in unità-symbol per 2h, con impatto monetario da verificare. Non considerare RAM/disco da soli prova della gratuità OCI.
