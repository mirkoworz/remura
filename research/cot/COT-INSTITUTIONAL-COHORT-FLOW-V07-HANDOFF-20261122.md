# REMURA Shark Science COT v0.7 — flusso istituzionale TFF per coorte
22 novembre 2026 · Europe/Rome · SOLO LAB, dati sintetici in-memory.

## Valore nuovo per il prodotto REMURA
Non un altro test infrastrutturale: lettore descrittivo delle posizioni TFF Asset Managers e Leveraged Funds per uno stesso contratto CFTC, su due o tre martedi' consecutivi. Usa solamente l'as-of v0.6 append-only disponibile alla data della decisione.

- research/cot/cot_institutional_cohort_flow_v07_lab.py
- research/cot/test_cot_institutional_cohort_flow_v07_lab.py (17 nuovi casi)
- .github/workflows/remura-cot-cohort-v07-only.yml

Metriche: saldo netto long-short per categoria, normalizzato sull'open interest della stessa settimana e presentato in percentuale (NON probabilita'); variazione settimana-su-settimana in punti percentuali, accelerazione con 3 settimane, variazione open interest, indicazione puramente descrittiva CO_MOVING/DIVERGENT/UNCHANGED_OR_MIXED_FLAT.

Regola fondamentale: se una qualunque delle 2/3 settimane manca nel ledger append-only **alla decisione**, l'intero confronto e' UNKNOWN, senza fallback su cot_reports legacy o valore corrente. Le revisioni sopravvenute NON possono correggere decisioni passate.

## Limiti
- Asset Managers e Leveraged Funds sono categorie aggregate del report TFF, NON istituti individuali identificati, operazioni degli insider o tutte le cosiddette balene.
- Il COT e' settimanale e pubblicato dopo la data di riferimento; un report di martedi' non prova che il dato fosse pubblicato martedi'.
- Il ledger v0.6 usa clock/fonte locale non verificati, NON dati reali Oracle. Futures CFTC non e' un ticker FX spot; orientamento, scadenza, FX inversioni e basis da verificare separatamente.
- Nessun punteggio buy/sell, soglia ottimizzata, esito di trading, forecast o margine di profitto dichiarato.
- Si tratta di un componente pronto per l'integrazione futura sotto prove reali, non di una funzione attiva nella pagina pubblica.

## Mac / avvio
Nessuna migrazione Oracle o modifica collector. Prima di qualsiasi input COT reale serve backup ripristinabile, schema forward-only affidabile, clock ricevuta verificabile e mapping contratto-to-FX ammesso. V0.7 rimane report DESCRIPTIVE_UNATTESTED e NO-GO alpha.
