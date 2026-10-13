const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { pathToFileURL } = require('node:url');
const path = require('node:path');
const modulePromise = import(pathToFileURL(path.resolve(__dirname, '../extension/src/main-world/stream-observer.mjs')));
const encode = (value) => new TextEncoder().encode(value);
const record = (delta = 'Example', done = true, extra = {}) => ({
  profile: 'aitrust.assistant-text.v1', message_id: 'sample-1', role: 'assistant', delta, done, ...extra
});
const event = (value) => 'data: ' + JSON.stringify(value) + '\n\n';
const response = (body, headers = { 'content-type': 'text/event-stream' }) => new Response(body, { headers });
const unavailable = (result, reason) => {
  assert.equal(result.status, 'unavailable');
  if (reason) assert.equal(result.reason, reason);
  assert.deepEqual(Object.keys(result).sort(), ['reason', 'status']);
};

test('original response identity, headers and body remain usable; split UTF-8 and CRLF work', async () => {
  const { observeAssistantStream } = await modulePromise;
  const raw = event(record('Hi 🙂', false)).replaceAll('\n', '\r\n') + event(record('!', true));
  const bytes = encode(raw);
  const stream = new ReadableStream({ start(c) { for (let n = 0; n < bytes.length; n++) c.enqueue(bytes.slice(n, n + 1)); c.close(); } });
  const original = response(stream, { 'content-type': 'text/event-stream; charset=utf-8', 'x-example': 'kept' });
  const observation = observeAssistantStream(original);
  assert.equal(observation.response, original);
  assert.equal(original.bodyUsed, false);
  assert.equal(original.headers.get('x-example'), 'kept');
  const [observed, page] = await Promise.all([observation.completion, original.text()]);
  assert.equal(page, raw); assert.equal(observed.text, 'Hi 🙂!'); assert.equal(observed.events, 2);
  assert.equal(observed.bytes, bytes.length); assert.ok(Object.isFrozen(observed));
});

test('unsupported, already consumed and non-success responses are not observed', async () => {
  const { observeAssistantStream } = await modulePromise;
  const used = response('example'); await used.text();
  for (const source of [null, {}, used, response('example', {}), new Response('', { status: 403, headers: { 'content-type': 'text/event-stream' } })]) {
    unavailable(await observeAssistantStream(source).completion, 'unsupported_response');
  }
});

test('closed schema rejects user, changing identity, missing completion and unknown fields', async () => {
  const { observeAssistantStream } = await modulePromise;
  const bodies = [event(record('private', true, { role: 'user' })), event(record('', true, { extra: 'private' })),
    event(record('first', false)) + event(record('second', true, { message_id: 'other' })),
    event(record('partial', false)), event(record('done', true)) + event(record('more', true)),
    event(record('  ', true)), event(record('done', true)).trimEnd(),
    event(record('text', true, { profile: 'other' })), event(record('text', true, { message_id: '../private' }))];
  for (const raw of bodies) unavailable(await observeAssistantStream(response(raw)).completion, 'invalid_stream');
});

test('duplicate keys, malformed JSON, nested fields, invalid Unicode and UTF-8 are refused', async () => {
  const { observeAssistantStream } = await modulePromise;
  const good = JSON.stringify(record());
  for (const raw of [good.replace('"delta":"Example"', '"delta":"hidden","delta":"Example"'),
    good.replace('"delta":"Example"', '"delta":{}'), good.replace('"delta":"Example"', '"delta":"\\ud800"'),
    good.replace('"delta":"Example"', '"delta":"\\u0000"'), good + ' extra', '{}', '[1]', '{broken']) {
    unavailable(await observeAssistantStream(response('data: ' + raw + '\n\n')).completion, 'invalid_stream');
  }
  unavailable(await observeAssistantStream(response(new Uint8Array([0xc3, 0x28]))).completion, 'invalid_stream');
});

