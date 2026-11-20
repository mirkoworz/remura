# REMURA Contributors — Gate accessi reali v0.57 — SOLO DESIGN
20/11/2026 23:18 CET. Questo file non aumenta la versione del codice Contributors v0.56 e NON autorizza alcuna attivazione.

## Base congelata
Contributors v0.56 LAB: branch research/contributors-offline-20261114, HEAD 21338d4a405b0a3053e5a51322f8643c428ac757. PR104 DRAFT, SQL e fixture già completati, Mac LOCAL_MATCH_ONLY su fonti D1 separate. Cloudflare remura-contributors-lab e remura-contributors-fixture esistenti: non creare/migrare altri DB.

## Principio fondamentale
Il Contributor può vedere esclusivamente le proiezioni approvate e creare o correggere SOLO i propri livelli entro finestra e contratto abilitati. Una UI nascosta non equivale a un divieto: l'autorizzazione deve essere ripetuta sul server per ogni richiesta e per ogni riga. La Home Experience non è ancora backend reale e la demo di ruolo non è enforcement.

## Matrice permessi da rendere verificabile
| Azione | OWNER | CONTRIBUTOR | VIEWER futuro |
| --- | --- | --- | --- |
| Vedere informazioni approvate assegnate | Sì | Sì | Solo in futuro, previo gate |
| Scrivere livelli personali | Sì, con policy amministrativa distinta | Solo i propri livelli e soltanto nei periodi autorizzati | No |
| Modificare livelli altrui | Sì, operazione amministrativa tracciata | No | No |
| Gestire utenti, ruoli, revoche | Sì con audit | No | No |
| Vedere Secret, collector, diagnostica privata, fixture o configurazioni | Accesso separato su backend, mai tramite vista pubblica | No | No |
| Pubblicare su Telegram | Solo flusso approvato futuro | No accesso diretto al bot | No |

Il Contributor non riceve token D1, token Worker amministrativo o accesso diretto ai database. Il backend deve convalidare identità, sessione, scadenza, ruolo, subject della riga e permessi dopo il controllo di integrità. Preferire endpoint minimi, nessun elenco di altri utenti, rate limit e quota gratuita osservabile.

## Contratto livelli NON modificato
- Unica ancora prezzo, data osservazione UTC, nota massima 280 caratteri.
- DAY, WEEK, CURRENT_MONTH, PREVIOUS_MONTH.
- DELTA_PEAK, EFFORT_RESULT, OTHER_VOLUME_LEVEL.
- Zone, timeframe e direzionalità solo in futura versione esplicita. Vietare normalizzazioni automatiche ambigue.

## Scenari sicurezza ancora da testare
1. Contributor A non legge/scrive la bozza B e non modifica l'owner di una riga.
2. Cambio ruolo/revoca durante operazione: fail-closed, nessun nuovo commit autorizzato.
3. Token e permessi scaduti, riuso idempotency key, doppia submit, replay e CSRF.
4. Approve/reject separati da ingresso del livello, con audit append-only.
5. No leak di errori interni, query, identità e Secret nei messaggi al browser.
6. Stale snapshot e disposizione ABANDONED/PENDING: no dati di mercato nella Home.
7. iPhone Safari fisico: flusso login, editing proprio livello, stato offline, refresh, logout, schede multiple, movimento ridotto.
8. Audit del costo/limiti Free prima della PR per attivazioni: requests Worker, letture/scritture D1, storage e GitHub Actions.

## Gate manuali futuri (non richiesti oggi)
Identità dell'OWNER validata, piano di invito revocabile, audit completo, autenticazione forte, ambiente preview e dominio di servizio con costi verificati, test di isolamento multiutente, autorizzazione esplicita dell'OWNER per binding/deploy/utenti reali. Nessuna migrazione aggiuntiva, nessun Telegram reale o nuovo servizio cloud oggi.

Stato: READINESS DESIGN. Il lavoro si coordina con Experience v0.24 LAB senza fare merge, cambiare il branch Contributors, né ripetere LOCAL_MATCH_ONLY.
