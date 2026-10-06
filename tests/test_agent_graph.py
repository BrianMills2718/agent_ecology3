"""Agents-only typed-graph/v1 projection (Plan 26 M2); no model calls."""

from __future__ import annotations

from agent_ecology3.dashboard.server import _agent_graph


def test_agent_graph_links_code_reads_and_reuse_and_counts_statement_reads() -> None:
    world_state = {
        "principals": ["alpha_10", "alpha_2", "alpha_1"],
        "balances": {"alpha_1": {"scrip": 120}},
        "artifacts": [
            {"id": "alpha_1_task_x", "type": "task_statement"},
            {"id": "alpha_1_sol", "type": "solution:CF/X/digits"},
        ],
    }
    events = [
        {"event_type": "artifact_read", "principal_id": "alpha_2", "recipient": "alpha_1",
         "artifact_id": "alpha_1_task_x", "read_price_paid": 2},
        {"event_type": "artifact_read", "principal_id": "alpha_2", "recipient": "alpha_1",
         "artifact_id": "alpha_1_sol", "read_price_paid": 0},
        {"event_type": "artifact_read", "principal_id": "alpha_2", "recipient": "alpha_1",
         "artifact_id": "alpha_1_sol", "read_price_paid": 0},
        {"event_type": "royalty_paid", "principal_id": "alpha_1", "solver": "alpha_2", "amount": 3},
        {"event_type": "task_bounty_scored", "principal_id": "alpha_2", "first_claim": True},
        {"event_type": "artifact_read", "principal_id": "alpha_1", "recipient": "alpha_1",
         "artifact_id": "alpha_1_task_x", "read_price_paid": 2},
    ]
    out = _agent_graph(events, world_state)
    graph = out["graph"]
    assert graph["schema"] == "typed-graph/v1"
    assert [n["id"] for n in graph["nodes"]] == ["alpha_1", "alpha_2", "alpha_10"]
    assert graph["nodes"][1]["label"] == "Agent 2 · 1 solved"
    edges = {e["id"]: e for e in graph["edges"]}
    assert set(edges) == {"read:alpha_2->alpha_1", "reused:alpha_2->alpha_1"}
    assert edges["read:alpha_2->alpha_1"]["label"] == "read code ×2" and not edges["read:alpha_2->alpha_1"]["dashed"]
    assert edges["reused:alpha_2->alpha_1"]["dashed"] is True
    assert out["summary"]["statement_reads"] == 1
    assert "paid 2 scrip to read 1 other agents' task descriptions" in out["details"]["alpha_2"]
    assert set(graph) == {"schema", "kinds", "nodes", "edges", "layout"}


def test_agent_graph_counts_messages() -> None:
    events = [{"event_type": "agent_message", "principal_id": "alpha_1", "recipient": "alpha_2", "text": "hi"}] * 3
    out = _agent_graph(events, {"principals": ["alpha_1", "alpha_2"], "artifacts": []})
    assert [(e["id"], e["label"]) for e in out["graph"]["edges"]] == [("messaged:alpha_1->alpha_2", "messaged ×3")]
    assert out["summary"]["messages"] == 3
