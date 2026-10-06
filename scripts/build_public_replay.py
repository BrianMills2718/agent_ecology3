#!/usr/bin/env python3
"""Build the public, read-only replay of one finished resident run (Plan 26 M4).

The replay is three static files served at brianmills.dev/agent-ecology/:
``index.html`` (activity feed and Interactions matrix), ``snapshot.json`` (the
redacted data both read) and ``living.html`` (World Substrate living view).

Redaction is an allow-list, not a deny-list: each kept event type keeps only
named structural fields (who, what, which artifact id, scrip amounts, pass or
fail). Everything else is dropped, including:

- artifact content and code, and the kernel's ``action`` events that carry it;
- agents' end-of-turn notes and message text (in run5, 27 of 640 notes quoted
  a bank sentence or hidden test input word for word, and many more quoted
  expected outputs or solution code, which no exact-match check can catch);
- checker reasons beyond the error type;
- session ids, trace ids, timestamps, local paths and the agents' Codex
  folders.

``leak_counts`` then scans every output file for bank sentences and hidden
test inputs (``scripts/run_evidence.py`` ``_leaks``), token-like strings, home
paths, Codex folders and email addresses; ``build`` refuses to write when any
count is above zero.

    uv run python scripts/build_public_replay.py build RUN_DIR --bank BANK [--out DIR]
    uv run python scripts/build_public_replay.py check DIR --bank BANK
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
PAGE_TEMPLATE = REPO / "scripts" / "public_replay_page.html"
DEFAULT_OUT = REPO / "deploy" / "cloudflare" / "agent-ecology" / "assets" / "agent-ecology"
NOTE_WITHHELD = "note withheld"
MESSAGE_WITHHELD = "(text withheld)"


def _run_evidence() -> Any:
    spec = importlib.util.spec_from_file_location("run_evidence", REPO / "scripts" / "run_evidence.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_EVIDENCE = _run_evidence()

# Event type -> fields that may be published. Free text is never listed.
KEEP: dict[str, tuple[str, ...]] = {
    "resident_action": ("sequence", "event_type", "event_number", "turn", "principal_id", "action_type",
                        "artifact_id", "success", "error_code", "read_price", "action_id"),
    "resident_turn": ("sequence", "event_type", "turn", "principal_id"),
    "artifact_read": ("sequence", "event_type", "event_number", "principal_id", "artifact_id",
                      "read_price_paid", "recipient"),
    "artifact_written": ("sequence", "event_type", "event_number", "principal_id", "artifact_id",
                         "artifact_type", "was_update"),
    "task_bounty_scored": ("sequence", "event_type", "event_number", "principal_id", "artifact_id", "task_id",
                           "passed", "first_claim", "scrip_minted", "reason"),
    "royalty_paid": ("sequence", "event_type", "event_number", "principal_id", "solver", "amount",
                     "dependency_task_id", "payer_task_id"),
    "agent_message": ("sequence", "event_type", "event_number", "principal_id", "recipient", "action_id"),
    "transfer": ("sequence", "event_type", "event_number", "sender", "recipient", "amount"),
    "kernel_query": ("sequence", "event_type", "event_number", "principal_id", "query_type"),
}
_SAFE_ID = re.compile(r"^[A-Za-z0-9_./:\-]{0,120}$")

# Patterns that must never appear in a public file.
PRIVATE_PATTERNS: dict[str, re.Pattern[str]] = {
    "home path": re.compile(r"/home/|/Users/|[A-Za-z]:\\\\Users|~/\.|\.local/state|\.cache/agent_ecology"),
    "codex folder": re.compile(r"\.codex\b|codex_home|CODEX_HOME"),
    "email address": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "token": re.compile(
        r"sk-[A-Za-z0-9_-]{16,}|sk-ant-|sk-or-|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_|xox[abpr]-|AKIA[0-9A-Z]{16}"
        r"|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}|Bearer\s+[A-Za-z0-9._-]{16,}"
        r"|(?:api[_-]?key|secret|password|token)\"?\s*[:=]\s*\"?[A-Za-z0-9_\-]{12,}",
        re.IGNORECASE,
    ),
}


def _clean_value(key: str, value: Any, passed: bool) -> Any:
    if key == "reason":
        return _EVIDENCE._redact_reason(str(value or ""), passed)
    if isinstance(value, bool) or value is None or isinstance(value, (int, float)):
        return value
    if isinstance(value, str) and _SAFE_ID.match(value):
        return value
    # Any other string in an allowed field is unexpected: drop it.
    return None


def redact_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only allow-listed structural fields of the event types the views read."""
    out: list[dict[str, Any]] = []
    for event in events:
        fields = KEEP.get(str(event.get("event_type")))
        if fields is None:
            continue
        passed = event.get("passed") is True
        kept = {k: _clean_value(k, event[k], passed) for k in fields if k in event}
        if kept.get("event_type") == "agent_message":
            kept["text"] = MESSAGE_WITHHELD
        out.append(kept)
    return out


