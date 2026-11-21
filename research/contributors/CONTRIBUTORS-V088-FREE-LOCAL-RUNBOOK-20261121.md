# REMURA Contributors v0.88 LAB — Free Budget Checker iPhone OFFLINE

**21/11/2026 ore 18:56 CET (Europe/Rome)**

Nuovo file autosufficiente `research/contributors/contributors_free_local_v088_lab.html`, in italiano, progettato per Safari iPhone. Calcolo lato dispositivo su numeri **inseriti manualmente**: righe lette/scritte D1, richieste Workers, numero DB, byte D1 totali/per DB, seat Access usati e totali, istante UTC osservazione.

- Soglie nominali controllate sulle pagine ufficiali D1 in data 21/11/2026: 5.000.000 letture/giorno, 100.000 scritture/giorno, 10 DB, 5GB storage account, 500MB per DB. Workers 100.000 richieste/giorno è il riferimento nominale da ricontrollare sul piano specifico.
- Fonti pubbliche: https://developers.cloudflare.com/d1/platform/limits/ , https://developers.cloudflare.com/d1/platform/pricing/ .
- Soglia di attenzione volontaria al 70% (più prudente dei limiti assoluti).
- Non usa account ID, token, email, user ID; nessun browser storage, cookie, clipboard, link esterno, fetch o rete: CSP `connect-src 'none'`. Il calcolo è volatile e `Cancella tutti i dati` svuota i campi. Le cifre potrebbero essere falsificate o errate: NON costituiscono prova del provider.
- Output **STAGING NO-GO SEMPRE**, anche con tutti i valori sotto la soglia. Se il GraphQL giornaliero è vuoto, lasciare D1 letture e scritture vuote; **UNKNOWN non è zero**. Seats Access reali non noti senza login Cloudflare privato.
- Banner versione v0.88 e data/ora in altissimo, come richiesto. Nessuna modifica alle 4 pagine private v0.78 o al router, nessun deploy Cloudflare o GitHub Pages, nessuna registrazione utente.
- Nuovo test `test_free_local_v088_lab.mjs`: 22 casi dinamici Node sandboxati di input/limit/freschezza/NO-GO più CSP; workflow GitHub one-shot da verificare prima di dichiarare PASS.
- Dato storico noto: monitor Cloudflare 21/11 `44919682812` = D1 daily UNKNOWN; 199 Workers richieste stimate, D1 4 DB e 6.557.696 byte. Questi **non** sono stati usati per riempire i campi, affinché dati del giorno invecchiati non siano presentati come attuali.
- Collaudo reale Access Free / D1 necessita autorizzazione separata; non fare query o deploy senza consenso specifico.

## Roadmap
1. Consenso specifico per controllo provider SOLO LETTURA, minimo possibile e senza PII. Valutare configurazione quote e capacità Access. Se UNKNOWN, nessun utente reale.
2. Pilot 1–2 collaboratori su Access/D1 fixture isolato con deny-default e verifica Safari logout/revoca; leggere REMURA e scrivere soltanto propri livelli; OWNER approva, RESERVED non auto-retry, original-level e amendment indipendenti.
3. TradingView v0.8.186 LAB, holdout 23–29/11 e 30/11–6/12 UTC, no real capture/anchor; Shark Science v0.4 codice COT, retail, CVD locale già esistente, dati indipendenti mancanti e nessun edge dimostrato.
4. Experience v0.30 splash toro/orso, logo SMF, Private Capture non attivo, Oracle collector preservato, Ampere Radar Telegram operativo, backup e Squalincome mantenuti.

Nessuna modifica main, Oracle, Secret, costo o release live. Mac non richiesto.
