# REMURA TradingView v0.8.185 LAB — registrazione locale evidenze M5

**Versione 0.8.185 LAB · 21 novembre 2026 · Europe/Rome**

Prima di consultare i risultati degli holdout, REMURA deve poter distinguere ciò che era pianificato, ciò che è stato ricevuto in tempo, ricevuto in ritardo e ciò che non è stato osservato.

Questo modulo LAB prepara una catena SHA-256 **solo su dati sintetici** e un piano di slot M5. Ogni record riporta il digest anonimo, l'ora di chiusura, il timestamp di ricezione o assenza e l'hash del record precedente. Alterare il contenuto senza ricomputare gli hash rompe la catena; **un operatore può comunque ricomputare tutta una catena non ancorata**, quindi non è una prova indipendente né di completezza né dell'orario reale.

- Il calendario V2 e le due finestre 23–29 novembre e 30 novembre–6 dicembre UTC sono immutati.
- Non esistono segnali di trading, PnL, risultati, dichiarazioni di edge o acquisizioni live.
- Le osservazioni `NOT_CAPTURED` significano assenza nel piano fornito e **non** quiete del mercato o assenza di ordini istituzionali.
- Questo lavoro non modifica Private Capture, Oracle collector, Shark Science o fonti reali.
- Prima di fare analisi prospettiche attendere dati attestati, un clock indipendente e la registrazione esterna dell'anchor; non inventare il ledger da dati posteriori.

Roadmap parallela conservata: Contributors v0.85 Access/D1 e collaudo privato no-go; Experience v0.30 splash toro/orso, Ampere Radar e backup senza interventi, Squalincome e Telegram livelli approvati futuri.
