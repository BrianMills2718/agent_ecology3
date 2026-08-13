"""Minimal AE3 dashboard API and single-page status UI."""

from __future__ import annotations

import json
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
  <title>AE3 Dashboard</title>
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
      max-width: 1200px;
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
      font-size: 22px;
      letter-spacing: .03em;
    }
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
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class=\"wrap\">
    <section class=\"top\">
      <h1 class=\"title\">Agent Ecology 3</h1>
      <div class=\"status\" id=\"statusLine\">loading...</div>
      <label class=\"review-picker\" id=\"reviewPicker\">Review run
        <select id=\"runSelect\" onchange=\"selectRun(this.value)\"></select>
      </label>
      <div class=\"actions\">
        <button id=\"resumeButton\" onclick=\"control('resume')\">Resume</button>
        <button id=\"pauseButton\" class=\"secondary\" onclick=\"control('pause')\">Pause</button>
        <button id=\"stopButton\" class=\"danger\" onclick=\"control('stop')\">Stop</button>
      </div>
    </section>
    <section class=\"grid\">
      <article class=\"panel\">
        <h2>State</h2>
        <pre id=\"state\">loading...</pre>
      </article>
      <article class=\"panel\">
        <h2>Recent Events</h2>
        <pre id=\"events\">loading...</pre>
      </article>
    </section>
  </div>
  <script>
    let selectedRun = null;
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
      refresh();
    }

    async function loadRuns() {
      const payload = await fetchJson('/runs');
      if (!payload.runs || payload.runs.length === 0) return;
      selectedRun = payload.default_run || payload.runs[0].id;
      const select = document.getElementById('runSelect');
      select.innerHTML = payload.runs.map(run =>
        `<option value="${run.id}">${run.label}</option>`
      ).join('');
      select.value = selectedRun;
      document.getElementById('reviewPicker').style.display = 'flex';
    }

    async function refresh() {
      try {
        const query = runQuery();
        const separator = selectedRun ? '&' : '?';
        const [state, events] = await Promise.all([
          fetchJson(`/state${query}`),
          fetchJson(`/events${query}${separator}limit=60`),
        ]);
        renderStatus(state);
        document.getElementById('state').textContent = JSON.stringify(state, null, 2);
        document.getElementById('events').textContent = JSON.stringify(events, null, 2);
      } catch (err) {
        document.getElementById('state').textContent = `dashboard error: ${err}`;
      }
    }

    async function control(action) {
      try {
        await fetchJson(`/control/${action}`, { method: 'POST' });
      } finally {
        await refresh();
      }
    }

    loadRuns().finally(refresh);
    setInterval(refresh, 1500);
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
