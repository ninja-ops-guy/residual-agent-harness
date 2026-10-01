import { DatabaseSync } from 'node:sqlite';
import { mkdirSync, lstatSync, chmodSync, existsSync, openSync, closeSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { randomUUID } from 'node:crypto';
import { canonical, sha256, requireThat, verifyEvidence } from './protocol.mjs';

// One SQLite transaction binds the command intent and its receipt. Provider I/O is NOT atomic with it.
export class Journal {
  constructor(directory, runtimeId, now = Date.now, maxEvents = 100000) {
    this.now = now; this.runtimeId = runtimeId; this.maxEvents = maxEvents;
    const dir = resolve(directory);
    mkdirSync(dir, {recursive: true, mode: 0o700});
    requireThat(lstatSync(dir).isDirectory() && !lstatSync(dir).isSymbolicLink(), 'UNSAFE_STATE_PATH');
    if (process.platform !== 'win32') requireThat((lstatSync(dir).mode & 0o077) === 0, 'UNSAFE_STATE_PERMISSIONS');
    const file = join(dir, 'control.sqlite');
    if (!existsSync(file)) closeSync(openSync(file, 'wx', 0o600));
    requireThat(lstatSync(file).isFile() && !lstatSync(file).isSymbolicLink(), 'UNSAFE_STATE_PATH');
    if (process.platform !== 'win32') requireThat((lstatSync(file).mode & 0o077) === 0, 'UNSAFE_STATE_PERMISSIONS');
    this.db = new DatabaseSync(file);
    this.db.exec(`PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; PRAGMA busy_timeout=5000;
      CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY,value TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY,body TEXT NOT NULL,digest TEXT NOT NULL,previous TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS operations (id TEXT PRIMARY KEY,digest TEXT NOT NULL,record TEXT NOT NULL,record_digest TEXT NOT NULL);
    `);
    this.instance = randomUUID();
    try { this.transaction(() => {
      this.verifyStored();
      const stored = this.getMeta('runtime');
      requireThat(!stored || stored === runtimeId, 'STATE_RUNTIME_MISMATCH');
      this.setMeta('runtime', runtimeId); this.setMeta('instance', this.instance);
      for (const record of this.all()) {
        if (['INVOCATION_STARTED','RUNNING'].includes(record.state)) {
          record.state = 'INDETERMINATE'; record.reason = 'PROCESS_REPLACED';
          this.put(record.operation_id, record);
          this.event('execution.indeterminate', {operation_id: record.operation_id, reason:'PROCESS_REPLACED'});
        }
      }
      this.event('runtime.started', {instance_id:this.instance});
    }); } catch (error) { this.db.close(); throw error; }
    if (process.platform !== 'win32') {
      for (const suffix of ['', '-wal', '-shm']) if (existsSync(file+suffix)) chmodSync(file+suffix, 0o600);
    }
  }
  transaction(fn) {
    this.db.exec('BEGIN IMMEDIATE');
    try { const out = fn(); this.db.exec('COMMIT'); return out; }
    catch (error) { this.db.exec('ROLLBACK'); throw error; }
  }
  getMeta(key) { return this.db.prepare('SELECT value FROM meta WHERE key=?').get(key)?.value; }
  setMeta(key, value) { this.db.prepare('INSERT OR REPLACE INTO meta VALUES (?,?)').run(key, value); }
  fence() { requireThat(this.getMeta('instance') === this.instance, 'STALE_INSTANCE'); }
  event(type, payload) {
    this.fence();
    const last = this.db.prepare('SELECT seq,digest FROM events ORDER BY seq DESC LIMIT 1').get();
    const sequence = (last?.seq || 0) + 1;
    requireThat(sequence <= this.maxEvents, 'EVIDENCE_CAPACITY');
    const previous = last?.digest || '0'.repeat(64);
    const data = {sequence, previous_sha256:previous, runtime_id:this.runtimeId,
      instance_id:this.instance, observed_at_ms:this.now(), type, payload,
      trust:'RUNTIME_REPORTED', acceptance:'NOT_EVALUATED'};
    const bytes = Buffer.from(canonical(data));
    this.db.prepare('INSERT INTO events VALUES (?,?,?,?)').run(sequence, bytes.toString('base64url'), sha256(bytes), previous);
    this.setMeta('event_sequence',String(sequence));this.setMeta('event_tip',sha256(bytes));
    return sequence;
  }
  append(type, payload) { return this.transaction(() => this.event(type, payload)); }
  verifyStored() {
    let previous={sequence:0,sha256:'0'.repeat(64)};
    for (const row of this.db.prepare('SELECT seq AS sequence,body,digest AS sha256,previous AS previous_sha256 FROM events ORDER BY seq').all()) {
      const body=verifyEvidence({...row},previous);
      requireThat(body.runtime_id===this.runtimeId,'STATE_RUNTIME_MISMATCH');
      previous=row;
    }
    requireThat(String(previous.sequence)===(this.getMeta('event_sequence') || '0') &&
      previous.sha256===(this.getMeta('event_tip') || '0'.repeat(64)),'JOURNAL_TRUNCATED');
    this.all();
  }
  decodeRecord(row) {
    requireThat(sha256(Buffer.from(row.record))===row.record_digest,'JOURNAL_INTEGRITY_FAILURE');
    const result=JSON.parse(row.record);
    requireThat(canonical(result)===row.record && result.operation_id===row.id,'JOURNAL_INTEGRITY_FAILURE');
    return result;
  }
  existing(id) {
    const row = this.db.prepare('SELECT * FROM operations WHERE id=?').get(id);
    return row ? {digest:row.digest, record:this.decodeRecord(row)} : null;
  }
  insert(id, digest, record) {
    const bytes=canonical(record);
    this.db.prepare('INSERT INTO operations VALUES (?,?,?,?)').run(id,digest,bytes,sha256(Buffer.from(bytes)));
  }
  put(id, record) {
    this.fence(); const bytes=canonical(record);
    requireThat(this.db.prepare('UPDATE operations SET record=?,record_digest=? WHERE id=?').run(bytes,sha256(Buffer.from(bytes)),id).changes===1,'NOT_FOUND');
  }
  all() { return this.db.prepare('SELECT * FROM operations').all().map(r=>this.decodeRecord(r)); }
  events(after, limit) {
    requireThat(Number.isSafeInteger(after) && after >= 0 && Number.isSafeInteger(limit) && limit >= 1 && limit <= 100, 'SCHEMA_INVALID');
    return this.db.prepare('SELECT seq AS sequence,body,digest AS sha256,previous AS previous_sha256 FROM events WHERE seq>? ORDER BY seq LIMIT ?').all(after, limit).map(r => ({...r}));
  }
  head() {
    this.fence();
    return {
      sequence: Number(this.getMeta('event_sequence') || '0'),
      sha256: this.getMeta('event_tip') || '0'.repeat(64),
    };
  }
  close() { this.db.close(); }
}
