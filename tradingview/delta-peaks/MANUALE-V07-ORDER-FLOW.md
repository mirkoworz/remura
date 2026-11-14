# REMURA ALL-IN-ONE Premium LAB v0.7 — Manuale operativo di studio
**Aggiornamento: 11/11/2026, ore 13:55 CET**  
**Codice Pine:** [REMURA-ALL-IN-ONE-Premium-v0.7.pine](REMURA-ALL-IN-ONE-Premium-v0.7.pine)

> Ricerca su TradingView Premium, `FXCM:EURUSD` M5. Sono stime e volumi classificati dal feed, **non** contratti CME o ordini attribuibili a istituzioni. Non sono segnali di acquisto/vendita validati.

## Il pannello COMPLETO: ogni riga
| Voce | Calcolo della versione v0.7 | Lettura pratica |
| --- | --- | --- |
| STATO | LIVE/PROVVISORIO se barra corrente non confermata | Non utilizzare il valore provvisorio per un risultato storico. |
| DELTA intrabar | `TradingView/ta/14 requestVolumeDelta("1", timeframe.period)`, valore finale della barra M5 | Pressione stimata + o -, aggregata usando 1m. |
| DELTA footprint | `request.footprint(10 tick/riga, VA70, imbalance300%)` | Volume classificato dal Footprint. Può differire dal delta intrabar. |
| BUY / SELL stimati | `fp.buy_volume()` e `fp.sell_volume()` | Volumi classificati per direzione dei movimenti intrabar, NON ordini aggressori CME verificati. |
| DELTA / VOL % | `100 * fp.delta() / fp.total_volume()` | Squilibrio della barra in % del volume. |
| SFORZO | `abs(deltaBar) / SMA(abs(deltaBar[1]), 30)` | 1x usuale; 1.5x per candidare livelli DAY; 3.5x per picchi ER; >=5x fascia intensità massima. |
| RISULTATO ATR | `sign(deltaBar)*(close-open)/ATR(14)` | Positivo: corpo coerente col segno delta. Negativo: corpo in direzione opposta. |
| EFFICIENZA ER | `RISULTATO / SFORZO` | Piccola/negativa = tanto sforzo relativo e poco progresso/contropressione, non prova di assorbimento. |
| ANOMALIA | Preview picco se SFORZO>=3.5; ER se EFFICIENZA<=0.07 e distanza dai picchi rispettata | Indicatore euristico, non verdetto operativo. |
| INTENSITA' | fasce <1, 1–<2, 2–<3.5, 3.5–<5, >=5 | Rapporti 1/5...5/5. Non probabilità e non percentuale ordini. |
| IMB BUY / SELL | Numero di righe con `row.has_buy_imbalance()` / `has_sell_imbalance()` | Numero di fasce in squilibrio; default 300% diagonale. Non è volume e non misura diretta di iceberg. |
| POC footprint | media dei limiti della riga `fp.poc()` | Fascia col volume totale maggiore **della candela**, non POC del giorno. |
| VAH / VAL | Limiti superiori/inferiori della Value Area del 70% **della candela** | Osserva accettazione/rifiuto attorno all'area, con esempi sia positivi sia negativi. |
| WEEK / CURRENT / PREVIOUS MONTH | Singola candela col massimo `abs(deltaBar)` nel periodo disponibile, linea a `hl2` | NON delta cumulativo del periodo e NON livelli di esecuzioni verificate. |
| DAY1 / DAY2 / DAY3 | Top 3 `abs(deltaBar)` del giorno, fra le barre chiuse con SFORZO>=1.5. Linee a HL2 (o centro POC della stessa candela se selezionato) | Classifica dinamica: possono cambiare rango o essere rimpiazzate quando arriva un picco più forte. |
| PREVIOUS DAY | Massimo DAY1 della giornata precedente visibile nello storico caricato | Livello grigio puntinato, non storico per tutte le giornate. |
| RETEST DAY | Conta primo attraversamento High–Low di una candela **successiva** sul livello, dopo una barra di assenza di contatto | RT = contatto, non conferma di inversione. I conteggi possono cambiare quando i livelli sono rimpiazzati. |
| EVENTO #1/#2/#3 | Ultimi 3 **picchi** confermati, non ultimi 3 retest | Ora di apertura candela Italia, tipo D+/D-/ER+/ER-, SFORZO x. Registro locale non persistente. |

