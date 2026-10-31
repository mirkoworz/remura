# REMURA — Roadmap scientifica Shark Tracker
Aggiornata: 31 ottobre 2026 (Europe/Rome). Stato: **piano di ricerca e sviluppo**, non release installata.

## Obiettivo e confini
Portare REMURA da dashboard COT / sentiment / prezzi a piattaforma privata di ricerca quantitativa capace di classificare il contesto, studiare i movimenti e **segnalare solo setup con evidenza fuori campione**. Nessun modello promette profitti. Le etichette "istituzionale", "squalo", "assorbimento" descrivono **ipotesi**: OHLC, tick e sentiment non identificano chi ha eseguito gli ordini.

Vincoli inderogabili:
- **Zero nuove spese per impostazione predefinita**. Prima misurare quote API, OCPU, RAM, disco, rete e backup della tenancy Oracle; nessuna scalata automatica o sottoscrizione a pagamento.
- **Nessuna operazione automatica**, nessun accesso a conti prop/MT5/CFD per inviare ordini, nessuna chiave o dato personale in commit/log/PR.
- **Preservare collezione, SQLite, COT, Squalincome, storico e accesso Tailscale**. No backfill inventati, report COT conoscibili soltanto dopo la prima disponibilità reale, sentiment associato all'istante effettivo.
- Nessuna pretesa "ENTRA ORA" prima di feed live attendibile, validazione prospettica e calcolo costi/latency.
- **Ogni rilascio visibile** deve aggiornare versione + data/ora italiana nella testata comune di ogni pagina e invalidare la cache PWA. Una PR di sola ricerca **non cambia** la versione live.
- Modifiche Python/scripts/workflows restano **manual_required** nel meccanismo attuale. Non forzare l'autoupdater né dichiarare installazioni non verificate.

## Stato iniziale verificato nel repository
- Branch `main` con intestazione UI **v1.52**, NON attestazione che ogni componente sia installato sulla VPS.
- `scripts/ctrader_feed.py`: richieste storiche **M15**, non streaming tick / delta futures. Il formato `candle()` e lo storage non conservano tick volume; il modello cTrader storico potrebbe renderlo disponibile, da verificare su schema e broker.
- `scripts/private_server.py`: raccolta a rotazione (gruppi di cinque) dopo il quarto d'ora; osservatore Squalincome ogni 15 minuti. Non supporta ingressi entro secondi.
- `scripts/price_store.py`: retention M15 **45 giorni**, max 4.320 barre per mercato, oltre a H1/H4 derivati.
- `scripts/statistical_validation.py` e `dual24_validation.py`: valutazioni **teoriche e lorde**, non risultati operativi netti.
- `remura-collector`: diagnostica remota GitHub/Tailscale **sola lettura**, nessuna SSH/root né deploy.

## Fasi, gate e criteri di uscita

### P0 — Sicurezza del rilascio e diagnostica risorse (prima di modificare il servizio attivo)
1. Misurare *sulla VPS* CPU, RAM, disco/inode, dimensione SQLite/WAL, spazio e integrità dei backup, rete, job, richieste al broker.
2. Verificare le quote **effettive** Always Free e GitHub Actions; impostare limiti di crescita, soglie di arresto e retention.
3. Progettare un deploy approvato per backend con **backup coerente, test, health-check, rollback, principio del minimo privilegio**, mai un accesso CI illimitato. Primo setup potrebbe richiedere un comando autorizzato.
**Gate:** risorse e backup attestati, accesso privato invariato, deploy di prova e rollback verificati. Finché manca, nessun cambio automatico alla VPS.

### P1 — Shark Science Lab offline (PR corrente: *fondazione*)
- Aggiungere un motore **puro e in sola lettura** di backtest M15: breakout e ripresa del trend dopo pullback come ipotesi iniziali, nessuna pretesa di "seguire la banca X".
- Signal solo a **chiusura barra**; ingresso ipotetico alla **open successiva**, entrate/uscite su OHLC autentico dello stesso feed; scartare buchi, barre incomplete e dati incoerenti.
- Costi **obbligatori** (spread + slippage + commissioni round-trip stimati), periodi di training/holdout separati per settimane, nessuna ottimizzazione sui dati holdout.
- Comparazione con baseline senza filtri REMURA e, **solo dopo aver provato l'allineamento temporale**, con filtri COT e sentiment "as-of".
**Gate:** test automatici su futuro, gap, costi, split, nessuna scrittura sul DB. I risultati sono *esplorativi*, non trade.

### P2 — Validazione scientifica
- Pre-registrare regole, mercati, orari, definizioni di segnale, parametri e date delle prove.
- Confrontare **breakout**, **pullback**, e successivamente **Wyckoff spring/upthrust** e **stop-cascade**: non trattare le etichette Wyckoff come verità.
- Misurare expectancy netta, max drawdown, profit factor, spread stressato, slippage, stabilità per sessione/regime, cluster indipendenti per settimana, CIs, periodi laterali e peggiori settimane.
- Separare addestramento, validazione e test; poi registrare in avanti ogni setup e anche gli **scartati**. Evitare data snooping e revisione retroattiva dei parametri.
**Gate:** miglioramento *fuori campione* rispetto alla baseline, ripetuto su settimane indipendenti, più verifica demo. Un campione sufficiente non implica alcuna garanzia.

