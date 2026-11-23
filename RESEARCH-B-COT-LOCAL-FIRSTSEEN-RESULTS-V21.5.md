# REMURA Filone B — V21.5 LAB, checkpoint COT locale reale e first_seen

**Versione aggiornamento: B V21.5 LAB · 23/11/2026, 23:52 Europe/Rome.**
**Ramo:** `research/filone-b-cot-intelligence-v206-20261123` · PR #108 Draft · **solo ricerca offline; nessun deploy né merge.**

## Evidenza riferita dal proprietario via schermate Codex Mac (23 novembre 2026, ~23:50 CET)

La verifica effettuata da Codex su un **backup privato SQLite Oracle verificato** è stata condivisa mediante screenshot in chat, **non con un export di righe sorgente controllabile autonomamente dal CI di GitHub**. Manteniamo separati i risultati *riferiti dal controllo locale* dalla convalida indipendente CFTC.

| Controllo locale riferito | Risultato |
|---|---|
| Database privato | Backup offline; in precedente rapporto: integrity_check OK, SHA-256 coincide con manifest origine, commit WAL visibili inclusi |
| `cot_reports` totali | 840 righe |
| `cot_first_seen` totali | 56 righe complessive (non significa che tutti siano nelle due date analizzate) |
| Report CFTC 2026-11-17 | TFF 11/11 + Disaggregated 3/3 = 14/14 |
| Report CFTC 2026-11-10 | TFF 11/11 + Disaggregated 3/3 = 14/14 |
| First seen su ciascuno dei due report al 2026-11-23 23:50 CET | 14/14 timestamp validi ciascuno; 0 assenti, 0 futuri rispetto all'istante di verifica, 0 invalidi |
| Prima acquisizione locale del report 2026-11-10 | **17 novembre 2026** (come riferito da Codex) |
| Prima acquisizione locale del report 2026-11-17 | **21 novembre 2026** (come riferito da Codex) |
| Fattori di posizionamento FX | 7/7 valute futures TFF, dati di netto e variazioni categorie Asset Manager e Leveraged Funds calcolati offline |
| Cross FX relativi | 28/28 calcolabili: 21/21 a due gambe futures + 7/7 con USD impostato a riferimento matematico zero, non posizionamento USD rilevato |
| Snapshot JSON | Preparato da Codex in cartella privata esterna al repository; file e dati individuali non inviati a GitHub |
| Parità con snapshot pubblico CFTC originale | **NON VERIFICATA** per 17/11 e 10/11, TFF e Disaggregated |
| Fonte/versione ufficiale dei dati al primo seen | **NON VERIFICATA**, non confondere timestamp locale con pubblicazione ufficiale |
| Precisione ora ufficiale di pubblicazione | **NON VERIFICATA** in questa acquisizione |
| P&L forward, potere predittivo, alpha | **N/D** |

**Causalità vincolante:** non retrodatare il report del 10/11 come utilizzabile prima della prima acquisizione locale del **17/11**, né il report del 17/11 prima della prima acquisizione locale del **21/11**. Il report date è diverso sia dall'orario di pubblicazione CFTC sia da `first_seen_at` privato. Il solo conteggio di first_seen **non** prova immutabilità/autenticità della prima versione dei valori archiviati. Non attribuire miglioramenti predittivi al fatto che i dati sono completi. Le 28 serie sintetiche sono interdipendenti e USD=0 è una normalizzazione, non prova di flussi USD.

**Interfaccia futura:** si può preparare un rendering LAB in sola lettura dei sette fattori / 28 cross, senza pubblicare il JSON locale riservato. Indicare `LOCAL_CFTC_PRIVATE_SNAPSHOT`, `PUBLIC_PARITY_NOT_VERIFIED`, fonte CFTC TFF, data del report, prima acquisizione locale, differenza fra numeri effettivamente misurati e USD zero. Evitare etichette `verificato CFTC pubblico`, `live institutional flow`, `BUY/SELL`, `alpha`.

## Prossima azione: parità originale, non duplicare calcoli

Eseguire, **solo dopo separata autorizzazione esplicita**, una verifica contro uno snapshot CFTC ufficiale completo 2026-11-17 e 2026-11-10, preferendo un file pubblico integrale **già disponibile offline** e acquisito con provenienza documentata. Il vecchio audit ufficiale del 23/11 [run #45206837974](https://github.com/mirkoworz/remura/actions/runs/45206837974) ha solo 12 valori stampati, non le 980 righe originali riutilizzabili: quel log **non** consente una parità completa. Non effettuare nuove chiamate HTTP senza richiesta/autorizzazione specifica. 

Queste schermate non costituiscono una nuova esecuzione CI né attestazione da parte di GitHub. Non ripetere i controlli locali della presenza 14/14, dei 28 cross o delle 4 coorti M15, già completati.

**Costi incrementali di questo checkpoint:** nessuna API, nessun GitHub Actions run, nessuna nuova risorsa Cloudflare, Oracle o provider. Quote residue Free da verificare separatamente.
