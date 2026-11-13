# REMURA — NQ / ATAS: analisi dei fotogrammi di sette lezioni
**CHECKPOINT RICERCA v0.8 — 10 novembre 2026** · SOLO OFFLINE · NESSUN deploy.

## Ambito, limiti e provenienza
- Cartella Google Drive privata condivisa dall'utente: 12 video censiti; **7 acquisiti e campionati visivamente** (SMF 4, 6, 7, 8, 9, 10, 12), con fotogrammi in vari minuti e zoom su configurazioni pertinenti.
- **5 non acquisiti** per dimensione oltre il limite del connettore (SMF 1, 2, 3, 5, 11). L'audio dei sette video **non e' stato trascritto** in modo affidabile; questa indagine non e' una visione integrale ne' una trascrizione del docente.
- Non pubblicare file originali, fotogrammi, audio, trascrizioni, URL/ID Drive o materiali del gruppo Telegram in questo repository pubblico. Riportare solo osservazioni fattuali e inferenze chiaramente etichettate.
- Le date visualizzate nei video (es. 30/09/2026 e 08/10/2026) non sono la sessione dei sei livelli NQ del 10/11. Non usare i prezzi dei filmati come conferma retroattiva dei sei livelli.

## Registro evidenze: visibile e verificabile nei fotogrammi
| Video | Momento | Elemento visuale verificato | Significato / limite |
|---|---|---|---|
| SMF 7 — VP 30:50 giorni, Delta Profile | 04:43 | Grafico NQZ6 **H1**, menu timeframe, `Days count = 50`; istogramma volume per prezzo sul lato destro | Esiste un contesto di **50 giorni** in vista H1; non prova quali periodi producano singoli livelli delta |
| SMF 7 | 11:01, 14:10, 20:28, 29:55 | Profili orizzontali, bande rosse disegnate sui prezzi, pannelli Speed of Tape/CVD e piu' grafici | Le zone vengono interpretate con prezzo e pressione; la regola vocale specifica non e' nota |
| SMF 8 — parte 2 Delta Profile | **07:09** | Menu timeframe **10R (Range 10)** e `Days count = 3`, con profilo bianco/rosso per prezzo e pannelli Volume/Speed of Tape | **Tre giorni** di dati nella vista Range 10, diversa dalla panoramica H1 50 giorni |
| SMF 8 | **30:02** | Setup a tre grafici (M5, M1, 10REN), profilo per prezzo e CVD; strumento posizione con area rossa sopra e verde sotto il prezzo | Si visualizzano stop/target di una **ipotesi short**; non prova esecuzione, fill o profitto |
| SMF 9 — CVD Pro Tips, recap | 03:27 | Candele NQZ6, cerchi verdi/rossi sulle candele e righe di Delta/Volume/DeltaVolume | Analisi di aggressioni e risposta; cerchi non identificano necessariamente trader istituzionali |
| SMF 9 | **10:21** | Etichetta indicatore **`QQQ NQ Premarket Walls (Bars, True)`**; messaggio `QQQ NQ: Dati 2026-10-08 assenti: avviare il raccoglitore Barchart` | **Altro layer indipendente** presente sul grafico; il dato e' esplicitamente segnalato mancante, quindi non inferire livelli QQQ/Wall validi da questa scena |
| SMF 9 | 31:05 | Tre grafici tra M5, M1 e 10REN; CVD, Delta/Volume, Speed of Tape; linee rosse/verdi | Contesto + dettaglio esecutivo; non e' possibile ricostruire una logica automatica di entrata |
| SMF 10 — recap, parte 2 | 00:26, 02:12, 03:05, 06:36 | Profilo prezzo grigio e bianco/rosso, zone gialle/orizzontali e grafici Delta/CVD | Congruenza con analisi di livelli e reazione; manca prova dell'algoritmo sorgente |
| SMF 12 — VWAP & Delta Profile | 21:11 | Bande VWAP sfumate su NQZ6 e segnalazione visibile di `Last Market Data Update: 28 min ago` | Il feed puo' risultare ritardato/stale e deve superare quality gate prima di qualsiasi convalida causale |
| SMF 12 | **29:39** | NQZ6 su **10R**, bande colorate, tooltip **`Upper Deviation 2`** e avviso `Last Market Data Update: 36 min ago` | Uso osservato di **seconda deviazione superiore** in quel settaggio; anchoring/formula e altre bande non attestati |
| SMF 4 — HTF momentum/IVB | 03:32–37:46 | Grafici TradingView di candele momentum HTF, zone e transizioni di trend | Filone di contesto price-action, non prova livelli Delta |
| SMF 6 — ciclicita' e TOME | 13:24–37:46 | Fasi di mercato annotate in TradingView e successivamente schermate ATAS con price/volume | Possibile filtro temporale/calendariale, non usarlo come trigger verificato senza audio/regole |

