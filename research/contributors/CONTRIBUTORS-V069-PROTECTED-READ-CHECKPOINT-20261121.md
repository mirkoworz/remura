# REMURA Contributors v0.69 LAB — PROTECTED READ BRIDGE
**21 novembre 2026 · 12:35 CET (Europe/Rome)**

## Stato e GitHub
- Repository: mirkoworz/remura.
- Branch isolato: research/contributors-protected-read-v069-20261121.
- Base: v0.68 0331e32a189fe2ea317b9be02eff6de27a3f54a6; v0.67 conservata a 01ad759d85b84200522bc6411c888d91d7da8ea4.
- Zero deploy, zero migrazioni, zero interventi D1 reale, zero Secret, zero identità reali, zero modifiche Oracle, zero merge, zero costi.
- protected_read_bridge_v069_lab.mjs: perimetro read-only, disattivato per qualunque uso reale, senza default Worker fetch.
- test_protected_read_bridge_v069_lab.mjs: **31/31 PASS** su Node.js v22.16 locale; test con mock sintetici.
- protected_read_composition_v069_lab.mjs: composizione esplicita degli originali accessBinding, d1_access_candidate.profile e amendmentHttpCandidateV065; controllo sintattico node --check PASS, non attestazione runtime end-to-end.
- test_staging_admission_v068_lab.mjs: **32/32 PASS** locale.
- Esecuzione combinata delle sole nuove suite v0.68/v0.69: **63/63 PASS, zero errori**. Test storici v0.66/v0.67 NON ripetuti. Nessun test GitHub Actions o Cloudflare reale dichiarato.

## Modello di accesso: solo lettura
1. Worker diretto deve fornire ctx.access autenticato, AUD identico e getIdentity. Nessuna identità o ruolo è ricavato da header o body di utente.
2. accessBinding esistente calcola subject ed email_tag HMAC da Access, rifiutando service token e account/audience discordanti.
3. D1 profile esistente risolve ruolo e diritto di lettura tramite first-primary, applicando controlli di revoca.
4. Solo tre route POST ammesse: /api/amendment/reconcile (body {}), /api/amendment/mine (body con after), /owner/amendment/reconcile-queue (body con after). Separazione rigida CONTRIBUTOR/OWNER.
5. Il bridge esige Sec-Fetch-Site same-origin, Origin e CSRF corretti, JSON, limite 4096 byte, blocco header di impersonazione, cursori non negativi e rimozione Content-Length non più attendibile dopo canonicalizzazione.
6. Rate limit obbligatorio, poi inoltro al backend v0.65 già sviluppato; ogni risposta senza no-store, redirect o errore sconosciuto fallisce chiuso.
7. Nessuna route di inserimento/approvazione/revisione può transitare tramite il nuovo bridge.
8. Attivabile SOLTANTO con READ_BRIDGE_V069=OFFLINE_FIXTURE_ONLY e tutti i kill-switch storici in OFFLINE_FIXTURE_ONLY; non esiste entrypoint Worker o deploy.
9. Le identità e i D1 profile della nuova suite sono MOCK. Le 31 prove non certificano Access reale, JWKS, D1 reale o revoche persistenti.

## Gratis: limiti ufficiali, non misure del nostro account
- Access Free: fino a 50 utenti — https://www.cloudflare.com/plans/zero-trust-services/
- Workers Free: 100.000 richieste/giorno; CPU 10ms/invocazione — https://developers.cloudflare.com/workers/platform/pricing/
- D1 Free: 5 milioni di righe lette/giorno; 100.000 scritte/giorno; 5GB complessivi; 10 database — https://developers.cloudflare.com/workers/platform/pricing/
- Verificare dal dashboard Cloudflare il consumo reale e numero attuale di database. Nessuna misurazione dell'account eseguita.
- Cloudflare dichiara che ctx.access vale per richieste dirette autenticate, NON si propaga automaticamente nei Service Bindings e ha limitazioni con router Static Assets — https://developers.cloudflare.com/workers/configuration/cloudflare-access/
- Per i percorsi privi di ctx.access affidabile, serve validare JWT Access (RS256, firma, issuer, AUD, scadenza) oppure rifiutare — https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/

## Successivi gate prima degli amici reali
1. Nuovo test di integrazione mirato v0.69 usando il fixture originale v0.66 come substrato, senza rieseguire la suite storica.
2. Verifica account reale Free e architettura di routing Access diretta; owner allowlist/revoca e IdP.
3. Test sessione reale di Cloudflare Access e logout effettivo: attualmente v0.67 chiude solo la vista locale.
4. Verifica D1 dedicato, HMAC, generazione, pin indipendente, first-primary, limitatore, ricevute minimizzate e approvazione.
5. Richiedere autorizzazioni nuove separate per qualsiasi deploy, migrazione, Secret, utente reale, modifica produzione o spesa.
6. Fino all'uscita di nuove pagine HTML, l'interfaccia resta etichettata v0.67; il nuovo backend LAB è v0.69.

## Filoni preservati
TradingView v0.8.181 LAB; Shark Science v0.4 LAB; Experience v0.30 LAB; Private Capture v0.15 LAB; Ampere Radar v0.36 operativo; Oracle v1.65 NO-GO; Telegram solo futuro; backup e Squalincome invariati.
