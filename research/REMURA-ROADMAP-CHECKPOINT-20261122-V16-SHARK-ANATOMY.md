# REMURA — ROADMAP V16 / SHARK ANATOMY PRODUCT — 22 novembre 2026 (Europe/Rome)

Checkpoint successivo alla V15 iPhone Preview. EREDITARE V01–V15, non rifare test gia' verdi salvo codice realmente cambiato. V15: research/remura-roadmap-v15-iphone-preview-20261122/research/REMURA-ROADMAP-CHECKPOINT-20261122-V15-IPHONE-PREVIEW.md, commit 28655b0c90de99291db4bb2fb2edc283646da963.

## Conferma utente e obiettivo
L'utente ha detto **"Funziona"** dopo aver aperto l'anteprima iPhone V15 (v1.67). Questo e' un feedback positivo sul caricamento della schermata su iPhone; NON prova automaticamente disponibilita' di entrambi i feed CFTC, origine first-seen o metriche real-time. Da questo checkpoint e' stata realizzata una funzionalita' utile per approfondire gli "squali", anziche' altri test teorici.

## FUNZIONE COSTRUITA: REMURA SHARK ANATOMY v1.68 LAB
Branch prodotto: feature/shark-cockpit-v168-flow-anatomy-20261122.
HEAD dopo documentazione: 1a3eabc87b49563cf75812cc32d15e61592a26c7.
Versione/testo in cima alle 10 pagine preview: v1.68 LAB · 22/11/2026 22:10 CET (non pubblicata).
Cosa fa: in ogni scheda del futuro CFTC, sotto categorie e schede storiche, apre "Radiografia del movimento · long e short reali", con i conteggi attuali e delta settimanali di contratti:
- per Asset Manager e Leveraged Funds: TFF futures;
- per Managed Money e Producer/Merchant: Disaggregated metalli/WTI;
- contratti long attuali e cambiamento da martedi' precedente;
- contratti short attuali e cambiamento da martedi' precedente;
- netto long-short e cambiamento in contratti, distinto dai pp del netto/open interest; OI corrente e differenza settimanale.
- Nessun nuovo download/provider: deriva dai dati gia' caricati nel browser CFTC dallo Shark Cockpit.
- Ammesso soltanto con gli stessi due report recenti, validi e martedi' consecutivi previsti dal core preesistente. Se manca settimana, e' vecchio o dati stessa data sono discordanti: N/D senza inferenza.
- Non deduce 'nuovi acquisti', 'short covering', transazioni, ordini identificabili o opening/closing da due fotografie CFTC. Prova causale/alpha ancora NON verificata.

File interessati: shark-cockpit-core.js (anatomyFor), shark-cockpit.js (pannello interattivo), shark-cockpit.css, shark-cockpit.html, nav.js (banner versione), sw.js (nuova cache shell v82-v1.68-shark-cockpit-anatomy-preview) e nove HTML legacy con solo cache bust nav.js?v=168. Splash Toro/Orso Mac e resto dell'app non modificati.

