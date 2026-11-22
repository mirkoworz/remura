# REMURA Retail v0.6 — ricevute temporali prospettiche (solo LAB)
22 novembre 2026, Europe/Rome. Nuovo sviluppo indipendente dalla v0.5, non ricontrolla i tre commit Myfxbook reali.

## Consegna
- Implementazione: research/retail/provenance_receipt_ledger_v06_lab.py
- Test nuovi: research/retail/test_provenance_receipt_ledger_v06_lab.py (14 casi dedicati)
- Un ledger accetta identificazione del contenuto e le future dichiarazioni di eventi: ritorno API collector, snapshot, commit, evento GitHub Actions, completamento Pages, pubblicazione provider, ricezione indipendente.
- Ogni evento contiene tipo, autorità classificata, timestamp dell'evento, timestamp di registrazione, riferimento e digest della risposta. Il digest è solo un valore dichiarato: in questo modulo non si confrontano i byte della risposta.
- Aggiunta non mutante, catena SHA-256 verificabile, duplicazioni e riscritture accidentali rifiutate, orari UTC canonici. Un aggressore può tuttavia riscrivere tutta la catena se manca un head pin indipendente.
- Disponibilità pubblica Pages diversa dall'avvio run Pages; pubblicazione Myfxbook diversa dal clock del collector; indipendent first-seen rimane UNKNOWN o CLAIM_ONLY_UNATTESTED.
- Eventuale evento witness autodichiarato NON rende una decisione scientificamente ammissibile; eventi successivi alla decisione bloccati esplicitamente.
- Stato: NO_GO_SCIENTIFIC_ADMISSION sempre; zero clock certificati e zero firme verificate.

Nessun servizio o automazione avviata, nessuna nuova spesa autorizzata, nessuna lettura Cloudflare/Oracle/Secret e nessun dato mercato creato. Prossimo gate: verifica reale di contenuti, fonte indipendente e firme prima di qualsiasi promozione scientifica.
