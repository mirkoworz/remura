# REMURA Shark CVD — prima prova gratuita (Track D / D0.1)

**Solo studio, non segnali operativi.** Codice: [remura_shark_cvd_fxcm_v01.pine](remura_shark_cvd_fxcm_v01.pine).
Roadmap: [ROADMAP-D-TRADINGVIEW-CVD.md](../../ROADMAP-D-TRADINGVIEW-CVD.md).

## Uso su TradingView

1. Accedi con il tuo account Premium dal **browser con Pine Editor** (consigliato desktop; l'app iPhone può non esporre l'editor Pine). Apri `FXCM:EURUSD`, grafico **5m**.
2. Apri **Pine Editor** e crea un nuovo indicatore, sostituisci il codice con il contenuto integrale del file `.pine`. Salva con nome `REMURA Shark CVD D0.1` e aggiungi al grafico.
3. Segnala l'esito compilazione, testo esatto di eventuali errori, e screenshot con pannello CVD. **Questo script non è ancora stato compilato/testato nel runtime TradingView**; i test GitHub sono solo un modello di riferimento offline.
4. Mantieni **disattivata** l'opzione `Abilita alert di RICERCA`. Il Pine non genera ordini né invia dati a REMURA finché non configuri volontariamente un alert.
5. Un eventuale pannello vuoto/arancione significa `DATI INCOMPLETI / NO SIGNAL`, non prova di assenza di divergenza. Il codice richiede esattamente cinque barre da 1m per ogni barra da 5m e invalida il resto della giornata se manca anche una sola barra.

## Cosa misura

- Volume delta **stimato**: la direzione delle barre FXCM da 1 minuto polarizza il volume disponibile e crea un cumulato che si azzera per ogni nuovo giorno TradingView.
- Due pivot di **prezzo** confermati; confronto del CVD agli stessi istanti; nessun look-ahead nei segnali che appaiono sulla barra di conferma.
- Non è il vero volume aggressore dei futures e non può dire quale istituzionale ha comprato o venduto.
- Non duplica il vecchio proxy cTrader (CLV×volume): fonte, metodo, unità e timeframe devono rimanere diversi.
- I dati storici/ricalcolati e realtime possono differire per limiti e correzioni del feed. Confermare su TradingView prima di ogni analisi scientifica.

## Alert e collegamento futuro

Se, dopo la prova e la verifica di qualità, decideremo di abilitare gli alert **solo per ricerca**: la casella Pine va attivata e l'utente deve creare esplicitamente un alert TradingView su **Any alert() function call**. Il messaggio JSON contiene identificativo evento deterministico, origine, algoritmo, tempi dei pivot, rilevamento e numeri CVD/prezzo. Un alert storico non viene inviato retroattivamente.

**Per ora NON inserire URL webhook**, non esporre la VPS/Tailscale, non incorporare token o dati privati nel codice Pine e non copiare chiavi in GitHub. TradingView usa porte 80/443, richiede 2FA per i webhook e non garantisce consegna; in seguito progetteremo un ricevitore HTTPS minimamente esposto con deduplica e controlli quota.

## Test locali offline

`python -m unittest discover -s tests -p 'test_track_d_tv_cvd_reference.py' -v`

Questi test **non compilano Pine**: esercitano un modello Python causale e controlli statici minimi. La compilazione TradingView, la parità con il CVD nativo e la prima vera consegna JSON richiedono verifiche distinte.

## Gate e costi

Nessuna modifica alla web app REMURA, al backend, a Oracle o al feed cTrader. Nessun acquisto futures. Premium è già un abbonamento esistente; le quote script/alert/1m vanno osservate. La versione applicativa visibile su tutte le pagine REMURA rimane invariata fino a un rilascio LIVE coordinato.
