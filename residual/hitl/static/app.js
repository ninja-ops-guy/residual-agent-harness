'use strict';
const credential = document.querySelector('#credential');
const status = document.querySelector('#status');
const container = document.querySelector('#challenges');
const more = document.querySelector('#more');
let cursor = null;
let generation = 0;
async function api(path, body) {
  const response = await fetch(path, {method: body ? 'POST' : 'GET', cache: 'no-store', credentials: 'omit',
    headers: {'Authorization': `Bearer ${credential.value}`, ...(body ? {'Content-Type':'application/json'} : {})},
    ...(body ? {body: JSON.stringify(body)} : {})});
  if (!response.ok) throw new Error(response.status === 409 ? 'Challenge changed, expired, or decision was rejected. Reload.' : 'Request rejected. Check your credential and role.');
  return response.json();
}
function element(tag, text) { const node = document.createElement(tag); node.textContent = text; return node; }
async function load(after = '') {
  const current = ++generation;
  status.textContent = 'Loading…';
  try {
    const page = await api('/api/challenges' + (after ? '?after=' + encodeURIComponent(after) : ''));
    if (current !== generation) return;
    container.replaceChildren();
    for (const challenge of page.challenges) {
      const card = element('article', '');
      card.append(element('h2', challenge.payload.task_id), element('p', `Status: ${challenge.status}`),
        element('p', challenge.payload.reason), element('p', `Goal: ${challenge.payload.goal_spec_hash}`),
        element('pre', JSON.stringify(challenge.payload.action, null, 2)));
      const label = element('label', 'Acting role ');
      const role = document.createElement('select');
      for (const name of challenge.authorized_roles.filter(name => page.operator_roles.includes(name))) { const option = element('option', name); option.value = name; role.append(option); }
      label.append(role); card.append(label);
      if (challenge.status === 'pending') for (const decision of ['approve', 'deny']) {
        const button = element('button', decision === 'approve' ? 'Approve exact action' : 'Deny action');
        button.addEventListener('click', async () => {
          if (!window.confirm(`${decision.toUpperCase()} the displayed action for ${challenge.payload.task_id}?`)) return;
          button.disabled = true;
          try {
            await api(`/api/challenges/${encodeURIComponent(challenge.challenge_id)}/decision`,
              {decision, role: role.value, challenge_signature: challenge.signature});
            await load();
          } catch (error) { status.textContent = error.message; button.disabled = false; }
        });
        card.append(button);
      }
      container.append(card);
    }
    cursor = page.next_cursor; more.hidden = !cursor;
    status.textContent = `${page.challenges.length} visible challenges on this page. Decisions never resume execution.`;
  } catch (error) { if (current === generation) status.textContent = error.message; }
}
document.querySelector('#load').addEventListener('click', () => load());
document.querySelector('#clear').addEventListener('click', () => { generation++; credential.value=''; container.replaceChildren(); status.textContent='Credential cleared.'; more.hidden=true; });
more.addEventListener('click', () => load(cursor));
window.addEventListener('pagehide', () => { credential.value=''; });
