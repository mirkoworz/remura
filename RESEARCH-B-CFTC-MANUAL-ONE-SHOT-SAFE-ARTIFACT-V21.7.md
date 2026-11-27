# REMURA — Filone B V21.7 LAB · Acquisizione CFTC manuale senza chiamate nascoste

**Aggiornamento V21.7 · 24/11/2026, 00:14 Europe/Rome**.
Branch `research/filone-b-cot-intelligence-v206-20261123`, PR #108 Draft. Nessun merge/deploy, nessuna modifica Oracle/Mac/collector/broker.

## Perché esiste V21.7

Il tentativo precedente da questa chat sulla risorsa CFTC TFF non ha ricevuto risposta HTTP per errore DNS. Per ordine espresso del proprietario **non è stato ripetuto** né è stato tentato Disaggregated. Il limite autorizzato allora non si trasferisce automaticamente ai nuovi ambienti.

V21.7 **non effettua alcuna nuova acquisizione pubblica**. Dà un percorso pronto solo per una futura autorizzazione distinta:

1. `scripts/cot_public_two_date_archive_v216.py`: la funzione `read_once` è ora **non-follow redirect**. L'eventuale redirect 301/302/307/308 viene rifiutato; nessun GET automatico aggiuntivo. Il file deve tornare tramite URL esatto e HTTP 200; i proxy ambientali non possono creare un trasferimento implicito. Una sessione futura potrà fare al massimo 2 GET selezionati (un TFF, un Disaggregated), mai retry. Il comportamento del provider non è stato verificato su rete nella fase di preparazione.
2. `tests/test_cot_public_budget_transport_v217.py`: quattro test offline per redirect, URL non corrispondente, codici HTTP diversi da 200 e installazione del transport sicuro. **Usano risposte finte in memoria**, non provider.
3. `.github/workflows/remura-b-v217-cftc-one-shot-public-archive.yml`: workflow **esclusivamente manuale**, senza `push`, `pull_request` o `schedule`. Richiede il testo esatto `ALLOW_2_PUBLIC_CFTC_GETS_NO_PRIVATE_DATA`; vincolato al branch LAB B e al **primo tentativo** del run GitHub (`run_attempt==1`); non utilizza credenziali, segreti, DB, Oracle o broker. Esegue fetch pubblico solo a fronte di nuovo consenso, verifica 28/28 chiavi, hash interno di righe e produce due soli file **pubblici** come artefatto Actions: `remura-cftc-public-2dates.json` e `remura-cftc-public-2dates.json.sha256` (retention 7 giorni). Niente archivio privato e niente commit automatico.
4. L'artefatto non è una verifica di parità privata. La parità pubblico/privato verrà calcolata dopo, **offline**, con l'esistente `scripts/cot_offline_parity_fx_bundle.py` e la copia già verificata sul Mac, senza produrre log di prezzi privati o token.

**Condizione pratica GitHub:** un workflow `workflow_dispatch` normalmente deve essere registrato nel branch predefinito GitHub (`main`) prima che possa essere lanciato via UI, anche scegliendo poi il ref LAB. Poiché la PR #108 è volutamente Draft e il progetto vieta merge/deploy, **questa preparazione non rende ancora eseguibile il workflow manuale dall'iPhone**. Non spostare il workflow a `main` né avviare job senza nuova autorizzazione; se necessario, pianificare in seguito un'incorporazione isolata del solo workflow su main previa verifica di sicurezza. I test PR sul branch sono invece sufficienti per validare il codice statico senza GET.

**Costi:** provider CFTC 0 nuove richieste in questa fase; nessuna spesa deliberata. GitHub Actions usa i minuti e lo storage del piano e il margine Free **non è stato verificato**, quindi verificare Billing prima del successivo run manuale.

**Limitazioni scientifiche permanenti:** una copia pubblica delle 28 righe può solo dimostrare coincidenza delle cinque misure di ogni contratto con il valore privato salvato. `first_seen_at` locale e orario ufficiale di rilascio restano concetti distinti; non retrodatare i valori, non chiamarli flussi live, non usare i 28 cross come 28 scommesse indipendenti, non dichiarare alpha.

## Checkpoint
- API CFTC da questa chat: **zero nuove chiamate**.
- Workflow remoto futuro: **file LAB non attivo**, nessun artefatto pubblicato.
- Parità con CFTC ufficiale: **NON VERIFICATA**.
- Prossimo lavoro autorizzabile: attivazione unicamente manuale con budget Free verificato, 2 GET massimi, consent esplicito e possibilità reale di scaricare lo snapshot pubblico.
