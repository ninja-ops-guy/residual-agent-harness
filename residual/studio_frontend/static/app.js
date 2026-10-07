"use strict";
/* Residual Studio frontend — stub API client. No build step.
 * Surfaces per docs/studio/STUDIO_SPECS.md:
 * requirement graph (STUDIO-R5/R7), swarm panel (STUDIO-R25/R33),
 * evidence receipts (STUDIO-R11), worker timeline, HITL approvals (STUDIO-R7).
 */
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const state = {view:"plan", plan:null, contracts:[], receipts:[], swarm:null, approvals:[], timeline:[], selected:null};

function toast(text, error=false){
  const el = document.createElement("div");
  el.className = "toast" + (error ? " error" : "");
  el.textContent = text;
  $("#toasts").append(el);
  setTimeout(() => el.remove(), error ? 12000 : 6000);
}

async function api(path, data){
  const res = await fetch(path, data === undefined ? {} : {
    method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(data)
  });
  const body = await res.json().catch(() => ({error:"bad response"}));
  if(!res.ok) throw Error(body.error || `HTTP ${res.status}`);
  return body;
}

function badge(status){
  const map = {accepted:"", approved:"", pass:"", ok:"", completed:"", pending:"amber",
    rejected:"red", fail:"red", contract_violation:"red", blocked:"amber", high:"red", medium:"amber", low:"gray"};
  return `<span class="tag ${map[status] ?? "gray"}">${esc(status)}</span>`;
}
const time = s => s ? new Date(s).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit",second:"2-digit"}) : "—";

/* ---------- Requirement graph (SVG, layered DAG) ---------- */
function layoutGraph(reqs){
  const depth = {};
  const dep = id => (reqs.find(r => r.id === id)?.dependencies || []);
  const calc = id => {
    if(depth[id] !== undefined) return depth[id];
    const ds = dep(id);
    depth[id] = ds.length ? Math.max(...ds.map(calc)) + 1 : 0;
    return depth[id];
  };
  reqs.forEach(r => calc(r.id));
  const lanes = {};
  reqs.forEach(r => {
    const d = depth[r.id];
    lanes[d] = lanes[d] || 0;
    r._x = 60 + d * 240;
    r._y = 40 + lanes[d] * 90;
    lanes[d]++;
  });
  return {w: 120 + (Math.max(...Object.values(depth)) + 1) * 240, h: 60 + Math.max(...Object.values(lanes)) * 90};
}

function graphView(){
  const p = state.plan, reqs = p.requirements, crit = new Set(p.critical_path || []);
  const {w, h} = layoutGraph(reqs);
  const byId = Object.fromEntries(reqs.map(r => [r.id, r]));
  let edges = "", nodes = "";
  for(const r of reqs){
    for(const d of r.dependencies){
      const a = byId[d];
      if(!a) continue;
      const isCrit = crit.has(r.id) && crit.has(d);
      edges += `<path class="edge${isCrit ? " critical" : ""}" d="M ${a._x+170} ${a._y+20} C ${a._x+205} ${a._y+20}, ${r._x-35} ${r._y+20}, ${r._x} ${r._y+20}"/>`;
    }
    nodes += `<g class="req-node${crit.has(r.id) ? " critical" : ""}${state.selected === r.id ? " selected" : ""}" data-req="${esc(r.id)}" transform="translate(${r._x},${r._y})">
      <rect width="170" height="40"></rect>
      <text x="10" y="17" font-weight="600">${esc(r.id)}</text>
      <text x="10" y="32" fill="#8aa5ae">${esc(r.title.slice(0, 24))}</text></g>`;
  }
  const sel = byId[state.selected];
  const detail = sel ? `<section class="panel"><h2>${esc(sel.id)} — ${esc(sel.title)}</h2>
    <dl class="detail">
      <dt>Description</dt><dd>${esc(sel.description)}</dd>
      <dt>Acceptance</dt><dd>${sel.acceptance.map(a => `<div>▢ ${esc(a)}</div>`).join("")}</dd>
      <dt>Dependencies</dt><dd>${sel.dependencies.length ? sel.dependencies.map(esc).join(", ") : "none"}</dd>
      <dt>Swarm / risk</dt><dd>${esc(sel.swarm)} · ${badge(sel.risk)}</dd>
      <dt>Provenance</dt><dd class="mono">intent span [${sel.provenance.intent_span.join(", ")}]</dd>
    </dl></section>` : "";
  return `<span class="eyebrow">Layer 3 · Requirement compiler output</span><h1>Requirement graph</h1>
    <p class="sub">${esc(p.intent)}</p>
    <div class="stats">
      <div class="stat"><div class="label">Requirements</div><div class="value">${reqs.length}</div></div>
      <div class="stat"><div class="label">Swarms</div><div class="value">${p.swarms.length}</div></div>
      <div class="stat"><div class="label">Parallelism est.</div><div class="value">${p.estimated_parallelism}×</div></div>
      <div class="stat"><div class="label">Serial estimate</div><div class="value">${p.serial_estimate_minutes}<em> min</em></div></div>
    </div>
    ${p.risk_flags.length ? `<div class="callout">⚠ Risk flags: ${p.risk_flags.map(esc).join(" · ")}</div>` : ""}
    <section class="panel"><h2>Dependency DAG <span class="sub" style="display:inline">amber = critical path · click a node</span></h2>
      <svg viewBox="0 0 ${w} ${h}" width="100%" role="img" aria-label="Requirement dependency graph">
        <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#5b6f78"/></marker></defs>
        ${edges}${nodes}</svg></section>${detail}`;
}

