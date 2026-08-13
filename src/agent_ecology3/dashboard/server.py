"""Minimal AE3 dashboard API and single-page status UI."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

_DASHBOARD_HTML = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <link rel=\"icon\" href=\"data:,\" />
  <title>Agent Ecology 3 Review</title>
  <style>
    :root {
      --bg: #0f1420;
      --panel: #171f31;
      --panel-2: #1d2840;
      --text: #e8eefc;
      --muted: #9fb1d1;
      --accent: #51c4a8;
      --warn: #f2c14e;
      --danger: #e76f51;
      --mono: "IBM Plex Mono", "Consolas", monospace;
      --sans: "IBM Plex Sans", "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: var(--sans);
      color: var(--text);
      background:
        radial-gradient(1200px 600px at 90% -10%, rgba(81,196,168,.20), transparent 60%),
        radial-gradient(1000px 500px at -10% 120%, rgba(90,126,255,.15), transparent 55%),
        var(--bg);
    }
    .wrap {
      max-width: 1180px;
      margin: 0 auto;
      padding: 20px;
      display: grid;
      gap: 16px;
    }
    .top {
      background: linear-gradient(140deg, var(--panel), var(--panel-2));
      border: 1px solid rgba(255,255,255,.08);
      border-radius: 14px;
      padding: 16px;
      display: grid;
      gap: 10px;
    }
    .title {
      margin: 0;
      font-size: clamp(24px, 4vw, 38px);
      letter-spacing: -.02em;
    }
    .eyebrow { color: var(--accent); font: 700 12px var(--mono); letter-spacing: .12em; text-transform: uppercase; }
    .subtitle { margin: 0; color: var(--muted); max-width: 780px; line-height: 1.5; }
    .status {
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
      color: var(--muted);
      font-size: 14px;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(255,255,255,.06);
      color: var(--text);
      font-size: 12px;
    }
    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--accent);
    }
    .danger { background: var(--danger); }
    .warn { background: var(--warn); }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    .review { display: none; gap: 16px; }
    .review.visible { display: grid; }
    .verdict {
      padding: 16px 18px;
      border-radius: 12px;
      background: rgba(81,196,168,.10);
      border-left: 4px solid var(--accent);
      line-height: 1.5;
    }
    .verdict strong { display: block; margin-bottom: 4px; }
    .condition-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .condition-card, .review-section {
      background: var(--panel);
      border: 1px solid rgba(255,255,255,.08);
      border-radius: 14px;
      padding: 16px;
    }
    .condition-card h2, .review-section h2 { margin: 0 0 4px; font-size: 18px; }
    .condition-card .intent { color: var(--muted); min-height: 42px; line-height: 1.4; }
    .metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 14px 0; }
    .metric { background: rgba(255,255,255,.045); padding: 10px; border-radius: 9px; }
    .metric b { display: block; font-size: 20px; }
    .metric span { color: var(--muted); font-size: 11px; }
    .mix { display: flex; flex-wrap: wrap; gap: 7px; }
    .chip { display: inline-flex; padding: 5px 8px; border-radius: 999px; background: rgba(117,167,255,.13); color: #c9dcff; font: 12px var(--mono); }
    .chip.fail { background: rgba(231,111,81,.17); color: #ffb19d; }
    .economic-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 12px; }
    .economic-grid .metric { min-height: 70px; }
    .timeline { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .timeline th { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .07em; text-align: left; }
    .timeline th, .timeline td { padding: 8px; border-bottom: 1px solid rgba(255,255,255,.07); }
    .timeline td:first-child { width: 42px; color: var(--muted); font: 12px var(--mono); }
    .actor { color: var(--muted); font-size: 11px; margin-right: 6px; }
    .quiet { color: var(--muted); line-height: 1.45; }
    details.advanced { background: rgba(255,255,255,.025); border: 1px solid rgba(255,255,255,.08); border-radius: 12px; padding: 12px 14px; }
    details.advanced summary { cursor: pointer; color: var(--muted); }
    .advanced-body { display: grid; gap: 12px; margin-top: 14px; }
    .advanced .panel { min-height: 240px; }
    .live { display: grid; gap: 16px; }
    .live.hidden { display: none; }
    .workspace-nav { display: none; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
    .workspace-nav.visible { display: flex; }
    .tabs { display: flex; gap: 6px; padding: 4px; border-radius: 10px; background: rgba(255,255,255,.04); }
    .tab { color: var(--muted); background: transparent; }
    .tab.active { color: #06110e; background: var(--accent); }
    .condition-picker { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 13px; }
    .operator { display: none; gap: 16px; }
    .operator.visible { display: grid; }
    .replay {
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 12px;
      align-items: center;
      background: var(--panel);
      border: 1px solid rgba(255,255,255,.08);
      border-radius: 14px;
      padding: 14px 16px;
    }
    input[type=range] { width: 100%; accent-color: var(--accent); }
    .turn-label { min-width: 100px; color: var(--muted); font: 12px var(--mono); text-align: right; }
    .operator-grid { display: grid; grid-template-columns: minmax(320px, .8fr) minmax(420px, 1.2fr); gap: 16px; }
    .operator-panel { min-height: 0; }
    .panel-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
    .panel-heading h2 { color: var(--text); font-size: 18px; text-transform: none; letter-spacing: 0; }
    .count { color: var(--muted); font: 12px var(--mono); }
    .agent-list { display: grid; gap: 10px; }
    .agent-card { border: 1px solid rgba(255,255,255,.08); background: rgba(255,255,255,.035); border-radius: 10px; padding: 12px; }
    .agent-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 9px; }
    .agent-head strong { font: 15px var(--mono); }
    .agent-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
    .agent-stat { color: var(--muted); font-size: 11px; }
    .agent-stat b { color: var(--text); display: block; font-size: 15px; margin-bottom: 2px; }
    .activity-list { display: grid; gap: 7px; max-height: 430px; overflow: auto; padding-right: 3px; }
    .activity-item { display: grid; grid-template-columns: 32px 72px 1fr auto; gap: 8px; align-items: center; padding: 9px; border-radius: 8px; background: rgba(255,255,255,.035); }
    .activity-item.failed { background: rgba(231,111,81,.10); }
    .activity-turn { color: var(--muted); font: 11px var(--mono); }
    .activity-agent { color: #c9dcff; font: 11px var(--mono); }
    .activity-text { font-size: 13px; }
    .artifact-link { color: var(--accent); cursor: pointer; text-decoration: underline; text-decoration-color: rgba(81,196,168,.35); }
    .result { font-size: 11px; color: var(--accent); }
    .result.failed { color: #ffb19d; }
    .artifact-toolbar { display: flex; gap: 8px; flex-wrap: wrap; }
    .search { flex: 1; min-width: 220px; background: var(--panel-2); color: var(--text); border: 1px solid rgba(255,255,255,.15); border-radius: 8px; padding: 8px 10px; }
    .artifact-table { width: 100%; border-collapse: collapse; }
    .artifact-table th { color: var(--muted); font-size: 11px; text-align: left; text-transform: uppercase; letter-spacing: .06em; }
    .artifact-table th, .artifact-table td { padding: 9px 8px; border-bottom: 1px solid rgba(255,255,255,.07); }
    .artifact-table tbody tr { cursor: pointer; }
    .artifact-table tbody tr:hover { background: rgba(81,196,168,.07); }
    .artifact-table td { font-size: 13px; }
    .empty { color: var(--muted); padding: 18px 4px; }
    .modal-backdrop { display: none; position: fixed; inset: 0; z-index: 20; background: rgba(3,7,14,.78); padding: 5vh 20px; }
    .modal-backdrop.visible { display: grid; place-items: center; }
    .modal { width: min(780px, 100%); max-height: 90vh; overflow: auto; background: var(--panel); border: 1px solid rgba(255,255,255,.14); border-radius: 14px; padding: 18px; box-shadow: 0 24px 80px rgba(0,0,0,.5); }
    .modal-head { display: flex; justify-content: space-between; gap: 12px; align-items: start; }
    .modal h2 { margin: 0; font: 20px var(--mono); }
    .modal-meta { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }
    .artifact-content { background: #0c111c; border-radius: 9px; padding: 14px; max-height: 50vh; overflow: auto; }
    .panel {
      background: var(--panel);
      border: 1px solid rgba(255,255,255,.08);
      border-radius: 14px;
      padding: 14px;
      min-height: 360px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .panel h2 {
      margin: 0;
      font-size: 15px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: .08em;
    }
    pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font: 12px/1.45 var(--mono);
      color: #dce8ff;
      overflow: auto;
      flex: 1;
    }
    .actions { display: flex; gap: 8px; flex-wrap: wrap; }
    .review-picker { display: none; align-items: center; gap: 8px; color: var(--muted); }
    select { background: var(--panel-2); color: var(--text); border: 1px solid rgba(255,255,255,.15); border-radius: 8px; padding: 7px 10px; }
    button {
      border: 0;
      border-radius: 8px;
      padding: 8px 12px;
      font: 13px var(--sans);
      cursor: pointer;
      color: #06110e;
      background: var(--accent);
    }
    button.secondary { background: #8fa4cc; color: #0d1628; }
    button.danger { background: var(--danger); color: #fff; }
    button:disabled { cursor: not-allowed; opacity: .45; }
    @media (max-width: 900px) {
      .grid, .condition-grid { grid-template-columns: 1fr; }
      .economic-grid { grid-template-columns: 1fr 1fr; }
      .operator-grid { grid-template-columns: 1fr; }
      .timeline th, .timeline td { padding: 6px 4px; }
    }
  </style>
</head>
<body>
  <div class=\"wrap\">
    <section class=\"top\">
      <div class=\"eyebrow\" id=\"eyebrow\">Live observability</div>
      <h1 class=\"title\" id=\"pageTitle\">Agent Ecology 3</h1>
      <p class=\"subtitle\" id=\"pageSubtitle\">Runtime state and recent events.</p>
      <div class=\"status\" id=\"statusLine\">loading...</div>
      <div class=\"actions\" id=\"liveControls\">
        <button id=\"resumeButton\" onclick=\"control('resume')\">Resume</button>
        <button id=\"pauseButton\" class=\"secondary\" onclick=\"control('pause')\">Pause</button>
        <button id=\"stopButton\" class=\"danger\" onclick=\"control('stop')\">Stop</button>
      </div>
    </section>
    <nav class=\"workspace-nav\" id=\"workspaceNav\" aria-label=\"Dashboard views\">
      <div class=\"tabs\">
        <button class=\"tab active\" id=\"ecosystemTab\" onclick=\"showView('ecosystem')\">Ecosystem</button>
        <button class=\"tab\" id=\"comparisonTab\" onclick=\"showView('comparison')\">Comparison</button>
        <button class=\"tab\" id=\"evidenceTab\" onclick=\"showView('evidence')\">Evidence</button>
      </div>
      <label class=\"condition-picker\" id=\"conditionPicker\">Condition
        <select id=\"runSelect\" onchange=\"selectRun(this.value)\"></select>
      </label>
    </nav>
    <main class=\"operator\" id=\"operatorView\">
      <section class=\"replay\">
        <button id=\"playButton\" onclick=\"toggleReplay()\" aria-label=\"Play run replay\">▶ Play</button>
        <input id=\"turnSlider\" type=\"range\" min=\"0\" max=\"14\" value=\"14\" oninput=\"setTurn(Number(this.value))\" aria-label=\"Replay decision\" />
        <div class=\"turn-label\" id=\"turnLabel\">Decision 14 / 14</div>
      </section>
      <section class=\"operator-grid\">
        <article class=\"panel operator-panel\">
          <div class=\"panel-heading\"><h2>Agents</h2><span class=\"count\" id=\"agentCount\"></span></div>
          <div class=\"agent-list\" id=\"agentList\"></div>
        </article>
        <article class=\"panel operator-panel\">
          <div class=\"panel-heading\"><h2>Activity</h2><span class=\"count\" id=\"activityCount\"></span></div>
          <div class=\"activity-list\" id=\"activityList\"></div>
        </article>
      </section>
      <section class=\"panel operator-panel\">
        <div class=\"panel-heading\"><h2>Artifacts</h2><span class=\"count\" id=\"artifactCount\"></span></div>
        <div class=\"artifact-toolbar\">
          <input class=\"search\" id=\"artifactSearch\" type=\"search\" placeholder=\"Search artifact ID, type, or owner\" oninput=\"renderOperator()\" />
          <select id=\"artifactScope\" onchange=\"renderOperator()\"><option value=\"created\">Agent-created</option><option value=\"economy\">Economic artifacts</option><option value=\"all\">All artifacts</option></select>
        </div>
        <div style=\"overflow-x:auto\"><table class=\"artifact-table\"><thead><tr><th>Artifact</th><th>Type</th><th>Owner</th><th>Price</th><th>Created</th></tr></thead><tbody id=\"artifactRows\"></tbody></table></div>
      </section>
    </main>
    <main class=\"review\" id=\"reviewView\">
      <section class=\"verdict\" id=\"verdict\"></section>
      <section class=\"condition-grid\" id=\"conditionCards\"></section>
      <section class=\"review-section\">
        <h2>Economic outcome</h2>
        <p class=\"quiet\" id=\"economicSummary\"></p>
        <div class=\"economic-grid\" id=\"economicMetrics\"></div>
      </section>
      <section class=\"review-section\">
        <h2>What happened, decision by decision</h2>
        <p class=\"quiet\">Each column is one condition in the matched pair. Red decisions failed locally; no substitute action was silently used.</p>
        <div style=\"overflow-x:auto\"><table class=\"timeline\"><thead><tr><th>#</th><th>Prescribed</th><th>Minimal</th></tr></thead><tbody id=\"timelineBody\"></tbody></table></div>
      </section>
    </main>
    <main class=\"review\" id=\"evidenceView\">
      <section class=\"review-section\">
        <h2>Raw evidence</h2>
        <p class=\"quiet\" id=\"evidenceDescription\">Preserved state and event records for the selected condition. This completed run is read-only.</p>
        <section class=\"grid\">
          <article class=\"panel\"><h2>State receipt</h2><pre id=\"state\">loading...</pre></article>
          <article class=\"panel\"><h2>Event records</h2><pre id=\"events\">loading...</pre></article>
        </section>
      </section>
    </main>
    <section class=\"live\" id=\"liveView\">
      <section class=\"grid\">
        <article class=\"panel\"><h2>State</h2><pre id=\"liveState\">loading...</pre></article>
        <article class=\"panel\"><h2>Recent Events</h2><pre id=\"liveEvents\">loading...</pre></article>
      </section>
    </section>
  </div>
  <div class=\"modal-backdrop\" id=\"artifactModal\" onclick=\"if(event.target === this) closeArtifact()\">
    <article class=\"modal\" role=\"dialog\" aria-modal=\"true\" aria-labelledby=\"artifactModalTitle\">
      <div class=\"modal-head\"><h2 id=\"artifactModalTitle\"></h2><button class=\"secondary\" onclick=\"closeArtifact()\">Close</button></div>
      <div class=\"modal-meta\" id=\"artifactModalMeta\"></div>
      <pre class=\"artifact-content\" id=\"artifactModalContent\"></pre>
    </article>
  </div>
  <script>
    let selectedRun = null;
    let reviewMode = false;
    let selectedView = 'ecosystem';
    let operatorState = null;
    let currentTurn = 0;
    let replayTimer = null;
    async function fetchJson(url, options) {
      const res = await fetch(url, options);
      return await res.json();
    }

    function renderStatus(state) {
      const status = [];
      const running = state.runner ? !!state.runner.running : null;
      const paused = state.runner ? !!state.runner.paused : null;
      const runDot = running ? '<span class="dot"></span>' : '<span class="dot warn"></span>';
      status.push(`<span class="pill">${runDot}${running ? 'running' : 'not-running'}</span>`);
      if (paused) status.push('<span class="pill"><span class="dot warn"></span>paused</span>');
      if (state.event_number !== undefined) status.push(`<span class="pill">events: ${state.event_number}</span>`);
      if (state.principal_count !== undefined) status.push(`<span class="pill">principals: ${state.principal_count}</span>`);
      if (state.artifact_count !== undefined) status.push(`<span class="pill">artifacts: ${state.artifact_count}</span>`);
      if (state.recovery) {
        status.push(`<span class="pill">run: ${state.recovery.run_id}</span>`);
        status.push(`<span class="pill">Luna attempts: ${state.recovery.committed_attempts}/${state.recovery.target_attempts}</span>`);
        status.push(`<span class="pill">custody: ${state.recovery.lifecycle_state}</span>`);
      }
      if (state.review && state.review.read_only) {
        status.push('<span class="pill"><span class="dot warn"></span>review only</span>');
      }
      document.getElementById('statusLine').innerHTML = status.join(' ');
      const readOnly = !!(state.review && state.review.read_only);
      const lifecycle = state.recovery ? state.recovery.lifecycle_state : null;
      const terminal = ['completed', 'stopped', 'invalid'].includes(lifecycle);
      document.getElementById('resumeButton').disabled = readOnly || terminal || (running && !paused);
      document.getElementById('pauseButton').disabled = readOnly || terminal || !running || paused;
      document.getElementById('stopButton').disabled = readOnly || terminal;
    }

    function runQuery() {
      return selectedRun ? `?run=${encodeURIComponent(selectedRun)}` : '';
    }

    async function selectRun(run) {
      selectedRun = run;
      document.getElementById('runSelect').value = run;
      await Promise.all([loadOperator(), refreshEvidence()]);
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>\"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#039;'}[char]));
    }

    function actionCell(action) {
      if (!action) return '<span class=\"quiet\">—</span>';
      const failure = action.success ? '' : ' fail';
      const error = action.error_code ? ` · ${escapeHtml(action.error_code)}` : '';
      return `<span class=\"actor\">${escapeHtml(action.principal_id)}</span><span class=\"chip${failure}\">${escapeHtml(action.action)}${error}</span>`;
    }

    function showView(view) {
      selectedView = view;
      const surfaces = {ecosystem: 'operatorView', comparison: 'reviewView', evidence: 'evidenceView'};
      for (const [name, id] of Object.entries(surfaces)) {
        document.getElementById(id).classList.toggle('visible', name === view);
        document.getElementById(`${name}Tab`).classList.toggle('active', name === view);
      }
      if (view !== 'ecosystem' && replayTimer) toggleReplay();
    }

    function formatMoney(value) {
      return typeof value === 'number' ? `$${value.toFixed(4)}` : '—';
    }

    function setTurn(turn) {
      if (!operatorState) return;
      currentTurn = Math.max(0, Math.min(turn, operatorState.max_turn));
      document.getElementById('turnSlider').value = currentTurn;
      document.getElementById('turnLabel').textContent = `Decision ${currentTurn} / ${operatorState.max_turn}`;
      renderOperator();
    }

    function toggleReplay() {
      const button = document.getElementById('playButton');
      if (replayTimer) {
        clearInterval(replayTimer);
        replayTimer = null;
        button.textContent = '▶ Play';
        button.setAttribute('aria-label', 'Play run replay');
        return;
      }
      if (!operatorState) return;
      if (currentTurn >= operatorState.max_turn) setTurn(0);
      button.textContent = '⏸ Pause';
      button.setAttribute('aria-label', 'Pause run replay');
      replayTimer = setInterval(() => {
        if (currentTurn >= operatorState.max_turn) {
          toggleReplay();
          return;
        }
        setTurn(currentTurn + 1);
      }, 650);
    }

    function actionDescription(action) {
      const base = escapeHtml(action.description);
      if (!action.artifact_id) return base;
      const artifact = escapeHtml(action.artifact_id);
      return base.replace(artifact, `<span class=\"artifact-link\" onclick=\"openArtifactById(decodeURIComponent('${encodeURIComponent(action.artifact_id)}'))\">${artifact}</span>`);
    }

    function renderOperator() {
      if (!operatorState) return;
      const visibleActions = operatorState.actions.filter(action => action.turn <= currentTurn);
      document.getElementById('agentCount').textContent = `${operatorState.agents.length} principals`;
      document.getElementById('agentList').innerHTML = operatorState.agents.map(agent => {
        const actions = visibleActions.filter(action => action.principal_id === agent.id);
        const failures = actions.filter(action => !action.success).length;
        const mix = {};
        actions.forEach(action => mix[action.action] = (mix[action.action] || 0) + 1);
        return `<article class=\"agent-card\">
          <div class=\"agent-head\"><strong>${escapeHtml(agent.id)}</strong><span class=\"pill\"><span class=\"dot${agent.frozen ? ' danger' : ''}\"></span>${agent.frozen ? 'frozen' : 'active'}</span></div>
          <div class=\"agent-stats\">
            <div class=\"agent-stat\"><b>${agent.scrip ?? '—'}</b>${operatorState.read_only ? 'final' : 'current'} scrip</div>
            <div class=\"agent-stat\"><b>${formatMoney(agent.llm_budget)}</b>budget left</div>
            <div class=\"agent-stat\"><b>${actions.length}</b>decisions so far</div>
          </div>
          <div class=\"mix\" style=\"margin-top:10px\">${Object.entries(mix).map(([name,count]) => `<span class=\"chip\">${escapeHtml(name)} × ${count}</span>`).join('')}${failures ? `<span class=\"chip fail\">${failures} failed</span>` : ''}</div>
        </article>`;
      }).join('');
      document.getElementById('activityCount').textContent = `${visibleActions.length} of ${operatorState.max_turn} decisions`;
      document.getElementById('activityList').innerHTML = visibleActions.length ? visibleActions.map(action => `
        <div class=\"activity-item${action.success ? '' : ' failed'}\">
          <span class=\"activity-turn\">#${action.turn}</span>
          <span class=\"activity-agent\">${escapeHtml(action.principal_id)}</span>
          <span class=\"activity-text\">${actionDescription(action)}</span>
          <span class=\"result${action.success ? '' : ' failed'}\">${action.success ? (action.value_amount ? `${action.value_amount} ${escapeHtml(action.value_unit)}` : 'success') : escapeHtml(action.error_code || 'failed')}</span>
        </div>`).join('') : `<div class=\"empty\">${operatorState.read_only ? 'Press Play to watch the agents begin.' : 'Waiting for the first agent decision.'}</div>`;
      const query = document.getElementById('artifactSearch').value.trim().toLowerCase();
      const scope = document.getElementById('artifactScope').value;
      const artifacts = operatorState.artifacts.filter(artifact =>
        artifact.created_turn <= currentTurn &&
        (scope === 'all' || artifact.agent_created || (scope === 'economy' && artifact.scenario_opportunity)) &&
        (!query || `${artifact.id} ${artifact.type} ${artifact.owner}`.toLowerCase().includes(query))
      );
      document.getElementById('artifactCount').textContent = `${artifacts.length} visible`;
      document.getElementById('artifactRows').innerHTML = artifacts.length ? artifacts.map(artifact => `
        <tr onclick=\"openArtifactById(decodeURIComponent('${encodeURIComponent(artifact.id)}'))\">
          <td><span class=\"artifact-link\">${escapeHtml(artifact.id)}</span></td><td>${escapeHtml(artifact.type)}</td><td>${escapeHtml(artifact.owner)}</td>
          <td>${artifact.read_price || artifact.invoke_price || 0} scrip</td><td>${artifact.created_turn ? `decision ${artifact.created_turn}` : 'initial'}</td>
        </tr>`).join('') : '<tr><td colspan=\"5\" class=\"empty\">No matching artifacts at this point in the replay.</td></tr>';
    }

    function openArtifactById(artifactId) {
      if (!operatorState) return;
      const artifact = operatorState.artifacts.find(item => item.id === artifactId);
      if (!artifact || artifact.created_turn > currentTurn) return;
      document.getElementById('artifactModalTitle').textContent = artifact.id;
      document.getElementById('artifactModalMeta').innerHTML = [artifact.type, `owner: ${artifact.owner}`, `read: ${artifact.read_price} scrip`, artifact.access_contract_id].map(value => `<span class=\"pill\">${escapeHtml(value)}</span>`).join('');
      document.getElementById('artifactModalContent').textContent = artifact.content || '(no content)';
      document.getElementById('artifactModal').classList.add('visible');
    }

    function closeArtifact() {
      document.getElementById('artifactModal').classList.remove('visible');
    }

    async function loadOperator() {
      const query = selectedRun ? `?run=${encodeURIComponent(selectedRun)}` : '';
      operatorState = await fetchJson(`/operator-state${query}`);
      currentTurn = operatorState.max_turn;
      const slider = document.getElementById('turnSlider');
      slider.max = operatorState.max_turn;
      slider.value = currentTurn;
      slider.disabled = !operatorState.read_only;
      document.getElementById('playButton').disabled = !operatorState.read_only;
      document.getElementById('turnLabel').textContent = operatorState.read_only ? `Decision ${currentTurn} / ${operatorState.max_turn}` : `Live · ${currentTurn} decisions`;
      if (operatorState.read_only) {
        document.getElementById('statusLine').innerHTML = `<span class=\"pill\"><span class=\"dot\"></span>${escapeHtml(operatorState.condition)}</span><span class=\"pill\">${operatorState.agents.length} agents</span><span class=\"pill\">${operatorState.artifacts.length} final artifacts</span><span class=\"pill\">${escapeHtml(operatorState.lifecycle_state)}</span><span class=\"pill\">read only replay</span>`;
      }
      renderOperator();
    }

    function renderReview(summary) {
      document.getElementById('liveControls').style.display = 'none';
      document.getElementById('liveView').classList.add('hidden');
      document.getElementById('verdict').innerHTML = `<strong>What this run shows</strong>${escapeHtml(summary.headline)}`;
      document.getElementById('conditionCards').innerHTML = summary.runs.map(run => `
        <article class=\"condition-card\">
          <h2>${escapeHtml(run.label)}</h2>
          <div class=\"intent\">${escapeHtml(run.condition_description)}</div>
          <div class=\"metrics\">
            <div class=\"metric\"><b>${run.succeeded}/${run.attempts}</b><span>successful decisions</span></div>
            <div class=\"metric\"><b>${run.artifacts_created.length}</b><span>new artifacts</span></div>
            <div class=\"metric\"><b>${run.failures}</b><span>local failures</span></div>
          </div>
          <div class=\"mix\">${Object.entries(run.action_counts).map(([name,count]) => `<span class=\"chip\">${escapeHtml(name)} × ${count}</span>`).join('')}</div>
        </article>`).join('');
      document.getElementById('economicSummary').textContent = summary.economic_summary;
      const totalNew = summary.runs.reduce((n, run) => n + run.artifacts_created.length, 0);
      const transfers = summary.runs.reduce((n, run) => n + run.transfers, 0);
      const mints = summary.runs.reduce((n, run) => n + run.mint_submissions, 0);
      const scripMoved = summary.runs.reduce((n, run) => n + run.scrip_moved, 0);
      document.getElementById('economicMetrics').innerHTML = [
        [transfers, 'transfer decisions'], [mints, 'mint submissions'], [scripMoved, 'net scrip moved'], [totalNew, 'artifacts created across pair']
      ].map(([value,label]) => `<div class=\"metric\"><b>${value}</b><span>${label}</span></div>`).join('');
      const byId = Object.fromEntries(summary.runs.map(run => [run.id, run]));
      const prescribed = byId.prescribed || summary.runs[0];
      const minimal = byId.minimal || summary.runs[1];
      const rows = Math.max(prescribed?.actions.length || 0, minimal?.actions.length || 0);
      document.getElementById('timelineBody').innerHTML = Array.from({length: rows}, (_, i) => `<tr><td>${i + 1}</td><td>${actionCell(prescribed?.actions[i])}</td><td>${actionCell(minimal?.actions[i])}</td></tr>`).join('');
    }

    async function loadRuns() {
      const payload = await fetchJson('/runs');
      if (!payload.runs || payload.runs.length === 0) return false;
      reviewMode = true;
      selectedRun = payload.runs.some(run => run.id === 'minimal') ? 'minimal' : (payload.default_run || payload.runs[0].id);
      const select = document.getElementById('runSelect');
      select.innerHTML = payload.runs.map(run =>
        `<option value="${run.id}">${run.label}</option>`
      ).join('');
      select.value = selectedRun;
      document.getElementById('eyebrow').textContent = 'Luna Medium ecology replay';
      document.getElementById('pageTitle').textContent = 'Agent Ecology 3';
      document.getElementById('pageSubtitle').textContent = 'Watch agents act, inspect what they create, and follow the ecology decision by decision.';
      document.getElementById('workspaceNav').classList.add('visible');
      document.getElementById('liveControls').style.display = 'none';
      document.getElementById('liveView').classList.add('hidden');
      renderReview(await fetchJson('/review-summary'));
      await loadOperator();
      showView('ecosystem');
      return true;
    }

    async function refreshEvidence() {
      try {
        const query = runQuery();
        const separator = selectedRun ? '&' : '?';
        const [state, events] = await Promise.all([
          fetchJson(`/state${query}`),
          fetchJson(`/events${query}${separator}limit=60`),
        ]);
        document.getElementById('state').textContent = JSON.stringify(state, null, 2);
        document.getElementById('events').textContent = JSON.stringify(events, null, 2);
      } catch (err) {
        document.getElementById('state').textContent = `dashboard error: ${err}`;
      }
    }

    async function refreshLive() {
      try {
        const [state, events, liveOperator] = await Promise.all([fetchJson('/state'), fetchJson('/events?limit=60'), fetchJson('/operator-state')]);
        renderStatus(state);
        operatorState = liveOperator;
        currentTurn = operatorState.max_turn;
        document.getElementById('turnSlider').max = currentTurn;
        document.getElementById('turnSlider').value = currentTurn;
        document.getElementById('turnLabel').textContent = `Live · ${currentTurn} decisions`;
        renderOperator();
        document.getElementById('liveState').textContent = JSON.stringify(state, null, 2);
        document.getElementById('liveEvents').textContent = JSON.stringify(events, null, 2);
        document.getElementById('state').textContent = JSON.stringify(state, null, 2);
        document.getElementById('events').textContent = JSON.stringify(events, null, 2);
      } catch (err) {
        document.getElementById('liveState').textContent = `dashboard error: ${err}`;
      }
    }

    async function control(action) {
      try {
        await fetchJson(`/control/${action}`, { method: 'POST' });
      } finally {
        await refreshLive();
      }
    }

    async function initializeLive() {
      selectedRun = null;
      document.getElementById('eyebrow').textContent = 'Live Luna Medium ecology';
      document.getElementById('pageSubtitle').textContent = 'Watch agents act, inspect resources and artifacts, and control the run from one workspace.';
      document.getElementById('workspaceNav').classList.add('visible');
      document.getElementById('conditionPicker').style.display = 'none';
      document.getElementById('comparisonTab').style.display = 'none';
      document.getElementById('liveView').classList.add('hidden');
      document.getElementById('playButton').disabled = true;
      document.getElementById('playButton').textContent = '● Live';
      document.getElementById('evidenceDescription').textContent = 'Current canonical state and recent event records from the live run.';
      document.getElementById('artifactScope').value = 'economy';
      showView('ecosystem');
      await refreshLive();
    }

    loadRuns().then(hasRuns => hasRuns ? refreshEvidence() : initializeLive());
    setInterval(() => { if (!reviewMode) refreshLive(); }, 1500);
  </script>
</body>
</html>
"""


