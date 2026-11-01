# REMURA — Roadmap operativa unica

**Aggiornata:** 01/11/2026 (Europe/Rome)  
**Baseline:** codice GitHub v1.55; l'installazione effettiva sulla VPS va verificata separatamente.  
**Scopo:** riconoscere possibili tracce dei grandi operatori combinando posizionamento COT, sentiment retail, struttura del prezzo e — come nuovo filone — volumi e order flow *stimato*; valutare le ipotesi con dati osservabili, test fuori campione e controllo dei costi. Nessun rendimento o anticipo delle mosse istituzionali è garantito.

## Regole che valgono per ogni fase

- **Gratis prima:** riutilizzare cTrader Open API, SQLite privato e Oracle Always Free finché sostenibile. Prima di aumentare frequenza, storage o servizi verificare quote reali, RAM, disco, traffico e possibili costi; una quota non misurata è **N/D**, non zero.
- **Nessun dato inventato:** mantenere fonte, broker, strumento, UTC, ora di acquisizione, granularità e qualità; se il feed è assente/stantio mostrare N/D. Distinguiamo forex/CFD dai futures sottostanti.
- **Sicurezza:** lettura soltanto, nessun invio ordini, token e database in `private/`, niente segreti/dati tick privati nel repository pubblico, backup SQLite prima delle migrazioni e rollback testato.
- **Versioning:** ogni *rilascio applicativo* aumenta la versione e mostra versione più data/ora italiana **in alto su ogni pagina**, con aggiornamento cache PWA e test. La sola modifica di questa roadmap non è un rilascio e non cambia v1.55.
- **Rilasci delicati:** i file `scripts/`, `deploy/oracle/` e i workflow richiedono il percorso di installazione manuale controllata; l'autoupdater evita di applicarli automaticamente.

## P0 — Completare la base esistente (priorità immediata)

- [ ] **Quando riaprono i mercati:** verificare acquisizioni reali per tutti i mercati configurati, copertura M15/H1/H4, rotazione, ritardi e gap di sessione, distinguendo weekend e feed rotto.
- [ ] Verificare COT settimanale (prima disponibilità effettiva, mapping futures/strumenti, freschezza), sentiment Myfxbook e Capital, e qualità temporale di ogni sorgente.
- [ ] Proseguire la **validazione prospettica Squalincome**: timestamp di conoscenza reale, coorti non duplicate, esiti 1/4/24h, confronti con benchmark, costi ipotetici (spread, slippage) e intervalli di confidenza; niente probabilità spacciate per affidabili con pochi casi.
- [ ] Ultimare Centro di Controllo: contatori **outbound per provider** (richieste, errori, limiti) distinti dalle chiamate in ingresso alla VPS; integrità/ultimo backup, dati da verificare su OCI/Firestore/GitHub senza fingere accesso ai contatori billing.

## P1 — Volumi da cTrader: primo incremento minimo e gratuito

- [ ] Verificare nel payload reale di `ProtoOAGetTrendbarsRes` il campo `volume` e la sua semantica: **tick volume**, non lotti o contratti transati.
- [ ] Estendere `scripts/ctrader_feed.py` per conservare il volume delle M15 chiuse invece di scartarlo in `convert_trendbar()`, senza alterare OHLC e senza cambiare l'origine broker.
- [ ] Estendere schema/ingestione di `scripts/price_feed.py` e `scripts/price_store.py` (versionamento compatibile con dati storici senza volume): M15 e aggregazione dei volumi in H1/H4 solo da barre M15 contigue, mai su gap.
- [ ] Test di regressione: valori negativi/assenti, volumi pari a zero, broker mismatched, timezone, doppio inserimento, fine sessione/weekend, database già esistente. Mostrare volumi e qualità su una scheda pilota.

**Gate P1:** volume storico reale verificato per EURUSD e XAUUSD; nessuna perdita di candele e backup/rollback verificati; risorse entro quote gratuite.

## P2 — Delta Volume *stimato* e CVD pilota

- [ ] **Baseline su candele:** costruire una prima stima direzionale basata su OHLC + tick volume, chiaramente etichettata **proxy** (es. allocazione per posizione della chiusura nel range, con trattamento neutro dei doji). Non chiamarla flusso buy/sell reale.
- [ ] **Miglioria tick:** valutare recupero dello storico tick Bid/Ask autorizzato e/o sottoscrizione spot live, classificazione della direzione dei tick e aggregazione per M1/M5/M15; confrontare costo, limiti e qualità con baseline a candele. Tick Bid/Ask **non sono trade prints**; non possono identificare con certezza ordini aggressivi o volumi reali.
- [ ] Definire un `delta_proxy` riproducibile e un `CVD_proxy = somma(delta_proxy)`: reset per sessione, gestione buchi/disconnessioni, sessioni del broker, segno, scala e soglia minima di campionamento.
- [ ] Salvare nel SQLite **aggregati** minuto/15 minuti e lo stato del feed; conservare i tick grezzi solo per finestra breve configurabile, se indispensabili, senza creare carico 24/7 su tutti i 38 mercati.
- [ ] Dashboard nelle pagine EURUSD e XAUUSD: prezzo vs CVD proxy, delta per intervallo, freschezza, copertura, metodo utilizzato e disclaimer visibile. Confrontare graficamente i due proxy senza confonderli con order flow futures.

