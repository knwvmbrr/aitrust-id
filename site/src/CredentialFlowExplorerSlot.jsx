import React,{Suspense,lazy} from 'react';
function Fallback(){return <section data-credential-unavailable className="mt-4 rounded-xl border border-line bg-surface p-4 text-sm leading-6"><h3 className="font-semibold">Python flow preview unavailable</h3><p className="mt-1">This preview could not open. Other tags remain separate.</p><a className="mt-2 inline-flex min-h-11 items-center underline underline-offset-4" href="https://github.com/knwvmbrr/aitrust-id/blob/main/docs/credential-flow-device.md">Use the local Python flow guide</a></section>;}
class Boundary extends React.Component{
 state={failed:false};
 static getDerivedStateFromError(){return {failed:true};}
 componentDidCatch(){} // Errors are confined to this optional surface, never a tag result.
 render(){return this.state.failed?<Fallback/>:this.props.children;}
}
export function createCredentialFlowExplorerSlot(load=()=>import('./CredentialFlowExplorer.jsx')){
 const Explorer=lazy(async()=>{
  let timer;
  try{
   const module=await Promise.race([load(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Python flow preview import unavailable')),15000);})]);
   if(typeof module.CredentialFlowExplorer!=='function')throw Error('Python flow preview export unavailable');
   return {default:module.CredentialFlowExplorer};
  }finally{clearTimeout(timer);}
 });
 return function CredentialFlowExplorerSlot(){return <Boundary><Suspense fallback={<p role="status" className="mt-4 text-sm">Opening the Python flow preview…</p>}><Explorer/></Suspense></Boundary>;};
}
export const CredentialFlowExplorerSlot=createCredentialFlowExplorerSlot();
