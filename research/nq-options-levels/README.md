# REMURA — NQ options-level research v0.1 — 10 novembre 2026

**ISOLATO / SOLO RICERCA.** Nessuna modifica a main, REMURA live, Oracle, collector o filoni A/B/C.

## Obiettivo
Confrontare separatamente: (1) zone operative pubblicate al mattino, (2) proxy GEX ottenuto dalle opzioni QQQ, (3) in futuro Open Interest ufficiale su opzioni NQ CME, (4) profilo volumetrico da volume futures autentico. Non dedurre la formula di terzi dalla sola vicinanza dei prezzi.

## Provenienza, licenze e sicurezza
- Le sei zone ricevute dall'utente il 10 novembre NON sono ripubblicate qui: provengono da un gruppo privato e i diritti di ridistribuzione non sono noti.
- Snapshot pubblico minimo del 09/11 alle 20:58:30 UTC: data/gex_qqq_reference_2026-11-09.json. Il file pubblico upstream esprime una stima GEX basata sulle opzioni QQQ, convertita nei livelli dell'indice NDX. **Non** sono prezzi delle opzioni sul future NQ e non sono dati ufficiali CME.
- Repository upstream: https://github.com/haus-edge/gex-levels ; al controllo del 10 novembre non era indicata una licenza software. Non importiamo il suo codice.
- Il timestamp nel file upstream non prova quando il dato fosse accessibile a un determinato osservatore; non equivale a receipt prospettica verificata.
- I livelli originali sono privi di timestamp di pubblicazione indipendentemente verificato e di identificazione certa del contratto NQ. Questo singolo caso e' escluso dalla validazione prospettica: NO edge, NO win rate, NO PnL.
- La heatmap CME e' consultabile su https://www.cmegroup.com/tools-information/quikstrike/open-interest-heatmap.html ; prima di acquisizione automatica valutare licenza, limiti e interfaccia machine-readable.

## Esecuzione offline

Il JSON privato deve avere le chiavi instrument=NQ, session_date=YYYY-MM-DD, levels=lista decrescente e published_at_utc=null quando sconosciuto.

    python3 research/nq-options-levels/scripts/compare_nq_levels.py /percorso-privato/zone.json research/nq-options-levels/data/gex_qqq_reference_2026-11-09.json
    python3 -m unittest discover -s research/nq-options-levels/tests -v

Solo libreria standard Python; nessuna rete, ordine, trade, schedulazione, prezzo live, accesso broker o segreto. Confronto **descrittivo** con differenze in punti, no soglia post-hoc o segnale.

## Gate successivi
1. Ricevute con ora di pubblicazione / primo avvistamento e contract-month NQ; anonimizzare dati del gruppo.
2. Verificare accesso gratuito e riuso legale di OI CME per strike e scadenza, confrontare con GEX QQQ senza mescolare basi prezzo.
3. Volume Profile reale NQ (POC, VAH, VAL) e registrazione dei livelli prima della sessione, evitando prezzi di indice/volume tick FXCM come sostituti.
4. Tolleranze congelate **prima** dei risultati, molte sessioni, baseline casuale e tecnica, walk-forward, costi, risultati OOS.
5. Nessun merge/deploy/cron/billing senza consenso, preflight e controllo costi.

**Revisione ricerca 0.1 / 2026-11-10. Versione applicazione REMURA invariata.**

## Spaziatura: ipotesi descrittiva, non ricerca della formula

`python3 research/nq-options-levels/scripts/inspect_spacing.py /percorso-privato/zone.json` rileva intervalli, multipli interi e residui di una griglia lineare, senza pubblicare i livelli originali. Il metodo e' **post-hoc** e non autorizza segnali o previsioni; intervalli teorici omessi dagli autori NON vanno trattati come vere zone operative. Test sintetici offline dedicati. Si valuta in futuro se la scala derivi da expected move, ATR/volatilita', volume profile o altre formule con dati indipendenti.
