# REMURA Level Confluence — protocollo E-R1, v0.12 LAB
14/11/2026 23:48 CET — DRAFT / SYNTHETIC ONLY / NO-GO REAL DATA

## Scopo
Misurare se livelli manuali e confluenze aggiungono informazione rispetto ai livelli automatici, senza trattare una vicinanza di prezzi come segnale o prova istituzionale. Nessuna modifica ai protocolli B/D.

## Prima di qualsiasi raccolta reale
- Congelare in manifest immutabile, prima degli esiti: versione motore, identificativi livelli, feed esatto, tipo prodotto/contratto, metodo/periodo/anchor, timestamp disponibilità/approvazione, cutoff UTC, fonte prezzo e licenza, regime di sessione, tick e tolleranza verificati, dedup, criteri esclusione, calendario, dimensionamento campione e piano analitico. Nessuna data di avvio o soglia di successo reale è approvata ora.
- Coorti candidate: automatici con manuale vicino, automatici con manuali confrontabili ma distanti, automatici senza manuale confrontabile (assenza dati distinta), manuali isolati. Non contare più coppie vicine allo stesso automatico come osservazioni indipendenti; unità livello/cutoff deduplicata, dipendenza per mercato/sessione/fonte e collaboratore.
- Congelare coorte al cutoff, non sostituire perdenti, no ottimizzazione su holdout, no ranking collaboratori con piccoli campioni. Conservare anche mancati contatti, revoche successive e N/D per audit; separare andamento dopo cutoff e stato conoscibile al cutoff. Nessun peso nuovo SQUALINCOME prima di validazione prospettica separata.

## Meccanica sintetica deterministica v1
- M5 allineate UTC; cutoff coincide con chiusura nota. Fixture richiede previous close disponibile esattamente al cutoff; in reale definire cutoff+maturazione/feed lag senza retrodatare nulla. Input manuale/automatico e regole devono già essere congelati e confrontabili.
- 24 barre consecutive interamente chiuse, 12 di ricerca primo contatto, successive 12 dopo la barra di contatto. Attendere maturazione di tutte 24 barre e disponibilità; anche NO_TOUCH solo su finestra completa. Non colmare buchi, non usare calendario come prova di dati. Su mercato chiuso N/D.
- Contatto: range OHLC include livello (proxy, non prova tick effettivamente eseguito). Gap open oltre livello prima del contatto: N/D. Prezzo già sul livello al cutoff: N/D. Lato iniziale dalla close al cutoff. Attraversamento: almeno una close dal lato opposto nel contatto o nelle successive 12 barre; nessun ordine intrabar inferito.
- Escursioni: massima distanza dal livello verso lato di provenienza e verso lato opposto nelle 12 barre DOPO quella di contatto; gli estremi della barra di contatto esclusi per ambiguità. Sono distanze descrittive, non MFE/MAE di un trade. Non implicano prezzo di entrata o esecuzione.
- Output TOUCHED/NO_TOUCH/N_D + ragione; nessun risultato binario successo, nessun rendimento, nessun ordine. Invalidità schema/cronologia/OHLC rifiutata. Comparabilità del feed e provenance non sono certificate dall'evaluatore: manifest e adapter verificato ancora mancanti.
- Futura analisi: frequenza contatti su finestre valide (N/D separati), distribuzione escursioni e attraversamenti condizionati al contatto, intervalli di incertezza e controllo dipendenze. Confronti a coorti equivalenti per mercato/sessione e volatilità; nessuna affermazione causale da confronto osservazionale. Disegno, campione, soglie, endpoint primario e valutazione holdout da congelare prima della raccolta.

## Stato
Solo funzione pura e fixture. Nessuna ammissione scientifica o reale; nessun provider, rete, scheduler o incremento costo cloud. Non leggere prezzi reali o integrare SQUALINCOME prima dell'autorizzazione e delle verifiche.
