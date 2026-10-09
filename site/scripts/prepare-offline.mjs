import {readFile,writeFile,readdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import sharp from 'sharp';
const dist=new URL('../dist/',import.meta.url);
for(const size of [192,512]){
 const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 72 72"><rect width="72" height="72" rx="12" fill="#f7f8f6"/><g transform="translate(12 12)" fill="none" stroke="#202723"><path d="M9 7h22l10 10v20a4 4 0 0 1-4 4H9a4 4 0 0 1-4-4V11a4 4 0 0 1 4-4Z" stroke-width="2.5"/><circle cx="31" cy="17" r="2.5" stroke-width="2"/><path d="M14 25h16M14 31h10" stroke-width="2.5" stroke-linecap="round"/></g></svg>`;
 await sharp(Buffer.from(svg)).png().toFile(fileURLToPath(new URL(`app-icon-${size}.png`,dist)));
}
await writeFile(new URL('manifest.webmanifest',dist),JSON.stringify({id:'/',name:'AI TRUST ID',short_name:'AI TRUST ID',start_url:'/#person/PS',scope:'/',display:'standalone',background_color:'#f7f8f6',theme_color:'#f7f8f6',icons:[192,512].map(size=>({src:`/app-icon-${size}.png`,sizes:`${size}x${size}`,type:'image/png',purpose:'any maskable'}))},null,2));
let html=await readFile(new URL('index.html',dist),'utf8');html=html.replace('</head>','<link rel="manifest" href="/manifest.webmanifest"/><link rel="apple-touch-icon" href="/app-icon-192.png"/></head>');await writeFile(new URL('index.html',dist),html);
async function list(directory,prefix){const files=[];for(const entry of await readdir(directory,{withFileTypes:true})){const name=prefix+entry.name;if(entry.isDirectory())files.push(...await list(new URL(entry.name+'/',directory),name+'/'));else files.push(name);}return files;}
const assets=['/','/theme.js','/favicon.svg','/manifest.webmanifest','/app-icon-192.png','/app-icon-512.png','/reference/independent-review.md'];
for(const name of ['assets','device','device-licenses','fonts'])assets.push(...await list(new URL(name+'/',dist),'/'+name+'/'));
const hash=createHash('sha256');let bytes=0;
for(const asset of assets.sort()){const data=await readFile(new URL(asset==='/'?'index.html':asset.slice(1),dist));hash.update(asset).update(data);bytes+=data.length;}
const version=hash.digest('hex');
// Explicit allowlist only: no text-bearing URLs, POSTs, private records or reviews.
const source=`const NAME=${JSON.stringify('aitrust-id-offline-'+version)},ASSETS=${JSON.stringify(assets)};
self.addEventListener('install',event=>event.waitUntil((async()=>{try{const cache=await caches.open(NAME);await cache.addAll(ASSETS);}catch(error){await caches.delete(NAME);throw error;}})()));
self.addEventListener('activate',event=>event.waitUntil((async()=>{for(const name of await caches.keys())if(name.startsWith('aitrust-id-offline-')&&name!==NAME)await caches.delete(name);await self.clients.claim();})()));
self.addEventListener('fetch',event=>{const url=new URL(event.request.url);if(event.request.method!=='GET'||url.origin!==self.location.origin||url.search||!ASSETS.includes(url.pathname))return;event.respondWith((async()=>{const cache=await caches.open(NAME);return await cache.match(url.pathname)||fetch(event.request);})());});
`;
await writeFile(new URL('offline-worker.js',dist),source);
await writeFile(new URL('offline-release.json',dist),JSON.stringify({format:'ai-trust-id-offline-assets/v1',version,public_asset_count:assets.length,bytes,assets},null,2));
console.log(`Offline allowlist: ${assets.length} public assets, ${bytes} bytes; no user data cached.`);
