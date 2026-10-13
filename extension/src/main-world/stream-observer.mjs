// Inactive developer component. No fetch patch, window message, or vendor adapter.
export const PROFILE = 'aitrust.assistant-text.v1';
export const LIMITS = Object.freeze({ bytes: 65536, chunks: 512, line: 8192,
  events: 128, text: 8000, milliseconds: 2000 });

const safeString = (value) => typeof value === 'string' &&
  !/[\u0000\uD800-\uDFFF]/u.test(value.replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]/g, ''));

// Closed flat JSON grammar: duplicate keys and nested/unknown values are refused.
function eventRecord(source) {
  let offset = 0;
  const string = /"(?:[^"\\\x00-\x1f]|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*"/y;
  const space = () => { while (/[ \t\r\n]/.test(source[offset] || 'X')) offset++; };
  const token = () => {
    string.lastIndex = offset;
    const match = string.exec(source);
    if (!match) throw new Error('invalid');
    offset = string.lastIndex;
    const value = JSON.parse(match[0]);
    if (!safeString(value)) throw new Error('invalid');
    return value;
  };
  const expect = (character) => { space(); if (source[offset++] !== character) throw new Error('invalid'); };
  const record = Object.create(null);
  expect('{');
  for (;;) {
    space(); const key = token(); expect(':'); space();
    if (Object.hasOwn(record, key) || !['profile', 'message_id', 'role', 'delta', 'done'].includes(key)) throw new Error('invalid');
    let value;
    if (source[offset] === '"') value = token();
    else if (source.startsWith('true', offset)) { value = true; offset += 4; }
    else if (source.startsWith('false', offset)) { value = false; offset += 5; }
    else throw new Error('invalid');
    record[key] = value;
    space(); if (source[offset] === '}') { offset++; break; } expect(',');
  }
  space();
  if (offset !== source.length || Object.keys(record).length !== 5 ||
      record.profile !== PROFILE || record.role !== 'assistant' ||
      typeof record.message_id !== 'string' || !/^[A-Za-z0-9_-]{1,64}$/.test(record.message_id) ||
      !safeString(record.delta) || typeof record.done !== 'boolean') throw new Error('invalid');
  return record;
}

/** Observe only a caller-owned synthetic profile. Original Response is returned unchanged.
 * Clone buffering belongs to the browser; these are observer limits, not a heap guarantee.
 * Completion text is explicit caller output. Refusal/cancellation never returns partial text.
 */
export function observeAssistantStream(response, requestedLimits = {}) {
  let finish;
  const completion = new Promise((resolve) => { finish = resolve; });
  let settled = false, reader, timer, buffer = '', text = '', eventData = null;
  const settle = (result) => {
    if (settled) return;
    settled = true; clearTimeout(timer); buffer = ''; text = ''; eventData = null;
    // tee cancellation may wait for the other branch; do not await it here.
    if (reader) {
      try { Promise.resolve(reader.cancel()).catch(() => {}); } catch { /* unavailable reader */ }
      try { reader.releaseLock(); } catch { /* outstanding read finishes later */ }
    }
    finish(Object.freeze(result));
  };
  const refuse = (reason) => settle({ status: 'unavailable', reason });
  const observation = Object.freeze({ response, completion, cancel: () => refuse('cancelled') });
  let limits;
  try {
    if (!requestedLimits || typeof requestedLimits !== 'object' || Array.isArray(requestedLimits) ||
        Object.keys(requestedLimits).some((key) => !Object.hasOwn(LIMITS, key))) throw new Error('limits');
    limits = { ...LIMITS, ...requestedLimits };
    if (Object.keys(LIMITS).some((key) => !Number.isSafeInteger(limits[key]) || limits[key] < 1 || limits[key] > LIMITS[key])) throw new Error('limits');
  } catch { refuse('invalid_limits'); return observation; }
  try {
    if (!(response instanceof Response) || response.bodyUsed || !response.ok || !response.body ||
        !/^text\/event-stream(?:\s*;\s*charset=utf-8)?\s*$/i.test(response.headers.get('content-type') || '')) {
      refuse('unsupported_response'); return observation;
    }
    reader = response.clone().body.getReader();
  } catch { refuse('unsupported_response'); return observation; }
  timer = setTimeout(() => refuse('timeout'), limits.milliseconds);
  let bytes = 0, chunks = 0, events = 0, messageId = null, ended = false;
  const decoder = new TextDecoder('utf-8', { fatal: true });
  const line = (value) => {
    if (value.length > limits.line || /\r/.test(value)) throw new Error('invalid');
    if (value === '') {
      if (eventData === null) return;
      if (ended || ++events > limits.events) throw new Error('invalid');
      const record = eventRecord(eventData); eventData = null;
      if (messageId !== null && messageId !== record.message_id) throw new Error('invalid');
      messageId = record.message_id;
      if (text.length + record.delta.length > limits.text) throw new Error('invalid');
      text += record.delta; ended = record.done;
    } else if (value.startsWith(':')) { /* bounded heartbeat comment */ }
    else if (value.startsWith('data: ') && eventData === null) eventData = value.slice(6);
    else throw new Error('invalid');
  };
  const decoded = (value) => {
    buffer += value;
    let newline;
    while ((newline = buffer.indexOf('\n')) !== -1) {
      const value = buffer.slice(0, newline); buffer = buffer.slice(newline + 1);
      line(value.endsWith('\r') ? value.slice(0, -1) : value);
    }
    if (buffer.length > limits.line) throw new Error('invalid');
  };
  (async () => {
    try {
      while (!settled) {
        const part = await reader.read();
        if (settled) return;
        if (part.done) {
          decoded(decoder.decode());
          if (buffer !== '' || eventData !== null || !ended || !text.trim()) throw new Error('invalid');
          settle({ status: 'observed', profile: PROFILE, message_id: messageId, text, bytes, chunks, events });
          return;
        }
        if (!(part.value instanceof Uint8Array) || ++chunks > limits.chunks || (bytes += part.value.byteLength) > limits.bytes) {
          refuse('resource_limit'); return;
        }
        decoded(decoder.decode(part.value, { stream: true }));
      }
    } catch { refuse('invalid_stream'); }
    finally { if (reader) { try { reader.releaseLock(); } catch { /* pending read */ } } }
  })();
  return observation;
}
