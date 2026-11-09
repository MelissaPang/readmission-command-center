// Readmission Command Center: frontend (vanilla JS + Chart.js)
const $ = (s) => document.querySelector(s);
const api = async (path, opts = {}) => {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
};
const pct = (v, d = 1) => (v == null ? "–" : `${Number(v).toFixed(d)}%`);
const usd = (v) => (v == null ? "–" : "$" + Math.round(v).toLocaleString());
const usdK = (v) => (v == null ? "–" : v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : `$${Math.round(v / 1e3)}K`);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const charts = {};
function chart(id, cfg) { charts[id]?.destroy(); charts[id] = new Chart(document.getElementById(id), cfg); }
function kpi(v, l, d = "", cls = "") { return `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div><div class="d ${cls}">${d}</div></div>`; }

// ---------------------------------------------------------------- tabs
document.querySelectorAll("#tabs button").forEach((b) =>
  b.addEventListener("click", () => {
    document.querySelectorAll("#tabs button").forEach((x) => x.classList.toggle("active", x === b));
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.id === b.dataset.tab));
    loaders[b.dataset.tab]?.();
  })
);

// ---------------------------------------------------------- unit trends
async function loadTrends() {
  const [hf, all, weekly, gap, events] = await Promise.all([
    api("/api/units/summary?condition=HF"), api("/api/units/summary?condition=ALL"),
    api("/api/units/CUMC-6N/weekly?condition=HF"), api("/api/followup-gap?unit_id=CUMC-6N&condition=HF"), api("/api/staffing-events"),
  ]);
  const six = hf.find((u) => u.unit_id === "CUMC-6N") || {};
  const others = all.filter((u) => u.unit_id !== "CUMC-6N");
  const maxOther = Math.max(...others.map((u) => Math.abs(u.delta_pts ?? 0)));
  const since = (t) => gap.find((g) => g.period === "since_2026-06-19" && g.discharge_day_type.startsWith(t)) || {};
  $("#trend-kpis").innerHTML =
    kpi(pct(six.last_20w_rate_pct), "6 North HF readmission, last 20 weeks", `from ${pct(six.prior_20w_rate_pct)} (+${(six.delta_pts ?? 0).toFixed(1)} pts)`, "up") +
    kpi(`±${maxOther.toFixed(1)} pts`, "Largest change at any other unit (all-cause)", "every other unit stable", "down") +
    kpi(pct(since("Weekend").fu7_booked_pct, 0), "6N weekend HF discharges with 7-day follow-up", `vs ${pct(since("Weekday").fu7_booked_pct, 0)} on weekdays (since 2026-06-19)`, "up") +
    kpi(String(events.length), "Operational changes logged", events.filter((e) => e.scope_id.startsWith("CUMC")).map((e) => e.event_date).join(", "));

  // weekly line (4-week rolling)
  const labels = weekly.map((r) => r.discharge_week);
  const roll = weekly.map((_, i) => {
    const s = weekly.slice(Math.max(0, i - 3), i + 1);
    const n = s.reduce((a, r) => a + r.index_admissions, 0), k = s.reduce((a, r) => a + r.readmissions, 0);
    return n ? (100 * k) / n : null;
  });
  const evIdx = events.filter((e) => e.scope_id.startsWith("CUMC")).map((e) => ({ e, i: labels.findIndex((l) => l >= e.event_date) }));
  chart("weeklyChart", {
    type: "line",
    data: { labels, datasets: [
      { label: "Weekly rate", data: weekly.map((r) => r.readmit_rate_pct), borderColor: "#b9c6d2", pointRadius: 0, borderWidth: 1 },
      { label: "4-week rolling rate", data: roll, borderColor: "#d9534f", pointRadius: 0, borderWidth: 2.5, tension: 0.3 },
    ] },
    options: { scales: { y: { title: { display: true, text: "% readmitted ≤30d" }, min: 0 } }, plugins: { legend: { position: "bottom" } } },
    plugins: [{ id: "events", afterDraw(c) {
      const { ctx, chartArea: a, scales: { x } } = c;
      evIdx.forEach(({ e, i }) => { if (i < 0) return; const px = x.getPixelForValue(i);
        ctx.save(); ctx.setLineDash([4, 4]); ctx.strokeStyle = "#0f5c7a"; ctx.beginPath(); ctx.moveTo(px, a.top); ctx.lineTo(px, a.bottom); ctx.stroke();
        ctx.fillStyle = "#0f5c7a"; ctx.font = "10px sans-serif"; ctx.fillText(e.event_date, px + 3, a.top + 10); ctx.restore(); });
    } }],
  });
  const per = ["before_2026-06-19", "since_2026-06-19"];
  const val = (p, t) => (gap.find((g) => g.period === p && g.discharge_day_type.startsWith(t)) || {}).fu7_booked_pct;
  chart("gapChart", {
    type: "bar",
    data: { labels: ["Before 2026-06-19", "Since 2026-06-19"], datasets: [
      { label: "Weekday (Mon–Thu)", data: per.map((p) => val(p, "Weekday")), backgroundColor: "#0f5c7a" },
      { label: "Weekend (Fri–Sun)", data: per.map((p) => val(p, "Weekend")), backgroundColor: "#d9534f" },
    ] },
    options: { scales: { y: { min: 0, max: 100, title: { display: true, text: "% with 7-day follow-up booked" } } }, plugins: { legend: { position: "bottom" } } },
  });
  renderUnitTable();
}
async function renderUnitTable() {
  const rows = await api(`/api/units/summary?condition=${$("#unitCond").value}`);
  $("#unitTable").innerHTML = `<tr><th>Hospital</th><th>Unit</th><th>Index (prior)</th><th>Prior 20w</th><th>Index (last)</th><th>Last 20w</th><th>Change</th></tr>` +
    rows.map((r) => `<tr class="${r.unit_id === "CUMC-6N" ? "hl" : ""}"><td>${r.hospital_id}</td><td>${esc(r.unit_name)}</td><td>${r.prior_20w_index}</td>
      <td>${pct(r.prior_20w_rate_pct)}</td><td>${r.last_20w_index}</td><td>${pct(r.last_20w_rate_pct)}</td>
      <td class="${r.delta_pts > 1.5 ? "up" : ""}"><b>${r.delta_pts > 0 ? "+" : ""}${(r.delta_pts ?? 0).toFixed(1)} pts</b></td></tr>`).join("");
}
$("#unitCond").addEventListener("change", renderUnitTable);

