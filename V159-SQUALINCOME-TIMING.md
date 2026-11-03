# REMURA v1.59 — misurazione tempi scansioni Squalincome (prototipo offline)

**Data:** 03/11/2026. **Stato:** candidato offline su PR #76, release UI e strumenti di collaudo in preparazione. VPS rimane v1.58, post-ingest già attivo. Nessun deploy o modifica ai dati VPS.

## Motivazione verificata
Diagnostica privata #27: 2 osservazioni dopo l'ultima full scan, evidenza indiretta; 12 esclusioni H1 stale e nessuna M15/H4 stale. Dobbiamo distinguere funzionamento tecnico, velocità e utilità statistica.

## Strumentazione
- Nuova tabella privata SQLite `squalincome_scan_timing` **solo nel futuro rilascio**, append con massimo 256 righe e pulizia in transazione; nessuna colonna con simboli, prezzi, credenziali o payload.
- Per `post_ingest` e `periodic`: inizio/fine UTC, durata monotona ms, successo/errore, numero simboli esaminati, numero eventi nuovi. Per post-ingest anche orario fine batch e intervallo fine-batch→fine-scan, **non** candela→segnale.
- La risposta privata `/private-api/signals/status` avrà `scanTiming` con soli contatori aggregati, mediane e ultimi timestamp; chiavi esistenti mantenute, UI non modificata.
- Errori del modulo telemetria non devono impedire una scansione valida; guardie H1/M15/H4, deduplica, storici e 34-mercati diagnostica generale non devono cambiare.
- Niente nuove API, polling o acquisizioni cTrader. Test solo offline prima di un eventuale installer v1.59 protetto.

## Rilascio manuale predisposto ma non eseguito

Gli script `release_v159.py` e `reconcile_v159.py` sono ora disponibili in PR #76 e hanno superato test offline. L'installer valida il **codice** live v1.58 immutabile, ammette lo stato autoupdater `data_only` (solo Myfxbook) senza cambiare `installedSha`, richiede il flag post-ingest ON, genera backup SQLite con restore-test e rollback per 13 file esistenti + rimozione controllata del nuovo modulo. `reconcile_v159.py` non installa codice, ma verifica 14 file e manifest prima di aggiornare il solo SHA.

**Importante:** `v1.59` in GitHub non significa installata: sulla VPS rimane v1.58. Non fare deploy automatico, non usare `--init-sha` né reinstallare la v1.58.

## Gate per il rilascio
1. Entrambe le CI verdi e test su SQLite, tempo UTC, registrazioni multiple, retention e assenza di segreti.
2. Installer v1.59 immutabile con controllo esatto dei file v1.58 live (comprese eventuali configurazioni private senza esposizione), preflight `--check` e `--apply` separato, snapshot SQLite restore-test e rollback, lock autoupdater.
3. Versione v1.59 + data/ora **italiana reale** in cima alle 9 pagine; invalidazione cache PWA; riconciliazione SHA e diagnostica privata GitHub.
4. Valutare i dati per più cicli (non uno snapshot): latenza tecnica, fallimenti, duplicazioni e confronti con il percorso periodico, senza promettere trade migliori. Per il vantaggio sui segnali servono timestamp di chiusura candela/pivot e una metodologia controfattuale rigorosa.
5. Firestore, quote broker, consumo OCI e fatturazione verificati o esplicitamente N/D.

## Futuro
Timestamps per singolo simbolo cTrader salvataggio→analisi→eventuale evento e controllo del benchmark, preservando privacy; poi PR #71 prezzo–CVD e Radar.
