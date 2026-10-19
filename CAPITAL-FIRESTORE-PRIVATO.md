# REMURA — feed Capital.com automatico e privato via Firestore

## Stato e motivo

Il sito GitHub Pages `mirkoworz.github.io/remura` è **pubblico**; il feed Capital.com
è nel repository **privato** `mirkoworz/remura-collector`. Il browser non deve
chiedere direttamente un Personal Access Token GitHub, la chiave Capital.com o
una chiave di servizio Firebase. Abbiamo predisposto una lettura su Firestore
autenticata con Google, ma il servizio resta **spento** finché il proprietario
non imposta Firebase e le regole di accesso.

Il lettore prova nell'ordine:
1. `/private-api/capital/latest.json` (soltanto quando usi un server REMURA privato);
2. Firestore, se configurato e se sei entrato con Google;
3. File `latest.json` già importato manualmente nel browser, come prima.

Ogni scheda legge soltanto lo storico del proprio symbol. Se non arrivano dati:
N/D o ultimo campione con etichetta 'datato'. Non vengono creati lotti, segnali
istituzionali, candele o osservazioni inesistenti.

## Collegamento una volta sola (Firebase Spark)

1. Nel progetto Firebase dell'utente, crea (o usa) il database
   **Cloud Firestore (default)**, piano Spark gratuito se disponibile.
2. In **Authentication > Sign-in method**, attiva Google; in
   **Authentication > Settings > Authorized domains**, aggiungi
   `mirkoworz.github.io` (senza path o protocollo). Non autorizzare domini terzi.
3. Crea una **Web App** nelle impostazioni del progetto Firebase. La sua
   `firebaseConfig` pubblica contiene `apiKey`, `authDomain`, `projectId` e `appId`.
   Questi identificativi **non sono credenziali di amministrazione**. Inseriscili
   esclusivamente in `capital-cloud-config.js` del repository pubblico REMURA,
   senza SERVICE ACCOUNT o altri segreti:
   
   ```js
   window.REMURA_FIREBASE_CONFIG = {
     apiKey: "valore-web-app",
     authDomain: "progetto.firebaseapp.com",
     projectId: "id-progetto",
     appId: "id-app-web"
   };
   ```
4. Sul sito, nella scheda di uno strumento, premi **Collega Google** ed entra
   con l'account da autorizzare. Questo crea o identifica un utente Firebase
   Authentication. Recupera il suo **User UID** da
   **Authentication > Users** nella console Firebase.
5. In Firestore Rules, **aggiungi** alle regole esistenti (senza eliminare
   le regole del tuo altro progetto!) queste regole con l'UID sostituito
   col valore corretto. Le regole qui sotto sono un esempio completo solo
   per un database dedicato a REMURA:

   ```
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /remuraPrivate/capital {
         allow read: if request.auth != null &&
           request.auth.uid == 'INSERISCI_IL_TUO_FIREBASE_UID';
         allow write: if false;
         match /history/{symbol} {
           allow read: if request.auth != null &&
             request.auth.uid == 'INSERISCI_IL_TUO_FIREBASE_UID';
           allow write: if false;
         }
       }
     }
   }
   ```

   Non usare mai `allow read: if true` o `allow write: if true`.
   Non sostituire tutte le regole di un database condiviso con quelle d'esempio:
   inserirle correttamente nel blocco `match /databases/{database}/documents`.
   Ricorda che le regole Firestore **sono permissive per OR**: altre
   regole generiche (`match /{document=**}`) che concedono accesso
   annullano la riservatezza! Verifica con Rules Playground.

6. Nel repository GitHub **privato** `remura-collector`, predisponi una
   service account **dedicata** con ruolo minimo Cloud Datastore User per
   Firestore. Crea la chiave JSON solo se strettamente necessario,
   poi aggiungila in **Settings > Secrets and variables > Actions > Secrets**,
   con nome `REMURA_FIREBASE_SERVICE_ACCOUNT`. Non inserire la chiave in
   chat, GitHub pubblico, screenshot, repository o configurazione frontend.
   Se il progetto consente Workload Identity Federation, possiamo usare quella
   in futuro per evitare chiavi permanenti.
7. In **Settings > Secrets and variables > Actions > Variables** del collector:
   - `REMURA_FIREBASE_PROJECT_ID`: ID del progetto Firebase associato alla service account;
   - `REMURA_FIRESTORE_PUBLISH_ENABLED`: `1` soltanto dopo aver
     verificato rules, login e corrispondenza del progetto.
8. Nel repository privato avvia una sola volta **Actions >
   REMURA Capital - sincronizza Firestore privato > Run workflow**.
   Questo lavoro esporta il JSON **già raccolto** e non consuma richieste
   Capital.com. Dopo ogni acquisizione Capital riuscita, la sincronizzazione
   verrà ripetuta automaticamente.
9. Apri la scheda di un pair sullo stesso iPhone e controlla lo stato
   **Capital.com · cloud privato**. Le rilevazioni vengono mostrate
   con timestamp e bande reali. Se sei offline, puoi ancora usare
   l'importazione manuale.

## Protezioni e limiti

- Il codice frontend esegue soltanto letture dopo l'autenticazione personale:
  le Firestore Rules limitano l'accesso; chi non è autorizzato vede N/D.
- I dati inviati dal workflow sono **solo percentuali, timestamp, simboli,
  etichette sorgente e osservazioni numeriche validate**. Non sono inviati
  credenziali Capital, email, token, bilanci, ordini o raw API bodies.
- La service account GitHub usa IAM e bypassa le Firestore Rules:
  concedile il minimo indispensabile e non esporne mai il file JSON.
- Il workflow per Firestore non fa chiamate Capital.com; un altro workflow
  esegue la raccolta DEMO con il contatore e i suoi limiti anti-spreco.
- Non aggiungere i JSON Capital.com nel repository GitHub Pages pubblico.
- La lettura attraverso Firestore mantiene i dati privati; verificare comunque
  i termini di utilizzo dei dati Capital.com.

Riferimenti ufficiali:
- https://firebase.google.com/docs/firestore/security/get-started
- https://firebase.google.com/docs/auth/web/google-signin
- https://firebase.google.com/docs/firestore/pricing

La copertura reale attuale è **31 dei 35** strumenti REMURA. Mancano USDCAD,
US500, US30, US2000. Questi rimangono N/D e non vengono simulati.
