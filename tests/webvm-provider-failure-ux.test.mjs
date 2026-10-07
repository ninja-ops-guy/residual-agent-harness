import test from 'node:test';
import assert from 'node:assert/strict';
import {providerFailureMessage, validModel} from '../demo/vm/provider-session.js';

test('provider-prefixed model identifiers remain valid and explicit', () => {
  assert.equal(validModel('openai/gpt-5-nano'), true);
});

test('safe provider failures are actionable without leaking upstream bodies', () => {
  const cases = [
    'provider_model_unavailable',
    'provider_authorization_failed',
    'provider_protocol_invalid',
    'provider_timeout',
    'provider_request_failed',
    'provider_response_too_large',
    'provider_budget_exhausted',
    'provider_disconnected',
  ];
  for (const code of cases) {
    const message = providerFailureMessage(code);
    assert.equal(typeof message, 'string');
    assert.ok(message.length > 20);
    assert.ok(!message.includes('secret'));
  }
  assert.match(providerFailureMessage('provider_authorization_failed'), /allowance|billing/i);
  assert.match(providerFailureMessage('provider_protocol_invalid'), /protocol/i);
});

test('unknown upstream error is intentionally generic', () => {
  assert.match(providerFailureMessage('upstream-secret-token-123'), /bounded safe error code/i);
});
