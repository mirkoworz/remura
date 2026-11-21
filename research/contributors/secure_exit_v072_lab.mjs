// REMURA Contributors v0.72 LAB — 21/11/2026 12:55 CET.
// Local closing is immediate; Cloudflare Access logout is only requested, not attested.
const DENIED='REMURA_V072_EXIT_DENIED';
const fail=()=>{throw new Error(DENIED)};
function exactHttpsOrigin(s){
 if(typeof s!=='string')fail();
 let u;try{u=new URL(s)}catch{fail()}
 if(u.protocol!=='https:'||u.origin!==s||u.pathname!=='/'||u.username||u.password||u.search||u.hash)fail();
 return s;
}
export function createExitCoordinatorV072({enabled=false,origin=null,navigate=null}={}){
 if(typeof enabled!=='boolean')fail();
 if(enabled){exactHttpsOrigin(origin);if(typeof navigate!=='function')fail();}
 let closed=false;
 return Object.freeze({
  leave(closeLocalView){
   if(typeof closeLocalView!=='function')fail();
   if(closed)return 'ALREADY_CLOSED';
   // Lock future callbacks BEFORE invoking any user-visible clear or provider navigation.
   closed=true;
   closeLocalView();
   if(!enabled)return 'LOCAL_VIEW_CLOSED';
   try{
    navigate(origin+'/cdn-cgi/access/logout');
    // Only navigation requested. The browser/Access provider still controls token revocation.
    return 'PROVIDER_LOGOUT_NAVIGATION_REQUESTED';
   }catch{return 'PROVIDER_LOGOUT_NAVIGATION_FAILED';}
  },
  get closed(){return closed;}
 });
}
