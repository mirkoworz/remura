# REMURA TradingView v0.8.183 LAB — M5 INTAKE QUALITY

**Checkpoint: 21 novembre 2026 · 18:09 CET (Europe/Rome)**

## Stato confermato
- Repo pubblico `mirkoworz/remura`, branch indipendente `research/tradingview-intake-quality-v0183-20261121`.
- Base TradingView v0.8.182 `7fca951833c776fe1a677866f84a25024de5d070`.
- Commit testato: `5bbb020941839e0bf754a1af64ad661b0f750b93`.
- Run GitHub https://github.com/mirkoworz/remura/actions/runs/44928473032 **SUCCESS**; log verificato: `Ran 18 tests`, `OK`, `REMURA_TV_V0183_INTAKE=18_18_PASS`.
- **18/18 nuovi test PASS**: nessuna suite storica rieseguita, nessuna vera acquisizione, nessun Secret, nessun deploy/merge, main immutato, nessuna modifica Oracle o costi.
- Nuovi moduli `tradingview/delta-peaks/m5_intake_gate_v0183_lab.py`, `test_m5_intake_gate_v0183_lab.py` e one-shot `.github/workflows/remura-tv-intake-v0183-one-shot-ci.yml`.

## Controlli aggiunti (solo dati sintetici)
- Richiama il **controllo del protocollo V2 pinned** v0.8.182, senza modificare documentazione o ipotesi.
- Accetta eventi M5 artificiale con close UTC, next close, ora di ricezione e fingerprint anonimo. Accetta come tempestivi SOLO eventi ricevuti alla chiusura o dopo, entro **close + 120 secondi** e comunque prima del prossimo close M5. I tardivi restano tardivi e NON riservano retroattivamente.
- Blocca duplicati/confitti sullo stesso timestamp e sul digest, timestamp non UTC, next close incoerente, evento antecedente a close, dati non M5, origine non sintetica, batch malformato.
- Rispetta finestre congelate UTC (inizio incluso, fine esclusa): development 16–22 novembre; holdout1 23–29 novembre; holdout2 30 novembre–6 dicembre 2026. I dati fuori finestra non sono riassegnati ad altri fold.
- Non calcola esiti, segnali, PnL, match di coppie, alpha o performance; non usa ordini reali. Risultato sempre `decision=NO_GO_LIVE`, `provenance_attested=false`, `edge_claim_allowed=false`, `captures_activated=false`.

## Scienza e prossimi passi
- Il protocollo primario preregistrato resta CVD vs price-only a 60 min con costi ipotetici, matching FIFO per strato e incompletezza delle coppie trattenuta senza sostituzioni ex post.
- I 18 test nuovi **non** significano che l'edge sia stato trovato. Mancano acquisizione certificata, esportazioni con storia completa dei fold, outcome maturi, validazione fuori campione e controllo indipendente dei conflitti.
- Prossimo lavoro LAB: aggiungere attestazione offline della **copertura temporale M5** (barre mancanti e ritardi con cause), in modo che zero osservazioni non appaia come assenza di anomalie; mai modificare V2, mai inventare dati. Non attivare Private Capture o collector.
- Gli altri filoni sono mantenuti: Contributors v0.83 Cloudflare/Access sempre NO-GO real; Shark Science v0.4 COT/sentiment/delta/CVD/ER; Experience v0.30 toro/orso 3D + logo SMF; Oracle collector e Ampere Radar invariati; backup e Squalincome/TG in roadmap.
- Per LAB bastano GitHub e runner gratuito; nessun Mac richiesto.

**Esito: 18/18 PASS sintetico. Nessun risultato di trading, nessuna release reale.**