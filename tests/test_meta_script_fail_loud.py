"""Fail-loud regressions in the vendored meta-process scripts.

Ported from agent_ecology2's 2026-09 audit fixes (#1170, #1172), which apply
to these byte-identical copies: plan lookups by number must refuse to pick an
arbitrary file when two share a number, and read/git failures must not be
converted into empty content or an "unknown" verification commit.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

META = Path(__file__).resolve().parents[1] / "scripts" / "meta"


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def dup_plans(tmp_path: Path) -> Path:
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "229_old.md").write_text("# Plan 229: old\n**Status:** 📋 Planned\n")
    (plans / "229_new.md").write_text("# Plan 229: new\n**Status:** 📋 Planned\n")
    (plans / "07_padded.md").write_text("# Plan 7: padded\n**Status:** 📋 Planned\n")
    (plans / "7_unpadded.md").write_text("# Plan 7: unpadded\n**Status:** 📋 Planned\n")
    (plans / "05_single.md").write_text("# Plan 5: single\n**Status:** 📋 Planned\n")
    return plans


def test_complete_plan_duplicate_plan_number_fails(dup_plans: Path) -> None:
    mod = _load(META / "complete_plan.py", "ae3_meta_complete_plan")
    with pytest.raises(SystemExit):
        mod.find_plan_file(229, dup_plans)
    assert mod.find_plan_file(5, dup_plans) == dup_plans / "05_single.md"


def test_parse_plan_duplicate_across_padding_fails(
    dup_plans: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load(META / "parse_plan.py", "ae3_meta_parse_plan")
    monkeypatch.chdir(dup_plans.parent.parent)
    monkeypatch.setattr(mod, "get_main_repo_root", lambda: dup_plans.parent.parent)
    with pytest.raises(SystemExit, match="Multiple plan files for #7"):
        mod.find_plan_file(7)
    assert mod.find_plan_file(5).name == "05_single.md"


def test_check_claims_duplicate_plan_number_fails(
    dup_plans: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load(META / "worktree-coordination" / "check_claims.py", "ae3_meta_check_claims")
    monkeypatch.setattr(mod, "PLANS_DIR", dup_plans)
    with pytest.raises(SystemExit, match="229_old.md"):
        mod.get_plan_status(229)
    assert mod.get_plan_status(404) == ("unknown", [])


def test_sync_plan_status_duplicate_plan_number_fails(
    dup_plans: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load(META / "sync_plan_status.py", "ae3_meta_sync_plan_status")
    index = dup_plans / "AGENTS.md"
    index.write_text("| # | Name | Status |\n|---|---|---|\n")
    monkeypatch.setattr(mod, "PLANS_DIR", dup_plans)
    monkeypatch.setattr(mod, "INDEX_FILE", index)
    with pytest.raises(SystemExit, match="Duplicate plan number"):
        mod.check_consistency()


def test_check_mock_usage_unreadable_file_fails_loudly(tmp_path: Path) -> None:
    mod = _load(META / "check_mock_usage.py", "ae3_meta_check_mock_usage")
    missing = tmp_path / "test_gone.py"
    with pytest.raises(OSError) as exc:
        mod.check_suspicious({str(missing): [(3, "@patch('src.world.ledger')")]})
    assert str(missing) in str(exc.value)


@pytest.mark.parametrize("subdir", ["nope", None])
def test_complete_plan_git_info_fails_loudly_outside_a_repo(
    tmp_path: Path, subdir: str | None
) -> None:
    mod = _load(META / "complete_plan.py", "ae3_meta_complete_plan_git")
    target = tmp_path / subdir if subdir else tmp_path
    with pytest.raises(SystemExit) as exc:
        mod.get_git_info(target)
    assert str(target) in str(exc.value.code)


def test_complete_plan_updates_the_agents_md_plan_index(tmp_path: Path) -> None:
    # docs/plans/CLAUDE.md was renamed to AGENTS.md (#58); the index update
    # must follow it rather than silently skipping a now-missing file.
    mod = _load(META / "complete_plan.py", "ae3_meta_complete_plan_index")
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    index = plans / "AGENTS.md"
    index.write_text("| 5 | [Single](05_single.md) | High | 📋 Planned | - |\n")
    assert mod.update_plan_index(5, plans) is True
    assert "✅ Complete" in index.read_text()