test('observer bounds bytes, chunks, line, event count and text without returning partial input', async () => {
  const { observeAssistantStream } = await modulePromise;
  const cases = [
    [response(event(record())), { bytes: 10 }, 'resource_limit'],
    [response(new ReadableStream({ start(c) { c.enqueue(encode(':heartbeat\n')); c.enqueue(encode(event(record()))); c.close(); } })), { chunks: 1 }, 'resource_limit'],
    [response(event(record())), { line: 10 }, 'invalid_stream'],
    [response(event(record('a', false)) + event(record('b', true))), { events: 1 }, 'invalid_stream'],
    [response(event(record('secret', true))), { text: 2 }, 'invalid_stream']
  ];
  for (const [source, limits, reason] of cases) unavailable(await observeAssistantStream(source, limits).completion, reason);
});

test('limits cannot be extended or replaced by invalid values', async () => {
  const { observeAssistantStream, LIMITS } = await modulePromise;
  for (const limits of [null, [], { extra: 1 }, { bytes: 0 }, { bytes: NaN }, { milliseconds: Infinity }, { line: 1.2 }, { text: LIMITS.text + 1 }]) {
    const source = response(event(record()));
    unavailable(await observeAssistantStream(source, limits).completion, 'invalid_limits');
    assert.equal(source.bodyUsed, false);
  }
});

test('timeout, explicit cancellation and late events cannot return partial data', async () => {
  const { observeAssistantStream } = await modulePromise;
  let controller;
  const source = response(new ReadableStream({ start(c) { controller = c; c.enqueue(encode(event(record('private', false)))); } }));
  const timed = observeAssistantStream(source, { milliseconds: 20 });
  unavailable(await timed.completion, 'timeout');
  controller.enqueue(encode(event(record('later', true)))); controller.close();
  assert.equal((await source.text()).includes('later'), true);
  unavailable(await timed.completion, 'timeout');
  const other = response(event(record('private', true)));
  const cancelled = observeAssistantStream(other); cancelled.cancel(); cancelled.cancel();
  unavailable(await cancelled.completion, 'cancelled');
  assert.equal(await other.text(), event(record('private', true)));
});

test('a reader error is bounded and never returns its exception message', async () => {
  const { observeAssistantStream } = await modulePromise;
  const original = response(new ReadableStream({ start(c) { c.error(new Error('PRIVATE-CANARY')); } }));
  const result = await observeAssistantStream(original).completion;
  unavailable(result, 'invalid_stream'); assert.equal(JSON.stringify(result).includes('PRIVATE-CANARY'), false);
});

test('bounded comments are accepted but other SSE fields and multiple data lines are refused', async () => {
  const { observeAssistantStream } = await modulePromise;
  assert.equal((await observeAssistantStream(response(':beat\n\n' + event(record()))).completion).status, 'observed');
  for (const body of ['event: message\n' + event(record()), 'data: {}\ndata: {}\n\n', ':bad\rline\n' + event(record())]) {
    unavailable(await observeAssistantStream(response(body)).completion, 'invalid_stream');
  }
});

test('installed manifest is DOM-only; developer observer has no automatic side effects', async () => {
  const { observeAssistantStream } = await modulePromise;
  assert.equal(typeof observeAssistantStream, 'function');
  const root = path.resolve(__dirname, '..');
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'extension/manifest.json')));
  assert.deepEqual(manifest.permissions, ['storage']);
  assert.deepEqual(manifest.host_permissions, ['http://127.0.0.1:8787/*']);
  assert.ok(manifest.content_scripts.every((entry) => entry.world === 'ISOLATED'));
  const installed = [...manifest.content_scripts.flatMap((entry) => entry.js), manifest.background.service_worker];
  for (const file of installed) assert.doesNotMatch(fs.readFileSync(path.join(root, 'extension', file), 'utf8'), /stream-observer|main-world\/tap/);
  const source = fs.readFileSync(path.join(root, 'extension/src/main-world/stream-observer.mjs'), 'utf8');
  assert.doesNotMatch(source, /window\.|postMessage\(|fetch\(|XMLHttpRequest|localStorage|chrome\./);
  assert.equal(fs.existsSync(path.join(root, 'extension/src/main-world/tap.js')), false);
});
