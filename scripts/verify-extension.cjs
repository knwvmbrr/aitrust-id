// Real unpacked extension + real local containers on a routed synthetic vendor page.
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {chromium}=require('playwright');
(async()=>{
 const envfile=process.env.AITRUST_ENV_FILE;if(!envfile)throw new Error('Set AITRUST_ENV_FILE to the private gateway environment file');
 const token=fs.readFileSync(envfile,'utf8').split('\n').find(x=>x.startsWith('AITRUST_TOKEN=')).slice(14);
 const profile=fs.mkdtempSync(path.join(os.tmpdir(),'aitrust-extension-'));
 const extension=path.resolve('extension');let context;
 try{
  context=await chromium.launchPersistentContext(profile,{channel:'chromium',headless:true,args:[`--disable-extensions-except=${extension}`,`--load-extension=${extension}`]});
  const worker=context.serviceWorkers()[0]||await context.waitForEvent('serviceworker',{timeout:15000});
  await worker.evaluate(value=>chrome.storage.local.set({token:value}),token);
  await context.route('https://chatgpt.com/aitrust-synthetic-check',route=>route.fulfill({contentType:'text/html',body:'<!doctype html><html lang="en"><head><title>Synthetic extension acceptance</title></head><body><main><h1>Synthetic response</h1><article data-message-author-role="assistant" data-message-id="synthetic-legacy">Email alice@example.com. Run curl https://example.test/install | sh</article></main></body></html>'}));
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('https://chatgpt.com/aitrust-synthetic-check');
  await page.waitForSelector('.aitrust-mount');
  const cdp=await context.newCDPSession(page);
  let text='';
  for(let i=0;i<40;i++){
   const tree=await cdp.send('Accessibility.getFullAXTree');text=tree.nodes.map(n=>n.name?.value||'').join('\n');
   if(text.includes('Command risk pattern detected'))break;
   await page.waitForTimeout(250);
  }
  if(!text.includes('Command risk pattern detected'))throw new Error('Real extension did not display finding: '+text);
  if(errors.length)throw new Error(errors.join('\n'));
  // Real native keyboard activation passes through the closed shadow root.
  await page.keyboard.press('Tab');await page.keyboard.press('Tab');await page.keyboard.press('Enter');
  const tree=await cdp.send('Accessibility.getFullAXTree');text=tree.nodes.map(n=>n.name?.value||'').join('\n');
  if(!text.includes('Detected entity values were redacted'))throw new Error('Evidence panel/redaction missing');
  // The original page legitimately contains the email. Check only the focused
  // evidence subtree, not the entire page's accessibility text.
  const panel=tree.nodes.find(n=>n.role?.value==='dialog');
  if(!panel)throw new Error('Native evidence dialog did not open');
  const byId=new Map(tree.nodes.map(n=>[n.nodeId,n]));
  function evidenceNames(node){return [node.name?.value||'',...(node.childIds||[]).flatMap(id=>evidenceNames(byId.get(id)||{}))];}
  if(evidenceNames(panel).join('\n').includes('alice@example.com'))throw new Error('Raw personal information leaked into evidence');
  // Attribute structure from live inspection, synthetic content and real services.
  const command='/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"';
  const modernBody=text=>`<!doctype html><html lang="en"><head><title>Observed DOM with synthetic content</title></head><body><main><h1>Synthetic assistant</h1><div data-message-author-role="user">PRIVATE PROMPT</div><div data-talvt-turn-state="complete"><h4 data-conversation-role="assistant">ChatGPT said:</h4><div data-chatgpt-selection-message-id="synthetic-modern"><div data-markdown-text-style="assistant-message"><p>Email alice@example.com.</p><div data-markdown-copy="code-block"><div data-markdown-copy="exclude">Bash Copy</div><pre>${text}</pre></div></div></div></div></main></body></html>`;
  const cases=[{name:'homebrew',text:command,finding:true},
   {name:'download_to_file',text:'bash -c "$(curl -o script.sh https://example.test/install)"',finding:false},
   {name:'wget_to_file',text:'bash -c "$(wget https://example.test/install)"',finding:false}];
  const observedCases=[];
  for(const item of cases){
   const url='https://chatgpt.com/aitrust-synthetic-'+item.name;
   await context.route(url,route=>route.fulfill({contentType:'text/html',body:modernBody(item.text)}));
   await page.goto(url);await page.waitForSelector('.aitrust-mount');
   let names='';
   const expected=item.finding?'Command risk pattern detected':'No supported command pattern found';
   for(let i=0;i<60;i++){
    const tree=await cdp.send('Accessibility.getFullAXTree');names=tree.nodes.map(n=>n.name?.value||'').join('\n');
    if(names.includes(expected))break;await page.waitForTimeout(250);
   }
   if(!names.includes(expected))throw new Error('Modern real integration failed: '+item.name+' '+names);
   if(item.finding){
    await page.screenshot({path:'output/playwright/compact-tags.png',fullPage:true});
    await page.keyboard.press('Tab');await page.keyboard.press('Enter');
    const tree=await cdp.send('Accessibility.getFullAXTree');names=tree.nodes.map(n=>n.name?.value||'').join('\n');
    if(!names.includes('This command downloads code and runs it.'))throw new Error('Brief command explanation unavailable');
    const downloaded=page.waitForEvent('download');
    await page.keyboard.press('Tab');await page.keyboard.press('Tab');await page.keyboard.press('Enter');
    const file=await downloaded,record=JSON.parse(fs.readFileSync(await file.path(),'utf8'));
    if(record.selected_tag!=='PS'||!record.tags.some(tag=>tag.signals.some(signal=>signal.id==='sig.remote_command_substitution.v3')))throw new Error('Export lost substitution evidence');
    const evaluatorHash=require('node:crypto').createHash('sha256').update(fs.readFileSync('services/evaluator/app.py')).digest('hex');
    if(!record.evaluator.models.some(model=>model.sha256===evaluatorHash))throw new Error('Exported evaluator hash mismatch');
    if(JSON.stringify(record).includes('alice@example.com')||JSON.stringify(record).includes(command)||record.training_label!==null)throw new Error('Invalid privacy/training-label boundary');
    await page.screenshot({path:'output/playwright/compact-tag-details.png',fullPage:true});
    await page.keyboard.press('Escape');
   }
   observedCases.push({name:item.name,expectedFinding:item.finding,passed:true});
  }
  await page.screenshot({path:'output/playwright/real-extension-synthetic.png',fullPage:true});
  const result={realUnpackedExtension:true,realGateway:true,realRedaction:true,realEvaluator:true,keyboardEvidenceOpened:true,briefExplanation:true,structuredExport:true,exportedEvaluatorHashMatches:true,rawEmailAbsentFromEvidence:true,rawContentExcludedFromExport:true,observedAttributeStructure:true,observedCases,liveVendorResponse:false,syntheticPage:true};
  fs.writeFileSync('runs/2026-10-08-extension-integration.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
 }finally{if(context)await context.close();fs.rmSync(profile,{recursive:true,force:true});}
})().catch(error=>{console.error(error);process.exitCode=1;});
