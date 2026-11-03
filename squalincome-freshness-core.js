/* REMURA research-only: source-backed Squalincome price freshness policy.
 * NOT wired to the live app. Does NOT authorize COT events, trading or alerts.
 * A future backend must produce one atomic price-integrity/scan snapshot and
 * attest the collector schedule; unrelated GET snapshots are NOT equivalent.
 */
(function(root) {
  "use strict";
  const LIMITS=Object.freeze({M15:180,H1:120,H4:300});
  const PERIODS=Object.freeze({M15:15,H1:60,H4:240});
  const MIN_BARS=55;
  const MAX_SCAN_LAG_MS=20*60*1000;
  const MAX_QUALITY_LAG_MS=1000; // same atomic backend scan, no stale join
  const MAX_NEXT_BATCH_MS=120*60*1000;
  const STATES=Object.freeze({
    LIVE:"price_live_ready",
    WAIT:"waiting_verified_batch",
    STALE:"price_stale",
    UNKNOWN:"unverified"
  });
  const LABELS=Object.freeze({
    [STATES.LIVE]:"Dati prezzo idonei alla verifica live",
    [STATES.WAIT]:"In attesa del batch verificato (non live)",
    [STATES.STALE]:"Dati prezzo fuori soglia (solo storico)",
    [STATES.UNKNOWN]:"Dati non verificabili (nessuna conferma live)"
  });
  function timestamp(s) {
    // Reject times without an explicit timezone, rather than guessing Rome/UTC.
    if(typeof s!=="string" ||
       !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(s))return null;
    const t=Date.parse(s);
    return Number.isFinite(t)?t:null;
  }
  function fail(reason) {
    return {state:STATES.UNKNOWN,label:LABELS[STATES.UNKNOWN],
      livePriceEligible:false,signalAuthorized:false,
      reason,overdue:[],ageMinutes:null};
  }
  function evaluate(input) {
    if(!input || typeof input!=="object")return fail("no_snapshot");
    const scanned=timestamp(input.scanAt),observed=timestamp(input.observedAt);
    if(scanned===null || observed===null || observed<scanned ||
       observed-scanned>MAX_SCAN_LAG_MS)return fail("scan_age_unverified");
    const quality=input.priceQuality;
    if(!quality || typeof quality!=="object" ||
       quality.integrity!=="verified" || quality.freshness!=="recent" ||
       quality.ready!==true)return fail("integrity_or_market_unverified");
    // The existing price-status and signals-status endpoints do not share an
    // atomic timestamp: this field is REQUIRED for any future green badge.
    const qualified=timestamp(quality.checkedAt);
    if(qualified===null || qualified>scanned ||
       scanned-qualified>MAX_QUALITY_LAG_MS)return fail("non_atomic_quality");
    const frames=input.frames;
    if(!frames || typeof frames!=="object")return fail("frames_unavailable");
    const ages={};
    const overdue=[];
    for(const key of ["M15","H1","H4"]) {
      const row=frames[key];
      if(!row || typeof row!=="object" || !Number.isSafeInteger(row.bars) ||
         row.bars<MIN_BARS || row.bars>5000)return fail("frame_history_unverified");
      const closed=timestamp(row.lastClosedAt),period=PERIODS[key];
      if(closed===null || closed%(period*60000)!==0 || closed>scanned ||
         closed>observed)return fail("frame_time_unverified");
      const age=(observed-closed)/60000;
      if(!Number.isFinite(age) || age<0 || age>10080)return fail("frame_age_unverified");
      ages[key]=Math.round(age*100)/100;
      if(age>LIMITS[key])overdue.push(key);
    }
    if(overdue.length===0) {
      return {state:STATES.LIVE,label:LABELS[STATES.LIVE],
        livePriceEligible:true,signalAuthorized:false,
        reason:"all_frames_within_original_gates",overdue:[],ageMinutes:ages};
    }
    // "Waiting" is *only* a non-live annotation backed by an explicit verified
    // schedule and a valid successful collection. Never infer a due time from
    // the 120-minute average, or from a failed request.
    const batch=input.batch;
    if(batch && batch.provenance==="server_collector_schedule" &&
       batch.lastOutcome==="ok" && batch.state==="running") {
      const last=timestamp(batch.lastSuccessfulCollectionAt);
      const next=timestamp(batch.nextExpectedAt);
      const latestM15=timestamp(frames.M15.lastClosedAt);
      if(last!==null && next!==null && latestM15!==null &&
         last>=latestM15 && last<=scanned &&
         next>observed && next>last && next-last<=MAX_NEXT_BATCH_MS) {
        return {state:STATES.WAIT,label:LABELS[STATES.WAIT],
          livePriceEligible:false,signalAuthorized:false,
          reason:"verified_next_batch_not_yet_due",overdue,ageMinutes:ages};
      }
    }
    return {state:STATES.STALE,label:LABELS[STATES.STALE],
      livePriceEligible:false,signalAuthorized:false,
      reason:"one_or_more_frames_over_original_gate",overdue,ageMinutes:ages};
  }
  root.REMURA_SQUAL_FRESHNESS=Object.freeze({evaluate,STATES,LABELS,LIMITS,MIN_BARS});
})(typeof window!=="undefined"?window:globalThis);
