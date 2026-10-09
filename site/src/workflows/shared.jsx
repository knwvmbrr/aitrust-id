import React from 'react';
import {clsx} from 'clsx';
import {twMerge} from 'tailwind-merge';
export const cn=(...values)=>twMerge(clsx(values));
export const repository='https://github.com/knwvmbrr/aitrust-id';
export const issueURL=repository+'/issues/new?template=tag-review.yml';
export const securityURL=repository+'/security/advisories/new';
export const action='inline-flex min-w-0 max-w-full whitespace-normal wrap-anywhere min-h-11 items-center justify-center rounded-lg border border-input px-4 py-2 text-sm font-semibold hover:bg-canvas';
export const input='mt-1 block min-w-0 min-h-11 w-full rounded-lg border border-input bg-surface p-3 text-base';
export function exportJSON(name,value){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
export function Intro({eyebrow,title,children}){return <div className="mb-5"><p className="mb-2 text-xs font-semibold uppercase text-muted">{eyebrow}</p><h3 className="text-2xl font-semibold text-balance">{title}</h3><div className="mt-2 text-sm leading-6 text-muted">{children}</div></div>;}
export function Callout({children}){return <p className="my-3 rounded-lg border border-line bg-canvas p-3 text-sm leading-6">{children}</p>;}
export function Field({id,label,children}){return <div><label className="block text-sm font-semibold" htmlFor={id}>{label}</label>{children}</div>;}
export function Link({href,children,primary=false}){return <a className={primary?action+' bg-ink text-surface hover:bg-ink':action} href={href} target={href.startsWith('https:')?'_blank':undefined} rel={href.startsWith('https:')?'noreferrer':undefined}>{children}</a>;}
export function WorkflowIcon({kind,className='size-5'}){const paths={Report:'M5 21V4m0 0h14l-3 4 3 4H5',Assist:'M14 5a5 5 0 0 0-6 6l-5 5a2 2 0 0 0 3 3l5-5a5 5 0 0 0 6-6l-3 3-3-3 3-3Z',Townhall:'M5 4h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-5 3v-3H3V6a2 2 0 0 1 2-2Z',Teamwork:'M8 4h13v16H8M3 7l1 1 2-2m-3 6 1 1 2-2m-3 6 1 1 2-2m5-8h7m-7 5h7m-7 5h7','How tags work':'M4 4h10l6 6v10H4V4Zm10 3h1m-8 6h10m-10 4h6',Scope:'M3 3h7v7H3V3Zm11 0h7v7h-7V3ZM3 14h7v7H3v-7Zm11 0h7v7h-7v-7Z',About:'M12 3a9 9 0 1 1 0 18 9 9 0 0 1 0-18Zm0 7v6m0-9v1',Legal:'M12 3v18M5 21h14M3 7h18M6 7l-3 7h6l-3-7Zm12 0-3 7h6l-3-7Z'};return <svg className={className} viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d={paths[kind]}/></svg>;}