def _read_jsonl_tail(path: Path, limit: int) -> list[dict[str, Any]]:
    if limit <= 0 or not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    selected = lines[-limit:]
    items: list[dict[str, Any]] = []
    for raw in selected:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            items.append(parsed)
    return items


def _summarize_review_run(run_id: str, data_dir: Path) -> dict[str, Any]:
    receipt = cast(
        dict[str, Any],
        json.loads((data_dir / "run_receipt.json").read_text(encoding="utf-8")),
    )
    world_state = receipt.get("world_state")
    recovery = receipt.get("recovery")
    if not isinstance(world_state, dict) or not isinstance(recovery, dict):
        raise TypeError(f"review receipt for {run_id} is missing run state")
    raw_log_path = world_state.get("log_path")
    if not isinstance(raw_log_path, str) or not raw_log_path:
        raise RuntimeError(f"review receipt for {run_id} has no log_path")
    events = _read_jsonl_tail(Path(raw_log_path), 100_000)
    decisions = [event for event in events if event.get("event_type") == "loop_decision"]
    action_counts: Counter[str] = Counter()
    actions: list[dict[str, Any]] = []
    scrip_moved = 0.0
    for event in decisions:
        action = str(event.get("decision_action") or "unknown")
        action_counts[action] += 1
        decision = event.get("decision")
        if (
            action.startswith("transfer")
            and event.get("result_success") is True
            and isinstance(decision, dict)
        ):
            amount = decision.get("amount", 0)
            if isinstance(amount, (int, float)):
                scrip_moved += float(amount)
        actions.append(
            {
                "principal_id": event.get("principal_id"),
                "action": action,
                "success": event.get("result_success") is True,
                "error_code": event.get("result_error_code"),
                "fallback_used": bool(event.get("fallback_used")),
            }
        )
    created = [
        {
            "id": event.get("artifact_id"),
            "type": event.get("artifact_type"),
            "owner": event.get("principal_id"),
        }
        for event in events
        if event.get("event_type") == "artifact_written"
        and event.get("was_update") is not True
    ]
    balances = world_state.get("balances")
    balance_rows: list[dict[str, Any]] = []
    if isinstance(balances, dict):
        for principal_id, raw_balance in balances.items():
            if not isinstance(raw_balance, dict):
                continue
            resources = raw_balance.get("resources")
            budget = resources.get("llm_budget") if isinstance(resources, dict) else None
            balance_rows.append(
                {
                    "principal_id": principal_id,
                    "scrip": raw_balance.get("scrip"),
                    "llm_budget": budget,
                }
            )
    attempts = int(recovery.get("committed_attempts", 0) or 0)
    failures = sum(not action["success"] for action in actions)
    condition_descriptions = {
        "prescribed": "Agents received assigned roles, objectives, and a role-specific playbook.",
        "minimal": "Agents received constraints but no assigned role, action sequence, or trading policy.",
    }
    return {
        "id": run_id,
        "label": run_id.replace("_", " ").title(),
        "condition_description": condition_descriptions.get(
            run_id, "Completed experimental condition."
        ),
        "model": receipt.get("model"),
        "acknowledgement": receipt.get("acknowledgement"),
        "lifecycle_state": recovery.get("lifecycle_state"),
        "attempts": attempts,
        "target_attempts": int(recovery.get("target_attempts", 0) or 0),
        "succeeded": len(actions) - failures,
        "failures": failures,
        "fallbacks": sum(action["fallback_used"] for action in actions),
        "action_counts": dict(action_counts),
        "actions": actions,
        "artifacts_created": created,
        "transfers": sum(
            count for action, count in action_counts.items() if action.startswith("transfer")
        ),
        "mint_submissions": sum(
            count for action, count in action_counts.items() if "mint" in action
        ),
        "scrip_moved": scrip_moved,
        "balances": balance_rows,
        "artifact_count": world_state.get("artifact_count"),
    }


