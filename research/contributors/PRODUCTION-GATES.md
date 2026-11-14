# REMURA Contributors — gate pre-produzione v0.14 LAB
14/11/2026 23:53 CET — DRAFT / NO-GO REAL / nessuna attivazione

## Perimetro candidato (decisione non approvata)
Separare raccolta collaboratori e analisi owner. Valutare Worker HTTPS dedicato + D1 dedicato, oppure servizio isolato con accesso solo a identità invitate; nessun riuso del Worker TEST TradingView, DB D1 telemetria o server privato. Un adapter futuro lato owner importa snapshot validati a sola lettura; nessun collegamento pubblico verso VPS/Tailscale, nessun Funnel, nessun accesso broker. Non scegliere o creare risorse finché costi e isolamento non verificati. Verificare condizioni/piani effettivi e quote aggregate Cloudflare/Oracle/GitHub prima della decisione, compresi overage, storage, invocazioni, analytics, e policy di arresto. Nessun prezzo o quota attestati da questo documento.

## Gate bloccanti per inviti reali
1. CI finale verde e review differenze isolate PR104; laboratorio Python non riutilizzabile direttamente come servizio. Staging nuovo senza dati reali e deploy esplicitamente autorizzato.
2. Scelta ingress/DB dedicati, origin HTTPS esatta, nessun percorso verso privato. Threat model: CSRF/replay, spoofing, XSS, IDOR, accesso cross-account, abuso richieste, token leakage, rollback, perdita DB e dipendenze. Rifiuto by default, budget per-request, rate limit e body cap prima di elaborazione.
3. GIS: creare client autorizzato solo per origin dedicata dopo scelta infrastruttura; libreria ufficiale per verifica token, firma/issuer/aud/exp, nonce monouso legato a sessione pre-login e CSRF. Non fidarsi di email o ruoli dal browser; identificatore stabile sub. Per bootstrap via invito verificare controllo email/subject, incluso caso indirizzi non gestiti da Google; owner esplicitamente autorizza binding. Nessun accesso Gmail/Drive, no password, no provider secret.
4. Sessione sicura server-side con revoca persistente, cookie Secure/HttpOnly/SameSite, rotazione, scadenza, verifica ruolo ogni operazione. Owner su superficie separata e protetta; nessuna commutazione ruoli demo. Test dopo restart, revoca e ripristino. Backup/restore coerenti, sospensione accessi dopo restore fino a riconciliazione revoche con registro affidabile separato; non riabilitare utenti tramite rollback.
5. Privacy: minimizzare identità, pseudonimi, retention e cancellazione account/contributi da concordare; niente token/PII nei log, niente credenziali provider nelle note. Informare collaboratori, verificare diritti di condividere livelli derivati dalle fonti.
6. Mapping effettivo per mercati iniziali con fonte/ticker/prodotto/contratto/anchor/tick verificati; restanti 67 candidati visibili ma non validati. Nessun prezzo o disponibilità inventati. Test reale solo dopo autorizzazione e piano separato.
7. Staging e collaudo iPhone: owner e due utenti test, inviti, rifiuto account sconosciuto, revoche, validazione server, separazione privata, verifica quote prima e dopo; nessuna pubblicazione o segnale automatico.

## Distinzione delle decisioni
Apertura Contributors e ammissione scientifica Level Confluence sono gate diversi. Anche dopo raccolta autorizzata, input manuali rimangono non ammessi a SQUALINCOME finché il protocollo prospettico E-R1 non è congelato, provenienza e completezza prezzi verificati e holdout indipendente valutato. No modifica B/D.

## Prossima azione
Verificare CI e architettura FREE candidata con fonti ufficiali e stato reale account prima di qualunque credenziale/deploy. Preparare adapter di verifica e test con fixture in ramo E. Nessun intervento manuale richiesto finché non è scelta una superficie autorizzata.
