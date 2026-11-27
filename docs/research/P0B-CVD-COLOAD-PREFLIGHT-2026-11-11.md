# REMURA — P0b → CVD co-load: preflight scientifico (11/11/2026)

**Stato:** SOLO PROGETTAZIONE OFFLINE, NON AUTORIZZA STAGING O LIVE. Filone B PR #89 DRAFT. Non modificare collector, VPS, MAIN, Filoni A/C o v1.64 documentata. Nessun nuovo costo.

## Evidenza disponibile
- Otto finestre passive su tre giorni UTC (06, 09, 11 novembre), riportate in screenshot dell'operatore e trascritte nella roadmap. Solo sette finestre V2 hanno burst CPU su ~5 s; una V1 no.
- Ottava finestra: `2026-11-11T09:31:30Z`, 18 campioni/85 s, CPU media 3.8807% di un core, massimo burst campionato 18.3123%, servizio RAM 156.73 MiB, host MemAvailable min 614.11 MiB, CPU PSI +41.399 ms, I/O PSI +82.323 ms, memoria PSI +0 ms. Collector batch timestamp avanzato, PID invariato, zero scritture/modifiche della sonda e zero chiamate broker aggiuntive.
- Sulle otto finestre: CPU media massima 3.9774% di un core; burst massimo V2 35.0196%; RAM servizio massima 156.73 MiB; host MemAvailable minimo 606.13 MiB. **Questi sono estremi campionati**, non picchi veri o garanzie future.
- La prova dell'ottava finestra è uno screenshot, non un report JSON grezzo firmato; non fabbricare input per `shark_p0b_window_census.py --audit-stdin`. La copertura osservazionale 8/8 non equivale a comparatore automatico completato.

## Ipotesi da verificare, NON risultati
1. Un recorder CVD isolato e disattivabile può convivere con il collector originale senza aumento materiale della latenza del batch, errori SQLite, perdita di campioni o degradazione dell'osservazione Squalincome.
2. CPU e RAM possono essere limitate da budget misurati realmente sulla specifica shape Oracle, senza assumere che % di un core = % di entitlement.
3. La raccolta può essere fermata e ripristinata senza toccare i dati originali, con prove di restore e rollback, e restando entro quote e costi effettivamente verificati.

## Piano di validazione a gate
**G0 — prova di integrità offline:** individuare l'esatto entrypoint e tutti gli effetti collaterali del recorder; test di isolamento con dati sintetici; garantire OFF di default, zero rete, zero broker API, zero scritture al DB di produzione, stop deterministico, test di errore disco pieno/SQLite busy. Se non verificato: NO-GO.

**G1 — audit infrastrutturale separato:** misurare entitlement OCPU e shape OCI, memoria e storage effettivi, contatori di throttling disponibili o N/D, quote/consumi di GitHub Actions, billing Oracle e protezione dai costi; backup/restore/rollback provati in ambiente isolato. Una sola evidenza mancante impedisce il passaggio a co-load reale.

**G2 — confronto controllato e reversibile (solo dopo autorizzazione esplicita):** osservare stesso perimetro e stessi orari di mercato con recorder spento/acceso; registrare baseline e differenze di latenza per mercato, età delle barre, errori, burst CPU, RAM, PSI, I/O, `SQLITE_BUSY`, lag e throughput; distinguere carico reale di tutti i mercati e campioni singoli da avanzamento di un timestamp batch. Non fare affermazioni di regressione o miglioramento senza coppie comparabili e dataset originale.

**G3 — decisione:** gate fail-closed per qualunque costo non autorizzato, perdita di dati, ritardo di mercato non quantificato, instabilità o impossibilità di ripristino. Solo dopo G0-G2 con evidenze verificabili valutare un esperimento prospettico limitato, separato da C5, FIRST-SEEN e release v1.65.

## Vincoli immutati
- `cgroupCpuThrottleObservable=false` significa contatori indisponibili, non assenza di throttle.
- `oracleCpuEntitlementMeasured=false`, `providerHypervisorThrottleMeasured=false`, `realCvdCollectorCoLoadTested=false`, `oracleBillingVerified=false`, `cvdResearchMayBeEnabled=false`.
- La prova P0b non misura vantaggio statistico, movimenti istituzionali, profitto o qualità del CVD.
- Nessun deploy, cron, benchmark intensivo, chiamata broker, modifica Oracle o merge senza nuovo consenso.
