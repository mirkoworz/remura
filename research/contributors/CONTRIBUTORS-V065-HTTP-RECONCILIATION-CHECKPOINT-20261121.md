# REMURA Contributors v0.65 LAB — checkpoint coordinamento HTTP e riconciliazione
**21 novembre 2026, sessione successiva alle 10:54 CET (Europe/Rome).**

## Provenienza verificata
- Repository GitHub privato: \`mirkoworz/remura\`.
- Base del nuovo lavoro: \`research/contributors-server-reconcile-v064-20261121\` @ **\`368ec07e92ad1a01fca84350b247d9c083a25a4a\`**.
- Branch isolato: **\`research/contributors-reconciled-http-v065-20261121\`**. Solo aggiunte, niente main/merge/deploy.
- Moduli versionati e impronte Git blob confrontate coi file usati localmente:
  - \`reconciliation_http_v065_lab.mjs\` → \`4f3c925e9b4f7d2c23b1017257de777bc238dfc4\`
  - \`reconciliation_composition_v065_lab.mjs\` → \`0126982c42941b0c07c6f4edbf48066469d201c9\`
  - \`reconciliation_client_v065_lab.mjs\` → \`6c062cc9c602411a442fe2c3e1eebd974311f9c5\`
  - \`test_reconciliation_http_v065_lab.mjs\` → \`0da901cd060889e527b5e702d07bd859f1a01981\` (corretta nel branch una parentesi errata nel file copiato per allineare i byte alla suite locale effettivamente eseguita)
  - \`test_reconciliation_client_v065_lab.mjs\` → \`895272c87163a98fc331e9b8a4259974a139ff3e\`
- Sono state riutilizzate senza modifica le versioni v0.59–v0.64 del candidato schema e dei moduli Access, intenti, adapter e recovery.
- Repository v0.56 originale \`research/contributors-offline-20261114\` @ \`21338d4a405b0a3053e5a51322f8643c428ac757\`, non modificato.

## Implementazione LAB (non servizio pubblico)
- \`reconciliation_http_v065_lab.mjs\`: funzione factory \`createReconciliationHttpV065\`, SENZA export fetch Worker. Intercetta soltanto:
  - \`POST /api/amendment/submit\`, rigorosa origine HTTPS + same-origin Sec-Fetch-Site + X-Remura-CSRF + JSON <=4096 byte, solo input esatto source_entry_id/request_id UUID/price/UTC/note, nessun subject/body role accettato.
  - \`POST /api/amendment/reconcile\`, lettura status propria (Access-bound via reader v0.64), mai autorizzazione a risottomettere.
  - \`POST /owner/amendment/reconcile-queue\`, coda lettura OWNER soltanto.
- Dopo un intento HMAC **effettivamente bruciato** prima dell'effetto, ricontrolla identità Access, costruisce SQL INSERT della prenotazione persistente nella nuova tabella v0.64 usando soggetto fidato e token normalizzato, pretende conferma primary \`served_by_primary===true\` e un singolo \`meta.changes\`. Ricontrolla identità prima di invocare \`submitAmendmentLab\` v0.61. Trigger v0.64 deve essere installato per bloccare righe senza prenotazione: se manca, fallisce.
- Un risultato sconosciuto o SQL/Access negativo dà **409 not_confirmed, retry:false**, nessuna ripetizione della write. Le altre route sono delegate al controller storico v0.62, che mantiene controlli Owner/intent/CSRF e proiezione approvata. Flag OFFLINE_FIXTURE_ONLY v0.61/62/64/65 obbligatori sulle route gestite; non è stato configurato alcun Worker.
- \`reconciliation_composition_v065_lab.mjs\` lega la factory ai moduli esistenti: \`amendmentHttpCandidateV062\`, \`burnAmendmentIntentLab\`, \`accessBinding\`, \`submitAmendmentLab\`, \`inspectMyAmendmentRecoveryV064\` e \`inspectOwnerRecoveryQueueV064\`. **La composizione è stata controllata per sintassi e nomi delle funzioni, ma NON eseguita contro l'intero stack reale.** Nessuna chiave o identità reale.
- \`reconciliation_client_v065_lab.mjs\`: legge SOLTANTO \`/api/amendment/reconcile\` con fetcher iniettato, no-store e risposta JSON di forma rigorosa, conserva \`mayResubmit=false\` per NO_ATTEMPT/UNRESOLVED/COMMITTED_UNREVIEWED/COMMITTED_REVIEWED/CLOSED. Nessuna funzione mutate, reset o auto-retry. Il browser v0.63 resta una pagina OFFLINE non collegata.

## Prove reali svolte in locale, limiti espliciti
- Linux, Node v22.16.0, node:sqlite, node:test. Nessun D1 cloud, nessun Access JWT reale, nessun runner Actions, nessun provider/Secret.
- Test **effettivamente eseguiti**:
  - 40/40 nel file \`test_reconciliation_http_v065_lab.mjs\` conservato nello ZIP LAB locale: prenotazione, una sola mutazione, contesa, risposta persa, HMAC sintetico, revoca, identità, origin/CSRF, UTC, 409, lettura ricostruita, privacy e fallback.
  - 24/24 nel file **versionato su GitHub** \`test_reconciliation_http_v065_lab.mjs\`: suite di regressione parzialmente sovrapposta ai 40, con un DB SQLite **surrogato ridotto** e trigger simili ai guard v0.64. Hash coincide coi byte locali provati.
  - 15/15 nel file **versionato** \`test_reconciliation_client_v065_lab.mjs\`: recovery read-only, formato risposta, rifiuto metadati/redirect, zero auto-resubmit.
- Esecuzione complessiva: \`node --test --disable-warning=ExperimentalWarning test_reconciliation_http_v065_lab.mjs test_reconciliation_http_repo_v065_lab.mjs test_reconciliation_client_v065_lab.mjs\` → **79/79 verifiche PASS (0 fail)**; comprendono suite sovrapposte, quindi non presentare 79 come casi distinti o test di Cloudflare.
- ZIP di consegna completo contenente anche i 40 test più estesi: \`/mnt/data/remura-contributors-v065-lab-tests-20261121.zip\` nel turno di creazione (NON URL GitHub o file del repository).
- Nessun test storico v0.64 76, v0.63 56, v0.62 60, v0.61 40, v0.60 80 oppure Oracle/TradingView/Experience ripetuto.
- Attenzione: non è stato usato in questa suite il D1 originale completo. È stato collaudato il **core con dependency injection e surrogate SQLite**; l'integrazione dell'intero schema D1/Access/Worker v0.65 resta a rischio e non è attestata.
- La reservation v0.64 è intenzionalmente separata dalla write v0.61 in due operazioni primary: se la seconda fallisce, la prenotazione resta aperta e occorre revisione manuale owner. Questo **non è un commit atomico della coppia** e non si deve presentare come tale.

## Condizioni NO-GO ancora attive
- Nessuna migrazione SQL v0.64 su remura-contributors-fixture o remura-contributors-lab; schema v0.64 + controller v0.65 non vanno combinati con il vecchio controller attivo prima di verificare a fondo la transizione.
- Nessun Access JWT/account di collaboratori, registrazione amici, Worker, live frontend, Safari iPhone fisico o chiamata D1 reali.
- Verifica Cloudflare D1 compatibilità in un ambiente LAB isolato + gestione dei costi Free prima di proporre qualunque attivazione.
- Il ripristino dello stato su due schede/refresh è simulato tramite DB condiviso nel core e SQL v0.64 precedentemente provato con più connessioni; la proprietà multi-dispositivo/browser e la persistenza Cloudflare reale sono ancora non provate.
- OWNER release resta operazione SQL manuale LAB non esposta via HTTP; richiede prova di assenza scrittura pendente e revisione operatore. Nessun auto-unlock.
- Una sola identità reale abilitata richiede consenso e audit indipendente. Nessun guadagno, edge statistico o identificazione dei trader istituzionali attestata da questi controlli.
- Quote residue Cloudflare Workers/D1, GitHub Actions, Oracle **non misurate** in questo ciclo; nessuna nuova risorsa cloud o spesa introdotta.

## Roadmap coordinata
1. **Contributors v0.66**: prova **full-schema** su \`d1_access_candidate.sql\` + overlay v0.59 + reservation v0.64 e composizione reale v0.65 con mock Access/D1 primary, inclusi intent HMAC, revoca tardiva, 2 schede, chiusura OWNER. Non ripetere le vecchie 79 prove se il codice resta immutato.
2. **Contributors v0.67 UI**: vista di riconciliazione read-only ben distinta dai comandi di correzione, Safari Mac e iPhone fisico, versione/data/ora italiana in cima a OGNI pagina modificata. UI v0.63 già ha header corretto e invio disabilitato fuori test.
3. **Contributors live**: solo dopo autorizzazione specifica e verifica quote Free, staging Cloudflare privato, identità di prova isolate, controlli CSRF/sessione/ruoli/limiti e rollback sicuro. Nessuna acquisizione dati di mercato e nessuna migrazione produzione senza consenso.
4. **Experience v0.30**: custodia monotona realmente indipendente Mac/iPhone ancora DESIGN, non attivata. Splash toro/orso 3D, pinna REMURA, ringraziamento SMF invariati.
5. **TradingView v0.8.181**: holdout 1 23–29/11/2026 UTC, holdout 2 30/11–06/12 UTC, criteri congelati; aspettare i dati veri, nessun vantaggio statistico dichiarato. Shark Science v0.4 separato.
6. **Oracle collector**, Ampere Radar, Private Capture e v1.65 staged restano invariati; niente autoupdater, merge o hosted Private Capture.

**Stato: REMURA Contributors v0.65 LAB code + recovery client, ma integrazione reale NO-GO.**