// ------------------------------------------------------------- worklist
let unitsLoaded = false;
async function loadWorklist() {
  if (!unitsLoaded) {
    const units = await api("/api/units/summary?condition=ALL");
    $("#wlUnit").innerHTML += units.sort((a, b) => a.unit_id.localeCompare(b.unit_id)).map((u) => `<option value="${u.unit_id}">${esc(u.unit_name)} (${u.hospital_id})</option>`).join("");
    unitsLoaded = true;
  }
  const p = new URLSearchParams();
  if ($("#wlHospital").value) p.set("hospital_id", $("#wlHospital").value);
  if ($("#wlUnit").value) p.set("unit_id", $("#wlUnit").value);
  if ($("#wlTier").value) p.set("risk_tier", $("#wlTier").value);
  if ($("#wlNoFu").checked) p.set("no_followup", "true");
  const rows = await api(`/api/worklist?${p}`);
  $("#wlTable").innerHTML = `<tr><th>Risk</th><th>Patient</th><th>Unit</th><th>Cond.</th><th>Discharged</th><th>7-day FU</th><th>Note flags (AI)</th><th>Top drivers</th><th>Plan</th></tr>` +
    rows.map((r) => `<tr class="click" data-id="${r.encounter_id}">
      <td><span class="pill ${r.risk_tier}">${r.risk_tier}</span> ${(100 * r.risk_score).toFixed(0)}%</td>
      <td><b>${esc(r.last_name)}, ${esc(r.first_name)}</b><br><small>${esc(r.mrn)} · ${r.age}y</small></td>
      <td>${esc(r.unit_name)}<br><small>${r.hospital_id}</small></td><td>${r.condition}</td>
      <td>${r.discharge_ts.slice(0, 10)} ${r.weekend_discharge ? "<small>(wknd)</small>" : ""}<br><small>${r.days_since_discharge} days ago</small></td>
      <td>${r.fu7_booked ? "✅" : "❌"}</td>
      <td>${r.ai_lives_alone ? '<span class="pill flag">lives alone</span> ' : ""}${r.ai_transport_barrier ? '<span class="pill flag">transport</span>' : ""}</td>
      <td><small>${esc(r.driver_1 || "")}${r.driver_2 ? "<br>" + esc(r.driver_2) : ""}</small></td>
      <td>${r.plan_status ? `<span class="pill ${r.plan_status}">${r.plan_status}</span>` : ""}</td></tr>`).join("");
  document.querySelectorAll("#wlTable tr.click").forEach((tr) => tr.addEventListener("click", () => openPatient(tr.dataset.id)));
}
["#wlHospital", "#wlUnit", "#wlTier", "#wlNoFu"].forEach((s) => $(s).addEventListener("change", loadWorklist));

