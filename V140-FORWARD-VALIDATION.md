# REMURA v1.40 — verifica prospettica (candidata, NON installata)

La v1.39 resta in produzione finché test, backup e installazione manuale del backend non siano conclusi. Nessun ordine né trading automatico.

## Metodo e limiti

- Origine esclusiva: storico osservato realmente da Squalincome. Il martedì della data COT NON è considerato il momento di conoscenza: si parte dall'ora italiana/UTC della prima osservazione autentica memorizzata.
- Campione: prima osservazione per ogni mercato e settimana COT per il gruppo principale. Si misura separatamente il primo passaggio a conferma tecnica e il primo evento qualificato, ciascuno una sola volta per mercato/settimana. I tre gruppi si possono sovrapporre: NON vengono sommati come risultati indipendenti.
- Ingresso teorico: prezzo open della prima candela M15 che inizia non prima dell'osservazione, entro 45 minuti e sullo stesso broker; non è un prezzo realmente negoziato.
- Uscita: close dopo 1/4/24 ore, rispettivamente su 4/16/96 M15 contigue, completamente chiuse. Weekend, festività, gap e mix tra broker non sono interpolati.
- Risultati: percentuale nella direzione COT, Wilson 95%, ritorno in punti base (bps), massima escursione favorevole e contraria, benchmark long dello stesso mercato e periodo. Tutti lordi, senza spread, commissioni, slippage.
- Confronti: convergenza vs divergenza, osservazione vs conferma tecnica vs evento qualificato. I sottogruppi sono correlati e NON indipendenti.
- Soglia espositiva: «Campione insufficiente» sotto 30 osservazioni o 8 report COT distinti. Anche superando la soglia, il dato resta descrittivo e non prova capacità predittiva.
- Persistenza SQLite privata: nessuna cancellazione dello storico esistente; una coorte per mercato/settimana, un esito per orizzonte. Misure aggregate e senza credenziali nell'API.
- Sentiment: escluso da questa prima release finché non sia verificato che l'osservazione era davvero disponibile all'epoca.
- Fuori campione: occorre una raccolta futura separata; non vengono retrodatati né il segnale né il rapporto COT.

API di sola lettura: GET /private-api/signals/validation (aggregati soltanto).
Calcolo dopo ogni scansione Squalincome. Nessuna modifica alle soglie di freschezza.

## Prima del rilascio in produzione

1. Verificare CI su PR e test di regressione, inclusi i casi con lacune nel feed.
2. Correlare per i 13 mercati datati: ultimo tentativo, esito raccolta, ultima candela chiusa, rotazione dei 5 strumenti e log di arresto/riavvio. Senza modificare la soglia attuale.
3. Eseguire backup SQLite coerente tramite sqlite3.Connection.backup, con archiviazione privata e permessi rigorosi; salvare configurazioni segrete separatamente senza mostrarle in chat.
4. Preparare procedura di rollback e installare manualmente backend: l'autoupdater blocca modifiche a scripts/ e workflow.
5. Dopo test e installazione, aggiornare versione, data/ora italiana su tutte le pagine e cache PWA. Non dichiarare v1.40 installata prima.

## Diagnostica di sola lettura (terminale autenticato VPS)

sudo systemctl --no-pager --full status remura-private.service remura-autoupdate.timer

curl -fsS http://127.0.0.1:8765/private-api/prices/status

curl -fsS http://127.0.0.1:8765/private-api/signals/status

Non condividere database, token, account o file sotto private/; le API locali non devono essere pubblicate.
