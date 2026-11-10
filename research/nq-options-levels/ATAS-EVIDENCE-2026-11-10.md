# REMURA NQ — Evidenza ATAS: screenshot 10 novembre 2026 (checkpoint 0.3)

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
