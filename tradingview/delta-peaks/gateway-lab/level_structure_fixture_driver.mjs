// REMURA v0.8.116 LAB — 17/11/2026 CET
// Differential driver only, reads a finite fixture array on stdin, never live.
import {validateLevelStructure} from "./level_structure_candidate.mjs";
let raw="";for await(const part of process.stdin){raw+=part;if(raw.length>2000000)throw Error("fixture cap");}
const items=JSON.parse(raw);if(!Array.isArray(items)||items.length>100)throw Error("fixture cap");
console.log(JSON.stringify(items.map(x=>{try{return {ok:true,result:validateLevelStructure(x)};}catch{return {ok:false};}})));
