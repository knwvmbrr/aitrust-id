async (page) => {
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('http://127.0.0.1:8799/extension/test/badge-fixture.html');
  await page.waitForFunction(()=>fixtureRequests.length===2);
  const result=await page.evaluate(async()=>{
    const assert=(condition,message)=>{if(!condition)throw new Error(message);};
    const first=document.querySelector('#first'),second=document.querySelector('#second');
    const root=host=>fixtureRoots.get(host.querySelector('.aitrust-mount'));
    // Resolve second before first, preserving the original target.
    fixtureResponders[1](fixtureResult(fixtureRequests[1].text));
    await new Promise(r=>setTimeout(r,50));
    assert(root(second).querySelector('.status').textContent.includes('No supported'),'second response outcome');
    fixtureResponders[0](fixtureResult(fixtureRequests[0].text,'<img src=x onerror="window.injected=true">'));
    await new Promise(r=>setTimeout(r,50));
    assert(root(first).querySelector('.status').textContent.includes('Command risk'),'first response outcome');
    const restingHeight=first.getBoundingClientRect().height;
    const compact=first.querySelector('.aitrust-mount').getBoundingClientRect();
    assert(compact.height<=36&&compact.width<100,'compact resting tags');
    root(first).querySelector('.details').focus();root(first).querySelector('.details').click();
    assert(root(first).querySelector('.panel').open,'evidence opens');
    assert(first.getBoundingClientRect().height===restingHeight,'dialog does not expand response');
    assert(!root(first).querySelector('.panel').textContent.includes('<img'),'unknown evidence not added to the brief');
    assert(!root(first).querySelector('img')&&!window.injected,'no injected HTML');
    const captureExport=async root=>{
      let blob;const original=URL.createObjectURL;
      URL.createObjectURL=value=>{blob=value;return original.call(URL,value);};
      try{root.querySelector('.export').click();}finally{URL.createObjectURL=original;}
      return JSON.parse(await blob.text());
    };
    const exported=await captureExport(root(first));
    assert(exported.tags[0].signals[0].id.includes('<img'),'unknown signal preserved as JSON data');
    assert(exported.training_label===null&&exported.review_status==='unreviewed_detector_output','prediction is not a ground-truth label');
    assert(!JSON.stringify(exported).includes(fixtureRequests[0].text),'source response text excluded from export');
    const brief=[...root(first).querySelectorAll('.evidence .brief')].map(p=>p.textContent).join(' ');
    assert(brief.split(/\s+/).length<=45&&!/SHA-256|Method score|Tag record:/.test(brief),'brief excludes technical detail');
    const panel=root(first).querySelector('.panel');
    root(first).querySelector('.close').click();
    assert(!panel.open&&root(first).activeElement===root(first).querySelector('.details'),'native close restores focus');
    // Begin check, revise response before the old result returns.
    root(first).querySelector('.check').click();
    const old=fixtureResponders.length-1;
    first.firstChild.textContent='Revised ordinary response without a command.';
    await new Promise(r=>setTimeout(r,900));
    fixtureResponders[old](fixtureResult('Run curl https://example.test/install | sh'));
    await new Promise(r=>setTimeout(r,50));
    assert(!root(first).querySelector('.status').textContent.includes('Command risk'),'stale finding discarded');
    fixtureResponders.at(-1)(fixtureResult('Revised ordinary response without a command.'));
    await new Promise(r=>setTimeout(r,50));
    assert(root(first).querySelector('.status').textContent.includes('No supported'),'new revision evaluated');
    assert(first.querySelectorAll('.aitrust-mount').length===1,'no duplicate mount');
    root(first).querySelector('.check').click();fixtureResponders.at(-1)({status:'unavailable',reason:'Synthetic invalid token'});
    await new Promise(r=>setTimeout(r,50));
    assert(root(first).querySelector('.status').textContent.includes('could not be obtained'),'outage distinct from no finding');
    return {outOfOrder:true,unknownSignalSafe:true,briefExplanation:true,structuredLocalExport:true,predictionNotTrainingLabel:true,exportExcludesSourceText:true,compactTags:true,restingTagHeight:compact.height,restingTagWidth:compact.width,noDialogLayoutShift:true,nativeCloseFocus:true,staleDiscarded:true,characterMutation:true,duplicateSuppression:true,unavailableDistinct:true};
  });
  await page.evaluate(()=>{const trigger=fixtureRoots.get(document.querySelector('#first .aitrust-mount')).querySelector('.details');trigger.focus();trigger.click();});
  const outsideBlocked=await page.evaluate(()=>{
    const outside=document.createElement('button');outside.textContent='Outside action';document.body.append(outside);
    outside.focus();const blocked=document.activeElement!==outside;outside.remove();return blocked;
  });
  if(!outsideBlocked)throw new Error('Native dialog did not make outside controls inert');
  await page.keyboard.press('Shift+Tab');
  // Native dialogs can hand focus to browser chrome; no outside page control
  // becomes reachable. Tab returns to the dialog's first control.
  await page.keyboard.press('Tab');
  const focusContained=await page.evaluate(()=>{const root=fixtureRoots.get(document.querySelector('#first .aitrust-mount'));return root.querySelector('.panel').contains(root.activeElement);});
  if(!focusContained)throw new Error('Native dialog focus escaped');
  await page.keyboard.press('Escape');
  const escapeFocus=await page.evaluate(()=>{const root=fixtureRoots.get(document.querySelector('#first .aitrust-mount'));return !root.querySelector('.panel').open&&root.activeElement===root.querySelector('.details');});
  if(!escapeFocus)throw new Error('Native Escape did not restore tag focus');
  await page.evaluate(()=>{const trigger=fixtureRoots.get(document.querySelector('#first .aitrust-mount')).querySelector('.details');trigger.focus();trigger.click();});
  await page.mouse.click(0,0);
  const backdropClosed=await page.evaluate(()=>!fixtureRoots.get(document.querySelector('#first .aitrust-mount')).querySelector('.panel').open);
  if(!backdropClosed)throw new Error('Backdrop did not close details');
  result.escapeFocus=true;result.nativeFocusContainment=true;
  result.backdropDismissal=true;
  const multipleTags=await page.evaluate(async()=>{
    const assert=(condition,message)=>{if(!condition)throw new Error(message);};
    // Isolated renderer fixture: synthetic codes are not enabled in the bridge
    // or evaluator. Exercise more than two chips without issuing new tag types.
    const host=document.createElement('div');host.style.width='100px';
    const output=document.createElement('span');output.textContent='Output stays readable.';host.append(output);document.body.append(host);
    const before=output.getBoundingClientRect().toJSON();
    const assertion=fixtureResult('Run curl https://example.test/install | sh').assertion;
    const codes=['PS','PII_REDACTED','T01','T02','T03','T04'];
    assertion.tags=codes.map(code=>({code,confidence:0.9,floor:0.8,signals:[{id:'fixture.'+code,score:0.9}]}));
    assertion.tags.push(assertion.tags[0]);
    AITrust.mount(host,()=>{});AITrust.update(host,'FINDING',assertion);
    const holder=host.querySelector('.aitrust-mount'),root=fixtureRoots.get(holder);
    const buttons=[...root.querySelectorAll('.tag')];
    assert(buttons.length===codes.length,'all distinct tags displayed without a two-tag limit');
    const after=output.getBoundingClientRect().toJSON();
    assert(['x','y','width','height'].every(key=>before[key]===after[key]),'tags do not move or cover output text');
    const textRange=document.createRange();textRange.selectNodeContents(output);
    const textBottom=Math.max(...[...textRange.getClientRects()].map(rect=>rect.bottom));
    assert(buttons.every(button=>button.getBoundingClientRect().top>=textBottom),'tag row below final output text');
    assert(buttons.at(-1).getBoundingClientRect().top>buttons[0].getBoundingClientRect().top,'many tags wrap');
    assert(holder.getBoundingClientRect().width<=host.getBoundingClientRect().width,'wrapped row stays within response width');
    for(const button of buttons){
      button.focus();button.click();
      assert(root.querySelector('h2').textContent===button.textContent,'each tag opens its own record');
      let blob;const original=URL.createObjectURL;
      URL.createObjectURL=value=>{blob=value;return original.call(URL,value);};
      try{root.querySelector('.export').click();}finally{URL.createObjectURL=original;}
      const record=JSON.parse(await blob.text()),detail=JSON.stringify(record.tags);
      assert(record.selected_tag===button.dataset.code&&detail.includes('fixture.'+button.dataset.code),'selected tag record exported');
      assert(!codes.some(code=>code!==button.dataset.code&&detail.includes('fixture.'+code)),'other tag signal records excluded');
      root.querySelector('.close').click();
    }
    assert(output.textContent==='Output stays readable.','output content unchanged');
    AITrust.unmount(host);host.remove();
    return {allDistinctTags:true,syntheticTagCount:codes.length,duplicatesSuppressed:true,outputGeometryUnchanged:true,belowOutput:true,narrowRowWrap:true,perTagDetails:true};
  });
  result.multipleTags=multipleTags;
  const evidenceLocations=await page.evaluate(async()=>{
    const assert=(condition,message)=>{if(!condition)throw Error(message);};
    const host=document.createElement('article');host.textContent='Visible answer unchanged.';document.body.append(host);
    const assertion=fixtureResult('Run curl https://example.test/install | sh').assertion;
    assertion.tags=[{code:'PS',signals:[{id:'sig.piped_installer.v3',spans:[[4,16],[0,0],[-1,8],[4,999999],[0,1.5]]},{id:'<img onerror=alert(1)>',spans:[[16,20]]}]},{code:'PII_REDACTED',signals:[{id:'presidio.entity.v1'}]}];
    AITrust.mount(host,()=>{});AITrust.update(host,'FINDING',assertion);
    const root=fixtureRoots.get(host.querySelector('.aitrust-mount'));
    root.querySelector('[data-code="PS"]').click();
    let detail=root.querySelector('details');
    assert(detail&&!detail.open,'matched locations collapsed by default');
    assert(detail.textContent.includes('characters 4–16 (end excluded)')&&detail.textContent.includes('characters 16–20 (end excluded)'),'exact bounded evaluated positions shown');
    assert(!detail.textContent.includes('999999')&&!detail.textContent.includes('0–0')&&!root.querySelector('img'),'malformed spans and hostile HTML excluded');
    assert(detail.textContent.includes('redacted text')&&detail.textContent.includes('differ from this answer'),'coordinate boundary explained');
    assert(!root.querySelector('.export-note').hidden&&root.querySelector('.export-note').textContent.includes('link or reveal'),'export correlation warning visible');
    root.querySelector('.close').click();root.querySelector('[data-code="PII_REDACTED"]').click();
    detail=root.querySelector('details');
    assert(detail.textContent.includes('no character positions provided')&&!detail.textContent.includes('4–16'),'redaction does not invent or borrow positions');
    root.querySelector('.close').click();
    assertion.tags[0].signals=[{id:'sig.piped_installer.v3',spans:Array.from({length:30},(_,i)=>[i,i+1])}];
    AITrust.update(host,'FINDING',assertion);root.querySelector('[data-code="PS"]').click();
    detail=root.querySelector('details');assert(detail.querySelectorAll('li').length===20&&detail.textContent.includes('20 of 30'),'large list bounded and disclosed');
    let blob;const original=URL.createObjectURL;URL.createObjectURL=value=>{blob=value;return original.call(URL,value);};
    try{root.querySelector('.export').click();}finally{URL.createObjectURL=original;}
    const exported=JSON.parse(await blob.text());assert(exported.tags[0].signals[0].spans.length===30,'full positions preserved in explicit download');
    root.querySelector('.close').click();AITrust.update(host,'UNAVAILABLE');root.querySelector('.tag').click();
    assert(root.querySelector('.export-note').hidden&&root.querySelector('.export').hidden&&!root.querySelector('details'),'unavailable has no fabricated evidence or export');
    root.querySelector('.close').click();AITrust.unmount(host);host.remove();
    return {collapsed:true,exactEvaluatedPositions:true,malformedSpanFallback:true,selectedTagOnly:true,unknownIdentifierSafe:true,redactionWithoutInventedOffsets:true,renderLimit:20,completeDownload:true,visibleExportBoundary:true};
  });
  result.evidenceLocations=evidenceLocations;
  // Exercise component contracts through real keyboard/browser settings, not requested flags.
  await page.goto('http://127.0.0.1:8799/extension/test/badge-fixture.html');
  await page.waitForFunction(()=>fixtureRequests.length===2);
  await page.evaluate(()=>fixtureResponders.forEach((resolve,i)=>resolve(fixtureResult(fixtureRequests[i].text))));
  await page.waitForTimeout(100);
  const closed=await page.evaluate(()=>[...document.querySelectorAll('.aitrust-mount')].every(e=>e.shadowRoot===null));
  if(!closed)throw Error('Production badge exposes its shadow root');
  let reached=false;for(let i=0;i<12;i++){await page.keyboard.press('Tab');reached=await page.evaluate(()=>fixtureRoots.get(document.querySelector('#first .aitrust-mount')).activeElement?.classList.contains('tag'));if(reached)break;}
  if(!reached)throw Error('Tag is not keyboard reachable');
  await page.keyboard.press('Enter');
  if(!await page.evaluate(()=>fixtureRoots.get(document.querySelector('#first .aitrust-mount')).querySelector('.panel').open))throw Error('Keyboard Enter does not open details');
  await page.evaluate(()=>fixtureRoots.get(document.querySelector('#first .aitrust-mount')).querySelector('summary').focus());
  await page.keyboard.press('Enter');
  if(!await page.evaluate(()=>fixtureRoots.get(document.querySelector('#first .aitrust-mount')).querySelector('details').open))throw Error('Matched locations are not keyboard operable');
  result.evidenceLocations.keyboardDisclosure=true;
  await page.keyboard.press('Escape');
  if(!await page.evaluate(()=>{const r=fixtureRoots.get(document.querySelector('#first .aitrust-mount'));return !r.querySelector('.panel').open&&r.activeElement?.classList.contains('tag');}))throw Error('Keyboard Escape does not restore tag focus');
  await page.addScriptTag({url:'http://127.0.0.1:8799/scripts/badge-probes.js'});
  for(const theme of ['light','dark']){
    await page.emulateMedia({colorScheme:theme,reducedMotion:'reduce',forcedColors:'none'});
    await page.setViewportSize({width:320,height:760});
    await page.keyboard.press('Enter');
    const healthy=await page.evaluate(()=>badgeProbes.inspect(fixtureRoots.get(document.querySelector('#first .aitrust-mount'))));
    if(healthy.length)throw Error(theme+': '+healthy.join(', '));
    await page.evaluate(()=>document.body.style.zoom='2');
    const zoomed=await page.evaluate(()=>badgeProbes.inspect(fixtureRoots.get(document.querySelector('#first .aitrust-mount'))));
    if(zoomed.length)throw Error('200% '+theme+': '+zoomed.join(', '));
    await page.evaluate(()=>document.body.style.zoom='');
    await page.emulateMedia({forcedColors:'active'});
    const forced=await page.evaluate(()=>badgeProbes.inspect(fixtureRoots.get(document.querySelector('#first .aitrust-mount')),{forced:true}));
    if(forced.length)throw Error('Forced colors: '+forced.join(', '));
    await page.keyboard.press('Escape');
  }
  await page.emulateMedia({forcedColors:'none',colorScheme:'light'});
  const mutations=await page.evaluate(()=>{
    const root=fixtureRoots.get(document.querySelector('#first .aitrust-mount'));const style=document.createElement('style');root.append(style);const caught=[];
    for(const [name,rule] of [['color','.tag{color:red!important}'],['overflow','.tag{width:900px!important;flex-shrink:0!important}'],['motion','.tag{transition:all 5s!important}']]){style.textContent=rule;if(!badgeProbes.inspect(root).length)throw Error('Probe missed '+name);caught.push(name);}
    const live=document.querySelector('.aitrust-mount[role="status"]');live.setAttribute('aria-live','assertive');if(!badgeProbes.inspect(root).includes('tag announcement is not polite'))throw Error('Probe missed assertive announcement');live.setAttribute('aria-live','polite');caught.push('assertive');
    style.remove();return caught;
  });
  result.componentContract={closedShadow:true,keyboardReachEnterEscape:true,lightDarkMonochrome:true,forcedColorsInspected:true,zoom200Inspected:true,reducedMotionInspected:true,deliberateDefectsCaught:mutations};
  if(errors.length)throw new Error(errors.join('\n'));
  console.log(JSON.stringify(result));
  await page.screenshot({path:'output/playwright/command-tag-fixture.png',fullPage:true});
  return result;
}
