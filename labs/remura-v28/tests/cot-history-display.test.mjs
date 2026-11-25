import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {buildCotHistory} from '../cot-history-core.mjs';
const d=JSON.parse(readFileSync(new URL('../data/cot-history-public.json',import.meta.url)));const b=buildCotHistory(d);assert.equal(Object.keys(b.series).length,42);assert.equal(b.dates.length,53);for(const s of Object.values(b.series)){assert.equal(s.rows.length,53);assert.ok(Object.values(s.index52).every(v=>v!==null&&v>=0&&v<=100));}for(let i=0;i<53;i++)for(let j=1;j<=2;j++)assert.ok(Math.abs(b.series.USDJPY.rows[i][j]+b.series.JPY.rows[i][j])<1e-9);const missing=structuredClone(d);missing.contracts.EUR.positions.pop();assert.throws(()=>buildCotHistory(missing));
