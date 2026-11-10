# REMURA NQ — Evidenza ATAS: screenshot 10 novembre 2026 (checkpoint 0.3)

> **AGGIORNAMENTO / RETTIFICA v0.5 — 10/11/2026:** il trader ha chiarito direttamente che i livelli vengono dai **picchi di Delta** e dal loro **sforzo/risultato**, osservando profili `Current Monthly`, `Previous Monthly`, `Week`, `Monthly`, soprattutto i `current`. Le interpretazioni precedenti sulle opzioni come origine dei sei livelli sono superate; PVP/VWAP rimangono possibili strumenti accessori, non conferma della formula delle zone. Si conserva sotto l'audit storico ma la priorita' e' documentata in [DELTA-EFFORT-RESULT-PROTOCOL.md](DELTA-EFFORT-RESULT-PROTOCOL.md).


**Fonte:** immagine ricevuta nel dialogo dall'utente dopo i livelli NQ del 10/11; screenshot grezzo non committato, e nessun livello Telegram privato ripubblicato.

## Leggibile nello screenshot
- Grafico ATAS per @NQZ6 (future Nasdaq, scadenza dicembre 2026), feed indicato: dxFeed.
- La barra superiore mostra **10R**: impostazione apparente di un grafico a range, non 10 minuti.
- Un profilo orizzontale storico (grigio/rosso) a sinistra dell'azione di prezzo e un profilo orizzontale (bianco/rosso) all'estremita' destra. Quest'ultimo e' compatibile con configurazioni Volume Profile / Bid e Ask di ATAS, **non** prova il tipo di profilo, segno, orizzonte o codifica colore.
- Etichetta visibile **CVD - Cumulative Volume Delta (Bars, True)** sul primo pannello basso; linea scende nella parte destra dell'immagine.
- Etichetta visibile **CVD pro(multi) / Multi Market Powers (Bars, True)** nell'ultimo pannello con tre curve di colori diversi. Le bande di dimensione dei trades (range minimo/massimo) non sono leggibili: **non** e' possibile associarle a istituzionali o retail.
- Due segmenti orizzontali gialli sul prezzo e bande/aree ombreggiate. Non possiamo identificarne la sorgente esatta: linee manuali, livelli VAH/VAL, VWAP, expected move, opzioni sono tutte ipotesi non confermate.
- Le quote dei segmenti gialli non coincidono necessariamente con le sei zone del gruppo ricevute il mattino e NON devono essere retroattivamente trattate come livelli pre-pubblicati.

## Riscontri documentali ATAS
- https://help.atas.net/it/support/solutions/articles/72000602305-volume-profile-tpo — profili possono usare Volume, Trades, Delta, Bid and Ask, Max Level POC, value area, colori personalizzabili.
- https://help.atas.net/it/support/solutions/articles/72000602434-cvd-pro-multi-multi-market-powers — indicatore confermato.
- https://atas.net/it/blog/glavnyie-preimuschestva-atas/ — CVD Pro multi confronta filtri di volume diversi, non identifica proprietari degli ordini.

## Interpretazione falsificabile
1. **Zone ex-ante** dal gruppo: origine ancora sconosciuta (OI, GEX, expected move, volume profile o griglia).
2. **Contesto in-session**: profili per prezzo e CVD filtrato; possibile supporto a decisioni di ingresso dopo un test delle zone.
3. **Non è uno screenshot di una catena opzioni**; non e' evidenza che le zone derivino da OI/GEX.
4. **No trigger ricostruibile**: immagini senza timestamp per ogni barra, raw tape Bid/Ask, impostazioni del profilo/filtri, storico e ordini/fill.

## Prossima prova non intrusiva
Richiedere SOLO schermata delle impostazioni dei due profili (Profile Type: Volume/Delta/Bid-Ask, periodi) e di **CVD pro (multi)** (range volumi per curva), e schermata che mostri il nome dell'indicatore che traccia i livelli gialli, senza account o dati personali. Confrontare le predizioni ex-ante, non ottimizzare soglie sul 10/11.

**Gate:** NO EDGE, NO LIVE, NO ORDINI, NO SCRAPING/ACQUISTI. Studio offline sul solo branch PR #101 DRAFT, non tocca PR #89, Track A, C, Oracle, collector, main o versione dell'app.

## 10/11/2026 — Integrazione dell'utente: PVP + VWAP con bande (checkpoint ricerca v0.4)

L'utente precisa che **le linee/zone gialle dovrebbero essere PVP** e **le bande celesti VWAP con bande**. Si tratta di testimonianza di seconda mano/probabile, non identificazione definitiva delle impostazioni ATAS. Aggiorna l'ipotesi del precedente paragrafo senza cancellare l'incertezza.

- **PVP** in alcune metodologie indica **Peak Volume Price**, ossia il prezzo modale per volume; coincide concettualmente con Volume POC per lo stesso periodo/criterio. In altre piattaforme PVP e' anche sigla di **Periodic Volume Profile**: non attribuire automaticamente una delle due accezioni al grafico ATAS senza nome e configurazione dell'indicatore. ATAS documenta esplicitamente POC e Value Area.
- **VWAP con bande**: prezzo medio ponderato dai volumi, spesso con deviazioni standard superiori/inferiori. Le aree celesti e la curva centrale sono compatibili con questa lettura. Periodo/ancoraggio (sessione, precedente giorno, swing) e moltiplicatori (1, 2, 3 sigma ecc.) sconosciuti. Il colore non dimostra l'indicatore.
- **Due linee gialle**: se PVP indica un singolo picco del profilo, due livelli possono riferirsi a periodi/ancoraggi diversi oppure a un altro indicatore. Non definire entrambe "il PVP" senza impostazioni.
- **Distinzione cruciale**: PVP/POC e VWAP/bande sono misure della distribuzione/prezzo-volume, mentre le sei zone pubblicate al mattino potrebbero essere calcolate separatamente da opzioni, volatilita', profili precedenti o livelli manuali. Il grafico non dimostra l'origine delle zone del mattino.
- **Protocollo sperimentale**: futuro replay offline con volume futures NQ genuino e cronologia *as-of*, VWAP da prezzi/volumi (trade-level se disponibili; OHLCV solo proxy), bande standardizzate ex ante, POC per periodo, confronto aggiuntivo con zone del mattino e CVD Multi. Segnalare se mancano trades-by-price; non costruire PVP vero da soli prezzi di chiusura M5.

Fonti verificate: https://atas.net/it/trading-indicators/ (VWAP e bande); https://help.atas.net/it/support/solutions/articles/72000602305-volume-profile-tpo (Volume POC); https://help.atas.net/it/support/solutions/articles/72000661101-ohlc-plus (POC, VWAP e livelli periodici).

**NESSUN codice produttivo, scheduler, richiesta API, deploy o modifica di main**. PR #101 rimane DRAFT.