def public_world_state(world_state: dict[str, Any]) -> dict[str, Any]:
    """Principals, scrip balances, and artifact id/type/owner (no content)."""
    balances = world_state.get("balances") or {}
    artifacts = []
    for raw in world_state.get("artifacts") or []:
        if not isinstance(raw, dict) or raw.get("deleted"):
            continue
        metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
        task_id = metadata.get("plan24_task_id")
        artifacts.append({
            "id": str(raw.get("id")),
            "type": str(raw.get("type") or ""),
            "owner": str(raw.get("owner") or raw.get("created_by") or ""),
            "read_price": raw.get("read_price") if isinstance(raw.get("read_price"), (int, float)) else 0,
            "metadata": {"plan24_task_id": task_id} if isinstance(task_id, str) else {},
        })
    return {
        "run_id": world_state.get("run_id"),
        "principals": [str(p) for p in world_state.get("principals") or balances],
        "balances": {str(p): {"scrip": (b or {}).get("scrip")} for p, b in balances.items()},
        "artifacts": artifacts,
    }


def _read_events(run_dir: Path) -> list[dict[str, Any]]:
    run_log = run_dir / "logs" / run_dir.name / "events.jsonl"
    path = run_log if run_log.is_file() else next(iter(sorted(run_dir.glob("logs/*/events.jsonl"))), None)
    if path is None:
        raise SystemExit(f"no events.jsonl under {run_dir}/logs")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_snapshot(events: list[dict[str, Any]], world_state: dict[str, Any], *, agents_meta: dict[str, Any]) -> dict[str, Any]:
    """The JSON the static page reads, built with the dashboard's own projections."""
    from agent_ecology3.dashboard.server import _agent_graph, _resident_action_rows
    from agent_ecology3.viz.world_substrate_view import principal_order

    public_events = redact_events(events)
    world = public_world_state(world_state)
    owners = {a["id"]: a["owner"] for a in world["artifacts"]}
    rows = _resident_action_rows(public_events, owners)
    for row in rows:
        if row["action"] == "note":
            row["description"] = f"ended turn {row['agent_turn']} ({NOTE_WITHHELD})"
    keep = ("turn", "agent_turn", "principal_id", "action", "description", "artifact_id", "success",
            "error_code", "value_amount", "value_unit", "counterparty")
    rows = [{k: row.get(k) for k in keep} for row in rows]
    graph = _agent_graph(public_events, world)
    solved = graph["summary"]["tasks_solved"]
    scored = [e for e in public_events if e.get("event_type") == "task_bounty_scored"]
    agents = []
    for principal in sorted(world["principals"], key=principal_order):
        mine = [r for r in rows if r["principal_id"] == principal and r["action"] != "note"]
        agents.append({
            "id": principal,
            "final_scrip": world["balances"].get(principal, {}).get("scrip"),
            "turns": int((agents_meta.get(principal) or {}).get("turns") or 0),
            "actions": len(mine),
            "refused": sum(1 for r in mine if not r["success"]),
        })
    return {
        "schema_version": "ae3_public_replay.v1",
        "run_id": world["run_id"],
        "summary": {
            "agents": len(world["principals"]),
            "turns_per_agent": max((a["turns"] for a in agents), default=0),
            "events_shown": len(rows),
            "tasks_in_bank": sum(1 for a in world["artifacts"] if a["type"] == "task_statement"),
            "tasks_solved": solved,
            "submissions": len(scored),
            "failed_submissions": sum(1 for e in scored if not e.get("passed")),
            "unpaid_passes": sum(1 for e in scored if e.get("passed") and not e.get("first_claim")),
            "royalties": sum(1 for e in public_events if e.get("event_type") == "royalty_paid"),
        },
        "agents": agents,
        "actions": rows,
        "graph": graph,
        "withheld": [
            "task statements, hidden tests and agents' solution code (CodeFlowBench-derived; redistribution terms unverified)",
            "agents' end-of-turn notes and message text (they can quote the above)",
            "checker messages beyond the error type",
            "session ids, local paths and the agents' working folders",
        ],
    }


