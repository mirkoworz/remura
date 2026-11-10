# REMURA Shark CVD — D0.4 (10/11/2026, Italia)

**USARE D0.4:** [remura_shark_cvd_fx_v04.pine](remura_shark_cvd_fx_v04.pine). D0.1/D0.2/D0.3 sono conservate solo come esperimenti precedenti.

L'errore mostrato sul tuo PC (`Invalid symbol: FXCM:EURUSD`) dipende dalla richiesta `FXCM:EURUSD`, che TradingView ha rifiutato. **D0.4 utilizza soltanto `FX:EURUSD`**, l'identificativo che il tuo indicatore D0.2 ha letto, associato alla dicitura **FXCM** dalla pagina ufficiale TradingView. Prezzo 5m e volume 1m vengono richiesti dalla stessa fonte `FX:EURUSD`. Fonte/provenienza vengono annotate senza fingere che il prefisso `FXCM:` sia disponibile.

1. Nel Pine Editor seleziona tutto il vecchio script e incolla il contenuto di D0.4.
2. Salva e aggiungi al grafico EURUSD 5 minuti, rimuovendo il pannello D0.3 precedente.
3. Leggi la tabella nel pannello CVD: deve mostrare `DATI: FX:EURUSD (TV: FXCM) 5m+1m` e `Minuti 1m ultima 5m chiusa: 5/5` quando il feed è completo. Se compare `DATI 1m INCOMPLETI` o `0/5`, invia screenshot **senza modificare le guardie**: è un problema di copertura, non di ticker.
4. Mantieni **Alert SOLO RICERCA** disattivato: nessun webhook, nessun invio a REMURA, nessuna operazione.

La D0.4 non è stata compilata su TradingView in questa chat. GitHub verifica soltanto logica di riferimento e contratti statici; eventuali errori runtime devono essere riportati con riga e testo. Il CVD usa volume spot disponibile e **non** il delta aggressore eseguito futures. Nessun acquisto, deploy VPS o nuova versione applicativa LIVE.

## Documentazione precedente (D0.3 / D0.2 storica)

# REMURA Shark CVD — Test D0.3 (10/11/2026 Italia)

**Usare il nuovo [remura_shark_cvd_fxcm_v03.pine](remura_shark_cvd_fxcm_v03.pine) — non D0.2.**

D0.2 ha mostrato sul PC `FX:EURUSD | TF=5` nonostante la testata `FXCM`. D0.3 risolve l'ambiguità leggendo **prezzi FXCM 5m + volumi FXCM 1m** tramite richieste a `FXCM:EURUSD` esplicite. Gli alias `FX:EURUSD` e `FXCM:EURUSD` sono ammessi *solo* come grafici EURUSD 5m; il grafico non fornisce prezzi al calcolo. Le candele visualizzate da `FX:EURUSD` potrebbero divergere da FXCM: giudicare i pivot soltanto sui prezzi FXCM richiesti, non a occhio sul grafico di un altro fornitore.

## Sostituzione sul PC

1. Aprire `FXCM:EURUSD` oppure l'EURUSD grafico già presente, sempre **5m**.
2. Nel **Pine Editor**, sostituire tutto il vecchio script D0.2 con il contenuto **integrale** di `remura_shark_cvd_fxcm_v03.pine`, salvare e aggiungere/aggiornare l'indicatore. Rimuovere i pannelli vecchi D0.1/D0.2 per non confondere diagnostiche.
3. Nel pannello D0.3 cercare `DATI CALCOLATI: FXCM:EURUSD 5m+1m`. La riga `Grafico: FX:EURUSD | TF=5` non è più motivo automatico per bloccare **il calcolo FXCM**.
4. Se compare `DATI 1m INCOMPLETI` o il pannello è arancione, **non eliminare il controllo**. Mandare screenshot della tabella/pannello: il modello richiede i 5 minuti FXCM esatti per ciascuna candela 5m. Potrebbe non avere lo storico sufficiente.
5. Lasciare disattivati gli **Alert SOLO RICERCA**. Il prototipo non invia dati a REMURA cloud e non genera ingressi, SL, TP o ordini.

**Verifica indispensabile:** D0.3 NON è stato ancora compilato/testato nel runtime TradingView. Test GitHub offline non confermano che i dati richiesti siano presenti o che l'indicatore produca una linea. Se Pine dà errore di compilazione, inviare messaggio e riga esatta. La versione REMURA applicativa LIVE è invariata, nessun webhook e nessun costo aggiuntivo.

## Documentazione precedente (D0.2 storico)

## Uso su TradingView