/* ---------- Swarm panel (STUDIO-R25 / R33) ---------- */
function swarmView(){
  const s = state.swarm, m = s.metrics;
  const cards = s.swarms.map(sw => `<section class="panel"><h2>${esc(sw.id)} ${badge(sw.state)}</h2>
    <table><tr><th>Worker</th><th>Task</th><th>Node</th><th>State</th></tr>
    ${sw.workers.map(w => `<tr><td class="mono">${esc(w.id)}</td><td class="mono">${esc(w.task_id)}</td><td class="mono">${esc(w.node_id)}</td><td>${badge(w.state)}</td></tr>`).join("")}
    </table>
    <p class="sub">ready: ${sw.ready_tasks.length} · blocked: ${sw.blocked_tasks.length}</p></section>`).join("");
  const nodes = s.nodes.map(n => `<tr><td class="mono">${esc(n.node_id)}</td><td>${n.engines.map(esc).join(", ")}</td>
    <td>${n.accelerators.length ? n.accelerators.map(esc).join(", ") : "cpu"}</td><td>${n.memory_gb} GB</td>
    <td>${n.queue_depth}</td><td>${badge(n.health)}</td><td>${esc(n.assignment)}</td></tr>`).join("");
  return `<span class="eyebrow">Layer 4 · Swarm runtime</span><h1>Swarm panel</h1>
    <p class="sub">run <span class="mono">${esc(s.run_id)}</span> · mode ${esc(s.mode)} · ${badge(s.state)}</p>
    <div class="stats">
      <div class="stat"><div class="label">Effective speedup</div><div class="value">${m.effective_speedup}×</div><small>${m.serial_estimate_minutes} min serial / ${m.actual_elapsed_minutes} min actual</small></div>
      <div class="stat"><div class="label">Coordination overhead</div><div class="value">${m.coordination_overhead_minutes}<em> min</em></div><small>method ${esc(m.overhead_methodology)}</small></div>
      <div class="stat"><div class="label">Rework rate</div><div class="value">${Math.round(m.rework_rate*100)}%</div></div>
      <div class="stat"><div class="label">Verifier rejections</div><div class="value">${Math.round(m.verifier_rejection_rate*100)}%</div><small>${m.verifier_rejections}/${m.verification_attempts} attempts</small></div>
    </div>
    <p class="sub">Critical path: ${(s.critical_path||[]).map(c => `<code>${esc(c)}</code>`).join(" → ")}</p>
    ${cards}
    <section class="panel"><h2>Cluster nodes</h2>
      <table><tr><th>Node</th><th>Engines</th><th>Accel</th><th>Mem</th><th>Queue</th><th>Health</th><th>Assignment</th></tr>${nodes}</table></section>`;
}

/* ---------- Evidence graph (receipts, STUDIO-R11/R18) ---------- */
function evidenceView(){
  const rs = state.receipts;
  const chain = rs.map(r => `<tr>
      <td class="mono">${esc(r.receipt_id)}${r.supersedes ? ` <span class="tag gray">supersedes ${esc(r.supersedes)}</span>` : ""}</td>
      <td class="mono">${esc(r.task_id)}<br><small style="color:var(--dim)">${esc(r.attempt_id)}</small></td>
      <td>${esc(r.engine)} <span class="mono">${esc(r.engine_version)}</span><br><small style="color:var(--dim)">${esc(r.node_id)}</small></td>
      <td>${Object.entries(r.requirement_verdicts).map(([k,v]) => `<code>${esc(k)}</code> ${badge(v)}`).join(" ")}</td>
      <td>${Object.entries(r.verification).map(([k,v]) => `<div>${v ? "✓" : "✗"} ${esc(k)}</div>`).join("")}</td>
      <td class="mono">${r.parent_receipts.length ? r.parent_receipts.map(esc).join(", ") : "—"}</td>
      <td>${time(r.started_at)} → ${time(r.ended_at)}</td>
      <td>${badge(r.status)}</td></tr>`).join("");
  return `<span class="eyebrow">Evidence bus · append-only receipts</span><h1>Evidence graph</h1>
    <p class="sub">${rs.length} receipts · superseding receipts reference the original; originals remain queryable (STUDIO-R18).</p>
    <section class="panel"><table><tr><th>Receipt</th><th>Task / attempt</th><th>Engine · node</th><th>Requirements</th><th>Verification</th><th>Parents</th><th>Window</th><th>Status</th></tr>${chain}</table></section>`;
}