def render_living(events: list[dict[str, Any]], world_state: dict[str, Any], run_id: str) -> str:
    """World Substrate living view of the redacted events (notes are empty, so no note bubbles)."""
    from agent_ecology3.dashboard.server import _living_view_inputs
    from agent_ecology3.viz.world_substrate_view import build_profile, build_projection, render_living_view

    public_events = redact_events(events)
    world = public_world_state(world_state)
    principals, task_ids = _living_view_inputs(public_events, world)
    bundle = build_projection(public_events, run_id=run_id, principals=principals, task_ids=task_ids, starting_scrip=100)
    profile = build_profile(bundle, principals=principals, task_ids=task_ids)
    page = render_living_view(bundle, profile)
    return page.replace("</head>", LIVING_EXTRA_HEAD + "</head>", 1).replace("</body>", LIVING_EXTRA_BODY + "</body>", 1)


# Added around World Substrate's page (its renderer is not edited): a back link,
# phone-width wrapping, and a styled tooltip on every control.
LIVING_EXTRA_HEAD = """<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
html,body{max-width:100%;overflow-x:hidden}
svg,canvas,img{max-width:100%;height:auto}
/* Blue and orange only (no red versus green): override the renderer's tokens. */
:root{--good:#7fb3ff!important;--danger:#f4a259!important;--warn:#f4a259!important;--accent:#7fb3ff!important}
[style*="--accent"]{--accent:#7fb3ff!important}
.actor.state-positive .actor-aura{background:radial-gradient(circle,#7fb3ff55,transparent 70%)!important}
.actor.state-warning .actor-aura,.actor.state-danger .actor-aura{background:radial-gradient(circle,#f4a25966,transparent 70%)!important}
.feedback.accepted{border-color:#7fb3ff!important}
.feedback:not(.accepted){border-color:#f4a259!important}
/* Phone width: the label bar sits below the scene instead of covering its controls. */
@media (max-width:700px){body>div[style*="position:fixed"][style*="bottom:0"]{position:static!important}}
.ae3-tip{position:fixed;z-index:1000;width:max-content;max-width:min(280px,calc(100vw - 8px));padding:6px 9px;border-radius:6px;background:#0b1730;color:#f1f5f9;
font:12px/1.35 system-ui,sans-serif;border:1px solid #7fb3ff;pointer-events:none;display:none}
.ae3-back{position:fixed;top:8px;right:8px;z-index:100;font:13px system-ui;background:#0b1730;color:#7fb3ff;
border:1px solid #7fb3ff;border-radius:6px;padding:4px 9px;text-decoration:none}
</style>"""
LIVING_EXTRA_BODY = """<a class="ae3-back" href="./" data-tip="Back to the activity feed and the Interactions matrix">← Feed and matrix</a>
<div class="ae3-tip" id="ae3Tip" role="tooltip"></div>
<script>
(function(){
  const words={play:'Play the replay from the current moment',pause:'Pause the replay',
    step:'Move one step',reset:'Go back to the start'};
  function label(el){
    if(el.dataset.tip) return el.dataset.tip;
    const t=(el.getAttribute('aria-label')||el.title||el.textContent||'').trim();
    if(el.id==='scrub'||el.type==='range') return 'Drag to move through the run: each step is one thing an agent did';
    if(el.tagName==='SELECT') return 'Choose what this view shows';
    const k=t.toLowerCase();
    for(const w in words){ if(k.includes(w)) return words[w]; }
    return t ? t + ' (World Substrate replay control)' : 'World Substrate replay control';
  }
  function attach(){
    document.querySelectorAll('button,input,select,a,[role=button],summary').forEach(el=>{
      if(!el.dataset.tip){ el.dataset.tip=label(el); }
      if(el.title){ el.removeAttribute('title'); }
    });
  }
  const tip=document.getElementById('ae3Tip');
  function show(el){ const r=el.getBoundingClientRect(); tip.textContent=el.dataset.tip; tip.style.display='block';
    const w=tip.offsetWidth, h=tip.offsetHeight;
    tip.style.left=Math.max(4,Math.min(window.innerWidth-w-4,r.left+r.width/2-w/2))+'px';
    tip.style.top=(r.top>h+10? r.top-h-6 : r.bottom+6)+'px'; }
  function hide(){ tip.style.display='none'; }
  document.addEventListener('mouseover',e=>{ const el=e.target.closest('[data-tip]'); if(el) show(el); else hide(); });
  document.addEventListener('focusin',e=>{ const el=e.target.closest('[data-tip]'); if(el) show(el); });
  document.addEventListener('focusout',hide);
  let pressTimer=null;
  document.addEventListener('touchstart',e=>{ const el=e.target.closest('[data-tip]'); if(el){ pressTimer=setTimeout(()=>show(el),450);} },{passive:true});
  document.addEventListener('touchend',()=>{ clearTimeout(pressTimer); setTimeout(hide,1800); });
  attach(); new MutationObserver(attach).observe(document.body,{childList:true,subtree:true});
})();
</script>"""


