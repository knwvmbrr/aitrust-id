import test from 'node:test';
import assert from 'node:assert/strict';
import {allTags} from '../site/src/catalog.js';
import {metadata,tagDescription,siteTitle,siteDescription} from '../site/scripts/seo.mjs';

const tag=id=>allTags.find(item=>item.id===id);
const graph=head=>JSON.parse(head.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1])['@graph'];

test('PS snippet describes the bounded job and current on-device preview',()=>{
 const description=tagDescription(tag('PS'));
 assert.match(description,/commands that run downloaded or encoded code/);
 assert.match(description,/Works here: PS command-pattern preview/);
 assert.doesNotMatch(description,/certified|safe to run|scam detector|accuracy guarantee/i);
});
test('local privacy setup is not described as a website capability',()=>{
 assert.match(tagDescription(tag('PII_REDACTED')),/Local setup required\. PII does not run in this website checker/);
});
test('unavailable adopted tags do not appear as available development checkers',()=>{
 for(const id of ['FI','IV','FA','PA','UNK','PII_OUTBOUND']){
  const description=tagDescription(tag(id));
  assert.match(description,/Planned · No checker available yet/,id);
  assert.doesNotMatch(description,/Development preview|Works here/,id);
 }
});
test('HP discovery distinguishes detail and uncertainty-word exploration from tag release',()=>{
 const description=tagDescription(tag('HP'));
 assert.equal(tag('HP').status,'Coming Soon');
 assert.equal(tag('HP').formalName,'Hallucination possible');
 assert.match(description,/Look more closely at details and wording/);
 assert.match(description,/Planned tag · Detail and uncertainty-word previews available/);
 assert.doesNotMatch(description,/No checker|Works here|certified|independently validated|detects hallucinations|verifies facts|accuracy guarantee/i);
});
test('MT discovery distinguishes its wording-method preview from tag release',()=>{
 const description=tagDescription(tag('MT'));
 assert.equal(tag('MT').status,'Coming Soon');
 assert.match(description,/Planned tag · Wording-method preview available/);
 assert.doesNotMatch(description,/No checker|Works here|certified|independently validated|detects manipulation|accuracy guarantee/i);
});
test('NF discovery distinguishes reference wording comparison from tag release',()=>{
 const description=tagDescription(tag('NF'));
 assert.equal(tag('NF').status,'Coming Soon');
 assert.match(description,/Compare a claim with a passage you choose/);
 assert.match(description,/Planned tag · Reference comparison preview available/);
 assert.doesNotMatch(description,/No checker|Works here|certified|independently validated|verifies facts|accuracy guarantee/i);
});
test('working organization tools are distinguished from unbuilt hosted offerings',()=>{
 for(const id of ['fleet','host','audit','sso'])assert.match(tagDescription(tag(id)),/Local software available\. No team service is running/,id);
 for(const id of ['support','proprietary'])assert.match(tagDescription(tag(id)),/Planned offering\. No team service is running/,id);
});
test('all catalogue summaries are unique, readable and bounded to their offering',()=>{
 const descriptions=allTags.map(tagDescription);
 assert.equal(new Set(descriptions).size,allTags.length);
 for(const [i,text] of descriptions.entries()){
  assert.ok(text.startsWith(allTags[i].code+' — '+allTags[i].name+'. '));
  assert.ok(text.length<400,'Unexpectedly unbounded snippet');
  assert.doesNotMatch(text,/undefined|\[object Object\]/);
 }
});
test('homepage discovery text explains the actual free check without an accuracy claim',()=>{
 assert.match(siteTitle,/Free, Open-Source AI Output Checks/);
 assert.match(siteDescription,/supported command-risk patterns/);
 assert.match(siteDescription,/PS preview/);
 assert.doesNotMatch(siteDescription,/detects all|certified|guaranteed|independently validated/i);
});
test('individual guides and policies are WebPages, not collections',()=>{
 assert.equal(graph(metadata({path:'/reference/operate/'}))[1]['@type'],'WebPage');
 assert.equal(graph(metadata({path:'/policies/privacy/'}))[1]['@type'],'WebPage');
 assert.equal(graph(metadata({path:'/'}))[1]['@type'],'CollectionPage');
 assert.equal(graph(metadata({path:'/tags/'}))[1]['@type'],'CollectionPage');
});
test('metadata preserves text without allowing script or attribute injection',()=>{
 const value='"/><script>alert(1)</script>&\u2028\u2029';
 const head=metadata({title:value,description:value});
 assert.equal((head.match(/<script /g)||[]).length,1);
 assert.ok(!head.includes('<script>alert(1)</script>'));
 assert.equal(graph(head)[1].description,value);
 assert.match(head,/&quot;\/&gt;&lt;script&gt;/);
});