## Architettura del metodo: distinzione tra livelli di evidenza

### A. Esplicitamente detto dal trader (testo del 10 novembre, ore 21:15–21:18)
1. Le zone derivano da **picchi di Delta** e dalla loro lettura **sforzo vs risultato**.
2. Periodi nominati: `Current Monthly`, `Previous Monthly`, `Week`, `Monthly`; priorita' ai `current`.
3. Non e' stato indicato se selezionare il massimo di Delta positivo, minimo negativo, valore assoluto, uno o piu' picchi locali, ne' la formula di soglia o estensione in zona.

### B. Osservato direttamente nelle schermate, con timestamp
1. Contesto multi-scala: H1 con 50 giorni; Range 10 con 3 giorni; in recap M5/M1/10REN.
2. Istogrammi per prezzo, zone manualmente marcate, CVD, Speed of Tape e a volte bande VWAP (in una scena `Upper Deviation 2`).
3. Tool grafico stop/target e monitoraggio della risposta del prezzo.
4. Indicatore separato `QQQ NQ Premarket Walls` con mancanza dati segnalata: **non** assumere che abbia generato le zone del giorno.

### C. Ipotesi operativa di lavoro REMURA (NON una citazione del docente)
```
Dati futures NQ autentici bid/ask + timestamp
  -> aggregazione Delta PER PREZZO E PER PERIODO (current week/month; previous month)
  -> candidati: picchi positivi, picchi negativi, picchi assoluti
  -> fotografia immutable/as-of dei candidati prima dell'inizio della sessione
  -> contesto 30/50 giorni, POC/value area, VWAP + bande (filtri, non origini certe)
  -> prezzo raggiunge una zona
  -> confronto sforzo (aggressione, intensita' delta) vs risultato (avanzamento del prezzo)
  -> conferme CVD/Speed of Tape/footprint su M1 o Range 10
  -> solo ipotesi di entrata con stop e target, validazione prospettica e costi
```
**Necessaria successiva prova**: la combinazione e l'ordine dei moduli non sono ancora dimostrati dai commenti vocali e dalle impostazioni integrali.

## Precisazioni fondamentali
- Il `delta_per_price` NON e' il CVD grafico nel tempo; un istogramma bianco/rosso potrebbe rappresentare anche il volume bid/ask invece del delta puro. Controllare impostazione `Profile Type`.
- **Current Week/Current Month sono mobili** e cambiano man mano che arriva volume nuovo: salvare tutto con timestamp first-seen, mai una fotografia post-sessione usata per fingere previsione mattutina.
- Le sei zone del 10/11 viste in chat hanno distanze quasi regolari, ma la formula non e' stata derivata dal Delta Profile; non reinterpretarle retroattivamente.
- I video mostrano NQZ6 ma altri eventuali simboli o roll vanno esplicitati. Gli ordini di mercato sono anonimizzati: picchi di Delta non provano chi siano gli operatori.
- L'avviso visibile di feed stale/mancante significa che REMURA dovra' mostrare **UNKNOWN** invece di generare segnali quando mancano input.
- Fonte dati futures bid/ask aggressor side genuina necessaria; i soli OHLCV di FXCM TradingView non bastano. Le licenze CME/feed real-time e il limite di gratuità non sono ancora verificati per un'acquisizione automatica.

## Prossime prove senza costi
1. Annotare impostazioni `Profile Type`, `Max Level Type`, session template, profili current vs previous, periodi di riferimento e tipo di CVD Multi con screenshot/clip leggeri dei momenti dove appaiono.
2. Se si puo' avere una trascrizione del parlato dai video, indicizzare frasi su "picchi di delta", "sforzo risultato", "battle zone", "LS", "10:1", "trigger". Senza trascrizione rimangono **domande aperte**, non regole codificate.
3. Pianificare motore Delta Profile offline basato su dati *real trade-by-price* e su test sintetici per temporalita' e duplicati; non attivare finche' non e' chiara la disponibilita'/licenza del feed.
4. Definire baseline/controlli, limiti di rischio, false reazioni, purging e test out-of-sample; nessuna promessa di redditivita'.

**Protezione progetto:** PR #101 DRAFT, Track B #89 DRAFT invariata, main/live A/C/Oracle/collector intatti, zero nuovi abbonamenti, zero trading.