## Comportamento dell'indicatore
- **Barra in formazione**: Delta, Footprint, Sforzo, Efficienza e ANOMALIA possono cambiare. Le linee DAY, WEEK/MONTH e segnali si confermano alla chiusura.
- **Fine barra**: l'eventuale picco ER viene disegnato se sono rispettate le soglie; i tre livelli DAY possono essere riordinati; il retest usa solo barre confermate. Una candela che crea un livello **non viene contata come retest del proprio livello**.
- **Fine giornata**: nuovo giorno TradingView `timeframe.change("1D")`; i DAY vengono azzerati e DAY1 precedente può diventare linea PREVIOUS DAY. L'ora della seduta non coincide necessariamente con la mezzanotte italiana.
- **Cambio impostazioni/timeframe/riapertura**: lo script si ricalcola sullo storico disponibile. Livelli/Footprint possono cambiare con la profondità/granularità dei dati. Non considerare un livello visto retrospettivamente come se fosse già noto ore prima.
- Il CVD di sessione delle immagini proviene dal **tipo grafico Footprint volume di TradingView** o dagli altri studi: v0.7 non lo usa nei suoi segnali ER.

## Come studiare MANUALMENTE EURUSD M5
1. Annota prima: data/ora Italia, simbolo `FXCM:EURUSD`, timeframe M5, versione v0.7, impostazioni (DAY=1.5, ER=3.5, Efficienza<=0.07, gap=6, Footprint 10 tick/riga/imbalance 300%).
2. All'istante di nascita della linea DAY: registra ora **della candela confermata**, prezzo livello, segno delta, SFORZO, EFFICIENZA, POC, IMB Buy/Sell. I tre livelli DAY sono **top 3 assoluti**, non necessariamente uno BUY e uno SELL.
3. Osserva il **primo ritorno** sul livello: il prezzo arriva da sopra o da sotto? La candela chiude oltre il livello oppure ritorna dalla parte di provenienza? Il POC si sposta oltre? Il delta è efficace o contrario? Gli sbilanciamenti confermano o contraddicono il movimento?
4. Classifica SOLO A POSTERIORI il comportamento come `RIFIUTO`, `ROTTURA/ACCETTAZIONE`, `INDEFINITO`, con regole oggettive da fissare prima del test sistematico.
5. Registra tutti i retest (anche fallimenti) e le reazioni **15 / 30 / 60 minuti** successive, idealmente in ATR, insieme al contesto di sessione/notizie.
6. Non usare ER+ come SELL o ER- come BUY per definizione. Un delta elevato senza movimento può precedere sia inversione sia consolidamento/continuazione.

## Esempio IPOTETICO di scheda
| Campo | Esempio fittizio |
| --- | --- |
| Evento | `DAY1_RETEST` |
| Rilevato alle | 11:15 Italia, candela M5 chiusa |
| Prezzo livello / chiusura | 1.11500 / 1.11490 |
| Provenienza | dal basso |
| Delta intrabar / SFORZO | +2400 / 4.8x |
| ER / efficienza | ER+ / 0.042 |
| Footprint Delta / imbalance | +250 / BUY 3, SELL 1 |
| Esito 15/30/60 min | **DA COMPILARE SOLO DOPO** |
| Interpretazione | Segnale di attenzione, **non ingresso automatico** |

## Limitazioni critiche
La classificazione Buy/Sell del Footprint segue la direzione dei movimenti intrabar e può variare tra storico e reale. Il grafico Footprint nativo disegna le celle a prezzi; il Pine v0.7 NON disegna quelle celle. `PREVIOUS MONTH` e DAY precedenti dipendono dai dati disponibili. Le linee a HL2 sono rappresentative della barra picco, non prezzi di massimo delta al singolo livello. Nessuna probabilità o statistica dimostrata ancora.
