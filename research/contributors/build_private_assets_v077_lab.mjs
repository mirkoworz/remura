// REMURA Contributors v0.77 LAB — 21/11/2026 16:44 CET
// Offline only: deterministic build or verify. No live secrets, network, deployment.
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const names=Object.freeze(["contributors_recovery_v077_private_lab.html","contributors_owner_recovery_v077_private_lab.html","contributors_levels_v077_lab.html","owner_levels_v077_lab.html","contributors_private_recovery_v076_lab.css","recovery_portal_v072_lab.mjs","secure_exit_v072_lab.mjs","recovery_transport_v070_lab.mjs","reconciliation_client_v065_lab.mjs","amendment_client_v063_lab.mjs","contributors_private_levels_v076_lab.css","contributors_levels_ui_v076_lab.mjs","contributors_candidate_client_v076_lab.mjs","owner_level_audit_ui_v077_lab.mjs"]);
function render(){
 const files=Object.fromEntries(names.map(n=>{
  if(!/^[a-z0-9_.-]+$/.test(n))throw Error('REMURA_V077_BAD_ASSET');
  const s=readFileSync(new URL('./'+n,import.meta.url),'utf8');
  if(s.length<1||s.length>120000)throw Error('REMURA_V077_BAD_LENGTH');
  return [n,s];
 }));
 return '// REMURA Contributors v0.77 LAB — 21/11/2026 16:44 CET · AUTO-GENERATED / NO SECRETS\n'+
  'export const privateAssetFilesV077=Object.freeze('+JSON.stringify(files)+');\n';
}
const expected=render();
const output=new URL('./private_assets_v077_lab.mjs',import.meta.url);
if(process.argv.includes('--build')){
 writeFileSync(output,expected,'utf8');
}else if(process.argv.includes('--check')){
 const actual=readFileSync(output,'utf8');
 if(actual!==expected)throw Error('REMURA_V077_ASSET_DRIFT');
 console.log('REMURA_V077_ASSETS=14_MATCH; sha256='+createHash('sha256').update(actual).digest('hex'));
}else if(import.meta.url===new URL(process.argv[1],'file://').href){
 throw Error('REMURA_V077_REQUIRES_BUILD_OR_CHECK');
}
export {render,names};
