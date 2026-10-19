/* Regression: real Myfxbook observations form filled bands even with multi-hour gaps. */
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),vm=require("node:vm");
const fixture=JSON.parse(fs.readFileSync("tests/fixtures/myfxbook-eurusd-gaps.json","utf8"));
const source=fs.readFileSync("retail.js","utf8");

function element(id=""){
 const listeners={};
 return {id,style:{},dataset:{},clientWidth:320,children:[],innerHTML:"",textContent:"",listeners,
  append(...items){this.children.push(...items)},
  replaceChildren(...items){this.children=items;this.innerHTML=""},
  setAttribute(){},
  addEventListener(name,handler){listeners[name]=handler},
  querySelectorAll(){return []},
  querySelector(){return {addEventListener(){},getBoundingClientRect(){return {width:320}}}},
  getBoundingClientRect(){return {width:320,left:0}}
 };
}
async function render(){
 const nodes=new Map();
 const get=id=>{if(!nodes.has(id))nodes.set(id,element(id));return nodes.get(id)};
 const modes=["lots","positions"].map(mode=>Object.assign(element(),{dataset:{mode}}));
 const windows=["6h","1d","7d","30d","all"].map(window=>Object.assign(element(),{dataset:{window}}));
 get("r-modes").querySelectorAll=()=>modes;
 get("r-windows").querySelectorAll=()=>windows;
 const latest={status:"ok",updatedAt:fixture.records.at(-1).t,symbols:{EURUSD:fixture.records.at(-1)}};
 const fetch=async url=>{
  if(url.startsWith("./private-api/"))return {ok:false};
  if(url.includes("latest.json"))return {ok:true,json:async()=>latest};
  if(url.includes("history/EURUSD.json"))return {ok:true,json:async()=>fixture};
  return {ok:false};
 };
 // Anchor this regression on the latest persisted observation: the fixture is
 // updated by an independent real collector; its length changes over time.
 const clock=Date.parse(fixture.records.at(-1).t)+30*60000;
 class Clock extends Date{static now(){return clock}}
 const document={getElementById:get,createElement:()=>element(),createTextNode:text=>({textContent:text})};
 const window={addEventListener(){},dispatchEvent(){}};
 vm.runInNewContext(source,{document,window,location:{search:"?symbol=EURUSD"},
  URLSearchParams,CustomEvent:class{},Date:Clock,fetch});
 await new Promise(resolve=>setImmediate(resolve));
 return {get,modes,windows};
}
test("real samples across gaps produce two colored continuous areas with dashed missing periods",async()=>{
 const {get}=await render();
 const svg=get("r-chart").innerHTML;
 assert.match(svg,/class="rt-area-green"/);
 assert.match(svg,/class="rt-area-red"/);
 const countGaps=fixture.records.slice(1).filter((row,i)=>
  Date.parse(row.t)-Date.parse(fixture.records[i].t)>75*60000).length;
 assert.equal((svg.match(/class="rt-long-line rt-gap"/g)||[]).length,countGaps);
 assert.equal((svg.match(/class="rt-short-line rt-gap"/g)||[]).length,countGaps);
 assert.equal((svg.match(/class="rt-sample"/g)||[]).length,fixture.records.length*2);
 assert.match(get("r-count").textContent,new RegExp(fixture.records.length+" rilevazioni"));
 assert.match(get("r-change").textContent,new RegExp(countGaps+" intervalli >75 min"));
 assert.match(svg,/viewBox="0 0 310 288"/);
});
test("changing to positions and six hours redraws genuine values, not synthetic points",async()=>{
 const {get,modes,windows}=await render();
 const original=get("r-chart").innerHTML;
 modes[1].listeners.click();
 assert.notEqual(get("r-chart").innerHTML,original);
 assert.match(get("r-change").textContent,/posizioni/);
 windows[0].listeners.click();
 const clock=Date.parse(fixture.records.at(-1).t)+30*60000;
 const subset=fixture.records.filter(row=>Date.parse(row.t)>=clock-6*3600000);
 assert.match(get("r-count").textContent,new RegExp(subset.length+" rilevazioni"));
 const svg=get("r-chart").innerHTML;
 if(subset.length>=2){
  assert.equal((svg.match(/class="rt-sample"/g)||[]).length,subset.length*2);
  const n= subset.slice(1).filter((p,i)=>Date.parse(p.t)-Date.parse(subset[i].t)>75*60000).length;
  assert.equal((svg.match(/class="rt-long-line rt-gap"/g)||[]).length,n);
 }else{
  assert.ok(!svg.includes('class="rt-sample"'));
 }
});
