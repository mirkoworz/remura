// REMURA v0.8.117 LAB — 17/11/2026 CET
import {validatePinnedLevel} from "./level_structure_candidate.mjs";
let raw="";for await(const part of process.stdin){raw+=part;if(raw.length>2000000)throw Error("fixture cap");}
const cases=JSON.parse(raw);if(!Array.isArray(cases)||cases.length>100)throw Error("fixture cap");
const out=[];
for(const c of cases){try{out.push({ok:true,result:await validatePinnedLevel(c.raw,c.expected,c.options)});}catch{out.push({ok:false});}}
console.log(JSON.stringify(out));