**Gate P2:** pilota funzionante e riproducibile su due strumenti con timestamp corretti; nessun falso CVD durante disconnessioni; costo/risorse monitorati. Estensione agli altri mercati solo se utile.

## P3 — Analisi dello squalo: confluenze, NON segnali automatici

- [ ] Studiare separatamente divergenze prezzo–CVD, rotture confermate/smentite, possibili assorbimenti, esaurimenti, Wyckoff e sweep di liquidità. Una divergenza da sola non dimostra assorbimento o intervento istituzionale.
- [ ] Collegare il nuovo fattore **senza doppio conteggio** con struttura prezzo M15/H1/H4, COT settimanale pubblicato, variazione sentiment retail e livelli/volatilità.
- [ ] Introdurre nel Radar Squali/Squalincome uno stato interpretabile: `CONFERMA`, `DIVERGENZA`, `NESSUN DATO` con spiegazione basata su osservazioni, invece di un'etichetta categorica “istituzionali long/short”.
- [ ] Misurare il **valore incrementale**: confronto out-of-sample Squalincome con/senza CVD, precisione, falsi segnali, expectancy e drawdown **netti dei costi ipotizzati**, su orari e strumenti non selezionati ex post.
- [ ] Solo dopo test utili, aggiungere notifiche private per eventi significativi con deduplica, limiti di frequenza e spiegazione del motivo.

**Gate P3:** il CVD migliora davvero un benchmark fuori campione con campioni adeguati; in caso contrario resta metrica descrittiva, non filtro operativo.

## P4 — Order flow più fedele (opzionale, non presumibilmente gratis)

- [ ] Valutare su **futures** relativi a oro, DAX, petrolio (e altri, in ordine di utilità) feed con scambi eseguiti, Bid/Ask aggressor tagging, volume e profondità, distinguendoli da CFD/spot.
- [ ] Verificare disponibilità, licenza, uso privato, ritardo, condizioni di ridistribuzione e costi effettivi del provider. Nessun abbonamento prima di una valutazione costo/beneficio.
- [ ] Se disponibile, costruire un CVD da **transazioni reali**, separato dal `CVD_proxy`, con identificazione di exchange e contratto; non chiamarlo misura diretta di tutte le operazioni istituzionali.
- [ ] Validare se aggiunge informazione concreta al modello REMURA prima dell'adozione.

## Sequenza e decisioni

1. Al prossimo mercato aperto **P0**: collaudo feed e validazione in corso; sono prerequisiti per non interpretare dati stantii.
2. In parallelo, progettazione/test offline di **P1**; prima release piccola: **tick volume M15** su due strumenti.
3. Dopo collaudo P1, **P2**: proxy CVD da candele, quindi confronto con feed tick, solo se sostenibile.
4. Se i dati sono affidabili, **P3**: aggiunta a Squalincome e analisi statistica prospettica.
5. **P4** soltanto se servono esecuzioni reali per una strategia che ha già mostrato potenziale e sappiamo valutarne i costi.

## Stato iniziale verificato nel codice (01/11/2026)

- `scripts/ctrader_feed.py`: preleva `ProtoOAGetTrendbarsReq` M15 e in `convert_trendbar()` restituisce OHLC, **non** il campo volume.
- `scripts/price_feed.py`: modello candela OHLC; `scripts/price_store.py`: archivia OHLC privati, senza delta o CVD.
- `V155-THREE-LEVEL-MONITOR.md`: i consumi misurati finora sono in ingresso alla VPS, **non** chiamate broker o fatturazione OCI.
- **Non implementato in questa modifica:** acquisizione volumi, streaming tick, CVD, nuove API e UI. Questa è soltanto la roadmap.

## Criterio di completamento di ogni step

Specifiche + fonte ufficiale + test unitari/integrazione + metrica di qualità + misure risorse/costo + backup/rollback + verifica reale su VPS + versione/data ora in ogni pagina **quando c'è un rilascio applicativo**. Documentare esplicitamente ciò che resta N/D.
