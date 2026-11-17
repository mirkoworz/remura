# REMURA — NQ OPTIONS / OPEN INTEREST | CHECKPOINT v0.2, 10/11/2026

**Solo ricerca offline. Nessun deploy/merge, nessun trigger operativo.** Track A, B (#89), C, main, Oracle e collector invariati.

## Fonti raccolte

1. **CME QuikStrike, fonte primaria**: https://www.cmegroup.com/tools-information/quikstrike/open-interest-heatmap.html — heatmap ufficiale OI per strike, scadenza e call/put. I conteggi puntuali della seduta 09/11 per i nostri strike **non sono stati certificati** nel canale di accesso disponibile. L'anteprima del Daily Bulletin CME presentava disallineamenti di data tra testo estratto e pagina visualizzata: **non** usarla come prova quantitativa per questa sessione. Verificare il PDF datato in modo riproducibile o esportazione manuale consentita, licenza di riuso e first-seen.

2. **GEX Metrix, modello NDX→NQZ26**: https://www.gexmetrix.com/gex/nq — 10/11 04:40 ET (orario dichiarato sulla pagina quando consultata); Zero Gamma, Call/Put Walls, Max Pain e strike gamma secondari raccolti in `data/reference-sources-2026-11-10.json`. La pagina è dinamica: uno snapshot successivo può mostrare numeri diversi o "n/a". Non equivale a dati CME OI.

3. **ZeroGEX, modello NDX→NQZ26**: https://zerogex.io/nq-gamma-levels — snapshot dichiarato del 09/11 15:59 ET, con Call Wall, Put Wall, Gamma Flip, Max Pain e Pin Strike. Pagina dinamica, impossibile qui verificare una ricevuta storica indipendente.

4. **Open Interest opzioni NQ, riscontro secondario**: https://trading-commodity.com/options-chain/nq/ — tabella della sessione 09/11/2026, scadenza 18/12/2026, contratto NQZ26. Il sito indica tra le put 28.000: 3.852 contratti; 28.500: 1.246; 27.500: 947; 27.250: 664. Non e' una verifica CME e **non** rappresenta il totale OI di tutte le scadenze.

## Logica di confronto

- Le zone operative del gruppo privato rimangono fuori dal repository pubblico: si usano solo nella copia privata fornita dall'utente.
- Vicinanza a qualsiasi strike o GEX pubblicato = confronto **post-hoc**, non conferma metodologica; i livelli dei diversi provider non sono indipendenti né una prova di inventory dealer.
- OI per strike non e' gamma exposure: OI misura contratti aperti; GEX e' una stima dipendente anche da IV, scadenze, segni convenzionali e prezzi.
- Distinguere indice NDX, ETF QQQ, future NQZ26 e future options NQ: **non** sommare o confrontare i prezzi senza base/contratto chiari.
- I timestamp delle pagine non sostituiscono una ricezione locale originale registrata prima della pubblicazione degli amici o prima della sessione; **nessuna validazione prospettica** del 10 novembre.
- Non abilitare scraping, cron, provider paid, trading o UI live; prima controllare licenze e regole CME, costi e eventuale quota GitHub Actions.

## Prossimo gate

Ottenere **OI CME ufficiale per strike e scadenza** da una vista/export permessi e salvarne data del report + SHA; poi protocollo pre-registrato e raccolta *first-seen* giornaliera su più sessioni. Aggiungere in seguito Profile Volume futures con volume di borsa, non tick-volume FX.

**Stato: fonti third-party raccolte; verifica Open Interest CME ufficiale INCOMPLETA. Nessuna edge/accuratezza di strategie certificata.**
