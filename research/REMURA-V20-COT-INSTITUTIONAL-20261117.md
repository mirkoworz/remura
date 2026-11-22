# REMURA V20 — COT istituzionali reali | aggiornamento 22/11/2026, 23:39:32 Europe/Rome

**Ricerca verificabile, non segnale operativo.** Fonte UFFICIALE: [CFTC TFF Futures-Only Financial Report](https://www.cftc.gov/dea/futures/financial_lf.htm), pubblicato/aggiornato **20/11/2026** su posizioni aggregate dei futures **17/11/2026**, variazioni settimanali rispetto a **10/11/2026**. Le categorie, le quotazioni e i codici contratto sono quelli di CFTC. Nessuna richiesta a provider privati, nessun deploy e nessun ordine.

## Snapshot vero per tre futures valutari

| Future | CFTC code | Open interest | Categoria | Long | Short | NET long−short | ΔNET settimanale | NET / OI attuale |
|---|---|---:|---|---:|---:|---:|---:|---:|
| Euro FX (EUR) | 099741 | 866.032 | Asset Manager/Institutional | 484.828 | 337.594 | +147.234 | -18.243 | 17,00% |
| Euro FX (EUR) | 099741 | 866.032 | Leveraged Funds | 116.493 | 193.080 | -76.587 | -4911 | -8,84% |
| Japanese Yen (JPY) | 097741 | 390.361 | Asset Manager/Institutional | 171.170 | 86.489 | +84.681 | -5663 | 21,69% |
| Japanese Yen (JPY) | 097741 | 390.361 | Leveraged Funds | 93.108 | 116.898 | -23.790 | -6935 | -6,09% |
| Canadian Dollar (CAD) | 090741 | 358.186 | Asset Manager/Institutional | 121.071 | 115.706 | +5365 | -9115 | 1,50% |
| Canadian Dollar (CAD) | 090741 | 358.186 | Leveraged Funds | 33.563 | 105.681 | -72.118 | -3913 | -20,13% |

**Formule:** NET = LONG − SHORT. ΔNET = (ΔLong) − (ΔShort) dalle colonne CFTC *Changes from November 10, 2026*. NET/OI attuale = 100 × NET / open interest del 17/11/2026. **NON** interpretare ΔNET diviso OI attuale come variazione esatta in punti di OI settimanale: l'OI passato era diverso. Se serve Δ(NET/OI), occorre usare anche OI del 10 novembre per ciascun contratto. Il campo *spreading* è separato e non va sommato al direzionale long o short.

## Lettura tecnica

- **EUR:** Asset Managers net LONG ma riducono il netto settimanale; Leveraged Funds net SHORT e accentuano lo short. Queste categorie **non concordano**: il Cockpit non deve produrre un unico finto 'consenso istituzionale'.
- **JPY:** Asset Managers net LONG sul future JPY; Leveraged Funds net SHORT. Una lettura del future JPY NON è automaticamente un long USDJPY: il cambio quotato USDJPY ha base USD e valuta quotata JPY, quindi orientamento inverso.
- **CAD:** Asset Managers leggermente net LONG, ma il netto si riduce molto; Leveraged Funds net SHORT accentuato. Contesto di disaccordo, non ordine di vendita su CADJPY.
- Una categoria regolamentare è un raggruppamento di operatori e posizioni pubblicate, non identificazione di singoli ordini o insider. Le coperture cross-market non sono qui visibili.

## Disponibilità temporale / anti-lookahead

- `position_as_of = 2026-11-17` è il martedì di rilevazione, **NON** il timestamp della conoscibilità pubblica.
- `public_report_updated = 2026-11-20` (fonte pagina CFTC). Per una simulazione storica con precisione intraday serve ora effettiva di pubblicazione indipendentemente attestata; **NON assegnare arbitrariamente 00:00 UTC del venerdì**.
- Senza attested first-seen del report e prezzi indipendenti successivi non è lecito calcolare performance.
- Non confrontare contratti COT di date diverse. Per TFF, una futura integrazione con Disaggregated richiede la medesima `position_as_of` del report.

## Riferimenti originali

- [CFTC TFF Futures Only, financial_lf.htm](https://www.cftc.gov/dea/futures/financial_lf.htm)
- [Portale COT CFTC](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm)

## Dati macchina — estratto pubblico auditabile

```json
[
  {
    "symbol": "Euro FX (EUR)",
    "cftc_code": "099741",
    "open_interest": 866032,
    "asset_manager": {
      "long": 484828,
      "short": 337594,
      "delta_long": -8888,
      "delta_short": 9355
    },
    "leveraged_funds": {
      "long": 116493,
      "short": 193080,
      "delta_long": 2442,
      "delta_short": 7353
    },
    "position_as_of": "2026-11-17",
    "published_date": "2026-11-20"
  },
  {
    "symbol": "Japanese Yen (JPY)",
    "cftc_code": "097741",
    "open_interest": 390361,
    "asset_manager": {
      "long": 171170,
      "short": 86489,
      "delta_long": 9848,
      "delta_short": 15511
    },
    "leveraged_funds": {
      "long": 93108,
      "short": 116898,
      "delta_long": 4019,
      "delta_short": 10954
    },
    "position_as_of": "2026-11-17",
    "published_date": "2026-11-20"
  },
  {
    "symbol": "Canadian Dollar (CAD)",
    "cftc_code": "090741",
    "open_interest": 358186,
    "asset_manager": {
      "long": 121071,
      "short": 115706,
      "delta_long": 1570,
      "delta_short": 10685
    },
    "leveraged_funds": {
      "long": 33563,
      "short": 105681,
      "delta_long": 2074,
      "delta_short": 5987
    },
    "position_as_of": "2026-11-17",
    "published_date": "2026-11-20"
  }
]
```

**Controllo:** questo dataset CFTC è pubblico e separato dalle 3.924 osservazioni Myfxbook e 3.791 Capital DEMO. Non sommare futures/posizioni/observation come se fossero la stessa unità. Roadmap V01–V20 preservata.
