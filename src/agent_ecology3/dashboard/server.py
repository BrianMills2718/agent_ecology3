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
      <details class=\"advanced\">
        <summary>Advanced evidence — raw state and event records</summary>
        <div class=\"advanced-body\">
          <label class=\"review-picker\" id=\"reviewPicker\">Evidence for
            <select id=\"runSelect\" onchange=\"selectRun(this.value)\"></select>
          </label>
          <p class=\"quiet\">This is a preserved completed run. Live Resume, Pause, and Stop controls are unavailable.</p>
          <section class=\"grid\">
            <article class=\"panel\"><h2>State receipt</h2><pre id=\"state\">loading...</pre></article>
            <article class=\"panel\"><h2>Event records</h2><pre id=\"events\">loading...</pre></article>
          </section>
        </div>
      </details>
    </main>
    <section class=\"live\" id=\"liveView\">
      <section class=\"grid\">
        <article class=\"panel\"><h2>State</h2><pre id=\"liveState\">loading...</pre></article>
        <article class=\"panel\"><h2>Recent Events</h2><pre id=\"liveEvents\">loading...</pre></article>
      </section>
    </section>
  </div>
  <script>
    let selectedRun = null;
    let reviewMode = false;
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
      for (const id of ['resumeButton', 'pauseButton', 'stopButton']) {
        document.getElementById(id).disabled = readOnly;
      }
    }

    function runQuery() {
      return selectedRun ? `?run=${encodeURIComponent(selectedRun)}` : '';
    }

    function selectRun(run) {
      selectedRun = run;
      refreshEvidence();
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

    function renderReview(summary) {
      document.getElementById('eyebrow').textContent = 'Completed Luna Medium run';
      document.getElementById('pageTitle').textContent = summary.title;
      document.getElementById('pageSubtitle').textContent = summary.scope_note;
      document.getElementById('statusLine').innerHTML = `<span class=\"pill\"><span class=\"dot\"></span>${summary.valid_pair ? 'valid matched pair' : 'incomplete pair'}</span><span class=\"pill\">14 decisions per condition</span><span class=\"pill\">read only</span>`;
      document.getElementById('liveControls').style.display = 'none';
      document.getElementById('liveView').classList.add('hidden');
      document.getElementById('reviewView').classList.add('visible');
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
      selectedRun = payload.default_run || payload.runs[0].id;
      const select = document.getElementById('runSelect');
      select.innerHTML = payload.runs.map(run =>
        `<option value="${run.id}">${run.label}</option>`
      ).join('');
      select.value = selectedRun;
      document.getElementById('reviewPicker').style.display = 'flex';
      renderReview(await fetchJson('/review-summary'));
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
        const [state, events] = await Promise.all([fetchJson('/state'), fetchJson('/events?limit=60')]);
        renderStatus(state);
        document.getElementById('liveState').textContent = JSON.stringify(state, null, 2);
        document.getElementById('liveEvents').textContent = JSON.stringify(events, null, 2);
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

    loadRuns().then(hasRuns => hasRuns ? refreshEvidence() : refreshLive());
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


def create_app(
    *,
    world_provider: Callable[[], Any | None] | None = None,
    runner_provider: Callable[[], Any | None] | None = None,
    recovery_provider: Callable[[], dict[str, Any] | None] | None = None,
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

    return app
