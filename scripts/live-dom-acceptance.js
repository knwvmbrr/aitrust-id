async (page) => {
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('http://127.0.0.1:8799/extension/test/live-dom-fixture.html');
  await page.waitForFunction(()=>fixtureRequests.length===1);
  const result=await page.evaluate(async()=>{
    const assert=(value,message)=>{if(!value)throw new Error(message);};
    const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
    const host=document.querySelector('#observed'),identity=document.querySelector('#identity');
    const root=()=>fixtureRoots.get(host.querySelector('.aitrust-mount'));
    const text=fixtureRequests[0].text;
    assert(text.includes('/bin/bash -c')&&text.includes('Review the source first.'),'whole assistant body');
    assert(!/PRIVATE|Bash Copy Wrap|ChatGPT said:/.test(text),'prompt, controls, hidden text excluded');
    assert(text.includes('Install with:\n'),'block boundary preserved');
    assert(AITrustAdapter.responses().length===2,'both explicit assistant anchors supported');
    assert(fixtureRequests.length===1,'identity-less response never submitted');
    assert(!document.querySelector('#private-prompt').querySelector('.aitrust-mount'),'prompt never tagged');
    fixtureResponders[0](fixtureResult(text,'sig.remote_command_substitution.v2'));await pause(50);
    assert(root().querySelector('.status').textContent.includes('Command risk'),'modern body finding');
    root().querySelector('.check').click();const old=fixtureResponders.length-1;
    identity.setAttribute('data-chatgpt-selection-message-id','synthetic-response-2');
    // Resolve before observer's debounce. Identity alone must invalidate the result.
    fixtureResponders[old](fixtureResult(text));await pause(900);
    assert(!root().querySelector('.status').textContent.includes('Command risk'),'same text/new identity discards result');
    assert(fixtureRequests.length===3,'new identity evaluated once');
    fixtureResponders.at(-1)(fixtureResult(text));await pause(50);
    root().querySelector('.check').click();const navigationOld=fixtureResponders.length-1;
    history.pushState({},'', '/extension/test/changed-conversation');
    fixtureResponders[navigationOld](fixtureResult(text));
    dispatchEvent(new PopStateEvent('popstate'));await pause(900);
    assert(!root().querySelector('.status').textContent.includes('Command risk'),'navigation discards same-text result');
    fixtureResponders.at(-1)(fixtureResult(text));await pause(50);
    const turn=host.closest('[data-talvt-turn-state]');turn.setAttribute('data-talvt-turn-state','unknown-streaming-state');await pause(150);
    const count=fixtureRequests.length;root().querySelector('.check').click();await pause(50);
    assert(fixtureRequests.length===count,'manual check cannot bypass unfinished turn');
    turn.setAttribute('data-talvt-turn-state','complete');await pause(900);
    assert(fixtureRequests.length===count+1,'completion resumes evaluation');
    host.removeAttribute('data-markdown-text-style');await pause(150);
    assert(!host.querySelector('.aitrust-mount'),'lost assistant ownership removes badge');
    document.querySelector('#unidentified').removeAttribute('data-message-author-role');await pause(150);
    const captureRoot=[...document.querySelectorAll('.aitrust-mount')].map(node=>fixtureRoots.get(node)).find(Boolean);
    assert(captureRoot?.querySelector('.tag').getAttribute('aria-label').includes('Nothing on this page has been evaluated.'),'unsupported capture compact and explicit');
    return {observedAttributeStructure:true,syntheticContent:true,wholeBody:true,toolbarExcluded:true,promptExcluded:true,hiddenExcluded:true,identityRequired:true,sameTextIdentityRace:true,navigationRace:true,streamingGuard:true,lostRoleCleanup:true,unsupportedCaptureVisible:true,liveVendorExecution:false};
  });
  if(errors.length)throw new Error(errors.join('\n'));
  console.log(JSON.stringify(result));return result;
}
