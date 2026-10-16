# REMURA v0.7 — Segui le tracce degli istituzionali

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

## Sentiment retail e grafico prezzi (v0.6)

**Pagina:** `asset.html?symbol=CADJPY&v=7` (vale anche per XAUUSD e gli altri simboli).

- Grafico a candele TradingView incorporato con pulsanti M1, M5, M15, M30, H1, H4, D1. L'intervallo si applica **solo al prezzo**, nel widget esterno.
- Riquadro Myfxbook Community Outlook: long%, short%, lotti long/short, numero posizioni e prezzi medi di apertura. Se il dato manca si vede N/D, mai valori inventati.
- Grafico dello storico long/short (lotti o posizioni), costruito soltanto da snapshot raccolti dopo l'attivazione. Campionamento orario e tempi reali delle osservazioni; non replica uno storico minuto-per-minuto Myfxbook.
- I grafici prezzo e sentiment sono **separati**; per ottenere assi temporali perfettamente sincronizzati in futuro servirà un feed di candele con accesso programmatico e diritto di utilizzo.
- Per gli strumenti non disponibili nella community Myfxbook, il sentiment resta N/D. Grafico TradingView e disponibilità di specifici ticker possono dipendere dal fornitore.

### Bande long/short v0.7
- **Frequenza richiesta:** 3 rilevazioni Community Outlook ogni ora (7, 27, 47 minuti UTC), 72 richieste nelle 24 ore. GitHub Actions può ritardare o saltare esecuzioni; anche Myfxbook può fornire valori non aggiornati tra due chiamate.
- **Grafico retail**: aree traslucide verde (lotti/posizioni long) e rossa (lotti/posizioni short); selettore Lotti / Posizioni; finestre 6 ore, 24 ore, 7 giorni, 30 giorni, Tutto; tocchi il grafico per leggere un'osservazione con data e valori.
- **Le finestre del sentiment non sono timeframe M1/M5.** Il periodo cambia solo lo zoom; frequenza dei dati reale circa 20 minuti, non 5 minuti. Per le candele rimane TradingView con M1–D1.
- **Interruzioni:** distanze superiori a 75 minuti tra due osservazioni non vengono connesse con bande inventate.
- **Archiviazione leggera:** ultimi 30 giorni massimo 2250 osservazioni per simbolo, salvati in data/myfxbook/history/SYMBOL.json per i 35 strumenti Remura. Il file legacy history.json contiene la primissima acquisizione ed è mantenuto come fallback.
- La prima acquisizione avvia solo un punto. Con almeno due osservazioni realmente disponibili appaiono bande e differenze tra ultimi campioni.
- Queste misure riguardano esposizione della community Myfxbook, non sono posizioni istituzionali.

### Attivazione sicura Myfxbook senza inserire credenziali nel sito
1. Possiedi o crea un account Myfxbook: https://www.myfxbook.com
2. Apri i [Secrets GitHub Actions del repository](https://github.com/mirkoworz/remura/settings/secrets/actions).
3. In **Repository secrets**, crea un secret `MYFXBOOK_EMAIL` contenente la tua email di login Myfxbook e un secondo secret `MYFXBOOK_PASSWORD` con la password.
4. Apri il workflow [REMURA Myfxbook sentiment](https://github.com/mirkoworz/remura/actions/workflows/myfxbook.yml) e scegli **Run workflow**, oppure attendi l'esecuzione programmata ogni 20 minuti (a 7, 27 e 47 minuti UTC; GitHub può ritardare).
5. Verifica nei log che il job sia riuscito e che il file `data/myfxbook/latest.json` contenga `status=ok`, data di rilevazione e simboli. Solo i dati aggregati vengono pubblicati; nessun secret/sessione nel repo.
6. Riapri la scheda: il pannello mostrerà i dati solo per i simboli restituiti da Myfxbook. Dopo una seconda raccolta compariranno le prime linee del grafico retail.

L'API ufficiale Myfxbook ha **limite gratuito 100 richieste Community Outlook al giorno**, usa sessioni legate all'IP e può modificare termini e disponibilità. Il workflow chiama login e logout nella stessa esecuzione, una lettura Community Outlook a ciclo. Non inviare password in chat o file pubblici. Controllare i termini Myfxbook per la ripubblicazione di aggregati su un sito pubblico.

**Importante:** lo storico non appare immediatamente solo aggiungendo le credenziali. Lo script inizializza il primo punto e accumula letture nel tempo.

## Prossimi sviluppi
Collegamento sentiment retail reale e sicuro, confronto con il prezzo, preferiti e alert esplicabili. Nessun rendimento garantito.

## Installazione iPhone
Apri [REMURA](https://mirkoworz.github.io/remura/) in Safari → Condividi → Aggiungi alla schermata Home.

## File principali
Home index.html, panoramiche catalogo.html, schede asset.html, scanner mercati.html, radar storico forex.html, menu nav.js / nav.css, cache shell sw.js.
