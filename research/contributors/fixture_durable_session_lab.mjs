// REMURA Contributors v0.55 LAB — 20/11/2026 CET
// POSIX synthetic orchestration only. No provider SDK, credentials or remote execution.
import {execFile} from "node:child_process";
import {promisify} from "node:util";
import {fileURLToPath} from "node:url";
import {fixtureConfigGate} from "./fixture_proxy_config_gate.mjs";
import {fixtureBatchProbe} from "./d1_fixture_batch_probe.mjs";
import {makeSyntheticSession} from "./fixture_session_orchestration_lab.mjs";

const exec=promisify(execFile);
const claimScript=fileURLToPath(new URL("./fixture_claim_cli_lab.py",import.meta.url));
export function makeDurableSyntheticSession(directory,openSynthetic){
 const run=makeSyntheticSession(fixtureConfigGate,fixtureBatchProbe,async cfg=>{
  // Claim BEFORE any attempt to open the injected mock. Never reset or retry.
  // No inherited credentials, shell, user-configurable executable or script.
  const result=await exec("/usr/bin/python3",["-I","-B",claimScript,directory],
   {env:{PATH:"/usr/bin:/bin",LANG:"C"},timeout:5000,maxBuffer:1024});
  if(result.stdout!=="SYNTHETIC_CLAIM_CONSUMED\n"||result.stderr!=="")throw Error("claim_denied");
  return openSynthetic(cfg);
 });
 return run;
}
