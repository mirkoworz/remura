# Capital.com privato nelle schede REMURA — importazione dall'iPhone

Soluzione **temporanea, senza nuove chiamate API** per vedere EUR/USD e gli altri
mercati già raccolti nel repository privato.

## Come vedere EUR/USD

1. Sul tuo iPhone, accedi a GitHub e apri
   https://github.com/mirkoworz/remura-collector/blob/main/private/capital/latest.json
2. Dal menu del file usa **Download raw file** o salva il JSON nell'app File.
3. Apri https://mirkoworz.github.io/remura/asset.html?symbol=EURUSD
4. Nella scheda Capital.com premi **Carica latest.json** e scegli il file.
5. Vedrai le percentuali della rilevazione realmente salvata. Al momento
   del test del 19 ottobre 2026 ore 09:25 italiane: 64,09% long,
   35,91% short. NON sono valori in tempo reale.
6. Tutte le altre coppie già contenute nel file saranno disponibili
   anche sulle rispettive schede nello stesso browser.

## Bande storiche

Se vuoi, scarica anche
https://github.com/mirkoworz/remura-collector/blob/main/private/capital/history/EURUSD.json
e usa **Carica storico EURUSD (facoltativo)**.
Almeno due osservazioni nello stesso periodo sono necessarie per
disegnare una banda. Le rilevazioni mancanti non vengono inventate.

## Privacy e costi

- La pagina GitHub Pages è pubblica e non può interrogare direttamente
  il repository privato senza autenticazione.
- Il browser legge solo il file selezionato dall'utente; non inoltra il
  suo contenuto ad alcun server.
- Nel browser rimangono SOLO percentuali long/short e timestamp validi.
  Tutte le altre proprietà JSON vengono eliminate prima del salvataggio.
- La copia numerica è salvata nel browser locale, non in GitHub pubblico.
  Il pulsante **Cancella dati importati** la elimina dal browser.
- Se cancelli i dati del sito, cambi browser o dispositivo, devi
  importare nuovamente l'ultimo file.
- Per aggiornare le percentuali devi scaricare e importare una nuova copia.
- Nessuna nuova chiamata Capital.com, MetaApi, Guardiano o Cloudflare.
- Non introdurre token GitHub nel browser pubblico né pubblicare
  snapshot o password in un repository pubblico.

In seguito progetteremo un ponte privato o cifrato per l'aggiornamento
automatico, dopo aver completato la discovery di tutti i mercati,
mantenendo il limite rigido delle chiamate.
