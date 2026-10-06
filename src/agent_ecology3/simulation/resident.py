"""Resident agents: long-lived agent sessions acting only through ae3_action.

Each principal is one Claude Agent SDK session (via the shared llm_client)
that is resumed every turn. The agent's only tool is the ``ae3_action`` MCP
server, which forwards each action to this kernel's ``/agent-act`` endpoint.
The kernel authenticates the principal, executes the action, records a
``resident_action`` event, and returns the real outcome to the agent.

The kernel owns all world state and receipts; the agent harness owns memory,
planning and tool use (FAILURE_MODE_DOSSIER FM-02/FM-07, design constraint 1).
"""

from __future__ import annotations

import asyncio
import secrets
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request

from ..world.world import World

MCP_SERVER_SCRIPT = Path(__file__).resolve().parents[1] / "mcp" / "loop_action_server.py"
AE3_TOOL_NAME = "mcp__ae3__ae3_action"
DISALLOWED_BUILTIN_TOOLS = [
    "Bash", "BashOutput", "Edit", "Glob", "Grep", "KillShell", "NotebookEdit",
    "Read", "Task", "TodoWrite", "WebFetch", "WebSearch", "Write",
]


SHELL_ITEM_TYPES = frozenset({"command_execution", "commandExecution"})


def count_shell_commands(codex_items: list[Any]) -> int:
    """Count shell commands in llm_client's completed Codex items.

    llm_client returns each completed item directly (``item["type"]``); the
    CLI stream spells it ``command_execution``, the app server
    ``commandExecution``.
    """
    return sum(
        1 for item in codex_items
        if isinstance(item, dict) and item.get("type") in SHELL_ITEM_TYPES
    )


class ResidentRunError(RuntimeError):
    """An authentic resident turn failed; the run stops instead of substituting."""


@dataclass
class ResidentAgent:
    principal_id: str
    token: str
    workdir: Path
    session_id: str | None = None
    codex_home: str | None = None
    turns_taken: int = 0
    actions_this_turn: int = 0
    session_ids_seen: list[str] = field(default_factory=list)


class ResidentKernel:
    """Authenticated action endpoint plus per-turn bookkeeping over one World."""

    def __init__(self, world: World, agents_root: Path, *, actions_per_turn: int) -> None:
        self.world = world
        self.actions_per_turn = actions_per_turn
        self.turn = 0
        self.lock = asyncio.Lock()
        self.agents: dict[str, ResidentAgent] = {}
        for principal_id in world.principal_ids:
            workdir = agents_root / principal_id
            workdir.mkdir(parents=True, exist_ok=True)
            self.agents[principal_id] = ResidentAgent(
                principal_id=principal_id, token=secrets.token_urlsafe(24), workdir=workdir
            )

    def install_routes(self, app: FastAPI) -> None:
        @app.post("/agent-act/{principal_id}")
        async def agent_act(
            principal_id: str, request: Request, authorization: str = Header(default="")
        ) -> dict[str, Any]:
            agent = self.agents.get(principal_id)
            if agent is None or authorization != f"Bearer {agent.token}":
                raise HTTPException(status_code=403, detail="unknown principal or bad token")
            payload = await request.json()
            if not isinstance(payload, dict):
                raise HTTPException(status_code=400, detail="action payload must be an object")
            return await self.act(agent, payload)

    async def act(self, agent: ResidentAgent, payload: dict[str, Any]) -> dict[str, Any]:
        async with self.lock:
            if agent.actions_this_turn >= self.actions_per_turn:
                outcome: dict[str, Any] = {
                    "success": False,
                    "error": f"turn limit reached: at most {self.actions_per_turn} actions per turn",
                    "error_code": "turn_action_limit",
                }
            else:
                agent.actions_this_turn += 1
                result = self.world.execute_action_data(agent.principal_id, payload)
                outcome = {
                    "success": bool(result.success),
                    "message": result.message,
                    "error_code": result.error_code,
                    "data": result.data,
                    "scrip_after": self.world.ledger.get_scrip(agent.principal_id),
                }
            self.world.logger.log(
                "resident_action",
                {
                    "event_number": self.world.event_number,
                    "turn": self.turn,
                    "principal_id": agent.principal_id,
                    "session_id": agent.session_id,
                    "action_type": payload.get("action_type"),
                    "artifact_id": payload.get("artifact_id"),
                    "success": outcome["success"],
                    "error_code": outcome.get("error_code"),
                },
            )
            return outcome

    def observation(self, agent: ResidentAgent) -> str:
        """What the agent sees at the start of its turn (kernel-generated)."""
        listing = self.world.query_handler.execute(
            "artifacts", {"_principal_id": agent.principal_id, "readable_only": True, "limit": 200}
        )
        rows = [
            row for row in listing.get("results", [])
            if not str(row.get("id", "")).endswith(("_loop", "_strategy", "_state", "_notebook"))
            and row.get("id") not in self.world.principal_ids
        ]
        lines = [
            f"- {row['id']} (type {row['type']}, owner {row['owner']}, read price {row['read_price']}"
            + (f", bounty claimed by {row['bounty_claimed_by']}" if row.get("bounty_claimed_by") else "")
            + ")"
            for row in rows
        ]
        balances = {pid: self.world.ledger.get_scrip(pid) for pid in self.world.principal_ids}
        return (
            f"Turn {self.turn}. You are {agent.principal_id}. Your scrip: "
            f"{balances[agent.principal_id]}. All scrip balances: {balances}.\n"
            f"Artifacts you can see now ({len(rows)}):\n" + "\n".join(lines)
        )