def _summarize_review_pair(review_runs: dict[str, Path]) -> dict[str, Any]:
    runs = [_summarize_review_run(run_id, path) for run_id, path in review_runs.items()]
    valid_pair = len(runs) == 2 and all(
        run["attempts"] == run["target_attempts"] and run["fallbacks"] == 0
        for run in runs
    )
    by_id = {run["id"]: run for run in runs}
    prescribed = by_id.get("prescribed")
    minimal = by_id.get("minimal")
    if prescribed is not None and minimal is not None:
        query_count = prescribed["action_counts"].get("query_kernel", 0)
        headline = (
            f"Minimal used {len(minimal['action_counts'])} action types and created "
            f"{len(minimal['artifacts_created'])} artifacts. Prescribed used "
            f"{query_count} of {prescribed['attempts']} decisions querying and had "
            f"{prescribed['failures']} authorization failures. Neither condition "
            "traded, submitted to mint, or moved scrip."
        )
    else:
        headline = "Completed-run evidence is available for review."
    return {
        "schema_version": "ae3_review_summary.v1",
        "title": "Evaluation 15 — Matched Pair Review",
        "valid_pair": valid_pair,
        "scope_note": (
            "One valid matched pair: useful PoC evidence of different behavior, "
            "not a causal result about cognition or economic performance."
        ),
        "headline": headline,
        "economic_summary": (
            "Both agents finished with 100 scrip in both conditions. There were no "
            "transfers, priced purchases, or mint submissions, so this run shows a "
            "behavioral contrast but not yet a functioning agent economy."
        ),
        "runs": runs,
    }


