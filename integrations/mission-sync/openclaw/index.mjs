import {readFileSync, statSync} from 'node:fs';
import {MissionClient} from './client.mjs';

/** Hooks observe only the configured canonical sessionKey. No native sends,
 * task dispatch, tool execution, lease renewal, acceptance or model override. */
export default {
  id: 'residual-mission-sync',
  name: 'RESIDUAL Mission Sync',
  register(api) {
    let client;
    const get = ctx => {
      const path = process.env.RESIDUAL_MISSION_CONFIG;
      if (!path) return null;
      if (!client) {
        if (process.platform !== 'win32' && (statSync(path).mode & 0o077)) throw new Error('Private mission config required');
        const raw = readFileSync(path); if (raw.length > 48000) throw new Error('Config too large');
        client = new MissionClient(JSON.parse(raw.toString('utf8')));
      }
      return ctx?.sessionKey === client.config.conversation_id ? client : null;
    };
    const warn = () => api.logger?.warn?.('RESIDUAL mission sync DEGRADED; inspect binding/spool. No acceptance implied.');
    const observe = async (phase,event,ctx) => {
      try {
        const c = get(ctx); if (!c) return;
        if (event.sessionKey && event.sessionKey !== ctx.sessionKey) throw new Error('Conflicting native session');
        await c.context(false);
        const capture = process.env.RESIDUAL_MISSION_CAPTURE_TEXT === '1';
        const content = capture ? event.content : `OpenClaw ${phase} observed; text capture disabled.`;
        const nativeId = typeof event.messageId === 'string' ? `${phase}:${event.messageId}` : undefined;
        await c.record(capture ? 'message' : 'progress', content, nativeId);
        await c.pump();
      } catch {warn();}
    };
    api.on('message_received',(event,ctx)=>observe('message_received',event,ctx));
    api.on('message_sent',(event,ctx)=>event.success === true ? observe('message_sent',event,ctx) : undefined);
    api.on('before_prompt_build',async (_event,ctx)=>{
      try {const c=get(ctx); if (!c) return; await c.context(false); await c.pump(); return {appendContext:await c.context()};}
      catch {warn(); return {appendContext:'RESIDUAL mission sync unavailable. Do not infer current task state or acceptance from this conversation.'};}
    });
    api.on('gateway_stop',async ()=>{if(client){await client.tail; client.close(); client=undefined;}});
  },
};
