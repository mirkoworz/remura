# REMURA V20.1 — MISURAZIONE REALE INCREMENTALE
Aggiornamento: **23 novembre 2026, ore 06:37 CET (Europe/Rome)** · NON DISTRIBUITO · ZERO NUOVI SERVIZI

**Eredita V01–V20 e il ramo research/remura-v20-real-measurements-20261122.** Nessuna modifica a main, produzione, Cloudflare/D1/Access, Oracle, Mac/Codex, provider, utenti o Secrets.

## Allineamento temporale corretto
- Checkpoint OWNER: 22 novembre 2026 ore 23:25 CET = **2026-11-22T22:25:00Z**.
- Cutoff dell'audit: **2026-11-23T05:35:00Z** = 06:35 CET.
- I timestamp nei record attestano l'orario degli snapshot salvati, NON un first-seen indipendente.
- Dati Myfxbook e Capital DEMO sono sentiment di clienti, non posizioni istituzionali, ordini o CVD.

## Nuove prove GitHub post-checkpoint
**Myfxbook pubblico**: main HEAD **a1188f8af77951b9c59b7bb1facbfa6fe2f820e7** (un commit oltre cce37d0). Run scheduled **45102902172 SUCCESS**, Pages **45102920518 SUCCESS**; latest 23/11 **02:55:17 UTC**, 89 simboli presenti nello snapshot, 30 serie aggiornate sulle 34 storiche.

**Capital DEMO privato**: run **45102692200 SUCCESS**, log verificato: 31 mercati acquisiti. Latest **02:53:02 UTC**; metrica client_positions. Il ledger privato giorno UTC 23/11 riporta 2 chiamate prenotate: dato storico, NON garanzia di budget futuro. Nessuna chiamata nuova a Capital da questo audit.

**Firestore**: run **45102719693 SUCCESS**, log **32 documenti sincronizzati**; non 32 rendimenti, segnali o outcome.

PR #105 e #106 ancora OPEN DRAFT, Cockpit v1.68 ancora LAB e non integrato in main.

## Rilevazioni vere appena aggiunte
Confronto diretto di **tutti i 30 storici Myfxbook aggiornati** e **tutti i 31 storici Capital privati** con il record al checkpoint. Capital è riportato SOLO in forma aggregata.

| Indicatore | Myfxbook retail | Capital DEMO |
|---|---:|---:|
| Nuove acquisizioni record dopo checkpoint | 30 | 31 |
| Ultima acquisizione UTC | 02:55:17Z | 02:53:02Z |
| Precedente acquisizione UTC | 22/11 22:23:40Z | 22/11 20:45:11Z |
| Gap singolo ciclo | 4h31m37s | 6h07m51s |
| Strumenti con percentuale long cambiata | **18/30** | **30/31** |
| Strumenti con percentuale long uguale | 12/30 | 1/31 |
| Payload oltre timestamp cambiato | 30/30 | 30/31 |
| Record totali conservati ora | 3.924 | 3.822 |

**61 nuove letture, 48 percentuali long variate, 13 invariate.** NON sono 48 segnali o trades. Totale archivi conservati: **7.746** contro 7.715 a V20. La crescita netta di 31 appartiene a Capital; Myfxbook conserva una **finestra mobile di 126 record** per ciascuno dei 30 strumenti attivi. Il totale Myfxbook non cresce quando il vecchio record esce dalla finestra. L'audit non preserva i record eliminati dalla retention.

### Esempi pubblici concreti
- USDJPY: **59% -> 51% long, -8 punti percentuali**.
- GBPCAD: **-5 pp**; XAUUSD: **62% -> 57%, -5 pp**.
- EURCHF e GBPJPY: **-4 pp** ciascuno.
- EURUSD: **85% -> 85%**, ma altre metriche retail sono mutate.
- CADJPY: **79% -> 79%**, ma altre metriche retail sono mutate.

I quattro indici Myfxbook **NAS100, US2000, US30, US500** rimangono obsoleti: ultimo record del 22 ottobre. La presenza di un simbolo nel feed generale non equivale a una storia fresca.

