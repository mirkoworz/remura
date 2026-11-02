# REMURA v1.56 — rilascio manuale protetto (non ancora eseguito)

**Data preparazione:** 02/11/2026, Italia. **Origine validata:** commit `3e0e34169ab89ccb2d6c09d777817ae3f705352b` del ramo `feature/volume-cvd-proxy-v156`, Git blob `8997906ee3d246b5c5d3f13a700b546c112dc525` per `deploy/oracle/release_v156.py`. I due check CI GitHub sono verdi. Non usare `main` o una URL senza commit fissato per questo rilascio.

**Attualmente sulla VPS:** v1.55. Il workflow diagnostico privato ha verificato 38 prezzi recenti, RAM 28%, disco 7,9%, tick volume assente su 64/64 M15 di EURUSD e XAUUSD. Il volume mancante è atteso nella v1.55. Non è stato ancora eseguito il backup remoto né installato il codice v1.56.

## 1. Preflight dalla VPS: una sola operazione read-only

Da Termius con un account autorizzato a `sudo`, eseguire **l'intero blocco**. Scarica uno script in un file temporaneo; verifica l'hash Git del contenuto; esegue solo `--check`. Non installa/riavvia alcunché e non crea il backup.

```bash
set -euo pipefail
COMMIT=3e0e34169ab89ccb2d6c09d777817ae3f705352b
FILE="$(mktemp /tmp/remura-v156.XXXXXX)"
trap 'rm -f "$FILE"' EXIT
curl --fail --silent --show-error --location --max-time 40 "https://raw.githubusercontent.com/mirkoworz/remura/${COMMIT}/deploy/oracle/release_v156.py" --output "$FILE"
test "$(git hash-object "$FILE")" = "8997906ee3d246b5c5d3f13a700b546c112dc525" || { echo "STOP: codice diverso dal commit verificato"; exit 1; }
sudo python3 -B "$FILE" --check --commit "$COMMIT"
```

Esito atteso: `PREFLIGHT_V156=OK`, `VERSIONE_LIVE_INVARIATA=SI`, `BACKUP_SQLITE_NON_ANCORA_ESEGUITO=SI`. Qualsiasi `STOP_...` blocca il rilascio. **Non eseguire `--apply` da soli:** va programmato dopo il controllo e con possibilità di analizzare l'output.

## 2. Applicazione dopo conferma esplicita

Lo stesso script in modalità `--apply --commit <SHA>` procede soltanto se:
- È root, `remura-private.service` è attivo e sano.
- `remura-autoupdate.service` non è in esecuzione e ottiene il lock esclusivo condiviso con l'autoupdater.
- Il codice scaricato appartiene all'esatto commit GitHub fissato; ogni file dell'allowlist viene verificato contro il suo **Git blob SHA**.
- La VPS ha ancora banner v1.55, file regolari senza symlink, database SQLite sano con tabelle necessarie e sufficiente spazio per due snapshot.
- Il database è copiato con SQLite Online Backup (WAL-aware), la copia ha superato `integrity_check`, ed è stata **ripristinata in un DB temporaneo** e verificata.
- Una copia persistente dei file originali viene salvata sotto `private/predeploy-backups/rollback-v156-...`, con manifest degli hash.

Solo dopo: arresta una volta `remura-private.service`, sostituisce **17 file di codice e interfaccia** in modo atomico, riavvia e verifica salute API locale. In caso di errore tenta immediatamente di ripristinare i file precedenti e il servizio. Non migra schema SQLite, non pubblica segreti e non invia ordini.

La data/ora italiana effettiva viene scritta nel banner condiviso `nav.js` al momento del rilascio. **La sola modifica al repository non aggiorna la versione installata**.

## 3. Dopo il rilascio

1. Ripetere il workflow privato diagnostico: 38 mercati, COT, Squalincome, RAM, disco e, soprattutto, `TICK_VOLUME_EURUSD` / `TICK_VOLUME_XAUUSD`.
2. Attendere almeno una acquisizione M15 per osservare volumi realmente presenti; se restano ASSENTE verificare disponibilità del campo presso broker/SDK, senza inventare valori.
3. Verificare che il CVD non si attivi quando i dati sono incompleti o stantii. Il preflight ha osservato EURUSD con apertura dell'ultima M15 di 124 minuti prima: la frequenza della rotazione 38 mercati può impedire segnali intraday validi. Lavorare sulla freschezza solo dopo misure API/CPU.
4. Controllare eventuale stato `manual_required` dell'autoupdater: **non** eseguire `--init-sha` arbitrariamente. Pianificare il merge e l'allineamento SHA dopo validazione reale del rilascio.
5. Verificare quote e addebiti Oracle nel pannello OCI, indipendentemente da RAM e disco.

## Limiti di sicurezza e costi

- La modalità `--check` consulta GitHub dal server e legge SQLite in sola lettura, senza cambiare codice. Potrà fallire se rete/servizio locale/permessi non soddisfano i prerequisiti.
- `--apply` **riavvia un servizio**: è prevista una breve interruzione della raccolta, non promettere disponibilità zero-downtime.
- Lo script conserva il rollback dei **file** e il backup del **database** in directory private differenti. Se l'host perde alimentazione durante una scrittura, potrebbe servire ripristino manuale usando il manifest; non si promette rollback automatico infallibile.
- Nessuna chiamata aggiuntiva a cTrader per i volumi delle trendbar M15; l'onere iniziale è locale (file, SQLite, grafico).
- RAM 28% e disco 7,9% sono buoni segnali di capienza attuale ma non certificano la permanenza nello scaglione Always Free né il costo di rete.
- CVD è un **proxy di tick volume**, non il delta degli ordini eseguiti sul future e non prova attività istituzionale.
