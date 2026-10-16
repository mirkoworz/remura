# REMURA v0.5 — Segui le tracce degli istituzionali

REMURA è una web app gratuita ottimizzata per iPhone, con radar COT ufficiali e percorsi per esplorare futures valutari, metalli e indici USA.

## Mappa del sito
- [Home](https://mirkoworz.github.io/remura/) — esposizione, variazioni, spinta e decelerazione.
- [Scanner completo](https://mirkoworz.github.io/remura/mercati.html?v=5) — movimenti maggiori, passaggi net long/short, accelerazioni e rallentamenti.
- [Forex](https://mirkoworz.github.io/remura/catalogo.html?categoria=forex&v=5) — 28 coppie Forex.
- [Radar Forex classico](https://mirkoworz.github.io/remura/forex.html?v=5) — il radar grafico originale.
- [Metalli](https://mirkoworz.github.io/remura/catalogo.html?categoria=metals&v=5) — Gold e Silver.
- [Indici](https://mirkoworz.github.io/remura/catalogo.html?categoria=indices&v=5) — S&P 500, Nasdaq 100, Dow, Russell 2000, DXY.
- [Scheda GOLD](https://mirkoworz.github.io/remura/asset.html?symbol=XAUUSD&v=5).
- [Scheda CADJPY](https://mirkoworz.github.io/remura/asset.html?symbol=CADJPY&v=5).

Menu hamburger con Home, Scanner e sottomenu apribili Forex → singole coppie, Metalli → Gold/Silver, Indici → 5 futures; ricerca integrata. Ogni strumento ha una scheda con URL proprio.

## Dati e fonti
- [CFTC Traders in Financial Futures Futures Only](https://publicreporting.cftc.gov/Commitments-of-Traders/TFF-Futures-Only/gpe5-46if): dataset gpe5-46if, Forex/indici, categorie Asset Manager e Leveraged Funds.
- [CFTC Disaggregated Futures Only](https://publicreporting.cftc.gov/Commitments-of-Traders/Disaggregated-Futures-Only/72hh-3qpy): dataset 72hh-3qpy, oro/argento, categorie Managed Money e Producer/Merchant.

I dati COT sono settimanali, NON in tempo reale. Le nuove schede mostrano N/D se i report mancano, senza inventare numeri. La vecchia pagina forex.html conserva la modalità DEMO ben etichettata in caso di mancata connessione.

## Come interpretare
- Netto % OI = (contratti long - short) / open interest × 100.
- Variazione settimanale: differenza in punti percentuali tra due rilevazioni.
- Più netto long non vuol dire che qualcuno abbia solo comprato: può dipendere anche dalla chiusura di short.
- Rallentamento = variazione dello stesso segno ma di ampiezza inferiore (nello scanner soglia 1,5 pp).
- Inversione netta = cambio del segno da netto positivo a netto negativo o viceversa; non equivale a un'inversione di prezzo.
- Cross Forex: differenza normalizzata tra due futures valutari contro USD. È un indicatore sintetico, non un COT diretto del cross.
- Categorie TFF e Disaggregated non sono intercambiabili; operatori commerciali possono coprire rischi.
- Schede: serie fino a 56 settimane, posizioni long/short, OI quando pertinente, variazioni, percentile relativo alla serie disponibile e sezione sentiment retail ancora non collegata.

## Prossimi sviluppi
Collegamento sentiment retail reale e sicuro, confronto con il prezzo, preferiti e alert esplicabili. Nessun rendimento garantito.

## Installazione iPhone
Apri [REMURA](https://mirkoworz.github.io/remura/) in Safari → Condividi → Aggiungi alla schermata Home.

## File principali
Home index.html, panoramiche catalogo.html, schede asset.html, scanner mercati.html, radar storico forex.html, menu nav.js / nav.css, cache shell sw.js.
