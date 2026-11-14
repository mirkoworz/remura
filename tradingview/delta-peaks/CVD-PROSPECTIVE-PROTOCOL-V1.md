# REMURA v0.8.71 LAB | 14/11/2026 16:56 CET
## Protocollo prospettico congelato prima del pilot
- Development: 16–22 novembre UTC; primo holdout: 23–29 novembre; replica: 30 novembre–6 dicembre. Estremi esclusivi a mezzanotte UTC. Il weekend iniziale è solo diagnostica.
- Primario: CVD vs price-only a 60 minuti; secondari 4h/24h e filtri ER, retest, concordanza segno footprint/delta. Nessuna scelta di vincitore a posteriori, nessun peso.
- Ingresso proxy alla successiva chiusura M5, costi round-trip ipotetici 0/1/2 pip. Nessun PnL eseguibile o spread misurato.
- Niente matching tra fold, niente outcome oltre fine fold, niente report fold anticipato. Controlli senza riutilizzo dentro confronto; confronti tra filtri dipendenti.
- Finestra completa riferita a slot richiesti, NON calendario di mercato. Le barre mancanti non sono imputate. Per i fold servono più export privati validati; il reader batch 48h non basta. Il report descrittivo precedente resta visibile: non è un sistema di blindaggio indipendente, l'operatore deve evitare tuning dopo averlo osservato.
- Il risultato storico D0.8 primario (-0.6680 pip) non mostrava miglioramento. Non cambiare ipotesi se holdout negativo. Nessuna soglia di successo, significatività o promessa introdotta senza piano di potenza e dati reali.
## Fonti ausiliarie
Il pin B 8dc51e8a199dc1cfd45e4cd2e7b339510af2eb2b, script shark_cvd_cot_price_triage.py, espone conteggi aggregati con proof HMAC della stessa decisione B o prefisso precedente. NON espone un sink per singola decisione CVD verificata. Unire questi conteggi ai conteggi TradingView sarebbe errore ecologico. Serve un'interfaccia privata per identità decisione, clock e tier attestato dal filone B; nessuna modifica B in questo lavoro. Per sentiment servono osservazione originaria e timestamp di disponibilità, provenienza e immutabilità; non usare valore corrente o assenza come negativo. Fino ad allora entrambi UNKNOWN rispetto alla stessa decisione TV.
