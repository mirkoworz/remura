# REMURA — checkpoint del 22 novembre 2026, filoni A–F, LAB v0.4
**Ora italiana:** Europe/Rome. **Produzione protetta; NO deploy, merge, Secret, utenti nuovi o spese.**
Documento cumulativo: checkpoint v0.3 precedente su
`research/cot-wal-reopen-v03-lab-20261122/research/REMURA-ROADMAP-CHECKPOINT-20261122-V03.md`.

## Novità di questa prosecuzione, senza ripetere controlli storici

| Filone | HEAD LAB verificato dopo documentazione | Nuova evidenza |
| --- | --- | --- |
| A — COT | `research/cot-integrity-global-v04-lab-20261122` / `59a3b7a0dc72e62d92ad4f08100dc97ce4736f54` | 12/12 PASS in [CI 45002593074](https://github.com/mirkoworz/remura/actions/runs/45002593074), integrità globale eventi/versioni/head su SQLite TEMPORANEO, no Oracle |
| D — Retail / Myfxbook | `research/retail-git-commit-witness-boundary-v03-20261122` / `6cbdedd4ba5abc52d4ced294331b7d642fbe7ce3` | 12/12 PASS in [CI 45002589685](https://github.com/mirkoworz/remura/actions/runs/45002589685), 4 **commit REALI Git** verificati byte-per-byte contro lo storico EURUSD |
| B — TradingView | `research/tv-prospective-admission-gate-v0187-20261122` / `af3448b114cc0a181d8b8a3d03686a37d293220d` | precedente 20/20 CI 44999527898, solo classificazione sintetica dei requisiti M5, V2 immutato |
| C — Contributors | `research/contributors-access-free-hardcap-v092-20261121` / `6f5ed30f9c7de3f9ee83a64a3851ab6c3707c5ce` | piano pilot 1–2 amici già preparato. Quota Access/D1/Workers vera e prova fisica Safari iPhone non effettuate: NO-GO |
| E — Codex Mac | Experience v0.30, Private Capture v0.15, Oracle security v1.65 in custodia | nessuna sovrapposizione né modifica ai servizi o file Mac |
| F — Free governance | Nessuna chiamata Cloudflare; due CI LAB su GitHub Actions standard | margine gratuito corrente di Cloudflare e GitHub Actions **UNKNOWN**, non zero e non garantito |

## Scoperta determinante sull'attestazione temporale Retail
Per i quattro commit Myfxbook del 20–22 novembre (SHA e blob esatti nel
documento `research/retail/MYFXBOOK-GIT-PROVENANCE-V03-CHECKPOINT-20261122.md`)
il timestamp *committer* riportato dall'oggetto Git coincide con l'ora
`t` dello snapshot. **Ma quel campo è creato dal sistema che scrive il
commit, non è un certificato del server GitHub di prima ricezione.**
Il codice `scripts/update_myfxbook.py` imposta `stamp` con l'orologio
UTC locale **dopo** il fetch, e il workflow `.github/workflows/myfxbook.yml`
fa commit/push senza introdurre un witness temporale indipendente.
I file e gli hash provano l'identità dei contenuti nei commit, non
l'effettiva disponibilità all'ora indicata. Mai promuovere questi metadati
in `EXTERNALLY_TIME_ATTESTED`.

## COT v0.4 — nuovo controllo complementare
Il replay `as_of` v0.2 e WAL reopen v0.3 coprivano versioni puntuali e
rollback. Il nuovo audit globale trova `current_head` assenti o obsoleti,
incongruenze nei contenuti e nelle transazioni conservate e manomissioni dei
trigger di protezione. Dataset vuoto = UNKNOWN; report o hash incoerenti =
QUARANTINE. Test su SQLite sintetico non attestano integrità Oracle.
Servono futura integrazione additiva e autorizzazione Mac, con backup e
clock/provenienza credibili, prima di ogni cutover.

## Confini TradingView, 23 novembre, e ricerca dell'edge
- Protocollo prospettico V2 congelato: Development fino a
  **2026-11-23T00:00:00Z**; holdout 1
  **[2026-11-23T00:00:00Z, 2026-11-30T00:00:00Z)**;
  holdout 2 **[2026-11-30T00:00:00Z, 2026-12-07T00:00:00Z)**.
  Inizio holdout 1 alle 01:00 Europe/Rome del 23 novembre.
- Nessun risultato CVD/price-only a 60 minuti autentico, copertura M5,
  first-seen indipendente, raccolta o alpha dimostrato.
  Una data passata o futura non cambia il NO-GO.
- Myfxbook = RETAIL; CFTC = posizionamento futures per categorie;
  cTrader tick-volume non è aggressor volume. Spot/futures mapping UNKNOWN
  senza prova. Nessun consiglio di investimento o segnale.
- Non ripetere suite COT v0.1/v0.2/v0.3, retail storico 34 file / 3.984
  osservazioni, TV v0.8.186, Contributors fino a nuove modifiche o un
  rischio documentato e concreto. I **24 test di questa prosecuzione sono nuovi**.

## Next precise gates
1. Costruire un witness temporale prospettico esterno per gli snapshot futuri,
   separando record UTC locale, timestamp Git commit e ricevuta indipendente,
   senza usare Secret o avviare servizi senza consenso.
2. Solo quando esistono veri artifact TV, applicare per decisione il
   classificatore V2, con coverage, missingness, timestamp e prove indipendenti
   e nessun tuning del fold in corso.
3. Coordinare integrazione COT su Mac, **senza toccare Oracle** finché non c'è
   autorizzazione separata e backup/integrità verificati nella specifica fase.
4. Contributors: quote Cloudflare Access/Workers/D1 reali con consenso,
   staging privato, login/logout/revoca e isolamento su iPhone fisico
   prima del pilot amici.
5. Costi: nessuna richiesta Cloudflare nel nuovo lavoro; margini di servizio
   UNKNOWN. Non aggiungere monitoraggi ridondanti ad Ampere Radar.
6. Se si modificano vere pagine REMURA, mostrare versione aggiornata e data/ora
   Europe/Rome in alto a ciascuna pagina. Solo LAB/docs sono stati toccati.

**Risultato: 24 nuovi casi GREEN, produzione invariata, vera inferenza di
vantaggio istituzionale ancora NON DIMOSTRATA.**
