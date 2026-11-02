# REMURA — Release v1.58, piano di deploy protetto

**02/11/2026.** Questa è una release **candidata su PR #74**. In produzione resta installata v1.57 e riconciliata al commit d445b17be20028fdb42ab303fa99718c1c33cd80. Nessuna operazione automatica sulla VPS.

## Controlli di installazione
- `deploy/oracle/release_v158.py --check --commit <SHA_MAIN_COMPLETO>`: verifica server attivo, main immutabile, confronto limitato ai file approvati, CI push Insights/Price Engine verdi, stato autoupdater ancora associato a v1.57, lock autoupdater inattivo, corrispondenza esatta di 13 file live v1.57 (timestamp installazione nav escluso), flag post-ingest OFF, integrità SQLite e spazio.
- `--apply` soltanto in un passaggio Termius separato dopo `--check`: lock esclusivo, backup SQLite coerente, restore-test isolato, directory rollback persistente, 13 file installati atomici e health dopo restart. Timbratura release italiana effettiva, non ora preparazione GitHub.
- `--rollback-dir` solo per il bundle v1.58 appena generato e con verifica dei digest del codice corrente; se dopo la riconciliazione SHA, effettuare anche controllo e ripristino dello stato autoupdater separato.
- L'installer non modifica `remura.env`, DB produzione, credenziali, Myfxbook, COT, stato autoupdater. Non introduce nuove API cTrader. La scansione post-ingest rimane disattivata finché non abilitiamo esplicitamente il flag in fase separata.
- Dopo rilascio: script di riconciliazione SHA v1.58 separato, backup stato, CI main verdi, diagnostica GitHub privata e misure reali di latenza tra ingest e osservazione, duplicati, freschezza H1, RAM, disco e quote.
- Sorgente CVD proxy resta CLV × tick volume e PR #71 è ancora offline; niente notifiche o trading automatico in questo rilascio.

**Budget:** risorse VPS note ma costi Oracle, billing Firestore e quota API ancora N/D; non dichiarare gratuito in modo certo.
