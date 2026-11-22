# REMURA — Shark Cockpit v1.67 LAB — Anteprima autonoma iPhone (V15)

22 novembre 2026, Europe/Rome. Solo anteprima; nessun deploy o merge.

## Apri da Safari su iPhone (senza modificare il sito ufficiale)

File unico:
preview/REMURA-Shark-Cockpit-v167-iPhone-STANDALONE-LAB.html

Sorgente GitHub:
https://github.com/mirkoworz/remura/blob/feature/shark-cockpit-v167-standalone-iphone-preview-20261122/preview/REMURA-Shark-Cockpit-v167-iPhone-STANDALONE-LAB.html

Possibile vista HTML tramite caching proxy di terze parti (SOLO TEST):
https://raw.githack.com/mirkoworz/remura/7ef470db84398a7577a105f62192f38e12f0cabe/preview/REMURA-Shark-Cockpit-v167-iPhone-STANDALONE-LAB.html

Il dominio raw.githack.com NON appartiene a OpenAI, GitHub o REMURA; serve in HTML il file pubblico da GitHub con Content-Type adeguato. Puo' mostrare una conferma anti-phishing. Non inserire password, indirizzi, token, chiavi, dati privati o livelli Contributors in questa anteprima. Se Safari segna il sito come pericoloso, NON aggirare il blocco; usare il file direttamente oppure fermare la prova.

Non esiste qui una distribuzione su GitHub Pages, Cloudflare Pages, Firebase, Netlify, Vercel, un dominio nuovo o qualunque backend attivato. Non aprire accesso ai collaboratori attraverso questo URL.

## Come e' stata prodotta
- Branch originario verificato: feature/shark-cockpit-v167-movers-lab-20261122 HEAD ca707a1488067e726c2cb0d6f6afa32d569f2fa6, con 45/45 suite mirata GREEN GitHub Actions run 45068490604.
- Branch indipendente preview: feature/shark-cockpit-v167-standalone-iphone-preview-20261122, commit di generazione 7ef470db84398a7577a105f62192f38e12f0cabe.
- HTML 52.888 caratteri: CSS del Cockpit inline, moduli core CFTC/Movers/Movers UI e browser UI inline, nessun file CSS/JS interno necessario, nessun service worker installato, nessun Secret incluso.
- Il menu del sito non e' incluso, perche' i suoi percorsi verso altre pagine non funzionerebbero da file locale. I riferimenti ad altre pagine sono esplicitamente link al sito gia' pubblicato; questa anteprima resta separata.
- La GET retail del solo file pubblico data/myfxbook/latest.json e' indirizzata a raw.githubusercontent.com/mirkoworz/remura/main/data/myfxbook/latest.json. Le GET CFTC TFF/disagg restano quelle pubbliche gia' implementate nella app; se CORS/rete/limitazioni Safari le bloccano, l'interfaccia segnala assenza dei dati, non inventa valori.
- Watchlist (14 codici CFTC whitelist), storico fino a 12 report e 6 movers del piu' recente martedi' confrontabile sono incorporati. Non contiene dataset CFTC fittizi incorporati e non trasforma mai COT futures in spot FX. No raccolta privata, no prezzi, no ordini.
- Il timestamp versione in cima al file e' v1.67 LAB 22/11/2026 21:41 CET. Non e' stata modificata alcuna altra pagina REMURA e non e' stato creato un nuovo numero di release di produzione.

## Verifiche e limiti
Dopo creazione, recupero del file GitHub e 12 controlli statici completi: doctype corretto, quattro script inline, CSS inline, nessuna dipendenza relativa, nessun script esterno, zero registrazioni service worker, zero route private, CFTC URLs ufficiali presenti, GET retail pubblico presente, banner preview, robots noindex, script tag chiusi. TUTTI veri.

Le 45 prove verdi sono relative al codice v1.67 del Cockpit prima dell'assemblaggio in un solo file; i 12 controlli statici di assemblaggio NON sono un test Safari visuale, non attestano HTTP 200 del proxy e non garantiscono CORS CFTC. Non creare nuove richieste Cloudflare/D1 o test live non autorizzati per compensare.

## Prova manuale minima proposta
1. Apri il link di visualizzazione da Safari su iPhone. Se appare una pagina di conferma, controlla dominio e nome file, non inserire credenziali.
2. Verifica se compare il banner v1.67 LAB e la sezione "Le mosse piu' grandi dei fondi".
3. Controlla il messaggio CFTC: entrambi i dataset caricati oppure parziale/errore. Se errore, screenshot del SOLO stato UI, senza dati sensibili.
4. Prova ☆ su EUR e USDJPY, attiva Solo seguiti e apri il dettaglio storico. Se la persistenza nel browser e' negata, il file informa che conserva preferiti solo fino alla chiusura.
5. Controlla Myfxbook marcato retail e, se il suo snapshot e' vecchio, ARCHIVIATO. Non confondere con le categorie CFTC.

## Gate successivi
Una vera preview sotto un dominio REMURA richiedera' una nuova autorizzazione specifica, verifica budget gratuito e separazione totale dal main; per Contributors restano necessari Access/D1 autentici, ruoli reali e collaudo revoca. Nessuna attivazione di pilot in questa versione.

Il provider statico esterno non offre garanzie di disponibilita'; puo' vedere l'IP e la user-agent del browser. Solo file pubblici, nessuna credenziale. Per riservatezza usare il file locale o un futuro hosting di anteprima REMURA autorizzato.
