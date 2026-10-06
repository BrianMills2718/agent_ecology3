"""The declared model (docs/model/ae3_model.yaml) matches the events the code emits.

No model calls. Scans src/ with the Python parser for ``<x>.logger.log("<type>", {...})``
calls and compares them with the YAML in both directions, so a new event type,
a removed one, a moved emitter or a changed payload fails here until the model
is updated.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest
import yaml

from agent_ecology3.world.actions import ActionType

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "docs" / "model" / "ae3_model.yaml"
SRC = ROOT / "src"
VIEWS = ("feed", "matrix", "living")
COVERAGE_VALUES = {"shown", "partial", "hidden", "missing"}


def _is_logger_log(node: ast.Call) -> bool:
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr != "log":
        return False
    owner = func.value
    return (isinstance(owner, ast.Attribute) and owner.attr == "logger") or (
        isinstance(owner, ast.Name) and owner.id == "logger"
    )


def _emitters_in_code() -> dict[str, list[dict[str, Any]]]:
    """event type -> [{file, line, function, keys}] for every logger.log call under src/."""
    found: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        functions = [
            n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not _is_logger_log(node):
                continue
            rel = str(path.relative_to(ROOT))
            first = node.args[0] if node.args else None
            assert isinstance(first, ast.Constant) and isinstance(first.value, str), (
                f"{rel}:{node.lineno} logs a non-literal event type; declare event types as string literals"
            )
            enclosing = [f for f in functions if f.lineno <= node.lineno <= (f.end_lineno or f.lineno)]
            function = min(enclosing, key=lambda f: (f.end_lineno or f.lineno) - f.lineno).name if enclosing else "<module>"
            keys: list[str] | None = None
            if len(node.args) > 1 and isinstance(node.args[1], ast.Dict):
                keys = [
                    k.value if isinstance(k, ast.Constant) and isinstance(k.value, str) else "**"
                    for k in node.args[1].keys
                ]
            found.setdefault(first.value, []).append(
                {"file": rel, "line": node.lineno, "function": function, "keys": keys}
            )
    return found


@pytest.fixture(scope="module")
def model() -> dict[str, Any]:
    data = yaml.safe_load(MODEL_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and data.get("schema") == "ae3-model/v1"
    return data


@pytest.fixture(scope="module")
def code_emitters() -> dict[str, list[dict[str, Any]]]:
    return _emitters_in_code()


def test_every_emitted_event_is_declared_and_vice_versa(
    model: dict[str, Any], code_emitters: dict[str, list[dict[str, Any]]]
) -> None:
    declared = {event["name"] for event in model["events"]}
    assert len(declared) == len(model["events"]), "duplicate event names in the model"
    in_code = set(code_emitters)
    assert sorted(in_code - declared) == [], "events emitted in code but not declared in ae3_model.yaml"
    assert sorted(declared - in_code) == [], "events declared in ae3_model.yaml but never emitted in code"


def test_declared_emitters_and_fields_match_code(
    model: dict[str, Any], code_emitters: dict[str, list[dict[str, Any]]]
) -> None:
    for event in model["events"]:
        name = event["name"]
        actual = code_emitters[name]
        declared_sites = {(e["file"], e["function"]) for e in event["emitters"]}
        actual_sites = {(e["file"], e["function"]) for e in actual}
        assert declared_sites == actual_sites, f"{name}: declared emitters differ from code"
        for site in actual:
            if site["keys"] is None:
                assert "fields_from" in event, f"{name}: payload is not a dict literal; give fields_from"
                continue
            extra: list[str] = []
            for declared_site in event["emitters"]:
                if (declared_site["file"], declared_site["function"]) == (site["file"], site["function"]):
                    extra = list(declared_site.get("extra_fields", []))
            expected = [f for f in event["fields"] if not str(f).startswith("**")] + extra
            got = [k for k in site["keys"] if k != "**"]
            assert sorted(got) == sorted(expected), f"{name} at {site['file']}:{site['line']}: fields differ"


def test_processes_and_events_agree(model: dict[str, Any]) -> None:
    processes = {p["name"]: p for p in model["processes"]}
    assert len(processes) == len(model["processes"]), "duplicate process names"
    events = {e["name"]: e for e in model["events"]}
    scopes = set(model["scopes"])
    for event in events.values():
        assert event["scope"] in scopes, event["name"]
        for process in event["emitted_by"]:
            assert process in processes, f"{event['name']} names unknown process {process}"
            assert event["name"] in processes[process]["emits"], f"{process} does not list {event['name']}"
    for process in processes.values():
        assert process["scope"] in scopes, process["name"]
        for name in process["emits"]:
            assert name in events, f"{process['name']} emits undeclared {name}"
            assert process["name"] in events[name]["emitted_by"], f"{name} does not name {process['name']}"


def test_every_kernel_action_has_a_process(model: dict[str, Any]) -> None:
    declared = {p["action_type"] for p in model["processes"] if "action_type" in p}
    expected = {a.value for a in ActionType} | {"send_message"}
    assert sorted(expected - declared) == [], "kernel actions with no declared process"
    assert sorted(declared - expected) == [], "declared processes for actions the kernel does not have"


def test_view_coverage_names_resident_events(model: dict[str, Any]) -> None:
    events = {e["name"]: e for e in model["events"]}
    coverage = model["view_coverage"]
    resident = {name for name, e in events.items() if e["scope"] == "resident"}
    assert set(coverage) == resident, "view_coverage must list exactly the resident-scope events"
    for name, row in coverage.items():
        assert set(row) == set(VIEWS), name
        assert set(row.values()) <= COVERAGE_VALUES, name
