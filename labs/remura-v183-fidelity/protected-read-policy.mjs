// Candidate only. Must be called AFTER existing native Access + D1 profile resolution.
export function createProtectedReadPolicy(approvedFiles){
 const validPath=p=>typeof p==='string'&&/^\/[A-Za-z0-9][A-Za-z0-9._/-]*$/.test(p)&&!p.includes('//')&&!p.split('/').some(s=>s==='.'||s==='..');
 const index=new Map();
 for(const f of approvedFiles){
  if(!validPath(f.path)||!f.path.startsWith('/remura/')||index.has(f.path)||!['shared','owner'].includes(f.scope))throw Error('invalid manifest');
  index.set(f.path,f.scope);
 }
 return function decide({method,path,profile}){
  if(method!=='GET'||!validPath(path)||profile?.can_read!==true)return false;
  const owner=profile.role==='OWNER'&&profile.slot==='owner';
  const friend=profile.role==='CONTRIBUTOR'&&['friend-a','friend-b','friend-c'].includes(profile.slot);
  if(!owner&&!friend)return false;
  const scope=index.get(path);
  return scope==='shared'||(scope==='owner'&&owner);
 };
}
