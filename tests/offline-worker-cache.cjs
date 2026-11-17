const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

test('the built offline worker replays its own cache and never recreates it after removal', async () => {
  const dist = path.resolve(__dirname, '../site/dist');
  const release = JSON.parse(fs.readFileSync(path.join(dist, 'offline-release.json'), 'utf8'));
  const worker = fs.readFileSync(path.join(dist, 'offline-worker.js'), 'utf8');
  const origin = 'http://127.0.0.1:4242';
  const asset = '/theme.js';
  const cacheName = 'aitrust-id-offline-' + release.version;
  const otherName = 'unrelated-cache';
  assert(release.assets.includes(asset));

  const stores = new Map([[otherName, new Map([[asset, 'wrong-cache-response']])]]);
  const caches = {
    async open(name) {
      if (!stores.has(name)) stores.set(name, new Map());
      const entries = stores.get(name);
      return {
        async addAll(urls) {
          for (const url of urls) entries.set(url, 'offline:' + url);
        },
        async match(url) {
          return entries.get(url);
        }
      };
    },
    async match(url, {cacheName} = {}) {
      if (cacheName !== undefined) return stores.get(cacheName)?.get(url);
      for (const entries of stores.values()) {
        if (entries.has(url)) return entries.get(url);
      }
    },
    async delete(name) {
      return stores.delete(name);
    }
  };
  const listeners = new Map();
  const network = [];
  vm.runInNewContext(worker, {
    URL,
    caches,
    self: {
      location: {origin},
      addEventListener: (name, listener) => listeners.set(name, listener)
    },
    fetch: async request => {
      network.push(request);
      return 'network:' + request.url;
    }
  }, {filename: 'offline-worker.js', timeout: 1000});

  let installation;
  listeners.get('install')({waitUntil: promise => {installation = promise;}});
  await installation;
  assert(stores.has(cacheName));

  function dispatchFetch(url, method = 'GET') {
    let response;
    listeners.get('fetch')({
      request: {url, method},
      respondWith: promise => {response = promise;}
    });
    return response;
  }

  assert.equal(await dispatchFetch(origin + asset), 'offline:' + asset);
  assert.equal(network.length, 0);
  assert.equal(await caches.delete(cacheName), true);

  // A document may still dispatch fetches through the worker after unregister.
  assert.equal(await dispatchFetch(origin + asset), 'network:' + origin + asset);
  assert.deepEqual([...stores.keys()], [otherName], 'fetch after removal recreated the deleted cache');
  assert.equal(stores.get(otherName).get(asset), 'wrong-cache-response');
  assert.deepEqual(network, [{url: origin + asset, method: 'GET'}]);

  assert.equal(dispatchFetch(origin + asset + '?query=synthetic'), undefined);
  assert.equal(dispatchFetch('https://example.invalid' + asset), undefined);
  assert.equal(dispatchFetch(origin + asset, 'POST'), undefined);
  assert.equal(dispatchFetch(origin + '/outside-allowlist'), undefined);
  assert.equal(network.length, 1);
  assert.deepEqual([...stores.keys()], [otherName]);
});
