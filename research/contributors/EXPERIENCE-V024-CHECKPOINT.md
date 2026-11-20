# REMURA Experience v0.24 LAB — Checkpoint — 20/11/2026 23:16 CET

## Branch e commit
- Ramo dedicato: research/experience-disposition-v024-20261120, partito dal checkpoint v0.23 60f1bff71dc8d352870e1ec9d848530d47062b7e.
- Gateway: research/contributors/disposition_gateway_v024_lab.mjs — commit 5c3ba08fba8bfcb1085a04420b3954aa555db5b4, blob 9f0f6a85b9bcdb0d356622599df66af293fd2815.
- Test: research/contributors/test_disposition_gateway_v024_lab.mjs — commit a322052ce3b35fccfd96500f5160bdf767eb028e, blob fc25ff3a70ebb4edc71eb9984552d820140840b5.
- Entrambi i blob su GitHub coincidono con le impronte Git dei file locali collaudati.
- Experience v0.22 originale invariata su research/contributors-experience-20261120 @ 3971c0af7b6a802a9d3566c4345e804d1ffdefbe.
- Checkpoint Mac separato invariato su codex/mac-experience-checkpoint-20261120 @ 57b8612dc30015046f36936e7a9fbf8298f41c88.
- Nessun HTML, logo SMF, asset toro/orso, nove frame o modulo Home originale modificato. Versione/data/ora dovranno figurare in alto nelle eventuali nuove pagine, non in questa fixture di servizio.

## Risultato LAB
Implementato gateway offline di ammissione alla vista V2, con cinque interfacce iniettate: lettura coerente, verifica di autenticità dell'autorità, lettura di pin indipendente, autorizzazione e orologio. Queste interfacce sono simulate nei test e NON rappresentano un servizio o custodia reale.

- PUBLISHED + prova sintetica approvata + testimone coerente + ruolo/soggetto + scadenza + vista V2 verificata: status 200, solo proiezione V2.
- ABANDONED: status 410 senza dati di mercato.
- PENDING: status 409 senza dati di mercato.
- Ruolo/soggetto non ammesso, revoca o cambio sessione: status 403 senza dati di mercato.
- Testimone, verifica, formato, scadenza, clock, proiezione o revisione non validi: status 503 senza dati di mercato.
- Cache-Control: no-store, max-age=0; Vary: Cookie, Authorization.
- Ricontrollo ruolo e pin dopo proiezione, prima della risposta. Nessuna garanzia di revoca istantanea dopo la consegna reale.
- Compatibilità con il consumer_v021.mjs esistente: dopo refresh 409/410 il valore precedentemente visibile viene nascosto; Home v0.22 riceve null al render successivo. Nessuna notifica push implementata, quindi non si garantisce sparizione immediata senza refresh.

## Test nuovi realmente eseguiti
- Ambiente: container Linux locale, Node.js v22.16.0, niente rete in runtime di prova.
- Comando: cd research/contributors && node --test test_disposition_gateway_v024_lab.mjs.
- Esito verificato due volte: 33 PASS, 0 FAIL.
- Dipendenze originali ricostruite identiche dai blob Git:
  * consumer_v021.mjs: 44ca4fabc9ba3fde07ea5d9a5be570e3bdebe5d1.
  * validate_shared_fixture_v011.mjs: 4d7d55e8e9854cfedc40271ce5e479808ae33787.
  * home_v022.mjs: c73458f3c742e204cc4bd3d71f80e88c36906b64.
- Verificati: 200 valido, 409/410 senza numeri, testimone mancante/obsoleto/modificato, proof mock fallita, ruoli diversi, revoca e cambio sessione, generazione o versione sbagliata, contenuto privato e dati invalidi, scadenza e regressione orologio, revisione incoerente, risposte tardive e logout, aggiornamento client/Home da 200 a 410 e 409.
- Nessuna ripetizione di 366 verifiche Experience precedenti, 40 Safari Mac, 21 test v0.23, Witness o prova APFS.

## Limiti aperti — NO-GO
1. Verificatore di autenticità mock e pin indipendente mock. La funzione non implementa protezione con firme reali, gestione di credenziali o un'ancora indipendente resistente al ripristino. Un verificatore deliberatamente permissivo può aggirare la sicurezza.
2. L'adapter non esegue readConsistent atomico su tre database o CAS distribuito: esige queste proprietà dal chiamante ma non le dimostra.
3. HTTP è simulato come oggetto JavaScript; nessun server, nessun Contributor reale, nessuna revoca push. Il client rimuove i dati abbandonati al refresh, non senza alcun refresh.
4. Nessuna protezione dimostrata contro rollback simultaneo di tutti i domini; nessun ripristino/crash fisico in v0.24.
5. Ancora nessuna validazione di dati COT reali, identità dei trader istituzionali o redditività.

## Roadmap coordinata
- Experience v0.25: progettare testimone indipendente con controprova di freschezza monotona e piano di recupero dopo perdita, PRIMA di collegare gateway al backend.
- Contributors v0.56: LOCAL_MATCH_ONLY acquisito; preparare solo contratto autorizzazioni OWNER/CONTRIBUTOR. Binding, preview e deploy NON autorizzati.
- TradingView v0.8.181: holdout 1 23–29/11 UTC, holdout 2 30/11–06/12 UTC; soglie congelate.
- Shark Science v0.4: misurare baseline, campione, affidabilità, falsi segnali, nessun edge dimostrato.
- Mac custody: Witness 001–005, APFS, Debian Private Capture e Safari Mac preservati; Safari iPhone fisico ancora non collaudato.
- Oracle collector e v1.65: invariati; NO-GO installazione/autoupdater.
- Telegram livelli Contributors: progettazione futura, nessun invio reale.

## Costi/autorizzazioni
Nessun nuovo servizio, DB D1, risorsa Oracle, workflow hosted, provider di mercato o spesa. Test locali offline. Nessun merge, deploy, acquisizione reale o utilizzo di Secret. Quota Cloudflare/GitHub non rimisurata, saldo storico non attuale.

STATO: Experience v0.24 LAB, non produzione, non ancora connesso a backend reale.