async function openPatient(id) {
  $("#drawer").classList.remove("hidden");
  $("#drawerBody").innerHTML = "Loading…";
  const { patient: p, plans, tasks } = await api(`/api/patients/${id}`);
  const drivers = [1, 2, 3].map((i) => p[`driver_${i}`] ? `<li>${esc(p[`driver_${i}`])} <small>(+${(100 * p[`driver_${i}_impact`]).toFixed(1)} pts)</small></li>` : "").join("");
  $("#drawerBody").innerHTML = `
    <h2 style="margin:0">${esc(p.first_name)} ${esc(p.last_name)}</h2>
    <div class="hint">${esc(p.mrn)} · ${p.age}y · ${esc(p.primary_language)} · ☎ ${esc(p.home_phone)}</div>
    <p><b>${esc(p.principal_dx_desc)}</b><br>${esc(p.unit_name)}, ${esc(p.hospital_name)} · discharged ${p.discharge_ts.slice(0, 16).replace("T", " ")} (${p.discharge_dow}) to ${p.discharge_disposition}</p>
    <div class="kpis small">${kpi(`${(100 * p.risk_score).toFixed(0)}%`, "30-day readmission risk", `<span class="pill ${p.risk_tier}">${p.risk_tier}</span> · model v${p.model_version}`)}
      ${kpi(p.fu7_booked ? "Booked" : "Not booked", "7-day follow-up", p.first_followup_ts ? p.first_followup_ts.slice(0, 10) : "")}</div>
    <h4>Why the model flags this patient</h4><ul>${drivers || "<li>No single dominant driver</li>"}</ul>
    <h4>From the discharge note (AI Functions)</h4>
    <div>${p.ai_lives_alone ? '<span class="pill flag">lives alone / no caregiver</span> ' : ""}${p.ai_transport_barrier ? '<span class="pill flag">transportation barrier</span> ' : ""}<span class="pill">${esc(p.ai_followup_status)}</span></div>
    ${p.ai_evidence ? `<p class="evidence">“${esc(p.ai_evidence)}”</p>` : ""}
    <h4>Recommended actions</h4><p>${esc(p.recommended_actions || "–")}</p>
    <h4>Transition plan</h4>
    <div id="plans">${plans.map(planHtml).join("") || '<p class="hint">No plan yet.</p>'}</div>
    <button id="draftBtn">✨ Draft transition plan with AI</button>
    ${tasks.length ? `<h4>Outreach tasks</h4><ul>${tasks.map((t) => `<li>${esc(t.description)}: <b>${t.status}</b> (due ${t.due_ts.slice(0, 10)})</li>`).join("")}</ul>` : ""}`;
  $("#draftBtn").onclick = async () => {
    $("#draftBtn").disabled = true; $("#draftBtn").textContent = "Drafting with Claude…";
    try { await api(`/api/patients/${id}/draft-plan`, { method: "POST" }); openPatient(id); }
    catch (e) { $("#draftBtn").outerHTML = `<p class="err">${esc(e.message)}</p>`; }
  };
  document.querySelectorAll(".approveBtn").forEach((b) => (b.onclick = async () => {
    b.disabled = true;
    const txt = document.getElementById(`txt-${b.dataset.plan}`).value;
    await api(`/api/plans/${b.dataset.plan}/approve`, { method: "POST", body: JSON.stringify({ final_text: txt }) });
    openPatient(id); loadWorklist();
  }));
  document.querySelectorAll(".rejectBtn").forEach((b) => (b.onclick = async () => {
    await api(`/api/plans/${b.dataset.plan}/reject`, { method: "POST" }); openPatient(id);
  }));
}
function planHtml(pl) {
  if (pl.status === "draft")
    return `<div class="plan"><span class="pill draft">draft</span> <small>${esc(pl.model_endpoint)} · ${pl.created_ts.slice(0, 16)}</small>
      <textarea id="txt-${pl.plan_id}">${esc(pl.draft_text)}</textarea>
      <div class="row"><button class="approveBtn" data-plan="${pl.plan_id}">Approve plan &amp; create outreach tasks</button>
      <button class="secondary rejectBtn" data-plan="${pl.plan_id}">Reject</button></div></div>`;
  return `<div class="plan"><span class="pill ${pl.status}">${pl.status}</span> <small>${pl.approved_by ? "by " + esc(pl.approved_by) + " · " + (pl.approved_ts || "").slice(0, 16) : ""}</small>
    <div>${marked.parse(pl.final_text || pl.draft_text)}</div></div>`;
}
$("#drawerClose").onclick = () => $("#drawer").classList.add("hidden");