def _operator_state(
    *,
    condition: str,
    world_state: dict[str, Any],
    recovery: dict[str, Any],
    model: str | None,
    events: list[dict[str, Any]],
    read_only: bool,
) -> dict[str, Any]:
    """Project canonical world state and events into the operator workflow."""
    decisions = [event for event in events if event.get("event_type") == "loop_decision"]
    event_turn = {
        int(event.get("event_number", 0) or 0): turn
        for turn, event in enumerate(decisions, start=1)
    }
    created_turn = {
        str(event.get("artifact_id")): event_turn.get(
            int(event.get("event_number", 0) or 0), 0
        )
        for event in events
        if event.get("event_type") == "artifact_written"
        and event.get("was_update") is not True
    }
    raw_artifacts = world_state.get("artifacts")
    artifacts: list[dict[str, Any]] = []
    owners: dict[str, str] = {}
    if isinstance(raw_artifacts, list):
        for raw in raw_artifacts:
            if not isinstance(raw, dict):
                continue
            artifact_id = str(raw.get("id") or "")
            owner = str(raw.get("owner") or raw.get("created_by") or "unknown")
            owners[artifact_id] = owner
            artifacts.append(
                {
                    "id": artifact_id,
                    "type": raw.get("type"),
                    "owner": owner,
                    "created_by": raw.get("created_by"),
                    "content": raw.get("content", ""),
                    "read_price": raw.get("read_price", 0),
                    "invoke_price": raw.get("invoke_price", 0),
                    "executable": bool(raw.get("executable")),
                    "access_contract_id": raw.get("access_contract_id"),
                    "scenario_opportunity": bool(
                        isinstance(raw.get("metadata"), dict)
                        and raw["metadata"].get("mvp_scenario_opportunity") is True
                    ),
                    "created_turn": created_turn.get(artifact_id, 0),
                    "agent_created": artifact_id in created_turn,
                }
            )
    action_rows: list[dict[str, Any]] = []
    paid_reads = {
        (int(event.get("event_number", 0) or 0), str(event.get("artifact_id") or "")): event
        for event in events
        if event.get("event_type") == "artifact_read"
    }
    agent_counts: dict[str, Counter[str]] = {}
    agent_failures: Counter[str] = Counter()
    for turn, event in enumerate(decisions, start=1):
        principal_id = str(event.get("principal_id") or "unknown")
        action = str(event.get("decision_action") or "unknown")
        raw_decision = event.get("decision")
        decision = cast(dict[str, Any], raw_decision) if isinstance(raw_decision, dict) else {}
        target_artifact_id = decision.get("artifact_id")
        success = event.get("result_success") is True
        value_amount: int | float = 0
        value_unit: str | None = None
        counterparty: str | None = None
        agent_counts.setdefault(principal_id, Counter())[action] += 1
        if not success:
            agent_failures[principal_id] += 1
        if action == "query_kernel":
            description = f"searched {decision.get('query_type', 'the kernel')}"
        elif action == "read_artifact":
            read_event = paid_reads.get(
                (
                    int(event.get("event_number", 0) or 0),
                    str(target_artifact_id or ""),
                )
            )
            if read_event is not None:
                raw_amount = read_event.get("read_price_paid", 0)
                if isinstance(raw_amount, (int, float)):
                    value_amount = raw_amount
                raw_counterparty = read_event.get("recipient")
                if isinstance(raw_counterparty, str):
                    counterparty = raw_counterparty
            if value_amount > 0:
                value_unit = "scrip"
                description = (
                    f"bought {target_artifact_id or 'an artifact'} from "
                    f"{counterparty or 'its owner'}"
                )
            else:
                description = f"read {target_artifact_id or 'an artifact'}"
        elif action == "write_artifact":
            description = f"created {target_artifact_id or 'an artifact'}"
        elif action.startswith("transfer"):
            description = f"attempted {action.replace('_', ' ')}"
        elif "mint" in action:
            description = "submitted an artifact to mint"
        else:
            description = action.replace("_", " ")
        action_rows.append(
            {
                "turn": turn,
                "event_number": event.get("event_number"),
                "principal_id": principal_id,
                "action": action,
                "description": description,
                "artifact_id": target_artifact_id,
                "artifact_owner": owners.get(str(target_artifact_id))
                if target_artifact_id
                else None,
                "success": success,
                "error_code": event.get("result_error_code"),
                "fallback_used": bool(event.get("fallback_used")),
                "value_amount": value_amount,
                "value_unit": value_unit,
                "counterparty": counterparty,
            }
        )
    balances = world_state.get("balances")
    quotas = world_state.get("quotas")
    frozen = world_state.get("frozen")
    principal_ids = world_state.get("principals")
    agents: list[dict[str, Any]] = []
    if isinstance(principal_ids, list):
        for raw_principal_id in principal_ids:
            principal_id = str(raw_principal_id)
            balance = balances.get(principal_id, {}) if isinstance(balances, dict) else {}
            quota = quotas.get(principal_id, {}) if isinstance(quotas, dict) else {}
            resources = balance.get("resources", {}) if isinstance(balance, dict) else {}
            disk = quota.get("disk", {}) if isinstance(quota, dict) else {}
            agents.append(
                {
                    "id": principal_id,
                    "scrip": balance.get("scrip") if isinstance(balance, dict) else None,
                    "llm_budget": resources.get("llm_budget")
                    if isinstance(resources, dict)
                    else None,
                    "disk_used": disk.get("used") if isinstance(disk, dict) else None,
                    "disk_quota": disk.get("quota") if isinstance(disk, dict) else None,
                    "frozen": principal_id in frozen if isinstance(frozen, list) else False,
                    "action_counts": dict(agent_counts.get(principal_id, Counter())),
                    "failures": agent_failures[principal_id],
                }
            )
    return {
        "schema_version": "ae3_operator_state.v1",
        "condition": condition,
        "run_id": world_state.get("run_id"),
        "model": model,
        "lifecycle_state": recovery.get("lifecycle_state"),
        "read_only": read_only,
        "max_turn": len(action_rows),
        "agents": agents,
        "artifacts": artifacts,
        "actions": action_rows,
    }


