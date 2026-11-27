# REMURA — Filone B v21.1 LAB: output offline CFTC FX per dashboard

**Versione:** B V21.1 LAB; **Europe/Rome:** 23/11/26, 21:02:35. **Ramo:** `research/filone-b-cot-intelligence-v206-20261123`; **PR #108 Draft**. Nessun merge/deploy o modifica HTML.

## Modulo operativo aggiunto

`scripts/cot_fx_dashboard_export.js` legge **un solo snapshot JSON CFTC già presente offline**, max 8 MB. Utilizza `cot-intelligence-fx-factors.js` già verificato; non richiede endpoint né nuove API e non chiama GitHub, CFTC, Cloudflare, broker, Mac/collector, D1, Workers. Produce a stdout un JSON `remura-cot-dashboard-fx-v1` **descrittivo**, pronto come contratto per il Filone D, contenente:

- esattamente **7 futures FX distinti**: EUR, GBP, JPY, AUD, CAD, CHF, NZD; confronto Asset Manager/Institutional vs Leveraged Funds;
- netto/OI, cambiamento settimanale in punti percentuali, open interest e variazione, indice 52 report quando copertura genuinamente sufficiente, data e primo acquisito locale se presente;
- **28 cross Forex sintetici**, con due gambe e pesi +1/-1. I cross non sono 28 osservazioni indipendenti e NON attestano posizioni spot;
- `state=blocked` e fattori/cross vuoti quando uno dei contratti necessari è mancante, report stale o non allineati;
- orologi separati: data report, data lettura pubblica, `first_seen_at` locale non autenticato, `observedAt` consentito solo su cache privata;
- **zero** BUY/SELL, stime di rendimento, ordini, cambiamenti alla dashboard LIVE o al Filone A.

### Comandi SOLO per file offline già custoditi

~~~bash
# Senza input: nessun dato inventato e nessuna chiamata
node scripts/cot_fx_dashboard_export.js

# Su snapshot autentico GIA' presente come file offline locale:
node scripts/cot_fx_dashboard_export.js \\
  --snapshot /percorso/offline/cftc-public.json \\
  --now-utc 2026-11-23T20:00:00Z

# Solo cache privata, con as-of dichiarato e verifiche di prima cattura:
node scripts/cot_fx_dashboard_export.js \\
  --snapshot /percorso/offline/remura-cot-copy.json \\
  --now-utc 2026-11-23T20:00:00Z \\
  --observed-at 2026-11-22T20:00:00Z
~~~

Nessun dato viene salvato automaticamente; se si reindirizza stdout, mantenere il risultato nella directory offline autorizzata fino alla revisione dei contenuti. Il programma **non certifica l'identità del file/sorgente** e non ricalcola il digest CFTC: la parità e l'integrità restano responsabilità del modulo Python v21.0 di custodia. Il programma non è un attivatore di segnali o ordinazione.

## Stato dei dati REALI, non confondere test con numeri veri

L'audit CFTC del 23/11 (run 45206837974) già confermato ha ottenuto 980 righe ufficiali e un digest; **le 980 righe non sono archiviate in un file riutilizzabile via GitHub**. Pertanto il nuovo modulo non può produrre in questo turno 7 valori **autentici** senza copia offline legittima o una nuova acquisizione pubblica. Nessun nuovo audit né nuova GET CFTC: **7 valori pubblici completi = N/D; confronto private first-seen = N/D**. I test (cinque nuovi casi) usano soltanto serie inventate per verificare il contratto, **non** per mostrare risultati reali.

**Passo prioritario:** portare una copia offline autorizzata dello snapshot CFTC e della cache COT privata nella stessa macchina, eseguire v21.0 parity per 14 contratti x 2 date e quindi l'export descrittivo in JSON. Non contare automaticamente la prima acquisizione come pubblicazione CFTC e non alterare le categorie Disaggregated (Managed Money vs Producer/Merchant), che restano in corsia separata.

**Gratis:** sola lettura di file locali + Node.js e test CI del repo già disponibile; nessun nuovo servizio o storage/cloud persistente. Quote effettive GitHub Actions non ricontrollate qui; non presumere risorse illimitate.
