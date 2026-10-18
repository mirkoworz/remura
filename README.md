# REMURA v0.9 — Segui le tracce degli istituzionali

## REMURA v1.3 — due soli sentiment sulle 35 schede

**Stato: modifica di sviluppo, nel ramo feature/capital-demo-sentiment-v12.
Non pubblicata su main/GitHub Pages.**

Nelle pagine asset.html di Forex, metalli e indici le fonti retail si riducono a
due sole fonti indipendenti:
- **Myfxbook Community Outlook**: numeri da file già archiviati in
  data/myfxbook/latest.json e data/myfxbook/history/SYMBOL.json, con fallback
  automatico al server /private-api/retail/ quando esiste. Percentuali del
  volume long/short, lotti, conteggi di posizioni, prezzi medi e bande storiche
  in 6h, 24h, 7g, 30g o tutto. Il sito NON effettua nuove API Myfxbook:
  interroga soltanto file dello stesso sito e non raddoppia le raccolte.
- **Capital.com Demo**: percentuali long/short e storico degli effettivi
  campioni dei clienti Capital.com, per mercati realmente confermati.
  L'app privata legge /private-api/capital/latest.json e
  /private-api/capital/history/SYMBOL.json. Il sito pubblico segnala N/D:
  non interroga GitHub privato dal browser, non trasferisce segreti e non
  pubblica i dataset Capital.com.

IG, Dukascopy, FX Blue, OANDA, Forex Factory e FXCM sono stati tolti dalle
schede dei singoli mercati e dalla pagina di descrizione delle fonti.
I vecchi backend non vengono richiamati: non modificano la prop o il Guardiano.

**Confronto:** non calcolare medie fra lotti e percentuali delle posizioni.
Eventuali divergenze sono fra DUE campioni retail, non la prova che gli
istituzionali occupino l'altro lato. Il COT rimane settimanale. Se manca una
fonte, il confronto resta N/D. I grafici non ricostruiscono punti non raccolti.

**Test:** node --test tests/sentiment.test.js; il controllo è integrato
nel workflow GitHub price-checks.yml. Nessuna credenziale è richiesta.


## Novità v0.9 — Interprete COT per tutti i 35 mercati
Le **28 schede Forex**, le **2 schede metalli** e le **5 schede indici** condividono il nuovo pannello di analisi in `asset.html`: trend netto % open interest, variazione della settimana e delle 4 precedenti, persistenza della spinta, differenze fra le categorie e testo interpretativo in italiano.

- Il pannello analizza realmente il dataset CFTC già acquisito da `asset.html`; non chiama servizi generativi e non inventa prezzi, percentuali di successo o ordini.
- **Forex:** usa il differenziale dei due futures valutari normalizzati; USD=0 soltanto come riferimento. Nei grafici dei contratti si visualizza una valuta alla volta, mai una somma sintetica di contratti non omogenei.
- **Metalli:** Managed Money è la categoria speculativa principale; Producer / Merchant sono spesso operatori in copertura e non vengono interpretati come avversari direzionali automatici.
- **Indici:** analisi delle categorie TFF sul future relativo, separato dai prezzi CFD.
- **Contratti verificabili:** per ogni categoria e future sono disponibili grafici settimanali separati di long, short e open interest, con periodi di 13, 26 e 52 settimane e differenze dal report precedente.
- **Retail Myfxbook:** il modulo esistente inoltra al pannello snapshot e storico già disponibili; la lettura contrarian è soltanto contestuale, non equivale a conoscere il lato istituzionale delle posizioni retail. Campioni insufficienti, feed vecchi o assenti sono esclusi.
- **Prezzi:** TradingView resta consultabile nella pagina, ma il suo widget non fornisce candele OHLC utilizzabili dal motore. Nessuna conferma automatica H4/H1, ingresso operativo o analisi tecnica del prezzo viene dichiarata finché non sarà integrato un feed programmatico.
- **Sicurezza delle interpretazioni:** COT datato oltre 14 giorni viene marcato; osservazioni insufficienti producono N/D. Nessun motore d'ordine e nessuna credenziale esposta.
- **Test:** `node --test tests/insights.test.js` con controllo di sintassi e wiring nel workflow `.github/workflows/insights-checks.yml`.

Il pannello compare automaticamente in `asset.html?symbol=EURUSD`, `asset.html?symbol=XAUUSD`, `asset.html?symbol=US500` e tutti gli altri simboli definiti in `nav.js`. Per attivare analisi automatica **del prezzo** serve una fonte OHLC legalmente utilizzabile (in valutazione MetaApi), poi un backtest con timestamp di pubblicazione COT realistici.


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

## Confronto multi-fonte sentiment (v0.8)
- [Indice delle fonti](https://mirkoworz.github.io/remura/fonti.html?v=8) — 7 provider con stato d'integrazione e differenze tra metriche.
- [Scheda CADJPY](https://mirkoworz.github.io/remura/asset.html?symbol=CADJPY&v=8) — nuovo modulo **Confronto sentiment multi-fonte** subito sotto la sezione prezzo/Myfxbook.
- **Myfxbook**: unica fonte retail con numeri caricati automaticamente in Remura al momento. Il modulo distingue la quota del volume in lotti dalla quota delle posizioni; dataset `data/myfxbook/latest.json`.
- **Dukascopy SWFX**: widget storico ufficiale incorporabile su coppie Forex; l'utente attiva manualmente il suo caricamento. Il caricamento effettivo nel browser e la copertura del simbolo devono essere verificati su Safari. I dati restano nel widget del provider e non vengono copiati nelle nostre analisi automatiche.
- **IG Client Sentiment**: API ufficiale esistente ma non autenticata in Remura, link alla pagina di mercato. Richiede verifiche su chiavi e licenza.
- **FX Blue**: conti reali net long/short, collegamento esterno; nessuna API di importazione attiva.
- **OANDA Position Book**: livelli di prezzo degli ordini/posizioni aperte su mercati selezionati; link esterno.
- **Forex Factory**: trader e lotti dei conti della community; link esterno alla sezione posizioni.
- **FXCM SSI**: feed professionale disponibile commercialmente; non importato in Remura.

**Non presentare come "7 fonti live"**: solo Myfxbook è numerica automatica. Widget esterno e link non sono assimilabili a feed acquisiti. Non creiamo una media/consenso artificiale fra lotti, posizioni, conti, transazioni o livelli di prezzo. Tutti i link ai provider sono ufficiali/verificati; la ripubblicazione di dati di terzi oltre i widget autorizzati è subordinata ai loro termini.

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

**Pagina:** `asset.html?symbol=CADJPY&v=8` (vale anche per XAUUSD e gli altri simboli).

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
