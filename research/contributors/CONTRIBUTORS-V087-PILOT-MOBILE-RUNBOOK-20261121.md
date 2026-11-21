# REMURA Contributors v0.87 LAB — Pilot Mobile Preview

Versione 0.87 LAB · 21 novembre 2026 ore 18:26 CET (Europe/Rome)

## Nuovo valore tangibile
- Creato **un file HTML autosufficiente**, `contributors_pilot_preview_v087_lab.html`, concepito per iPhone/Safari e desktop, esclusivamente come **anteprima offline** del futuro onboarding dei collaboratori. Sezioni navigabili con link interni e `<details>` nativi, senza JavaScript.
- Anteprima mostra due viste separate **CONTRIBUTOR / OWNER**: consultazione REMURA e proposte dei soli propri livelli per collaboratore; OWNER revisione, audit, coda originali e amendment distinti. Risposte incerte e RESERVED non rilanciate.
- Banner versione/data ora **in cima a pagina**, stato Cloudflare Free D1 e seats sconosciuto esplicitato, login/revoca Safari non collaudati. Nessun input, form, auth, accesso a Worker, JavaScript, storage, fetch, iframe, CDN, deploy, utente reale o operazione di mercato.
- UI separata dal router e dai 14 file sorgenti private v0.78 byte-pinned, quindi non altera né allenta le autorizzazioni reali.
- `test_contributors_pilot_preview_v087_lab.py`: 22 test NUOVI su integrità accessibilità, separazione ruoli narrativa, CSP restrittiva, link interni, nessun network e version banner. Workflow one-shot confinato ai nuovi file.

## Cosa manca al pilot REALE
1. Verificare le quote D1 giornaliere reali e i posti Free Access **con apposita autorizzazione**. Il run Cloudflare del 21 novembre `44919682812` ha dato `UNKNOWN_NO_GRAPHQL_DATA`: non significa zero.
2. Approvare un staging privato con DB fixture isolato, allowlist Access default-deny e ruolo server-side. Fare collaudo Safari iPhone login/logout/revoca reale e piano rollback.
3. Solo dopo, invitare 1–2 collaboratori reali; scrivono soltanto i propri livelli e l'OWNER approva con audit persistente. No Telegram prima dell'approvazione.

## Altri filoni conservati
- TradingView v0.8.186 LAB, holdout 23–29/11 e 30/11–6/12 UTC, preregistrazione invariata e ledger anchor ancora non attivo; Shark Science v0.4 LAB COT/sentiment/CVD as-of già articolato, niente ricostruzione tardiva.
- Experience v0.30 LAB toro/orso 3D con esplosione/pinna REMURA/SMF, foto da rimuovere e test Safari reale quando possibile.
- Private Capture non attivato, Oracle collector operativo/autoupdater bloccato/v1.65 staged non installare. Ampere Radar per Oracle Milano e Telegram operativo. Backup, Squalincome e futuro Telegram post-approvazione preservati.
- Nessun merge main, chiave personale, spesa o Mac per questa lavorazione.

**Limitazione: un'anteprima statica NON autentica utenti, non implementa ACL né prova i permessi in produzione.**
