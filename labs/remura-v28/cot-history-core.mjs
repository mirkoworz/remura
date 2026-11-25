// REMURA v1.82 LAB — descriptive public CFTC history, no network.
export function buildCotHistory(data) {
  const codes={AUD:"232741",NZD:"112741",GBP:"096742",CAD:"090741",EUR:"099741",CHF:"092741",JPY:"097741",US30:"124603",NAS100:"209742",US500:"13874A",DXY:"098662",XAUUSD:"088691",XAGUSD:"084691",USOIL:"067651"};
  const pairs="EURUSD GBPUSD AUDUSD NZDUSD USDJPY USDCAD USDCHF EURGBP EURJPY EURCHF EURCAD EURAUD EURNZD GBPJPY GBPCHF GBPCAD GBPAUD GBPNZD AUDJPY AUDCAD AUDCHF AUDNZD NZDJPY NZDCAD NZDCHF CADJPY CADCHF CHFJPY".split(" ");
  const fx=Object.keys(codes).slice(0,7);
  const dates=data?.reportDates;
  if(data?.schema!=="remura-cftc-history-public-v1" || data.historicalAvailabilityAttested!==false || !Array.isArray(dates) || dates.length!==53 || Object.keys(data.contracts??{}).length!==14) throw Error("invalid archive");
  for(let i=0;i<53;i++) { const d=dates[i],t=Date.parse(d+"T00:00:00Z"); if(!/^\d{4}-\d{2}-\d{2}$/.test(d)||!Number.isFinite(t)||new Date(t).toISOString().slice(0,10)!==d||(i&&t-Date.parse(dates[i-1]+"T00:00:00Z")!==604800000)) throw Error("invalid weekly coverage"); }
  const series={};
  for(const [symbol,code] of Object.entries(codes)) {
    const c=data.contracts[symbol],ds=["XAUUSD","XAGUSD","USOIL"].includes(symbol)?"disagg":"tff";
    if(c?.code!==code||c.dataset!==ds||!Array.isArray(c.positions)||c.positions.length!==53) throw Error("invalid contract");
    series[symbol]={kind:fx.includes(symbol)?"currency_future":"futures_reference",codes:[code],categories:ds==="tff"?["Asset Manager/Institutional","Leveraged Funds"]:["Managed Money","Producer/Merchant"],rows:c.positions.map((r,i)=>{
      if(!Array.isArray(r)||r.length!==5||r.some(v=>!Number.isSafeInteger(v)||v<0)||r[0]<=0||r.slice(1).some(v=>v>r[0]))throw Error("invalid positions");
      return [dates[i],100*(r[1]-r[2])/r[0],100*(r[3]-r[4])/r[0]];
    })};
  }
  for(const pair of pairs) {
    const a=pair.slice(0,3),b=pair.slice(3),leg=(s,i,j)=>s==="USD"?0:series[s].rows[i][j];
    series[pair]={kind:"synthetic_fx",codes:[a,b].filter(s=>s!=="USD").map(s=>codes[s]),categories:["Asset Manager/Institutional","Leveraged Funds"],rows:dates.map((d,i)=>[d,leg(a,i,1)-leg(b,i,1),leg(a,i,2)-leg(b,i,2)])};
  }
  const index=values=>{const lo=Math.min(...values),hi=Math.max(...values);return hi===lo?null:Math.min(100,Math.max(0,100*(values.at(-1)-lo)/(hi-lo)));};
  const evaluate=r=>({a:index(r.map(x=>x[1])),b:index(r.map(x=>x[2])),gap:index(r.map(x=>x[1]-x[2]))});
  for(const s of Object.values(series)) { const r=s.rows;s.index52=evaluate(r.slice(-52));s.previousIndex52=evaluate(r.slice(0,-1));s.weeklyDeltaPp=[r.at(-1)[1]-r.at(-2)[1],r.at(-1)[2]-r.at(-2)[2]]; }
  return {dates,series};
}
