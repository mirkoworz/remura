# REMURA D0.8 — Esperimento PREZZO vs CVD (10/11/2026)

**Nuovo script Pine:** [remura_shark_cvd_fx_v08.pine](remura_shark_cvd_fx_v08.pine) · **Analizzatore gratuito CSV:** [compare_d08_baseline.py](compare_d08_baseline.py) · [Roadmap D](../../ROADMAP-D-TRADINGVIEW-CVD.md).

**Scopo:** stabilire se l'aggiunta del CVD **seleziona meglio** le configurazioni rispetto agli stessi pivot di prezzo senza CVD, NON attribuire i volumi agli istituzionali né generare trade. Il CVD filtrato è un SOTTOINSIEME degli eventi prezzo. Non trattare le due serie come campioni indipendenti.

## Procedura iniziale sul PC

1. Apri TradingView, `EURUSD` fornitore FXCM: Pine lo identifica come **`FX:EURUSD`**. Mantieni timeframe **5m**.
2. Nel Pine Editor crea un indicatore nuovo con il contenuto **integrale** del file `remura_shark_cvd_fx_v08.pine`. Salva `REMURA D0.8`, aggiungi al grafico e rimuovi il pannello D0.7 per evitare confusioni. **D0.8 non è stata ancora compilata/provata nel runtime TradingView**; i check GitHub sono offline.
3. Controlla nella tabella `D0.8 | BASELINE vs CVD (NO TRADE)`, `Ultimi intrabar 1m: 5/5 | OK`, `Contesto ultima 5m CHIUSA: CONTINUO` e `Oggi: PREZZO=X | con CVD=Y`. Se la 5m è ancora aperta, la tabella legge l'ultima candela chiusa.
4. I simboli `ST+`/`ST-` continuano a mostrare le sole divergenze CVD. La nuova baseline di PREZZO è **registrata nel Data Window**, senza moltiplicare i marcatori visivi: `BASELINE_PREZZO_RIALZISTA`, `BASELINE_PREZZO_RIBASSISTA`, `PREZZO_SENZA_CVD_RIALZISTA`, `PREZZO_SENZA_CVD_RIBASSISTA`; sono preservati `EVENTO_STUDIO_RIALZISTA` e `EVENTO_STUDIO_RIBASSISTA`.
5. Invia uno screenshot del grafico e della diagnostica D0.8. Annotiamo data/ora reale italiana della prima installazione: gli eventi precedenti sono solo ricalcoli storici, **non** osservazioni prospettiche.
6. Dopo conferma del funzionamento esporta `Esporta dati grafico...` in CSV, mantenendo le due serie di eventi. Salva privatamente l'originale con data/ora di esportazione; non pubblicare dati TradingView nel repository. Per un'analisi offline:
   `python experiments/tradingview/compare_d08_baseline.py "FX_EURUSD, 5.csv"`

## Protocollo congelato

Pivot 2/2, distanza 3–72 barre, 5 tick prezzo, warmup 12 barre 5m, soglia differenza CVD 10, FX:EURUSD 5m, dati 1m completi e continuità obbligatoria, eventi solo alla chiusura della barra di conferma. I due bracci condividono qualità e finestre osservabili: il solo elemento diverso è il **filtro CVD**.

Lo script di analisi riporta gruppi prezzo totale, prezzo confermato dal CVD e prezzo senza conferma CVD, outcome direzionali a 1/4/24 ore, eventi non osservabili e sovrapposizioni. Le metriche sono **variazioni del prezzo, non profitti netti**: nessuno spread/slippage simulato e nessun risultato di vantaggio statistico sinora dimostrato. La prossima validazione PROSPETTICA inizia soltanto dopo l'attivazione manuale D0.8 documentata; evitare selezione retroattiva dell'inizio.

**Sicurezza e costo:** niente Pine `alert()`, niente webhook/endpoint, niente ordini o VPS, nessun cambio versione delle pagine REMURA LIVE. Premium TradingView già in uso, costo aggiuntivo previsto per laboratorio **0 €**, limiti di intrabar e licenze sempre validi.

