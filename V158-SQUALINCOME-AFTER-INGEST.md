# REMURA — Esperimento v1.58 Squalincome immediato dopo raccolta (offline)

**02/11/2026, ora italiana.** **Solo sviluppo GitHub**, nessun deploy, nessuna modifica a credenziali, costo broker, VPS, app visiva o database di produzione. Live rimane **v1.57**, con EURUSD e XAUUSD acquisiti a cadenza nominale 60 minuti (due intervalli osservati) e 38/38 mercati verificati in diagnostica.

## Problema misurato

Diagnostica privata #23: tutti e 38 i mercati erano recenti nel controllo prezzi, ma Squalincome ha escluso **14/34** per l'ultima **H1 più vecchia della sua soglia di 120 minuti**; nessuno escluso per M15/H4. H1 più vecchia 129 min, cioè 9 min oltre limite. Motivo: 36 mercati vengono acquisiti mediamente ogni 120 minuti in otto gruppi e Squalincome esegue una scansione indipendente ogni 15 minuti. Gli indicatori H1/H4 sono ricostruiti da vere M15 ricevute dal broker e **non devono** essere ricreati usando il tempo attuale senza candele nuove.

## Esperimento di calcolo, zero nuova rete

- Un **solo flag privato disattivo per default** `REMURA_SQUALINCOME_AFTER_INGEST_ENABLED=1` potrà, **dopo** un futuro rilascio controllato, abilitare la scansione dei **soli simboli effettivamente salvati** dal batch cTrader.
- `scan_once(...,targets=(...))` mantiene inalterati COT, i controlli di provenienza/qualità, la guardia H1 **120min**, H4 300min, M15 180min, l'idempotenza SQL e la verifica delle transizioni fra campioni realmente nuovi.
- Una scansione mirata **non sovrascrive** `squalincome_last_scan`: il quadro generale dei 34 mercati rimane quello della scansione periodica completa. Evita falsi 0-stale dopo un batch da cinque strumenti.
- Un lock nel processo protegge la scrittura delle osservazioni da sovrapposizioni fra thread periodico e thread post-ingest. Gli altri servizi continuano senza aggiornamenti di rete aggiuntivi.
- Macro senza COT diretto (DXY/VIX/GER30/UKOIL) non vengono aggiunti forzatamente ai 34 mercati monitorati. Il limite è massimo cinque simboli già acquisiti.
- L'azione invoca la scansione **solo se il flag è ON** e il collector/COT/monitor sono abilitati. Il codice non contiene ordini, notifiche, webhook, login né nuove API.

## Verifiche offline completate

- Test Python del server: flag OFF, filtro degli strumenti, batch che restituisce solo il simbolo salvato, dati invalidi, lock durante la scansione, zero nuove funzioni broker invocate dal monitor.
- Test Python del monitor: full snapshot conservato, COT e prezzi validi, baselines, transizione storica reale con primo evento unico, ripetizione senza duplicato, invalid input fail closed, nessun evento senza fonti.
- GitHub Actions `REMURA private price engine checks` e `REMURA insights checks` **success** nel commit candidato `10407dbf60d09c3aea20b58f4ae8ecd3f0c61fd1`. La prima esecuzione aveva unicamente un test che assumeva un ordine errato dell'elenco storico; test corretto per selezionare lo strumento per simbolo e poi nuova CI verde.

## Gate per futura abilitazione (non superati qui)

- [ ] Integrare prima v1.57 dal ramo #69 a main, eseguire CI di entrambe le suite sul commit finale, mettere in sicurezza lo SHA dell'autoupdater e *non* usare `--init-sha` alla cieca.
- [ ] Verificare con backup + restore-test e piano di rollback un **rilascio v1.58** isolato, che mantenga banner versione/data/ora aggiornato su TUTTE le pagine. Non attivare direttamente da GitHub senza check espliciti.
- [ ] Eseguire una diagnosi **read-only** della nuova modalità e una breve prova controllata: tempi `ingestAt`→`observeAt`, 34 simboli, eventi duplicati, scansione completa, Squalincome, integrità SQLite, RAM/disco, quote broker.
- [ ] Prima di valutare notifiche: **attenzione a report outcome**: un evento registrato da scansione mirata comparirà già in `lastEvents`, ma il campo `diagnostics.outcome` dell'ultima scansione completa può restare invariato fino al successivo aggiornamento; progettare una rappresentazione esplicita dei due timestamp/canali, senza proclamare `no_significant_event` come verità sul canale mirato.
- [ ] **Valutare miglioramento reale** rispetto alla sola scansione periodica, e distinguere *osservazioni tempestive* da *dati H1 sempre freschi*: questo prototipo non promette 34/34 sotto 120 min in ogni istante.
- [ ] Collegare dopo i test il progetto divergente CVD **PR #71**, ora anch'esso offline. Il CVD attuale è un **proxy CLV×tick volume** e deve dimostrare valore incrementale vs prezzo-solo, senza pretendere volumi istituzionali reali.

## Budget

**Nuove chiamate cTrader da questo esperimento: zero.** Vengono analizzati gli stessi dati SQLite già raccolti. Il costo computazionale di un scan di massimo 5 simboli ogni 15 minuti appare contenuto ma va misurato sulla VPS. RAM/disco favorevoli da soli **non certificano** costo Oracle Always Free né quota API libera.
