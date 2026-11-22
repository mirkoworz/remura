# REMURA COT v0.8 LAB — revisione esplicita della direzione futures -> spot Forex
22 novembre 2026, Europe/Rome — solo fixture sintetiche.

## Perché la fase di mapping è necessaria
Il precedente COT v0.7 confronta Asset Manager e Leveraged Funds sui contratti TFF in punti percentuali di open interest. Per tradurre un cambiamento in esposizione valutaria Forex non basta il codice CFTC: servono dati ufficiali del contratto, base/quote, direzione, mapping di ticker spot, maturità futures, convenzione dei prezzi, rilascio pubblico e disponibilità alla data della decisione. Una coppia con USD come BASE (es. USD/JPY) inverte l'orientamento di un future sulla valuta non-USD quotato in USD; EUR/USD no. I cross senza USD richiedono due leg e ulteriori verifiche.

## Consegna
- research/cot/cot_spot_futures_mapping_v08_lab.py
- research/cot/test_cot_spot_futures_mapping_v08_lab.py (15 nuovi casi)
- .github/workflows/remura-cot-fx-map-v08-only.yml

Valuta soltanto una *proposta* sintetica esplicita con codice CFTC, valuta sottostante dichiarata, valuta di quotazione dichiarata USD, codice FX, hash/dettaglio documento dichiarati. Verifica il formato ma NON l'autenticità o l'associazione codice-contratto. Se il set delle 2 settimane COT non è disponibile come as-of, risponde UNKNOWN. Un cross come EUR/JPY resta UNKNOWN_UNSUPPORTED_OR_CROSS_MAPPING.

Solo nel caso di un prototipo di singola coppia con una gamba USD, restituisce il segno matematico ASSUNTO dei cambiamenti TFF in punti percentuali. Il risultato è rigorosamente UNATTESTED_USD_LEG_DIRECTION_SKETCH_NOT_SIGNAL: mai un segnale, né prova del mapping o trade reale. Non inserire in Shark Score finché una sorgente ufficiale del contratto e un test indipendente non attestano la convenzione e il clock.

No provider call, no Oracle/Cloudflare, no deploy, no modifica del protocollo V2, nessuna spesa. Il ramo COT v0.7 resta intatto.
