# REMURA Contributors v0.97 LAB — Gate di prontezza pilot GRATIS (NO-GO per default)
Checkpoint: 22 novembre 2026, Europe/Rome. **Nessun Cloudflare API chiamato, nessun account iscritto, nessun deploy, nessuna spesa.**

## Verifica esterna ufficiale (22 novembre 2026)

| Risorsa | Piano Free documentato | Origine |
|---|---:|---|
| Cloudflare Zero Trust / Access | Per team fino a 50 utenti; i posti consumati devono essere verificati nell'account | https://www.cloudflare.com/it-it/products/access/ |
| Workers | 100.000 richieste/giorno, 10 ms CPU per invocazione, 50 subrequest per invocazione | https://developers.cloudflare.com/workers/platform/limits/ |
| D1 letture | 5.000.000 **righe** lette/giorno, non interrogazioni | https://developers.cloudflare.com/d1/platform/pricing/ |
| D1 scritture | 100.000 **righe** scritte/giorno; gli indici incrementano le scritture | https://developers.cloudflare.com/d1/platform/pricing/ |
| D1 storage | 5 GB totali, fino a 10 database Free; **500 MB massimo per singolo database Free** | https://developers.cloudflare.com/d1/platform/limits/ |

Il piano Zero Trust Free e' pubblicamente adeguato come **classe di servizio**, ma non si puo' attestare che l'account personale abbia ancora posti o quota residua senza leggere il proprio pannello. Cloudflare segnala che l'utilizzo reale D1 e' leggibile da dashboard/GraphQL, e perfino interrogazioni eseguite dalla dashboard possono consumare righe: https://developers.cloudflare.com/d1/observability/metrics-analytics/ . Qui NON abbiamo eseguito nessuna richiesta D1/GraphQL; la precedente autorizzazione per massimo due richieste una tantum non viene riutilizzata.

**Dettaglio importante sulla revoca:** liberare un posto Access con *Remove user* non impedisce una futura autenticazione. Cloudflare avverte che *Revoke sessions* interrompe sessioni esistenti ma l'utente puo' autenticarsi di nuovo se una policy lo consente. Per revocare un collaboratore REMURA servono D1 identity revoked + policy Access che impedisca nuovi login + invalidazione sessioni + verifica da Safari che GET/POST siano realmente negati. Fonte: https://developers.cloudflare.com/cloudflare-one/team-and-resources/users/seat-management/

## Codice nuovo pronto, senza Cloudflare reale

- `contributors_free_readiness_v097_lab.mjs`: **solo calcolo locale**, ritorna sempre `goLive:false` e `deployAuthorized:false`, anche con condizioni verdi. I dati devono provenire da ispezione manuale *read-only* della dashboard e restare aggiornati allo stesso giorno UTC; niente valori indovinati. Conta i consumi dell'intero account, non solo REMURA.
- `REMURA-CONTRIBUTORS-V097-EVIDENCE-BLANK.json`: modello senza nessun nome, email, ID account, token, API key o cifra inventata. Tutte le osservazioni su consumo e le prove di sicurezza sono `null` / `false`: la situazione oggi e' **NO-GO, margine account reale NON VERIFICATO**.
- `test_contributors_free_readiness_v097_lab.mjs`: 21 casi nuovi mirati, con sole quantita' artificiali. Prova che non passa se quota, percentuali, prove di ruolo/revoca o provenienza mancano.
- `.github/workflows/remura-contributors-v097-free-readiness.yml`: checks limitati al branch/path, `contents:read`, Node 22, no Secret, deploy, scritture D1 o nuovi utenti.

**Riserva interna gratuita REMURA:** il gate chiede un margine del **25%** sotto i limiti ufficiali per Workers giornalieri, letture/scritture D1 e storage. Questa e' una prudenza progettuale REMURA, **non** una soglia o un costo imposto da Cloudflare. CPU Worker ha 10 ms di limite Free; una media/p95 sotto 10 ms non e' garanzia assoluta, serve un collaudo reale su staging e comportamento fail-safe.

**Trucco risparmio:** il controllo considera il riutilizzo di un database D1 gia' esistente, ma **soltanto** se e' isolato dai dati fixture/produzione e se conosciamo il suo spazio libero per database. Non creare un nuovo database se una risorsa separata, autorizzata e capiente e' gia' disponibile; non unire i dati fixture con i contributi reali. L'evidenza `existingDatabaseIndex` e' solo l'indice anonimo della dimensione del DB attestato, **non** un database ID o credenziale.

## Check manuale veloce da iPhone, quando autorizzato

1. Aprire https://dash.cloudflare.com in Safari e confermare che Workers/D1 sono sul piano **Free**, senza upgrade. Non inserire token in ChatGPT o su raw.githack.
2. **Workers & Pages → Metrics/Analytics:** annotare il totale richieste oggi UTC e il dato CPU disponibile. Non generare carico o interrogazioni per questo controllo.
3. **Workers & Pages → D1 → Metrics / Row Metrics:** annotare righe lette e scritte oggi UTC, spazio totale, dimensioni e numero DB. Non usare SQL Console per raccogliere questi numeri.
4. **Zero Trust → Overview → Team & Resources → Users:** annotare solo posti Access usati e assegnati e confermare piano Free. Non creare, rimuovere, revocare o modificare account in questa fase.
5. **Billing/Subscriptions:** confermare piano a $0 e nessuna funzione a pagamento accidentalmente attivata. Nessun cambio piano.
6. Per avviare **1–2 collaboratori REALI** richiedere successivo consenso esplicito e preparare staging private: Access JWT lato Worker, roles/scope server, isolamento D1, map catalogo server, ricevuta persistente, no automatic retry, APPROVE solo OWNER, doppia revoca, prove Safari OWNER/CONTRIBUTOR e account Free confermato.

## Stato e permessi NON mutati

Il portale e' LAB; le PR Contributors #105 / TradingView #106 erano DRAFT; l'app v1.70 iPhone bozza e' separata. Il nuovo gate non prova identita' reali, Access JWT, rivendicazioni server o spazio rimanente. **Non pubblicare la manifest con valori o dettagli personali/account**: condividere semmai soltanto un riepilogo anonimo di utilizzo. Nessuna modifica Cloudflare, D1, Worker, Pages, Oracle, Mac, Experience o produzione.

Il file di evidence da solo non autorizza mai il pilot: anche una valutazione `EVIDENCE_READY_FOR_INDEPENDENT_REVIEW` richiede approvazione distinta dell'OWNER e collaudi effettivi prima di qualunque deploy/attivazione.
