import React,{Suspense,lazy} from 'react';
function Fallback(){return <section data-mt-choice-unavailable className="mt-3 rounded-xl border border-line bg-surface p-4 text-sm leading-6"><h3 className="text-balance font-semibold">Selected wording unavailable</h3><p className="text-pretty mt-1">This optional preview could not open. The other wording checks and tags remain separate.</p><a className="mt-2 inline-flex min-h-11 items-center underline underline-offset-4" href="/reference/mt-choice-device.md">Read the selected-wording guide</a></section>;}
class Boundary extends React.Component{
 state={failed:false};
 static getDerivedStateFromError(){return {failed:true};}
 componentDidCatch(){}
 render(){return this.state.failed?<Fallback/>:this.props.children;}
}
export function createMTChoiceExplorerSlot(load=()=>import('./MTChoiceExplorer.jsx')){
 const Explorer=lazy(async()=>{let timer;try{const m=await Promise.race([load(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Selected wording import unavailable')),15000);})]);if(typeof m.MTChoiceExplorer!=='function')throw Error('Selected wording export unavailable');return{default:m.MTChoiceExplorer};}finally{clearTimeout(timer);}});
 return function MTChoiceExplorerSlot(){return <Boundary><Suspense fallback={<p role="status" className="mt-3 text-sm">Opening the selected-wording preview…</p>}><Explorer/></Suspense></Boundary>;};
}
export const MTChoiceExplorerSlot=createMTChoiceExplorerSlot();
