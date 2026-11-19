import React,{Suspense,lazy} from 'react';
function Fallback(){return <section data-hp-unavailable className="mt-4 rounded-xl border border-line bg-surface p-4 text-sm leading-6"><h3 className="font-semibold">Detail explorer unavailable</h3><p className="mt-1">This preview could not open. Other tags remain separate.</p><a className="mt-2 inline-flex min-h-11 items-center underline underline-offset-4" href="https://github.com/knwvmbrr/aitrust-id/blob/main/docs/hp-device-explorer.md">Use the local detail guide</a></section>;}
class Boundary extends React.Component{
 state={failed:false};
 static getDerivedStateFromError(){return {failed:true};}
 componentDidCatch(){} // Errors are confined to this optional surface, never a tag result.
 render(){return this.state.failed?<Fallback/>:this.props.children;}
}
export function createHPExplorerSlot(load=()=>import('./HPExplorer.jsx')){
 const Explorer=lazy(async()=>{
  let timer;
  try{
   const module=await Promise.race([load(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('HP preview import unavailable')),15000);})]);
   if(typeof module.HPExplorer!=='function')throw Error('HP preview export unavailable');
   return {default:module.HPExplorer};
  }finally{clearTimeout(timer);}
 });
 return function HPExplorerSlot(){return <Boundary><Suspense fallback={<p role="status" className="mt-4 text-sm">Opening the detail explorer…</p>}><Explorer/></Suspense></Boundary>;};
}
export const HPExplorerSlot=createHPExplorerSlot();
