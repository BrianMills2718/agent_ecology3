"""Minimal AE3 dashboard API and single-page status UI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse


_DASHBOARD_HTML = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
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
      <div class=\"actions\">
        <button onclick=\"control('resume')\">Resume</button>
        <button class=\"secondary\" onclick=\"control('pause')\">Pause</button>
        <button class=\"danger\" onclick=\"control('stop')\">Stop</button>
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
      document.getElementById('statusLine').innerHTML = status.join(' ');
    }

    async function refresh() {
      try {
        const state = await fetchJson('/state');
        renderStatus(state);
        document.getElementById('state').textContent = JSON.stringify(state, null, 2);

        const events = await fetchJson('/events?limit=60');
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

    refresh();
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
    jsonl_path: str | None = None,
) -> FastAPI:
    """Create a minimal dashboard app for live run or log-only mode."""

    world_provider = world_provider or (lambda: None)
    runner_provider = runner_provider or (lambda: None)
    log_path = Path(jsonl_path) if jsonl_path else None

    app = FastAPI(title="Agent Ecology 3 Dashboard", version="0.1.0")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return _DASHBOARD_HTML

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"ok": True}

    @app.get("/state")
    async def state() -> dict[str, Any]:
        world = world_provider()
        runner = runner_provider()
        if world is not None:
            payload = world.get_state_summary(event_limit=150)
            payload["runner"] = runner.get_status().__dict__ if runner is not None else None
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
            "log_path": str(log_path) if log_path else None,
        }

    @app.get("/events")
    async def events(limit: int = Query(default=100, ge=1, le=2000)) -> dict[str, Any]:
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
