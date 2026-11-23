# REMURA — CHECKPOINT V20.4: CVD reale e disponibilita' prezzi cTrader
Aggiornamento: **23 novembre 2026, ore 07:26 CET — Europe/Rome**.

**Stato:** laboratorio isolato. Eredita integralmente checkpoint V01–V20.3; nessun merge main, deploy, Oracle, Mac/Codex, collector privato, Cloudflare, D1, Access, Firestore, nuovi utenti o costi. Nessuna nuova chiamata Cloudflare effettuata in V20.4.

## Risultati REALI mantenuti
Run https://github.com/mirkoworz/remura/actions/runs/45121703188: 12 chiusure M5 CVD valide su 12 tra 04:30Z e 05:25Z, giorno 23/11/2026, FX:EURUSD, ritardo massimo 15.510 ms, 0 slot mancanti. Diagnosi consumata completamente l'autorizzazione a due richieste REST TEST: 1 GET inventario + 1 POST esclusivamente SELECT, 25 righe lette, 0 scritte. Radar 12 OBSERVATION_ONLY, 10 FP_ALIGNED, 2 FP_DISAGREE, 12 ER_NONE, NO_OPERATIONAL_SIGNAL. Non confondere questi conteggi con successi di trading.
Dati Myfxbook 30 e Capital DEMO privato 31 aggiornamenti restano stati verificati; 7.746 osservazioni trattenute e nessun outcome indipendente o alfa ancora dimostrato.
Prezzo BCE daily ufficiale del 20/11 osservato 23/11 05:46:14Z, 28 cross, non M15 e non quotazione eseguibile.

## Il progresso V20.4: 12 M5 non sono 12 ingressi indipendenti
Nuovo codice sul ramo research/remura-v204-private-price-coverage-20261123.
Il massimo lag realmente osservato dei receipt CVD era 15,510 secondi. Scegliendo prudenzialmente il PRIMO OPEN M15 successivo a (close M5 + lag massimo), i 12 M5 diventano SOLO quattro potenziali istanti temporali OPEN M15:
- UTC 04:45, 05:00, 05:15, 05:30 il 23 novembre.
- Un'ora: prezzi completamente chiusi alle UTC 05:45–06:30, 06:45–07:30 CET.
- Quattro ore: UTC 08:45–09:30, 09:45–10:30 CET.
- Ventiquattro ore: UTC 04:45–05:30 del 24 novembre, 05:45–06:30 CET.
Sono slot temporali molto correlati, non decisioni di trading. La maturita' temporale non significa che il dato OHLC sia stato acquisito o sia continuo.

File REALMENTE AGGIUNTI:
- research/v204_private_cvd_price_coverage.py: legge il file pubblicamente attestato delle 12 ricevute e, solo su Mac/VPS autorizzato, in modalita' SQLite mode=ro e query_only=ON il campo payload EURUSD della tabella prezzi personale. Accetta solo provider ctrader e candele M15 ordinate, UTC, OHLC validi, gia' completamente chiusi. Conta solo completezza e gap per quattro coorti ai tre orizzonti 1/4/24 ore. NON esporta prezzi, ticker privati, account, raw JSON o statistica di rendimento.
- research/test_v204_private_cvd_price_coverage.py: 9 NUOVI test offline dell'adapter, usando il receipt reale gia' salvato e SOLO CANDELE SINTETICHE per validare i guardrail, in nessun caso prezzi reali.
- .github/workflows/remura-v204-private-m15-coverage.yml: CI isolato, 9 test nuovi e conferma che la prova CVD vera produce 4 coorti ma nessun esito senza prezzi privati, ZERO Secrets e ZERO chiamate cloud/broker.
- Prova CI https://github.com/mirkoworz/remura/actions/runs/45123836848 : **SUCCESS**, marker REMURA_V204_NEW_TESTS=9_PASS e REMURA_V204_REAL_CVD_INPUT_AND_PRIVATE_M15_ABSENCE=12_TO_4_COHORTS_NO_ALPHA_PASS.