// ----------------------------------------------------------------- HRRP
let hrrpData;
async function loadHrrp() {
  hrrpData = await api("/api/hrrp");
  const c = hrrpData.hospitals.find((h) => h.hospital_id === "CUMC");
  const hf = hrrpData.conditions.find((x) => x.hospital_id === "CUMC" && x.hrrp_condition === "HF");
  $("#hrrp-kpis").innerHTML =
    kpi(usdK(c.estimated_penalty), "CUMC estimated HRRP penalty", c.at_cap ? `at the 3% cap (uncapped ${usdK(c.uncapped_penalty)})` : "") +
    kpi(usdK(hf.penalty_contribution), "Heart-failure line (largest)", `${hf.readmissions} readmissions / ${hf.index_admissions} index admissions`) +
    kpi(hf.err.toFixed(2), "CUMC HF excess readmission ratio", `observed ${pct(100 * hf.observed_rate)} vs expected ${pct(100 * hf.expected_readmission_rate)}`, "up") +
    kpi(usdK(hrrpData.hospitals.reduce((a, h) => a + h.estimated_penalty, 0)), "Cedarbrook Health system total", hrrpData.hospitals.map((h) => `${h.hospital_id} ${usdK(h.estimated_penalty)}`).join(" · "));
  const cumc = hrrpData.conditions.filter((x) => x.hospital_id === "CUMC");
  chart("penaltyChart", {
    type: "bar",
    data: { labels: cumc.map((x) => x.hrrp_condition), datasets: [{ label: "Penalty contribution ($)", data: cumc.map((x) => x.penalty_contribution),
      backgroundColor: cumc.map((x) => (x.hrrp_condition === "HF" ? "#d9534f" : "#0f5c7a")) }] },
    options: { indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { ticks: { callback: (v) => usdK(v) } } } },
  });
  $("#errTable").innerHTML = `<tr><th>Hospital</th><th>Condition</th><th>Index adm.</th><th>Readmits</th><th>Observed</th><th>Expected</th><th>ERR</th><th>Penalty contribution</th></tr>` +
    hrrpData.conditions.map((x) => `<tr class="${x.err > 1 ? "" : ""}"><td>${x.hospital_id}</td><td>${x.hrrp_condition}</td><td>${x.index_admissions}</td><td>${x.readmissions}</td>
      <td>${pct(100 * x.observed_rate)}</td><td>${pct(100 * x.expected_readmission_rate)}</td><td class="${x.err > 1 ? "up" : "down"}"><b>${x.err.toFixed(3)}</b></td><td>${usd(x.penalty_contribution)}</td></tr>`).join("");
  loadWhatif();
}
let wiRows = [];
async function loadWhatif() {
  wiRows = await api(`/api/hrrp/whatif?scope=${encodeURIComponent($("#wiScope").value)}`);
  renderWhatif();
}
function renderWhatif() {
  const t = +$("#wiTarget").value; $("#wiTargetLbl").textContent = `${t}%`;
  const r = wiRows.find((x) => x.fu7_target_pct === t); if (!r) return;
  $("#wi-kpis").innerHTML =
    kpi(`${r.current_fu7_pct}%`, "Booked today (trailing 12m)", `${r.booked_12m} of ${r.discharges_12m} discharges`) +
    kpi(r.additional_followups.toFixed(0), "Additional follow-ups needed") +
    kpi(`≈ ${r.readmissions_avoided.toFixed(1)}`, "Readmissions avoided / 12 months", "", "down") +
    kpi(`${r.hf_err_current.toFixed(2)} → ${r.hf_err_scenario.toFixed(2)}`, "CUMC HF ERR", "", "down") +
    kpi(usdK(r.penalty_saved), "HRRP penalty saved", `${usdK(r.penalty_current)} → ${usdK(r.penalty_scenario)}`, "down");
  $("#wiMethod").textContent = `Deterministic: additional follow-ups × (HF readmit rate without 7-day FU ${pct(100 * r.rate_no_fu7)} − with ${pct(100 * r.rate_with_fu7)}). ERR and penalty recomputed with the 3% cap.`;
}
$("#wiTarget").addEventListener("input", renderWhatif);
$("#wiScope").addEventListener("change", loadWhatif);

