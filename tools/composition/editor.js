/* Attached only to this editor after explicit Start. No global keyboard capture. */
'use strict';
const observation = AITrustComposition.create();
const field = document.querySelector('#editor');
const mode = document.querySelector('#mode');
const output = document.querySelector('#summary');
const status = document.querySelector('#status');
const start = document.querySelector('#start');
const pause = document.querySelector('#pause');
const download = document.querySelector('#download');
let previous = '', before = null, timer = null, generation = 0;
const now = () => performance.now();
function paint() {
  const record = observation.snapshot();
  output.textContent = JSON.stringify(record, null, 2);
  status.textContent = record.status === 'observing' ? 'Observing this editor only.' : record.status === 'not_started' ? 'Not started. Nothing is observed.' : 'Stopped. Reset to start a new session.';
  field.readOnly = record.status !== 'observing'; start.disabled = record.status !== 'not_started';
  pause.disabled = record.status !== 'observing'; mode.disabled = record.status !== 'not_started';
  download.disabled = record.status !== 'paused' && record.status !== 'limit_reached';
  document.querySelector('#download-text').disabled = download.disabled;
  if (record.status !== 'observing' && timer) { clearTimeout(timer); timer = null; }
}
function event(e) {
  try { observation.event(e); } catch (_) {
    observation.pause(now(), 'invalid_or_unsupported_input');
    status.textContent = 'Input could not be measured safely. Reset to try again.';
  }
  paint();
}
start.addEventListener('click', () => {
  generation++;
  observation.start(now(), mode.value); field.focus();
  observation.event({kind:'focus', at:now(), value:true});
  timer = setTimeout(() => { observation.pause(now(), 'limit_reached'); paint(); }, 1800000);
  paint();
});
pause.addEventListener('click', () => { observation.pause(now()); paint(); });
document.querySelector('#reset').addEventListener('click', () => {
  generation++;
  if (timer) clearTimeout(timer); timer = null;
  observation.reset(); field.value = ''; previous = ''; before = null; paint();
});
field.addEventListener('keydown', e => event({kind:'keyDown',at:now(),code:e.code || 'Unknown',trusted:e.isTrusted && !!e.code,repeat:e.repeat}));
field.addEventListener('keyup', e => event({kind:'keyUp',at:now(),code:e.code || 'Unknown',trusted:e.isTrusted && !!e.code}));
field.addEventListener('compositionstart', () => event({kind:'composition',at:now()}));
field.addEventListener('select', () => event({kind:'caret',at:now(),position:field.selectionStart}));
field.addEventListener('focus', () => event({kind:'focus',at:now(),value:true}));
field.addEventListener('blur', () => event({kind:'focus',at:now(),value:false}));
document.addEventListener('visibilitychange', () => event({kind:'visibility',at:now(),value:!document.hidden}));
field.addEventListener('beforeinput', e => {
  before = {start:field.selectionStart,end:field.selectionEnd,type:e.inputType};
});
field.addEventListener('input', e => {
  const next = field.value;
  // Common prefix/suffix determines the actual observed edit, including browser replacements.
  let position = 0;
  while (position < previous.length && position < next.length && previous[position] === next[position]) position++;
  let tail = 0;
  while (tail < previous.length-position && tail < next.length-position && previous[previous.length-1-tail] === next[next.length-1-tail]) tail++;
  let removed = previous.length-position-tail, added = next.length-position-tail;
  const type = before?.type || e.inputType || '';
  if (before) {
    const selected = before.end - before.start;
    const deleted = Math.max(0, previous.length - next.length);
    const candidate = type === 'deleteContentBackward' && !selected ? before.start - deleted : before.start;
    const candidateRemoved = type.startsWith('delete') ? Math.max(selected, deleted) : selected;
    const candidateAdded = next.length - previous.length + candidateRemoved;
    if (candidate >= 0 && candidateAdded >= 0 && previous.slice(0,candidate) === next.slice(0,candidate) && previous.slice(candidate+candidateRemoved) === next.slice(candidate+candidateAdded)) {
      position = candidate; removed = candidateRemoved; added = candidateAdded;
    }
  }
  const input = e.isComposing || type.includes('Composition') ? 'composition' : type === 'insertFromPaste' ? 'paste' : type === 'insertReplacementText' ? 'replacement' : ['insertText','insertLineBreak','deleteContentBackward','deleteContentForward'].includes(type) ? 'keyboard' : 'unknown';
  event({kind:'edit',at:now(),before:previous.length,after:next.length,position,removed,added,input});
  previous = next; before = null;
});
function save(blob, name) {
  const url = URL.createObjectURL(blob), link = document.createElement('a');
  link.href = url; link.download = name; document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
document.querySelector('#download-text').addEventListener('click', () => {
  if (!['paused','limit_reached'].includes(observation.snapshot().status)) return;
  save(new Blob([new TextEncoder().encode(field.value)],{type:'text/plain;charset=utf-8'}),'artifact.txt');
});
download.addEventListener('click', async () => {
  const record = observation.snapshot();
  const capturedGeneration = generation;
  if (!['paused','limit_reached'].includes(record.status)) return;
  let digest;
  try { digest = await crypto.subtle.digest('SHA-256',new TextEncoder().encode(field.value)); }
  catch (_) { status.textContent = 'This browser cannot bind the summary to your text. No download was created.'; return; }
  if (capturedGeneration !== generation) return;
  const artifact_sha256 = Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
  const blob = new Blob([JSON.stringify({...record, artifact_sha256, artifact_encoding:'UTF-8; exact editor value; no normalization', source_sha256:document.querySelector('meta[name="method-sha256"]').content},null,2)+'\n'], {type:'application/json'});
  save(blob, 'composition-observation.json');
});
paint();
