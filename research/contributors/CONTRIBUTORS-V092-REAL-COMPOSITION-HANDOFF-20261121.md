# REMURA Contributors v0.92 LAB — reale composizione delle dipendenze; pilot NO-GO

**21 novembre 2026 · Europe/Rome · Rapporto tecnico offline. Nessuna nuova pagina UI.**

## Base scientifica e Cloudflare intoccati
- Base esatta v0.91: `94c739fa3bbb3fcccb2e3f8034b40f01d50d03c6`; rapporto `CONTRIBUTORS-V091-REAL-D1-RESULT-20261121.md`.
- Diagnosi reale del 21/11 già esaurita: **2/2** richieste GraphQL; `TODAY_EMPTY_PREVIOUS_PRESENT`, metriche giornaliere read/write **UNKNOWN**, zero D1 SQL, nessun retry. I vecchi consensi NON si riutilizzano. **Non rieseguire**.
- `main` identico al checkpoint `26896d642ea311f23dfa7f30ea1c8599c8c099e3` prima dei nuovi commit LAB. Nessun merge o deploy.
- Source v0.78 e v0.90 congelati NON modificati. Nuova integrazione `private_worker_composition_v092_lab.mjs` importa il vero Access/HMAC `accessBinding`, `profile` D1, read v0.69, level/owner v0.78, assets v0.78 e filtro POST v0.90. Non esporta un `default fetch`: resta **inerte**.
- Aggiunto filtro OWNER fail-closed centralizzato: se il profilo D1 è `OWNER` ma `can_recover` non è attivo, vengono negati anche GET `/owner/*` e POST `/api/profile`. Il router v0.78 autentica Access e verifica il profilo per le risorse statiche. Il controllo extra iniziale della prima versione di v0.92 è stato sostituito: nel codice ora **una sola chiamata `profile` per GET OWNER**, anziché due, limitando il costo D1 teorico. Il consumo reale resta UNKNOWN fino a staging autorizzato.
- `test_private_worker_composition_v092_lab.mjs`: **15 casi nuovi**, di cui una POST `/api/profile` attraversa i delegati autentici di laboratorio con Access HMAC, lookup D1 primario sintetico, verifica generazione e rate limiter sintetico. Non sono test Cloudflare reali.
- Workflow nuovo `.github/workflows/remura-contributors-v092-one-shot-ci.yml` limitato a branch e soli file nuovi, niente Secret, niente acquisizioni o deploy. **Esito CI remoto non verificato in questo rapporto**: il connettore corrente non elenca i run push e gli stati commit vuoti non attestano GREEN. Non dichiarare 15/15 PASS fino a lettura del run.
- Commit prima della documentazione: codice `d03f82651c2fcf65eca8523422414e824036fd30`; test `f4a11310e2b5bb8ea314006da9bff3b6ceac9271`; workflow `c090cceb0d7a5093672babb02d5cf275f501d955`; correzione sintassi fixture test `ae011e6aedbb0a066fa62e7cac4b91d4f8e825c0`; consolidamento profilo OWNER e risparmio lettura D1 `48958d0640113eca1c5a20761d5e4c0b9d494af5`; 2 test aggiuntivi `2ab9e06d225222cb3d2ab16aebbde6dc337fcb3e`; workflow aggiornato `33a846fcf06091f11f4325f8fc6bed24f2779171`.
- **Nuova prova NON ottenuta**: JWT Access provider, compatibilità Safari reale, sicurezza Cloudflare, consumo D1, post deploy, isolamento fixture, correctness temporale o trading edge.

## Unico input realmente utile da dashboard privata, senza API/Secret
Consultare personalmente in Cloudflare dashboard; **non cliccare create/upgrade/enable**:
1. **Account > Billing > Billable Usage**: confermare piano Workers Free, contatori account D1 righe **lette/scritte** per oggi UTC e l'eventuale stato unavailable. Il semplice grafico dei query count NON è il consumo billable di righe.
2. **Workers & Pages > D1 > Metrics > Row Metrics**: usare come riscontro per i database della stessa account; attenzione a finestra UTC e chart eventualmente vuoto. Non interpretare il vuoto come zero.
3. **Zero Trust > Overview**: annotare piano Cloudflare One e **posti Access attivi/usati/disponibili**. Zero Trust Free nominale non prova la disponibilità reale.
4. Restituire solo aggregati: `Workers plan=Free/Other/UNKNOWN`, `D1 rows read=<numero o UNKNOWN>`, `D1 rows written=<numero o UNKNOWN>`, `Access seats used=<numero o UNKNOWN>`, `Access seats available=<numero o UNKNOWN>`, `UTC day=<YYYY-MM-DD>`. **Nessun token, e-mail, user_uuid, nome DB o account ID**.

