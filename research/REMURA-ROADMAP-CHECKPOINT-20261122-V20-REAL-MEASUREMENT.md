# REMURA — CHECKPOINT V20 | 22/11/2026, 23:41:33 Europe/Rome

**Principio:** passaggio a MISURAZIONI REALI, non altri simulatori. Roadmap V01–V19 conservata; padre V19: `research/remura-roadmap-v19-free-pilot-gate-20261122` SHA `aaa07a3bb633a3cc037c52c3a50f0293ba295c55`. Nessuna mutazione a main, produzione, Oracle, Mac/Codex, Cloudflare, D1 o utenti.

## Acquisito oggi — evidenza effettiva
1. **MYFXBOOK:** main `cce37d0bcf55d8b1c02d56304e7e2c29d1319c59`, snapshot `2026-11-22T22:23:40Z` con 89 simboli; **34 storici**, **3.924 osservazioni**, 30 serie recenti × 126 e 4 serie indici ferme al 22/10 × 36. Su 3.890 coppie consecutive, **2.244 (57,7%)** uguale long%; fra le 30 serie attive intervallo mediano 5,91h.
2. **CAPITAL DEMO:** repository separato `mirkoworz/remura-collector` main `a8f8cedf2ff1960f6bee3f8ed7dd24f864656844`; snapshot `2026-11-22T20:45:11Z` con 31 mercati. **31 storici**, **3.791 osservazioni**, mediana intervallo 6,85–6,87h, **1.229/3.760 (32,7%)** delle coppie con uguale long%, 32 intervalli >12h, nessuno >24h. In questo repository PUBBLICO non si riversano record o valori privati per simbolo.
3. **Totale 7.715 osservazioni descrittive** non significa 7.715 trades/campioni indipendenti, previsioni, CVD o performance.
4. **FIRESTORE:** run privata `45068217134` SUCCESS, 32 documenti; sincronizzazione riuscita, non ritorni dei prezzi.
5. **COT ORIGINALE CFTC:** TFF Futures Only posizioni **17 novembre**, release **20 novembre 2026**; calcolo vero dei net Asset Managers e Leveraged Funds e variazioni settimanali su EUR FX, JPY, CAD. Fonte https://www.cftc.gov/dea/futures/financial_lf.htm. Sfasamento temporale obbligatorio; NO lookahead.
6. **FREE:** run esistente `45039172579` (22/11 15:35Z) FALLITA PER INCOMPLETEZZA: D1 account daily `UNKNOWN_NO_GRAPHQL_DATA`, Workers adaptive `OK`, D1 TEST 6.266.880 byte/500.000.000, account storage 6.557.696/5.000.000.000. Access seats/billing non noti. Nessuna nuova interrogazione Cloudflare effettuata.
7. **CVD:** sorgenti TEST pinnate/historical run presenti, ma **stato runtime attuale, alert TradingView, first-seen reali e prezzo indipendente non attestati**. Holdout V2 **23/11 00:00 UTC (01:00 Europe/Rome)**: non retrodatare; assenza evento confermato = risultato operativo UNKNOWN, non risultato di performance.

## Codice e documenti nuovi sul ramo isolato
Branch: `research/remura-v20-real-measurements-20261122`.
- `research/REMURA-V20-REAL-MEASUREMENTS-20261122.md` — rapporti veri, lacune, cloud quotas e percorso scientifico.
- `research/REMURA-V20-COT-INSTITUTIONAL-20261117.md` — TFF ufficiale, NET e ΔNET auditabili per due categorie su 3 contratti.
- `research/v20_real_measurements.py` — motore stdlib completamente offline, legge file locali già acquisiti; segna timestamp futuro, stale >24h, duplicati, ritardi, percentuali invalide. Per directory Capital privata emette **solo aggregati**, senza nomi simboli.
- `research/test_v20_real_measurements.py` — **6 nuovi test mirati**, nessun vecchio test rifatto.
- `.github/workflows/remura-v20-real-measurements.yml` — solo branch/path V20, runner standard pubblico Free, 3min timeout, nessun Secret.
- **CI nuova [run 45079063611](https://github.com/mirkoworz/remura/actions/runs/45079063611): SUCCESS**, solo test NEW e syntax check. Non presenta claim di accuratezza previsionale.

Esempio offline sul branch/repo locale:
```bash
python3 research/v20_real_measurements.py --myfxbook-dir data/myfxbook/history --as-of 2026-11-22T22:33:00Z
```
Se repository privato collector disponibile LOCALMENTE, aggiungere `--capital-dir ../remura-collector/private/capital/history`. Non fare push dell'output privato al repository pubblico. Per riprodurre i numeri dell'audit V20 usare le revisioni *pinnate* dei due repository, non le future nuove main.

## Decisioni operative / NO-GO da non occultare
- **SI:** acquisizione sentiment retail/DEMO vera, serie leggibili, dati COT pubblici ufficiali, analisi descrittive riproducibili, prodotto Shark v1.68 Safari LAB testato.
- **NO:** Alpha, rendimento e direzione futura comparata non attestati: non ci sono in V20 prezzo indipendente + timestamp first-seen + lead/lag + outcome 60m/H4/24h maturi.
- **NO:** pilot amici già attivo. Contributors v0.95/v0.96 UI LAB verificata; v0.97 Free gate 21/21 GREEN; manca prova quote giornaliere D1, Access seats, Billing, JWT/runtime, ownership, receipt, review e revoca reale. PR #105 DRAFT, PR #106 DRAFT.
- **NO:** Cockpit v1.68 già in main. main resta nav.js v1.64; splash 3D toro/orso coordinato da Mac senza interferenze. Nessun merge/deploy senza consenso.

## Next EXACT — senza ripetere test
A. **23/11 00:00 UTC:** verificare in SOLA LETTURA con evidenza autorizzata lo stato TEST Worker + alert + prima ricevuta CVD reale, e il suo primo timestamp. Senza nuova autorizzazione a Cloudflare/Secrets NON chiamare provider: da GitHub codice e CI non si inferisce lo stato live. Non usare gli eventi precedenti nel holdout.
B. **Mentre raccogliamo:** agganciare prezzo indipendente con timestamp coerente e costi/spread, bloccare regole ex-ante e misurare 60m, H4 e 24h solo quando maturi, confronto price-only. NO alpha senza comparatore.
C. **Contributors:** una sola visita da iPhone dashboard Cloudflare in modalità lettura per seats Access, Billing Free, D1 rows letture/scritture UTC del giorno e Worker usage, senza API nuove; poi autorizzazione mirata per pilot 1 OWNER + 1–2 CONTRIBUTOR su staging protetto e doppia revoca provata.
D. **Raccolta:** sorvegliare reale regolarità dello scheduling (mediane 5,91h retail e 6,85–6,87h DEMO) e marcare simboli stale; non attribuire cause a cron o mercato senza log.
E. **Release:** integrazione controllata di Cockpit e Contributors, mantenendo banner versione+timestamp Europe/Rome su pagine modificate, dopo permesso esplicito; zero sovrapposizione col Mac/Codex.

## Vincoli invariati
Nessun deploy, merge, attivazione, registrazione collaboratore, query GraphQL Cloudflare nuova, Secret nuovo, modifica Oracle, ordine reale o spesa senza consenso. Nessun test storico ripetuto. Se serve un'altra conversazione, usare questo checkpoint V20 come continuità.