## Archivio D0.1–D0.7.1

# REMURA Shark CVD — TEST D0.7 · 10 novembre 2026 (Filone D)

**Codice nuovo da provare:** [remura_shark_cvd_fx_v07.pine](remura_shark_cvd_fx_v07.pine) · [Roadmap D](../../ROADMAP-D-TRADINGVIEW-CVD.md)

**Perché questa revisione:** nel CSV D0.6 (7.388 candele) il delta era identico a TradingView su 4.667/4.667 candele complete precedute da una completa contigua. Le 5 differenze osservate tra tutte le 4.702 candele complete arrivavano subito dopo dati 1m incompleti. D0.7 conserva il valore grezzo, ma mette una bandierina di **continuità precedente**: il primo 5m dopo un buco NON può confermare una divergenza.

## Prova TradingView dal PC (nessun nuovo acquisto)

1. Sul grafico TradingView **Euro/Dollaro FXCM** identificato da Pine come `FX:EURUSD`, sempre **5 minuti**, apri Pine Editor, incolla il **file intero D0.7**, salva e aggiungilo al grafico. Puoi lasciare l'indicatore CVD nativo con ancoraggio `1 giorno`; rimuovi il precedente REMURA D0.6 dal pannello per evitare doppioni.
2. Leggi la tabella del nuovo **REMURA CVD D0.7**. Cerca la riga `Ultimi intrabar 1m: 5/5 | OK`, il campo `Contesto precedente: CONTINUO` e `Segmento #... | barre ... | warmup 12`.
3. Nel **Data Window** sono presenti `QUALITA_5M_COMPLETA` (0/1), `CONTINUITA_PRECEDENTE_5M` (0/1/NA), `DELTA_5M_GREZZO_COMPLETO` e `DELTA_5M_CONTINUO_VERIFICATO`. Quando `QUALITA=1` ma `CONTINUITA=0`, il delta grezzo rimane visibile, quello affidabile rimane vuoto: comportamento corretto e deliberato.
4. La curva **arancione** è soltanto il cumulato ricostruito di un segmento, mai una giornata completa se ci sono buchi. I simboli `ST+` e `ST-` sono **ipotesi di divergenza per ricerca**, riconosciute a pivot prezzo confermato (non retrodatate), solo dopo un warmup preimpostato di 12 barre consecutive. Non costituiscono suggerimenti di trading.
5. Mandami una foto della tabella e del grafico o, se compare un errore, il messaggio e la riga Pine. La compilazione/esecuzione D0.7 su TradingView **NON è ancora verificata**. I test GitHub Actions sono test offline, non compilano Pine.

**Sicurezza:** D0.7 non invia alert, non ha webhook, non invia alcun dato a REMURA cloud, non esegue ordini, non modifica l'app LIVE e non utilizza dati futures real-time. Lo scopo è preparare un dataset prospettico rigoroso per Shark Science, non stimare profitti su quattro marcatori storici.

## Archivio versioni precedenti D0.1–D0.6

# REMURA Shark CVD — D0.6 | Test di parità numerica (10/11/2026, Italia)

**Codice da provare:** [remura_shark_cvd_fx_v06.pine](remura_shark_cvd_fx_v06.pine) · **Roadmap:** [ROADMAP-D](../../ROADMAP-D-TRADINGVIEW-CVD.md)

## Obiettivo

Confrontare il **delta di una singola candela 5m** calcolato da REMURA con quello dell'indicatore `CVD` nativo TradingView. **Non confrontare i valori cumulati giornalieri direttamente**, perché i reset della nostra curva arancione differiscono. Formula nativa verificata nella documentazione TradingView: `Delta nativo della candela = Chiusura CVD - Apertura CVD`.

## Procedura sul PC

