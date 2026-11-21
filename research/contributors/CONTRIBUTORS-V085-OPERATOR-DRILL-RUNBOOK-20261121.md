# REMURA Contributors v0.85 LAB — Piano di prova manuale e rollback

**Versione 0.85 LAB · 21 novembre 2026 · Europe/Rome**

Scopo: avere un elenco verificabile e ripetibile per un **futuro** collaudo Cloudflare privato, senza effettuare alcuna operazione reale e senza dedurre autorizzazioni dalla checklist.

## Prima di qualunque staging
1. Confermare account e Free plan dalla console privata, senza riportare in repository pubblico nomi, email, account ID, token o screenshot identificativi.
2. Misurare **nello stesso giorno UTC** consumo righe D1 read/write da fonte realmente verificata; se GraphQL vuoto, non provare zero. Verificare richieste Workers e D1 storage separatamente.
3. Confermare posti Access **effettivamente disponibili**, policy allowlist a negazione predefinita, JWT `ctx.access` e ruolo D1 verificato server-side; dichiarare espressamente i responsabili della revoca.
4. Pianificare DB fixture separato e reversibile, schemi verificati, backup e raccolta evidenze reali **solo dopo specifica autorizzazione**.
5. Preparare login/logout/revoca su Safari fisico, senza creare utenti reali fino al consenso e senza pubblicare identità.
6. Preservare l'integrità del router Worker v0.78 e quattro pagine private, che mostrano già versione e data/ora; non fare merge né deploy.
7. Mantenere separate le code `original-level` e `amendment`, l'OWNER audit append-only e gli stati RESERVED senza invio/ripristino automatico.

## Rollback progettato, NON automatizzato
- Arrestare l'ingresso privato (se attivo in futuro), bloccare la policy Access, revocare sessioni; verificare con una nuova sessione il deny.
- Sospendere eventuali scritture della fixture e preservare audit e RESERVED prima di ogni riconciliazione manuale.
- Ritirare le route private solo secondo piano autorizzato; verificare che l'accesso sia negato e che nessun `retry` o rilascio RESERVED sia partito.
- OWNER firma/attesta manualmente la conclusione della riconciliazione, senza modifica delle evidenze storiche.

**Tutti i passaggi reali sono esplicitamente fuori ambito della v0.85**. Il modulo `staging_drill_v085_lab.py` controlla soltanto l'ordine documentale e produce sempre `NO_GO`. Un test Green non equivale a collaudo sul provider e il rollback reale richiede autorizzazione specifica.

Roadmap: collaudo Access Free seats e D1 giornaliero in lettura con consenso specifico; successivo pilot 1–2 amici, scrittura solo dei livelli propri, revisione OWNER, Telegram solo dopo approvazione. TV holdout 23/11–06/12 UTC, Shark Science, Experience splash, Oracle collector protetto, radar Ampere, backup, Squalincome preservati.
