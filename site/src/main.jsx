import React,{useState,useEffect,useSyncExternalStore} from 'react';
import {createRoot} from 'react-dom/client';
import * as Dialog from '@radix-ui/react-dialog';
import * as Tabs from '@radix-ui/react-tabs';
import {clsx} from 'clsx';
import {twMerge} from 'tailwind-merge';
import {personTags,enterpriseTags,allTags} from './catalog.js';
import scope from './public-scope.json';
import {registerPublicTagTools} from './model-tools.js';
import {presentation} from './presentation.js';
import {usage} from './usage.js';
import {HandheldDialogs} from './handheld.jsx';
import {WorkflowPanel,workflows} from './workflows/index.jsx';
import {WorkflowIcon} from './workflows/shared.jsx';

const cn=(...x)=>twMerge(clsx(x));
const repository='https://github.com/knwvmbrr/aitrust-id';
const sourceDownload=repository+'/archive/refs/heads/main.zip';
const quickstart=repository+'/blob/main/docs/open-validation-path.md';
const securityReport=repository+'/security/advisories/new';
const button='rounded-lg border border-line bg-surface px-4 py-3 text-sm font-medium hover:border-ink hover:bg-ink hover:text-surface';
const featuresById=new Map(scope.records.map(r=>[r.id,r]));
const sharedIds=['F-001','F-003','F-004','F-005','F-007','F-008','F-009','N-005','N-006'];
function download(name,content,type='application/json'){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function route(){let decoded;try{decoded=decodeURIComponent(location.hash.slice(1));}catch{return {audience:'person',id:null};}const [audience,id]=decoded.split('/');return {footer:workflows.find(w=>w.slug===decoded)?.name||null,audience:audience==='enterprise'?'enterprise':'person',id:allTags.some(t=>t.id===id&&t.audience===audience)?id:null};}
function Section({title,children}){return <section className="border-t border-line py-4"><h3 className="mb-2 text-base font-semibold">{title}</h3>{children}</section>}
function Bullets({items}){return <ul className="list-disc space-y-1 pl-5 text-sm leading-6">{items.map((item,i)=><li key={i}>{item}</li>)}</ul>}
function Shell({children,title,description}) {
 return <Dialog.Portal><Dialog.Overlay className="fixed inset-0 z-40 bg-black/60"/><Dialog.Content className="modal fixed inset-x-3 top-1/2 z-50 mx-auto max-h-[calc(100dvh-1.5rem)] max-w-2xl -translate-y-1/2 overflow-y-auto break-words rounded-2xl border border-line bg-surface shadow-lg sm:inset-x-6 sm:max-h-[calc(100dvh-3rem)]">
  <header className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-line bg-surface px-5 py-4 sm:px-6">
   <div className="min-w-0"><Dialog.Title className="text-xl font-semibold">{title}</Dialog.Title><Dialog.Description className="mt-1 text-sm text-muted">{description}</Dialog.Description></div>
   <Dialog.Close aria-label="Close" className="flex size-11 shrink-0 items-center justify-center rounded-lg border border-line hover:border-ink"><svg aria-hidden="true" viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="m6 6 12 12M18 6 6 18"/></svg></Dialog.Close>
  </header><div className="px-5 py-5 sm:px-6">{children}</div>
 </Dialog.Content></Dialog.Portal>;
}
function Disclosure({title,children}) {
 return <details className="tag-disclosure border-t border-line"><summary className="flex min-h-12 cursor-pointer items-center justify-between gap-3 py-3 text-sm font-semibold"><span>{title}</span><span aria-hidden="true" className="disclosure-symbol text-lg font-normal">+</span></summary><div className="pb-4 text-sm leading-6">{children}</div></details>;
}
function FeatureList({ids}){const unique=[...new Set(ids)].map(id=>featuresById.get(id)).filter(Boolean);return <ul className="mt-2 space-y-3">{unique.map(f=><li key={f.id}><p className="text-sm font-semibold">{f.title}</p><p className="text-sm leading-6">{f.job}</p><p className="mt-1 text-sm text-muted">{f.id} · {f.disposition} · Scope record; not an implementation claim</p></li>)}</ul>}
function UseTag({tag}) {
 const use=usage(tag);const [message,setMessage]=useState('');
 async function copy(command){try{await navigator.clipboard.writeText(command);setMessage('Commands copied. Review them before running in Terminal.');}catch{setMessage('Copy is unavailable. Select the commands, or open the full setup guide.');}}
 return <section data-tag-usage className="mb-4 rounded-xl border border-line p-4 text-sm leading-6">
  <h3 className="mb-1 font-semibold">Use this tag</h3><p>{use.summary}</p>{tag.id==='PS'&&<HandheldDialogs Shell={Shell}/>}
  {use.available?<>
   <div className="my-3 flex flex-wrap gap-2"><a className={button} href={sourceDownload}>Download source</a><a className={button} href={quickstart} target="_blank" rel="noreferrer">Try locally</a></div>
   <details className="tag-disclosure"><summary className="flex min-h-12 cursor-pointer items-center justify-between gap-3 font-semibold"><span>Setup instructions</span><span aria-hidden="true" className="disclosure-symbol text-lg">+</span></summary>
    <p className="mb-3 text-muted">{use.prerequisites}</p><ol className="list-decimal space-y-4 pl-5">{use.steps.map((step,i)=><li key={step.title}><h4 className="font-semibold">{step.title}</h4><p>{step.body}</p><pre className="my-2 overflow-x-auto rounded-lg border border-line bg-canvas p-3 text-xs leading-5"><code>{step.command}</code></pre><button type="button" className="min-h-11 rounded-lg border border-line px-3 text-xs" aria-label={'Copy step '+(i+1)+' commands'} onClick={()=>copy(step.command)}>Copy commands</button></li>)}</ol>
    <p className="mt-3">{use.browser}</p><p className="mt-3 text-muted">{use.privacy}</p><h4 className="mt-3 font-semibold">Stop the checker</h4><pre className="my-2 overflow-x-auto rounded-lg border border-line bg-canvas p-3 text-xs"><code>{use.stop}</code></pre>
   </details><p className="mt-2">{use.next}</p><p role="status" className="mt-1 text-muted">{message}</p>
  </>:<p className="mt-2 text-muted">{use.next}</p>}
 </section>;
}
function TagDetails({tag}) {
 const [message,setMessage]=useState('');
 const intro=presentation(tag);
 async function copyLink(){try{await navigator.clipboard.writeText(location.href);setMessage('Tag link copied.');}catch{setMessage('Copy was unavailable. The browser address is the tag link.');}}
 return <>
  <div className="mb-3 flex flex-wrap items-center gap-2 text-xs"><span className="rounded-md border border-input px-2 py-1 font-mono font-semibold">{tag.code}</span><span className="rounded-md bg-canvas px-2 py-1">{tag.status}</span><span className="text-muted">{intro.access}</span></div>
  <p data-tag-summary className="text-lg leading-7">{intro.summary}</p>
  <p data-tag-limit className="mt-2 text-sm leading-6 text-muted">{intro.limit}</p>
  <section aria-label="Validation status" className="my-4 rounded-xl border border-line bg-canvas p-4">
   <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="text-sm font-semibold">Validation</h3><span className="text-xs text-muted">{intro.stage}</span></div>
   <p className="mt-1 text-sm font-semibold">{intro.validationTitle}</p><p className="mt-1 text-sm leading-6 text-muted">{intro.validation}</p><a className="mt-2 block text-xs underline underline-offset-4" href="/policies/validation/">{intro.releasePolicy}</a>
  </section>
  <UseTag tag={tag}/>
  <Disclosure title="How it works">
   <h4 className="font-semibold">What it can say</h4><p>{tag.claim}</p>
   <h4 className="mt-3 font-semibold">Method</h4><p>{tag.method}</p>
   <h4 className="mt-3 font-semibold">What it checks</h4><Bullets items={tag.supported}/>
   <h4 className="mt-3 font-semibold">Limits</h4><Bullets items={tag.limits}/>
   <dl className="mt-3 space-y-2"><div><dt className="font-semibold">Input</dt><dd>{tag.inputs}</dd></div><div><dt className="font-semibold">Output</dt><dd>{tag.outputs}</dd></div><div><dt className="font-semibold">Baseline job and outcome</dt><dd>{tag.job} {tag.outcome}</dd></div></dl>
  </Disclosure>
  <Disclosure title="Testing and evidence">
   <h4 className="font-semibold">What has been checked</h4><p className="tabular-nums">{tag.validation}</p>
   <p className="mt-2 text-muted">Repeating a result or checking its signature can confirm a record. It does not establish that the finding is correct.</p>
   <h4 className="mt-3 font-semibold">Before release</h4><p>{tag.release}</p>
   <h4 className="mt-3 font-semibold">Method settings</h4><p>{tag.version}</p>{tag.floor&&<p>{tag.floor}</p>}
   <p className="mt-3"><a className="underline underline-offset-4" href={'/tags/'+tag.id.toLowerCase().replaceAll('_','-')+'/'}>Full tag reference</a></p>
   <ul className="mt-2 space-y-1">{tag.references.map(url=><li key={url}><a className="break-all underline underline-offset-4" href={url} target="_blank" rel="noreferrer">{url.split('/').at(-1)}</a></li>)}</ul>
   <p className="mt-2 text-xs text-muted">Record {tag.id} · Scope {tag.scopeId}. A planned feature is not evidence that it works.</p>
  </Disclosure>
  <Disclosure title="Privacy, access and all features">
   <h4 className="font-semibold">Privacy</h4><p>{tag.privacy}</p><h4 className="mt-3 font-semibold">Access</h4><p>{tag.price}</p>
   <h4 className="mt-3 font-semibold">Dependencies and failure</h4><Bullets items={tag.dependencies}/><p className="mt-2">{tag.failure}</p>
   <h4 className="mt-3 font-semibold">Who is responsible</h4><p>{tag.owner}</p>
   <h4 className="mt-3 font-semibold">Tag features</h4>{tag.features.length?<FeatureList ids={tag.features}/>:<p>This proposal needs its own validated method.</p>}
   <h4 className="mt-3 font-semibold">Shared capabilities</h4><FeatureList ids={sharedIds}/>
   <div className="mt-4 flex flex-wrap gap-2"><button className={button} onClick={copyLink}>Copy link</button><button className={button} onClick={()=>download('ai-trust-id-'+tag.id+'.json',JSON.stringify({...tag,use:usage(tag),scopeFeatures:[...sharedIds,...tag.features].map(id=>featuresById.get(id)).filter(Boolean)},null,2))}>Download details</button></div><p role="status" className="mt-2">{message}</p>
  </Disclosure>
  <div className="mt-4 flex flex-wrap items-center gap-2"><WorkDialog intent="Report" tag={tag} label="Report an issue"/><WorkDialog intent="Assist" tag={tag} label="Help improve this tag"/></div>
 </>;
}
function TagMark({className=''}){return <svg aria-hidden="true" focusable="false" viewBox="0 0 48 48" fill="none" className={className}><path d="M9 7h22l10 10v20a4 4 0 0 1-4 4H9a4 4 0 0 1-4-4V11a4 4 0 0 1 4-4Z" stroke="currentColor" strokeWidth="2.5"/><circle cx="31" cy="17" r="2.5" stroke="currentColor" strokeWidth="2"/><path d="M14 25h16M14 31h10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/></svg>}
function Appearance() {
 const theme=window.AITrustTheme;
 const state=useSyncExternalStore(theme.subscribe,theme.snapshot,theme.snapshot);
 const [preference,resolved]=state.split(':');
 return <div className="appearance flex items-center gap-2 text-sm">
  <label className="theme-control flex min-h-11 cursor-pointer items-center gap-2"><span className="text-muted" aria-hidden="true">{resolved==='dark'?'Dark':'Light'}</span><input type="checkbox" role="switch" aria-label="Dark mode" className="theme-toggle" checked={resolved==='dark'} onChange={e=>theme.setPreference(e.target.checked?'dark':'light')}/></label>
  <button type="button" aria-label="Use device theme" aria-pressed={preference==='system'} onClick={()=>theme.setPreference('system')} className="min-h-11 rounded-lg px-2 text-xs text-muted underline underline-offset-4">Auto</button>
 </div>;
}
function TagTile({tag,open,onOpen,onClose}){return <Dialog.Root open={open} onOpenChange={value=>value?onOpen(tag):onClose()}><Dialog.Trigger asChild><button data-tag-id={tag.id} aria-label={tag.code+' · '+tag.name} className="tag-tile flex w-full items-center justify-center rounded-xl p-5 text-center"><svg aria-hidden="true" focusable="false" className="tag-outline" viewBox="0 0 180 112" preserveAspectRatio="none"><path d="M12 1H147L179 33V100Q179 111 168 111H12Q1 111 1 100V12Q1 1 12 1Z" stroke="currentColor" strokeWidth="1" vectorEffect="non-scaling-stroke"/><circle cx="152" cy="19" r="3" fill="none" stroke="currentColor" strokeWidth="1" vectorEffect="non-scaling-stroke"/></svg><span className={cn('font-sans text-3xl font-semibold',tag.code.length>3&&'text-xl')}>{tag.code}</span></button></Dialog.Trigger><Shell title={tag.name} description={tag.audience==='person'?'Person tag':'Enterprise offering'}><TagDetails tag={tag}/></Shell></Dialog.Root>}

function WorkDialog({intent,tag=null,label=intent}){return <Dialog.Root><Dialog.Trigger className={button}>{label}</Dialog.Trigger><Shell title={intent} description={tag?tag.code+' · '+tag.name:workflows.find(w=>w.name===intent)?.brief}><WorkflowPanel kind={intent} tag={tag}/></Shell></Dialog.Root>}
function App(){const initial=route();const [audience,setAudience]=useState(initial.audience);const [selected,setSelected]=useState(initial.id);const [footer,setFooter]=useState(initial.footer||null);const [contributionRole,setContributionRole]=useState('labels');
 useEffect(()=>registerPublicTagTools(),[]);
 useEffect(()=>{function sync(){const r=route();if(!r.footer)setAudience(r.audience);setSelected(r.id);setFooter(r.footer||null);}window.addEventListener('hashchange',sync);window.addEventListener('popstate',sync);return()=>{window.removeEventListener('hashchange',sync);window.removeEventListener('popstate',sync);};},[]);
 function switchAudience(value){setSelected(null);setAudience(value);history.replaceState(null,'','#'+value);}
 function openTag(tag){setSelected(tag.id);history.replaceState(null,'','#'+tag.audience+'/'+encodeURIComponent(tag.id));}
 function closeTag(){setSelected(null);history.replaceState(null,'','#'+audience);}
 function openWorkflow(name,role='labels'){setContributionRole(role);setSelected(null);setFooter(name);history.replaceState(null,'','#'+workflows.find(w=>w.name===name).slug);}
 function closeWorkflow(){setFooter(null);history.replaceState(null,'','#'+audience);}
 return <><a href="#tag-grid" className="sr-only focus:not-sr-only focus:absolute focus:left-5 focus:top-4 focus:z-50 focus:bg-surface focus:p-3">Skip to tags</a><main className="mx-auto max-w-5xl px-6 pb-8 pt-6 sm:px-10 sm:pt-8"><div className="mb-5 flex justify-end"><Appearance/></div><header className="flex flex-wrap items-center justify-center gap-3"><TagMark className="size-10 shrink-0"/><h1 className="break-words text-center text-3xl font-semibold sm:text-4xl">AI TRUST ID</h1></header><Tabs.Root id="tag-grid" tabIndex={-1} value={audience} onValueChange={switchAudience} className="mt-7"><Tabs.List aria-label="Tag audience" className="mx-auto flex w-fit max-w-full flex-wrap justify-center gap-1 rounded-xl border border-line bg-surface p-1"><Tabs.Trigger value="person" className="rounded-lg px-5 py-2 text-sm text-muted data-[state=active]:bg-ink data-[state=active]:text-surface">Person</Tabs.Trigger><Tabs.Trigger value="enterprise" className="rounded-lg px-5 py-2 text-sm text-muted data-[state=active]:bg-ink data-[state=active]:text-surface">Enterprise</Tabs.Trigger></Tabs.List>{['person','enterprise'].map(value=><Tabs.Content key={value} value={value} className="tag-grid mt-10 grid gap-4">{(value==='person'?personTags:enterpriseTags).map(tag=><TagTile key={tag.id} tag={tag} open={selected===tag.id} onOpen={openTag} onClose={closeTag}/>)}</Tabs.Content>)}</Tabs.Root><footer className="mt-10 border-t border-line pt-5"><nav aria-label="Company and community" className="grid gap-6 sm:grid-cols-2">{['Community','Understand'].map(group=><section key={group}><h2 className="mb-2 text-xs font-semibold text-muted">{group}</h2><div className="grid grid-cols-1 gap-2 sm:grid-cols-2">{workflows.filter(w=>w.group===group).map(w=><Dialog.Root key={w.name} open={footer===w.name} onOpenChange={value=>value?openWorkflow(w.name):closeWorkflow()}><Dialog.Trigger asChild><a href={'#'+w.slug} aria-label={w.name} onClick={e=>{e.preventDefault();openWorkflow(w.name);}} className="flex min-h-20 min-w-0 items-start gap-2 break-words rounded-xl p-3 hover:bg-surface"><WorkflowIcon kind={w.name} className="mt-1 size-5 shrink-0"/><span className="min-w-0"><span className="block text-sm font-semibold">{w.name}</span><span className="mt-1 block text-xs leading-5 text-muted">{w.brief}</span></span></a></Dialog.Trigger><Shell title={w.name} description={w.brief}><WorkflowPanel kind={w.name} role={contributionRole} chooseContribution={role=>openWorkflow('Assist',role)}/></Shell></Dialog.Root>)}</div></section>)}</nav><div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4 text-xs text-muted"><span>AI TRUST ID · Development preview</span><a className="min-h-11 py-3 underline underline-offset-4" href="/tags/">Tag reference</a></div></footer></main></>;

}
createRoot(document.getElementById('root')).render(<App/>);