1. Sul grafico EURUSD FXCM (`FX:EURUSD` in Pine), 5 minuti, lascia il CVD nativo con **Periodo di riferimento = 1 giorno**. Non scegliere `1 tick`: quello è un altro periodo di ancoraggio, NON un aumento di precisione intrabar.
2. In Pine Editor copia integralmente il nuovo file D0.6, salva e aggiungi al grafico, rimuovendo il pannello vecchio D0.5. **Nessun webhook, gli alert restano disattivati.**
3. Nel pannello D0.6 vedrai i medesimi CVD verde (giorno integro) o arancione (segmento parziale, **NO SIGNAL**). La tabella mostra due righe nuove: `Ultimo DELTA 5M verificato` e `Candela chiusa` in ora italiana; servono solo per confermare che il calcolo gira.
4. Apri la **Finestra dati** (Data Window) di TradingView. Posiziona il cursore su **una candela 5m già chiusa**, non l'ultima in formazione. Per lo stesso timestamp, sotto REMURA leggi `DELTA 5M REMURA verificato` e `QUALITA 5M (1 valida / 0 incompleta)`; sotto CVD nativo leggi i valori **Open** e **Close** della candela CVD.
5. Ripeti su 3–5 candele chiuse preferibilmente dello stesso giorno; mandami screenshot della Finestra dati e orario cursore. Useremo `Close CVD - Open CVD` per confrontarlo al valore REMURA. Se qualità è 0 o N/D, **non** comparare: registra la candela come incompleta.

Il Pine D0.6 **non è ancora compilato nel runtime TradingView**. GitHub Actions testa soltanto le proprietà statiche del codice e un modello di riferimento, non l'API live. Una differenza numerica potrebbe dipendere dal metodo di classificazione/tie-break, dall'accesso allo storico 1m, dal modello del provider o dal CVD nativo tick-based (da verificare separatamente). Nessuno di questi controlli dimostra un vantaggio statistico. Non generare ingressi, SL/TP, notifiche né ordini.

## Archivio esperimenti precedenti (D0.1–D0.5)

# REMURA Shark CVD — D0.5 (10/11/2026, Italia) — TEST DIAGNOSTICO

**Nuovo codice:** [remura_shark_cvd_fx_v05.pine](remura_shark_cvd_fx_v05.pine)

La **D0.4 compilava** dopo che l'utente ha aggiunto la parentesi mancante nella chiamata `table.cell`, ma la curva CVD è rimasta vuota. La causa non è stata ancora osservata: può dipendere dall'assenza di qualche barra 1m, da uno storico intrabar limitato, da un gap o dalla giornata incompleta. Non dedurre automaticamente che FXCM non trasmetta volume.

## Prova senza costi sul PC

1. Aprire EURUSD 5m esistente, TradingView lo identifica in Pine con `FX:EURUSD` (etichetta FXCM).
2. Sostituire l'intero Pine D0.4 con [D0.5](remura_shark_cvd_fx_v05.pine), salvare e rimuovere i vecchi pannelli D0.1–D0.4; aggiungere il nuovo indicatore.
3. Guardare il riquadro diagnostico in alto sul pannello `REMURA CVD D0.5`. Copiare/fotografare **stato**, **Barre 1m ultima 5m chiusa: x/5**, **Ultimo controllo** e **Barre parziali consecutive**.
4. Interpretazione: **linea verde** = cumulato giornaliero completo secondo gate conservativo; **linea arancione** = solo tratto di 5m consecutive valide, ricominciato da zero dopo gap, **NO SIGNAL**; **nessuna linea** = non si è ancora formato un tratto sufficiente o manca un dato. Se `0/5`, indagheremo lo storico 1m.
5. Lasciare l'opzione `Alert SOLO RICERCA` **disattivata**. Nessun webhook, ordine, SL/TP o collegamento cloud è abilitato.

**D0.5 è da compilare nel runtime TradingView.** I test GitHub possono trovare parentesi mancanti e controllare il contratto del codice, ma non confermano né la compilazione Pine né la disponibilità dei dati. Il CVD rimane un **proxy di volume FX spot**, non volumi di contratti futures eseguiti. Nessuna nuova spesa, deploy o modifica alle nove pagine REMURA.

## Versioni precedenti (archivio, non usare nel nuovo test)

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
