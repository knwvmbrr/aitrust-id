// Targeted engineering probes. A pass is not a complete WCAG/ACR assessment.
const CONTROL_SELECTOR='a[href],button,input:not([type="hidden"]),textarea,select,summary,[role="button"],[role="tab"],[role="switch"]';
// One physical-node snapshot; never re-resolve an ordinal after an async step.
// Internal callers own this capture and dispose every handle in finally.
async function controls(root,context={}){
 const host=await root.elementHandle();let all=[],last=host,disposed=false;
 const dispose=async()=>{if(disposed)return;disposed=true;await Promise.allSettled([...all,host].filter(Boolean).map(e=>e.dispose()));};
 const verify=async()=>{
  if(!host||!await host.evaluate((root,{selector,nodes})=>{
   const current=[...root.querySelectorAll(selector)];
   return root.isConnected&&current.length===nodes.length&&current.every((node,i)=>node===nodes[i]);
  },{selector:CONTROL_SELECTOR,nodes:all}))throw Error('Accessibility control set changed during probe');
 };
 try{
  if(!host)throw Error('Accessibility probe root unavailable');
  all=await host.$$(CONTROL_SELECTOR);const items=[];
  for(const el of all){last=el;if(!await el.evaluate(e=>e.isConnected))throw Error('Accessibility control detached during capture');if(!await el.isVisible())continue;if(await el.evaluate(e=>e.disabled||Boolean(e.closest('[inert],[aria-hidden="true"]'))))continue;items.push(el);}
  await verify();return {items,verify,dispose};
 }catch(error){error.accessibilityDiagnostic=await focusFailure(last,context,'capture_controls');await dispose();throw error;}
}
async function targetSizes(root,context={}){
 const items=[],capture=await controls(root,context);let last;
 try{for(const el of capture.items){last=el;items.push(await el.evaluate(e=>{
  const effective=e.matches('input[type="checkbox"],input[type="radio"]')&&e.labels?.length?e.labels[0]:e;
  const b=effective.getBoundingClientRect();const parent=e.parentElement;const clone=parent?.cloneNode(true);if(clone){for(const a of clone.querySelectorAll('a,input,button,select,textarea'))a.remove();}
  const inline=e.tagName==='A'&&getComputedStyle(e).display==='inline'&&Boolean(clone?.textContent.trim());
  return {name:(e.getAttribute('aria-label')||effective.textContent||e.getAttribute('name')||e.tagName).trim().slice(0,90),x:b.x,y:b.y,w:b.width,h:b.height,inline_exception:inline};
 }));}
 await capture.verify();
 }catch(error){error.accessibilityDiagnostic=await focusFailure(last,context,'inspect_targets');throw error;}finally{await capture.dispose();}
 const failures=[];for(let i=0;i<items.length;i++){const a=items[i];if(a.inline_exception||a.w>=24&&a.h>=24)continue;const cx=a.x+a.w/2,cy=a.y+a.h/2;for(let j=0;j<items.length;j++){if(i===j)continue;const b=items[j];if(b.w<24||b.h<24){if(Math.hypot(cx-b.x-b.w/2,cy-b.y-b.h/2)<24-0.1)failures.push(a.name+' overlaps adjacent undersized target '+b.name);}else{const x=Math.max(b.x,Math.min(cx,b.x+b.w)),y=Math.max(b.y,Math.min(cy,b.y+b.h));if(Math.hypot(cx-x,cy-y)<12-0.1)failures.push(a.name+' lacks spacing from '+b.name);}}}
 return {controls:items.length,inline_exceptions:items.filter(i=>i.inline_exception).length,failures:[...new Set(failures)]};
}
// Read only after the original action fails; never alter successful probe timing.
async function focusFailure(el,context,action){
 const diagnostic={surface:context.surface||null,theme:context.theme||null,action,selector:el?.toString()||null,identity:'captured_element',control:null};
 let handle,timer,owned=false;
 try{
  if(el){if(typeof el.elementHandle==='function'){handle=await el.elementHandle({timeout:1000});owned=true;}else handle=el;}
  if(handle)diagnostic.control=await Promise.race([handle.evaluate(e=>{
   const css=getComputedStyle(e),rect=e.getBoundingClientRect();
   const label=e.getAttribute('aria-label')||(['INPUT','TEXTAREA','SELECT'].includes(e.tagName)?[...(e.labels||[])].map(l=>l.textContent).join(' '):e.textContent)||e.tagName;
   return {name:label.trim().slice(0,120),tag:e.tagName,
    connected:e.isConnected,visible:Boolean(e.getClientRects().length)&&css.visibility!=='hidden'&&css.display!=='none',
    rect:{x:rect.x,y:rect.y,width:rect.width,height:rect.height}};
  }),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Diagnostic deadline')),1000);})]);
 }catch{diagnostic.control_unavailable=true;}
 finally{clearTimeout(timer);if(owned)await handle?.dispose().catch(()=>{});}
 return diagnostic;
}
async function focusVisibility(page,root,context={}){
 let checked=0;const failures=[];await page.keyboard.press('Tab');
 const capture=await controls(root,context);let last;
 try{for(const el of capture.items){last=el;
  if(await el.evaluate(e=>e.tabIndex<0))continue;
  let action='scroll_into_view';
  try{
   await el.scrollIntoViewIfNeeded();action='focus';await el.focus();action='inspect_focus';
   const p=await el.evaluate(e=>{const c=getComputedStyle(e),r=e.getBoundingClientRect();const visible=(parseFloat(c.outlineWidth)>0&&c.outlineStyle!=='none')||c.boxShadow!=='none';const points=[[r.x+r.width/2,r.y+r.height/2],[r.x+1,r.y+1],[r.right-1,r.y+1],[r.x+1,r.bottom-1],[r.right-1,r.bottom-1]];const reachable=points.some(([x,y])=>{if(x<0||y<0||x>=innerWidth||y>=innerHeight)return false;const h=document.elementFromPoint(x,y);return h===e||Boolean(h&&e.contains(h));});return {name:(e.getAttribute('aria-label')||e.textContent||e.tagName).trim().slice(0,90),visible,reachable,focused:document.activeElement===e};});
   checked++;if(!p.focused)failures.push('Not keyboard focused: '+p.name);if(!p.visible)failures.push('No focus indicator: '+p.name);if(!p.reachable)failures.push('Focused control fully obscured: '+p.name);
  }catch(error){error.accessibilityDiagnostic=await focusFailure(el,context,action);throw error;}
 }await capture.verify();return {checked,failures};
 }catch(error){if(!error.accessibilityDiagnostic)error.accessibilityDiagnostic=await focusFailure(last,context,'verify_control_set');throw error;}finally{await capture.dispose();}
}
async function spacing(page,root){
 const style=await page.addStyleTag({content:'body,body *{line-height:1.5!important;letter-spacing:.12em!important;word-spacing:.16em!important}body p{margin-bottom:2em!important}'});
 try{return await root.evaluate(root=>{
  const clipped=[];for(const e of root.querySelectorAll('p,h1,h2,h3,h4,li,span,button,a,label,pre,code,summary')){const c=getComputedStyle(e);if(!e.getClientRects().length||c.visibility==='hidden'||!e.textContent.trim())continue;if(e.closest('[aria-hidden="true"],[inert]'))continue;const sr=c.position==='absolute'&&e.clientWidth<=1&&e.clientHeight<=1&&(c.clip!=='auto'||c.clipPath!=='none');if(sr)continue;
   const hiddenX=['hidden','clip'].includes(c.overflowX),hiddenY=['hidden','clip'].includes(c.overflowY);if(hiddenX&&e.scrollWidth>e.clientWidth+2||hiddenY&&e.scrollHeight>e.clientHeight+2)clipped.push(e.tagName.toLowerCase()+': '+e.textContent.trim().slice(0,70));
  }return {clipped,horizontal_overflow:document.documentElement.scrollWidth>document.documentElement.clientWidth+1||root.scrollWidth>root.clientWidth+1};
 });}finally{await style.evaluate(e=>e.remove());}
}
async function disclosures(root,{afterExpand=async()=>{}}={}){let checked=0;const failures=[];for(const d of await root.locator('details').all()){
 const summary=d.locator('summary').first();if(!await summary.isVisible())continue;
 if(await d.evaluate(e=>e.open))await summary.press('Enter');const closed=await d.evaluate(e=>e.getBoundingClientRect().height);await summary.press('Enter');await afterExpand(d);const expanded=await d.evaluate(e=>({open:e.open,height:e.getBoundingClientRect().height}));if(!expanded.open||expanded.height<=closed+1)failures.push('Disclosure fails to expand: '+(await summary.innerText()));await summary.press('Enter');if(await d.evaluate(e=>e.open))failures.push('Disclosure fails to close');checked++;
 }return {checked,failures};}
module.exports={controls,targetSizes,focusVisibility,spacing,disclosures};