def leak_counts(blob: str, bank: dict[str, dict[str, Any]]) -> dict[str, int]:
    """Counts of each private-content class found in ``blob`` (all should be 0)."""
    found = _EVIDENCE._leaks(blob, bank)
    counts = {
        "bank sentence": sum(1 for f in found if f.endswith("statement text")),
        "hidden test input": sum(1 for f in found if f.endswith("hidden test input")),
    }
    for name, pattern in PRIVATE_PATTERNS.items():
        counts[name] = len(pattern.findall(blob))
    return counts


def check_dir(out: Path, bank_path: Path) -> dict[str, int]:
    blob = "\n".join(p.read_text(encoding="utf-8") for p in sorted(out.rglob("*")) if p.is_file())
    return leak_counts(blob, _EVIDENCE._bank(bank_path))


def build(run_dir: Path, bank_path: Path, out: Path) -> int:
    receipt = json.loads((run_dir / "run_receipt.json").read_text(encoding="utf-8"))
    world_state = receipt["world_state"]
    events = _read_events(run_dir)
    snapshot = build_snapshot(events, world_state, agents_meta=receipt.get("agents") or {})
    files = {
        "snapshot.json": json.dumps(snapshot, separators=(",", ":")),
        "index.html": PAGE_TEMPLATE.read_text(encoding="utf-8"),
        "living.html": render_living(events, world_state, str(snapshot["run_id"])),
    }
    counts = leak_counts("\n".join(files.values()), _EVIDENCE._bank(bank_path))
    print("leak check:", json.dumps(counts))
    if any(counts.values()):
        print("REFUSED: private content would be published", file=sys.stderr)
        return 1
    out.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8")
    print(f"wrote {len(files)} files to {out}: {snapshot['summary']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["build", "check"])
    parser.add_argument("path", type=Path, help="run directory (build) or built directory (check)")
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    if args.command == "build":
        return build(args.path, args.bank, args.out)
    counts = check_dir(args.path, args.bank)
    print("leak check:", json.dumps(counts), "total:", sum(counts.values()))
    return 1 if any(counts.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
