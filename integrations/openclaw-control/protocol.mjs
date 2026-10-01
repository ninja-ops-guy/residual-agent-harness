// RESIDUAL OpenClaw control protocol. Only the external controller holds signing keys.
import { createHash, createPublicKey, sign, verify } from 'node:crypto';
export const PROTOCOL = 'residual.openclaw.control.v1';
export const MAX_WIRE_BYTES = 96 * 1024;
export class ControlError extends Error {
  constructor(code) { super(code); this.name = 'ControlError'; this.code = code; }
}
export function requireThat(value, code) { if (!value) throw new ControlError(code); }
export const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
export const canonical = value => {
  if (value === null || typeof value === 'boolean' || typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'number' && Number.isSafeInteger(value)) return String(value);
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  requireThat(value && Object.getPrototypeOf(value) === Object.prototype, 'INVALID_JSON_VALUE');
  return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
};
export function exactKeys(value, required, optional = []) {
  requireThat(value && typeof value === 'object' && !Array.isArray(value), 'SCHEMA_INVALID');
  requireThat(required.every(k => Object.hasOwn(value, k)) &&
    Object.keys(value).every(k => required.includes(k) || optional.includes(k)), 'SCHEMA_INVALID');
}
export function identifier(value) {
  requireThat(typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/.test(value), 'INVALID_ID');
  return value;
}
export function boundedText(value, maxBytes) {
  requireThat(typeof value === 'string' && value.length > 0 && Buffer.byteLength(value) <= maxBytes, 'INVALID_TEXT');
  return value;
}
export function decode64(value, limit) {
  requireThat(typeof value === 'string' && /^[A-Za-z0-9_-]+$/.test(value) && value.length <= Math.ceil(limit * 4 / 3), 'ENCODING_INVALID');
  const bytes = Buffer.from(value, 'base64url');
  requireThat(bytes.length <= limit && bytes.toString('base64url') === value, 'ENCODING_INVALID');
  return bytes;
}
export function publicKey(pem) {
  const key = createPublicKey(pem);
  requireThat(key.asymmetricKeyType === 'ed25519', 'KEY_TYPE_INVALID');
  return key;
}
export const keyId = key => sha256((key?.type === 'public' ? key : createPublicKey(key)).export({type:'spki', format:'der'}));
export function signCommand(command, privateKey, id) {
  const bytes = Buffer.from(canonical(command));
  return {key_id: id, body: bytes.toString('base64url'), signature: sign(null, bytes, privateKey).toString('base64url')};
}
export function verifyCommand(envelope, keys, identity, now) {
  exactKeys(envelope, ['key_id', 'body', 'signature']);
  requireThat(typeof envelope.key_id === 'string' && Object.hasOwn(keys, envelope.key_id), 'AUTHORITY_DENIED');
  const bytes = decode64(envelope.body, 64 * 1024);
  const signature = decode64(envelope.signature, 64);
  requireThat(signature.length === 64 && verify(null, bytes, keys[envelope.key_id], signature), 'AUTHORITY_DENIED');
  let cmd;
  try { cmd = JSON.parse(bytes.toString('utf8')); } catch { throw new ControlError('SCHEMA_INVALID'); }
  // A unique canonical representation rejects duplicate JSON keys and lossy/non-finite numbers.
  requireThat(Buffer.from(canonical(cmd)).equals(bytes), 'NONCANONICAL_COMMAND');
  exactKeys(cmd, ['protocol','operation_id','runtime_id','instance_id','config_digest','issued_at_ms','expires_at_ms','action','body']);
  requireThat(cmd.protocol === PROTOCOL, 'PROTOCOL_MISMATCH');
  identifier(cmd.operation_id); identifier(cmd.action);
  requireThat(cmd.runtime_id === identity.runtime_id && cmd.instance_id === identity.instance_id, 'STALE_INSTANCE');
  requireThat(cmd.config_digest === identity.config_digest, 'CONFIG_DRIFT');
  requireThat(Number.isSafeInteger(cmd.issued_at_ms) && Number.isSafeInteger(cmd.expires_at_ms) &&
    cmd.issued_at_ms <= now + 2000 && cmd.expires_at_ms > now &&
    cmd.expires_at_ms > cmd.issued_at_ms && cmd.expires_at_ms - cmd.issued_at_ms <= 30000, 'AUTHORITY_EXPIRED');
  return {command: cmd, digest: sha256(bytes), key_id: envelope.key_id};
}
export function verifyEvidence(row, previous = null) {
  exactKeys(row, ['sequence','body','sha256','previous_sha256']);
  const bytes = decode64(row.body, 128 * 1024);
  requireThat(sha256(bytes) === row.sha256, 'INTEGRITY_FAILURE');
  const body = JSON.parse(bytes.toString('utf8'));
  requireThat(canonical(body) === bytes.toString('utf8') && body.sequence === row.sequence &&
    body.previous_sha256 === row.previous_sha256, 'EVIDENCE_BINDING_FAILURE');
  if (previous) requireThat(row.sequence === previous.sequence + 1 && row.previous_sha256 === previous.sha256, 'EVIDENCE_GAP');
  return body;
}
