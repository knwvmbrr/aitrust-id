import React,{Suspense,lazy} from 'react';
function Fallback(){return <section data-hp-uncertainty-unavailable className="mt-4 rounded-xl border border-line bg-surface p-4 text-sm leading-6"><h3 className="font-semibold">Uncertainty wording unavailable</h3><p className="mt-1">This preview could not open. Other tags remain separate.</p><a className="mt-2 inline-flex min-h-11 items-center underline underline-offset-4" href="https://github.com/knwvmbrr/aitrust-id/blob/main/docs/hp-uncertainty-device.md">Read the uncertainty-word guide</a></section>;}
class Boundary extends React.Component{
 state={failed:false};
 static getDerivedStateFromError(){return {failed:true};}
 componentDidCatch(){} // Errors are confined to this optional surface, never a tag result.
 render(){return this.state.failed?<Fallback/>:this.props.children;}
}
export function createHPUncertaintyExplorerSlot(load=()=>import('./HPUncertaintyExplorer.jsx')){
 const Explorer=lazy(async()=>{
  let timer;
  try{
   const module=await Promise.race([load(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Uncertainty preview import unavailable')),15000);})]);
   if(typeof module.HPUncertaintyExplorer!=='function')throw Error('Uncertainty preview export unavailable');
   return {default:module.HPUncertaintyExplorer};
  }finally{clearTimeout(timer);}
 });
 return function HPUncertaintyExplorerSlot(){return <Boundary><Suspense fallback={<p role="status" className="mt-4 text-sm">Opening the uncertainty wording check…</p>}><Explorer/></Suspense></Boundary>;};
}
export const HPUncertaintyExplorerSlot=createHPUncertaintyExplorerSlot();
