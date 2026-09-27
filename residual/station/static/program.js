"use strict";

function refreshProgram(){
  return api("/api/program").then(value => {
    state.program = value;
    return value;
  });
}

function programBadge(value){
  const v=String(value||"").toUpperCase();
  const cls=["BLOCKED","HUMAN_ACTION_REQUIRED"].includes(v)?"amber":
    ["READY_FOR_OWNER_GATE","VERIFYING"].includes(v)?"teal":
    ["CLOSED","SUPERSEDED","HISTORICAL_EVIDENCE"].includes(v)?"gray":"";
  return `<span class="tag ${cls}">${e(label(v))}</span>`;
}

function programRow(item){
  return `<tr>
    <td><button class="text-button" data-action="program-item" data-id="${e(item.item_id)}"><code>${e(item.item_id)}</code></button>
      <br><span class="muted">${e(item.title)}</span></td>
    <td>${programBadge(item.state)}</td>
    <td><span class="tag gray">${e(item.v1_disposition)}</span></td>
    <td>${e(item.workstream)}</td>
    <td>${e(item.next_action||"—")}</td>
  </tr>`;
}

function programItemDialog(item){
  const source=item.source||{};
  const sourceLink=source.url
    ? `<a class="text-button" href="${e(source.url)}" target="_blank" rel="noreferrer">Open source ↗</a>`
    : "";
  const buttons=[
    button("Ready","program-set",false,`data-id="${e(item.item_id)}" data-state="READY" data-owner-action="false"`),
    button("Blocked","program-set",false,`data-id="${e(item.item_id)}" data-state="BLOCKED"`),
    button("Owner gate","program-set",false,`data-id="${e(item.item_id)}" data-state="READY_FOR_OWNER_GATE" data-owner-action="true"`),
    button("V1 required","program-set",false,`data-id="${e(item.item_id)}" data-disposition="V1_REQUIRED"`),
    button("Post-v1","program-set",false,`data-id="${e(item.item_id)}" data-state="DEFERRED_POST_V1" data-disposition="POST_V1" data-owner-action="false"`),
    button("Research only","program-set",false,`data-id="${e(item.item_id)}" data-state="RESEARCH_ONLY" data-disposition="RESEARCH_ONLY" data-owner-action="false"`),
    button("Superseded","program-set",false,`data-id="${e(item.item_id)}" data-state="SUPERSEDED" data-owner-action="false"`),
    button("Closed","program-set",false,`data-id="${e(item.item_id)}" data-state="CLOSED" data-owner-action="false"`)
  ].join("");
  openDialog(item.title,`
    <div class="button-row">
      ${programBadge(item.state)}
      <span class="tag gray">${e(item.v1_disposition)}</span>
      <span class="tag gray">${e(item.priority)}</span>
    </div>
    <dl class="detail-grid">
      <div class="detail-cell"><dt>Program item</dt><dd>${e(item.item_id)}</dd></div>
      <div class="detail-cell"><dt>Workstream</dt><dd>${e(item.workstream)}</dd></div>
      <div class="detail-cell"><dt>Source HEAD</dt><dd>${e(source.head||"not revision-bound")}</dd></div>
      <div class="detail-cell"><dt>Owner</dt><dd>${e(item.owner||"unassigned")}</dd></div>
      <div class="detail-cell"><dt>Blocked by</dt><dd>${e((item.blocked_by||[]).join(", ")||"none")}</dd></div>
      <div class="detail-cell"><dt>Superseded by</dt><dd>${e((item.superseded_by||[]).join(", ")||"none")}</dd></div>
    </dl>
    <p class="small-text"><b>Next action:</b> ${e(item.next_action||"Not classified yet.")}</p>
    ${item.override_stale?'<div class="callout warn"><b>STALE AUTHORITY OVERRIDE</b> · Source identity changed; an earlier HEAD-bound decision was not transferred.</div>':""}
    <div class="button-row section-gap">${buttons}</div>
    <div class="section-gap">${sourceLink}</div>
  `,"PROGRAM CONTROL / ITEM");
}

