// REMURA V28.3 public release packager. Node 22+, local Git object database only.
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {readFileSync,mkdirSync,writeFileSync,existsSync,rmSync} from 'node:fs';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
export function validateRelease(manifest){
 const paths=["index.html","app.mjs","experience.mjs","markets.mjs","retail-history.mjs","pwa.mjs","remura.css","manifest.webmanifest","sw.js","assets/app-icon-180.png","assets/app-icon-192.png","assets/app-icon-512.png","assets/experience/intro.css","assets/experience/smf.webp",...Array.from({length:9},(_,i)=>`assets/experience/frame-${i}.webp`),"data/cot-b223.json","data/myfxbook-latest.json","data/myfxbook-history.json"];
 const fail=m=>{throw Error(m)};
 if(!manifest||manifest.schema!=="remura-public-release-v1"||!/^v\d+\.\d+(\.\d+)?$/.test(manifest.version)||!/^[a-f0-9]{40}$/.test(manifest.commit)||!Array.isArray(manifest.files)||manifest.files.length!==paths.length)fail("Invalid release manifest");
 const seen=new Set();let total=0;
 for(const f of manifest.files){
   if(!f||!paths.includes(f.path)||seen.has(f.path)||f.mode!=="100644"||f.type!=="blob"||!/^[a-f0-9]{40}$/.test(f.sha)||!Number.isSafeInteger(f.size)||f.size<=0||f.size>1024*1024)fail("Invalid public asset");
   seen.add(f.path);total+=f.size;
 }
 if(total>2*1024*1024||paths.some(p=>!seen.has(p)))fail("Incomplete or oversized release");
 return {files:seen.size,bytes:total};
}
export function buildRelease(manifest, output){
 const counts=validateRelease(manifest);const dir=resolve(output);
 if(existsSync(dir))throw Error('Output already exists; choose a new directory');
 const git=(...args)=>execFileSync('git',args,{maxBuffer:4*1024*1024});
 if(git('rev-parse',manifest.commit+'^{commit}').toString().trim()!==manifest.commit)throw Error('Commit mismatch');
 const all=[];
 for(const f of manifest.files){
  const path='labs/remura-v28/'+f.path;
  const entry=git('ls-tree',manifest.commit,'--',path).toString().trim();
  if(entry!==f.mode+' '+f.type+' '+f.sha+'\\t'+path && entry!==f.mode+' '+f.type+' '+f.sha+'\t'+path)throw Error('Tree mismatch: '+f.path);
  const bytes=git('cat-file','blob',f.sha);
  const id=createHash('sha1').update('blob '+bytes.length+'\0').update(bytes).digest('hex');
  if(bytes.length!==f.size||id!==f.sha)throw Error('Blob mismatch: '+f.path);
  all.push([f.path,bytes]);
 }
 const get=p=>all.find(([n])=>n===p)[1].toString('utf8');
 if(!get('index.html').includes(manifest.version+' LAB')||!get('sw.js').includes("'"+manifest.version+"'"))throw Error('Version mismatch');
 const digest=all.map(([p,b])=>createHash('sha256').update(b).digest('hex')+'  '+p).join('\n')+'\n';
 mkdirSync(dir,{recursive:false});
 try{for(const [p,b] of all){const dst=join(dir,p);mkdirSync(dirname(dst),{recursive:true});writeFileSync(dst,b,{flag:'wx'});}}catch(e){rmSync(dir,{recursive:true,force:true});throw e;}
 return {...counts,sha256sums:digest};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 if(process.argv.length!==4)throw Error('Usage: node pack-public-release.mjs MANIFEST NEW_OUTPUT_DIRECTORY');
 const manifest=JSON.parse(readFileSync(process.argv[2],'utf8'));
 const result=buildRelease(manifest,process.argv[3]);
 process.stdout.write(result.sha256sums);process.stderr.write(JSON.stringify({files:result.files,bytes:result.bytes})+'\n');
}
