const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs");
const macro=require("../macro-core.js");
const HOUR=3600000,QUARTER=900000,END=Date.parse("2026-10-23T14:00:00Z");
const iso=t=>new Date(t).toISOString();
function bars(hours=100,start=END-100*HOUR,base=100,rate=0.002){
 const m15=[];
 for(let i=0;i<hours*4;i++){
  const t=start+i*QUARTER;
  const p=base*Math.exp(rate*i/4+0.002*Math.sin(i/4));
  m15.push({t:iso(t),o:p,h:p*1.002,l:p*0.998,c:p*1.0003});
 }
 function frame(n){
  const rows=[];
  for(let i=0;i<m15.length;i+=n){
   const part=m15.slice(i,i+n);
   if(part.length!==n)continue;
   const t=Date.parse(part[0].t);
   if(t%(n*QUARTER))continue;
   rows.push({t:iso(t),o:part[0].o,h:Math.max(...part.map(x=>x.h)),l:Math.min(...part.map(x=>x.l)),c:part.at(-1).c});
  }
  return rows;
 }
 return {symbol:"GER30",provider:"ctrader",timeframes:{M15:m15,H1:frame(4),H4:frame(16)}};
}
test("OHLC integrity and contiguity are audited without inventing bars",()=>{
 const data=bars(),q=macro.audit(data,END);
 assert.equal(q.state,"recent");
 assert.equal(q.recentGaps,0);
 assert.equal(q.h1.mismatched,0);assert.equal(q.h4.mismatched,0);
 assert.equal(q.h1.verified,q.h1.checked);
 assert.equal(q.h4.verified,q.h4.checked);
 assert.ok(q.ready);
 const broken=structuredClone(data);
 broken.timeframes.H1.at(-1).h*=1.2;
 assert.equal(macro.audit(broken,END).state,"invalid");
 const interrupted=structuredClone(data);
 interrupted.timeframes.M15.splice(-10,1);
 assert.equal(macro.audit(interrupted,END).recentGaps,1);
 assert.ok(macro.audit(interrupted,END).h1.missingInputs>0);
 const weekend=macro.audit(data,END+48*HOUR);
 assert.equal(weekend.state,"stale");
});
test("H1 Pearson uses only aligned contiguous hourly log returns",()=>{
 const a=bars(100,END-100*HOUR,100,0.004);
 const b=structuredClone(a);
 for(const tf of ["H1","H4","M15"])for(const bar of b.timeframes[tf]){
   bar.o*=2;bar.c*=2;bar.h*=2;bar.l*=2;
 }
 const pos=macro.correlation(a,b,{now:END});
 assert.equal(pos.state,"ok");assert.ok(Math.abs(pos.value-1)<1e-9);assert.equal(pos.samples,99);
 const lag=structuredClone(b);
 lag.timeframes.H1=lag.timeframes.H1.filter((_,i)=>i%2===0);
 const fewer=macro.correlation(a,lag,{now:END});
 assert.ok(fewer.samples<pos.samples);
 const missing=macro.correlation(a,null,{now:END});
 assert.equal(missing.state,"insufficient");
});
test("Macro page has a private-readonly architecture and correct menu version",()=>{
 const html=fs.readFileSync("macro.html","utf8");
 const ui=fs.readFileSync("macro.js","utf8");
 const nav=fs.readFileSync("nav.js","utf8");
 const service=fs.readFileSync("sw.js","utf8");
 for(const script of ["nav.js?v=118","macro-core.js?v=118","macro.js?v=118"])assert.ok(html.includes(script));
 assert.ok(ui.includes("./private-api/prices/"));
 assert.ok(!ui.includes("apiKey")&&!ui.includes("CTRADER_ACCESS_TOKEN"));
 assert.ok(nav.includes('href="./macro.html"'));
 assert.ok(service.includes('"./macro.html"'));
});
