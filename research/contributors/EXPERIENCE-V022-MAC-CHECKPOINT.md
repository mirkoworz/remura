# REMURA Experience v0.22 LAB — collaudo Mac — 20/11/2026 20:36 CET

Base `3971c0af7b6a802a9d3566c4345e804d1ffdefbe`. Entrambi i file HTML completi sono stati estratti immutati da Git e avviati come documenti locali con Chrome 157.0.8103.80 sul Mac. Blob v0.12 `9a29b85db66c284cebe97a0a0e97cb016514f7ca`, blob v0.22 `ebab7141864302c442bd9bcd876faf6d40b731d8`. I dieci asset incorporati, nell'ordine originale, coincidono byte per byte. Nessuna grafica modificata.

| Prova sui documenti completi | Esito |
| --- | --- |
| v0.12 cinematografico, desktop 1366×900 | 9/9 fotogrammi decodificati e osservati in sequenza, logo SMF decodificato, flash e dissolvenza rilevati. Progressione 0, 33, 67 e 100%. |
| v0.22 cinematografico, profilo mobile Chromium | 9/9 fotogrammi decodificati e osservati in sequenza, logo SMF decodificato, flash e dissolvenza rilevati, progressione completa e nessun overflow orizzontale. Il caso non era passato con otto scenari concorrenti ed è passato in una riprova isolata. Il motivo dell'esito iniziale resta indeterminato. |
| v0.22, OWNER / CONTRIBUTOR / VIEWER | 3/3 scenari con menu e accesso allo snapshot dimostrativo conformi ai ruoli simulati. |
| v0.22, accesso negato ed errore | 2/2. Ritorno alla scelta senza mostrare la Home o il menu del ruolo. |
| v0.22, movimento ridotto | La scena è nascosta mentre autorizzazione e avanzamento continuano fino alla Home. |
| v0.22, prezzi, COT e livello in compilazione | Prezzo fresco e prezzo obsoleto rimossi alle rispettive scadenze previste con l'orologio di prova. COT sintetico disponibile e caso N/D verificati. La bozza sopravvive al timer e al refresh. |
| v0.22, logout e risposta tardiva | Una risposta sintetica risolta dopo il logout resta senza effetto sulla vista chiusa. |

Ispezione visiva dei nove fotogrammi decodificati e del logo originale. Riconosciuti toro e orso, avvicinamento, scontro, esplosione, scritta REMURA e pinna. Il ringraziamento compare durante la sequenza e nella Home.

Esito finale **10/10 scenari**, di cui uno passato in riprova isolata. Nessun errore JavaScript di pagina o richiesta HTTP osservati nei casi passati. Il profilo mobile usa viewport 390×664, DPR 3 e input touch in Chrome, con schermo simulato 390×844. Le 366 verifiche storiche restano il loro checkpoint separato. Le prove qui riportate usano fixture sintetiche e orologio controllato nel caso di scadenza. Safari Mac rinviato su richiesta dopo che WebDriver ha segnalato l'automazione remota disattivata. Safari su iPhone reale non eseguito. L'autorizzazione server, il dispositivo reale e la produzione restano fuori da questa attestazione.

Stato Experience v0.22 LAB e asset invariati. Questo addendum resta sul ramo di checkpoint Mac. Lo sviluppo Experience su iPhone continua sul suo ramo.

## WebKit nativo sul Mac — 20/11/2026 22:04 CET

**PASS, 10/10 verifiche su v0.12 e 11/11 su v0.22.** I due HTML completi sono stati caricati dal disco con una piccola app di test Swift e il framework WKWebView di macOS 13.7.8. Viewport 390 px, archivio browser non persistente e regola che blocca le richieste HTTP e HTTPS. Entrambi hanno decodificato i nove fotogrammi e il logo, raggiunto il 100%, aperto la Home Contributor, mostrato prezzi e COT sintetici e chiuso la sessione con logout. Col layout stretto non è stato osservato overflow. Il candidato ha superato anche lo scenario di accesso negato.

Il risultato è un collaudo del motore WebKit della piattaforma Mac. Safari come applicazione resta rinviato. Safari iPhone reale e playback temporale dei fotogrammi in questa app di test restano fuori da questa attestazione. Asset, codice HTML e ramo iPhone invariati.
