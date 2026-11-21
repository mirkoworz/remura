# REMURA Contributors v0.86 LAB — autorizzazione futura SOLO LETTURA

**21 novembre 2026, Europe/Rome — documento pubblicabile senza credenziali**

## Perché siamo ancora bloccati

Monitor giornaliero esistente: `.github/workflows/remura-cloudflare-budget-daily.yml`, `main` con schedulazione autonoma; checkout monitor revisionato al commit `08ee9d8f5ba0b4655f4b0b84245afc7cb7a360c8`. Il codice fa una query singola al dataset GraphQL `d1AnalyticsAdaptiveGroups` per il giorno UTC corrente; una risposta senza gruppi causa `REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA` e `REAL_ACCOUNT_DAILY_USAGE=NOT_MEASURED`.

Il monitor del **21/11/2026** ha restituito stato INCOMPLETE (run https://github.com/mirkoworz/remura/actions/runs/44919682812). Non è corretto sostituirlo con un vecchio GREEN, né trattare la lista vuota come zero. Nessun accorgimento LAB può attestare il consumo reale senza osservazione provider. La documentazione ufficiale Cloudflare D1 è https://developers.cloudflare.com/d1/observability/metrics-analytics/ .

## Futura attività autorizzabile, distinta da questo commit

**Non eseguire finché non arriva un consenso specifico** e una verifica aggiornata del margine gratuito:

1. Controllare se il monitor schedulato di `main` ha già fornito un giorno UTC corrente verificabile. Evitare duplicazioni; non cambiarne orario né credenziali.
2. Se indispensabile, predisporre una sola diagnosi **non schedulata**: massimo **2 HTTP POST** al solo endpoint ufficiale GraphQL Analytics, giorno UTC corrente + precedente, con **sola lettura**, timeout 15 s/call, body di risposta <=100 KB/call, zero retry. Query e percorso del guard devono restare byte-pinned. Endpoint e account ID/token restano esclusivamente nello spazio Secret privato del runner; non stampare HTTP headers, body, UUID, account ID, token né log grezzi. Se query fallisce o dati vuoti, uscita UNKNOWN e NO-GO.
3. Produrre solo stato sintetico pubblico (`TODAY_GROUPS_PRESENT_ESTIMATE_ONLY`, `TODAY_EMPTY_PRIOR_PRESENT`, `BOTH_DAYS_UNKNOWN`, `ERROR_OR_TIMEOUT`) e metadati non identificativi. Non pubblicare rows aggregate se la provenienza non è indipendentemente verificabile. Valutare eventuali limiti di GraphQL e margine Free prima della prova.
4. La verifica del piano **Cloudflare Zero Trust Free** e dei posti Access consumati/residui si esegue in privato dalla dashboard **Zero Trust > Team & Resources > Users**, senza esporre le identità ( https://developers.cloudflare.com/cloudflare-one/team-and-resources/users/seat-management/ ). Revoca seat e revoca accesso sono **processi diversi**; per negare accesso modificare policy o membership appropriate, non solo la seat.
5. Validare i quattro router private v0.78, allowlist deny-default, ACL JWT + ruolo D1, DB fixture isolato, RESERVED e rollback; prima del pilot di 1–2 collaboratori servirà autorizzazione distinta per deploy/login/revoca.
6. Non usare `workflow_dispatch` del monitor come prova automatica di nulla. Il modulo `readonly_probe_plan_v086_lab.py` usa una fixture GraphQL locale **non eseguibile** (`monitor_query_reference_v086_lab.graphql`), corrispondente alla query estratta dal sorgente del commit storico e bloccata con SHA-256 `483e14a113af7841fb69bdfdb7ea3fa3ee616b74f4f28b9cbc509b29d022754a`. Il sorgente HTTP storico NON è incluso su questo branch; il confronto è una prova di coerenza della query copiata, non un controllo live della sorgente monitor. Il modulo genera esclusivamente un **piano**; non fa richieste né accede a Secret. `NO_GO` preservato.

## Limiti e roadmap

- Questo documento **non richiede nuove credenziali né risorse paganti**. Nessuna attivazione Cloudflare, deploy, merge `main`, Oracle o provider live.
- TradingView: v0.8.186 preparazione ancoraggio esterno sul branch separato. Holdout1 23–29/11 e holdout2 30/11–06/12/2026 UTC immutati, nessun alpha dimostrato.
- Shark Science v0.4, Experience splash v0.30 toro/orso/SMF, Private Capture sintetico non attivo, Oracle collector non toccare, Ampere Radar, backup, Squalincome e Telegram livelli OWNER-approvati rimangono in roadmap.
