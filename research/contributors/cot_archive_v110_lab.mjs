// Public CFTC snapshot markup carried forward from the two v1.08 dashboards.
// Source: staging_readonly_bundle_v108_lab.mjs at d34a3a71fc1e32c7244b7f7a5a65f80528abdf21.
export const COT_ARCHIVE_V110 = `
<section class="panel" id="cot"><div class="eyebrow">Shark Cockpit</div><h2>Shark Cockpit · COT</h2><p class="tag">ARCHIVIO AUTENTICO · SOLO DESCRITTIVO</p><p>Report CFTC 17/11/2026 e 10/11/2026. Acquisiti il 24/11/2026 alle 10:05 CET. Snapshot B V22.3; commit 3ddf1f93. Non rappresentano ordini live, segnali di trading o un vantaggio statistico dimostrato. Parità privata, primo avvistamento storico e indice COT 52 settimane non verificati.</p><div class="metrics"><div class="metric"><small>Fattori valutari</small><strong>7</strong></div><div class="metric"><small>Cross sintetici</small><strong>28</strong></div><div class="metric"><small>Futures</small><strong>7</strong></div></div><p class="hint">Apri le sezioni per leggere i valori. Le tabelle scorrono orizzontalmente su iPhone.</p>
</section>
<details class="panel market-group" id="valute">
<summary>7 fattori valutari<span class="chevron" aria-hidden="true"></span></summary><div class="scroll" tabindex="0">
<table>
<thead>
<tr><th scope="col">Valuta</th><th scope="col">AM net % OI</th><th scope="col">LF net % OI</th><th scope="col">Δ AM pp</th><th scope="col">Δ LF pp</th></tr>
</thead>
<tbody>
<tr><th scope="row">AUD</th><td data-exact="-48.820271400364966">-48.82</td><td data-exact="10.147456055744215">10.15</td><td data-exact="-4.267914793334967">-4.27</td><td data-exact="-4.254613892875488">-4.25</td></tr>
<tr><th scope="row">NZD</th><td data-exact="-34.65136457429511">-34.65</td><td data-exact="-17.2039169078885">-17.20</td><td data-exact="-3.552111962982707">-3.55</td><td data-exact="1.618756408970949">1.62</td></tr>
<tr><th scope="row">GBP</th><td data-exact="-44.803189735287944">-44.80</td><td data-exact="12.329817258318023">12.33</td><td data-exact="3.3891429719149784">3.39</td><td data-exact="-3.3590702155868932">-3.36</td></tr>
<tr><th scope="row">CAD</th><td data-exact="1.4978251522951762">1.50</td><td data-exact="-20.134231935363193">-20.13</td><td data-exact="-2.7277283572779787">-2.73</td><td data-exact="-0.23064926129986318">-0.23</td></tr>
<tr><th scope="row">EUR</th><td data-exact="17.00098841613243">17.00</td><td data-exact="-8.843437655883385">-8.84</td><td data-exact="-2.3597266843993303">-2.36</td><td data-exact="-0.4573863282323245">-0.46</td></tr>
<tr><th scope="row">CHF</th><td data-exact="-8.863222846293805">-8.86</td><td data-exact="-15.634047939245313">-15.63</td><td data-exact="1.5571034763256382">1.56</td><td data-exact="-2.918227147651839">-2.92</td></tr>
<tr><th scope="row">JPY</th><td data-exact="21.69299699508916">21.69</td><td data-exact="-6.094358811459136">-6.09</td><td data-exact="-1.539147010053881">-1.54</td><td data-exact="-1.7600611579715117">-1.76</td></tr>
</tbody>
</table></div>
</details>
<details class="panel market-group" id="forex">
<summary>28 cross sintetici — non spot diretto<span class="chevron" aria-hidden="true"></span></summary><div class="scroll" tabindex="0">
<table>
<thead>
<tr><th scope="col">Cross</th><th scope="col">Δ AM pp</th><th scope="col">Δ LF pp</th></tr>
</thead>
<tbody>
<tr><th scope="row">EURUSD</th><td data-exact="-2.3597266843993303">-2.36</td><td data-exact="-0.4573863282323245">-0.46</td></tr>
<tr><th scope="row">GBPUSD</th><td data-exact="3.3891429719149784">3.39</td><td data-exact="-3.3590702155868932">-3.36</td></tr>
<tr><th scope="row">AUDUSD</th><td data-exact="-4.267914793334967">-4.27</td><td data-exact="-4.254613892875488">-4.25</td></tr>
<tr><th scope="row">NZDUSD</th><td data-exact="-3.552111962982707">-3.55</td><td data-exact="1.618756408970949">1.62</td></tr>
<tr><th scope="row">USDJPY</th><td data-exact="1.539147010053881">1.54</td><td data-exact="1.7600611579715117">1.76</td></tr>
<tr><th scope="row">USDCAD</th><td data-exact="2.7277283572779787">2.73</td><td data-exact="0.23064926129986318">0.23</td></tr>
<tr><th scope="row">USDCHF</th><td data-exact="-1.5571034763256382">-1.56</td><td data-exact="2.918227147651839">2.92</td></tr>
<tr><th scope="row">EURGBP</th><td data-exact="-5.748869656314309">-5.75</td><td data-exact="2.9016838873545687">2.90</td></tr>
<tr><th scope="row">EURJPY</th><td data-exact="-0.8205796743454492">-0.82</td><td data-exact="1.3026748297391872">1.30</td></tr>
<tr><th scope="row">EURCHF</th><td data-exact="-3.9168301607249685">-3.92</td><td data-exact="2.4608408194195146">2.46</td></tr>
<tr><th scope="row">EURCAD</th><td data-exact="0.3680016728786484">0.37</td><td data-exact="-0.22673706693246132">-0.23</td></tr>
<tr><th scope="row">EURAUD</th><td data-exact="1.9081881089356365">1.91</td><td data-exact="3.7972275646431637">3.80</td></tr>
<tr><th scope="row">EURNZD</th><td data-exact="1.1923852785833766">1.19</td><td data-exact="-2.0761427372032735">-2.08</td></tr>
<tr><th scope="row">GBPJPY</th><td data-exact="4.9282899819688595">4.93</td><td data-exact="-1.5990090576153815">-1.60</td></tr>
<tr><th scope="row">GBPCHF</th><td data-exact="1.8320394955893402">1.83</td><td data-exact="-0.4408430679350541">-0.44</td></tr>
<tr><th scope="row">GBPCAD</th><td data-exact="6.116871329192957">6.12</td><td data-exact="-3.12842095428703">-3.13</td></tr>
<tr><th scope="row">GBPAUD</th><td data-exact="7.657057765249945">7.66</td><td data-exact="0.895543677288595">0.90</td></tr>
<tr><th scope="row">GBPNZD</th><td data-exact="6.941254934897685">6.94</td><td data-exact="-4.977826624557842">-4.98</td></tr>
<tr><th scope="row">AUDJPY</th><td data-exact="-2.7287677832810857">-2.73</td><td data-exact="-2.4945527349039764">-2.49</td></tr>
<tr><th scope="row">AUDCAD</th><td data-exact="-1.5401864360569881">-1.54</td><td data-exact="-4.023964631575625">-4.02</td></tr>
<tr><th scope="row">AUDCHF</th><td data-exact="-5.825018269660605">-5.83</td><td data-exact="-1.336386745223649">-1.34</td></tr>
<tr><th scope="row">AUDNZD</th><td data-exact="-0.7158028303522599">-0.72</td><td data-exact="-5.873370301846437">-5.87</td></tr>
<tr><th scope="row">NZDJPY</th><td data-exact="-2.012964952928826">-2.01</td><td data-exact="3.3788175669424607">3.38</td></tr>
<tr><th scope="row">NZDCAD</th><td data-exact="-0.8243836057047282">-0.82</td><td data-exact="1.8494056702708122">1.85</td></tr>
<tr><th scope="row">NZDCHF</th><td data-exact="-5.109215439308345">-5.11</td><td data-exact="4.536983556622788">4.54</td></tr>
<tr><th scope="row">CADJPY</th><td data-exact="-1.1885813472240976">-1.19</td><td data-exact="1.5294118966716486">1.53</td></tr>
<tr><th scope="row">CADCHF</th><td data-exact="-4.284831833603617">-4.28</td><td data-exact="2.687577886351976">2.69</td></tr>
<tr><th scope="row">CHFJPY</th><td data-exact="3.0962504863795193">3.10</td><td data-exact="-1.1581659896803274">-1.16</td></tr>
</tbody>
</table></div>
</details>
<details class="panel market-group" id="futures-finanziari">
<summary>Futures finanziari<span class="chevron" aria-hidden="true"></span></summary><div class="scroll" tabindex="0">
<table>
<thead>
<tr><th scope="col">Riferimento</th><th scope="col">Asset Manager/Institutional net % OI</th><th scope="col">Leveraged Funds net % OI</th><th scope="col">Δ A pp</th><th scope="col">Δ B pp</th></tr>
</thead>
<tbody>
<tr><th scope="row">US30</th><td data-exact="-9.238772159029619">-9.24</td><td data-exact="4.133955004734451">4.13</td><td data-exact="-11.740335636202852">-11.74</td><td data-exact="2.5524377102715663">2.55</td></tr>
<tr><th scope="row">NAS100</th><td data-exact="27.96679070112643">27.97</td><td data-exact="-3.686623507622553">-3.69</td><td data-exact="2.756983173339705">2.76</td><td data-exact="-8.524232654295592">-8.52</td></tr>
<tr><th scope="row">US500</th><td data-exact="42.68321063178185">42.68</td><td data-exact="-11.205660771460373">-11.21</td><td data-exact="-2.6226271914285917">-2.62</td><td data-exact="3.8145083628007868">3.81</td></tr>
<tr><th scope="row">DXY</th><td data-exact="33.75705961452263">33.76</td><td data-exact="-2.2429403854773646">-2.24</td><td data-exact="1.789719023542851">1.79</td><td data-exact="-7.783375844264301">-7.78</td></tr>
</tbody>
</table></div>
</details>
<details class="panel market-group" id="futures-fisici">
<summary>Futures fisici<span class="chevron" aria-hidden="true"></span></summary><div class="scroll" tabindex="0">
<table>
<thead>
<tr><th scope="col">Riferimento</th><th scope="col">Managed Money net % OI</th><th scope="col">Producer/Merchant net % OI</th><th scope="col">Δ A pp</th><th scope="col">Δ B pp</th></tr>
</thead>
<tbody>
<tr><th scope="row">XAUUSD</th><td data-exact="25.24115203734853">25.24</td><td data-exact="-1.1257031046945571">-1.13</td><td data-exact="-2.516214075444104">-2.52</td><td data-exact="1.5627890813577006">1.56</td></tr>
<tr><th scope="row">XAGUSD</th><td data-exact="1.0411159461547848">1.04</td><td data-exact="-10.47378909268372">-10.47</td><td data-exact="-2.0846406339302983">-2.08</td><td data-exact="-0.045089199901926946">-0.05</td></tr>
<tr><th scope="row">USOIL</th><td data-exact="0.8457638803094895">0.85</td><td data-exact="20.602699021119495">20.60</td><td data-exact="-0.49527195174655503">-0.50</td><td data-exact="1.3801076208755276">1.38</td></tr>
</tbody>
</table></div>
</details>
<section class="panel" id="moduli"><h2>Altri moduli</h2><p>Myfxbook privato, CVD, Ampere e Squalincome: non collegati a questo portale. Nessun dato simulato.</p><p>AM = Asset Manager/Institutional; LF = Leveraged Funds; OI = open interest; pp = punti percentuali.</p>
</section>
`;
