import {mountExperience} from './experience.mjs';
const controller=mountExperience(document.querySelector('#play-intro'));
let internal=false;try{internal=!!document.referrer&&new URL(document.referrer).origin===location.origin&&new URL(document.referrer).pathname.startsWith(new URL('./',location.href).pathname);}catch{}
if(controller&&!internal&&!matchMedia('(prefers-reduced-motion: reduce)').matches)controller.open({auto:true});
