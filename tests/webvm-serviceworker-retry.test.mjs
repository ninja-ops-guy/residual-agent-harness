import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../demo/vm/serviceworker_retry_fragment.js', import.meta.url), 'utf8');

function request(path, method='GET', origin='https://example.test') {
  return {method, url: origin + path, clone(){ return this; }};
}

async function withRuntime(sequence, callback) {
  let calls = 0;
  const messages = [];
  const context = vm.createContext({
    URL,
    Promise,
    console: {warn() {}},
    self: {
      location: {origin: 'https://example.test'},
      clients: {async matchAll() { return [{postMessage(message) { messages.push(message); }}]; }},
    },
    setTimeout(fn) { fn(); return 0; },
    fetch: async () => {
      const value = sequence[Math.min(calls++, sequence.length - 1)];
      if (value instanceof Error) throw value;
      return value;
    },
  });
  vm.runInContext(source, context, {filename: 'serviceworker_retry_fragment.js'});
  await callback(() => calls, context.residualFetchWithRetry, () => messages);
}

const chunk = '/residual-agent-harness/demo/residual-demo-' + 'a'.repeat(64) + '.ext2.c0001e9.txt';

test('same-origin immutable disk chunk retries one transient 503', async () => {
  await withRuntime([{status:503},{status:200}], async (calls, fetchWithRetry) => {
    const result = await fetchWithRetry(request(chunk));
    assert.equal(result.status, 200);
    assert.equal(calls(), 2);
  });
});

test('same-origin immutable disk chunk retries a network exception', async () => {
  await withRuntime([new Error('network'),{status:200}], async (calls, fetchWithRetry) => {
    const result = await fetchWithRetry(request(chunk));
    assert.equal(result.status, 200);
    assert.equal(calls(), 2);
  });
});

test('immutable disk chunk exhausts at three attempts', async () => {
  await withRuntime([{status:503},{status:502},{status:504}], async (calls, fetchWithRetry) => {
    const result = await fetchWithRetry(request(chunk));
    assert.equal(result.status, 504);
    assert.equal(calls(), 3);
  });
});

test('same-origin immutable disk chunk 4xx is never retried', async () => {
  await withRuntime([{status:404},{status:200}], async (calls, fetchWithRetry) => {
    const result = await fetchWithRetry(request(chunk));
    assert.equal(result.status, 404);
    assert.equal(calls(), 1);
  });
});

test('non-chunk 503 is never retried', async () => {
  await withRuntime([{status:503},{status:200}], async (calls, fetchWithRetry) => {
    const result = await fetchWithRetry(request('/provider/provider.js'));
    assert.equal(result.status, 503);
    assert.equal(calls(), 1);
  });
});

test('cross-origin and non-GET requests are never retried', async () => {
  await withRuntime([{status:503},{status:200}], async (calls, fetchWithRetry) => {
    const cross = await fetchWithRetry(request(chunk, 'GET', 'https://cdn.example'));
    assert.equal(cross.status, 503);
    assert.equal(calls(), 1);
  });
  await withRuntime([{status:503},{status:200}], async (calls, fetchWithRetry) => {
    const post = await fetchWithRetry(request(chunk, 'POST'));
    assert.equal(post.status, 503);
    assert.equal(calls(), 1);
  });
});

test('service-worker retry diagnostics expose bounded metadata without request URLs', async () => {
  await withRuntime([{status:503},{status:200}], async (calls, fetchWithRetry, diagnostics) => {
    const result = await fetchWithRetry(request(chunk));
    assert.equal(result.status, 200);
    await Promise.resolve();
    const events = diagnostics();
    assert.equal(events.length, 1);
    assert.equal(events[0].protocol, 'residual.diagnostic.v1');
    assert.equal(events[0].event_type, 'serviceworker.disk_chunk_retry');
    assert.deepEqual(JSON.parse(JSON.stringify(events[0].context)), {attempt:1,max_attempts:3,http_status:503});
    assert.equal(JSON.stringify(events).includes(chunk), false);
  });
});

test('service-worker exhaustion is classified without changing final HTTP behavior', async () => {
  await withRuntime([{status:503},{status:502},{status:504}], async (calls, fetchWithRetry, diagnostics) => {
    const result = await fetchWithRetry(request(chunk));
    assert.equal(result.status, 504);
    await Promise.resolve();
    const final = diagnostics().at(-1);
    assert.equal(final.event_type, 'serviceworker.disk_chunk_retry_exhausted');
    assert.equal(final.failure_class, 'NetworkFailure');
    assert.equal(final.severity, 'error');
    assert.equal(calls(), 3);
  });
});
