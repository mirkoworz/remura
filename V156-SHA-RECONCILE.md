# REMURA v1.56 — riallineamento prudente dell'autoupdater

**Preparato il 02/11/2026.** Non aggiorna il sistema di trading, non modifica la VPS finché non viene esplicitamente eseguito da Termius. La v1.56 è già installata, con backup SQLite verificato e test di ripristino completato. La PR #68 è integrata in `main` (commit `b4ec4cdee133d3cdf97b94abf75f5f13c5872cf1`). L'autoupdater conserva invece il precedente SHA `d8ae01e19dd87e21b48c0d08c4b0c46a66b1eee4`.

Lo script `deploy/oracle/reconcile_v156.py` verifica **prima di qualsiasi modifica**:
1. Il codice v1.56 installato nei 17 file del rilascio e altri 3 file di base, con differenza ammessa sul solo timestamp realmente stampato nel banner comune.
2. I due check CI verdi associati al main attuale. Se `main` si è mosso con codice non appartenente ai tre file del nuovo strumento di riconciliazione, si arresta. Con aggiornamenti di soli dati/documentazione senza CI sul nuovo head può fermarsi prudenzialmente.
3. Salute del servizio privato, backup SQLite coerente con hash e manifest e presenza dei file originali per rollback.
4. Autoupdater abilitato, SHA attuale atteso e assenza di un rilascio fallito registrato.

`--check` legge soltanto. `--apply` acquisisce il lock dell'autoupdater, crea un backup privato del JSON di stato e aggiorna solo `private/autoupdate-state.json`, senza azzerare i campi non pertinenti, senza riavviare e senza alterare il database. In caso di qualsiasi divergenza, restituisce `RICONCILIAZIONE=STOP`. Non si usa `--init-sha`.

## Esecuzione da Termius dopo PR #70 integrata

Scaricare solo da commit immutabile con verifica Git blob (non scaricare un branch mobile). Questo comando è **solo preflight**, e non modifica alcun file:

```bash
set -euo pipefail
COMMIT=14284b5b2895ac562720018e3a6c4746c99209bb
EXPECTED=f695df39bf5a3c731437e287676b132980c4882f
FILE="$(mktemp /tmp/remura-sha-reconcile.XXXXXX)"
trap 'rm -f "$FILE"' EXIT
curl -fsSL --max-time 40 "https://raw.githubusercontent.com/mirkoworz/remura/${COMMIT}/deploy/oracle/reconcile_v156.py" -o "$FILE"
test "$(git hash-object "$FILE")" = "$EXPECTED" || { echo "STOP: script non verificato"; exit 1; }
sudo python3 -B "$FILE" --check
```

Output atteso (solo se nessuna verifica fallisce):

```text
RICONCILIAZIONE=VERIFICATA
FILE_CONTROLLATI=20
BACKUP_E_ROLLBACK=VERIFICATI
SHA_LIVE_STATO=VECCHIO
STATO_INVARIATO=SI
```

Solo **dopo aver esaminato questo output**, si potrà eseguire separatamente `--apply` sullo stesso script fissato, con il lock esclusivo. Nessun comando di installazione della v1.56 deve essere ripetuto.

## Avvertenze

- `--check` può effettuare chiamate HTTPS a GitHub per la verifica, ma **non chiama cTrader** o servizi a pagamento.
- Questa riconciliazione serve solo a evitare un futuro aggiornamento automatico basato su un SHA obsoleto. Non rende il CVD più tempestivo e non abilita v1.57.
- La versione v1.57 resta una PR a parte, con scheduler prioritario disattivato fino al rilascio protetto e al monitoraggio dei limiti delle richieste.
- Dopo `--apply`, ripetere la diagnostica privata per confermare `SHA_INSTALLATO` e `AUTUPDATE_STATO`; la nuova versione andrà attivata separatamente.
