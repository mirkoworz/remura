# REMURA TradingView — Delta Peaks LAB v0.1
**Aggiornamento: 11/11/2026, ore 08:41 CET**

> Ricerca separata: nessuna modifica alla web app REMURA, al deploy, ai dati raccolti o alle PR dei filoni A, B e C.

## COPIA IL CODICE
**File da usare:** [REMURA-Delta-Peaks-LAB.pine](REMURA-Delta-Peaks-LAB.pine)  
**Vista RAW (testo puro):** apri il file su GitHub e tocca **Raw** per copiare il codice completo.

1. Apri TradingView, simbolo **FXCM:EURUSD**, timeframe **5 minuti**.
2. Apri **Pine Editor**, crea un nuovo indicatore, sostituisci il codice con il contenuto completo del file `.pine` (a partire da `//@version=6`).
3. Salva e clicca **Aggiungi al grafico**. Se compare un errore, riportane il testo o fai uno screenshot.
4. Impostazione di partenza: **delta intrabar = 1 minuto**, **lookback = 30 barre**, **moltiplicatore = 2.5**.
5. Controlla i simboli **D+**, **D-**, **ER** e i tre livelli.

## COSA FA v0.1
- Rileva **picchi di delta stimato** rispetto alla media del suo valore assoluto su 30 barre.
- Evidenzia un'**ipotesi** di sforzo elevato e risultato debole/opposto (**ER**), senza chiamarla assorbimento istituzionale certo.
- Disegna il livello della barra con massimo |delta| della **settimana**, del **mese** e del **mese precedente**.
- Traccia i livelli a **hl2** (media tra massimo e minimo della barra), non a un prezzo di scambio istituzionale verificato.
- Offre condizioni di **alert TradingView**; non invia automaticamente notifiche a REMURA.

## LIMITI IMPORTANTI
- La libreria **TradingView/ta/14** e la funzione `requestVolumeDelta()` classificano volume intrabar: non sono il flusso certificato degli ordini CME. Nel forex FXCM il dato dipende dal feed e puo' essere tick volume.
- I livelli sono calcolati solo sullo **storico intrabar accessibile all'account**. Se un periodo non e' caricato o mancano dati, la stima puo' essere incompleta e mostrare **N/D**.
- La classe **ER** e' una regola euristica (delta elevato + corpo piccolo o direzione contraria): NON prova un acquisto/vendita di istituzionali.
- Il criterio di selezione dei livelli v0.1 usa il **massimo delta assoluto della singola barra** per periodo; va ancora confrontato con gli esempi Week / Current Monthly / Previous Monthly del metodo di riferimento.
- Il Pine Script **non e' ancora stato compilato o eseguito in TradingView**: primo test da fare sul grafico.
- Nessun costo cloud, server, API o servizio a pagamento introdotto da questo codice; funzioni e limiti operativi di TradingView dipendono dal piano dell'utente.

## MODIFICHE FUTURE
Apri [ROADMAP.md](ROADMAP.md). Tutte le modifiche qui restano in laboratorio finche' non vengono testate; nessun merge verso `main` o deploy automatico.

**Codice sorgente**: [REMURA-Delta-Peaks-LAB.pine](REMURA-Delta-Peaks-LAB.pine)  
**Fonti**: [libreria TradingView ta](https://www.tradingview.com/script/BICzyhq0-ta/), [documentazione Pine Script v6](https://www.tradingview.com/pine-script-docs/).