VERDETTO: il database SQLite privato NON e' disponibile su GitHub. La CI riporta PRICE_NOT_PROVIDED (NON significa database VPS vuoto). Nessuna candela privata reale letta; nessun esito di trading misurato.

## Scoperta economica/legale su prezzi alternativi
La fonte Dukascopy ha storico Forex accessibile gratuitamente, ma i termini ufficiali vietano scraping/acquisizione automatizzata senza previo consenso scritto: https://www.dukascopy.com/swiss/english/legal-pages/terms-of-use/ . Per questo NON e' stata aggiunta nessuna chiamata o automazione Dukascopy.
Il motore cTrader gia' presente in scripts/ctrader_feed.py, scripts/price_store.py e scripts/statistical_validation.py supporta dati M15 privati; non duplicarlo e non cambiarlo durante lavoro Mac/Codex.

## Punti bloccanti scientifici
- L'aggregato reale delle 12 ricevute CVD NON contiene la decisione/direzione di ciascuna M5. Le 12 erano OBSERVATION_ONLY. Non inventare segnali dal rapporto 10/2 footprint/delta.
- Mancano accesso autorizzato ai prezzi cTrader M15 specifici del 23/11 e relative chiusure, provenienza verificata, segnali prespecificati, costi/spread/slippage.
- I 4 istanti temporali non costituiscono 4 operazioni né campioni indipendenti.
- Non ricostruire decisioni passate guardando ex post i prezzi. Non dichiarare successo o vantaggio istituzionale prima di una coorte lunga, forward-only, con controlli stessi-periodi.

## Prossima azione che NON richiede nuove spese
Alla prossima sessione Mac, previa verifica di non sovrapporsi a Codex, individuare il percorso esistente del DB prezzi PRIVATO senza condividerlo e provare SOLO la lettura con comando:

python3 research/v204_private_cvd_price_coverage.py --receipt-proof research/real-proofs/REMURA-V203-CVD-TEST-RECEIPTS-20261123.json --private-sqlite /PERCORSO_PRIVATO_EFFETTIVO/prices.sqlite

Eseguire nel checkout del RAMO V20.4, non sulla produzione; non ipotizzare il nome o percorso del database, non esportare database/credenti/chiavi e non fare nuove scansioni cTrader. Lo script puo' anche essere avviato senza --private-sqlite per attestare in modo esplicito PRICE_NOT_PROVIDED senza creare file.
Se la macchina e' spenta, **NON e' richiesto alcun intervento iPhone ora**.

## Roadmap continuativa
1. CVD: abbiamo prova attuale per 12/12 slot nella finestra TEST, non una copertura dell'intera giornata. Non ripetere query Cloudflare senza nuova specifica autorizzazione.
2. Prezzi: verificare cTrader privato in sola lettura, rilevare gap M15 e maturazione 60m/4h/24h. Nessun PnL finche' non ci sono scelte direzionali prospettiche e prezzi indipendenti.
3. Conservazione retail: trovare via FREE un archivio append-only prima che Myfxbook rolling elimini storia utile; no scrittura/deploy senza approvazione.
4. Contributors: quota Workers Free e D1 Free attestata con dashboard 23/11; Access seats, Billing e JWT/ownership/revoca reale ancora ignoti. Pilot live 1–2 NO-GO.
5. Versione web: Cockpit v1.68 LAB, Contributors LAB, splash Toro/Orso e Mac v1.65 non interferire; future pagine HTML aggiornate devono mostrare nuova versione e timestamp Europe/Rome in alto.
6. Conservare checkpoint e avanzare con risultati reali, senza rifare suite/test superati.

## Sicurezza / costi
ZERO nuove richieste Cloudflare/Broker, zero nuovo abbonamento o DB, zero deploy e nessuna modifica ai file HTML di produzione. Il CI ha soltanto impiegato una breve esecuzione di GitHub Actions su repository pubblico e non ha visto nessun dato privato.

**Sintesi V20.4:** transport CVD TEST reale provato 12/12; il nuovo motore di verifica di copertura prezzi M15 e' pronto e validato 9/9; prezzi privati non ancora consultati; alfa non provato.
