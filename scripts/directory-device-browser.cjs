// Disposable-provider acceptance only. Never accepts real account credentials.
const fs=require('node:fs');
const {chromium}=require('playwright');
(async()=>{
 const input=JSON.parse(fs.readFileSync(0,'utf8'));
 if(input.synthetic_only!==true||!/^https:\/\/127\.0\.0\.1:18443\/realms\/directory_lab\/device$/.test(input.uri)||!/^lab_[a-z]+$/.test(input.username)||!/^[-A-Za-z0-9+/=]{43,44}$/.test(input.spki))throw Error('Disposable directory browser refused');
 const browser=await chromium.launch({channel:'chromium',headless:true,args:['--ignore-certificate-errors-spki-list='+input.spki]});
 try{
  const page=await browser.newPage();const outside=[];
  page.on('request',r=>{if(!r.url().startsWith('https://127.0.0.1:18443/')&&!r.url().startsWith('data:'))outside.push(true)});
  await page.goto(input.uri,{waitUntil:'domcontentloaded',timeout:20000});
  const code=page.locator('input[name="device_user_code"],input[name="user_code"]');await code.fill(input.code);await page.locator('input[type="submit"],button[type="submit"]').first().click();
  if(await page.locator('#username').count()){
   await page.locator('#username').fill(input.username);await page.locator('#password').fill(input.password);await page.locator('#kc-login').click();
  }
  const consent=page.locator('input[name="accept"],button[name="accept"]');
  if(await consent.count())await consent.first().click();
  await page.waitForFunction(()=>/success|complete|approved|signed in/i.test(document.body.innerText),null,{timeout:15000});
  if(outside.length)throw Error('Unexpected provider request');
  console.log(JSON.stringify({pass:true,synthetic_identity_only:true,pinned_lab_tls:true,outside_requests:0}));
 }finally{await browser.close()}
})().catch(()=>{console.error('Disposable provider browser failed');process.exitCode=1});
