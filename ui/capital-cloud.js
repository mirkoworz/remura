/* Firebase browser bridge for personally authenticated REMURA Capital.com data.
   No GitHub token, Capital API credentials or Firebase service account in the browser.
   Cloud Firestore security rules MUST restrict reads to the account owner's Firebase UID.
*/
(function(root){
 "use strict";
 const cfg=root.REMURA_FIREBASE_CONFIG;
 const enabled=!!(cfg&&typeof cfg==="object"&&
  typeof cfg.apiKey==="string"&&cfg.apiKey.length>5&&
  typeof cfg.authDomain==="string"&&cfg.authDomain.length>5&&
  typeof cfg.projectId==="string"&&/^[a-z][a-z0-9-]{4,62}$/.test(cfg.projectId)&&
  typeof cfg.appId==="string"&&cfg.appId.length>5);
 const base="https://www.gstatic.com/firebasejs/12.4.0/";
 let pending;
 function setup(){
  if(!enabled)throw Error("Firebase non è ancora configurato.");
  if(!pending)pending=(async()=>{
   const [appModule,authModule,dbModule]=await Promise.all([
    import(base+"firebase-app.js"),import(base+"firebase-auth.js"),
    import(base+"firebase-firestore.js")]);
   const app=appModule.getApps().find(x=>x.name==="remura-capital")||
    appModule.initializeApp(cfg,"remura-capital");
   const auth=authModule.getAuth(app);
   await auth.authStateReady();
   return {auth,authModule,dbModule,db:dbModule.getFirestore(app)};
  })().catch(e=>{pending=null;throw e;});
  return pending;
 }
 async function isSignedIn(){
  if(!enabled)return false;
  const {auth}=await setup();
  return !!auth.currentUser;
 }
 async function signIn(){
  const {auth,authModule}=await setup();
  await authModule.signInWithPopup(auth,new authModule.GoogleAuthProvider());
  return !!auth.currentUser;
 }
 async function signOut(){
  const {auth,authModule}=await setup();
  await authModule.signOut(auth);
 }
 async function readDocument(path){
  const {auth,db,dbModule}=await setup();
  if(!auth.currentUser)return null;
  const snap=await dbModule.getDocFromServer(dbModule.doc(db,...path));
  if(!snap.exists())return null;
  const payload=snap.data()?.payload;
  if(typeof payload!=="string"||payload.length>750000)
   throw Error("Formato cloud Capital.com non valido.");
  return JSON.parse(payload);
 }
 // Firestore paths are fixed: never accept paths or project IDs from URL parameters.
 async function latest(){return readDocument(["remuraPrivate","capital"]);}
 async function history(symbol){
  if(!/^[A-Z0-9]{3,8}$/.test(symbol))throw Error("Simbolo non valido");
  return readDocument(["remuraPrivate","capital","history",symbol]);
 }
 root.REMURA_CAPITAL_CLOUD={enabled,isSignedIn,signIn,signOut,latest,history};
 if(enabled)setup().catch(()=>{});
})(window);
