// Exact-byte response authentication. The operator selects a key independently.
(() => {
 const PROFILE='loopback-response/p256-sha256/v1',encoder=new TextEncoder();
 const hex=bytes=>Array.from(new Uint8Array(bytes),n=>n.toString(16).padStart(2,'0')).join('');
 function decode(value,length){
  if(typeof value!=='string'||value.length!==Math.ceil(length*4/3)||!/^[A-Za-z0-9_-]+$/.test(value))throw Error('Invalid public encoding');
  const bytes=Uint8Array.from(atob(value.replace(/-/g,'+').replace(/_/g,'/')),c=>c.charCodeAt(0));
  if(bytes.length!==length||btoa(String.fromCharCode(...bytes)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'')!==value)throw Error('Invalid public encoding');
  return bytes;
 }
 async function selectedKey(value){
  if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).sort().join(',')!=='key_id,profile,public_key'||value.profile!==PROFILE||!(/^[a-f0-9]{64}$/).test(value.key_id))throw Error('Select a gateway public key');
  const raw=decode(value.public_key,65);if(raw[0]!==4||hex(await crypto.subtle.digest('SHA-256',raw))!==value.key_id)throw Error('Invalid gateway key fingerprint');
  const key=await crypto.subtle.importKey('raw',raw,{name:'ECDSA',namedCurve:'P-256'},false,['verify']);
  return Object.freeze({key,key_id:value.key_id,public_key:value.public_key,profile:PROFILE});
 }
 async function verify(response,bytes,nonce,requestBody,selected){
  if(!/^[a-f0-9]{64}$/.test(nonce)||response.headers.get('X-AITrust-Profile')!==PROFILE||response.headers.get('X-AITrust-Key')!==selected.key_id)throw Error('Untrusted gateway response');
  const signature=decode(response.headers.get('X-AITrust-Signature'),64);
  const hash=hex(await crypto.subtle.digest('SHA-256',encoder.encode(requestBody)));
  const prefix=encoder.encode(PROFILE+'\n'+nonce+'\n'+hash+'\n'),data=new Uint8Array(prefix.length+bytes.length);data.set(prefix);data.set(bytes,prefix.length);
  if(!await crypto.subtle.verify({name:'ECDSA',hash:'SHA-256'},selected.key,signature,data))throw Error('Gateway response signature did not verify');
 }
 const nonce=()=>hex(crypto.getRandomValues(new Uint8Array(32)));
 globalThis.AITrustTransport=Object.freeze({PROFILE,selectedKey,verify,nonce});
})();