## Codice V20.1 nuovo, totalmente offline
- research/v20_incremental_observation_audit.py: legge SOLO file esistenti, valida UTC, monotonia timestamp, assenza duplicati/futuro, percentuali, baseline prima del checkpoint, delta long e variazione delle altre metriche, gap, stale >24h e retention. Output privato Capital **esclusivamente aggregato**, senza nomi, valori per strumento o percorsi.
- research/test_v20_incremental_observation_audit.py: **9 NUOVI test mirati** su nuovi controlli, privacy, no lookahead, stale, record invariati e più aggiornamenti dopo checkpoint. Le vecchie suite V20 non vengono rieseguite.
- .github/workflows/remura-v20-incremental-observation-audit.yml: CI limitata al nuovo codice/ramo, nessun Secret, dati privati, Cloudflare o provider.

Esempio offline con data pubblica e checkpoint corretto:

~~~bash
python3 research/v20_incremental_observation_audit.py \
  --myfxbook-dir data/myfxbook/history \
  --since 2026-11-22T22:25:00Z \
  --as-of 2026-11-23T05:35:00Z
~~~

Se il privato collector è già disponibile **localmente**, aggiungere la directory --capital-dir ../remura-collector/private/capital/history. Non fare push di dati, path, file o output privati a questo repository pubblico. Il codice emette solo aggregati, ma non costituisce automaticamente autorizzazione alla pubblicazione dei metadati privati.

## Risultati COT / CVD / performance / collaboratori
- COT ufficiale verificato in V20: report CFTC TFF sulle posizioni futures del **17 novembre**, pubblicato il **20 novembre**; EUR/JPY/CAD net Asset Manager e Leveraged Funds già documentati nel precedente report. Il martedì as-of NON è il venerdì di disponibilità.
- TradingView CVD TEST holdout partito il **23/11/2026 00:00 UTC**. Il codice GitHub e i workflow manuali non provano Worker runtime, alert live, eventi con first_seen e prezzo indipendente. **Stato: NON ATTESTATO**, non zero trade e non alpha negativo. Nessuna query Cloudflare eseguita ora; la precedente autorizzazione di 2 GraphQL è esaurita.
- Nessun PnL/alpha/hit-rate/edge calcolabile senza prezzo indipendente temporalmente allineato, prova di first-seen, universo strumenti congelato, comparatore price-only, costi/spread e outcomes 60m/H4/24h realmente maturi.
- Pilot 1 OWNER + 1–2 CONTRIBUTOR ancora **NO-GO**: posti Access, consumo giornaliero D1 e billing personali UNKNOWN. Necessari runtime JWT/server role/ownership/receipt/approvazione OWNER, Safari e revoca completa prima dell'attivazione. Nessun utente attivato.
- Free-first: nessun provider interrogato e nessun nuovo servizio a pagamento. La capacità storage vista nei vecchi log Cloudflare non dimostra capacità giornaliera residua.

## Prossime operazioni esecutive senza duplicazioni
1. Acquisire prova **runtime TEST e ricevute CVD forward-only** da Cloudflare SOLO dopo consenso separato mirato; mai ricostruire un first-seen.
2. Collegare dati indipendenti di prezzo alle sole decisioni future con available_at precedente, quindi confrontare CVD+contesto contro price-only, con costi e censura.
3. Valutare retention append-only dei dati Myfxbook prima che il rolling elimini evidenza vecchia, ma attivarla SOLO in ambiente e budget autorizzati senza sovrapporsi al Mac/collector.
4. OWNER da iPhone legge nel dashboard Cloudflare Access/Workers/D1/Billing in sola lettura per chiudere il Free gate; poi autorizzazione distinta per pilot reale.
5. Cockpit e Contributors integrati solo dopo revisione e merge/deploy autorizzati; eventuali pagine modificate mostrano in cima versione e timestamp Europe/Rome.

**Conservare integralmente V01–V20 e le suite già GREEN.**
