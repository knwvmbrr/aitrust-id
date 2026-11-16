// Checks rendered theme selection and every opaque camouflage color, not an
// average background: text and focus/control edges must survive each patch.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium,webkit} = require('playwright');
const {writeReport} = require('./execution-report.cjs');
const root = path.resolve(__dirname, '..');
const base = process.env.AITRUST_SITE_URL || 'http://127.0.0.1:5188';
const engine = process.env.AITRUST_THEME_ENGINE || 'chromium';
assert(['chromium','webkit'].includes(engine),'AITRUST_THEME_ENGINE must be chromium or webkit');
const themes = {
  light: {page:'#f3f1e7',panel:'#fffef8',foreground:'#20281e',secondary:'#53604b',control:'#72806a',patches:['#e1e4d3','#dce1ce','#e3ddc8']},
  dark: {page:'#11170f',panel:'#1c2419',foreground:'#f0f3e9',secondary:'#b8c3ab',control:'#879575',patches:['#172012','#222c1b','#2b3321']}
};
function luminance(hex) {
  const rgb = hex.slice(1).match(/../g).map(v=>parseInt(v,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);
  return rgb.reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
}
function contrast(a,b) {const values=[luminance(a),luminance(b)].sort((a,b)=>b-a);return (values[0]+.05)/(values[1]+.05);}
(async()=>{
  const svg=fs.readFileSync(path.join(root,'site/public/camo-q4.svg'),'utf8');
  assert(!/<(?:script|animate|foreignObject)\b/.test(svg),'Pattern must be inert and static');
  assert.equal((svg.match(/<g opacity="0\.3">/g)||[]).length,2,'Both variants must keep their patches at 30% opacity');
  const measurements={};
  for(const [mode,colors] of Object.entries(themes)){
    const backgrounds=[colors.page,colors.panel,...colors.patches];
    for(const color of [colors.page,...colors.patches])assert(svg.includes(color),'SVG color missing '+color);
    measurements[mode]={};
    for(const [name,floor] of [['foreground',4.5],['secondary',4.5],['control',3]]){
      const worst=Math.min(...backgrounds.map(bg=>contrast(colors[name],bg)));
      assert(worst>=floor,`${mode} ${name} has ${worst.toFixed(2)}:1 contrast`);
      measurements[mode][name]=Number(worst.toFixed(3));
    }
  }
  const browser=await ({chromium,webkit}[engine]).launch();
  try{
    const page=await browser.newPage({viewport:{width:390,height:844},colorScheme:'dark'});
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    await page.goto(base);await page.waitForFunction(()=>window.AITrustTheme);
    async function inspect(mode,preference){
      await page.evaluate(value=>window.AITrustTheme.setPreference(value),preference);
      const actual=await page.evaluate(()=>{
        const style=getComputedStyle(document.documentElement);
        return {page:style.getPropertyValue('--page').trim(),panel:style.getPropertyValue('--panel').trim(),foreground:style.getPropertyValue('--foreground').trim(),secondary:style.getPropertyValue('--secondary').trim(),control:style.getPropertyValue('--control-border').trim(),themeColor:document.querySelector('meta[name="theme-color"]')?.content,background:getComputedStyle(document.body).backgroundImage,overflow:document.documentElement.scrollWidth>innerWidth+1};
      });
      for(const key of ['page','panel','foreground','secondary','control'])assert.equal(actual[key],themes[mode][key],`${preference} ${key}`);
      assert.equal(actual.themeColor,themes[mode].page,'Browser chrome theme color '+preference);
      assert(actual.background.includes(`camo-q4.svg#${mode}`),'Wrong pattern variant '+preference);
      assert.equal(actual.overflow,false,'Horizontal overflow '+preference);
      await page.goto(base+'/#person/PS');
      const dialog=page.getByRole('dialog');await dialog.waitFor();
      assert.equal(await dialog.evaluate(el=>getComputedStyle(el).backgroundImage),'none','Reading panel must remain solid');
      await page.goto(base);
    }
    await inspect('light','light');await inspect('dark','dark');await inspect('dark','system');
    await page.emulateMedia({colorScheme:'light'});await inspect('light','system');
    await page.emulateMedia({forcedColors:'active'});
    assert.equal(await page.evaluate(()=>getComputedStyle(document.body).backgroundImage),'none','Forced colors must remove pattern');
    assert.equal((await page.request.get(base+'/camo-q4.svg')).status(),200,'Pattern asset unavailable');
    assert.deepEqual(errors,[]);
    const report={captured_at:new Date().toISOString(),pass:true,engine,season:'2026-Q4',background_patch_opacity:0.3,contrast_bound:'conservative opaque-patch lower bound',base,worst_case_contrast:measurements,explicit_light_dark:true,system_light_dark:true,solid_reading_panels:true,forced_colors_pattern_removed:true,viewport:{width:390,height:844},physical_device:false,full_wcag_conformance_asserted:false};
    writeReport(process.env.AITRUST_SEASONAL_REPORT||'output/verification/seasonal-theme.json',report);
    console.log(JSON.stringify(report));
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
