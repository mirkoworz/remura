# REMURA — COT Index, Gap Index e Shark Radar (19 ottobre 2026)

## Fonti
Le 35 schede `asset.html` interrogano la **CFTC**: Traders in Financial Futures Futures Only per Forex e indici, Disaggregated Futures Only per metalli. Richiedono fino a circa cinque anni (261 report settimanali allineati), senza provider a pagamento. Non esiste ancora un archivio COT centralizzato persistente: il browser deve riuscire a ricevere le API CFTC.

## Indicatori
- Net% = 100 × (Long - Short)/Open Interest.
- COT Index = 100 × (Net% attuale - minimo)/ (massimo - minimo), finestra 26, 52, 156 o 260 report.
- Gap = Net% categoria A meno Net% categoria B, in punti percentuali **con segno**.
- Gap Index = stesso indice 0–100 calcolato sul gap con segno, **non sulla distanza assoluta**.
- Su tutte le 35 schede il pannello si trova dopo il COT riepilogativo e **prima** di Myfxbook e Capital.com, che restano consecutivi.

Lo scanner già presente in `mercati.html` ha il filtro **Estremi COT 52s** che mostra valori COT o Gap Index <=10 o >=90 sui report recenti. Le altre modalità non cambiano. Se la CFTC non fornisce abbastanza report, se il range è costante o se la serie è datata, si usano N/D e le avvertenze esistenti; non si creano valori fittizi.

I cross Forex sono **differenziali sintetici tra due futures** (USD = 0 matematico), non posizioni istituzionali spot. Asset Manager, Leveraged Funds e Managed Money sono categorie CFTC con funzioni diverse; Producer/Merchant spesso sono hedger. Un estremo non prova inversione del prezzo, non è percentuale di long, non è probabilità o segnale di trading. Per test robusti occorrono prezzi OHLC storici e date di pubblicazione dei report, evitando il lookahead bias.

## Collaudi
`node --test tests/cot-indices.test.js tests/cot-scanner.test.js tests/insights.test.js tests/retail-chart.test.js`.
PWA e server privato includono il nuovo `cot-indices-core.js`; nessuna credenziale nelle pagine.
