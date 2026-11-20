// REMURA Experience v0.9 LAB — 20/11/2026 17:07 CET
// Offline DOM stub only, not a browser test.
import {readFileSync} from "node:fs";
import {runInNewContext,Script} from "node:vm";
import assert from "node:assert/strict";
const html=readFileSync(new URL("./REMURA_Experience_v0.9_LAB.html",import.meta.url),"utf8");
const js=html.slice(html.indexOf("<script>")+8,html.lastIndexOf("</script>"));
new Script(js);
const start=js.indexOf("function forexCotFixture"),end=js.indexOf("function renderHome(role)");
assert.ok(start>=0&&end>start);
const setup=`function node(tag,text=''){return {tag,textContent:text,children:[],value:'',append(...v){this.children.push(...v)},replaceChildren(...v){this.children=v},setAttribute(){}}} const document={createElement:tag=>node(tag)};const el=(tag,v)=>node(tag,v);function selectField(panel,label,options){const n=node('select');n.options=options;n.value=options[0];panel.append(n);return n}`;
const test=`let count=0;const ok=v=>{if(!v)throw Error("check "+count);count++};const dump=n=>[n.textContent,...n.children.map(dump)].join(" ");const p=node('section');renderForexCot(p);const selector=p.children.find(x=>x.tag==='select');ok(selector.options.length===28);ok(dump(p).includes('Asset Manager: +20 pp'));selector.value='USDJPY';selector.onchange();ok(dump(p).includes('Asset Manager: +10 pp'));selector.value='EURJPY';selector.onchange();ok(dump(p).includes('Asset Manager: +30 pp'));selector.value='CADJPY';selector.onchange();ok(dump(p).includes('Asset Manager: N/D'));ok(dump(p).includes('date report non allineate'));selector.value='GBPUSD';selector.onchange();ok(dump(p).includes('Asset Manager: N/D'));ok(dump(p).includes('Myfxbook')&&dump(p).includes('Capital.com')&&dump(p).includes('condivisione reale non abilitata'));selector.value='USDCAD';selector.onchange();ok(dump(p).includes('Pubblicazione ufficiale: N/D'));const m=node('section');renderMarketCatalog(m);const ms=m.children.find(x=>x.tag==='select');ok(ms.options.length===28&&dump(m).includes('esempio sintetico disponibile'));ms.value='GBPUSD';ms.onchange();ok(dump(m).includes('COT N/D'));ok(!dump(m).includes('Long demo'));count;`;
const n=runInNewContext(setup+"\n"+js.slice(start,end)+"\n"+test,{}, {timeout:1000});
assert.equal(n,12);
console.log("REMURA_EXPERIENCE_V09_UI_STUB_PASS="+n);
