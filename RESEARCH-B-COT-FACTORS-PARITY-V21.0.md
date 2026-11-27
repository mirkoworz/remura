# REMURA — Filone B v21.0 LAB: 7 fattori FX + parità archivio CFTC

**Checkpoint:** 23 novembre 2026, Europe/Rome. **PR #108 Draft**, ramo \`research/filone-b-cot-intelligence-v206-20261123\`.

## Risultato costruttivo 1 — de-duplicazione dell'esposizione Forex

\`cot-intelligence-fx-factors.js\` costruisce un **report di 7 distinti contratti valutari CFTC TFF** (EUR, GBP, JPY, AUD, CAD, CHF, NZD contro USD) a partire dallo stesso snapshot ufficiale o archivio offline già normalizzato.

Per ogni valuta espone:
- posizione netta Asset Manager/Institutional e Leveraged Funds, entrambe normalizzate su open interest;
- variazione netta fra due report consecutivi in **punti percentuali**; variazione del numero di contratti open interest;
- COT Index (min-max) a 52 report, solo su serie osservate e contigue;
- data report, codice contratto e \`first_seen_at\` locale, se presente.

La vista dei **28 cross** include la scomposizione matematica \`delta(base) - delta(quote)\`. Le 7 coppie con USD impiegano convenzionalmente **USD = 0** come riferimento *matematico*, non come dato istituzionale; non esiste alcun dato di posizionamento diretto sul mercato spot Forex del cross.

Le 28 coppie riutilizzano soltanto 7 futures: **non sono 28 segnali indipendenti**. Le 7 valute distinte sono contratti diversi ma possono comunque essere economicamente correlate. La classifica ordina per ampiezza assoluta della variazione del netto Asset Manager/OI; niente raccomandazione di trading.

### Lavoro sui dati autentici, senza duplicare la chiamata CFTC

La prova precedente **è già stata eseguita**: GitHub Actions \`#45206837974\` ha acquisito 980 righe ufficiali, 70 settimane x 14 contratti, e ha prodotto la prima classifica settimanale verificata; checksum pubblico \`a2d58c5a3347c121b491c5f495f7ee01ed83b6a282cc11fb2e5f49b1688ffb23\`. Le righe dettagliate non sono state conservate fuori dal runner effimero: non pretendere che il nuovo fattorizzatore abbia già prodotto 7 numeri autentici. Nessuna nuova interrogazione della CFTC è schedulata nel workflow.

## Risultato costruttivo 2 — parità CFTC pubblico e cache privata

\`scripts/cot_intelligence_parity.py\` legge **solo due JSON già esistenti sul disco**:

- \`--public\`: esportazione originata da \`scripts/cot_public_official_audit.py\` con dati CFTC ufficiali, \`readAtUtc\` e SHA-256 delle righe normalizzate;
- \`--private\`: esportazione di una **copia offline** SQLite REMURA, prodotta con \`scripts/cot_intelligence_snapshot.py\`, con valori e \`first_seen_at\` se registrati.

**Non accede direttamente alla VPS, non apre SQLite e non effettua HTTP.** La funzione pure \`reconcile()\` confronta le 14 chiavi attese per ognuna delle due date report esplicite, per **28 verifiche dataset/codice/report-date**. Verifica tutte e cinque le grandezze: OI, prima categoria long/short, seconda categoria long/short. L'assenza di un contratto, una discrepanza o un timestamp locale futuro viene segnalata, mai interpolata.

### Distinzioni epistemiche non negoziabili

1. SHA-256 valida **l'integrità interna** della copia JSON pubblica rispetto all'hash dichiarato; non autentica la CFTC come firmataria e non prova che i dati fossero disponibili in un giorno precedente.
2. \`value_parity_only\` significa **valori storici attuali identici** fra le due fotografie, non assenza di revisioni né prova di corretto backtest.
3. \`first_seen_at\` prova solamente un timestamp **dichiarato** dalla cache del collector; non è il rilascio ufficiale CFTC. Timestamp mancanti e anteriori alla data del report sono visibili; questi ultimi fanno fallire lo stato di parità pulita.
4. Un report con dati pubblici letti oggi non va convertito retroattivamente in un dato disponibile nel momento della decisione di trading.
5. La prova su copie offline serve a preparare l'audit; **non dimostra che la cache di produzione sia già completa**.

### Esecuzione SOLO su due file offline, nessun network

Esempio dopo aver già ottenuto e custodito in sicurezza le due fotografie:

\`\`\`bash
python3 scripts/cot_intelligence_parity.py \
  --public /percorso/offline/cftc-public.json \
  --private /percorso/offline/remura-cot-copy.json \
  --report-dates 2026-11-10,2026-11-17 \
  --now-utc 2026-11-23T19:00:00Z
\`\`\`

Per generare la fotografia della **copia** privata (mai il database live):

\`\`\`bash
python3 scripts/cot_intelligence_snapshot.py \
  --db /percorso/copia-offline/remura-prices.sqlite3 \
  --limit 5000 > /percorso/offline/remura-cot-copy.json
\`\`\`

Non esiste attualmente nel repository un export pubblico completo della prova del 23/11: una nuova foto pubblica andrà ottenuta **solo quando necessario**, previa verifica dei limiti gratuiti e con provenienza e data proprie. Non usare dati finti per colmare l'assenza.

## Test automatici

- \`tests/cot-intelligence-fx-factors.test.js\`: scomposizione cross 28->7, segni valute, indice 52w, invalidità e as-of reale.
- \`tests/test_cot_intelligence_parity.py\`: controllo dei 28 valori attesi su due settimane, mismatch, checksum, catture sconosciute, report mancanti, data futura, duplicati, sola lettura.
- CI sul ramo PR \`.github/workflows/cot-intelligence-lab-checks.yml\`: standard Node 22/Python 3.11; nessun secret, nessuna richiesta HTTP, niente deploy.

## Prossimo gate

1. Portare una **copia offline autorizzata** del collector e una fotografia pubblica verificabile nella stessa macchina, confrontare i 28 report-code, verificare percentuale di timestamp locale coperta e discrepanze.
2. Su dati ufficiali conservati in modo corretto, calcolare il report dei 7 fattori reali per mostrare al Filone D solo un **contratto di output descrittivo**.
3. Eventuali correlazioni con prezzo futuro, benchmark e costi spettano al Filone A (nessuna conclusione qui).
4. La futura release UI dovrà presentare la versione con **data e ora Europe/Rome** in alto; in questa PR non si modifica alcun HTML.

**Cosa NON è stato fatto:** autenticazione sulla VPS, acquisizione o deploy di produzione, Cloudflare, nuovi utenti, merge, ordini sul broker. **Incremento di costo: zero euro** (soli script locali e CI esistente, senza nuovi servizi).
