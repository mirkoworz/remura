# REMURA — ATAS: cartella formativa condivisa, primo esame visivo
**Checkpoint ricerca v0.6 — 10 novembre 2026** · SOLO OFFLINE · PR #101 DRAFT.

## Acquisizione e privacy
- Il proprietario del progetto ha condiviso in chat l'accesso a una cartella Google Drive privata, e il connettore ha elencato **12 video**.
- I video includono spiegazioni tematiche su rapporto sforzo/risultato, CVD, Delta Profile, VWAP, ciclicità, renko/range, stacked imbalance e gestione del trade.
- **Non** committare video, screenshot, trascrizioni, Google Drive ID o link diretti: i diritti di redistribuzione non sono stabiliti. I file rimangono nel contesto privato della conversazione.
- Primo campionamento visuale a intervalli di **tre video** scelti per pertinenza (due su profili Delta/VWAP e un breve trade recap CVD Pro). Non equivale ad analisi completa del parlato: **audio NON trascritto**.
- Non attribuire regole vocali o frasi al docente prima della revisione dell'audio. Non affermare che un particolare ingresso sia stato replicato esattamente.

## Osservazioni dai fotogrammi realmente esaminati
1. **Video profilo volume / Delta (parte 1)**: diverse finestre ATAS e profili orizzontali a destra, talvolta colorati per lato/flusso; vengono segnate e discusse visivamente aree orizzontali, contestualizzate su più grafici. Sono visibili anche grafici prezzo affiancati a CVD e a una vista Speed of Tape. Il titolo riferisce un intervallo di 30–50 giorni e un Delta Profile 10:1, ma **non** ne dimostra la configurazione numerica.
2. **Video VWAP & Delta Profile**: bande dinamiche attorno al prezzo (alcune blu/celesti e grigie), profili orizzontali rosso/bianco e zone orizzontali sovrapposte. In un fotogramma la legenda dell'indicatore mostra una variante VWAP/TWAP su finestra settimanale; in altri sono presenti CVD e CVD Pro/Multi Market Powers. I parametri (periodo sessione, deviazione sigma, delta per strike, formula zone) non sono ricavabili in modo certo da questo campionamento.
3. **Breve recap CVD Pro**: profili a destra, bande di prezzo colorate, grafico del prezzo e pannelli di pressione/Delta. Le schermate sono compatibili con un uso congiunto di livelli preventivi e convalida contestuale, ma non ne dimostrano il processo temporale o un vantaggio predittivo.

## Ipotesi principali, ordine di lavoro aggiornato
**A. Delta Profile multi-periodo** secondo comunicazione diretta del trader (10/11): studiare Current Week, Current Month, Previous Month e significato esatto di Monthly, con attenzione alle zone di Delta massimo positivo/negativo assoluto.
**B. Sforzo vs risultato**: identificare sul prezzo chiuso quanta pressione aggressiva compare presso il livello e con quale risposta del prezzo, evitando indicatori che leggono il futuro.
**C. Conferma d'ingresso**: CVD su timeframe/range, CVD Multi e lettura di assorbimento/esaurimento, con regole esplicite soltanto dopo che video/audio/settings le confermano.
**D. VWAP con bande, profilo volume, PVP/POC**: strumenti complementari e filtri da distinguere nettamente dal Delta Profile.
**E. GEX/OI/expected move**: archiviare come piste secondarie, non attribuire la generazione dei sei livelli alla catena opzioni.

## Requisiti per ricostruzione REMURA
- Il Delta per livello di prezzo richiede prints reali, quantità, bid/ask aggressor side ed exchange timestamp; i prezzi FXCM M5/M15 non bastano.
- Occorrono snapshot "first-seen" nel **momento del calcolo mattutino**; i profili Current Week/Month sono mobili. Non usare retroattivamente i profili finali della giornata.
- Separare: indicatore esplorativo, prova causale, entry trigger, economic edge after costs. Nessun profitto o affidabilità dimostrati.
- Prima del motore reale, inventario fonti gratuite e limiti: dati CME a pagamento/licenze possibili; ridurre chiamate e retention e non avviare cron.
- Quando disponibili i parametri ATAS, costruire parser o calcolatore **solo offline/sintetico** con test causali, senza toccare main, VPS, collector, PR #89, o Track A/C.

## Questioni ancora aperte
- Che cosa si intende esattamente per `Delta Profile 10:1` e `LS`? Il titolo non basta.
- I livelli sono gli estremi di Delta **per prezzo** oppure Delta aggregato di periodi diversi? Come viene misurato sforzo/risultato?
- Quali date/orari definiscono "Week" e "Monthly" in ATAS e quale feed dati/contract-roll?
- Qual è l'algoritmo di conferma dell'entry, e quali sono le impostazioni di CVD Pro/ VWAP (ancoraggio, bande)?
- Disponiamo di dati tick NQ legalmente riutilizzabili, completi, accessibili gratis?

**Stato:** cartella raggiungibile e primo esame visivo di 3 video; nessuna trascrizione del parlato, nessuna ricostruzione ufficiale del metodo o prova di edge. Zero deploy e zero nuove spese.
