import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const providerHtml = readFileSync(new URL('../demo/vm/provider.html', import.meta.url), 'utf8');
const providerSource = readFileSync(new URL('../demo/vm/provider.js', import.meta.url), 'utf8');

test('provider load control fails closed until the private bridge is initialized', () => {
  assert.match(providerHtml, /<button id="load" disabled>1 · Load Puter<\/button>/);
  assert.match(providerHtml, /<button id="signin" disabled>2 · Sign in to Puter<\/button>/);
  assert.match(providerSource, /load\.disabled = true;/);
  assert.match(providerSource, /channel = event\.ports\[0\]/);
  assert.match(providerSource, /load\.disabled = false; tell\('Bridge ready\. Load Puter when you are ready; no inference has run\.'\); state\(\);/);
});
