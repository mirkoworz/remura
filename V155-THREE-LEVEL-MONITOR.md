# REMURA v1.55 — Salute tecnica, dati e consumi (01/11/2026)

Questa release aggiunge i tre livelli distinti per ogni componente nel Centro di Controllo di Impostazioni: **Tecnica**, **Dati**, **Consumi**. Tutto il monitoraggio è in sola lettura: usa sette endpoint *già esistenti* nella VPS privata, senza modificare server Python, database, secrets, collector o chiamare nuove API broker.

- Le candele verificate durante la chiusura del mercato sono archiviate correttamente, ma la salute DATI indica `Mercato chiuso` e non nuove candele live.
- Squalincome con 0 analizzati e tutti esclusi per `market_closed` è tecnicamente attivo ma DATI indica `Mercato chiuso`, non un segnale né un guasto.
- Una riserva cTrader configurata non è dichiarata effettivamente utilizzata; si legge `source=backup` dalle righe stato prezzi quando disponibili.
- Per Myfxbook sulla VPS viene letto `/private-api/retail/latest.json` e la data del file aggregato. Questo timestamp non prova la variazione delle posizioni retail. Capital su Firestore è separato da Capital sulla VPS.
- **Consumi già misurabili:** `GET` totali e private ricevute dal server Python dopo l'ultimo avvio, usando `resources.webApi`. Sono chiamate **in ingresso alla nostra VPS**, non contatori delle richieste cTrader/Capital/IG/Myfxbook, non traffico OCI né billing. Queste ultime rimangono N/D; N/D non significa 0.
- Unici interventi: HTML/JS/CSS frontend, versioning PWA e test. Il gate dell'autoupdater rimane invariato; bisogna verificare l'effettiva distribuzione sulla VPS.

**Passo successivo protetto:** inserire veri contatori outbound nei singoli collector con categorie di operazione, successo/errore e persistenza privata. Richiederà modifica a `scripts/`, backup e rilascio manuale controllato; nessuna chiamata aggiuntiva soltanto per misurare.