### P3 — Live Timing minimizzato
- Prima aggiungere volume/tick-volume alle barre **solo se davvero presente nel feed** e senza confonderlo con i contratti futures o con il delta bid/ask.
- Se P2 giustifica il costo infrastrutturale, abilitare **un solo simbolo EURUSD**, streaming quotazioni autorizzate cTrader, aggregazione M1/M5, sampling e retention corta.
- Registrare data evento e data ingestione, bid/ask e latenza; mai spacciare livello II del broker per book di tutto il mercato Forex.
**Gate:** quote API e risorse sotto limite, assenza di dati obsoleti, stop automatico se l'acquisizione è anomala.

### P4 — Risk Guardian (prima delle notifiche operative)
- Simulare stop realistici, spread dinamico, slippage, rischio per trade e aggregato, esposizioni correlate, limiti giornalieri e **stato 'non entrare'**.
- Lo stop deve poter annullare ogni verdetto di altri moduli. Nessun martingala o mediazione in perdita.
**Gate:** backtest + forward demo conservativi e protezioni testate.

### P5 — Shark Entry su iPhone
- Pannello "osservazione / preparazione / trigger candidato / veto rischio", con timestamp, feed, segnale e motivazioni; push solo dopo test delle notifiche PWA e Tailscale.
- Esplicitare ritardo, prezzo effettivo ottenibile e stop/invalidazione; no ordini automatici.
**Gate:** segnale riconducibile a dati precedentemente osservati, audit dei falsi segnali, alert tempestivi.

### P6 — Espansione disciplinata
- Estendere a XAUUSD, DAX, petrolio e altri strumenti **uno alla volta**, con orari/contratti/quotazioni appropriati; non riutilizzare soglie EURUSD.
- Feed futures CME/Eurex o licenze solo se l'esperimento gratuito dimostra cosa manca e si è valutato il costo aggiuntivo (con esplicito consenso).

## Registro dei rischi
- **Leakage:** mai usare COT del martedì prima della pubblicazione effettiva; non interpolare sentiment mancante; controllare i timestamp UTC.
- **Esecuzione:** `open` successiva è fill teorico; costi fissi sono ipotesi, non spread misurato. Comparare anche scenari di costo peggiori.
- **Campione:** 38 mercati nella stessa settimana macro NON sono 38 prove indipendenti. Una finestra di 45 giorni è troppo corta per conclusioni robuste.
- **Qualità dati:** quando il prezzo è stale/gap, o broker/ticker differiscono, risposta = N/D e mai segnale.
- **Strategia pubblicata:** nessuna teoria (Wyckoff, smart money, momentum, COT) è profitto garantito. Ricercare anche controesempi.

## Tracciabilità di questa PR
Solo moduli di ricerca offline, test e documentazione su un branch di sviluppo.
Nessuna versione UI aggiornata, nessuna installazione su Oracle, nessuna nuova API, nessun costo abilitato.
Prossimo rilascio visibile: numero successivo **solo dopo** test verdi, backup, approvazione e collaudo effettivo.

## Avanzamento P1 — adattatore SQLite offline (31/10/2026)
- `scripts/shark_sqlite_lab.py` legge **un solo strumento** direttamente dalla tabella `prices` già esistente, con `mode=ro` e `PRAGMA query_only=ON`. Non usa `price_store.connect()` (che configura WAL e crea tabelle) e non modifica collector, API o stato dei servizi.
- Per avviare la ricerca sarà necessario far girare localmente il programma in un ambiente autorizzato con accesso all'archivio. **Non è stato eseguito sulla VPS**, né su dati privati reali durante questa PR.
- Rifiuta documenti con broker, simbolo, provider o `lastComplete` incoerenti. Restituisce **solo aggregati e timestamp**, senza OHLC o identificativo del broker. Analizza l'intero campione conservato, non inventa storico remoto.
- Test offline aggiunti; il laboratorio non potrà dichiarare una strategia validata con il solo archivio a rotazione di circa 45 giorni. I costi sono **stime fornite esplicitamente**, non misure reali del broker.
- Nessuna nuova lettura cTrader, chiamata GitHub, spazio dati aggiuntivo sulla VPS o upgrade Oracle. Non utilizzare in produzione prima dei gate P0.

## Avanzamento P0 — preflight risorse (31/10/2026)
- Nuovo script `scripts/resource_preflight.py`: quando eseguito **localmente sulla VPS autorizzata**, raccoglie *solo metadati* di volume disponibile, inode, memoria (con preferenza limiti cgroup), carico CPU informativo, dimensione archivio SQLite + WAL e presenza della directory dei backup.
- Non legge contenuto dei backup o del database, non apre connessioni SQLite, non richiede nuove API Oracle/cTrader, non accede a chiavi, non modifica servizi o raccolte. Nessun percorso o identificativo personale appare nel riepilogo JSON.
- Conserva **sempre** `allowAutomaticExpansion=false`: un esito positivo del solo controllo locale NON certifica la fatturazione Oracle Always Free, le quote della tenancy, l'integrità reale del backup, la qualità dei dati o la sicurezza di un deploy.
- Soglie prudenziali di sola **capacità locale**: almeno 2 GiB e 20% disco libero, almeno 512 MiB e 20% RAM disponibile, almeno 10% inode liberi. Dati mancanti, assenza archivio o della directory backup impongono lo stato `hold`.
- Aggiunti test offline riproducibili; **nessun test live Oracle è stato eseguito**. Per completare P0 serve esecuzione autorizzata sulla VPS, verifica indipendente della quota Always Free e collaudo backup/rollback.