function program(){
  const p=state.program;
  const actions=button("↻ Sync GitHub","program-sync",true)+button("↻ Refresh snapshot","program-refresh");
  if(!p){
    return pageTitle(
      "SELF-HOSTING / PROGRAM CONTROL",
      "Track RESIDUAL through RESIDUAL.",
      "GitHub facts in. Evidence-bound program state out.",
      actions
    )+`<div class="panel empty">
      <div class="empty-icon">⌁</div>
      <h2>No program snapshot yet.</h2>
      <p>Sync the repository to import open PRs and issues without treating repository-open state as authoritative program state.</p>
    </div>`;
  }
  const m=p.summary||{},owners=p.owner_actions||[],critical=p.v1_critical||[],active=p.active_items||[],tracked=p.all_items||active,streams=p.workstreams||[];
  return pageTitle(
    "SELF-HOSTING / PROGRAM CONTROL",
    "RESIDUAL program control.",
    "Normalize open work, preserve supersession, and surface only genuine owner gates.",
    actions
  )+`<div class="stats">
    <div class="stat"><div class="label">TRACKED <span>▤</span></div><div class="value">${num(m.total)}</div><small>${num(m.active)} active after program-state projection</small></div>
    <div class="stat"><div class="label">OWNER ACTIONS <span>◆</span></div><div class="value amber">${num(m.owner_actions)}</div><small>Human authority or decision required</small></div>
    <div class="stat"><div class="label">V1 SURFACE <span>◇</span></div><div class="value teal">${num((m.v1_required||0)+(m.v1_supporting||0))}</div><small>${num(m.v1_required)} required · ${num(m.v1_supporting)} supporting</small></div>
    <div class="stat"><div class="label">UNCLASSIFIED <span>?</span></div><div class="value">${num(m.unclassified)}</div><small>Needs program triage, not automatic closure</small></div>
  </div>
  <div class="callout info">
    <b>PROGRAM SNAPSHOT</b> · ${e(short(p.snapshot_sha256))} · ${e(p.generated_at||"not synced")}<br>
    <span class="mono small-text">${e(p.repo||"No repository configured")}</span>
  </div>
  <div class="grid-two">
    <section class="panel">
      <div class="panel-head"><h2>Owner action queue</h2><span class="tag amber">${owners.length} surfaced</span></div>
      <div class="table-wrap"><table><thead><tr><th>Item</th><th>State</th><th>Disposition</th><th>Workstream</th><th>Next action</th></tr></thead>
      <tbody>${owners.length?owners.slice(0,30).map(programRow).join(""):'<tr><td colspan="5">No owner action is currently recorded.</td></tr>'}</tbody></table></div>
    </section>
    <section class="panel">
      <div class="panel-head"><h2>Active workstreams</h2><span class="tag gray">NORMALIZED</span></div>
      <div class="panel-body">${streams.length?streams.slice(0,20).map(x=>`<div class="route-row"><span>${e(x.name)}</span><span class="mono">${num(x.count)}</span></div>`).join(""):'<p class="small-text muted">Sync to calculate workstreams.</p>'}</div>
    </section>
  </div>
  <section class="panel section-gap">
    <div class="panel-head"><h2>V1 critical / supporting surface</h2><span class="tag teal">${critical.length} visible</span></div>
    <div class="table-wrap"><table><thead><tr><th>Item</th><th>State</th><th>Disposition</th><th>Workstream</th><th>Next action</th></tr></thead>
    <tbody>${critical.length?critical.slice(0,80).map(programRow).join(""):'<tr><td colspan="5">No V1 items classified yet.</td></tr>'}</tbody></table></div>
  </section>
  <section class="panel section-gap">
    <div class="panel-head"><h2>Full tracked inventory</h2><span class="tag gray">${tracked.length} shown</span></div>
    <div class="table-wrap"><table><thead><tr><th>Item</th><th>State</th><th>Disposition</th><th>Workstream</th><th>Next action</th></tr></thead>
    <tbody>${tracked.length?tracked.map(programRow).join(""):'<tr><td colspan="5">No tracked program items.</td></tr>'}</tbody></table></div>
  </section>`;
}

async function programAction(el){
  const a=el.dataset.action;
  if(a==="program-refresh"){
    await refreshProgram();
    if(state.view==="program")render();
    return;
  }
  if(a==="program-sync"){
    await queue("/api/program/sync",{repo:state.program?.repo||"ninja-ops-guy/residual-agent-harness"});
    toast("Program sync started. GitHub remains observational input.");
    return;
  }
  if(a==="program-item"){
    const item=await api("/api/program/item?"+new URLSearchParams({id:el.dataset.id}));
    programItemDialog(item);
    return;
  }
  if(a==="program-set"){
    const patch={};
    if(el.dataset.state)patch.state=el.dataset.state;
    if(el.dataset.disposition)patch.v1_disposition=el.dataset.disposition;
    if(el.dataset.ownerAction!==undefined)patch.owner_action_required=el.dataset.ownerAction==="true";
    await api("/api/program/item",{item_id:el.dataset.id,patch,bind_current_head:true});
    await refreshProgram();
    const item=await api("/api/program/item?"+new URLSearchParams({id:el.dataset.id}));
    programItemDialog(item);
    if(state.view==="program")render();
    toast("Program state updated with current source binding.");
  }
}

async function programJobCompleted(job){
  if(job.kind!=="program-sync")return;
  await refreshProgram();
  if(state.view==="program")render();
}