/* ---------- Worker timeline ---------- */
function timelineView(){
  const ts = state.timeline;
  if(!ts.length) return "<div class='panel'>No attempts recorded.</div>";
  const t0 = Math.min(...ts.map(s => Date.parse(s.started_at)));
  const t1 = Math.max(...ts.map(s => Date.parse(s.ended_at)));
  const span = Math.max(t1 - t0, 1);
  const rows = ts.map(s => {
    const l = (Date.parse(s.started_at) - t0) / span * 100;
    const w = Math.max((Date.parse(s.ended_at) - Date.parse(s.started_at)) / span * 100, 1.5);
    return `<div class="tl-label"><span class="mono">${esc(s.worker_id)} · ${esc(s.attempt_id)}</span><span>${time(s.started_at)} → ${time(s.ended_at)} ${badge(s.status)}</span></div>
    <div class="bar-track"><div class="bar ${esc(s.status)}" style="left:${l}%;width:${w}%">${esc(s.task_id)}</div></div>`;
  }).join("");
  return `<span class="eyebrow">Worker execution</span><h1>Worker timeline</h1>
    <p class="sub">Attempt spans across the run window. Amber bars are rejected attempts (rework).</p>
    <section class="panel">${rows}</section>`;
}

/* ---------- Approvals (HITL gate, STUDIO-R7) ---------- */
function approvalsView(){
  const items = state.approvals.map(a => `<div class="approval-card">
    <h3>${esc(a.summary)}</h3>
    <p class="sub"><span class="mono">${esc(a.approval_id)}</span> · ${esc(a.kind)} · subject <span class="mono">${esc(a.subject)}</span> · requested ${time(a.requested_at)}</p>
    <p class="sub">binds hash <span class="mono">${esc(a.subject_hash.slice(0, 24))}…</span></p>
    ${a.status === "pending"
      ? `<div class="button-row"><button class="button primary" data-decide="approve" data-id="${esc(a.approval_id)}">Approve</button>
         <button class="button danger" data-decide="reject" data-id="${esc(a.approval_id)}">Reject</button></div>`
      : `<p>${badge(a.decision === "approve" ? "approved" : "rejected")} by ${esc(a.decided_by)} at ${time(a.decided_at)}</p>`}
  </div>`).join("");
  return `<span class="eyebrow">Human-in-the-loop</span><h1>Approvals</h1>
    <p class="sub">Plan execution and retry gates block here until a human decides (STUDIO-R7/R8). Decisions are recorded against the exact subject hash.</p>
    ${items || "<div class='panel'>No approval items.</div>"}`;
}

const views = {plan:graphView, swarm:swarmView, evidence:evidenceView, timeline:timelineView, approvals:approvalsView};

function render(){
  document.querySelectorAll("nav a").forEach(a => a.classList.toggle("active", a.dataset.view === state.view));
  const pending = state.approvals.filter(a => a.status === "pending").length;
  const b = $("#approval-badge");
  b.textContent = pending; b.classList.toggle("hidden", !pending);
  $("#main").innerHTML = views[state.view]();
}

async function load(){
  try {
    const [plan, contracts, swarm, receipts, timeline, approvals] = await Promise.all([
      api("/api/plan"), api("/api/contracts"), api("/api/swarm/status"),
      api("/api/evidence/receipts"), api("/api/workers/timeline"), api("/api/approvals")]);
    Object.assign(state, {plan, contracts, swarm, receipts, timeline, approvals});
    $("#connection").textContent = "stub API online";
    $("#connection").classList.add("ok");
  } catch(err){
    $("#connection").textContent = "stub API unreachable";
    $("#main").innerHTML = `<div class="panel"><h2>Stub API unreachable</h2><p>Start it with <code>python3 -m residual.studio_frontend.stub_server</code> and reload.</p><p class="mono">${esc(err.message)}</p></div>`;
    return;
  }
  render();
}

document.addEventListener("click", async ev => {
  const nav = ev.target.closest("nav a");
  if(nav){ state.view = nav.dataset.view; render(); return; }
  const node = ev.target.closest(".req-node");
  if(node){ state.selected = state.selected === node.dataset.req ? null : node.dataset.req; render(); return; }
  const btn = ev.target.closest("[data-decide]");
  if(btn){
    btn.disabled = true;
    try {
      await api(`/api/approvals/${btn.dataset.id}`, {decision: btn.dataset.decide, decided_by: "studio-operator"});
      toast(`Approval ${btn.dataset.decide}d`);
      state.approvals = await api("/api/approvals");
      render();
    } catch(err){ toast(err.message, true); btn.disabled = false; }
  }
});

window.addEventListener("hashchange", () => {
  const v = location.hash.slice(1);
  if(views[v]){ state.view = v; render(); }
});
state.view = views[location.hash.slice(1)] ? location.hash.slice(1) : "plan";
load();
