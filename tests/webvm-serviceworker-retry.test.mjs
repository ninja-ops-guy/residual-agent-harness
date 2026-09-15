import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../demo/vm/serviceworker_retry_fragment.js', import.meta.url), 'utf8');

function request(path, method='GET', origin='https://example.test') {
  return {method, url: origin + path, clone(){ return this; }};
}

async function withRuntime(sequence, callback) {
  const originalFetch = globalThis.fetch;
  const originalSelf = globalThis.self;
  const originalTimeout = globalThis.setTimeout;
  const originalWarn = console.warn;
  let calls = 0;
  globalThis.self = {location:{origin:'https://example.test'}};
  globalThis.setTimeout = fn => { fn(); return 0; };
  console.warn = () => {};
  globalThis.fetch = async () => {
    const value = sequence[Math.min(calls++, sequence.length - 1)];
    if (value instanceof Error) throw value;
    return value;
  };
  vm.runInThisContext(source, {filename:'serviceworker_retry_fragment.js'});
  try { await callback(() => calls); }
  finally {
    globalThis.fetch = originalFetch;
    globalThis.self = originalSelf;
    globalThis.setTimeout = originalTimeout;
    console.warn = originalWarn;
    delete globalThis.residualIsImmutableDiskChunk;
    delete globalThis.residualDiskRetryDelay;
    delete globalThis.residualFetchWithRetry;
  }
}

const chunk = '/residual-agent-harness/demo/residual-demo-' + 'a'.repeat(64) + '.ext2.c0001e9.txt';

test('same-origin immutable disk chunk retries one transient 503', async () => {
  await withRuntime([{status:503},{status:200}], async calls => {
    const result = await residualFetchWithRetry(request(chunk));
    assert.equal(result.status, 200);
    assert.equal(calls(), 2);
  });
});

test('same-origin immutable disk chunk retries a network exception', async () => {
  await withRuntime([new Error('network'),{status:200}], async calls => {
    const result = await residualFetchWithRetry(request(chunk));
    assert.equal(result.status, 200);
    assert.equal(calls(), 2);
  });
});

test('immutable disk chunk exhausts at three attempts', async () => {
  await withRuntime([{status:503},{status:502},{status:504}], async calls => {
    const result = await residualFetchWithRetry(request(chunk));
    assert.equal(result.status, 504);
    assert.equal(calls(), 3);
  });
});

test('non-chunk 503 is never retried', async () => {
  await withRuntime([{status:503},{status:200}], async calls => {
    const result = await residualFetchWithRetry(request('/provider/provider.js'));
    assert.equal(result.status, 503);
    assert.equal(calls(), 1);
  });
});

test('cross-origin and non-GET requests are never retried', async () => {
  await withRuntime([{status:503},{status:200}], async calls => {
    const cross = await residualFetchWithRetry(request(chunk, 'GET', 'https://cdn.example'));
    assert.equal(cross.status, 503);
    assert.equal(calls(), 1);
  });
  await withRuntime([{status:503},{status:200}], async calls => {
    const post = await residualFetchWithRetry(request(chunk, 'POST'));
    assert.equal(post.status, 503);
    assert.equal(calls(), 1);
  });
});