## TEST MIRATI GREEN — NON RIFARE SUITE STORICHE
Nuovi 12 test in tests/shark-anatomy.test.js + 45 test di prodotto coinvolti (shark-movers.test.js, shark-cockpit.test.js, release-consistency.test.js). Workflow nuovo .github/workflows/remura-shark-cockpit-v168-anatomy.yml: push solo branch/path, read-only contents, runner timeout 4min, nessun provider, secret, deploy.
Prima CI run 45070861265 56/57, falliva solo una versione v1.67 test di wiring; corretta.
**CI verificata finale SUCCESS**: [45070919371](https://github.com/mirkoworz/remura/actions/runs/45070919371), commit testato 5774604d6b40eea60fb8589b9ffe78ad12ba703d. Log letti: '# tests 57', '# pass 57', '# fail 0', REMURA_SHARK_COCKPIT_V168=57_57_PASS. Dopo green solo nuovo file anteprima/documentazione, niente modifiche ai moduli eseguibili testati.

## ANTEPRIMA AUTONOMA iPHONE v1.68 — LINK VERO
File creato nel branch prodotto:
preview/REMURA-Shark-Anatomy-v168-iPhone-STANDALONE-LAB.html
Primo commit contenente l'anteprima: 21f7871d153cdad8f894283afb147d3059f62cce.
SHA blob verificato dopo il salvataggio: 2b60b0dd5dce80b0c16a3eb51b0276a084889c6e.

Link sperimentale visualizzatore esterno gratuito, SENZA deploy:
https://raw.githack.com/mirkoworz/remura/21f7871d153cdad8f894283afb147d3059f62cce/preview/REMURA-Shark-Anatomy-v168-iPhone-STANDALONE-LAB.html

Sorgente GitHub:
https://github.com/mirkoworz/remura/blob/feature/shark-cockpit-v168-flow-anatomy-20261122/preview/REMURA-Shark-Anatomy-v168-iPhone-STANDALONE-LAB.html

README sul branch:
preview/README-REMURA-V16-SHARK-ANATOMY.md.

HTML standalone statico 59.491 caratteri con CSS e quattro JS inline; link relativi eliminati, link menu esterno alla REMURA Pages gia' pubblicata; Myfxbook retail letto dal file pubblico raw.githubusercontent.com, CFTC via GET pubblici browser; non importa o dichiara DATI REALI GIA' RICEVUTI. Se i dati mancano la UI dice N/D. Nessun server aggiunto o nuovo billable provider.
12 controlli di packaging TRUE dopo salvataggio (DOCTYPE, style, 4 script inline, zero source esterni, zero relative assets, anatomyFor collegata, date/weekly gate, CFTC/public retail, noindex, banner, script balance); NOTA: packaging test NON equivale a Safari/HTTP/CFTC validato; e' da provare il nuovo pannello v1.68 su iPhone.

Raw.githack e' un visualizzatore di terzi (non proprieta' REMURA), potenzialmente espone IP/UA. Non inserire password, token o dati privati. Se browser avvisa rischio non aggirare blocco. V15 versione precedente si apriva secondo feedback utente, ma il nuovo link v1.68 non e' ancora stato confermato visivamente.

## Stato globale: sicurezza e gratis
- MAIN verificato invariato: 9758bdcbf1c55b1c63ad66bcf6716872cdc906e4; nessun merge, GitHub Pages, Cloudflare Pages, Worker, D1, Oracle modificati da questo intervento.
- Myfxbook retail e' campione separato, non istituzionali; i valori CFTC sono futures settimanali e non flusso ordini Forex.
- CVD TEST e holdout V2: lunedi' 23 novembre 2026 00:00 UTC / 01:00 CET parte il primo fold. Senza primi timestamp indipendenti e receiver live realmente verificato non esistono alpha/squal-shark signals provati. Non fare chiamate Cloudflare/GraphQL non autorizzate.
- Cloudflare D1 Free/account headroom UNKNOWN_NO_GRAPHQL_DATA (precedenti 2 GET GraphQL consumati); Access seats/free, spazi e costi non attestati. Nessun uso Secret reale; non promettere pilot Contributors attivo.
- Contributors: riutilizzare LAB v0.94 least privilege + prototipo web esistente, PR #105 DRAFT, proprietario approva, collaboratori solo livello proprio; non aprire accesso reale o permettere scritture altrove finche' non sono verificate autorizzazioni/budget.
- TradingView PR #106 DRAFT; Mac Codex gestisce Experience splash Toro-Orso realistico 3D, backup, collector Oracle v1.65 root-owned staged/antirollback; no sovrapposizione.
- Ampere Radar Telegram per disponibilita' free Oracle Milano rimane in repo separato attivo.

## Next concrete steps V17
1. iPhone Safari: aprire il link v1.68 e visualizzare "Radiografia del movimento". Verificare che CFTC risponda e il pannello mostri per ogni gruppo delta long, delta short, netto e OI. Se manca un report, N/D e' corretto; non inventare. Basta un breve feedback, non rifare suite per successo visivo.
2. Se UX approvata, predisporre preview a dominio REMURA separato dal live, ma ogni deploy/hosting/merge richiede consenso esplicito e verifica quota Free. Nessuna pubblicazione automatica.
3. Evitare creare un altro scanner duplicato: integrare questo cockpit con l'esistente in un percorso coerente quando pronto.
4. Avanzare il vero portale Contributors usando frontend LAB gia' presente, login Access con autorizzazione reale, quota D1, revoca e ruolo minimo prima di 1-2 amici piloto.
5. Verificare lo stato reale di CVD TEST e ricevute del holdout solo su mandato separato READ-ONLY e dopo prova Free. Prima delle prove niente anticipazione squali/edge affermato.
6. Mantenere numero progressivo aggiornamento e data/ora Europe/Rome in cima a ogni pagina realmente modificata, preservare tutte le roadmap precedenti e non rifare test gia' superati senza causa nuova.

**Esito V16: funzionalita' reale aggiunta al Cockpit e nella preview iPhone, CI 57/57, 12 packaging check, zero nuovi costi e nessun deploy.**
