# REMURA — CHECKPOINT V20.5: recupero storico reale Myfxbook
Aggiornamento: **23 novembre 2026, ore 07:35 CET (Europe/Rome)**.
STATO: ricerca isolata; main e produzione invariati. Eredita integralmente tutti i checkpoint REMURA V01–V20.4.

## REAL DATA: recupero di 1.410 osservazioni precedentemente uscite dal file rolling
Main sorgente fissato al commit pubblico a1188f8af77951b9c59b7bb1facbfa6fe2f820e7.
- File storici Myfxbook: 34 simboli (30 attivi + 4 indici stale).
- Versioni storiche dei singoli file esaminate: **5.300**.
- Record attualmente visibili nei 34 file: **3.924**.
- Record storici univoci ricostruiti da tutte le revisioni: **5.334**.
- Record aggiuntivi che non appaiono piu' nel file rolling: **1.410** (circa +35,9% rispetto alle 3.924 correnti).
- Timestamp con valori in conflitto: **ZERO**; deduplicazione per coppia + timestamp, senza inventare osservazioni.
- Un esempio verificato: il file EURUSD attuale comincia il 24/10; una revisione Git del 28/10 conteneva osservazioni dal 16/10.
- Rispetto ai 3.822 record Capital DEMO ancora presenti nel repository PRIVATO, la somma puramente descrittiva 5.334+3.822 = **9.156** osservazioni di due fonti, non unite ne' pubblicate insieme, NON 9.156 decisioni/trade indipendenti.

## Prova e procedura
GitHub Actions https://github.com/mirkoworz/remura/actions/runs/45124731092
**SUCCESS**, 6 nuovi test PASS, recupero vero dal Git pubblico e zero API/provider/Cloudflare/Secrets.
- Nuovo motore research/v205_public_git_retention_recovery.py: uso solo di Git locale, sorgente main PINNED, tutte le revisioni per ciascuna coppia, rifiuto di JSON non valido, cronologie troncate, timestamp doppi o modificati, quarantena dei conflitti.
- Nuove verifiche research/test_v205_public_git_retention_recovery.py (6 test nuovi).
- Unico workflow non periodico .github/workflows/remura-v205-retail-git-recovery.yml: trigger solo quando nasce questo file sul ramo ricerca, permessi contents:read, nessun cron o deploy.
- Marker prova real-data: REMURA_V205_REAL_PUBLIC_GIT_HISTORY_RECOVERED=PASS.

## Archiviazione effettivamente persistita sul ramo research
Oltre ai soli log, e' stato salvato uno snapshot PUBBLICO compresso dei 5.334 record con metadati di provenienza Git nel ramo:
research/remura-v205-retail-git-history-recovery-20261123

Cinque file Base64, da ricomporre in ordine, dentro research/archives/:
REMURA-V205-MYFXBOOK-PUBLIC-a1188f8.part01.b64
REMURA-V205-MYFXBOOK-PUBLIC-a1188f8.part02.b64
REMURA-V205-MYFXBOOK-PUBLIC-a1188f8.part03.b64
REMURA-V205-MYFXBOOK-PUBLIC-a1188f8.part04.b64
REMURA-V205-MYFXBOOK-PUBLIC-a1188f8.part05.b64

Base64 totale **386.512 caratteri**. I contenuti letti DI NUOVO dal ramo GitHub sono stati comparati esattamente contro la sequenza Base64 del workflow reale: **uguali, senza tagli o divergenze**.
Impronta SHA-256 del binario compresso riportata dal workflow:
**c2b55a7c0db5dd8e6dd8ed53f643ef3b4cfe366db7132da41aaab7513b4e03b4**.