def _operator_review_state(run_id: str, data_dir: Path) -> dict[str, Any]:
    """Project a completed receipt into the human operator workflow."""
    receipt = cast(
        dict[str, Any],
        json.loads((data_dir / "run_receipt.json").read_text(encoding="utf-8")),
    )
    world_state = receipt.get("world_state")
    recovery = receipt.get("recovery")
    if not isinstance(world_state, dict) or not isinstance(recovery, dict):
        raise TypeError(f"review receipt for {run_id} is missing run state")
    raw_log_path = world_state.get("log_path")
    if not isinstance(raw_log_path, str) or not raw_log_path:
        raise RuntimeError(f"review receipt for {run_id} has no log_path")
    model = receipt.get("model")
    return _operator_state(
        condition=run_id,
        world_state=world_state,
        recovery=recovery,
        model=model if isinstance(model, str) else None,
        events=_read_jsonl_tail(Path(raw_log_path), 100_000),
        read_only=True,
    )


def create_app(
    *,
    world_provider: Callable[[], Any | None] | None = None,
    runner_provider: Callable[[], Any | None] | None = None,
    recovery_provider: Callable[[], dict[str, Any] | None] | None = None,
    shutdown_provider: Callable[[], None] | None = None,
    jsonl_path: str | None = None,
    review_runs: dict[str, Path] | None = None,
) -> FastAPI:
    """Create a minimal dashboard app for live run or log-only mode."""

    world_provider = world_provider or (lambda: None)
    runner_provider = runner_provider or (lambda: None)
    recovery_provider = recovery_provider or (lambda: None)
    log_path = Path(jsonl_path) if jsonl_path else None
    review_runs = review_runs or {}

    def review_payload(run: str | None) -> tuple[dict[str, Any], Path] | None:
        if not review_runs:
            return None
        run_id = run if run in review_runs else next(iter(review_runs))
        data_dir = review_runs[run_id]
        receipt = cast(
            dict[str, Any],
            json.loads((data_dir / "run_receipt.json").read_text(encoding="utf-8")),
        )
        world_state = receipt.get("world_state")
        if not isinstance(world_state, dict):
            raise TypeError(f"review receipt for {run_id} has no world_state")
        raw_log_path = world_state.get("log_path")
        if not isinstance(raw_log_path, str) or not raw_log_path:
            raise RuntimeError(f"review receipt for {run_id} has no log_path")
        payload = cast(dict[str, Any], json.loads(json.dumps(world_state)))
        payload["runner"] = None
        payload["recovery"] = receipt.get("recovery")
        payload["review"] = {
            "read_only": True,
            "run": run_id,
            "acknowledgement": receipt.get("acknowledgement"),
        }
        return payload, Path(raw_log_path)

    app = FastAPI(title="Agent Ecology 3 Dashboard", version="0.1.0")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return _DASHBOARD_HTML

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"ok": True}

    @app.get("/runs")
    async def runs() -> dict[str, Any]:
        items = [
            {"id": run_id, "label": run_id.replace("_", " ").title()}
            for run_id in review_runs
        ]
        return {
            "runs": items,
            "default_run": next(iter(review_runs), None),
            "read_only": bool(review_runs),
        }

    @app.get("/review-summary")
    async def review_summary() -> dict[str, Any]:
        if not review_runs:
            return {"success": False, "error": "completed review unavailable"}
        return _summarize_review_pair(review_runs)

    @app.get("/operator-state")
    async def operator_state(run: str | None = None) -> dict[str, Any]:
        if review_runs:
            run_id = run if run in review_runs else next(iter(review_runs))
            return _operator_review_state(run_id, review_runs[run_id])
        world = world_provider()
        if world is None:
            return {"success": False, "error": "live operator unavailable"}
        world_state = cast(dict[str, Any], world.get_state_summary(event_limit=2000))
        recovery = recovery_provider() or {}
        config = getattr(world, "config", None)
        llm_config = getattr(config, "llm", None)
        model = getattr(llm_config, "default_model", None)
        condition = getattr(llm_config, "loop_cognition_mode", "live")
        return _operator_state(
            condition=str(condition),
            world_state=world_state,
            recovery=recovery,
            model=model if isinstance(model, str) else None,
            events=world.logger.read_recent(2000),
            read_only=False,
        )

    @app.get("/state")
    async def state(run: str | None = None) -> dict[str, Any]:
        review = review_payload(run)
        if review is not None:
            return review[0]
        world = world_provider()
        runner = runner_provider()
        if world is not None:
            payload = cast(dict[str, Any], world.get_state_summary(event_limit=150))
            payload["runner"] = runner.get_status().__dict__ if runner is not None else None
            payload["recovery"] = recovery_provider()
            return payload

        events = _read_jsonl_tail(log_path, 150) if log_path else []
        event_number = max((int(e.get("event_number", 0) or 0) for e in events), default=0)
        return {
            "run_id": None,
            "event_number": event_number,
            "principal_count": None,
            "artifact_count": None,
            "events": events,
            "runner": None,
            "recovery": recovery_provider(),
            "log_path": str(log_path) if log_path else None,
        }

    @app.get("/events")
    async def events(
        limit: int = Query(default=100, ge=1, le=2000), run: str | None = None
    ) -> dict[str, Any]:
        review = review_payload(run)
        if review is not None:
            items = _read_jsonl_tail(review[1], limit)
            return {"success": True, "events": items, "count": len(items)}
        world = world_provider()
        if world is not None:
            items = world.logger.read_recent(limit)
            return {"success": True, "events": items, "count": len(items)}

        items = _read_jsonl_tail(log_path, limit) if log_path else []
        return {"success": True, "events": items, "count": len(items)}

    @app.post("/control/pause")
    async def control_pause() -> dict[str, Any]:
        runner = runner_provider()
        if runner is None:
            return {"success": False, "error": "runner unavailable"}
        runner.pause()
        return {"success": True, "paused": True}

    @app.post("/control/resume")
    async def control_resume() -> dict[str, Any]:
        runner = runner_provider()
        if runner is None:
            return {"success": False, "error": "runner unavailable"}
        runner.resume()
        return {"success": True, "paused": False}

    @app.post("/control/stop")
    async def control_stop() -> dict[str, Any]:
        runner = runner_provider()
        if runner is None:
            return {"success": False, "error": "runner unavailable"}
        runner.stop()
        return {"success": True, "stopping": True}

    @app.post("/control/shutdown")
    async def control_shutdown() -> dict[str, Any]:
        if shutdown_provider is None:
            return {"success": False, "error": "shutdown unavailable"}
        shutdown_provider()
        return {"success": True, "shutting_down": True}

    return app
