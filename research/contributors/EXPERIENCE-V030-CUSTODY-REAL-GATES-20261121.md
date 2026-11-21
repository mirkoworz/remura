# REMURA Experience v0.30 — piano custodia indipendente: gate reali
**21/11/2026, 08:34 CET (Europe/Rome) — DESIGN LAB, non release.**

## Contesto conservato
- Base Experience v0.29: research/experience-handoff-contributors-amend-v029-20261121 @ 46c2d5e34a198513e8a23e768950094077c70c80.
- v0.23–v0.29: simulazioni di annullamento, pin di monotonicità, verificatori Ed25519, doppie attestazioni e verifiche file offline. Tutti i risultati LAB restano acquisiti e non vengono ripetuti.
- Nuova v0.30: **un gate verificabile da superare con persone/dispositivi**, non un ulteriore algoritmo di firme chiamato impropriamente “indipendente”.
- Nessun file HTML cambiato, splash 3D toro/orso, nove frame, pinna REMURA e logo/ringraziamento SMF invariati. Una futura pagina aggiornata dovrà riportare in alto numero versione e ora locale italiana.

## Modello minacce
Il problema non è soltanto una firma falsa: una copia vecchia può avere firma autentica. Mac, iPhone, un altro backup, GitHub e Cloudflare NON sono automaticamente cinque custodi indipendenti se lo stesso proprietario o un unico processo può cancellarli, sovrascriverli o ripristinarli simultaneamente.

Scenario avversario | Conseguenza se manca una testa davvero indipendente
- Rollback simultaneo di registro, due ricevute e floor → tutte le firme potrebbero restare valide e coerenti.
- Ripristino iCloud su Mac e iPhone sotto il medesimo account → possibile condivisione del dominio di ripristino; da verificare, non presume protezione.
- Firma chiave nuova in caso di perdita di entrambe → reset della radice di fiducia; STOP salvo recovery manuale esternamente attestato.
- Ricevute firmate con timestamp recente ma catena vecchia → tempo dichiarato non prova “ultima sequenza”.
- Compromissione di un unico operatore con accesso a entrambe le chiavi → due firme non sono due autorizzazioni indipendenti.
- Mancanza del testimone → NO-GO a lettura di valori protetti e a nuove pubblicazioni, nessun fallback alla testa precedente.

## Soluzione gratuita proposta, DA COLLAUDARE
1. Registrare il digest+sequenza dell'ultima testa accettata in un registro offline fisico, fuori da Mac/Oracle/Cloudflare e dalla normale sincronizzazione. Un supporto non modificabile o un secondo custode amministrativamente indipendente sarebbe preferibile; una semplice nota su iPhone NON è un monotonic witness affidabile.
2. Ogni avanzamento richiede doppia verifica umana del predecessore e dell'impronta con materiale di prova sintetico; firmare solo dopo verifica separata e documentata.
3. Nessuna chiave privata reale in GitHub, chat, QR non protetti o file HTML. Chiavi di test effimere soltanto per esercitazione. Non associare una identità di produzione a una chiave appena generata nel laboratorio.
4. In seguito all'interruzione: non creare nuova generazione “da zero”; consultare un riferimento esterno verifi­cato e bloccare finché non si stabilisce la testa massima.
5. Salvare un rapporto senza dati segreti: id generazione di prova, ultima sequenza, hash file, dispositivo e dominio amministrativo, data/ora, osservatore e risultati di verifica.
6. Conservare eventi irrevocabili ABANDONED distinti dai PUBLISHED; mai servirli a vecchi consumer V1/V2 come dati numerici.

## Collaudo fisico sintetico futuro (NON eseguito)
- Mac verifica un pacchetto di prova e lo confronta con pin registrato offline; iPhone riceve soltanto un attestato sintetico.
- Spegnere/disconnettere uno dei dispositivi: la mancanza di una prova fa bloccare la lettura.
- Ripristinare una copia n-1 su Mac con pin n custodito separatamente: rifiuto totale.
- Ripristinare entrambe le copie ma preservare una terza floor indipendente n: rifiuto totale.
- Simulare perdita della floor e delle due chiavi: fail-closed, nessun auto-reset.
- Dimostrare quali backup/amministratori possono effettivamente riscrivere i dispositivi; conservare il risultato come evidenza, non semplice dichiarazione.
- Safari su iPhone fisico: test UI/login/splash separati, non confondere con custodia monotona.

## Gate release e disponibilità
- Non usare v0.30 per attivare Contributors reali, Private Capture hosted, Oracle collector, merge o deploy.
- Nessun servizio terzo o quota Cloudflare necessaria per il solo design e per eventuali future verifiche sintetiche **offline**.
- Una soluzione davvero automatica H24 potrà richiedere servizio indipendente con garanzie di consistenza/immutabilità e costi da valutare allora, non da inventare adesso.
- Richieste manuali per prove fisiche reali o provisioning di identità/chiavi solo dopo autorizzazione esplicita.

**Esito v0.30: threat model e protocollo pronti; custodia indipendente reale NON attestata, NO-GO mantenuto.**