Ricostruzione locale gratuita, dentro il checkout del ramo di ricerca:
    cat research/archives/REMURA-V205-MYFXBOOK-PUBLIC-a1188f8.part*.b64 | tr -d '\n' | base64 -d > remura-v205-public-recovered.json.gz
    sha256sum remura-v205-public-recovered.json.gz
    gzip -t remura-v205-public-recovered.json.gz
    gzip -dc remura-v205-public-recovered.json.gz > remura-v205-public-recovered.json

La SHA-256 deve corrispondere all'impronta sopra. Non importare il dataset nel collector vivo senza piano, lock e autorizzazione.

## Salvaguardie scientifiche
I timestamps presenti in un commit Git e nei record Myfxbook non dimostrano autonomamente la prima pubblicazione del provider, ne' la disponibilita' prima di una decisione storica. Il campo first_visible_in_local_git_revision e' un puntatore Git, non una attestazione provider first_seen. Niente backtest retrodatati per affermare un vantaggio.
Si tratta di sentiment RETAIL, non posizioni dei grandi istituzionali. Molti record per coppia/strumento sono correlati. Un dataset piu' grande senza prezzi futuri ed eventi decisionali autentici NON prova alpha.

## Prezzi reali privati: prova storica ma nessuna prova attuale del 23/11
Dal log del vecchio workflow privato 44765941152 del 20/11 ore 15:42 UTC, il collector prezzi risultava running; ultimo open EURUSD M15 20/11 14:45Z, eta' 43 minuti; XAUUSD M15 ultimo open 14:45Z, eta' 43 minuti. Il controllo cTrader di quel giorno NON certifica il runtime o lo storico del 23 novembre.
Il probe V20.4 sul ramo research/remura-v204-private-price-coverage-20261123 e' GREEN con 9 nuovi test e converte i 12 receipt CVD M5 del 23/11 in solo 4 istanti possibili M15; NON ha avuto accesso al database locale del Mac o della VPS.

## Roadmap continua senza prove duplicate
1. **CVD**: ricevute vere nel TEST 12/12 nella finestra 23/11 04:30–05:25Z, run 45121703188; zero nuove chiamate Cloudflare da V20.3. Non ripetere query senza nuovo consenso limitato.
2. **Prezzi**: alla prossima sessione Mac/VPS consentita, controllare in sola lettura l'esistenza delle M15 EURUSD del 23/11, senza toccare collector v1.65/Mac, senza nuovi accessi broker.
3. **Retention**: storico pubblico Myfxbook recuperato e salvato durevolmente nella branch research. Per archiviare continuamente i nuovi cicli senza rifare 5300 letture Git serve successiva progettazione append-only e approvazione distinta prima di modifiche alla produzione.
4. **Contributors**: dashboard 23/11 conferma Workers 151/100k, D1 72/5M rows read e 288/100k write, 4/10 DB, storage 6.93 MB/5GB; non provati posti Access, Billing, permessi reali JWT e revoca. Pilot proprietario+1/2 amici resta NO-GO.
5. **BCE**: primo witness 28 cross ufficiali con reference_date 20/11 osservato 23/11 06:46 CET, non M15.
6. **Roadmap futura**: calcolare outcome prospettici con primi prezzi veramente osservati, controlli allineati e benchmark price-only, costi e periodi indipendenti, poi Cockpit v1.68 LAB, release Contributors, Splash Toro-Orso, custodia Mac. NESSUNA pagina HTML e' stata modificata; a ogni aggiornamento HTML reale serve nuova versione + data/ora Europe/Rome in cima ad ogni pagina.

## Costi/limiti
Nessuna nuova spesa o servizio: dati pubblici gia' in GitHub, esecuzione breve Actions su repository pubblico, archivio su un ramo GitHub research. Nessun deploy, merge, nuova programmazione, Oracle, Firestore, D1, Cloudflare, Myfxbook API o Capital DEMO API. Il main pubblico e il collector privato restano invariati.

**V20.5 conclusa: 1.410 nuovi record storici reali recuperati e custoditi; vera misurazione intraday delle previsioni ancora non dimostrata.**
