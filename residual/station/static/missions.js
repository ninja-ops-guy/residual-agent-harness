'use strict';
let token = '';
const byId = id => document.getElementById(id);
const el = (tag, text, cls) => { const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n; };
async function api(path, data) {
  const r = await fetch(path, {method: data ? 'POST' : 'GET', cache: 'no-store', headers: {'X-Station-Token': token, ...(data ? {'Content-Type': 'application/json'} : {})}, ...(data ? {body: JSON.stringify(data)} : {})});
  const j = await r.json(); if (!r.ok) throw new Error(j.error || 'Request failed'); return j;
}
async function load() {
  try {
    if (!token) token = (await api('/api/bootstrap')).token;
    const data = await api('/api/missions');
    const root = byId('missions'); root.replaceChildren();
    let taskCount = 0, links = 0;
    for (const m of data.missions) {
      const section = el('section', '', 'mission');
      section.append(el('h2', m.name || m.id), el('p', `${m.id} · ${m.paused ? 'PAUSED' : 'ACTIVE'}`, 'muted'), el('p', m.goal));
      for (const t of m.tasks) {
        taskCount++;
        const card = el('article', '', 'task');
        card.append(el('h3', `${t.id} · ${t.title || ''}`), el('p', `Station: ${t.state} · attempt ${t.attempt} · owner ${t.owner || 'unassigned'}`, 'state'));
        card.append(el('p', `Dependencies: ${(t.depends_on || []).join(', ') || 'none'}`, 'muted'));
        if (!t.conversations.length) card.append(el('p', 'No bound conversations.', 'muted'));
        for (const b of t.conversations) {
          links++;
          const box = el('div', '', 'binding');
          box.append(el('strong', `${b.agent_id} / ${b.harness} · ${b.sync_state}`), el('p', `${b.instance_id} · ${b.conversation_id}`, 'muted'), el('p', `${b.pending_deliveries} awaiting adapter ACK · last source sequence ${b.last_source_seq}`));
          if (b.latest_report) { const r = b.latest_report.report; box.append(el('p', `AGENT REPORT · ${r.kind} · not verified`, 'claim'), el('pre', r.text)); }
          const revoke = el('button', 'Revoke binding'); revoke.disabled = b.revoked;
          revoke.onclick = async () => { try { await api('/api/missions/revoke', {binding_id: b.binding_id}); await load(); } catch (e) { byId('status').textContent = e.message; } };
          box.append(revoke); card.append(box);
        }
        section.append(card);
      }
      root.append(section);
    }
    if (!data.missions.length) root.append(el('p', 'Create or import a project in Station to start a mission.'));
    byId('status').textContent = `${data.missions.length} missions · ${taskCount} tasks · ${links} conversation bindings · updated ${new Date().toLocaleTimeString()}`;
  } catch (e) { byId('status').textContent = `SYNC UNAVAILABLE: ${e.message}`; }
}
byId('refresh').onclick = load;
byId('bind').onsubmit = async event => {
  event.preventDefault();
  try { const f = new FormData(event.target); const d = Object.fromEntries(f); d.share_messages = f.has('share_messages'); const r = await api('/api/missions/bind', d); byId('binding-result').textContent = JSON.stringify(r, null, 2); await load(); }
  catch (e) { byId('binding-result').textContent = e.message; }
};
load();
setInterval(() => { if (!document.hidden) load(); }, 5000);
