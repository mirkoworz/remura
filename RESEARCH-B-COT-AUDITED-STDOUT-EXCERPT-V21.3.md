# REMURA — FILONE B V21.3 LAB — salvataggio parziale reale CFTC dai log già acquisiti
**Versione/aggiornamento:** V21.3 LAB — 23/11/26, 21:35:43 Europe/Rome. **Ramo:** `research/filone-b-cot-intelligence-v206-20261123`, PR #108 Draft.

## Risultato non sintetico finalmente conservato senza nuove richieste CFTC

Lo storico audit pubblico già autorizzato una tantum, [run #45206837974](https://github.com/mirkoworz/remura/actions/runs/45206837974), job `137804869184`, **SUCCESS**, riportò sulla console i risultati descrittivi calcolati dai dataset ufficiali CFTC Socrata, letti in data `2026-11-23T15:35:17.664069Z`. Il snapshot completo fu temporaneo sul runner e non ha artifact scaricabili. Il log esistente però conserva **12 righe NUMERICHE REALI**, oltre a riepilogo copertura.

Le abbiamo trascritte direttamente dal job esistente in `research/real-proofs/REMURA-B-CFTC-20261123-STDOUT-PARTIAL-EXCERPT.json`. Non sono fixture sintetiche e non sono valori inventati. Il file è **solo un estratto della console di un run GitHub riuscito**: non recupera le 980 righe sorgente, non verifica autonomamente il digest delle 980 righe, non rappresenta uno snapshot CFTC completo e non attesta una firma indipendente del log. Si conserva il digest *dichiarato dalla vecchia esecuzione* `a2d58c5a3347c121b491c5f495f7ee01ed83b6a282cc11fb2e5f49b1688ffb23` esplicitamente marcato come non verificabile senza i raw completi.

**CFTC report 17/11/2026 vs 10/11/2026**, `deltaCategoryA_pp` (variazione settimanale net/OI categoria A, in punti percentuali del rispettivo open interest), `categoryGap_pp` (differenziale descrittivo categoria A rispetto a B):

| Gruppo | Simbolo | Delta cat. A (pp OI) | Gap cat. A–B (pp OI) |
|---|---|---:|---:|
| TFF, sintetico Forex | GBPAUD | +7.6571 | +1.8347 |
| TFF, sintetico Forex | GBPNZD | +6.9413 | -39.6856 |
| TFF, sintetico Forex | GBPCAD | +6.1169 | -78.7651 |
| TFF, sintetico Forex | AUDCHF | -5.8250 | -65.7386 |
| TFF, sintetico Forex | EURGBP | -5.7489 | +82.9774 |
| TFF, futures finanziari | US30 | -11.7403 | -13.3727 |
| TFF, futures finanziari | NAS100 | +2.7570 | +31.6534 |
| TFF, futures finanziari | US500 | -2.6226 | +53.8889 |
| TFF, futures finanziari | DXY | +1.7897 | +36.0000 |
| Disagg, futures fisici | XAUUSD | -2.5162 | +26.3669 |
| Disagg, futures fisici | XAGUSD | -2.0846 | +11.5149 |
| Disagg, futures fisici | USOIL | -0.4953 | -19.7569 |

`TFF` compara Asset Manager/Institutional con Leveraged Funds; `Disaggregated` compara Managed Money con Producer/Merchant. I cinque cross FX sono differenze **sintetiche** tra futures di singole valute, non 5 posizioni spot direttamente misurate e non 5 esperimenti indipendenti. Il job precedente riportava 28 cross calcolati, ma soltanto i **primi cinque** erano stampati. Per i 7 futures diretti, invece, tutti e sette i record sono stati stampati.

## Utilizzo futuro senza inganno

Il nuovo file JSON può essere letto in sola lettura da un componente di interfaccia separato, con etichette sempre visibili `PARZIALE · CFTC SETTIMANALE · PRELEVATO IL 23/11`. Non autorizza merge nel Filone D, deploy, schermate BUY/SELL, feed live né aggiornamenti automatici. I controlli `tests/test_cot_stdout_excerpt_v213.py` assicurano che le 12 cifre corrispondano all'output scritto del job e che questo estratto **non superi mai** il validatore per un dataset pubblico completo.

**Separazione dai moduli B esistenti:** `scripts/cot_offline_parity_fx_bundle.py` richiede ancora un **vero snapshot completo pubblico + copia della cache privata** per creare 7 fattori numerici e misurare 28 confronti. L'estratto V21.3 non può soddisfare quei requisiti, non costituisce una prova `first_seen_at` e non fornisce prezzi futuri. Non ripetere il vecchio audit per forzare la ricostruzione.

## Checkpoint scientifico
- **Reale:** 12 valori settimanali parziali stampati da audit CFTC riuscito, persistiti per la prima volta nel repository LAB (il file persistito **non** ha firma sorgente indipendente).
- **Non disponibile:** 980 righe CFTC RAW, vettore autentico completo dei 7 fattori, parità con D1/SQLite privato, provenienza temporale immutabile, return forward/alpha/statistica.
- **Test:** cinque controlli nuovi solo offline; CI da registrare con run verde separato.
- **Costo incrementale:** €0 API CFTC, 0 HTTP, 0 Secrets, 0 Cloudflare/Oracle, 0 deploy, 0 merge; quota residua GitHub Actions non verificata.