RESIDENT_RULES = """You are {principal_id}, a long-lived agent in an economy simulation. You keep
your memory between turns. Your only way to act is the ae3_action tool; each
call returns the real result. You may make up to {actions_per_turn} ae3_action
calls this turn, then end your turn with a one-paragraph note to yourself about
what you learned and what you plan next.

Rules of this economy: some artifacts state programming tasks. Solving one
means writing an artifact (action_type write_artifact) whose artifact_type is
"solution:<task id>" and whose content is plain Python defining the requested
function, then submitting it (action_type submit_to_mint, bid 1; the bid is
refunded). An outside checker runs hidden tests at once and tells you the
result. The first passing solution for a task earns 10 scrip; later solutions
for the same task earn nothing, and the artifact list shows tasks already
claimed. Reading an artifact you do not own (action_type read_artifact) costs
its read price, paid to its owner, and returns its content. You may set
read_price on your own artifacts. Use artifact ids prefixed with {principal_id}_.
Other actions: transfer (recipient_id, amount), query_kernel (query_type, params).
You have no assigned role or strategy; decide for yourself.
"""


def _ae3_mcp_server(agent: ResidentAgent, kernel_url: str) -> dict[str, Any]:
    return {
        "type": "stdio",
        "command": sys.executable,
        "args": [str(MCP_SERVER_SCRIPT)],
        "env": {
            "PYTHONUNBUFFERED": "1",
            "AE3_KERNEL_URL": kernel_url,
            "AE3_PRINCIPAL_ID": agent.principal_id,
            "AE3_AGENT_TOKEN": agent.token,
        },
    }


def codex_call_kwargs(agent: ResidentAgent, kernel_url: str, *, reasoning_effort: str) -> dict[str, Any]:
    """Codex CLI options (llm_client built-ins): persistent per-agent home with the
    ae3 MCP server, read-only sandbox, never-ask approvals, resumed session."""
    if agent.codex_home is None:
        from llm_client.sdk.agents_codex import _create_codex_home

        import shutil

        created = _create_codex_home({"ae3": _ae3_mcp_server(agent, kernel_url)})
        # Keep the session home with the run (Codex refuses helpers under /tmp,
        # and the session must survive the turn).
        target = agent.workdir / "codex_home"
        shutil.move(created, target)
        # llm_client links `sessions` to the user's real Codex history so a
        # throwaway home cannot lose transcripts. This home is persistent and
        # run-owned, so keep transcripts here instead: otherwise every agent
        # indexes the user's whole Codex history (about 300 MB per agent) and
        # its sessions land among the user's own.
        sessions = target / ".codex" / "sessions"
        if sessions.is_symlink():
            sessions.unlink()
        sessions.mkdir(exist_ok=True)
        # Under approval_policy=never Codex rejects MCP calls that need approval;
        # pre-approve only this server's tools (the kernel is the authority).
        config_path = target / ".codex" / "config.toml"
        config = config_path.read_text(encoding="utf-8")
        header = '[mcp_servers."ae3"]\n'
        if header not in config:
            raise ResidentRunError("codex home is missing the ae3 MCP server table")
        config_path.write_text(
            config.replace(header, header + 'default_tools_approval_mode = "approve"\n', 1),
            encoding="utf-8",
        )
        agent.codex_home = str(target)
    kwargs: dict[str, Any] = {
        "codex_home": agent.codex_home,
        "codex_transport": "cli",
        "reasoning_effort": reasoning_effort,
        "working_directory": str(agent.workdir),
        "sandbox_mode": "read-only",
        "approval_policy": "never",
        "skip_git_repo_check": True,
        "fallback_models": [],
        # No wall-clock cutoff: a turn is bounded by the kernel's per-turn
        # action limit, not a timer (an agent turn makes several tool calls).
        "agent_hard_timeout": 0,
    }
    if agent.session_id:
        kwargs["codex_session_mode"] = "resume"
        kwargs["codex_session_id"] = agent.session_id
    else:
        kwargs["codex_session_mode"] = "fresh"
    return kwargs