// -------------------------------------------------------------- outreach
async function loadOutreach() {
  const rows = await api("/api/outreach-tasks?status=open");
  $("#taskTable").innerHTML = `<tr><th>Due</th><th>Task</th><th>Patient</th><th>Unit</th><th>Risk</th><th>Phone</th><th></th></tr>` +
    (rows.map((t) => `<tr><td>${t.due_ts.slice(0, 10)}</td><td>${esc(t.description)}</td><td>${esc(t.last_name)}, ${esc(t.first_name)}</td>
      <td>${esc(t.unit_name)}</td><td><span class="pill ${t.risk_tier}">${t.risk_tier}</span></td><td>${esc(t.home_phone)}</td>
      <td><button data-task="${t.task_id}" class="doneBtn">Mark done</button></td></tr>`).join("") || `<tr><td colspan="7" class="hint">No open tasks. Approve a transition plan in the worklist to create some.</td></tr>`);
  document.querySelectorAll(".doneBtn").forEach((b) => (b.onclick = async () => { await api(`/api/outreach-tasks/${b.dataset.task}/complete`, { method: "POST" }); loadOutreach(); }));
}

// ----------------------------------------------------------------- genie
let convId = null;
const SAMPLES = ["Which unit's HF readmission rate rose the most in the last 20 weeks?",
  "Compare 7-day follow-up booking on 6 North for weekend vs weekday HF discharges since 2026-06-19",
  "What is CUMC's HF ERR and how much of the HRRP penalty comes from heart failure?",
  "Do HF patients who live alone readmit more often?"];
$("#genieChips").innerHTML = SAMPLES.map((s) => `<button type="button">${esc(s)}</button>`).join("");
document.querySelectorAll("#genieChips button").forEach((b) => (b.onclick = () => { $("#genieQ").value = b.textContent; $("#genieForm").requestSubmit(); }));
$("#genieForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = $("#genieQ").value.trim(); if (!q) return;
  $("#genieQ").value = "";
  $("#chat").insertAdjacentHTML("beforeend", `<div class="msg user"><div class="b">${esc(q)}</div></div><div class="msg bot" id="pending"><div class="b">Genie is thinking…</div></div>`);
  try {
    const r = await api("/api/genie/ask", { method: "POST", body: JSON.stringify({ question: q, conversation_id: convId }) });
    convId = r.conversation_id;
    const table = r.columns.length ? `<table><tr>${r.columns.map((c) => `<th>${esc(c)}</th>`).join("")}</tr>${r.rows.slice(0, 15).map((row) => `<tr>${row.map((v) => `<td>${esc(v)}</td>`).join("")}</tr>`).join("")}</table>` : "";
    $("#pending").outerHTML = `<div class="msg bot"><div class="b">${esc(r.text || r.status)}${table}${r.sql ? `<details><summary>SQL</summary><pre>${esc(r.sql)}</pre></details>` : ""}</div></div>`;
  } catch (err) { $("#pending").outerHTML = `<div class="msg bot"><div class="b err">${esc(err.message)}</div></div>`; }
  $("#chat").scrollTop = 1e9;
});

const loaders = { trends: loadTrends, worklist: loadWorklist, hrrp: loadHrrp, outreach: loadOutreach };
loadTrends().catch((e) => ($("#trend-kpis").innerHTML = `<p class="err">${esc(e.message)}</p>`));
