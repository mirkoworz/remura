# REMURA v0.3 — Radar istituzionale multi-asset

Web app gratuita per iPhone e PC, basata sui report settimanali ufficiali CFTC.

## Apri la web app
- [Radar Forex (28 coppie principali)](https://mirkoworz.github.io/remura/)
- [Radar multi-asset (Forex, oro, argento e indici USA)](https://mirkoworz.github.io/remura/mercati.html?v=3)

## Fonti
- Forex e indici finanziari: [CFTC TFF - Futures Only](https://publicreporting.cftc.gov/Commitments-of-Traders/TFF-Futures-Only/gpe5-46if), dataset `gpe5-46if`.
- Oro e argento: [CFTC Disaggregated - Futures Only](https://publicreporting.cftc.gov/Commitments-of-Traders/Disaggregated-Futures-Only/72hh-3qpy), dataset `72hh-3qpy`.

## Mercati supportati
- Tutte le 28 coppie **distinte** delle otto valute: EUR, GBP, AUD, NZD, USD, JPY, CAD, CHF (la selezione utilizza una sola direzione per ogni coppia: ad es. EURUSD, non USDEUR).
- XAUUSD (future Gold COMEX) e XAGUSD (future Silver COMEX).
- US500 (future E-mini S&P 500), NAS100 (future E-mini Nasdaq-100), US30 (future Mini Dow x5), US2000 (E-mini Russell 2000), DXY (US Dollar Index).

## Scanner istituzionale automatico
- **Movimenti maggiori**: ordina i cambi di posizione netta (long-short)/open interest settimanali per ampiezza in punti percentuali.
- **Cambi net long/short**: indica il passaggio netto da positivo a negativo o viceversa, con soglia minima ±0,5 pp. Non implica l'inversione di prezzo.
- **Accelerazioni**: stessa direzione in due settimane consecutive, con incremento nell'ampiezza della variazione settimanale di almeno 1,5 pp.
- Esclude report più vecchi di 14 giorni e intervalli consecutivi oltre 14 giorni. Per il Forex le coppie sono correlate tra loro.
- Fonte primaria per movimento: Leveraged Funds nel TFF (FX/indici), Managed Money nel Disaggregated (metalli). La comparabilità tra categorie è limitata.

## Correzione metalli v0.3
Socrata Disaggregated usa i campi `prod_merc_positions_long` e `prod_merc_positions_short` (senza `_all`). La correzione è nel codice pubblicato; caricamento dell'API dal browser da verificare.

## Metodologia e limiti
- `Net % OI = (Long - Short) / Open Interest * 100`.
- Per i cross Forex, il proxy è `Net% valuta base - Net% valuta quotata`; non è un contratto COT diretto sul cross.
- Forex e indici mostrano categorie Asset Manager e Leveraged Funds della CFTC TFF.
- Oro/argento mostrano invece **Managed Money** e **Producer/Merchant**, categorie *diverse* del report Disaggregated. Gli hedger possono assumere posizioni legate a copertura e non a una direzione di prezzo.
- Il dato è settimanale, relativo alle posizioni del martedì e normalmente pubblicato venerdì: non è realtime.
- Per i mercati senza righe CFTC riconosciute la vista multi-asset mostra **N/D** (non dati inventati).
- La dashboard originale è ancora dotata di modalità **DEMO** chiaramente etichettata quando il caricamento Forex fallisce.

## Installazione iPhone
Apri il sito con Safari → Condividi → Aggiungi alla schermata Home.

## Test
Parser e calcoli Forex, Gold e indice S&P 500 testati su dati di esempio controllati. Il corretto caricamento *live* di oro e indici va confermato dal browser dell'utente; il passaggio non si deduce dalla compilazione del codice.

Il progetto è sperimentale e non costituisce consulenza finanziaria.
