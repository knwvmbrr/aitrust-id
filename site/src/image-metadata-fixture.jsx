import React,{useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import * as Dialog from '@radix-ui/react-dialog';
import {ImageMetadataExplorerSlot} from './ImageMetadataExplorerSlot.jsx';
import {MTExplorer} from './MTExplorer.jsx';
import {HandheldDialogs} from './handheld.jsx';
import './styles.css';
function Shell({title,description,children}){return <Dialog.Portal><Dialog.Overlay className="fixed inset-0 bg-black/40"/><Dialog.Content className="fixed inset-x-2 top-2 bottom-2 overflow-auto rounded-2xl border border-line bg-surface p-5 text-ink sm:left-1/2 sm:right-auto sm:w-full sm:max-w-xl sm:-translate-x-1/2"><Dialog.Title className="text-balance text-xl font-semibold">{title}</Dialog.Title><Dialog.Description className="mt-1 text-sm text-muted">{description}</Dialog.Description><Dialog.Close className="my-3 min-h-11 rounded-lg border border-input px-3 py-2">Close check</Dialog.Close>{children}</Dialog.Content></Dialog.Portal>;}
function Fixture(){
 const ref=useRef(null),[open,setOpen]=useState(false),[epoch,setEpoch]=useState(0);
 useEffect(()=>{const node=ref.current,observe=new MutationObserver(records=>{if(records.some(r=>r.oldValue!==null))setEpoch(v=>v+1);setOpen(node.open);});observe.observe(node,{attributes:true,attributeFilter:['open'],attributeOldValue:true});return()=>observe.disconnect();},[]);
 return <main className="mx-auto max-w-2xl space-y-6 p-4 text-ink"><header><h1 className="text-balance text-2xl font-semibold">AI TRUST ID · image details</h1><p className="text-pretty mt-2">Independent experimental method preview. No AI-origin or tag verdict.</p></header><details data-image-device-method ref={ref}><summary className="min-h-11 cursor-pointer py-3 font-semibold">Image details · preview</summary>{open&&<ImageMetadataExplorerSlot key={epoch}/>}</details><section aria-label="Independent PS checker"><h2 className="text-balance font-semibold">Check an answer with PS</h2><HandheldDialogs Shell={Shell}/></section><section aria-label="Independent wording checker"><h2 className="text-balance font-semibold">Existing MT wording preview</h2><MTExplorer/></section></main>;
}
createRoot(document.getElementById('image-fixture-root')).render(<Fixture/>);
