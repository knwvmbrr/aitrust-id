// Executed in the synthetic fixture's page; production roots remain closed.
(function(){
 function inspect(root,{forced=false}={}){
  const failures=[];const tag=root.querySelector('.tag'),panel=root.querySelector('.panel');
  if(!tag||!panel)throw Error('Missing tagging component');
  const live=document.querySelector('.aitrust-mount[role="status"]');
  if(!live||live.getAttribute('aria-live')!=='polite')failures.push('tag announcement is not polite');
  const gray=value=>{const m=value.match(/^rgba?\(\s*([\d.]+)[, ]+([\d.]+)[, ]+([\d.]+)/);return !m||m[1]===m[2]&&m[2]===m[3];};
  for(const e of [tag,panel,...root.querySelectorAll('.close,.check,.export')]){
   const css=getComputedStyle(e);
   if(!forced&&!['color','backgroundColor','borderTopColor'].every(key=>gray(css[key])))failures.push('colored component');
   if(forced&&css.forcedColorAdjust==='none')failures.push('system colors blocked');
  }
  for(const e of [tag,...(panel.open?[panel,...panel.querySelectorAll('button')]:[])]){
   const rect=e.getBoundingClientRect();if(rect.width>innerWidth+1||rect.left< -1||rect.right>innerWidth+1)failures.push('component horizontal overflow');
   const css=getComputedStyle(e);if(['hidden','clip'].includes(css.overflowY)&&e.scrollHeight>e.clientHeight+1)failures.push('clipped tagging text');
  }
  // Host output may contain its own overflowing code. Inspect tag/dialog geometry
  // without assigning unrelated source-page overflow to this component.
  if(matchMedia('(prefers-reduced-motion: reduce)').matches){for(const e of [tag,panel]){const css=getComputedStyle(e);if(css.animationName!=='none'||css.transitionDuration.split(',').some(n=>parseFloat(n)>0))failures.push('motion despite reduced-motion preference');}}
  return [...new Set(failures)];
 }
 globalThis.badgeProbes={inspect};
})()