1. Accedi con il tuo account Premium dal **browser con Pine Editor** (consigliato desktop; l'app iPhone può non esporre l'editor Pine). Apri `FXCM:EURUSD`, grafico **5m**.
2. Apri **Pine Editor** e crea un nuovo indicatore, sostituisci il codice con il contenuto integrale del file `.pine`. Salva con nome `REMURA Shark CVD D0.2` e aggiungi al grafico. **Importante:** eliminare dal grafico la vecchia versione D0.1 che mostra RE10142, dopo aver aggiunto D0.2; salvare il codice aggiornato NON aggiorna automaticamente un indicatore già compilato.
3. D0.1 ha compilato sul tuo TradingView, ma si è fermato a bar 0 con errore `RE10142` su un controllo troppo restrittivo (la vera causa dell'ineguaglianza non era visibile). D0.2 sostituisce quel blocco con un messaggio diagnostico **in alto nel pannello REMURA CVD**: `Letto: FXCM:EURUSD | TF=5` è l'esito atteso. Fai screenshot del pannello e dell'eventuale errore; il runtime D0.2 NON è ancora verificato e i test Python non equivalgono alla compilazione Pine.
4. Mantieni **disattivata** l'opzione `Abilita alert di RICERCA`. Il Pine non genera ordini né invia dati a REMURA finché non configuri volontariamente un alert.
5. Un eventuale pannello vuoto/arancione significa `DATI INCOMPLETI / NO SIGNAL`, non prova di assenza di divergenza. Il codice richiede esattamente cinque barre da 1m per ogni barra da 5m e invalida il resto della giornata se manca anche una sola barra.

## Cosa misura

- Volume delta **stimato**: la direzione delle barre FXCM da 1 minuto polarizza il volume disponibile e crea un cumulato che si azzera per ogni nuovo giorno TradingView.
- Due pivot di **prezzo** confermati; confronto del CVD agli stessi istanti; nessun look-ahead nei segnali che appaiono sulla barra di conferma.
- Non è il vero volume aggressore dei futures e non può dire quale istituzionale ha comprato o venduto.
- Non duplica il vecchio proxy cTrader (CLV×volume): fonte, metodo, unità e timeframe devono rimanere diversi.
- I dati storici/ricalcolati e realtime possono differire per limiti e correzioni del feed. Confermare su TradingView prima di ogni analisi scientifica.

## Alert e collegamento futuro

Se, dopo la prova e la verifica di qualità, decideremo di abilitare gli alert **solo per ricerca**: la casella Pine va attivata e l'utente deve creare esplicitamente un alert TradingView su **Any alert() function call**. Il messaggio JSON contiene identificativo evento deterministico, origine, algoritmo, tempi dei pivot, rilevamento e numeri CVD/prezzo. Un alert storico non viene inviato retroattivamente.

**Per ora NON inserire URL webhook**, non esporre la VPS/Tailscale, non incorporare token o dati privati nel codice Pine e non copiare chiavi in GitHub. TradingView usa porte 80/443, richiede 2FA per i webhook e non garantisce consegna; in seguito progetteremo un ricevitore HTTPS minimamente esposto con deduplica e controlli quota.

## Test locali offline

`python -m unittest discover -s tests -p 'test_track_d_tv_cvd_reference.py' -v`

Questi test **non compilano Pine**: esercitano un modello Python causale e controlli statici minimi. La compilazione TradingView, la parità con il CVD nativo e la prima vera consegna JSON richiedono verifiche distinte.

## Gate e costi

Nessuna modifica alla web app REMURA, al backend, a Oracle o al feed cTrader. Nessun acquisto futures. Premium è già un abbonamento esistente; le quote script/alert/1m vanno osservate. La versione applicativa visibile su tutte le pagine REMURA rimane invariata fino a un rilascio LIVE coordinato.

## Diagnostica D0.2

- Testata fonte/timeframe corretti: `REMURA D0.2 | FXCM 5m OK` e riga `Letto: FXCM:EURUSD | TF=5` (confronto normalizzato con `ticker.standard`).
- Fonte/timeframe diversi: `SORGENTE/TIMEFRAME ERRATO` con identificativi effettivi; nessun CVD, divergenza o alert di ricerca viene generato per sbaglio. **Manda uno screenshot di quella riga**, non cambiare arbitrariamente il codice per superare il gate.
- Fonte corretta ma pannello vuoto/arancione: possibile incompletezza 1m, gap 5m o storico intrabar troncato; il fail-closed è voluto per impedire segnali inesatti.
- La patch è solo sul ramo D, PR #100 ancora DRAFT, senza deploy e senza costi aggiuntivi.
