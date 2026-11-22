# REMURA — ROADMAP V14 PRODUCT CHECKPOINT — 22 novembre 2026, Europe/Rome

**Nuovo progresso sul prodotto reale: Shark Cockpit v1.67 LAB.** Il checkpoint V13 resta in research/remura-roadmap-v13-product-20261122/research/REMURA-ROADMAP-CHECKPOINT-20261122-V13-PRODUCT.md (commit cdf63aa674fea9259aa3f22df3b495ea73491289). Non rifare test o lavori storici senza modifiche che lo richiedano.

## Nuova funzionalita': le mosse dei fondi
- Branch prodotto: feature/shark-cockpit-v167-movers-lab-20261122; commit verificato con CI GREEN: ca707a1488067e726c2cb0d6f6afa32d569f2fa6.
- Nuovo modulo shark-movers-core.js: calcola fino a sei maggiori movimenti netti COT in punti percentuali di open interest, scegliendo la categoria che ha cambiato maggiormente il posizionamento sul singolo futures. Prende solo contratti con delta settimanale disponibile e validato rispetto alla settimana esattamente precedente (preparato dal core della v1.66). Confronta esclusivamente i futures con data report dello stesso piu' recente martedi'; non mescola oro, EUR, indici e altre rilevazioni appartenenti a martedi' differenti; rende esplicito quante altre settimane sono escluse. Le categorie restano denominate precisamente: Asset Manager e Leveraged Funds su TFF; Managed Money e Producer/Merchant su Disaggregated.
- Nuovo shark-movers-ui.js: DOM della sezione "Le mosse piu' grandi dei fondi", fino a sei schede toccabili su iPhone che portano alla corrispondente scheda future sullo stesso Cockpit. TextContent, nessuna interpolazione HTML remota, nessuna chiamata API. Solo report settimanali pubblici, NON transazioni identificabili, first-seen indipendente, prezzo spot o segnali di acquisto/vendita.
- shark-cockpit.html/css/js: montaggio reale di sezione visibile, card responsive iPhone, focus/scroll navigabile. Permangono le 14 schede futures e i filtri famiglia, ricerca, preferiti locali, storico fino a 12 report CFTC, retail Myfxbook separato. I movers riutilizzano il contenuto CFTC gia' caricato dal Cockpit, senza nuove GET.
- nav.js e tutte le dieci pagine REMURA dell'anteprima: numero in alto aggiornato **v1.67 LAB · 22/11/2026 21:41 CET (anteprima, non pubblicata)**, nav.js?v=167. Il contenuto delle vecchie pagine non e' stato riscritto, solo riferimento alla nuova versione del menu. Mac Experience/splash Toro-Orso non modificato.
- sw.js: cache statica remura-shell-v81-v1.67-shark-cockpit-movers-preview e i due nuovi moduli; non conserva i CFTC come dati live.
- SHARK-COCKPIT-V167-MOVERS-20261122.md: handoff di prodotto sul branch.
- tests/shark-movers.test.js: 12 test nuovi mirati, oltre 33 verifiche della pagina e della release realmente interessate dalle modifiche. Workflow .github/workflows/remura-shark-cockpit-v167-movers.yml: branch/path-filtered, 4min, permissions contents read, niente Secret/deploy/provider.

