# REMURA v1.54 — Centro di Controllo infrastrutturale (01/11/2026)

**Prima fase: dashboard di sola lettura, zero costi nuovi.** La sezione `Impostazioni → Centro di Controllo` e la scorciatoia nel menu utilizzano sei endpoint *già esistenti* della VPS: `/private-api/health`, `/private-api/resources`, `/private-api/prices/status`, `/private-api/cot/status`, `/private-api/signals/status`, `/private-api/autoupdate`. Nessun nuovo processo, pacchetto, segreto, permesso, database o porta. Nessuna chiamata ai broker per la diagnostica.

Vengono visualizzati: stato VPS; risorse; cTrader principale e riserva; aggregati di qualità prezzi, COT, Myfxbook/Capital/IG **sulla VPS**; scanner Squalincome; updater. Il collegamento Capital via Google/Firestore è distinto e non viene dedotto dal collector Capital VPS. I timestamp rappresentano controlli/tentativi, non acquisizioni confermate. Il weekend non viene considerato automaticamente errore delle fonti, e nessun segnale non significa fallimento di Squalincome.

Restano intenzionalmente **N/D** i consumi Oracle, l'effettivo numero chiamate ai provider, il billing, l'utilizzo Firestore, GitHub Actions e l'integrità/ultimo backup SQLite. Non mostriamo credenziali, URL, ID conto, log grezzi o percentuali di provider inventate.

Il pannello interroga gli endpoint **solo all'apertura** e quando viene premuto `Aggiorna diagnosi`. Le richieste non vengono memorizzate dalla service worker. La nuova cache `remura-shell-v68-v1.54-monitor` e il banner in cima sono applicati a tutte le nove pagine.

## Distribuzione
La release modifica solo frontend, test e documentazione. Non modifica `scripts/`, `deploy/` o workflow, dunque è candidata al rilascio automatico secondo i controlli esistenti **se** i test push sono verdi e l'autoupdater riesce a confrontare i commit. Non affermare che sia già installata sulla VPS senza verificare la UI e `/private-api/autoupdate`.
