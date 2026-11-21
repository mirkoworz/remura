# REMURA TradingView v0.8.186 LAB — digest pronto per ancoraggio esterno (NON ancorato)

**21/11/2026 Europe/Rome**

`anchor_request_v0186_lab.py` crea un digest SHA-256 deterministico di una **catena sintetica M5 verificata localmente**, con separazione di dominio `REMURA_TV_HOLDOUT_V0186_ANCHOR_REQUEST\\0`. Il digest è un identificatore del contenuto, non prova che i dati esistessero all'ora dichiarata.

Non fa upload, network, query dati reali, scansioni o transazioni. Non ricava risultati di trading, non altera holdout preregistrati, non cambia fold o matching. L'input rimane sintetico e solo sulle finestre 23–29 novembre e 30 novembre–6 dicembre UTC.

## Prima di dichiarare una prova temporale indipendente

1. Occorre generare l'anchor **nel momento della cattura** da infrastruttura effettivamente operativa, con origine e orologi attendibili; un dato ricostruito dopo l'holdout non è trasformabile retroattivamente in dato prospettico.
2. La futura attestazione esterna potrebbe usare un servizio di marca temporale RFC 3161 o un testimone indipendente; valutare affidabilità, disponibilità e costi gratuiti prima di selezionarlo.
3. Validare davvero firma della ricevuta, identità/chain di fiducia, digest, timestamp, validità certificato e condizioni di riproducibilità. La funzione `receipt_review` controlla **solo la corrispondenza testuale di un placeholder**: `signature_verified=false` SEMPRE. Non è un verificatore RFC 3161.
4. Non pubblicare i dati grezzi, i digest individuali di decisioni o file con PII nel repo pubblico. Un eventuale anchor pubblico deve essere solo aggregato/opportunamente progettato.
5. Fino a verifica reale: `trusted_anchor_established=false`, `capture_clock_proven=false`, `trade_edge_proven=false` e `NO_GO_LIVE`.

## Roadmap preservata

Protocollo V2 byte-pinned; holdout1 23–29/11 e holdout2 30/11–06/12 UTC, primario CVD vs price-only a 60 min e costi ipotetici congelati. Shark Science v0.4 su COT/sentiment/CVD/ER senza vantaggi garantiti; Contributors v0.86 piano di diagnosi Cloudflare senza nuove chiamate né Secret; Experience v0.30 splash toro/orso e SMF; Private Capture LAB fermo; Oracle collector/autoupdater invariati; Ampere Radar e backup, Squalincome, Telegram approvati preservati.

La fase successiva utile non è moltiplicare gli hash di fixture, ma **attestare un flusso reale con consenso e provenienza indipendente**; senza tale fonte restare NO_GO.
