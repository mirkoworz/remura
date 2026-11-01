# REMURA v1.53 — Salute VPS / controllo gratuito (01/11/2026)

La scheda è visibile in Impostazioni su iPhone; i dati sono disponibili solo dalla VPS privata tramite Tailscale. Il nuovo endpoint GET /private-api/resources legge /proc, carico Linux e disco con librerie standard; non effettua chiamate Oracle, non contatta broker e non legge token.

RAM, carico a 1 minuto, filesystem principale, traffico dell'interfaccia predefinita dall'avvio, uptime VPS, chiamate GET del server da ultimo riavvio sono metriche **locali**. Non sono l'utilizzo di tutto l'account Oracle, non sono traffico mensile OCI, non sono richieste ai broker. Fatturazione, quote OCI e chiamate API esterne rimangono N/D o NON VERIFICATE.

Riferimenti: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm e https://docs.oracle.com/it-it/iaas/Content/Billing/Concepts/costanalysisoverview.htm. Nell'account effettivo controllare regione, tipo VM, quote, fatturazione e costi: i report possono avere ritardo. Non promettere 0 € se non verificato.

**Rilascio**: per scelta di sicurezza l'autoupdater segnala manual_required se cambia scripts/private_server.py o altri file in scripts/. Eseguire prima test, backup e procedura manuale approvata su VPS. Non disattivare il controllo e non esporre il server al pubblico. Nessuna modifica ai database o agli ordini.
