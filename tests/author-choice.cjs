'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const c=require('../protocol/author-choice.cjs');
for(const action of ['use','observe'])test(action+' without a receipt or author export choice',()=>assert.equal(c.authorize(c.profile(),action,false),true));
for(const action of ['export','issue','endorse']){
 test(action+' declines without explicit choice',()=>assert.equal(c.authorize(c.profile(),action,false),false));
 test(action+' accepts explicit local choice',()=>assert.equal(c.authorize(c.profile(),action,true),true));
}
for(const [field,value] of [['receipt_required',true],['ordinary_use_without_receipt',false],['automatic_receipt',true],['automatic_upload',true],['receipt_required','false'],['version','author-choice/9.0.0'],['organization_override',{required:true}]])test('refuse '+field,()=>assert.throws(()=>c.authorize({...c.profile(),[field]:value},'observe',true)));
test('missing field refused',()=>{const p=c.profile();delete p.receipt_required;assert.throws(()=>c.inspect(p));});
test('policy must be an object',()=>{for(const p of [null,[],true,'optional'])assert.throws(()=>c.inspect(p));});
test('unknown action or truthy permission refused',()=>{assert.throws(()=>c.authorize(c.profile(),'submit'));assert.throws(()=>c.authorize(c.profile(),'issue','yes'));});
test('validated policy is immutable and separate from caller input',()=>{const p=c.profile(),v=c.inspect(p);p.automatic_receipt=true;assert.equal(v.automatic_receipt,false);assert(Object.isFrozen(v));});
