// REMURA Contributors v0.99 LAB — 23 novembre 2026, Europe/Rome.
// Read-only three-principal rehearsal. No fetch, endpoints, credentials, writes, retries or deploy.
// The injected transport MUST be a synthetic offline fixture. This is not a Safari/Access proof.
const CASES=Object.freeze([
  {id:'anonymous-owner-denied',who:'ANON',path:'/owner/',expected:403},
  {id:'anonymous-contributor-denied',who:'ANON',path:'/contributors/',expected:403},
  {id:'owner-home',who:'OWNER',path:'/owner/',expected:200},
  {id:'owner-levels',who:'OWNER',path:'/owner/levels/',expected:200},
  {id:'owner-no-contributor-portal',who:'OWNER',path:'/contributors/',expected:403},
  {id:'owner-no-contributor-levels',who:'OWNER',path:'/contributors/levels/',expected:403},
  {id:'contributor-home',who:'A',path:'/contributors/',expected:200},
  {id:'contributor-levels',who:'A',path:'/contributors/levels/',expected:200},
  {id:'contributor-no-owner-home',who:'A',path:'/owner/',expected:403},
  {id:'contributor-no-owner-levels',who:'A',path:'/owner/levels/',expected:403},
  {id:'contributor-no-owner-js',who:'A',path:'/owner/levels/owner_level_audit_ui_v077_lab.mjs',expected:403},
  {id:'contributor-no-disguised-owner-js',who:'A',path:'/contributors/levels/owner_level_audit_ui_v077_lab.mjs',expected:403},
  {id:'contributor-no-owner-query',who:'A',path:'/owner/?role=OWNER',expected:403},
  {id:'no-get-profile',who:'A',path:'/api/profile',expected:403}
]);
const WHO=Object.freeze(['ANON','OWNER','A','B']);
const SCHEMA='remura.contributors.pilot.readonly.v099';
function casesFor(contributors){
  if(contributors!==1&&contributors!==2)throw Error('pilot_scope_denied');
  const checks=CASES.map(x=>Object.freeze({...x}));
  if(contributors===2){
    checks.push(...[
      {id:'second-contributor-home',who:'B',path:'/contributors/',expected:200},
      {id:'second-contributor-levels',who:'B',path:'/contributors/levels/',expected:200},
      {id:'second-contributor-no-owner',who:'B',path:'/owner/',expected:403},
      {id:'second-contributor-no-owner-js',who:'B',path:'/owner/levels/owner_level_integrity_ui_v078_lab.mjs',expected:403}
    ].map(x=>Object.freeze(x)));
  }
  return Object.freeze(checks);
}
function assess(response,expected,path){
  if(!(response instanceof Response)||response.redirected!==false)return 'INVALID_RESPONSE';
  if(response.status!==expected)return 'WRONG_HTTP_STATUS';
  if(!/(?:^|,)\s*no-store\b/i.test(response.headers.get('Cache-Control')??''))return 'CACHE_NOT_BLOCKED';
  const type=response.headers.get('Content-Type')??'';
  const wanted=expected===403?'application/json':path.endsWith('.mjs')?'text/javascript':'text/html';
  if(!type.toLowerCase().startsWith(wanted))return 'MIME_MISMATCH';
  return 'MATCHED';
}
export async function runPilotReadOnlyFixtureV099({
  mode,send,contributors=2
}={}){
  // No default transport: this code cannot contact a Worker by itself.
  if(mode!=='OFFLINE_FIXTURE_ONLY'||typeof send!=='function')
    return Object.freeze({schema:SCHEMA,status:'NOT_RUN_NO_OFFLINE_FIXTURE',
      checks:0,matched:0,failed:0,results:Object.freeze([]),
      providerVerified:false,safariVerified:false,revocationVerified:false,
      deploymentAuthorized:false,pilotAllowed:false});
  let checks;
  try{checks=casesFor(contributors);}catch{
    return Object.freeze({schema:SCHEMA,status:'NOT_RUN_INVALID_PILOT_SCOPE',
      checks:0,matched:0,failed:0,results:Object.freeze([]),
      providerVerified:false,safariVerified:false,revocationVerified:false,
      deploymentAuthorized:false,pilotAllowed:false});
  }
  const results=[];
  // Deliberately sequential, at most 18 synthetic read-only calls; NO retry.
  for(const check of checks){
    if(!WHO.includes(check.who))throw Error('unreachable_fixture');
    let outcome='TRANSPORT_UNAVAILABLE';
    try{
      const response=await send(Object.freeze({
        fixturePrincipal:check.who,method:'GET',path:check.path
      }));
      outcome=assess(response,check.expected,check.path);
    }catch{outcome='TRANSPORT_UNAVAILABLE';}
    results.push(Object.freeze({id:check.id,outcome}));
  }
  const matched=results.filter(x=>x.outcome==='MATCHED').length;
  return Object.freeze({
    schema:SCHEMA,status:matched===checks.length?'FIXTURE_MATCHES_DESIGN':'FIXTURE_FAIL_CLOSED',
    checks:checks.length,matched,failed:checks.length-matched,
    results:Object.freeze(results),
    // Fixture-only success NEVER converts to real Access, Safari or pilot authorization.
    providerVerified:false,safariVerified:false,revocationVerified:false,
    deploymentAuthorized:false,pilotAllowed:false
  });
}
export {SCHEMA as V099_SCHEMA,casesFor as v099FixtureCases};
