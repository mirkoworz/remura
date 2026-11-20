// REMURA Contributors v0.56 LAB — 20/11/2026 CET
// Offline private configuration preparation only. No SDK, network or remote session.
import {constants as C} from "node:fs";
import {open,realpath,lstat} from "node:fs/promises";
import {isAbsolute,join,dirname} from "node:path";
import {fixtureConfigGate} from "./fixture_proxy_config_gate.mjs";

function need(ok){if(!ok)throw Error("private_config_denied");}
const exact=(o,ks)=>o!==null&&typeof o==="object"&&!Array.isArray(o)&&Object.keys(o).sort().join("|")===ks.slice().sort().join("|");

async function readPrivate(path){
 const file=await open(path,C.O_RDONLY|C.O_NOFOLLOW);
 try{
  const st=await file.stat();
  need(st.isFile()&&st.uid===process.getuid()&&(st.mode&0o777)===0o600&&st.size>0&&st.size<=8192);
  const bytes=Buffer.alloc(8193);
  let size=0;
  while(size<bytes.length){const r=await file.read(bytes,size,bytes.length-size,null);if(r.bytesRead===0)break;size+=r.bytesRead;}
  need(size>0&&size<=8192&&size===st.size);
  return JSON.parse(bytes.subarray(0,size).toString("utf8"));
 }finally{await file.close();}
}

async function prepare(dir){
 need(process.platform!=="win32"&&typeof process.getuid==="function"&&isAbsolute(dir)&&await realpath(dir)===dir);
 const st=await lstat(dir);
 need(st.isDirectory()&&st.uid===process.getuid()&&(st.mode&0o777)===0o700);
 // Never write within a Git working tree (including worktrees).
 for(let p=dir;;p=dirname(p)){
  try{await lstat(join(p,".git"));throw Error("git_tree_denied");}
  catch(e){if(e.code!=="ENOENT")throw e;}
  if(dirname(p)===p)break;
 }
 const a=await readPrivate(join(dir,"dashboard.json"));
 const b=await readPrivate(join(dir,"inventory.json"));
 need(exact(a,["account_id","fixture_uuid","lab_uuid"]));
 need(exact(b,["account_id","databases"])&&b.account_id===a.account_id&&Array.isArray(b.databases)&&b.databases.length===4);
 const find=(name,uuid)=>{
  const matches=b.databases.filter(d=>d?.name===name);
  need(matches.length===1&&matches[0].uuid===uuid&&matches[0].jurisdiction==="eu");
  need(b.databases.filter(d=>d?.uuid===uuid).length===1);
 };
 find("remura-contributors-fixture",a.fixture_uuid);
 find("remura-contributors-lab",a.lab_uuid);
 const cfg={name:"remura-contributors-fixture-proxy",account_id:a.account_id,compatibility_date:"2026-11-15",workers_dev:false,preview_urls:false,routes:[],d1_databases:[{binding:"CONTRIBUTORS_FIXTURE_DB",database_name:"remura-contributors-fixture",database_id:a.fixture_uuid,remote:true}]};
 fixtureConfigGate(cfg,a);
 const target=await open(join(dir,"wrangler.fixture.json"),C.O_WRONLY|C.O_CREAT|C.O_EXCL|C.O_NOFOLLOW,0o600);
 try{await target.chmod(0o600);await target.writeFile(JSON.stringify(cfg,null,2)+"\n");await target.sync();}
 finally{await target.close();}
 const parent=await open(dir,C.O_RDONLY|C.O_DIRECTORY|C.O_NOFOLLOW);
 try{await parent.sync();}finally{await parent.close();}
}
try{
 need(process.argv.length===3);
 await prepare(process.argv[2]);
 console.log("REMURA_PRIVATE_CONFIG=LOCAL_MATCH_ONLY");
}catch{console.error("REMURA_PRIVATE_CONFIG=BLOCKED");process.exitCode=2;}
