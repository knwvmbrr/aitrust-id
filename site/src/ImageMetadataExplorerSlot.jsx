import React,{Component,lazy,Suspense} from 'react';
const Reader=lazy(()=>Promise.race([import('./ImageMetadataExplorer.jsx').then(m=>({default:m.ImageMetadataExplorer})),new Promise((_,reject)=>setTimeout(()=>reject(Error('Optional reader unavailable')),15000))]));
const fallback=<p data-image-metadata-unavailable role="status" className="mt-3 text-sm">This optional image reader is unavailable. Other checks remain separate. <a href="/reference/image-device-guide.md" className="underline">Read the method guide</a>.</p>;
class LocalBoundary extends Component{constructor(props){super(props);this.state={failed:false};}static getDerivedStateFromError(){return {failed:true};}render(){return this.state.failed?fallback:this.props.children;}}
export function ImageMetadataExplorerSlot(){return <LocalBoundary><Suspense fallback={<p role="status">Opening the optional image reader…</p>}><Reader/></Suspense></LocalBoundary>;}