Se una qualunque cifra manca, annotare **UNKNOWN** e mantenere NO-GO. Una verifica dashboard non concede deploy automatico.

## Cancelli successivi, separati e sempre con nuovo consenso
- Validare budget Free account D1 e seats; se non verificati, stop. Gli stessi limiti vanno ricontrollati prima di un eventuale collaudo privato.
- Autorizzazione esplicita per staging privato isolato, senza usare i DB storici; Secret minimi solo in ambiente privato, Access allowlist/deny-default; verifica del binding diretto e del prezzo delle letture extra.
- Login/logout/revoca Safari, Contributor può solo proprie proposte e ricevute; OWNER può approvare e vedere audit; RESERVED senza retry/sblocco; rollback provato.
- Il vecchio workflow di consenso v0.91 è già stato disattivato. Non ripristinarlo.
- Telegram dei livelli approvati solo in fase successiva e previa autorizzazione.

## Raccordo roadmap
- TradingView v0.8.186 LAB; protocollo V2 byte-pinned, holdout1 23–29/11/2026 UTC, holdout2 30/11–06/12 UTC. Le acquisizioni genuine prospettiche, il clock indipendente e il confronto CVD vs price-only 60m **NON sono attestati**. Se i feed non vengono ricevuti in tempo, mancanti UNKNOWN; mai ricostruire retroattivamente.
- Shark Science v0.4 LAB: i moduli as-of COT, receipt retail, bridge decisione e CVD proxy preesistono. Non unire metriche non riferite alla stessa decisione o a diverso feed/prodotto/contratto.
- Experience v0.30: futuro splash toro/orso 3D, collisione, esplosione, REMURA/pinna + SMF; test Safari più avanti. Ogni **nuova pagina** avrà banner versione e data/ora Europe/Rome in cima.
- Private Capture v0.15 soltanto sintetico; Oracle collector e autoupdater protetti, v1.65 depositata non installata; Ampere Radar v0.36, backup e Squalincome invariati.

## Aggiornamento 21/11/2026 — PR draft di certificazione CI
- Aggiunto al workflow il trigger **pull_request** limitato a base `research/contributors-d1-diagnostic-v091-20261121` e head `research/contributors-private-composition-v092-20261121`, solo file della v0.92; commit workflow `2f080961b61b3742c99088d402a41555f37c0d73`.
- Aperta **PR DRAFT #105** [GitHub](https://github.com/mirkoworz/remura/pull/105) da v0.92 a v0.91 LAB, **non verso main**, senza merge e senza deploy. Diff soltanto 4 file v0.92 al confronto verificato.
- Il connettore `fetch_commit_workflow_runs` restituisce attualmente un elenco vuoto e `get_commit_combined_status` non offre check; **run CI non attestato** e non equivale a esito SUCCESS o a prova che il job non sia partito. Potrebbe richiedere approvazione della PR generata dal connettore; non rilanciare test storici.
- GitHub ufficiale dichiara runner standard gratuiti per repository pubblici (https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job). Non usiamo runner maggiorati né repository privati per questa CI.
- Documentazione aggiornata Cloudflare `ctx.access` conferma invocazione diretta Worker, ma non propagazione su Service Binding e router di Static Assets: https://developers.cloudflare.com/workers/configuration/cloudflare-access/ . Nulla di ciò attesta un vero login o misura quota D1.

**Verdetto v0.92:** integrazione LAB codificata con 15 nuovi test e workflow preparato, ma **CI green non ancora attestata** e **pilot reale NO-GO**. Nessuna chiamata Cloudflare, deploy, modifica Oracle, utente nuovo, merge o spesa.