def agent_call_kwargs(agent: ResidentAgent, kernel_url: str, *, max_turns: int) -> dict[str, Any]:
    """Claude Agent SDK options: only the ae3 MCP tool, no built-ins, resumed session."""
    kwargs: dict[str, Any] = {
        "cwd": str(agent.workdir),
        "max_turns": max_turns,
        "mcp_servers": {
            "ae3": {
                "type": "stdio",
                "command": sys.executable,
                "args": [str(MCP_SERVER_SCRIPT)],
                "env": {
                    "PYTHONUNBUFFERED": "1",
                    "AE3_KERNEL_URL": kernel_url,
                    "AE3_PRINCIPAL_ID": agent.principal_id,
                    "AE3_AGENT_TOKEN": agent.token,
                },
            }
        },
        "allowed_tools": [AE3_TOOL_NAME],
        "disallowed_tools": list(DISALLOWED_BUILTIN_TOOLS),
        "tools": [],
        "strict_mcp_config": True,
        "setting_sources": [],
    }
    if agent.session_id:
        kwargs["resume"] = agent.session_id
    return kwargs


async def run_agent_turn(
    kernel: ResidentKernel,
    agent: ResidentAgent,
    *,
    model: str,
    kernel_url: str,
    run_id: str,
    acall_llm: Any,
    reasoning_effort: str = "low",
) -> dict[str, Any]:
    """One resumed turn for one agent. Raises ResidentRunError on any failure."""
    agent.actions_this_turn = 0
    prompt = kernel.observation(agent)
    if agent.session_id is None:
        prompt = RESIDENT_RULES.format(
            principal_id=agent.principal_id, actions_per_turn=kernel.actions_per_turn
        ) + "\n" + prompt
    trace_id = f"ae3/{run_id}/turn_{kernel.turn}/{agent.principal_id}"
    try:
        result = await acall_llm(
            model,
            [{"role": "user", "content": prompt}],
            task="agent_ecology3_resident_turn",
            trace_id=trace_id,
            max_budget=0,
            num_retries=0,
            model_justification=kernel.world.config.llm.model_justification,
            **(
                codex_call_kwargs(agent, kernel_url, reasoning_effort=reasoning_effort)
                if model.startswith("codex/")
                else agent_call_kwargs(agent, kernel_url, max_turns=kernel.actions_per_turn * 2 + 2)
            ),
        )
    except Exception as exc:  # noqa: BLE001 - surface the original boundary error
        raise ResidentRunError(f"{agent.principal_id} turn {kernel.turn} failed: {type(exc).__name__}: {exc}") from exc
    usage = getattr(result, "usage", {}) or {}
    raw = getattr(result, "raw_response", None)
    session_id = usage.get("session_id") or (raw.get("session_id") if isinstance(raw, dict) else None)
    if not isinstance(session_id, str) or not session_id:
        raise ResidentRunError(f"{agent.principal_id} turn {kernel.turn}: no session id returned")
    if agent.session_id is not None and session_id != agent.session_id:
        # A resumed SDK session may be forked to a new id; keep it, but record it.
        kernel.world.logger.log(
            "resident_session_changed",
            {"principal_id": agent.principal_id, "turn": kernel.turn, "old": agent.session_id, "new": session_id},
        )
    agent.session_id = session_id
    agent.session_ids_seen.append(session_id)
    agent.turns_taken += 1
    shell_commands = count_shell_commands(getattr(result, "codex_events", None) or [])
    builtin_calls = [] if model.startswith("codex/") else [
        call for call in (getattr(result, "tool_calls", None) or [])
        if isinstance(call, dict)
        and str((call.get("function") or {}).get("name") or call.get("name") or "") not in ("", AE3_TOOL_NAME, "ae3_action")
    ]
    note = str(getattr(result, "content", "") or "")
    kernel.world.logger.log(
        "resident_turn",
        {
            "turn": kernel.turn,
            "principal_id": agent.principal_id,
            "session_id": session_id,
            "trace_id": trace_id,
            "actions": agent.actions_this_turn,
            "num_turns": usage.get("num_turns"),
            "duration_ms": usage.get("duration_ms"),
            "builtin_tool_calls": len(builtin_calls),
            "sandboxed_shell_commands": shell_commands,
            "note": note[:2000],
            "finish_reason": getattr(result, "finish_reason", None),
            "cost": getattr(result, "cost", None),
            "cost_source": getattr(result, "cost_source", None),
        },
    )
    if builtin_calls:
        raise ResidentRunError(f"{agent.principal_id} used a non-ae3 tool: {builtin_calls[:1]}")
    if getattr(result, "finish_reason", None) == "error":
        raise ResidentRunError(f"{agent.principal_id} turn {kernel.turn} ended in error: {note[:300]}")
    return {"principal_id": agent.principal_id, "session_id": session_id, "actions": agent.actions_this_turn}
