// Targeted engineering probes. A pass is not a complete WCAG/ACR assessment.
async function controls(root){
 const all=await root.locator('a[href],button,input:not([type="hidden"]),textarea,select,summary,[role="button"],[role="tab"],[role="switch"]').all();const result=[];
 for(const el of all){if(!await el.isVisible())continue;if(await el.evaluate(e=>e.disabled||Boolean(e.closest('[inert],[aria-hidden="true"]'))))continue;result.push(el);}return result;
}
async function targetSizes(root){
 const items=[];
 for(const el of await controls(root))items.push(await el.evaluate(e=>{
  const effective=e.matches('input[type="checkbox"],input[type="radio"]')&&e.labels?.length?e.labels[0]:e;
  const b=effective.getBoundingClientRect();const parent=e.parentElement;const clone=parent?.cloneNode(true);if(clone){for(const a of clone.querySelectorAll('a,input,button,select,textarea'))a.remove();}
  const inline=e.tagName==='A'&&getComputedStyle(e).display==='inline'&&Boolean(clone?.textContent.trim());
  return {name:(e.getAttribute('aria-label')||effective.textContent||e.getAttribute('name')||e.tagName).trim().slice(0,90),x:b.x,y:b.y,w:b.width,h:b.height,inline_exception:inline};
 }));
 const failures=[];for(let i=0;i<items.length;i++){const a=items[i];if(a.inline_exception||a.w>=24&&a.h>=24)continue;const cx=a.x+a.w/2,cy=a.y+a.h/2;for(let j=0;j<items.length;j++){if(i===j)continue;const b=items[j];if(b.w<24||b.h<24){if(Math.hypot(cx-b.x-b.w/2,cy-b.y-b.h/2)<24-0.1)failures.push(a.name+' overlaps adjacent undersized target '+b.name);}else{const x=Math.max(b.x,Math.min(cx,b.x+b.w)),y=Math.max(b.y,Math.min(cy,b.y+b.h));if(Math.hypot(cx-x,cy-y)<12-0.1)failures.push(a.name+' lacks spacing from '+b.name);}}}
 return {controls:items.length,inline_exceptions:items.filter(i=>i.inline_exception).length,failures:[...new Set(failures)]};
}
async function focusVisibility(page,root){
 let checked=0;const failures=[];await page.keyboard.press('Tab');
 for(const el of await controls(root)){
  if(await el.evaluate(e=>e.tabIndex<0))continue;
  await el.scrollIntoViewIfNeeded();await el.focus();
  const p=await el.evaluate(e=>{const c=getComputedStyle(e),r=e.getBoundingClientRect();const visible=(parseFloat(c.outlineWidth)>0&&c.outlineStyle!=='none')||c.boxShadow!=='none';const points=[[r.x+r.width/2,r.y+r.height/2],[r.x+1,r.y+1],[r.right-1,r.y+1],[r.x+1,r.bottom-1],[r.right-1,r.bottom-1]];const reachable=points.some(([x,y])=>{if(x<0||y<0||x>=innerWidth||y>=innerHeight)return false;const h=document.elementFromPoint(x,y);return h===e||Boolean(h&&e.contains(h));});return {name:(e.getAttribute('aria-label')||e.textContent||e.tagName).trim().slice(0,90),visible,reachable,focused:document.activeElement===e};});
  checked++;if(!p.focused)failures.push('Not keyboard focused: '+p.name);if(!p.visible)failures.push('No focus indicator: '+p.name);if(!p.reachable)failures.push('Focused control fully obscured: '+p.name);
 }return {checked,failures};
}
async function spacing(page,root){
 const style=await page.addStyleTag({content:'body,body *{line-height:1.5!important;letter-spacing:.12em!important;word-spacing:.16em!important}body p{margin-bottom:2em!important}'});
 try{return await root.evaluate(root=>{
  const clipped=[];for(const e of root.querySelectorAll('p,h1,h2,h3,h4,li,span,button,a,label,pre,code,summary')){const c=getComputedStyle(e);if(!e.getClientRects().length||c.visibility==='hidden'||!e.textContent.trim())continue;if(e.closest('[aria-hidden="true"],[inert]'))continue;const sr=c.position==='absolute'&&e.clientWidth<=1&&e.clientHeight<=1&&(c.clip!=='auto'||c.clipPath!=='none');if(sr)continue;
   const hiddenX=['hidden','clip'].includes(c.overflowX),hiddenY=['hidden','clip'].includes(c.overflowY);if(hiddenX&&e.scrollWidth>e.clientWidth+2||hiddenY&&e.scrollHeight>e.clientHeight+2)clipped.push(e.tagName.toLowerCase()+': '+e.textContent.trim().slice(0,70));
  }return {clipped,horizontal_overflow:document.documentElement.scrollWidth>document.documentElement.clientWidth+1||root.scrollWidth>root.clientWidth+1};
 });}finally{await style.evaluate(e=>e.remove());}
}
async function disclosures(root){let checked=0;const failures=[];for(const d of await root.locator('details').all()){
 const summary=d.locator('summary').first();if(!await summary.isVisible())continue;
 if(await d.evaluate(e=>e.open))await summary.press('Enter');const closed=await d.evaluate(e=>e.getBoundingClientRect().height);await summary.press('Enter');const expanded=await d.evaluate(e=>({open:e.open,height:e.getBoundingClientRect().height}));if(!expanded.open||expanded.height<=closed+1)failures.push('Disclosure fails to expand: '+(await summary.innerText()));await summary.press('Enter');if(await d.evaluate(e=>e.open))failures.push('Disclosure fails to close');checked++;
 }return {checked,failures};}
module.exports={controls,targetSizes,focusVisibility,spacing,disclosures};
