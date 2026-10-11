// One immutable build-bound scope. No user data or live API participates.
import scopeUrl from './public-scope.json?url';
import manifest from './scope-manifest.json';
let current;
let pending;
async function readScope() {
  const controller = new AbortController();
  const timer = setTimeout(()=>controller.abort(), 8000);
  try {
    const response = await fetch(scopeUrl, {signal:controller.signal,
      credentials:'omit', referrerPolicy:'no-referrer', cache:'force-cache'});
    if (!response.ok || !response.body) throw Error('Scope unavailable');
    const reader = response.body.getReader();
    const pieces = []; let size = 0;
    try {
      for (;;) {
        const {done,value} = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > manifest.bytes) throw Error('Scope size mismatch');
        pieces.push(value);
      }
    } catch (error) { await reader.cancel().catch(()=>{}); throw error; }
    finally { reader.releaseLock(); }
    if (size !== manifest.bytes) throw Error('Scope size mismatch');
    const bytes = new Uint8Array(size); let offset = 0;
    for (const piece of pieces) { bytes.set(piece,offset); offset += piece.length; }
    const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))]
      .map(value=>value.toString(16).padStart(2,'0')).join('');
    if (hash !== manifest.sha256) throw Error('Scope version mismatch');
    const data = JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
    if (JSON.stringify(data.records.map(record=>record.id)) !== JSON.stringify(manifest.ids))
      throw Error('Scope records mismatch');
    return data;
  } finally { clearTimeout(timer); }
}
export function loadScope() {
  if (current) return Promise.resolve(current);
  if (!pending) pending = readScope().then(data => {
    current = data;
    pending = undefined;
    return current;
  }, error => {
    pending = undefined;
    throw error;
  });
  return pending;
}
