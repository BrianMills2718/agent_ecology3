from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_ecology3.analysis.phase1_suite import _parse_conditions, _resolve_summary_path


def test_parse_conditions_accepts_supported_values() -> None:
    assert _parse_conditions("baseline,reduced,off") == ["baseline", "reduced", "off"]
    assert _parse_conditions(" baseline , OFF ") == ["baseline", "off"]


def test_parse_conditions_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="unsupported condition"):
        _parse_conditions("baseline,custom")
    with pytest.raises(ValueError, match="must include at least one"):
        _parse_conditions("   ")


def test_resolve_summary_path_picks_most_recent(tmp_path: Path) -> None:
    older = tmp_path / "phase1_suite_demo_baseline_111_summary.json"
    newer = tmp_path / "phase1_suite_demo_baseline_222_summary.json"
    older.write_text(json.dumps({"old": True}), encoding="utf-8")
    newer.write_text(json.dumps({"new": True}), encoding="utf-8")
    older.touch()
    newer.touch()

    resolved = _resolve_summary_path(tmp_path, "phase1_suite_demo_baseline")
    assert resolved == newer


def test_resolve_summary_path_returns_none_when_missing(tmp_path: Path) -> None:
    assert _resolve_summary_path(tmp_path, "missing_prefix") is None