## Collaudo effettivo e correzione
- Primo run 45068438773 FAILED 42/45: l'interfaccia selezionava il gruppo maggiore ma il modulo non traduceva correttamente la chiave interna first/second nell'indice numerico dell'etichetta categoria, causando categoria non mostrata nei risultati. Un test release verificava ancora la regex v1.66.
- Correzione codice e regex in due commit sul branch; secondo run 45068487367 non ancora sufficiente per la regex, non necessita ripetizione.
- Run finale GitHub Actions **[45068490604](https://github.com/mirkoworz/remura/actions/runs/45068490604)**: SUCCESS sul commit ca707a1488067e726c2cb0d6f6afa32d569f2fa6, job logs letti realmente: '# tests 45', '# pass 45', '# fail 0', 'REMURA_SHARK_COCKPIT_V167=45_45_PASS'. Nuove 12 prove + 33 verifiche delle parti di pagina/versione davvero cambiate. NON rieseguite le grandi suite storiche CVD, COT, Mac o Oracle.
- Una CI GREEN non dimostra che il browser Safari riceva davvero oggi tutti i contratti CFTC o che questi siano disponibili secondo il protocollo causale; e' ancora necessario collaudo visivo reale e provider GET dal browser.

## Sito, anteprima e sicurezza
- GitHub repo main **9758bdcbf1c55b1c63ad66bcf6716872cdc906e4**, verificato invariato durante V14; prodotto su branch isolato, NON merge, NON pubblicato su produzione. README storico documenta il sito Pages https://mirkoworz.github.io/remura/ ma questo NON contiene la nuova pagina v1.67; GitHub Pages non pubblica automaticamente la pagina contenuta in un branch differente. La Pages API non e' interrogabile con il connettore GitHub corrente; non inventare URL di preview.
- NO deploy Pages/Cloudflare, non cambiati Oracle, D1, Access, Webhook, Secret, codici collector, Mac, prezzi o timer. Nessuna spesa e nessun nuovo servizio/polling. Il margine Cloudflare Free resta NON ATTESTATO; non eseguire chiamate GraphQL gia' autorizzate in passato e consumate.
- Existing Contributors: riusare research/contributors/contributors_candidate.html e preview mobile v0.87/v0.89, role/scope v0.94 e PR #105 DRAFT, senza duplicare UI o distribuire credenziali e scritture D1 prima delle verifiche di Access/quote Free, owner/contributor scopes, login/logout/revoca reale Safari.
- TradingView CVD: il gateway TEST storicamente attivato 14 novembre non prova lo stato attuale; PR #106 DRAFT. Protocollo V2 holdout1 parte il 23 novembre 2026 00:00 UTC (01:00 CET), niente backfill retrospettivo, niente alpha dichiarato senza ricevute indipendenti, denominatore M5 e price-only comparator.
- COT v0.7 coorti e v0.8 futures/spot mapping restano scientific LAB, non integrati come prova istituzionale live; cockpit legge API CFTC public nel browser e segnala il carattere settimanale.
- Remura collector Oracle v1.65, backup antirollback, splash 3D toro/orso e Ampere Radar Telegram restano agli altri filoni separati e non sovrapposti.

## V15 — priorita' concreta
1. **Anteprima Safari iPhone davvero navigabile:** verificare una modalita' di preview non produttiva e gratis, con consenso specifico prima di deploy e controllo dei limiti Free. Non presentare la pagina GitHub blob come un sito funzionante. Controllare su Safari i 14 contratti, i 6 movers, preferiti ★, storico, CFTC CORS e Myfxbook.
2. **Contributors vero:** riusare la form candidato esistente, non creare altri simulatori; solo dopo verifica Cloudflare Free, Access seats, auth server, 1–2 identita' reali, scope e revoca testata con nuova autorizzazione. Niente utenti/Worker live ora.
3. **Holdout prospettico CVD:** chiedere specifica nuova autorizzazione READ-ONLY, previa quota, per stato reale Worker TEST/Alert e successivi dati temporizzati, senza consumi in autonomia.
4. Solo dopo preview/consensi, preparare rilascio controllato in sincronia con Mac Experience e Oracle custodia, mantenendo versioni e timestamp su tutte le pagine.
5. Continuare FREE-FIRST e verificare di tanto in tanto Actions/Cloudflare D1/Access/Oracle; non dichiarare quote gratis verificate finche' non provate.

**Conclusione:** V14 e' costruzione concreta: nuova panoramica dei fondi con confronto corretto di date e categorie, 45/45 tests, nessun deploy e nessun costo nuovo. Non ancora visibile su Safari pubblico.
