const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {parseHeaders,headersFor}=require('../scripts/static-headers.cjs');
const rules=parseHeaders(fs.readFileSync(path.join(__dirname,'../site/public/_headers'),'utf8'));
test('homepage retains security headers without attachment behavior',()=>{const h=headersFor(rules,'/');assert(h['content-security-policy']);assert.equal(h['content-disposition'],undefined);assert.equal(h['content-type'],undefined);});
test('only exact editor download route receives attachment headers',()=>{const h=headersFor(rules,'/reference/offline-editor.html');assert(h['content-disposition'].startsWith('attachment;'));assert.equal(h['content-type'],'application/octet-stream');assert(h['content-security-policy']);assert.equal(headersFor(rules,'/reference/offline-editor.html/other')['content-disposition'],undefined);});
test('malformed and duplicate header rules are refused',()=>{for(const raw of ['  Name: value','/path\n  bad','/path\n  X: a\n  x: b','/path*other\n  X: a'])assert.throws(()=>parseHeaders(raw));});
test('route rules cannot leak to other files',()=>{assert.equal(headersFor(rules,'/assets/site.js')['content-disposition'],undefined);assert.equal(headersFor(rules,'/policies/privacy/')['content-disposition'],undefined);});
