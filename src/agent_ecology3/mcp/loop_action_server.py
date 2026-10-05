"""MCP stdio server that exposes a single AE3 action tool.

This tool lets agent SDK models (for example, Claude Code) emit one kernel
action payload in tool-call form so AE3 can parse and execute it.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from mcp.server.mcpserver import MCPServer


server = MCPServer("ae3-loop-action")


def _build_action_payload(
    *,
    action_type: str,
    artifact_id: str | None,
    artifact_type: str | None,
    content: str | None,
    recipient_id: str | None,
    amount: float | None,
    memo: str | None,
    resource: str | None,
    bid: int | None,
    query_type: str | None,
    params: dict[str, Any] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"action_type": action_type.strip()}
    if artifact_id:
        payload["artifact_id"] = artifact_id
    if artifact_type:
        payload["artifact_type"] = artifact_type
    if content is not None:
        payload["content"] = content
    if recipient_id:
        payload["recipient_id"] = recipient_id
    if amount is not None:
        payload["amount"] = amount
    if memo is not None:
        payload["memo"] = memo
    if resource:
        payload["resource"] = resource
    if bid is not None:
        payload["bid"] = bid
    if query_type:
        payload["query_type"] = query_type
    if isinstance(params, dict):
        payload["params"] = params
    return payload


@server.tool(
    name="ae3_action",
    description=(
        "Submit one AE3 kernel action payload. "
        "Use action_type plus action-specific fields (artifact_id, recipient_id, amount, etc.)."
    ),
)
def ae3_action(
    action_type: str,
    artifact_id: str | None = None,
    artifact_type: str | None = None,
    content: str | None = None,
    recipient_id: str | None = None,
    amount: float | None = None,
    memo: str | None = None,
    resource: str | None = None,
    bid: int | None = None,
    query_type: str | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _build_action_payload(
        action_type=action_type,
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        content=content,
        recipient_id=recipient_id,
        amount=amount,
        memo=memo,
        resource=resource,
        bid=bid,
        query_type=query_type,
        params=params,
    )
    kernel_url = os.environ.get("AE3_KERNEL_URL")
    if not kernel_url:
        # Legacy loop mode: the world parses the echoed tool call afterwards.
        return {
            "ok": True,
            "action": payload,
        }
    return _execute_on_kernel(kernel_url, payload)


def _execute_on_kernel(kernel_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Resident mode: the kernel executes the action and returns the real outcome.

    The acting principal comes from this server's launch environment, never
    from tool arguments, so an agent can only act as itself.
    """
    principal_id = os.environ["AE3_PRINCIPAL_ID"]
    token = os.environ["AE3_AGENT_TOKEN"]
    request = urllib.request.Request(
        f"{kernel_url.rstrip('/')}/agent-act/{principal_id}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result: dict[str, Any] = json.loads(response.read().decode("utf-8"))
            return result
    except urllib.error.HTTPError as exc:
        return {"success": False, "error": f"kernel refused action: HTTP {exc.code}", "error_code": "kernel_refused"}


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()

