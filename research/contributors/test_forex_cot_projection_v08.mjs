// REMURA Experience v0.8 LAB — 20/11/2026 CET
import {forexCotFixture} from './forex_cot_projection_v08.mjs';
function checks(f){
 const now="2026-11-20T16:00:00Z", row=(code)=>({dataset:"TFF_FIXTURE",code,report_date:"2026-11-17",first_seen_at:"2026-11-20T15:00:00Z",oi:1000,asset_long:300,asset_short:100,leveraged_long:100,leveraged_short:300});
 let n=0;const ok=x=>{if(!x)throw Error("test_failed");n++};const eur=row("099741"),jpy={...row("097741"),asset_long:100,asset_short:200};
 let p=f("EURUSD",[eur],now);ok(p.asset_gap===20&&p.leveraged_gap===-20&&p.publication_at===null);
 ok(f("USDJPY",[jpy],now).asset_gap===10);ok(f("EURJPY",[eur,jpy],now).asset_gap===30);ok(f("JPYEUR",[eur,jpy],now).asset_gap===-30);
 ok(f("EURJPY",[eur],now).status==="UNAVAILABLE");ok(f("EURJPY",[eur,{...jpy,report_date:"2026-11-10"}],now).status==="UNAVAILABLE");
 ok(f("EURUSD",[{...eur,first_seen_at:null}],now).legs[0].first_seen_at===null);
 ok(f("EURUSD",[{...eur,report_date:"2026-10-20"}],now).status==="STALE");
 for(const r of [{...eur,code:"097741"},{...eur,dataset:"LIVE"},{...eur,oi:0},{...eur,asset_long:1001},{...eur,asset_long:1.2},{...eur,report_date:"2026-11-31"},{...eur,first_seen_at:"2026-11-21T00:00:00Z"},{...eur,first_seen_at:"2026-11-16T15:00:00Z"},{...eur,raw:"not allowed"}]){
 let denied=false;try{f("EURUSD",[r],now)}catch(e){denied=e.message==="COT_FIXTURE_DENIED"}ok(denied);
 }
 let denied=false;try{f("EURUSD",[eur,eur],now)}catch(e){denied=e.message==="COT_FIXTURE_DENIED"}ok(denied);
 return n;
}
console.log('REMURA_COT_FIXTURE_PASS='+checks(forexCotFixture));
