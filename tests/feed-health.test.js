const test=require('node:test'),assert=require('node:assert/strict'),{inspect}=require('../feed-health-core.js');
const now=Date.parse('2026-10-22T20:00:00Z');
const doc=m=>({status:'ok',updatedAt:new Date(now-m*60000).toISOString(),symbols:{EURUSD:{lPct:80},XAUUSD:{lPct:40}}});
test('fresh verified data and coverage',()=>{const x=inspect(doc(25),['EURUSD','US500'],now);assert.equal(x.valid,true);assert.equal(x.recent,true);assert.equal(x.ageMinutes,25);assert.equal(x.covered,1);});
test('stale, future or missing observations are not live',()=>{assert.equal(inspect(doc(181),[],now).recent,false);assert.equal(inspect(doc(-10),[],now).recent,false);assert.equal(inspect({},[],now).valid,false);});