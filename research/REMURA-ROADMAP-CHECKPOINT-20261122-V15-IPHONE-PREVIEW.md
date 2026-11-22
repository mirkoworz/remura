# REMURA — ROADMAP CHECKPOINT V15 — iPhone Preview — 22 novembre 2026 Europe/Rome

**V15: Anteprima reale senza nuovo deploy, non un altro laboratorio di test.** I checkpoint precedenti V01–V14 sono preservati. V14 documentato in research/remura-roadmap-v14-product-20261122/research/REMURA-ROADMAP-CHECKPOINT-20261122-V14-PRODUCT.md, commit a129d0fc8f11557b1735dd85ccee8feb9a9cb354. Non ripetere suite precedenti se non cambia codice inerente.

## Lavoro effettivamente consegnato
Branch separato: feature/shark-cockpit-v167-standalone-iphone-preview-20261122, basato su v1.67 HEAD ca707a1488067e726c2cb0d6f6afa32d569f2fa6.
- Unico file visualizzabile/downloadable da iPhone: preview/REMURA-Shark-Cockpit-v167-iPhone-STANDALONE-LAB.html, primo commit 7ef470db84398a7577a105f62192f38e12f0cabe; contenuto 52.888 caratteri, GitHub Blob SHA 47b3d7ad43bb942ecde1808117d7573beba13206.
- README: preview/README-REMURA-V15-IPHONE-PREVIEW.md, commit successivo 667d349cfe449a6890a4d9903807fcd07ee3759e.
- Inline senza framework/hosting: CSS del Cockpit v1.67; CFTC core; movers core; movers UI; browser UI. 4 moduli JS inlined e CSS incorporato. Non richiede alcun altro file app, no service worker. Nell'HTML sono presenti i movimenti netti fino a 6 contratti dell'ultimo martedi' comune, i 14 futures, preferiti locali e dettaglio fino a 12 report, Myfxbook retail distinto.
- Per i link ai moduli esistenti non presenti nel file locale sono usati URL della PRODUZIONE GIA' ESISTENTE; non e' stato toccato il sito. L'unica GET retail prevista usa il JSON pubblico https://raw.githubusercontent.com/mirkoworz/remura/main/data/myfxbook/latest.json, e la pagina mantiene le consuete GET al dataset CFTC pubblico solo all'apertura o sul click Aggiorna. Nessun token, nessun account, nessuna API Cloudflare/Oracle, nessuna scrittura di dati.
- Banner fisso "REMURA · v1.67 LAB · ANTEPRIMA LOCALE iPhone · 22/11/2026 21:41 CET · NON PUBBLICATA", robots noindex.

## Come aprirla — test iPhone sperimentale
Sorgente/autonomo GitHub:
https://github.com/mirkoworz/remura/blob/feature/shark-cockpit-v167-standalone-iphone-preview-20261122/preview/REMURA-Shark-Cockpit-v167-iPhone-STANDALONE-LAB.html

Visualizzatore HTML gratuito di terze parti, da verificare su Safari (non servizio REMURA, niente password):
https://raw.githack.com/mirkoworz/remura/7ef470db84398a7577a105f62192f38e12f0cabe/preview/REMURA-Shark-Cockpit-v167-iPhone-STANDALONE-LAB.html

Il provider raw.githack.com documenta un link development CDN per file GitHub pubblici, corretto Content-Type HTML e possibile conferma anti-phishing prima di aprire. Non vi e' garanzia di uptime o di compatibilita' CFTC Safari; web tool non ha potuto aprire/verificare l'URL specifico. Rawgit.hack e' di terzi, puo' vedere IP/user-agent; non autorizzare o inserire dati sensibili. Il branch resta pubblico perche' il repository principale e' pubblico; codice statico e nessun Secret inclusi. Non presentare il link come pagina REMURA ufficiale o deployed/QA Safari PASS.

## Verifica tecnica eseguita
Il file assemblato e' stato recuperato tramite GitHub e ispezionato senza chiamate CFTC, D1, Secrets o nuove CI:
12/12 verifiche statiche vere: doctype, esattamente 4 JS inline, CSS interno, zero script esterni, zero riferimenti di asset relativi, nessuna registrazione service worker, assenza di route private API, URL CFTC TFF/Disaggregated, sorgente retail GitHub pubblico, banner, robots noindex, tags script bilanciati.
Il Cockpit fonte v1.67 era gia' passato nella CI mirata [45068490604](https://github.com/mirkoworz/remura/actions/runs/45068490604) con 45/45; NON ripetuto. I 12 controlli di file packaging NON provano funzionamento Safari con rete CORS e dati reali.

## Priorita' successive V16
1. **Prova manuale iPhone una sola volta**: aprire il link sperimentale; verificare banner, lista CFTC, fino a sei movers, preferiti ☆/★, storia fino a 12 report, etichetta RETAIL e soprattutto il testo dello stato CFTC (due dataset/parziale/errore). Un solo screenshot dell'eventuale errore, evitando dati privati. Non eseguire nuovi test storici sulla sola base della prova visiva.
2. Se il visualizzatore di terze parti e' bloccato o la CFTC non funziona per CORS, NON attivare Cloudflare Worker per aggirarlo: valutare prima il file locale e successivamente ambiente preview a costo zero su hosting autorizzato, previa verifica Free e consenso esplicito.
3. Integrare i risultati della prova Safari con la roadmap prodotto, non aggiungere una seconda pagina radar duplicata.
4. Contributors: riusare form candidato v0.31 e UX LAB v0.87/v0.89 gia' costruiti; l'accesso reale Access/D1, ruoli e revoca devono essere verificati con quota Free e nuovo consenso. PR #105 resta DRAFT senza merge.
5. TradingView: prima finestra holdout V2 inizia 23/11 00:00 UTC (01:00 CET). La data non prova attivazione del Worker e primo timestamp CVD. Consentire solo read-only con nuova autorizzazione specifica e quota; CVD vs price-only alpha ancora NO-GO.
6. Mac/Oracle custodia collector v1.65, backup/root-owned, splash toro/orso 3D e radar Oracle Milano rimangono separati e non modificati; PR #106 TV DRAFT.
7. Rispettare versione/timestamp Europe/Rome in cima a tutte le pagine realmente modificate. V15 aggiunge solo il file preview autonomo con il banner v1.67, non aggiorna il sito esistente. Nessuna spesa o deploy.

**Verdetto:** un file HTML effettivo da aprire su iPhone in anteprima, nessun cambio main/Pages, nessun costo nuovo, codice originale v1.67 invariato, 12 check packaging, attendiamo solo prova Safari reale. 
