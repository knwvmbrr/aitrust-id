#!/usr/bin/env node
// Actual built HTML: run after build:site. No ranking or indexing claim follows.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import {origin,escapeHTML,tagPath,tagDescription} from '../site/scripts/seo.mjs';
import {allTags} from '../site/src/catalog.js';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const dist=path.resolve(process.argv[2]||path.join(root,'site/dist'));
const sitemap=fs.readFileSync(path.join(dist,'sitemap.xml'),'utf8');
const urls=[...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(match=>match[1]);
assert.ok(urls.length>allTags.length,'Sitemap missing reference/policy pages');
assert.equal(new Set(urls).size,urls.length,'Duplicate sitemap URL');
const titles=new Set(),descriptions=new Set();
for(const url of urls){
 const parsed=new URL(url);
 assert.equal(parsed.origin,origin,'Foreign canonical in sitemap');
 assert.ok(!parsed.hash&&!parsed.search&&parsed.pathname.endsWith('/'),'Unstable sitemap URL');
 const html=fs.readFileSync(path.join(dist,parsed.pathname,'index.html'),'utf8');
 const head=html.match(/<head>([\s\S]*?)<\/head>/)?.[1];assert.ok(head,'Missing head: '+url);
 assert.equal((head.match(/rel="canonical"/g)||[]).length,1,'Canonical count: '+url);
 assert.ok(head.includes(`rel="canonical" href="${url}"`),'Wrong canonical: '+url);
 assert.ok(head.includes('content="index,follow,max-image-preview:large"'),'Unexpected indexing directive: '+url);
 assert.doesNotMatch(head,/noindex|nofollow/,'Excluded sitemap page: '+url);
 const title=head.match(/<title>([^<]+)<\/title>/)?.[1],description=head.match(/<meta name="description" content="([^"]+)"/)?.[1];
 assert.ok(title&&!titles.has(title),'Missing/duplicate title: '+url);titles.add(title);
 assert.ok(description&&!descriptions.has(description),'Missing/duplicate description: '+url);descriptions.add(description);
 const json=head.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)?.[1];
 assert.equal(JSON.parse(json)['@context'],'https://schema.org','Invalid structured data: '+url);
 assert.ok(head.includes(`property="og:url" content="${url}"`),'Wrong sharing URL: '+url);
}
for(const tag of allTags){
 const html=fs.readFileSync(path.join(dist,tagPath(tag),'index.html'),'utf8');
 const encoded=escapeHTML(tagDescription(tag));
 assert.ok(html.includes(`<meta name="description" content="${encoded}"`),'Stale tag metadata: '+tag.id);
 assert.ok(html.includes(`<meta property="og:description" content="${encoded}"`),'Stale tag social summary: '+tag.id);
 const reference=fs.readFileSync(path.join(dist,'tags/index.html'),'utf8');
 assert.ok(reference.includes(`href="${tagPath(tag)}"`),'Tag not linked from reference index: '+tag.id);
}
const robots=fs.readFileSync(path.join(dist,'robots.txt'),'utf8');
assert.match(robots,/User-agent: \*\s+Allow: \//);
assert.ok(robots.includes(`Sitemap: ${origin}/sitemap.xml`));
const guidePath='/reference/operate/';
assert.ok(urls.includes(origin+guidePath),'Search guide missing from sitemap');
const guide=fs.readFileSync(path.join(dist,guidePath,'index.html'),'utf8');
assert.match(guide,/<title>Check AI Commands on Your Phone or Computer \| AI Trust ID<\/title>/);
assert.match(guide,/<h2>Check an answer from your phone<\/h2>/);
assert.match(guide,/<a href="\/#person\/PS">Open the free PS preview<\/a>/);
assert.match(guide,/<a href="\/tags\/ps\/">PS evidence page<\/a>/);
const ps=fs.readFileSync(path.join(dist,'tags/ps/index.html'),'utf8');
assert.match(ps,/<a href="\/reference\/operate\/">Check an AI answer on your phone or computer<\/a>/);
console.log(JSON.stringify({pass:true,canonical_pages:urls.length,tag_summaries:allTags.length,phone_guide_linked:true,scope:'Built HTML metadata, static tag discovery and declared crawler policy. Actual indexing/ranking unmeasured.'},null,2));
