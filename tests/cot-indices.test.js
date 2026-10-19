/* Eseguire con: node --test tests/cot-indices.test.js */
const test = require("node:test");
const assert = require("node:assert/strict");
const {index,evaluate,WINDOWS} = require("../cot-indices-core.js");
const week = i => new Date(Date.UTC(2020,0,7+i*7)).toISOString().slice(0,10);
const series = n => Array.from({length:n},(_,i)=>({date:week(i),a:i-60,b:60-i}));

test("finestre COT disponibili da 26 a 260 settimane",()=>{
  assert.deepEqual(WINDOWS,[26,52,156,260]);
  assert.throws(()=>evaluate(series(100),25),RangeError);
});
test("COT Index usa minimo e massimo storici compreso il valore attuale",()=>{
  assert.equal(index([1,3,5]).value,100);
  assert.equal(index([5,3,1]).value,0);
  assert.equal(index([-20,0,-10]).value,50);
});
test("range piatto o non valido restituisce N/D anziché 50 arbitrario",()=>{
  assert.equal(index([3,3,3]),null);
  assert.equal(index([0,NaN,4]),null);
  const constant=Array.from({length:26},(_,i)=>({date:week(i),a:7,b:-7}));
  const r=evaluate(constant,26);
  assert.equal(r.state,"ok");
  assert.equal(r.a,null);
  assert.equal(r.gapIndex,null);
  assert.equal(r.gap,14);
});
test("l'indice a 156 settimane non usa una storia incompleta",()=>{
  const r=evaluate(series(100),156);
  assert.equal(r.state,"insufficient");
  assert.equal(r.available,100);
  assert.equal(r.gapIndex,null);
});
test("Gap in punti percentuali con segno e Gap Index sul suo range",()=>{
  const r=evaluate(series(260),52);
  assert.equal(r.state,"ok");
  assert.equal(r.a.value,100);
  assert.equal(r.b.value,0);
  assert.equal(r.gap,2*259-120);
  assert.equal(r.gapIndex.value,100);
  assert.equal(r.gapSeries.length,52);
});
test("dati disordinati, duplicati e non numerici non falsano l'indice",()=>{
  const rows=series(26);
  const r=evaluate([...rows.slice().reverse(),rows[25],{date:"2020-10-10",a:Infinity,b:0}],26);
  assert.equal(r.state,"ok");
  assert.equal(r.available,26);
  assert.equal(r.asof,week(25));
});
test("intervallo a 260 settimane è calcolabile con almeno 260 report",()=>{
  assert.equal(evaluate(series(259),260).state,"insufficient");
  assert.equal(evaluate(series(260),260).a.value,100);
});

test("le 35 schede condivise collegano gli indici e hanno uno script inline sintatticamente valido",()=>{
  const fs=require("node:fs"),vm=require("node:vm");
  const html=fs.readFileSync("asset.html","utf8");
  for(const id of ['id="cot-period"','id="cot-index-a"','id="cot-index-b"','id="cot-index-gap"','id="cot-gap-chart"','id="chart-period"','cot-indices-core.js']) {
    assert.ok(html.includes(id),"Elemento mancante: "+id);
  }
  const scripts=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
    .map(match=>match[1]).filter(Boolean);
  assert.equal(scripts.length,1,"La pagina dovrebbe avere un solo script inline");
  assert.doesNotThrow(()=>new vm.Script(scripts[0]));
});
